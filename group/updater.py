"""PCG 集團版：一鍵更新（小更新包）。

更新來源（照順序找，先找到較新的就用）：
  1. 公司共用資料夾（IT 在設定頁填，例如 \\\\檔案伺服器\\PCG\\）：IT 把 PCG-Update-<版本>.exe 放進去。
     不能上網、只連得到公司內網的電腦也能更新。旁邊有 <檔名>.sha256 就會比對
  2. GitHub 發布頁（repo 公開時）：只認這個 repo 的發布附檔，比對 GitHub 提供的 SHA-256
只下載小更新包；新版只有完整安裝檔時回報 kind="full"，畫面請同仁找 IT。
小更新包本身會檢查能不能裝（沒裝過、套件不同就拒絕），裝完跑自我檢查。
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

GITHUB_REPO = "fairy715/PCG-live-whisper"
GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
GITHUB_DL_PREFIX = f"https://github.com/{GITHUB_REPO}/releases/download/"
PATCH_RE = re.compile(r"^PCG-Update-(\d{4}\.\d{1,2}\.\d{1,2}\.r\d+)\.exe$", re.I)
FULL_RE = re.compile(r"^PCG-Meeting-Translator-Setup-(\d{4}\.\d{1,2}\.\d{1,2}\.r\d+)\.exe$", re.I)
MAX_PATCH_BYTES = 300 * 1024 * 1024
# 這一版新增的功能（r19）：發布頁附 whats-new.json，共用資料夾放 PCG-Update-<版本>.whats-new.json。
# 同仁頁面打開時用它跳出「有新版本、這次新增了什麼」。內容只當純文字顯示；版本對不上就不用（避免舊說明配新版）
WHATS_NEW = "whats-new.json"
WN_LANGS = ("zh", "en", "id", "vi", "hi")
WN_MAX_ITEMS = 8
WN_MAX_CHARS = 240


def highlights(data, version):
    """whats-new.json 的內容 → {語言: [重點, …]}；格式不對或版本不是這一版 → {}"""
    if not isinstance(data, dict) or str(data.get("version") or "").lstrip("v") != str(version):
        return {}
    out = {}
    for L in WN_LANGS:
        items = data.get(L)
        if isinstance(items, list):
            clean = [str(x).strip()[:WN_MAX_CHARS] for x in items if isinstance(x, str) and x.strip()]
            if clean:
                out[L] = clean[:WN_MAX_ITEMS]
    return out


def parse_ver(v):
    """'2026.11.5.r7'（可有前置 v）→ (2026, 11, 5, 7)；格式不對（例如 dev）→ None"""
    m = re.fullmatch(r"v?(\d{4})\.(\d{1,2})\.(\d{1,2})\.r(\d+)", str(v or "").strip())
    return tuple(int(x) for x in m.groups()) if m else None


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def from_share(folder):
    """共用資料夾裡最新的一版：{"version", "kind", "path", "sha256"}；資料夾不存在或沒有檔案 → None"""
    if not folder:
        return None
    d = Path(folder)
    try:
        names = [p.name for p in d.iterdir() if p.is_file()]
    except OSError:
        return None
    best = None
    for n in names:
        for rx, kind in ((PATCH_RE, "patch"), (FULL_RE, "full")):
            m = rx.match(n)
            if not m:
                continue
            v = parse_ver(m.group(1))
            # 同一版同時有完整安裝檔與小更新包：用小更新包
            if v and (best is None or v > best[0] or (v == best[0] and kind == "patch")):
                best = (v, m.group(1), kind, n)
    if not best:
        return None
    _, ver, kind, name = best
    sha = ""
    side = d / (name + ".sha256")
    if kind == "patch" and side.is_file():
        try:
            sha = side.read_text(encoding="utf-8", errors="replace").split()[0].lower()
        except (OSError, IndexError):
            sha = ""
    wn = {}
    for cand in (d / f"PCG-Update-{ver}.whats-new.json", d / WHATS_NEW):
        if cand.is_file():
            try:
                wn = highlights(json.loads(cand.read_text(encoding="utf-8-sig")[:65536]), ver)
            except (OSError, ValueError):
                wn = {}
            if wn:
                break
    return {"version": ver, "kind": kind, "path": str(d / name), "sha256": sha, "source": "share",
            "notes_url": "", "highlights": wn}


def from_github(timeout=8, fetch=None):
    """GitHub 最新發布：有小更新包 → kind=patch（附下載網址與 SHA-256）；只有完整安裝檔 → kind=full"""
    if fetch is None:
        def fetch(url):
            req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json",
                                                       "User-Agent": "PCG-Meeting-Translator-updater"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
    try:
        rel = fetch(GITHUB_API)
    except Exception:  # noqa: BLE001  連不上網、repo 改私人、被擋：都當作沒有更新
        return None
    ver = str(rel.get("tag_name") or "").lstrip("v")
    if not parse_ver(ver):
        return None
    patch = None
    full = False
    wn_url = ""
    for a in rel.get("assets") or []:
        name = str(a.get("name") or "")
        if PATCH_RE.match(name):
            patch = a
        elif FULL_RE.match(name):
            full = True
        elif name == WHATS_NEW:
            wn_url = str(a.get("browser_download_url") or "")
    out = {"version": ver, "source": "github", "notes_url": str(rel.get("html_url") or ""), "highlights": {}}
    if wn_url.startswith(GITHUB_DL_PREFIX):
        try:
            out["highlights"] = highlights(fetch(wn_url), ver)
        except Exception:  # noqa: BLE001  沒有說明也照常更新
            pass
    if patch:
        url = str(patch.get("browser_download_url") or "")
        digest = str(patch.get("digest") or "")
        if not url.startswith(GITHUB_DL_PREFIX) or not digest.startswith("sha256:"):
            return None                  # 只接受這個 repo 的發布附檔，而且一定要有指紋可以比對
        out.update(kind="patch", url=url, sha256=digest.split(":", 1)[1].lower(),
                   size=int(patch.get("size") or 0), name=str(patch.get("name")))
        return out
    if full:
        out.update(kind="full")
        return out
    return None


def check(current, share="", use_github=True, github_fetch=None):
    """回傳 {"available": bool, "latest": {...} 或 None}。current 是目前版本（'dev' 不提供更新）"""
    cur = parse_ver(current)
    if not cur:
        return {"available": False, "latest": None, "reason": "dev"}
    cands = [c for c in (from_share(share), from_github(fetch=github_fetch) if use_github else None) if c]
    newer = [c for c in cands if parse_ver(c["version"]) and parse_ver(c["version"]) > cur]
    if not newer:
        return {"available": False, "latest": None}
    # 最新的版本；同一版兩邊都有時用共用資料夾（公司內網，比較快）
    newer.sort(key=lambda c: (parse_ver(c["version"]), c["kind"] == "patch", c["source"] == "share"), reverse=True)
    return {"available": True, "latest": newer[0]}


def download(latest, dest_dir: Path, opener=None):
    """把小更新包放到 dest_dir，比對 SHA-256。回傳檔案路徑；失敗丟 RuntimeError（訊息給畫面看）"""
    if latest.get("kind") != "patch":
        raise RuntimeError("這一版需要完整安裝檔，請找 IT 更新")
    dest_dir.mkdir(parents=True, exist_ok=True)
    name = f"PCG-Update-{latest['version']}.exe"
    dst = dest_dir / name
    tmp = dest_dir / (name + ".part")
    if latest["source"] == "share":
        shutil.copyfile(latest["path"], tmp)
    else:
        url = latest["url"]
        if not url.startswith(GITHUB_DL_PREFIX):
            raise RuntimeError("下載網址不是集團版的發布頁")
        opener = opener or (lambda u: urllib.request.urlopen(
            urllib.request.Request(u, headers={"User-Agent": "PCG-Meeting-Translator-updater"}), timeout=60))
        n = 0
        with opener(url) as r, open(tmp, "wb") as f:
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                n += len(chunk)
                if n > MAX_PATCH_BYTES:
                    raise RuntimeError("下載的檔案大小不對")
                f.write(chunk)
    want = (latest.get("sha256") or "").lower()
    if want and _sha256(tmp) != want:
        tmp.unlink(missing_ok=True)
        raise RuntimeError("下載的檔案指紋不符（可能下載不完整或被竄改），已刪除，沒有安裝")
    if latest["source"] == "github" and not want:
        tmp.unlink(missing_ok=True)
        raise RuntimeError("發布頁沒有提供檔案指紋，不安裝")
    os.replace(tmp, dst)
    return dst


def launch(exe: Path):
    """在背景啟動小更新包（跟這個程式脫鉤：更新時會關掉這個程式）。
    /SILENT：只顯示進度視窗；失敗時的訊息照常顯示。/RELAUNCH=1：裝完自動重新開啟（不開新的瀏覽器分頁）"""
    if os.name != "nt":
        raise RuntimeError("一鍵更新只支援 Windows")
    args = [str(exe), "/SILENT", "/NORESTART", "/RELAUNCH=1"]
    flags = 0x00000008 | 0x00000200          # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    try:
        subprocess.Popen(args, creationflags=flags | 0x01000000, close_fds=True)   # + CREATE_BREAKAWAY_FROM_JOB
    except OSError:
        subprocess.Popen(args, creationflags=flags, close_fds=True)
