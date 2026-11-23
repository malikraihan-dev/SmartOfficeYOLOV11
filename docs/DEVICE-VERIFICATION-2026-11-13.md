# Perbaikan backend dan verifikasi perangkat

Tanggal: 13 November 2026.

## Perubahan

- camera_worker.py: satu thread produsen kamera/inference untuk semua pembaca MJPEG dalam satu proses backend. Klien lambat melewati frame lama; disconnect klien tidak menghentikan capture. Generator melepas kamera dan menutup kunjungan zona melalui finally. Worker mencoba ulang setelah kegagalan.
- database.py: schema, koneksi, read dan write dikeluarkan dari app.py. admin_auth.py dan sensor_dataset.py tetap terpisah.
- settings_store.py: confidence, zona dan ambang audio tervalidasi disimpan ke tabel runtime_settings. Pengaturan dimuat saat startup. Kegagalan tulis menghasilkan HTTP 503 tanpa mengganti state aktif. Ambang manual yang tersimpan tidak ditimpa kalibrasi otomatis startup; kalibrasi ulang eksplisit juga disimpan.
- Pesan pengaturan dan dokumentasi diperbarui. SMARTOFFICE_DATABASE dan SMARTOFFICE_DATA_DIR memungkinkan diagnosis memakai database serta folder sementara.

## Hasil uji

- 19 tes Python lulus, termasuk satu produsen untuk lima subscriber, capture berlanjut setelah disconnect, cleanup worker, persistensi lintas instance, nilai NaN/Infinity invalid, kegagalan tulis, dan schema idempoten.
- 26 tes browser fixture lulus dalam 1,5 menit. Ini regresi UI/auth/API fixture, bukan pengujian kamera fisik di browser.
- Kamera HP HD Camera berhasil dibuka di luar sandbox: 5 frame dibaca dengan DirectShow.
- Mikrofon berhasil membaca 8.000 sampel pada 8 kHz; RMS sampel -56,43 dBFS. Audio mentah tidak disimpan. Ini uji akses mikrofon, bukan pengujian klasifikasi segmen penuh.
- Backend YOLO asli berhasil dijalankan di luar sandbox dengan database/folder sementara. Dua subscriber masing-masing menerima tiga payload frame dengan ukuran berpasangan sama (48.916, 49.044, 49.581 byte). Status kamera terhubung, worker tanpa error, shutdown selesai.
- Sampel status backend: 34,4 FPS, inference 13,2 ms. Ini bukan benchmark berkelanjutan atau pengukuran latensi kamera-ke-layar.
- Dalam sandbox, PyTorch shm.dll diblokir Windows Application Control dan akses perangkat gagal; pemeriksaan ulang berizin di luar sandbox berhasil. Tidak ada perubahan kebijakan keamanan Windows.
- sensor_updated_at tetap null pada sesi pengujian backend. ESP32/SCD40 nyata belum terverifikasi. Tes ingest database dan browser fixture bukan bukti perangkat fisik terhubung.

## Batas deployment dan tindak lanjut

Gunakan satu proses backend untuk satu kamera fisik; thread worker dibagi antar-klien di proses tersebut. Banyak proses OS memerlukan layanan kamera terpisah. Kamera mulai saat menjalankan app.py dan terus memantau tanpa subscriber; impor WSGI memulai kamera saat subscriber pertama. Audio mengikuti startup app.py seperti sebelumnya.

Untuk menuntaskan uji end-to-end, ESP32 harus mengirim pembacaan SCD40 ke alamat LAN server, lalu dashboard dibuka untuk mengukur waktu kirim, waktu simpan, dan waktu tampil. Latensi sensor-ke-layar, klasifikasi audio penuh, serta video nyata melalui proxy/browser belum diukur. Tidak ada klaim seluruh perangkat telah lulus realtime.
