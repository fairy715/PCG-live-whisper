"""PCG 集團版：「回報問題」的診斷檔。

同仁在簡易頁面（或 IT 在設定頁）按「回報問題」→ 這裡把版本、電腦規格、設定（金鑰與密碼遮掉）、
模型、最近的工作狀態與程式記錄打包成一個 zip，存在 group_data/reports/，再由瀏覽器下載，
同仁把檔案寄給 IT。不連網、不上傳到任何地方。

不放進診斷檔的：錄音檔、逐字稿、會議紀錄、檔名與主題（工作只留狀態與錯誤）、
API 金鑰、密碼與雜湊。程式記錄是選擇性的（可能有部分字幕內容），同仁可以取消勾選。
"""
import json
import os
import platform
import re
import shutil
import sys
import time
import zipfile
from pathlib import Path

REPORT_DIR = "reports"
KEEP_REPORTS = 10
_NAME_RE = re.compile(r"PCG-report-[A-Za-z0-9_-]{1,40}-\d{8}-\d{6}\.zip")
_SECRET_KEY = re.compile(r"key|password|passwd|hash|token|secret|sha256|credential", re.I)
_SECRET_TEXT = [
    (re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]{8,}"), r"\1***"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{8,}"), "sk-***"),
    (re.compile(r"(?i)((?:api[_-]?key|token|password)[\"']?\s*[:=]\s*[\"']?)[^\s\"',}]{4,}"), r"\1***"),
]
LOG_FILES = ["webui.log", "webui-error.log", "update.log", "install.log", "gpu_check.log", "gpu_check.json"]
LOG_TAIL_LINES = 400
LOG_TAIL_BYTES = 256 * 1024
JOB_LOGS = 3                      # 最近幾件工作的記錄（失敗的優先）
JOB_FIELDS = ("id", "scenario", "mode", "state", "stage", "error", "error_code", "created", "started", "finished")


def valid_name(name):
    return bool(_NAME_RE.fullmatch(name or ""))


def redact(obj):
    """設定裡名稱像金鑰、密碼、雜湊的值一律換成 ***（有沒有設還看得出來）"""
    if isinstance(obj, dict):
        return {k: ("***" if _SECRET_KEY.search(str(k)) and v not in ("", None, {}, [])
                    and not isinstance(v, (dict, list, bool)) else redact(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact(v) for v in obj]
    return obj


def redact_text(s):
    for pat, rep in _SECRET_TEXT:
        s = pat.sub(rep, s)
    return s


def redact_args(args):
    """即時字幕的命令列：--xxx-key 後面的值遮掉"""
    out, hide = [], False
    for a in args or []:
        a = str(a)
        out.append("***" if hide else redact_text(a))
        hide = a.startswith("--") and bool(_SECRET_KEY.search(a))
    return out


def tail(path: Path, lines=LOG_TAIL_LINES, max_bytes=LOG_TAIL_BYTES):
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(0, size - max_bytes))
            data = f.read()
    except OSError:
        return None
    text = data.decode("utf-8", "replace")
    if size > max_bytes:
        text = text.split("\n", 1)[-1]
    return redact_text("\n".join(text.splitlines()[-lines:]))


def _ram_gb():
    try:
        if os.name == "nt":
            import ctypes

            class MS(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
            m = MS()
            m.dwLength = ctypes.sizeof(MS)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):
                return round(m.ullTotalPhys / 2**30, 1), round(m.ullAvailPhys / 2**30, 1)
        with open("/proc/meminfo", encoding="ascii") as f:
            info = {ln.split(":")[0]: int(ln.split()[1]) for ln in f if ":" in ln and ln.split()[1].isdigit()}
        return round(info["MemTotal"] / 2**20, 1), round(info.get("MemAvailable", 0) / 2**20, 1)
    except Exception:  # noqa: BLE001
        return None, None


def _cpu_name():
    if os.name == "nt":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as k:
                return str(winreg.QueryValueEx(k, "ProcessorNameString")[0]).strip()
        except OSError:
            pass
    try:
        with open("/proc/cpuinfo", encoding="utf-8") as f:
            for ln in f:
                if ln.startswith("model name"):
                    return ln.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or platform.machine()


def _dir_mb(d: Path):
    total = 0
    for root, _dirs, files in os.walk(d):
        for n in files:
            try:
                total += os.path.getsize(os.path.join(root, n))
            except OSError:
                pass
    return round(total / 2**20)


def computer_name():
    n = os.environ.get("COMPUTERNAME") or platform.node() or "pc"
    return re.sub(r"[^A-Za-z0-9_-]", "_", n)[:40] or "pc"


def system_info(base_dir: Path):
    total, avail = _ram_gb()
    try:
        du = shutil.disk_usage(base_dir)
        disk = {"free_gb": round(du.free / 2**30, 1), "total_gb": round(du.total / 2**30, 1)}
    except OSError:
        disk = {}
    models = base_dir / "models"
    gpu_dir = base_dir / "gpu"
    return {
        "computer": computer_name(),
        "os": platform.platform(),
        "python": sys.version.split()[0],
        "cpu": _cpu_name(),
        "cpu_logical": os.cpu_count(),
        "ram_gb": total, "ram_free_gb": avail,
        "disk": disk,
        "app_dir": str(base_dir),
        "gpu_pack": sorted(p.name for p in gpu_dir.iterdir()) if gpu_dir.is_dir() else [],
        "models": {p.name: _dir_mb(p) for p in sorted(models.iterdir()) if p.is_dir() and p.name != "packs"}
        if models.is_dir() else {},
        "hf_cache": sorted(p.name for p in (base_dir / "hf_cache").iterdir() if p.name.startswith("models--"))
        if (base_dir / "hf_cache").is_dir() else [],
    }


def _summary_text(info):
    v = info.get("version") or {}
    s = info.get("system") or {}
    c = info.get("client") or {}
    rows = [
        ("時間 Time", info.get("time")),
        ("版本 Version", f"{v.get('version')}" + (f" ({v['commit']})" if v.get("commit") else "")
         + f" · jt-live-whisper {v.get('upstream') or '?'}"),
        ("電腦 Computer", s.get("computer")),
        ("系統 OS", s.get("os")),
        ("處理器 CPU", f"{s.get('cpu')} · {s.get('cpu_logical')} threads"),
        ("記憶體 RAM", f"{s.get('ram_gb')} GB（可用 free {s.get('ram_free_gb')} GB）"),
        ("磁碟 Disk", f"{(s.get('disk') or {}).get('free_gb')} GB free / {(s.get('disk') or {}).get('total_gb')} GB"),
        ("GPU 加速包", ", ".join(s.get("gpu_pack") or []) or "—"),
        ("模型包 Packs", ", ".join(p.get("id", "") for p in info.get("packs") or []) or "—"),
        ("即時字幕 Live", "進行中 running" if (info.get("live") or {}).get("running") else "—"),
        ("瀏覽器 Browser", c.get("ua")),
        ("畫面 Page", " · ".join(str(c[k]) for k in ("page", "lang", "tab", "screen") if c.get(k)) or "—"),
    ]
    out = ["PCG 會議翻譯：問題回報 / Problem report", "=" * 40, ""]
    out += [f"{k}: {val}" for k, val in rows]
    out += ["", "同仁的說明 / Description:", info.get("description") or "（沒有填 / none）", ""]
    out += ["檔案 Files: summary.txt, report.json, config.json（金鑰與密碼已遮掉 / secrets removed）"
            + (", logs/" if info.get("with_logs") else "（沒有附程式記錄 / no logs）")]
    return "\n".join(out) + "\n"


def build(base_dir: Path, *, description="", client=None, with_logs=True, config=None, version=None,
          packs=None, jobs=None, live=None):
    """產生診斷檔，回傳 zip 的路徑。jobs：工作佇列的 dict（只取狀態欄位）"""
    base_dir = Path(base_dir)
    data = base_dir / "group_data"
    out_dir = data / REPORT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    now = time.localtime()
    name = f"PCG-report-{computer_name()}-{time.strftime('%Y%m%d-%H%M%S', now)}.zip"
    client = {k: str(v)[:300] for k, v in (client or {}).items() if k in ("ua", "lang", "tab", "page", "screen", "me", "scene", "live_lang")}
    job_list = sorted((jobs or {}).values(), key=lambda j: j.get("created") or 0, reverse=True)[:20]
    info = {
        "time": time.strftime("%Y-%m-%d %H:%M:%S %z", now),
        "version": version or {},
        "system": system_info(base_dir),
        "packs": [{k: p.get(k) for k in ("id", "type", "version", "size_mb", "languages")} for p in packs or []],
        "live": {"running": bool((live or {}).get("running")), "args": redact_args((live or {}).get("args"))},
        "jobs": [{k: j.get(k) for k in JOB_FIELDS} for j in job_list],
        "client": client,
        "description": str(description or "")[:4000],
        "with_logs": bool(with_logs),
    }
    tmp = out_dir / (name + ".part")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("summary.txt", _summary_text(info))
        z.writestr("report.json", json.dumps(info, ensure_ascii=False, indent=2, default=str))
        z.writestr("config.json", json.dumps(redact(config or {}), ensure_ascii=False, indent=2))
        if with_logs:
            for n in LOG_FILES:
                t = tail(data / n)
                if t is not None:
                    z.writestr(f"logs/{n}", t)
            failed = [j for j in job_list if j.get("state") == "failed"]
            rest = [j for j in job_list if j not in failed]
            for j in (failed + rest)[:JOB_LOGS]:
                jid = str(j.get("id") or "")
                if re.fullmatch(r"[0-9A-Za-z-]{1,40}", jid):
                    t = tail(data / f"job_{jid}.log", lines=200)
                    if t is not None:
                        z.writestr(f"logs/job_{jid}.log", t)
    tmp.replace(out_dir / name)
    old = sorted((p for p in out_dir.glob("PCG-report-*.zip") if valid_name(p.name)),
                 key=lambda p: p.stat().st_mtime, reverse=True)
    for p in old[KEEP_REPORTS:]:
        try:
            p.unlink()
        except OSError:
            pass
    return out_dir / name
