"""PCG 集團版：模型包（額外的語音辨識／翻譯模型）。

主安裝檔只放基本款（Whisper small、M2M100、Moonshine 英文），其他模型做成「模型包」另外裝，
IT 在設定頁的「模型管理」安裝、更新、移除，並指定每種語言用哪個模型。

磁碟上：<安裝資料夾>/models/packs/<id>/pack.json ＋ 模型檔
    pack.json：{"id", "name", "type": "asr"|"mt", "engine": "faster-whisper"|"madlad",
                "languages": ["vi"], "purpose": ["live", "file"], "version", "size_mb", "license", "source", "note"}
模型包清單（catalog.json，發布在 GitHub 的 model-packs 發布頁，或 IT 放在公司共用資料夾）：
    {"format": 1, "packs": [{…pack.json 的欄位…, "parts": [{"name", "size", "sha256"}]}]}
    每個模型包是一個 zip（裡面是 <id>/pack.json 與模型檔）；超過 GitHub 單檔上限時切成 .001、.002…

不能上網的電腦：IT 把發布頁上的 catalog.json 與模型包檔案放在一鍵更新用的公司共用資料夾（或它的 models 子資料夾）。
"""
import hashlib
import io
import json
import os
import re
import shutil
import threading
import time
import urllib.request
import zipfile
from pathlib import Path

GITHUB_REPO = "fairy715/PCG-live-whisper"
RELEASE_TAG = "model-packs"
GITHUB_RELEASE_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/tags/{RELEASE_TAG}"
GITHUB_DL_PREFIX = f"https://github.com/{GITHUB_REPO}/releases/download/{RELEASE_TAG}/"
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,63}$")
PART_RE = re.compile(r"^[A-Za-z0-9._-]{1,120}$")
LANGS = ("zh", "en", "id", "vi", "hi", "ja", "ko")
UA = {"User-Agent": "PCG-Meeting-Translator-models"}


def packs_dir(base_dir):
    return Path(base_dir) / "models" / "packs"


def _valid_meta(m):
    return (isinstance(m, dict) and ID_RE.match(str(m.get("id", ""))) and m.get("type") in ("asr", "mt")
            and isinstance(m.get("languages", []), list))


def installed(base_dir):
    """這台電腦裝了哪些模型包：[{pack.json 的欄位, "path", "size_mb"}]"""
    out = []
    d = packs_dir(base_dir)
    if not d.is_dir():
        return out
    for p in sorted(d.iterdir()):
        f = p / "pack.json"
        if not p.is_dir() or p.name.startswith(".") or not f.is_file():
            continue
        try:
            m = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not _valid_meta(m) or m["id"] != p.name:
            continue
        m = dict(m, path=str(p))
        m.setdefault("size_mb", round(sum(x.stat().st_size for x in p.rglob("*") if x.is_file()) / 1048576))
        out.append(m)
    return out


def find(base_dir, pid, kind=None, lang=None, purpose=None):
    """找一個裝好、而且符合條件的模型包；沒有回 None"""
    for m in installed(base_dir):
        if m["id"] != pid or (kind and m["type"] != kind):
            continue
        if lang and lang not in m.get("languages", []):
            continue
        if purpose and purpose not in m.get("purpose", ["live", "file"]):
            continue
        return m
    return None


def asr_model_for(base_dir, settings, lang, purpose):
    """IT 指定這個語言（live／file）用哪個語音辨識模型包：回傳給主程式 -m 的名稱 "pack:<id>"，沒有指定或沒裝回 None"""
    pid = ((settings.get("asr_packs") or {}).get(lang) or {}).get(purpose)
    if pid and find(base_dir, pid, "asr", lang, purpose):
        return f"pack:{pid}"
    return None


# ─── 模型包清單 ───────────────────────────────────────────

def _http_json(url, fetch=None, timeout=15):
    if fetch:
        return fetch(url)
    with urllib.request.urlopen(urllib.request.Request(url, headers=dict(UA, Accept="application/vnd.github+json")),
                                timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _share_dirs(share):
    if not share:
        return []
    d = Path(share)
    return [x for x in (d / "models", d) if x.is_dir()]


def _clean_catalog(data, source):
    packs = []
    for p in (data or {}).get("packs", []) if isinstance(data, dict) else []:
        parts = p.get("parts") if isinstance(p, dict) else None
        if not _valid_meta(p) or not isinstance(parts, list) or not parts:
            continue
        if not all(isinstance(x, dict) and PART_RE.match(str(x.get("name", "")))
                   and re.fullmatch(r"[0-9a-f]{64}", str(x.get("sha256", "")).lower()) for x in parts):
            continue
        packs.append(dict(p, source_kind=source))
    return packs


def catalog(share="", use_github=True, fetch=None):
    """可以安裝的模型包：共用資料夾的 catalog.json 優先（公司內網、快），再加上 GitHub 的。
    回傳 ({id: 項目}, 錯誤訊息清單)"""
    out, errors = {}, []
    for d in _share_dirs(share):
        f = d / "catalog.json"
        if f.is_file():
            try:
                for p in _clean_catalog(json.loads(f.read_text(encoding="utf-8")), "share"):
                    out.setdefault(p["id"], dict(p, share_dir=str(d)))
            except (OSError, ValueError) as e:
                errors.append(f"共用資料夾的 catalog.json 讀不了：{e}")
            break
    if use_github:
        try:
            rel = _http_json(GITHUB_RELEASE_API, fetch)
            asset = next((a for a in rel.get("assets", []) if a.get("name") == "catalog.json"), None)
            if asset:
                url = str(asset.get("browser_download_url") or "")
                if not url.startswith(GITHUB_DL_PREFIX):
                    raise ValueError("清單的下載位址不是這個專案的")
                for p in _clean_catalog(_http_json(url, fetch), "github"):
                    out.setdefault(p["id"], p)
        except Exception as e:                       # 連不到 GitHub：只用共用資料夾的
            errors.append(f"GitHub 連不到（{type(e).__name__}）")
    return out, errors


# ─── 安裝／移除 ───────────────────────────────────────────

class _Joined(io.RawIOBase):
    """把切開的幾個檔案當成一個檔案讀（zipfile 要能 seek），不用先接成一個大檔、佔兩倍空間"""

    def __init__(self, paths):
        self.files = [open(p, "rb") for p in paths]
        self.sizes = [os.path.getsize(p) for p in paths]
        self.total = sum(self.sizes)
        self.pos = 0

    def readable(self):
        return True

    def seekable(self):
        return True

    def seek(self, off, whence=0):
        self.pos = {0: off, 1: self.pos + off, 2: self.total + off}[whence]
        return self.pos

    def tell(self):
        return self.pos

    def readinto(self, b):
        n, want, start = 0, len(b), 0
        for f, size in zip(self.files, self.sizes):
            if self.pos < start + size and n < want:
                f.seek(self.pos - start)
                chunk = f.read(min(want - n, start + size - self.pos))
                b[n:n + len(chunk)] = chunk
                n += len(chunk)
                self.pos += len(chunk)
            start += size
        return n

    def close(self):
        for f in self.files:
            f.close()
        super().close()


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


JOBS = {}                 # id → {"state": "downloading"|"installing"|"done"|"failed", "done_mb", "total_mb", "error"}
_LOCK = threading.Lock()


def _get_part(pack, part, dest, opener=None, progress=None):
    name = part["name"]
    if pack.get("share_dir"):
        src = Path(pack["share_dir"]) / name
        if not src.is_file():
            raise RuntimeError(f"共用資料夾少了 {name}")
        shutil.copyfile(src, dest)
        if progress:
            progress(src.stat().st_size)
        return
    url = GITHUB_DL_PREFIX + name
    op = opener or (lambda u: urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60))
    with op(url) as r, open(dest, "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            if progress:
                progress(len(chunk))


def install(base_dir, pack, opener=None):
    """下載（或從共用資料夾複製）→ 每個檔案比對 SHA-256 → 解壓到 models/packs/<id>（換掉舊版）。失敗丟 RuntimeError"""
    pid = pack["id"]
    root = packs_dir(base_dir)
    tmp = root / f".download-{pid}"
    stage = root / f".installing-{pid}"
    for d in (tmp, stage):
        shutil.rmtree(d, ignore_errors=True)
    tmp.mkdir(parents=True)
    total = sum(int(p.get("size") or 0) for p in pack["parts"])
    need = total * 2 + 200 * 1048576
    free = shutil.disk_usage(root).free
    if free < need:
        shutil.rmtree(tmp, ignore_errors=True)
        raise RuntimeError(f"磁碟空間不夠：要 {need / 1073741824:.1f} GB，剩 {free / 1073741824:.1f} GB")
    job = JOBS.setdefault(pid, {})
    job.update(state="downloading", done_mb=0, total_mb=round(total / 1048576), error="")

    def prog(n):
        job["done_mb"] = round(job.get("done_mb", 0) + n / 1048576, 1)
    try:
        paths = []
        for part in pack["parts"]:
            dest = tmp / part["name"]
            _get_part(pack, part, dest, opener, prog)
            if part.get("size") and dest.stat().st_size != int(part["size"]):
                raise RuntimeError(f"{part['name']} 大小不對（下載不完整）")
            if _sha256(dest) != str(part["sha256"]).lower():
                raise RuntimeError(f"{part['name']} 指紋不符（下載不完整或被竄改），沒有安裝")
            paths.append(dest)
        job["state"] = "installing"
        src = _Joined(paths)
        try:
            with zipfile.ZipFile(src) as z:
                for n in z.namelist():
                    p = Path(n)
                    if p.is_absolute() or ".." in p.parts or not n.startswith(pid + "/"):
                        raise RuntimeError(f"模型包裡有不該有的路徑：{n}")
                z.extractall(stage)
        finally:
            src.close()
        meta_f = stage / pid / "pack.json"
        meta = json.loads(meta_f.read_text(encoding="utf-8")) if meta_f.is_file() else None
        if not _valid_meta(meta) or meta["id"] != pid:
            raise RuntimeError("模型包內容不對（pack.json）")
        final = root / pid
        old = root / f".old-{pid}"
        shutil.rmtree(old, ignore_errors=True)
        if final.exists():
            final.rename(old)
        (stage / pid).rename(final)
        shutil.rmtree(old, ignore_errors=True)
        job.update(state="done", done_mb=job["total_mb"])
        return meta
    except Exception as e:
        job.update(state="failed", error=str(e) if isinstance(e, RuntimeError) else f"{type(e).__name__}: {e}")
        raise RuntimeError(job["error"]) from e
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.rmtree(stage, ignore_errors=True)


def install_async(base_dir, pack, opener=None):
    with _LOCK:
        j = JOBS.get(pack["id"]) or {}
        if j.get("state") in ("downloading", "installing"):
            return False
        JOBS[pack["id"]] = {"state": "downloading", "done_mb": 0, "total_mb": 0, "error": "", "started": time.time()}

    def run():
        try:
            install(base_dir, pack, opener)
        except Exception:
            pass                                    # 原因記在 JOBS，設定頁會顯示
    threading.Thread(target=run, daemon=True).start()
    return True


def remove(base_dir, pid):
    if not ID_RE.match(pid or ""):
        raise RuntimeError("模型包代號不正確")
    d = packs_dir(base_dir) / pid
    if not (d / "pack.json").is_file():
        raise RuntimeError("沒有裝這個模型包")
    shutil.rmtree(d)
    JOBS.pop(pid, None)
