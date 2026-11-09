"""SCD40 dataset storage and read-only exports, separate from camera inference."""
import csv
import io
from pathlib import Path
from flask import jsonify, request, Response, stream_with_context, send_file


def init_sensor_schema(db):
    db.execute("""CREATE TABLE IF NOT EXISTS sensor_readings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL UNIQUE,
        co2_ppm REAL NOT NULL CHECK(co2_ppm > 0 AND co2_ppm <= 40000),
        temperature_c REAL NOT NULL CHECK(temperature_c >= -40 AND temperature_c <= 125),
        humidity_percent REAL NOT NULL CHECK(humidity_percent >= 0 AND humidity_percent <= 100),
        source TEXT NOT NULL DEFAULT 'scd40' CHECK(source = 'scd40')
    )""")


def register_sensor_dataset(app, db_connect):
    @app.get('/api/sensors/dataset')
    def sensor_dataset_summary():
        try:
            limit = int(request.args.get('limit', 20))
            if not 1 <= limit <= 200:
                raise ValueError
        except ValueError:
            return jsonify(message='limit harus 1 sampai 200.'), 400
        db = db_connect()
        try:
            summary = dict(db.execute('''SELECT COUNT(*) AS total_rows,
                MIN(timestamp) AS first_at, MAX(timestamp) AS last_at
                FROM sensor_readings''').fetchone())
            rows = [dict(row) for row in db.execute(
                'SELECT * FROM sensor_readings ORDER BY id DESC LIMIT ?', (limit,))]
        finally:
            db.close()
        response = jsonify(**summary, source='scd40', rows=rows,
                       forecast_status='not_connected', horizon_minutes=5,
                       note='Jumlah baris bukan jaminan kesiapan training. Kontinuitas dan split waktu diperiksa di Colab.')
        response.headers['Cache-Control'] = 'no-store'
        return response

    @app.get('/api/sensors/export')
    def export_sensor_dataset():
        def generate():
            db = db_connect()
            buffer = io.StringIO()
            writer = csv.writer(buffer)
            columns = ['timestamp', 'co2_ppm', 'temperature_c', 'humidity_percent', 'source']
            try:
                writer.writerow(columns)
                yield buffer.getvalue()
                buffer.seek(0); buffer.truncate(0)
                # One ordered cursor gives a consistent SQLite read snapshot during download.
                for row in db.execute('SELECT '+','.join(columns)+' FROM sensor_readings ORDER BY timestamp'):
                    writer.writerow(tuple(row))
                    yield buffer.getvalue()
                    buffer.seek(0); buffer.truncate(0)
            finally:
                db.close()
        return Response(stream_with_context(generate()), mimetype='text/csv', headers={
            'Content-Disposition': 'attachment; filename=scd40_real.csv', 'Cache-Control': 'no-store'})

    @app.get('/api/sensors/assets/<kind>')
    def sensor_training_asset(kind):
        allowed = {
            'notebook': 'SmartOffice_Colab_Training_SCD40.ipynb',
            'dummy': 'sensor_training/scd40_dummy.csv',
        }
        if kind not in allowed:
            return jsonify(message='File tidak ditemukan.'), 404
        path = Path(app.root_path) / allowed[kind]
        if not path.is_file():
            return jsonify(message='File training belum tersedia di server.'), 404
        return send_file(path, as_attachment=True, download_name=path.name)
