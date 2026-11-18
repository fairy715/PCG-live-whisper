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


class GpuHint(unittest.TestCase):
    """r25：偵測到 NVIDIA 顯示卡、還沒裝 GPU 加速包 → 建議安裝"""

    def setUp(self):
        self.base = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.base, ignore_errors=True)

    RTX = [{"name": "NVIDIA GeForce RTX 3060", "vram_mb": 12288}]

    def hint(self, gpus, settings=None, now=1000.0):
        return hwtier.gpu_hint(self.base, settings or {}, now, gpus)

    def test_show_for_nvidia_with_enough_memory(self):
        h = self.hint(self.RTX)
        self.assertEqual((h["show"], h["name"], h["vram_mb"]), (True, "NVIDIA GeForce RTX 3060", 12288))
        self.assertTrue(self.hint([{"name": "GTX 1650", "vram_mb": 4096}])["show"])
        # 兩張卡：看記憶體最大的那張
        self.assertEqual(self.hint([{"name": "MX150", "vram_mb": 2048}] + self.RTX)["name"], "NVIDIA GeForce RTX 3060")

    def test_not_shown(self):
        self.assertEqual(self.hint([])["why"], "no_gpu")                                   # 沒有 NVIDIA（含 AMD、Intel）
        self.assertEqual(self.hint([{"name": "MX330", "vram_mb": 2048}])["why"], "small")   # 2 GB 多半跑不動
        self.assertEqual(self.hint(self.RTX, {"gpu_hint": {"off": True}})["why"], "off")
        self.assertEqual(self.hint(self.RTX, {"gpu_hint": {"until": 2000}})["why"], "later")
        self.assertTrue(self.hint(self.RTX, {"gpu_hint": {"until": 500}})["show"])          # 「下次再說」過期了再提醒
        (self.base / "gpu" / "cuda12").mkdir(parents=True)
        self.assertEqual(self.hint(self.RTX)["why"], "installed")

    def test_nvidia_smi_parsing(self):
        import types
        calls = []

        def run(cmd, **kw):
            calls.append(cmd[0])
            if len(calls) == 1:
                raise FileNotFoundError("nvidia-smi")                # PATH 上沒有：試下一個位置
            return types.SimpleNamespace(returncode=0, stdout="NVIDIA GeForce RTX 3060, 12288\nNVIDIA RTX A2000, 6138\n\nbad line\n")
        self.assertEqual(hwtier.nvidia_gpus(run), [{"name": "NVIDIA GeForce RTX 3060", "vram_mb": 12288},
                                                   {"name": "NVIDIA RTX A2000", "vram_mb": 6138}])
        self.assertEqual(len(calls), 2)
        self.assertEqual(hwtier.nvidia_gpus(lambda cmd, **kw: types.SimpleNamespace(returncode=9, stdout="")), [])

        def boom(cmd, **kw):
            raise OSError("no such file")
        self.assertEqual(hwtier.nvidia_gpus(boom), [])


class GpuHintRoutes(unittest.TestCase):
    def setUp(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        self.base = Path(tempfile.mkdtemp())
        (self.base / "translate_meeting.py").write_text('APP_VERSION = "2.99"\n', encoding="utf-8")
        (self.base / "group_data").mkdir()
        self.cfg = self.base / "config.json"
        self.cfg.write_text(json.dumps({"pcg_simple": {"it_password_hash": "h:itpass1"}}), encoding="utf-8")
        self.local, self.asked = True, []
        app = FastAPI()
        simple_routes.register(
            app, self.base, lambda r: self.local, lambda raw: "h:" + raw, lambda raw, h: h == "h:" + (raw or ""),
            self.cfg, lambda c: self.cfg.write_text(json.dumps(c), encoding="utf-8"), gpu_alive=lambda h, p: False,
            update_hooks={"github_fetch": self._off, "models_fetch": self._off,
                          "gpus": lambda: self.asked.append(1) or [{"name": "NVIDIA GeForce RTX 4060", "vram_mb": 8188}]})
        self.c = TestClient(app)

    def tearDown(self):
        shutil.rmtree(self.base, ignore_errors=True)

    @staticmethod
    def _off(u):
        raise OSError("offline")

    def test_hint_later_never_and_detection_is_cached(self):
        j = self.c.get("/api/simple/gpu-hint").json()
        self.assertEqual((j["show"], j["name"], j["who"], j["mb"]), (True, "NVIDIA GeForce RTX 4060", "staff", hwtier.GPU_PACK_MB))
        self.assertTrue(j["url"].endswith(".exe"))
        self.assertTrue(self.c.post("/api/simple/gpu-hint", json={"action": "later"}).json()["ok"])
        self.assertEqual(self.c.get("/api/simple/gpu-hint").json()["why"], "later")
        self.c.post("/api/simple/gpu-hint", json={"action": "never"})
        self.assertEqual(self.c.get("/api/simple/gpu-hint").json()["why"], "off")
        self.assertEqual(self.c.post("/api/simple/gpu-hint", json={"action": "x"}).status_code, 400)
        self.assertEqual(len(self.asked), 1)                           # nvidia-smi 只問一次

    def test_only_on_this_computer(self):
        self.local = False
        self.assertFalse(self.c.get("/api/simple/gpu-hint").json()["show"])
        self.assertEqual(self.c.post("/api/simple/gpu-hint", json={"action": "never"}).status_code, 403)
        self.assertEqual(self.asked, [])


CAT = {pid: {"id": pid, "name": pid.upper(), "size_mb": mb} for pid, mb in (
    ("breeze-asr-25", 1500), ("whisper-large-v3-turbo", 800), ("whisper-base", 80),
    ("phowhisper-small", 240), ("phowhisper-medium", 740), ("whisper-id-small", 240))}
GPU, CPU4, CPU2 = {"gpu": True, "physical": 4, "logical": 8}, {"gpu": False, "physical": 4, "logical": 8}, \
    {"gpu": False, "physical": 2, "logical": 4}


class ModelHint(unittest.TestCase):
    """r25：開啟程式時推薦更適合的語音模型包"""

    def hint(self, hw, src="", settings=None, installed=(), now=1000.0, cat=CAT, free_mb=None):
        return hwtier.model_hint(settings or {}, now, hw, cat, list(installed), src, free_mb)

    def test_language_first_then_hardware(self):
        self.assertEqual(self.hint(GPU, "zh")["id"], "breeze-asr-25")               # 有顯示卡＋常用中文
        self.assertEqual(self.hint(GPU, "vi")["id"], "phowhisper-medium")           # 有顯示卡：語言包用 medium
        h = self.hint(CPU4, "vi")
        self.assertEqual((h["id"], h["why"], h["lang"], h["size_mb"]), ("phowhisper-small", "lang", "vi", 240))
        self.assertEqual(self.hint(GPU, "en")["id"], "whisper-large-v3-turbo")      # 沒有語言專用的：硬體建議
        self.assertEqual(self.hint(CPU2, "")["id"], "whisper-base")
        self.assertFalse(self.hint(CPU4, "zh")["show"])                             # 一般筆電說中文：內建的就好
        self.assertFalse(self.hint(CPU4, "")["show"])

    def test_skips_installed_and_moves_to_next(self):
        vi = [{"id": "phowhisper-small", "type": "asr", "languages": ["vi"]}]
        self.assertEqual(self.hint(GPU, "vi", installed=vi)["id"], "whisper-large-v3-turbo")     # 越南文已經有：推薦下一個
        turbo = [{"id": "whisper-large-v3-turbo", "type": "asr", "languages": ["zh", "en"], "multilingual": True}]
        self.assertFalse(self.hint(GPU, "en", installed=turbo)["show"])
        self.assertEqual(self.hint(GPU, "zh", installed=turbo)["id"], "breeze-asr-25")           # 多語的大模型不算中文專用
        base = [{"id": "whisper-base", "type": "asr", "languages": ["zh"], "multilingual": True}]
        self.assertFalse(self.hint(CPU2, "", installed=base)["show"])

    def test_respects_later_never_it_choice_catalog_and_disk(self):
        self.assertFalse(self.hint(CPU2, "", {"model_hint": {"off": True}})["show"])
        self.assertFalse(self.hint(CPU2, "", {"model_hint": {"until": {"whisper-base": 2000}}})["show"])
        self.assertTrue(self.hint(CPU2, "", {"model_hint": {"until": {"whisper-base": 500}}})["show"])
        # 「下次再說」只擋那一個：越南文的照樣推薦
        self.assertEqual(self.hint(CPU2, "vi", {"model_hint": {"until": {"phowhisper-small": 2000}}})["id"], "whisper-base")
        self.assertFalse(self.hint(CPU2, "", {"local_live_model": "small"})["show"])              # IT 指定了模型：不推薦硬體的
        self.assertEqual(self.hint(CPU2, "vi", {"local_live_model": "small"})["id"], "phowhisper-small")
        self.assertFalse(self.hint(CPU2, "", cat={})["show"])                                     # 清單裡沒有（連不上）：不推薦
        self.assertFalse(self.hint(GPU, "zh", free_mb=2000, cat={"breeze-asr-25": CAT["breeze-asr-25"]})["show"])   # 磁碟不夠


class ModelHintRoutes(unittest.TestCase):
    """用共用資料夾放一個假的模型包，實際跑：推薦 → 安裝 → 自動指定給那個語言"""

    def setUp(self):
        import hashlib
        import io
        import zipfile
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        self.base = Path(tempfile.mkdtemp())
        (self.base / "translate_meeting.py").write_text('APP_VERSION = "2.99"\n', encoding="utf-8")
        (self.base / "group_data").mkdir()
        share = self.base / "share"
        (share / "models").mkdir(parents=True)
        meta = {"id": "phowhisper-small", "name": "PhoWhisper small", "type": "asr", "engine": "faster-whisper",
                "languages": ["vi"], "purpose": ["live", "file"], "version": "1", "license": "BSD-3-Clause", "size_mb": 1}
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("phowhisper-small/pack.json", json.dumps(meta))
            z.writestr("phowhisper-small/model.bin", b"x" * 3000)
        raw = buf.getvalue()
        (share / "models" / "phowhisper-small.zip").write_bytes(raw)
        (share / "models" / "catalog.json").write_text(json.dumps({"format": 1, "packs": [dict(meta, parts=[
            {"name": "phowhisper-small.zip", "size": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}])]}), encoding="utf-8")
        self.cfg = self.base / "config.json"
        self.cfg.write_text(json.dumps({"pcg_simple": {"it_password_hash": "h:itpass1", "update_share": str(share)}}),
                            encoding="utf-8")
        self.local = True
        app = FastAPI()
        simple_routes.register(
            app, self.base, lambda r: self.local, lambda raw: "h:" + raw, lambda raw, h: h == "h:" + (raw or ""),
            self.cfg, lambda c: self.cfg.write_text(json.dumps(c), encoding="utf-8"), gpu_alive=lambda h, p: False,
            update_hooks={"github_fetch": self._off, "models_fetch": self._off, "hw": CPU4, "gpus": lambda: []})
        self.c = TestClient(app)

    def tearDown(self):
        shutil.rmtree(self.base, ignore_errors=True)
        simple_routes.model_packs.JOBS.clear()

    @staticmethod
    def _off(u):
        raise OSError("offline")

    def ps(self):
        return json.loads(self.cfg.read_text(encoding="utf-8"))["pcg_simple"]

    def test_recommend_install_and_assign(self):
        import time as _t
        j = self.c.get("/api/simple/model-hint?src=vi").json()
        self.assertEqual((j["show"], j["id"], j["why"], j["who"]), (True, "phowhisper-small", "lang", "staff"))
        self.assertFalse(self.c.get("/api/simple/model-hint?src=en").json()["show"])
        r = self.c.post("/api/simple/model-hint", json={"action": "install", "id": "whisper-base", "src": "vi"})
        self.assertEqual(r.status_code, 409)                                   # 只能裝這次推薦的那一個
        self.assertTrue(self.c.post("/api/simple/model-hint", json={"action": "install", "id": "phowhisper-small", "src": "vi"}).json()["ok"])
        for _ in range(100):
            st = self.c.get("/api/simple/model-hint?src=vi").json()
            if (st["jobs"].get("phowhisper-small") or {}).get("state") in ("done", "failed"):
                break
            _t.sleep(0.05)
        self.assertEqual(st["jobs"]["phowhisper-small"]["state"], "done", st)
        st = self.c.get("/api/simple/model-hint?src=vi").json()
        self.assertFalse(st["show"])                                           # 裝好了：不再推薦
        self.assertEqual(self.ps()["asr_packs"], {"vi": {"live": "phowhisper-small", "file": "phowhisper-small"}})

    def test_later_never_it_only_and_remote(self):
        self.assertTrue(self.c.post("/api/simple/model-hint", json={"action": "later", "id": "phowhisper-small", "src": "vi"}).json()["ok"])
        self.assertFalse(self.c.get("/api/simple/model-hint?src=vi").json()["show"])
        c = json.loads(self.cfg.read_text(encoding="utf-8"))
        c["pcg_simple"].pop("model_hint")
        c["pcg_simple"]["update_who"] = "it"
        self.cfg.write_text(json.dumps(c), encoding="utf-8")
        self.assertEqual(self.c.get("/api/simple/model-hint?src=vi").json()["who"], "it")
        r = self.c.post("/api/simple/model-hint", json={"action": "install", "id": "phowhisper-small", "src": "vi"})
        self.assertEqual((r.status_code, r.json()["code"]), (403, "it_only"))  # 只有 IT 能裝的電腦：同仁不能裝
        self.c.post("/api/simple/model-hint", json={"action": "never"})
        self.assertFalse(self.c.get("/api/simple/model-hint?src=vi").json()["show"])
        self.local = False
        self.assertFalse(self.c.get("/api/simple/model-hint?src=vi").json()["show"])
        self.assertEqual(self.c.post("/api/simple/model-hint", json={"action": "never"}).status_code, 403)


if __name__ == "__main__":
    unittest.main()
