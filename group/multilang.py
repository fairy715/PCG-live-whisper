"""PCG 集團版 r19：多語字幕——記下看字幕的人各自要看哪種語言，交給主程式另外翻譯。

字幕畫面（/simple/live，這台或分享出去的手機）連上 /ws 後送 {"action": "want_lang", "lang": "vi"}，
換語言時再送一次。這裡把所有連線要的語言合起來寫進 .extra_langs（例如 "id vi"），
主程式（translate_meeting.py 的 _PcgExtraSubs）每秒看一次，只把有人要看的語言多翻一份。
連線斷了就把那個人的語言拿掉；沒人要的語言不翻，省下 CPU。
"""
import os
import threading
from pathlib import Path

LANGS = ("zh", "id", "vi", "hi", "en")


class Wants:
    def __init__(self, flag_path):
        self.flag = Path(flag_path)
        self.lock = threading.Lock()
        self.by_conn = {}
        self.last = None
        try:
            self.flag.unlink()           # 上一次沒收乾淨的：一開始沒有人要看別的語言
        except OSError:
            pass

    def set(self, conn, lang):
        lang = str(lang or "").strip().lower()
        with self.lock:
            if lang in LANGS:
                self.by_conn[id(conn)] = lang
            else:
                self.by_conn.pop(id(conn), None)
            self._write()

    def drop(self, conn):
        with self.lock:
            if self.by_conn.pop(id(conn), None) is not None:
                self._write()

    def current(self):
        with self.lock:
            return sorted(set(self.by_conn.values()))

    def _write(self):
        text = " ".join(sorted(set(self.by_conn.values())))
        if text == self.last:
            return
        self.last = text
        try:
            if text:
                tmp = self.flag.with_name(self.flag.name + ".tmp")
                tmp.write_text(text, encoding="utf-8")
                os.replace(tmp, self.flag)
            else:
                self.flag.unlink()
        except OSError:
            pass
