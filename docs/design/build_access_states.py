"""Additional FigCraft storyboards for notification history, roles, and motion."""
import build_figcraft as d
from pathlib import Path
d.parts.clear()
from build_figcraft import rect,text,pill,button,icon,line,card,shell,end,INK,MUTED,BG
p=d.parts
p.append('<svg xmlns="http://www.w3.org/2000/svg" width="3040" height="2420" viewBox="0 0 3040 2420"><title>SmartOffice — Riwayat, akses, dan aksesibilitas</title>')
rect(0,0,3040,2420,'#dfe7dc',0)
text(40,44,'SMARTOFFICE / RIWAYAT, AKSES & AKSESIBILITAS',24,INK,700)
text(40,76,'Rancangan UI · Seluruh pesan, waktu, dan jumlah adalah contoh desain · Izin operator/admin merupakan usulan kebijakan akses',15,MUTED)

shell(40,105,'Monitoring','Contoh panel riwayat notifikasi pada dashboard.',0,9)
pill(1030,92,'OPERATOR',w=140);button(1190,88,'Notifikasi (2)',w=208)
rect(272,182,1128,47,'#fff2bc',12);pill(284,191,'DEMO',fill='#ffffff',w=80)
text(380,212,'Simulasi · Data ini bukan pembacaan alat. Pembaruan asli: --',14)
card(272,253,630,500,'Pemantauan kamera','Ilustrasi kamera; tidak membuka perangkat asli.')
rect(296,343,582,275,'#edf1e9',14);icon(565,435,2,d.GREEN);text(470,512,'Pratinjau kamera',20,INK,600)
button(296,653,'Ambil foto',True,174);text(493,680,'Simpan satu frame.',14,MUTED)
card(272,777,630,224,'Riwayat lingkungan')
text(296,864,'Belum ada riwayat sensor asli.',18,MUTED)
text(296,916,'Riwayat tersimpan tidak menandakan sensor online.',13,MUTED)
rect(926,253,474,748,'#ffffff',18,stroke='#d9e2d5')
text(950,289,'Riwayat notifikasi',23,INK,700);text(1362,289,'×',23,MUTED)
pill(950,314,'2 BELUM DIBACA',w=173);text(1145,333,'Tandai semua dibaca',12,INK,600)
button(950,365,'Semua',True,99);button(1061,365,'Foto',w=88);button(1161,365,'Perangkat',w=152)
text(950,438,'HARI INI · CONTOH',11,MUTED,600)
for y,title,detail,time,status,fill in [
    (458,'Foto berhasil disimpan','capture_demo_003.jpg · Dataset kamera','10.42 WIB','BERHASIL','#dcefdc'),
    (617,'Foto gagal disimpan','Koneksi ke server terputus.','10.39 WIB','GAGAL','#f7e3da'),
    (776,'Foto berhasil disimpan','capture_demo_002.jpg · Dataset kamera','10.35 WIB','BERHASIL','#dcefdc')]:
    rect(944,y,438,143,'#f4f6ef' if y!=776 else '#ffffff',12)
    pill(958,y+12,status,fill=fill,w=110);text(1214,y+31,time,12,MUTED)
    text(958,y+65,title,17,INK,600);text(958,y+92,detail,12,MUTED)
    text(958,y+122,'Coba lagi' if status=='GAGAL' else 'Lihat dataset',13,INK,600)
text(950,963,'Pesan tetap tersedia setelah toast menghilang.',12,MUTED)
end()

def dataset(ox,oy,admin,num):
    role='ADMIN' if admin else 'OPERATOR'
    shell(ox,oy,'Dataset sensor','Contoh tampilan sesuai izin akun · bukan data sensor aktual.',1,num)
    pill(1225,91,role,fill='#dcefdc' if admin else '#eef3e9',w=172)
    rect(272,183,1128,66,'#eef3e9',14)
    text(296,211,'RIWAYAT TERSIMPAN · CONTOH DESAIN',11,INK,700)
    text(296,234,'Data historis tersedia; status perangkat diperiksa terpisah dari jumlah baris.',13,MUTED)
    for x,l,v in [(272,'JUMLAH BARIS','1.248'),(654,'PERIODE CONTOH','01–05 Nov 2026'),(1036,'SUMBER HISTORIS','SCD40')]:
        rect(x,273,364,127);text(x+22,304,l,11,MUTED,600);text(x+22,349,v,27,INK,600);text(x+22,377,'ILUSTRASI DATA',11,MUTED)
    card(272,424,730,397,'Pratinjau data','12 data terbaru · Nilai di bawah hanya contoh desain')
    rect(296,512,682,43,BG,9)
    for x,s in [(310,'Waktu (WIB)'),(535,'CO₂ (ppm)'),(692,'Suhu (°C)'),(846,'RH (%)')]:text(x,539,s,12,MUTED,600)
    for i,(t,c,s,h) in enumerate([('05 Nov · 10.42','850','27,0','58'),('05 Nov · 10.41','842','26,9','58'),('05 Nov · 10.40','846','27,0','57')]):
        yy=596+i*62
        for x,v in [(310,t),(535,c),(692,s),(846,h)]:text(x,yy,v,15,INK)
        line(296,yy+20,978,yy+20)
    card(1026,424,374,397,'Unduhan dataset')
    pill(1050,487,'IZIN ADMIN' if admin else 'AKSES TERBATAS',fill='#dcefdc' if admin else '#fff2bc',w=202)
    text(1050,554,'CSV asli seluruh riwayat',17,INK,600)
    text(1050,586,'Diizinkan untuk akun admin.' if admin else 'Unduhan asli khusus admin.',14,MUTED)
    button(1050,615,'Unduh CSV asli',True,326,disabled=not admin)
    text(1050,692,'Ekspor mengikuti izin akun.' if admin else 'Hubungi admin bila memerlukan CSV.',13,MUTED)
    button(1050,736,'Unduh CSV dummy',w=326)
    card(272,845,1128,156,'Cakupan akses · '+role)
    text(296,916,'Monitoring + ambil foto + unduh dataset asli + pengaturan akses.' if admin else 'Monitoring + ambil foto + pratinjau dataset + unduh dummy.',16,INK,600)
    text(296,955,'Periksa izin ekspor di backend, termasuk saat endpoint dipanggil langsung.' if admin else 'Tombol CSV asli dinonaktifkan dengan alasan yang terlihat, bukan disembunyikan.',14,MUTED)
    end()
dataset(1560,105,False,10)
dataset(40,1265,True,11)

shell(1560,1265,'Pengaturan','Preferensi animasi dan pola status data yang konsisten.',4,12)
card(272,183,1128,282,'Gerakan & aksesibilitas','Preferensi diterapkan ke sidebar, toast, drawer, dan dialog.')
rect(296,275,680,65,'#eef3e9',12,stroke='#699c7b');text(316,315,'●  Ikuti pengaturan sistem',17,INK,600)
text(1002,314,'DEFAULT',12,MUTED,600)
rect(296,355,680,65,'#ffffff',12,stroke='#d9e2d5');text(316,395,'○  Selalu kurangi animasi',17,INK,600)
text(1002,394,'Tanpa geser / zoom',13,MUTED)
card(272,489,1128,328,'Status sumber data','Gunakan label teks, sumber, dan waktu pembaruan; jangan mengandalkan warna.')
for y,label,fill,main,sub in [
    (577,'LIVE','#dcefdc','Pembacaan SCD40 baru tersedia.','Sumber: SCD40 · Diterima: contoh 10.42 WIB'),
    (652,'DEMO','#fff2bc','Data simulasi, bukan pembacaan alat.','Sumber: synthetic · Tidak masuk dataset asli'),
    (727,'TERPUTUS','#f7e3da','Pembacaan terakhir sudah kedaluwarsa.','Nilai terakhir diberi tanda kedaluwarsa; jangan dianggap data saat ini.')]:
    pill(296,y,label,fill=fill,w=145);text(466,y+19,main,16,INK,600);text(466,y+46,sub,13,MUTED)
card(272,841,1128,160,'Aturan transisi')
text(296,909,'Standar: sidebar 220 ms · label 120 ms · toast 180 ms · dialog 160 ms.',16,INK,600)
text(296,951,'Kurangi animasi: perubahan langsung, tanpa pergeseran. Fungsi dan notifikasi tetap tersedia.',14,MUTED)
end()
p.append('</svg>')
target=Path(__file__).parent/'SmartOffice-Access-States.svg'
target.write_text('\n'.join(p),encoding='utf-8');print(target.resolve())
