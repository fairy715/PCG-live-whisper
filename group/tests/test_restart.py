"""集團版 r20：程式自己重新啟動（同仁不用去工作管理員關 python.exe）。

執行（在專案根目錄）：
    python3 -m unittest group/tests/test_restart.py -v
"""
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from group import restart, simple_routes  # noqa: E402


class Restart(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp())
        (self.base / "translate_meeting.py").write_text('APP_VERSION = "2.99"\n', encoding="utf-8")
        (self.base / "group_data").mkdir()
        self.cfg = self.base / "config.json"
        self.cfg.write_text(json.dumps({"pcg_simple": {"it_password_hash": "h:itpass1", "allow_remote_view": True}}),
                            encoding="utf-8")
        self.local = True
        self.running = False
        self.args = ["python", "translate_meeting.py", "--mode", "zh2id"]
        self.stopped = []
        self.relaunched = []
        self.exited = []

        async def stop_live():
            self.stopped.append(1)
            self.running = False

        app = FastAPI()
        simple_routes.register(
            app, self.base, lambda r: self.local, lambda raw: "h:" + raw, lambda raw, h: h == "h:" + (raw or ""),
            self.cfg, lambda c: self.cfg.write_text(json.dumps(c), encoding="utf-8"),
            start_live=lambda b: None, live_running=lambda: self.running, live_args=lambda: self.args,
            stop_live=stop_live, gpu_alive=lambda h, p: False,
            update_hooks={"github_fetch": self._offline, "models_fetch": self._offline,
                          "restart": lambda base, pid, port: self.relaunched.append((base, pid, port)),
                          "exit": lambda: self.exited.append(1)})
        self.c = TestClient(app)
        self._host = os.environ.get("PCG_WEBUI_HOST")
        os.environ["PCG_WEBUI_HOST"] = "127.0.0.1"

    def tearDown(self):
        shutil.rmtree(self.base, ignore_errors=True)
        if self._host is None:
            os.environ.pop("PCG_WEBUI_HOST", None)
        else:
            os.environ["PCG_WEBUI_HOST"] = self._host

    @staticmethod
    def _offline(u):
        raise OSError("offline")

    def test_pages_know_a_restart_is_needed(self):
        j = self.c.get("/api/simple/live").json()
        self.assertTrue(j["remote_view"])
        self.assertFalse(j["bound"])
        self.assertTrue(j["can_restart"])
        s = self.c.get("/api/simple/share").json()
        self.assertEqual((s["allowed"], s["bound"], s["can_restart"]), (True, False, True))
        os.environ["PCG_WEBUI_HOST"] = "0.0.0.0"
        self.assertTrue(self.c.get("/api/simple/live").json()["bound"])
        a = self.c.get("/api/simple/admin/state", headers={"X-IT-Token": "itpass1"}).json()["state"]
        self.assertEqual((a["allow_remote_view"], a["remote_bound"]), (True, True))

    def test_restart_relaunches_then_exits(self):
        r = self.c.post("/api/simple/restart", json={})
        self.assertEqual(r.json(), {"ok": True})
        self.assertEqual(len(self.relaunched), 1)
        base, pid, port = self.relaunched[0]
        self.assertEqual((base, pid), (self.base, os.getpid()))
        # 第二次按：不會再叫起一個
        self.assertTrue(self.c.post("/api/simple/restart", json={}).json().get("already"))
        self.assertEqual(len(self.relaunched), 1)

    def test_only_on_this_computer(self):
        self.local = False
        r = self.c.post("/api/simple/restart", json={})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.relaunched, [])

    def test_live_running_needs_stop_live(self):
        self.running = True
        r = self.c.post("/api/simple/restart", json={})
        self.assertEqual((r.status_code, r.json()["code"]), (409, "restart_live"))
        self.assertEqual(self.relaunched, [])
        r = self.c.post("/api/simple/restart", json={"stop_live": True})
        self.assertTrue(r.json()["ok"])
        self.assertEqual(self.stopped, [1])
        self.assertEqual(len(self.relaunched), 1)

    def test_not_while_processing_a_recording(self):
        self.running = True
        self.args = ["python", "translate_meeting.py", "--input", "a.wav"]
        r = self.c.post("/api/simple/restart", json={"stop_live": True})
        self.assertEqual((r.status_code, r.json()["code"]), (409, "restart_busy_file"))
        self.assertEqual((self.stopped, self.relaunched), ([], []))

    def test_relaunch_command(self):
        cmd = restart.command(Path("D:/PCG-live-whisper"), 4321, 19781)
        self.assertEqual(cmd[0], "powershell.exe")
        self.assertIn("-NoBrowser", cmd)
        self.assertEqual(cmd[cmd.index("-AfterPid") + 1], "4321")
        self.assertEqual(cmd[cmd.index("-Port") + 1], "19781")
        self.assertTrue(cmd[cmd.index("-File") + 1].endswith("launch.ps1"))
        seen = []
        restart.relaunch(Path("x"), 1, 2, popen=lambda a, **kw: seen.append((a, kw)))
        self.assertTrue(seen[0][1]["creationflags"] & 0x00000008)     # DETACHED_PROCESS：這邊結束它還在

    def test_launch_ps1_waits_for_old_process(self):
        ps = (ROOT / "group" / "windows" / "launch.ps1").read_text(encoding="utf-8-sig")
        self.assertIn("[int]$AfterPid = 0", ps)
        self.assertIn("Wait-Process -Id $AfterPid", ps)
        self.assertLess(ps.index("Wait-Process -Id $AfterPid"), ps.index("if (-not (Test-Port $Port)) {"))


if __name__ == "__main__":
    unittest.main()
