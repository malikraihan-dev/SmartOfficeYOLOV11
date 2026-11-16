"""Run with python -m unittest discover -s tests. No YOLO or real device startup."""
import ast
import csv
import io
from pathlib import Path
import sqlite3
import tempfile
import threading
import time
import unittest
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from sensor_dataset import init_sensor_schema, register_sensor_dataset

ROOT = Path(__file__).resolve().parents[1]


class SensorDatasetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        app = Flask(__name__, root_path=str(ROOT))
        app.config['TESTING'] = True
        self.ns = dict(app=app, sqlite3=sqlite3, DATABASE_PATH=str(Path(self.temp.name)/'test.db'),
                       request=request, jsonify=jsonify, datetime=datetime, timezone=timezone,
                       state_lock=threading.Lock(), system_state={}, init_sensor_schema=init_sensor_schema)
        tree = ast.parse((ROOT/'app.py').read_text(encoding='utf-8'))
        names = {'db_connect', 'db_write', 'init_database', 'receive_scd40'}
        nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
        exec(compile(ast.Module(body=nodes, type_ignores=[]), 'app_routes', 'exec'), self.ns)
        self.ns['init_database']()
        register_sensor_dataset(app, self.ns['db_connect'])
        self.client = app.test_client()

    def post_sample(self, **extra):
        return self.client.post('/api/scd40', json=dict(co2_ppm=720, temperature_c=25.4,
                                                       humidity_percent=52.3, **extra))

    def test_real_readings_and_csv_round_trip(self):
        self.assertEqual(self.post_sample().status_code, 200)
        self.assertEqual(self.post_sample().status_code, 200)
        data = self.client.get('/api/sensors/dataset').get_json()
        self.assertEqual(data['total_rows'], 2)
        self.assertEqual(data['rows'][0]['source'], 'scd40')
        self.assertEqual(data['forecast_status'], 'not_connected')
        response = self.client.get('/api/sensors/export')
        rows = list(csv.DictReader(io.StringIO(response.get_data(as_text=True))))
        self.assertEqual(len(rows), 2)
        self.assertEqual(float(rows[0]['co2_ppm']), 720)
        self.assertIsNotNone(datetime.fromisoformat(rows[0]['timestamp']).tzinfo)
        self.assertLess(rows[0]['timestamp'], rows[1]['timestamp'])

    def test_date_filter_summary_and_export_use_same_exclusive_end(self):
        db = self.ns['db_connect']()
        for at in ['2026-11-08T17:00:00+00:00', '2026-11-09T16:59:59+00:00', '2026-11-09T17:00:00+00:00']:
            db.execute('INSERT INTO sensor_readings(timestamp,co2_ppm,temperature_c,humidity_percent) VALUES(?,720,25,50)', (at,))
        db.commit()
        db.close()
        query = {'from': '2026-11-09T00:00:00+07:00', 'to': '2026-11-10T00:00:00+07:00'}
        summary = self.client.get('/api/sensors/dataset', query_string=query).get_json()
        exported = self.client.get('/api/sensors/export', query_string=query)
        rows = list(csv.DictReader(io.StringIO(exported.get_data(as_text=True))))
        self.assertEqual(summary['total_rows'], 2)
        self.assertEqual({row['timestamp'] for row in rows}, {row['timestamp'] for row in summary['rows']})
        for query in [{'period': 'invalid'}, {'from': '2026-11-09'}, {'from': 'bad'}, {'from': '2026-11-10T00:00:00Z', 'to': '2026-11-09T00:00:00Z'}]:
            for path in ['/api/sensors/dataset', '/api/sensors/export']:
                self.assertEqual(self.client.get(path, query_string=query).status_code, 400)

    def test_period_excludes_old_readings(self):
        self.post_sample()
        db = self.ns['db_connect']()
        db.execute("INSERT INTO sensor_readings(timestamp,co2_ppm,temperature_c,humidity_percent) VALUES('2020-01-01T00:00:00Z',720,25,50)")
        db.commit()
        db.close()
        self.assertEqual(self.client.get('/api/sensors/dataset?period=1h').get_json()['total_rows'], 1)

    def test_invalid_or_synthetic_input_is_not_logged(self):
        bad = [None, [], [1], 'invalid', 42, {'co2_ppm': 0, 'temperature_c': 25, 'humidity_percent': 50},
               {'co2_ppm': float('nan'), 'temperature_c': 25, 'humidity_percent': 50},
               {'co2_ppm': 500, 'temperature_c': 25, 'humidity_percent': 101}]
        for payload in bad:
            self.assertEqual(self.client.post('/api/scd40', json=payload).status_code, 400)
        self.assertEqual(self.post_sample(source='synthetic').status_code, 400)
        self.assertEqual(self.client.get('/api/sensors/dataset').get_json()['total_rows'], 0)

    def test_empty_limit_and_idempotent_schema(self):
        self.ns['init_database']()
        self.assertEqual(self.client.get('/api/sensors/dataset').get_json()['rows'], [])
        self.assertEqual(self.client.get('/api/sensors/dataset').headers['Cache-Control'], 'no-store')
        for limit in ['0', '201', 'abc']:
            self.assertEqual(self.client.get('/api/sensors/dataset?limit='+limit).status_code, 400)
        self.assertEqual(len(self.client.get('/api/sensors/export').get_data(as_text=True).splitlines()), 1)

    def test_status_demo_is_not_saved_and_stale_sensor_is_explicit(self):
        tree = ast.parse((ROOT/'app.py').read_text(encoding='utf-8'))
        nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in {'db_read', 'api_status'}]
        self.ns.update(time=time, system_state={
            'co2_ppm': None, 'sensor_updated_at': None, 'sensor_status': 'Mode demo (data dummy)'})
        exec(compile(ast.Module(body=nodes, type_ignores=[]), 'status_routes', 'exec'), self.ns)
        response = self.client.get('/api/status')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['Cache-Control'], 'no-store')
        self.assertEqual(response.get_json()['sensor_status'], 'Mode demo (data dummy)')
        self.assertEqual(self.client.get('/api/sensors/dataset').get_json()['total_rows'], 0)
        self.ns['system_state'].update(sensor_updated_at='2020-01-01T00:00:00+00:00',
                                       sensor_status='Data SCD40 diterima')
        self.assertEqual(self.client.get('/api/status').get_json()['sensor_status'], 'Data SCD40 kedaluwarsa')

    def test_training_download_allowlist(self):
        for asset in ['notebook', 'dummy']:
            response = self.client.get('/api/sensors/assets/'+asset)
            self.assertEqual(response.status_code, 200)
            self.assertIn('attachment', response.headers['Content-Disposition'])
            response.close()
        self.assertEqual(self.client.get('/api/sensors/assets/app.py').status_code, 404)


if __name__ == '__main__':
    unittest.main()
