"""集團版 r21：依電腦規格自動選即時字幕的辨識模型。

執行（在專案根目錄）：
    python3 -m unittest group/tests/test_hwtier.py -v
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from group import hwtier, simple_routes  # noqa: E402


def pick(phys, logical, gpu=False, packs=()):
    return hwtier.pick("x", hw={"physical": phys, "logical": logical, "gpu": gpu}, has_pack=lambda p: p in packs)


class Pick(unittest.TestCase):
    def test_two_core_laptop(self):
        r = pick(2, 4)                                     # i3-10110U：沒有 base 模型包
        self.assertEqual((r["model"], r["reason"], r["suggest"]), ("small", "weak", "whisper-base"))
        r = pick(2, 4, packs={"whisper-base"})
        self.assertEqual((r["model"], r["suggest"]), ("pack:whisper-base", ""))

    def test_normal_laptop_keeps_small(self):
        r = pick(4, 8, packs={"whisper-base", "whisper-medium"})
        self.assertEqual((r["model"], r["reason"], r["suggest"]), ("small", "normal", ""))

    def test_gpu_prefers_bigger_packs(self):
        self.assertEqual(pick(4, 8, gpu=True, packs={"whisper-medium", "whisper-large-v3-turbo"})["model"],
                         "pack:whisper-large-v3-turbo")
        self.assertEqual(pick(4, 8, gpu=True, packs={"whisper-medium"})["model"], "pack:whisper-medium")
        r = pick(2, 4, gpu=True)
        self.assertEqual((r["model"], r["reason"], r["suggest"]), ("small", "gpu", "whisper-large-v3-turbo"))

    def test_unknown_physical_cores(self):
        self.assertEqual(pick(None, 2)["reason"], "weak")
        self.assertEqual(pick(None, 4)["reason"], "normal")      # 非 Windows 查不到實體核心：4 執行緒不算弱


class GpuCheck(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp())
        (self.base / "group_data").mkdir()

    def tearDown(self):
        shutil.rmtree(self.base, ignore_errors=True)

    def test_needs_pack_and_passing_check(self):
        self.assertFalse(hwtier.gpu_ok(self.base))
        (self.base / "gpu").mkdir()
        self.assertFalse(hwtier.gpu_ok(self.base))               # 沒有檢查結果
        (self.base / "group_data" / "gpu_check.json").write_text(json.dumps({"ok": False}), encoding="utf-8")
        self.assertFalse(hwtier.gpu_ok(self.base))
        (self.base / "group_data" / "gpu_check.json").write_text(json.dumps({"ok": True}), encoding="utf-8")
        self.assertTrue(hwtier.gpu_ok(self.base))


class Routes(unittest.TestCase):
    def test_live_model_defaults_to_auto(self):
        self.assertEqual(simple_routes.profile({})["live_model"], "auto")
        self.assertEqual(simple_routes.profile({"backend": "server"}, has_gpu=False)["live_model"], "auto")
        self.assertEqual(simple_routes.profile({"local_live_model": "small"})["live_model"], "small")   # IT 指定的照舊

    def test_auto_is_resolved_before_starting(self):
        with mock.patch.object(hwtier, "pick", lambda b: {"model": "pack:whisper-base"}), \
                mock.patch.object(simple_routes.model_packs, "find", lambda *a, **k: {"id": "whisper-base"}):
            self.assertEqual(simple_routes.local_model_ok("x", "auto"), "pack:whisper-base")
        with mock.patch.object(hwtier, "pick", lambda b: {"model": "pack:whisper-base"}), \
                mock.patch.object(simple_routes.model_packs, "find", lambda *a, **k: None):
            self.assertEqual(simple_routes.local_model_ok("x", "auto"), "small")   # 剛好被移除：用內建的


if __name__ == "__main__":
    unittest.main()
