# Penerjemah Rapat PCG: contoh penggunaan

[中文](使用情境.md) · [English](USE-CASES-en.md) · [Bahasa Indonesia](USE-CASES-id.md) · [Tiếng Việt](USE-CASES-vi.md)

Subtitle langsung membedakan bahasa **dari sumber suara**:

- **Suara yang diputar komputer** (lawan bicara di Teams/Zoom, video) = bahasa lawan bicara
- **Mikrofon** (jika "Saya juga akan berbicara" dicentang) = bahasa Mandarin Anda sendiri

Jadi hanya **komputer yang menjalankan rapat atau kelas** yang perlu memasang aplikasi. Pihak lain tidak perlu memasang apa pun.

## 1. Rapat atau kelas online: Mandarin ⇄ bahasa lain

> Contoh: pengajar berbicara bahasa Mandarin, siswa Indonesia menjawab dalam bahasa Indonesia, semua di Teams.

**Siapa yang memasang**: hanya komputer pengajar. Siswa ikut Teams/Zoom seperti biasa.

1. Di komputer pengajar: "Penerjemah Rapat PCG" → "Subtitle langsung".
2. Pilih "**Bahasa Indonesia**" (lawan bicara), centang "**Saya juga akan berbicara (dua arah)**", klik Mulai.
3. **Pakai headphone**, agar suara siswa dari speaker tidak masuk ke mikrofon dan dianggap bahasa Mandarin.

Subtitle: bahasa Mandarin pengajar → Mandarin + terjemahan Indonesia; bahasa Indonesia siswa → Indonesia + terjemahan Mandarin.

**Agar siswa melihat subtitle** (pilih salah satu):
- **Bagikan layar** (di mana saja): centang "Subtitle selalu di atas" dan bagikan layar di Teams.
- **Ponsel** (siswa di jaringan perusahaan): klik "Bagikan", siswa memindai kode QR, memasukkan kata sandi staf, lalu memilih bahasa. IT harus mengaktifkan "Izinkan komputer dan ponsel lain melihat subtitle".

**Siswa ingin melihat subtitle di komputer sendiri** (mulai v2026.11.5.r9): pasang aplikasi di komputer siswa, buka "Subtitle langsung", pilih "**Mandarin → Indonesia**" (juga ada Vietnam, Hindi, Inggris), klik Mulai. Siswa hanya mendengar, jadi tidak perlu dua arah dan tidak perlu headphone. Aplikasi menangkap suara pengajar dari Teams dan menampilkannya dalam bahasa Indonesia; komputer pengajar tetap memakai dua arah. Tidak perlu berbagi layar; setiap orang membaca bahasanya sendiri.

## 2. Hanya ingin memahami lawan bicara

Pilih bahasa lawan bicara, **jangan** centang "Saya juga akan berbicara", klik Mulai. Tidak perlu headphone.

## 3. Satu ruang rapat atau kelas, satu mikrofon (mode kelas)

> Contoh: pengajar dan siswa Indonesia berbicara di kelas yang sama. (mulai v2026.11.5.r9)

1. Pasang mikrofon yang bisa menangkap suara seluruh ruangan (mikrofon rapat atau mikrofon meja).
2. "Subtitle langsung" → pilih "**Bahasa Indonesia**" → centang "**Mode kelas**" → Mulai. (Vietnam, Hindi, dan Inggris juga bisa.)
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

## Tips

- Bicara jelas, satu per satu, mikrofon dekat pembicara. Isi topik rapat jika banyak istilah teknis.
- Bagian atas halaman menunjukkan di mana suara dan teks diproses. Periksa sebelum rapat rahasia.
- Versi ada di bagian bawah halaman; klik untuk menyalin saat melaporkan masalah.
