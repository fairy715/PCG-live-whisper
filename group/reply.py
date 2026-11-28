"""PCG 集團版 r32：打字回覆——在字幕畫面用自己的語言打字，翻成對方的語言用大字顯示。

口音重、環境吵、辨識不出來時的退路：打字 → 翻譯 → 念出來、給對方看，或複製貼到 Teams 的聊天。
翻譯交給正在跑字幕的主程式（它已經載入翻譯模型，或連著大模型）：
  1. 這裡把要翻的句子寫進 .pcg_say（{"id", "text", "src", "tgt", "at"}）
  2. 主程式（translate_meeting.py 的 _PcgReply）每 1/4 秒看一次，翻好用 pcg_reply 事件送回 WebUI
  3. WebUI 收到事件交給 on_event：對回等待中的那一次請求，不轉給看字幕的人
所以只有字幕進行中才能用，而且只能在收音的這台電腦上打字（分享出去的手機不行）。

做法參考 OwnVoice Meet（https://github.com/Zaious/ownvoice-meet ，Apache-2.0，(c) Zaious）的回覆視窗，
程式依集團版重寫，沒有複製原始碼。
"""
import asyncio
import json
import os
import time
from pathlib import Path

FILE_NAME = ".pcg_say"
EVENT_PREFIX = '{"type": "pcg_reply"'
MAX_TEXT = 300              # 一次最多打這麼多字（即時字幕的翻譯模型一次一句）
TIMEOUT = 30.0              # 本機翻譯模型第一次用某個方向要載入，給它一點時間
LANGS = ("zh", "en", "id", "vi", "hi", "ja", "ko")


def pair(mode):
    """主程式的 --mode → {"me": 我的語言, "other": 對方的語言}；只辨識不翻譯的（大家都說中文）回 None。
    單向 A2B＝對方說 A、我看 B；雙向與教室模式 A_B＝對方 A、我 B"""
    m = str(mode or "")
    for sep in ("2", "_"):
        if sep in m:
            a, b = m.split(sep, 1)
            if a in LANGS and b in LANGS and a != b:
                return {"me": b, "other": a}
    return None


def clean(text):
    return " ".join(str(text or "").split())[:MAX_TEXT]


class Desk:
    def __init__(self, base_dir):
        self.flag = Path(base_dir) / FILE_NAME
        self.seq = int(time.time() * 1000) % 1_000_000_000      # 程式重開後編號不會跟上一次的重複
        self.waiting = {}
        self._lock = None
        self._clear()

    def _clear(self):
        try:
            self.flag.unlink()
        except OSError:
            pass

    def _write(self, req):
        tmp = self.flag.with_name(self.flag.name + ".tmp")
        tmp.write_text(json.dumps(req, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self.flag)

    async def ask(self, text, src, tgt, timeout=TIMEOUT, kind="say"):
        """請主程式把 text 從 src 翻成 tgt。回傳主程式的事件（{"ok": True, "text": …}）；
        沒有回應回 {"ok": False, "code": "say_timeout"}。一次一句：前一句還沒回來時排隊。
        kind="explain"（r34）：text 是剛才那一段，請大模型重新翻譯成 tgt 並解釋（group/explain.py）"""
        if self._lock is None:
            self._lock = asyncio.Lock()
        async with self._lock:
            self.seq += 1
            rid = self.seq
            fut = asyncio.get_running_loop().create_future()
            self.waiting[rid] = fut
            try:
                await asyncio.to_thread(self._write, {"id": rid, "kind": kind, "text": text, "src": src,
                                                      "tgt": tgt, "at": time.time()})
                return await asyncio.wait_for(fut, timeout)
            except asyncio.TimeoutError:
                return {"ok": False, "code": "say_timeout"}
            except OSError:
                return {"ok": False, "code": "say_failed"}
            finally:
                self.waiting.pop(rid, None)
                self._clear()

    def on_event(self, line):
        """WebUI 收到主程式的每一個事件都先問這裡：是打字回覆的結果就收下（回 True＝不要轉給看字幕的人）"""
        if not isinstance(line, str) or not line.startswith(EVENT_PREFIX):
            return False
        try:
            ev = json.loads(line)
        except ValueError:
            return True
        fut = self.waiting.get(ev.get("id"))
        if fut is not None and not fut.done():
            fut.set_result(ev)
        return True
