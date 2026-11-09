# Login admin lokal

## Siapkan akun sekali

Dari root proyek jalankan `python manage_admin.py` atau `setup_admin.bat`. Isi nama pengguna (default nama: admin) dan kata sandi 12–128 karakter; input kata sandi tidak ditampilkan. Tidak ada kata sandi default. Skrip tidak membuka kamera, memuat model, atau mengubah database sensor. Menjalankan kembali dengan nama yang sama mereset hash kata sandi dan mencabut semua sesi akun tersebut.

Jalankan backend dan frontend, lalu buka `http://127.0.0.1:3000/login`. Halaman login tidak menjalankan polling kamera/status. Password manager dan paste didukung. Akun baru hanya dibuat lewat akses terminal server; tidak ada registrasi publik.

## Penyimpanan dan sesi

- Akun dan sesi disimpan di `instance/admin_auth.db`, terpisah dari `smartoffice.db` dan diabaikan version control. `SMARTOFFICE_AUTH_DB` dapat mengubah lokasi file.
- Kata sandi di-hash dengan Werkzeug scrypt. Token sesi acak hanya dikirim lewat cookie `smartoffice_admin` (HttpOnly, SameSite=Lax, Path=/); database menyimpan hash SHA-256 token.
- Sesi kedaluwarsa setelah 8 jam. Logout menghapus cookie dan mencabut sesi di database, sehingga cookie lama tidak dapat dipakai ulang.
- Sebelum halaman admin dirender, Next.js memverifikasi cookie ke backend dengan `no-store`. Backend memeriksa sesi kembali pada setiap akses API, gambar, unduhan, dan video. Mutasi memerlukan `X-CSRF-Token` sesuai sesi.
- Login dibatasi 10 percobaan gagal per alamat selama 15 menit. Di balik proxy lokal, klien dapat berbagi alamat; gunakan pengaturan proxy/rate limiter yang sesuai sebelum deployment lebih luas.

## Kontrak API

| Endpoint | Permintaan / respons |
| --- | --- |
| `GET /api/auth/session` | Publik. `{authenticated:false, configured:boolean}` atau `{authenticated:true, configured:true, user:{username,role:"admin"}, csrf_token}`. Tidak mengembalikan token sesi atau hash kata sandi. |
| `POST /api/auth/login` | JSON `{username,password}`, header `X-SmartOffice-Client: web`. Origin browser harus sesuai daftar yang diizinkan. Berhasil: HTTP 200 + Set-Cookie; salah: 401; belum setup: 503; terlalu banyak: 429 + Retry-After. |
| `POST /api/auth/logout` | Cookie sesi + `X-CSRF-Token`; mencabut sesi. |

API aplikasi, `/video_feed`, `/snapshots/*`, dan `/training_data/*` mengembalikan 401 tanpa sesi. Mutasi tanpa token CSRF valid mengembalikan 403. Respons privat memakai `Cache-Control: no-store`. Frontend mengarahkan sesi tidak valid kembali ke login.

## ESP32 terpisah dari sesi admin

`POST /api/scd40` tetap dapat digunakan firmware yang ada tanpa cookie admin. Secara default autentikasi perangkat belum diaktifkan. Jika variabel `SMARTOFFICE_DEVICE_TOKEN` diatur pada server, firmware harus mengirim header `X-Device-Token` yang cocok. Jangan menyimpan token tersebut dalam source publik. Token ini tidak memberi akses ke dashboard atau endpoint admin.

## Konfigurasi server

Variabel berikut dibaca dari environment proses Python, bukan otomatis dari `.env.local` milik Next.js:

| Variabel | Default / penggunaan |
| --- | --- |
| `SMARTOFFICE_AUTH_DB` | `instance/admin_auth.db` |
| `SMARTOFFICE_WEB_ORIGIN` | Origin login yang diizinkan, pisahkan koma. Default `http://127.0.0.1:3000,http://localhost:3000`. Untuk deployment atur origin publik HTTPS yang tepat. |
| `SMARTOFFICE_COOKIE_SECURE` | Set `1` pada deployment HTTPS. HTTP lokal memakai cookie non-Secure agar pengembangan lokal dapat berjalan. |
| `SMARTOFFICE_DEVICE_TOKEN` | Opsional untuk ingest ESP32. |

SQLite akun perlu backup tersendiri dengan izin file terbatas. Jangan membuka server pengembangan Flask ke internet. Deployment banyak pengguna masih memerlukan HTTPS, proxy tepercaya, retensi/backup, dan pengelolaan peran/perangkat yang lebih lengkap.
