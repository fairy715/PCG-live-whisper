# PCG Meeting Translator: install and update guide

[中文](安裝說明.md) · [English](INSTALL-GUIDE-en.md) · [Bahasa Indonesia](INSTALL-GUIDE-id.md) · [Tiếng Việt](INSTALL-GUIDE-vi.md)

Latest version: **https://github.com/fairy715/PCG-live-whisper/releases/latest**

Each release page has the same instructions and says whether the small update can be used.

## 1. Download

1. Open the release page: https://github.com/fairy715/PCG-live-whisper/releases/latest
2. Under "Assets" at the bottom of the page, click `PCG-Meeting-Translator-Setup-<version>.exe` (about 1.8 GB).
   * If the browser warns that the file "isn't commonly downloaded", choose "Keep" (Edge: click "…" → "Keep").
   * The file is large: IT can also put it on a shared folder or Google Drive for you.

## 2. Install

1. Double-click the downloaded exe.
2. A blue window "Windows protected your PC" appears:
   * Click "More info", then "Run anyway".
   * This always appears the first time because the installer has no code-signing certificate.
3. If a language window appears, choose your language and click "OK" (usually it is chosen automatically from the Windows language).
4. Install location: `D:\PCG-live-whisper` by default (`C:\PCG-live-whisper` if there is no D drive). Keep it and click "Next" → "Install".
   * No administrator rights and no internet connection are needed.
5. The window shows "Installing the runtime and models". This takes about 3–10 minutes. Do not close it.
6. Done: tick "Open PCG Meeting Translator now" and click "Finish". A desktop shortcut is created (its name follows the installer language, e.g. "PCG Meeting Translator" or "Penerjemah Rapat PCG").

## 3. First use

1. Double-click the desktop shortcut. The browser opens the app page (`http://localhost:19781/simple`).
2. A short guided tour runs the first time. Follow it once.
3. You can switch the page language at the top right (中文 / English / Bahasa Indonesia / Tiếng Việt / हिन्दी).
4. Live subtitles: choose the language the other person speaks → "Start". Recordings: upload → when processing is done, download the minutes.
5. The version is shown at the bottom of the page (e.g. v2026.11.5.r5). Include it when you report a problem (click it to copy).

## 4. Update

You do **not** need to uninstall first. Settings, recordings and transcripts are kept.

* **One-click update (easiest)**: on computers with internet, or where IT has set a shared folder, a "new version" notice appears at the top of the app page. Click "Update now"; the page reloads by itself after 1–2 minutes.

* **Small update** (`PCG-Update-….exe`, about 10 MB): close PCG Meeting Translator → double-click the update → if the blue window appears, "More info" → "Run anyway" → done in about 1 minute.
  * If it says the update "needs new components that are only in the full installer", use the full installer instead.
* **Full installer**: just install it over the old version.
* IT mass deployment (no windows shown): add `/VERYSILENT /SUPPRESSMSGBOXES /NORESTART` after the exe.

## 5. Problems

* Installation failed: send `D:\PCG-live-whisper\group_data\install.log` (for a failed update: `update.log`) to IT.
* Blocked by antivirus: ask IT to add the install folder as an exception.
* Uninstall: Windows "Settings" → "Apps" → "PCG Meeting Translator" → "Uninstall". Recordings, transcripts and settings stay in the folder; delete it manually if you no longer need them.

## For IT

* **IT settings page**: on the staff computer, click "IT settings" at the bottom of the app page, or open `http://localhost:19781/simple/admin`.
  * First time: set an IT password on that computer (at least 6 characters). It is required every time after that. Staff do not need to know it.
  * You can change: local/server mode, the LLM (group Open WebUI, internal server or external AI service) and API key, GPU server, recognition models, staff password, and whether other computers may view subtitles.
  * Changes take effect when saved; no reinstall needed. Details in [INSTALL.md](INSTALL.md) (Chinese).
* How the installer and the small update are built: [windows/README.md](windows/README.md) (Chinese).
