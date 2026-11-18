# 發布檢查清單（每次打包 rN 都要做）

使用者 2026-11-16 交代：**每次打包，說明該改的就要改**。打包前照這份清單走一遍，沒做完不要觸發 release.yml。

## 1. 先確認要發布的內容
- `git log v<上一版>..origin/main`：列出這次包含的每一項變更（含原作者合併）
- 等推上 main 的那次「Windows 安裝程式」CI 通過再打包（推新 commit 會取消正在跑的 CI）

## 2. 說明文件（該改的都要改）
| 檔案 | 要做的事 |
|---|---|
| `group/whats-new.json` | `release` 改成這次的 `rN`；zh／en／id／vi／hi 各 1～5 點，一點一句、240 字以內（發布流程只在 release 相符時才附上） |
| `README.md` 版本紀錄 | 新增一列 `| **rN** | 日期 | 主要更新 |` |
| `README.md` 功能表 | 「給同仁」「給 IT」裡跟這次變更有關的列要一起改（例如 CPU、安全、自動測試） |
| `README.md` 截圖 | 畫面有變（含頁面最下方的版本號）就用這一版重拍 `group/docs/images/` 的截圖 |
| IT 必讀（4 種語言） | `group/INSTALL.md`、`group/IT-GUIDE-en.md`、`-id.md`、`-vi.md`：設定、環境變數、行為改變 |
| 使用情境（4 種語言） | `group/使用情境.md`、`group/USE-CASES-en.md`、`-id.md`、`-vi.md`：同仁操作方式有變時 |
| 安裝說明（4 種語言） | `group/安裝說明.md`、`group/INSTALL-GUIDE-*.md`：安裝或更新步驟有變時 |
| `SECURITY.md` | 跟安全有關的變更、原作者新的安全公告 |
| 廣告影片 | `group/docs/promo/`：同仁頁面的畫面有變時重拍 `ui-*.png` 並重新產生影片（先逐像素比對，沒變就不用）。這一版有同仁看得到的新功能、但不在廣告拍到的畫面裡時，問使用者要不要加一段（r24 的聲音測試就是這樣加的）；影片長度變了要一起改 README 的秒數與封面右下角的時間 |

## 3. 檢查
- `python3 -m unittest discover -s group/tests`
- `node group/tests/check_i18n.js`
- `python3 group/windows/whats_new_prep.py <版本> <輸出>`：確認新功能說明會被附上

## 4. 打包與驗證
- 觸發 `release.yml`（`models=small`），版本號是「日期.r＋第幾次執行」，要等於 whats-new.json 的 rN
- 發布後確認：發布頁有完整安裝檔、小更新包、`.sha256`、`whats-new.json`；記錄裡自我檢查全部通過、小更新包與共用資料夾一鍵更新「全部完成」
- 看記錄裡「離 2 GB 上限還有 N MB」（GitHub 單檔上限 2 GB，超過會發布失敗）：少於 25 MB 會出現警告，要告訴使用者並先減少安裝檔的內容。`group/docs`（宣傳影片、截圖）已經不放進安裝檔（`PCG-Setup.iss` 的 Excludes）；新增只給 GitHub 看的大檔案也要放在被排除的資料夾
- 告訴使用者：這版內容、CI 驗證到哪裡、哪些要在實機測
