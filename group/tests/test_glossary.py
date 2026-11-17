"""集團版 r23：詞庫（專有名詞的辨識提示、聽錯修正、指定譯法）。

執行（在專案根目錄）：
    python3 -m unittest group/tests/test_glossary.py -v
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
from group import glossary as g, simple_routes  # noqa: E402

TEXT = """# 測試用
寶成 | 寶城 | 保成 = Pou Chen
Sukabumi | Suka Bumi
MES
ME
IPQC
"""


class Parse(unittest.TestCase):
    def test_lines(self):
        es = g.parse(TEXT)
        self.assertEqual([e.src for e in es], ["寶成", "Sukabumi", "MES", "ME", "IPQC"])
        self.assertEqual((es[0].aliases, es[0].dst), (("寶城", "保成"), "Pou Chen"))
        self.assertEqual((es[1].aliases, es[1].dst), (("Suka Bumi",), ""))

    def test_excel_paste_and_duplicates(self):
        es = g.parse("裕元\tYue Yuen\t玉元\nMES\nmes\n \n=x\n")
        self.assertEqual([(e.src, e.dst, e.aliases) for e in es], [("裕元", "Yue Yuen", ("玉元",)), ("MES", "", ())])

    def test_limits(self):
        self.assertEqual(len(g.parse("\n".join(f"w{i}" for i in range(2000)))), g.MAX_ENTRIES)
        self.assertLessEqual(len(g.parse("x" * 500)[0].src), g.MAX_TERM)
        big = g.Glossary(g.parse("\n".join(f"term{i:04d}" for i in range(400))))
        self.assertLessEqual(len(big.hotwords()), g.HOT_MAX_CHARS)
        self.assertLessEqual(big.hotwords().count(",") + 1, g.HOT_MAX_TERMS)


class Use(unittest.TestCase):
    def setUp(self):
        self.G = g.Glossary(g.parse(TEXT))

    def test_hotwords(self):
        self.assertEqual(self.G.hotwords(), "寶成, Sukabumi, MES, ME, IPQC")
        self.assertEqual(g.Glossary().hotwords(), "")
        self.assertFalse(g.Glossary())

    def test_fix_misheard(self):
        self.assertEqual(self.G.fix("我們在寶城和 suka bumi 開會"), "我們在寶成和 Sukabumi 開會")
        self.assertEqual(self.G.fix("give me the times"), "give me the times")       # 沒有別名的詞不動

    def test_word_boundaries_and_case(self):
        pairs, keep = self.G.terms_for("give me ten times, the MES is down", "zh")
        self.assertEqual((pairs, keep), ([], ["MES"]))            # me、times 不算；MES 要完整的字
        self.assertEqual(self.G.terms_for("the mes is down", "zh")[1], [])       # 3 個字母以內要大小寫一樣
        self.assertEqual(self.G.terms_for("pabrik sukabumi", "zh")[1], ["Sukabumi"])   # 長的不分大小寫

    def test_terms_for_llm(self):
        self.assertEqual(self.G.terms_for("寶成的 IPQC", "id"), ([("寶成", "Pou Chen")], ["IPQC"]))
        self.assertEqual(self.G.terms_for("Pou Chen punya IPQC", "zh"), ([("Pou Chen", "寶成")], ["IPQC"]))
        self.assertEqual(self.G.terms_for("Pou Chen punya IPQC", "vi"), ([], ["IPQC"]))
        self.assertEqual(self.G.terms_for("今天天氣很好", "id"), ([], []))

    def test_substitute_for_local_mt(self):
        self.assertEqual(self.G.substitute("寶成的 MES 系統", "id"), "Pou Chen的 MES 系統")
        self.assertEqual(self.G.substitute("Pou Chen uses MES", "zh"), "寶成 uses MES")
        self.assertEqual(self.G.substitute("Pou Chen uses MES", "vi"), "Pou Chen uses MES")

    def test_only_terms_is_a_leaked_prompt(self):
        self.assertTrue(self.G.only_terms("寶成, Sukabumi, MES"))
        self.assertFalse(self.G.only_terms("寶成的 MES"))
        self.assertFalse(self.G.only_terms("MES"))
        self.assertFalse(self.G.only_terms(""))


class Engine(unittest.TestCase):
    def setUp(self):
        self.saved = t._PCG_GLOSS[0]
        t._PCG_GLOSS[0] = g.Glossary(g.parse(TEXT))

    def tearDown(self):
        t._PCG_GLOSS[0] = self.saved
        t._PCG_GLOSS_HOTWORDS_OK[0] = True

    def model(self, fn):
        m = t._FwModel.__new__(t._FwModel)
        m._kw, m._m = {"device": "cpu"}, types.SimpleNamespace(transcribe=fn)
        return m

    def test_hotwords_passed_and_segments_fixed(self):
        import dataclasses
        Seg = dataclasses.make_dataclass("Seg", [("text", str)])
        seen = []

        def fake(audio, **kw):
            seen.append(kw)
            return iter([Seg("我們在寶城"), Seg("寶成, Sukabumi, MES"), Seg("開會")]), "info"
        segs, info = self.model(fake).transcribe("a", language="zh", beam_size=5)
        self.assertEqual(seen[0]["hotwords"], "寶成, Sukabumi, MES, ME, IPQC")
        self.assertEqual([x.text for x in segs], ["我們在寶成", "開會"])      # 修正聽錯的；照抄提示詞的那段丟掉
        self.assertEqual(info, "info")

    def test_no_hotwords_for_language_detection_or_empty_glossary(self):
        seen = []

        def fake(audio, **kw):
            seen.append(kw)
            return iter([]), None
        self.model(fake).transcribe("a", language=None, vad_filter=True)
        t._PCG_GLOSS[0] = ()
        self.model(fake).transcribe("a", language="zh")
        self.assertEqual([("hotwords" in k) for k in seen], [False, False])

    def test_old_faster_whisper_without_hotwords(self):
        calls = []

        def fake(audio, **kw):
            calls.append(kw)
            if "hotwords" in kw:
                raise TypeError("transcribe() got an unexpected keyword argument 'hotwords'")
            return iter([]), None
        self.model(fake).transcribe("a", language="zh")
        self.model(fake).transcribe("a", language="zh")
        self.assertEqual([("hotwords" in k) for k in calls], [True, False, False])   # 試一次，之後不再帶

    def test_prompt_for_llm_and_local_mt(self):
        p = t._pcg_gloss_prompt("寶成的 IPQC 報告", "zh2id")
        self.assertIn("寶成 → Pou Chen", p)
        self.assertIn("IPQC", p)
        self.assertEqual(t._pcg_gloss_prompt("今天天氣很好", "zh2id"), "")
        self.assertEqual(t._pcg_gloss_sub("寶成的 MES", "zh2vi"), "Pou Chen的 MES")
        self.assertEqual((t._pcg_gloss_tgt("en2zh"), t._pcg_gloss_tgt("nan2en"), t._pcg_gloss_tgt("zh")), ("zh", "en", "zh"))


class Sync(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp())
        self.share = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.base, ignore_errors=True)
        shutil.rmtree(self.share, ignore_errors=True)

    def out(self):
        p = self.base / "group_data" / "glossary.txt"
        return p.read_text(encoding="utf-8") if p.exists() else None

    def test_local_and_share_are_merged_local_first(self):
        (self.share / "glossary.txt").write_text("MES = 製造執行系統\n裕元\n", encoding="utf-8")
        r = g.sync(self.base, {"glossary": "MES\n寶成", "update_share": str(self.share)})
        self.assertEqual(r, {"count": 3, "share_count": 2})
        es = g.load(self.base / "group_data" / "glossary.txt").entries
        self.assertEqual([(e.src, e.dst) for e in es], [("MES", ""), ("寶成", ""), ("裕元", "")])

    def test_share_unreachable_uses_last_copy(self):
        (self.share / "glossary.txt").write_text("裕元\n", encoding="utf-8")
        g.sync(self.base, {"update_share": str(self.share)})
        shutil.rmtree(self.share)
        self.assertEqual(g.sync(self.base, {"update_share": str(self.share)})["share_count"], 1)
        self.assertIn("裕元", self.out())

    def test_empty_removes_file(self):
        g.sync(self.base, {"glossary": "MES"})
        self.assertIn("MES", self.out())
        g.sync(self.base, {})
        self.assertIsNone(self.out())


class Routes(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp())
        (self.base / "translate_meeting.py").write_text('APP_VERSION = "2.99"\n', encoding="utf-8")
        (self.base / "group_data").mkdir()
        self.cfg = self.base / "config.json"
        self.cfg.write_text(json.dumps({"pcg_simple": {"it_password_hash": "h:itpass1"}}), encoding="utf-8")
        app = FastAPI()
        simple_routes.register(
            app, self.base, lambda r: True, lambda raw: "h:" + raw, lambda raw, h: h == "h:" + (raw or ""),
            self.cfg, lambda c: self.cfg.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8"),
            gpu_alive=lambda h, p: False, update_hooks={"github_fetch": self._off, "models_fetch": self._off})
        self.c = TestClient(app)
        self.h = {"X-IT-Token": "itpass1"}

    def tearDown(self):
        shutil.rmtree(self.base, ignore_errors=True)

    @staticmethod
    def _off(u):
        raise OSError("offline")

    def test_save_writes_file_for_the_engine(self):
        r = self.c.post("/api/simple/admin/save", headers=self.h, json={"backend": "local", "glossary": "寶成 | 寶城\r\nMES\r\n"})
        self.assertTrue(r.json()["ok"], r.text)
        st = r.json()["state"]
        self.assertEqual((st["glossary"], st["glossary_info"]["local"]), ("寶成 | 寶城\nMES", 2))
        self.assertEqual([e.src for e in g.load(self.base / "group_data" / "glossary.txt").entries], ["寶成", "MES"])
        r = self.c.post("/api/simple/admin/save", headers=self.h, json={"backend": "local", "glossary": ""})
        self.assertEqual(r.json()["state"]["glossary"], "")
        self.assertFalse((self.base / "group_data" / "glossary.txt").exists())

    def test_too_long_is_rejected_and_needs_it_password(self):
        r = self.c.post("/api/simple/admin/save", headers=self.h, json={"backend": "local", "glossary": "x" * 20001})
        self.assertEqual((r.status_code, r.json()["code"]), (400, "bad_glossary"))
        r = self.c.post("/api/simple/admin/save", headers={"X-IT-Token": "wrong"}, json={"backend": "local", "glossary": "MES"})
        self.assertFalse(r.json().get("ok"))


if __name__ == "__main__":
    unittest.main()
