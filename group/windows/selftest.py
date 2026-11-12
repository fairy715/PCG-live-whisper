"""PCG 集團版：安裝後的自我檢查（安裝程式會自動執行；IT 也可以手動執行看結果）。

    python group/windows/selftest.py           # 完整：套件、模型、翻譯 7 個方向（含外語對外語）
    python group/windows/selftest.py --quick   # 安裝時用：套件、模型、翻譯一句

需要的環境變數由 launch.ps1／pcg-install.ps1 設定（HF_HUB_CACHE、HF_HUB_OFFLINE、PATH 裡的 ffmpeg）。
"""
import argparse
import os
import shutil
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
ok = True


def check(name, fn):
    global ok
    t0 = time.time()
    try:
        detail = fn()
        print(f"[OK]   {name}  {detail or ''}  ({time.time() - t0:.1f}s)", flush=True)
    except Exception as e:
        ok = False
        print(f"[FAIL] {name}：{type(e).__name__}: {e}", flush=True)


def imports():
    import importlib
    mods = {m: importlib.import_module(m) for m in
            ("ctranslate2", "faster_whisper", "sentencepiece", "fastapi", "uvicorn", "websockets", "opencc",
             "sounddevice", "pyaudiowpatch", "PyQt6.QtWidgets", "resemblyzer")}
    return f"ctranslate2 {mods['ctranslate2'].__version__}, faster-whisper {mods['faster_whisper'].__version__}"


def ffmpeg():
    p = shutil.which("ffmpeg")
    if not p:
        raise RuntimeError("PATH 裡找不到 ffmpeg")
    return p


def whisper_model():
    from faster_whisper import WhisperModel
    WhisperModel("small", device="cpu", compute_type="int8")
    return "small（離線快取）"


def moonshine():
    """英文即時字幕（Moonshine medium）：離線載得起來、辨識一段聲音不出錯（不連網路：模型在 models/moonshine）"""
    sys.argv = [sys.argv[0]]
    import translate_meeting as t
    if not os.path.isdir(t._PCG_MOONSHINE_DIR):
        raise RuntimeError(f"找不到模型資料夾 {t._PCG_MOONSHINE_DIR}")
    if not t._MOONSHINE_AVAILABLE:
        raise RuntimeError("moonshine_voice 沒有裝好")
    os.environ["HTTPS_PROXY"] = os.environ["HTTP_PROXY"] = "http://127.0.0.1:9"     # 確認真的不需要網路
    try:
        from moonshine_voice import get_model_for_language, ModelArch
        from moonshine_voice.transcriber import Transcriber
        path, arch = get_model_for_language("en", ModelArch.MEDIUM_STREAMING)
        tr = Transcriber(model_path=path, model_arch=arch)
        import math
        audio = [0.05 * math.sin(i * 2 * math.pi * 220 / 16000) for i in range(16000 * 2)]
        tr.transcribe_without_streaming(audio, sample_rate=16000)
        tr.close()
    finally:
        os.environ.pop("HTTPS_PROXY", None)
        os.environ.pop("HTTP_PROXY", None)
    return "medium（離線）"


def cpu_budget():
    """CPU 用量限制：實體核心數讀得到、執行緒數合理、語音辨識模型吃得下 cpu_threads、低優先順序有生效"""
    sys.argv = [sys.argv[0]]
    import translate_meeting as t
    logical, phys = os.cpu_count() or 0, t._pcg_physical_cores()
    if phys is not None and not 1 <= phys <= max(logical, 1):
        raise RuntimeError(f"實體核心數不合理：{phys}（邏輯 {logical}）")
    asr, mt = t._pcg_cpu_threads()
    if asr < 1 or mt < 1 or asr + mt > max(logical, 2):
        raise RuntimeError(f"執行緒數不合理：辨識 {asr}、翻譯 {mt}（邏輯 {logical}）")
    from faster_whisper import WhisperModel
    kw = {"device": "cpu", "compute_type": "int8", "cpu_threads": asr}
    WhisperModel("small", **kw)
    pri = ""
    if sys.platform == "win32":
        k32, me = t._win_k32_process()
        before = k32.GetPriorityClass(me)
        t._pcg_lower_priority()
        after = k32.GetPriorityClass(me)
        if after != 0x00004000:
            raise RuntimeError(f"優先順序沒有改成低於標準（0x{before:x} → 0x{after:x}）")
        # r20：字幕跟不上時暫時調回標準、追上再讓回去（真的呼叫 Windows，不是假的）
        if not t._pcg_set_priority(t._PRIORITY_NORMAL) or k32.GetPriorityClass(me) != t._PRIORITY_NORMAL:
            raise RuntimeError(f"字幕跟不上時沒有辦法調回標準優先順序（0x{k32.GetPriorityClass(me):x}）")
        if not t._pcg_set_priority(t._PRIORITY_BELOW_NORMAL) or k32.GetPriorityClass(me) != 0x00004000:
            raise RuntimeError("追上後沒有辦法讓回低於標準")
        k32.SetPriorityClass(me, before)
        pri = "，低於標準優先順序 OK、跟不上時調回標準 OK"
    return f"邏輯 {logical}、實體 {phys}：辨識 {asr}、翻譯 {mt} 執行緒{pri}"


def report():
    """「回報問題」的診斷檔：讀得到電腦規格（記憶體、處理器）、金鑰會遮掉；做完就刪掉，不留在電腦上"""
    import json
    import zipfile
    from pathlib import Path
    from group import diagnostics
    secret = "sk-selftest-0123456789"
    p = diagnostics.build(Path(ROOT), description="selftest", config={"llm_api_key": secret, "pcg_simple": {}},
                          live={"running": True, "args": ["--llm-api-key", secret]}, with_logs=True)
    try:
        with zipfile.ZipFile(p) as z:
            names = z.namelist()
            text = "".join(z.read(n).decode("utf-8", "replace") for n in names)
            info = json.loads(z.read("report.json"))
    finally:
        p.unlink()
    if secret in text:
        raise RuntimeError("診斷檔裡有沒遮掉的金鑰")
    sysinfo = info["system"]
    if not sysinfo.get("ram_gb") or not sysinfo.get("cpu"):
        raise RuntimeError(f"讀不到電腦規格：{sysinfo}")
    return f"{sysinfo['cpu']}，記憶體 {sysinfo['ram_gb']} GB，{len(names)} 個檔案"


def multilang():
    """多語字幕（r19）：同一句翻成四種語言（字幕機有人選了不同語言時），量時間：
    一種、四種一起送（舊做法，CPU 上其實輪流算）、四種批次一次算（新做法）。翻譯模型只能載入一份"""
    import time as _t
    from concurrent.futures import ThreadPoolExecutor
    sys.argv = [sys.argv[0]]
    import translate_meeting as t
    if not t.LOCAL_MT_IS_M2M:
        raise RuntimeError("找不到 M2M100 模型")
    t._pcg_tr_note["tr"] = None
    x = t._PcgExtraSubs()
    langs = ("id", "vi", "hi", "en")
    trs = [x.translator(f"zh2{L}") for L in langs]
    if len(t.M2M100Translator._SHARED) != 1:
        raise RuntimeError(f"翻譯模型載入了 {len(t.M2M100Translator._SHARED)} 份（應該共用一份）")
    text = "新設備下週一開始試產，請大家先完成安全檢查。"
    trs[0].translate("暖機")
    t0 = _t.monotonic()
    trs[0].translate(text)
    t_one = _t.monotonic() - t0
    t0 = _t.monotonic()
    with ThreadPoolExecutor(max_workers=x.WORKERS) as pool:
        list(pool.map(lambda tr: tr.translate(text), trs))
    t_par = _t.monotonic() - t0
    t0 = _t.monotonic()
    outs = trs[0].translate_multi(text, list(langs))
    t_batch = _t.monotonic() - t0
    for L in langs:
        o = outs.get(L) or ""
        if not o.strip():
            raise RuntimeError(f"zh2{L} 沒有譯文")
        if any("\u4e00" <= c <= "\u9fff" for c in o):
            raise RuntimeError(f"zh2{L} 譯文還有中文：{o}")
    if not any("\u0900" <= c <= "\u097f" for c in outs["hi"]):
        raise RuntimeError(f"zh2hi 譯文沒有天城文：{outs['hi']}")
    dev = getattr(trs[0].ct2, "device", "?")
    return (f"翻 1 種 {t_one:.2f}s；4 種一起送 {t_par:.2f}s；4 種批次 {t_batch:.2f}s（{dev}）\n       "
            + "\n       ".join(f"zh2{L}: {outs[L]}" for L in langs))


def translations(quick):
    sys.argv = [sys.argv[0]]
    import translate_meeting as t
    if not t.LOCAL_MT_IS_M2M:
        raise RuntimeError(f"找不到 M2M100 模型（{t.M2M_MODEL_DIR}）")
    cases = [("id2zh", "Kita akan rapat besok pagi."),
             ("vi2zh", "Chúng ta sẽ họp vào sáng mai."),
             ("hi2zh", "हम कल सुबह बैठक करेंगे।"),
             ("zh2id", "我們明天早上開會。"),
             ("zh2hi", "我們明天早上開會。"),
             # 外語對外語（r17）：不經過中文
             ("vi2id", "Chúng ta sẽ họp vào sáng mai."),
             ("id2vi", "Kita akan rapat besok pagi.")]
    if quick:
        cases = cases[:1]
    out = []
    for d, text in cases:
        tr = t.NllbTranslator(direction=d)
        r = tr.translate(text)
        if not r.strip():
            raise RuntimeError(f"{d} 沒有譯文")
        if d.endswith("2zh") and not any("\u4e00" <= c <= "\u9fff" for c in r):
            raise RuntimeError(f"{d} 譯文沒有中文：{r}")
        if d == "zh2hi" and not any("\u0900" <= c <= "\u097f" for c in r):
            raise RuntimeError(f"{d} 譯文沒有天城文：{r}")
        if d in ("vi2id", "id2vi") and any("\u4e00" <= c <= "\u9fff" for c in r):
            raise RuntimeError(f"{d} 譯文跑出中文：{r}")
        if d == "vi2id" and t._VI_DIACRITIC_RE.search(r):
            raise RuntimeError(f"{d} 譯文還是越南文：{r}")
        if d == "id2vi" and not t._VI_DIACRITIC_RE.search(r):
            raise RuntimeError(f"{d} 譯文不像越南文：{r}")
        out.append(f"{d}: {r}")
    return "\n       " + "\n       ".join(out)


def live_segment():
    """r21 依停頓切句：Windows 語音合成念兩句（中間停 1.5 秒）→ 真的 Silero VAD 切段 → small 辨識 → 句子合併。
    切成兩段以上、而且辨識得出內容，才算過（這是即時字幕預設的做法，壞掉時字幕會整個出不來）"""
    import subprocess
    import tempfile
    import wave
    import numpy as np
    sys.argv = [sys.argv[0]]
    import translate_meeting as t
    from faster_whisper import WhisperModel
    wav = os.path.join(tempfile.gettempdir(), "pcg_selftest_seg.wav")
    ps = ("Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
          f"$s.SetOutputToWaveFile('{wav}'); "
          "$b = New-Object System.Speech.Synthesis.PromptBuilder; "
          "$b.AppendText('We will check the inventory tomorrow morning.'); "
          "$b.AppendBreak([TimeSpan]::FromMilliseconds(1500)); "
          "$b.AppendText('Please send the report to the factory before Friday.'); "
          "$b.AppendBreak([TimeSpan]::FromMilliseconds(1500)); $s.Speak($b); $s.Dispose()")
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True, timeout=120,
                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    with wave.open(wav, "rb") as w:
        sr, ch, raw = w.getframerate(), w.getnchannels(), w.readframes(w.getnframes())
    os.unlink(wav)
    audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if ch > 1:
        audio = audio.reshape(-1, ch).mean(axis=1)
    audio = t._pcg_to_16k(audio, sr)
    seg, merger = t._PcgSegmenter(), t._PcgSentenceMerger()
    model = WhisperModel("small", device="cpu", compute_type="int8", cpu_threads=t._pcg_cpu_threads()[0])
    texts, n = [], 0
    for i in range(0, len(audio), 1600):                  # 跟即時一樣每 0.1 秒送一小塊
        seg.push(audio[i:i + 1600])
        for a, forced, pause in seg.poll():
            n += 1
            segs, _ = model.transcribe(a, language="en", beam_size=5, vad_filter=False)
            texts += [u[0] for u in merger.add(" ".join(x.text.strip() for x in segs), "en", i / 16000, forced, pause)]
    texts += [u[0] for u in merger.flush()]
    joined = " ".join(texts).lower()
    if n < 2 or "inventory" not in joined or "report" not in joined:
        raise RuntimeError(f"切了 {n} 段，辨識結果：{texts}")
    return f"{n} 段 → {texts}"


def main():
    for stream in (sys.stdout, sys.stderr):          # 非中文版 Windows 的命令列印中文會當掉
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    print(f"Python {sys.version.split()[0]}  {sys.executable}")
    check("套件", imports)
    check("ffmpeg", ffmpeg)
    check("語音辨識模型", whisper_model)
    check("本機翻譯 M2M100", lambda: translations(a.quick))
    if not a.quick:                       # 安裝時不檢查：查不到也只是用預設值，不該讓安裝失敗
        check("英文即時字幕 Moonshine", moonshine)
        check("CPU 用量限制", cpu_budget)
        check("回報問題的診斷檔", report)
        check("多語字幕（同時翻成四種語言）", multilang)
        check("即時字幕依停頓切句（VAD）", live_segment)
    print("結果：" + ("全部通過" if ok else "有項目沒通過"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
