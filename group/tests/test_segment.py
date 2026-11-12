"""集團版 r21：依停頓切句＋句子合併、重複迴圈處理（不需要模型，VAD 用假的）。

執行（在專案根目錄）：
    python3 -m unittest group/tests/test_segment.py -v
"""
import sys
import types
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
for _name in ("ctranslate2", "sentencepiece"):
    sys.modules.setdefault(_name, types.ModuleType(_name))
sys.argv = [sys.argv[0]]
import translate_meeting as t  # noqa: E402

SR = t._SEG_SR


def energy_vad(audio):
    """假的 VAD：振幅 > 0.05 的連續區段就是講話（中間短於 0.3 秒的空白算同一段）"""
    on = np.abs(audio) > 0.05
    spans, start, last = [], None, None
    for i in range(0, len(audio), 160):
        if on[i:i + 160].any():
            if start is None:
                start = i
            last = i + 160
        elif start is not None and i - last >= int(0.3 * SR):
            spans.append((start, last))
            start = None
    if start is not None:
        spans.append((start, last))
    return spans


def tone(sec):
    return (0.3 * np.sin(np.arange(int(sec * SR)) / 5.0)).astype(np.float32)


def sil(sec):
    return np.zeros(int(sec * SR), np.float32)


def feed(seg, audio, block=0.1):
    out = []
    n = int(block * SR)
    for i in range(0, len(audio), n):
        seg.push(audio[i:i + n])
        out += seg.poll()
    return out


class Segmenter(unittest.TestCase):
    def test_cuts_at_pause_and_keeps_whole_phrase(self):
        seg = t._PcgSegmenter(vad_fn=energy_vad)
        out = feed(seg, np.concatenate([sil(0.5), tone(2.0), sil(0.2), tone(1.0), sil(1.2), tone(1.5), sil(1.2)]))
        self.assertEqual(len(out), 2)                       # 0.2 秒的換氣不切；1.2 秒的停頓才切
        a, forced, pause = out[0]
        self.assertFalse(forced)
        self.assertGreaterEqual(pause, 0.6)
        self.assertAlmostEqual(len(a) / SR, 3.2 + 1.0, delta=0.4)   # 整句（含前後 0.5 秒）
        self.assertAlmostEqual(len(out[1][0]) / SR, 1.5 + 1.0, delta=0.4)

    def test_forced_cut_when_nobody_pauses(self):
        seg = t._PcgSegmenter(vad_fn=energy_vad, chunk=8.0)
        out = feed(seg, np.concatenate([sil(0.3), tone(20.0)]))
        self.assertGreaterEqual(len(out), 2)
        self.assertTrue(all(f for _, f, _ in out))
        self.assertTrue(all(len(a) / SR <= 9.0 for a, _, _ in out))

    def test_silence_only_never_grows(self):
        seg = t._PcgSegmenter(vad_fn=energy_vad)
        self.assertEqual(feed(seg, sil(30)), [])
        self.assertLessEqual(len(seg.buf), SR)              # 只留一點尾巴，不會一直長

    def test_reset_drops_pending_audio(self):
        seg = t._PcgSegmenter(vad_fn=energy_vad)
        feed(seg, tone(2.0))
        seg.reset()
        self.assertEqual(len(seg.buf), 0)
        self.assertEqual(feed(seg, sil(1.5)), [])

    def test_resample_to_16k(self):
        self.assertEqual(len(t._pcg_to_16k(np.ones(4800, np.float32), 48000)), 1600)
        self.assertEqual(len(t._pcg_to_16k(np.ones(4410, np.float32), 44100)), 1600)
        self.assertEqual(len(t._pcg_to_16k(np.ones(1600, np.float32), 16000)), 1600)
        self.assertEqual(t._pcg_to_16k(np.ones(4800, np.float32), 48000).dtype, np.float32)


class Merger(unittest.TestCase):
    def test_sentence_end_releases_at_once(self):
        m = t._PcgSentenceMerger()
        self.assertEqual(m.add("We will check the stock.", "en", 0.0), [("We will check the stock.", "en", False)])

    def test_half_sentences_are_joined(self):
        m = t._PcgSentenceMerger()
        self.assertEqual(m.add("Kami akan memeriksa", "id", 0.0, pause=0.6), [])
        self.assertEqual(m.add("stok besok pagi.", "id", 1.0), [("Kami akan memeriksa stok besok pagi.", "id", False)])

    def test_pause_or_timeout_releases(self):
        m = t._PcgSentenceMerger(max_wait=3.0)
        self.assertEqual(m.add("chúng ta sẽ kiểm tra", "vi", 0.0, pause=1.0), [("chúng ta sẽ kiểm tra", "vi", True)])
        self.assertEqual(m.add("明天早上檢查庫存", "zh", 10.0, pause=0.6), [])
        self.assertEqual(m.due(12.0), [])
        self.assertEqual(m.due(13.1), [("明天早上檢查庫存", "zh", True)])

    def test_chinese_joined_without_space_korean_with_space(self):
        m = t._PcgSentenceMerger()
        m.add("明天早上", "zh", 0.0)
        self.assertEqual(m.add("檢查庫存。", "zh", 0.5), [("明天早上檢查庫存。", "zh", False)])
        m.add("내일 아침에", "ko", 1.0)
        self.assertEqual(m.add("재고를 확인합니다.", "ko", 1.5), [("내일 아침에 재고를 확인합니다.", "ko", False)])

    def test_hindi_danda_ends_a_sentence(self):
        m = t._PcgSentenceMerger()
        self.assertEqual(m.add("हम कल स्टॉक देखेंगे। और", "hi", 0.0), [("हम कल स्टॉक देखेंगे।", "hi", False)])
        self.assertEqual(m.flush(), [("और", "hi", True)])

    def test_language_change_flushes(self):
        m = t._PcgSentenceMerger()
        m.add("明天早上", "zh", 0.0)
        self.assertEqual(m.add("Besok pagi.", "id", 0.5), [("明天早上", "zh", True), ("Besok pagi.", "id", False)])

    def test_forced_cut_overlap_and_ellipsis(self):
        m = t._PcgSentenceMerger()
        self.assertEqual(m.add("we need to check the...", "en", 0.0, forced_cut=True), [])
        self.assertEqual(m.add("the inventory today.", "en", 1.0), [("we need to check the inventory today.", "en", False)])

    def test_abbreviation_is_not_an_end(self):
        m = t._PcgSentenceMerger()
        self.assertEqual(m.add("Please call Mr.", "en", 0.0), [])
        self.assertEqual(m.add("Tan tomorrow.", "en", 0.5), [("Please call Mr. Tan tomorrow.", "en", False)])

    def test_long_text_is_released(self):
        m = t._PcgSentenceMerger(max_words=10)
        out = m.add(" ".join(["kata"] * 12), "id", 0.0)
        self.assertEqual(len(out), 1)
        self.assertTrue(out[0][2])


class Repeats(unittest.TestCase):
    def test_collapse_word_loops(self):
        self.assertEqual(t._pcg_collapse_repeats("thank you thank you thank you thank you"), "thank you")
        self.assertEqual(t._pcg_collapse_repeats("ok ok ok ok ok"), "ok")
        self.assertEqual(t._pcg_collapse_repeats("ya ya ya kita mulai"), "ya ya ya kita mulai")   # 正常說話

    def test_collapse_cjk_char_loops(self):
        self.assertEqual(t._pcg_collapse_repeats("我們明天開會我們明天開會我們明天開會"), "我們明天開會")
        self.assertEqual(t._pcg_collapse_repeats("哈哈哈"), "哈哈哈")

    def test_has_loop(self):
        self.assertTrue(t._pcg_has_loop("A B C " * 6))
        self.assertFalse(t._pcg_has_loop("We will check the inventory tomorrow morning."))
        self.assertFalse(t._pcg_has_loop(""))


if __name__ == "__main__":
    unittest.main()
