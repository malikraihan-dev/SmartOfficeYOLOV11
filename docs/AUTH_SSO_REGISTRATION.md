# Rancangan Google SSO dan pendaftaran pengguna

Tanggal: 11 November 2026. Status: **rancangan sebelum implementasi**.

Keputusan pengguna: dokumentasikan arsitektur dan alur di folder `docs`; semua pengguna baru **menunggu persetujuan admin**. Dokumen ini tidak mengaktifkan SSO, membuat akun Google Cloud, mengubah database, atau mengganti login yang sedang berjalan. Perincian teknis berikut merupakan usulan implementasi.

## 1. Kondisi saat ini

- `admin_auth.py` memiliki `AdminStore`, tabel `admins`, `admin_sessions`, dan `login_attempts` dalam `instance/admin_auth.db`.
- Akun dibuat melalui `manage_admin.py`; belum ada register publik atau email akun.
- Login memakai username/password, hash scrypt, cookie HttpOnly `smartoffice_admin`, sesi 8 jam, serta CSRF untuk mutasi.
- `apps/web/src/lib/session.ts` memeriksa sesi melalui Flask. Respons sesi saat ini selalu menyatakan peran `admin`.
- Next.js meneruskan `/api/*` ke Flask; database sensor dan perangkat tetap dimiliki backend Python.

Detail perilaku aktif ada di [AUTH.md](AUTH.md). Dokumen tersebut tetap menjadi acuan untuk menjalankan versi sekarang.

## 2. Cakupan dan keputusan akses

Tambahkan masuk/daftar dengan Google, register email/password, verifikasi email, pemulihan password, halaman menunggu persetujuan, dan pengelolaan pendaftaran oleh admin. Login admin lokal dipertahankan untuk akses operasional.

| Status akun | Akses |
| --- | --- |
| `unverified` | Verifikasi email, kirim ulang verifikasi, logout |
| `pending` | Melihat status pendaftaran dan logout |
| `active` | Sesuai peran `user` atau `admin` |
| `rejected` | Melihat pendaftaran ditolak dan logout |
| `disabled` | Sesi dicabut; login ditolak |

Peran dan status merupakan dua hal berbeda. Pendaftaran publik selalu menghasilkan peran `user`; isian `role`/`status` dari klien tidak boleh menentukan hak akses. Persetujuan admin mengubah status menjadi `active`, bukan menaikkan peran.

Usulan akses `user` aktif: membaca monitoring dan ringkasan sensor pada instalasi bersama yang sama. Video langsung, gambar, ekspor dataset, pengambilan snapshot, pelabelan, pengaturan perangkat, dan penghapusan tetap khusus admin pada tahap pertama. Pisahkan payload status bila memuat konfigurasi privat. Perluasan akses dapat ditetapkan kemudian; tahap ini belum mendukung organisasi atau isolasi banyak kantor.

Backend memeriksa status/peran pada setiap endpoint, termasuk URL file dan video. Menyembunyikan menu bukan kontrol akses. Akun pending yang sudah terautentikasi tetap menerima 403 saat mencoba mengakses data kantor.

## 3. Arsitektur yang diusulkan

```text
Browser -> Next.js (halaman + proxy satu origin) -> Flask auth -> database akun
Browser -> Google -> callback lewat origin Next.js -> Flask -> Google token endpoint
Flask -> layanan email -> tautan verifikasi/pemulihan -> Browser
Admin -> halaman pengguna -> Flask pemeriksa peran -> persetujuan + audit
```

Flask menjadi satu-satunya penerbit sesi aplikasi untuk kedua metode login. Next.js membaca sesi untuk redirect dan tampilan. Token Google tidak menjadi cookie sesi aplikasi dan tidak disimpan di localStorage. Logout mencabut sesi Smart Office, bukan sesi Google.

Struktur target, seluruh berkas baru di bawah ini masih rencana:

```text
auth/
  __init__.py           # registrasi route dan middleware
  store.py             # transaksi akun, identitas, sesi
  routes.py            # login, register, status, logout
  google.py            # OIDC dan validasi callback
  permissions.py       # pemeriksaan status dan peran
  email.py             # pengiriman verifikasi dan pemulihan
  tokens.py            # token sekali pakai
  admin.py             # daftar pendaftaran dan keputusan admin
migrations/auth/       # migrasi versi database akun
apps/web/src/
  app/register/page.tsx
  app/verify-email/page.tsx
  app/forgot-password/page.tsx
  app/reset-password/page.tsx
  app/account/pending/page.tsx
  app/(office)/users/page.tsx
  features/auth/       # perluas login-form, tambah form dan status akun
  features/users/      # daftar pending dan tindakan admin
  lib/session.ts       # requireSession, requireActiveUser, requireAdmin
tests/                 # unit/integrasi auth tanpa perangkat
apps/web/tests/        # alur browser dengan backend fixture
```

`app.py` tetap menjadi entry point. `admin_auth.py` menjadi lapisan kompatibilitas selama pemindahan; `manage_admin.py` memakai store baru setelah migrasi. Tidak perlu memindahkan seluruh backend atau mengganti framework untuk fitur ini.

## 4. Struktur data

Gunakan database autentikasi yang sama, terpisah dari `smartoffice.db`, dengan migrasi bernomor dan transaksi. Aktifkan foreign key pada setiap koneksi SQLite.

| Tabel usulan | Kolom inti dan batasan |
| --- | --- |
| `users` | `id`, `username` unik nullable untuk admin lama, `email` unik nullable untuk admin lama, `display_name`, `password_hash` nullable, `email_verified_at`, `role`, `status`, `created_at`, `updated_at`, `approved_by`, `approved_at`; CHECK role/status |
| `auth_identities` | `id`, `user_id`, `provider`, `subject`, `created_at`; UNIQUE(provider, subject), UNIQUE(user_id, provider) |
| `sessions` | `token_hash` unik, `user_id`, `csrf_token`, `expires_at`, `created_at` |
| `oauth_transactions` | hash state, hash pengikat browser, nonce, masa berlaku, tujuan internal; transaksi hanya dapat dikonsumsi sekali |
| `account_tokens` | hash token, `user_id`, tujuan verify/reset, masa berlaku, waktu digunakan |
| `auth_audit_events` | pelaku, akun sasaran, tindakan, waktu, hasil; tanpa password/token |
| `auth_schema_versions` | nomor migrasi dan waktu penerapan |

Identitas Google menggunakan pasangan provider dan `sub`, bukan email sebagai identifier permanen. Email dinormalisasi konsisten untuk pencarian/keunikan; jangan menghapus titik atau bagian `+tag`. Konflik akun ditangani eksplisit, bukan dengan penggabungan otomatis. Simpan timestamp UTC.

Status/peran dibaca dari akun terbaru saat memvalidasi sesi; jangan membekukan izin di dalam cookie. Penonaktifan mencabut semua sesi. Lindungi admin aktif terakhir agar tidak dapat dinonaktifkan melalui halaman pengelolaan.

## 5. Alur Google SSO

1. Tombol masuk/daftar Google memulai transaksi di Flask.
2. Backend membuat state dan nonce acak dengan masa berlaku 10 menit, serta mengikat transaksi ke cookie sementara HttpOnly, SameSite=Lax. Redirect hanya menuju provider yang telah dikonfigurasi.
3. Google meminta persetujuan untuk scope `openid email profile`. Tidak meminta akses Gmail, Drive, atau refresh token.
4. Callback memeriksa state, pengikat browser, masa berlaku, dan penggunaan ulang. Backend menukar authorization code, lalu memvalidasi tanda tangan ID token, issuer, audience, expiry, dan nonce memakai pustaka OIDC yang terpelihara. Wajib `email_verified=true` untuk jalur pendaftaran ini.
5. Jika identitas sudah dikenal, gunakan akun terkait. Akun baru dibuat atomik sebagai `user/pending` dan dicatat di audit. Akun disabled/rejected tidak diaktifkan kembali oleh callback.
6. Terbitkan sesi aplikasi baru. Akun pending menuju `/account/pending`; akun aktif menuju halaman yang diizinkan.

Email yang sama dengan akun lokal tidak otomatis ditautkan. Pengguna harus masuk lewat metode lama lalu melakukan penautan terpisah dengan autentikasi ulang; penautan bukan bagian tahap awal. Akun admin lama tidak memperoleh identitas Google hanya karena email/nama cocok.

Jika pengguna membatalkan Google, transaksi kedaluwarsa, atau provider gagal, tampilkan pesan yang dapat dicoba ulang tanpa membuat akun setengah jadi. Batasi tujuan kembali ke path internal yang diizinkan; jangan menerima URL redirect bebas.

Kontrak OIDC, penggunaan state/nonce, dan validasi identitas mengikuti [dokumentasi resmi Google OpenID Connect](https://developers.google.com/identity/openid-connect/openid-connect). Masa berlaku transaksi, kebijakan persetujuan, dan struktur database adalah keputusan rancangan proyek.

## 6. Register email/password dan persetujuan

1. Pengguna mengisi nama, email, password, dan konfirmasi password. Pertahankan kebijakan panjang 12–128 karakter dan hash scrypt yang ada.
2. Backend memvalidasi, membatasi percobaan, lalu membuat akun `unverified`. Respons pendaftaran tidak membocorkan apakah email sudah ada.
3. Kirim tautan verifikasi sekali pakai (usulan berlaku 24 jam). Halaman meminta konfirmasi eksplisit melalui POST agar pemindai tautan email tidak mengonsumsi token lewat GET.
4. Verifikasi berhasil mengubah `unverified` menjadi `pending`. Email Google yang valid melewati langkah email ini, tetapi tetap menunggu admin.
5. Admin melihat daftar pending, memilih setujui/tolak, dan dapat menambahkan alasan. Mutasi wajib sesi admin aktif dan CSRF; catat pelaku, sasaran, serta waktu keputusan.
6. Pengguna pending dapat memeriksa ulang status. Persetujuan membuka akses `user`; penolakan menampilkan status yang sesuai. Notifikasi email keputusan dapat dikirim, tetapi status database tetap sumber kebenaran bila pengiriman gagal.

Pemulihan password: respons generik, token sekali pakai (usulan 30 menit), hash token di database, pembatasan permintaan, dan pencabutan semua sesi setelah reset. Akun Google saja tidak diberi password diam-diam oleh endpoint reset. Kegagalan pengiriman email menyediakan kirim ulang dengan jeda; tidak mengaktifkan akun otomatis.

## 7. Kontrak endpoint usulan

Semua route berikut belum tersedia kecuali session/login/logout versi lama.

| Endpoint | Akses / perilaku |
| --- | --- |
| `GET /api/auth/providers` | Publik; metode yang tersedia, tanpa secret |
| `POST /api/auth/register` | Publik; JSON dan pemeriksaan origin; 202 generik |
| `POST /api/auth/login` | Pertahankan admin username; tambahkan email; status akun dikembalikan |
| `GET /api/auth/google/start` | Memulai transaksi OAuth |
| `GET /api/auth/google/callback` | Validasi transaksi dan redirect internal |
| `POST /api/auth/email/verify` | Token sekali pakai; bukan sesi admin |
| `POST /api/auth/email/resend` | Respons generik, rate limit |
| `POST /api/auth/password/forgot` | Respons generik, rate limit |
| `POST /api/auth/password/reset` | Token sekali pakai dan password baru |
| `GET /api/auth/session` | Identitas, role, status, CSRF; no-store |
| `POST /api/auth/logout` | Semua status dengan sesi valid dan CSRF |
| `GET /api/admin/users?status=pending&cursor=...` | Admin; daftar berhalaman |
| `POST /api/admin/users/<id>/approve` | Admin + CSRF; pending menjadi active |
| `POST /api/admin/users/<id>/reject` | Admin + CSRF; pending menjadi rejected |
| `POST /api/admin/users/<id>/disable` | Admin + CSRF; cabut seluruh sesi |

Usulan respons sesi: `{authenticated, configured, user:{id, username, display_name, email, role, status}, csrf_token}`. `configured` tetap menunjukkan adanya admin aktif, bukan sekadar adanya pendaftaran. Pertahankan `username` kompatibel selama pembaruan shell frontend. 401 untuk sesi tidak valid, 403 untuk status/peran tidak memenuhi, 409 untuk konflik transisi admin, 429 untuk batas percobaan.

Middleware menggunakan daftar endpoint publik eksplisit. Jangan mengecualikan seluruh `/api/auth/*` dari proteksi secara umum. Pisahkan validasi sesi dari syarat akun aktif agar pending tetap bisa logout dan membaca statusnya. Ingest ESP32 mempertahankan autentikasi perangkat yang terpisah.

## 8. Konfigurasi yang dibutuhkan saat implementasi

| Variabel usulan pada backend | Kegunaan |
| --- | --- |
| `SMARTOFFICE_GOOGLE_CLIENT_ID` | OAuth client bertipe Web application |
| `SMARTOFFICE_GOOGLE_CLIENT_SECRET` | Secret backend, tidak masuk repo/browser |
| `SMARTOFFICE_GOOGLE_REDIRECT_URI` | URL callback absolut yang didaftarkan persis di Google |
| `SMARTOFFICE_PUBLIC_ORIGIN` | Satu origin kanonis untuk callback dan tautan email |
| `SMARTOFFICE_REGISTRATION_ENABLED` | Sakelar pendaftaran baru |
| `SMARTOFFICE_SMTP_HOST/PORT/USER/PASSWORD` | Konfigurasi layanan email dan TLS |
| `SMARTOFFICE_EMAIL_FROM` | Pengirim terverifikasi pada layanan email |

Pertahankan `SMARTOFFICE_AUTH_DB`, `SMARTOFFICE_WEB_ORIGIN`, dan `SMARTOFFICE_COOKIE_SECURE`. Variabel Python tidak otomatis dibaca dari `.env.local` Next.js. Buat contoh konfigurasi tanpa nilai rahasia ketika implementasi dimulai.

Callback lokal yang direncanakan: `http://127.0.0.1:3000/api/auth/google/callback`, melalui proxy frontend. Gunakan host yang sama selama login; jangan berpindah antara localhost dan 127.0.0.1. Produksi menggunakan origin HTTPS dan cookie Secure. Daftarkan setiap redirect URI yang digunakan secara tepat sesuai [panduan Google](https://developers.google.com/identity/openid-connect/openid-connect).

Siapkan project Google Cloud, branding/consent, audience dan test users sesuai lingkungan. Kredensial nyata dan penyedia email belum diperlukan untuk penulisan dokumen ini. Pilih serta pin pustaka OIDC ketika implementasi, sesudah memeriksa kompatibilitas Python proyek.

## 9. Migrasi dan urutan implementasi

1. Tambahkan tes karakterisasi login lama, matriks izin endpoint, serta migrasi menggunakan database sementara.
2. Cadangkan database akun secara konsisten ketika layanan dihentikan. Migrasikan admin lama menjadi `admin/active`, mempertahankan username dan hash tanpa membuat email palsu. Cabut sesi lama; pengguna login kembali. Jangan menyentuh database sensor.
3. Implementasikan store, sesi bersama, status/peran, halaman status, dan persetujuan admin terlebih dahulu.
4. Tambahkan Google SSO dengan callback pengujian; uji manual akun Google pada lingkungan lokal terkonfigurasi.
5. Tambahkan register email, verifikasi, dan reset setelah layanan email siap. Pendaftaran tetap nonaktif jika dependensi pengiriman belum siap.
6. Perbarui UI login/register, fixture browser, panduan setup dan AUTH.md agar membedakan fitur aktif dari rencana.
7. Aktifkan pendaftaran setelah seluruh kriteria lolos. Rollback: matikan pendaftaran/Google, hentikan layanan, pulihkan kode serta backup database akun yang cocok. Perubahan akun setelah backup tidak ikut pulih; jangan melakukan rollback database tanpa memperhitungkannya.

Migrasi harus dapat dijalankan ulang dengan aman, memeriksa versi skema, dan berhenti tanpa perubahan parsial bila gagal. Cookie `smartoffice_admin` dapat dipertahankan sementara untuk kompatibilitas; namanya tidak boleh dijadikan bukti peran admin.

## 10. Kriteria penerimaan

- Admin lama tetap dapat login dan mengelola perangkat setelah migrasi; tidak ada admin otomatis dari pendaftaran.
- Google baru dan email terverifikasi berakhir sebagai pending; API data, unduhan, video, dan mutasi menolak aksesnya.
- Persetujuan/tolak hanya dapat dilakukan admin aktif; akun user aktif tidak dapat mengubah pengaturan atau menghapus data.
- Callback menolak state/nonce salah, replay, transaksi kedaluwarsa, issuer/audience/signature tidak valid, serta email tidak terverifikasi. Uji konflik identitas dan dua pendaftaran bersamaan.
- Token email kedaluwarsa/dipakai ulang ditolak; password reset dan disable mencabut sesi. CSRF dan rate limit berlaku pada jalur yang sesuai.
- Register/login menangani provider batal, jaringan gagal, email gagal terkirim, akun pending/rejected/disabled, dan sesi habis tanpa loop redirect.
- Tes migrasi mencakup database kosong, admin lama, rerun, kegagalan/rollback, dan tidak berubahnya database sensor.
- Tes backend/browser memakai database sementara dan provider/email fixture; tes tidak membuka kamera atau mengirim email nyata. Uji Google nyata dilakukan terpisah setelah kredensial tersedia.

Hal yang masih perlu ditetapkan sebelum aktivasi: domain produksi, audience Google (publik atau organisasi), penyedia email, dan persetujuan atas batas akses `user` yang diusulkan. Kebijakan wajib persetujuan admin sudah ditetapkan oleh pengguna.
