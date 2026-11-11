# Satu perintah untuk pengembangan lokal

Dari root `SmartOffice_YOLOv11` atau `apps/web`, jalankan `npm run dev`. Launcher memulai Python `app.py` pada port 5000 dan Next.js pada port 3000. Windows memakai compiler WebAssembly yang sudah tersedia di dependensi proyek. Tidak ada dependensi Node baru.

Setup satu kali: pasang dependensi Python (`python -m pip install -r requirements.txt`), frontend (`npm --prefix apps/web ci` dari root), dan akun admin (`python manage_admin.py`). Launcher tidak menginstal paket atau membuat akun.

Python dipilih dari `SMARTOFFICE_PYTHON`, virtual environment aktif, `.venv` proyek, atau `python` di PATH. Interpreter khusus harus berupa executable/path, tanpa argumen shell. Backend selalu dijalankan dengan working directory root agar model, database dan aset memakai lokasi yang benar.

`npm run dev -- --port 3001` memilih port frontend lain dan menyesuaikan origin login Python. Port backend tetap 5000. Launcher selalu memakai API lokal, termasuk ketika `.env.local` menunjuk backend lain. Untuk backend yang sudah berjalan atau backend eksternal, gunakan `npm run dev:web` atau `npm run dev:web:compat` dari `apps/web`. `run_frontend.bat` memakai jalur frontend saja. Produksi tetap memakai build/start dan backend terkelola terpisah.

Ctrl+C menghentikan layanan yang dibuat launcher beserta turunannya. Jika salah satu layanan gagal, layanan lainnya ikut dihentikan dan launcher mengembalikan status gagal. Sebelum startup, kedua port diperiksa. Server lama atau proses lain tidak dihentikan otomatis; hentikan server lama lewat terminalnya sebelum memakai launcher. Layanan tidak memakai autorestart; setelah mengubah backend Python, hentikan dan jalankan kembali launcher.

## Verifikasi 11 November 2026

- Empat tes launcher lulus: penghentian anak dan turunan, kegagalan satu layanan, executable tidak ditemukan, dan port terpakai tanpa menghentikan pemiliknya.
- Uji `npm run dev` nyata berhasil menjalankan Next.js dan Flask. Login frontend, endpoint sesi backend, dan endpoint sesi melalui proxy masing-masing HTTP 200. Tidak memasukkan kredensial atau membuka kamera untuk uji ini.
- Dua tes autentikasi Playwright terisolasi lulus (akses anonim, login, reload dan logout). Konfigurasi tes memakai `dev:web:compat` dan fixture 5051, sehingga tidak menyalakan backend perangkat kedua.
- Pemeriksaan sintaks kedua script dan `git diff --check` lulus.

Percobaan awal dalam sandbox menolak proses turunan Next.js; proses uji tersebut dibersihkan sebelum pengulangan di luar sandbox. Uji sukses dilakukan dengan izin proses yang cukup. Server pengembangan lokal tidak ditujukan sebagai pengelola layanan produksi.
