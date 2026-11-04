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

### 尚未處理

- REST API（`jtlw_api/`）的語言清單還沒加這三種語言
- 雙向語音口譯（念出來）仍只支援英中雙向
- 台語模式（Breeze-ASR-26）、Qwen3-ASR 不適用這三種語言

## 測試

不需要 AI 模型或 GPU，只檢查程式邏輯：

```bash
python3 -m unittest group/tests/test_xlangs.py -v
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
