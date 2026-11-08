# PCG 集團版：系統架構與安裝（給 IT）

[中文](INSTALL.md) · [English](IT-GUIDE-en.md) · [Bahasa Indonesia](IT-GUIDE-id.md) · [Tiếng Việt](IT-GUIDE-vi.md)

<!-- 修改這份說明時，中文、英文、印尼文、越南文四份要一起更新（INSTALL.md、IT-GUIDE-en.md、IT-GUIDE-id.md、IT-GUIDE-vi.md）。 -->

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

- **本機模式與內部伺服器：語音與文字都不離開公司內網**。接集團 Open WebUI 時，文字會送到它背後的模型（請確認 luna／deepseek 在集團內部）；選「外部 AI 服務」時會送出公司（見下方「伺服器模式：大模型有三種接法」）
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

在**要設定的那台電腦上**打開 IT 設定頁（簡易頁面最下方的「IT 設定」；右上角可切換繁體中文、English、Bahasa Indonesia）：

- 同仁電腦（離線安裝檔裝的）：`http://localhost:19781/simple/admin`
- 應用伺服器：`http://應用伺服器:19781/simple/admin`


1. **第一次使用**：在這台電腦上打開，設定 IT 密碼（至少 6 個字）。之後進入都要輸入，本機也一樣
2. **運作模式**：本機模式（CPU，M2M100 翻譯，不產出 AI 會議紀錄）／伺服器模式（大模型伺服器翻譯並產出 AI 會議紀錄；GPU 伺服器選填）
3. **伺服器位址**：填大模型伺服器網址（必填）與 GPU 伺服器（選填）→ 按「測試連線」→ 會列出伺服器上的模型可以選。
   沒填 GPU 伺服器時，語音辨識留在這台電腦（用「本機辨識模型」），只有翻譯與會議紀錄交給大模型
4. **同仁密碼**：從別台電腦連進來時要輸入（本機不用）
5. 按「儲存」：下一次開始字幕或處理錄音就生效，不用重新啟動

設定存在同一個 `config.json`（密碼都是雜湊），格式與原作者的程式相同。

### 一鍵更新

IT 設定頁的「更新」：

- **自動檢查新版本**（預設開）：有新的小更新包時，同仁頁面上方顯示「有新版本」與「立即更新」
- **誰可以按更新**：同仁自己按（預設）／只有 IT（要輸入 IT 密碼）
- **更新來源**：
  1. **公司共用資料夾**（選填，例如 `\\檔案伺服器\PCG\更新`）：把發布頁上的 `PCG-Update-<版本>.exe` 和同名的 `.sha256` 檔放進去。不能上網、只連得到內網的電腦也能一鍵更新
  2. **GitHub 發布頁**：能上網的電腦自動使用（repo 改成私人後就不能用，請改用共用資料夾）
- 按下更新後：下載（或從共用資料夾複製）→ 比對檔案指紋，不符就刪除、不安裝 → 關掉程式 → 安裝 → 自我檢查 → 自動重新開啟，原本的頁面會自己重新整理
- 正在即時字幕或處理錄音時不能更新；需要完整安裝檔的版本只會提示「請找 IT」
- 紀錄：`group_data\update.log`；下載的檔案：`group_data\updates\`
- **`.sha256` 指紋檔**：每個小更新包旁邊都有一個同名的 `.sha256`，內容是這個 exe 的 SHA-256 指紋（一行 64 個字元）
  - 共用資料夾：`.exe` 和 `.sha256` 一起放，更新前會比對，不符就不安裝；沒有 `.sha256` 一樣會安裝，只是不檢查
  - GitHub：不需要這個檔，程式直接讀發布頁附檔的指紋；發布頁沒有指紋就不安裝
  - 手動核對（PowerShell）：`Get-FileHash .\PCG-Update-<版本>.exe -Algorithm SHA256`，算出來的 Hash 跟 `.sha256` 的內容一樣（大小寫不拘）就是完好的檔案

### 伺服器模式：大模型有三種接法

IT 設定頁的「伺服器類型」：

| 類型 | 什麼時候用 | 網址 | API 金鑰 |
|---|---|---|---|
| 集團 Open WebUI | 現在（luna、deepseek） | 瀏覽器打開 Open WebUI 的網址 | 必填 |
| 內部伺服器 | 買到 RTX Spark／DGX Spark，或自己架 Ollama、vLLM | `主機:11434` | 通常不用 |
| 外部 AI 服務 | OpenAI、DeepSeek、Google Gemini、OpenRouter 等 | 點按鈕自動帶入 base URL | 必填 |

GPU 伺服器（語音辨識）跟大模型是分開的，可以任意搭配：例如大模型用集團 Open WebUI、辨識用自己的 RTX Spark。
GPU 伺服器有填但當下連不上時，會自動改在同仁電腦上用小模型辨識，不會卡住。

#### 集團 Open WebUI（luna、deepseek）

1. 到 Open WebUI 建一把 API 金鑰：登入 → 右上角頭像 → 設定 → 帳號 → API 金鑰 → 建立
   （看不到這個選項：請集團 AI 管理者在「管理員設定 → 使用者權限」開放 API Keys）
2. IT 設定頁：模式選「伺服器模式」，類型選「集團 Open WebUI」，填網址（例如 `https://ai.公司網域`），貼上金鑰
3. 按「測試連線」，從清單選模型：**翻譯選 luna**（快，即時字幕不延遲），**會議紀錄選 deepseek**（推理型，慢但完整）
4. 沒有 GPU 伺服器就把 GPU 欄位留空：辨識在同仁電腦的 CPU 上跑（small 模型）

注意：金鑰是**個人**的，用量記在申請人名下，建議申請專用帳號；同仁電腦要連得到 Open WebUI 的網址。

#### 內部伺服器（RTX Spark、DGX Spark）

買到之後，同一台可以同時當「大模型」和「GPU 語音辨識」：

- **大模型**：在 Spark 上裝 Ollama 並下載模型，讓區網連得到（`OLLAMA_HOST=0.0.0.0`）。IT 設定頁類型選「內部伺服器」，填 `Spark的IP:11434`
- **GPU 語音辨識**：Spark 上要跑原作者的 GPU 辨識服務（`remote_whisper_server.py`，支援 aarch64 的 DGX Spark）。
  在 IT 設定頁「GPU 伺服器」填 `Spark的IP`、Port `8978`
  - DGX Spark（DGX OS／Ubuntu）：從一台 Linux 或 Mac 執行 `bash install.sh`，問到 GPU 伺服器時填 Spark 的位址，會透過 SSH 自動安裝並設成開機自動啟動
  - RTX Spark 筆電（Windows on Arm）：辨識服務只有 Linux 版，要在 WSL2 裡安裝；**到貨後需要實測**
- 同仁電腦**只用網址**連 GPU 服務，不需要也不會用 SSH（服務由 Spark 上的 systemd 常駐）
- 只有大模型、沒有 GPU 辨識也可以：照樣能翻譯、出會議紀錄

#### 外部 AI 服務（OpenAI、DeepSeek、Gemini…）

- **會議內容會送出公司**，並依用量計費：先確認符合公司資料規範，機密會議請用 Open WebUI 或內部伺服器
- 用公司帳號申請金鑰，並在服務的網站設定每月用量上限
- 類型選「外部 AI 服務」→ 點 OpenAI／DeepSeek／Google Gemini／OpenRouter 帶入網址 → 貼金鑰 → 測試連線 → 選模型
- 其他 OpenAI 相容的服務也可以，填它文件上的 base URL（通常以 `/v1` 結尾）。Azure OpenAI 不支援（認證方式不同），可改用 OpenRouter 或架 LiteLLM 代理

設定檔欄位（給除錯用）：`llm_url`、`llm_api_key`、`llm_api_style`（`openwebui`／`openai`／沒有＝內部自動偵測）、`remote_whisper.host`。

建議另外到完整 WebUI 的「安全設定」限制來源 IP（只允許公司網段）。

**同仁的網址：`http://應用伺服器:19781/simple`**（完整版 WebUI 在 `/`，給 IT 用）

## 同仁電腦離線安裝（沒有網路、沒有 GPU 伺服器也能用）

**請看 [windows/README.md](windows/README.md)**：Setup.exe＋離線資源包，預設本機模式（CPU），
之後有了 GPU 伺服器，IT 在 `/simple/admin` 切換即可。下面「③」是有網路時的另一種安裝方式。

### CPU 用量（同仁電腦在本機辨識時）

即時字幕、錄音檔處理在同仁電腦的 CPU 上跑時（本機模式，或只接大模型伺服器的伺服器模式）：

- 語音辨識＋本機翻譯合計只用約 **3/4 的核心**、而且不超過實體核心數（4 核筆電：辨識 2～3、翻譯 1），留給 Teams 和其他程式
- Windows 上用「**低於標準**」的優先順序：CPU 忙的時候先讓給前景的程式，Teams、滑鼠不會頓
- 舊電腦還是很吃力、字幕跟不上：先在「模型管理」安裝 **Whisper base（多語）** 模型包，再把「本機即時字幕模型」換成它（較快但錯字多）。**程式不會自己上網下載模型**（離線安裝固定不下載），設定頁只列出這台已經有的模型
- 要調整（Windows 系統環境變數，設定後重開程式）：
  - `PCG_CPU_THREADS=8`：指定總共用幾個執行緒（例如效能好的桌機要全速跑）
  - `PCG_NORMAL_PRIORITY=1`：改回一般優先順序

### 模型管理（模型包，r15 起）

主安裝檔只放基本款（Whisper small、M2M100、Moonshine 英文）；其他模型做成**模型包**，在 IT 設定頁的「模型管理」安裝：

| 模型包 | 用途 | 大小 | 授權 |
|---|---|---|---|
| PhoWhisper small／medium | 越南文語音辨識 | 約 240／740 MB | BSD-3-Clause |
| Whisper small 印尼文（maleo-ai） | 印尼文語音辨識 | 約 240 MB | Apache-2.0 |
| Whisper medium 印尼文（cahya） | 印尼文語音辨識 | 約 740 MB | Apache-2.0 |
| Whisper small／medium 印地語（vasista22） | 印地語語音辨識 | 約 240／740 MB | Apache-2.0 |
| Whisper base／medium／large-v3-turbo（多語，OpenAI） | 所有語言（含中文）的「本機辨識模型」，也用在雙向、教室模式 | 約 80／740 MB／800 MB | Apache-2.0（base、medium）／MIT（large-v3-turbo） |
| MADLAD-400 3B | 本機翻譯（較慢；試翻有加料的情況，先實測再換） | 約 2.8 GB | Apache-2.0 |

印尼文 small 用 maleo-ai/whisper-small-id（Apache-2.0）；cahya/whisper-small-id 的授權只寫「cc」、無法確認能商用，打包時自動略過。

#### 要裝哪些（建議）

**只在需要的電腦裝**：例如常跟印尼同事開會的台灣同仁電腦，裝印尼文的模型包。外語同仁自己的電腦（選「對方說中文 → 翻成我的語言」）聽的是中文，**不用裝**語言模型包。

| 語言 | 即時字幕（一般筆電，CPU） | 即時字幕（有 NVIDIA 顯示卡＋GPU 加速包） | 錄音檔 |
|---|---|---|---|
| 越南文 | PhoWhisper small | PhoWhisper medium | PhoWhisper medium |
| 印尼文 | Whisper small 印尼文（maleo-ai） | Whisper medium 印尼文（cahya） | Whisper medium 印尼文（cahya） |
| 印地語 | Whisper small 印地語 | Whisper medium 印地語 | Whisper medium 印地語 |
| 本機翻譯 | 維持內建 M2M100 | 維持內建 M2M100 | 先維持 M2M100；MADLAD-400 實測比較後再決定 |

- small 約 240 MB、medium 約 740 MB；一種語言兩個都裝約 1 GB
- medium 在 CPU 上比 small 慢 2～3 倍：一般筆電即時字幕用 small，medium 留給錄音檔
- 打包時的試辨識（電腦合成語音）：PhoWhisper medium、印尼文 small 全對；PhoWhisper small、印尼文 medium 各錯 1 個字。真人錄音的效果請實測
- 伺服器模式而且有 GPU 伺服器時，辨識在伺服器上做，同仁電腦的模型包用不到

#### 依電腦規格（新筆電建議）

先看有沒有 NVIDIA 顯示卡（工作管理員 →「效能」→ GPU）：

| 電腦 | 本機辨識模型（中文、雙向、教室模式） | 外語即時字幕 | 錄音檔 |
|---|---|---|---|
| **有 NVIDIA 顯示卡**（RTX 4050／4060／5050／5060 等） | 先裝 GPU 加速包，再裝 Whisper medium 或 large-v3-turbo（多語）並選用 | 各語言 medium | 各語言 medium；中文用 large-v3-turbo |
| **2025～2026 年的新筆電**（Core Ultra、Ryzen AI；16 GB 記憶體、8 核以上） | 內建 small；可以試 Whisper medium（多語），字幕跟不上就改回 small | 各語言 small（可以試 medium） | 各語言 medium |
| **一般或較舊的筆電**（8 GB 記憶體、4 核） | 內建 small；跟不上就換 Whisper base（多語） | 各語言 small | 各語言 medium（會比較久） |

- 新筆電標榜的「AI 晶片（NPU）」目前用不到：語音辨識只會用 CPU 或 NVIDIA 顯示卡
- 記憶體建議 16 GB 以上：同時開 Teams、瀏覽器和 medium 模型，8 GB 會很吃緊

#### 安裝步驟（每台要用的電腦做一次）

1. 那台電腦先更新到 **r15 以上**（頁面最下方看版本；舊的按「檢查更新」）
2. 在那台電腦打開 `http://localhost:19781/simple/admin`，輸入 IT 密碼（只能在那台電腦上安裝）
3. 往下到「**模型管理（模型包）**」→「可以安裝」，按要的模型包的「安裝」，等進度條跑完（一個 small 約 1～3 分鐘，看網路）
4. 在「**每種語言用哪個模型**」照上表選好「即時字幕」「錄音檔」，按「**套用模型設定**」
5. 開一次「對方說○○文」的即時字幕確認：字幕畫面能正常出字就好了
6. 不要了：「這台電腦已安裝」按「移除」，用到它的語言自動改回內建模型

很多台電腦要裝：IT 先把[發布頁](https://github.com/fairy715/PCG-live-whisper/releases/tag/model-packs)的 `catalog.json` 與要用的 `*.zip` 放到公司共用資料夾（「更新」那欄填的資料夾），各電腦從內網複製，比每台都從 GitHub 下載快。

#### 細節

- **來源**：GitHub 的 [model-packs 發布頁](https://github.com/fairy715/PCG-live-whisper/releases/tag/model-packs)；不能上網的電腦：IT 把那一頁的 `catalog.json` 與模型包檔案放到「更新」的公司共用資料夾（或它的 `models` 子資料夾）
- **安裝**：只能在那台電腦上按（要 IT 密碼）；每個檔案比對 SHA-256，不符就不裝；裝到 `models\packs\<代號>`
- **指定用途**：「每種語言用哪個模型」選即時字幕、錄音檔各用哪個，按「套用模型設定」，下次開始字幕或處理錄音時生效
  - 只用在「對方說這種語言」的**單向**即時字幕與錄音檔；雙向（麥克風那邊是中文）、教室模式照舊用內建的多語模型
  - 本機翻譯選 MADLAD-400 時，本機模式的所有翻譯都改用它（大約每句幾秒，舊電腦的即時字幕會跟不上，建議先用在錄音檔）
- **移除**：用到它的語言自動改回內建模型
- 製作方式：`.github/workflows/model-packs.yml`（從 Hugging Face 下載、轉成 CTranslate2 int8、只收可商用授權、試辨識／試翻、實際安裝一次才發布）

### 英文即時字幕（Moonshine）

- 「對方說英文」在同仁電腦上辨識時，改用 **Moonshine medium**（英文專用，MIT 授權，約 250 MB，離線資源包附）：延遲約 0.3 秒、CPU 比 Whisper 輕很多
- 雙向（我也要說話）、教室模式、其他語言照舊用 Whisper（Moonshine 只聽得懂英文）
- 接了 GPU 伺服器（辨識在伺服器）時照舊用伺服器的 Whisper
- 要改回 Whisper：在 `config.json` 的 `pcg_simple` 加 `"english_asr": "whisper"`
- Moonshine 的非英文模型是非商業授權，集團版不使用

### NVIDIA GPU 加速包（有 NVIDIA 顯示卡的同仁電腦）

- 發布頁另外有「NVIDIA GPU 加速包」（標籤 `gpu-cuda12-v…`，約 670 MB）：CUDA 12 的 cuBLAS、cuDNN 9、NVRTC
- 只有 NVIDIA 顯示卡（GeForce、RTX、MX）用得到；Intel、AMD 顯示卡不適用
- 需要 PCG 會議翻譯 r13 以上、NVIDIA 驅動支援 CUDA 12（約 2023 年以後的驅動）
- 裝到 PCG 會議翻譯資料夾的 `gpu\cuda12`，主程式重裝、小更新包都不會刪；只要裝一次
- 裝好自動檢查並跳視窗說結果（安靜安裝不跳，看 `group_data\gpu_check.log`）；不能用時程式照常用 CPU
- 手動檢查：在安裝資料夾執行 `python\python.exe gpu\gpu_check.py`
- 計算格式自動選：GTX 10／MX 系列（計算能力 6.x）用 int8，RTX 20 系列以後用 float16
- 雲端打包時沒有顯示卡可測：第一次請在有 NVIDIA 顯示卡的電腦實測後再推廣

### 會議室字幕機（一台有顯示卡的電腦，大家連進去看）

基本安裝檔只有 small 模型，一般筆電跑得動，但印尼文、越南文的錯字比較多。要更準的字幕，可以讓**一台有 NVIDIA 顯示卡的電腦當「字幕機」**：它負責收音、辨識、翻譯，其他人用手機或筆電的瀏覽器連進來看。同仁的電腦不用改。

**建議規格**：NVIDIA 顯示卡、至少 4 GB 顯示記憶體（例如 RTX 3050 以上）。只有 2 GB 的 MX330 這一級可能跑不動或很慢，要實測。

**設定（IT 在字幕機上做一次）**

1. 安裝完整安裝檔，再安裝 NVIDIA GPU 加速包（裝完會自動檢查能不能用顯示卡）。
2. IT 設定頁 →「模型管理（模型包）」→ 安裝「Whisper large-v3-turbo（多語）」。
3. 「本機辨識模型」的「即時字幕」選 large-v3-turbo，按「儲存」。
4. （選用）印尼文、越南文、印地語的語言模型包（medium）：在「每種語言用哪個模型」指定，按「套用模型設定」。只用在「只看字幕」。
5. 勾「允許其他電腦或手機連進來看字幕」，設定「同仁密碼」，存檔後**關掉程式再開一次**。
6. Windows 防火牆開放連入（要系統管理員：用系統管理員身分開 PowerShell）：
   ```powershell
   New-NetFirewallRule -DisplayName "PCG Meeting Translator" -Direction Inbound -Protocol TCP -LocalPort 19781 -RemoteAddress LocalSubnet -Action Allow -Profile Domain,Private
   ```
   只開放同一個網段。公司網路是多個網段時，把 `LocalSubnet` 換成實際的網段（例如 `10.10.0.0/16`）。
7. 建議字幕機用固定 IP（或 DHCP 保留），QR Code 的網址才不會變。

**開會時**

1. 字幕機加入 Teams（線上會議），或接會議室的麥克風（現場會議：場合選「同一間教室，一支麥克風」）。
2. 選好語言按開始，在字幕畫面按「分享」，把 QR Code 投影出來。
3. 大家掃 QR Code（或開 `http://字幕機的IP:19781/simple/live`），輸入同仁密碼，用右上角的語言選單選要大字顯示的語言。手機只能看，不能停止字幕。

**限制**

- **一場字幕只有兩種語言**：每一句只會翻成一種語言（例如「中文 ⇄ 印尼文」這場，每句只有中文和印尼文兩個版本）。連進來的人可以在這兩種之間選，選第三種語言（例如越南文）看不到越南文。三種以上語言的會議，見使用情境的「多國同仁會議」。
- 只有同一個公司內網的電腦和手機連得進來。
- 安全：r18 起只接受用 IP 或電腦名稱連進來；同仁密碼請設長一點（目前沒有輸錯次數鎖定）。

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
4. 這種安裝方式建立的桌面捷徑會打開完整版，請另外幫同仁建一個書籤：**`http://localhost:19781/simple`**（用離線安裝檔就沒有這個問題，桌面的「PCG 會議翻譯」直接打開簡易頁面）

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

原作者出新版時（啟動時會提示「有新版本」），請把新版合併進集團版再更新，不要直接用 `--upgrade`。GitHub 每週一會自動檢查原作者的更新，有新東西就開 Issue 通知。

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

### 問題回報（r16 起）

* **同仁**：頁面最下方「回報問題」→ 寫下發生什麼事 →「產生診斷檔」，瀏覽器會下載 `PCG-report-<電腦名稱>-<日期時間>.zip`，同仁把它寄給 IT。只能在那台電腦上產生（記錄是那台電腦的）。
* **IT**：設定頁「問題回報」可以填「同仁回報問題時寄給誰」（信箱或 Teams 群組），會顯示給同仁；填信箱時多一個「寫信給 IT」按鈕（會帶好主旨與說明，zip 要同仁自己附上）。同一張卡片的「產生這台電腦的診斷檔」：IT 自己產生；打開「允許其他電腦或手機連進來看字幕」時，也能從 IT 的電腦用 IT 密碼遠端拿。
* **zip 裡有**：`summary.txt`（版本、電腦規格、記憶體、磁碟、GPU 加速包、模型包、瀏覽器、同仁的說明）、`report.json`（同樣的資料加上最近 20 件錄音工作的狀態與錯誤、即時字幕的參數）、`config.json`（設定，**金鑰、密碼、雜湊一律換成 `***`**）、`logs/`（`webui.log`、`webui-error.log`、`update.log`、`install.log`、`gpu_check.log` 的最後 400 行，以及最近 3 件工作的記錄，失敗的優先）。
* **zip 裡沒有**：錄音、逐字稿、會議紀錄、錄音的檔名與會議主題。程式記錄可能有部分字幕文字，同仁可以取消勾選「附上最近的程式記錄」。
* 同一台電腦只留最近 10 個診斷檔（`group_data\reports\`）。
* 診斷檔可能有會議片段，**不要貼到公開的 GitHub issue**；GitHub 的「問題回報」範本只放版本、現象與步驟。
