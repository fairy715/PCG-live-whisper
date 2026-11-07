"""PCG 集團版：擋「瀏覽器裡別的網站」打這台電腦上的 WebUI。

WebUI 只看來源 IP 判斷「本機」：127.0.0.1 不用密碼、有管理權限。但同仁開著 PCG 時，
瀏覽器裡任何一個網頁都能對 http://localhost:19781 送請求，來源 IP 一樣是 127.0.0.1。
2026-11-07 實測（Chromium + 丟棄式 WebUI）：
  - 別的網站用 fetch(no-cors, text/plain) 改掉「字幕轉發」設定（/api/save-forward 自己讀 JSON，不看 Content-Type）
    → 之後的即時字幕會一句句送到對方的網址
  - 別的網站開 ws://localhost:19781/ws → 被接受而且是管理權限（可以讀即時字幕、停止字幕）
  - Host 標頭是別的網域（DNS rebinding）也照樣回應

這裡用一個 ASGI 中介層（HTTP 與 WebSocket 都經過，上游的 HTTP middleware 管不到 WebSocket）：
  1. Host 必須是 localhost、IP 位址、或這台電腦的名稱 → 擋 DNS rebinding（攻擊者只能用網域名稱）
  2. 會改東西的請求（POST/PUT/PATCH/DELETE）與 WebSocket：有 Origin 標頭時必須跟 Host 同一個網址
     → 擋別的網站代送請求、偷連字幕通道。沒有 Origin 的（主程式、命令列工具、懸浮字幕視窗）照常
手機或其他電腦用 IP 連進來看字幕（同仁頁面的「分享」QR Code 用的是 IP）：Host 是 IP、Origin 也是同一個 IP，不受影響。
"""
import ipaddress
import socket
from urllib.parse import urlsplit

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _split_host(value):
    """'Host' 標頭 → (主機名稱小寫, 連接埠或 None)；IPv6 的 [::1]:19781 也處理"""
    value = (value or "").strip().lower()
    if not value:
        return "", None
    try:
        u = urlsplit("//" + value)
        return (u.hostname or "").rstrip("."), u.port
    except ValueError:
        return value, None


def _is_ip(name):
    try:
        ipaddress.ip_address(name)
        return True
    except ValueError:
        return False


def own_names():
    """這台電腦自己的名稱（同仁可能用 http://電腦名稱:19781 連進來）"""
    names = {"localhost"}
    for fn in (socket.gethostname, socket.getfqdn):
        try:
            n = (fn() or "").strip().lower().rstrip(".")
            if n:
                names.add(n)
                names.add(n.split(".")[0])
        except OSError:
            pass
    return names


def host_ok(host_header, names=None):
    """Host 標頭可以接受嗎：沒有（非瀏覽器的舊客戶端）、localhost、IP、這台電腦的名稱"""
    name, _port = _split_host(host_header)
    if not name:
        return True
    if _is_ip(name) or name.endswith(".localhost"):
        return True
    return name in (names if names is not None else own_names())


def origin_ok(origin, host_header):
    """Origin 標頭（瀏覽器才會帶）是否跟 Host 同一個網址；沒有 Origin 的請求不在這裡擋"""
    if origin is None:
        return True
    origin = origin.strip()
    if not origin or origin.lower() == "null":
        return False                         # 沙箱 iframe、file:// 頁面送來的
    try:
        o = urlsplit(origin)
    except ValueError:
        return False
    if o.scheme not in ("http", "https") or not o.hostname:
        return False
    oh, op = o.hostname.lower().rstrip("."), o.port or (443 if o.scheme == "https" else 80)
    hh, hp = _split_host(host_header)
    if not hh:
        return False
    if hp is None:
        hp = op if oh == hh else -1
    return (oh, op) == (hh, hp)


class LocalGuard:
    """包在整個 WebUI 外面的 ASGI 中介層"""

    def __init__(self, app, names=None):
        self.app = app
        self.names = names if names is not None else own_names()

    async def __call__(self, scope, receive, send):
        kind = scope.get("type")
        if kind not in ("http", "websocket"):
            return await self.app(scope, receive, send)
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers") or []}
        host = headers.get("host", "")
        origin = headers.get("origin")
        bad = None
        if not host_ok(host, self.names):
            bad = "host"
        elif (kind == "websocket" or scope.get("method", "GET").upper() in UNSAFE_METHODS) \
                and not origin_ok(origin, host):
            bad = "origin"
        if bad is None:
            return await self.app(scope, receive, send)
        if kind == "websocket":
            await send({"type": "websocket.close", "code": 4003, "reason": "blocked"})
            return
        body = (b'{"ok":false,"code":"blocked_' + bad.encode() + b'",'
                b'"error":"request blocked (not from this app)"}')
        await send({"type": "http.response.start", "status": 403,
                    "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]})
        await send({"type": "http.response.body", "body": body})


def protect(app):
    """WebUI 的 FastAPI app 加上防護（webui.py 的集團版區塊呼叫）"""
    app.add_middleware(LocalGuard)
    return app
