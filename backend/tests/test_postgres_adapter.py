"""Unit tests for PostgreSQL/SQLite dual-engine adapter, connect_postgres script, and backend root health JSON."""
import ast
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import MagicMock, patch
from flask import Flask, jsonify

from database import (
    DatabaseConnection,
    HybridRow,
    connect_database,
    get_db_engine_name,
    is_postgres_target,
    resolve_database_target,
    translate_sql_for_postgres,
)
from mqtt_listener import get_mqtt_config, parse_and_validate_scd40_payload, process_mqtt_scd40_message
from scripts.connect_postgres import mask_dsn, resolve_postgres_dsn
from scripts.docker_bootstrap import wait_for_database

BACKEND_ROOT = Path(__file__).resolve().parents[1]


class PostgresAdapterTests(unittest.TestCase):
    def test_hybrid_row_supports_dict_tuple_and_index_access(self):
        row = HybridRow(["id", "co2_ppm", "source"], [42, 715.5, "scd40"])
        self.assertEqual(row[0], 42)
        self.assertEqual(row["co2_ppm"], 715.5)
        self.assertEqual(dict(row), {"id": 42, "co2_ppm": 715.5, "source": "scd40"})
        self.assertEqual(tuple(row), (42, 715.5, "scd40"))
        self.assertEqual(len(row), 3)

    def test_sql_translation_handles_ddl_pragma_conflict_and_julianday(self):
        ddl, ret = translate_sql_for_postgres(
            "CREATE TABLE IF NOT EXISTS sensor_readings (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT)"
        )
        self.assertIn("BIGSERIAL PRIMARY KEY", ddl)
        self.assertFalse(ret)

        pragma_wal, _ = translate_sql_for_postgres("PRAGMA journal_mode=WAL")
        self.assertEqual(pragma_wal, "SELECT 1")

        pragma_info, _ = translate_sql_for_postgres("PRAGMA table_info(occupancy_samples)")
        self.assertIn("information_schema.columns", pragma_info)
        self.assertIn("occupancy_samples", pragma_info)

        tracking_sql, tracking_ret = translate_sql_for_postgres(
            "INSERT OR IGNORE INTO tracking_points (sampled_at,session_id,track_id,x_norm,y_norm,confidence) VALUES (?,?,?,?,?,?)"
        )
        self.assertIn("ON CONFLICT (sampled_at, session_id, track_id) DO NOTHING", tracking_sql)
        self.assertEqual(tracking_sql.count("%s"), 6)
        self.assertFalse(tracking_ret)

        sensor_sql, _ = translate_sql_for_postgres(
            "SELECT * FROM sensor_readings WHERE julianday(timestamp) >= julianday(?) ORDER BY julianday(timestamp) DESC LIMIT ?"
        )
        self.assertIn("CAST(timestamp AS TIMESTAMPTZ) >= CAST(%s AS TIMESTAMPTZ)", sensor_sql)
        self.assertIn("ORDER BY CAST(timestamp AS TIMESTAMPTZ) DESC LIMIT %s", sensor_sql)

        insert_sql, has_returning = translate_sql_for_postgres(
            "INSERT INTO zone_visits (session_id,track_id,entered_at) VALUES (?,?,?)"
        )
        self.assertTrue(has_returning)
        self.assertTrue(insert_sql.endswith("RETURNING id"))

    def test_postgres_connection_wrapper_executes_and_returns_lastrowid(self):
        raw_conn = MagicMock()
        raw_cursor = MagicMock()
        raw_cursor.fetchone.return_value = (99,)
        raw_conn.cursor.return_value = raw_cursor

        db = DatabaseConnection(raw_conn, is_postgres=True, target="postgresql://postgres:secret@127.0.0.1:5432/smartoffice")
        cur = db.execute("INSERT INTO zone_visits (session_id,track_id,entered_at) VALUES (?,?,?)", ("s1", 1, "2026-11-14T10:00:00Z"))
        self.assertEqual(cur.lastrowid, 99)
        executed_sql, executed_params = raw_cursor.execute.call_args[0]
        self.assertIn("RETURNING id", executed_sql)
        self.assertEqual(executed_params, ("s1", 1, "2026-11-14T10:00:00Z"))

    def test_sqlite_fallback_and_postgres_target_resolution(self):
        self.assertTrue(is_postgres_target("postgresql://user:pass@localhost:5432/smartoffice"))
        self.assertTrue(is_postgres_target("postgres://user:pass@localhost:5432/smartoffice"))
        self.assertFalse(is_postgres_target("smartoffice.db"))

        with tempfile.TemporaryDirectory() as tmp:
            db_file = Path(tmp) / "fallback.db"
            db = connect_database(db_file)
            try:
                with db:
                    db.execute("CREATE TABLE test_items (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)")
                    cur = db.execute("INSERT INTO test_items (name) VALUES (?)", ("alpha",))
                    self.assertEqual(cur.lastrowid, 1)
                    row = db.execute("SELECT id, name FROM test_items WHERE id=?", (1,)).fetchone()
                    self.assertEqual(dict(row), {"id": 1, "name": "alpha"})
            finally:
                db.close()

    def test_connect_postgres_helpers_mask_password_and_resolve_dsn(self):
        dsn = "postgresql://postgres:rahasia123@127.0.0.1:5432/smartoffice"
        self.assertEqual(mask_dsn(dsn), "postgresql://postgres:***@127.0.0.1:5432/smartoffice")
        self.assertEqual(resolve_postgres_dsn(dsn), dsn)

    def test_backend_root_returns_json_health_without_redirect(self):
        app = Flask(__name__)
        ns = {
            "app": app,
            "os": __import__("os"),
            "jsonify": jsonify,
            "DATABASE_PATH": "isolated_test.db",
            "MODEL_PATH": "yolo11n.pt",
            "get_db_engine_name": get_db_engine_name,
            "get_mqtt_config": get_mqtt_config,
            "system_state": {"mqtt_status": "Terhubung ke MQTT (127.0.0.1:1883 -> smartoffice/scd40/telemetry)"},
        }
        tree = ast.parse((BACKEND_ROOT / "app.py").read_text(encoding="utf-8"))
        nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "index"]
        exec(compile(ast.Module(body=nodes, type_ignores=[]), "app_index", "exec"), ns)
        client = app.test_client()
        for path in ("/", "/api/health"):
            res = client.get(path)
            self.assertEqual(res.status_code, 200)
            body = res.get_json()
            self.assertEqual(body["service"], "smartoffice-backend")
            self.assertEqual(body["status"], "ok")
            self.assertEqual(body["database_engine"], "sqlite")
            self.assertEqual(body["mqtt"]["topic"], "smartoffice/scd40/telemetry")

    def test_mqtt_scd40_payload_validation_and_persistence(self):
        written = []
        state = {}
        lock = threading.Lock()
        reading = process_mqtt_scd40_message(
            b'{"co2_ppm":712,"temperature_c":25.3,"humidity_percent":54.1,"source":"scd40"}',
            db_write=lambda sql, params: written.append((sql, params)),
            state_lock=lock,
            system_state=state,
        )
        self.assertEqual(reading["co2_ppm"], 712.0)
        self.assertEqual(len(written), 1)
        self.assertEqual(state["sensor_status"], "Data SCD40 diterima")
        self.assertEqual(state["co2_ppm"], 712.0)

        alias_reading = parse_and_validate_scd40_payload('{"co2":690,"suhu":24.8,"lembap":50.5}')
        self.assertEqual(alias_reading["co2_ppm"], 690.0)
        self.assertEqual(alias_reading["temperature_c"], 24.8)
        self.assertEqual(alias_reading["humidity_percent"], 50.5)

        with self.assertRaises(ValueError):
            parse_and_validate_scd40_payload('{"co2_ppm":0,"temperature_c":25,"humidity_percent":50}')

    def test_docker_bootstrap_wait_for_database_succeeds_on_sqlite(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_file = Path(tmp) / "boot.db"
            wait_for_database(str(db_file), max_attempts=2, delay_sec=0.01)
