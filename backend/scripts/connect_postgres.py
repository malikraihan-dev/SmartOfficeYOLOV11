"""CLI script untuk menguji koneksi PostgreSQL, membuat database, dan menginisialisasi skema Smart Office."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import sys
import time
from urllib.parse import urlparse, urlunparse

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from database import (  # noqa: E402
    ISOLATION_LEVEL_AUTOCOMMIT,
    connect_database,
    is_postgres_target,
    load_backend_env,
    normalize_postgres_dsn,
    psycopg2,
)

DEFAULT_PG_DSN = "postgresql://postgres:postgres@127.0.0.1:5432/smartoffice"

APP_TABLES = (
    "sensor_readings",
    "evaluation_samples",
    "occupancy_samples",
    "tracking_points",
    "quality_events",
    "audio_samples",
    "zone_visits",
    "admins",
    "admin_sessions",
    "login_attempts",
)

POSTGRES_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS sensor_readings (
    id BIGSERIAL PRIMARY KEY,
    timestamp TEXT NOT NULL UNIQUE,
    co2_ppm DOUBLE PRECISION NOT NULL CHECK(co2_ppm > 0 AND co2_ppm <= 40000),
    temperature_c DOUBLE PRECISION NOT NULL CHECK(temperature_c >= -40 AND temperature_c <= 125),
    humidity_percent DOUBLE PRECISION NOT NULL CHECK(humidity_percent >= 0 AND humidity_percent <= 100),
    source TEXT NOT NULL DEFAULT 'scd40' CHECK(source = 'scd40')
);

CREATE TABLE IF NOT EXISTS evaluation_samples (
    id BIGSERIAL PRIMARY KEY,
    captured_at TEXT NOT NULL,
    predicted_count INTEGER NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    activity TEXT NOT NULL,
    objects_json TEXT NOT NULL,
    image_file TEXT NOT NULL,
    actual_count INTEGER,
    reviewed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_evaluation_pending ON evaluation_samples(actual_count, id DESC);

CREATE TABLE IF NOT EXISTS occupancy_samples (
    id BIGSERIAL PRIMARY KEY,
    sampled_at TEXT NOT NULL,
    session_id TEXT NOT NULL,
    person_count INTEGER NOT NULL,
    mean_confidence DOUBLE PRECISION NOT NULL,
    activity TEXT NOT NULL,
    camera_fps DOUBLE PRECISION DEFAULT 0,
    inference_ms DOUBLE PRECISION DEFAULT 0
);

CREATE TABLE IF NOT EXISTS tracking_points (
    id BIGSERIAL PRIMARY KEY,
    sampled_at TEXT NOT NULL,
    session_id TEXT NOT NULL,
    track_id INTEGER NOT NULL,
    x_norm DOUBLE PRECISION NOT NULL,
    y_norm DOUBLE PRECISION NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    UNIQUE(sampled_at, session_id, track_id)
);

CREATE INDEX IF NOT EXISTS idx_tracking_session ON tracking_points(session_id, sampled_at);

CREATE TABLE IF NOT EXISTS quality_events (
    id BIGSERIAL PRIMARY KEY,
    observed_at TEXT NOT NULL,
    event_type TEXT NOT NULL,
    brightness DOUBLE PRECISION NOT NULL
);

CREATE TABLE IF NOT EXISTS audio_samples (
    id BIGSERIAL PRIMARY KEY,
    sampled_at TEXT NOT NULL,
    level_dbfs DOUBLE PRECISION NOT NULL,
    zero_crossing_rate DOUBLE PRECISION NOT NULL,
    predicted_label TEXT NOT NULL,
    threshold_dbfs DOUBLE PRECISION NOT NULL,
    processed_features TEXT NOT NULL,
    actual_label TEXT,
    reviewed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_audio_review ON audio_samples(actual_label, id DESC);

CREATE TABLE IF NOT EXISTS zone_visits (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    track_id INTEGER NOT NULL,
    entered_at TEXT NOT NULL,
    exited_at TEXT,
    duration_sec DOUBLE PRECISION
);

CREATE TABLE IF NOT EXISTS admins (
    username TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS admin_sessions (
    token_hash TEXT PRIMARY KEY,
    username TEXT NOT NULL,
    csrf_token TEXT NOT NULL,
    expires_at DOUBLE PRECISION NOT NULL
);

CREATE TABLE IF NOT EXISTS login_attempts (
    address TEXT NOT NULL,
    attempted_at DOUBLE PRECISION NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_login_attempts ON login_attempts(address, attempted_at);
"""


def mask_dsn(dsn: str) -> str:
    parsed = urlparse(dsn)
    if not parsed.password:
        return dsn
    netloc = parsed.netloc.replace(f":{parsed.password}@", ":***@")
    return urlunparse(parsed._replace(netloc=netloc))


def resolve_postgres_dsn(cli_dsn: str | None = None) -> str:
    load_backend_env()
    raw = (
        cli_dsn
        or os.environ.get("SMARTOFFICE_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or DEFAULT_PG_DSN
    )
    dsn = normalize_postgres_dsn(raw)
    if not is_postgres_target(dsn):
        raise ValueError(
            f"Target '{dsn}' bukan URL PostgreSQL. Gunakan format postgresql://user:pass@host:5432/dbname"
        )
    return dsn


def ensure_database_exists(dsn: str) -> bool:
    """Create the PostgreSQL database if it does not exist yet. Returns True if created."""
    if psycopg2 is None:
        raise RuntimeError("Driver psycopg2 belum terpasang. Jalankan: pip install psycopg2-binary")
    parsed = urlparse(dsn)
    target_db = (parsed.path or "").lstrip("/")
    if not target_db:
        raise ValueError("Nama database tidak ditemukan pada URL PostgreSQL.")

    admin_dsn = urlunparse(parsed._replace(path="/postgres"))
    conn = psycopg2.connect(admin_dsn, connect_timeout=10)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target_db,))
        exists = cur.fetchone() is not None
        if not exists:
            safe_ident = target_db.replace('"', '""')
            cur.execute(f'CREATE DATABASE "{safe_ident}"')
            return True
        return False
    finally:
        conn.close()


def init_postgres_schema(dsn: str) -> None:
    """Create all Smart Office & Admin Auth tables in PostgreSQL."""
    db = connect_database(dsn)
    try:
        with db:
            db.executescript(POSTGRES_SCHEMA_SQL)
    finally:
        db.close()


def seed_minimal_data(dsn: str) -> None:
    """Insert minimal initial sample data into PostgreSQL so Frontend & DBeaver immediately show records."""
    now = datetime.now(timezone.utc)
    db = connect_database(dsn)
    try:
        with db:
            db.executescript(POSTGRES_SCHEMA_SQL)
            for idx in range(5):
                ts = (now - timedelta(minutes=(4 - idx))).isoformat(timespec="microseconds")
                db.execute(
                    "INSERT INTO sensor_readings (timestamp, co2_ppm, temperature_c, humidity_percent, source) "
                    "VALUES (?, ?, ?, ?, ?) ON CONFLICT (timestamp) DO NOTHING",
                    (ts, 680.0 + idx * 15.0, round(24.8 + idx * 0.2, 1), round(51.0 + idx * 0.5, 1), "scd40"),
                )
            local_ts = now.astimezone().isoformat(timespec="seconds")
            db.execute(
                "INSERT INTO occupancy_samples (sampled_at, session_id, person_count, mean_confidence, activity, camera_fps, inference_ms) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (local_ts, "seed-session-1", 2, 0.89, "Aktivitas di zona kerja", 24.5, 28.4),
            )
            db.execute(
                "INSERT INTO zone_visits (session_id, track_id, entered_at, exited_at, duration_sec) "
                "VALUES (?, ?, ?, ?, ?)",
                ("seed-session-1", 1, local_ts, local_ts, 45.0),
            )
            db.execute(
                "INSERT INTO audio_samples (sampled_at, level_dbfs, zero_crossing_rate, predicted_label, threshold_dbfs, processed_features) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (local_ts, -46.5, 0.042, "quiet", -42.0, "[0.12,0.18,0.15,0.11]"),
            )
    finally:
        db.close()


def check_postgres_connection(dsn: str) -> dict:
    """Test connection to PostgreSQL and return server metadata + table counts."""
    started = time.perf_counter()
    db = connect_database(dsn)
    try:
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        info = db.execute(
            "SELECT version() AS version, current_database() AS database, current_user AS user, "
            "inet_server_addr()::text AS server_addr, inet_server_port() AS server_port"
        ).fetchone()
        existing_rows = db.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = current_schema()"
        ).fetchall()
        existing_tables = {row["table_name"] for row in existing_rows}
        table_counts = {}
        for table in APP_TABLES:
            if table in existing_tables:
                cnt = db.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]
                table_counts[table] = int(cnt or 0)
            else:
                table_counts[table] = None
    finally:
        db.close()

    return {
        "dsn_masked": mask_dsn(dsn),
        "latency_ms": latency_ms,
        "version": info["version"],
        "database": info["database"],
        "user": info["user"],
        "server_addr": info["server_addr"],
        "server_port": info["server_port"],
        "tables": table_counts,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Uji koneksi PostgreSQL dan inisialisasi skema database Smart Office YOLOv11."
    )
    parser.add_argument(
        "--dsn",
        help="URL koneksi PostgreSQL (default: DATABASE_URL di .env atau postgresql://postgres:postgres@127.0.0.1:5432/smartoffice)",
    )
    parser.add_argument(
        "--create-db",
        action="store_true",
        help="Buat database PostgreSQL secara otomatis jika belum ada.",
    )
    parser.add_argument(
        "--init-schema",
        action="store_true",
        help="Buat seluruh tabel Smart Office dan autentikasi admin di PostgreSQL.",
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Isi data awal minimal (sensor_readings, occupancy_samples, zone_visits, audio_samples) untuk uji coba.",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Tampilkan status koneksi dan jumlah baris setiap tabel.",
    )
    args = parser.parse_args(argv)

    try:
        dsn = resolve_postgres_dsn(args.dsn)
        print(f"[PostgreSQL] Target DSN : {mask_dsn(dsn)}")
        if args.create_db:
            created = ensure_database_exists(dsn)
            print(
                "[PostgreSQL] Database baru berhasil dibuat."
                if created
                else "[PostgreSQL] Database sudah tersedia."
            )
        if args.init_schema:
            init_postgres_schema(dsn)
            print("[PostgreSQL] Skema tabel Smart Office & Admin berhasil diinisialisasi.")
        if args.seed:
            seed_minimal_data(dsn)
            print("[PostgreSQL] Data awal minimal berhasil ditambahkan.")

        status = check_postgres_connection(dsn)
        print(f"[PostgreSQL] Status     : TERHUBUNG ({status['latency_ms']} ms)")
        print(f"[PostgreSQL] Database   : {status['database']} (user: {status['user']})")
        print(f"[PostgreSQL] Versi      : {status['version'].splitlines()[0]}")
        if args.status or args.init_schema or args.seed:
            print("\nRingkasan Tabel:")
            for table, count in status["tables"].items():
                label = f"{count} baris" if count is not None else "belum dibuat (jalankan dengan --init-schema)"
                print(f"  - {table:<22}: {label}")
        return 0
    except Exception as exc:
        print(f"[PostgreSQL] Gagal terhubung: {exc}", file=sys.stderr)
        print(
            "\nTips:\n"
            "  1. Pastikan layanan PostgreSQL sedang berjalan.\n"
            "  2. Atur DATABASE_URL di backend/.env atau gunakan --dsn postgresql://user:pass@127.0.0.1:5432/smartoffice\n"
            "  3. Gunakan --create-db --init-schema untuk membuat database dan tabel secara otomatis.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
