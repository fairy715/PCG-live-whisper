"""集團版 r33：即時字幕的逐字稿、語音辨識 API 的今日用量、模型的實測錯誤率。

執行（在專案根目錄）：
    python3 -m unittest group/tests/test_transcript.py -v
"""
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from group import asr_api, model_bench, transcript  # noqa: E402


def ev(**kw):
    return json.dumps({"type": "transcription", **kw}, ensure_ascii=False)


class Fold(unittest.TestCase):
    def test_finishes_follows_the_subtitle_screen_rule(self):
        self.assertTrue(transcript.finishes("We will check", "We will check the inventory tomorrow."))
        self.assertTrue(transcript.finishes("我們明天", "我們明天開會討論"))
        self.assertFalse(transcript.finishes("We will check the inventory.", "Please send the report."))
        self.assertFalse(transcript.finishes("好", "好的我知道了"))               # 太短，不當成半句
        self.assertFalse(transcript.finishes("同一句話", "同一句話"))

    def test_half_sentences_are_replaced_only_on_the_same_source(self):
        raw = [{"k": "s", "t": 1, "source": "main", "src": "We will check", "id": 1},
               {"k": "s", "t": 2, "source": "mic", "src": "我們明天", "id": 2},
               {"k": "s", "t": 3, "source": "main", "src": "We will check the inventory tomorrow.", "id": 3},
               {"k": "x", "id": 3, "tag": "VI", "text": "Chúng tôi sẽ kiểm tra"},
               {"k": "s", "t": 50, "source": "mic", "src": "我們明天開會", "id": 4}]      # 超過 30 秒：是新的一句
        lines = transcript.fold(raw)
        self.assertEqual([x["src"] for x in lines],
                         ["We will check the inventory tomorrow.", "我們明天", "我們明天開會"])
        self.assertEqual(lines[0]["extra"], {"VI": "Chúng tôi sẽ kiểm tra"})

    def test_mode_title(self):
        self.assertEqual(transcript.mode_title("id2zh"), "印尼文 → 中文")
        self.assertEqual(transcript.mode_title("vi_id"), "越南文 ↔ 印尼文")
        self.assertEqual(transcript.mode_title("zh"), "中文轉錄")


class Recording(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp())
        self.r = transcript.Recorder(self.base)

    def test_a_session_becomes_a_text_file_in_the_engines_log_format(self):
        self.r.on_event('{"type": "started", "mode": "id2zh"}')
        self.r.on_event(ev(source="main", src_lang="ID", src_text="Selamat pagi", dst_lang="中", dst_text="早安",
                           timestamp="14:30:05", id=1))
        self.r.on_event('{"type": "audio_level", "rms": 0.2}')                 # 別的事件不記
        self.r.on_event(json.dumps({"type": "transcription_extra", "id": 1, "lang": "VI", "text": "Chào buổi sáng"}))
        self.r.typed("zh", "id", "請再說一次", "Tolong ulangi")
        self.r.on_event(ev(source="main", src_lang="ID", src_text="Terima kasih", dst_lang="中", dst_text="（翻譯失敗）",
                           timestamp="14:31:00", id=2))
        s = self.r.sessions()
        self.assertEqual((len(s), s[0]["lines"], s[0]["mode"], s[0]["title"], s[0]["current"]),
                         (1, 3, "id2zh", "印尼文 → 中文", True))
        text = self.r.text(s[0]["id"])
        self.assertIn("[14:30:05] [ID] Selamat pagi\n[14:30:05] [中] 早安\n[14:30:05] [VI] Chào buổi sáng\n", text)
        self.assertRegex(text, r"\[\d\d:\d\d:\d\d\] \[中\] （打字）請再說一次\n\[\d\d:\d\d:\d\d\] \[ID\] Tolong ulangi\n")
        self.assertIn("[14:31:00] [ID] Terima kasih\n", text)
        self.assertNotIn("翻譯失敗", text)
        self.assertTrue(text.startswith("PCG 會議翻譯 即時字幕逐字稿"))

    def test_it_survives_a_restart_and_keeps_only_recent_sessions(self):
        self.r.on_event('{"type": "started", "mode": "zh"}')
        self.r.on_event(ev(source="main", src_lang="中", src_text="大家好"))
        again = transcript.Recorder(self.base)                                # 程式重開：上一場還讀得到
        s = again.sessions()
        self.assertEqual((s[0]["lines"], s[0]["current"]), (1, False))
        d = self.base / "group_data" / "live"
        for i in range(15):
            (d / f"202601{i + 1:02d}_090000.jsonl").write_text('{"k": "h", "started": 1, "mode": "zh"}\n', encoding="utf-8")
        time.sleep(1.1)                                                       # 檔名到秒：下一場要換一秒
        again.on_event('{"type": "started", "mode": "zh"}')
        self.assertEqual(len(list(d.glob("*.jsonl"))), transcript.KEEP)

    def test_empty_sessions_and_bad_ids_give_nothing(self):
        self.r.on_event('{"type": "started", "mode": "id2zh"}')
        self.assertEqual(self.r.sessions(), [])
        self.assertIsNone(self.r.text(self.r.sid))
        self.assertIsNone(self.r.text("../../config"))
        self.r.on_event(ev(source="main", src_text="", dst_text=""))            # 空的句子不記
        self.assertEqual(self.r.sessions(), [])

    def test_last_activity_time_follows_the_subtitles(self):
        self.r.on_event('{"type": "started", "mode": "id2zh"}')
        t0 = self.r.last
        self.assertGreater(t0, 0)
        time.sleep(0.02)
        self.r.on_event(ev(source="main", src_lang="ID", src_text="Selamat pagi"))
        self.assertGreater(self.r.last, t0)


class Usage(unittest.TestCase):
    def test_todays_usage_adds_up_and_starts_over_the_next_day(self):
        base = Path(tempfile.mkdtemp())
        now = time.mktime((2026, 11, 22, 10, 0, 0, 0, 0, -1))
        self.assertEqual(asr_api.usage_today(base, now)["requests"], 0)
        asr_api.usage_note(base, 6.5, now=now)
        asr_api.usage_note(base, 3.5, now=now)
        asr_api.usage_note(base, limited=True, now=now)
        u = asr_api.usage_today(base, now)
        self.assertEqual((u["requests"], u["seconds"], u["limited"]), (2, 10.0, 1))
        self.assertEqual(asr_api.usage_today(base, now + 86400)["requests"], 0)


class Bench(unittest.TestCase):
    def test_every_measured_pack_compares_with_the_built_in_model(self):
        b = model_bench.for_pack("whisper-id-small")
        self.assertEqual(b["rates"], [["id", 9.2, 16.1]])
        self.assertIsNone(model_bench.for_pack("madlad400-3b"))
        s = model_bench.summary()
        self.assertEqual(s["builtin"]["rates"][0], ["zh", 10.6, 10.6])
        self.assertNotIn("small", s["packs"])
        self.assertIn("breeze-asr-25", s["packs"])


if __name__ == "__main__":
    unittest.main()
