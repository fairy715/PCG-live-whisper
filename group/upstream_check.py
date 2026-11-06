"""PCG 集團版：檢查原作者（jasoncheng7115/jt-live-whisper）有沒有新的更新（GitHub Actions 每週一執行）。

    python group/upstream_check.py --out 結果.md
    結束代碼：0＝有新的更新（結果寫在 --out，第一行是標題）；3＝沒有新的更新

只檢查與試合併，不會真的合併或發布：集團版改了不少原作者的程式，合併要人確認後再做。
需要事先：git remote 有 upstream、已 fetch。試合併在暫時的分支上做，結束後回到原本的位置。
"""
import argparse
import re
import subprocess
import sys

UP = "upstream/main"
# 原作者的更新裡，跟集團版（Windows 同仁電腦）多半無關的：Mac 專用、Linux 安裝程式等
MAC_HINT = re.compile(r"mac|apple|mlx|metal|screencapturekit|\bsck\b|install\.sh|linux", re.I)


def git(*a, check=True):
    r = subprocess.run(["git", *a], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(a)}：{r.stderr.strip()}")
    return r.stdout.strip()


def app_version(ref):
    try:
        src = git("show", f"{ref}:translate_meeting.py")
    except RuntimeError:
        return "?"
    m = re.search(r'^APP_VERSION = "([^"]+)"', src, re.M)
    return m.group(1) if m else "?"


def run_tests():
    r = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "group/tests", "-q"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    tail = [ln for ln in r.stderr.splitlines() if ln.startswith(("Ran ", "OK", "FAILED", "FAIL:", "ERROR:"))]
    return r.returncode == 0, tail[-8:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    base = git("merge-base", "HEAD", UP)
    new = git("rev-list", "--reverse", f"{base}..{UP}").split()
    if not new:
        print("原作者沒有新的更新")
        sys.exit(3)
    head_up = new[-1][:7]
    ours_v, theirs_v = app_version("HEAD"), app_version(UP)
    commits = git("log", "--reverse", "--format=%h%x09%ad%x09%s", "--date=short", f"{base}..{UP}").splitlines()
    up_files = set(filter(None, git("diff", "--name-only", base, UP).splitlines()))
    our_files = set(filter(None, git("diff", "--name-only", base, "HEAD").splitlines()))
    overlap = sorted(up_files & our_files)

    # 試合併（暫時的分支），乾淨的話跑集團版的測試
    start = git("rev-parse", "HEAD")
    git("checkout", "-q", "-B", "upstream-trial", start)
    merged = subprocess.run(["git", "merge", "--no-edit", "-q", UP], capture_output=True, text=True).returncode == 0
    conflicts = []
    tests_ok, tests_tail = None, []
    if merged:
        tests_ok, tests_tail = run_tests()
    else:
        conflicts = sorted(filter(None, git("diff", "--name-only", "--diff-filter=U", check=False).splitlines()))
        git("merge", "--abort", check=False)
    git("checkout", "-q", "--detach", start)

    ver = f"v{theirs_v}" if theirs_v != ours_v else f"v{theirs_v}（版本號沒變）"
    title = f"原作者有更新：{ver}，{len(new)} 個變更（{head_up}）"
    L = [title, "",
         f"原作者 [jt-live-whisper](https://github.com/jasoncheng7115/jt-live-whisper) 有集團版還沒合併的更新。",
         f"集團版目前根據 **v{ours_v}**；原作者最新 **v{theirs_v}**。", ""]
    if merged and tests_ok:
        L.append("**試合併：✅ 沒有衝突，集團版的測試全部通過。** 可以請 Claude 合併、在乾淨的 Windows 上測試後發新版。")
    elif merged:
        L.append("**試合併：⚠️ 沒有衝突，但集團版的測試沒有全部通過**（見下方），合併時要一起修正。")
    else:
        L.append(f"**試合併：⚠️ 有 {len(conflicts)} 個檔案衝突**，原作者和集團版改到同一段程式，合併時要人工處理。")
    L += ["", "### 原作者的變更", "", "| 變更 | 日期 | 說明 | |", "|---|---|---|---|"]
    for c in commits:
        h, d, s = (c.split("\t") + ["", ""])[:3]
        tag = "Mac／Linux 相關，集團版多半不用" if MAC_HINT.search(s) else ""
        L.append(f"| [`{h}`](https://github.com/jasoncheng7115/jt-live-whisper/commit/{h}) | {d} | {s.replace('|', '／')} | {tag} |")
    L += ["", f"### 改到的檔案（{len(up_files)} 個）", ""]
    if conflicts:
        L += ["衝突：" + "、".join(f"`{f}`" for f in conflicts), ""]
    if overlap:
        L += ["集團版也改過、要特別注意：" + "、".join(f"`{f}`" for f in overlap[:30]) + ("…" if len(overlap) > 30 else ""), ""]
    others = sorted(up_files - set(overlap))
    if others:
        L += ["其他：" + "、".join(f"`{f}`" for f in others[:40]) + ("…" if len(others) > 40 else ""), ""]
    if tests_tail:
        L += ["### 測試結果", "", "```", *tests_tail, "```", ""]
    L += ["### 下一步", "",
          "要跟上這次更新，請 Claude「合併原作者的更新」：合併、處理衝突、跑測試，再發一版（一鍵更新會通知同仁）。"
          "不需要的更新（例如 Mac 專用）可以不跟，關掉這張 Issue 即可。", "",
          "---", "_每週一自動檢查（.github/workflows/upstream-check.yml）；不會自動合併或發布。_"]
    with open(a.out, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print(title)


if __name__ == "__main__":
    main()
