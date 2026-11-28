"""PCG 集團版 r34：沒看懂？AI 重新翻譯並解釋——把剛才那一段交給大模型整段重新翻譯，並解釋專業用語。

即時字幕是一句一句翻的：前後文容易斷、聽錯的字照錯的翻、數字和料號偶爾漏掉。看字幕的人覺得剛才那段沒看懂時
按一下，程式把最近幾句的「原文」合成一段，請大模型：
  1. 依前後文整段重新翻譯成看的人的語言（數字、日期、金額、料號、人名照原樣，一個都不漏）
  2. 有專業用語或縮寫就用一兩句話解釋
只在伺服器模式（有大模型）能用；本機模式的 M2M100 不能下指令。翻譯交給正在跑字幕的主程式（group/reply.py 的通道）。

做法參考 SubKun Live Transcribe（https://subkun.com/zh-tw/live-transcribe/）的「沒聽懂？AI 翻譯解釋」，
提示與程式是依集團版自己寫的。
"""
import re

LANG_NAME = {"zh": "台灣繁體中文", "en": "English", "id": "Bahasa Indonesia", "vi": "Tiếng Việt", "hi": "हिन्दी",
             "ja": "日本語", "ko": "한국어"}
# 輸出的兩個小標題，用看的人的語言
LABELS = {"zh": ("翻譯", "說明"), "en": ("Translation", "Notes"), "id": ("Terjemahan", "Penjelasan"),
          "vi": ("Bản dịch", "Giải thích"), "hi": ("अनुवाद", "व्याख्या"), "ja": ("翻訳", "解説"), "ko": ("번역", "설명")}
MAX_LINES = 6               # 最多拿最近幾句
WINDOW_SEC = 120.0          # 只拿最後一句往前這麼多秒以內的
MAX_CHARS = 1500            # 這一段最長
MAX_OUT = 2000              # 回答最長（超過就截掉）
_THINK = re.compile(r"<think>[\s\S]*?</think>|<think>[\s\S]*", re.I)


def passage(lines, max_lines=MAX_LINES, window=WINDOW_SEC, max_chars=MAX_CHARS):
    """逐字稿的每一句（transcript.fold 的結果）→ 剛才那一段的原文（一行一句，前面標語言）。
    只拿聽到的話（打字回覆不算）；沒有就回空字串"""
    heard = [x for x in lines if x.get("k") == "s" and str(x.get("src") or "").strip()]
    if not heard:
        return ""
    last_t = heard[-1].get("t") or 0
    picked = [x for x in heard[-max_lines:] if last_t - (x.get("t") or 0) <= window]
    out = []
    for x in picked:
        out.append(f"[{x.get('src_tag') or '?'}] {' '.join(str(x['src']).split())}")
    text = "\n".join(out)
    while len(text) > max_chars and len(out) > 1:          # 太長：從最舊的丟
        out.pop(0)
        text = "\n".join(out)
    return text[-max_chars:]


def prompt(passage_text, tgt, extra=""):
    """給大模型的提示。extra＝這場會議的背景資料與詞庫（主程式給的，放最前面）"""
    tgt = tgt if tgt in LANG_NAME else "zh"
    name, (l1, l2) = LANG_NAME[tgt], LABELS[tgt]
    zh_rule = "用台灣繁體中文與台灣用語，不要用簡體字。\n" if tgt == "zh" else ""
    return (
        f"{extra}"
        "你是會議的口譯員。下面是會議裡剛才說的一段話，一行一句，前面的方括號是那一句的語言。"
        "文字來自語音辨識，可能有聽錯的字、同音字，句子也可能被切斷。\n"
        f"看字幕的人沒看懂這一段。請用 {name} 回答，只寫下面兩個部分：\n"
        f"{l1}：依前後文把這一段完整、準確地重新翻譯成 {name}，寫成通順的一段話。"
        "看起來是聽錯的字，用最合理的意思；數字、日期、時間、金額、料號、人名一個都不能漏，照原樣保留。"
        f"原文已經是 {name} 的句子，就把它整理通順。不要加原文沒有的內容。\n"
        f"{l2}：這一段裡有專業用語、縮寫或代號時，各用一句話解釋；沒有就整個省略這個部分。\n"
        f"{zh_rule}"
        "不要寫開場白、不要評論辨識的品質、不要輸出思考過程。格式：\n"
        f"{l1}：…\n{l2}：…\n\n"
        f"這一段話：\n{passage_text}\n"
    )


def clean(text):
    """大模型的回答 → 給畫面用的文字（拿掉思考過程、Markdown 的粗體記號、多餘的空行）"""
    s = _THINK.sub("", str(text or ""))
    s = s.replace("**", "").replace("\r", "")
    lines = [ln.rstrip() for ln in s.split("\n")]
    out, blank = [], False
    for ln in lines:
        if not ln.strip():
            blank = bool(out)
            continue
        if blank:
            out.append("")
        out.append(ln.strip())
        blank = False
    return "\n".join(out).strip()[:MAX_OUT]
