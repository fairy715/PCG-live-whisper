"""模型包：清單、下載（共用資料夾／GitHub）、分割檔、指紋、安裝、移除，以及 IT 設定頁的 API 與主程式的接法"""
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent.parent))
import model_packs as mp  # noqa: E402
import types  # noqa: E402
for _name in ("ctranslate2", "sentencepiece"):        # 跟 test_xlangs 一樣用假模組，只測程式邏輯
    sys.modules.setdefault(_name, types.ModuleType(_name))


def make_pack(pid, kind="asr", langs=("vi",), purpose=("live", "file"), version="1", parts=1, files=None):
    """做一個模型包 zip（可切成幾份），回傳 (catalog 項目, {檔名: bytes})"""
    meta = {"id": pid, "name": f"測試 {pid}", "type": kind, "engine": "faster-whisper" if kind == "asr" else "madlad",
            "languages": list(langs), "purpose": list(purpose), "version": version, "license": "Apache-2.0"}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(f"{pid}/pack.json", json.dumps(meta))
        for name, data in (files or {"model.bin": os.urandom(5000)}).items():
            z.writestr(f"{pid}/{name}", data)
    raw = buf.getvalue()
    step = -(-len(raw) // parts)
    blobs = {}
    for i in range(parts):
        name = f"{pid}.zip" if parts == 1 else f"{pid}.zip.{i + 1:03d}"
        blobs[name] = raw[i * step:(i + 1) * step]
    item = dict(meta, parts=[{"name": n, "size": len(b), "sha256": hashlib.sha256(b).hexdigest()} for n, b in blobs.items()])
    return item, blobs


class Packs(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp())
        self.share = self.base / "share"
        (self.share / "models").mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.base, ignore_errors=True)
        mp.JOBS.clear()

    def put_share(self, items_blobs):
        packs = []
        for item, blobs in items_blobs:
            for n, b in blobs.items():
                (self.share / "models" / n).write_bytes(b)
            packs.append(item)
        (self.share / "models" / "catalog.json").write_text(json.dumps({"format": 1, "packs": packs}), encoding="utf-8")

    def test_install_from_share_with_split_parts(self):
        item, blobs = make_pack("phowhisper-small", parts=3)
        self.put_share([(item, blobs)])
        cat, errs = mp.catalog(str(self.share), use_github=False)
        self.assertIn("phowhisper-small", cat)
        mp.install(self.base, cat["phowhisper-small"])
        inst = mp.installed(self.base)
        self.assertEqual([m["id"] for m in inst], ["phowhisper-small"])
        self.assertTrue((self.base / "models" / "packs" / "phowhisper-small" / "model.bin").is_file())
        self.assertEqual(mp.JOBS["phowhisper-small"]["state"], "done")
        self.assertFalse(any(p.name.startswith(".") for p in (self.base / "models" / "packs").iterdir()))   # 暫存都清掉
        # 選用：只用在對應的語言與用途
        s = {"asr_packs": {"vi": {"live": "phowhisper-small"}}}
        self.assertEqual(mp.asr_model_for(self.base, s, "vi", "live"), "pack:phowhisper-small")
        self.assertIsNone(mp.asr_model_for(self.base, s, "vi", "file"))
        self.assertIsNone(mp.asr_model_for(self.base, s, "id", "live"))
        mp.remove(self.base, "phowhisper-small")
        self.assertEqual(mp.installed(self.base), [])
        self.assertIsNone(mp.asr_model_for(self.base, s, "vi", "live"))

    def test_bad_checksum_does_not_install(self):
        item, blobs = make_pack("whisper-id-small", langs=("id",))
        name = next(iter(blobs))
        blobs[name] = blobs[name][:-1] + b"X"           # 內容被改過
        self.put_share([(item, blobs)])
        cat, _ = mp.catalog(str(self.share), use_github=False)
        with self.assertRaisesRegex(RuntimeError, "指紋不符"):
            mp.install(self.base, cat["whisper-id-small"])
        self.assertEqual(mp.installed(self.base), [])
        self.assertEqual(mp.JOBS["whisper-id-small"]["state"], "failed")

    def test_zip_with_bad_paths_is_refused(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("evil/pack.json", "{}")
            z.writestr("../x.txt", "x")
        raw = buf.getvalue()
        item = {"id": "evil", "type": "asr", "languages": ["vi"],
                "parts": [{"name": "evil.zip", "size": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}]}
        (self.share / "models" / "evil.zip").write_bytes(raw)
        (self.share / "models" / "catalog.json").write_text(json.dumps({"packs": [item]}), encoding="utf-8")
        cat, _ = mp.catalog(str(self.share), use_github=False)
        with self.assertRaisesRegex(RuntimeError, "不該有的路徑"):
            mp.install(self.base, cat["evil"])
        self.assertFalse((self.base / "models" / "x.txt").exists())

    def test_update_replaces_old_version(self):
        old, ob = make_pack("madlad400-3b", kind="mt", langs=("zh", "id", "vi", "hi", "en"), version="1",
                            files={"model.bin": b"old"})
        self.put_share([(old, ob)])
        mp.install(self.base, mp.catalog(str(self.share), use_github=False)[0]["madlad400-3b"])
        new, nb = make_pack("madlad400-3b", kind="mt", langs=("zh", "id"), version="2", files={"model.bin": b"new"})
        self.put_share([(new, nb)])
        mp.install(self.base, mp.catalog(str(self.share), use_github=False)[0]["madlad400-3b"])
        d = self.base / "models" / "packs" / "madlad400-3b"
        self.assertEqual((d / "model.bin").read_bytes(), b"new")
        self.assertEqual(mp.installed(self.base)[0]["version"], "2")

    def test_github_catalog_and_download(self):
        item, blobs = make_pack("whisper-hi-small", langs=("hi",), parts=2)
        cat_url = mp.GITHUB_DL_PREFIX + "catalog.json"
        rel = {"assets": [{"name": "catalog.json", "browser_download_url": cat_url}]}

        def fetch(url):
            if url == mp.GITHUB_RELEASE_API:
                return rel
            if url == cat_url:
                return {"packs": [item]}
            raise OSError(url)

        class R(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                self.close()

        def opener(url):
            return R(blobs[url[len(mp.GITHUB_DL_PREFIX):]])
        cat, errs = mp.catalog("", fetch=fetch)
        self.assertEqual((list(cat), errs), (["whisper-hi-small"], []))
        mp.install(self.base, cat["whisper-hi-small"], opener=opener)
        self.assertEqual(mp.installed(self.base)[0]["languages"], ["hi"])
        # 下載位址不是這個專案的：不採用
        rel["assets"][0]["browser_download_url"] = "https://evil.example.com/catalog.json"
        cat, errs = mp.catalog("", fetch=fetch)
        self.assertEqual(cat, {})
        self.assertTrue(errs)

    def test_github_down_uses_share_only(self):
        item, blobs = make_pack("phowhisper-medium", purpose=("file",))
        self.put_share([(item, blobs)])

        def down(url):
            raise OSError("offline")
        cat, errs = mp.catalog(str(self.share), fetch=down)
        self.assertEqual(list(cat), ["phowhisper-medium"])
        self.assertEqual(cat["phowhisper-medium"]["source_kind"], "share")
        self.assertTrue(errs)


class AdminApi(unittest.TestCase):
    """IT 設定頁的模型管理：要 IT 密碼、只在本機安裝、選用要裝好而且語言對得上、移除時一起拿掉設定"""

    def setUp(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        import simple_routes
        self.sr = simple_routes
        self.base = Path(tempfile.mkdtemp())
        self.share = self.base / "share"
        (self.share / "models").mkdir(parents=True)
        self.cfg = self.base / "config.json"
        self.local = True
        h = lambda p: "h:" + p
        self.cfg.write_text(json.dumps({"pcg_simple": {"it_password_hash": h("itpass1"), "update_share": str(self.share)}}),
                            encoding="utf-8")
        app = FastAPI()
        self.started = []

        async def start_live(body):
            self.started.append(body)

        def nogh(u):
            raise OSError("offline")
        self.q = simple_routes.register(app, self.base, lambda r: self.local, h, lambda p, hh: h(p) == hh, self.cfg,
                               lambda c: self.cfg.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8"),
                               start_live=start_live, live_running=lambda: False, live_args=lambda: None,
                               update_hooks={"github_fetch": nogh, "launch": lambda e: None, "models_fetch": nogh})
        self.c = TestClient(app)
        self.h = {"X-IT-Token": "itpass1"}

    def tearDown(self):
        shutil.rmtree(self.base, ignore_errors=True)
        mp.JOBS.clear()

    def wait(self, pid):
        for _ in range(100):
            j = self.c.get("/api/simple/admin/models", headers=self.h).json()["jobs"].get(pid, {})
            if j.get("state") in ("done", "failed"):
                return j
            time.sleep(0.05)
        self.fail("安裝沒有結束")

    def test_flow(self):
        self.assertEqual(self.c.get("/api/simple/admin/models").status_code, 401)
        item, blobs = make_pack("phowhisper-small")
        for n, b in blobs.items():
            (self.share / "models" / n).write_bytes(b)
        (self.share / "models" / "catalog.json").write_text(json.dumps({"packs": [item]}), encoding="utf-8")
        st = self.c.get("/api/simple/admin/models?refresh=1", headers=self.h).json()
        self.assertEqual([p["id"] for p in st["available"]], ["phowhisper-small"])
        self.assertEqual(st["installed"], [])
        # 別台電腦不能裝
        self.local = False
        self.assertEqual(self.c.post("/api/simple/admin/models/install", json={"id": "phowhisper-small"},
                                     headers=self.h).status_code, 403)
        self.local = True
        self.assertTrue(self.c.post("/api/simple/admin/models/install", json={"id": "phowhisper-small"},
                                    headers=self.h).json()["ok"])
        self.assertEqual(self.wait("phowhisper-small")["state"], "done")
        # 選用：語言不對不行
        r = self.c.post("/api/simple/admin/models/use", json={"asr_packs": {"id": {"live": "phowhisper-small"}}}, headers=self.h)
        self.assertEqual(r.status_code, 400)
        r = self.c.post("/api/simple/admin/models/use", json={"asr_packs": {"vi": {"live": "phowhisper-small"}}}, headers=self.h)
        self.assertTrue(r.json()["ok"])
        # 即時字幕：對方說越南文（單向）用模型包；雙向照舊
        self.c.post("/api/simple/live", json={"scenario": "vi"})
        self.assertEqual(self.started[-1]["model"], "pack:phowhisper-small")
        self.c.post("/api/simple/live", json={"scenario": "vi", "speak": True})
        self.assertEqual(self.started[-1]["model"], "small")
        self.c.post("/api/simple/live", json={"scenario": "id"})
        self.assertEqual(self.started[-1]["model"], "small")
        # 移除：設定一起拿掉
        self.assertTrue(self.c.post("/api/simple/admin/models/remove", json={"id": "phowhisper-small"}, headers=self.h).json()["ok"])
        self.assertNotIn("asr_packs", json.loads(self.cfg.read_text(encoding="utf-8"))["pcg_simple"])
        self.c.post("/api/simple/live", json={"scenario": "vi"})
        self.assertEqual(self.started[-1]["model"], "small")

    def test_file_job_uses_file_pack(self):
        item, blobs = make_pack("whisper-id-medium", langs=("id",), purpose=("file",))
        for n, b in blobs.items():
            (self.share / "models" / n).write_bytes(b)
        (self.share / "models" / "catalog.json").write_text(json.dumps({"packs": [item]}), encoding="utf-8")
        self.c.get("/api/simple/admin/models?refresh=1", headers=self.h)
        self.c.post("/api/simple/admin/models/install", json={"id": "whisper-id-medium"}, headers=self.h)
        self.wait("whisper-id-medium")
        self.c.post("/api/simple/admin/models/use", json={"asr_packs": {"id": {"file": "whisper-id-medium"}}}, headers=self.h)
        q = self.q
        args = q._args({"path": "a.wav", "mode": "id2zh"})
        self.assertEqual(args[args.index("-m") + 1], "pack:whisper-id-medium")
        args = q._args({"path": "a.wav", "mode": "zh"})
        self.assertEqual(args[args.index("-m") + 1], "small")


class MainProgram(unittest.TestCase):
    """主程式：-m pack:<id> 指到模型包資料夾；IT 選了 MADLAD 時本機翻譯改用它"""

    def setUp(self):
        sys.argv = [sys.argv[0]]
        import translate_meeting as t
        self.t = t
        self.root = Path(tempfile.mkdtemp())
        self.fake = str(self.root / "translate_meeting.py")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def add(self, pid, kind, engine, files=("model.bin",)):
        d = self.root / "models" / "packs" / pid
        d.mkdir(parents=True)
        (d / "pack.json").write_text(json.dumps({"id": pid, "type": kind, "engine": engine, "languages": ["vi"]}))
        for f in files:
            (d / f).write_bytes(b"x")
        return d

    def test_pack_names_and_resolve(self):
        from unittest import mock
        d = self.add("phowhisper-small", "asr", "faster-whisper")
        self.add("madlad400-3b", "mt", "madlad")
        with mock.patch.object(self.t, "__file__", self.fake):
            self.assertEqual(self.t._pcg_pack_model_names(), ["pack:phowhisper-small"])
            self.assertEqual(self.t._resolve_fw_model("pack:phowhisper-small"), str(d))
            self.assertEqual(self.t._resolve_fw_model("small"), "small")
            with self.assertRaises(FileNotFoundError):
                self.t._resolve_fw_model("pack:nope")

    def test_madlad_selected_by_it(self):
        from unittest import mock
        d = self.add("madlad400-3b", "mt", "madlad", files=("model.bin", "sentencepiece.model"))
        cfg = self.root / "config.json"
        cfg.write_text(json.dumps({"pcg_simple": {"mt_pack": "madlad400-3b"}}))
        with mock.patch.object(self.t, "__file__", self.fake), mock.patch.object(self.t, "CONFIG_PATH", str(cfg)):
            self.assertEqual(self.t._pcg_mt_pack(), str(d))
            cfg.write_text(json.dumps({"pcg_simple": {}}))
            self.assertIsNone(self.t._pcg_mt_pack())

    def test_madlad_prompt_format(self):
        from unittest import mock
        tr = object.__new__(self.t.MadladTranslator)
        tr.tgt_lang = "id"
        tr.sp = mock.Mock(Encode=lambda s, out_type=str: s.split(), Decode=lambda toks: " ".join(toks))
        res = mock.Mock(hypotheses=[["Selamat", "pagi"]])
        tr.ct2 = mock.Mock(translate_batch=mock.Mock(return_value=[res]))
        self.assertEqual(tr._translate_short("早安"), "Selamat pagi")
        sent = tr.ct2.translate_batch.call_args[0][0][0]
        self.assertEqual(sent[0], "<2id>")


if __name__ == "__main__":
    unittest.main()
