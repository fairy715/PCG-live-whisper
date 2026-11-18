# Edisi grup PCG: arsitektur dan instalasi (untuk IT)

[中文](INSTALL.md) · [English](IT-GUIDE-en.md) · [Bahasa Indonesia](IT-GUIDE-id.md) · [Tiếng Việt](IT-GUIDE-vi.md)

<!-- Jika panduan ini diubah, perbarui keempat bahasa (INSTALL.md, IT-GUIDE-en.md, IT-GUIDE-id.md, IT-GUIDE-vi.md). -->

## Arsitektur

```
                         ┌──────────────── Jaringan perusahaan ─────────┐
                         │                                              │
  Komputer karyawan (browser) │ ① Server aplikasi (Linux, tanpa GPU)    │
  ───────────────────    │   ─────────────────────────────              │
  http://server-aplikasi:19781/simple ─→ WebUI (termasuk halaman /simple) │
  unggah rekaman → unduh notulen │ antrean: satu per satu, sisanya menunggu │
                         │   penyimpanan: recordings/, hasil logs/      │
                         │        │ pengenalan suara   │ terjemahan/ringkasan │
                         │        ▼                     ▼              │
                         │   ② Host GPU (Ubuntu + NVIDIA)               │
                         │   ─────────────────────────────              │
                         │   Layanan pengenalan suara GPU (port 8978)   │
                         │   LLM Ollama (port 11434)                    │
                         │     terjemahan gemma4:26b, ringkasan qwen3.8:27b │
                         │        ▲                     ▲              │
  ③ Komputer karyawan yang perlu subtitle langsung ─┘───┘              │
  (dipasang di masing-masing Windows/Mac)                               │
  menangkap suara yang diputar di PC itu → http://localhost:19781/simple │
                         └──────────────────────────────────────────────┘
```

| Peran | Fungsi | Perangkat keras yang disarankan |
|---|---|---|
| ① Server aplikasi | Halaman web, antrean pekerjaan, menyimpan rekaman dan notulen | Linux (Ubuntu 22.04 / Debian 12 ke atas), 2 vCPU, RAM 4 GB, disk sesuai volume rekaman (satu jam m4a sekitar 30–60 MB) |
| ② Host GPU | Pengenalan suara, terjemahan, ringkasan (bagian paling berat) | NVIDIA DGX Spark, atau RTX 4090/5090 (VRAM 24 GB ke atas) + RAM 64 GB; menjalankan pengenalan suara dan LLM sekaligus |
| ③ Komputer karyawan | Hanya yang perlu **subtitle langsung** yang memasang | Windows 10/11 atau Mac; pengenalan suara dan terjemahan dikerjakan ②, jadi PC kantor biasa sudah cukup |

- **Mode lokal dan server internal: suara dan teks tidak keluar dari jaringan perusahaan.** Dengan Open WebUI grup, teks dikirim ke model di belakangnya (pastikan luna/deepseek berada di dalam grup); dengan "Layanan AI eksternal", data keluar perusahaan (lihat "Mode server: tiga cara menghubungkan LLM" di bawah)
- ① dan ② boleh satu mesin, tetapi penulis asli menyarankan dipisah: saat host GPU menjalankan LLM, halaman web dan pengolahan file lebih stabil di mesin lain
- Subtitle langsung harus berjalan di ③ sendiri: yang ditangkap adalah **suara yang diputar di komputer itu** (Teams, Zoom), dan server tidak bisa mendapatkannya

## Sebelum memasang

1. **Jangan gunakan perintah instalasi satu baris dari penulis asli** (`curl … jasoncheng7115 … | bash`, `irm … | iex`): yang terpasang adalah versi asli, tanpa bahasa baru dan halaman sederhana
2. **Jangan memperbarui dengan `./install.sh --upgrade`**: perintah ini mengunduh versi asli dan menimpa edisi grup (edisi grup sudah memblokirnya dan menyarankan git pull)
3. Repositori bisa bersifat privat: mengunduh memerlukan akses GitHub (akun, atau minta administrator membuat deploy key hanya-baca)

## ② Host GPU

1. Pasang driver NVIDIA dan CUDA (`nvidia-smi` menampilkan kartu grafis)
2. Pasang Ollama dan unduh modelnya:
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ollama pull gemma4:26b       # terjemahan
   ollama pull qwen3.8:27b      # ringkasan, koreksi transkrip
   ```
   Agar bisa dijangkau di LAN: tambahkan `OLLAMA_HOST=0.0.0.0` di pengaturan systemd Ollama, dan buka firewall hanya untuk ① dan subnet komputer karyawan
3. Layanan pengenalan suara GPU **tidak perlu dipasang manual**: di akhir instalasi ① akan ditanya tentang server GPU; masukkan alamat host dan layanan dipasang otomatis lewat SSH

## ① Server aplikasi

```bash
# 1. Unduh edisi grup (sebagai pengguna biasa, bukan root)
mkdir -p ~/Apps
git clone https://github.com/fairy715/PCG-live-whisper.git ~/Apps/jt-live-whisper
cd ~/Apps/jt-live-whisper

# 2. Pasang sebagai server (WebUI berjalan sebagai layanan systemd jt-live-whisper-webui)
bash install.sh --server
```

Selama instalasi:
- `sudo apt` menambahkan paket sistem seperti ffmpeg
- **"Kata sandi admin" dan "kata sandi hanya-baca" dicetak sekali saja: segera catat**
- Di akhir akan ditanya server GPU: masukkan alamat ②, layanan pengenalan suara GPU dipasang lewat SSH
- Server LLM: atur alamat Ollama ② di WebUI (`http://server-aplikasi:19781`, dengan kata sandi admin), atau tulis sebagai `llm_host` di `config.json`

### Halaman pengaturan IT (tanpa mengedit file konfigurasi)

Buka halaman pengaturan IT **di komputer yang ingin diatur** ("Pengaturan IT" di bagian bawah halaman sederhana):

- Komputer karyawan (dipasang dengan penginstal offline): `http://localhost:19781/simple/admin`
- Server aplikasi: `http://server-aplikasi:19781/simple/admin`

1. **Pertama kali**: buka di komputer itu dan buat kata sandi IT (minimal 6 karakter). Setelah itu selalu diminta, juga secara lokal
2. **Mode**: mode lokal (CPU, terjemahan M2M100, tanpa notulen AI) / mode server (server LLM menerjemahkan dan membuat notulen AI; server GPU opsional)
3. **Alamat server**: isi URL server LLM (wajib) dan server GPU (opsional) → klik "Tes koneksi" → model di server ditampilkan untuk dipilih.
   Tanpa server GPU, pengenalan suara tetap di komputer ini (memakai "model pengenalan lokal"); hanya terjemahan dan notulen yang dikirim ke LLM
4. **Kata sandi karyawan**: diminta saat terhubung dari komputer lain (tidak untuk lokal)
5. Klik "Simpan": berlaku saat subtitle atau rekaman berikutnya dimulai; tidak perlu restart

Pengaturan disimpan di `config.json` yang sama (kata sandi berupa hash), dengan format yang sama seperti program asli.

### Pembaruan sekali klik

"Pembaruan" di halaman pengaturan IT:

- **Periksa versi baru** (aktif secara bawaan): jika ada pembaruan kecil baru, karyawan melihat "Versi baru" dan "Perbarui sekarang" di atas halamannya
- **Siapa yang boleh memperbarui**: karyawan sendiri (bawaan) / hanya IT (perlu kata sandi IT)
- **Sumber pembaruan**:
  1. **Folder bersama perusahaan** (opsional, misalnya `\\fileserver\PCG\update`): taruh `PCG-Update-<versi>.exe` dan file `.sha256` dengan nama yang sama dari halaman rilis di sana. Komputer tanpa internet yang bisa menjangkau jaringan perusahaan juga bisa memperbarui sekali klik
  2. **Halaman rilis GitHub**: dipakai otomatis oleh komputer yang terhubung internet (tidak bisa dipakai jika repositori dijadikan privat; gunakan folder bersama)
- Setelah klik perbarui: unduh (atau salin dari folder bersama) → cocokkan sidik jari file, hapus dan jangan pasang jika tidak cocok → tutup aplikasi → pasang → pemeriksaan mandiri → buka kembali otomatis; halaman yang terbuka dimuat ulang sendiri
- Tidak bisa memperbarui saat subtitle langsung atau pemrosesan rekaman berjalan; versi yang memerlukan penginstal lengkap hanya menampilkan "hubungi IT"
- Log: `group_data\update.log`; file unduhan: `group_data\updates\`
- **File sidik jari `.sha256`**: setiap pembaruan kecil memiliki file `.sha256` dengan nama yang sama, berisi sidik jari SHA-256 dari exe tersebut (satu baris, 64 karakter)
  - Folder bersama: taruh `.exe` dan `.sha256` bersamaan; sidik jari dicocokkan sebelum memasang dan pembaruan ditolak jika tidak cocok; tanpa `.sha256` tetap terpasang, tetapi tanpa pemeriksaan
  - GitHub: file ini tidak diperlukan; aplikasi membaca sidik jari aset rilis langsung, dan tidak memasang jika tidak ada
  - Pemeriksaan manual (PowerShell): `Get-FileHash .\PCG-Update-<versi>.exe -Algorithm SHA256`; file utuh jika hash sama dengan isi `.sha256` (huruf besar/kecil tidak berpengaruh)
- **Jendela fitur baru** (pembaruan setelah r19): saat staf membuka halaman, jendela "Ada versi baru" menampilkan fitur baru versi ini, dengan pilihan "Perbarui sekarang" atau "Nanti saja"; "Nanti saja" tetap menampilkan pemberitahuan pembaruan di atas halaman seperti biasa dan jendela tidak muncul lagi sampai halaman dibuka berikutnya. Di folder bersama Anda bisa menaruh juga `PCG-Update-<versi>.whats-new.json` (halaman rilis menyertakan `whats-new.json`; cukup ganti namanya); tanpa file itu hanya nomor versi yang ditampilkan

### Mode server: tiga cara menghubungkan LLM

"Jenis server" di halaman pengaturan IT:

| Jenis | Kapan dipakai | URL | Kunci API |
|---|---|---|---|
| Open WebUI grup | Sekarang (luna, deepseek) | Alamat Open WebUI yang dibuka di browser | Wajib |
| Server internal | Setelah RTX Spark / DGX Spark tersedia, atau Ollama, vLLM sendiri | `host:11434` | Biasanya tidak perlu |
| Layanan AI eksternal | OpenAI, DeepSeek, Google Gemini, OpenRouter, dll. | Klik tombol untuk mengisi base URL | Wajib |

Server GPU (pengenalan suara) terpisah dari LLM; kombinasi apa pun bisa, misalnya LLM di Open WebUI grup dan pengenalan suara di RTX Spark sendiri.
Jika server GPU sudah diisi tetapi sedang tidak bisa dijangkau, pengenalan suara otomatis beralih ke model kecil di komputer karyawan, jadi tidak macet.

#### Open WebUI grup (luna, deepseek)

1. Buat kunci API di Open WebUI: masuk → avatar di kanan atas → Settings → Account → API keys → Create
   (Tidak ada opsi ini: minta administrator AI grup mengizinkan API Keys di "Admin settings → User permissions")
2. Halaman pengaturan IT: mode "Mode server", jenis "Open WebUI grup", isi URL (misalnya `https://ai.domain-perusahaan`), tempel kuncinya
3. Klik "Tes koneksi" dan pilih dari daftar: **terjemahan: luna** (cepat, subtitle langsung tidak tertunda), **notulen: deepseek** (model penalaran, lambat tetapi lengkap)
4. Tanpa server GPU, kosongkan kolom GPU: pengenalan suara berjalan di CPU komputer karyawan (model small)

Catatan: kunci bersifat **pribadi** dan pemakaian dicatat atas nama pemiliknya; disarankan memakai akun khusus. Komputer karyawan harus bisa menjangkau alamat Open WebUI.

#### Server internal (RTX Spark, DGX Spark)

Setelah tersedia, satu mesin bisa menjadi "LLM" sekaligus "pengenalan suara GPU":

- **LLM**: pasang Ollama di Spark, unduh modelnya dan buat bisa dijangkau di LAN (`OLLAMA_HOST=0.0.0.0`). Di halaman pengaturan IT pilih jenis "Server internal" dan isi `IP-Spark:11434`
- **Pengenalan suara GPU**: Spark menjalankan layanan pengenalan suara GPU dari penulis asli (`remote_whisper_server.py`, mendukung DGX Spark aarch64).
  Isi `IP-Spark` dan port `8978` di "Server GPU" pada halaman pengaturan IT
  - DGX Spark (DGX OS / Ubuntu): jalankan `bash install.sh` dari mesin Linux atau Mac; saat ditanya server GPU, isi alamat Spark; layanan dipasang lewat SSH dan diatur berjalan saat boot
  - Laptop RTX Spark (Windows on Arm): layanan pengenalan suara hanya ada untuk Linux dan harus dipasang di WSL2; **uji setelah perangkat tiba**
- Komputer karyawan menjangkau layanan GPU **hanya lewat URL**; tidak perlu dan tidak memakai SSH (layanan berjalan dengan systemd di Spark)
- LLM tanpa pengenalan suara GPU juga bisa: terjemahan dan notulen tetap berjalan

#### Layanan AI eksternal (OpenAI, DeepSeek, Gemini…)

- **Isi rapat keluar dari perusahaan** dan ditagih sesuai pemakaian: pastikan dulu sesuai aturan data perusahaan; gunakan Open WebUI atau server internal untuk rapat rahasia
- Ajukan kunci dengan akun perusahaan dan atur batas pemakaian bulanan di situs layanannya
- Pilih jenis "Layanan AI eksternal" → klik OpenAI / DeepSeek / Google Gemini / OpenRouter untuk mengisi URL → tempel kunci → Tes koneksi → pilih model
- Layanan lain yang kompatibel dengan OpenAI juga bisa: isi base URL dari dokumentasinya (biasanya diakhiri `/v1`). Azure OpenAI tidak didukung (cara autentikasi berbeda); gunakan OpenRouter atau proxy LiteLLM

Kolom konfigurasi (untuk pemecahan masalah): `llm_url`, `llm_api_key`, `llm_api_style` (`openwebui` / `openai` / kosong = internal, dideteksi otomatis), `remote_whisper.host`.

Disarankan juga membatasi IP sumber (hanya subnet perusahaan) di "Pengaturan keamanan" pada WebUI lengkap.

**URL untuk karyawan: `http://server-aplikasi:19781/simple`** (WebUI lengkap ada di `/`, untuk IT)

## Instalasi offline di komputer karyawan (bisa tanpa internet atau server GPU)

**Lihat [windows/README.md](windows/README.md)**: penginstal tunggal, secara bawaan mode lokal (CPU);
jika nanti ada server GPU, IT cukup mengganti di `/simple/admin`. "③" di bawah adalah cara instalasi lain jika ada internet.

### Pemakaian CPU (saat komputer karyawan mengenali suara secara lokal)

Saat subtitle langsung dan rekaman diproses di CPU komputer karyawan (mode lokal, atau mode server yang hanya terhubung ke server LLM):

- Pengenalan suara + terjemahan lokal bersama-sama memakai sekitar **3/4 inti**, tidak pernah lebih dari jumlah inti fisik (laptop 4 inti: pengenalan 2–3, terjemahan 1), menyisakan ruang untuk Teams dan program lain
- Di Windows prosesnya berjalan dengan prioritas **di bawah normal**: saat CPU sibuk, program di depan didahulukan, sehingga Teams dan mouse tidak tersendat
  - **Otomatis kembali ke normal saat subtitle tertinggal** (r20): jika satu potongan suara belum selesai dikenali lebih dari 6 detik (misalnya video Teams memakai seluruh CPU), prioritas sementara dikembalikan ke normal; subtitle sedikit lebih lambat tetapi tetap muncul. Setelah 30 detik berturut-turut lancar, prioritas diturunkan lagi. Sebelumnya, di laptop 2 inti dengan Teams terbuka subtitle berhenti total dan baru muncul sekaligus setelah Teams ditutup
  - **Laptop hemat daya 2 inti 4 utas** (misalnya i3-10110U): pengenalan suara memakai 2 utas (sebelumnya 1)
- **Memotong ucapan saat jeda** (r21, bawaan subtitle langsung lokal): sebelumnya 5 detik suara terakhir dikenali ulang setiap 3 detik (setiap potongan suara 1,7 kali); sekarang suara dipotong saat pembicara berhenti dan dikenali sekali, dan terjemahan menunggu kalimat selesai. Pada uji dengan 38 detik bahasa Inggris yang sama (Whisper base, 2 utas) CPU pengenalan turun dari 20,9 ke 13,3 detik (37% lebih sedikit), dan subtitle muncul sebagai kalimat utuh, bukan potongan yang berulang. Jika Whisper terjebak mengulang kalimat yang sama, potongan itu dikenali sekali lagi dengan suhu berbeda dan sisa pengulangan disimpan sekali saja. Untuk kembali ke cara lama: variabel lingkungan sistem Windows `PCG_LIVE_SEGMENT=window` (mulai ulang program setelahnya)
- **Model subtitle langsung lokal "Otomatis"** (bawaan mulai r21): komputer 2 inti memakai paket **Whisper base** jika terpasang (jika tidak, small bawaan, dan halaman Pengaturan IT menyarankan memasangnya); komputer dengan paket GPU yang lulus pemeriksaan memakai paket large-v3-turbo atau medium jika terpasang; lainnya memakai small bawaan. Halaman Pengaturan IT menampilkan model yang dipakai komputer ini. Komputer yang sebelumnya menyimpan small tetap memakai small; pilih "Otomatis (disarankan)" lalu simpan untuk beralih
- Komputer lama masih berat, subtitle tertinggal: pasang dulu paket **Whisper base (multibahasa)** di "Model", lalu pilih sebagai "Model subtitle langsung lokal" (lebih cepat, lebih banyak salah). **Aplikasi tidak pernah mengunduh model sendiri** (instalasi offline tidak mengunduh), jadi halaman pengaturan hanya menampilkan model yang ada di komputer ini
- Penyesuaian (variabel lingkungan sistem Windows, lalu buka ulang aplikasi):
  - `PCG_CPU_THREADS=8`: jumlah total thread (misalnya PC desktop kuat yang ingin berjalan penuh)
  - `PCG_NORMAL_PRIORITY=1`: kembali ke prioritas normal

### API pengenalan suara (r24, opsional)

"**API pengenalan suara**" di halaman Pengaturan IT menyerahkan pengenalan suara ke API yang kompatibel dengan OpenAI (`/audio/transcriptions`). Biasanya lebih akurat daripada model kecil di komputer staf, dan laptop tidak perlu menjalankan pengenalan.

| Tujuan | Alamat | Ke mana suara dikirim | Biaya |
|---|---|---|---|
| OpenAI | `https://api.openai.com/v1`, model misalnya `gpt-4o-transcribe`, `gpt-4o-mini-transcribe`, `whisper-1` | **Keluar dari perusahaan** | Ditagih menurut durasi suara sesuai harga resmi OpenAI; setiap komputer yang menampilkan subtitle dihitung sendiri |
| Groq (r26) | `https://api.groq.com/openai/v1`, model `whisper-large-v3-turbo` (bawaan) atau `whisper-large-v3` | **Keluar dari perusahaan** | Ada kuota gratis dengan batas pemakaian (lihat di bawah); dapatkan kunci di [console.groq.com/keys](https://console.groq.com/keys) |
| Layanan pengenalan di dalam perusahaan (RTX Spark, atau server kompatibel OpenAI milik tim lain) | Misalnya `http://10.x.x.x:8000/v1` | Tetap di dalam perusahaan | Tanpa biaya tambahan |

- Isi alamat, model, dan kunci (layanan internal boleh tanpa kunci), lalu tekan "**Uji koneksi**": satu detik senyap dikirim untuk memeriksa alamat, kunci, dan model
- **Layanan eksternal harus memakai https dan kunci**; alamat dengan IP internal atau nama host biasa dianggap internal, dan untuk layanan internal dengan nama domain centang "Ini layanan di dalam perusahaan"
- Jika aktif: setiap kalimat subtitle langsung (potongan yang dipotong saat jeda) dikirim sekali; rekaman dipotong saat jeda menjadi potongan paling lama 25 detik. **Didahulukan daripada server GPU**, dan bahasa Inggris juga dikirim ke API (Moonshine tidak dipakai)
- **Jika API tidak terjangkau, terlalu lama, atau kuncinya salah**: potongan itu dikenali di komputer ini, sehingga subtitle tidak berhenti; setelah 3 kali gagal berturut-turut API dijeda 2 menit, dan 10 menit jika kunci atau model salah
- Istilah glosarium dikirim sebagai petunjuk (`prompt`), dan ejaan salah dengar tetap dikembalikan
- Jika suara keluar dari perusahaan, pemberitahuan oranye tampil di halaman Pengaturan IT dan di bagian atas halaman staf. Matikan untuk rapat rahasia atau gunakan layanan internal
- Kunci disimpan di `config.json` komputer ini (`pcg_simple.asr_api_key`) dan disamarkan di file diagnostik; variabel lingkungan sistem Windows `PCG_ASR_API=off` mematikan API untuk sementara
- Mode "Saya juga berbicara" (dua arah) tetap mengirim suara yang tumpang-tindih setiap 3 detik, sekitar 1,7 kali pemakaian satu arah
- **Groq (r26)**: tekan "Groq (kuota gratis)" di halaman pengaturan untuk mengisi alamat dan model, tempel kunci, lalu tekan "Uji koneksi". Pengenalan memakai Whisper large-v3, lebih akurat daripada model small bawaan; program tetap mengirim ke API lebih dulu dan kembali ke komputer ini bila API tidak bisa dipakai
  - **Kuota gratis punya batas, dipakai bersama oleh satu akun.** Angka dari situs pihak ketiga (Groq bisa mengubahnya kapan saja; periksa [halaman batas di konsol Groq](https://console.groq.com/settings/limits)): sekitar 20 permintaan per menit, sekitar 2.000 permintaan per hari, sekitar 7.200 detik suara per jam, dan sekitar 28.800 detik (8 jam) per hari
  - Dalam praktik: satu komputer pada "Hanya baca subtitle" (satu permintaan per kalimat) membuat sekitar 8–15 permintaan per menit, jadi kira-kira 2–4 jam per hari; beberapa komputer dengan satu kunci pada waktu yang sama, atau "Saya juga berbicara" (satu permintaan tiap 3 detik, tepat 20 per menit), cepat mencapai batas
  - **Saat batas tercapai (HTTP 429)**: potongan itu langsung dikenali di komputer ini, dan API dijeda selama waktu yang diminta Groq (minimal 15 detik, maksimal 10 menit, 60 detik jika tidak disebutkan), lalu dipakai lagi secara otomatis; subtitle tidak berhenti, hanya akurasinya kembali ke model lokal selama itu. "Uji koneksi" menampilkan "Tersambung, tetapi batas pemakaian tercapai"
  - Kunci tidak bisa disertakan di dalam penginstal (penginstal bersifat publik), jadi IT mengisinya sekali di tiap komputer; untuk pemakaian besar, gunakan layanan berbayar atau layanan pengenalan di dalam perusahaan
  - Diuji pada 2026-11-18 dengan server simulasi (termasuk 429); belum diuji dengan kunci Groq asli
- Diuji pada 2026-11-18 dengan server API tiruan; belum diuji dengan kunci OpenAI asli, jadi tekan "Uji koneksi" saat pertama kali mengatur

### Glosarium (nama dan istilah, r23)

Nama perusahaan, lokasi pabrik, nama sistem, dan nama orang sering salah dengar atau salah terjemah oleh model umum. Setelah "**Glosarium**" di halaman Pengaturan IT diisi:

| Tahap | Yang dilakukan | Berlaku di mana |
|---|---|---|
| Pengenalan suara | Istilah glosarium diberikan ke Whisper sebagai petunjuk, sehingga bunyi yang mirip lebih memilih istilah ini | Bahasa Mandarin, Indonesia, Vietnam, dll. yang dikenali di komputer staf (Whisper). Subtitle bahasa Inggris (Moonshine) dan pengenalan di server GPU tidak memakai petunjuk |
| Setelah pengenalan | Ejaan yang didaftarkan sebagai "sering salah dengar" dikembalikan ke istilah yang benar | Semua (termasuk subtitle bahasa Inggris dan server GPU) |
| Terjemahan | Mode server: model besar diminta memakai terjemahan yang ditentukan dan membiarkan istilah tanpa terjemahan apa adanya. Mode lokal (M2M100): istilah diganti dengan terjemahan yang ditentukan sebelum diterjemahkan | Paling andal di mode server; di mode lokal biasanya berhasil, tidak dijamin |

Format: satu istilah per baris. Setelah "`=`" terjemahan yang diwajibkan (opsional), setelah "`|`" ejaan yang sering salah dengar; menempel dari Excel juga bisa (tiga kolom: istilah, terjemahan, ejaan salah dengar).

```
寶成 | 寶城 | 保成 = Pou Chen
MES
Sukabumi | Suka Bumi
# baris yang diawali # adalah komentar
```

- Berlaku mulai subtitle atau rekaman **berikutnya** setelah disimpan; maksimal 500 istilah dan 20000 karakter. Hanya 60 istilah pertama yang diberikan ke Whisper sebagai petunjuk (lebih banyak justru memperburuk), jadi **taruh istilah penting di depan**
- **Dipakai semua komputer**: taruh `glossary.txt` (UTF-8) dengan format yang sama di folder bersama perusahaan yang diatur di "Pembaruan"; setiap komputer membacanya saat subtitle atau rekaman dimulai, dan memakai salinan terakhir jika folder tidak terjangkau. Untuk istilah yang sama, isian di komputer ini didahulukan
- Istilah bahasa Inggris 3 huruf atau kurang (misalnya ME) harus sama persis huruf besar/kecilnya, agar "me" biasa tidak dianggap istilah
- Petunjuk hanya menaikkan peluang, bukan jaminan: untuk istilah yang masih salah dengar, menambahkan ejaan salahnya setelah "`|`" adalah cara paling pasti
- Glosarium disimpan di `config.json` komputer ini (`pcg_simple.glossary`) dan ikut dalam file diagnostik "Laporkan masalah"

### Manajemen model (paket model, mulai r15)

Penginstal utama hanya berisi yang dasar (Whisper small, M2M100, Moonshine untuk bahasa Inggris); model lain dibuat sebagai **paket model**, dipasang di "Model" pada halaman pengaturan IT:

| Paket model | Kegunaan | Ukuran | Lisensi |
|---|---|---|---|
| PhoWhisper small / medium | Pengenalan suara bahasa Vietnam | sekitar 240 / 740 MB | BSD-3-Clause |
| Whisper small bahasa Indonesia (maleo-ai) | Pengenalan suara bahasa Indonesia | sekitar 240 MB | Apache-2.0 |
| Whisper medium bahasa Indonesia (cahya) | Pengenalan suara bahasa Indonesia | sekitar 740 MB | Apache-2.0 |
| Whisper small / medium bahasa Hindi (vasista22) | Pengenalan suara bahasa Hindi | sekitar 240 / 740 MB | Apache-2.0 |
| Breeze ASR 25 (MediaTek Research, r25) | Pengenalan suara Mandarin Taiwan dan campuran Mandarin-Inggris; ukuran large-v2, perlu kartu NVIDIA untuk subtitle langsung | sekitar 1,5 GB | Apache-2.0 |
| Whisper base / medium / large-v3-turbo (multibahasa, OpenAI) | "Model pengenalan lokal" untuk semua bahasa (termasuk Mandarin), juga dipakai untuk dua arah dan mode kelas | sekitar 80 / 740 / 800 MB | Apache-2.0 (base, medium) / MIT (large-v3-turbo) |
| MADLAD-400 3B | Terjemahan lokal (lebih lambat; dalam uji terjemahan ada tambahan isi, bandingkan dulu sebelum mengganti) | sekitar 2,8 GB | Apache-2.0 |

**Rekomendasi otomatis saat halaman dibuka** (r25): berdasarkan komputer ini dan "bahasa lawan bicara" yang terakhir dipilih staf, program merekomendasikan satu paket model yang belum terpasang, satu per satu: akselerasi GPU + Mandarin → Breeze ASR 25; Vietnam / Indonesia / Hindi → paket untuk bahasa itu (medium jika ada akselerasi GPU, small jika tidak); ada akselerasi GPU dan belum ada model multibahasa besar → large-v3-turbo; komputer 2 inti → base. Staf bisa menekan "Pasang" (paket langsung ditetapkan untuk bahasa itu), "Nanti saja" (paket ini diingatkan lagi setelah 7 hari), atau "Jangan ingatkan lagi". Jika "siapa yang boleh memperbarui" hanya IT, jendela hanya meminta staf menghubungi IT. Rekomendasi terkait perangkat keras tidak ditampilkan jika IT sudah menetapkan "model subtitle langsung lokal". Tidak ada rekomendasi jika daftar tidak terbaca (tanpa internet dan tidak ada `catalog.json` di folder bersama) atau ruang disk kurang.

Bahasa Indonesia small memakai maleo-ai/whisper-small-id (Apache-2.0); cahya/whisper-small-id hanya bertanda "cc", sehingga pemakaian komersial tidak bisa dipastikan dan otomatis dilewati saat pembuatan paket.

#### Paket yang perlu dipasang (saran)

**Hanya di komputer yang membutuhkan**: misalnya komputer karyawan Taiwan yang sering rapat dengan rekan Indonesia dipasangi paket bahasa Indonesia. Komputer milik karyawan asing (memilih "Mandarin → bahasa saya") mendengar bahasa Mandarin dan **tidak perlu** paket bahasa.

| Bahasa | Subtitle langsung (laptop biasa, CPU) | Subtitle langsung (kartu NVIDIA + paket GPU) | Rekaman |
|---|---|---|---|
| Vietnam | PhoWhisper small | PhoWhisper medium | PhoWhisper medium |
| Indonesia | Whisper small bahasa Indonesia (maleo-ai) | Whisper medium bahasa Indonesia (cahya) | Whisper medium bahasa Indonesia (cahya) |
| Hindi | Whisper small bahasa Hindi | Whisper medium bahasa Hindi | Whisper medium bahasa Hindi |
| Terjemahan lokal | Tetap M2M100 bawaan | Tetap M2M100 bawaan | Sementara tetap M2M100; putuskan MADLAD-400 setelah dibandingkan |

- small sekitar 240 MB, medium sekitar 740 MB; keduanya untuk satu bahasa sekitar 1 GB
- medium 2–3 kali lebih lambat dari small di CPU: pakai small untuk subtitle langsung di laptop biasa, medium untuk rekaman
- Uji pengenalan saat pembuatan paket (suara sintetis): PhoWhisper medium dan Indonesia small benar seluruhnya; PhoWhisper small dan Indonesia medium masing-masing salah satu kata. Uji dengan rekaman nyata
- Dalam mode server dengan server GPU, pengenalan suara dilakukan di server dan paket di komputer karyawan tidak dipakai

#### Menurut spesifikasi komputer (laptop baru)

Periksa dulu apakah ada kartu grafis NVIDIA (Task Manager → "Performance" → GPU):

| Komputer | Model pengenalan lokal (Mandarin, dua arah, mode kelas) | Subtitle langsung bahasa asing | Rekaman |
|---|---|---|---|
| **Dengan kartu NVIDIA** (RTX 4050/4060/5050/5060 dll.) | Pasang paket GPU, lalu Whisper medium atau large-v3-turbo (multibahasa) dan pilih | medium untuk setiap bahasa | medium untuk setiap bahasa; large-v3-turbo untuk Mandarin |
| **Laptop baru 2025–2026** (Core Ultra, Ryzen AI; RAM 16 GB, 8 inti ke atas) | small bawaan; coba Whisper medium (multibahasa), kembali ke small jika subtitle tertinggal | small untuk setiap bahasa (coba medium) | medium untuk setiap bahasa |
| **Laptop biasa atau lama** (RAM 8 GB, 4 inti) | small bawaan; jika tertinggal, Whisper base (multibahasa) | small untuk setiap bahasa | medium untuk setiap bahasa (lebih lama) |

- "Chip AI (NPU)" yang diiklankan di laptop baru tidak dipakai: pengenalan suara hanya memakai CPU atau kartu NVIDIA
- Disarankan RAM 16 GB ke atas: dengan Teams, browser, dan model medium terbuka, 8 GB akan sesak

#### Langkah pemasangan (sekali di setiap komputer yang membutuhkan)

1. Perbarui komputer itu ke **r15 atau lebih baru** (versi ada di bagian bawah halaman; jika lebih lama, klik "Periksa pembaruan")
2. Di komputer itu buka `http://localhost:19781/simple/admin` dan masukkan kata sandi IT (paket hanya bisa dipasang di komputer itu sendiri)
3. Gulir ke "**Model (paket model)**" → "Tersedia", klik "Pasang" untuk paket yang diinginkan dan tunggu bilah kemajuan selesai (paket small sekitar 1–3 menit, tergantung jaringan)
4. Di "**Model untuk setiap bahasa**", pilih "Subtitle langsung" dan "Rekaman" sesuai tabel di atas, lalu klik "**Terapkan pengaturan model**"
5. Mulai satu subtitle langsung "lawan bicara berbahasa …" untuk memeriksa: jika teks muncul dengan normal, selesai
6. Tidak diperlukan lagi: klik "Hapus" di "Terpasang di komputer ini"; bahasa yang memakainya kembali ke model bawaan

Banyak komputer: IT terlebih dulu menaruh `catalog.json` dan file `*.zip` yang diperlukan dari [halaman rilis](https://github.com/fairy715/PCG-live-whisper/releases/tag/model-packs) di folder bersama perusahaan (folder yang diisi di "Pembaruan"); setiap komputer menyalin dari jaringan perusahaan, lebih cepat daripada mengunduh dari GitHub setiap kali.

Catatan: halaman pengaturan IT tersedia dalam bahasa Indonesia: pilih **Bahasa Indonesia** di kanan atas. Nama tombol di panduan ini mengikuti versi bahasa Indonesia.

#### Rincian

- **Sumber**: [halaman rilis model-packs](https://github.com/fairy715/PCG-live-whisper/releases/tag/model-packs) di GitHub; komputer tanpa internet: IT menaruh `catalog.json` dan file paket dari halaman itu di folder bersama yang diisi di "Pembaruan" (atau subfolder `models`-nya)
- **Pemasangan**: hanya di komputer itu (perlu kata sandi IT); SHA-256 setiap file dicocokkan dan tidak ada yang dipasang jika tidak cocok; paket ditaruh di `models\packs\<id>`
- **Penetapan**: di "Model untuk setiap bahasa", pilih model untuk subtitle langsung dan rekaman, klik "Terapkan pengaturan model"; berlaku saat subtitle atau rekaman berikutnya dimulai
  - Hanya dipakai untuk subtitle langsung dan rekaman **satu arah** dalam bahasa itu ("lawan bicara berbahasa …"); dua arah (sisi mikrofon berbahasa Mandarin) dan mode kelas tetap memakai model multibahasa bawaan
  - Jika MADLAD-400 dipilih untuk terjemahan lokal, semua terjemahan di mode lokal memakainya (beberapa detik per kalimat; subtitle langsung di komputer lama akan tertinggal, jadi coba dulu untuk rekaman)
- **Hapus**: bahasa yang memakainya otomatis kembali ke model bawaan
- Cara paket dibuat: `.github/workflows/model-packs.yml` (unduh dari Hugging Face, ubah ke CTranslate2 int8, hanya menerima lisensi yang mengizinkan pemakaian komersial, uji pengenalan/terjemahan, pasang sekali sebelum dirilis)

### Subtitle langsung bahasa Inggris (Moonshine)

- Saat "lawan bicara berbahasa Inggris" dikenali di komputer karyawan, dipakai **Moonshine medium** (khusus bahasa Inggris, lisensi MIT, sekitar 250 MB, termasuk dalam penginstal offline): latensi sekitar 0,3 detik dan jauh lebih ringan di CPU daripada Whisper
- Dua arah ("Saya juga berbicara"), mode kelas, dan bahasa lain tetap memakai Whisper (Moonshine hanya mengerti bahasa Inggris)
- Jika ada server GPU (pengenalan suara di server), tetap memakai Whisper di server
- Kembali ke Whisper: tambahkan `"english_asr": "whisper"` di bawah `pcg_simple` dalam `config.json`
- Model Moonshine untuk bahasa selain Inggris berlisensi non-komersial dan tidak dipakai edisi grup

### Paket GPU NVIDIA (komputer karyawan dengan kartu NVIDIA)

- Halaman rilis juga berisi "Paket GPU NVIDIA" (tag `gpu-cuda12-v…`, sekitar 670 MB): CUDA 12 cuBLAS, cuDNN 9, NVRTC
- Hanya untuk kartu NVIDIA (GeForce, RTX, MX); grafis Intel dan AMD tidak didukung
- Memerlukan PCG Meeting Translator r13 atau lebih baru dan driver NVIDIA yang mendukung CUDA 12 (kira-kira 2023 ke atas)
- Dipasang ke `gpu\cuda12` di folder PCG Meeting Translator; pemasangan ulang aplikasi atau pembaruan kecil tidak menghapusnya; cukup dipasang sekali
- Setelah dipasang, otomatis diperiksa dan hasilnya ditampilkan (pemasangan senyap tidak menampilkan apa pun; lihat `group_data\gpu_check.log`); jika kartu tidak bisa dipakai, aplikasi tetap memakai CPU
- Pemeriksaan manual: jalankan `python\python.exe gpu\gpu_check.py` di folder instalasi
- Format komputasi dipilih otomatis: seri GTX 10 / MX (compute capability 6.x) memakai int8, seri RTX 20 ke atas memakai float16
- Pembuatan di cloud tidak memiliki kartu grafis untuk diuji: coba dulu di komputer dengan kartu NVIDIA sebelum disebarkan

### Komputer subtitle (satu komputer dengan kartu grafis, semua orang terhubung ke sana)

Penginstal utama hanya berisi model small: berjalan di laptop biasa, tetapi bahasa Indonesia dan Vietnam lebih banyak salah kenal. Untuk subtitle yang lebih akurat, jadikan **satu komputer dengan kartu grafis NVIDIA sebagai "komputer subtitle"**: komputer ini menangkap suara, mengenali, dan menerjemahkan, sementara yang lain membaca subtitle di browser ponsel atau laptop. Komputer karyawan tidak perlu diubah.

**Disarankan**: kartu grafis NVIDIA dengan memori video minimal 4 GB (mis. RTX 3050 ke atas). Kartu 2 GB seperti MX330 mungkin terlalu lambat; uji dulu.

**Saran otomatis** (r25): saat staf membuka halaman, program bertanya ke `nvidia-smi` apakah komputer ini punya kartu grafis NVIDIA. Jika ada, memori videonya minimal 4 GB, dan paket belum terpasang, muncul jendela yang menyarankan pemasangan: "Unduh paket" (penginstal di halaman rilis GitHub, sekitar 706 MB), "Nanti saja" (diingatkan lagi setelah 7 hari), atau "Jangan ingatkan lagi". Jika "siapa yang boleh memperbarui" diatur hanya IT, jendela hanya meminta staf menghubungi IT dan tidak menampilkan unduhan. Kartu grafis diskret AMD dan Intel tidak bisa memakai paket ini (hanya mendukung NVIDIA CUDA), jadi tidak ada pengingat; komputer tanpa driver NVIDIA (tanpa `nvidia-smi`) juga tidak terdeteksi. Untuk komputer tanpa internet, IT perlu membawakan penginstal paketnya.

**Pengaturan (IT, sekali, di komputer subtitle)**

1. Pasang penginstal lengkap, lalu paket GPU NVIDIA (setelah terpasang, kartu grafis diperiksa otomatis).
2. Halaman pengaturan IT → "Model (paket model)" → pasang "Whisper large-v3-turbo (multibahasa)".
3. Di "Model pengenalan lokal", pilih large-v3-turbo untuk "Subtitle langsung", lalu klik "Simpan".
4. (Opsional) Paket bahasa (medium) untuk Indonesia, Vietnam, dan Hindi: pilih di "Model untuk setiap bahasa", lalu klik "Terapkan pengaturan model". Hanya dipakai untuk "Hanya baca subtitle".
5. Centang "Izinkan komputer dan ponsel lain menonton subtitle", isi "Kata sandi karyawan", simpan, lalu tekan "**Mulai ulang program sekarang**" yang muncul di halaman (sekitar 10 detik, mulai r20; tidak perlu mengakhiri python.exe di Task Manager). Jika staf memulai skenario "komputer subtitle ruang rapat" sebelum program dimulai ulang, program akan memulai ulang sendiri dulu
   - Penulis asli menambahkan "Allow other computers to connect" di "Security settings" WebUI lanjutan (`/`) pada 2.34.1: saat edisi grup dibuka dari pintasan desktop, **yang menentukan adalah opsi di halaman Pengaturan IT di atas**; abaikan kotak centang di WebUI lanjutan (r22)
6. Izinkan koneksi masuk di Windows Firewall (perlu administrator: buka PowerShell sebagai administrator):
   ```powershell
   New-NetFirewallRule -DisplayName "PCG Meeting Translator" -Direction Inbound -Protocol TCP -LocalPort 19781 -RemoteAddress LocalSubnet -Action Allow -Profile Domain,Private
   ```
   Ini hanya mengizinkan subnet lokal. Jika jaringan perusahaan punya beberapa subnet, ganti `LocalSubnet` dengan rentang sebenarnya (mis. `10.10.0.0/16`).
7. Beri komputer subtitle IP tetap (atau reservasi DHCP) agar alamat di kode QR tidak berubah.

**Saat rapat**

1. Komputer subtitle bergabung ke rapat Teams (online), atau memakai mikrofon ruang rapat (di ruangan: pilih "**Komputer subtitle**", mulai r19).
2. Pilih bahasa lalu klik Mulai: pada pilihan ruang rapat kode QR langsung tampil (selain itu klik "Bagikan" di layar subtitle); tampilkan kode QR di proyektor.
3. Semua orang memindai kode QR (atau membuka `http://<IP komputer subtitle>:19781/simple/live`), memasukkan kata sandi karyawan, dan memilih bahasa yang ditampilkan besar lewat menu bahasa di kanan atas. Ponsel hanya bisa melihat, tidak bisa menghentikan subtitle.

**Batasan**

- **Subtitle multibahasa (mulai r19)**: penonton memilih bahasanya sendiri di kanan atas (Mandarin, Indonesia, Vietnam, Hindi, Inggris). Jika sebuah kalimat tidak dalam bahasa itu, komputer subtitle menerjemahkan satu salinan lagi; mis. di sesi "Mandarin ⇄ Indonesia", penonton yang memilih Vietnam melihat bahasa Vietnam. Pengenalan suara tidak bertambah, hanya terjemahan: di CPU komputer subtitle pada mode lokal (kartu grafis jika ada paket GPU), atau di server LLM pada mode server; bahasa yang tidak dipilih siapa pun tidak diterjemahkan. Di komputer yang lambat, hapus centang "Subtitle multibahasa" di halaman IT. Ucapan bahasa Jepang dan Korea hanya bisa ditambah ke Mandarin.
- Hanya komputer dan ponsel di jaringan perusahaan yang sama yang bisa terhubung.
- Keamanan: mulai r18 hanya koneksi lewat alamat IP atau nama komputer yang diterima; gunakan kata sandi karyawan yang panjang (belum ada penguncian setelah salah berulang).

### Pengajar di Taiwan mengajar dalam bahasa Mandarin, pabrik luar negeri membaca subtitle: Breeze untuk Mandarin, suara tetap di dalam perusahaan

Langkah untuk karyawan ada di skenario 8 pada contoh penggunaan. Satu komputer subtitle ikut kelas Teams dan mengenali bahasa Mandarin pengajar dengan kartu grafis dan **Breeze ASR 25** (MediaTek Research, dilatih untuk Mandarin Taiwan dan campuran Mandarin-Inggris); karyawan di luar negeri tersambung lewat browser dan memilih bahasanya sendiri. Suara dikenali satu kali, dan hanya diproses di komputer subtitle.

**IT melakukannya sekali di komputer subtitle**

1. Ikuti langkah "komputer subtitle ruang rapat" di atas: penginstal lengkap, paket GPU, "Izinkan komputer dan ponsel lain menonton subtitle", kata sandi staf. Breeze berukuran large-v2: disarankan memori video 6 GB atau lebih; kartu 4 GB perlu diuji.
2. Di "Model (paket model)", pasang "**Breeze ASR 25（台灣華語、中英夾雜）**" (sekitar 1,5 GB).
3. Tetapkan Breeze untuk bahasa Mandarin:
   - **Mulai r28**: di "Model untuk setiap bahasa", baris "Mandarin", pilih Breeze ASR 25 untuk "Subtitle langsung" lalu tekan "Terapkan pengaturan model".
   - **r25 dan r26**: halaman pengaturan tidak punya baris "Mandarin". Satu-satunya cara adalah halaman staf di komputer subtitle: pilih "Semua berbahasa Mandarin", muat ulang, lalu tekan "Pasang" pada jendela "Disarankan memasang model suara yang lebih akurat" (setelah terpasang, model otomatis ditetapkan untuk Mandarin). Setelah itu **jangan tekan "Terapkan pengaturan model"**, karena menghapus penetapan Mandarin. Disarankan memperbarui ke r28.
4. Firewall: aturan di atas hanya membuka subnet yang sama. Untuk pabrik luar negeri, ganti `-RemoteAddress` dengan subnet mereka (misalnya `10.10.0.0/16,10.20.0.0/16`) dan minta tim jaringan memastikan TCP 19781 dari tiap lokasi ke komputer subtitle terbuka.
5. Isi istilah pelajaran (perusahaan, pabrik, sistem, nama) ke glosarium.
6. Kualitas terjemahan: mode lokal memakai M2M100, biasa saja untuk bahasa Indonesia dan Vietnam; agar lebih baik, alihkan komputer subtitle ke mode server dan terjemahkan dengan platform AI grup atau model besar internal (pengenalan tetap di komputer subtitle).

**Cara kerja program yang sebenarnya**

- Paket model Mandarin dipakai untuk subtitle satu arah yang mendengarkan bahasa Mandarin: staf berbahasa Mandarin yang memilih "Semua berbahasa Mandarin", dan staf berbahasa asing yang memilih "Mandarin → bahasa Anda". Mode kelas (satu mikrofon, dua bahasa) dan "Saya juga berbicara" memakai model multibahasa, bukan Breeze.
- Suara yang didengarkan "Semua berbahasa Mandarin" bergantung pada jenis rapat (**mulai r28**):
  - "Hanya baca subtitle": **suara yang diputar komputer** (komputer subtitle yang ikut Teams dan mendengar pengajar). Speaker atau headset jangan dibisukan.
  - "Satu ruang kelas" dan "Komputer subtitle": **mikrofon** (pengajar berbicara ke komputer ini atau mikrofon ruangan). Dipakai mikrofon yang dipilih di "Suara dan mikrofon", atau mikrofon bawaan Windows jika belum dipilih; jika tidak ada mikrofon sama sekali, sesi tidak dimulai dan halaman menyatakan mikrofon tidak ditemukan.
  - Keduanya memakai paket model Mandarin (Breeze). Satu sesi mendengarkan satu sumber; memulai lagi "Semua berbahasa Mandarin" pada jenis rapat lain menggantikan sesi yang sedang berjalan.
  - Sampai r26 jenis rapat tidak berpengaruh: selalu suara yang diputar komputer (jadi "Komputer subtitle" dengan "Semua berbahasa Mandarin" tidak mendengar mikrofon ruangan).
- Sebuah bahasa baru diterjemahkan jika ada penonton yang memilihnya. Yang dikirim keluar hanya teks subtitle, jadi lalu lintas data kecil.
- Jika "API pengenalan suara" aktif, suara dikirim ke API lebih dulu dan Breeze hanya cadangan. Agar suara tetap di dalam perusahaan, jangan aktifkan API eksternal.

**Belum diuji di komputer nyata**: jeda Breeze pada subtitle langsung (bergantung kartu grafis), penangkapan mikrofon untuk "Semua berbahasa Mandarin" (cloud tidak punya perangkat audio, jadi yang diuji hanya penerusan nomor mikrofon ke program utama), akses antar lokasi, dan banyak penonton sekaligus. Pada 2026-11-18 hanya pemuatan model dengan satu kalimat Mandarin dan cara kerja di atas (uji otomatis) yang dipastikan di cloud. Coba dulu pada satu kelas.

### Perubahan pada halaman Pengaturan IT (r29)

- **“Ke mana data dikirim” di bagian atas**: berdasarkan nilai yang sedang tampil di halaman, selalu ditunjukkan ke mana “Suara” dan “Teks” dikirim (hanya komputer ini, server GPU perusahaan, layanan internal, platform AI grup, atau ke luar perusahaan). Jika salah satunya keluar dari perusahaan, seluruh baris menjadi oranye. Baris ini juga mengikuti perubahan yang belum disimpan, jadi bisa diperiksa sebelum menyimpan.
- **Tujuan data LLM kini mengikuti alamat**: jika jenis server “Server internal” tetapi alamatnya domain atau IP publik di luar perusahaan, halaman staf menampilkan “layanan AI di luar perusahaan” (sampai r28 hanya jenisnya yang dilihat, sehingga alamat eksternal tetap tampil sebagai internal). Jika server internal memakai nama domain (bukan alamat 10.x atau 192.168.x dan bukan nama host tanpa titik), di bawah alamat muncul kotak “Ini server di dalam perusahaan”; centang setelah dipastikan. **Setelah memperbarui, buka halaman pengaturan sekali dan baca baris atas**: server internal yang dialamatkan dengan nama domain dianggap eksternal sampai kotak itu dicentang.
- **Bagian yang jarang diubah awalnya tertutup**: glosarium, pembaruan, laporan masalah, model. Nilai saat ini tampil di kanan judul (jumlah istilah, periksa otomatis atau tidak, kontak, jumlah paket model); klik judul untuk membuka.
- **Baris simpan tetap di bawah jendela**: menampilkan “Ada perubahan yang belum disimpan” dan hasil penyimpanan. “Terapkan pengaturan model” tetap tombol terpisah di dalam Model.
- **Mode lokal menyembunyikan pengaturan server.**
- **Menonton jarak jauh aktif tanpa kata sandi staf**: muncul peringatan oranye di bawah kotak centang.
- Judul halaman sebelumnya menulis perubahan langsung berlaku; sebenarnya berlaku mulai subtitle atau rekaman berikutnya. Teksnya sudah diperbaiki.
- **Dua tombol uji** (r30): “Uji koneksi LLM” dan “Uji server GPU”, masing-masing menampilkan hasil di bawahnya. Setelah uji LLM berhasil, halaman memeriksa apakah nama di “Model terjemahan” dan “Model notulen (ringkasan)” ada di daftar server dan memperingatkan jika tidak ada (salah ketik nama model adalah penyebab paling umum subtitle tidak diterjemahkan).
- **Ganti kata sandi IT** (r30): jendela di halaman, isian tersembunyi, dimasukkan dua kali; minimal 6 karakter.
- **Komputer tanpa internet** (r30): Model menampilkan “Komputer ini sedang tidak bisa menjangkau GitHub, jadi hanya paket model di folder bersama perusahaan yang ditampilkan”. Ini normal, bukan kesalahan.
- **Peringatan bahwa data keluar dari perusahaan** (r30) memiliki garis oranye tebal di kiri, agar berbeda dari pemberitahuan biasa.

### Ikon yang dipakai di antarmuka (r29)

- Ikon jenis rapat adalah SVG satu warna yang digambar di halaman, bukan emoji lagi (emoji tampil berbeda di Windows 10 dan 11).
- Status “mendengarkan, menyiapkan, memproses, menyambung ulang, menguji” memakai ikon bergerak dari [Ultra Lab Motion Icons](https://github.com/ppcvote/ultralab-anim-icons) v0.3.1 (Lisensi MIT). Hanya 8 ikon yang dipakai yang disematkan di halaman; tidak ada yang dimuat dari internet. Ikon tidak bergerak jika efek animasi Windows dimatikan (Settings → Accessibility → Visual effects → Animation effects).

## ③ Komputer karyawan yang perlu subtitle langsung

### Windows

1. Unduh edisi grup ke `C:\jt-live-whisper`:
   - Dengan Git: `git clone https://github.com/fairy715/PCG-live-whisper.git C:\jt-live-whisper`
   - Tanpa Git: di halaman GitHub klik Code → Download ZIP, ekstrak, lalu taruh **file di dalamnya** ke `C:\jt-live-whisper`
2. Buka PowerShell sebagai administrator:
   ```powershell
   cd C:\jt-live-whisper
   powershell -ExecutionPolicy Bypass -File install.ps1
   ```
   Saat ditanya server GPU di akhir, isi alamat ② (pengenalan suara dikerjakan host GPU, jadi komputer pribadi tidak perlu kartu grafis yang bagus)
3. Atur server LLM: isi alamat Ollama ② saat pertama kali membuka WebUI (akan diingat)
4. Pintasan desktop yang dibuat dengan cara ini membuka WebUI lengkap; buatkan bookmark untuk karyawan: **`http://localhost:19781/simple`** (penginstal offline tidak mengalami hal ini: pintasan "PCG Meeting Translator"-nya membuka halaman sederhana)

### Mac

```bash
mkdir -p ~/Apps
git clone https://github.com/fairy715/PCG-live-whisper.git ~/Apps/jt-live-whisper
cd ~/Apps/jt-live-whisper
bash install.sh
```

Saat pertama kali, izinkan "Screen & System Audio Recording" untuk Terminal (akan diminta), lalu tutup Terminal sepenuhnya dan buka kembali.

## Pembaruan

```bash
cd ~/Apps/jt-live-whisper        # Windows: cd C:\jt-live-whisper
git pull
./install.sh                     # Windows: .\install.ps1 (menambahkan paket yang diperlukan versi baru)
sudo systemctl restart jt-live-whisper-webui    # hanya di ①
```

Saat penulis asli merilis versi baru (aplikasi menampilkan "versi baru" saat dimulai), gabungkan dulu ke edisi grup, baru perbarui; jangan langsung memakai `--upgrade`. Pemeriksaan mingguan di GitHub membuka issue jika proyek asli memiliki pembaruan.

## Operasional

| Item | Lokasi / perintah |
|---|---|
| Status layanan, log kesalahan | `systemctl status jt-live-whisper-webui`, `journalctl -u jt-live-whisper-webui` |
| Daftar pekerjaan halaman sederhana | `group_data/jobs.json` |
| Log lengkap satu pekerjaan | `group_data/job_<id pekerjaan>.log` (karyawan melihat id pekerjaan di layar) |
| Rekaman yang diunggah karyawan | `recordings/simple/` |
| Notulen dan transkrip | `logs/` |
| Pemeriksaan kesehatan | `./install.sh --doctor` |

**Rekaman dan hasil tidak pernah dihapus otomatis**: rekaman rapat adalah data sensitif; bersihkan secara berkala sesuai aturan penyimpanan data perusahaan (misalnya simpan 90 hari).

### Laporan masalah (mulai r16)

* **Karyawan**: “Laporkan masalah” di bagian bawah halaman → tulis apa yang terjadi → “Buat laporan”. Browser mengunduh `PCG-report-<komputer>-<tanggal-jam>.zip`, lalu karyawan mengirimnya ke IT. Hanya bisa dibuat di komputer itu sendiri (log-nya milik komputer itu).
* **IT**: di halaman pengaturan, “Laporan masalah” untuk mengisi ke mana karyawan mengirim laporan (email atau grup Teams); ditampilkan ke karyawan. Alamat email juga menambahkan tombol “Email IT” (subjek dan deskripsi sudah terisi; karyawan melampirkan zip sendiri). “Buat file diagnostik komputer ini” di kartu yang sama membuatnya untuk IT; jika “Izinkan komputer dan ponsel lain menonton subtitle” aktif, IT juga bisa mengambilnya dari komputernya sendiri dengan kata sandi IT.
* **Isi zip**: `summary.txt` (versi, spesifikasi komputer, memori, disk, paket GPU, paket model, browser, deskripsi karyawan), `report.json` (data yang sama ditambah status dan error 20 pekerjaan rekaman terakhir serta parameter subtitle langsung), `config.json` (pengaturan, **kunci, kata sandi, dan hash diganti `***`**), `logs/` (400 baris terakhir `webui.log`, `webui-error.log`, `update.log`, `install.log`, `gpu_check.log`, dan log 3 pekerjaan terakhir, yang gagal lebih dulu).
* **Tidak ada di zip**: rekaman, transkrip, notulen, nama file rekaman, dan topik rapat. Log program mungkin berisi sebagian teks subtitle; karyawan bisa menghapus centang “Sertakan log program terbaru”.
* Setiap komputer hanya menyimpan 10 file diagnostik terakhir (`group_data\reports\`).
* File diagnostik mungkin berisi potongan rapat: **jangan ditempel di issue GitHub publik**. Templat “Laporan masalah” di GitHub hanya meminta versi, gejala, dan langkah.
