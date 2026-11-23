# Smart Office YOLOv11

Dashboard web untuk pemantauan ruang kerja menggunakan Python, Flask, OpenCV, dan YOLOv11. Aplikasi menampilkan video kamera langsung, deteksi penghuni dan objek meja, status aktivitas, serta pencatatan data untuk evaluasi. Sensor SCD40 melalui ESP32 dapat mengirim data kualitas udara ke server.

Frontend tersedia di `frontend/`: **Next.js App Router + React + TypeScript**, dengan login admin serta lima halaman Monitoring, Dataset sensor, Dataset kamera, Model, dan Pengaturan. Backend tersedia di `backend/`: **Python + Flask + OpenCV + YOLOv11**, mengelola perangkat, inference, database (**PostgreSQL** atau fallback **SQLite**), sesi admin, dan seluruh API. Port `5000` hanya melayani backend API dan mengembalikan status JSON pada `/` serta `/api/health` (tidak lagi me-redirect ke port `3000`).

Beranda **http://127.0.0.1:3000/** kini berupa landing page SaaS dengan kartu kaca, hero pratinjau, fitur, alur data, pricing, dan tautan login. Pratinjau publik/login diberi label ilustrasi. Dashboard admin menggunakan grafik riwayat sensor asli. Harga belum ditetapkan dan pembayaran belum diaktifkan; tema yang sama berlaku pada semua halaman.

## Menjalankan frontend baru

Peta struktur kode tersedia melalui [Graphify khusus proyek](docs/GRAPHIFY.md), termasuk cara query dan memperbarui grafik selama pengembangan.

Rancangan sebelum implementasi: [Google SSO, pendaftaran pengguna, dan persetujuan admin](docs/AUTH_SSO_REGISTRATION.md), mencakup arsitektur, struktur modul/database, kontrak API, dan tahapan migrasi.

Kebutuhan tambahan: Node.js 22.20+ dengan npm. Python tetap memakai dependensi di `requirements.txt`.

Dari folder `SmartOfficeYOLOV11`, siapkan dependensi backend (`backend/`) dan frontend (`frontend/`) serta akun admin sekali:

```powershell
python -m pip install -r backend/requirements.txt
npm --prefix frontend ci
python backend/manage_admin.py
```

### Koneksi Database PostgreSQL (Opsional, Fallback ke SQLite)

Salin `backend/.env.example` menjadi `backend/.env` dan atur `DATABASE_URL`:

```dotenv
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/smartoffice
```

Gunakan script `backend/scripts/connect_postgres.py` untuk menguji koneksi, membuat database PostgreSQL secara otomatis, dan menginisialisasi seluruh tabel:

```powershell
python backend/scripts/connect_postgres.py --create-db --init-schema --status
```

Jika `DATABASE_URL` tidak diatur, backend otomatis menggunakan SQLite lokal (`backend/smartoffice.db` dan `backend/instance/admin_auth.db`).

### Menjalankan Seluruh Sistem dengan Docker Compose (Direkomendasikan)

Seluruh 4 layanan (**PostgreSQL**, **Mosquitto MQTT Broker**, **Backend Python/YOLOv11**, dan **Frontend Next.js**) dapat dijalankan sekaligus menggunakan satu perintah dari folder `SmartOfficeYOLOV11`:

```powershell
docker compose up -d --build
```

Saat container menyala pertama kali, `backend/scripts/docker_bootstrap.py` otomatis:
1. Menunggu container PostgreSQL siap (`smartoffice-postgres`),
2. Membuat seluruh 10 tabel database,
3. Mengisi 5 baris data awal sensor (`--seed`), dan
4. Membuat akun admin bawaan (`username`: `admin`, `password`: `smartoffice2026` — dapat diubah melalui environment variable `SMARTOFFICE_ADMIN_USER` & `SMARTOFFICE_ADMIN_PASSWORD`).

Akses layanan Docker:
- **Frontend Web & Login**: `http://localhost:3000/login`
- **Backend Health JSON**: `http://localhost:5000/api/health`
- **MQTT Broker (ESP32-S3)**: Port `1883` (topic `smartoffice/scd40/telemetry`)
- **Database PostgreSQL (DBeaver)**: Host `localhost`, Port `5433`, Database `smartoffice`, User `postgres`, Password `1234`

### Menjalankan Secara Lokal Tanpa Docker (2 Service Terpisah atau Gabungan)

- **Service Backend mandiri (Port 5000)**:
  ```powershell
  cd backend
  .\.venv\Scripts\python.exe app.py
  ```
- **Service Frontend mandiri (Port 3000)**:
  ```powershell
  cd frontend
  npm run dev:web:compat
  ```
- **Gabungan dalam satu terminal (dari root)**:
  ```powershell
  npm run dev
  ```

Buka **http://127.0.0.1:3000/login** dan masuk dengan akun yang dibuat. Flask berjalan di **http://127.0.0.1:5000**. Request `/api/*`, `/video_feed`, `/snapshots/*`, dan `/training_data/*` diteruskan ke Flask oleh Next.js. Sesi memakai cookie HttpOnly, bukan credential di source browser. Salin `apps/web/.env.example` menjadi `.env.local` untuk mengubah `SMARTOFFICE_API_URL`, kemudian mulai ulang Next.js.

`npm run dev` juga dapat dijalankan dari `apps/web`. Launcher menjalankan Flask dan Next.js bersama; Ctrl+C menghentikan kedua layanan beserta proses turunannya. Jika satu layanan gagal, layanan lainnya ikut dihentikan. Hentikan server lama di port 3000/5000 sebelum memakai launcher; proses lain tidak dihentikan otomatis. Dependensi tidak diinstal ulang setiap startup.

Python dipilih dari `SMARTOFFICE_PYTHON` bila diatur, virtual environment aktif, `.venv` proyek, lalu perintah `python`. Contoh interpreter khusus: `$env:SMARTOFFICE_PYTHON = 'C:\path\venv\Scripts\python.exe'`. Launcher selalu mengarahkan frontend ke API lokal port 5000; untuk backend eksternal atau yang sudah berjalan, gunakan frontend saja: `cd apps/web` lalu `npm run dev:web` (atau `npm run dev:web:compat` di Windows). `run_frontend.bat` tetap menjalankan frontend saja.

Pratinjau UI dari backend fixture pengujian, bukan pengukuran perangkat nyata:

![Landing page SaaS dengan pratinjau ilustratif](docs/screenshots/landing-1440.png)

![Monitoring desktop dengan sensor demo](docs/screenshots/monitoring-1440.png)

Di Windows, launcher memakai compiler WebAssembly untuk kompatibilitas Application Control. `npm run dev:compat` memilih jalur itu secara eksplisit di platform lain. Mode produksi dari `apps/web`: `npm run build:compat` lalu `npm start` (atau `npm run build` pada mesin yang mendukung compiler native); backend produksi tetap dikelola terpisah. Override compiler ini memakai API internal Next.js dan perlu diperiksa kembali saat memperbarui Next.js; gunakan `apps/web/package-lock.json` yang disediakan.

Ketika Flask mati, halaman login menjelaskan kegagalan koneksi; sesi harus diverifikasi sebelum dashboard dapat dibuka. Pada sesi aktif, polling menampilkan error jika endpoint data gagal. Buka hanya satu halaman kamera aktif pada instalasi lokal; generator kamera Flask masih mengikuti koneksi MJPEG dan belum dipisah menjadi satu worker bersama. Rincian pengujian dan konfigurasi proxy produksi ada di [apps/web/README.md](apps/web/README.md).

## Fitur

- Login/logout admin, sesi 8 jam, proteksi API/unduhan/video, dan sidebar otomatis mengikuti kedekatan kursor (menu tombol pada ponsel).
- Deteksi jumlah orang dan objek menggunakan model YOLO.
- Tampilan video kamera langsung, status kamera, FPS, dan waktu inferensi.
- Pelacakan aktivitas/zona dan penyimpanan snapshot.
- Pemeriksaan kualitas frame dan penyamaran wajah jika model YuNet tersedia.
- Pemantauan tingkat audio melalui mikrofon (opsional).
- Data CO₂, suhu, dan kelembapan; mode demo digunakan sebelum data SCD40 diterima.
- Ulasan sampel deteksi/audio dan ekspor data untuk analisis atau pelatihan di Google Colab.
- Penyimpanan riwayat menggunakan SQLite.

## Kebutuhan

- Windows 10/11 (petunjuk di bawah memakai Windows) atau lingkungan Python yang kompatibel.
- Python 3.10 atau versi yang didukung oleh paket Ultralytics yang terpasang.
- Kamera USB/webcam untuk deteksi langsung.
- Mikrofon untuk fitur audio (opsional).
- ESP32 dan sensor SCD40 untuk pembacaan CO₂, suhu, dan kelembapan aktual (opsional).
- Koneksi internet saat instalasi dependensi dan pengunduhan bobot model pertama kali, jika bobot belum tersedia.

## Menjalankan di Windows

1. Pasang Python dan pastikan perintah `python` serta `pip` tersedia di terminal.
2. Buka folder proyek ini.
3. Siapkan dependensi dan akun seperti bagian di atas, lalu jalankan `npm run dev` untuk kedua layanan.
4. Buka [halaman login](http://127.0.0.1:3000/login). Jalur terpisah tetap tersedia: `run_windows.bat` untuk backend dan `run_frontend.bat` untuk frontend.

Alternatif melalui PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
```

Kamera harus dapat diakses oleh komputer yang menjalankan Flask. Tutup aplikasi lain yang sedang memakai kamera jika kamera tidak terdeteksi. Model bawaan adalah `yolo11n.pt`; model hasil training `best_smartoffice.pt` dapat dipilih dengan variabel lingkungan `SMARTOFFICE_MODEL` sebelum menjalankan aplikasi.

## Menghubungkan ESP32 + SCD40 (opsional)

1. Pastikan ESP32, komputer server, dan Wi-Fi berada pada jaringan yang sama.
2. Buka `SCD40_ESP32.ino` di Arduino IDE. Pasang library **Sensirion I2C SCD4x** melalui Library Manager.
3. Isi `WIFI_SSID` dan `WIFI_PASSWORD`.
4. Ganti alamat IP pada `API_URL` dengan IP komputer yang menjalankan Flask, misalnya `http://192.168.1.10:5000/api/scd40`. Jangan gunakan `127.0.0.1` pada ESP32 karena alamat itu menunjuk ke ESP32 sendiri.
5. Unggah program ke ESP32. Saat data diterima, status sensor di dashboard berubah dari mode demo ke data SCD40.

## Struktur utama

```text
SmartOfficeYOLOV11/
├── backend/                       # Service Backend Python (Flask :5000)
│   ├── app.py                     # Server Flask, deteksi YOLO, API
│   ├── database.py                # Adapter database PostgreSQL & SQLite
│   ├── admin_auth.py              # Akun, sesi dan perlindungan API
│   ├── manage_admin.py            # Pembuatan/reset akun admin
│   ├── sensor_dataset.py          # Dataset & ekspor sensor SCD40
│   ├── requirements.txt           # Dependensi Python (+ psycopg2-binary)
│   ├── .env.example               # Template DATABASE_URL PostgreSQL
│   ├── run_backend.bat            # Menjalankan service backend mandiri
│   ├── scripts/
│   │   └── connect_postgres.py    # Script CLI koneksi & init skema PostgreSQL
│   └── tests/                     # Unit test backend & PostgreSQL adapter
├── frontend/                      # Service Frontend Next.js (:3000)
│   ├── src/                       # Halaman & komponen React/TypeScript
│   ├── scripts/                   # Script launcher & kompatibilitas WASM
│   ├── run_frontend.bat           # Menjalankan service frontend mandiri
│   └── tests/                     # Tes E2E Playwright & mock API
├── SCD40_ESP32.ino                # Contoh firmware ESP32 + sensor SCD40
└── sensor_training/               # Dataset dummy & artefak training SCD40
```

Folder `snapshots/`, `training_data/`, dan `dataset_images/` dibuat otomatis bila belum tersedia. Database `smartoffice.db` juga diinisialisasi saat aplikasi berjalan.

## Data dan privasi

Aplikasi menyimpan sampel evaluasi, titik pelacakan, peristiwa kualitas frame, sampel audio, kunjungan zona, dan pembacaan SCD40 ke SQLite serta menyimpan gambar pada folder proyek. Tombol penghapusan lama mencakup data kamera/audio; riwayat sensor di `sensor_readings` tidak ikut dihapus. Ekspor dan cadangkan data sensor sebelum melakukan pengelolaan database. Pastikan kamera, mikrofon, dan data ruang kerja digunakan sesuai kebijakan privasi organisasi.

## Dataset sensor dan training Colab

1. Jalankan ulang `python app.py` setelah pembaruan ini. Tabel `sensor_readings` dibuat otomatis tanpa menghapus tabel lama.
2. Setelah login, buka [Dataset sensor](http://127.0.0.1:3000/datasets/sensors). Setiap pembacaan valid baru dari `/api/scd40` dicatat otomatis. Riwayat sebelum pembaruan tidak dapat dipulihkan dari nilai terakhir.
3. Pilih **Unduh CSV asli** untuk data yang terkumpul. Data demo dashboard tidak disimpan sebagai data asli. Instalasi saat ini ditujukan untuk satu sensor di satu ruangan.
4. Untuk latihan tanpa alat, gunakan [CSV dummy](sensor_training/scd40_dummy.csv): 30 hari, interval satu menit, 43.200 baris dengan `source=synthetic`.
5. Unggah [notebook SCD40](SmartOffice_Colab_Training_SCD40.ipynb) ke Google Colab. Runtime CPU cukup. Default `DATA_MODE='dummy'` membuat data simulasi sendiri. Pilih `DATA_MODE='upload'` untuk CSV asli atau CSV dummy yang diunduh.
6. Jalankan semua sel. Notebook memprediksi suhu dan CO₂ lima menit ke depan, membandingkan persistence/Ridge/HistGradientBoosting dengan pemisahan waktu, lalu mengunduh ZIP model, metadata, metrik dan grafik.

Hasil dummy hanya latihan alur, bukan akurasi fisik SCD40 atau validasi ruangan nyata. MAE suhu memakai °C dan MAE CO₂ memakai ppm. Model hasil notebook **belum dihubungkan** ke dashboard dan tidak menggantikan bobot YOLO. Contoh hasil simulasi lokal tersedia di `sensor_training/hasil_training_scd40.zip`.

File fitur sensor: `sensor_dataset.py`, `apps/web/src/features/sensors/sensor-dataset.tsx`, dan `tests/test_sensor_dataset.py`. Kontrak data dijelaskan di [SENSOR_API.md](docs/SENSOR_API.md).

## Pengujian fitur sensor

```powershell
python -m unittest discover -s tests -v
```

Tes memakai SQLite sementara dan tidak membuka kamera, memuat YOLO, atau mengubah database pengguna. Notebook juga dapat dijalankan di Colab untuk memeriksa training menyeluruh; dependensi training dipasang oleh sel pertama, terpisah dari dependensi web.

## Rancangan migrasi web

Tahap frontend **Next.js (React + TypeScript)** sudah diimplementasikan di `apps/web` dengan backend Flask. Backend belum dipindahkan ke FastAPI, database/perangkat tetap pada Python, dan model prediksi sensor belum dihubungkan. Dashboard Flask lama telah dihapus.

- [Arsitektur dan struktur folder](docs/ARCHITECTURE.md): tahapan migrasi dan struktur README yang disarankan.
- [Aturan pengembangan](docs/RULES.md): data, model, kode, dan pengujian.
- [Desain halaman](docs/DESIGN.md): navigasi, komponen, palet, serta status data.

## Catatan

- Jika `sounddevice` atau perangkat input audio tidak tersedia, fitur mikrofon akan nonaktif; fungsi dashboard lainnya tetap dapat digunakan.
- Data lingkungan memakai nilai demo sampai server menerima POST dari ESP32 pada endpoint `/api/scd40`.
- Proyek ini menyediakan notebook `SmartOffice_Colab_Training_YOLOv11.ipynb` dan `SmartOffice_Colab_Analisis.ipynb` untuk alur pelatihan/analisis.
- Informasi lisensi komponen pihak ketiga tersedia di `THIRD_PARTY_NOTICES.txt`.
