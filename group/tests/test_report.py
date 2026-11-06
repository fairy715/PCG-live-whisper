"""集團版「回報問題」：診斷檔的內容（遮掉金鑰與密碼、不含檔名與主題）、只能在本機產生、IT 設定頁要密碼。

執行（在專案根目錄）：
    python3 -m unittest group/tests/test_report.py -v
"""
import io
import json
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from group import diagnostics, simple_routes  # noqa: E402

SECRET = "sk-THISISSECRET123456"


class Report(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp())
        (self.base / "translate_meeting.py").write_text('APP_VERSION = "2.99"\n', encoding="utf-8")
        data = self.base / "group_data"
        data.mkdir()
        (data / "webui.log").write_text("".join(f"line {i}\n" for i in range(1000))
                                        + f"Authorization: Bearer {SECRET}\n", encoding="utf-8")
        (data / "webui-error.log").write_text("Traceback: boom\n", encoding="utf-8")
        (data / "job_20261106120000-abc123.log").write_text("[錯誤] 無法讀取音訊檔\n", encoding="utf-8")
        (data / "jobs.json").write_text(json.dumps({"20261106120000-abc123": {
            "id": "20261106120000-abc123", "owner": "browserA1234", "file": "董事會機密.m4a",
            "path": str(data / "up" / "董事會機密.m4a"), "scenario": "id2zh", "mode": "id_zh",
            "scenario_title": "印尼文會議", "topic": "併購案", "speakers": 0, "state": "failed",
            "created": 1.0, "started": 2.0, "finished": 3.0, "error": "無法讀取音訊檔", "out_dir": "", "stage": ""}},
            ensure_ascii=False), encoding="utf-8")
        self.cfg = self.base / "config.json"
        self.cfg.write_text(json.dumps({
            "llm_api_key": SECRET, "llm_host": "10.0.0.5",
            "webui_passwords": {"read_sha256": "abcdef0123"},
            "pcg_simple": {"it_password_hash": "h:itpass1", "password_hash": "h:staff1", "backend": "server",
                           "support_contact": "it-helpdesk@example.com"}}), encoding="utf-8")
        self.local = True
        app = FastAPI()
        self.q = simple_routes.register(
            app, self.base, lambda r: self.local, lambda raw: "h:" + raw, lambda raw, h: h == "h:" + (raw or ""),
            self.cfg, lambda c: self.cfg.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8"),
            live_running=lambda: True,
            live_args=lambda: ["python", "translate_meeting.py", "--mode", "id_zh", "--llm-api-key", SECRET],
            gpu_alive=lambda h, p: False,
            update_hooks={"github_fetch": self._offline, "models_fetch": self._offline})
        self.c = TestClient(app)
        self.c.get("/api/simple/jobs", headers={"X-Client-Id": "browserA1234"})   # 載入工作佇列

    @staticmethod
    def _offline(url):
        raise OSError("offline")

    def tearDown(self):
        shutil.rmtree(self.base, ignore_errors=True)

    def staff_report(self, **body):
        return self.c.post("/api/simple/report", json={"desc": "字幕沒有出現", "client": {"ua": "Edge", "lang": "zh"},
                                                       **body})

    @staticmethod
    def unzip(r):
        z = zipfile.ZipFile(io.BytesIO(r.content))
        return {n: z.read(n).decode("utf-8") for n in z.namelist()}

    def test_staff_report_contents(self):
        r = self.staff_report()
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.headers["content-type"], "application/zip")
        self.assertRegex(r.headers["content-disposition"], r"PCG-report-[A-Za-z0-9_-]+-\d{8}-\d{6}\.zip")
        files = self.unzip(r)
        self.assertTrue({"summary.txt", "report.json", "config.json", "logs/webui.log", "logs/webui-error.log",
                         "logs/job_20261106120000-abc123.log"} <= set(files), files.keys())
        everything = "\n".join(files.values())
        # 金鑰、密碼、雜湊都不在裡面（設定、即時字幕的命令列、記錄）
        for secret in (SECRET, "h:itpass1", "h:staff1", "abcdef0123"):
            self.assertNotIn(secret, everything)
        cfg = json.loads(files["config.json"])
        self.assertEqual(cfg["llm_api_key"], "***")
        self.assertEqual(cfg["pcg_simple"]["backend"], "server")
        self.assertEqual(cfg["llm_host"], "10.0.0.5")
        # 工作只留狀態與錯誤：檔名、主題、路徑、瀏覽器代號都不在裡面
        for private in ("董事會機密", "併購案", "browserA1234"):
            self.assertNotIn(private, everything)
        rep = json.loads(files["report.json"])
        self.assertEqual(rep["jobs"][0]["state"], "failed")
        self.assertEqual(rep["jobs"][0]["error"], "無法讀取音訊檔")
        self.assertTrue(rep["live"]["running"])
        self.assertIn("--mode", rep["live"]["args"])
        self.assertEqual(rep["version"]["upstream"], "2.99")
        self.assertIn("字幕沒有出現", files["summary.txt"])
        self.assertIn("Edge", files["summary.txt"])
        # 記錄只取最後一段
        self.assertLessEqual(len(files["logs/webui.log"].splitlines()), diagnostics.LOG_TAIL_LINES)
        self.assertIn("line 999", files["logs/webui.log"])
        self.assertNotIn("line 1\n", files["logs/webui.log"])
        # 存在 group_data/reports
        self.assertEqual(len(list((self.base / "group_data" / "reports").glob("PCG-report-*.zip"))), 1)

    def test_without_logs(self):
        files = self.unzip(self.staff_report(logs=False))
        self.assertFalse([n for n in files if n.startswith("logs/")])
        self.assertIn("summary.txt", files)

    def test_staff_report_local_only(self):
        self.local = False
        r = self.c.post("/api/simple/report", json={}, headers={"X-Client-Id": "browserB1234"})
        self.assertEqual((r.status_code, r.json()["code"]), (403, "report_remote"))

    def test_admin_report_needs_it_password(self):
        self.local = False
        self.assertEqual(self.c.post("/api/simple/admin/report", json={}).status_code, 401)
        r = self.c.post("/api/simple/admin/report", json={}, headers={"X-IT-Token": "itpass1"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("config.json", self.unzip(r))

    def test_keeps_last_reports(self):
        d = self.base / "group_data" / "reports"
        d.mkdir(parents=True, exist_ok=True)
        for i in range(diagnostics.KEEP_REPORTS + 3):
            (d / f"PCG-report-pc-20260101-0000{i:02d}.zip").write_bytes(b"x")
        self.staff_report()
        self.assertEqual(len(list(d.glob("PCG-report-*.zip"))), diagnostics.KEEP_REPORTS)

    def test_support_contact_setting(self):
        h = {"X-IT-Token": "itpass1"}
        self.assertEqual(self.c.get("/api/simple/config", headers={"X-Client-Id": "browserA1234"}).json()["support"],
                         "it-helpdesk@example.com")
        st = self.c.get("/api/simple/admin/state", headers=h).json()["state"]
        self.assertEqual(st["support_contact"], "it-helpdesk@example.com")
        base = {"backend": "server", "llm_url": "10.0.0.5:11434"}
        r = self.c.post("/api/simple/admin/save", json={**base, "support_contact": "Teams：IT 服務台"}, headers=h)
        self.assertTrue(r.json()["ok"], r.text)
        self.assertEqual(r.json()["state"]["support_contact"], "Teams：IT 服務台")
        self.assertEqual(self.c.post("/api/simple/admin/save", json={**base, "support_contact": "a<b>"},
                                     headers=h).json()["code"], "bad_contact")
        r = self.c.post("/api/simple/admin/save", json={**base, "support_contact": ""}, headers=h)
        self.assertEqual(r.json()["state"]["support_contact"], "")

    def test_redact_helpers(self):
        self.assertEqual(diagnostics.redact({"a": {"api_key": "x", "token": "", "keep_days": 14, "pw_set": True}}),
                         {"a": {"api_key": "***", "token": "", "keep_days": 14, "pw_set": True}})
        self.assertEqual(diagnostics.redact_args(["--api-key", "abc", "--mode", "x"]), ["--api-key", "***", "--mode", "x"])
        self.assertNotIn("abcdefgh123", diagnostics.redact_text('{"llm_api_key": "abcdefgh123"}'))
        self.assertTrue(diagnostics.valid_name("PCG-report-PC_01-20261106-120000.zip"))
        self.assertFalse(diagnostics.valid_name("../x.zip"))


if __name__ == "__main__":
    unittest.main()
