"""Validated settings persisted independently of device state."""
from contextlib import closing
import json
import math
import sqlite3


def validate_detection(data):
    if not isinstance(data, dict):
        raise ValueError("Payload harus berupa objek JSON.")
    confidence = float(data["confidence"])
    zone = {key: float(data["zone"][key]) for key in ("x1", "y1", "x2", "y2")}
    if not math.isfinite(confidence) or not .1 <= confidence <= .9:
        raise ValueError("Confidence harus 10–90%.")
    if any(not math.isfinite(v) or not 0 <= v <= 1 for v in zone.values()):
        raise ValueError("Batas zona harus 0–100%.")
    if zone["x2"] - zone["x1"] < .1 or zone["y2"] - zone["y1"] < .1:
        raise ValueError("Lebar dan tinggi zona harus minimal 10%.")
    return {"confidence": confidence, "zone": zone}


def validate_audio(data):
    if not isinstance(data, dict):
        raise ValueError("Payload harus berupa objek JSON.")
    value = float(data["threshold_dbfs"])
    if not math.isfinite(value) or not -80 <= value <= -10:
        raise ValueError("Ambang harus antara -80 dan -10 dBFS.")
    return {"threshold_dbfs": value}


class SettingsStore:
    validators = {"detection": validate_detection, "audio": validate_audio}

    def __init__(self, path):
        self.path = path
        with closing(sqlite3.connect(path, timeout=10)) as db, db:
            db.execute("CREATE TABLE IF NOT EXISTS runtime_settings (name TEXT PRIMARY KEY, value TEXT NOT NULL)")

    def save(self, name, value):
        value = self.validators[name](value)
        with closing(sqlite3.connect(self.path, timeout=10)) as db, db:
            db.execute("INSERT INTO runtime_settings VALUES (?, ?) ON CONFLICT(name) DO UPDATE SET value=excluded.value",
                       (name, json.dumps(value, allow_nan=False)))
        return value

    def load(self, name, default):
        with closing(sqlite3.connect(self.path, timeout=10)) as db, db:
            row = db.execute("SELECT value FROM runtime_settings WHERE name=?", (name,)).fetchone()
        return self.validators[name](json.loads(row[0]) if row else default)

    def contains(self, name):
        with closing(sqlite3.connect(self.path, timeout=10)) as db, db:
            return db.execute("SELECT 1 FROM runtime_settings WHERE name=?", (name,)).fetchone() is not None
