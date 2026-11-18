"""PCG 集團版 r24：語音辨識 API（OpenAI 相容的 /audio/transcriptions）。

IT 設定頁填「網址、金鑰、模型」之後，語音辨識改交給這個 API：
  - OpenAI（https://api.openai.com/v1，付費，聲音會送出公司）
  - Groq（https://api.groq.com/openai/v1，Whisper large-v3；有免費額度、有用量上限，聲音會送出公司；r26）
  - 公司內部的辨識服務（RTX Spark、其他團隊架的 OpenAI 相容伺服器；聲音留在公司內）
主程式（translate_meeting.py 的 _FwModel）把切好的每一段聲音送過來；API 連不上、金鑰不對時那一段改回這台電腦辨識，字幕不會斷。
這個檔只做 HTTP 與格式轉換，主程式與 IT 設定頁的「測試連線」共用。
"""
import io
import ipaddress
import json
import uuid
import wave
from urllib import error as _uerr
from urllib import request as _ureq
from urllib.parse import urlsplit

DEFAULT_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-transcribe"
GROQ_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = "whisper-large-v3-turbo"
LIMIT_WAIT = (15, 600)      # 用量達到上限（HTTP 429）時暫停幾秒：照伺服器說的 Retry-After，限制在這個範圍；沒說就 60 秒
SR = 16000
MAX_CHUNK_S = 25.0          # 一次送出去的聲音最長幾秒（長錄音在停頓的地方切開）
LANGS = {"zh": "zh", "en": "en", "ja": "ja", "ko": "ko", "id": "id", "vi": "vi", "hi": "hi", "nan": "zh"}


class ApiError(Exception):
    def __init__(self, status, message, retry_after=None):
        super().__init__(f"HTTP {status}：{message}" if status else message)
        self.status, self.message, self.retry_after = status, message, retry_after

    @property
    def limited(self):
        """用量達到上限（免費額度的每分鐘、每天上限）：過一陣子就能再用"""
        return self.status == 429

    @property
    def wait(self):
        """用量達到上限時，建議暫停幾秒"""
        lo, hi = LIMIT_WAIT
        try:
            return int(min(hi, max(lo, float(self.retry_after)))) if self.retry_after is not None else 60
        except (TypeError, ValueError):
            return 60

    @property
    def fatal(self):
        """金鑰不對、沒有權限、模型不存在：重試也沒用"""
        return self.status in (401, 403, 404)


def clean_url(url):
    url = str(url or "").strip().rstrip("/")
    for tail in ("/audio/transcriptions", "/audio"):
        if url.endswith(tail):
            url = url[:-len(tail)]
    return url


def default_model(url):
    """模型沒填時用哪一個：依網址（Groq 沒有 gpt-4o-transcribe）"""
    try:
        host = (urlsplit(clean_url(url)).hostname or "").lower()
    except ValueError:
        host = ""
    return GROQ_MODEL if host == "groq.com" or host.endswith(".groq.com") else DEFAULT_MODEL


def _private_host(host):
    host = (host or "").strip("[]").lower()
    if not host:
        return False
    if host == "localhost" or host.endswith(".local") or "." not in host and ":" not in host:
        return True
    try:
        ip = ipaddress.ip_address(host)
        return ip.is_private or ip.is_loopback or ip.is_link_local
    except ValueError:
        return False


def scope(url, internal=False):
    """聲音送到哪裡："internal"（公司內部：內部 IP、主機名稱，或 IT 勾了「這是公司內部的服務」）／"external" """
    try:
        host = urlsplit(clean_url(url)).hostname
    except ValueError:
        host = ""
    return "internal" if internal or _private_host(host) else "external"


def check_url(url, internal=False):
    """回傳 (整理過的網址, 錯誤代碼或 "")。外部服務一定要 https（金鑰與聲音不可以明碼傳）"""
    url = clean_url(url)
    try:
        u = urlsplit(url)
    except ValueError:
        return url, "bad_asr_url"
    if u.scheme not in ("http", "https") or not u.hostname or len(url) > 300 or any(c in url for c in " \r\n\t\"<>"):
        return url, "bad_asr_url"
    if u.scheme == "http" and scope(url, internal) == "external":
        return url, "asr_url_https"
    return url, ""


def wav_bytes(audio16k):
    """16 kHz 單聲道 float32（-1～1）→ 16-bit PCM 的 WAV"""
    import numpy as np
    pcm = (np.clip(np.asarray(audio16k, dtype=np.float32), -1.0, 1.0) * 32767.0).astype("<i2")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return buf.getvalue()


def _multipart(fields, wav):
    boundary = "----pcg" + uuid.uuid4().hex
    out = []
    for k, v in fields.items():
        if v is None or v == "":
            continue
        out.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode("utf-8"))
    out.append(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="audio.wav"\r\n'
               f'Content-Type: audio/wav\r\n\r\n'.encode("utf-8") + wav + b"\r\n")
    out.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(out), f"multipart/form-data; boundary={boundary}"


def post(cfg, wav, language=None, prompt=None, timeout=20, fmt="json", opener=None):
    """送一段 WAV，回傳 API 的 JSON（dict）。cfg：{"url", "model", "key"}。出錯丟 ApiError"""
    body, ctype = _multipart({"model": cfg.get("model") or default_model(cfg.get("url")), "response_format": fmt,
                              "language": LANGS.get(language or "", ""), "prompt": (prompt or "")[:800]}, wav)
    req = _ureq.Request(clean_url(cfg["url"]) + "/audio/transcriptions", data=body, method="POST")
    req.add_header("Content-Type", ctype)
    req.add_header("Accept", "application/json")
    req.add_header("User-Agent", "pcg-meeting-translator")
    if cfg.get("key"):
        req.add_header("Authorization", "Bearer " + str(cfg["key"]))
    try:
        with (opener or _ureq.urlopen)(req, timeout=timeout) as resp:
            raw = resp.read(8 * 1024 * 1024)
    except _uerr.HTTPError as e:
        try:
            detail = e.read(4000).decode("utf-8", "replace")
            j = json.loads(detail)
            detail = (j.get("error") or {}).get("message") if isinstance(j.get("error"), dict) else (j.get("error") or j.get("message") or detail)
        except Exception:  # noqa: BLE001
            detail = getattr(e, "reason", "") or ""
        try:
            after = float((e.headers.get("Retry-After") or "").strip())
        except (AttributeError, TypeError, ValueError):
            after = None
        raise ApiError(e.code, str(detail or "")[:300], after) from None
    except Exception as e:  # noqa: BLE001  逾時、連不上、憑證問題
        raise ApiError(0, f"{type(e).__name__}: {str(e)[:200]}") from None
    try:
        data = json.loads(raw.decode("utf-8", "replace"))
    except ValueError:
        text = raw.decode("utf-8", "replace").strip()
        if not text or text.startswith("<"):
            raise ApiError(0, "回應不是 JSON（網址可能不是語音辨識 API）") from None
        data = {"text": text}                       # 有些伺服器固定回純文字
    if not isinstance(data, dict):
        raise ApiError(0, "回應格式不對")
    return data


def wants_segments(model):
    """哪些模型可以要每一句的時間（verbose_json）：whisper 系列；gpt-4o-transcribe 這類只回整段文字"""
    return "whisper" in str(model or "").lower()


def pieces(data, offset, end):
    """API 回應 → [(開始秒, 結束秒, 文字)]；offset／end 是這一塊聲音在整段裡的位置（秒）"""
    out = []
    segs = data.get("segments")
    if isinstance(segs, list) and segs:
        for s in segs:
            if isinstance(s, dict) and str(s.get("text") or "").strip():
                try:
                    a, b = float(s.get("start") or 0.0), float(s.get("end") or 0.0)
                except (TypeError, ValueError):
                    a, b = 0.0, end - offset
                out.append((offset + a, min(end, offset + max(b, a)), str(s["text"]).strip()))
        if out:
            return out
    text = str(data.get("text") or "").strip()
    return [(offset, end, text)] if text else []


def chunks(spans, total, max_s=MAX_CHUNK_S, pad=0.2):
    """VAD 找到的語音區段（取樣點）→ 一塊一塊要送出去的範圍（取樣點），每塊不超過 max_s 秒，盡量切在停頓的地方"""
    limit, padn, out = int(max_s * SR), int(pad * SR), []      # out：(開始, 結束, 是不是硬切的)
    cur_s = cur_e = None
    for s, e in spans:
        while e - s > limit:                        # 一口氣講超過上限：硬切（硬切的邊不多留，免得同一個字出現兩次）
            if cur_s is not None:
                out.append((cur_s, cur_e, False))
                cur_s = cur_e = None
            out.append((s, s + limit, True))
            s += limit
        if cur_s is None:
            cur_s, cur_e = s, e
        elif e - cur_s <= limit:
            cur_e = e
        else:
            out.append((cur_s, cur_e, False))
            cur_s, cur_e = s, e
    if cur_s is not None:
        out.append((cur_s, cur_e, False))
    return [((s, e) if hard else (max(0, s - padn), min(total, e + padn))) for s, e, hard in out if e > s]


def test(cfg, opener=None):
    """IT 設定頁的「測試連線」：送 1 秒的靜音，看網址、金鑰、模型對不對。回傳 {"ok", "status", "message"}"""
    import numpy as np
    try:
        post(cfg, wav_bytes(np.zeros(SR, np.float32)), timeout=20, opener=opener)
        return {"ok": True, "status": 200, "message": ""}
    except ApiError as e:
        return {"ok": False, "status": e.status, "message": e.message}
