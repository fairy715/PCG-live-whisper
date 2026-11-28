"""PCG 集團版 r33：即時字幕的逐字稿——字幕結束後可以下載這一場的文字，伺服器模式可以直接產會議紀錄。

原本即時字幕一結束，同仁頁面就沒有東西可以拿；要會議紀錄得另外錄音、再上傳。
這裡在 WebUI 這一端把每一句字幕記下來（主程式送給字幕畫面的同一份事件），所以：
  - 不管主程式用哪一種辨識方式（Whisper、Moonshine、GPU 伺服器、語音辨識 API）都記得到
  - 打字回覆（r32）的句子也記在裡面，標「打字」
  - 「半句換整句」照字幕畫面同一條規則：畫面上被取代的半句，逐字稿裡也不會留

每一場存成 group_data/live/<開始時間>.jsonl（一行一個事件，邊開會邊寫，程式當掉也留得住），只留最近 10 場。
下載的文字檔是原作者記錄檔的格式（[時:分:秒] [語言] 內容），可以直接交給主程式的 --summarize 產會議紀錄。
"""
import json
import re
import threading
import time
from pathlib import Path

KEEP = 10                   # 留最近幾場
MERGE_SEC = 30.0            # 半句換整句：同一路、這麼多秒以內
MAX_EVENTS = 20000          # 一場最多記這麼多句（八小時的會議大約五千句）
_ID_RE = re.compile(r"^\d{8}_\d{6}$")
_NORM = re.compile(r"[^0-9a-zऀ-ॿÀ-ỹ぀-ヿ㐀-鿿가-힯]")
_CJK = re.compile(r"[぀-ヿ㐀-鿿가-힯]")
LANG_TAG = {"zh": "中", "en": "EN", "id": "ID", "vi": "VI", "hi": "HI", "ja": "日", "ko": "韓"}
LANG_NAME = {"zh": "中文", "en": "英文", "id": "印尼文", "vi": "越南文", "hi": "印地語", "ja": "日文", "ko": "韓文",
             "nan": "台語"}


def _norm(s):
    return _NORM.sub("", str(s or "").lower())


def finishes(old, new):
    """new 是不是 old 這半句講完的版本（與字幕畫面 live.html 的 finishes 同一條規則）"""
    o, n = _norm(old), _norm(new)
    if len(o) < 2 or len(n) <= len(o):
        return False
    k = 0
    while k < len(o) and o[k] == n[k]:
        k += 1
    tail = 2 if _CJK.search(o) else 4
    return k >= 2 and k * 2 >= len(o) and (k * 10 >= len(o) * 7 or k >= len(o) - tail)


def mode_title(mode):
    """主程式的 --mode → 給人看的說明（印尼文 → 中文、印尼文 ↔ 中文、中文轉錄）"""
    m = str(mode or "")
    for sep, arrow in (("2", " → "), ("_", " ↔ ")):
        if sep in m:
            a, b = m.split(sep, 1)
            if a in LANG_NAME and b in LANG_NAME:
                return LANG_NAME[a] + arrow + LANG_NAME[b]
    return LANG_NAME[m] + "轉錄" if m in LANG_NAME else m


def fold(raw):
    """原始事件（照時間）→ 逐字稿的每一句：半句換整句、把另外翻的語言接到那一句後面"""
    out, by_id = [], {}
    for ev in raw:
        kind = ev.get("k")
        if kind == "x":                               # 多語字幕另外翻的一份
            line = by_id.get(ev.get("id"))
            if line is not None and ev.get("text"):
                line.setdefault("extra", {})[ev.get("tag") or ""] = ev["text"]
            continue
        if kind not in ("s", "t"):
            continue
        line = dict(ev)
        if kind == "s":
            src = ev.get("source") or ""
            for i in range(len(out) - 1, max(-1, len(out) - 7), -1):
                p = out[i]
                if p.get("k") != "s" or (p.get("source") or "") != src:
                    continue
                if (ev.get("t") or 0) - (p.get("t") or 0) < MERGE_SEC and finishes(p.get("src"), ev.get("src")):
                    out[i] = line
                    line = None
                break
            if line is None:
                if ev.get("id") is not None:
                    by_id[ev["id"]] = out[i]
                continue
        out.append(line)
        if ev.get("id") is not None:
            by_id[ev["id"]] = line
    return out


TAG_LANG = {"中": "zh", "台": "zh", "EN": "en", "ID": "id", "VI": "vi", "HI": "hi", "日": "ja", "韓": "ko"}


def _versions(ln):
    """這一句有哪幾種語言的版本：[(語言代碼, 標籤, 文字)]，原文在前"""
    out = []
    for tag, text in ((ln.get("src_tag"), ln.get("src")), (ln.get("dst_tag"), ln.get("dst"))):
        if tag and text and text != "（翻譯失敗）":
            out.append((TAG_LANG.get(tag, tag), tag, text))
    for tag, text in sorted((ln.get("extra") or {}).items()):
        if tag and text and tag not in (ln.get("src_tag"), ln.get("dst_tag")):
            out.append((TAG_LANG.get(tag, tag), tag, text))
    return out


def langs_of(lines):
    """這一場出現過的語言（代碼），照出現的順序"""
    out = []
    for ln in lines:
        for code, _tag, _text in _versions(ln):
            if code not in out:
                out.append(code)
    return out


def to_text(header, lines, only=None):
    """逐字稿的文字檔（原作者記錄檔的格式，可以交給 --summarize）。
    only＝語言代碼（r34）：每一句只留那一種語言的版本（原文或譯文），沒有那種語言的句子略過"""
    if only:
        return _to_text_one(header, lines, only)
    out = []
    started = header.get("started") or 0
    title = mode_title(header.get("mode"))
    out.append("PCG 會議翻譯 即時字幕逐字稿　" + time.strftime("%Y-%m-%d %H:%M", time.localtime(started))
               + ("　" + title if title else ""))
    out.append("")
    for ln in lines:
        ts = ln.get("ts") or time.strftime("%H:%M:%S", time.localtime(ln.get("t") or started))
        mark = "（打字）" if ln.get("k") == "t" else ""
        if ln.get("src"):
            out.append(f"[{ts}] [{ln.get('src_tag') or '?'}] {mark}{ln['src']}")
        if ln.get("dst") and ln["dst"] != "（翻譯失敗）":
            out.append(f"[{ts}] [{ln.get('dst_tag') or '?'}] {ln['dst']}")
        for tag, text in sorted((ln.get("extra") or {}).items()):
            if tag and tag not in (ln.get("src_tag"), ln.get("dst_tag")):
                out.append(f"[{ts}] [{tag}] {text}")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def _to_text_one(header, lines, only):
    started = header.get("started") or 0
    out = ["PCG 會議翻譯 即時字幕逐字稿　" + time.strftime("%Y-%m-%d %H:%M", time.localtime(started))
           + "　" + LANG_NAME.get(only, only), ""]
    for ln in lines:
        hit = next((v for v in _versions(ln) if v[0] == only), None)
        if not hit:
            continue
        ts = ln.get("ts") or time.strftime("%H:%M:%S", time.localtime(ln.get("t") or started))
        mark = "（打字）" if ln.get("k") == "t" and hit[1] == ln.get("src_tag") else ""
        out.append(f"[{ts}] {mark}{hit[2]}")
    return "\n".join(out).rstrip() + "\n"


class Recorder:
    def __init__(self, base_dir):
        self.dir = Path(base_dir) / "group_data" / "live"
        self.lock = threading.Lock()
        self.sid = None
        self.count = 0
        self.last = 0.0              # 最後一次有字幕（或這一場開始）的時間：太久沒有字幕自動結束（r33）看這個

    # ── 寫 ──
    def _path(self, sid):
        return self.dir / f"{sid}.jsonl"

    def _append(self, obj):
        if self.sid is None or self.count >= MAX_EVENTS:
            return
        try:
            with open(self._path(self.sid), "a", encoding="utf-8") as f:
                f.write(json.dumps(obj, ensure_ascii=False) + "\n")
            self.count += 1
        except OSError:
            pass

    def start(self, mode):
        """新的一場（主程式送來 started）"""
        with self.lock:
            now = time.time()
            sid = time.strftime("%Y%m%d_%H%M%S", time.localtime(now))
            try:
                self.dir.mkdir(parents=True, exist_ok=True)
                self._path(sid).write_text(json.dumps({"k": "h", "started": now, "mode": str(mode or "")},
                                                      ensure_ascii=False) + "\n", encoding="utf-8")
            except OSError:
                self.sid = None
                return
            self.sid, self.count, self.last = sid, 0, now
            self._prune()

    def _prune(self):
        try:
            files = sorted(p for p in self.dir.glob("*.jsonl") if _ID_RE.match(p.stem))
        except OSError:
            return
        for p in files[:-KEEP]:
            try:
                p.unlink()
            except OSError:
                pass

    def on_event(self, line):
        """WebUI 收到主程式的每一個事件都給這裡看一眼（只記，不攔）"""
        if not isinstance(line, str) or not line.startswith('{"type": "'):
            return
        head = line[10:32]
        if head.startswith("started"):
            try:
                self.start(json.loads(line).get("mode"))
            except ValueError:
                pass
        elif head.startswith("transcription_extra"):
            try:
                ev = json.loads(line)
            except ValueError:
                return
            with self.lock:
                self._append({"k": "x", "id": ev.get("id"), "tag": ev.get("lang"), "text": ev.get("text")})
        elif head.startswith("transcription"):
            try:
                ev = json.loads(line)
            except ValueError:
                return
            if not ev.get("src_text") and not ev.get("dst_text"):
                return
            with self.lock:
                self.last = time.time()
                self._append({"k": "s", "t": time.time(), "ts": ev.get("timestamp"), "id": ev.get("id"),
                              "source": ev.get("source"), "src_tag": ev.get("src_lang"), "src": ev.get("src_text"),
                              "dst_tag": ev.get("dst_lang"), "dst": ev.get("dst_text")})

    def typed(self, src, tgt, text, out):
        """打字回覆（r32）的一句"""
        with self.lock:
            self.last = time.time()
            self._append({"k": "t", "t": time.time(), "src_tag": LANG_TAG.get(src, src), "src": text,
                          "dst_tag": LANG_TAG.get(tgt, tgt), "dst": out})

    # ── 讀 ──
    def _read(self, sid):
        header, raw = {}, []
        try:
            with open(self._path(sid), encoding="utf-8") as f:
                for row in f:
                    try:
                        ev = json.loads(row)
                    except ValueError:
                        continue
                    if ev.get("k") == "h":
                        header = ev
                    else:
                        raw.append(ev)
        except OSError:
            return None, []
        return header, raw

    def sessions(self):
        """最近的幾場（新的在前）：[{"id", "started", "mode", "title", "lines", "current"}]；沒有內容的不列"""
        try:
            ids = sorted((p.stem for p in self.dir.glob("*.jsonl") if _ID_RE.match(p.stem)), reverse=True)
        except OSError:
            return []
        out = []
        for sid in ids[:KEEP]:
            header, raw = self._read(sid)
            if header is None:
                continue
            n = len(fold(raw))
            if n:
                out.append({"id": sid, "started": header.get("started") or 0, "mode": header.get("mode") or "",
                            "title": mode_title(header.get("mode")), "lines": n, "current": sid == self.sid,
                            "langs": langs_of(fold(raw))})
        return out

    def text(self, sid, only=None):
        """某一場的逐字稿文字；沒有這一場（或沒有內容）回 None。only＝只留這一種語言（r34）"""
        if not _ID_RE.match(str(sid or "")):
            return None
        header, raw = self._read(sid)
        lines = fold(raw) if header is not None else []
        if not lines or (only and only not in langs_of(lines)):
            return None
        return to_text(header, lines, only)

    def recent(self):
        """正在進行的這一場的每一句（給「AI 重新翻譯並解釋」拿剛才那一段，r34）；沒有就是空的"""
        if self.sid is None:
            return []
        header, raw = self._read(self.sid)
        return fold(raw[-80:]) if header is not None else []
