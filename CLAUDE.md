# 給 Claude 的固定規則（PCG 會議翻譯）

- 一律用繁體中文回覆使用者。
- **打包（發布 rN）前一定照 [group/RELEASE-CHECKLIST.md](group/RELEASE-CHECKLIST.md) 走一遍：說明該改的就要改**（使用者 2026-11-16 交代）。
- 沒有使用者明確說要打包，不要觸發 release.yml。
- 不要修改 `group/windows/build_bundle.py` 與 `group/windows/requirements-cpu.txt`（改了已安裝的電腦就不能用小更新包）。
- 原作者 jt-live-whisper 的程式盡量不動；集團版的修改集中在 `group/`，必要時在原檔加最小的掛鉤並註明「集團版」。
