import tempfile
import threading
import time
import unittest
import ast
from unittest.mock import patch
from flask import Flask, request, jsonify
from pathlib import Path

from camera_worker import CameraWorker
from database import Database
from settings_store import SettingsStore, validate_detection, validate_audio


class RuntimeServicesTests(unittest.TestCase):
    def test_actual_settings_routes_persist_and_keep_state_on_write_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            app = Flask(__name__)
            store = SettingsStore(str(Path(directory) / "settings.db"))
            namespace = dict(app=app, request=request, jsonify=jsonify, settings_store=store,
                             settings_lock=threading.Lock(), state_lock=threading.Lock(),
                             system_state={}, ZONE_CONFIG={}, validate_detection=validate_detection,
                             validate_audio=validate_audio)
            tree = ast.parse((Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8"))
            nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and
                     node.name in {"set_detection_settings", "set_audio_threshold"}]
            exec(compile(ast.Module(body=nodes, type_ignores=[]), "settings_routes", "exec"), namespace)
            client = app.test_client()
            detection = {"confidence": .55, "zone": {"x1": .1, "y1": .1, "x2": .9, "y2": .9}}
            self.assertEqual(client.post("/api/detection/settings", json=detection).status_code, 200)
            self.assertEqual(client.post("/api/audio/threshold", json={"threshold_dbfs": -36}).status_code, 200)
            self.assertEqual(SettingsStore(store.path).load("detection", {}), detection)
            self.assertEqual(SettingsStore(store.path).load("audio", {}), {"threshold_dbfs": -36})
            self.assertEqual(client.post("/api/detection/settings", json=[1]).status_code, 400)
            with patch.object(store, "save", side_effect=OSError("disk unavailable")):
                self.assertEqual(client.post("/api/audio/threshold", json={"threshold_dbfs": -40}).status_code, 503)
            self.assertEqual(namespace["AUDIO_THRESHOLD_DBFS"], -36)

    def test_subscribers_share_producer_and_disconnect_does_not_stop_capture(self):
        starts, closed = [], threading.Event()
        def source():
            starts.append(1)
            try:
                while True:
                    yield b"frame"
                    time.sleep(.01)
            finally:
                closed.set()
        worker = CameraWorker(source)
        try:
            clients = [worker.subscribe() for _ in range(5)]
            threads = [threading.Thread(target=lambda client=c: self.assertEqual(next(client), b"frame")) for c in clients]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(2)
                self.assertFalse(thread.is_alive())
            self.assertEqual(len(starts), 1)
            for client in clients:
                client.close()
            previous = worker.sequence
            deadline = time.monotonic() + 2
            while worker.sequence <= previous and time.monotonic() < deadline:
                time.sleep(.01)
            self.assertGreater(worker.sequence, previous)
        finally:
            worker.stop()
        self.assertTrue(closed.is_set())
        self.assertFalse(worker.thread.is_alive())

    def test_settings_survive_new_instance_and_invalid_values_do_not_replace_saved(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "test.db")
            store = SettingsStore(path)
            detection = {"confidence": .6, "zone": {"x1": .1, "y1": .2, "x2": .9, "y2": .8}}
            store.save("detection", detection)
            store.save("audio", {"threshold_dbfs": -38})
            restarted = SettingsStore(path)
            self.assertEqual(restarted.load("detection", {}), detection)
            self.assertEqual(restarted.load("audio", {}), {"threshold_dbfs": -38})
            for value in (float("nan"), float("inf"), -81, 0):
                with self.assertRaises(ValueError):
                    store.save("audio", {"threshold_dbfs": value})
            for value in ([], None, {"confidence": .5, "zone": {"x1": float("nan"), "y1": 0, "x2": 1, "y2": 1}}):
                with self.assertRaises((ValueError, KeyError, TypeError)):
                    store.save("detection", value)
            self.assertEqual(restarted.load("detection", {}), detection)
            self.assertEqual(restarted.load("audio", {}), {"threshold_dbfs": -38})

    def test_extracted_database_initialization_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Database(str(Path(directory) / "test.db"))
            db.initialize()
            db.initialize()
            db.write("INSERT INTO sensor_readings (timestamp,co2_ppm,temperature_c,humidity_percent,source) VALUES (?,?,?,?,?)",
                     ("2026-11-13T00:00:00Z", 700, 25, 50, "scd40"))
            self.assertEqual(db.read("SELECT COUNT(*) n FROM sensor_readings")[0]["n"], 1)
