# Kontrak API dataset SCD40

Implementasi aktif: Flask, satu sensor/satu ruangan. Pembacaan ringkasan, ekspor dan aset memerlukan sesi admin. Ingest perangkat tidak memakai cookie admin; autentikasi perangkat opsional memakai `SMARTOFFICE_DEVICE_TOKEN` dan header `X-Device-Token`. Default ingest tetap kompatibel dengan firmware lama. Lihat [AUTH.md](AUTH.md).
`source=scd40` menandai asal jalur penerimaan, bukan bukti kriptografis bahwa pembacaan berasal dari alat.

## POST /api/scd40

```json
{"co2_ppm":720,"temperature_c":25.4,"humidity_percent":52.3}
```

Tiga nilai wajib berupa angka yang dapat dikonversi dan berada dalam batas pemeriksaan:
CO₂ > 0 sampai 40000 ppm, suhu -40 sampai 125 °C, kelembapan 0 sampai 100%.
Batas ini pemeriksaan input, bukan klaim akurasi sensor. `source` opsional; bila diberikan harus `scd40`.
Payload invalid atau source sintetis menghasilkan HTTP 400 dan tidak ditulis.
HTTP 200 berarti pembacaan sudah disimpan dan status terkini diperbarui.

Server memberi timestamp UTC berzona waktu sampai mikrodetik, berdasarkan waktu penerimaan.
Pembacaan tersimpan mempertahankan presisi input; tampilan status dapat membulatkan.
Tidak ada perekaman historis dari nilai demo `/api/status`.

## GET /api/sensors/dataset?limit=20

`limit` integer 1–200; invalid menghasilkan HTTP 400. Halaman meminta 12 baris terbaru.
Respons: `total_rows`, `first_at`, `last_at`, `source`, `rows`, `forecast_status`,
`horizon_minutes`, `note`. Setiap row memiliki id, timestamp dan tiga nilai sensor beserta source.
Baris diurutkan id terbaru terlebih dahulu. Ringkasan kosong memiliki jumlah 0 dan waktu null. Respons memakai `Cache-Control: no-store`, seperti `/api/status`.
`forecast_status=not_connected` berarti belum ada layanan prediksi aktif. Jumlah data tidak
menyatakan kesiapan training: celah, lama pengamatan dan pembagian waktu diperiksa di notebook.

## GET /api/sensors/export

Mengunduh seluruh riwayat secara berurutan, bukan hanya 12 baris pada tabel.
CSV UTF-8 dengan header:

```csv
timestamp,co2_ppm,temperature_c,humidity_percent,source
2026-11-03T08:00:00.000000+00:00,720.0,25.4,52.3,scd40
```

Contoh baris di atas ilustrasi format. Ekspor kosong hanya berisi header. Tidak mengisi
menit kosong dan tidak mencampur dummy. Notebook mengagregasi data menjadi satu menit.

## Aset training

- `GET /api/sensors/assets/dummy`: CSV dummy 30 hari dengan source synthetic.
- `GET /api/sensors/assets/notebook`: notebook training SCD40.
- Jenis aset lain menghasilkan HTTP 404. Tidak ada unggahan/aktivasi model pada API ini.

## Penyimpanan dan retensi

Tabel `sensor_readings` dibuat saat aplikasi mulai. Data yang diterima setelah pembaruan
dicatat, tanpa backfill. Retensi otomatis dan endpoint penghapusan sensor belum disediakan.
Tombol penghapusan kamera/audio lama tidak menghapus tabel sensor. Backup SQLite dan ekspor
CSV perlu dikelola sesuai penggunaan, khususnya bila ESP32 mengirim setiap lima detik.
