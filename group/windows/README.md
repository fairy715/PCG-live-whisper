# Windows 離線安裝包（給沒有網路的同仁電腦）

同仁電腦：Windows 10／11、64 位元，不需要獨立顯示卡（i5-1235U、16 GB 實際規劃），不需要網路、不需要系統管理員。

## 給 IT：最簡單的方式（單一安裝檔）

GitHub → Actions →「發布安裝包」→ Run workflow，約 20 分鐘後 **Releases** 會出現
`PCG-Meeting-Translator-Setup-版本.exe`：**資源包已經包在裡面，只要這一個檔案**。
放到 Google Drive 或共用資料夾，同仁下載後點兩下安裝。發布前會先在乾淨的 Windows 上實際安裝、自我檢查。
Releases 不會過期。

## 給 IT：自己製作與發放

1. **下載 Setup.exe**：GitHub → Actions → 「Windows 安裝程式」→ 最新一次成功的執行 → Artifacts 的 `PCG-Setup`
   （每次推送程式都會自動產生，並在乾淨的 Windows 上實際安裝、測試一次；`e2e-logs` 是測試紀錄）
2. **製作離線資源包**（在一台能上網的電腦，Windows／Mac／Linux 都可以，需要 Python 3.9 以上）：
   ```
   python group/windows/build_bundle.py
   ```
   產生 `PCG-offline` 資料夾（約 2 GB）：Python、套件、語音辨識模型（small）、翻譯模型 M2M100、ffmpeg。
   想要更準的錄音辨識可以加 `--models small,medium`（再多約 1.5 GB）
3. **放在一起發放**（公司共用資料夾或 USB）：
   ```
   PCG-Setup-2026.11.4.N.exe
   PCG-offline\
   ```
4. 同仁執行 Setup.exe（第一次會出現「Windows 已保護您的電腦」：按「其他資訊」→「仍要執行」，因為沒有程式碼簽章）

資源包只有在 `requirements-cpu.txt` 或模型改變時才需要重做；一般程式更新只要發新的 Setup.exe（資源包沿用）。

## 同仁安裝時會發生什麼

- 預設裝到 `D:\PCG-live-whisper`（沒有 D 槽就裝 `C:\PCG-live-whisper`），可以改
- 解壓縮 Python（免安裝版，不寫登錄檔、不影響電腦上其他 Python）、從資源包安裝套件、複製模型，約 3～10 分鐘
- 自我檢查（套件、模型、翻譯一句印尼文），沒通過會跳出訊息與紀錄檔位置
- 桌面與開始功能表出現「PCG 會議翻譯」：點開就是簡易頁面（`http://localhost:19781/simple`）
- 預設本機模式、只給這台電腦用；IT 在 `/simple/admin` 切換伺服器模式或允許別台電腦觀看字幕

## 更新與移除

- 更新：執行新版 Setup.exe（設定、錄音、逐字稿都保留；程式在跑會先關掉）
- 移除：Windows「設定 → 應用程式」→ PCG Meeting Translator。錄音（recordings）、逐字稿（logs）、設定（config.json）保留

## 檔案

| 檔案 | 用途 |
|---|---|
| `requirements-cpu.txt` | 同仁電腦要裝的套件 |
| `build_bundle.py` | 製作離線資源包（用 uv 以 Windows 平台解出確切版本，記在 requirements-lock.txt） |
| `PCG-Setup.iss` | 安裝程式（Inno Setup 6）；介面有繁中、英文、印尼文、越南文、印地語 |
| `pcg-install.ps1` | 安裝時執行：Python、套件、模型、設定檔、自我檢查；也可以手動執行來修復 |
| `launch.vbs`／`launch.ps1` | 桌面捷徑：背景啟動程式、打開簡易頁面 |
| `selftest.py` | 自我檢查（`python\python.exe group\windows\selftest.py`） |

## 已知限制

- 沒有程式碼簽章：第一次執行會出現 Windows SmartScreen 警告
- 防毒軟體可能攔下 Setup.exe 或 python.exe：請 IT 加入允許清單
- 即時字幕在 i5-1235U 上的延遲約 3～6 秒（推估，待實機確認）

## 小更新包（PCG-Update-<版本>.exe，約 10 MB）

發布流程每次會同時產出完整安裝檔與小更新包。小更新包**只換程式檔**，執行環境（python）、模型、ffmpeg 沿用電腦上已經裝好的：

- 安裝前比對已安裝的 `group/windows/requirements-cpu.txt` 與 `build_bundle.py`：跟這一版不同（有新套件、新模型）就拒絕，提示改用完整安裝檔，不會裝到一半壞掉
- 沒有裝過的電腦也會拒絕
- 裝好後執行 `pcg-update.ps1`：清舊的編譯快取、跑自我檢查，紀錄在 `group_data\update.log`
- 設定、錄音、逐字稿都保留；靜默安裝一樣加 `/VERYSILENT /SUPPRESSMSGBOXES /NORESTART`
- 發布流程會實測兩件事：套用到剛裝好的電腦能更新成功；套件不同時會拒絕且不動到程式
- 跟上一版比較套件清單沒變，才會把小更新包放上發布頁；有變的那一版只放完整安裝檔

本機製作：`ISCC.exe /DAppVersion=<版本> /DPatchOnly /DReqSha=<requirements-cpu.txt 的 SHA-256> /DBundleSha=<build_bundle.py 的 SHA-256> group\windows\PCG-Setup.iss`
