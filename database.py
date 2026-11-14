"""SQLite schema and connection lifecycle for office datasets."""
import sqlite3
from sensor_dataset import init_sensor_schema


class Database:
    def __init__(self, path):
        self.path = path

    def connect(self):
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection


    def initialize(self):
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
            occupancy_cols = {row[1] for row in db.execute("PRAGMA table_info(occupancy_samples)").fetchall()}
            if "camera_fps" not in occupancy_cols:
                db.execute("ALTER TABLE occupancy_samples ADD COLUMN camera_fps REAL DEFAULT 0")
            if "inference_ms" not in occupancy_cols:
                db.execute("ALTER TABLE occupancy_samples ADD COLUMN inference_ms REAL DEFAULT 0")
            db.commit()
        finally:
            db.close()


    def read(self, query, params=()):
        db = self.connect()
        try:
            return db.execute(query, params).fetchall()
        finally:
            db.close()


    def write(self, query, params=()):
        db = self.connect()
        try:
            cursor = db.execute(query, params)
            db.commit()
            return cursor.lastrowid
        finally:
            db.close()
