# Rancangan migrasi Next.js dan Python

Status: **frontend dan login admin diimplementasikan**. Next.js App Router + TypeScript tersedia di `apps/web`, dengan login dan lima halaman sesuai DESIGN.md. Backend tetap Flask; dashboard HTML lama telah dihapus. Port 5000 mengelola API, perangkat dan sesi admin. Pemisahan backend, layanan prediksi sensor, dan deployment banyak perangkat masih rancangan.

## Pilihan stack

- Frontend: Next.js App Router + React + TypeScript. React sudah menjadi bagian Next.js; tidak perlu aplikasi React/Vite kedua.
- Backend tahap pertama: Flask yang ada. Pertahankan API, pemrosesan kamera, SQLite, dan penerimaan ESP32.
- Backend tahap berikutnya, bila dibutuhkan: FastAPI dengan router terpisah. Jangan memigrasikan framework frontend dan seluruh backend pada satu perubahan.
- SQLite cukup untuk tahap satu instalasi lokal. Pertimbangkan PostgreSQL setelah kebutuhan banyak ruangan/perangkat ditetapkan.
- Training: notebook Colab di luar proses web. Inference Python menggunakan artefak tervalidasi, tidak menjalankan training dari request browser.

Server Components untuk kerangka halaman dan konten awal. Client Components untuk polling, filter, kontrol kamera, dan grafik interaktif. Rujukan: [Next.js Server and Client Components](https://nextjs.org/docs/app/getting-started/server-and-client-components). Jika beralih ke FastAPI, pisahkan router seperti [Bigger Applications](https://fastapi.tiangolo.com/tutorial/bigger-applications/).

## Struktur yang disarankan setelah migrasi

```text
smartoffice/
  apps/
    web/
      src/app/
        (office)/layout.tsx
        (office)/monitoring/page.tsx
        (office)/datasets/sensors/page.tsx
        (office)/datasets/vision/page.tsx
        (office)/models/page.tsx
        (office)/settings/page.tsx
      src/components/ui/
      src/features/monitoring/
      src/features/sensors/
      src/features/datasets/
      src/lib/api.ts
      src/lib/types.ts
      src/styles/tokens.css
    api/
      app/main.py
      app/routes/       # sensors, datasets, camera, models
      app/services/     # sensor ingest, vision inference, sensor forecast
      app/repositories/ # SQL dan transaksi
      app/schemas/      # validasi input/output
      app/workers/      # satu pemilik kamera dan mikrofon
      tests/
  notebooks/
  data/examples/       # dummy saja; data nyata tidak masuk version control
  models/              # artefak terverifikasi, metadata dan versi
  docs/
  README.md
```

Struktur di atas adalah tujuan jangka panjang. Frontend memakai `apps/web/src/app`, `components`, `features`, `lib`, dan `styles`. Backend `app.py`, `sensor_dataset.py`, notebook, model, dan data lama tidak dipindah agar aplikasi tetap berjalan.

## Alur data

ESP32 → API Python → database → API ringkasan/CSV → halaman Dataset sensor → Colab → model + metadata → validasi → layanan prediksi Python → halaman monitoring.

Untuk tahap lokal, Next.js rewrites meneruskan `/api/*`, `/video_feed`, `/snapshots/*`, dan `/training_data/*` ke `SMARTOFFICE_API_URL` (default `http://127.0.0.1:5000`), sisanya ditangani Next.js. Untuk produksi, gunakan reverse proxy dengan buffering MJPEG nonaktif; contoh ada di `apps/web/README.md`. Endpoint status dan dataset sensor memakai `no-store`. Polling dibatasi timeout 8 detik, tidak tumpang tindih, berhenti saat komponen dilepas, dan dijeda saat tab disembunyikan. Pembacaan sensor lebih dari 30 detik ditandai kedaluwarsa. Tidak ada loop kamera di Next.js. Generator Flask lama masih dimiliki request MJPEG, sehingga batasi satu pratinjau aktif; pemilik kamera tunggal lintas-klien adalah pekerjaan backend berikutnya.

## Tahapan dan kriteria selesai

1. **Saat ini:** pencatatan sensor, CSV asli/dummy, notebook, API kontrak, dan UI dataset. Uji database sementara tanpa membuka kamera.
2. **Frontend (diimplementasikan):** shell Next.js, monitoring, dataset sensor/kamera, model dan pengaturan memakai API yang sama. Tes browser memakai API fixture terisolasi untuk loading, kosong, offline, mobile, keyboard, ekspor, ulasan dan pengaturan. Kamera fisik, mikrofon dan ESP32 perlu uji integrasi perangkat terpisah.
3. **Pisahkan backend:** keluarkan database, kamera, audio, dan sensor dari `app.py`. Pindah ke FastAPI hanya jika ada alasan yang jelas; pertahankan kontrak dengan tes.
4. **Integrasi model:** verifikasi asal, versi library, daftar fitur, horizon, interval, dan metrik terhadap baseline. Pasang hanya artefak tepercaya. Riwayat kurang dari 31 menit/celah data harus menghasilkan status unavailable, bukan prediksi dummy.
5. **Banyak perangkat/deployment:** tambahkan identitas room/device, peran pengguna yang lebih lengkap, retensi, backup, dan timestamp ukur perangkat. Login admin lokal serta proteksi unduhan sudah diimplementasikan di `admin_auth.py`; token ingest perangkat opsional. Autentikasi memakai database terpisah `instance/admin_auth.db`, cookie opaque HttpOnly dan sesi 8 jam, bukan credential pada browser. Lihat [AUTH.md](AUTH.md).

## Struktur README yang disarankan

Ringkasan → fitur yang sudah berjalan → screenshot → kebutuhan → cara menjalankan → konfigurasi → struktur folder → alur sensor/training → kontrak API → pengujian → batasan → roadmap → lisensi.
Pisahkan fitur aktif dari rencana. README utama memberi petunjuk singkat; detail berada di dokumen terkait.
