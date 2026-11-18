"""集團版 r24：語音辨識 API（OpenAI 相容的 /audio/transcriptions）。用本機的假伺服器，不連外網。

執行（在專案根目錄）：
    python3 -m unittest group/tests/test_asr_api.py -v
"""
import json
import re
import shutil
import sys
import tempfile
import threading
import types
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
for _name in ("ctranslate2", "sentencepiece"):
    sys.modules.setdefault(_name, types.ModuleType(_name))
sys.argv = [sys.argv[0]]

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import translate_meeting as t  # noqa: E402
from group import asr_api, glossary, simple_routes  # noqa: E402

SR = asr_api.SR


class FakeApi:
    """假的 OpenAI 相容伺服器：記下每次呼叫；mode 決定回什麼"""

    def __init__(self):
        self.calls, self.mode, self.key, self.retry_after = [], "ok", "sk-test", "7"
        outer = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
                f = {k.decode(): v.decode("utf-8", "replace")
                     for k, v in re.findall(rb'name="(\w+)"\r\n\r\n([^\r]*)\r\n', body)}
                outer.calls.append({"path": self.path, "auth": self.headers.get("Authorization"), "fields": f,
                                    "wav": b"RIFF" in body})

                def send(code, obj, headers=()):
                    raw = obj if isinstance(obj, bytes) else json.dumps(obj).encode()
                    self.send_response(code)
                    for k, v in headers:
                        self.send_header(k, v)
                    self.send_header("Content-Length", str(len(raw)))
                    self.end_headers()
                    self.wfile.write(raw)
                if not self.path.endswith("/audio/transcriptions"):
                    return send(404, {"error": {"message": "not found"}})
                if outer.mode == "down":
                    return send(503, {"error": {"message": "overloaded"}})
                if outer.mode == "limit":               # 免費額度用完（Groq）：429＋Retry-After
                    return send(429, {"error": {"message": "Rate limit reached for model"}},
                                [("Retry-After", outer.retry_after)] if outer.retry_after else [])
                if outer.mode == "html":
                    return send(200, b"<html>login</html>")
                if outer.key and self.headers.get("Authorization") != "Bearer " + outer.key:
                    return send(401, {"error": {"message": "Incorrect API key provided"}})
                if f.get("response_format") == "verbose_json":
                    if outer.mode == "no_verbose":
                        return send(400, {"error": {"message": "verbose_json not supported"}})
                    return send(200, {"text": "a b", "segments": [{"start": 0.0, "end": 1.0, "text": " a"},
                                                                 {"start": 1.0, "end": 2.5, "text": "b "}]})
                send(200, {"text": f"第{len(outer.calls)}段 寶城"})
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}/v1"

    def close(self):
        self.srv.shutdown()
        self.srv.server_close()


class Helpers(unittest.TestCase):
    def test_scope_and_url_rules(self):
        self.assertEqual(asr_api.scope("https://api.openai.com/v1"), "external")
        for u in ("http://10.1.2.3:8000/v1", "http://spark:8000/v1", "http://localhost:9000/v1", "http://asr.local/v1"):
            self.assertEqual(asr_api.scope(u), "internal", u)
        self.assertEqual(asr_api.scope("https://ai.example.com/v1", internal=True), "internal")
        self.assertEqual(asr_api.check_url("https://api.openai.com/v1/audio/transcriptions/"), ("https://api.openai.com/v1", ""))
        self.assertEqual(asr_api.check_url("http://api.openai.com/v1")[1], "asr_url_https")     # 外部一定要 https
        self.assertEqual(asr_api.check_url("http://192.168.1.5:8000/v1")[1], "")
        for bad in ("ftp://x/v1", "api.openai.com/v1", "https://", "https://a b/v1"):
            self.assertEqual(asr_api.check_url(bad)[1], "bad_asr_url", bad)

    def test_wav_bytes(self):
        import io
        import wave
        w = wave.open(io.BytesIO(asr_api.wav_bytes(np.array([0.0, 0.5, -2.0, 2.0], np.float32))))
        self.assertEqual((w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()), (SR, 1, 2, 4))
        self.assertEqual(list(np.frombuffer(w.readframes(4), "<i2")), [0, 16383, -32767, 32767])

    def test_chunks_cut_at_pauses(self):
        spans = [(0, 10 * SR), (11 * SR, 20 * SR), (21 * SR, 30 * SR), (40 * SR, 100 * SR)]
        got = [(round(s / SR, 1), round(e / SR, 1)) for s, e in asr_api.chunks(spans, 100 * SR)]
        self.assertEqual(got, [(0.0, 20.2), (20.8, 30.2), (40.0, 65.0), (65.0, 90.0), (89.8, 100.0)])
        self.assertTrue(all(e - s <= 25.5 for s, e in got))
        self.assertEqual(asr_api.chunks([], 100 * SR), [])

    def test_pieces(self):
        self.assertEqual(asr_api.pieces({"text": " hi "}, 10.0, 12.0), [(10.0, 12.0, "hi")])
        self.assertEqual(asr_api.pieces({"text": ""}, 0, 1), [])
        self.assertEqual(asr_api.pieces({"text": "x", "segments": [{"start": 0, "end": 1, "text": " a"},
                                                                  {"start": 1, "end": 99, "text": "b"}]}, 5.0, 8.0),
                         [(5.0, 6.0, "a"), (6.0, 8.0, "b")])
        self.assertTrue(asr_api.wants_segments("whisper-1"))
        self.assertFalse(asr_api.wants_segments("gpt-4o-transcribe"))


class Client(unittest.TestCase):
    def setUp(self):
        self.api = FakeApi()
        self.cfg = {"url": self.api.url, "model": "gpt-4o-transcribe", "key": "sk-test"}
        self.wav = asr_api.wav_bytes(np.zeros(SR, np.float32))

    def tearDown(self):
        self.api.close()

    def test_post_sends_openai_fields(self):
        data = asr_api.post(self.cfg, self.wav, "id", "寶成, MES")
        self.assertIn("寶城", data["text"])
        c = self.api.calls[0]
        self.assertEqual((c["path"], c["auth"], c["wav"]), ("/v1/audio/transcriptions", "Bearer sk-test", True))
        self.assertEqual(c["fields"], {"model": "gpt-4o-transcribe", "response_format": "json", "language": "id",
                                       "prompt": "寶成, MES"})

    def test_no_key_no_header_and_unknown_language_omitted(self):
        self.api.key = ""
        asr_api.post({"url": self.api.url, "model": "m"}, self.wav, "xx")
        self.assertIsNone(self.api.calls[0]["auth"])
        self.assertNotIn("language", self.api.calls[0]["fields"])

    def test_errors(self):
        with self.assertRaises(asr_api.ApiError) as e:
            asr_api.post(dict(self.cfg, key="bad"), self.wav)
        self.assertEqual((e.exception.status, e.exception.fatal), (401, True))
        self.assertIn("Incorrect API key", e.exception.message)
        self.api.mode = "down"
        with self.assertRaises(asr_api.ApiError) as e:
            asr_api.post(self.cfg, self.wav)
        self.assertEqual((e.exception.status, e.exception.fatal), (503, False))
        self.api.mode = "html"
        with self.assertRaises(asr_api.ApiError):
            asr_api.post(self.cfg, self.wav)
        with self.assertRaises(asr_api.ApiError) as e:
            asr_api.post({"url": "http://127.0.0.1:9/v1", "model": "m"}, self.wav, timeout=2)
        self.assertEqual(e.exception.status, 0)

    def test_rate_limit_carries_wait_time(self):
        self.api.mode = "limit"
        with self.assertRaises(asr_api.ApiError) as e:
            asr_api.post(self.cfg, self.wav)
        self.assertEqual((e.exception.status, e.exception.limited, e.exception.fatal), (429, True, False))
        self.assertEqual(e.exception.wait, 15)                         # 伺服器說 7 秒：至少等 15 秒
        self.api.retry_after = "90"
        with self.assertRaises(asr_api.ApiError) as e:
            asr_api.post(self.cfg, self.wav)
        self.assertEqual(e.exception.wait, 90)
        self.api.retry_after = "86400"
        with self.assertRaises(asr_api.ApiError) as e:
            asr_api.post(self.cfg, self.wav)
        self.assertEqual(e.exception.wait, 600)                        # 最多 10 分鐘就再試一次
        self.api.retry_after = ""
        with self.assertRaises(asr_api.ApiError) as e:
            asr_api.post(self.cfg, self.wav)
        self.assertEqual(e.exception.wait, 60)                         # 沒說多久：60 秒
        r = asr_api.test(self.cfg)
        self.assertEqual((r["ok"], r["status"]), (False, 429))

    def test_default_model_follows_the_service(self):
        self.assertEqual(asr_api.default_model("https://api.groq.com/openai/v1"), "whisper-large-v3-turbo")
        self.assertEqual(asr_api.default_model("https://api.openai.com/v1"), "gpt-4o-transcribe")
        self.assertEqual(asr_api.default_model("https://notgroq.com/v1"), "gpt-4o-transcribe")
        self.assertEqual(asr_api.default_model(""), "gpt-4o-transcribe")
        self.assertEqual(asr_api.scope(asr_api.GROQ_URL), "external")
        self.assertEqual(asr_api.check_url(asr_api.GROQ_URL + "/audio/transcriptions"), (asr_api.GROQ_URL, ""))
        asr_api.post({"url": self.api.url, "key": "sk-test"}, self.wav)      # 模型沒填：依網址決定
        self.assertEqual(self.api.calls[-1]["fields"]["model"], "gpt-4o-transcribe")

    def test_connection_test(self):
        self.assertEqual(asr_api.test(self.cfg), {"ok": True, "status": 200, "message": ""})
        r = asr_api.test(dict(self.cfg, key="bad"))
        self.assertEqual((r["ok"], r["status"]), (False, 401))


class Engine(unittest.TestCase):
    """主程式的 _FwModel：開了 API 就送 API，失敗的那一塊用本機模型"""

    def setUp(self):
        self.api = FakeApi()
        self.saved = dict(t._PCG_ASR_API)
        self.gl = t._PCG_GLOSS[0]
        t._PCG_GLOSS[0] = ()
        self.use()
        self.local_calls = []
        Seg = types.SimpleNamespace

        def local(audio, **kw):
            self.local_calls.append(kw)
            return iter([Seg(start=0.0, end=1.0, text="本機")]), types.SimpleNamespace(language=kw.get("language"))
        self.m = t._FwModel.__new__(t._FwModel)
        self.m._kw, self.m._m = {"device": "cpu"}, types.SimpleNamespace(transcribe=local)
        self.speech = (0.1 * np.ones(3 * SR)).astype(np.float32)

    def tearDown(self):
        self.api.close()
        lock = t._PCG_ASR_API["lock"]
        t._PCG_ASR_API.clear()
        t._PCG_ASR_API.update(self.saved, lock=lock)
        t._PCG_GLOSS[0] = self.gl

    def use(self, model="gpt-4o-transcribe", key="sk-test"):
        t._PCG_ASR_API.update(loaded=True, cfg={"url": self.api.url, "model": model, "key": key},
                              fails=0, pause_until=0.0, json_only=False, said=True)

    def run_(self, audio=None, **kw):
        segs, info = self.m.transcribe(self.speech if audio is None else audio, language="id", **kw)
        return [(round(s.start, 1), round(s.end, 1), s.text) for s in segs], info

    def test_short_segment_goes_to_api_with_glossary(self):
        t._PCG_GLOSS[0] = glossary.Glossary(glossary.parse("寶成 | 寶城\nMES"))
        out, info = self.run_()
        self.assertEqual(out, [(0.0, 3.0, "第1段 寶成")])                 # API 的結果也修正聽錯的寫法
        self.assertEqual(info.language, "id")
        self.assertEqual(self.api.calls[0]["fields"]["prompt"], "寶成, MES")
        self.assertEqual(self.local_calls, [])

    def test_language_detection_stays_local(self):
        self.m.transcribe(self.speech, language=None, vad_filter=True)
        self.assertEqual((len(self.api.calls), len(self.local_calls)), (0, 1))

    def test_whisper_model_gets_segment_times_and_falls_back_to_json(self):
        self.use("whisper-1")
        self.assertEqual(self.run_()[0], [(0.0, 1.0, "a"), (1.0, 2.5, "b")])
        self.api.mode = "no_verbose"
        self.use("whisper-1")
        self.api.calls.clear()
        self.assertEqual(len(self.run_()[0]), 1)
        self.assertEqual([c["fields"]["response_format"] for c in self.api.calls], ["verbose_json", "json"])
        self.run_()
        self.assertEqual(self.api.calls[-1]["fields"]["response_format"], "json")      # 之後直接要 json

    def test_long_audio_is_chunked_and_silence_is_not_sent(self):
        long = np.zeros(60 * SR, np.float32)
        with mock.patch.object(t, "_pcg_silero_spans", lambda a: [(0, 20 * SR), (22 * SR, 40 * SR), (45 * SR, 58 * SR)]):
            out, _ = self.run_(long)
        self.assertEqual(len(self.api.calls), 3)
        self.assertEqual([x[0] for x in out], [0.0, 21.8, 44.8])
        self.api.calls.clear()
        with mock.patch.object(t, "_pcg_silero_spans", lambda a: []):
            self.assertEqual(self.run_(np.zeros(3 * SR, np.float32), vad_filter=True)[0], [])
        self.assertEqual(self.api.calls, [])

    def test_wrong_key_falls_back_and_pauses(self):
        self.use(key="bad")
        self.assertEqual(self.run_()[0], [(0.0, 1.0, "本機")])
        self.assertIsNone(t._pcg_asr_api_ready())                       # 金鑰不對：暫停，不再一直打 API
        self.run_()
        self.assertEqual(len(self.api.calls), 1)
        self.assertIs(self.local_calls[0]["vad_filter"], False)         # 已經切好的一塊，不用再做一次 VAD

    def test_server_down_three_times_then_pause(self):
        self.api.mode = "down"
        for _ in range(5):
            self.assertEqual(self.run_()[0][0][2], "本機")
        self.assertEqual(len(self.api.calls), 3)

    def test_rate_limit_pauses_at_once_and_uses_local(self):
        self.api.mode, self.api.retry_after = "limit", "40"
        before = t.time.monotonic()
        self.assertEqual(self.run_()[0], [(0.0, 1.0, "本機")])           # 這一段改在這台電腦辨識，字幕不斷
        self.assertIsNone(t._pcg_asr_api_ready())                       # 第一次就暫停，不用等連續 3 次
        self.assertEqual(t._PCG_ASR_API["fails"], 0)                    # 不算「壞掉」
        wait = t._PCG_ASR_API["pause_until"] - before
        self.assertTrue(39 <= wait <= 42, wait)                         # 照伺服器說的 40 秒
        self.run_()
        self.assertEqual(len(self.api.calls), 1)                        # 暫停期間不再打 API
        t._PCG_ASR_API["pause_until"] = 0.0                             # 時間到：額度恢復，回到 API
        self.api.mode = "ok"
        self.assertIn("寶城", self.run_()[0][0][2])

    def test_off_by_default(self):
        t._PCG_ASR_API.update(loaded=True, cfg=None)
        self.assertEqual(self.run_()[0], [(0.0, 1.0, "本機")])
        self.assertEqual(self.api.calls, [])


class Routes(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp())
        (self.base / "translate_meeting.py").write_text('APP_VERSION = "2.99"\n', encoding="utf-8")
        (self.base / "group_data").mkdir()
        self.cfg = self.base / "config.json"
        self.cfg.write_text(json.dumps({"remote_whisper": {"host": "10.0.0.9"},
                                        "pcg_simple": {"it_password_hash": "h:itpass1"}}), encoding="utf-8")
        self.tested = []
        app = FastAPI()
        simple_routes.register(
            app, self.base, lambda r: True, lambda raw: "h:" + raw, lambda raw, h: h == "h:" + (raw or ""),
            self.cfg, lambda c: self.cfg.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8"),
            gpu_alive=lambda h, p: True,
            update_hooks={"github_fetch": self._off, "models_fetch": self._off,
                          "asr_test": lambda cfg: self.tested.append(cfg) or {"ok": True, "status": 200, "message": ""}})
        self.c = TestClient(app)
        self.h = {"X-IT-Token": "itpass1"}

    def tearDown(self):
        shutil.rmtree(self.base, ignore_errors=True)

    @staticmethod
    def _off(u):
        raise OSError("offline")

    def save(self, **kw):
        return self.c.post("/api/simple/admin/save", headers=self.h, json={"backend": "local", **kw})

    def test_save_state_and_key_is_never_returned(self):
        r = self.save(asr_api_enabled=True, asr_api_url="https://api.openai.com/v1/", asr_api_model="whisper-1",
                      asr_api_key="sk-secret123")
        self.assertTrue(r.json()["ok"], r.text)
        a = r.json()["state"]["asr_api"]
        self.assertEqual(a, {"enabled": True, "url": "https://api.openai.com/v1", "model": "whisper-1",
                             "internal": False, "key_set": True, "scope": "external"})
        self.assertNotIn("sk-secret123", r.text)
        saved = json.loads(self.cfg.read_text(encoding="utf-8"))["pcg_simple"]
        self.assertEqual(saved["asr_api_key"], "sk-secret123")
        # 金鑰留空＝不變；勾刪除才拿掉（外部服務沒有金鑰不給存）
        self.assertTrue(self.save(asr_api_enabled=True, asr_api_url="https://api.openai.com/v1").json()["state"]["asr_api"]["key_set"])
        r = self.save(asr_api_enabled=True, asr_api_url="https://api.openai.com/v1", clear_asr_api_key=True)
        self.assertEqual((r.status_code, r.json()["code"]), (400, "asr_key_required"))

    def test_groq_default_model_and_key_required(self):
        """Groq（r26）：模型沒填就用 whisper-large-v3-turbo（Groq 沒有 gpt-4o-transcribe）；是外部服務，要金鑰"""
        r = self.save(asr_api_enabled=True, asr_api_url="https://api.groq.com/openai/v1")
        self.assertEqual((r.status_code, r.json()["code"]), (400, "asr_key_required"))
        r = self.save(asr_api_enabled=True, asr_api_url="https://api.groq.com/openai/v1/", asr_api_key="gsk_secret456")
        a = r.json()["state"]["asr_api"]
        self.assertEqual((a["url"], a["model"], a["scope"], a["key_set"]),
                         ("https://api.groq.com/openai/v1", "whisper-large-v3-turbo", "external", True))
        self.assertNotIn("gsk_secret456", r.text)
        r = self.c.post("/api/simple/admin/asr-test", headers=self.h,
                        json={"asr_api_url": "https://api.groq.com/openai/v1", "asr_api_model": ""})
        self.assertTrue(r.json()["ok"])
        self.assertEqual(self.tested[-1], {"url": "https://api.groq.com/openai/v1", "model": "whisper-large-v3-turbo",
                                           "key": "gsk_secret456"})

    def test_llm_internal_is_saved_and_reported(self):
        """r29：「這是公司內部的伺服器」的勾選會存起來，設定頁也拿得到目前算出來的去向"""
        self.cfg.write_text(json.dumps({"llm_host": "llm.vendor.com", "llm_port": 443, "llm_url": "https://llm.vendor.com",
                                        "pcg_simple": {"it_password_hash": "h:itpass1", "backend": "server"}}), encoding="utf-8")
        st = self.c.post("/api/simple/admin/save", headers=self.h, json={"backend": "server", "llm_url": "https://llm.vendor.com", "llm_internal": False}).json()["state"]
        self.assertEqual((st["llm_internal"], st["llm_scope"]), (False, "external"))
        st = self.c.post("/api/simple/admin/save", headers=self.h, json={"backend": "server", "llm_url": "https://llm.vendor.com", "llm_internal": True}).json()["state"]
        self.assertEqual((st["llm_internal"], st["llm_scope"]), (True, "internal"))
        self.assertTrue(json.loads(self.cfg.read_text(encoding="utf-8"))["pcg_simple"]["llm_internal"])
        st = self.c.post("/api/simple/admin/save", headers=self.h, json={"backend": "server", "llm_url": "https://llm.vendor.com", "llm_internal": False}).json()["state"]
        self.assertFalse(st["llm_internal"])
        self.assertNotIn("llm_internal", json.loads(self.cfg.read_text(encoding="utf-8"))["pcg_simple"])

    def test_validation(self):
        self.assertEqual(self.save(asr_api_enabled=True, asr_api_url="http://api.openai.com/v1", asr_api_key="k").json()["code"],
                         "asr_url_https")
        self.assertEqual(self.save(asr_api_enabled=True, asr_api_url="nonsense", asr_api_key="k").json()["code"], "bad_asr_url")
        self.assertEqual(self.save(asr_api_enabled=True, asr_api_url="https://x.example/v1", asr_api_key="a b").json()["code"],
                         "bad_asr_key")
        r = self.save(asr_api_enabled=True, asr_api_url="http://10.1.1.5:8000/v1")          # 內部服務：http、沒有金鑰都可以
        self.assertEqual(r.json()["state"]["asr_api"]["scope"], "internal")

    def test_staff_page_scope_and_gpu_server_gives_way(self):
        self.assertEqual(self.c.get("/api/simple/config", headers={"X-Client-Id": "browserA1234"}).json()["asr_scope"], "")
        self.save(asr_api_enabled=True, asr_api_url="https://api.openai.com/v1", asr_api_key="sk-x")
        self.assertEqual(self.c.get("/api/simple/config", headers={"X-Client-Id": "browserA1234"}).json()["asr_scope"], "external")
        s = json.loads(self.cfg.read_text(encoding="utf-8"))["pcg_simple"]
        self.assertTrue(simple_routes.asr_api_on(s))
        self.save(asr_api_enabled=False)
        self.assertEqual(self.c.get("/api/simple/config", headers={"X-Client-Id": "browserA1234"}).json()["asr_scope"], "")

    def test_connection_test_uses_saved_key_and_needs_it_password(self):
        self.save(asr_api_enabled=True, asr_api_url="https://api.openai.com/v1", asr_api_key="sk-saved")
        r = self.c.post("/api/simple/admin/asr-test", headers=self.h,
                        json={"asr_api_url": "https://api.openai.com/v1", "asr_api_model": "whisper-1"})
        self.assertEqual((r.json()["ok"], r.json()["scope"]), (True, "external"))
        self.assertEqual(self.tested[0], {"url": "https://api.openai.com/v1", "model": "whisper-1", "key": "sk-saved"})
        r = self.c.post("/api/simple/admin/asr-test", headers=self.h, json={"asr_api_url": "http://api.openai.com/v1"})
        self.assertEqual(r.json()["code"], "asr_url_https")
        r = self.c.post("/api/simple/admin/asr-test", headers={"X-IT-Token": "no"}, json={})
        self.assertFalse(r.json().get("ok"))
        self.assertEqual(len(self.tested), 1)


if __name__ == "__main__":
    unittest.main()
