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
        app = FastAPI()

        async def start_live(body):
            self.started.append(body)

        self.q = simple_routes.register(
            app, self.base, lambda r: self.local, _pw_hash, _pw_match, self.cfg,
            lambda c: self.cfg.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8"),
            start_live=start_live, live_running=lambda: False)
        self.c = TestClient(app)
        self.h = {"X-Client-Id": "browserA1234"}

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
        self.assertIn("PCG 會議翻譯", self.c.get("/simple").text)
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

    def test_live(self):
        info = self.c.get("/api/simple/live").json()
        self.assertTrue(info["local"])
        r = self.c.post("/api/simple/live", json={"scenario": "vi", "speak": True, "topic": "週會"}).json()
        self.assertEqual(r["mode"], "vi_zh")
        self.assertEqual(self.started[-1]["mode"], "vi_zh")
        self.assertEqual(self.started[-1]["engine"], "llm")
        r = self.c.post("/api/simple/live", json={"scenario": "zh", "speak": True}).json()
        self.assertEqual(r["mode"], "zh")                     # 中文沒有雙向
        self.assertIsNone(self.started[-1]["engine"])
        self.local = False
        self.assertEqual(self.c.post("/api/simple/live", json={"scenario": "id"}).status_code, 403)


if __name__ == "__main__":
    unittest.main()
