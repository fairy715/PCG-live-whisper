"""辨識模型比較（group/bench_asr.py）：文字整理、錯字率、聲音讀取、報表。資料集與模型在 GitHub 上跑，這裡不下載"""
import io
import sys
import unittest
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from group import bench_asr as b  # noqa: E402


class Text(unittest.TestCase):
    def test_chinese_is_compared_by_character_ignoring_script_and_punctuation(self):
        self.assertEqual(b.tokens("大家好，今天開會。", "zh"), b.tokens("大家好 今天开会", "zh"))
        self.assertEqual(len(b.tokens("今天開會", "zh")), 4)

    def test_other_languages_are_compared_by_word(self):
        self.assertEqual(b.tokens("Selamat pagi, semuanya!", "id"), ["selamat", "pagi", "semuanya"])
        self.assertEqual(b.tokens("Hôm nay chúng ta họp.", "vi"), ["hôm", "nay", "chúng", "ta", "họp"])
        self.assertEqual(len(b.tokens("आज हम बैठक करेंगे।", "hi")), 4)            # 母音記號留在詞裡，句號不算
        self.assertEqual(b.tokens("It's 1.8 percent", "en"), ["it's", "1", "8", "percent"])

    def test_mixed_chinese_english(self):
        self.assertEqual(b.tokens("先請 QC 報告 IPQC 的不良率", "zh-en"),
                         ["先", "请", "qc", "报", "告", "ipqc", "的", "不", "良", "率"])

    def test_spelled_out_abbreviations_are_one_word(self):
        self.assertEqual(b.tokens("我专业是 i s m information systems", "zh-en"), b.tokens("我專業是ISM Information Systems", "zh-en"))
        self.assertEqual(b.tokens("a b c", "en"), ["abc"])
        self.assertEqual(b.tokens("I am a student", "en"), ["i", "am", "a", "student"])       # 中間隔著別的詞：不併

    def test_error_rate(self):
        self.assertEqual(b.edit_distance(list("abc"), list("abc")), 0)
        self.assertEqual(b.edit_distance(list("abc"), list("axc")), 1)
        self.assertEqual(b.edit_distance(list("abc"), list("ac")), 1)
        self.assertEqual(b.edit_distance([], list("ab")), 2)
        rate, err, total = b.error_rate([("今天開會", "今天开会"), ("大家早安", "大家晚安")], "zh")
        self.assertEqual((rate, err, total), (12.5, 1, 8))
        rate, err, total = b.error_rate([("selamat pagi semuanya", "selamat pagi"), ("", "x")], "id")
        self.assertEqual((err, total), (1, 3))                                   # 沒有標準答案的那一句不算
        self.assertEqual(b.error_rate([], "id")[0], None)


class Audio(unittest.TestCase):
    def wav(self, sr, ch, seconds=0.5):
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(ch)
            w.setsampwidth(2)
            w.setframerate(sr)
            w.writeframes((np.sin(np.arange(int(sr * seconds) * ch) / 9.0) * 8000).astype("<i2").tobytes())
        return buf.getvalue()

    def test_wav_is_read_as_16k_mono(self):
        a = b.wav_to_16k(self.wav(16000, 1))
        self.assertEqual((a.dtype, len(a)), (np.float32, 8000))
        self.assertEqual(len(b.wav_to_16k(self.wav(48000, 2))), 8000)             # 重新取樣、兩聲道混成一聲道
        self.assertLessEqual(float(np.abs(a).max()), 1.0)


class Report(unittest.TestCase):
    def test_report_sorts_by_error_rate_and_lists_skipped(self):
        res = {"n": 2, "skipped": ["x 載入失敗"], "sets": {"id": {"count": 2, "seconds": 10.0, "rows": [
            {"id": "a", "name": "模型甲", "rate": 20.0, "err": 2, "total": 10, "rtf": 0.5},
            {"id": "b", "name": "模型乙", "rate": 5.0, "err": 1, "total": 20, "rtf": 1.5}]}, "vi": {"count": 0, "seconds": 0, "rows": []}}}
        md = b.report_md(res)
        self.assertLess(md.index("模型乙"), md.index("模型甲"))
        self.assertIn("沒有跑成的", md)
        self.assertNotIn("越南文", md)                                           # 沒有結果的語言不列

    def test_every_pack_model_exists_in_the_pack_builder(self):
        from group import build_model_packs as bp
        ids = {p["id"] for p in bp.PACKS}
        for m in b.MODELS:
            if m.get("pack"):
                self.assertIn(m["pack"], ids, m["id"])


if __name__ == "__main__":
    unittest.main()
