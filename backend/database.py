"""Dual-engine database adapter supporting PostgreSQL (via DATABASE_URL) and SQLite fallback."""
from __future__ import annotations

import os
from pathlib import Path
import re
import sqlite3
from typing import Any, Iterable, Sequence

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

try:
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
except Exception:
    psycopg2 = None
    ISOLATION_LEVEL_AUTOCOMMIT = None

BACKEND_DIR = Path(__file__).resolve().parent
DEFAULT_SQLITE_PATH = BACKEND_DIR / "smartoffice.db"
DEFAULT_AUTH_SQLITE_PATH = BACKEND_DIR / "instance" / "admin_auth.db"

SERIAL_ID_TABLES = {
    "sensor_readings",
    "evaluation_samples",
    "occupancy_samples",
    "tracking_points",
    "quality_events",
    "audio_samples",
    "zone_visits",
}


def load_backend_env(env_file: Path | str | None = None) -> None:
    """Load environment variables from backend/.env if present."""
    candidates = [Path(env_file)] if env_file else [BACKEND_DIR / ".env", BACKEND_DIR.parent / ".env"]
    for path in candidates:
        if not path.is_file():
            continue
        if load_dotenv is not None:
            load_dotenv(path, override=False)
        else:
            for raw_line in path.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip("'").strip('"')
                if key and key not in os.environ:
                    os.environ[key] = value


load_backend_env()


def is_postgres_target(target: str | Path | None) -> bool:
    if not target:
        return False
    raw = str(target).strip().lower()
    return raw.startswith(("postgresql://", "postgres://", "postgresql+psycopg2://"))


def normalize_postgres_dsn(dsn: str) -> str:
    raw = dsn.strip()
    if raw.lower().startswith("postgresql+psycopg2://"):
        return "postgresql://" + raw.split("://", 1)[1]
    return raw


def resolve_database_target(explicit_target: str | Path | None = None, default_sqlite: Path = DEFAULT_SQLITE_PATH) -> str:
    """Resolve database connection target (PostgreSQL DSN or SQLite file path)."""
    if explicit_target is not None:
        target_str = str(explicit_target).strip()
        if is_postgres_target(target_str):
            return normalize_postgres_dsn(target_str)
        # If caller passed the default SQLite path but DATABASE_URL is configured in env, prefer DATABASE_URL.
        env_url = (os.environ.get("SMARTOFFICE_DATABASE_URL") or os.environ.get("DATABASE_URL") or "").strip()
        if env_url and is_postgres_target(env_url):
            try:
                if Path(target_str).resolve() == Path(default_sqlite).resolve():
                    return normalize_postgres_dsn(env_url)
            except OSError:
                pass
        return target_str

    env_url = (os.environ.get("SMARTOFFICE_DATABASE_URL") or os.environ.get("DATABASE_URL") or "").strip()
    if env_url:
        return normalize_postgres_dsn(env_url) if is_postgres_target(env_url) else env_url

    pg_host = os.environ.get("PGHOST", "").strip()
    pg_db = os.environ.get("PGDATABASE", "").strip()
    if pg_host and pg_db:
        pg_user = os.environ.get("PGUSER", "postgres").strip()
        pg_pass = os.environ.get("PGPASSWORD", "").strip()
        pg_port = os.environ.get("PGPORT", "5432").strip()
        auth = f"{pg_user}:{pg_pass}@" if pg_pass else f"{pg_user}@"
        return f"postgresql://{auth}{pg_host}:{pg_port}/{pg_db}"

    return str(default_sqlite)


def get_db_engine_name(explicit_target: str | Path | None = None) -> str:
    target = resolve_database_target(explicit_target)
    return "postgresql" if is_postgres_target(target) else "sqlite"


class HybridRow:
    """Row object compatible with both dict(row) / row['col'] and tuple(row) / row[0]."""

    __slots__ = ("_columns", "_values", "_map")

    def __init__(self, columns: Sequence[str], values: Sequence[Any]):
        self._columns = tuple(columns)
        self._values = tuple(values)
        self._map = dict(zip(self._columns, self._values))

    def __getitem__(self, key: int | slice | str) -> Any:
        if isinstance(key, (int, slice)):
            return self._values[key]
        return self._map[key]

    def __iter__(self):
        return iter(self._values)

    def __len__(self) -> int:
        return len(self._values)

    def keys(self) -> list[str]:
        return list(self._columns)

    def items(self) -> list[tuple[str, Any]]:
        return list(self._map.items())

    def values(self) -> list[Any]:
        return list(self._values)

    def get(self, key: str, default: Any = None) -> Any:
        return self._map.get(key, default)

    def __repr__(self) -> str:
        return f"HybridRow({self._map!r})"


_PRAGMA_TABLE_INFO_RE = re.compile(r"^\s*PRAGMA\s+table_info\(\s*([a-zA-Z0-9_]+)\s*\)\s*;?\s*$", re.IGNORECASE)
_INSERT_OR_IGNORE_TRACKING_RE = re.compile(
    r"^\s*INSERT\s+OR\s+IGNORE\s+INTO\s+tracking_points\b(.*)$",
    re.IGNORECASE | re.DOTALL,
)
_INSERT_TABLE_RE = re.compile(r"^\s*INSERT\s+INTO\s+([a-zA-Z0-9_]+)\b", re.IGNORECASE)


def translate_sql_for_postgres(sql: str, *, for_executemany: bool = False) -> tuple[str, bool]:
    """Translate SQLite-flavored SQL used by Smart Office into PostgreSQL syntax.

    Returns (translated_sql, appended_returning_id).
    """
    stripped = sql.strip()
    upper = stripped.upper()

    if upper.startswith("PRAGMA JOURNAL_MODE"):
        return "SELECT 1", False

    pragma_match = _PRAGMA_TABLE_INFO_RE.match(stripped)
    if pragma_match:
        table_name = pragma_match.group(1).lower()
        return (
            "SELECT ordinal_position AS cid, column_name AS name "
            "FROM information_schema.columns "
            f"WHERE table_schema = current_schema() AND table_name = '{table_name}' "
            "ORDER BY ordinal_position",
            False,
        )

    translated = stripped
    translated = re.sub(
        r"INTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT",
        "BIGSERIAL PRIMARY KEY",
        translated,
        flags=re.IGNORECASE,
    )
    if re.match(r"^\s*(CREATE|ALTER)\s+TABLE\b", translated, re.IGNORECASE):
        translated = re.sub(r"\bREAL\b", "DOUBLE PRECISION", translated, flags=re.IGNORECASE)

    tracking_match = _INSERT_OR_IGNORE_TRACKING_RE.match(translated)
    if tracking_match:
        rest = tracking_match.group(1).rstrip().rstrip(";")
        translated = f"INSERT INTO tracking_points{rest} ON CONFLICT (sampled_at, session_id, track_id) DO NOTHING"

    # Replace SQLite julianday(...) with PostgreSQL TIMESTAMPTZ cast for accurate timezone ordering/filtering.
    translated = re.sub(
        r"julianday\(\s*\?\s*\)",
        "CAST(? AS TIMESTAMPTZ)",
        translated,
        flags=re.IGNORECASE,
    )
    translated = re.sub(
        r"julianday\(\s*([a-zA-Z0-9_.]+)\s*\)",
        r"CAST(\1 AS TIMESTAMPTZ)",
        translated,
        flags=re.IGNORECASE,
    )

    # Convert '?' parameter placeholders outside single-quoted literals into '%s'.
    parts = translated.split("'")
    for idx in range(0, len(parts), 2):
        parts[idx] = parts[idx].replace("?", "%s")
    translated = "'".join(parts)

    appended_returning = False
    if not for_executemany:
        insert_match = _INSERT_TABLE_RE.match(translated)
        if insert_match:
            table_name = insert_match.group(1).lower()
            upper_translated = translated.upper()
            if (
                table_name in SERIAL_ID_TABLES
                and "RETURNING " not in upper_translated
                and "ON CONFLICT" not in upper_translated
            ):
                translated = translated.rstrip().rstrip(";") + " RETURNING id"
                appended_returning = True

    return translated, appended_returning


class CursorAdapter:
    """Unified cursor adapter for PostgreSQL and SQLite."""

    def __init__(self, raw_cursor: Any, is_postgres: bool, lastrowid: int | None = None):
        self._cursor = raw_cursor
        self._is_postgres = is_postgres
        self.lastrowid = lastrowid if is_postgres else getattr(raw_cursor, "lastrowid", None)

    def _wrap_row(self, row: Any) -> HybridRow | None:
        if row is None:
            return None
        if isinstance(row, HybridRow):
            return row
        if isinstance(row, sqlite3.Row):
            cols = row.keys()
            return HybridRow(cols, tuple(row))
        cols = [col[0] for col in (self._cursor.description or ())]
        return HybridRow(cols, row)

    def fetchone(self) -> HybridRow | None:
        return self._wrap_row(self._cursor.fetchone())

    def fetchall(self) -> list[HybridRow]:
        return [self._wrap_row(row) for row in self._cursor.fetchall()]

    def __iter__(self):
        for row in self._cursor:
            yield self._wrap_row(row)


class DatabaseConnection:
    """Unified connection wrapper supporting both SQLite and PostgreSQL."""

    def __init__(self, raw_conn: Any, is_postgres: bool, target: str):
        self._conn = raw_conn
        self.is_postgres = is_postgres
        self.target = target

    def execute(self, sql: str, params: Sequence[Any] = ()) -> CursorAdapter:
        if not self.is_postgres:
            cur = self._conn.execute(sql, tuple(params))
            return CursorAdapter(cur, is_postgres=False)

        pg_sql, has_returning = translate_sql_for_postgres(sql, for_executemany=False)
        cur = self._conn.cursor()
        cur.execute(pg_sql, tuple(params))
        lastrowid = None
        if has_returning:
            fetched = cur.fetchone()
            if fetched:
                lastrowid = fetched[0]
        return CursorAdapter(cur, is_postgres=True, lastrowid=lastrowid)

    def executemany(self, sql: str, seq_of_params: Iterable[Sequence[Any]]) -> CursorAdapter:
        if not self.is_postgres:
            cur = self._conn.executemany(sql, seq_of_params)
            return CursorAdapter(cur, is_postgres=False)

        pg_sql, _ = translate_sql_for_postgres(sql, for_executemany=True)
        cur = self._conn.cursor()
        cur.executemany(pg_sql, list(seq_of_params))
        return CursorAdapter(cur, is_postgres=True)

    def executescript(self, script: str) -> None:
        if not self.is_postgres:
            self._conn.executescript(script)
            return

        statements = [stmt.strip() for stmt in script.split(";") if stmt.strip()]
        cur = self._conn.cursor()
        for stmt in statements:
            pg_sql, _ = translate_sql_for_postgres(stmt, for_executemany=True)
            cur.execute(pg_sql)

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "DatabaseConnection":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_type is None:
            self._conn.commit()
        else:
            self._conn.rollback()
        return False


def connect_database(explicit_target: str | Path | None = None, default_sqlite: Path = DEFAULT_SQLITE_PATH) -> DatabaseConnection:
    """Open a database connection to PostgreSQL (if configured) or SQLite."""
    target = resolve_database_target(explicit_target, default_sqlite=default_sqlite)
    if is_postgres_target(target):
        if psycopg2 is None:
            raise RuntimeError(
                "Driver psycopg2 belum terpasang. Jalankan: pip install psycopg2-binary"
            )
        conn = psycopg2.connect(target, connect_timeout=10)
        return DatabaseConnection(conn, is_postgres=True, target=target)

    sqlite_path = Path(target)
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(sqlite_path), timeout=10)
    conn.row_factory = sqlite3.Row
    return DatabaseConnection(conn, is_postgres=False, target=str(sqlite_path))


class Database:
    """High-level database lifecycle and query wrapper for SQLite and PostgreSQL."""

    def __init__(self, path: str | Path | None = None):
        self.path = resolve_database_target(path)

    def connect(self) -> DatabaseConnection:
        return connect_database(self.path)

    def initialize(self) -> None:
        from sensor_dataset import init_sensor_schema

        db = self.connect()
        try:
            db.execute("PRAGMA journal_mode=WAL")
            init_sensor_schema(db)
            db.execute("""CREATE TABLE IF NOT EXISTS evaluation_samples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                captured_at TEXT NOT NULL,
                predicted_count INTEGER NOT NULL,
                confidence REAL NOT NULL,
                activity TEXT NOT NULL,
                objects_json TEXT NOT NULL,
                image_file TEXT NOT NULL,
                actual_count INTEGER,
                reviewed_at TEXT
            )""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_evaluation_pending ON evaluation_samples(actual_count, id DESC)")
            db.execute("""CREATE TABLE IF NOT EXISTS occupancy_samples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sampled_at TEXT NOT NULL,
                session_id TEXT NOT NULL,
                person_count INTEGER NOT NULL,
                mean_confidence REAL NOT NULL,
                activity TEXT NOT NULL,
                camera_fps REAL DEFAULT 0,
                inference_ms REAL DEFAULT 0
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS tracking_points (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sampled_at TEXT NOT NULL,
                session_id TEXT NOT NULL,
                track_id INTEGER NOT NULL,
                x_norm REAL NOT NULL,
                y_norm REAL NOT NULL,
                confidence REAL NOT NULL,
                UNIQUE(sampled_at, session_id, track_id)
            )""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_tracking_session ON tracking_points(session_id, sampled_at)")
            db.execute("""CREATE TABLE IF NOT EXISTS quality_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                observed_at TEXT NOT NULL,
                event_type TEXT NOT NULL,
                brightness REAL NOT NULL
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS audio_samples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sampled_at TEXT NOT NULL,
                level_dbfs REAL NOT NULL,
                zero_crossing_rate REAL NOT NULL,
                predicted_label TEXT NOT NULL,
                threshold_dbfs REAL NOT NULL,
                processed_features TEXT NOT NULL,
                actual_label TEXT,
                reviewed_at TEXT
            )""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_audio_review ON audio_samples(actual_label, id DESC)")
            db.execute("""CREATE TABLE IF NOT EXISTS zone_visits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                track_id INTEGER NOT NULL,
                entered_at TEXT NOT NULL,
                exited_at TEXT,
                duration_sec REAL
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS runtime_settings (
                name TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )""")
            occupancy_cols = {row[1] for row in db.execute("PRAGMA table_info(occupancy_samples)").fetchall()}
            if "camera_fps" not in occupancy_cols:
                db.execute("ALTER TABLE occupancy_samples ADD COLUMN camera_fps REAL DEFAULT 0")
            if "inference_ms" not in occupancy_cols:
                db.execute("ALTER TABLE occupancy_samples ADD COLUMN inference_ms REAL DEFAULT 0")
            db.commit()
        finally:
            db.close()

    def read(self, query: str, params: Sequence[Any] = ()) -> list[HybridRow]:
        db = self.connect()
        try:
            return db.execute(query, params).fetchall()
        finally:
            db.close()

    def write(self, query: str, params: Sequence[Any] = ()) -> int | None:
        db = self.connect()
        try:
            cursor = db.execute(query, params)
            db.commit()
            return cursor.lastrowid
        finally:
            db.close()
