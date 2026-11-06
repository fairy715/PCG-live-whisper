## NVIDIA GPU 加速包（CUDA 12）

**只有裝了 NVIDIA 顯示卡（GeForce、RTX、MX 系列等）的電腦需要。** 沒有 NVIDIA 顯示卡的電腦不用裝，PCG 會議翻譯照常用 CPU。

裝好之後，語音辨識改由顯示卡處理：CPU 用量大幅下降、字幕更快。翻譯仍在 CPU 上（比語音辨識輕很多）。

### 安裝

1. 先確認 PCG 會議翻譯已經是 **r13 以上**（頁面最下方看版本；舊版請先按「檢查更新」）。
2. 下載 `{FILE}`（約 {MB} MB），點兩下安裝。出現藍色視窗「Windows 已保護您的電腦」時按「其他資訊」→「仍要執行」。
3. 不用選位置：會自動裝到 PCG 會議翻譯的資料夾（`gpu\cuda12`）。安裝時會先關掉 PCG 會議翻譯。
4. 裝好會自動檢查這台電腦能不能用顯示卡，並跳視窗說明結果：
   * 「已啟用顯示卡加速」：重新打開 PCG 會議翻譯就會使用。
   * 「目前不能用顯示卡」：視窗會說原因（最常見是 **NVIDIA 驅動太舊**，請 IT 更新驅動後重新執行這個加速包）。程式照常用 CPU，不會壞。
5. 檢查紀錄：`group_data\gpu_check.log`。IT 也可以手動檢查：在安裝資料夾執行 `python\python.exe gpu\gpu_check.py`。

### 其他

* 只要裝一次。PCG 會議翻譯之後的小更新包、完整安裝檔都不會刪掉加速包。
* 不需要系統管理員權限；IT 大量派送可加 `/VERYSILENT /SUPPRESSMSGBOXES /NORESTART`（安靜安裝不跳視窗，結果看 `gpu_check.log`）。
* 移除：Windows「設定」→「應用程式」→「PCG Meeting Translator NVIDIA GPU Pack」→「解除安裝」，程式改回 CPU。
* 需要 NVIDIA 驅動支援 CUDA 12（大約 2023 年以後的驅動）。
* 舊顯示卡（GTX 10 系列、MX 系列）會自動用 int8 格式；RTX 20 系列以後用 float16。

---

## NVIDIA GPU pack (CUDA 12)

**Only for computers with an NVIDIA graphics card** (GeForce, RTX, MX). Other computers do not need it; PCG Meeting Translator keeps using the CPU.

1. PCG Meeting Translator must be **r13 or newer** (version at the bottom of the page; click "Check for updates" first).
2. Download `{FILE}` (about {MB} MB) and double-click it. It installs into the PCG Meeting Translator folder (`gpu\cuda12`) and closes the app first.
3. When it finishes, it checks whether this computer can use the graphics card and shows the result. If not (usually an old NVIDIA driver), ask IT to update the driver and run the pack again. The app keeps working on the CPU either way.
4. Log: `group_data\gpu_check.log`. Uninstall from Windows Settings → Apps → "PCG Meeting Translator NVIDIA GPU Pack".

---
內容：nvidia-cublas-cu12 {CUBLAS}、nvidia-cudnn-cu12 {CUDNN}、nvidia-cuda-nvrtc-cu12 {NVRTC}（NVIDIA 在 PyPI 發布的檔案）。雲端測試機沒有顯示卡：已測試檔案齊全、安裝與移除、沒有顯示卡時照常用 CPU；實際用顯示卡辨識請在有 NVIDIA 顯示卡的電腦確認。commit {COMMIT}
