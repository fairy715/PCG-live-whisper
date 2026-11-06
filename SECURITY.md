# 資安問題通報（PCG 會議翻譯，集團版）

[中文](#資安問題通報pcg-會議翻譯集團版) · [English](#security-policy-pcg-meeting-translator-group-edition) · [Bahasa Indonesia](#kebijakan-keamanan-pcg-penerjemah-rapat-edisi-grup)

這個專案是 PCG 集團內部使用的版本，以 [jt-live-whisper](https://github.com/jasoncheng7115/jt-live-whisper) 為基礎修改。集團版的資安問題由**集團 IT** 處理。

## 怎麼通報

- **不要開公開的 GitHub issue**，也不要在大群組公開討論細節。
- 寄信給集團 IT 窗口：**pgt.it@pci.co.id**，主旨寫「PCG 會議翻譯 資安通報」。
- 請寫：版本（頁面最下方，例如 v2026.11.6.r16）、哪一個部分（同仁頁面、IT 設定頁、安裝檔／更新、模型包、GPU 加速包、伺服器）、怎麼重現、可能的影響。
- **不要附真實的會議錄音、逐字稿或會議紀錄**。「回報問題」的診斷檔可能有部分字幕內容，只有 IT 要求時才用公司內部管道傳。

## 支援的版本

只有最新版會收到資安修正。同仁電腦用頁面上的「立即更新」或[發布頁](https://github.com/fairy715/PCG-live-whisper/releases)的小更新包更新。

## IT 收到之後

- 確認問題、評估影響，修正後發新版，並通知受影響的單位。
- 如果問題出在原作者的程式（集團版沒改過的部分），IT 會再**私下**通報原作者（原專案的 GitHub「Report a vulnerability」或 service@jason.tools），不在公開的地方討論。
- 原作者已發布的安全公告：https://github.com/jasoncheng7115/jt-live-whisper/security/advisories （每週一的「檢查原作者更新」會把原作者的新修正開成 issue，IT 評估後合併）。

---

# Security policy (PCG Meeting Translator, group edition)

This project is the PCG group's internal edition, based on [jt-live-whisper](https://github.com/jasoncheng7115/jt-live-whisper). Security problems in the group edition are handled by **group IT**.

## How to report

- **Do not open a public GitHub issue**, and do not discuss details in large group chats.
- Email group IT: **pgt.it@pci.co.id**, subject "PCG Meeting Translator security report".
- Include: the version (bottom of the page, e.g. v2026.11.6.r16), the part affected (staff page, IT settings page, installer/update, model packs, GPU pack, servers), steps to reproduce and the possible impact.
- **Do not attach real meeting recordings, transcripts or minutes.** The "Report a problem" diagnostic file may contain some subtitle text; send it only when IT asks, through internal channels.

## Supported versions

Only the latest release receives security fixes. Update staff computers with "Update now" on the page or the small update on the [release page](https://github.com/fairy715/PCG-live-whisper/releases).

## What IT does

- Confirms the problem and its impact, releases a fixed version and informs the affected units.
- If the problem is in the original author's code (parts the group edition did not change), IT also reports it **privately** to the original author (GitHub "Report a vulnerability" on the original project, or service@jason.tools).
- Advisories published by the original author: https://github.com/jasoncheng7115/jt-live-whisper/security/advisories (the Monday "upstream check" opens an issue for each new upstream fix; IT reviews and merges them).

---

# Kebijakan keamanan (PCG Penerjemah Rapat, edisi grup)

Proyek ini adalah edisi internal grup PCG, berdasarkan [jt-live-whisper](https://github.com/jasoncheng7115/jt-live-whisper). Masalah keamanan edisi grup ditangani oleh **IT grup**.

## Cara melapor

- **Jangan membuka issue GitHub publik**, dan jangan membahas detailnya di grup obrolan besar.
- Kirim email ke IT grup: **pgt.it@pci.co.id**, subjek "Laporan keamanan PCG Penerjemah Rapat".
- Tuliskan: versi (bagian bawah halaman, mis. v2026.11.6.r16), bagian yang terdampak (halaman karyawan, halaman pengaturan IT, penginstal/pembaruan, paket model, paket GPU, server), langkah untuk mengulang, dan kemungkinan dampaknya.
- **Jangan lampirkan rekaman rapat, transkrip, atau notulen asli.** File diagnostik "Laporkan masalah" mungkin berisi sebagian teks subtitle; kirim hanya jika diminta IT, lewat jalur internal.

## Versi yang didukung

Hanya versi terbaru yang menerima perbaikan keamanan. Perbarui komputer karyawan dengan "Perbarui sekarang" di halaman atau pembaruan kecil di [halaman rilis](https://github.com/fairy715/PCG-live-whisper/releases).

## Yang dilakukan IT

- Memastikan masalah dan dampaknya, merilis versi perbaikan, dan memberi tahu unit yang terdampak.
- Jika masalahnya ada di kode penulis asli (bagian yang tidak diubah edisi grup), IT juga melaporkannya **secara pribadi** ke penulis asli (GitHub "Report a vulnerability" di proyek asli, atau service@jason.tools).
- Pengumuman keamanan dari penulis asli: https://github.com/jasoncheng7115/jt-live-whisper/security/advisories ("pemeriksaan upstream" setiap Senin membuka issue untuk setiap perbaikan baru; IT meninjau lalu menggabungkannya).
