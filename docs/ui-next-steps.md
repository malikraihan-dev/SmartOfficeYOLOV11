# Usulan UI berikutnya

Pembaruan: strip status perangkat, filter periode grafik/tanggal dataset sensor, dialog gambar evaluasi, serta penanda pengaturan belum disimpan telah diimplementasikan. Pagination, penataan ulang panel ponsel dan pembanding model tetap usulan. Prioritaskan manfaat operator dan data yang tersedia, bukan jumlah efek visual.

1. **Monitoring:** satukan status kamera, sensor, audio dan umur pembacaan dalam strip ringkas dekat judul. Bedakan kondisi perangkat dan pembacaan terakhir; kamera terputus tidak berarti riwayat hilang.
2. **Grafik:** filter periode dengan sumber historis nyata. API saat ini membatasi grafik ke 12 baris; tambahkan dukungan rentang di backend sebelum menampilkan pilihan 1 jam/24 jam/7 hari.
3. **Monitoring di ponsel:** pindahkan aktivitas terkini sesudah kamera, lalu tampilkan riwayat dan snapshot dalam bagian yang dapat dibuka. Pertahankan akses keyboard dan kondisi kosong yang jelas.
4. **Dataset sensor:** filter tanggal, pagination, jumlah hasil dan status filter; unduhan harus menjelaskan apakah mencakup semua data atau hasil filter.
5. **Dataset kamera:** pratinjau gambar dalam dialog yang dapat ditutup dengan Escape, tombol gambar sebelumnya/berikutnya dan pengembalian fokus. Jangan mengubah berkas sumber.
6. **Model:** tampilkan versi aktif, status validasi dan pembanding metrik hanya bila artefak serta hasil evaluasi nyata tersedia.
7. **Pengaturan:** tandai perubahan belum disimpan dan tampilkan ringkasan konfigurasi yang benar-benar berhasil diterapkan. Pertahankan konfirmasi hapus yang sudah ada.

Login dikembalikan ke pratinjau produk sebelumnya sesuai permintaan pengguna. Hindari animasi baru pada setiap kartu dashboard: perhatian operator sebaiknya mengikuti perubahan status nyata.
