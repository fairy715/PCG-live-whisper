"""集團版：擋瀏覽器裡別的網站打這台電腦的 WebUI（group/security.py）。

執行（在專案根目錄）：
    python3 -m unittest group/tests/test_security.py -v
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, WebSocket  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from starlette.websockets import WebSocketDisconnect  # noqa: E402

from group import security  # noqa: E402


def make_app():
    app = FastAPI()
    hits = []

    @app.get("/page")
    async def page():
        return {"ok": True}

    @app.post("/api/save-forward")
    async def save_forward():
        hits.append("saved")
        return {"ok": True}

    @app.websocket("/ws")
    async def ws(sock: WebSocket):
        await sock.accept()
        await sock.send_text("subtitle")
        await sock.close()

    app.add_middleware(security.LocalGuard, names={"localhost", "pcg-pc01"})
    return app, hits


class Guard(unittest.TestCase):
    def setUp(self):
        self.app, self.hits = make_app()
        self.c = TestClient(self.app, base_url="http://localhost:19781")

    def post(self, **headers):
        return self.c.post("/api/save-forward", headers=headers)

    def test_same_origin_and_tools_pass(self):
        self.assertEqual(self.post(Origin="http://localhost:19781").status_code, 200)
        self.assertEqual(self.post().status_code, 200)                       # 主程式、命令列：沒有 Origin
        self.assertEqual(self.c.get("/page").status_code, 200)
        # 手機或其他電腦用 IP 連進來（分享的 QR Code）
        self.assertEqual(self.post(Host="192.168.1.20:19781", Origin="http://192.168.1.20:19781").status_code, 200)
        self.assertEqual(self.post(Host="[::1]:19781", Origin="http://[::1]:19781").status_code, 200)
        self.assertEqual(self.post(Host="PCG-PC01:19781", Origin="http://pcg-pc01:19781").status_code, 200)
        self.assertEqual(self.hits.count("saved"), 5)

    def test_other_sites_blocked(self):
        for origin in ("http://evil.example", "http://127.0.0.1:8899", "http://localhost:8080", "null",
                       "file://", "chrome-extension://abc"):
            r = self.post(Origin=origin)
            self.assertEqual((r.status_code, r.json()["code"]), (403, "blocked_origin"), origin)
        self.assertEqual(self.hits, [])

    def test_dns_rebinding_blocked(self):
        r = self.c.get("/page", headers={"Host": "evil.example:19781"})
        self.assertEqual((r.status_code, r.json()["code"]), (403, "blocked_host"))
        r = self.post(Host="rebind.attacker.test:19781", Origin="http://rebind.attacker.test:19781")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.hits, [])

    def test_websocket(self):
        # 測試工具的 WebSocket 一律送 Host: testserver，所以每次都自己帶 Host
        h = {"Host": "localhost:19781"}
        with self.c.websocket_connect("/ws", headers={**h, "Origin": "http://localhost:19781"}) as s:
            self.assertEqual(s.receive_text(), "subtitle")
        with self.c.websocket_connect("/ws", headers=h) as s:                # 懸浮字幕視窗等，沒有 Origin
            self.assertEqual(s.receive_text(), "subtitle")
        for headers in ({**h, "Origin": "http://evil.example"}, {**h, "Origin": "http://127.0.0.1:8899"},
                        {"Host": "evil.example:19781"}):
            with self.assertRaises(WebSocketDisconnect, msg=str(headers)):
                with self.c.websocket_connect("/ws", headers=headers) as s:
                    s.receive_text()

    def test_helpers(self):
        self.assertTrue(security.host_ok("localhost:19781", {"localhost"}))
        self.assertTrue(security.host_ok("10.0.0.5", {"localhost"}))
        self.assertTrue(security.host_ok("", {"localhost"}))
        self.assertFalse(security.host_ok("localhost.evil.example", {"localhost"}))
        self.assertTrue(security.origin_ok(None, "localhost:19781"))
        self.assertTrue(security.origin_ok("http://localhost", "localhost"))
        self.assertFalse(security.origin_ok("http://localhost:19781", ""))
        self.assertIn("localhost", security.own_names())

    def test_webui_registers_the_guard(self):
        src = (ROOT / "webui.py").read_text(encoding="utf-8")
        self.assertIn("_pcg_security.protect(app)", src)


if __name__ == "__main__":
    unittest.main()
