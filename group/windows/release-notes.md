## PCG 會議翻譯 {VER}

**Guide / Panduan / Hướng dẫn**：[English](https://github.com/fairy715/PCG-live-whisper/blob/main/group/INSTALL-GUIDE-en.md) · [Bahasa Indonesia](https://github.com/fairy715/PCG-live-whisper/blob/main/group/INSTALL-GUIDE-id.md) · [Tiếng Việt](https://github.com/fairy715/PCG-live-whisper/blob/main/group/INSTALL-GUIDE-vi.md)

### 要下載哪一個？

| 情況 | 下載 |
|---|---|
| 第一次安裝 | `{FULL}`（約 {FULL_MB} MB） |
| 已經裝過，要更新 | {PATCH_LINE} |
| `.sha256` 檔 | 不用下載（給 IT 核對檔案用，見「四、更新」） |

## 一、下載

1. 打開發布頁：就是這一頁
2. 在頁面下方「Assets」點 `{FULL}` 下載（約 {FULL_GB} GB）。
   * 瀏覽器如果警告「這個檔案不常下載」，選「保留」（Edge：點「…」→「保留」）。
   * 檔案很大，也可以由 IT 放到公司共用資料夾或 Google Drive 再發給同仁。

## 二、安裝

1. 點兩下下載好的 exe。
2. 出現藍色視窗「Windows 已保護您的電腦」：
   * 點「其他資訊」，再按「仍要執行」。
   * 這是因為安裝檔沒有程式碼簽章，第一次一定會出現。
3. 如果出現選語言的視窗，選好按「確定」（通常會依 Windows 語言自動選好，不會出現）。
4. 安裝位置：預設 `D:\PCG-live-whisper`（沒有 D 槽就是 `C:\PCG-live-whisper`），不用改，按「下一步」→「安裝」。
   * 不需要系統管理員權限，也不需要網路。
5. 畫面顯示「正在安裝執行環境與模型」，約 3～10 分鐘，請不要關掉。
6. 完成：勾「立即開啟 PCG 會議翻譯」再按「完成」。桌面會多一個「PCG 會議翻譯」捷徑。

## 三、第一次使用

1. 點桌面的「PCG 會議翻譯」，瀏覽器會自動打開操作頁面（`http://localhost:19781/simple`）。
2. 第一次會有導覽，照著看一遍。
3. 即時字幕：選你說的語言 → 哪一種場合 → 對方說的語言 → 按「開始」（外語同仁選自己的語言就會自動選好）；錄音檔：上傳 → 處理完下載會議紀錄。
4. 頁面最下方會顯示版本（例如 v{VER}），回報問題時請附上（點一下就會複製）。

## 四、更新

已經裝過的電腦**不用先移除**，設定、錄音、逐字稿都會保留：

* **小更新包**（`PCG-Update-….exe`，約 10 MB）：先關掉 PCG 會議翻譯 → 點兩下小更新包 → 一樣出現藍色視窗就按「其他資訊」→「仍要執行」→ 約 1 分鐘完成。
  * 如果出現「這次更新包含新的套件或模型」，代表這次必須用完整安裝檔。
* **完整安裝檔**：直接裝在舊版上面即可。
* IT 大量派送（不跳任何視窗）：在 exe 後面加 `/VERYSILENT /SUPPRESSMSGBOXES /NORESTART`。
* 發布頁上的 `.sha256` 檔是更新包的「指紋」，用來確認檔案完整、沒被改過，**同仁不用下載**。
  * IT 把小更新包放到公司共用資料夾時，`.exe` 和同名的 `.sha256` 要**一起放**：一鍵更新會先比對指紋，不符就不安裝（例如下載被截斷）。
  * 從 GitHub 一鍵更新不需要這個檔，程式會直接讀發布頁上的指紋。

## 五、遇到問題

* 安裝失敗：把 `D:\PCG-live-whisper\group_data\install.log`（更新失敗是 `update.log`）交給 IT。
* 防毒軟體攔截：請 IT 把安裝資料夾加入例外。
* 解除安裝：Windows「設定」→「應用程式」→「PCG Meeting Translator」→「解除安裝」。錄音、逐字稿、設定會留在資料夾裡，確定不要了再手動刪除。


---

# English

### Which file do I download?

| Situation | Download |
|---|---|
| First installation | `{FULL}` (about {FULL_MB} MB) |
| Already installed, updating | {PATCH_LINE_EN} |
| `.sha256` file | No need to download (for IT to check files, see "4. Update") |

## 1. Download

1. Open the release page: this page
2. Under "Assets" at the bottom of the page, click `{FULL}` (about {FULL_GB} GB).
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
4. Live subtitles: choose the language you speak → the kind of meeting → the language the others speak → "Start" (if you speak Indonesian, Vietnamese, Hindi or English, it is chosen for you). Recordings: upload → when processing is done, download the minutes.
5. The version is shown at the bottom of the page (e.g. v{VER}). Include it when you report a problem (click it to copy).

## 4. Update

You do **not** need to uninstall first. Settings, recordings and transcripts are kept.

* **Small update** (`PCG-Update-….exe`, about 10 MB): close PCG Meeting Translator → double-click the update → if the blue window appears, "More info" → "Run anyway" → done in about 1 minute.
  * If it says the update "needs new components that are only in the full installer", use the full installer instead.
* **Full installer**: just install it over the old version.
* IT mass deployment (no windows shown): add `/VERYSILENT /SUPPRESSMSGBOXES /NORESTART` after the exe.
* The `.sha256` file on the release page is the update's "fingerprint", used to check the file is complete and unchanged. **Staff do not need to download it.**
  * When IT puts a small update on the shared folder, put the `.exe` and the `.sha256` file with the same name **together**: one-click update checks the fingerprint first and does not install if it does not match (for example, a cut-off download).
  * One-click update from GitHub does not need this file; it reads the fingerprint from the release page.

## 5. Problems

* Installation failed: send `D:\PCG-live-whisper\group_data\install.log` (for a failed update: `update.log`) to IT.
* Blocked by antivirus: ask IT to add the install folder as an exception.
* Uninstall: Windows "Settings" → "Apps" → "PCG Meeting Translator" → "Uninstall". Recordings, transcripts and settings stay in the folder; delete it manually if you no longer need them.

---
已在乾淨的 Windows 上實際安裝{PATCH_TESTED}並通過自我檢查（套件、模型、5 個翻譯方向）。語音辨識模型：{MODELS}；commit {COMMIT}
