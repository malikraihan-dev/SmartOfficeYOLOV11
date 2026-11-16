"""Script CLI untuk simulasi publish data SCD40 ke broker MQTT Mosquitto."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from mqtt_listener import get_mqtt_config, mqtt  # noqa: E402


def main() -> int:
    cfg = get_mqtt_config()
    parser = argparse.ArgumentParser(description="Kirim paket uji SCD40 ke broker MQTT Mosquitto.")
    parser.add_argument("--host", default=cfg["host"], help=f"Host broker MQTT (default: {cfg['host']})")
    parser.add_argument("--port", type=int, default=cfg["port"], help=f"Port broker MQTT (default: {cfg['port']})")
    parser.add_argument("--topic", default=cfg["topic"], help=f"Topic MQTT (default: {cfg['topic']})")
    parser.add_argument("--co2", type=float, default=735.0, help="Nilai CO2 ppm (default: 735.0)")
    parser.add_argument("--temp", type=float, default=25.3, help="Nilai suhu C (default: 25.3)")
    parser.add_argument("--humidity", type=float, default=53.5, help="Nilai kelembapan %% (default: 53.5)")
    args = parser.parse_args()

    if mqtt is None:
        print("Library paho-mqtt belum terpasang. Jalankan: pip install paho-mqtt", file=sys.stderr)
        return 1

    payload = json.dumps({
        "co2_ppm": args.co2,
        "temperature_c": args.temp,
        "humidity_percent": args.humidity,
        "source": "scd40",
    })

    if hasattr(mqtt, "CallbackAPIVersion"):
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    else:
        client = mqtt.Client()

    if cfg["username"]:
        client.username_pw_set(cfg["username"], cfg["password"] or None)

    client.connect(args.host, args.port, keepalive=15)
    info = client.publish(args.topic, payload, qos=1)
    info.wait_for_publish(timeout=5)
    client.disconnect()
    print(f"[MQTT Publish OK] {args.host}:{args.port} [{args.topic}] -> {payload}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
