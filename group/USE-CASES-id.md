# Penerjemah Rapat PCG: contoh penggunaan

[中文](使用情境.md) · [English](USE-CASES-en.md) · [Bahasa Indonesia](USE-CASES-id.md) · [Tiếng Việt](USE-CASES-vi.md)

Subtitle langsung membedakan bahasa **dari sumber suara**:

- **Suara yang diputar komputer** (lawan bicara di Teams/Zoom, video) = bahasa lawan bicara
- **Mikrofon** (jika memilih "Saya juga berbicara") = bahasa Anda sendiri

Jadi hanya **komputer yang menjalankan rapat atau kelas** yang perlu memasang aplikasi. Pihak lain tidak perlu memasang apa pun.

## Memilih opsi yang tepat (mulai versi r11)

"Subtitle langsung" menanyakan tiga hal secara berurutan, dan hanya opsi yang cocok untuk Anda yang tetap tampil:

1. **Anda berbicara bahasa apa?** Karyawan Taiwan memilih "中文"; karyawan Indonesia, Vietnam, dan India memilih bahasanya sendiri.
2. **Jenis rapat apa?**
   - Hanya baca subtitle
   - Saya juga berbicara
   - Satu ruang kelas
   - Komputer subtitle (mulai r19; kode QR langsung tampil setelah Mulai dan setiap orang memilih bahasanya sendiri)
3. **Lawan bicara berbahasa apa?** Jika Anda memilih bahasa Indonesia, Anda melihat "Mandarin → Indonesia" dan bahasa asing lain (mulai r17; mis. "Bahasa Vietnam, ke Indonesia").

Pilihan terakhir Anda akan diingat. Jika opsi yang dicari tidak muncul, klik "Tampilkan semua pilihan".

**"Bahasa Indonesia" dan "Mandarin → Indonesia": apa bedanya?**

| Opsi | Yang didengar | Subtitle dalam | Komputer siapa | Bisa ditambah |
|---|---|---|---|---|
| Bahasa Indonesia (lawan bicara berbahasa Indonesia) | Bahasa Indonesia | Mandarin | Karyawan Taiwan yang tidak mengerti bahasa Indonesia | Saya juga berbicara (dua arah), mode kelas |
| Mandarin → Indonesia | Mandarin | Bahasa Indonesia | Karyawan Indonesia yang tidak mengerti pengajar atau atasan berbahasa Mandarin | Mode kelas |
| Bahasa Vietnam, ke Indonesia (r17) | Bahasa Vietnam | Bahasa Indonesia | Karyawan Indonesia yang rapat dengan karyawan Vietnam | Saya juga berbicara (dua arah), mode kelas |

Contoh: Guru Lin mengajar Budi di Indonesia lewat Teams.
- Komputer Guru Lin: saya berbicara "中文" → "Saya juga berbicara" → "Bahasa Indonesia".
- Komputer Budi: saya berbicara "Bahasa Indonesia" → "Mandarin → Indonesia" langsung terpilih.

Cara mengingat: nama opsi adalah bahasa **lawan bicara**; subtitle muncul dalam bahasa **Anda**. Vietnam, Hindi, dan Inggris juga sama.

## 1. Rapat atau kelas online: Mandarin ⇄ bahasa lain

> Contoh: pengajar berbicara bahasa Mandarin, siswa Indonesia menjawab dalam bahasa Indonesia, semua di Teams.

**Siapa yang memasang**: hanya komputer pengajar. Siswa ikut Teams/Zoom seperti biasa.

1. Di komputer pengajar: "Penerjemah Rapat PCG" → "Subtitle langsung".
2. Saya berbicara "**中文**" → jenis rapat "**Saya juga berbicara**" → "**Bahasa Indonesia**", klik Mulai.
3. **Pakai headphone**, agar suara siswa dari speaker tidak masuk ke mikrofon dan dianggap bahasa Mandarin.

Subtitle: bahasa Mandarin pengajar → Mandarin + terjemahan Indonesia; bahasa Indonesia siswa → Indonesia + terjemahan Mandarin.

**Agar siswa melihat subtitle** (pilih salah satu):
- **Bagikan layar** (di mana saja): centang "Subtitle selalu di atas" dan bagikan layar di Teams.
- **Ponsel** (siswa di jaringan perusahaan): klik "Bagikan", siswa memindai kode QR, memasukkan kata sandi staf, lalu memilih bahasa. IT harus mengaktifkan "Izinkan komputer dan ponsel lain melihat subtitle".

**Siswa ingin melihat subtitle di komputer sendiri** (mulai v2026.11.5.r9): pasang aplikasi di komputer siswa, buka "Subtitle langsung", pilih saya berbicara "**Bahasa Indonesia**": "**Mandarin → Indonesia**" langsung terpilih (Vietnam, Hindi, Inggris juga sama). Klik Mulai. Siswa hanya mendengar, jadi tidak perlu headphone. Aplikasi menangkap suara pengajar dari Teams dan menampilkannya dalam bahasa Indonesia; komputer pengajar tetap memakai dua arah. Tidak perlu berbagi layar; setiap orang membaca bahasanya sendiri.

## 2. Hanya ingin memahami lawan bicara

Saya berbicara "中文" → jenis rapat "**Hanya baca subtitle**" → bahasa lawan bicara, klik Mulai. Tidak perlu headphone.

## 3. Satu ruang rapat atau kelas, satu mikrofon (mode kelas)

> Contoh: pengajar dan siswa Indonesia berbicara di kelas yang sama. (mulai v2026.11.5.r9)

1. Pasang mikrofon yang bisa menangkap suara seluruh ruangan (mikrofon rapat atau mikrofon meja).
2. "Subtitle langsung" → saya berbicara "中文" → jenis rapat "**Satu ruang kelas**" → "**Bahasa Indonesia**" → Mulai. (Vietnam, Hindi, dan Inggris juga bisa.)
3. Tampilkan subtitle di proyektor, atau siswa memindai kode QR dari "Bagikan".

Setiap kalimat dikenali otomatis sebagai Mandarin atau Indonesia: Mandarin → Mandarin + terjemahan Indonesia; Indonesia → Indonesia + terjemahan Mandarin.

**Keterbatasan**
- Paling baik **satu orang berbicara bergantian**; bicara bersamaan atau kalimat campuran dikenali kurang baik.
- **Jawaban sangat pendek** ("ok", "ya") bisa salah dikenali bahasanya.
- Subtitle **sedikit lebih lambat** karena bahasa setiap kalimat dikenali dulu.
- Mode kelas memakai pengenalan suara di komputer ini (bukan server GPU) dengan model lokal yang diatur IT.
- "Mode kelas" dan "Saya juga akan berbicara" pilih salah satu: kelas online → "Saya juga akan berbicara" + headphone; satu ruangan → mode kelas.

## 4. Banyak orang ingin membaca subtitle di ponsel

1. IT mengaktifkan "Izinkan komputer dan ponsel lain melihat subtitle" dan membuat kata sandi staf (lalu tekan "Mulai ulang program sekarang" di halaman, sekitar 10 detik; jika lupa, saat menekan Mulai program akan memulai ulang sendiri).
2. Mulai subtitle langsung, klik "Bagikan", tampilkan kode QR.
3. Peserta memindai, memasukkan kata sandi staf, dan memilih bahasanya di "Saya baca" di kanan atas: Mandarin, Indonesia, Vietnam, Hindi, atau Inggris. Jika sebuah kalimat tidak dalam bahasa itu, komputer rapat menerjemahkan satu salinan lagi (subtitle multibahasa, mulai r19), dan bagian atas halaman menjelaskannya. Ponsel hanya bisa melihat. Ponsel harus terhubung ke komputer itu, biasanya di jaringan perusahaan.

## 5. Notulen setelah rapat

1. "Rekaman → Notulen" → unggah rekaman atau video Teams/Zoom (mp3, m4a, wav, mp4).
2. Pilih bahasa yang **paling banyak dipakai**; boleh isi topik dan jumlah pembicara.
3. Halaman boleh ditutup; kembali nanti untuk mengunduh notulen, transkrip, dan file subtitle (sekitar 10–30 menit untuk rapat 1 jam).
4. Notulen AI (keputusan, tindak lanjut, risiko) memerlukan mode server; mode lokal menghasilkan transkrip dan terjemahan.

## 6. Rapat antar karyawan asing (mis. karyawan Indonesia dan Vietnam, mulai r17)

Diterjemahkan langsung, tidak lewat bahasa Mandarin. Dua bahasa mana pun dari Indonesia, Vietnam, Hindi, dan Inggris.

**Rapat online (masing-masing di komputernya sendiri)**
- Karyawan Indonesia: saya berbicara "Bahasa Indonesia" → jenis rapat → "Bahasa Vietnam" (subtitle dalam bahasa Indonesia).
- Karyawan Vietnam: saya berbicara "Tiếng Việt" → jenis rapat → "Bahasa Indonesia" (subtitle dalam bahasa Vietnam).
- Pilih "Hanya baca subtitle", atau "Saya juga berbicara (pakai headset)" agar terjemahan ucapan Anda juga tampil.

**Satu ruang rapat, satu mikrofon**: di satu komputer pilih bahasa Anda → "Satu ruang kelas" → bahasa lawan bicara. Setiap kalimat dikenali lalu diterjemahkan ke bahasa lainnya; gunakan "Bagikan" agar orang lain bisa mengikuti di ponsel dalam bahasa pilihannya.

**Kualitas**
- Secara bawaan hanya model dasar yang dipakai: Whisper small untuk pengenalan suara dan M2M100 di komputer untuk terjemahan. Pengenalan bahasa Indonesia dan Vietnam bisa salah, dan terjemahan ikut salah.
- Agar lebih akurat, IT dapat memasang paket model bahasa (membantu untuk "Hanya baca subtitle") atau beralih ke mode server di halaman pengaturan IT agar diterjemahkan oleh model bahasa besar.
- Notulen dari rekaman masih ditulis dalam bahasa Mandarin.

---

## 7. Rapat multinasional, karyawan Taiwan berbahasa Mandarin

Misalnya atasan dari Taiwan memimpin rapat dalam bahasa Mandarin, dihadiri karyawan Indonesia, Vietnam, dan India, dan setiap orang ingin subtitle dalam bahasanya sendiri.

**Rapat online (Teams): setiap orang membuka subtitle di komputernya sendiri (sudah bisa)**
- **Karyawan asing**: di komputer sendiri pilih saya berbicara "bahasa Anda" → "Hanya baca subtitle" → "Mandarin". Bahasa Mandarin di Teams diterjemahkan ke bahasa Anda; setiap orang membaca bahasanya sendiri.
- **Karyawan Taiwan yang ingin memahami ucapan karyawan asing**: pilih "Bahasa Indonesia" dan seterusnya. Hanya satu bahasa asing sekaligus; saat orang lain berbicara bahasa lain, pilih bahasa itu lalu klik Mulai (sesi sebelumnya otomatis diganti).

**Satu ruang rapat**
- Gunakan "komputer subtitle" ruang rapat (satu komputer dengan kartu grafis; pengaturan di panduan IT): pilih "**Komputer subtitle**" dan bahasa yang paling banyak dipakai peserta lain (mis. Indonesia), klik Mulai; kode QR langsung tampil, tampilkan di proyektor.
- Semua orang memindai kode QR dan memilih bahasanya sendiri di kanan atas (subtitle multibahasa, mulai r19): penonton Mandarin dan Indonesia membaca subtitle biasa; untuk penonton Vietnam, Hindi, atau Inggris, komputer subtitle menerjemahkan satu salinan lagi.
- Mikrofon hanya membedakan Mandarin dan satu bahasa asing yang dipilih. Karyawan yang berbicara bahasa lain sebaiknya memakai bahasa Inggris atau dibantu orang lain.
- Jika hanya karyawan Taiwan yang berbicara di ruangan, pilih "**Semua berbahasa Mandarin**": mulai r28 pilihan ini memakai mikrofon, dan karyawan asing membaca bahasanya sendiri lewat subtitle multibahasa. (Sampai r26 pilihan ini hanya mendengarkan suara yang diputar komputer; perbarui dulu.)

---

## 8. Pengajar di Taiwan mengajar dalam bahasa Mandarin, Anda membaca subtitle dalam bahasa Anda (r26)

Misalnya pengajar di Taiwan mengajar pabrik Indonesia, Vietnam, dan India lewat Teams, sepenuhnya dalam bahasa Mandarin. Anda ingin subtitle dalam bahasa Anda, dan **suara tidak boleh keluar dari perusahaan**.

**Cara yang disarankan: satu "komputer subtitle" dengan kartu grafis ikut kelas, bahasa Mandarin dikenali satu kali**

Komputer subtitle punya kartu grafis NVIDIA (IT memasang paket GPU dan model Mandarin Breeze ASR 25 lebih dulu; lihat panduan IT). Komputer itu ikut kelas Teams seperti peserta, mendengarkan pengajar, mengenali bahasa Mandarin, lalu menerjemahkannya; Anda cukup memakai browser.

- **Anda (karyawan di pabrik luar negeri)**: buka alamat yang dibagikan di chat Teams (`http://<IP komputer subtitle>:19781/simple/live`) di browser komputer atau ponsel, masukkan kata sandi staf, lalu pilih bahasa Anda di kanan atas (Indonesia, Vietnam, Hindi, Inggris). **Tidak perlu memasang program.**
- **Pengajar**: mengajar lewat Teams seperti biasa, tidak perlu memasang apa pun.
- **Yang menjalankan komputer subtitle** (asisten atau IT):
  1. Komputer subtitle bergabung ke kelas Teams, mikrofon dimatikan, speaker atau headset **jangan dibisukan** (program mendengarkan suara yang diputar komputer).
  2. Buka PCG Meeting Translator → saya berbicara "中文" → "**Hanya baca subtitle**" → "**Semua berbahasa Mandarin**" → Mulai.
  3. Di layar subtitle tekan "**Bagikan**", lalu tempel alamat dan kata sandi staf ke chat Teams.

**Komputer pengajar punya kartu grafis: langsung jadi komputer subtitle (mulai r28)**

Pengajar mengajar di komputernya sendiri (lewat Teams atau di ruang kelas), tanpa komputer kedua: saya berbicara "中文" → "**Satu ruang kelas**" (atau "Komputer subtitle") → "**Semua berbahasa Mandarin**" → Mulai. Program mendengarkan pengajar lewat **mikrofon** dan tetap mengenali dengan Breeze; tekan "Bagikan" lalu berikan alamatnya ke karyawan di luar negeri. Ucapan peserta di Teams tidak muncul di subtitle (hanya mikrofon).

**Mengapa lebih akurat**

- Bahasa Mandarin dikenali kartu grafis komputer subtitle dengan Breeze ASR 25 (dilatih untuk Mandarin Taiwan dan campuran Mandarin-Inggris), lebih akurat daripada model kecil bawaan di laptop biasa.
- Semua orang membaca hasil pengenalan yang sama; minta IT mengisi istilah pelajaran ke glosarium lebih dulu.
- Suara hanya diproses di komputer subtitle dan tidak dikirim ke luar perusahaan.

**Cara lain: membuka subtitle di komputer Anda sendiri**

Saya berbicara "Bahasa Indonesia" → "Hanya baca subtitle" → "Mandarin → Indonesia". Pengenalan berjalan di komputer Anda: jika ada kartu grafis NVIDIA, halaman menyarankan memasang Breeze ASR 25 dan hasilnya sama dengan komputer subtitle; laptop biasa hanya bisa memakai model kecil bawaan, jadi akurasi bahasa Mandarin tidak meningkat.

**Batasan**

- Suara yang didengarkan "Semua berbahasa Mandarin" bergantung pada jenis rapat (mulai r28; halaman menuliskannya setelah dipilih): "Hanya baca subtitle" mendengarkan **suara yang diputar komputer** (komputer subtitle yang ikut Teams dan mendengar pengajar); "Satu ruang kelas" dan "Komputer subtitle" mendengarkan **mikrofon** (pengajar berbicara ke komputer ini atau mikrofon ruangan). Sampai r26 selalu suara yang diputar komputer.
- Satu sesi mendengarkan satu sumber: dengan mikrofon, ucapan orang lain di Teams tidak terdengar; dengan suara komputer, mikrofon komputer ini tidak terdengar.
- Pabrik luar negeri harus bisa menjangkau komputer subtitle lewat jaringan perusahaan (port 19781). Tanyakan dulu ke IT atau tim jaringan apakah akses antar lokasi bisa.
- Kualitas terjemahan bergantung pada pengaturan IT: mode lokal (M2M100) biasa saja untuk bahasa Indonesia dan Vietnam; mode server (model besar) jauh lebih baik.
- Cara ini menggabungkan fitur yang sudah ada. Jeda Breeze pada subtitle langsung, penangkapan suara lewat mikrofon, akses antar lokasi, dan banyak penonton sekaligus belum diuji di komputer nyata, jadi coba dulu pada satu kelas.

---

## Nama dan nomor part sering salah dengar? Tempelkan informasi rapat ini dulu (r32)

"**+ Tambahkan informasi rapat ini**" di subtitle langsung (juga ada di "Rekaman → Notulen"):

1. Tempelkan **nama peserta, nama produk, nomor part, dan butir agenda** rapat ini, satu per baris atau dipisahkan koma. Contoh:

   ```
   Peserta: Wang Hsiao-ming, Budi Santoso
   Serah terima mesin pabrik Jawa Tengah
   PO-12345
   ```
2. Klik "Mulai subtitle langsung". Saat pengenalan suara mendengar bunyi yang mirip, penulisan inilah yang diutamakan; saat LLM menerjemahkan, nama dan istilah juga mengikuti penulisan ini.
3. Informasi ini hanya disimpan di komputer ini dan masih ada saat dibuka lagi (rapat rutin tidak perlu menempel ulang); untuk rapat lain, ubah atau klik "Hapus".

- Tidak perlu menempelkan seluruh presentasi: kata-kata pendek paling membantu. Kalimat panjang hanya menjadi latar untuk terjemahan dan tidak dipakai untuk membantu pengenalan suara.
- Saat komputer ini dalam **mode lokal**, informasi ini hanya membantu pengenalan suara (model terjemahan lokal tidak bisa memakainya).
- Saat ada peringatan oranye di bagian atas halaman (suara atau teks dikirim ke layanan di luar perusahaan), informasi ini ikut terkirim: jangan menempelkan isi yang rahasia.
- Kata yang dipakai seluruh perusahaan (nama perusahaan, pabrik, nama sistem) sebaiknya dimasukkan IT ke "Glosarium", sehingga tidak perlu ditempel setiap kali.

## Lawan bicara tidak mengerti ucapan saya? Ketik di layar subtitle (r32)

"**Ketik balasan**" di bagian bawah layar subtitle: ketik dalam bahasa Anda, klik "Terjemahkan", dan bahasa lawan bicara muncul dengan huruf besar.

- **Bacakan**, atau putar layar dan **tunjukkan**; di rapat online klik "Salin" lalu tempel ke obrolan Teams/Zoom.
- Tombol di sebelah kiri menunjukkan arahnya (mis. "Indonesia → Mandarin ⇄"); klik untuk menukar, sehingga lawan bicara juga bisa mengetik dalam bahasanya di komputer Anda.
- Satu kalimat setiap kali, paling banyak 300 karakter. Kalimat yang diketik tetap ada di percakapan halaman ini; **orang yang menonton subtitle di ponsel tidak melihatnya**.
- Hanya tersedia saat subtitle berjalan, di komputer yang menangkap suara; "Semua berbahasa Mandarin" tidak memiliki terjemahan, jadi tidak ada fitur ini.
- Untuk menyembunyikannya, klik lagi "Ketik balasan" di bagian bawah. Di tampilan subtitle berlatar hitam, bagian ini tersembunyi secara bawaan.

---

## Bantuan di layar (r29)

- **Kalimat konfirmasi sebelum mulai**: di atas tombol tertulis “Anda mendengar: Mandarin → subtitle: Indonesia”. Jika tidak sesuai harapan, langkah 3 terbalik; ubah dulu sebelum mulai.
- **Sama seperti terakhir kali**: setelah sesi pertama, halaman hanya menampilkan pilihan terakhir dan “Mulai”. Tekan “Ubah” di sampingnya untuk memilih bahasa atau jenis rapat lain.
- **Staf berbahasa asing**: setelah memilih bahasa Anda, “Mandarin → bahasa Anda” sudah dipilihkan; ubah hanya jika perlu bahasa lain.
- **Tombol berwarna abu-abu**: masih ada yang belum dipilih; tekan tombol itu dan halaman memberi tahu langkah mana yang kurang.
- **Ikon mikrofon di kiri atas layar subtitle**: bergerak saat program mendengarkan dan belum ada yang berbicara, diam saat subtitle sedang muncul. Ikon sambungan berwarna oranye berarti koneksi terputus dan sedang disambung ulang.
- **Komputer subtitle**: langsung terbuka dalam mode subtitle huruf besar; pakai A−/A+ di kanan atas untuk mengubah ukuran satu tingkat.
- **Kembali ke beranda saat subtitle berjalan** (r30): di bawah layar subtitle ada “Kembali ke beranda”. Subtitle tidak berhenti; di bagian atas beranda muncul tombol untuk membuka lagi layar subtitle.
- **Menekan “Berhenti”** (r30): halaman menanyakan “Lanjutkan rapat” atau “Akhiri subtitle”, jadi salah tekan tidak langsung menghentikan sesi.
- **Saat pertama kali membuka halaman** hanya panduan yang muncul; saran pembaruan dan pemasangan menunggu sampai lain kali, dan tidak pernah muncul saat subtitle berjalan.

---

## Subtitle tidak muncul? Uji suara dulu (r24)

Di halaman subtitle langsung, buka "**🔊 Suara dan mikrofon: uji dan pilih perangkat**":

1. Tekan "**Mulai uji**": komputer memutar nada pendek; ucapkan juga beberapa kata ke mikrofon.
2. Perhatikan dua batang:
   - **Suara yang diputar komputer ini** bergerak = ucapan lawan bicara tertangkap. Jika tidak: speaker dibisukan, volume 0, atau Teams bersuara lewat headset lain (pilih di "Lanjutan").
   - **Mikrofon** bergerak = ucapan Anda tertangkap. Jika tidak: mikrofon dibisukan, atau pilih mikrofon lain di daftar bawah (misalnya mikrofon konferensi USB).
3. Mikrofon dan speaker yang dipilih diingat dan berlaku mulai subtitle berikutnya. "Otomatis" cocok untuk kebanyakan orang; mengikuti perangkat bawaan Windows.

Mikrofon tidak dipakai jika Anda hanya membaca subtitle; dipakai pada "Saya juga berbicara", "satu ruang kelas", dan "komputer subtitle ruang rapat". Uji tidak bisa dilakukan saat subtitle berjalan; tekan Berhenti dulu.

## Saran saat halaman dibuka (r25)

Saat halaman dibuka, program melihat komputer ini dan bahasa yang terakhir Anda pilih. Saran hanya muncul bila perlu, satu per satu:

- **“Komputer ini punya kartu grafis NVIDIA”**: komputer punya kartu grafis tetapi paket GPU belum dipasang. Tekan “**Unduh paket**”, klik dua kali berkas yang diunduh untuk memasangnya (tidak perlu hak administrator), lalu buka lagi program. Subtitle lebih cepat dan komputer lebih ringan.
- **“Disarankan memasang model suara yang lebih akurat”**: misalnya, jika Anda sering memilih bahasa Vietnam sebagai bahasa lawan bicara, model khusus bahasa Vietnam disarankan; dengan kartu grafis dan bahasa Mandarin, disarankan Breeze ASR 25 (Mandarin Taiwan). Tekan “**Pasang**” dan model diunduh otomatis; dipakai mulai subtitle berikutnya.
- Belum sempat? Tekan “**Nanti saja**” (diingatkan lagi setelah 7 hari). Tidak mau lagi? Tekan “**Jangan ingatkan lagi**”.
- Jika jendela menulis “Minta IT”, komputer ini dipasang oleh IT: sampaikan isi jendela itu ke IT.

## Tips

- Bicara jelas, satu per satu, mikrofon dekat pembicara. Isi topik rapat jika banyak istilah teknis.
- Bagian atas halaman menunjukkan di mana suara dan teks diproses. Periksa sebelum rapat rahasia.
- **Ada masalah**: klik “Laporkan masalah” di bagian bawah halaman, tulis apa yang terjadi, lalu tekan “Buat laporan”. File zip akan diunduh; kirim ke IT (jika IT sudah mengaturnya, halaman menampilkan tujuan dan tombol “Email IT”). Isinya versi, spesifikasi komputer, dan log program, tanpa rekaman, transkrip, atau notulen.
