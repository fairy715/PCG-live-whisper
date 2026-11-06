"""PCG 集團版：給一般同仁用的簡易頁面（/simple）。

同仁只要做三件事：選錄音檔 → 選「錄音裡主要說什麼語言」→ 送出，等一下就能下載會議紀錄。
辨識模型、翻譯模型、LLM 伺服器、講者辨識這些設定全部由 IT 在 config.json 的 "pcg_simple" 統一設定。

設計：
- 所有程式都在 group/ 裡，webui.py 只多幾行把路由掛上來，同步上游新版時不容易衝突
- 自己的工作佇列，一次只處理一件（GPU 與 LLM 伺服器同時跑多件只會一起變慢），其他人排隊
- 跟完整 WebUI 的「開始／停止」互不干擾：這裡自己啟動 translate_meeting.py，不經過 WebUI 的子程序
- 每台瀏覽器有自己的代號（存在瀏覽器裡），只列出自己送的工作。這只是方便，不是權限控管：
  真正的門檻是 IT 設的「同仁密碼」與 WebUI 原本的來源 IP 限制

config.json 範例（都可省略，省略時用括號裡的預設）：
    "pcg_simple": {
        "password": "大家共用的密碼",        // 第一次啟動時自動換成雜湊存回（空＝不需要密碼）
        "asr_model": "large-v3-turbo",       // 辨識模型（large-v3-turbo）
        "llm_model": "gemma4:26b",           // 翻譯模型（主程式預設）
        "summary_model": "",                 // 摘要模型（主程式預設）
        "diarize": true,                     // 講者辨識（true）
        "keep_days": 14,                     // 工作紀錄保留天數；錄音與產出檔不會自動刪（14）
        "scenarios": [ ... ]                 // 自訂情境，格式同下方 DEFAULT_SCENARIOS
    }
LLM 伺服器與 GPU 伺服器沿用 config.json 原本的 llm_host／remote_whisper 設定。
"""
import json
import os
import re
import secrets
import subprocess
import sys
import threading
import time
from pathlib import Path

# 情境：同仁看到的是「錄音裡主要說什麼語言 → 拿到什麼」，背後對應主程式的模式代號
DEFAULT_SCENARIOS = [
    {"id": "zh", "mode": "zh", "title": "中文", "subtitle": "中文逐字稿", "flag": "中"},
    {"id": "id2zh", "mode": "id2zh", "title": "印尼文", "subtitle": "翻成中文", "flag": "ID"},
    {"id": "vi2zh", "mode": "vi2zh", "title": "越南文", "subtitle": "翻成中文", "flag": "VI"},
    {"id": "hi2zh", "mode": "hi2zh", "title": "印地語", "subtitle": "印度・翻成中文", "flag": "HI"},
    {"id": "en2zh", "mode": "en2zh", "title": "英文", "subtitle": "翻成中文", "flag": "EN"},
    {"id": "ja2zh", "mode": "ja2zh", "title": "日文", "subtitle": "翻成中文", "flag": "日"},
    {"id": "ko2zh", "mode": "ko2zh", "title": "韓文", "subtitle": "翻成中文", "flag": "韓"},
]

# 即時字幕：選「對方說什麼語言」，勾「我也要說話」就改用雙向（我說中文翻成對方的語言，需要麥克風）
LIVE_SCENARIOS = [
    {"id": "id", "title": "對方說印尼文", "flag": "ID", "mode": "id2zh", "bidi": "id_zh"},
    {"id": "vi", "title": "對方說越南文", "flag": "VI", "mode": "vi2zh", "bidi": "vi_zh"},
    {"id": "hi", "title": "對方說印地語", "flag": "HI", "mode": "hi2zh", "bidi": "hi_zh"},
    {"id": "en", "title": "對方說英文", "flag": "EN", "mode": "en2zh", "bidi": "en_zh"},
    {"id": "ja", "title": "對方說日文", "flag": "日", "mode": "ja2zh", "bidi": "ja_zh"},
    {"id": "ko", "title": "對方說韓文", "flag": "韓", "mode": "ko2zh", "bidi": "ko_zh"},
    {"id": "zh", "title": "大家都說中文", "flag": "中", "mode": "zh", "bidi": None},
    # 外語同仁自己的電腦：對方（例如老師）說中文，翻成自己的語言看
    {"id": "zh2id", "title": "對方說中文，翻成印尼文", "flag": "→ID", "mode": "zh2id", "bidi": None},
    {"id": "zh2vi", "title": "對方說中文，翻成越南文", "flag": "→VI", "mode": "zh2vi", "bidi": None},
    {"id": "zh2hi", "title": "對方說中文，翻成印地語", "flag": "→HI", "mode": "zh2hi", "bidi": None},
    {"id": "zh2en", "title": "對方說中文，翻成英文", "flag": "→EN", "mode": "zh2en", "bidi": None},
]

# 教室模式（同一支麥克風，中文與這些語言互相翻譯）可以用的情境
ROOM_SCENARIOS = ("id", "vi", "hi", "en")

_AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".mp4", ".mkv", ".webm", ".avi", ".aac", ".wma", ".mov"}
_MAX_UPLOAD_MB = int(os.environ.get("PCG_SIMPLE_MAX_UPLOAD_MB", "2048"))
_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
_SESSION_RE = re.compile(r"記錄檔\s+(\S+?)/?\s*$")
_ID_RE = re.compile(r"^[A-Za-z0-9_-]{8,64}$")

# 產出檔的顯示名稱（依檔名開頭判斷，排序也照這個順序）
# kind 是給畫面翻譯用的代碼（多國語言），label 是中文的備用名稱
_OUTPUT_KINDS = [
    ("摘要", ".html", "會議紀錄（網頁）", "primary", "minutes_html"),
    ("摘要", ".txt", "會議紀錄（文字檔）", "", "minutes_txt"),
    ("時間逐字稿", ".html", "逐字稿（可點時間播放錄音）", "", "transcript_html"),
    ("時間逐字稿", ".txt", "逐字稿（文字檔）", "", "transcript_txt"),
    ("時間逐字稿", ".srt", "字幕檔 SRT", "", "srt"),
    ("時間逐字稿", ".vtt", "字幕檔 VTT", "", "vtt"),
]


def profile(s, has_gpu=True):
    """混合模式：依 pcg_simple.backend 決定怎麼跑。
    - "local"（預設，沒有 GPU 伺服器時）：全部在這台電腦的 CPU 上跑。辨識用小模型、翻譯用 M2M100（可商用），
      不產出 AI 會議紀錄（摘要要大模型，CPU 太慢、品質太差）；只出翻譯好的逐字稿與字幕檔
    - "server"：辨識交給 GPU 伺服器（config.json 的 remote_whisper）、翻譯與會議紀錄交給 LLM 伺服器（llm_host）
    IT 之後有了 GPU 伺服器，把 backend 改成 "server"、填好兩台伺服器的位址就切過去，同仁電腦不用重裝"""
    local = (s.get("backend") or "local") != "server"
    if local:
        return {"backend": "local", "engine": "m2m", "summarize": False,
                "file_model": s.get("local_file_model") or "small",
                "live_model": s.get("local_live_model") or "small",
                "diarize": bool(s.get("diarize", False)), "local_asr": True}
    if not has_gpu:
        # 伺服器模式但只接大模型伺服器（例如集團的 Open WebUI）：辨識留在這台電腦（小模型），翻譯與會議紀錄交給大模型
        return {"backend": "server", "engine": "llm", "summarize": True,
                "file_model": s.get("local_file_model") or "small",
                "live_model": s.get("local_live_model") or "small",
                "diarize": bool(s.get("diarize", False)), "local_asr": True}
    return {"backend": "server", "engine": "llm", "summarize": True,
            "file_model": s.get("asr_model") or "large-v3-turbo",
            "live_model": s.get("live_model") or s.get("asr_model") or "large-v3-turbo",
            "diarize": bool(s.get("diarize", True)), "local_asr": False}


def _strip_name(name):
    """上傳檔名只留檔名本身，去掉目錄成分與危險字元；副檔名必須是音訊／影片"""
    base = os.path.basename((name or "").replace("\\", "/")).strip()
    stem, ext = os.path.splitext(base)
    if ext.lower() not in _AUDIO_EXTS:
        return None
    stem = re.sub(r"[^\w一-鿿\-. ]+", "_", stem).strip(" ._") or "錄音"
    return stem[:80] + ext.lower()


class SimpleQueue:
    """簡易版的工作佇列：一次處理一件，狀態存在 group_data/jobs.json（重新啟動後還看得到結果）"""

    def __init__(self, base_dir: Path, settings_fn, has_gpu_fn=lambda: True):
        self.base = base_dir
        self.settings = settings_fn
        self.has_gpu = has_gpu_fn
        self.data_dir = base_dir / "group_data"
        self.upload_dir = base_dir / "recordings" / "simple"
        self.data_dir.mkdir(exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.db = self.data_dir / "jobs.json"
        self.lock = threading.Lock()
        self.wake = threading.Event()
        self.jobs = self._load()
        self.proc = None
        threading.Thread(target=self._worker, daemon=True, name="pcg-simple-worker").start()

    # ── 狀態存取 ──
    def _load(self):
        try:
            jobs = json.loads(self.db.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        for j in jobs.values():
            if j.get("state") == "running":      # 上次處理到一半伺服器就重新啟動了
                j.update(state="failed", error="處理途中伺服器重新啟動，請重新送出", error_code="restarted",
                         finished=time.time())
        return jobs

    def _save(self):
        tmp = self.db.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.jobs, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, self.db)

    def _prune(self):
        keep = float(self.settings().get("keep_days", 14)) * 86400
        now = time.time()
        for jid in [k for k, j in self.jobs.items()
                    if j.get("finished") and now - j["finished"] > keep]:
            del self.jobs[jid]

    def add(self, owner, filename, path, scenario, topic, speakers):
        jid = time.strftime("%Y%m%d%H%M%S") + "-" + secrets.token_hex(3)
        with self.lock:
            self._prune()
            self.jobs[jid] = {"id": jid, "owner": owner, "file": filename, "path": str(path),
                              "scenario": scenario["id"], "mode": scenario["mode"],
                              "scenario_title": f"{scenario['title']}會議" if not scenario["title"].endswith("會議")
                              else scenario["title"], "topic": topic, "speakers": speakers,
                              "state": "queued", "created": time.time(), "started": None, "finished": None,
                              "error": "", "out_dir": "", "stage": ""}
            self._save()
        self.wake.set()
        return jid

    def list_for(self, owner):
        with self.lock:
            queued = sorted((j for j in self.jobs.values() if j["state"] == "queued"), key=lambda j: j["created"])
            pos = {j["id"]: i + 1 for i, j in enumerate(queued)}
            running = any(j["state"] == "running" for j in self.jobs.values())
            out = []
            for j in sorted(self.jobs.values(), key=lambda j: j["created"], reverse=True):
                if j["owner"] != owner:
                    continue
                item = {k: j.get(k, "") for k in ("id", "file", "scenario", "scenario_title", "topic", "state",
                                                  "created", "started", "finished", "error", "error_code",
                                                  "stage")}
                if j["state"] == "queued":
                    item["ahead"] = pos[j["id"]] - 1 + (1 if running else 0)
                if j["state"] == "done":
                    item["outputs"] = self.outputs(j)
                out.append(item)
            return out

    def get(self, jid):
        with self.lock:
            return dict(self.jobs[jid]) if jid in self.jobs else None

    def cancel(self, jid, owner):
        with self.lock:
            j = self.jobs.get(jid)
            if not j or j["owner"] != owner:
                return False
            if j["state"] == "queued":
                j.update(state="cancelled", finished=time.time())
                self._save()
                return True
            if j["state"] == "running" and self.proc and self.proc.poll() is None:
                j["cancel"] = True
                self.proc.terminate()
                return True
            return False

    def outputs(self, job):
        """這件工作產出的檔案（會議紀錄、逐字稿、字幕）"""
        d = self.out_path(job)
        if not d:
            return []
        files = []
        for prefix, ext, label, style, kind in _OUTPUT_KINDS:
            for f in sorted(d.iterdir()):
                # 檔名像「印尼翻中_摘要_會議_20261104.html」「印尼翻中_時間逐字稿_會議_….srt」
                is_kind = ("_摘要" in f.name or f.name.startswith("摘要")) if prefix == "摘要" \
                    else ("時間逐字稿" in f.name and "摘要" not in f.name)
                if f.suffix.lower() == ext and is_kind and not any(x["name"] == f.name for x in files):
                    files.append({"name": f.name, "label": label, "style": style, "kind": kind,
                                  "size_kb": round(f.stat().st_size / 1024, 1)})
        return files

    def out_path(self, job):
        rel = job.get("out_dir")
        if not rel:
            return None
        d = (self.base / rel).resolve()
        logs = (self.base / "logs").resolve()
        if logs not in d.parents or not d.is_dir():
            return None
        return d

    # ── 背景處理 ──
    def _next(self):
        with self.lock:
            queued = sorted((j for j in self.jobs.values() if j["state"] == "queued"), key=lambda j: j["created"])
            if not queued:
                return None
            j = queued[0]
            j.update(state="running", started=time.time(), stage="prepare")
            self._save()
            return dict(j)

    def _args(self, job):
        s = self.settings()
        pf = profile(s, self.has_gpu())
        args = [sys.executable, str(self.base / "translate_meeting.py"),
                "--input", job["path"], "--mode", job["mode"], "-m", pf["file_model"]]
        if pf["summarize"]:
            args.append("--summarize")
            if s.get("summary_model"):
                args += ["--summary-model", s["summary_model"]]
        if pf["local_asr"]:
            args.append("--local-asr")
        if job["mode"] not in ("zh", "en", "ja", "ko", "id", "vi", "hi"):
            args += ["-e", pf["engine"]]
            if pf["engine"] == "llm" and s.get("llm_model"):
                args += ["--llm-model", s["llm_model"]]
        if pf["diarize"]:
            args.append("--diarize")
            if job.get("speakers"):
                args += ["--num-speakers", str(int(job["speakers"]))]
        if job.get("topic"):
            args += ["--topic", job["topic"]]
        return args

    def _worker(self):
        while True:
            job = self._next()
            if job is None:
                self.wake.wait(timeout=5)
                self.wake.clear()
                continue
            self._run(job)

    def _run(self, job):
        log_path = self.data_dir / f"job_{job['id']}.log"
        out_dir, tail = "", []
        rc = -1
        try:
            # PCG_NONINTERACTIVE：處理完不開視窗、不等「按 ESC 鍵退出」（否則工作永遠不會結束）
            env = dict(os.environ, PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8", PYTHONUTF8="1",
                       PCG_NONINTERACTIVE="1")
            with open(log_path, "w", encoding="utf-8") as log:
                self.proc = subprocess.Popen(self._args(job), cwd=str(self.base), env=env,
                                             stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                             stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                                             errors="replace", bufsize=1)
                try:                                  # 主程式偶爾會問「確定開始？」之類的問題：一律回答 y
                    self.proc.stdin.write("y\n" * 40)
                    self.proc.stdin.close()
                except OSError:
                    pass
                for line in self.proc.stdout:
                    clean = _ANSI.sub("", line).rstrip()
                    log.write(clean + "\n")
                    if not clean.strip():
                        continue
                    tail = (tail + [clean.strip()])[-12:]
                    m = _SESSION_RE.search(clean)
                    if m and not out_dir:
                        out_dir = m.group(1).rstrip("/")
                    stage = _stage_of(clean)
                    if stage:
                        with self.lock:
                            if job["id"] in self.jobs:
                                self.jobs[job["id"]]["stage"] = stage
                rc = self.proc.wait()
                self.proc.stdout.close()
        except Exception as e:                         # 啟動不了（找不到 Python 之類）
            tail.append(f"{type(e).__name__}: {e}")
        finally:
            self.proc = None
        with self.lock:
            j = self.jobs.get(job["id"])
            if j is None:
                return
            j["out_dir"] = out_dir
            j["finished"] = time.time()
            if j.get("cancel"):
                j.update(state="cancelled", error="已取消")
            elif rc == 0 and self.outputs(j):
                j.update(state="done", stage="done")
            else:
                code, msg = _error_of(tail, rc)
                j.update(state="failed", error=msg, error_code=code)
            self._save()


def _stage_of(line):
    """從主程式的輸出猜目前在做什麼（給同仁看的進度，不求精確）。回傳代碼，畫面依語言顯示"""
    for key, code in (("轉檔", "convert"), ("講者辨識", "diarize"), ("Diariz", "diarize"),
                      ("翻譯", "translate"), ("校正", "correct"), ("會議分析", "summary"),
                      ("摘要", "summary"), ("辨識", "asr"), ("處理完成", "finishing")):
        if key in line:
            return code
    return ""


def _error_of(tail, rc):
    """回傳 (代碼, 細節)：代碼給畫面翻譯，細節是主程式的原文（給 IT 查問題）"""
    for line in reversed(tail):
        if "[錯誤]" in line or "Error" in line or "錯誤" in line:
            return "detail", re.sub(r"^\[錯誤\]\s*", "", line)[:200]
    if rc == 0:
        return "no_output", "處理完成但沒有產出檔案：可能是錄音的語言選錯，或錄音沒有人聲"
    return "failed", f"處理失敗（錯誤碼 {rc}），請把這件工作的編號告訴 IT"


_VERSION = {}


def app_version(base_dir: Path):
    """顯示在畫面上的版本：安裝檔版本（發布流程寫進 group/version.json）、commit、原作者版本。
    沒有 version.json（git 直接拿來用、CI 測試包）時顯示 dev＋commit"""
    key = str(base_dir)
    if key in _VERSION:
        return _VERSION[key]
    v = {"version": "dev", "commit": "", "upstream": ""}
    try:
        v.update({k: str(x) for k, x in json.loads((base_dir / "group" / "version.json").read_text(encoding="utf-8")).items()
                  if k in v and x})
    except (OSError, ValueError):
        pass
    if not v["commit"] and (base_dir / ".git").exists():
        try:
            v["commit"] = subprocess.run(["git", "-C", str(base_dir), "rev-parse", "--short", "HEAD"], capture_output=True,
                                         text=True, timeout=5).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            pass
    try:
        with open(base_dir / "translate_meeting.py", encoding="utf-8") as f:
            for line in f:
                m = re.match(r'APP_VERSION = "([^"]+)"', line)
                if m:
                    v["upstream"] = m.group(1)
                    break
    except OSError:
        pass
    _VERSION[key] = v
    return v


LLM_STYLES = ("openwebui", "openai")    # 沒設＝內部 Ollama／OpenAI 相容自動偵測（RTX Spark、自建伺服器）


def parse_llm(text, keep_v1=False):
    """大模型伺服器位址 → (base_url, host, port, None)；格式不對 → (None, None, None, 說明)。
    可填「主機」「主機:連接埠」（Ollama，預設 11434）或完整網址 http(s)://主機[:連接埠][/路徑]（Open WebUI、反向代理）。
    keep_v1：外部 AI 服務的 base URL 原樣保留（…/v1、…/v1beta/openai），程式直接在後面接 /chat/completions"""
    s = (text or "").strip().rstrip("/")
    if not s:
        return None, None, None, "沒有填位址"
    scheme, given = "http", False
    low = s.lower()
    if low.startswith(("http://", "https://")):
        scheme, given = ("https" if low.startswith("https://") else "http"), True
        s = s.split("://", 1)[1]
    elif "://" in s:
        return None, None, None, "只支援 http:// 或 https://"
    hostport, _, path = s.partition("/")
    path = ("/" + path.strip("/")) if path.strip("/") else ""
    if path.lower().endswith("/v1") and not keep_v1:
        path = path[:-3]
    if not re.fullmatch(r"[A-Za-z0-9._\-/~%]*", path):
        return None, None, None, "路徑格式不正確"
    m = re.fullmatch(r"(\[[0-9A-Fa-f:.]+\]|[A-Za-z0-9.\-]{1,253})(?::(\d{1,5}))?", hostport)
    if not m:
        return None, None, None, f"位址格式不正確：{text.strip()}"
    host = m.group(1)
    port = int(m.group(2)) if m.group(2) else ((443 if scheme == "https" else 80) if given else 11434)
    if not 1 <= port <= 65535:
        return None, None, None, f"連接埠 {port} 超出範圍"
    hp = host if (scheme, port) in (("http", 80), ("https", 443)) else f"{host}:{port}"
    return f"{scheme}://{hp}{path}", host, port, None


def register(app, base_dir: Path, is_local, pw_hash, pw_match, config_file: Path, write_config,
             start_live=None, live_running=None, live_args=None, set_view_password=None, gpu_alive=None,
             update_hooks=None, stop_live=None):
    """把簡易版的路由掛到 WebUI 的 FastAPI app 上（webui.py 呼叫）。
    start_live(body)：用 WebUI 原本的方式啟動即時字幕；live_running()：WebUI 是否正在跑；
    stop_live()：停止即時字幕（首頁「字幕進行中」旁的停止按鈕）"""
    from fastapi import File, Form, Request, UploadFile
    from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response

    def _gpu_alive(host, port):
        import urllib.request
        try:
            with urllib.request.urlopen(f"http://{host}:{port}/health", timeout=2) as r:
                return r.status == 200
        except Exception:
            return False
    alive_fn = gpu_alive or _gpu_alive
    _alive_cache = {}

    def has_gpu():
        """有設 GPU 伺服器、而且現在連得上。連不上（關機、斷線）就照「沒有 GPU」處理：辨識改在這台電腦用小模型，
        不要讓主程式在 CPU 上硬跑 large-v3-turbo（i5 筆電會慢到不能用）。結果記 20 秒，避免每次都等逾時"""
        try:
            c = json.loads(config_file.read_text(encoding="utf-8")) if config_file.exists() else {}
        except (OSError, ValueError):
            c = {}
        rw = c.get("remote_whisper")
        if not (isinstance(rw, dict) and rw.get("host")):
            return False
        key = (str(rw["host"]), int(rw.get("whisper_port") or 8978))
        hit = _alive_cache.get(key)
        if hit and time.time() - hit[0] < 20:
            return hit[1]
        ok = bool(alive_fn(*key))
        _alive_cache[key] = (time.time(), ok)
        return ok

    def settings():
        try:
            cfg = json.loads(config_file.read_text(encoding="utf-8")) if config_file.exists() else {}
        except (OSError, ValueError):
            cfg = {}
        s = cfg.get("pcg_simple") or {}
        return s if isinstance(s, dict) else {}

    def migrate_password():
        """設定檔裡的明文密碼換成雜湊（比照 WebUI 的做法）"""
        try:
            cfg = json.loads(config_file.read_text(encoding="utf-8")) if config_file.exists() else {}
            s = cfg.get("pcg_simple")
            if isinstance(s, dict) and s.get("password"):
                s["password_hash"] = pw_hash(s.pop("password"))
                write_config(cfg)
        except (OSError, ValueError):
            pass

    # 佇列（含背景執行緒）與密碼轉換都等第一次有人用到才做：import webui（例如測試）時不改設定檔、不開執行緒
    _state = {}
    _state_lock = threading.Lock()

    def ensure():
        with _state_lock:
            if "q" not in _state:
                migrate_password()
                _state["q"] = SimpleQueue(base_dir, settings, has_gpu)
        return _state["q"]

    class _LazyQueue:
        def __getattr__(self, name):
            return getattr(ensure(), name)

    queue = _LazyQueue()
    html_path = Path(__file__).with_name("simple.html")

    def scenarios():
        sc = settings().get("scenarios")
        return sc if isinstance(sc, list) and sc else DEFAULT_SCENARIOS

    def auth(request: Request):
        """回傳 (owner, 錯誤回應)；owner 是瀏覽器自己產生的代號"""
        ensure()                       # 先把設定檔的明文密碼換成雜湊，否則剛設好密碼後的第一個請求會不用密碼就通過
        h = settings().get("password_hash", "")
        if h and not is_local(request) and not pw_match(request.headers.get("X-Simple-Token", ""), h):
            return None, JSONResponse({"ok": False, "need_password": True, "code": "need_password",
                                       "error": "請輸入同仁密碼"}, status_code=401)
        owner = request.headers.get("X-Client-Id", "")
        if not _ID_RE.match(owner):
            return None, JSONResponse({"ok": False, "code": "bad_client", "error": "瀏覽器代號不正確，請重新整理頁面"},
                                    status_code=400)
        return owner, None

    @app.get("/simple", response_class=HTMLResponse)
    async def simple_page():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))

    @app.get("/simple/live", response_class=HTMLResponse)
    async def simple_live_page():
        """精簡字幕畫面（五種語言、我要看的語言）。字幕內容沿用 WebUI 的 /ws 即時推送"""
        return HTMLResponse(Path(__file__).with_name("live.html").read_text(encoding="utf-8"))

    @app.get("/api/simple/config")
    async def simple_config(request: Request):
        owner, err = auth(request)
        if err:
            return err
        pf = profile(settings(), has_gpu())
        return {"ok": True, "scenarios": [{k: s.get(k, "") for k in ("id", "title", "subtitle", "flag")}
                                          for s in scenarios()],
                "max_upload_mb": _MAX_UPLOAD_MB, "backend": pf["backend"], "minutes": pf["summarize"],
                "version": app_version(base_dir), "data_scope": data_scope(pf)}

    def data_scope(pf):
        """畫面上「資料送到哪裡」：local＝只在這台電腦；internal＝這台＋公司內部伺服器；
        group＝集團 Open WebUI；external＝公司外部的 AI 服務（IT 設定頁選的伺服器類型）"""
        if pf["backend"] != "server":
            return "local"
        style = read_cfg().get("llm_api_style")
        return {"openwebui": "group", "openai": "external"}.get(style, "internal")

    @app.get("/api/simple/jobs")
    async def simple_jobs(request: Request):
        owner, err = auth(request)
        if err:
            return err
        return {"ok": True, "jobs": queue.list_for(owner)}

    @app.post("/api/simple/jobs")
    async def simple_submit(request: Request, file: UploadFile = File(...), scenario: str = Form(...),
                            topic: str = Form(""), speakers: str = Form("")):
        owner, err = auth(request)
        if err:
            return err
        sc = next((s for s in scenarios() if s.get("id") == scenario), None)
        if not sc:
            return JSONResponse({"ok": False, "code": "pick_language", "error": "請選擇錄音的語言"}, status_code=400)
        name = _strip_name(file.filename)
        if not name:
            return JSONResponse({"ok": False, "code": "bad_file", "error": "只接受錄音或影片檔（mp3、m4a、wav、mp4…）"},
                                status_code=400)
        spk = int(speakers) if speakers.strip().isdigit() and 1 <= int(speakers) <= 20 else None
        dest_dir = queue.upload_dir / (time.strftime("%Y%m%d_%H%M%S") + "_" + secrets.token_hex(3))
        dest_dir.mkdir(parents=True)
        dest = dest_dir / name
        limit, size = _MAX_UPLOAD_MB * 1048576, 0
        try:
            with open(dest, "wb") as f:
                while True:
                    chunk = await file.read(1048576)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > limit:
                        raise ValueError(f"檔案超過上限 {_MAX_UPLOAD_MB} MB")
                    f.write(chunk)
        except ValueError as e:
            dest.unlink(missing_ok=True)
            dest_dir.rmdir()
            return JSONResponse({"ok": False, "code": "too_large", "error": str(e)}, status_code=413)
        jid = queue.add(owner, name, dest, sc, topic.strip()[:60], spk)
        return {"ok": True, "id": jid}

    @app.post("/api/simple/jobs/{jid}/cancel")
    async def simple_cancel(request: Request, jid: str):
        owner, err = auth(request)
        if err:
            return err
        return {"ok": queue.cancel(jid, owner)}

    @app.get("/simple/files/{jid}/{name}")
    async def simple_file(request: Request, jid: str, name: str):
        # 逐字稿 HTML 用相對路徑載入同資料夾的錄音：瀏覽器帶不了標頭，所以這條用網址上的 ?k=（工作的下載代號）
        job = queue.get(jid)
        if not job or not secrets.compare_digest(request.query_params.get("k", "") or
                                                 request.cookies.get(f"pcg_{jid}", ""), job.get("dl_key", "")):
            return JSONResponse({"ok": False, "error": "找不到檔案或連結已失效"}, status_code=404)
        d = queue.out_path(job)
        target = (d / name).resolve() if d else None
        if not target or target.parent != d or not target.is_file():
            return JSONResponse({"ok": False, "error": "找不到檔案"}, status_code=404)
        resp = FileResponse(str(target))
        resp.set_cookie(f"pcg_{jid}", job["dl_key"], httponly=True, samesite="strict", path=f"/simple/files/{jid}/")
        return resp

    @app.get("/api/simple/jobs/{jid}/link")
    async def simple_link(request: Request, jid: str):
        """下載連結（每件工作一組隨機代號，只有送件的瀏覽器拿得到）"""
        owner, err = auth(request)
        if err:
            return err
        with queue.lock:
            j = queue.jobs.get(jid)
            if not j or j["owner"] != owner:
                return JSONResponse({"ok": False, "error": "找不到這件工作"}, status_code=404)
            if not j.get("dl_key"):
                j["dl_key"] = secrets.token_urlsafe(18)
                queue._save()
            return {"ok": True, "key": j["dl_key"]}

    def _lan_ips():
        """這台電腦在區網上的 IPv4（給別台電腦連進來用）"""
        import socket
        ips = []
        try:
            for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
                ips.append(info[4][0])
        except OSError:
            pass
        try:                                  # 預設路由那張網卡（不會真的送封包）
            s_ = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s_.connect(("10.255.255.255", 1))
            ips.insert(0, s_.getsockname()[0])
            s_.close()
        except OSError:
            pass
        out = []
        for ip in ips:
            if ip not in out and not ip.startswith(("127.", "169.254.")):
                out.append(ip)
        return out

    @app.get("/api/simple/share")
    async def simple_share(request: Request):
        """分享字幕（只在這台電腦上）：別台電腦要用的網址、目前能不能連進來、有沒有密碼"""
        if not is_local(request):
            return JSONResponse({"ok": False, "code": "local_only"}, status_code=403)
        cfg = read_cfg()
        s = cfg.get("pcg_simple") or {}
        port = request.url.port or 19781
        bound_all = (os.environ.get("PCG_WEBUI_HOST") or "0.0.0.0") not in ("127.0.0.1", "localhost", "::1")
        return {"ok": True, "allowed": bool(s.get("allow_remote_view")), "bound": bound_all,
                "password_set": bool(s.get("password_hash") or (cfg.get("webui_passwords") or {}).get("read_sha256")),
                "urls": [f"http://{ip}:{port}/simple/live" for ip in _lan_ips()]}

    @app.get("/api/simple/share/qr.svg")
    async def simple_share_qr(request: Request, u: str = ""):
        """QR Code（SVG，本機產生、不連網）。只接受這台電腦自己的分享網址"""
        if not is_local(request) or not re.fullmatch(r"http://[0-9.]{7,15}:\d{2,5}/simple/live", u):
            return JSONResponse({"ok": False}, status_code=400)
        try:
            import qrcode
            import qrcode.image.svg
        except ImportError:
            return JSONResponse({"ok": False, "code": "no_qrcode"}, status_code=404)
        img = qrcode.make(u, image_factory=qrcode.image.svg.SvgPathImage, box_size=10, border=2)
        return Response(img.to_string(), media_type="image/svg+xml", headers={"Cache-Control": "no-store"})

    @app.get("/api/simple/live")
    async def simple_live_info(request: Request):
        """即時字幕只能在自己的電腦上開（要抓這台電腦播出來的聲音）"""
        args = live_args() if live_args else None
        mode = args[args.index("--mode") + 1] if args and "--mode" in args[:-1] else ""
        return {"ok": True, "local": bool(is_local(request)), "available": start_live is not None,
                "running": bool(live_running and live_running()),
                "mode": mode, "is_file": bool(args and "--input" in args), "version": app_version(base_dir),
                "scenarios": [{k: s[k] for k in ("id", "title", "flag")}
                              | {"can_bidi": bool(s["bidi"]), "can_room": s["id"] in ROOM_SCENARIOS}
                              for s in LIVE_SCENARIOS]}

    @app.post("/api/simple/live/stop")
    async def simple_live_stop(request: Request):
        """首頁的「停止」：只能在這台電腦上按；正在處理錄音檔時不停"""
        if not is_local(request):
            return JSONResponse({"ok": False, "code": "live_remote", "error": "只能在這台電腦上停止"}, status_code=403)
        if stop_live is None:
            return JSONResponse({"ok": False, "code": "live_unavailable", "error": "這個版本不支援"}, status_code=503)
        if not (live_running and live_running()):
            return {"ok": True, "stopped": False}
        if "--input" in ((live_args() if live_args else None) or []):
            return JSONResponse({"ok": False, "code": "live_busy_file",
                                 "error": "這台電腦正在處理錄音檔，處理完再開即時字幕"}, status_code=409)
        await stop_live()
        return {"ok": True, "stopped": True}

    @app.post("/api/simple/live")
    async def simple_live_start(request: Request, body: dict = {}):
        if not is_local(request):
            return JSONResponse({"ok": False, "code": "live_remote", "error": "即時字幕要在自己的電腦上開：請在這台電腦安裝 PCG-live-whisper，"
                                                       "用桌面捷徑開啟"}, status_code=403)
        if start_live is None:
            return JSONResponse({"ok": False, "code": "live_unavailable", "error": "這個版本不支援即時字幕"}, status_code=503)
        sc = next((x for x in LIVE_SCENARIOS if x["id"] == body.get("scenario")), None)
        if not sc:
            return JSONResponse({"ok": False, "code": "pick_language", "error": "請選擇對方說的語言"}, status_code=400)
        s = settings()
        room = bool(body.get("room")) and sc["id"] in ROOM_SCENARIOS
        mode = sc["mode"] if room else (sc["bidi"] if (body.get("speak") and sc["bidi"]) else sc["mode"])
        if live_running and live_running():
            # 上一場沒按「停止」還在跑：同一種語言就回到那一場；換了語言就換掉（start_live 會先停掉舊的），
            # 不然選「對方說英文」會回到還在跑的「中文 → 印尼文」
            cur = (live_args() if live_args else None) or []
            if "--input" in cur:
                return JSONResponse({"ok": False, "code": "live_busy_file",
                                     "error": "這台電腦正在處理錄音檔，處理完再開即時字幕"}, status_code=409)
            cur_mode = cur[cur.index("--mode") + 1] if "--mode" in cur[:-1] else None
            if cur_mode is None or (cur_mode == mode and ("--room" in cur) == room):
                return {"ok": True, "already": True}
        pf = profile(s, has_gpu())
        if room:
            # 教室模式：每一句要先判斷語言，只做在這台電腦的辨識（GPU 伺服器不支援），用本機的即時字幕模型
            pf = {**pf, "local_asr": True, "live_model": s.get("local_live_model") or "small"}
        start = {
            "mode": mode,
            "room": room,
            "model": pf["live_model"],
            "scene": s.get("live_scene") or "meeting",
            # 本機模式：WebUI 的 nllb 路徑在集團版會改用 M2M100（見 translate_meeting.py 的 NllbTranslator.__new__）
            "engine": None if mode == "zh" else ("llm" if pf["engine"] == "llm" else "nllb"),
            "local_asr": pf["local_asr"],
            # 不帶 llm_host：主程式用 config.json 的 llm_host／llm_port（IT 在 /simple/admin 設定）
            "llm_host": "",
            "llm_model": s.get("llm_model") or "",
            "topic": (body.get("topic") or "").strip()[:60],
            "record": bool(s.get("live_record", False)),
            "denoise": True,
            "subtitle_overlay": bool(body.get("overlay")),
        }
        try:
            await start_live(start)
        except Exception as e:
            return JSONResponse({"ok": False, "code": "live_failed", "error": f"啟動失敗：{e}"}, status_code=500)
        return {"ok": True, "mode": f"{sc['id']}_zh" if room else mode, "room": room}

    # ─── 一鍵更新（小更新包）：來源是 IT 設定的共用資料夾，或 GitHub 發布頁（見 updater.py） ───
    from group import updater as _upd
    hooks = update_hooks or {}
    _upd_cache = {"at": 0.0, "key": None, "result": None}
    _upd_lock = threading.Lock()
    _upd_busy = {"on": False}

    def upd_settings():
        s = settings()
        return {"check": bool(s.get("update_check", True)), "who": "it" if s.get("update_who") == "it" else "staff",
                "share": str(s.get("update_share") or "")}

    def upd_check(force=False):
        us = upd_settings()
        cur = app_version(base_dir)["version"]
        key = (cur, us["share"])
        # 有新版記 1 小時；沒有新版只記 10 分鐘：程式一直開著時，新版發布後不用等太久就會看到
        ttl = 3600 if (_upd_cache["result"] or {}).get("available") else 600
        if not force and _upd_cache["key"] == key and time.time() - _upd_cache["at"] < ttl:
            return _upd_cache["result"]
        res = _upd.check(cur, share=us["share"], github_fetch=hooks.get("github_fetch"))
        _upd_cache.update(at=time.time(), key=key, result=res)
        return res

    def busy_now():
        if live_running and live_running():
            return True
        q = _state.get("q")
        return bool(q) and any(j.get("state") == "running" for j in q.jobs.values())

    @app.get("/api/simple/update")
    async def update_info(request: Request):
        """同仁頁面打開時問一次：有沒有新版、是小更新包還是要完整安裝檔、誰可以按"""
        if not is_local(request):
            return {"ok": True, "enabled": False}
        us = upd_settings()
        if not us["check"]:
            return {"ok": True, "enabled": False}
        import asyncio
        res = await asyncio.to_thread(upd_check, request.query_params.get("force") == "1")
        latest = res.get("latest") or {}
        return {"ok": True, "enabled": True, "current": app_version(base_dir)["version"],
                "available": bool(res.get("available")),
                "latest": {k: latest.get(k) for k in ("version", "kind", "source", "notes_url")} if latest else None,
                "who": us["who"], "installing": _upd_busy["on"]}

    @app.post("/api/simple/update")
    async def update_install(request: Request):
        if not is_local(request):
            return JSONResponse({"ok": False, "code": "update_remote", "error": "只能在這台電腦上更新"}, status_code=403)
        if upd_settings()["who"] == "it":
            err = admin_auth(request)
            if err:
                return err
        if busy_now():
            return JSONResponse({"ok": False, "code": "update_busy",
                                 "error": "正在進行即時字幕或處理錄音，結束後再更新"}, status_code=409)
        if not _upd_lock.acquire(blocking=False):
            return JSONResponse({"ok": False, "code": "update_busy", "error": "已經在更新了"}, status_code=409)
        try:
            import asyncio
            res = await asyncio.to_thread(upd_check, True)
            latest = res.get("latest")
            if not res.get("available") or not latest:
                return JSONResponse({"ok": False, "code": "update_none", "error": "已經是最新版"}, status_code=409)
            if latest.get("kind") != "patch":
                return JSONResponse({"ok": False, "code": "update_full",
                                     "error": "這一版需要完整安裝檔，請找 IT 更新"}, status_code=409)
            try:
                exe = await asyncio.to_thread(_upd.download, latest, base_dir / "group_data" / "updates",
                                              hooks.get("opener"))
                (hooks.get("launch") or _upd.launch)(exe)
            except Exception as e:  # noqa: BLE001
                return JSONResponse({"ok": False, "code": "update_failed", "error": str(e)[:300]}, status_code=500)
            _upd_busy["on"] = True
            return {"ok": True, "version": latest["version"]}
        finally:
            _upd_lock.release()

    # ─── IT 設定頁（/simple/admin）：切換本機／伺服器、填伺服器位址、測試連線、設定密碼 ───
    # 一律要 IT 密碼（同仁就坐在這台電腦前，「本機」不能當成 IT）。還沒設定時，只能在本機設定第一組密碼
    admin_html = Path(__file__).with_name("admin.html")

    def read_cfg():
        try:
            return json.loads(config_file.read_text(encoding="utf-8")) if config_file.exists() else {}
        except (OSError, ValueError):
            return {}

    def admin_auth(request: Request):
        h = (read_cfg().get("pcg_simple") or {}).get("it_password_hash", "")
        if not h:
            return JSONResponse({"ok": False, "code": "it_password_unset",
                                 "error": "還沒有設定 IT 密碼"}, status_code=401)
        if not pw_match(request.headers.get("X-IT-Token", ""), h):
            return JSONResponse({"ok": False, "code": "it_password_wrong", "error": "IT 密碼不正確"}, status_code=401)
        return None

    def admin_state():
        cfg = read_cfg()
        s = cfg.get("pcg_simple") or {}
        rw = cfg.get("remote_whisper") or {}
        return {"backend": "server" if s.get("backend") == "server" else "local",
                "gpu_host": rw.get("host", ""), "gpu_port": rw.get("whisper_port", 8978),
                "llm_host": cfg.get("llm_host", ""), "llm_port": cfg.get("llm_port", 11434),
                "llm_url": cfg.get("llm_url") or (f"{cfg['llm_host']}:{cfg.get('llm_port', 11434)}"
                                                  if cfg.get("llm_host") else ""),
                "llm_api_style": cfg.get("llm_api_style") if cfg.get("llm_api_style") in LLM_STYLES else "auto",
                "llm_api_key_set": bool(str(cfg.get("llm_api_key") or "").strip()),
                "llm_model": s.get("llm_model", ""), "summary_model": s.get("summary_model", ""),
                "asr_model": s.get("asr_model", "large-v3-turbo"),
                "local_file_model": s.get("local_file_model", "small"),
                "local_live_model": s.get("local_live_model", "small"),
                "diarize": bool(s.get("diarize", s.get("backend") == "server" and bool(rw.get("host")))),
                "staff_password_set": bool(s.get("password_hash") or s.get("password")),
                "allow_remote_view": bool(s.get("allow_remote_view", False)),
                "m2m_installed": (base_dir / "models" / "m2m100_418m" / "model.bin").is_file(),
                "update_check": bool(s.get("update_check", True)),
                "update_who": "it" if s.get("update_who") == "it" else "staff",
                "update_share": str(s.get("update_share") or ""),
                "version": app_version(base_dir)}

    @app.get("/simple/admin", response_class=HTMLResponse)
    async def admin_page():
        return HTMLResponse(admin_html.read_text(encoding="utf-8"))

    @app.get("/api/simple/admin/state")
    async def admin_get(request: Request):
        ensure()
        h = (read_cfg().get("pcg_simple") or {}).get("it_password_hash", "")
        if not h:
            return {"ok": False, "code": "it_password_unset", "can_set": bool(is_local(request))}
        err = admin_auth(request)
        if err:
            return err
        return {"ok": True, "state": admin_state()}

    @app.post("/api/simple/admin/password")
    async def admin_password(request: Request, body: dict = {}):
        new = str(body.get("new") or "").strip()
        if len(new) < 6:
            return JSONResponse({"ok": False, "code": "too_short", "error": "密碼至少 6 個字"}, status_code=400)
        cfg = read_cfg()
        s = cfg.setdefault("pcg_simple", {})
        if s.get("it_password_hash"):
            err = admin_auth(request)               # 改密碼：要知道舊的（放在 X-IT-Token）
            if err:
                return err
        elif not is_local(request):
            return JSONResponse({"ok": False, "code": "local_only",
                                 "error": "第一次設定 IT 密碼只能在這台電腦上操作"}, status_code=403)
        s["it_password_hash"] = pw_hash(new)
        write_config(cfg)
        return {"ok": True}

    def _probe(url, timeout=4, headers=None):
        import urllib.request
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers or {}), timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace") or "{}")

    @app.post("/api/simple/admin/test")
    async def admin_test(request: Request, body: dict = {}):
        """測試 GPU 伺服器（語音辨識服務的 /health）與 LLM 伺服器（Ollama 或 OpenAI 相容），回傳可選的模型"""
        err = admin_auth(request)
        if err:
            return err
        import asyncio
        out = {"ok": True}
        gh, gp = str(body.get("gpu_host") or "").strip(), int(body.get("gpu_port") or 8978)
        if gh:
            try:
                h = await asyncio.to_thread(_probe, f"http://{gh}:{gp}/health")
                out["gpu"] = {"ok": True, "detail": " / ".join(str(h.get(k)) for k in ("backend", "device", "version")
                                                               if h.get(k))}
            except Exception as e:
                out["gpu"] = {"ok": False, "detail": f"{type(e).__name__}: {e}"[:200]}
        raw = str(body.get("llm_url") or "").strip()
        if not raw and body.get("llm_host"):
            raw = f"{str(body['llm_host']).strip()}:{int(body.get('llm_port') or 11434)}"
        if raw:
            base, _h, _p, perr = parse_llm(raw)
            if perr:
                out["llm"] = {"ok": False, "detail": perr}
                return out
            key = str(body.get("llm_api_key") or "").strip() or str(read_cfg().get("llm_api_key") or "").strip()
            hdr = {"Authorization": f"Bearer {key}"} if key else {}
            style = body.get("llm_api_style") if body.get("llm_api_style") in LLM_STYLES else "auto"
            if style == "openai":
                base = parse_llm(raw, keep_v1=True)[0]

            def ids(d):
                return [m.get("id") for m in (d.get("data") or []) if isinstance(m, dict) and m.get("id")]
            tries = ([("Open WebUI", "/api/models")] if style == "openwebui" else
                     [("外部 AI 服務", "/models")] if style == "openai" else
                     [("Ollama", "/api/tags"), ("OpenAI 相容", "/v1/models"), ("Open WebUI", "/api/models")])
            first = None
            for kind, path in tries:
                try:
                    d = await asyncio.to_thread(_probe, base + path, 6, hdr)
                    models = ([m.get("name") for m in d.get("models", []) if m.get("name")]
                              if path == "/api/tags" else ids(d))
                    if path == "/api/tags" and not d.get("models") and "models" not in d:
                        raise ValueError("不是 Ollama")
                    out["llm"] = {"ok": True, "type": kind, "models": models,
                                  "style": {"Open WebUI": "openwebui", "外部 AI 服務": "openai"}.get(kind, "auto")}
                    break
                except Exception as e:
                    code = getattr(e, "code", None)
                    if code in (401, 403):
                        first = ("API 金鑰不正確或沒有權限（Open WebUI：設定 → 帳號 → API 金鑰）" if style != "openai"
                                 else "API 金鑰不正確、沒有權限或額度用完")
                    elif first is None:
                        first = f"{type(e).__name__}: {e}"[:200]
            else:
                out["llm"] = {"ok": False, "detail": first or "連不上"}
        return out

    @app.post("/api/simple/admin/save")
    async def admin_save(request: Request, body: dict = {}):
        err = admin_auth(request)
        if err:
            return err
        backend = "server" if body.get("backend") == "server" else "local"
        gh = str(body.get("gpu_host") or "").strip()
        raw_llm = str(body.get("llm_url") or "").strip()
        if not raw_llm and str(body.get("llm_host") or "").strip():
            raw_llm = f"{str(body['llm_host']).strip()}:{int(body.get('llm_port') or 11434)}"
        # 伺服器模式只一定要有大模型伺服器；GPU 伺服器選填（沒填＝語音辨識留在這台電腦）
        if backend == "server" and not raw_llm:
            return JSONResponse({"ok": False, "code": "need_llm",
                                 "error": "伺服器模式要填大模型伺服器（例如集團的 Open WebUI 網址）"}, status_code=400)
        if gh and not re.fullmatch(r"[A-Za-z0-9.\-:\[\]]{1,253}", gh):
            return JSONResponse({"ok": False, "code": "bad_host", "error": f"位址格式不正確：{gh}"},
                                status_code=400)
        style = body.get("llm_api_style") if "llm_api_style" in body else read_cfg().get("llm_api_style")
        style = style if style in LLM_STYLES else ""
        llm = None
        if raw_llm:
            base, lh, lp, perr = parse_llm(raw_llm, keep_v1=(style == "openai"))
            if perr:
                return JSONResponse({"ok": False, "code": "bad_host", "error": perr}, status_code=400)
            llm = (base, lh, lp)
        key = str(body.get("llm_api_key") or "").strip()
        if key and (len(key) > 512 or any(c.isspace() for c in key)):
            return JSONResponse({"ok": False, "code": "bad_key", "error": "API 金鑰格式不正確"}, status_code=400)
        has_key = bool(key) or (bool(str(read_cfg().get("llm_api_key") or "").strip())
                                and not body.get("clear_llm_api_key"))
        if backend == "server" and style and not has_key:
            # Open WebUI 與外部 AI 服務一定要金鑰；內部 Ollama／RTX Spark 不用
            return JSONResponse({"ok": False, "code": "need_key",
                                 "error": "這種伺服器要填 API 金鑰"}, status_code=400)
        cfg = read_cfg()
        s = cfg.setdefault("pcg_simple", {})
        s["backend"] = backend
        for k in ("llm_model", "summary_model", "asr_model", "local_file_model", "local_live_model"):
            if k in body:
                v = str(body.get(k) or "").strip()[:120]
                if v:
                    s[k] = v
                else:
                    s.pop(k, None)
        s["diarize"] = bool(body.get("diarize"))
        if "update_check" in body:
            s["update_check"] = bool(body.get("update_check"))
        if "update_who" in body:
            s["update_who"] = "it" if body.get("update_who") == "it" else "staff"
        if "update_share" in body:
            share = str(body.get("update_share") or "").strip()
            if len(share) > 260 or any(c in share for c in "\r\n\t\"<>|?*"):
                return JSONResponse({"ok": False, "code": "bad_share", "error": "共用資料夾路徑格式不正確"}, status_code=400)
            if share:
                s["update_share"] = share
            else:
                s.pop("update_share", None)
        s["allow_remote_view"] = bool(body.get("allow_remote_view"))
        if gh:
            rw = cfg.get("remote_whisper") if isinstance(cfg.get("remote_whisper"), dict) else {}
            rw.update(host=gh, whisper_port=int(body.get("gpu_port") or 8978))
            cfg["remote_whisper"] = rw
        elif "remote_whisper" in cfg and (backend == "server" or body.get("clear_gpu")):
            # 伺服器模式沒填 GPU 伺服器＝辨識在本機：拿掉舊的設定，畫面上看到的就是實際用的
            cfg.pop("remote_whisper")
        if llm:
            base, lh, lp = llm
            cfg["llm_host"], cfg["llm_port"] = lh, lp
            if base == f"http://{lh}:{lp}" and style != "openai":
                cfg.pop("llm_url", None)
            else:
                cfg["llm_url"] = base          # https、路徑：主程式從 llm_url 解析
        if style:
            cfg["llm_api_style"] = style
        else:
            cfg.pop("llm_api_style", None)
        if key:
            cfg["llm_api_key"] = key
        elif body.get("clear_llm_api_key"):
            cfg.pop("llm_api_key", None)
        sp = str(body.get("staff_password") or "").strip()
        view_hash = None
        if sp:
            s["password_hash"] = view_hash = pw_hash(sp)
            s.pop("password", None)
        elif body.get("clear_staff_password"):
            s.pop("password_hash", None)
            s.pop("password", None)
            view_hash = ""
        if view_hash is not None:
            # 同仁密碼也是「觀看字幕」的密碼（WebUI 的唯讀密碼，/ws 用它驗證）：同一組，IT 只要設一次
            wp = cfg.get("webui_passwords") if isinstance(cfg.get("webui_passwords"), dict) else {}
            wp["read_sha256"] = view_hash
            cfg["webui_passwords"] = wp
        write_config(cfg)
        if view_hash is not None and set_view_password:
            set_view_password(view_hash)
        return {"ok": True, "state": admin_state()}

    return queue
