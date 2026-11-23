"""Bootstrap script executed on Backend container startup.

1. Waits for PostgreSQL to accept connections.
2. Initializes all 10 Smart Office & Admin Auth tables.
3. Seeds minimal initial telemetry if sensor_readings is empty (andSMARTOFFICE_AUTO_SEED=1).
4. Creates default admin account if admins table is empty and SMARTOFFICE_ADMIN_PASSWORD is set.
"""
from __future__ import annotations

import os
from pathlib import Path
import sys
import time

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from admin_auth import AdminStore  # noqa: E402
from database import connect_database, is_postgres_target, resolve_database_target  # noqa: E402
from scripts.connect_postgres import init_postgres_schema, seed_minimal_data  # noqa: E402


def wait_for_database(target: str, max_attempts: int = 30, delay_sec: float = 2.0) -> None:
    for attempt in range(1, max_attempts + 1):
        try:
            db = connect_database(target)
            try:
                db.execute("SELECT 1")
            finally:
                db.close()
            print(f"[Bootstrap] Database siap pada percobaan ke-{attempt}.")
            return
        except Exception as exc:
            print(f"[Bootstrap] Menunggu database siap ({attempt}/{max_attempts}): {exc}")
            time.sleep(delay_sec)
    raise RuntimeError("Database tidak merespons setelah batas waktu tunggu habis.")


def main() -> int:
    target = resolve_database_target()
    wait_for_database(target)

    if is_postgres_target(target):
        init_postgres_schema(target)
        print("[Bootstrap] Skema tabel PostgreSQL siap.")
        auto_seed = os.environ.get("SMARTOFFICE_AUTO_SEED", "1").strip().lower() not in ("0", "false", "no")
        if auto_seed:
            db = connect_database(target)
            try:
                cnt = int(db.execute("SELECT COUNT(*) AS n FROM sensor_readings").fetchone()["n"] or 0)
            finally:
                db.close()
            if cnt == 0:
                seed_minimal_data(target)
                print("[Bootstrap] Data awal minimal ditambahkan ke PostgreSQL.")

    admin_user = os.environ.get("SMARTOFFICE_ADMIN_USER", "admin").strip() or "admin"
    admin_pass = os.environ.get("SMARTOFFICE_ADMIN_PASSWORD", "").strip()
    if admin_pass:
        store = AdminStore(target)
        if not store.configured():
            store.set_admin(admin_user, admin_pass)
            print(f"[Bootstrap] Akun admin awal '{admin_user}' berhasil dibuat.")
        else:
            print("[Bootstrap] Akun admin sudah tersedia di database.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
