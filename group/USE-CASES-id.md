# Penerjemah Rapat PCG: contoh penggunaan

[中文](使用情境.md) · [English](USE-CASES-en.md) · [Bahasa Indonesia](USE-CASES-id.md) · [Tiếng Việt](USE-CASES-vi.md)

Subtitle langsung membedakan bahasa **dari sumber suara**:

- **Suara yang diputar komputer** (lawan bicara di Teams/Zoom, video) = bahasa lawan bicara
- **Mikrofon** (jika memilih "saya juga berbicara") = bahasa Anda sendiri

Jadi hanya **komputer yang menjalankan rapat atau kelas** yang perlu memasang aplikasi. Pihak lain tidak perlu memasang apa pun.

## Memilih opsi yang tepat (mulai versi r11)

"Subtitle langsung" menanyakan tiga hal secara berurutan, dan hanya opsi yang cocok untuk Anda yang tetap tampil:

1. **Anda berbicara bahasa apa?** Karyawan Taiwan memilih "中文"; karyawan Indonesia, Vietnam, dan India memilih bahasanya sendiri.
2. **Jenis rapat apa?**
   - Rapat atau kelas online, saya hanya membaca subtitle
   - Rapat atau kelas online, saya juga berbicara (pakai headset)
   - Satu ruang kelas, satu mikrofon
3. **Lawan bicara berbahasa apa?** Jika Anda memilih bahasa Indonesia, Anda melihat "Mandarin → Indonesia" dan bahasa asing lain (mulai r17; mis. "Bahasa Vietnam, ke Indonesia").

Pilihan terakhir Anda akan diingat. Jika opsi yang dicari tidak muncul, klik "Tampilkan semua pilihan".

**"Bahasa Indonesia" dan "Mandarin → Indonesia": apa bedanya?**

| Opsi | Yang didengar | Subtitle dalam | Komputer siapa | Bisa ditambah |
|---|---|---|---|---|
| Bahasa Indonesia (lawan bicara berbahasa Indonesia) | Bahasa Indonesia | Mandarin | Karyawan Taiwan yang tidak mengerti bahasa Indonesia | Saya juga berbicara (dua arah), mode kelas |
| Mandarin → Indonesia | Mandarin | Bahasa Indonesia | Karyawan Indonesia yang tidak mengerti pengajar atau atasan berbahasa Mandarin | Mode kelas |
| Bahasa Vietnam, ke Indonesia (r17) | Bahasa Vietnam | Bahasa Indonesia | Karyawan Indonesia yang rapat dengan karyawan Vietnam | Saya juga berbicara (dua arah), mode kelas |

Contoh: Guru Lin mengajar Budi di Indonesia lewat Teams.
- Komputer Guru Lin: saya berbicara "中文" → "saya juga berbicara" → "Bahasa Indonesia".
- Komputer Budi: saya berbicara "Bahasa Indonesia" → "Mandarin → Indonesia" langsung terpilih.

Cara mengingat: nama opsi adalah bahasa **lawan bicara**; subtitle muncul dalam bahasa **Anda**. Vietnam, Hindi, dan Inggris juga sama.

## 1. Rapat atau kelas online: Mandarin ⇄ bahasa lain

> Contoh: pengajar berbicara bahasa Mandarin, siswa Indonesia menjawab dalam bahasa Indonesia, semua di Teams.

**Siapa yang memasang**: hanya komputer pengajar. Siswa ikut Teams/Zoom seperti biasa.

1. Di komputer pengajar: "Penerjemah Rapat PCG" → "Subtitle langsung".
2. Saya berbicara "**中文**" → jenis rapat "**Rapat atau kelas online, saya juga berbicara (pakai headset)**" → "**Bahasa Indonesia**", klik Mulai.
3. **Pakai headphone**, agar suara siswa dari speaker tidak masuk ke mikrofon dan dianggap bahasa Mandarin.

Subtitle: bahasa Mandarin pengajar → Mandarin + terjemahan Indonesia; bahasa Indonesia siswa → Indonesia + terjemahan Mandarin.

**Agar siswa melihat subtitle** (pilih salah satu):
- **Bagikan layar** (di mana saja): centang "Subtitle selalu di atas" dan bagikan layar di Teams.
- **Ponsel** (siswa di jaringan perusahaan): klik "Bagikan", siswa memindai kode QR, memasukkan kata sandi staf, lalu memilih bahasa. IT harus mengaktifkan "Izinkan komputer dan ponsel lain melihat subtitle".

**Siswa ingin melihat subtitle di komputer sendiri** (mulai v2026.11.5.r9): pasang aplikasi di komputer siswa, buka "Subtitle langsung", pilih saya berbicara "**Bahasa Indonesia**": "**Mandarin → Indonesia**" langsung terpilih (Vietnam, Hindi, Inggris juga sama). Klik Mulai. Siswa hanya mendengar, jadi tidak perlu headphone. Aplikasi menangkap suara pengajar dari Teams dan menampilkannya dalam bahasa Indonesia; komputer pengajar tetap memakai dua arah. Tidak perlu berbagi layar; setiap orang membaca bahasanya sendiri.

## 2. Hanya ingin memahami lawan bicara

Saya berbicara "中文" → jenis rapat "**Rapat atau kelas online, saya hanya membaca subtitle**" → bahasa lawan bicara, klik Mulai. Tidak perlu headphone.

## 3. Satu ruang rapat atau kelas, satu mikrofon (mode kelas)

> Contoh: pengajar dan siswa Indonesia berbicara di kelas yang sama. (mulai v2026.11.5.r9)

1. Pasang mikrofon yang bisa menangkap suara seluruh ruangan (mikrofon rapat atau mikrofon meja).
2. "Subtitle langsung" → saya berbicara "中文" → jenis rapat "**Satu ruang kelas, satu mikrofon**" → "**Bahasa Indonesia**" → Mulai. (Vietnam, Hindi, dan Inggris juga bisa.)
3. Tampilkan subtitle di proyektor, atau siswa memindai kode QR dari "Bagikan".

Setiap kalimat dikenali otomatis sebagai Mandarin atau Indonesia: Mandarin → Mandarin + terjemahan Indonesia; Indonesia → Indonesia + terjemahan Mandarin.

**Keterbatasan**
- Paling baik **satu orang berbicara bergantian**; bicara bersamaan atau kalimat campuran dikenali kurang baik.
- **Jawaban sangat pendek** ("ok", "ya") bisa salah dikenali bahasanya.
- Subtitle **sedikit lebih lambat** karena bahasa setiap kalimat dikenali dulu.
- Mode kelas memakai pengenalan suara di komputer ini (bukan server GPU) dengan model lokal yang diatur IT.
- "Mode kelas" dan "Saya juga akan berbicara" pilih salah satu: kelas online → "Saya juga akan berbicara" + headphone; satu ruangan → mode kelas.

## 4. Banyak orang ingin membaca subtitle di ponsel

1. IT mengaktifkan "Izinkan komputer dan ponsel lain melihat subtitle" dan membuat kata sandi staf (lalu aplikasi dibuka ulang).
2. Mulai subtitle langsung, klik "Bagikan", tampilkan kode QR.
3. Peserta memindai, memasukkan kata sandi staf, dan memilih bahasa (hanya melihat). Ponsel harus terhubung ke komputer itu, biasanya di jaringan perusahaan.

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
- Pilih "saya hanya membaca subtitle", atau "saya juga berbicara (pakai headset)" agar terjemahan ucapan Anda juga tampil.

**Satu ruang rapat, satu mikrofon**: di satu komputer pilih bahasa Anda → "Satu ruang kelas, satu mikrofon" → bahasa lawan bicara. Setiap kalimat dikenali lalu diterjemahkan ke bahasa lainnya; gunakan "Bagikan" agar orang lain bisa mengikuti di ponsel dalam bahasa pilihannya.

**Kualitas**
- Secara bawaan hanya model dasar yang dipakai: Whisper small untuk pengenalan suara dan M2M100 di komputer untuk terjemahan. Pengenalan bahasa Indonesia dan Vietnam bisa salah, dan terjemahan ikut salah.
- Agar lebih akurat, IT dapat memasang paket model bahasa (membantu untuk "saya hanya membaca subtitle") atau beralih ke mode server di halaman pengaturan IT agar diterjemahkan oleh model bahasa besar.
- Notulen dari rekaman masih ditulis dalam bahasa Mandarin.

---

## Tips

- Bicara jelas, satu per satu, mikrofon dekat pembicara. Isi topik rapat jika banyak istilah teknis.
- Bagian atas halaman menunjukkan di mana suara dan teks diproses. Periksa sebelum rapat rahasia.
- **Ada masalah**: klik “Laporkan masalah” di bagian bawah halaman, tulis apa yang terjadi, lalu tekan “Buat laporan”. File zip akan diunduh; kirim ke IT (jika IT sudah mengaturnya, halaman menampilkan tujuan dan tombol “Email IT”). Isinya versi, spesifikasi komputer, dan log program, tanpa rekaman, transkrip, atau notulen.
