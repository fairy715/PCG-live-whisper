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
]

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


def profile(s):
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

    def __init__(self, base_dir: Path, settings_fn):
        self.base = base_dir
        self.settings = settings_fn
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
        pf = profile(s)
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
            env = dict(os.environ, PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8")
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


def register(app, base_dir: Path, is_local, pw_hash, pw_match, config_file: Path, write_config,
             start_live=None, live_running=None):
    """把簡易版的路由掛到 WebUI 的 FastAPI app 上（webui.py 呼叫）。
    start_live(body)：用 WebUI 原本的方式啟動即時字幕；live_running()：WebUI 是否正在跑"""
    from fastapi import File, Form, Request, UploadFile
    from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

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
                _state["q"] = SimpleQueue(base_dir, settings)
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

    @app.get("/api/simple/config")
    async def simple_config(request: Request):
        owner, err = auth(request)
        if err:
            return err
        pf = profile(settings())
        return {"ok": True, "scenarios": [{k: s.get(k, "") for k in ("id", "title", "subtitle", "flag")}
                                          for s in scenarios()],
                "max_upload_mb": _MAX_UPLOAD_MB, "backend": pf["backend"], "minutes": pf["summarize"]}

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

    @app.get("/api/simple/live")
    async def simple_live_info(request: Request):
        """即時字幕只能在自己的電腦上開（要抓這台電腦播出來的聲音）"""
        return {"ok": True, "local": bool(is_local(request)), "available": start_live is not None,
                "running": bool(live_running and live_running()),
                "scenarios": [{k: s[k] for k in ("id", "title", "flag")} | {"can_bidi": bool(s["bidi"])}
                              for s in LIVE_SCENARIOS]}

    @app.post("/api/simple/live")
    async def simple_live_start(request: Request, body: dict = {}):
        if not is_local(request):
            return JSONResponse({"ok": False, "code": "live_remote", "error": "即時字幕要在自己的電腦上開：請在這台電腦安裝 PCG-live-whisper，"
                                                       "用桌面捷徑開啟"}, status_code=403)
        if start_live is None:
            return JSONResponse({"ok": False, "code": "live_unavailable", "error": "這個版本不支援即時字幕"}, status_code=503)
        if live_running and live_running():
            return {"ok": True, "already": True}
        sc = next((x for x in LIVE_SCENARIOS if x["id"] == body.get("scenario")), None)
        if not sc:
            return JSONResponse({"ok": False, "code": "pick_language", "error": "請選擇對方說的語言"}, status_code=400)
        s = settings()
        mode = sc["bidi"] if (body.get("speak") and sc["bidi"]) else sc["mode"]
        pf = profile(s)
        start = {
            "mode": mode,
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
        return {"ok": True, "mode": mode}

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
                "llm_model": s.get("llm_model", ""), "summary_model": s.get("summary_model", ""),
                "asr_model": s.get("asr_model", "large-v3-turbo"),
                "local_file_model": s.get("local_file_model", "small"),
                "local_live_model": s.get("local_live_model", "small"),
                "diarize": bool(s.get("diarize", s.get("backend") == "server")),
                "staff_password_set": bool(s.get("password_hash") or s.get("password")),
                "m2m_installed": (base_dir / "models" / "m2m100_418m" / "model.bin").is_file()}

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

    def _probe(url, timeout=4):
        import urllib.request
        with urllib.request.urlopen(url, timeout=timeout) as r:
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
        lh, lp = str(body.get("llm_host") or "").strip(), int(body.get("llm_port") or 11434)
        if lh:
            try:
                tags = await asyncio.to_thread(_probe, f"http://{lh}:{lp}/api/tags")
                models = [m.get("name") for m in tags.get("models", []) if m.get("name")]
                out["llm"] = {"ok": True, "type": "Ollama", "models": models}
            except Exception as e1:
                try:
                    data = await asyncio.to_thread(_probe, f"http://{lh}:{lp}/v1/models")
                    out["llm"] = {"ok": True, "type": "OpenAI 相容",
                                  "models": [m.get("id") for m in data.get("data", []) if m.get("id")]}
                except Exception:
                    out["llm"] = {"ok": False, "detail": f"{type(e1).__name__}: {e1}"[:200]}
        return out

    @app.post("/api/simple/admin/save")
    async def admin_save(request: Request, body: dict = {}):
        err = admin_auth(request)
        if err:
            return err
        backend = "server" if body.get("backend") == "server" else "local"
        gh, lh = str(body.get("gpu_host") or "").strip(), str(body.get("llm_host") or "").strip()
        if backend == "server" and not (gh and lh):
            return JSONResponse({"ok": False, "code": "need_servers",
                                 "error": "伺服器模式要填 GPU 伺服器與 LLM 伺服器的位址"}, status_code=400)
        for host in (gh, lh):
            if host and not re.fullmatch(r"[A-Za-z0-9.\-:\[\]]{1,253}", host):
                return JSONResponse({"ok": False, "code": "bad_host", "error": f"位址格式不正確：{host}"},
                                    status_code=400)
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
        if gh:
            rw = cfg.get("remote_whisper") if isinstance(cfg.get("remote_whisper"), dict) else {}
            rw.update(host=gh, whisper_port=int(body.get("gpu_port") or 8978))
            cfg["remote_whisper"] = rw
        elif "remote_whisper" in cfg and backend == "local" and body.get("clear_gpu"):
            cfg.pop("remote_whisper")
        if lh:
            cfg["llm_host"], cfg["llm_port"] = lh, int(body.get("llm_port") or 11434)
        sp = str(body.get("staff_password") or "").strip()
        if sp:
            s["password_hash"] = pw_hash(sp)
            s.pop("password", None)
        elif body.get("clear_staff_password"):
            s.pop("password_hash", None)
            s.pop("password", None)
        write_config(cfg)
        return {"ok": True, "state": admin_state()}

    return queue
