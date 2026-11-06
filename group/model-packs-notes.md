## 模型包（語音辨識與翻譯）

PCG 會議翻譯的**額外模型**，由 IT 在設定頁的「**模型管理**」安裝（`http://localhost:19781/simple/admin`），**同仁不用自己下載**。需要 PCG 會議翻譯 **r15 以上**。

| 模型包 | 用途 | 大小 | 授權 |
|---|---|---|---|
| PhoWhisper small／medium | 越南文語音辨識（越南 VinAI 加強版 Whisper） | 約 250／780 MB | BSD-3-Clause |
| Whisper small／medium 印尼文（cahya） | 印尼文語音辨識 | 約 250／780 MB | Apache-2.0 |
| Whisper small／medium 印地語（vasista22） | 印地語語音辨識 | 約 250／780 MB | Apache-2.0 |
| MADLAD-400 3B（Google） | 本機翻譯，印尼文、越南文、印地語比內建 M2M100 好（較慢） | 約 3 GB（分成兩個檔案） | Apache-2.0 |

* **small**：CPU 上即時字幕也跑得動。**medium**：比較準、慢約 2～3 倍，建議錄音檔用（有 NVIDIA 顯示卡時即時字幕也可以）。
* 裝好後在「模型管理」指定每種語言的「即時字幕」「錄音檔」各用哪個模型；只用在「對方說這種語言」的單向字幕與錄音檔，雙向、教室模式照舊用內建的多語模型。
* **不能上網的電腦**：把這一頁的 `catalog.json` 與模型包檔案（`*.zip`、`*.zip.001`…）放到 IT 設定頁「更新」的公司共用資料夾（或它的 `models` 子資料夾），「模型管理」就會列出來。
* 每個檔案下載後都會比對 SHA-256 指紋（寫在 `catalog.json`），不符就不安裝。
* 模型由原作者發布在 Hugging Face，這裡轉成 CTranslate2 int8 格式；實際準確度請用公司自己的錄音比較後再決定要不要換。
