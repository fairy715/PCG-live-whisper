"""集團版 r32：這場會議的資料、「聽錯的字」規則、打字回覆。

不需要 AI 模型：翻譯器用假的代替，只檢查流程與提示的內容。
執行（在專案根目錄）：
    python3 -m unittest group/tests/test_meeting_notes.py -v
"""
import asyncio
import json
import os
import queue
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
for _name in ("ctranslate2", "sentencepiece"):
    sys.modules.setdefault(_name, types.ModuleType(_name))
sys.argv = [sys.argv[0]]

import translate_meeting as t  # noqa: E402
from group import meeting_notes as mn  # noqa: E402
from group import reply  # noqa: E402

NOTES = """議程：
1. 14:30 開場
2. 中爪新廠 設備驗收
與會者：王小明、Budi Santoso, Nguyễn Văn An
料號: PO-12345; SKU 88-A
MES: 製造執行系統
這一段是很長的句子，說明這次會議的目的是討論第三季的出貨計畫以及品質異常的處理方式，請大家準備資料。
2026/11/23
"""


class Notes(unittest.TestCase):
    def test_terms_keep_names_and_part_numbers_and_skip_sentences(self):
        self.assertEqual(mn.terms(NOTES), ["開場", "中爪新廠 設備驗收", "王小明", "Budi Santoso", "Nguyễn Văn An",
                                           "PO-12345", "SKU 88-A", "MES", "製造執行系統"])

    def test_hotwords_have_a_limit(self):
        many = "\n".join(f"產品名稱第{i}號機台" for i in range(200))
        hot = mn.hotwords(many)
        self.assertLessEqual(len(hot), mn.HOT_MAX_CHARS)
        self.assertTrue(hot.startswith("產品名稱第0號機台"))

    def test_this_meetings_words_come_first_locally_and_last_for_the_api(self):
        # 提示詞超過長度：這台電腦的 Whisper 截掉後面的，語音辨識 API 只看最後一段
        self.assertEqual(mn.join_hotwords("王小明", "寶成, MES"), "王小明, 寶成, MES")
        self.assertEqual(mn.join_hotwords("王小明", "寶成, MES", api=True), "寶成, MES, 王小明")
        self.assertEqual(mn.join_hotwords("", "寶成"), "寶成")
        self.assertEqual(mn.join_hotwords("王小明", ""), "王小明")

    def test_echo_only_when_the_text_copies_several_hint_words(self):
        hot = mn.hotwords(NOTES)
        self.assertTrue(mn.echo("中爪新廠 設備驗收 王小明 Budi Santoso", hot))
        self.assertFalse(mn.echo("Budi Santoso", hot))                 # 真的有人念了一個名字
        self.assertFalse(mn.echo("中爪新廠 設備驗收", hot))             # 念了一個議程項目
        self.assertFalse(mn.echo("我們今天討論設備驗收", hot))
        self.assertFalse(mn.echo("", hot))

    def test_prompt_block_is_reference_only_and_bounded(self):
        b = mn.prompt_block(NOTES)
        self.assertIn("Budi Santoso", b)
        self.assertIn("不要翻譯", b)
        self.assertIn("never translate", b)
        self.assertEqual(mn.prompt_block("  \n "), "")
        self.assertLess(len(mn.prompt_block("字" * 9000)), mn.PROMPT_MAX + 400)

    def test_clean_removes_control_characters_and_caps_the_length(self):
        self.assertEqual(mn.clean("a\x00b\r\n\r\n\r\nc  "), "ab\n\nc")
        self.assertEqual(len(mn.clean("x" * 9999)), mn.MAX_TEXT)

    def test_save_and_load_and_empty_removes_the_file(self):
        base = Path(tempfile.mkdtemp())
        self.assertEqual(mn.save(base, " 王小明\n"), 3)
        self.assertEqual(mn.load(base), "王小明")
        self.assertEqual(mn.save(base, ""), 0)
        self.assertFalse(mn.path(base).exists())
        self.assertEqual(mn.load(base), "")


class AsrRule(unittest.TestCase):
    def setUp(self):
        self._tr = t._pcg_tr_note["tr"]          # 建翻譯器會被記成「主程式在用的」：測完還原，不影響別的測試

    def tearDown(self):
        os.environ.pop("PCG_TRANSLATE_GUESS", None)
        t._pcg_tr_note["tr"] = self._tr

    def test_known_rules_are_replaced_and_others_get_a_header(self):
        zh = mn.asr_rule("7. 即使原文不完整或語意不清，也直接逐字翻譯，不要跳過或加說明\n")
        self.assertNotIn("逐字翻譯", zh)
        self.assertIn("最合理的意思", zh)
        en = mn.asr_rule("6. If input is incomplete, translate it literally as-is without explanation\n")
        self.assertNotIn("literally", en)
        self.assertIn("most plausible", en)
        other = mn.asr_rule("Bạn là phiên dịch viên.")
        self.assertTrue(other.startswith("The text to translate comes from speech recognition"))
        self.assertTrue(other.endswith("Bạn là phiên dịch viên."))

    def test_it_can_be_switched_off(self):
        os.environ["PCG_TRANSLATE_GUESS"] = "off"
        s = "7. 即使原文不完整或語意不清，也直接逐字翻譯，不要跳過或加說明\n"
        self.assertEqual(mn.asr_rule(s), s)

    def test_every_translation_direction_carries_the_rule(self):
        """原作者改了提示的用語時這裡會抓到：每個方向的提示都要有「聽錯的字」那一條"""
        for d in ("en2zh", "zh2en", "ja2zh", "ko2zh", "id2zh", "vi2zh", "hi2zh", "zh2id", "zh2vi", "zh2hi",
                  "id2en", "en2id", "vi2id"):
            tr = t.OllamaTranslator("m", direction=d, skip_check=True)
            p = tr._build_prompt("hello", [])
            self.assertTrue("最合理的意思" in p or "most plausible" in p, d)
            self.assertNotIn("也直接逐字翻譯", p, d)


class EngineNotes(unittest.TestCase):
    """主程式：這場會議的資料 → 辨識的提示詞、翻譯提示的最前面"""

    def setUp(self):
        self._old = (t._PCG_NOTES[0], t._PCG_GLOSS[0], t._pcg_tr_note["tr"])
        t._PCG_NOTES[0] = mn.clean(NOTES)
        t._PCG_GLOSS[0] = ()

    def tearDown(self):
        t._PCG_NOTES[0], t._PCG_GLOSS[0], t._pcg_tr_note["tr"] = self._old

    def test_hotwords_include_this_meetings_words(self):
        self.assertIn("Budi Santoso", t._pcg_hotwords())
        t._PCG_NOTES[0] = ""
        self.assertEqual(t._pcg_hotwords(), "")

    def test_translation_prompt_starts_with_the_background(self):
        tr = t.OllamaTranslator("m", direction="id2zh", skip_check=True)
        p = tr._build_prompt("Selamat pagi", [])
        self.assertTrue(p.startswith("這場會議的背景資料"))
        self.assertIn("PO-12345", p)
        self.assertIn("Selamat pagi", p)
        t._PCG_NOTES[0] = ""
        self.assertNotIn("背景資料", tr._build_prompt("Selamat pagi", []))

    def test_segments_that_copy_the_hint_are_dropped(self):
        seg = types.SimpleNamespace
        out = list(t._pcg_gloss_segments([seg(text="中爪新廠 設備驗收 王小明 Budi Santoso"), seg(text="大家好")]))
        self.assertEqual([s.text for s in out], ["大家好"])


class FakeTr:
    def __init__(self, direction):
        self.direction = direction

    def translate(self, text):
        if "壞掉" in text:
            raise RuntimeError("boom")
        return f"[{self.direction}] {text}"


class EngineReply(unittest.TestCase):
    """主程式：.pcg_say 裡的句子 → 翻譯 → pcg_reply 事件"""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self._old = (t._PCG_SAY_FLAG, t._webui_queue, t._pcg_extra)
        t._PCG_SAY_FLAG = os.path.join(self.dir, ".pcg_say")
        t._webui_queue = queue.Queue()
        t._pcg_extra = t._PcgExtraSubs()
        t._pcg_extra.translator = FakeTr
        self.r = t._PcgReply()

    def tearDown(self):
        t._PCG_SAY_FLAG, t._webui_queue, t._pcg_extra = self._old

    def ask(self, **req):
        Path(t._PCG_SAY_FLAG).write_text(json.dumps({"at": time.time(), **req}, ensure_ascii=False), encoding="utf-8")
        self.r.poll()
        try:
            return t._webui_queue.get_nowait()
        except queue.Empty:
            return None

    def test_a_typed_sentence_is_translated_once(self):
        ev = self.ask(id=7, text="  請 再說一次 ", src="zh", tgt="id")
        self.assertEqual((ev["type"], ev["id"], ev["ok"], ev["text"]), ("pcg_reply", 7, True, "[zh2id] 請 再說一次"))
        self.r.poll()                                   # 同一個編號不會翻第二次
        self.assertTrue(t._webui_queue.empty())

    def test_the_event_line_is_what_the_webui_looks_for(self):
        ev = self.ask(id=8, text="好", src="zh", tgt="vi")
        self.assertTrue(json.dumps(ev, ensure_ascii=False).startswith(reply.EVENT_PREFIX))

    def test_unsupported_pairs_and_failures_answer_with_a_code(self):
        self.assertEqual(self.ask(id=1, text="好", src="zh", tgt="xx")["code"], "say_unsupported")
        self.assertEqual(self.ask(id=2, text="壞掉", src="zh", tgt="id")["code"], "say_failed")
        self.assertEqual(self.ask(id=3, text="   ", src="zh", tgt="id")["code"], "say_unsupported")

    def test_a_request_left_from_an_earlier_session_is_ignored(self):
        self.assertIsNone(self.ask(id=9, text="好", src="zh", tgt="id", at=time.time() - 600))

    def test_the_watcher_starts_with_the_subtitles(self):
        old = t._pcg_reply
        t._pcg_reply = types.SimpleNamespace(n=0, start=lambda: setattr(t._pcg_reply, "n", t._pcg_reply.n + 1))
        try:
            t._webui_send({"type": "started", "mode": "id2zh"})
            self.assertEqual(t._pcg_reply.n, 1)
        finally:
            t._pcg_reply = old


class Desk(unittest.TestCase):
    """WebUI 這一端：寫請求、等主程式的事件"""

    def test_pair_follows_the_mode(self):
        self.assertEqual(reply.pair("id2zh"), {"me": "zh", "other": "id"})
        self.assertEqual(reply.pair("zh2vi"), {"me": "vi", "other": "zh"})
        self.assertEqual(reply.pair("id_zh"), {"me": "zh", "other": "id"})
        self.assertEqual(reply.pair("vi_id"), {"me": "id", "other": "vi"})
        self.assertIsNone(reply.pair("zh"))
        self.assertIsNone(reply.pair("nan2en"))
        self.assertIsNone(reply.pair(""))

    def test_ask_writes_the_request_and_returns_the_engines_answer(self):
        base = Path(tempfile.mkdtemp())
        desk = reply.Desk(base)

        async def run():
            task = asyncio.create_task(desk.ask("你好", "zh", "id", timeout=5))
            for _ in range(100):
                await asyncio.sleep(0.02)
                if (base / reply.FILE_NAME).exists():
                    break
            req = json.loads((base / reply.FILE_NAME).read_text(encoding="utf-8"))
            self.assertEqual((req["text"], req["src"], req["tgt"]), ("你好", "zh", "id"))
            line = json.dumps({"type": "pcg_reply", "id": req["id"], "ok": True, "text": "Halo"})
            self.assertTrue(desk.on_event(line))                 # 收下，不轉給看字幕的人
            self.assertFalse(desk.on_event('{"type": "transcription", "src_text": "x"}'))
            return await task
        ev = asyncio.run(run())
        self.assertEqual(ev["text"], "Halo")
        self.assertFalse((base / reply.FILE_NAME).exists())      # 用完就刪掉

    def test_no_answer_times_out(self):
        desk = reply.Desk(Path(tempfile.mkdtemp()))
        ev = asyncio.run(desk.ask("你好", "zh", "id", timeout=0.2))
        self.assertEqual(ev, {"ok": False, "code": "say_timeout"})


if __name__ == "__main__":
    unittest.main()
