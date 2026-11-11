# Graphify untuk Smart Office

Graphify dipasang khusus proyek dalam `.venv-graphify/`, terpisah dari dependensi aplikasi. Paket resmi adalah `graphifyy`; versi pemasangan awal `0.9.106` dipatok di `requirements-graphify.txt`. Instalasi ini memakai Python 3.12.3.

## Penggunaan dari PowerShell

Jalankan perintah dari root `SmartOffice_YOLOv11`:

```powershell
# Buat peta kode lokal pertama kali atau setelah mengambil proyek di komputer lain.
.\graphify.cmd extract . --code-only --no-cluster --max-workers 1
.\graphify.cmd cluster-only . --no-label

# Cari konsep dan hubungan pada grafik.
.\graphify.cmd query "AdminStore register_admin_auth" --budget 1000
.\graphify.cmd explain "AdminStore"
.\graphify.cmd path "register_admin_auth" "AdminStore"

# Perbarui grafik setelah perubahan kode.
.\graphify.cmd update .
```

`graphify.cmd` menjalankan modul Python secara langsung. Jalur ini dipakai karena Windows Application Control pada komputer pemasangan memblokir launcher `graphify.exe`, sedangkan `python -m graphify` berhasil berjalan.

Hasil berada di `graphify-out/`:

- `graph.html`: grafik interaktif, dapat dibuka di browser.
- `GRAPH_REPORT.md`: laporan struktur dan komunitas kode.
- `graph.json`: data grafik untuk query berikutnya.

Lingkungan Python dan hasil grafik diabaikan Git; source konfigurasi dan skill proyek dapat disimpan dalam version control. Grafik perlu dibuat ulang pada komputer lain. Pembaruan dilakukan lewat perintah di atas atau instruksi Codex setelah perubahan kode; tidak ada proses watch atau git hook pembaruan otomatis yang diaktifkan oleh pemasangan ini.

## Integrasi Codex

Skill tersedia di `.codex/skills/graphify/SKILL.md`, dengan referensi pendukung di folder yang sama. Skill dapat ditemukan pada giliran berikutnya; gunakan `$graphify` ketika ingin memanggilnya secara eksplisit. `AGENTS.md` mengarahkan Codex memakai query grafik untuk pertanyaan tentang kode dan memperbaruinya setelah perubahan.

`.codex/hooks.json` berisi hook bawaan `hook-check`, disesuaikan agar memakai Python proyek. Hook ini merupakan no-op kompatibilitas Codex; panduan penggunaan grafik berasal dari `AGENTS.md`. Tidak ada perubahan konfigurasi global Codex atau aktivasi multi-agent.

## Cakupan pemasangan awal

Peta awal dibuat memakai AST kode secara lokal, tanpa API model. Pemindaian awal mencatat 63 berkas kode, 389 node, dan 20 komunitas. Ini bukan jaminan seluruh hubungan runtime terpetakan.

Dokumen Markdown, gambar, notebook, dan firmware `.ino` belum dianalisis dalam peta awal. Beberapa berkas tes Playwright dan konfigurasinya tidak menghasilkan simbol; `tokens.css` dilewati oleh pemeriksaan nama sensitif bawaan. Analisis semantik dokumen dapat ditambahkan secara terpisah setelah memilih model/backend. Rancangan SSO pada `AUTH_SSO_REGISTRATION.md` tetap berstatus rencana dan tidak menjadi bukti fitur sudah tersedia.

`.graphifyignore` mengecualikan lingkungan Python, dependensi, konfigurasi skill, database, kredensial, data perangkat, dan model biner. `.gitignore` juga tetap dihormati. Jangan memakai pemindaian database produksi untuk membangun grafik struktur kode.

## Memasang ulang pada komputer lain

Dengan Python 3.10+ dan `uv` tersedia, dari root proyek:

```powershell
uv venv .venv-graphify --python python
uv pip install --python .venv-graphify/Scripts/python.exe -r requirements-graphify.txt
.\graphify.cmd --help
```

Konfigurasi Codex dan skill proyek sudah disimpan sebagai berkas proyek. Untuk menghasilkan ulang integrasi bila berkas tersebut tidak tersedia, perintah resmi adalah `.\graphify.cmd install --project --platform codex`; perintah tersebut dapat menulis ulang `AGENTS.md` dan hook. Sesuaikan kembali perintah hook agar memakai `.venv-graphify\\Scripts\\python.exe -m graphify hook-check` dan pertahankan panduan wrapper Windows di `AGENTS.md`.

Setelah memasang ulang, buat grafik dengan dua perintah pertama pada bagian penggunaan. Untuk pembaruan versi, ubah pin paket secara sengaja, pasang ulang, lalu buat dan periksa grafik sebelum memakai hasilnya.

Sumber: [repository resmi Graphify](https://github.com/Graphify-Labs/graphify).
