"""Browser fixtures + REAL admin auth, all in a temporary database; no devices."""
import sys
from pathlib import Path
import tempfile
import logging
from datetime import datetime, timezone, timedelta
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from flask import Flask, jsonify, request, Response
from admin_auth import AdminStore, register_admin_auth

temp = tempfile.TemporaryDirectory()
store = AdminStore(Path(temp.name) / 'auth.db')
store.set_admin('admin', 'test-admin-password-2026')
app = Flask(__name__, static_folder=None)
logging.getLogger('werkzeug').setLevel(logging.ERROR)
app.config['ADMIN_WEB_ORIGINS'] = ['http://127.0.0.1:3100']
register_admin_auth(app, store)
mode, calls = {}, []


@app.get('/health')
def health():
    return jsonify(ok=True)


@app.post('/test/control')
def control():
    mode.clear()
    mode.update(request.get_json() or {})
    calls.clear()
    return jsonify(ok=True)


@app.get('/test/calls')
def call_log():
    return jsonify(calls)


@app.route('/api/<path:rest>', methods=['GET', 'POST'])
def fixture(rest):
    path = '/api/' + rest
    calls.append(dict(path=path, method=request.method, body=request.get_json(silent=True)))
    if mode.get('offline'):
        return jsonify(message='Server uji tidak tersedia.'), 503
    now = datetime.now(timezone.utc)
    if rest == 'status':
        return jsonify(person_count=3, person_confidence=87, visual_activity='Aktivitas di zona kerja',
            desk_objects=['laptop (92%)'], co2_ppm=720, temperature_c=25.4, humidity_percent=52.3,
            sensor_status='Data SCD40 diterima' if mode.get('live') else 'Mode demo (data dummy)',
            sensor_updated_at=('2020-01-01T00:00:00Z' if mode.get('stale') else now.isoformat()) if mode.get('live') else None,
            camera_status='Kamera terhubung' if mode.get('live') else 'Kamera belum tersedia', last_frame_at=now.isoformat() if mode.get('live') else None,
            snapshots=[], camera_fps=24, inference_ms=32, dark_frame=False, frame_brightness=90,
            final_validation='Objek dan orang terdeteksi pada area kerja', dark_frame_events=0,
            audio_available=True, audio_status='Mikrofon aktif', audio_label='quiet', audio_level_dbfs=-48,
            audio_threshold_dbfs=-42, audio_calibration_progress=0, detection_confidence_threshold=.35,
            zone_config=dict(x1=.12, y1=.15, x2=.88, y2=.92), model_name='yolo11n.pt',
            zone_duration_sec=120, zone_entries_today=4, zone_exits_today=1)
    if rest == 'sensors/dataset':
        return jsonify(total_rows=100 if mode.get('populated') else 0, first_at=now.isoformat() if mode.get('populated') else None,
            last_at=now.isoformat() if mode.get('populated') else None, source='scd40',
            rows=[dict(id=100-i, timestamp=(now-timedelta(minutes=i)).isoformat(), co2_ppm=720+i,
                       temperature_c=25.4, humidity_percent=52.3, source='scd40') for i in range(12)] if mode.get('populated') else [],
            forecast_status='not_connected', horizon_minutes=5, note='Jumlah baris bukan jaminan kesiapan training.')
    if rest == 'evaluation':
        return jsonify(reviewed_samples=0, exact_count_matches=0, count_accuracy_percent=None,
            pending_count=1 if mode.get('populated') else 0,
            samples=[dict(id=1, captured_at=now.isoformat(), predicted_count=2, confidence=86,
                          activity='Aktif', image_url='/training_data/test.svg', actual_count=None)] if mode.get('populated') else [],
            metric_note='Ketepatan hitung bukan mAP YOLO.')
    if rest == 'audio/evaluation':
        return jsonify(available=True, accuracy_percent=None, reviewed_samples=0, class_metrics={},
            samples=[dict(id=1, sampled_at=now.isoformat(), level_dbfs=-48, predicted_label='quiet', actual_label=None)] if mode.get('populated') else [])
    if rest == 'training/export' and not mode.get('populated'):
        return jsonify(message='Belum ada foto dataset. Ambil foto terlebih dahulu.'), 404
    if rest in ('sensors/export', 'training/export', 'export/colab') or rest.startswith('sensors/assets/'):
        return Response('timestamp,co2_ppm,temperature_c,humidity_percent,source\n', mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename="test.csv"'})
    if request.method == 'POST':
        return jsonify(status='ok', image_count=1)
    return jsonify(message='Not found'), 404


@app.get('/video_feed')
@app.get('/training_data/<path:filename>')
def picture(filename=None):
    if request.path == '/video_feed' and not mode.get('live'):
        return Response('Test camera unavailable', status=503)
    return Response('<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360"><rect width="640" height="360" fill="#284e38"/><text x="220" y="180" fill="white">TEST CAMERA FIXTURE</text></svg>', mimetype='image/svg+xml')


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5051, threaded=True, use_reloader=False)
