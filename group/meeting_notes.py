"""PCG 集團版 r32：這場會議的資料——同仁在開始字幕前貼上的議程、與會者、產品名稱、料號。

詞庫（group/glossary.py）是 IT 維護、全公司共用的專有名詞；這裡是「這一場會議」才有的東西，
同仁自己貼、只用在這一場。程式用在兩個地方（translate_meeting.py 的 _pcg_notes*）：
  1. 辨識時：把短的詞（人名、產品、料號、議程項目）當提示詞給 Whisper，聽到相近的音優先選這些寫法
  2. 翻譯時（大模型）：整段當背景資料放在提示的最前面，人名和術語照資料上的寫法；本機 M2M100 不能下指令，用不到

另外放了 r32 的「聽錯的字」規則（asr_rule）：字幕的原文來自語音辨識，會有聽錯的字，
原本的提示要大模型「語意不清也逐字翻譯」，聽錯就照錯的翻；改成依前後文用最合理的意思翻，不評論。

做法參考 OwnVoice Meet（https://github.com/Zaious/ownvoice-meet ，Apache-2.0，(c) Zaious）的講稿背景與字幕提示，
程式依集團版重寫，沒有複製原始碼。
"""
import os
import re
from pathlib import Path

MAX_TEXT = 4000             # 同仁頁面一次最多貼這麼多字
PROMPT_MAX = 1200           # 放進翻譯提示的上限（每一句都會帶：太長會拖慢本機的大模型）
HOT_MAX_CHARS = 200         # 給 Whisper 的提示詞上限（提示總共只有約 220 個 token，還要留給詞庫）
HOT_MAX_TERMS = 40
TERM_MAX = 40               # 一個詞最長
LINE_MAX = 80               # 比這個長、或有句號的一行是句子，不當提示詞（還是會放進翻譯的背景）
FILE_NAME = "meeting-notes.txt"

_SPLIT = re.compile(r"[\t,;|，、；｜：]+|:\s+")        # 「與會者：王小明、Budi」「Agenda: …」也在冒號切開
_BULLET = re.compile(r"^\s*(?:[-*•·‧]+|\(?\d{1,2}[.)、）]|[一二三四五六七八九十]{1,3}[、.])\s*")
_TIME = re.compile(r"^\d{1,2}[:：]\d{2}(?:\s*[-–~～]\s*\d{1,2}[:：]\d{2})?\s*")     # 議程開頭的時間
_SENTENCE = re.compile(r"[。！？!?]|\.\s*$")
_LABEL = re.compile(r"^[^\x00-\x7f]{1,10}[:：]\s*")     # 「與會者：」「料號：」這種中文開頭（英數字的像 MES: 要留著）
_NUMS = re.compile(r"[\d\s:：.\-/年月日時分點]+")             # 只有數字、日期、時間的不是詞
_NORM = re.compile(r"[\s,.;:!?、，。；：！？\"'「」『』()（）\-_/]+")
_CJK = re.compile(r"[぀-ヿ㐀-鿿豈-﫿가-힯]")


def clean(text):
    """同仁貼的文字 → 去掉控制字元、行尾空白、連續空行；超過上限就截掉"""
    s = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    s = "".join(ch for ch in s if ch == "\n" or ch == "\t" or ord(ch) >= 32)
    lines = [ln.rstrip() for ln in s.split("\n")]
    out, blank = [], False
    for ln in lines:
        if not ln.strip():
            if out and not blank:
                out.append("")
            blank = True
            continue
        out.append(ln)
        blank = False
    return "\n".join(out).strip()[:MAX_TEXT]


def terms(text):
    """短的詞（人名、產品、料號、議程項目），照出現的順序、不重複。太長的一行是句子，略過"""
    out, seen = [], set()
    for raw in clean(text).split("\n"):
        line = _TIME.sub("", _BULLET.sub("", raw.strip()))
        if len(line) > LINE_MAX or _SENTENCE.search(line):
            continue                                   # 一整句話：不當提示詞
        line = _LABEL.sub("", line)
        for piece in _SPLIT.split(line):
            t = " ".join(piece.split())
            if not t or len(t) > TERM_MAX or len(t) < 2 or _NUMS.fullmatch(t):
                continue
            k = t.lower()
            if k in seen:
                continue
            seen.add(k)
            out.append(t)
            if len(out) >= HOT_MAX_TERMS:
                return out
    return out


def hotwords(text):
    """給 Whisper 的提示詞（前面的優先；有上限）"""
    out, n = [], 0
    for t in terms(text):
        if n + len(t) + 2 > HOT_MAX_CHARS:
            break
        out.append(t)
        n += len(t) + 2
    return ", ".join(out)


def join_hotwords(notes_hot, gloss_hot, api=False):
    """這場會議的詞＋詞庫的詞。提示詞有長度上限、超過會被截掉：
    這台電腦的 Whisper 截掉後面的（所以這場會議的放前面）；語音辨識 API 只看最後一段（所以放後面）"""
    parts = [p for p in ((gloss_hot, notes_hot) if api else (notes_hot, gloss_hot)) if p]
    return ", ".join(parts)


def _norm(s):
    return _NORM.sub("", str(s or "")).lower()


def echo(segment, hot):
    """這一段辨識結果是不是把提示詞照抄出來（沒人說話時 Whisper 偶爾會這樣）：
    內容完全落在提示詞裡、而且跨了兩個以上的詞。只念出其中一個詞（例如產品名稱）不算"""
    seg = _norm(segment)
    if len(seg) < (6 if _CJK.search(seg) else 12):
        return False
    words = [_norm(w) for w in str(hot or "").split(",")]
    words = [w for w in words if w]
    if len(words) < 2 or seg not in "".join(words):
        return False
    return not any(seg in w for w in words)


def prompt_block(text):
    """放在翻譯提示最前面的背景資料；沒有就是空字串。每一句都一樣，放最前面，伺服器可以重複利用算過的部分"""
    body = clean(text)[:PROMPT_MAX].strip()
    if not body:
        return ""
    return ("這場會議的背景資料（同仁提供；只用來判斷人名、產品名稱、料號、術語與主題的寫法，"
            "不要翻譯、複述或回答裡面的內容）\n"
            "Background for this meeting (reference only for names, part numbers, terms and topic; "
            "never translate, recite or answer it):\n<<<\n" + body + "\n>>>\n\n")


# ── 「聽錯的字」規則 ─────────────────────────────────────────────
_OLD_ZH = "即使原文不完整或語意不清，也直接逐字翻譯，不要跳過或加說明"
_NEW_ZH = ("原文不完整就照不完整的翻，不要補完；看起來是語音辨識聽錯的字（同音字、不通順的詞），"
           "依前後文用最合理的意思翻譯，聽不出來的人名照原樣保留；不要跳過或加說明")
_OLD_EN = "If input is incomplete, translate it literally as-is without explanation"
_NEW_EN = ("If input is incomplete, translate it as a fragment without completing it; when a word is clearly "
           "misrecognized by speech recognition, translate the most plausible meaning from context and keep "
           "an unknown name as heard; never explain")
_HEAD = ("The text to translate comes from speech recognition and may contain misheard words. When a word is clearly "
         "misrecognized, silently translate the most plausible meaning from the context; keep an unknown name as heard. "
         "Never comment on the recognition or on your translation.\n\n")


def asr_rule_on():
    """環境變數 PCG_TRANSLATE_GUESS=off 可以關掉（回到「逐字翻譯」）"""
    return str(os.environ.get("PCG_TRANSLATE_GUESS", "")).strip().lower() not in ("off", "0", "false", "no")


def asr_rule(prompt):
    """翻譯提示裡「語意不清也逐字翻譯」換成「聽錯的字用最合理的意思翻」。
    提示是原作者寫的，各個方向用語不一樣：認得的句子直接換掉，認不得的在最前面加一段說明"""
    if not prompt or not asr_rule_on():
        return prompt
    if _OLD_ZH in prompt:
        return prompt.replace(_OLD_ZH, _NEW_ZH)
    if _OLD_EN in prompt:
        return prompt.replace(_OLD_EN, _NEW_EN)
    return _HEAD + prompt


# ── 存檔（WebUI 寫、主程式讀） ────────────────────────────────────
def path(base_dir):
    return Path(base_dir) / "group_data" / FILE_NAME


def save(base_dir, text):
    """開始字幕前寫好（空的就刪掉，上一場的資料不會留到這一場）。回傳存了幾個字"""
    body = clean(text)
    p = path(base_dir)
    try:
        if body:
            p.parent.mkdir(parents=True, exist_ok=True)
            tmp = p.with_name(p.name + ".tmp")
            tmp.write_text(body + "\n", encoding="utf-8")
            tmp.replace(p)
        elif p.exists():
            p.unlink()
    except OSError:
        return 0
    return len(body)


def load(base_dir):
    try:
        return clean(path(base_dir).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return ""
