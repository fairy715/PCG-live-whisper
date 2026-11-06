# Penerjemah Rapat PCG: panduan instalasi dan pembaruan

[中文](安裝說明.md) · [English](INSTALL-GUIDE-en.md) · [Bahasa Indonesia](INSTALL-GUIDE-id.md) · [Tiếng Việt](INSTALL-GUIDE-vi.md)

Versi terbaru: **https://github.com/fairy715/PCG-live-whisper/releases/latest**

Setiap halaman rilis berisi petunjuk yang sama dan menjelaskan apakah pembaruan kecil dapat digunakan.

Cara memakai untuk rapat online, kelas, dan notulen: lihat [contoh penggunaan](USE-CASES-id.md).

## 1. Unduh

1. Buka halaman rilis: https://github.com/fairy715/PCG-live-whisper/releases/latest
2. Di bagian "Assets" di bawah halaman, klik `PCG-Meeting-Translator-Setup-<versi>.exe` (sekitar 1,8 GB).
   * Jika browser memperingatkan bahwa file ini "tidak umum diunduh", pilih "Simpan" / "Keep" (Edge: klik "…" → "Simpan").
   * Filenya besar: IT juga bisa menaruhnya di folder bersama atau Google Drive untuk Anda.

## 2. Instal

1. Klik dua kali file exe yang sudah diunduh.
2. Muncul jendela biru "Windows melindungi PC Anda" ("Windows protected your PC"):
   * Klik "Info selengkapnya" ("More info"), lalu "Tetap jalankan" ("Run anyway").
   * Jendela ini selalu muncul pertama kali karena penginstal tidak memiliki sertifikat tanda tangan kode.
3. Jika muncul jendela pilihan bahasa, pilih bahasa lalu klik "OK" (biasanya sudah dipilih otomatis sesuai bahasa Windows).
4. Lokasi instalasi: bawaan `D:\PCG-live-whisper` (`C:\PCG-live-whisper` jika tidak ada drive D). Biarkan saja, klik tombol lanjut lalu "Instal".
   * Tidak perlu hak administrator dan tidak perlu internet.
5. Jendela menampilkan "Memasang runtime dan model". Proses ini sekitar 3–10 menit. Jangan ditutup.
6. Selesai: centang "Buka Penerjemah Rapat PCG sekarang", lalu klik "Selesai". Pintasan "Penerjemah Rapat PCG" dibuat di desktop.

## 3. Penggunaan pertama

1. Klik dua kali pintasan di desktop. Browser membuka halaman aplikasi (`http://localhost:19781/simple`).
2. Pertama kali akan ada tur panduan singkat. Ikuti sekali.
3. Bahasa halaman bisa diganti di kanan atas (中文 / English / Bahasa Indonesia / Tiếng Việt / हिन्दी).
4. Subtitle langsung: pilih bahasa Anda (Bahasa Indonesia) → "Mandarin → Indonesia" langsung terpilih → "Mulai". Rekaman: unggah file → setelah selesai diproses, unduh notulen rapat.
5. Versi ditampilkan di bagian bawah halaman (misalnya v2026.11.5.r5). Sertakan saat melaporkan masalah (klik untuk menyalin).

## 4. Pembaruan

**Tidak perlu** menghapus versi lama. Pengaturan, rekaman, dan transkrip tetap disimpan.

* **Pembaruan sekali klik (paling mudah)**: di komputer yang terhubung internet, atau jika IT sudah mengatur folder bersama, muncul pemberitahuan "Versi baru" di bagian atas halaman aplikasi. Klik "Perbarui sekarang"; halaman akan dimuat ulang otomatis setelah 1–2 menit.

* **Pembaruan kecil** (`PCG-Update-….exe`, sekitar 10 MB): tutup Penerjemah Rapat PCG → klik dua kali file pembaruan → jika jendela biru muncul, "Info selengkapnya" → "Tetap jalankan" → selesai dalam sekitar 1 menit.
  * Jika muncul pesan bahwa pembaruan ini "memerlukan komponen baru yang hanya ada di penginstal lengkap", gunakan penginstal lengkap.
* **Penginstal lengkap**: cukup instal di atas versi lama.
* Distribusi massal oleh IT (tanpa jendela): tambahkan `/VERYSILENT /SUPPRESSMSGBOXES /NORESTART` setelah nama file exe.
* File `.sha256` di halaman rilis adalah "sidik jari" file pembaruan, untuk memastikan file lengkap dan tidak diubah. **Karyawan tidak perlu mengunduhnya.**
  * Saat IT menaruh pembaruan kecil di folder bersama, taruh file `.exe` dan file `.sha256` dengan nama yang sama **bersamaan**: pembaruan sekali klik akan mencocokkan sidik jari dulu, dan tidak menginstal jika tidak cocok (misalnya unduhan terputus).
  * Pembaruan sekali klik dari GitHub tidak memerlukan file ini; sidik jari dibaca langsung dari halaman rilis.

## 5. Jika ada masalah

* Instalasi gagal: kirim file `D:\PCG-live-whisper\group_data\install.log` (jika pembaruan gagal: `update.log`) ke IT.
* Diblokir antivirus: minta IT menambahkan folder instalasi sebagai pengecualian.
* Hapus instalasi: Windows "Pengaturan" → "Aplikasi" → "PCG Meeting Translator" → "Copot pemasangan". Rekaman, transkrip, dan pengaturan tetap ada di folder; hapus manual jika sudah tidak diperlukan.

## Untuk IT

* **Halaman Pengaturan IT**: di komputer staf, klik "Pengaturan IT" di bagian bawah halaman aplikasi, atau buka `http://localhost:19781/simple/admin`.
  * Pertama kali: buat kata sandi IT di komputer tersebut (minimal 6 karakter). Setelah itu selalu diminta. Staf tidak perlu mengetahuinya.
  * Yang dapat diubah: mode lokal/server, LLM (Open WebUI grup, server internal, atau layanan AI eksternal) dan kunci API, server GPU, model pengenalan suara, kata sandi staf, dan izin komputer lain untuk melihat subtitle.
  * Langsung berlaku setelah disimpan, tanpa instal ulang. Detail di [INSTALL.md](INSTALL.md) (bahasa Mandarin).
