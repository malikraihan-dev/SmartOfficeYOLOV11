# Desain akses dan interaksi SmartOffice

File utama: `SmartOffice-Dashboard.figcraft`, halaman **Akses & Interaksi**.
Sumber vektor: `SmartOffice-Auth-Motion.svg`.
Tambahan: halaman **Riwayat, Akses & Gerakan**, sumber `SmartOffice-Access-States.svg`.
Pratinjau: buka `interaction-preview.html` di browser, lalu pilih **Buka pratinjau dashboard**.

## Cakupan

- Login email/kata sandi, opsi Google SSO, lupa kata sandi, serta tautan register.
- Register dengan nama, email, kata sandi, opsi Google, dan status verifikasi email/izin pengelola.
- Sidebar desktop terbuka 232 px dan tertutup 80 px; transisi 220 ms ease-out, label 120 ms.
- Drawer ponsel 280 px, overlay, penutupan dengan Escape, serta navigasi keyboard.
- Pengambilan foto: menyimpan, berhasil, gagal, coba lagi, dan riwayat notifikasi.
- Dialog logout dengan fokus awal Batalkan, Escape untuk batal, dan pengembalian fokus.
- Panel riwayat dengan waktu, filter Semua/Foto/Perangkat, status baca, dan aksi lihat dataset/coba lagi.
- Perbandingan tampilan operator/admin: CSV asli nonaktif untuk operator dan tersedia bagi admin.
- Pola label LIVE / DEMO / TERPUTUS dengan asal data dan waktu, terpisah dari riwayat tersimpan.
- Preferensi gerakan: ikuti sistem (default) atau selalu kurangi animasi; perubahan langsung pada mode pengurangan.

Kebijakan akses pada tambahan desain merupakan usulan: operator memantau, mengambil foto,
melihat pratinjau dataset, dan mengunduh dummy; admin juga mengunduh CSV asli serta mengelola akses.
Izin harus ditegakkan backend saat implementasi, bukan hanya pada tombol antarmuka.
Jumlah baris, waktu, nama foto dan nilai pada papan tambahan hanya ilustrasi.
Tambahan ini ada di FigCraft; pratinjau HTML belum diperluas dengan pilihan peran/preferensi gerakan.

FigCraft memuat storyboard dan spesifikasi gerakan sebagai teks serta bentuk yang dapat diedit.
Gerakan berjalan di pratinjau HTML; koneksi prototipe animasi native FigCraft belum dibuat.
Pratinjau tidak mengirim request, membuka perangkat kamera, membuat akun, atau menjalankan OAuth.
Navigasi menu hanya memperagakan pilihan aktif; konten kamera tetap tersedia untuk uji notifikasi.

## Saat diimplementasikan ke aplikasi

Notifikasi berhasil harus muncul setelah backend mengonfirmasi penyimpanan foto. Saat gagal,
beri pesan yang jelas, jangan menganggap foto sudah masuk dataset, dan tawarkan percobaan ulang.
Toast sukses tampil 5 detik, berhenti menghitung saat disentuh pointer atau fokus keyboard;
riwayat menyimpan pesan yang sudah hilang. Notifikasi gagal bertahan sampai ditutup.

Google SSO memerlukan konfigurasi OAuth, callback backend, dan pemeriksaan izin akun sebelum
akses dashboard diberikan. Pendaftaran email memerlukan verifikasi dan alur pemulihan akun.
Logout harus mengakhiri sesi aplikasi di backend; dialog desain tidak melakukan logout Google.

## Saran desain

1. Gunakan Monitoring sebagai halaman awal; kelompokkan tindakan pengelolaan dataset tersendiri.
2. Pertahankan panel riwayat notifikasi agar informasi penyimpanan tidak hilang bersama toast.
3. Beri tooltip menu saat sidebar diciutkan dan gunakan teks status selain warna.
4. Bedakan akses operator dan pengelola pada tahap implementasi, termasuk hak unduh dataset.
5. Uji login, drawer, dialog, fokus keyboard, kontras, dan reduced motion pada ponsel sebelum rilis.

## Pemeriksaan

Papan tambahan sudah diimpor dan diperiksa secara visual di FigCraft, lalu file native disimpan.
SVG lolos parsing XML dan JavaScript pratinjau lolos pemeriksaan sintaks.
Pratinjau browser belum diuji langsung karena konektor browser tidak tersedia pada sesi ini.
