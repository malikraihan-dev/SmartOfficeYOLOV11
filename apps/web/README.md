# Smart Office frontend

Next.js App Router, React, TypeScript dan CSS tokens. Tidak mengakses SQLite, model, kamera atau mikrofon secara langsung. Backend Flask yang ada tetap menjadi pemilik data/perangkat; tidak ada migrasi database.

## Jalankan

1. Dari root `SmartOffice_YOLOv11`, buat akun sekali dengan `python manage_admin.py`, lalu jalankan `python app.py`.
2. Pada terminal kedua di folder ini: `npm ci`, lalu `npm run dev`.
3. Buka http://127.0.0.1:3000/login dan masuk dengan akun yang dibuat. API default http://127.0.0.1:5000.

Jika compiler native SWC diblokir Application Control Windows, gunakan `npm run dev:compat`. Runner ini memilih `@next/swc-wasm-nodejs` melalui override internal `NEXT_TEST_WASM_DIR`; dependensi dikunci oleh lockfile. Gunakan runner normal jika compiler native didukung. Periksa kompatibilitas override setiap memperbarui Next.js.

Produksi lokal: `npm run build` lalu `npm start`. Jalur WebAssembly: `npm run build:compat` lalu `npm start`. Konfigurasi backend melalui `.env.local` mengikuti `.env.example`, tanpa prefix NEXT_PUBLIC. Mulai ulang/build ulang setelah mengubah backend karena rewrites disiapkan oleh konfigurasi Next.js.

## Halaman & perilaku

| Route | Fungsi |
| --- | --- |
| `/` | Landing SaaS publik, hero pratinjau demo, fitur, alur data, pricing belum ditetapkan, dan CTA login |
| `/login` | Masuk admin, pesan setup akun dan pemulihan kesalahan login |
| `/monitoring` | Kamera MJPEG, snapshot, okupansi, sumber sensor/audio, objek, tren selama halaman dibuka |
| `/datasets/sensors` | Ringkasan asli, 12 pembacaan terbaru, seluruh CSV asli, dummy terpisah, notebook Colab |
| `/datasets/vision` | Foto asli untuk anotasi, ZIP analisis, ulasan jumlah orang |
| `/models` | Artefak YOLO yang dikonfigurasi dan status model sensor yang belum terhubung |
| `/settings` | Zona & confidence, ambang/kalibrasi audio, label audio manual, penghapusan kamera/audio |

Dashboard Flask, aset UI lama, tautan dan route `/legacy` sudah dihapus. Port 5000 tetap menangani API/perangkat. Halaman di grup `(office)` memverifikasi sesi admin di server sebelum menampilkan shell; backend memeriksa sesi kembali untuk setiap endpoint privat. Lihat [AUTH.md](../../docs/AUTH.md) untuk setup akun, cookie, CSRF, rate limit dan opsi produksi.

Sistem visual SaaS di `src/styles/saas.css` menggunakan token semantik yang sama untuk beranda, login, monitoring, dataset, model dan pengaturan. Kartu kaca memiliki fallback putih dan kontras teks yang tetap jelas. `ProductPreview` publik/login memakai data ilustratif berlabel dan tidak memanggil API privat. `LiveTelemetry` pada monitoring membaca 12 pembacaan tersimpan, diurutkan kronologis, mendukung pilihan CO₂/suhu, serta mengikuti jeda polling status. Riwayat kosong tetap kosong; tidak ada grafik sintetis pada dashboard asli.

Pricing adalah informasi cakupan aplikasi/perangkat/pengembangan, tanpa angka harga atau pembayaran yang diaktifkan. Badge menjelaskan sifat sistem yang diimplementasikan, bukan sertifikasi atau endorsement pihak ketiga.

Sidebar desktop berupa rail 84 px. Kursor dalam jarak 24 px dari rail membuka panel hingga 268 px; keluar lebih dari 24 px dari panel menutupnya setelah jeda 240 ms. Panel melebar di atas konten tanpa memindahkan layout. Fokus keyboard juga membuka panel; Escape menutupnya. Pada ponsel menu dibuka dengan tombol, mendukung focus trap dan pengembalian fokus. Animasi mengikuti reduced-motion.

Polling status 4 detik, dataset/evaluasi 10 detik, timeout 8 detik, no-store, berhenti ketika komponen dilepas, dijeda di tab tersembunyi. Tombol jeda pada monitoring menghentikan polling status; kontrol jeda kamera terpisah. Angka demo ditandai DEMO, pembacaan SCD40 >30 detik ditandai KEDALUWARSA, kegagalan API ditandai TERPUTUS. Riwayat dataset bukan bukti perangkat online. Prediksi tidak diisi sebelum layanan model tersedia.

Form pengaturan hanya diinisialisasi sekali agar polling tidak menimpa suntingan. Zona minimum 10% x 10%. Pengaturan server saat ini tidak persisten setelah restart. Penghapusan memakai dialog native dan konfirmasi ketik HAPUS; tabel sensor tidak dihapus. Unduhan memiliki loading dan pesan error; ekspor asli nonaktif ketika kosong/offline. Unduhan menggunakan Blob browser; pertimbangkan streaming ke disk pada deployment dengan ekspor sangat besar.

## Verifikasi

```powershell
npm run typecheck
npm run build:compat
npm run test:e2e
```

Tes Playwright membutuhkan Microsoft Edge (`channel: msedge`) dan Python dengan Flask; untuk lingkungan lain ubah channel atau pasang browser Playwright. Tes menyalakan backend fixture pada **5051** dan frontend pada **3100**; keduanya terikat ke loopback dan ditutup sesudah tes. `tests/mock_api.py` menggunakan implementasi autentikasi asli dengan akun/database sementara dan data perangkat fixture. File ini hanya untuk tes. Tidak memuat YOLO, tidak membuka kamera/mikrofon, dan tidak membaca/mengubah database asli.

Cakupan: login/logout asli melalui proxy, cookie HttpOnly, sesi kedaluwarsa, penolakan akses anonim, sidebar kedekatan kursor/tutup otomatis tanpa layout bergeser, menu keyboard/ponsel, demo, data kosong, kedaluwarsa sensor, offline/pemulihan, CSV lewat proxy, kontrol kamera, zona/normalisasi request, persistensi suntingan ketika polling, ulasan vision/audio, dialog hapus, dan overflow pada 320/375/768/1440 px. Kamera fisik/MJPEG berkelanjutan, audio, ESP32, dan pelatihan notebook perlu pemeriksaan perangkat terpisah.

## Proxy produksi

Untuk deployment, gunakan satu origin dengan reverse proxy. Contoh Nginx (sesuaikan host dan port; ini konfigurasi contoh, belum dideploy):

```nginx
location /api/ { proxy_pass http://127.0.0.1:5000; }
location /video_feed {
    proxy_pass http://127.0.0.1:5000;
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 3600s;
}
location /snapshots/ { proxy_pass http://127.0.0.1:5000; }
location /training_data/ { proxy_pass http://127.0.0.1:5000; }
location / { proxy_pass http://127.0.0.1:3000; }
```

Ini prototipe satu sensor/satu ruangan dengan autentikasi admin lokal. Sebelum deployment multi-user tambahkan identitas perangkat/ruang, pengelolaan peran, backup/retensi, HTTPS dengan cookie Secure dan satu pemilik kamera lintas-klien. Atur `SMARTOFFICE_WEB_ORIGIN` pada backend sesuai origin publik untuk login. Generator kamera mengikuti request: jangan membuka beberapa pratinjau kamera sekaligus.
