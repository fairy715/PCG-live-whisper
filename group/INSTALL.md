# PCG 集團版：系統架構與安裝（給 IT）

## 系統架構

```
                         ┌──────────────── 公司內網 ────────────────┐
                         │                                          │
  同仁的電腦（瀏覽器）     │   ① 應用伺服器（Linux，不需要 GPU）        │
  ───────────────────    │   ─────────────────────────────          │
  http://應用伺服器:19781/simple ─→  WebUI（含簡易頁面 /simple）     │
  上傳錄音 → 下載會議紀錄  │   工作佇列：一次處理一件，其他排隊          │
                         │   存放：錄音 recordings/、產出 logs/       │
                         │        │ 語音辨識              │ 翻譯／摘要 │
                         │        ▼                       ▼          │
                         │   ② GPU 主機（Ubuntu＋NVIDIA）             │
                         │   ─────────────────────────────          │
                         │   GPU 語音辨識服務（port 8978）            │
                         │   Ollama 大模型（port 11434）              │
                         │     翻譯 gemma4:26b、摘要 qwen3.8:27b       │
                         │        ▲                       ▲          │
  ③ 需要即時字幕的同仁電腦 ─────────┘───────────────────────┘          │
  （Windows／Mac 各自安裝）│                                          │
  抓本機播出的聲音 → http://localhost:19781/simple                    │
                         └──────────────────────────────────────────┘
```

| 角色 | 做什麼 | 硬體建議 |
|---|---|---|
| ① 應用伺服器 | 網頁、工作排隊、存放錄音與會議紀錄 | Linux（Ubuntu 22.04／Debian 12 以上），2 vCPU、4 GB 記憶體、磁碟依錄音量（一小時 m4a 約 30～60 MB） |
| ② GPU 主機 | 語音辨識、翻譯、摘要（最吃算力的部分） | NVIDIA DGX Spark，或 RTX 4090／5090（24 GB 以上顯示記憶體）＋ 64 GB 記憶體；同時跑辨識和大模型 |
| ③ 同仁電腦 | 只有要「即時字幕」的人需要安裝 | Windows 10／11 或 Mac；辨識與翻譯交給 ②，所以一般文書機即可 |

- **所有語音與文字都不離開公司內網**：不需要任何雲端 API（接集團 Open WebUI 時，文字會送到 Open WebUI 背後的模型，請先確認 luna／deepseek 是集團內部主機，見下方「接集團 Open WebUI」）
- ① 和 ② 可以是同一台，但原作者建議分開：GPU 主機同時跑大模型時，網頁與檔案處理放另一台比較穩
- 即時字幕一定要在 ③ 本機跑：它擷取的是**那台電腦播出來的聲音**（Teams、Zoom），伺服器拿不到

## 安裝前要知道的事

1. **不要用原作者的一鍵安裝指令**（`curl … jasoncheng7115 … | bash`、`irm … | iex`），那會裝成原作者的版本，沒有新語言與簡易頁面
2. **更新不要用 `./install.sh --upgrade`**：它會下載原作者的版本、蓋掉集團版（集團版已經擋下來，會提示改用 git pull）
3. 本 repo 是私人的：下載要有 GitHub 權限（帳號、或請管理者開一把唯讀的 Deploy key）

## ② GPU 主機

1. 安裝 NVIDIA 驅動與 CUDA（`nvidia-smi` 看得到顯示卡）
2. 安裝 Ollama 並下載模型：
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ollama pull gemma4:26b       # 翻譯
   ollama pull qwen3.8:27b      # 摘要、逐字稿校正
   ```
   讓區網連得到：在 Ollama 的 systemd 設定加 `OLLAMA_HOST=0.0.0.0`，防火牆只開給 ① 與同仁電腦的網段
3. GPU 語音辨識服務**不用手動裝**：裝 ① 的最後會問要不要設定 GPU 伺服器，回答主機位址後透過 SSH 自動安裝

## ① 應用伺服器

```bash
# 1. 下載集團版（用一般帳號，不要用 root）
mkdir -p ~/Apps
git clone https://github.com/fairy715/PCG-live-whisper.git ~/Apps/jt-live-whisper
cd ~/Apps/jt-live-whisper

# 2. 安裝成伺服器版（WebUI 以 systemd 服務常駐，名稱 jt-live-whisper-webui）
bash install.sh --server
```

安裝過程：
- 會用 `sudo apt` 補 ffmpeg 等系統套件
- **會印出一次「管理密碼」與「唯讀密碼」，當下記下來**
- 最後問 GPU 伺服器：填 ② 的位址，自動透過 SSH 安裝 GPU 語音辨識服務
- LLM 伺服器：在 WebUI（`http://應用伺服器:19781`，用管理密碼）設定 ② 的 Ollama 位址，或直接寫在 `config.json` 的 `llm_host`

### IT 設定頁（不用改設定檔）

打開 `http://應用伺服器:19781/simple/admin`（簡易頁面最下方的「IT 設定」）：

1. **第一次使用**：在這台電腦上打開，設定 IT 密碼（至少 6 個字）。之後進入都要輸入，本機也一樣
2. **運作模式**：本機模式（CPU，M2M100 翻譯，不產出 AI 會議紀錄）／伺服器模式（大模型伺服器翻譯並產出 AI 會議紀錄；GPU 伺服器選填）
3. **伺服器位址**：填大模型伺服器網址（必填）與 GPU 伺服器（選填）→ 按「測試連線」→ 會列出伺服器上的模型可以選。
   沒填 GPU 伺服器時，語音辨識留在這台電腦（用「本機辨識模型」），只有翻譯與會議紀錄交給大模型
4. **同仁密碼**：從別台電腦連進來時要輸入（本機不用）
5. 按「儲存」：下一次開始字幕或處理錄音就生效，不用重新啟動

設定存在同一個 `config.json`（密碼都是雜湊），格式與原作者的程式相同。

### 接集團 Open WebUI（luna、deepseek）

集團的 AI 一律經 Open WebUI 使用，不用自己架大模型：

1. 到 Open WebUI 建一把 API 金鑰：登入 → 右上角頭像 → 設定 → 帳號 → API 金鑰 → 建立
   （看不到這個選項：請集團 AI 管理者在「管理員設定 → 使用者權限」開放 API Keys）
2. IT 設定頁：模式選「伺服器模式」，大模型伺服器網址填瀏覽器打開 Open WebUI 的網址（例如 `https://ai.公司網域`），
   伺服器類型選「Open WebUI」，貼上 API 金鑰
3. 按「測試連線」，從清單選模型：**翻譯選 luna**（快，即時字幕不延遲），**會議紀錄選 deepseek**（推理型，慢但完整）
4. 沒有 GPU 伺服器就把 GPU 欄位留空：辨識在同仁電腦的 CPU 上跑（small 模型），翻譯與會議紀錄交給 luna／deepseek

注意：
- 金鑰是**個人**的：用誰的金鑰，Open WebUI 的用量就記在誰身上。建議向 AI 管理者申請一個專用帳號
- 同仁電腦要連得到 Open WebUI（離線、不能上網的電腦也要能連到集團內網的這個網址）
- 程式呼叫的是 Open WebUI 的 `/api/chat/completions` 與 `/api/models`（設定檔 `llm_api_style: "openwebui"`、`llm_url`、`llm_api_key`）
建議另外到完整 WebUI 的「安全設定」限制來源 IP（只允許公司網段）。

**同仁的網址：`http://應用伺服器:19781/simple`**（完整版 WebUI 在 `/`，給 IT 用）

## 同仁電腦離線安裝（沒有網路、沒有 GPU 伺服器也能用）

**請看 [windows/README.md](windows/README.md)**：Setup.exe＋離線資源包，預設本機模式（CPU），
之後有了 GPU 伺服器，IT 在 `/simple/admin` 切換即可。下面「③」是有網路時的另一種安裝方式。

## ③ 需要即時字幕的同仁電腦

### Windows

1. 下載集團版放到 `C:\jt-live-whisper`：
   - 有 Git：`git clone https://github.com/fairy715/PCG-live-whisper.git C:\jt-live-whisper`
   - 沒有 Git：在 GitHub 網頁按 Code → Download ZIP，解壓縮後把**裡面的檔案**放進 `C:\jt-live-whisper`
2. 以系統管理員開 PowerShell：
   ```powershell
   cd C:\jt-live-whisper
   powershell -ExecutionPolicy Bypass -File install.ps1
   ```
   最後問 GPU 伺服器時填 ② 的位址（辨識交給 GPU 主機，個人電腦不用好顯示卡）
3. 設定 LLM 伺服器：第一次打開 WebUI 時填 ② 的 Ollama 位址（之後記住）
4. 安裝程式會建立桌面捷徑（打開完整版）。請另外幫同仁建一個書籤：**`http://localhost:19781/simple`**

### Mac

```bash
mkdir -p ~/Apps
git clone https://github.com/fairy715/PCG-live-whisper.git ~/Apps/jt-live-whisper
cd ~/Apps/jt-live-whisper
bash install.sh
```

第一次使用要授權「螢幕與系統音訊錄製」給終端機（畫面會提示），授權後要完全結束終端機再打開。

## 更新

```bash
cd ~/Apps/jt-live-whisper        # Windows：cd C:\jt-live-whisper
git pull
./install.sh                     # Windows：.\install.ps1（補齊新版需要的套件）
sudo systemctl restart jt-live-whisper-webui    # 只有 ① 需要
```

原作者出新版時（啟動時會提示「有新版本」），請把新版合併進集團版再更新，不要直接用 `--upgrade`。

## 維運

| 項目 | 位置／指令 |
|---|---|
| 服務狀態、錯誤紀錄 | `systemctl status jt-live-whisper-webui`、`journalctl -u jt-live-whisper-webui` |
| 簡易頁面的工作清單 | `group_data/jobs.json` |
| 某件工作的完整執行紀錄 | `group_data/job_<工作編號>.log`（同仁畫面上會顯示工作編號） |
| 同仁上傳的錄音 | `recordings/simple/` |
| 產出的會議紀錄、逐字稿 | `logs/` |
| 健康檢查 | `./install.sh --doctor` |

**錄音與產出檔不會自動刪除**：會議錄音屬於敏感資料，請依公司的資料保存規定定期清理（例如保留 90 天）。
