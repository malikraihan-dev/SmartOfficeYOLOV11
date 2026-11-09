"""Create the vector design board imported into FigCraft; no real sensor data."""
from pathlib import Path
from html import escape

OUT = Path(__file__).parent
parts = []
INK, MUTED, BG, GREEN = '#203d30', '#64796c', '#f4f6ef', '#699c7b'
def rect(x,y,w,h,fill='#ffffff',r=18,stroke='none'):
    parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}"/>')
def text(x,y,s,size=16,color=INK,weight=400):
    parts.append(f'<text x="{x}" y="{y}" font-family="Segoe UI, Arial, sans-serif" font-size="{size}" font-weight="{weight}" fill="{color}">{escape(str(s))}</text>')
def line(x,y,x2,y2,color='#e4eade'):
    parts.append(f'<path d="M{x} {y} L{x2} {y2}" stroke="{color}" fill="none"/>')
def pill(x,y,s,fill='#eef3e9',color=INK,w=112):
    rect(x,y,w,28,fill,14); text(x+12,y+19,s,12,color,600)
def button(x,y,s,primary=False,w=168,disabled=False):
    rect(x,y,w,42,'#e8ece5' if disabled else INK if primary else '#f4f6ef',11)
    text(x+16,y+27,s,14,'#89948b' if disabled else '#ffffff' if primary else INK,600)
def icon(x,y,kind,color='#b6cdbc'):
    shapes={
      0:'M2 3 H20 V17 H2 Z M6 21 H16 M11 17 V21',
      1:'M3 5 Q11 -1 19 5 Q11 11 3 5 V17 Q11 23 19 17 V5 M3 11 Q11 17 19 11',
      2:'M2 5 H17 V19 H2 Z M17 10 L23 6 V18 L17 14',
      3:'M11 1 L21 7 V17 L11 23 L1 17 V7 Z M1 7 L11 13 L21 7 M11 13 V23',
      4:'M2 6 H22 M2 17 H22 M8 2 V10 M16 13 V21'}
    parts.append(f'<path transform="translate({x} {y})" d="{shapes[kind]}" fill="none" stroke="{color}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>')
def shell(ox,oy,title,sub,active,num):
    parts.append(f'<g id="screen-{num}" transform="translate({ox} {oy})">')
    rect(0,0,1440,1080,BG,24);rect(0,0,232,1080,INK,24);rect(210,0,22,1080,INK,0)
    rect(24,30,36,36,'#7ec486',10);text(34,55,'S',23,INK,700)
    text(72,48,'SmartOffice',21,'#ffffff',700);text(73,68,'WORKSPACE INTELLIGENCE',9,'#bbd1c0',600)
    text(26,122,'RUANG KERJA',11,'#a9c2b0',600)
    rect(18,138,196,60,'#304e3d',12);text(34,164,'Kantor utama',15,'#ffffff',600);text(34,184,'1 ruangan · Asia/Jakarta',12,'#bbd1c0')
    labels=['Monitoring','Dataset sensor','Dataset kamera','Model','Pengaturan']
    for i,label in enumerate(labels):
        y=234+i*58
        if i==active:rect(16,y-12,200,46,'#fff2bc',12)
        icon(30,y,i,INK if i==active else '#b6cdbc');text(66,y+17,label,15,INK if i==active else '#d8e5da',600 if i==active else 400)
    line(24,884,208,884,'#42604b');text(28,920,'PROTOTIPE LOKAL',11,'#b6cdbc',600)
    text(28,947,'Satu sensor, satu ruangan',12,'#d8e5da');text(28,970,'Data demo ditandai jelas.',12,'#b6cdbc')
    text(272,49,'SMARTOFFICE  /  '+title.upper(),11,MUTED,600)
    pill(1192,24,'DESAIN UI',w=104);text(1320,44,'WIB',12,MUTED)
    line(264,70,1408,70)
    text(272,122,title,34,INK,700);text(272,151,sub,15,MUTED)
    text(272,1051,'SmartOffice · Konsep antarmuka / bukan data sensor aktual',12,MUTED)
    text(1260,1051,f'{num:02d} / DESKTOP',11,MUTED,600)
def end():parts.append('</g>')
def card(x,y,w,h,title,subtitle=None):
    rect(x,y,w,h);text(x+24,y+34,title,18,INK,600)
    if subtitle:text(x+24,y+59,subtitle,13,MUTED)
def metric(x,label,value,unit,note):
    rect(x,245,266,136);text(x+20,275,label,13,MUTED,600)
    text(x+20,322,value,36,INK,600);text(x+138,319,unit,15,MUTED)
    text(x+20,357,note,12,MUTED)

parts.append('<svg xmlns="http://www.w3.org/2000/svg" width="4560" height="2420" viewBox="0 0 4560 2420"><title>SmartOffice — Dashboard design</title>')
rect(0,0,4560,2420,'#dfe7dc',0)
text(40,45,'SMARTOFFICE / ANTARMUKA RUANG KERJA',23,INK,700)
text(40,73,'Panduan DESIGN.md · Desktop 1440 px · Mobile 390 px · Semua nilai bertanda DEMO adalah ilustrasi',14,MUTED)
shell(40,105,'Monitoring','Pantau aktivitas dan kondisi ruang dalam satu tampilan.',0,1)
rect(272,177,1128,48,'#fff2bc',12);pill(286,187,'DEMO',fill='#ffffff',w=72)
text(374,207,'Data simulasi · Belum ada pembacaan SCD40 asli. Hubungkan ESP32 untuk mulai merekam.',14)
for x,l,v,u,n in [(272,'OKUPANSI','--','orang','Kamera belum aktif'),(558,'CO₂','850','ppm','DEMO · bukan pembacaan alat'),(844,'SUHU','27,0','°C','DEMO · bukan pembacaan alat'),(1130,'KELEMBAPAN','58','%','DEMO · bukan pembacaan alat')]:
    metric(x,l,v,u,n)
card(272,405,730,382,'Pemantauan kamera','Kamera 01 · Ruang kerja utama')
pill(826,426,'NONAKTIF',w=146)
rect(296,488,682,225,'#edf1e9',14);icon(610,540,2,GREEN)
text(523,596,'Kamera belum diaktifkan',20,INK,600);text(469,625,'Aktifkan kamera untuk melihat deteksi penghuni.',14,MUTED)
button(296,730,'Aktifkan kamera',True,180);button(490,730,'Atur zona kerja',w=160)
card(1026,405,374,180,'Aktivitas ruang')
text(1050,479,'Menunggu kamera',23,INK,600);text(1050,511,'Ringkasan aktivitas muncul setelah',14,MUTED);text(1050,535,'kamera mulai mengirim frame.',14,MUTED)
card(1026,609,374,178,'Koneksi perangkat')
pill(1050,664,'SENSOR: DEMO',fill='#fff2bc',w=152);text(1050,723,'Pembaruan asli: --',14,MUTED);text(1050,748,'Zona waktu: Asia/Jakarta',14,MUTED)
card(272,811,730,190,'Riwayat lingkungan','Grafik memakai riwayat asli yang tersimpan.')
line(296,962,976,962);text(477,928,'Belum ada riwayat sensor asli',17,MUTED)
card(1026,811,374,190,'Prediksi 5 menit ke depan')
pill(1050,864,'BELUM DIHUBUNGKAN',w=220);text(1050,928,'Suhu  -- °C     CO₂  -- ppm',20,INK,600);text(1050,970,'Butuh model tervalidasi + riwayat lengkap.',12,MUTED)
end()

shell(1560,105,'Dataset sensor','Kelola riwayat asli dan siapkan data untuk training.',1,2)
for x,l,v,n in [(272,'PEMBACAAN ASLI','0','Belum ada data tersimpan'),(654,'PERIODE DATA','--','Waktu awal hingga akhir'),(1036,'SUMBER DATA','SCD40','Terpisah dari data sintetis')]:
    rect(x,183,364,126);text(x+22,213,l,11,MUTED,600);text(x+22,256,v,30,INK,600);text(x+22,286,n,13,MUTED)
card(272,333,730,575,'Riwayat pembacaan','12 data terbaru · Ekspor mencakup seluruh riwayat')
pill(812,354,'KOSONG',w=160)
rect(296,419,682,44,BG,9)
for x,s in [(310,'Waktu (WIB)'),(510,'CO₂ (ppm)'),(670,'Suhu (°C)'),(824,'RH (%)')]:text(x,447,s,12,MUTED,600)
icon(620,535,1,GREEN);text(469,599,'Belum ada data sensor asli',22,INK,600)
text(424,634,'Hubungkan ESP32 + SCD40 ke server SmartOffice.',14,MUTED)
text(433,660,'Pembacaan valid akan tersimpan secara otomatis.',14,MUTED)
button(526,695,'Lihat panduan koneksi',True,222)
line(296,803,978,803);button(296,827,'Unduh CSV asli',w=184,disabled=True)
text(503,854,'Tersedia setelah ada pembacaan asli.',12,MUTED)
card(1026,333,374,575,'Siapkan training di Colab','Training berjalan di luar dashboard.')
steps=[('01','Kumpulkan data asli','Satu sensor di satu ruangan.'),('02','Unduh CSV','Waktu, CO₂, suhu, kelembapan.'),('03','Jalankan notebook','Pilih DATA_MODE = upload.'),('04','Evaluasi model','Bandingkan dengan baseline.')]
for i,(n,t,s) in enumerate(steps):
    y=437+i*91;rect(1050,y-22,36,36,'#eef3e9',10);text(1058,y+2,n,13,INK,600);text(1100,y,t,16,INK,600);text(1100,y+26,s,12,MUTED)
button(1050,824,'Buka notebook Colab',True,326)
rect(272,932,1128,69,'#fff2bc',14);text(294,959,'LATIHAN TANPA ALAT',11,INK,700)
text(294,983,'CSV dummy berisi simulasi; jangan dicampur dengan pembacaan sensor asli.',13)
button(1130,946,'Unduh CSV dummy',w=246)
end()

shell(3080,105,'Dataset kamera','Tinjau foto, anotasi, dan bahan evaluasi deteksi.',2,3)
rect(272,183,1128,64,'#eef3e9',14);text(296,221,'Riwayat foto adalah data tersimpan; bukan indikator kamera sedang aktif.',15)
card(272,271,1128,640,'Koleksi gambar','Foto dan anotasi dari sesi kamera SmartOffice')
button(1170,291,'Ekspor dataset',w=204,disabled=True)
rect(296,359,1080,432,BG,16);icon(816,468,2,GREEN)
text(669,538,'Belum ada foto tersimpan',25,INK,600)
text(600,577,'Aktifkan kamera dan ambil sampel melalui halaman Monitoring.',15,MUTED)
button(736,614,'Ke Monitoring',True,200)
text(296,855,'0 foto',14,INK,600);text(390,855,'Anotasi dan evaluasi tersedia setelah sampel dikumpulkan.',14,MUTED)
rect(272,935,1128,66,'#fff2bc',14);text(296,975,'Gunakan foto ruang kerja sesuai kebijakan privasi organisasi.',15)
end()

shell(40,1265,'Model','Periksa sumber training dan hasil evaluasi sebelum aktivasi.',3,4)
card(272,183,1128,196,'Prediksi lingkungan · SCD40','Model sensor terpisah dari deteksi objek YOLO.')
pill(1118,208,'BELUM DIHUBUNGKAN',w=254)
text(296,291,'Suhu + CO₂',29,INK,600);text(650,284,'HORIZON',11,MUTED,600);text(650,313,'5 menit',23,INK,600)
text(952,284,'VERSI AKTIF',11,MUTED,600);text(952,313,'--',23,INK,600)
text(296,350,'Tidak ada prediksi yang ditampilkan sebelum model tervalidasi terhubung.',14,MUTED)
card(272,403,730,306,'Evaluasi model','Metrik dari data test asli, dengan split kronologis.')
rect(296,491,682,43,BG,9)
for x,s in [(312,'Target'),(490,'MAE'),(654,'RMSE'),(823,'Baseline MAE')]:text(x,518,s,12,MUTED,600)
for y,s,u in [(580,'Suhu','°C'),(637,'CO₂','ppm')]:
    text(312,y,s,15,INK,600);text(490,y,'-- '+u,15,MUTED);text(654,y,'-- '+u,15,MUTED);text(823,y,'-- '+u,15,MUTED)
card(1026,403,374,306,'Metadata training')
for i,(l,v) in enumerate([('Sumber data','--'),('Periode test','--'),('Versi library','--'),('Zona waktu','Asia/Jakarta')]):
    text(1050,483+i*50,l,13,MUTED);text(1240,483+i*50,v,13,INK,600)
card(272,733,1128,268,'Kesiapan integrasi')
for i,s in enumerate(['Verifikasi asal model, versi library, dan daftar fitur.','Bandingkan MAE/RMSE terhadap persistence pada data asli.','Pastikan 31 menit riwayat lengkap tersedia sebelum prediksi.']):
    rect(296,796+i*47,22,22,'#eef3e9',6);text(334,813+i*47,s,15,MUTED)
pill(1100,927,'AKTIVASI BELUM TERSEDIA',w=272)
end()

shell(1560,1265,'Pengaturan','Konfigurasi perangkat dan ruang kerja untuk satu instalasi lokal.',4,5)
card(272,183,730,424,'Koneksi sensor','ESP32 + SCD40 · Satu sensor / satu ruangan')
text(296,283,'Endpoint penerimaan',13,MUTED,600);rect(296,299,682,52,BG,10);text(312,332,'POST /api/scd40',17,INK,600)
text(296,393,'Alamat server pada firmware',13,MUTED,600);rect(296,409,682,52,BG,10);text(312,442,'http://<IP-komputer>:5000/api/scd40',16)
text(296,503,'ESP32 harus berada pada jaringan yang sama dengan server.',14,MUTED)
button(296,535,'Lihat panduan perangkat',True,244)
card(1026,183,374,424,'Status instalasi')
pill(1050,262,'DEMO',fill='#fff2bc',w=90)
text(1050,333,'Data asli terakhir',13,MUTED);text(1050,366,'Belum tersedia',22,INK,600)
text(1050,425,'Riwayat tersimpan',13,MUTED);text(1050,458,'0 pembacaan',22,INK,600)
text(1050,548,'Status memakai teks dan warna.',13,MUTED)
card(272,631,1128,370,'Ruang kerja dan tampilan')
for x,label,value in [(296,'Nama ruangan','Kantor utama'),(852,'Zona waktu','Asia/Jakarta (WIB)')]:
    text(x,730,label,13,MUTED,600);rect(x,748,524,54,BG,10);text(x+16,782,value,17)
text(296,854,'Zona kamera',14,INK,600);text(296,884,'Tentukan area kerja pada pratinjau kamera di halaman Monitoring.',14,MUTED)
text(296,947,'Konsep pengaturan · Perubahan belum terhubung ke backend.',13,MUTED)
end()

parts.append('<g id="monitoring-mobile" transform="translate(3080 1265)">')
rect(0,0,390,1080,BG,24);rect(0,0,390,74,INK,24);text(22,45,'SmartOffice',22,'#ffffff',700);text(307,44,'Menu',14,'#fff2bc',600)
text(20,117,'Monitoring',28,INK,700);text(20,145,'Kantor utama · WIB',13,MUTED)
rect(20,168,350,78,'#fff2bc',14);text(36,196,'DEMO · Data simulasi',14,INK,700);text(36,222,'Belum ada pembacaan sensor asli.',13)
for x,y,l,v in [(20,266,'CO₂','850 ppm'),(205,266,'Suhu','27,0 °C'),(20,392,'Kelembapan','58 %'),(205,392,'Okupansi','-- orang')]:
    rect(x,y,165,106);text(x+16,y+29,l,13,MUTED);text(x+16,y+67,v,25,INK,600);text(x+16,y+90,'DEMO' if l!='Okupansi' else 'NONAKTIF',10,MUTED,600)
card(20,518,350,246,'Pemantauan kamera');rect(36,574,318,114,'#edf1e9',12)
text(89,637,'Kamera belum aktif',17,MUTED);button(36,704,'Aktifkan kamera',True,318)
card(20,784,350,168,'Prediksi 5 menit ke depan');pill(36,840,'BELUM DIHUBUNGKAN',w=232)
text(36,909,'Suhu -- °C  ·  CO₂ -- ppm',21,INK,600)
rect(0,982,390,98,'#ffffff',0)
for x,i,s in [(20,0,'Pantau'),(116,1,'Dataset'),(217,3,'Model'),(309,4,'Atur')]:icon(x+12,999,i,GREEN);text(x+2,1048,s,12,INK,600)
parts.append('</g>')
text(3520,1310,'SISTEM VISUAL',23,INK,700)
text(3520,1340,'Fondasi dari docs/DESIGN.md',15,MUTED)
for i,(c,n) in enumerate([(INK,'Teks & sidebar'),('#699c7b','Sage'),('#7ec486','Hijau lembut'),('#fff2bc','Krem'),(BG,'Latar')]):
    rect(3520,1370+i*75,52,52,c,12);text(3592,1392+i*75,n,16,INK,600);text(3592,1413+i*75,c,13,MUTED)
text(3520,1804,'STATUS DATA',18,INK,700)
for y,s,fill,n in [(1830,'LIVE','#dcefdc','Pembacaan sensor baru tersedia'),(1900,'DEMO','#fff2bc','Simulasi, bukan pembacaan alat'),(1970,'TERPUTUS','#f7e3da','Pembacaan kedaluwarsa / tidak tersedia'),(2040,'RIWAYAT','#e8ece5','Data tersimpan; bukan status online')]:
    pill(3520,y,s,fill=fill,w=146);text(3520,y+52,n,14,MUTED)
text(3520,2160,'Kartu 18 px · Jarak 24 px',16,INK,600)
text(3520,2190,'Ikon garis · Satuan dekat angka',15,MUTED)
text(3520,2220,'Desktop: dua kolom · Ponsel: satu kolom',15,MUTED)
text(3520,2250,'Tidak ada skor akurasi atau prediksi palsu.',15,MUTED)
parts.append('</svg>')
target=OUT/'SmartOffice-FigCraft.svg'
target.write_text('\n'.join(parts),encoding='utf-8')
print(target.resolve())
