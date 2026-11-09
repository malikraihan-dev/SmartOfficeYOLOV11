# Aturan pengembangan yang disarankan

Dokumen panduan tim; bukan konfigurasi otomatis alat atau framework.

## Data dan model

1. Pisahkan `scd40` dari `synthetic`. Nilai demo dashboard tidak boleh masuk dataset asli.
2. Cantumkan satuan: CO₂ ppm, suhu °C, kelembapan %. Timestamp ISO 8601 berzona waktu; simpan UTC, tampilkan lokal.
3. Saat ini satu sensor/satu ruangan. Tambahkan `device_id` dan `room_id` sebelum menerima beberapa sensor pada dataset yang sama.
4. Gunakan split kronologis dengan label tidak melewati batas split. Fitur tidak membaca masa depan. Jangan membuang tanggal sebelum membuat lag.
5. Laporkan MAE/RMSE dalam satuan sensor, R², baseline, horizon, sumber data dan rentang test. Persentase dalam toleransi harus menyertakan ambangnya.
6. Jangan menyebut skor dummy sebagai akurasi ruangan atau kalibrasi sensor. Prediksi masa depan berbeda dari klasifikasi kenyamanan ruangan.
7. Model Python dan YOLO terpisah. Simpan versi library, fitur, horizon, zona waktu, metrik, dan asal data bersama model. Tidak ada pemuatan joblib unggahan publik secara otomatis.

## Kode dan UI

- TypeScript untuk frontend baru; komponen mengikuti fitur, bukan satu halaman raksasa.
- Akses database dan perangkat hanya di backend Python. Jangan memasukkan credential ke kode browser.
- Reuse komponen, token warna, dan kontrak API. Label tombol memakai Bahasa Indonesia.
- Setiap request memiliki loading/error/empty state. Polling tidak tumpang tindih dan berhenti saat komponen dilepas.
- Status data harus memakai teks, bukan warna saja. Prediksi belum tersedia ditampilkan sebagai `--` dengan alasan.
- Fitur hapus, impor dan aktivasi model perlu alur eksplisit. Jangan memperluas tombol penghapusan lama secara diam-diam.
- Dataset asli, database, snapshot dan credential tidak masuk repository. Dokumentasikan lokasi backup serta retensi saat deployment disiapkan.

## Pemeriksaan perubahan

- Tes API dengan database sementara; jangan menyalakan kamera atau menghapus data pengguna saat tes.
- Uji JSON invalid, batas nilai, sumber sintetis, CSV round-trip, kondisi data kosong, dan koneksi terputus.
- Jalankan notebook menyeluruh pada dummy; periksa bahwa test tidak dipakai memilih model.
- Periksa tampilan desktop/ponsel, keyboard, nama aksesibel, dan overflow tabel.
- Perbarui README/kontrak apabila route, format data, atau cara menjalankan berubah.
