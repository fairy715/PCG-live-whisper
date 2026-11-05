"""集團版：印尼文（id）、越南文（vi）、印地語（hi）模式的檢查。

不需要安裝 AI 模型或 GPU：ctranslate2、sentencepiece 用假模組代替，只檢查程式邏輯。
執行（在專案根目錄）：
    python3 -m unittest group/tests/test_xlangs.py -v
"""
import os
import sys
import types
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
for _name in ("ctranslate2", "sentencepiece"):
    sys.modules.setdefault(_name, types.ModuleType(_name))
sys.argv = [sys.argv[0]]

import translate_meeting as t  # noqa: E402

LANGS = ("id", "vi", "hi")
NEW_MODES = [m for L in LANGS for m in (f"{L}2zh", f"zh2{L}", f"{L}_zh", L, f"{L}2en", f"en2{L}")]


class ModeTables(unittest.TestCase):
    def test_all_modes_in_presets_and_cli(self):
        keys = [k for k, _, _ in t.MODE_PRESETS]
        for m in NEW_MODES:
            self.assertIn(m, keys)
            self.assertIn(m, t.MODE_MAP)
        self.assertEqual(len(keys), len(set(keys)), "模式代號重複")
        self.assertEqual(keys[-1], "record", "純錄音要維持在最後")

    def test_every_mode_has_labels_and_langs(self):
        # 上游的雙向與離線流程直接用 dict[mode] 取值，少一個就 KeyError
        for m in NEW_MODES:
            self.assertIn(m, t._MODE_LABELS)
            self.assertIn(m, t._BIDI_LABELS)
            self.assertIn(m, t._LB_LANG)
            self.assertIn(m, t._MIC_LANG)

    def test_whisper_language(self):
        for L in LANGS:
            self.assertEqual(t._mode_whisper_lang(f"{L}2zh"), L)
            self.assertEqual(t._mode_whisper_lang(L), L)
            self.assertEqual(t._mode_whisper_lang(f"{L}2en"), L)
            self.assertEqual(t._mode_whisper_lang(f"zh2{L}"), "zh")
            self.assertEqual(t._mode_whisper_lang(f"en2{L}"), "en")

    def test_classification(self):
        for L in LANGS:
            self.assertIn(f"{L}_zh", t._BIDI_MODES)
            self.assertEqual(t._BIDI_LB_DIR[f"{L}_zh"], f"{L}2zh")
            self.assertEqual(t._BIDI_MIC_DIR[f"{L}_zh"], f"zh2{L}")
            self.assertNotIn(L, t._TRANSLATE_MODES)
            self.assertIn(L, t._TRANSCRIBE_ONLY_MODES)
            for m in (f"{L}2zh", f"zh2{L}", f"{L}2en", f"en2{L}"):
                self.assertIn(m, t._TRANSLATE_MODES)
                self.assertIn(m, t._ARGOS_UNSUPPORTED_MODES)
            # 只有「英翻 L」可以用 .en 模型（輸入是英文）
            self.assertNotIn(f"en2{L}", t._NOENG_MODELS)
            self.assertIn(f"{L}2zh", t._NOENG_MODELS)
        # 上游原本的模式不受影響
        self.assertEqual(t._mode_whisper_lang("ko2zh"), "ko")
        self.assertEqual(t._mode_whisper_lang("zh2en"), "zh")
        self.assertNotIn("en2zh", t._ARGOS_UNSUPPORTED_MODES)

    def test_names(self):
        self.assertEqual(t._xl_mode_name("id2zh"), "印尼翻中")
        self.assertEqual(t._xl_mode_name("zh2vi"), "中翻越")
        self.assertEqual(t._xl_mode_name("hi_zh"), "印地中雙向")
        self.assertEqual(t._xl_mode_name("hi"), "印地語")
        self.assertEqual(t._xl_mode_name("en2id"), "英翻印尼")
        self.assertIsNone(t._xl_mode_name("en2zh"))

    def test_summary_names(self):
        self.assertEqual(t._xl_summary_name("印尼翻中_時間逐字稿_會議_20261104.txt"), "印尼翻中_摘要_會議_20261104.txt")
        self.assertEqual(t._xl_summary_name("越中雙向_時間逐字稿_x.txt"), "越中雙向_摘要_x.txt")
        self.assertEqual(t._xl_summary_name("中翻印地_配對時間逐字稿_x.txt"), "中翻印地_配對摘要_x.txt")
        self.assertIsNone(t._xl_summary_name("英翻中_時間逐字稿_x.txt"))

    def test_nllb_directions(self):
        for L in LANGS:
            for d in (f"{L}2zh", f"zh2{L}", f"{L}2en", f"en2{L}"):
                src, tgt = t.NllbTranslator._DIRECTION_MAP[d]
                self.assertIn(src, t.NllbTranslator._LANG_MAP)
                self.assertIn(tgt, t.NllbTranslator._LANG_MAP)


def _translator(direction, topic=None):
    return t.OllamaTranslator("m", direction=direction, skip_check=True, meeting_topic=topic)


class Prompts(unittest.TestCase):
    def test_prompt_per_direction(self):
        cases = {
            "id2zh": "印尼文", "vi2zh": "越南文", "hi2zh": "印地語",
            "id2en": "Indonesian", "vi2en": "Vietnamese", "hi2en": "Hindi",
            "zh2id": "bahasa Indonesia", "en2id": "bahasa Inggris",
            "zh2vi": "tiếng Việt", "en2vi": "tiếng Anh",
            "zh2hi": "हिंदी", "en2hi": "अंग्रेज़ी",
        }
        for d, needle in cases.items():
            p = _translator(d, topic="ASICS 新廠").\
                _build_prompt("TEXT", [("a", "b")])
            self.assertIn(needle, p, d)
            self.assertIn("TEXT", p, d)
            self.assertIn("ASICS 新廠", p, d)
            # 不可以落到上游預設的「英翻中」提示詞
            self.assertNotIn("將英文翻譯成台灣繁體中文", p, d)

    def test_upstream_prompts_unchanged(self):
        p = _translator("en2zh")._build_prompt("Hello", [])
        self.assertIn("將英文翻譯成台灣繁體中文", p)
        p = _translator("zh2ko")._build_prompt("你好", [])
        self.assertIn("한국어", p)


class OutputChecks(unittest.TestCase):
    def bad(self, d, text):
        return _translator(d)._contains_bad_chars(text)

    def test_to_chinese(self):
        self.assertFalse(self.bad("id2zh", "我們明天開會"))
        self.assertTrue(self.bad("id2zh", "Kita rapat besok"))          # 模型把原文丟回來
        self.assertTrue(self.bad("hi2zh", "我們 कल 開會"))               # 夾帶天城文
        self.assertTrue(self.bad("vi2zh", "我們 ngày mai 開會"))          # 夾帶越南文
        self.assertFalse(self.bad("vi2zh", "OK"))

    def test_to_target(self):
        self.assertFalse(self.bad("zh2vi", "Chúng ta sẽ họp vào ngày mai"))
        self.assertTrue(self.bad("zh2vi", "我們明天開會"))
        self.assertFalse(self.bad("zh2hi", "हम कल बैठक करेंगे"))
        self.assertTrue(self.bad("zh2hi", "We will meet tomorrow"))     # 沒有天城文
        self.assertFalse(self.bad("en2id", "Kita akan rapat besok"))
        self.assertTrue(self.bad("en2id", "我們明天開會"))

    def test_to_english(self):
        self.assertFalse(self.bad("hi2en", "We will meet tomorrow"))
        self.assertTrue(self.bad("hi2en", "We will meet कल"))

    def test_length_ratio(self):
        # 中文很短，越南文、印尼文譯文常超過 4 倍，不能當成幻覺
        tr = _translator("zh2vi")
        self.assertFalse(tr._is_hallucinated("我們明天開會", "Chúng ta sẽ họp vào ngày mai", tr._ratio_limit()))
        self.assertEqual(_translator("en2zh")._ratio_limit(), 4)

    def test_prefix_strip(self):
        rx = t.OllamaTranslator._XL_PREFIX_RE
        self.assertEqual(rx.sub("", "Terjemahan: Kita rapat besok"), "Kita rapat besok")
        self.assertEqual(rx.sub("", "Bản dịch: Xin chào"), "Xin chào")


class Hallucinations(unittest.TestCase):
    def test_real_speech_passes(self):
        self.assertFalse(t._is_id_hallucination("Kita perlu cek stok bahan baku minggu ini"))
        self.assertFalse(t._is_vi_hallucination("Chúng ta cần kiểm tra tồn kho tuần này"))
        self.assertFalse(t._is_hi_hallucination("हमें इस हफ्ते कच्चे माल का स्टॉक जांचना है"))
        # 句中出現「謝謝」不擋
        self.assertFalse(t._is_id_hallucination("Terima kasih, sekarang kita lanjut ke agenda kedua"))

    def test_known_hallucinations_blocked(self):
        self.assertTrue(t._is_id_hallucination("Terima kasih telah menonton!"))
        self.assertTrue(t._is_id_hallucination("Terima kasih."))
        self.assertTrue(t._is_vi_hallucination("Hãy subscribe cho kênh Ghiền Mì Gõ Để không bỏ lỡ những video hấp dẫn"))
        self.assertTrue(t._is_hi_hallucination("धन्यवाद।"))
        self.assertTrue(t._is_hi_hallucination("चैनल को सब्सक्राइब करें"))
        self.assertTrue(t._is_vi_hallucination("a a a a a a a a"))

    def test_not_using_chinese_filter(self):
        # 上游加韓文時的坑：落到中文過濾會整句丟掉。這三種語言都要走自己的過濾
        for m in ("id2zh", "vi", "hi2en"):
            L = t._XL_MODE_LANG[m]
            self.assertIsNot(t._HALLU_BY_LANG[L], t._is_zh_hallucination)
        self.assertTrue(t._is_zh_hallucination("Kita perlu cek stok bahan baku"))  # 證明確實會被中文過濾丟掉

    def test_bidi_side_filters(self):
        self.assertIs(t._xl_hallu_for_mode("id_zh", "lb"), t._is_id_hallucination)
        self.assertIs(t._xl_hallu_for_mode("id_zh", "mic"), t._is_zh_hallucination)
        self.assertIs(t._xl_hallu_for_mode("en2hi", "lb"), t._is_en_hallucination)


class Summary(unittest.TestCase):
    def test_meeting_language_gate(self):
        ok, _ = t._meeting_language_ok([{"text": "हमें इस हफ्ते स्टॉक जांचना है"}] * 3)
        self.assertFalse(ok)
        ok, _ = t._meeting_language_ok([{"text": "Chúng ta cần kiểm tra tồn kho tuần này"}] * 3)
        self.assertFalse(ok)
        ok, _ = t._meeting_language_ok([{"text": "我們這週要檢查原料庫存"}] * 3)
        self.assertTrue(ok)

    def test_correction_guard(self):
        self.assertFalse(t._accept_correction("हम कल बैठक करेंगे", "We will meet tomorrow"))
        self.assertTrue(t._accept_correction("हम कल बैठक करेंगे", "हम कल बैठक करेंगे।"))
        self.assertFalse(t._accept_correction("Chúng ta sẽ họp vào ngày mai", "We will meet tomorrow"))



class OpenWebUI(unittest.TestCase):
    """集團的 AI 都經 Open WebUI：llm_api_style＝openwebui 時 OpenAI 相容路徑換成 /api/…"""

    def test_paths(self):
        h, p, err = t._parse_llm_host("https://ai.example.com")
        self.assertIsNone(err)
        os.environ["JTLW_LLM_API_STYLE"] = "openwebui"
        try:
            self.assertEqual(t._llm_url(h, p, "/v1/chat/completions"), "https://ai.example.com/api/chat/completions")
            self.assertEqual(t._llm_url(h, p, "/v1/models"), "https://ai.example.com/api/models")
        finally:
            os.environ.pop("JTLW_LLM_API_STYLE")
        os.environ["JTLW_LLM_API_STYLE"] = "auto"
        try:
            self.assertEqual(t._llm_url(h, p, "/v1/models"), "https://ai.example.com/v1/models")
        finally:
            os.environ.pop("JTLW_LLM_API_STYLE")

    def test_external_base_url(self):
        os.environ["JTLW_LLM_API_STYLE"] = "openai"
        try:
            for base, want in (("https://api.openai.com/v1", "https://api.openai.com/v1/chat/completions"),
                               ("https://generativelanguage.googleapis.com/v1beta/openai",
                                "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"),
                               ("https://openrouter.ai/api/v1", "https://openrouter.ai/api/v1/chat/completions")):
                h, p, err = t._parse_llm_host(base)
                self.assertIsNone(err)
                self.assertEqual(t._llm_url(h, p, "/v1/chat/completions"), want)
                self.assertEqual(t._llm_url(h, p, "/v1/models"), want.replace("chat/completions", "models"))
        finally:
            os.environ.pop("JTLW_LLM_API_STYLE")

    def test_gpu_server_without_ssh(self):
        """IT 設定頁只存位址（沒有 ssh_user）：GPU 服務沒回應時不可以去 SSH（同仁電腦沒有權限，以前會 KeyError）"""
        import unittest.mock as um
        with um.patch.object(t.subprocess, "run") as run:
            t._remote_whisper_start({"host": "127.0.0.1", "whisper_port": 1})
            run.assert_not_called()
            t._ssh_close_cm({"host": "127.0.0.1"})

if __name__ == "__main__":
    unittest.main()


class LocalM2M(unittest.TestCase):
    """本機離線翻譯 M2M100：有模型時 NllbTranslator 一律改用它；送進模型的 token 格式要對"""

    def setUp(self):
        import tempfile
        self.dir = tempfile.mkdtemp()
        open(os.path.join(self.dir, "sentencepiece.bpe.model"), "w").close()
        self.calls = []
        calls = self.calls

        class SP:
            def Load(self, p): pass
            def Encode(self, text, out_type=str): return ["▁" + w for w in text.split()]
            def Decode(self, toks): return "".join(toks).replace("▁", " ").strip()

        class CT2:
            def __init__(self, path, **kw): calls.append(("init", path, kw))
            def translate_batch(self, src, **kw):
                calls.append(("batch", src, kw))
                return [types.SimpleNamespace(hypotheses=[kw["target_prefix"][0] + ["我們", "明天", "开会"]])]

        self.saved = (t.LOCAL_MT_IS_M2M, t.M2M_MODEL_DIR, getattr(t.sentencepiece, "SentencePieceProcessor", None),
                      getattr(t.ctranslate2, "Translator", None))
        t.LOCAL_MT_IS_M2M, t.M2M_MODEL_DIR = True, self.dir
        t.sentencepiece.SentencePieceProcessor = SP
        t.ctranslate2.Translator = CT2

    def tearDown(self):
        t.LOCAL_MT_IS_M2M, t.M2M_MODEL_DIR, sp, ct = self.saved
        t.sentencepiece.SentencePieceProcessor = sp
        t.ctranslate2.Translator = ct

    def test_redirect_and_tokens(self):
        tr = t.NllbTranslator(direction="id2zh")
        self.assertIsInstance(tr, t.M2M100Translator)
        self.assertEqual(tr.LABEL, "M2M100")
        out = tr.translate("Kita rapat besok")
        _, src, kw = next(c for c in self.calls if c[0] == "batch")
        self.assertEqual(src, [["__id__", "▁Kita", "▁rapat", "▁besok", "</s>"]])
        self.assertEqual(kw["target_prefix"], [["__zh__"]])
        self.assertEqual(kw["beam_size"], 2)
        _, path, ikw = next(c for c in self.calls if c[0] == "init")
        self.assertEqual((path, ikw["device"], ikw["compute_type"]), (self.dir, "cpu", "int8"))
        self.assertEqual(out, "我們明天開會")      # 去掉語言代碼、簡轉繁（M2M100 的中文多半是簡體）
        self.assertNotIn("__zh__", out)

    def test_all_new_directions_have_codes(self):
        for L in LANGS:
            for d in (f"{L}2zh", f"zh2{L}", f"{L}2en", f"en2{L}"):
                src, tgt = t.M2M100Translator._DIRECTION_MAP[d]
                self.assertIn(src, t.M2M100Translator._LANG_MAP)
                self.assertIn(tgt, t.M2M100Translator._LANG_MAP)

    def test_upstream_nllb_untouched_without_m2m(self):
        t.LOCAL_MT_IS_M2M = False
        self.assertIs(type(t.NllbTranslator.__new__(t.NllbTranslator)), t.NllbTranslator)
