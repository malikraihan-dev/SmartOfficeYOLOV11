"""MQTT subscriber worker for receiving SCD40 telemetry from ESP32 via Mosquitto."""
from __future__ import annotations

from datetime import datetime, timezone
import hmac
import json
import os
import threading
import time
from typing import Any, Callable

from database import load_backend_env

try:
    import paho.mqtt.client as mqtt
    MQTT_LIBRARY_AVAILABLE = True
except Exception:
    mqtt = None
    MQTT_LIBRARY_AVAILABLE = False

load_backend_env()

DEFAULT_MQTT_HOST = "127.0.0.1"
DEFAULT_MQTT_PORT = 1883
DEFAULT_MQTT_TOPIC = "smartoffice/scd40/telemetry"


def get_mqtt_config() -> dict[str, Any]:
    enabled_raw = os.environ.get("MQTT_ENABLED", "1").strip().lower()
    enabled = enabled_raw not in ("0", "false", "no", "off")
    host = os.environ.get("MQTT_BROKER_HOST", DEFAULT_MQTT_HOST).strip() or DEFAULT_MQTT_HOST
    try:
        port = int(os.environ.get("MQTT_BROKER_PORT", str(DEFAULT_MQTT_PORT)).strip())
    except ValueError:
        port = DEFAULT_MQTT_PORT
    topic = os.environ.get("MQTT_TOPIC", DEFAULT_MQTT_TOPIC).strip() or DEFAULT_MQTT_TOPIC
    username = os.environ.get("MQTT_USERNAME", "").strip()
    password = os.environ.get("MQTT_PASSWORD", "").strip()
    device_token = os.environ.get("SMARTOFFICE_DEVICE_TOKEN", "").strip()
    return {
        "enabled": enabled,
        "host": host,
        "port": port,
        "topic": topic,
        "username": username,
        "password": password,
        "device_token": device_token,
    }


def parse_and_validate_scd40_payload(
    raw_payload: str | bytes | dict[str, Any],
    expected_device_token: str = "",
) -> dict[str, Any]:
    """Parse and validate SCD40 telemetry JSON from MQTT or HTTP.

    Supports canonical keys (co2_ppm, temperature_c, humidity_percent) and short aliases
    (co2, suhu/temp, lembap/humidity/rh).
    """
    if isinstance(raw_payload, (bytes, bytearray)):
        data = json.loads(raw_payload.decode("utf-8"))
    elif isinstance(raw_payload, str):
        data = json.loads(raw_payload)
    elif isinstance(raw_payload, dict):
        data = raw_payload
    else:
        raise ValueError("Payload harus berupa objek JSON.")

    if not isinstance(data, dict):
        raise ValueError("Payload harus berupa objek JSON.")

    if expected_device_token:
        provided_token = str(data.get("device_token", "") or "")
        if not hmac.compare_digest(provided_token.encode("utf-8"), expected_device_token.encode("utf-8")):
            raise PermissionError("Token perangkat MQTT tidak valid.")

    source = str(data.get("source", "scd40"))
    if source != "scd40":
        raise ValueError("Source hanya mendukung 'scd40'.")

    co2_raw = data.get("co2_ppm", data.get("co2"))
    temp_raw = data.get("temperature_c", data.get("suhu", data.get("temp")))
    hum_raw = data.get("humidity_percent", data.get("lembap", data.get("humidity", data.get("rh"))))

    if co2_raw is None or temp_raw is None or hum_raw is None:
        raise ValueError("Kirim co2_ppm, temperature_c, humidity_percent dengan angka valid.")

    co2 = float(co2_raw)
    temp = float(temp_raw)
    humidity = float(hum_raw)

    if not (0 < co2 <= 40000 and -40 <= temp <= 125 and 0 <= humidity <= 100):
        raise ValueError("Nilai sensor di luar rentang fisik SCD40.")

    return {
        "co2_ppm": co2,
        "temperature_c": temp,
        "humidity_percent": humidity,
        "source": "scd40",
    }


def process_mqtt_scd40_message(
    raw_payload: str | bytes | dict[str, Any],
    db_write: Callable[[str, tuple[Any, ...]], Any],
    state_lock: threading.Lock,
    system_state: dict[str, Any],
    expected_device_token: str = "",
) -> dict[str, Any]:
    """Validate an incoming MQTT payload, persist to sensor_readings, and update system_state."""
    reading = parse_and_validate_scd40_payload(raw_payload, expected_device_token=expected_device_token)
    sampled_at = datetime.now(timezone.utc).isoformat(timespec="microseconds")
    db_write(
        "INSERT INTO sensor_readings (timestamp,co2_ppm,temperature_c,humidity_percent,source) VALUES (?,?,?,?,?)",
        (sampled_at, reading["co2_ppm"], reading["temperature_c"], reading["humidity_percent"], "scd40"),
    )
    now_local = datetime.now().astimezone().isoformat(timespec="seconds")
    with state_lock:
        system_state.update({
            "co2_ppm": round(reading["co2_ppm"], 1),
            "temperature_c": round(reading["temperature_c"], 1),
            "humidity_percent": round(reading["humidity_percent"], 1),
            "sensor_status": "Data SCD40 diterima",
            "sensor_updated_at": now_local,
            "mqtt_last_message_at": now_local,
        })
    return reading


def start_mqtt_listener(
    db_write: Callable[[str, tuple[Any, ...]], Any],
    state_lock: threading.Lock,
    system_state: dict[str, Any],
) -> threading.Thread | None:
    """Start a daemon thread subscribing to Mosquitto MQTT for SCD40 telemetry."""
    cfg = get_mqtt_config()
    if not cfg["enabled"]:
        with state_lock:
            system_state["mqtt_status"] = "MQTT dinonaktifkan (MQTT_ENABLED=0)"
        return None

    if not MQTT_LIBRARY_AVAILABLE:
        with state_lock:
            system_state["mqtt_status"] = "Library paho-mqtt belum terpasang"
        return None

    def worker() -> None:
        if hasattr(mqtt, "CallbackAPIVersion"):
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"smartoffice-backend-{os.getpid()}")
        else:
            client = mqtt.Client(client_id=f"smartoffice-backend-{os.getpid()}")

        if cfg["username"]:
            client.username_pw_set(cfg["username"], cfg["password"] or None)

        def on_connect(cli, _userdata, _flags, reason_code, *_extra):
            rc = getattr(reason_code, "value", reason_code)
            if rc == 0:
                cli.subscribe(cfg["topic"], qos=1)
                with state_lock:
                    system_state["mqtt_status"] = f"Terhubung ke MQTT ({cfg['host']}:{cfg['port']} -> {cfg['topic']})"
                print(f"[MQTT] Terhubung ke broker {cfg['host']}:{cfg['port']} | Subscribe: {cfg['topic']}")
            else:
                with state_lock:
                    system_state["mqtt_status"] = f"Gagal konek MQTT (kode {rc})"
                print(f"[MQTT] Gagal konek ke broker, kode: {rc}")

        def on_disconnect(_cli, _userdata, *_extra):
            with state_lock:
                system_state["mqtt_status"] = f"Terputus dari MQTT ({cfg['host']}:{cfg['port']}), mencoba ulang..."

        def on_message(_cli, _userdata, msg):
            try:
                reading = process_mqtt_scd40_message(
                    msg.payload,
                    db_write=db_write,
                    state_lock=state_lock,
                    system_state=system_state,
                    expected_device_token=cfg["device_token"],
                )
                print(
                    f"[MQTT] Data SCD40 masuk ({msg.topic}): "
                    f"CO2={reading['co2_ppm']:.0f} ppm, T={reading['temperature_c']:.1f} C, RH={reading['humidity_percent']:.1f}%"
                )
            except Exception as exc:
                print(f"[MQTT] Payload diabaikan pada {msg.topic}: {exc}")

        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        client.on_message = on_message
        client.reconnect_delay_set(min_delay=2, max_delay=30)

        while True:
            try:
                with state_lock:
                    system_state["mqtt_status"] = f"Menghubungkan ke MQTT {cfg['host']}:{cfg['port']}..."
                client.connect(cfg["host"], cfg["port"], keepalive=60)
                client.loop_forever(retry_first_connection=True)
            except Exception as exc:
                with state_lock:
                    system_state["mqtt_status"] = f"Menunggu broker MQTT ({cfg['host']}:{cfg['port']}): {str(exc)[:60]}"
                time.sleep(5)

    thread = threading.Thread(target=worker, daemon=True, name="mqtt-scd40-listener")
    thread.start()
    return thread
