"""PCG 集團版 r24：聲音測試與音訊裝置選擇（同仁頁面「聲音與麥克風」）。

同仁最常問「為什麼沒有字幕」，多半是聲音沒進來：喇叭選錯、麥克風被靜音、接了 USB 會議麥克風卻沒選到。
這裡提供：
  - 列出這台電腦的麥克風與喇叭（Windows）；同仁可以指定，預設「自動」＝跟著 Windows 的預設裝置
  - 聲音測試：同時量「電腦播放的聲音」與「麥克風」的音量幾秒鐘，頁面顯示音量條
設定存在 config.json 的 pcg_simple.mic_name／speaker_name（存的是裝置名稱：裝置編號每次插拔都會變）。
開始字幕時 simple_routes 把麥克風名稱換成編號交給主程式（--mic-device／-d）；喇叭由主程式的 _pcg_pick_loopback 依名稱找。
"""
import sys
import threading
import time

MAX_NAME = 200
MAX_SECONDS = 30
_LOOP_SUFFIX = " [Loopback]"


def clean_name(name):
    name = " ".join(str(name or "").split())
    return name[:MAX_NAME] if not any(c in name for c in "\r\n\t\"<>") else ""


def strip_loopback(name):
    name = str(name or "")
    return name[:-len(_LOOP_SUFFIX)] if name.endswith(_LOOP_SUFFIX) else name


def _is_loopback_name(name):
    n = name.lower()
    return "loopback" in n or "stereo mix" in n or "立體聲混音" in name or "what u hear" in n


class RealBackend:
    """真的音訊裝置（sounddevice＋Windows 的 pyaudiowpatch）。測試用假的 backend 取代"""

    def _sd(self):
        import sounddevice as sd
        return sd

    def mics(self):
        """[{"id": sounddevice 編號, "name"}]：Windows 只列 WASAPI 的（名稱完整、不重複），其他系統列全部輸入裝置"""
        sd = self._sd()
        devs, apis = list(sd.query_devices()), list(sd.query_hostapis())
        want_api = next((i for i, h in enumerate(apis) if "WASAPI" in h["name"]), None) if sys.platform == "win32" else None
        out, seen = [], set()
        for i, d in enumerate(devs):
            if d["max_input_channels"] <= 0 or _is_loopback_name(d["name"]):
                continue
            if want_api is not None and d["hostapi"] != want_api:
                continue
            if d["name"] in seen:
                continue
            seen.add(d["name"])
            out.append({"id": i, "name": d["name"]})
        return out

    def default_mic(self):
        sd = self._sd()
        try:
            i = sd.default.device[0]
            return sd.query_devices(i)["name"] if i is not None and i >= 0 else ""
        except Exception:  # noqa: BLE001
            return ""

    def speakers(self):
        """[{"name"}]：可以錄「播放的聲音」的喇叭／耳機（Windows 的 WASAPI Loopback）；其他系統沒有"""
        if sys.platform != "win32":
            return []
        import pyaudiowpatch as pa
        p = pa.PyAudio()
        try:
            return [{"name": strip_loopback(d["name"])} for d in p.get_loopback_device_info_generator()]
        finally:
            p.terminate()

    def default_speaker(self):
        if sys.platform != "win32":
            return ""
        import pyaudiowpatch as pa
        p = pa.PyAudio()
        try:
            return strip_loopback(p.get_default_wasapi_loopback()["name"])
        except Exception:  # noqa: BLE001
            return ""
        finally:
            p.terminate()

    def open_mic(self, device_id, on_peak):
        """開麥克風；回傳一個呼叫了就關掉的函式"""
        import numpy as np
        sd = self._sd()

        def cb(indata, frames, t, status):
            on_peak(float(np.max(np.abs(indata))) if len(indata) else 0.0)
        st = sd.InputStream(device=device_id, channels=1, dtype="float32", callback=cb)
        st.start()

        def close():
            st.stop()
            st.close()
        return close

    def open_speaker(self, name, on_peak):
        """開「播放的聲音」（Windows WASAPI Loopback；name 空的＝預設喇叭）"""
        if sys.platform != "win32":
            raise RuntimeError("unsupported")
        import numpy as np
        import pyaudiowpatch as pa
        p = pa.PyAudio()
        try:
            info = None
            if name:
                info = next((d for d in p.get_loopback_device_info_generator()
                             if name.lower() in d["name"].lower()), None)
            if info is None:
                info = p.get_default_wasapi_loopback()

            def cb(in_data, frame_count, time_info, status):
                a = np.frombuffer(in_data, dtype=np.float32)
                on_peak(float(np.max(np.abs(a))) if len(a) else 0.0)
                return (None, pa.paContinue)
            st = p.open(format=pa.paFloat32, channels=int(info["maxInputChannels"]) or 2,
                        rate=int(info["defaultSampleRate"]), input=True, input_device_index=info["index"],
                        frames_per_buffer=int(info["defaultSampleRate"] * 0.05), stream_callback=cb)
        except Exception:
            p.terminate()
            raise

        def close():
            try:
                st.stop_stream()
                st.close()
            finally:
                p.terminate()
        return close


class _Level:
    def __init__(self):
        self.now, self.max, self.error, self.got = 0.0, 0.0, "", False

    def feed(self, peak):
        peak = max(0.0, min(1.0, peak))
        self.got = True
        self.now = max(peak, self.now * 0.6)          # 音量條往下掉得慢一點，看得清楚
        self.max = max(self.max, peak)

    def view(self):
        return {"level": round(self.now, 4), "max": round(self.max, 4), "error": self.error, "data": self.got}


class Meter:
    """聲音測試：一次只跑一個；最久 MAX_SECONDS 秒自動停（忘了關也不會一直佔著麥克風）"""

    def __init__(self, backend=None, clock=time.monotonic):
        self.backend = backend or RealBackend()
        self.clock = clock
        self.lock = threading.Lock()
        self._closers, self._until = [], 0.0
        self.system, self.mic = _Level(), _Level()

    def devices(self):
        out = {"mics": [], "speakers": [], "default_mic": "", "default_speaker": "", "error": ""}
        try:
            out["mics"] = [{"name": m["name"]} for m in self.backend.mics()]
            out["default_mic"] = self.backend.default_mic()
        except Exception as e:  # noqa: BLE001
            out["error"] = f"{type(e).__name__}: {str(e)[:120]}"
        try:
            out["speakers"] = self.backend.speakers()
            out["default_speaker"] = self.backend.default_speaker()
        except Exception as e:  # noqa: BLE001
            out["error"] = out["error"] or f"{type(e).__name__}: {str(e)[:120]}"
        return out

    def mic_index(self, name):
        """麥克風名稱 → sounddevice 編號；找不到（拔掉了）回 None＝用預設"""
        name = clean_name(name)
        if not name:
            return None
        try:
            for m in self.backend.mics():
                if m["name"] == name:
                    return m["id"]
        except Exception:  # noqa: BLE001
            pass
        return None

    def default_mic_index(self):
        """Windows 預設麥克風的 sounddevice 編號；沒有麥克風回 None（r28：「大家都說中文」用麥克風收音時要明確指定）"""
        try:
            name = clean_name(self.backend.default_mic())
            mics = list(self.backend.mics())
        except Exception:  # noqa: BLE001
            return None
        if not mics:
            return None
        for m in mics:
            if name and m["name"] == name:
                return m["id"]
        for m in mics:                                  # 預設裝置的名稱可能被截短（非 WASAPI 的名稱最多 31 個字）
            if name and (m["name"].startswith(name) or name.startswith(m["name"])):
                return m["id"]
        return mics[0]["id"]

    def running(self):
        return bool(self._closers) and self.clock() < self._until

    def start(self, mic="", speaker="", seconds=12):
        with self.lock:
            self._stop()
            self.system, self.mic = _Level(), _Level()
            self._until = self.clock() + max(1, min(MAX_SECONDS, int(seconds or 12)))
            try:
                self._closers.append(self.backend.open_speaker(clean_name(speaker), self.system.feed))
            except Exception as e:  # noqa: BLE001
                self.system.error = "unsupported" if "unsupported" in str(e) else f"{type(e).__name__}: {str(e)[:120]}"
            try:
                self._closers.append(self.backend.open_mic(self.mic_index(mic), self.mic.feed))
            except Exception as e:  # noqa: BLE001
                self.mic.error = f"{type(e).__name__}: {str(e)[:120]}"
        return self.levels()

    def levels(self):
        with self.lock:
            if self._closers and self.clock() >= self._until:
                self._stop()
            return {"running": bool(self._closers), "system": self.system.view(), "mic": self.mic.view()}

    def stop(self):
        with self.lock:
            self._stop()
        return self.levels()

    def _stop(self):
        closers, self._closers = self._closers, []
        for c in closers:
            try:
                c()
            except Exception:  # noqa: BLE001
                pass
