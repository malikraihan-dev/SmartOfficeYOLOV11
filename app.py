import os
import time
import threading
import sqlite3
import json
import glob
import csv
import io
import uuid
import zipfile
from collections import deque, Counter
from datetime import datetime, timezone
from sensor_dataset import init_sensor_schema, register_sensor_dataset
from admin_auth import register_admin_auth

import cv2
import numpy as np
from flask import Flask, Response, jsonify, redirect, request, send_file, send_from_directory, stream_with_context
from ultralytics import YOLO

try:
    import sounddevice as sd
    AUDIO_AVAILABLE = True
except Exception:
    sd = None
    AUDIO_AVAILABLE = False

app = Flask(__name__)
register_admin_auth(app)
cv2.setNumThreads(1)
CUSTOM_MODEL_PATH = os.path.join(app.root_path, "best_smartoffice.pt")
BASE_MODEL_PATH = os.path.join(app.root_path, "yolo11n.pt")
MODEL_PATH = os.path.abspath(os.environ.get(
    "SMARTOFFICE_MODEL",
    BASE_MODEL_PATH if os.path.isfile(BASE_MODEL_PATH) else CUSTOM_MODEL_PATH,
))
model = YOLO(MODEL_PATH)
FACE_MODEL_PATH = os.path.join(app.root_path, "face_detection_yunet_2023mar.onnx")
FACE_DETECTOR = None
if os.path.isfile(FACE_MODEL_PATH) and hasattr(cv2, "FaceDetectorYN_create"):
    try:
        FACE_DETECTOR = cv2.FaceDetectorYN_create(FACE_MODEL_PATH, "", (320, 320), 0.45, 0.3, 5000)
    except cv2.error:
        FACE_DETECTOR = None
SNAPSHOT_DIR = os.path.join(app.root_path, "snapshots")
DATASET_DIR = os.path.join(app.root_path, "training_data")
RAW_DATASET_DIR = os.path.join(app.root_path, "dataset_images")
DATABASE_PATH = os.path.join(app.root_path, "smartoffice.db")
BRIGHTNESS_THRESHOLD = 10.0
DETECTION_CONFIDENCE = 0.35
ZONE_CONFIG = {"x1": 0.12, "y1": 0.15, "x2": 0.88, "y2": 0.92}
AUDIO_SAMPLE_RATE = 8000
AUDIO_THRESHOLD_DBFS = -42.0
AUDIO_CALIBRATION_SEGMENTS = 2
audio_calibrate_event = threading.Event()
os.makedirs(SNAPSHOT_DIR, exist_ok=True)
os.makedirs(DATASET_DIR, exist_ok=True)
os.makedirs(RAW_DATASET_DIR, exist_ok=True)

ALLOWED_DESK_CLASSES = {
    "laptop": "laptop", "mouse": "mouse", "keyboard": "keyboard",
    "key": "kunci", "keys": "kunci", "tumbler": "tumbler",
    "cup": "tumbler", "bottle": "tumbler",
    "cell phone": "handphone", "cell-phone": "handphone", "cellphone": "handphone",
    "mobile phone": "handphone", "mobile-phone": "handphone",
    "phone": "handphone", "smart phone": "handphone", "smartphone": "handphone", "handphone": "handphone",
}
PERSON_CLASS_ALIASES = {"person", "people"}
state_lock = threading.Lock()
latest_frame = None
latest_clean_frame = None
last_detection = False
camera_retry_requested = False
system_state = {
    "person_detected": False, "person_count": 0, "person_confidence": 0.0,
    "visual_activity": "Menunggu kamera", "desk_objects": [],
    "co2_ppm": None, "temperature_c": None, "humidity_percent": None,
    "sensor_status": "Mode demo (data dummy)", "sensor_updated_at": None,
    "final_validation": "Menunggu kamera...", "snapshots": [],
    "camera_status": "Mencari kamera", "camera_index": None,
    "last_frame_at": None,
    "tracking_method": "Centroid Tracker",
    "frame_brightness": None, "dark_frame": False, "dark_frame_events": 0,
    "audio_available": AUDIO_AVAILABLE, "audio_status": "Menunggu mikrofon" if AUDIO_AVAILABLE else "Mikrofon belum tersedia",
    "audio_label": "Belum ada data audio", "audio_level_dbfs": None,
    "audio_threshold_dbfs": AUDIO_THRESHOLD_DBFS, "audio_sample_id": None,
    "audio_accuracy_percent": None, "audio_reviewed_samples": 0,
    "audio_baseline_dbfs": None, "audio_calibration_progress": 0,
    "camera_fps": 0.0, "inference_ms": 0.0,
    "detection_confidence_threshold": DETECTION_CONFIDENCE,
    "zone_config": ZONE_CONFIG.copy(), "model_name": os.path.basename(MODEL_PATH),
    "zone_duration_sec": 0.0, "zone_entries_today": 0, "zone_exits_today": 0,
}


def db_connect():
    connection = sqlite3.connect(DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def init_database():
    db = db_connect()
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


def db_read(query, params=()):
    db = db_connect()
    try:
        return db.execute(query, params).fetchall()
    finally:
        db.close()


def db_write(query, params=()):
    db = db_connect()
    try:
        cursor = db.execute(query, params)
        db.commit()
        return cursor.lastrowid
    finally:
        db.close()


init_database()
register_sensor_dataset(app, db_connect)


def save_evaluation_sample(frame, people, confidence, activity, objects):
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"sample_{stamp}.jpg"
    if not cv2.imwrite(os.path.join(DATASET_DIR, filename), frame):
        return
    db_write(
        "INSERT INTO evaluation_samples (captured_at,predicted_count,confidence,activity,objects_json,image_file) VALUES (?,?,?,?,?,?)",
        (datetime.now().astimezone().isoformat(timespec="seconds"), people, confidence,
         activity, json.dumps(objects, ensure_ascii=False), filename),
    )
    clean_old_images(DATASET_DIR, "sample_*.jpg", keep=200)


def save_spatiotemporal_data(session_id, sampled_at, people_count, confidence, activity, tracks, camera_fps=0.0, inference_ms=0.0):
    db = db_connect()
    try:
        db.execute(
            "INSERT INTO occupancy_samples (sampled_at,session_id,person_count,mean_confidence,activity,camera_fps,inference_ms) VALUES (?,?,?,?,?,?,?)",
            (sampled_at, session_id, people_count, confidence, activity, camera_fps, inference_ms),
        )
        if tracks:
            db.executemany(
                "INSERT OR IGNORE INTO tracking_points (sampled_at,session_id,track_id,x_norm,y_norm,confidence) VALUES (?,?,?,?,?,?)",
                [(sampled_at, session_id, tid, x, y, conf) for tid, x, y, conf in tracks],
            )
        db.commit()
    finally:
        db.close()


def open_zone_visit(session_id, track_id, entered_at):
    return db_write("INSERT INTO zone_visits (session_id,track_id,entered_at) VALUES (?,?,?)",
                    (session_id, track_id, entered_at))


def close_zone_visit(visit_id, entered_epoch, exited_at):
    duration = max(0.0, time.time() - entered_epoch)
    db_write("UPDATE zone_visits SET exited_at=?,duration_sec=? WHERE id=?",
             (exited_at, round(duration, 1), visit_id))
    return duration


def save_quality_event(event_type, brightness):
    db_write("INSERT INTO quality_events (observed_at,event_type,brightness) VALUES (?,?,?)",
             (datetime.now().astimezone().isoformat(timespec="seconds"), event_type, round(float(brightness), 2)))
    total = db_read("SELECT COUNT(*) AS n FROM quality_events WHERE event_type='dark_frame'")[0]["n"]
    with state_lock:
        system_state["dark_frame_events"] = int(total or 0)


def update_audio_accuracy():
    row = db_read("SELECT COUNT(*) AS n, SUM(CASE WHEN predicted_label=actual_label THEN 1 ELSE 0 END) AS correct FROM audio_samples WHERE actual_label IS NOT NULL")[0]
    reviewed = int(row["n"] or 0)
    correct = int(row["correct"] or 0)
    with state_lock:
        system_state["audio_reviewed_samples"] = reviewed
        system_state["audio_accuracy_percent"] = round(100 * correct / reviewed, 1) if reviewed else None


def save_audio_sample(level_dbfs, zcr, predicted_label, threshold_dbfs, processed_features):
    sampled_at = datetime.now().astimezone().isoformat(timespec="seconds")
    sample_id = db_write(
        "INSERT INTO audio_samples (sampled_at,level_dbfs,zero_crossing_rate,predicted_label,threshold_dbfs,processed_features) VALUES (?,?,?,?,?,?)",
        (sampled_at, level_dbfs, zcr, predicted_label, threshold_dbfs,
         json.dumps(processed_features, separators=(",", ":"))),
    )
    with state_lock:
        system_state.update({
            "audio_status": "Mikrofon aktif", "audio_label": predicted_label,
            "audio_level_dbfs": round(level_dbfs, 1), "audio_sample_id": sample_id,
        })
    update_audio_accuracy()
    return sample_id


def audio_listener_thread():
    global AUDIO_THRESHOLD_DBFS
    if not AUDIO_AVAILABLE:
        return
    try:
        with sd.InputStream(channels=1, samplerate=AUDIO_SAMPLE_RATE, blocksize=AUDIO_SAMPLE_RATE, dtype="float32") as stream:
            with state_lock:
                system_state["audio_status"] = "Mikrofon aktif"
            calibration_levels = []
            current_label = "quiet"
            candidate_label = None
            candidate_repeats = 0
            while True:
                if audio_calibrate_event.is_set():
                    audio_calibrate_event.clear()
                    calibration_levels.clear()
                    current_label, candidate_label, candidate_repeats = "quiet", None, 0
                    with state_lock:
                        system_state["audio_calibration_progress"] = 0
                        system_state["audio_baseline_dbfs"] = None
                        system_state["audio_status"] = "Kalibrasi audio (20 detik)"
                chunks = []
                for _ in range(10):
                    block, _overflow = stream.read(AUDIO_SAMPLE_RATE)
                    chunks.append(np.asarray(block[:, 0], dtype=np.float32))
                raw = np.concatenate(chunks)
                centered = raw - float(np.mean(raw))
                rms = float(np.sqrt(np.mean(np.square(centered))))
                level_dbfs = 20 * np.log10(rms + 1e-9)
                zcr = float(np.mean(np.abs(np.diff(np.signbit(centered)))))
                # Keep only a privacy-reduced 10-second envelope; discard the original PCM samples.
                rectified = np.abs(centered)
                usable = (len(rectified) // 100) * 100
                features = rectified[:usable].reshape(-1, 100).mean(axis=1)
                peak = float(features.max()) if features.size else 0.0
                if peak > 0:
                    features = features / peak
                if len(calibration_levels) < AUDIO_CALIBRATION_SEGMENTS:
                    calibration_levels.append(float(level_dbfs))
                    with state_lock:
                        system_state["audio_calibration_progress"] = len(calibration_levels)
                        system_state["audio_status"] = f"Kalibrasi audio ({len(calibration_levels)}/{AUDIO_CALIBRATION_SEGMENTS})"
                    if len(calibration_levels) == AUDIO_CALIBRATION_SEGMENTS:
                        baseline = float(np.median(calibration_levels))
                        AUDIO_THRESHOLD_DBFS = float(np.clip(baseline + 8.0, -55.0, -25.0))
                        with state_lock:
                            system_state.update({
                                "audio_baseline_dbfs": round(baseline, 1),
                                "audio_threshold_dbfs": round(AUDIO_THRESHOLD_DBFS, 1),
                                "audio_status": "Kalibrasi selesai",
                            })
                    continue
                threshold = AUDIO_THRESHOLD_DBFS
                raw_label = "noise" if level_dbfs >= threshold else "quiet"
                # Two consecutive threshold crossings are required before changing state.
                if raw_label != current_label:
                    if raw_label == candidate_label:
                        candidate_repeats += 1
                    else:
                        candidate_label, candidate_repeats = raw_label, 1
                    if candidate_repeats >= 2:
                        current_label, candidate_label, candidate_repeats = raw_label, None, 0
                else:
                    candidate_label, candidate_repeats = None, 0
                label = current_label
                save_audio_sample(round(float(level_dbfs), 2), round(zcr, 5), label,
                                  threshold, np.round(features, 4).tolist())
    except Exception as error:
        with state_lock:
            system_state["audio_status"] = f"Mikrofon tidak aktif: {str(error)[:80]}"


def assign_track_ids(centers, active_tracks, next_track_id, max_distance=65, max_missed=8):
    """Associate centers between frames using a small greedy nearest-center tracker."""
    candidates = []
    for index, (x, y) in enumerate(centers):
        for track_id, track in active_tracks.items():
            px, py = track["center"]
            distance = float(np.hypot(x - px, y - py))
            if distance <= max_distance:
                candidates.append((distance, track_id, index))
    candidates.sort()
    matched_tracks, matched_detections = set(), set()
    detection_ids = [None] * len(centers)
    for _, track_id, index in candidates:
        if track_id in matched_tracks or index in matched_detections:
            continue
        active_tracks[track_id] = {"center": centers[index], "missed": 0}
        detection_ids[index] = track_id
        matched_tracks.add(track_id)
        matched_detections.add(index)
    for track_id in list(active_tracks):
        if track_id not in matched_tracks:
            active_tracks[track_id]["missed"] += 1
            if active_tracks[track_id]["missed"] > max_missed:
                del active_tracks[track_id]
    for index, center in enumerate(centers):
        if detection_ids[index] is None:
            detection_ids[index] = next_track_id
            active_tracks[next_track_id] = {"center": center, "missed": 0}
            next_track_id += 1
    return detection_ids, next_track_id


def clean_old_images(directory, pattern, keep=200):
    files = sorted(glob.glob(os.path.join(directory, pattern)), key=os.path.getmtime, reverse=True)
    for old_file in files[keep:]:
        try:
            os.remove(old_file)
        except OSError:
            pass


def save_snapshot(frame, people, confidence, trigger="manual"):
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"snapshot_{stamp}.jpg"
    cv2.imwrite(os.path.join(SNAPSHOT_DIR, filename), frame)
    item = {
        "filename": filename, "url": f"/snapshots/{filename}",
        "captured_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "person_count": people, "confidence_percent": round(confidence * 100, 1),
        "trigger": trigger,
    }
    with state_lock:
        system_state["snapshots"] = ([item] + system_state["snapshots"])[:20]
    clean_old_images(SNAPSHOT_DIR, "snapshot_*.jpg", keep=200)
    return item


def demo_frame():
    frame = np.full((480, 640, 3), (38, 48, 65), dtype=np.uint8)
    cv2.putText(frame, "MODE DEMO - MENCARI KAMERA LAPTOP...", (55, 55), cv2.FONT_HERSHEY_SIMPLEX, .62, (255, 255, 255), 2)
    cv2.putText(frame, "Pastikan aplikasi lain tidak memakai kamera", (105, 440), cv2.FONT_HERSHEY_SIMPLEX, .5, (210, 220, 230), 1)
    return frame


def detect_face_boxes(frame):
    """Run lightweight YuNet once per frame and return face boxes in source-frame coordinates."""
    if FACE_DETECTOR is None:
        return []
    height, width = frame.shape[:2]
    scale = min(320.0 / width, 320.0 / height)
    resized_w, resized_h = max(1, int(round(width * scale))), max(1, int(round(height * scale)))
    resized = cv2.resize(frame, (resized_w, resized_h), interpolation=cv2.INTER_AREA)
    pad_x, pad_y = (320 - resized_w) // 2, (320 - resized_h) // 2
    canvas = np.zeros((320, 320, 3), dtype=np.uint8)
    canvas[pad_y:pad_y + resized_h, pad_x:pad_x + resized_w] = resized
    try:
        FACE_DETECTOR.setInputSize((320, 320))
        _, detections = FACE_DETECTOR.detect(canvas)
    except cv2.error:
        return []
    if detections is None:
        return []
    boxes = []
    for detection in detections:
        fx = (float(detection[0]) - pad_x) / scale
        fy = (float(detection[1]) - pad_y) / scale
        fw = float(detection[2]) / scale
        fh = float(detection[3]) / scale
        score = float(detection[-1])
        x1, y1 = max(0, int(fx)), max(0, int(fy))
        x2, y2 = min(width, int(fx + fw)), min(height, int(fy + fh))
        if x2 > x1 and y2 > y1:
            boxes.append((x1, y1, x2, y2, score))
    return boxes


def blur_face_oval(frame, box, source=None, detected_faces=None):
    """Blur an oval centered on a YuNet face detection, with a small-box fallback."""
    x1, y1, x2, y2 = box
    source = source if source is not None else frame
    crop = source[y1:y2, x1:x2]
    height, width = crop.shape[:2]
    if width < 16 or height < 24:
        return None
    candidates = [face for face in (detected_faces or [])
                  if face[0] < x2 and face[2] > x1 and face[1] < y2 and face[3] > y1]
    face = max(candidates, key=lambda item: item[4]) if candidates else None
    if face is None:
        # Do not put an oval on an estimated body location when face detection is available.
        if FACE_DETECTOR is not None:
            return None
        # Fallback for OpenCV builds without YuNet: approximate the head area in the person box.
        center_x, center_y = width // 2, int(height * .29)
        radius_x, radius_y = max(8, int(width * .23)), max(10, int(height * .13))
    else:
        fx, fy, fx2, fy2, _ = face
        fx, fy, fw, fh = int(fx - x1), int(fy - y1), int(fx2 - fx), int(fy2 - fy)
        center_x, center_y = fx + fw // 2, fy + fh // 2
        radius_x, radius_y = max(8, int(fw * .62)), max(10, int(fh * .72))
    center_x = min(max(center_x, radius_x), max(radius_x, width - radius_x - 1))
    center_y = min(max(center_y, radius_y), max(radius_y, height - radius_y - 1))
    mask = np.zeros((height, width), dtype=np.uint8)
    cv2.ellipse(mask, (center_x, center_y), (radius_x, radius_y), 0, 0, 360, 255, -1, cv2.LINE_AA)
    sigma = max(2.0, min(radius_x, radius_y) * .18)
    alpha = cv2.GaussianBlur(mask, (0, 0), sigmaX=sigma).astype(np.float32) / 255.0
    blur_size = max(15, int(min(radius_x, radius_y) * 1.3) | 1)
    blurred = cv2.GaussianBlur(crop, (blur_size, blur_size), max(5.0, sigma * 1.8))
    alpha = alpha[:, :, None]
    frame[y1:y2, x1:x2] = (crop.astype(np.float32) * (1 - alpha) + blurred.astype(np.float32) * alpha).astype(np.uint8)
    return mask


def generate_video_frames():
    global latest_frame, latest_clean_frame, last_detection, camera_retry_requested
    cap = None
    camera_index = None
    retry_at = 0.0
    was_demo = False
    previous_centers = []
    active_tracks = {}
    next_track_id = 1
    zone_visits = {}
    last_motion = 0.0
    count_history = deque(maxlen=3)
    activity_history = deque(maxlen=5)
    last_sample_at = 0.0
    last_auto_snapshot_at = 0.0
    last_spatiotemporal_at = 0.0
    last_dark_event_at = 0.0
    was_dark = False
    session_id = uuid.uuid4().hex[:12]
    last_perf_at = time.perf_counter()

    def finish_zone_visit(track_id):
        visit = zone_visits.pop(track_id, None)
        if visit:
            visit_id, entered_epoch = visit
            close_zone_visit(visit_id, entered_epoch, datetime.now().astimezone().isoformat(timespec="seconds"))

    while True:
        now = time.time()
        with state_lock:
            force_retry = camera_retry_requested
            camera_retry_requested = False
        if force_retry:
            retry_at = 0.0
            for tracked_id in list(zone_visits):
                finish_zone_visit(tracked_id)
            active_tracks.clear()
            session_id = uuid.uuid4().hex[:12]
            if cap is not None:
                cap.release()
            cap = None
        ok, frame = (False, None)
        if cap is not None and cap.isOpened():
            ok, frame = cap.read()

        # Try common Windows webcam indices and backends; retry every 3 seconds if unavailable.
        if not ok and now >= retry_at:
            if cap is not None:
                cap.release()
            cap = None
            for index in range(4):
                for backend in (cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY):
                    candidate = cv2.VideoCapture(index, backend)
                    if candidate.isOpened():
                        candidate.set(cv2.CAP_PROP_FRAME_WIDTH, 480)
                        candidate.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)
                        candidate.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                        read_ok, first_frame = candidate.read()
                        if read_ok:
                            cap, camera_index, ok, frame = candidate, index, True, first_frame
                            break
                    candidate.release()
                if ok:
                    break
            retry_at = now + 3

        if not ok:
            was_demo = True
            for tracked_id in list(zone_visits):
                finish_zone_visit(tracked_id)
            frame = demo_frame()
            with state_lock:
                latest_frame = frame.copy()
                system_state.update({
                    "person_detected": False, "person_count": 0, "person_confidence": 0.0,
                    "visual_activity": "Kamera belum tersedia", "desk_objects": [],
                    "final_validation": "Mode demo: menunggu kamera laptop",
                    "camera_status": "Mencari kamera laptop", "camera_index": None,
                    "last_frame_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                    "zone_duration_sec": 0.0,
                })
            ok, buffer = cv2.imencode(".jpg", frame)
            if ok:
                try:
                    yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
                except GeneratorExit:
                    if cap is not None:
                        cap.release()
                    raise
            time.sleep(.2)
            continue

        if was_demo:
            last_detection = False
            was_demo = False
            session_id = uuid.uuid4().hex[:12]
            active_tracks.clear()
            previous_centers = []
            last_perf_at = time.perf_counter()
        with state_lock:
            system_state.update({"camera_status": "Kamera terhubung", "camera_index": camera_index})
        if frame.shape[1] > 480:
            ratio = 480.0 / frame.shape[1]
            frame = cv2.resize(frame, (480, int(frame.shape[0] * ratio)), interpolation=cv2.INTER_AREA)
        h, w = frame.shape[:2]
        with state_lock:
            latest_clean_frame = frame.copy()
        small_gray = cv2.cvtColor(cv2.resize(frame, (32, 32), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
        brightness = float(np.mean(small_gray))
        if brightness < BRIGHTNESS_THRESHOLD:
            if not was_dark or now - last_dark_event_at >= 30:
                save_quality_event("dark_frame", brightness)
                last_dark_event_at = now
            was_dark = True
            for tracked_id in list(zone_visits):
                finish_zone_visit(tracked_id)
            active_tracks.clear()
            count_history.clear()
            activity_history.clear()
            dark_elapsed = max(1e-6, time.perf_counter() - last_perf_at)
            camera_fps = 1.0 / dark_elapsed
            last_perf_at = time.perf_counter()
            cv2.putText(frame, f"FRAME GELAP - DETEKSI DILEWATI ({brightness:.1f}/255)", (12, 28), cv2.FONT_HERSHEY_SIMPLEX, .58, (100, 220, 255), 2)
            with state_lock:
                system_state.update({
                    "person_detected": False, "person_count": 0, "person_confidence": 0.0,
                    "visual_activity": "Frame gelap; deteksi dilewati", "desk_objects": [],
                    "final_validation": "Frame terlalu gelap untuk deteksi yang andal",
                    "dark_frame": True, "frame_brightness": round(brightness, 2),
                    "camera_status": "Kamera terhubung · frame gelap", "camera_index": camera_index,
                    "last_frame_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                    "camera_fps": round(camera_fps, 1), "inference_ms": 0.0,
                    "zone_duration_sec": 0.0,
                })
                latest_frame = frame.copy()
            ok, buffer = cv2.imencode(".jpg", frame)
            if ok:
                try:
                    yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
                except GeneratorExit:
                    if cap is not None:
                        cap.release()
                    raise
            time.sleep(.1)
            continue
        if was_dark:
            save_quality_event("dark_frame_ended", brightness)
            was_dark = False
        with state_lock:
            zone = ZONE_CONFIG.copy()
        roi = (int(w * zone["x1"]), int(h * zone["y1"]), int(w * zone["x2"]), int(h * zone["y2"]))
        people, confidences, centers, desk_items, object_boxes = [], [], [], [], []
        inference_start = time.perf_counter()
        result = model.predict(source=frame, imgsz=320, conf=DETECTION_CONFIDENCE, max_det=12, verbose=False)[0]
        inference_ms = (time.perf_counter() - inference_start) * 1000
        for box in result.boxes:
            cls_id, conf = int(box.cls[0]), float(box.conf[0])
            label = str(model.names[cls_id]).lower()
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            x1, y1, x2, y2 = max(0, x1), max(0, y1), min(w, x2), min(h, y2)
            if label in PERSON_CLASS_ALIASES:
                people.append((x1, y1, x2, y2))
                confidences.append(conf)
                center = ((x1 + x2) // 2, (y1 + y2) // 2)
                centers.append(center)
            elif label in ALLOWED_DESK_CLASSES:
                mapped = ALLOWED_DESK_CLASSES[label]
                desk_items.append(f"{mapped} ({conf * 100:.0f}%)")
                object_boxes.append((x1, y1, x2, y2, mapped, conf))

        track_ids, next_track_id = assign_track_ids(centers, active_tracks, next_track_id)
        tracked_points = [
            (track_id, center[0] / w, center[1] / h, confidences[index])
            for index, (track_id, center) in enumerate(zip(track_ids, centers))
        ]

        # Blur only the segmented silhouette; render labels after blur for readability.
        original = frame.copy()
        detected_faces = detect_face_boxes(original)
        person_masks = [blur_face_oval(frame, box, original, detected_faces) for box in people]
        for x1, y1, x2, y2, name, conf in object_boxes:
            color = (60, 210, 115)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            text = f"{name} {conf * 100:.0f}%"
            (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, .46, 1)
            top = max(0, y1 - th - 9)
            cv2.rectangle(frame, (x1, top), (min(w - 1, x1 + tw + 8), y1), color, -1)
            cv2.putText(frame, text, (x1 + 4, max(th, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, .46, (18, 35, 31), 1, cv2.LINE_AA)
        for index, ((x1, y1, x2, y2), conf, mask) in enumerate(zip(people, confidences, person_masks)):
            if mask is not None and mask.size:
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if contours:
                    cv2.drawContours(frame[y1:y2, x1:x2], contours, -1, (255, 190, 75), 1, cv2.LINE_AA)
            track_id = track_ids[index] if index < len(track_ids) else index + 1
            cv2.putText(frame, f"Orang #{track_id} {conf * 100:.0f}%", (x1, max(16, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, .45, (255, 210, 115), 1, cv2.LINE_AA)

        raw_count = len(people)
        count_history.append(raw_count)
        count = int(np.median(count_history))
        confidence = float(np.mean(confidences)) if confidences else 0.0
        moving = False
        if centers and previous_centers:
            moving = any(min(np.hypot(x - px, y - py) for px, py in previous_centers) >= 4 for x, y in centers)
        if moving or (centers and not previous_centers):
            last_motion = now
        previous_centers = centers
        inside = any(roi[0] <= x <= roi[2] and roi[1] <= y <= roi[3] for x, y in centers)
        current_ids = set()
        for track_id, (cx, cy) in zip(track_ids, centers):
            if roi[0] <= cx <= roi[2] and roi[1] <= cy <= roi[3]:
                current_ids.add(track_id)
                if track_id not in zone_visits:
                    entered_at = datetime.now().astimezone().isoformat(timespec="seconds")
                    zone_visits[track_id] = (open_zone_visit(session_id, track_id, entered_at), time.time())
            elif track_id in zone_visits:
                finish_zone_visit(track_id)
        for track_id in list(zone_visits):
            if track_id not in active_tracks:
                finish_zone_visit(track_id)
        zone_duration = round(sum(max(0, time.time() - entered) for _, entered in zone_visits.values()), 1)
        if not centers:
            activity = "Tidak ada orang"
        elif not inside:
            activity = "Di luar zona kerja"
        elif now - last_motion <= 5:
            activity = "Sedang bergerak / aktif"
        else:
            activity = "Diam / tidak banyak bergerak"
        activity_history.append(activity)
        activity = Counter(activity_history).most_common(1)[0][0]

        roi_color = (0, 255, 0) if inside else (0, 200, 255)
        x1, y1, x2, y2 = roi
        length = max(16, min(w, h) // 18)
        for x, y, sx, sy in ((x1,y1,1,1),(x2,y1,-1,1),(x1,y2,1,-1),(x2,y2,-1,-1)):
            cv2.line(frame, (x,y), (x+sx*length,y), roi_color, 2)
            cv2.line(frame, (x,y), (x,y+sy*length), roi_color, 2)
        cv2.putText(frame, "ZONA KERJA", (x1 + 5, max(16, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, .42, roi_color, 1, cv2.LINE_AA)
        cv2.putText(frame, f"Orang: {count} | Confidence rata-rata: {confidence * 100:.1f}%", (12, 28), cv2.FONT_HERSHEY_SIMPLEX, .62, (255, 255, 255), 2)
        cv2.putText(frame, f"Kamera laptop #{camera_index} | {activity}", (12, 54), cv2.FONT_HERSHEY_SIMPLEX, .55, (255, 255, 255), 2)
        elapsed = max(1e-6, time.perf_counter() - last_perf_at)
        camera_fps = 1.0 / elapsed
        last_perf_at = time.perf_counter()
        with state_lock:
            latest_frame = frame.copy()
            system_state.update({
                "person_detected": count > 0, "person_count": count,
                "person_confidence": round(confidence * 100, 1), "visual_activity": activity,
                "desk_objects": desk_items,
                "final_validation": "Orang terdeteksi" if count else "Tidak ada orang terdeteksi",
                "camera_status": "Kamera terhubung", "camera_index": camera_index,
                "last_frame_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                "dark_frame": False, "frame_brightness": round(brightness, 2),
                "camera_fps": round(camera_fps, 1), "inference_ms": round(inference_ms, 1),
                "zone_duration_sec": zone_duration,
            })
        if count and not last_detection and now - last_auto_snapshot_at >= 30:
            save_snapshot(frame.copy(), count, confidence, "deteksi baru")
            last_auto_snapshot_at = now
        last_detection = count > 0
        if now - last_sample_at >= 30:
            save_evaluation_sample(frame.copy(), count, confidence, activity, desk_items)
            last_sample_at = now
        if now - last_spatiotemporal_at >= 1:
            sampled_at = datetime.now().astimezone().isoformat(timespec="seconds")
            save_spatiotemporal_data(session_id, sampled_at, count, confidence, activity,
                                     tracked_points, camera_fps, inference_ms)
            last_spatiotemporal_at = now
        ok, buffer = cv2.imencode(".jpg", frame)
        if ok:
            try:
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
            except GeneratorExit:
                if cap is not None:
                    cap.release()
                raise
    if cap is not None:
        cap.release()


@app.route("/")
@app.route("/monitoring")
def index():
    return redirect(os.environ.get("SMARTOFFICE_WEB_ORIGIN", "http://127.0.0.1:3000").split(",")[0].rstrip("/") + "/login", code=302)


@app.route("/video_feed")
def video_feed():
    return Response(stream_with_context(generate_video_frames()), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/api/status")
def api_status():
    with state_lock:
        if system_state["co2_ppm"] is None:
            tick = int(time.time() // 4)
            system_state.update({
                "co2_ppm": 620 + (tick % 8) * 35,
                "temperature_c": round(24.0 + (tick % 5) * .3, 1),
                "humidity_percent": round(48.0 + (tick % 7) * 1.2, 1),
                "sensor_status": "Mode demo (data dummy)",
            })
        elif system_state["sensor_updated_at"] and system_state["sensor_status"] == "Data SCD40 diterima":
            try:
                updated = datetime.fromisoformat(system_state["sensor_updated_at"])
                age = (datetime.now().astimezone() - updated).total_seconds()
                if age > 30:
                    system_state["sensor_status"] = "Data SCD40 kedaluwarsa"
            except ValueError:
                system_state["sensor_status"] = "Waktu data SCD40 tidak valid"
        today = datetime.now().astimezone().date().isoformat()
        system_state["zone_entries_today"] = int(db_read(
            "SELECT COUNT(*) AS n FROM zone_visits WHERE entered_at LIKE ?", (today + "%",)
        )[0]["n"] or 0)
        system_state["zone_exits_today"] = int(db_read(
            "SELECT COUNT(*) AS n FROM zone_visits WHERE exited_at LIKE ?", (today + "%",)
        )[0]["n"] or 0)
        response = jsonify(system_state.copy())
        response.headers["Cache-Control"] = "no-store"
        return response


@app.route("/api/camera/reconnect", methods=["POST"])
def reconnect_camera():
    global camera_retry_requested
    with state_lock:
        camera_retry_requested = True
        system_state["camera_status"] = "Mencoba menyambungkan ulang"
    return jsonify({"status": "ok", "message": "Kamera akan dicoba kembali."})


@app.route("/api/detection/settings", methods=["POST"])
def set_detection_settings():
    global DETECTION_CONFIDENCE
    data = request.get_json(silent=True) or {}
    try:
        confidence = float(data["confidence"])
        zone = {key: float(data["zone"][key]) for key in ("x1", "y1", "x2", "y2")}
        if not 0.1 <= confidence <= 0.9 or any(not 0 <= value <= 1 for value in zone.values()):
            raise ValueError
        if zone["x2"] - zone["x1"] < 0.1 or zone["y2"] - zone["y1"] < 0.1:
            raise ValueError
    except (KeyError, TypeError, ValueError):
        return jsonify({"status": "error", "message": "Confidence harus 10–90% dan zona valid dengan lebar/tinggi minimal 10%."}), 400
    DETECTION_CONFIDENCE = confidence
    with state_lock:
        ZONE_CONFIG.update(zone)
        system_state["detection_confidence_threshold"] = confidence
        system_state["zone_config"] = ZONE_CONFIG.copy()
    return jsonify({"status": "ok", "confidence": confidence, "zone": ZONE_CONFIG.copy()})


@app.route("/api/evaluation")
def evaluation_summary():
    summary = db_read("""SELECT COUNT(*) AS reviewed,
        SUM(CASE WHEN actual_count = predicted_count THEN 1 ELSE 0 END) AS exact_matches
        FROM evaluation_samples WHERE actual_count IS NOT NULL""")[0]
    reviewed = int(summary["reviewed"] or 0)
    matches = int(summary["exact_matches"] or 0)
    rows = db_read("""SELECT id,captured_at,predicted_count,confidence,activity,objects_json,
        image_file,actual_count,reviewed_at FROM evaluation_samples
        ORDER BY CASE WHEN actual_count IS NULL THEN 0 ELSE 1 END, id DESC LIMIT 25""")
    samples = []
    for row in rows:
        item = dict(row)
        item["objects"] = json.loads(item.pop("objects_json"))
        item["image_url"] = f"/training_data/{item.pop('image_file')}"
        samples.append(item)
    return jsonify({
        "reviewed_samples": reviewed,
        "exact_count_matches": matches,
        "count_accuracy_percent": round(matches * 100 / reviewed, 1) if reviewed else None,
        "pending_count": sum(1 for row in samples if row["actual_count"] is None),
        "samples": samples,
        "metric_note": "Akurasi hitung = sampel yang jumlah prediksinya sama dengan jumlah aktual / seluruh sampel yang sudah dikonfirmasi.",
    })


@app.route("/api/evaluation/<int:sample_id>/review", methods=["POST"])
def review_evaluation_sample(sample_id):
    data = request.get_json(silent=True) or {}
    try:
        actual_count = int(data["actual_count"])
        if actual_count < 0 or actual_count > 100:
            raise ValueError
    except (KeyError, TypeError, ValueError):
        return jsonify({"status": "error", "message": "Jumlah aktual harus berupa angka 0 sampai 100."}), 400
    exists = db_read("SELECT id FROM evaluation_samples WHERE id=?", (sample_id,))
    if not exists:
        return jsonify({"status": "error", "message": "Sampel tidak ditemukan."}), 404
    db_write("UPDATE evaluation_samples SET actual_count=?, reviewed_at=? WHERE id=?",
             (actual_count, datetime.now().astimezone().isoformat(timespec="seconds"), sample_id))
    return jsonify({"status": "ok"})


@app.route("/api/audio/evaluation")
def audio_evaluation():
    reviewed_rows = db_read("SELECT predicted_label,actual_label FROM audio_samples WHERE actual_label IS NOT NULL")
    reviewed = len(reviewed_rows)
    correct = sum(1 for row in reviewed_rows if row["predicted_label"] == row["actual_label"])
    class_metrics = {}
    confusion = {actual: {predicted: 0 for predicted in ("quiet", "noise")} for actual in ("quiet", "noise")}
    for row in reviewed_rows:
        actual, predicted = row["actual_label"], row["predicted_label"]
        if actual in confusion and predicted in confusion[actual]:
            confusion[actual][predicted] += 1
    for label in ("quiet", "noise"):
        tp = confusion[label][label]
        fp = sum(confusion[actual][label] for actual in ("quiet", "noise") if actual != label)
        fn = sum(confusion[label][predicted] for predicted in ("quiet", "noise") if predicted != label)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        class_metrics[label] = {
            "precision_percent": round(precision * 100, 1),
            "recall_percent": round(recall * 100, 1),
            "f1_percent": round((2 * precision * recall / (precision + recall) * 100) if precision + recall else 0.0, 1),
            "support": tp + fn,
        }
    rows = db_read("SELECT id,sampled_at,level_dbfs,zero_crossing_rate,predicted_label,threshold_dbfs,actual_label FROM audio_samples ORDER BY id DESC LIMIT 12")
    return jsonify({
        "available": AUDIO_AVAILABLE,
        "accuracy_percent": round(correct * 100 / reviewed, 1) if reviewed else None,
        "reviewed_samples": reviewed,
        "class_metrics": class_metrics,
        "confusion_matrix": confusion,
        "samples": [dict(row) for row in rows],
        "note": "Akurasi dihitung dari prediksi tersimpan yang dibandingkan dengan label noise/quiet yang dikonfirmasi manual.",
    })


@app.route("/api/audio/review/<int:sample_id>", methods=["POST"])
def review_audio_sample(sample_id):
    data = request.get_json(silent=True) or {}
    actual = str(data.get("actual_label", "")).lower()
    if actual not in ("noise", "quiet"):
        return jsonify({"status": "error", "message": "Label harus noise atau quiet."}), 400
    if not db_read("SELECT id FROM audio_samples WHERE id=?", (sample_id,)):
        return jsonify({"status": "error", "message": "Sampel audio tidak ditemukan."}), 404
    db_write("UPDATE audio_samples SET actual_label=?, reviewed_at=? WHERE id=?",
             (actual, datetime.now().astimezone().isoformat(timespec="seconds"), sample_id))
    update_audio_accuracy()
    return jsonify({"status": "ok"})


@app.route("/api/audio/threshold", methods=["POST"])
def set_audio_threshold():
    global AUDIO_THRESHOLD_DBFS
    data = request.get_json(silent=True) or {}
    try:
        value = float(data["threshold_dbfs"])
        if not -80 <= value <= -10:
            raise ValueError
    except (KeyError, TypeError, ValueError):
        return jsonify({"status": "error", "message": "Ambang harus antara -80 dan -10 dBFS."}), 400
    AUDIO_THRESHOLD_DBFS = value
    with state_lock:
        system_state["audio_threshold_dbfs"] = value
    return jsonify({"status": "ok", "threshold_dbfs": value})


@app.route("/api/audio/calibrate", methods=["POST"])
def calibrate_audio():
    if not AUDIO_AVAILABLE:
        return jsonify({"status": "error", "message": "sounddevice atau mikrofon belum tersedia."}), 503
    audio_calibrate_event.set()
    with state_lock:
        system_state["audio_status"] = "Kalibrasi akan dimulai pada segmen audio berikutnya"
        system_state["audio_calibration_progress"] = 0
    return jsonify({"status": "ok", "message": "Kalibrasi berlangsung selama dua segmen 10 detik."})


@app.route("/api/export/colab")
def export_colab_data():
    """Package SQLite tables and saved review frames for the Colab analysis notebook."""
    occupancy = db_read("SELECT sampled_at,session_id,person_count,mean_confidence,activity,camera_fps,inference_ms FROM occupancy_samples ORDER BY sampled_at")
    tracks = db_read("SELECT sampled_at,session_id,track_id,x_norm,y_norm,confidence FROM tracking_points ORDER BY sampled_at")
    visits = db_read("SELECT session_id,track_id,entered_at,exited_at,duration_sec FROM zone_visits ORDER BY entered_at")
    evaluations = db_read("SELECT id,captured_at,predicted_count,confidence,activity,objects_json,image_file,actual_count,reviewed_at FROM evaluation_samples ORDER BY id")
    output = io.BytesIO()

    def add_csv(archive, filename, headers, rows):
        stream = io.StringIO()
        writer = csv.writer(stream)
        writer.writerow(headers)
        writer.writerows([tuple(row) for row in rows])
        archive.writestr(filename, stream.getvalue().encode("utf-8-sig"))

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        add_csv(archive, "occupancy.csv", ["sampled_at", "session_id", "person_count", "mean_confidence", "activity", "camera_fps", "inference_ms"], occupancy)
        add_csv(archive, "tracks.csv", ["sampled_at", "session_id", "track_id", "x_norm", "y_norm", "confidence"], tracks)
        add_csv(archive, "zone_visits.csv", ["session_id", "track_id", "entered_at", "exited_at", "duration_sec"], visits)
        add_csv(archive, "evaluation_samples.csv", ["id", "captured_at", "predicted_count", "confidence", "activity", "objects_json", "image_file", "actual_count", "reviewed_at"], evaluations)
        quality = db_read("SELECT observed_at,event_type,brightness FROM quality_events ORDER BY observed_at")
        audio = db_read("SELECT id,sampled_at,level_dbfs,zero_crossing_rate,predicted_label,threshold_dbfs,processed_features,actual_label,reviewed_at FROM audio_samples ORDER BY id")
        add_csv(archive, "quality_events.csv", ["observed_at", "event_type", "brightness"], quality)
        add_csv(archive, "audio_samples.csv", ["id", "sampled_at", "level_dbfs", "zero_crossing_rate", "predicted_label", "threshold_dbfs", "processed_features", "actual_label", "reviewed_at"], audio)
        for row in evaluations:
            image_path = os.path.join(DATASET_DIR, row["image_file"])
            if os.path.isfile(image_path):
                archive.write(image_path, f"training_data/{row['image_file']}")
        archive.writestr("README.txt", "Ekspor Smart Office untuk notebook Google Colab. occupancy.csv berisi jumlah orang per detik; tracks.csv berisi posisi ternormalisasi dan ID tracker centroid; evaluation_samples.csv berisi sampel yang dapat diberi label jumlah aktual; audio_samples.csv berisi fitur audio tereduksi tanpa PCM mentah dan label noise/quiet; quality_events.csv menandai frame gelap (mean grayscale <10). Akurasi hanya dapat dihitung pada baris berlabel aktual. Data ini untuk analisis; bukan anotasi bounding box untuk melatih bobot YOLO.")
    output.seek(0)
    return send_file(output, mimetype="application/zip", as_attachment=True, download_name="smartoffice_colab_export.zip")


@app.route("/api/data/clear", methods=["POST"])
def clear_collected_data():
    global camera_retry_requested
    db = db_connect()
    try:
        for table in ("evaluation_samples", "occupancy_samples", "tracking_points", "quality_events", "audio_samples", "zone_visits"):
            db.execute(f"DELETE FROM {table}")
        db.commit()
    finally:
        db.close()
    for directory, pattern in ((SNAPSHOT_DIR, "snapshot_*.jpg"), (DATASET_DIR, "sample_*.jpg"), (RAW_DATASET_DIR, "capture_*.jpg")):
        for filename in glob.glob(os.path.join(directory, pattern)):
            try:
                os.remove(filename)
            except OSError:
                pass
    with state_lock:
        camera_retry_requested = True
        system_state.update({
            "snapshots": [], "audio_accuracy_percent": None, "audio_reviewed_samples": 0,
            "audio_sample_id": None, "dark_frame_events": 0,
            "zone_entries_today": 0, "zone_exits_today": 0, "zone_duration_sec": 0.0,
        })
    return jsonify({"status": "ok", "message": "Data, sampel gambar, dan evaluasi tersimpan sudah dihapus."})


@app.route("/api/scd40", methods=["POST"])
def receive_scd40():
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({"status": "error", "message": "Payload harus berupa objek JSON."}), 400
    try:
        co2 = float(data["co2_ppm"])
        temp = float(data["temperature_c"])
        humidity = float(data["humidity_percent"])
        if data.get("source", "scd40") != "scd40":
            raise ValueError
        if not (0 < co2 <= 40000 and -40 <= temp <= 125 and 0 <= humidity <= 100):
            raise ValueError
    except (KeyError, TypeError, ValueError):
        return jsonify({"status": "error", "message": "Kirim co2_ppm, temperature_c, humidity_percent dengan angka valid."}), 400
    sampled_at = datetime.now(timezone.utc).isoformat(timespec="microseconds")
    db_write("INSERT INTO sensor_readings (timestamp,co2_ppm,temperature_c,humidity_percent,source) VALUES (?,?,?,?,?)",
             (sampled_at, co2, temp, humidity, "scd40"))
    with state_lock:
        system_state.update({"co2_ppm": round(co2, 1), "temperature_c": round(temp, 1),
                             "humidity_percent": round(humidity, 1), "sensor_status": "Data SCD40 diterima",
                             "sensor_updated_at": datetime.now().astimezone().isoformat(timespec="seconds")})
    return jsonify({"status": "ok"})


@app.route("/api/snapshot", methods=["POST"])
def take_snapshot():
    with state_lock:
        frame = latest_frame.copy() if latest_frame is not None else None
        count = system_state["person_count"]
        confidence = system_state["person_confidence"] / 100
    if frame is None:
        return jsonify({"status": "error", "message": "Frame kamera belum tersedia."}), 503
    return jsonify({"status": "ok", "snapshot": save_snapshot(frame, count, confidence)})


@app.route("/api/training/capture", methods=["POST"])
def capture_training_image():
    with state_lock:
        frame = latest_clean_frame.copy() if latest_clean_frame is not None else None
    if frame is None:
        return jsonify({"status": "error", "message": "Frame kamera belum tersedia."}), 503
    filename = f"capture_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.jpg"
    if not cv2.imwrite(os.path.join(RAW_DATASET_DIR, filename), frame, [cv2.IMWRITE_JPEG_QUALITY, 95]):
        return jsonify({"status": "error", "message": "Gagal menyimpan foto dataset."}), 500
    clean_old_images(RAW_DATASET_DIR, "capture_*.jpg", keep=500)
    count = len(glob.glob(os.path.join(RAW_DATASET_DIR, "capture_*.jpg")))
    return jsonify({"status": "ok", "filename": filename, "image_count": count,
                    "message": "Foto asli tersimpan tanpa blur dan overlay. Pastikan hanya objek yang ingin dilatih yang terlihat."})


@app.route("/api/training/export")
def export_training_images():
    images = sorted(glob.glob(os.path.join(RAW_DATASET_DIR, "capture_*.jpg")))
    if not images:
        return jsonify({"status": "error", "message": "Belum ada foto dataset. Ambil foto dari panel kamera terlebih dahulu."}), 404
    output = io.BytesIO()
    readme = ("Foto kamera asli untuk tahap ANOTASI, belum berlabel dan belum siap untuk training. "
              "Unggah images/ ke proyek Object Detection Roboflow, buat bounding box dan kelas, "
              "kemudian ekspor dataset format YOLOv8/YOLO11 Detection agar memperoleh data.yaml dan label YOLO. "
              "Foto ini disimpan tanpa blur/overlay. Jangan sertakan orang tanpa izin; untuk kelas objek, arahkan kamera hanya ke objek.")
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("README.txt", readme)
        for path in images:
            archive.write(path, f"images/{os.path.basename(path)}")
    output.seek(0)
    return send_file(output, mimetype="application/zip", as_attachment=True,
                     download_name="smartoffice_foto_asli_untuk_anotasi.zip")


@app.route("/snapshots/<path:filename>")
def snapshot_file(filename):
    return send_from_directory(SNAPSHOT_DIR, filename)


@app.route("/training_data/<path:filename>")
def training_sample_file(filename):
    return send_from_directory(DATASET_DIR, filename)


if __name__ == "__main__":
    print("Server Smart Office berjalan di http://127.0.0.1:5000")
    if AUDIO_AVAILABLE:
        threading.Thread(target=audio_listener_thread, daemon=True, name="audio-monitor").start()
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
