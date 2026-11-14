# Desain halaman dan struktur informasi

## Navigasi Next.js yang diimplementasikan

| Halaman | Isi utama |
| --- | --- |
| Beranda publik | Hero SaaS, pratinjau demo berlabel, fitur, alur data, pricing belum ditetapkan, dan CTA login |
| Login admin | Form login nyata, bantuan setup akun, dan pratinjau produk ilustratif |
| Monitoring | Kamera, okupansi, suhu/CO₂/kelembapan, status sumber, waktu pembaruan |
| Dataset sensor | Jumlah baris, periode data, tabel, unduhan asli/dummy, panduan Colab |
| Dataset kamera | Foto, anotasi, evaluasi deteksi dan ekspor |
| Model | Jenis model, versi, sumber training, horizon dan metrik; aktivasi setelah validasi |
| Pengaturan | Koneksi perangkat, zona kerja, ambang dan konfigurasi |

Frontend: `/` (landing publik), `/login`, `/monitoring`, `/datasets/sensors`, `/datasets/vision`, `/models`, dan `/settings` pada port 3000. Dashboard Flask lama telah dihapus; route root Flask mengarahkan ke login Next.js.

Implementasi memakai sistem SaaS glassmorphism yang konsisten pada beranda, login, dan seluruh halaman admin. Token dasar berada di `apps/web/src/styles/tokens.css`, aturan layout di `console.css`, dan tema SaaS di `saas.css`. Ikon garis Lucide dan angka tabular digunakan bersama. Route/root layout memakai Server Component; polling dan kontrol memakai Client Component per fitur. Menu ponsel mendukung Escape, focus trap, dan pengembalian fokus. Tombol hapus tetap memakai konfirmasi ketik HAPUS.

Sidebar desktop tetap ringkas 84 px dan terbuka 268 px saat kursor mendekati tepi, menutup setelah jeda 240 ms saat menjauh tanpa menggeser konten. Login memakai dua panel desktop, satu kolom ponsel, field berlabel, tampil/sembunyikan sandi, loading dan pesan error berfokus. Topbar menampilkan akun admin dan tombol keluar.

## Gaya visual

- Palet baru sesuai permintaan SaaS: teal `#166a78`, biru muda dan mint sebagai aksen.
- Teks utama `#173440`, latar `#f2f7fa`, kartu putih transparan dengan garis halus, sidebar navy–teal `#153541`.
- Glassmorphism memakai permukaan putih dengan opacity tinggi dan blur 14–18 px; fallback putih polos tersedia bila backdrop-filter tidak didukung. Gradasi lembut berfungsi sebagai latar, bukan penanda status.
- Gunakan ikon SVG garis seragam, radius kartu 16–20 px, jarak antarkartu 16–24 px.
- Teks angka menggunakan tabular numerals. Tampilkan satuan dekat angka.

## Komponen yang dapat dipakai ulang

### Penyesuaian monitoring, 10 November 2026

Monitoring menampilkan ringkasan metrik dan kamera sebelum panel riwayat sensor agar kondisi ruang lebih cepat ditemukan. Panel dan kartu metrik di halaman ini memakai latar putih solid; kartu grafik sensor memakai teal solid. Blur tetap terbatas pada shell navigasi, sementara halaman lain mengikuti tema sebelumnya. Metadata waktu dan status memakai 12–13 px, deskripsi panel 14 px, serta judul grafik 16 px agar lebih mudah dibaca. Aturan dibatasi oleh `.monitoring-page`.

OfficeShell, PageHeader, MetricCard, SourceBadge, TimestampLabel, SensorTable,
DatasetDownloadActions, EmptyState, ConnectionNotice, TrainingSteps, ModelStatusCard.

Komponen SaaS tambahan: PublicHeader, ProductPreview, TrendChart, dan LiveTelemetry. ProductPreview pada beranda/login selalu berlabel DEMO · ILUSTRASI dan tidak mengakses API privat. LiveTelemetry mengambil 12 baris SCD40 terbaru dari API terautentikasi, menampilkan urutan waktu, memilih CO₂/suhu, dan mengikuti jeda polling. Grafik tidak membuat data ketika riwayat kosong.

Pricing pada beranda menjelaskan aplikasi lokal, kebutuhan perangkat, dan pengembangan lanjut. Harga aplikasi belum ditetapkan, biaya perangkat menyesuaikan alat, dan fitur lanjutan belum tersedia. Tidak ada checkout, klaim pelanggan, sertifikasi, atau harga buatan. Badge kepercayaan menjelaskan sifat sistem yang sudah diimplementasikan.

## Perilaku dataset

Monitoring memiliki strip status kamera, SCD40 dan audio. Umur frame/pembacaan dihitung dari timestamp sumber, terpisah dari waktu pemeriksaan server; audio hanya menyatakan ketersediaan karena API belum memberi timestamp segmen. Penghitung umur bukan live-region agar tidak mengganggu pembaca layar setiap detik.

Grafik sensor menyediakan 12 terbaru, 1 jam, 24 jam dan 7 hari; rentang berbatas maksimum 200 pembacaan terbaru, bukan agregasi seluruh periode. Backend menerapkan parameter `period`, `from` dan `to` dengan query terparameterisasi. Filter tanggal dataset memakai tengah malam zona browser, mengubahnya ke ISO UTC, dan menerapkan akhir rentang eksklusif pada hari berikutnya. Ringkasan, tabel dan ekspor CSV memakai rentang identik. Data filter sebelumnya dikosongkan ketika URL polling berubah.

Gambar evaluasi kamera dibuka dalam dialog native dengan tombol tutup, Escape dan pengembalian fokus. Pengaturan deteksi dan audio menunjukkan perubahan belum disimpan berdasarkan nilai terakhir yang berhasil dikirim; kegagalan menyimpan tidak menghapus penanda. Polling tidak menimpa edit pengguna.

Ringkasan mengambil data asli yang tersimpan, bukan angka buatan. Empty state menjelaskan bahwa
ESP32 harus mengirim data. Unduh CSV asli nonaktif bila belum ada baris atau API gagal.
Dummy diberi nama yang eksplisit. Tabel menampilkan 12 data terbaru, sementara ekspor mencakup
seluruh riwayat. Menambah pagination/filter tanggal merupakan tahap berikutnya bila diperlukan.

## Aksesibilitas dan responsivitas

Desktop: tabel dan langkah training dua kolom. Ponsel: satu kolom; tabel dapat digeser tanpa
menggeser seluruh halaman. Gunakan judul, label kolom, focus ring, tombol native, dan pesan error
yang bisa dibaca pembaca layar. Jangan mengumumkan setiap polling sebagai live-region agar
pembaca layar tidak terus terganggu.

## Status yang wajib berbeda

- LIVE: pembacaan sensor baru tersedia.
- DEMO: simulasi, bukan pembacaan alat.
- TERPUTUS/kedaluwarsa: status saat ini tidak dapat dipercaya.
- Riwayat tersimpan: data historis ada, tidak menyatakan perangkat sedang online.
- Model belum dihubungkan: tidak menampilkan prediksi atau skor palsu.

Pada tahap integrasi model, tampilkan waktu pengamatan, waktu target prediksi, versi model dan
satuan. Jangan mengubah batas CO₂/suhu menjadi klaim nyaman/aman tanpa kriteria yang disepakati.
