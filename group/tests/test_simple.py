"""集團版簡易頁面（/simple）的端對端檢查：用假的主程式跑完整流程（上傳 → 排隊 → 處理 → 下載）。

不需要 AI 模型：假的 translate_meeting.py 照真的主程式的檔名格式產出逐字稿與摘要。
執行（在專案根目錄）：
    python3 -m unittest group/tests/test_simple.py -v
"""
import json
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from group import simple_routes  # noqa: E402

FAKE_MAIN = r'''
import os, sys, time
a = sys.argv
inp = a[a.index("--input") + 1]; mode = a[a.index("--mode") + 1]
open(os.path.join(os.path.dirname(__file__), "args.txt"), "a").write(" ".join(a[1:]) + "\n")
if "FAIL" in inp:
    print("[錯誤] 無法讀取音訊檔"); sys.exit(2)
base = os.path.splitext(os.path.basename(inp))[0]
d = os.path.join("logs", f"{base}_20261104_120000"); os.makedirs(d, exist_ok=True)
print("\x1b[37m  辨識語言    id\x1b[0m"); print(f"  記錄檔      {d}/", flush=True)
if "SLOW" in inp:
    time.sleep(30)
for n in (f"印尼翻中_時間逐字稿_{base}.txt", f"印尼翻中_時間逐字稿_{base}.html", f"印尼翻中_時間逐字稿_{base}.srt",
          f"印尼翻中_摘要_{base}.html", f"印尼翻中_摘要_{base}.txt", f"{base}.mp3"):
    open(os.path.join(d, n), "w").write("x")
print("  處理完成")
'''


def _pw_hash(raw):
    return "h:" + raw


def _pw_match(raw, h):
    return h == "h:" + (raw or "")


class SimpleFlow(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp())
        (self.base / "translate_meeting.py").write_text(FAKE_MAIN, encoding="utf-8")
        self.cfg = self.base / "config.json"
        self.local = True
        self.started = []
        self.view_pw = []
        self.gpu_up = True
        self.launched = []
        self.running = False
        self.args = ["python", "translate_meeting.py", "--webui", "--mode", "id_zh"]
        app = FastAPI()

        async def start_live(body):
            self.started.append(body)

        self.stopped = 0

        async def stop_live():
            self.stopped += 1
            self.running = False

        self.q = simple_routes.register(
            app, self.base, lambda r: self.local, _pw_hash, _pw_match, self.cfg,
            lambda c: self.cfg.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8"),
            start_live=start_live, live_running=lambda: self.running,
            live_args=lambda: self.args,
            set_view_password=self.view_pw.append, gpu_alive=lambda h, p: self.gpu_up,
            update_hooks={"github_fetch": self._no_github, "launch": self.launched.append}, stop_live=stop_live)
        self.c = TestClient(app)
        self.h = {"X-Client-Id": "browserA1234"}

    @staticmethod
    def _no_github(url):
        raise OSError("offline")

    def tearDown(self):
        shutil.rmtree(self.base, ignore_errors=True)

    def submit(self, name="會議.m4a", scenario="id2zh", h=None, **form):
        return self.c.post("/api/simple/jobs", headers=h or self.h,
                           files={"file": (name, b"RIFF....", "audio/mp4")},
                           data={"scenario": scenario, **form})

    def wait(self, jid, states=("done", "failed", "cancelled"), timeout=20):
        end = time.time() + timeout
        while time.time() < end:
            j = next(x for x in self.c.get("/api/simple/jobs", headers=self.h).json()["jobs"] if x["id"] == jid)
            if j["state"] in states:
                return j
            time.sleep(0.2)
        self.fail(f"工作沒有結束：{j}")

    def test_full_flow(self):
        self.cfg.write_text(json.dumps({"pcg_simple": {"backend": "server"},
                                        "remote_whisper": {"host": "10.0.0.5", "whisper_port": 8978}}), encoding="utf-8")
        self.assertIn("PCG", self.c.get("/simple").text)
        cfg = self.c.get("/api/simple/config", headers=self.h).json()
        self.assertIn("id2zh", [s["id"] for s in cfg["scenarios"]])
        r = self.submit(topic="中爪新廠", speakers="3").json()
        self.assertTrue(r["ok"], r)
        job = self.wait(r["id"])
        self.assertEqual(job["state"], "done", job)
        labels = [o["label"] for o in job["outputs"]]
        self.assertEqual(labels[0], "會議紀錄（網頁）")
        self.assertIn("字幕檔 SRT", labels)
        self.assertNotIn("x.mp3", [o["name"] for o in job["outputs"]])
        # 主程式拿到的參數
        args = (self.base / "args.txt").read_text(encoding="utf-8")
        for want in ("--mode id2zh", "--summarize", "--diarize", "--num-speakers 3", "--topic 中爪新廠", "-e llm"):
            self.assertIn(want, args)
        # 下載：要有工作的代號；逐字稿 HTML 載入的錄音（同資料夾）也拿得到
        key = self.c.get(f"/api/simple/jobs/{r['id']}/link", headers=self.h).json()["key"]
        name = job["outputs"][0]["name"]
        self.assertEqual(self.c.get(f"/simple/files/{r['id']}/{name}?k={key}").status_code, 200)
        self.assertEqual(self.c.get(f"/simple/files/{r['id']}/{name}?k=wrong").status_code, 404)
        self.assertEqual(self.c.get(f"/simple/files/{r['id']}/..%2F..%2Fconfig.json?k={key}").status_code, 404)
        # 別的瀏覽器看不到、拿不到下載代號
        other = {"X-Client-Id": "browserB5678"}
        self.assertEqual(self.c.get("/api/simple/jobs", headers=other).json()["jobs"], [])
        self.assertEqual(self.c.get(f"/api/simple/jobs/{r['id']}/link", headers=other).status_code, 404)

    def test_chinese_meeting_has_no_translation_engine(self):
        self.cfg.write_text(json.dumps({"pcg_simple": {"backend": "server"}}), encoding="utf-8")
        jid = self.submit(scenario="zh").json()["id"]
        self.wait(jid)
        self.assertNotIn("-e llm", (self.base / "args.txt").read_text(encoding="utf-8"))

    def test_failure_message(self):
        jid = self.submit(name="FAIL.mp3").json()["id"]
        job = self.wait(jid)
        self.assertEqual(job["state"], "failed")
        self.assertEqual(job["error"], "無法讀取音訊檔")

    def test_queue_and_cancel(self):
        a = self.submit(name="SLOW.mp3").json()["id"]
        self.wait(a, states=("running",))
        b = self.submit(name="second.mp3").json()["id"]
        jb = next(x for x in self.c.get("/api/simple/jobs", headers=self.h).json()["jobs"] if x["id"] == b)
        self.assertEqual((jb["state"], jb["ahead"]), ("queued", 1))
        self.assertTrue(self.c.post(f"/api/simple/jobs/{b}/cancel", headers=self.h).json()["ok"])
        self.assertTrue(self.c.post(f"/api/simple/jobs/{a}/cancel", headers=self.h).json()["ok"])
        self.assertEqual(self.wait(a)["state"], "cancelled")
        self.assertEqual(self.wait(b)["state"], "cancelled")

    def test_rejects(self):
        self.assertEqual(self.submit(name="x.exe").status_code, 400)
        self.assertEqual(self.submit(scenario="nope").status_code, 400)
        self.assertEqual(self.c.get("/api/simple/jobs", headers={"X-Client-Id": "bad id"}).status_code, 400)

    def test_password(self):
        self.cfg.write_text(json.dumps({"pcg_simple": {"password": "pcg123"}}), encoding="utf-8")
        self.local = False
        r = self.c.get("/api/simple/jobs", headers=self.h)        # 第一次使用時把明文密碼換成雜湊
        self.assertEqual(r.status_code, 401)
        self.assertTrue(r.json()["need_password"])
        saved = json.loads(self.cfg.read_text(encoding="utf-8"))["pcg_simple"]
        self.assertNotIn("password", saved)
        self.assertEqual(saved["password_hash"], "h:pcg123")
        ok = self.c.get("/api/simple/jobs", headers={**self.h, "X-Simple-Token": "pcg123"})
        self.assertEqual(ok.status_code, 200)

    def test_local_backend_default(self):
        """沒有設定 backend＝本機模式：小模型、M2M100、不做摘要、強制本機辨識"""
        jid = self.submit().json()["id"]
        self.wait(jid)
        args = (self.base / "args.txt").read_text(encoding="utf-8")
        for want in ("-e m2m", "-m small", "--local-asr"):
            self.assertIn(want, args)
        self.assertNotIn("--summarize", args)
        self.assertFalse(self.c.get("/api/simple/config", headers=self.h).json()["minutes"])

    def test_data_scope(self):
        """簡易頁面「資料送到哪裡」照設定顯示，不能寫死「不會送到外部」"""
        scope = lambda: self.c.get("/api/simple/config", headers=self.h).json()["data_scope"]
        self.assertEqual(scope(), "local")
        for style, want in ((None, "internal"), ("openwebui", "group"), ("openai", "external")):
            cfg = {"pcg_simple": {"backend": "server"}, "llm_host": "10.0.0.6"}
            if style:
                cfg["llm_api_style"] = style
            self.cfg.write_text(json.dumps(cfg), encoding="utf-8")
            self.assertEqual(scope(), want, style)
        page = self.c.get("/simple").text
        self.assertNotIn("不會送到外部", page)

    def test_version(self):
        """畫面上的版本：安裝檔寫的 group/version.json；原作者版本從 translate_meeting.py 讀"""
        simple_routes._VERSION.clear()
        (self.base / "group").mkdir(exist_ok=True)
        (self.base / "group" / "version.json").write_text('{"version": "2026.11.5.r5", "commit": "abc1234"}', encoding="utf-8")
        with open(self.base / "translate_meeting.py", "a", encoding="utf-8") as f:
            f.write('\nAPP_VERSION = "2.34.0"\n')
        v = self.c.get("/api/simple/config", headers=self.h).json()["version"]
        self.assertEqual(v, {"version": "2026.11.5.r5", "commit": "abc1234", "upstream": "2.34.0"})
        self.assertEqual(self.c.get("/api/simple/live").json()["version"]["version"], "2026.11.5.r5")
        simple_routes._VERSION.clear()
        (self.base / "group" / "version.json").unlink()
        self.assertEqual(self.c.get("/api/simple/config", headers=self.h).json()["version"]["version"], "dev")
        simple_routes._VERSION.clear()

    def test_live(self):
        info = self.c.get("/api/simple/live").json()
        self.assertTrue(info["local"])
        self.assertEqual(info["mode"], "id_zh")              # 精簡字幕頁顯示「印尼文 ↔ 中文」用
        page = self.c.get("/simple/live").text
        self.assertIn("/ws", page)
        self.assertIn("only_mine", page)
        r = self.c.post("/api/simple/live", json={"scenario": "vi", "speak": True, "topic": "週會"}).json()
        self.assertEqual(r["mode"], "vi_zh")
        self.assertEqual(self.started[-1]["mode"], "vi_zh")
        self.assertEqual(self.started[-1]["engine"], "nllb")     # 本機模式：走 nllb 路徑（集團版改用 M2M100）
        self.assertTrue(self.started[-1]["local_asr"])
        self.cfg.write_text(json.dumps({"pcg_simple": {"backend": "server"}}), encoding="utf-8")
        self.c.post("/api/simple/live", json={"scenario": "vi"})
        self.assertEqual(self.started[-1]["engine"], "llm")
        # 教室模式：同一支麥克風，模式是「印尼文→中文」加 room，一定本機辨識；跟「我也要說話」二選一
        r = self.c.post("/api/simple/live", json={"scenario": "id", "room": True, "speak": True}).json()
        self.assertEqual((r["mode"], r["room"]), ("id_zh", True))
        self.assertEqual((self.started[-1]["mode"], self.started[-1]["room"], self.started[-1]["local_asr"]), ("id2zh", True, True))
        self.assertFalse(self.c.post("/api/simple/live", json={"scenario": "ja", "room": True}).json()["room"])
        # 外語同仁自己的電腦：對方說中文，翻成印尼文（單向，沒有雙向）
        r = self.c.post("/api/simple/live", json={"scenario": "zh2id", "speak": True}).json()
        self.assertEqual(r["mode"], "zh2id")
        self.assertIsNotNone(self.started[-1]["engine"])
        self.assertIn("zh2vi", [x["id"] for x in self.c.get("/api/simple/live").json()["scenarios"]])
        r = self.c.post("/api/simple/live", json={"scenario": "zh", "speak": True}).json()
        self.assertEqual(r["mode"], "zh")                     # 中文沒有雙向
        self.assertIsNone(self.started[-1]["engine"])
        self.local = False
        self.assertEqual(self.c.post("/api/simple/live", json={"scenario": "id"}).status_code, 403)

    def test_live_switch_language_while_running(self):
        """上一場沒按停止：同一種語言回到那一場；換語言要換掉，不能回到舊的那一場"""
        self.running = True
        self.args = ["python", "translate_meeting.py", "--webui", "--mode", "zh2id"]
        r = self.c.post("/api/simple/live", json={"scenario": "zh2id"}).json()
        self.assertTrue(r.get("already"))
        self.assertEqual(self.started, [])
        r = self.c.post("/api/simple/live", json={"scenario": "en"}).json()
        self.assertFalse(r.get("already"))
        self.assertEqual(self.started[-1]["mode"], "en2zh")
        # 同一種語言，但這次要開教室模式：也要重開
        self.args = ["python", "translate_meeting.py", "--webui", "--mode", "en2zh"]
        self.c.post("/api/simple/live", json={"scenario": "en", "room": True})
        self.assertEqual((self.started[-1]["mode"], self.started[-1]["room"]), ("en2zh", True))
        # 正在處理錄音檔：不要把它停掉
        self.args = ["python", "translate_meeting.py", "--webui", "--mode", "id2zh", "--input", "a.mp3"]
        r = self.c.post("/api/simple/live", json={"scenario": "en"})
        self.assertEqual((r.status_code, r.json()["code"]), (409, "live_busy_file"))
        self.assertEqual(len(self.started), 2)

    def test_live_stop_from_home(self):
        """首頁「字幕進行中」旁的停止：只在這台電腦、沒在跑就不用停、處理錄音檔時不停"""
        self.assertFalse(self.c.post("/api/simple/live/stop").json()["stopped"])
        self.running = True
        self.args = ["python", "translate_meeting.py", "--webui", "--mode", "id2zh", "--input", "a.mp3"]
        self.assertEqual(self.c.post("/api/simple/live/stop").status_code, 409)
        self.args = ["python", "translate_meeting.py", "--webui", "--mode", "zh2id"]
        self.local = False
        self.assertEqual(self.c.post("/api/simple/live/stop").status_code, 403)
        self.local = True
        self.assertTrue(self.c.post("/api/simple/live/stop").json()["stopped"])
        self.assertEqual(self.stopped, 1)
        self.assertFalse(self.c.get("/api/simple/live").json()["running"])


class AdminPage(SimpleFlow):
    """IT 設定頁：一律要 IT 密碼、第一次只能在本機設定、存檔寫成主程式讀得懂的格式"""

    def post(self, path, body, token=None):
        return self.c.post(path, json=body, headers={"X-IT-Token": token} if token else {})

    def test_first_password_local_only(self):
        self.local = False
        r = self.c.get("/api/simple/admin/state").json()
        self.assertEqual((r["code"], r["can_set"]), ("it_password_unset", False))
        self.assertEqual(self.post("/api/simple/admin/password", {"new": "itpass1"}).status_code, 403)
        self.local = True
        self.assertTrue(self.c.get("/api/simple/admin/state").json()["can_set"])
        self.assertEqual(self.post("/api/simple/admin/password", {"new": "123"}).status_code, 400)
        self.assertTrue(self.post("/api/simple/admin/password", {"new": "itpass1"}).json()["ok"])
        # 設好之後本機也要密碼（同仁就坐在這台電腦前）
        self.assertEqual(self.c.get("/api/simple/admin/state").status_code, 401)
        self.assertEqual(self.c.get("/api/simple/admin/state", headers={"X-IT-Token": "wrong"}).status_code, 401)
        st = self.c.get("/api/simple/admin/state", headers={"X-IT-Token": "itpass1"}).json()
        self.assertEqual(st["state"]["backend"], "local")
        # 改密碼要舊密碼
        self.assertEqual(self.post("/api/simple/admin/password", {"new": "newpass2"}).status_code, 401)
        self.assertTrue(self.post("/api/simple/admin/password", {"new": "newpass2"}, "itpass1").json()["ok"])

    def test_save_switches_to_server(self):
        self.post("/api/simple/admin/password", {"new": "itpass1"})
        tok = "itpass1"
        r = self.post("/api/simple/admin/save", {"backend": "server", "gpu_host": "10.0.0.5", "llm_host": ""}, tok)
        self.assertEqual(r.json()["code"], "need_llm")          # 伺服器模式一定要有大模型伺服器；GPU 選填
        r = self.post("/api/simple/admin/save", {"backend": "server", "gpu_host": "10.0.0.5; rm -rf /",
                                                  "llm_host": "10.0.0.5"}, tok)
        self.assertEqual(r.json()["code"], "bad_host")
        r = self.post("/api/simple/admin/save", {
            "backend": "server", "gpu_host": "10.0.0.5", "gpu_port": 8978, "llm_host": "10.0.0.6", "llm_port": 11434,
            "llm_model": "gemma4:26b", "diarize": True, "staff_password": "staff99"}, tok).json()
        self.assertTrue(r["ok"], r)
        cfg = json.loads(self.cfg.read_text(encoding="utf-8"))
        # 主程式讀的就是這幾個欄位（translate_meeting.py 的 REMOTE_WHISPER_CONFIG、OLLAMA_HOST/PORT）
        self.assertEqual(cfg["remote_whisper"], {"host": "10.0.0.5", "whisper_port": 8978})
        self.assertEqual((cfg["llm_host"], cfg["llm_port"]), ("10.0.0.6", 11434))
        self.assertEqual(cfg["pcg_simple"]["backend"], "server")
        self.assertEqual(cfg["pcg_simple"]["password_hash"], "h:staff99")
        self.assertTrue(cfg["pcg_simple"]["it_password_hash"])
        # 存完下一件工作就用伺服器模式
        jid = self.submit().json()["id"]
        self.wait(jid)
        args = (self.base / "args.txt").read_text(encoding="utf-8")
        self.assertIn("--summarize", args)
        self.assertIn("-e llm --llm-model gemma4:26b", args)
        # 切回本機
        r = self.post("/api/simple/admin/save", {"backend": "local", "gpu_host": "10.0.0.5", "llm_host": "10.0.0.6",
                                                  "local_live_model": "base"}, tok).json()
        self.assertEqual((r["state"]["backend"], r["state"]["local_live_model"]), ("local", "base"))

    def test_staff_password_is_view_password(self):
        """同仁密碼＝看分享字幕的密碼：寫進 WebUI 的唯讀密碼（設定檔與執行中的記憶體）"""
        self.post("/api/simple/admin/password", {"new": "itpass1"})
        self.post("/api/simple/admin/save", {"backend": "local", "staff_password": "staff99"}, "itpass1")
        cfg = json.loads(self.cfg.read_text(encoding="utf-8"))
        self.assertEqual(cfg["webui_passwords"]["read_sha256"], "h:staff99")
        self.assertEqual(self.view_pw[-1], "h:staff99")
        self.post("/api/simple/admin/save", {"backend": "local", "clear_staff_password": True}, "itpass1")
        cfg = json.loads(self.cfg.read_text(encoding="utf-8"))
        self.assertEqual(cfg["webui_passwords"]["read_sha256"], "")
        self.assertEqual(self.view_pw[-1], "")
        # 其他設定存檔（沒動密碼）不會改到觀看密碼
        n = len(self.view_pw)
        self.post("/api/simple/admin/save", {"backend": "local"}, "itpass1")
        self.assertEqual(len(self.view_pw), n)

    def test_share(self):
        import os as _os
        r = self.c.get("/api/simple/share").json()
        self.assertFalse(r["allowed"])                       # 預設沒開放
        self.post("/api/simple/admin/password", {"new": "itpass1"})
        self.post("/api/simple/admin/save", {"backend": "local", "allow_remote_view": True,
                                              "staff_password": "staff99"}, "itpass1")
        _os.environ["PCG_WEBUI_HOST"] = "127.0.0.1"         # 開放了但程式還沒重開
        try:
            self.assertFalse(self.c.get("/api/simple/share").json()["bound"])
        finally:
            _os.environ.pop("PCG_WEBUI_HOST", None)
        r = self.c.get("/api/simple/share").json()
        self.assertTrue(r["allowed"] and r["bound"] and r["password_set"])
        for u in r["urls"]:
            self.assertRegex(u, r"^http://[0-9.]+:\d+/simple/live$")
        qr = self.c.get("/api/simple/share/qr.svg", params={"u": "http://192.168.1.23:19781/simple/live"})
        self.assertEqual(qr.status_code, 200)
        self.assertIn("<svg", qr.text)
        # 只產生這台電腦自己的字幕網址（不能拿來做任意 QR Code）
        self.assertEqual(self.c.get("/api/simple/share/qr.svg", params={"u": "http://evil.example/"}).status_code, 400)
        self.local = False
        self.assertEqual(self.c.get("/api/simple/share").status_code, 403)

    def test_openwebui_without_gpu(self):
        """集團 Open WebUI：填完整網址＋API 金鑰；沒有 GPU 伺服器＝辨識在本機（小模型），翻譯與會議紀錄交給大模型"""
        self.post("/api/simple/admin/password", {"new": "itpass1"})
        tok = "itpass1"
        self.cfg.write_text(json.dumps({**json.loads(self.cfg.read_text(encoding="utf-8")),
                                        "remote_whisper": {"host": "10.9.9.9", "whisper_port": 8978}}), encoding="utf-8")
        r = self.post("/api/simple/admin/save", {
            "backend": "server", "gpu_host": "", "llm_url": "https://ai.example.com/", "llm_api_style": "openwebui",
            "llm_api_key": "sk-abc123", "llm_model": "luna", "summary_model": "deepseek-pro"}, tok).json()
        self.assertTrue(r["ok"], r)
        cfg = json.loads(self.cfg.read_text(encoding="utf-8"))
        self.assertEqual((cfg["llm_url"], cfg["llm_host"], cfg["llm_port"]), ("https://ai.example.com", "ai.example.com", 443))
        self.assertEqual((cfg["llm_api_style"], cfg["llm_api_key"]), ("openwebui", "sk-abc123"))
        self.assertNotIn("remote_whisper", cfg)                 # 畫面上沒填 GPU＝不用舊的 GPU 設定
        st = r["state"]
        self.assertTrue(st["llm_api_key_set"])
        self.assertNotIn("sk-abc123", json.dumps(st))           # 金鑰不回給畫面
        self.assertEqual((st["llm_url"], st["llm_api_style"]), ("https://ai.example.com", "openwebui"))
        jid = self.submit().json()["id"]
        self.wait(jid)
        args = (self.base / "args.txt").read_text(encoding="utf-8")
        for want in ("--summarize", "--local-asr", "-m small", "-e llm --llm-model luna", "--summary-model deepseek-pro"):
            self.assertIn(want, args)
        self.c.post("/api/simple/live", json={"scenario": "id"})
        self.assertEqual((self.started[-1]["engine"], self.started[-1]["local_asr"], self.started[-1]["model"]),
                         ("llm", True, "small"))
        # 存別的設定不會清掉金鑰；勾「刪除」才清
        self.post("/api/simple/admin/save", {"backend": "server", "llm_url": "https://ai.example.com"}, tok)
        self.assertEqual(json.loads(self.cfg.read_text(encoding="utf-8"))["llm_api_key"], "sk-abc123")
        self.post("/api/simple/admin/save", {"backend": "server", "llm_url": "10.0.0.6:11434", "llm_api_style": "auto",
                                              "clear_llm_api_key": True}, tok)
        cfg = json.loads(self.cfg.read_text(encoding="utf-8"))
        for k in ("llm_api_key", "llm_api_style", "llm_url"):
            self.assertNotIn(k, cfg)
        self.assertEqual((cfg["llm_host"], cfg["llm_port"]), ("10.0.0.6", 11434))
        for bad in ("ftp://x", "https://a b", "http://x:99999"):
            self.assertEqual(self.post("/api/simple/admin/save", {"backend": "server", "llm_url": bad}, tok).json()["code"],
                             "bad_host", bad)

    def test_gpu_down_falls_back_to_local(self):
        """GPU 伺服器有設但連不上：辨識改在本機用小模型（不要在 CPU 上硬跑 large-v3-turbo）"""
        self.gpu_up = False
        self.cfg.write_text(json.dumps({"pcg_simple": {"backend": "server"}, "llm_host": "10.0.0.6",
                                        "remote_whisper": {"host": "10.0.0.5", "whisper_port": 8978}}), encoding="utf-8")
        jid = self.submit().json()["id"]
        self.wait(jid)
        args = (self.base / "args.txt").read_text(encoding="utf-8")
        for want in ("--local-asr", "-m small", "--summarize", "-e llm"):
            self.assertIn(want, args)

    def test_external_ai(self):
        """外部 AI 服務（OpenAI 相容）：base URL 原樣保留（含 /v1）、一定要金鑰"""
        self.post("/api/simple/admin/password", {"new": "itpass1"})
        tok = "itpass1"
        body = {"backend": "server", "llm_url": "https://generativelanguage.googleapis.com/v1beta/openai",
                "llm_api_style": "openai", "llm_model": "gemini-2.5-flash"}
        self.assertEqual(self.post("/api/simple/admin/save", body, tok).json()["code"], "need_key")
        r = self.post("/api/simple/admin/save", {**body, "llm_api_key": "AIza-test"}, tok).json()
        self.assertTrue(r["ok"], r)
        cfg = json.loads(self.cfg.read_text(encoding="utf-8"))
        self.assertEqual((cfg["llm_url"], cfg["llm_api_style"]),
                         ("https://generativelanguage.googleapis.com/v1beta/openai", "openai"))
        self.post("/api/simple/admin/save", {**body, "llm_url": "https://api.openai.com/v1"}, tok)
        self.assertEqual(json.loads(self.cfg.read_text(encoding="utf-8"))["llm_url"], "https://api.openai.com/v1")
        self.assertEqual(self.post("/api/simple/admin/save", {}, tok).json().get("code"), None)
        # 內部伺服器（RTX Spark 上的 Ollama）不用金鑰
        r = self.post("/api/simple/admin/save", {"backend": "server", "llm_url": "192.168.1.60:11434",
                                                  "llm_api_style": "auto", "clear_llm_api_key": True}, tok).json()
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["state"]["llm_api_style"], "auto")
        # Open WebUI 沒金鑰也不行
        self.assertEqual(self.post("/api/simple/admin/save", {"backend": "server", "llm_url": "https://ai.example.com",
                                                               "llm_api_style": "openwebui"}, tok).json()["code"], "need_key")

    def test_openwebui_connection_test(self):
        """測試連線：帶 Bearer 金鑰查 /api/models，列出 luna、deepseek；金鑰錯時講清楚"""
        import threading
        from http.server import BaseHTTPRequestHandler, HTTPServer

        class H(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path != "/api/models":
                    body, code = b"<html>Open WebUI</html>", 200     # 前端頁面（SPA）
                elif self.headers.get("Authorization") != "Bearer sk-good":
                    body, code = b'{"detail":"Not authenticated"}', 401
                else:
                    body, code = json.dumps({"data": [{"id": "luna"}, {"id": "deepseek-pro"}]}).encode(), 200
                self.send_response(code)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *a):
                pass
        srv = HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            url = f"http://127.0.0.1:{srv.server_port}"
            self.post("/api/simple/admin/password", {"new": "itpass1"})
            r = self.post("/api/simple/admin/test", {"llm_url": url, "llm_api_key": "sk-good"}, "itpass1").json()
            self.assertTrue(r["llm"]["ok"], r)
            self.assertEqual((r["llm"]["type"], r["llm"]["style"], r["llm"]["models"]),
                             ("Open WebUI", "openwebui", ["luna", "deepseek-pro"]))
            r = self.post("/api/simple/admin/test", {"llm_url": url, "llm_api_style": "openwebui",
                                                      "llm_api_key": "sk-bad"}, "itpass1").json()
            self.assertFalse(r["llm"]["ok"])
            self.assertIn("API 金鑰", r["llm"]["detail"])
            # 外部 AI 服務：base URL 後面直接接 /models
            r = self.post("/api/simple/admin/test", {"llm_url": url + "/api", "llm_api_style": "openai",
                                                      "llm_api_key": "sk-good"}, "itpass1").json()
            self.assertEqual((r["llm"]["ok"], r["llm"]["style"], r["llm"]["models"]), (True, "openai", ["luna", "deepseek-pro"]))
        finally:
            srv.shutdown()

    def test_one_click_update(self):
        """一鍵更新：共用資料夾有較新的小更新包 → 同仁可以按；改成只有 IT 時要 IT 密碼；別台電腦不行"""
        import hashlib
        simple_routes._VERSION.clear()
        (self.base / "group").mkdir(exist_ok=True)
        (self.base / "group" / "version.json").write_text('{"version": "2026.11.5.r6"}', encoding="utf-8")
        share = self.base / "share"
        share.mkdir()
        data = b"MZ patch"
        (share / "PCG-Update-2026.11.5.r7.exe").write_bytes(data)
        (share / "PCG-Update-2026.11.5.r7.exe.sha256").write_text(hashlib.sha256(data).hexdigest())
        self.post("/api/simple/admin/password", {"new": "itpass1"})
        self.post("/api/simple/admin/save", {"backend": "local", "update_share": str(share)}, "itpass1")
        info = self.c.get("/api/simple/update?force=1").json()
        self.assertTrue(info["available"], info)
        self.assertEqual((info["latest"]["version"], info["latest"]["kind"], info["who"]), ("2026.11.5.r7", "patch", "staff"))
        r = self.c.post("/api/simple/update", json={}).json()
        self.assertTrue(r["ok"], r)
        self.assertEqual(self.launched[-1].name, "PCG-Update-2026.11.5.r7.exe")
        # 只有 IT
        self.post("/api/simple/admin/save", {"backend": "local", "update_who": "it"}, "itpass1")
        self.assertEqual(self.c.post("/api/simple/update", json={}).status_code, 401)
        self.assertTrue(self.c.post("/api/simple/update", json={}, headers={"X-IT-Token": "itpass1"}).json()["ok"])
        # 別台電腦：看不到、不能按
        self.local = False
        self.assertFalse(self.c.get("/api/simple/update").json()["enabled"])
        self.assertEqual(self.c.post("/api/simple/update", json={}).status_code, 403)
        self.local = True
        # 關掉自動檢查
        self.post("/api/simple/admin/save", {"backend": "local", "update_check": False}, "itpass1")
        self.assertFalse(self.c.get("/api/simple/update").json()["enabled"])
        self.assertEqual(self.post("/api/simple/admin/save", {"backend": "local", "update_share": "a\nb"}, "itpass1")
                         .json()["code"], "bad_share")
        simple_routes._VERSION.clear()

    def test_update_no_new_version_rechecks_after_10_minutes(self):
        """程式一直開著：之前查過「沒有新版」，新版發布後 10 分鐘內要看得到（以前要等 1 小時）"""
        import hashlib
        from unittest import mock
        simple_routes._VERSION.clear()
        (self.base / "group").mkdir(exist_ok=True)
        (self.base / "group" / "version.json").write_text('{"version": "2026.11.5.r9"}', encoding="utf-8")
        share = self.base / "share"
        share.mkdir()
        self.post("/api/simple/admin/password", {"new": "itpass1"})
        self.post("/api/simple/admin/save", {"backend": "local", "update_share": str(share)}, "itpass1")
        now = [1_000_000.0]
        with mock.patch.object(simple_routes.time, "time", lambda: now[0]):
            self.assertFalse(self.c.get("/api/simple/update").json()["available"])
            data = b"MZ patch"
            (share / "PCG-Update-2026.11.6.r10.exe").write_bytes(data)
            (share / "PCG-Update-2026.11.6.r10.exe.sha256").write_text(hashlib.sha256(data).hexdigest())
            now[0] += 300
            self.assertFalse(self.c.get("/api/simple/update").json()["available"])      # 5 分鐘：還是上次的結果
            self.assertTrue(self.c.get("/api/simple/update?force=1").json()["available"])  # 「檢查更新」馬上查
        simple_routes._VERSION.clear()

    def test_update_cache_expires(self):
        from unittest import mock
        import hashlib
        simple_routes._VERSION.clear()
        (self.base / "group").mkdir(exist_ok=True)
        (self.base / "group" / "version.json").write_text('{"version": "2026.11.5.r9"}', encoding="utf-8")
        share = self.base / "share"
        share.mkdir()
        self.post("/api/simple/admin/password", {"new": "itpass1"})
        self.post("/api/simple/admin/save", {"backend": "local", "update_share": str(share)}, "itpass1")
        now = [2_000_000.0]
        with mock.patch.object(simple_routes.time, "time", lambda: now[0]):
            self.assertFalse(self.c.get("/api/simple/update").json()["available"])
            data = b"MZ patch"
            (share / "PCG-Update-2026.11.6.r10.exe").write_bytes(data)
            (share / "PCG-Update-2026.11.6.r10.exe.sha256").write_text(hashlib.sha256(data).hexdigest())
            now[0] += 601
            self.assertTrue(self.c.get("/api/simple/update").json()["available"])
        simple_routes._VERSION.clear()

    def test_connection_test_reports_failures(self):
        self.post("/api/simple/admin/password", {"new": "itpass1"})
        r = self.post("/api/simple/admin/test", {"gpu_host": "127.0.0.1", "gpu_port": 1,
                                                  "llm_host": "127.0.0.1", "llm_port": 1}, "itpass1").json()
        self.assertFalse(r["gpu"]["ok"])
        self.assertFalse(r["llm"]["ok"])


if __name__ == "__main__":
    unittest.main()
