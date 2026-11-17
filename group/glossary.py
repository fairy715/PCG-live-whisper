"""PCG 集團版 r23：詞庫——公司名、廠區、系統名稱、人名這些專有名詞，讓辨識與翻譯比較不會錯。

IT 在設定頁的「詞庫」編輯（也可以在公司共用資料夾放 glossary.txt 給所有電腦共用），一行一個詞：

    寶成 | 寶城 | 保成 = Pou Chen       ← 「|」後面是常被聽錯的寫法；「=」後面是指定譯法（選填）
    MES
    Sukabumi | Suka Bumi
    # 井字號開頭是註解；從 Excel 貼上（Tab 分隔：詞、譯法、聽錯的寫法…）也可以

程式用在三個地方（translate_meeting.py 的 _pcg_gloss_*）：
  1. 辨識時：詞庫的詞當提示詞（hotwords）給 Whisper，聽到相近的音優先選這些詞
  2. 辨識後：把「常被聽錯的寫法」換回正確的詞
  3. 翻譯時：句子裡有詞庫的詞 → 大模型照指定譯法翻、沒有譯法的保留原樣；本機 M2M100 先把詞換成譯法再翻

做法參考 tinglongWu 的 glossary.py（https://github.com/sunososobro-hub/tinglongwu ，MIT，(c) 2026 Alonso），格式與規則依集團版改寫。
"""
import re
import threading
from pathlib import Path

MAX_TEXT = 20000            # 設定頁存檔的上限（字元）
MAX_ENTRIES = 500
MAX_TERM = 60               # 一個詞（或譯法）最長
HOT_MAX_TERMS = 60          # 給 Whisper 的提示詞上限：太多反而變差
HOT_MAX_CHARS = 400
FILE_NAME = "glossary.txt"
SHARE_MAX_BYTES = 200_000

_CJK = re.compile(r"[぀-ヿ㐀-鿿豈-﫿가-힯]")
_PUNCT = re.compile(r"[\s,.;:!?、，。；：！？\"'「」『』()（）\-]+")


def _clean(s):
    return " ".join(str(s or "").replace("　", " ").split())[:MAX_TERM]


class Entry:
    __slots__ = ("src", "aliases", "dst")

    def __init__(self, src, aliases=(), dst=""):
        self.src, self.aliases, self.dst = src, tuple(aliases), dst


def parse(text):
    """文字 → [Entry]。看不懂的行略過；同一個詞出現兩次以先出現的為準"""
    out, seen = [], set()
    for raw in str(text or "")[:MAX_TEXT * 4].splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line and "\t" in line:                   # 從 Excel 貼上：詞、譯法、聽錯的寫法…
            cells = [_clean(c) for c in line.split("\t")]
            left, dst = [cells[0]] + cells[2:], cells[1] if len(cells) > 1 else ""
        else:
            lhs, _, rhs = line.partition("=")
            left, dst = [_clean(x) for x in lhs.replace("｜", "|").split("|")], _clean(rhs)
        left = [x for x in left if x]
        if not left:
            continue
        src, key = left[0], left[0].lower()
        if key in seen:
            continue
        seen.add(key)
        aliases = []
        for a in left[1:]:
            if a.lower() != key and a.lower() not in (x.lower() for x in aliases):
                aliases.append(a)
        out.append(Entry(src, aliases, dst if dst.lower() != key else ""))
        if len(out) >= MAX_ENTRIES:
            break
    return out


def _pattern(term):
    """找這個詞用的 regex：中日韓直接比對；英數字要是完整的字（MES 不會對到 times），3 個字母以內還要大小寫一樣（ME 不會對到 me）"""
    esc = re.escape(term)
    if _CJK.search(term):
        return re.compile(esc)
    flags = 0 if len(term) <= 3 else re.IGNORECASE
    return re.compile(r"(?<![A-Za-z0-9])" + esc.replace(r"\ ", r"\s+") + r"(?![A-Za-z0-9])", flags)


class Glossary:
    def __init__(self, entries=()):
        self.entries = list(entries)
        self._fix = [(_pattern(a), e.src) for e in self.entries for a in e.aliases]
        self._src = [(_pattern(e.src), e) for e in self.entries]
        self._dst = [(_pattern(e.dst), e) for e in self.entries if e.dst]
        self._terms = {t.lower() for e in self.entries for t in (e.src, e.dst) if t}

    def __bool__(self):
        return bool(self.entries)

    def __len__(self):
        return len(self.entries)

    def hotwords(self):
        """給 Whisper 的提示詞（前面的優先；有上限）"""
        out, n = [], 0
        for e in self.entries[:HOT_MAX_TERMS]:
            if n + len(e.src) + 2 > HOT_MAX_CHARS:
                break
            out.append(e.src)
            n += len(e.src) + 2
        return ", ".join(out)

    def fix(self, text):
        """辨識結果裡「常被聽錯的寫法」換回正確的詞"""
        for pat, src in self._fix:
            text = pat.sub(lambda m, s=src: s, text)
        return text

    def only_terms(self, text):
        """整段只有詞庫的詞（3 個以上）：多半是提示詞被模型照抄出來，不是真的有人說"""
        rest, hits = str(text or ""), 0
        for pat, _e in sorted(self._src, key=lambda x: -len(x[1].src)):
            rest, n = pat.subn(" ", rest)
            hits += n
        return hits >= 3 and not _PUNCT.sub("", rest)

    def _to_src(self, e, tgt):
        """翻成 tgt 時該用原詞而不是譯法嗎：原詞是中文而且翻成中文、原詞不是中文而且不是翻成中文以外…
        規則：原詞是中日韓文字 → 只有翻成中文（zh）時用原詞；原詞是英數字 → 翻成中文以外用原詞"""
        return (tgt == "zh") if _CJK.search(e.src) else (tgt != "zh")

    def terms_for(self, text, tgt):
        """這句話裡出現的詞 → ([(出現的寫法, 要翻成)], [保留原樣的詞])，給大模型的提示用"""
        pairs, keep = [], []
        for pat, e in self._src:
            if pat.search(text):
                if e.dst and not self._to_src(e, tgt):
                    pairs.append((e.src, e.dst))
                elif not _CJK.search(e.src) or tgt == "zh":
                    keep.append(e.src)
        for pat, e in self._dst:
            if pat.search(text) and self._to_src(e, tgt) and (e.dst, e.src) not in pairs:
                pairs.append((e.dst, e.src))
        return pairs, keep

    def substitute(self, text, tgt):
        """本機翻譯（M2M100 不能下指令）：翻譯前先把詞換成指定的寫法，模型多半會照抄英數字的專有名詞"""
        for pat, e in self._src:
            if e.dst and not self._to_src(e, tgt):
                text = pat.sub(lambda m, d=e.dst: d, text)
        for pat, e in self._dst:
            if self._to_src(e, tgt):
                text = pat.sub(lambda m, s=e.src: s, text)
        return text


def load(path):
    try:
        return Glossary(parse(Path(path).read_text(encoding="utf-8-sig")))
    except (OSError, ValueError):
        return Glossary()


def _read_share(share, box):
    try:
        p = Path(share) / FILE_NAME
        if p.is_file() and p.stat().st_size <= SHARE_MAX_BYTES:
            box.append(p.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        pass


def sync(base_dir, settings, timeout=3.0):
    """把「公司共用資料夾的 glossary.txt」＋「這台電腦 IT 設定頁填的」合起來寫到 group_data/glossary.txt（主程式讀這個檔）。
    共用資料夾連不上（或太慢，超過 timeout 秒）就用上一次讀到的。回傳 {"count", "share_count"}"""
    data = Path(base_dir) / "group_data"
    data.mkdir(parents=True, exist_ok=True)
    cache = data / "glossary-share.txt"
    share = str((settings or {}).get("update_share") or "").strip()
    share_text = ""
    if share:
        box = []
        th = threading.Thread(target=_read_share, args=(share, box), daemon=True)
        th.start()
        th.join(timeout)
        if box:
            share_text = box[0]
            try:
                cache.write_text(share_text, encoding="utf-8")
            except OSError:
                pass
        elif cache.is_file():
            try:
                share_text = cache.read_text(encoding="utf-8")
            except OSError:
                share_text = ""
    local = str((settings or {}).get("glossary") or "")
    merged = (local.strip() + "\n" + share_text.strip()).strip()      # 這台填的優先（同一個詞以先出現的為準）
    out = data / FILE_NAME
    try:
        if merged:
            tmp = out.with_name(out.name + ".tmp")
            tmp.write_text(merged + "\n", encoding="utf-8")
            tmp.replace(out)
        elif out.exists():
            out.unlink()
    except OSError:
        pass
    return {"count": len(parse(merged)), "share_count": len(parse(share_text))}
