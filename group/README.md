# PCG 集團版（PCG-live-whisper）

本專案 fork 自 [jasoncheng7115/jt-live-whisper](https://github.com/jasoncheng7115/jt-live-whisper)
（原作者 Jason Cheng，Apache License 2.0）。原作的著作權聲明與 `LICENSE` 保持不變；
依 Apache-2.0 第 4(b) 條，修改過的檔案開頭都有修改聲明，程式內的修改處以「集團版」註解標示。

## 與上游的差異

### 新增語言：印尼文（id）、越南文（vi）、印地語（hi）

每種語言 6 個模式，即時字幕、離線處理、WebUI 都可以選：

| 模式代號 | 說明 |
|---|---|
| `id2zh` `vi2zh` `hi2zh` | 外語語音 → 繁體中文 |
| `zh2id` `zh2vi` `zh2hi` | 中文語音 → 外語 |
| `id_zh` `vi_zh` `hi_zh` | 雙向：對方說外語翻中文 ＋ 自己說中文翻外語 |
| `id` `vi` `hi` | 純轉錄 |
| `id2en` `vi2en` `hi2en` | 外語語音 → 英文 |
| `en2id` `en2vi` `en2hi` | 英文語音 → 外語 |

```bash
./start.sh --mode id2zh                       # 即時：印尼文翻中文
./start.sh --mode vi_zh                       # 即時：越中雙向
./start.sh --input 會議.mp3 --mode hi2zh --summarize   # 離線：印地語會議錄音 → 中文逐字稿＋摘要
```

做法與注意事項：

- **辨識**直接用 Whisper 本身的多語能力，不需另外下載模型。建議 `large-v3` 或 `large-v3-turbo`；small／base 對這三種語言明顯較差
- **翻譯建議只用 LLM 伺服器**（預設 gemma4:26b）。翻成外語的提示詞用目標語言寫（比照上游中翻日、中翻韓的做法），
  並檢查譯文：譯成中文卻沒有漢字、夾帶天城文或越南文聲調字母，譯成印地語卻沒有天城文……都會重試一次
- NLLB 也接上了這三種語言，但 **NLLB 是 CC-BY-NC-4.0（非商業）**，集團內部使用也請不要選它
- Argos 只有英翻中，這些模式不支援
- **幻覺過濾**：三種語言各自一套（不能落到中文過濾，否則整句會被丟掉——上游加韓文時踩過）。
  清單是初版，取自 Whisper 常見的 YouTube 結尾語與字幕歸屬（例：越南文「Ghiền Mì Gõ」、印尼文「Terima kasih telah menonton」），
  **還沒有像上游韓文那樣用靜音、雜訊實測**；實際使用看到新的幻覺請回報補上
- **中文翻成外語的長度比例**：中文很精簡，翻成越南文、印尼文、印地語常超過原文 4 倍，原本會被當成幻覺丟掉，這些方向放寬為 10 倍
- **會議摘要**：有中文譯文的模式（X翻中、雙向）照常走會議分析；只有印地語或越南文原文的逐字稿（純轉錄、X翻英）
  改用舊的摘要方式（會議分析的引用比對目前只認中文與英文，同上游對日文、韓文的處理）
- **逐字稿校正**：不准把印地語、越南文的行「校正」成別的語言（沒有天城文、聲調字母全不見的校正結果一律不採用）

### 給一般同仁用的簡易頁面（`/simple`）

原本的 WebUI 選項很多，適合 IT；一般同仁改用簡易頁面：`http://<伺服器>:19781/simple`。
**安裝與架構說明見 [INSTALL.md](INSTALL.md)。**

- **混合模式**：本機模式（沒有 GPU 伺服器時，CPU 跑小模型＋M2M100 翻譯）／伺服器模式，IT 在 **`/simple/admin`** 切換，不用改檔案
- **導覽**：第一次打開自動開始，右上角「導覽」可再看（五種語言）
- **精簡字幕畫面**（`/simple/live`）：對話模式、字幕模式（黑底大字）、懸浮字幕；五種語言、字體大小 A−／A+；
  **我要看的語言**：每一句用看的人選的語言大字顯示（雙向會議兩種語言都有），可勾「只顯示我的語言」。
  其他電腦用瀏覽器連進來看是唯讀（不能停止）
- **分享字幕**：字幕畫面的「分享」顯示 QR Code 與網址（本機產生，不連網），其他人用手機掃描就能看、各選各的語言。
  IT 要先在設定頁開啟「允許其他電腦或手機連進來看字幕」
- **密碼整合**：IT 設的「同仁密碼」同時是簡易頁面（從別台電腦）與觀看分享字幕的密碼（寫進 WebUI 的唯讀密碼），只要設一組
- IT 設定頁只有繁中與英文

畫面支援**繁體中文、English、Bahasa Indonesia、Tiếng Việt、हिन्दी**：依瀏覽器語言自動選擇，右上角可切換（記在瀏覽器裡）。
文字都在 `simple.html` 的 `I18N` 對照表；`node group/tests/check_i18n.js` 檢查每種語言的詞條是否齊全。
產出的會議紀錄目前一律是中文；按「開始」後切到的字幕畫面沿用完整 WebUI，介面仍是中文。
程式都在 `group/`（`simple_routes.py`、`simple.html`），`webui.py` 只多一小段把它掛上去。

| 分頁 | 同仁要做的事 | 在哪裡用 |
|---|---|---|
| **即時字幕** | 選「對方說什麼語言」→（要說話就勾「雙向」）→ 開始，切到原本的字幕畫面 | **只能在自己的電腦上**（要抓這台電腦播出來的聲音）：每台電腦安裝本專案，打開 `http://localhost:19781/simple` |
| **錄音 → 會議紀錄** | 選檔 → 選錄音的語言 → 送出；完成後下載會議紀錄、逐字稿、字幕檔 | 任何電腦的瀏覽器連到 IT 的伺服器 |

- 會議紀錄一次處理一件，其他人排隊（畫面會顯示前面還有幾件）；每台瀏覽器只看得到自己送的錄音
- 跟完整 WebUI 的「開始／停止」互不干擾
- 辨識模型、翻譯模型、講者辨識都由 IT 設定；LLM 伺服器與 GPU 伺服器沿用 `config.json` 原本的設定

#### IT 設定（`config.json`，全部可省略）

```json
"pcg_simple": {
  "password": "大家共用的同仁密碼",
  "asr_model": "large-v3-turbo",
  "live_model": "large-v3-turbo",
  "llm_model": "gemma4:26b",
  "summary_model": "",
  "diarize": true,
  "keep_days": 14
}
```

- `password`：遠端連進來要輸入（本機不用）。第一次有人使用時自動換成雜湊存回，設定檔裡不會留明文。
  空白＝不需要密碼；建議設定，並搭配 WebUI 原本的來源 IP 限制
- `keep_days`：「我送出的錄音」清單保留幾天。**錄音檔（`recordings/simple/`）與產出檔（`logs/`）不會自動刪除**，請 IT 依公司的資料保存規定定期清理
- `scenarios`：要調整「錄音的語言」選項時，照 `simple_routes.py` 的 `DEFAULT_SCENARIOS` 格式填

### 尚未處理

- REST API（`jtlw_api/`）的語言清單還沒加這三種語言
- 雙向語音口譯（念出來）仍只支援英中雙向
- 台語模式（Breeze-ASR-26）、Qwen3-ASR 不適用這三種語言
- 原作者的 `--upgrade` 會蓋掉集團版：已在 `install.sh`、`install.ps1` 擋下，改用 `git pull`（見 INSTALL.md）
- 用原作者的 `install.ps1`／`install.sh`（有網路、用 git 的安裝方式）建立的桌面捷徑會打開完整 WebUI，這種電腦要另外加書籤 `http://localhost:19781/simple`。**集團的離線安裝檔不受影響**：它建立的「PCG 會議翻譯」捷徑直接打開簡易頁面

## 測試

不需要 AI 模型或 GPU：

```bash
python3 -m unittest group/tests/test_xlangs.py -v    # 新語言的程式邏輯（20 項）
python3 -m unittest group/tests/test_simple.py -v    # 簡易頁面：用假的主程式跑完上傳、排隊、處理、下載、密碼、取消（7 項）
```

**還需要實機驗證**：用真的印尼文、越南文、印地語會議錄音，跑離線處理與即時字幕，確認辨識、翻譯、摘要品質。

## 同步上游新版

```bash
git remote add upstream https://github.com/jasoncheng7115/jt-live-whisper.git   # 只需設定一次
git fetch upstream
git merge upstream/main
python3 -m unittest group/tests/test_xlangs.py
```

集團版的語言設定集中在 `translate_meeting.py` 的 `_XLANGS` 區塊（搜尋「集團版」），衝突大多會落在這附近與少數判斷式。
