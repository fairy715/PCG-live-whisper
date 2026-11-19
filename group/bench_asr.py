"""PCG 集團版：用公開的語音資料集比較各個語音辨識模型的錯字率。

公司的錄音沒有「標準答案」（正確的逐字稿），所以改用公開資料集：每一句都附正確的文字，
同一批句子給每個模型辨識一次，算錯字率，就知道換模型到底好多少。在 GitHub 的機器上跑
（.github/workflows/asr-benchmark.yml），不會用到公司的任何資料。

資料集
  - FLEURS（Google，CC-BY 4.0）：每種語言的朗讀句子。中文是中國大陸的華語（簡體），不是台灣華語
  - ASCEND（CAiRE，CC-BY-SA 4.0）：中英夾雜的對話。拿得到才用，拿不到就略過

要知道的限制
  - 公開資料是清楚的朗讀或對話，沒有工廠術語、口音、會議室的回音：錯字率會比實際開會低，
    看的是「模型之間差多少」，不是「實際開會會錯多少」
  - 在 GitHub 的機器上只有 CPU，「花的時間」不代表有顯示卡時的速度
  - 每種語言只取幾十句，差距很小（一兩個百分點）時不能下結論

用法：python group/bench_asr.py --out bench --langs zh,id,vi,hi,en --n 40
"""
import argparse
import io
import json
import re
import shutil
import sys
import tarfile
import time
import unicodedata
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

FLEURS = {"zh": "cmn_hans_cn", "id": "id_id", "vi": "vi_vn", "hi": "hi_in", "en": "en_us"}
LANG_NAME = {"zh": "中文（FLEURS，大陸華語朗讀）", "id": "印尼文（FLEURS）", "vi": "越南文（FLEURS）",
             "hi": "印地語（FLEURS）", "en": "英文（FLEURS）", "zh-en": "中英夾雜（ASCEND，對話）"}

# 要比的模型：代號、怎麼取得（hf＝faster-whisper 內建名稱；pack＝我們發布的模型包）、用在哪些資料
MODELS = [
    {"id": "small", "name": "Whisper small（安裝檔內建）", "hf": "small", "langs": "*"},
    {"id": "whisper-base", "name": "Whisper base（模型包）", "pack": "whisper-base", "langs": "*"},
    {"id": "whisper-medium", "name": "Whisper medium（模型包）", "pack": "whisper-medium", "langs": "*"},
    {"id": "whisper-large-v3-turbo", "name": "Whisper large-v3-turbo（模型包）", "pack": "whisper-large-v3-turbo", "langs": "*"},
    {"id": "breeze-asr-25", "name": "Breeze ASR 25（模型包）", "pack": "breeze-asr-25", "langs": ("zh", "zh-en")},
    {"id": "phowhisper-small", "name": "PhoWhisper small（模型包）", "pack": "phowhisper-small", "langs": ("vi",)},
    {"id": "phowhisper-medium", "name": "PhoWhisper medium（模型包）", "pack": "phowhisper-medium", "langs": ("vi",)},
    {"id": "whisper-id-small", "name": "Whisper small 印尼文（模型包）", "pack": "whisper-id-small", "langs": ("id",)},
    {"id": "whisper-id-medium", "name": "Whisper medium 印尼文（模型包）", "pack": "whisper-id-medium", "langs": ("id",)},
    {"id": "whisper-hi-small", "name": "Whisper small 印地語（模型包）", "pack": "whisper-hi-small", "langs": ("hi",)},
    {"id": "whisper-hi-medium", "name": "Whisper medium 印地語（模型包）", "pack": "whisper-hi-medium", "langs": ("hi",)},
]


def log(*a):
    print(*a, flush=True)


# ─── 文字整理與錯字率 ─────────────────────────────────────────

_T2S = [None]


def _t2s(text):
    """繁體 → 簡體（比中文時兩邊都轉成簡體：FLEURS 的標準答案是簡體，Breeze 輸出繁體，Whisper 兩種都有）"""
    if _T2S[0] is None:
        try:
            from opencc import OpenCC
            _T2S[0] = OpenCC("t2s").convert
        except Exception:  # noqa: BLE001
            _T2S[0] = lambda s: s
    return _T2S[0](text)


def _is_cjk(ch):
    return "㐀" <= ch <= "鿿" or "豈" <= ch <= "﫿"


def tokens(text, lang):
    """整理成比對用的單位：中文一個字一個單位；其他語言一個詞一個單位；中英夾雜＝中文字＋英文詞。
    大小寫、標點、全形半形的差別不算錯"""
    s = unicodedata.normalize("NFKC", str(text or "")).lower()
    if lang in ("zh", "zh-en"):
        s = _t2s(s)
    out, word = [], []
    for ch in s:
        cat = unicodedata.category(ch)
        if _is_cjk(ch):
            if word:
                out.append("".join(word))
                word = []
            out.append(ch)
        elif cat[0] in "LMN" or ch == "'":            # 字母、附加符號（印地語的母音記號）、數字
            word.append(ch)
        else:
            if word:
                out.append("".join(word))
                word = []
    if word:
        out.append("".join(word))
    out = [w.strip("'") for w in out]
    return [w for w in out if w]


def edit_distance(a, b):
    """兩串單位差幾步（替換、多出、漏掉各算一步）"""
    if not a:
        return len(b)
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1]


def error_rate(pairs, lang):
    """[(標準答案, 辨識結果)] → (錯誤率 %, 錯的單位數, 標準答案的單位數)。整批一起算，不是每句平均"""
    err = total = 0
    for ref, hyp in pairs:
        r, h = tokens(ref, lang), tokens(hyp, lang)
        if not r:
            continue
        err += edit_distance(r, h)
        total += len(r)
    return (round(100.0 * err / total, 1) if total else None), err, total


# ─── 聲音 ───────────────────────────────────────────────────

def wav_to_16k(data):
    """WAV 檔的內容 → 16 kHz 單聲道 float32；不是 WAV 就交給 ffmpeg"""
    import numpy as np
    try:
        with wave.open(io.BytesIO(data), "rb") as w:
            sr, ch, sw, n = w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()
            raw = w.readframes(n)
        if sw != 2:
            raise ValueError("只處理 16-bit")
        a = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
        if ch > 1:
            a = a.reshape(-1, ch).mean(axis=1)
        if sr != 16000:
            idx = np.linspace(0, len(a) - 1, int(len(a) * 16000 / sr))
            a = np.interp(idx, np.arange(len(a)), a).astype(np.float32)
        return a
    except Exception:  # noqa: BLE001  壓縮過的格式
        import subprocess
        p = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", "pipe:0", "-f", "s16le", "-ac", "1", "-ar", "16000", "pipe:1"],
                           input=data, capture_output=True, check=True)
        return np.frombuffer(p.stdout, dtype="<i2").astype(np.float32) / 32768.0


# ─── 資料集 ─────────────────────────────────────────────────

def _hf_file(repo, name):
    from huggingface_hub import hf_hub_download
    return hf_hub_download(repo_id=repo, repo_type="dataset", filename=name)


def _hf_list(repo):
    from huggingface_hub import list_repo_files
    return list(list_repo_files(repo, repo_type="dataset"))


def load_fleurs(lang, n):
    """FLEURS 測試集的前 n 句 → [{"id", "ref", "audio"}]。標準答案用原始的句子（raw_transcription）"""
    cfg = FLEURS[lang]
    tsv = Path(_hf_file("google/fleurs", f"data/{cfg}/test.tsv")).read_text(encoding="utf-8")
    refs = {}
    for line in tsv.splitlines():
        col = line.split("\t")
        if len(col) >= 3 and col[1].endswith(".wav"):
            refs.setdefault(col[1], col[2])          # 同一個檔名只留第一筆
    tar = _hf_file("google/fleurs", f"data/{cfg}/audio/test.tar.gz")
    out = []
    with tarfile.open(tar, "r:gz") as t:
        for m in t:
            name = Path(m.name).name
            if not m.isfile() or name not in refs:
                continue
            out.append({"id": name, "ref": refs[name], "audio": wav_to_16k(t.extractfile(m).read())})
            if len(out) >= n:
                break
    return out


def load_ascend(n):
    """ASCEND 測試集裡「中英夾雜」的前 n 句。資料集的格式可能會變：讀不到就丟例外，由呼叫的地方略過"""
    import pyarrow.parquet as pq
    files = [f for f in _hf_list("CAiRE/ASCEND") if f.endswith(".parquet") and "test" in f.lower()]
    if not files:
        raise RuntimeError("ASCEND 沒有找到測試集的 parquet 檔")
    out = []
    for f in sorted(files):
        tb = pq.read_table(_hf_file("CAiRE/ASCEND", f)).to_pylist()
        for row in tb:
            text = str(row.get("transcription") or "")
            au = row.get("audio") or {}
            lang_tag = str(row.get("language") or "")
            has_zh, has_en = any(_is_cjk(c) for c in text), bool(re.search(r"[A-Za-z]{2,}", text))
            if not (lang_tag == "mixed" or (has_zh and has_en)) or not isinstance(au, dict) or not au.get("bytes"):
                continue
            a = wav_to_16k(au["bytes"])
            if not 1.0 <= len(a) / 16000 <= 28.0:
                continue
            out.append({"id": str(row.get("id") or len(out)), "ref": text, "audio": a})
            if len(out) >= n:
                return out
    if not out:
        raise RuntimeError("ASCEND 測試集裡沒有找到中英夾雜的句子")
    return out


# ─── 模型 ───────────────────────────────────────────────────

def open_model(spec, work):
    """→ (WhisperModel, 用完要呼叫的清理函式)。模型包：從我們的發布頁下載、驗證、解開（跟同仁電腦上的程式同一段）"""
    from faster_whisper import WhisperModel
    if spec.get("hf"):
        return WhisperModel(spec["hf"], device="cpu", compute_type="int8"), (lambda: None)
    import model_packs as mp
    cat, errs = mp.catalog(share="", use_github=True)
    if spec["pack"] not in cat:
        raise RuntimeError(f"發布頁的清單裡沒有 {spec['pack']}（{'；'.join(errs)}）")
    base = Path(work) / "base"
    mp.install(base, cat[spec["pack"]])
    meta = mp.find(base, spec["pack"], "asr")
    return WhisperModel(meta["path"], device="cpu", compute_type="int8"), (lambda: shutil.rmtree(base, ignore_errors=True))


def transcribe(model, audio, lang):
    segs, _ = model.transcribe(audio, language="zh" if lang == "zh-en" else lang, beam_size=5,
                               condition_on_previous_text=False, vad_filter=False)
    return "".join(s.text for s in segs).strip()


# ─── 主程式 ─────────────────────────────────────────────────

def report_md(res):
    lines = ["# 語音辨識模型比較（公開資料集）", "",
             f"每種語言 {res['n']} 句；錯誤率＝錯的字（中文）或詞（其他語言）÷ 標準答案的字／詞數，越低越好。",
             "在 GitHub 的機器上用 CPU 跑，「慢幾倍」是辨識花的時間 ÷ 聲音長度，不代表有顯示卡時的速度。", ""]
    for lang, d in res["sets"].items():
        if not d.get("rows"):
            continue
        lines += [f"## {LANG_NAME.get(lang, lang)}", "", f"{d['count']} 句、共 {d['seconds']:.0f} 秒", "",
                  "| 模型 | 錯誤率 | 錯／總數 | CPU 上慢幾倍 |", "|---|---|---|---|"]
        for r in sorted(d["rows"], key=lambda x: (x["rate"] is None, x["rate"])):
            lines.append(f"| {r['name']} | {r['rate']}% | {r['err']}／{r['total']} | {r['rtf']:.2f} |")
        lines.append("")
    if res.get("skipped"):
        lines += ["## 沒有跑成的", ""] + [f"- {x}" for x in res["skipped"]] + [""]
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="bench")
    ap.add_argument("--langs", default="zh,id,vi,hi,en")
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--models", default="", help="只跑這些模型代號（逗號分隔），空白＝全部")
    ap.add_argument("--ascend", default="yes", help="yes／no：要不要跑中英夾雜（ASCEND）")
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    only = {x.strip() for x in a.models.split(",") if x.strip()}
    res = {"n": a.n, "sets": {}, "skipped": []}

    sets = {}
    for lang in [x.strip() for x in a.langs.split(",") if x.strip()]:
        if lang not in FLEURS:
            res["skipped"].append(f"{lang}：沒有這個語言的資料集")
            continue
        try:
            t0 = time.time()
            sets[lang] = load_fleurs(lang, a.n)
            log(f"資料 {lang}：{len(sets[lang])} 句（{time.time() - t0:.0f} 秒）")
        except Exception as e:  # noqa: BLE001
            res["skipped"].append(f"{lang} 的資料集下載失敗：{type(e).__name__}: {str(e)[:200]}")
            log("[略過]", res["skipped"][-1])
    if a.ascend == "yes":
        try:
            sets["zh-en"] = load_ascend(a.n)
            log(f"資料 zh-en：{len(sets['zh-en'])} 句")
        except Exception as e:  # noqa: BLE001
            res["skipped"].append(f"中英夾雜（ASCEND）拿不到：{type(e).__name__}: {str(e)[:200]}")
            log("[略過]", res["skipped"][-1])
    for lang, items in sets.items():
        res["sets"][lang] = {"count": len(items), "seconds": sum(len(x["audio"]) for x in items) / 16000, "rows": [], "samples": {}}

    for spec in MODELS:
        if only and spec["id"] not in only:
            continue
        todo = [l for l in sets if spec["langs"] == "*" or l in spec["langs"]]
        if not todo:
            continue
        log(f"\n▶ {spec['name']}")
        try:
            t0 = time.time()
            model, done = open_model(spec, out / "work")
            log(f"   載入 {time.time() - t0:.0f} 秒")
        except Exception as e:  # noqa: BLE001
            res["skipped"].append(f"{spec['name']} 載入失敗：{type(e).__name__}: {str(e)[:200]}")
            log("[略過]", res["skipped"][-1])
            continue
        for lang in todo:
            pairs, t0 = [], time.time()
            for it in sets[lang]:
                try:
                    hyp = transcribe(model, it["audio"], lang)
                except Exception as e:  # noqa: BLE001
                    hyp = ""
                    log(f"   [辨識失敗] {it['id']}：{e}")
                pairs.append((it["ref"], hyp))
            spent = time.time() - t0
            rate, err, total = error_rate(pairs, lang)
            d = res["sets"][lang]
            d["rows"].append({"id": spec["id"], "name": spec["name"], "rate": rate, "err": err, "total": total,
                              "rtf": spent / max(1.0, d["seconds"])})
            d["samples"][spec["id"]] = [h for _, h in pairs[:5]]
            d.setdefault("refs", [r for r, _ in pairs[:5]])
            log(f"   {lang}：錯誤率 {rate}%（{err}／{total}），花了 {spent:.0f} 秒")
            (out / "results.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        del model
        done()

    md = report_md(res)
    (out / "results.md").write_text(md, encoding="utf-8")
    (out / "results.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    log("\n" + md)
    for lang, d in res["sets"].items():           # 每種語言前幾句的實際輸出：看得出錯在哪裡
        if not d.get("rows"):
            continue
        log(f"\n── {lang} 前幾句 ──")
        for i, ref in enumerate(d.get("refs", [])):
            log(f"[答案] {ref}")
            for mid, hyps in d["samples"].items():
                log(f"  {mid}: {hyps[i] if i < len(hyps) else ''}")
    return 0 if any(d.get("rows") for d in res["sets"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
