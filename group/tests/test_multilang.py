"""集團版 r19 多語字幕：看字幕的人選的語言 → 主程式另外翻譯（transcription_extra）。

不需要 AI 模型：翻譯器用假的代替，只檢查流程。
執行（在專案根目錄）：
    python3 -m unittest group/tests/test_multilang.py -v
"""
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
from group import multilang  # noqa: E402


class FakeTr:
    def __init__(self, direction):
        self.direction = direction

    def translate(self, text):
        return f"[{self.direction}] {text}"


class Extra(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.flag = os.path.join(self.dir, ".extra_langs")
        self._old = (t._PCG_XT_FLAG, t._webui_queue, t._pcg_extra)
        t._PCG_XT_FLAG = self.flag
        t._webui_queue = queue.Queue()
        t._pcg_extra = t._PcgExtraSubs()
        t._pcg_extra.enabled = True
        self.made = []

        def fake_translator(direction):
            self.made.append(direction)
            return FakeTr(direction)
        t._pcg_extra.translator = fake_translator

    def tearDown(self):
        t._PCG_XT_FLAG, t._webui_queue, t._pcg_extra = self._old

    def want(self, text):
        Path(self.flag).write_text(text, encoding="utf-8")
        t._pcg_extra.checked = 0

    def send(self, **ev):
        t._webui_send({"type": "transcription", "source": "main", **ev})

    def drain(self, n, timeout=3):
        out, end = [], time.time() + timeout
        while len(out) < n and time.time() < end:
            try:
                out.append(t._webui_queue.get(timeout=0.1))
            except queue.Empty:
                pass
        return out

    def test_translates_only_missing_wanted_languages(self):
        self.want("vi id hi xx")
        self.send(src_lang="中", src_text="設備要先關電源", dst_lang="ID", dst_text="Matikan listrik")
        evs = self.drain(3)
        main = [e for e in evs if e["type"] == "transcription"][0]
        extra = sorted((e for e in evs if e["type"] == "transcription_extra"), key=lambda e: e["lang_code"])
        self.assertEqual([e["lang_code"] for e in extra], ["hi", "vi"])        # 印尼文這句已經有了
        self.assertTrue(all(e["id"] == main["id"] for e in extra))             # 對回同一句
        self.assertEqual(extra[1]["text"], "[zh2vi] 設備要先關電源")
        self.assertEqual(extra[1]["lang"], "VI")
        self.assertEqual(set(self.made), {"zh2hi", "zh2vi"})

    def test_nobody_wants_nothing_translated(self):
        self.send(src_lang="中", src_text="你好", dst_lang="ID", dst_text="Halo")
        evs = self.drain(2, timeout=0.5)
        self.assertEqual([e["type"] for e in evs], ["transcription"])
        self.assertIn("id", evs[0])
        self.assertIsNone(t._pcg_extra.pool)

    def test_ids_increase(self):
        self.send(src_lang="中", src_text="一")
        self.send(src_lang="中", src_text="二")
        a, b = self.drain(2)
        self.assertEqual(b["id"], a["id"] + 1)

    def test_switch_off(self):
        self.want("vi")
        t._pcg_extra.enabled = False
        self.send(src_lang="中", src_text="你好")
        self.assertEqual([e["type"] for e in self.drain(2, timeout=0.5)], ["transcription"])

    def test_unsupported_direction_skipped(self):
        self.want("vi")
        self.send(src_lang="日", src_text="こんにちは", dst_lang="中", dst_text="你好")   # ja2vi 沒有
        self.assertEqual([e["type"] for e in self.drain(2, timeout=0.5)], ["transcription"])

    def test_foreign_pair_and_transcribe_only(self):
        self.want("zh")
        self.send(src_lang="VI", src_text="Xin chào", dst_lang="ID", dst_text="Halo")      # 外語對外語的場次
        self.send(src_lang="EN", src_text="Hello")                                         # 只轉錄
        extra = [e for e in self.drain(4) if e["type"] == "transcription_extra"]
        self.assertEqual(sorted(e["text"] for e in extra), ["[en2zh] Hello", "[vi2zh] Xin chào"])

    def test_local_model_translates_all_languages_in_one_call(self):
        """本機 M2M100：同一句的幾種語言一次翻（translate_multi），不是一種一種"""
        calls = []

        class Multi:
            def translate_multi(self, text, langs):
                calls.append(list(langs))
                return {L: f"<{L}> {text}" for L in langs}
        t._pcg_extra.translator = lambda d: Multi()
        self.want("vi hi en")
        self.send(src_lang="中", src_text="你好", dst_lang="ID", dst_text="Halo")
        extra = [e for e in self.drain(4) if e["type"] == "transcription_extra"]
        self.assertEqual(calls, [["en", "hi", "vi"]])
        self.assertEqual(sorted(e["text"] for e in extra), ["<en> 你好", "<hi> 你好", "<vi> 你好"])

    def test_llm_keeps_one_request_per_language(self):
        old = t._pcg_tr_note["tr"]
        try:
            t._pcg_tr_note["tr"] = t.OllamaTranslator("m", direction="zh2id", skip_check=True)
            self.want("vi hi")
            self.send(src_lang="中", src_text="你好", dst_lang="ID", dst_text="Halo")
            self.drain(3)
            self.assertEqual(sorted(self.made), ["zh2hi", "zh2vi"])
        finally:
            t._pcg_tr_note["tr"] = old

    def test_translation_failure_is_quiet(self):
        self.want("vi")

        def broken(direction):
            raise RuntimeError("boom")
        t._pcg_extra.translator = broken
        self.send(src_lang="中", src_text="你好")
        self.assertEqual([e["type"] for e in self.drain(2, timeout=0.5)], ["transcription"])


class BatchM2M(unittest.TestCase):
    """M2M100 的批次翻譯：同一段原文、每一筆帶自己的目標語言代碼，一次 translate_batch"""

    def test_one_batch_with_target_prefixes(self):
        calls = []

        class SP:
            def Encode(self, text, out_type=str): return ["▁" + w for w in text.split()]
            def Decode(self, toks): return " ".join(toks).replace("▁", "").strip()

        class CT2:
            def translate_batch(self, src, **kw):
                calls.append((src, kw["target_prefix"]))
                return [types.SimpleNamespace(hypotheses=[p + ["X" + p[0].strip("_")]]) for p in kw["target_prefix"]]

        tr = t.M2M100Translator.__new__(t.M2M100Translator)
        tr.sp, tr.ct2, tr.src_lang, tr.direction = SP(), CT2(), "__zh__", "zh2vi"
        out = tr.translate_multi("我們 明天 開會", ["vi", "hi", "zh", "ja", "xx"])
        self.assertEqual(len(calls), 1)                                   # 一次就好
        src, prefixes = calls[0]
        self.assertEqual(prefixes, [["__vi__"], ["__hi__"], ["__zh__"], ["__ja__"]])   # 不認得的語言略過
        self.assertTrue(all(x == ["__zh__", "▁我們", "▁明天", "▁開會", "</s>"] for x in src))
        self.assertEqual(out["vi"], "Xvi")
        self.assertEqual(set(out), {"vi", "hi", "zh", "ja"})
        self.assertEqual(tr.translate_multi("", ["vi"]), {})


class Translators(unittest.TestCase):
    def test_note_ignores_extra_translators(self):
        old = t._pcg_tr_note["tr"]
        try:
            t._pcg_tr_note["tr"] = "main"
            t._pcg_tr_note["building"] = True
            t._pcg_note_translator("extra")
            self.assertEqual(t._pcg_tr_note["tr"], "main")
            t._pcg_tr_note["building"] = False
            t._pcg_note_translator("other")
            self.assertEqual(t._pcg_tr_note["tr"], "other")
        finally:
            t._pcg_tr_note["tr"] = old
            t._pcg_tr_note["building"] = False

    def test_same_kind_as_main_translator(self):
        x = t._PcgExtraSubs()
        old = t._pcg_tr_note["tr"]
        try:
            t._pcg_tr_note["tr"] = t.OllamaTranslator("luna", "10.0.0.5", 11434, direction="zh2id", skip_check=True,
                                                      server_type="openai", meeting_topic="ASICS")
            tr = x.translator("zh2vi")
            self.assertIsInstance(tr, t.OllamaTranslator)
            self.assertEqual((tr.model, tr.host, tr.direction, tr.meeting_topic), ("luna", "10.0.0.5", "zh2vi", "ASICS"))
            self.assertIs(x.translator("zh2vi"), tr)                                   # 建好就留著
            self.assertEqual(t._pcg_tr_note["tr"].direction, "zh2id")                  # 主程式的不被蓋掉
        finally:
            t._pcg_tr_note["tr"] = old


class Wants(unittest.TestCase):
    def test_union_and_drop(self):
        d = Path(tempfile.mkdtemp())
        flag = d / ".extra_langs"
        flag.write_text("hi", encoding="utf-8")
        w = multilang.Wants(flag)
        self.assertFalse(flag.exists())                        # 啟動時清掉上一次留下的
        a, b, c = object(), object(), object()
        w.set(a, "vi")
        w.set(b, "id")
        w.set(c, "vi")
        self.assertEqual(flag.read_text(encoding="utf-8"), "id vi")
        w.set(b, "ja")                                         # 不支援的語言：當作沒選
        self.assertEqual(w.current(), ["vi"])
        w.drop(a)
        self.assertEqual(flag.read_text(encoding="utf-8"), "vi")
        w.drop(c)
        self.assertFalse(flag.exists())

    def test_webui_hooks(self):
        src = (ROOT / "webui.py").read_text(encoding="utf-8")
        self.assertIn('msg.get("action") == "want_lang"', src)
        self.assertIn("_pcg_wants.drop(ws)", src)
        self.assertIn('_pcg_multilang.Wants(BASE_DIR / ".extra_langs")', src)


if __name__ == "__main__":
    unittest.main()
