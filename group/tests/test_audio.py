"""集團版 r24：聲音測試與音訊裝置選擇（用假的音訊裝置，不需要音效卡）。

執行（在專案根目錄）：
    python3 -m unittest group/tests/test_audio.py -v
"""
import json
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
for _name in ("ctranslate2", "sentencepiece"):
    sys.modules.setdefault(_name, types.ModuleType(_name))
sys.argv = [sys.argv[0]]

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import translate_meeting as t  # noqa: E402
from group import audio_test, simple_routes  # noqa: E402


class FakeBackend:
    def __init__(self):
        self.opened, self.closed, self.cbs = [], [], {}

    def mics(self):
        return [{"id": 3, "name": "麥克風 (Realtek)"}, {"id": 7, "name": "Jabra Speak 510"}]

    def default_mic(self):
        return "麥克風 (Realtek)"

    def speakers(self):
        return [{"name": "喇叭 (Realtek)"}, {"name": "耳機 (Jabra)"}]

    def default_speaker(self):
        return "喇叭 (Realtek)"

    def open_mic(self, idx, cb):
        if idx == 7:
            raise OSError("Device unavailable")
        self.opened.append(("mic", idx))
        self.cbs["mic"] = cb
        return lambda: self.closed.append("mic")

    def open_speaker(self, name, cb):
        self.opened.append(("speaker", name))
        self.cbs["speaker"] = cb
        return lambda: self.closed.append("speaker")


class MeterTest(unittest.TestCase):
    def setUp(self):
        self.now = [0.0]
        self.b = FakeBackend()
        self.m = audio_test.Meter(self.b, clock=lambda: self.now[0])

    def test_devices_and_name_to_index(self):
        d = self.m.devices()
        self.assertEqual([x["name"] for x in d["mics"]], ["麥克風 (Realtek)", "Jabra Speak 510"])
        self.assertEqual((d["default_mic"], d["default_speaker"], d["error"]), ("麥克風 (Realtek)", "喇叭 (Realtek)", ""))
        self.assertEqual(self.m.mic_index("Jabra Speak 510"), 7)
        self.assertIsNone(self.m.mic_index("拔掉的麥克風"))            # 找不到 → 用預設
        self.assertIsNone(self.m.mic_index(""))

    def test_levels_and_auto_stop(self):
        r = self.m.start(mic="", speaker="耳機 (Jabra)", seconds=5)
        self.assertTrue(r["running"])
        self.assertEqual(self.b.opened, [("speaker", "耳機 (Jabra)"), ("mic", None)])
        self.b.cbs["speaker"](0.5)
        self.b.cbs["mic"](0.0)
        lv = self.m.levels()
        self.assertEqual((lv["system"]["max"], lv["system"]["data"], lv["mic"]["max"]), (0.5, True, 0.0))
        self.b.cbs["speaker"](0.0)
        self.assertAlmostEqual(self.m.levels()["system"]["level"], 0.3)      # 音量條慢慢掉
        self.now[0] = 6.0
        self.assertFalse(self.m.levels()["running"])                         # 時間到自己停，不會一直佔著麥克風
        self.assertEqual(sorted(self.b.closed), ["mic", "speaker"])

    def test_broken_device_reports_error_and_other_side_still_runs(self):
        r = self.m.start(mic="Jabra Speak 510")
        self.assertIn("Device unavailable", r["mic"]["error"])
        self.assertEqual(r["system"]["error"], "")
        self.assertTrue(r["running"])
        self.m.stop()
        self.assertEqual(self.b.closed, ["speaker"])

    def test_restart_closes_previous_and_seconds_are_capped(self):
        self.m.start()
        self.m.start(seconds=9999)
        self.assertEqual(self.b.closed.count("speaker"), 1)
        self.now[0] = audio_test.MAX_SECONDS + 1
        self.assertFalse(self.m.levels()["running"])

    def test_clean_name(self):
        self.assertEqual(audio_test.clean_name("  Jabra   Speak "), "Jabra Speak")
        self.assertEqual(audio_test.clean_name('x"y'), "")
        self.assertEqual(audio_test.strip_loopback("喇叭 (Realtek) [Loopback]"), "喇叭 (Realtek)")


class PickLoopback(unittest.TestCase):
    """主程式要錄哪一個喇叭：沒指定跟以前一樣只問預設喇叭；指定了但找不到 → 預設喇叭"""

    class P:
        def __init__(self):
            self.gen_calls = 0

        def get_default_wasapi_loopback(self):
            return {"index": 1, "name": "喇叭 (Realtek) [Loopback]"}

        def get_loopback_device_info_generator(self):
            self.gen_calls += 1
            yield {"index": 1, "name": "喇叭 (Realtek) [Loopback]"}
            yield {"index": 5, "name": "耳機 (Jabra) [Loopback]"}

    def test_default_path_is_untouched(self):
        p = self.P()
        self.assertEqual(t._pcg_pick_loopback(p, want="")["index"], 1)
        self.assertEqual(p.gen_calls, 0)

    def test_chosen_speaker_and_missing_one(self):
        self.assertEqual(t._pcg_pick_loopback(self.P(), want="耳機 (Jabra)")["index"], 5)
        self.assertEqual(t._pcg_pick_loopback(self.P(), want="不存在的喇叭")["index"], 1)


class Routes(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp())
        (self.base / "translate_meeting.py").write_text('APP_VERSION = "2.99"\n', encoding="utf-8")
        (self.base / "group_data").mkdir()
        self.cfg = self.base / "config.json"
        self.cfg.write_text(json.dumps({"pcg_simple": {"it_password_hash": "h:itpass1"}}), encoding="utf-8")
        self.local, self.running, self.started = True, False, []
        self.args = None
        self.b = FakeBackend()

        async def start_live(body):
            self.started.append(body)
        app = FastAPI()
        simple_routes.register(
            app, self.base, lambda r: self.local, lambda raw: "h:" + raw, lambda raw, h: h == "h:" + (raw or ""),
            self.cfg, lambda c: self.cfg.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8"),
            start_live=start_live, live_running=lambda: self.running, live_args=lambda: self.args,
            gpu_alive=lambda h, p: False,
            update_hooks={"github_fetch": self._off, "models_fetch": self._off, "audio_backend": self.b})
        self.c = TestClient(app)

    def tearDown(self):
        shutil.rmtree(self.base, ignore_errors=True)

    @staticmethod
    def _off(u):
        raise OSError("offline")

    def test_list_save_and_clear(self):
        j = self.c.get("/api/simple/audio").json()
        self.assertEqual((j["mic"], j["speaker"], len(j["mics"]), len(j["speakers"]), j["live"]), ("", "", 2, 2, False))
        r = self.c.post("/api/simple/audio", json={"mic": "Jabra Speak 510", "speaker": "耳機 (Jabra)"}).json()
        self.assertEqual((r["mic"], r["speaker"]), ("Jabra Speak 510", "耳機 (Jabra)"))
        s = json.loads(self.cfg.read_text(encoding="utf-8"))["pcg_simple"]
        self.assertEqual((s["mic_name"], s["speaker_name"]), ("Jabra Speak 510", "耳機 (Jabra)"))
        self.c.post("/api/simple/audio", json={"mic": ""})
        s = json.loads(self.cfg.read_text(encoding="utf-8"))["pcg_simple"]
        self.assertNotIn("mic_name", s)
        self.assertEqual(s["speaker_name"], "耳機 (Jabra)")                  # 沒送的那一項不動
        self.assertEqual(self.c.post("/api/simple/audio", json={"mic": 'a"b'}).json()["code"], "bad_device")

    def test_test_start_level_stop(self):
        r = self.c.post("/api/simple/audio/test", json={"action": "start", "mic": "", "speaker": ""}).json()
        self.assertTrue(r["ok"] and r["running"])
        self.b.cbs["mic"](0.2)
        self.assertEqual(self.c.get("/api/simple/audio/level").json()["mic"]["max"], 0.2)
        self.assertFalse(self.c.post("/api/simple/audio/test", json={"action": "stop"}).json()["running"])

    def test_only_on_this_computer_and_not_during_live(self):
        self.running = True
        r = self.c.post("/api/simple/audio/test", json={"action": "start"})
        self.assertEqual((r.status_code, r.json()["code"]), (409, "audio_live"))
        self.local = False
        for method, url in (("get", "/api/simple/audio"), ("post", "/api/simple/audio"),
                            ("post", "/api/simple/audio/test"), ("get", "/api/simple/audio/level")):
            self.assertEqual(getattr(self.c, method)(url).status_code, 403, url)
        self.assertEqual(self.b.opened, [])

    def test_everyone_speaks_chinese_can_use_the_microphone(self):
        """「大家都說中文」（r28）：場合是教室／會議室字幕機時頁面帶 mic → 用麥克風收音，一定給主程式麥克風的編號
        （不給的話主程式收的是電腦播放的聲音）；其他場合照舊收電腦的聲音"""
        self.c.post("/api/simple/live", json={"scenario": "zh"})                                  # 我只看字幕：電腦的聲音
        self.assertEqual(self.started[-1]["mode"], "zh")
        self.assertNotIn("device", self.started[-1])
        self.c.post("/api/simple/live", json={"scenario": "zh", "mic": True})                     # 自動：Windows 預設麥克風
        st = self.started[-1]
        self.assertEqual((st["mode"], st["room"], st["device"]), ("zh", False, 3))
        self.assertNotIn("mic_device", st)                                                        # 不是「電腦聲音＋麥克風」兩路
        self.c.post("/api/simple/audio", json={"mic": "Jabra Speak 510"})                         # 同仁選的那一支
        self.c.post("/api/simple/live", json={"scenario": "zh", "mic": True})
        self.assertEqual(self.started[-1]["device"], 7)
        self.c.post("/api/simple/audio", json={"mic": "拔掉的麥克風"})                              # 選的拔掉了：用預設
        self.c.post("/api/simple/live", json={"scenario": "zh", "mic": True})
        self.assertEqual(self.started[-1]["device"], 3)
        # mic 只對「大家都說中文」有意義：其他語言不受影響
        self.c.post("/api/simple/live", json={"scenario": "id", "me": "zh", "mic": True})
        self.assertNotIn("device", self.started[-1])
        # 完全沒有麥克風：不要默默改收電腦的聲音，直接說找不到
        n = len(self.started)
        self.b.mics = lambda: []
        r = self.c.post("/api/simple/live", json={"scenario": "zh", "mic": True})
        self.assertEqual((r.status_code, r.json()["code"]), (409, "no_mic"))
        self.assertEqual(len(self.started), n)

    def test_switching_chinese_source_replaces_the_running_session(self):
        """上一場還在跑：同樣是中文，但一場收電腦的聲音、一場收麥克風，要換掉，不能當成「已經在跑」"""
        self.running = True
        self.args = ["--mode", "zh", "--local-asr"]                                               # 正在收電腦的聲音
        self.assertTrue(self.c.post("/api/simple/live", json={"scenario": "zh"}).json().get("already"))
        r = self.c.post("/api/simple/live", json={"scenario": "zh", "mic": True}).json()
        self.assertFalse(r.get("already"))
        self.assertEqual(self.started[-1]["device"], 3)
        self.args = ["--mode", "zh", "--local-asr", "-d", "3"]                                    # 正在收麥克風
        self.assertTrue(self.c.post("/api/simple/live", json={"scenario": "zh", "mic": True}).json().get("already"))
        self.assertFalse(self.c.post("/api/simple/live", json={"scenario": "zh"}).json().get("already"))

    def test_default_mic_index(self):
        m = audio_test.Meter(self.b)
        self.assertEqual(m.default_mic_index(), 3)
        self.b.default_mic = lambda: "Jabra Speak"                 # 預設裝置的名稱被截短
        self.assertEqual(m.default_mic_index(), 7)
        self.b.default_mic = lambda: ""                            # 問不到預設：用第一支
        self.assertEqual(m.default_mic_index(), 3)
        self.b.mics = lambda: []
        self.assertIsNone(m.default_mic_index())

    def test_chosen_mic_is_passed_to_the_engine(self):
        self.c.post("/api/simple/audio", json={"mic": "Jabra Speak 510"})
        self.c.post("/api/simple/live", json={"scenario": "id", "me": "zh", "speak": True})       # 我也要說話：雙向
        self.assertEqual(self.started[-1].get("mic_device"), 7)
        self.assertNotIn("device", self.started[-1])
        self.c.post("/api/simple/live", json={"scenario": "id", "me": "zh", "room": True})        # 教室：收音就是麥克風
        self.assertEqual(self.started[-1].get("device"), 7)
        self.c.post("/api/simple/live", json={"scenario": "id", "me": "zh"})                      # 只看字幕：不用麥克風
        self.assertNotIn("mic_device", self.started[-1])
        self.assertNotIn("device", self.started[-1])
        self.c.post("/api/simple/audio", json={"mic": "拔掉的麥克風"})
        self.c.post("/api/simple/live", json={"scenario": "id", "me": "zh", "speak": True})
        self.assertNotIn("mic_device", self.started[-1])                                          # 找不到 → 用預設


if __name__ == "__main__":
    unittest.main()
