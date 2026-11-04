"""PCG 集團版：安裝後的自我檢查（安裝程式會自動執行；IT 也可以手動執行看結果）。

    python group/windows/selftest.py           # 完整：套件、模型、翻譯 5 種語言方向
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


def translations(quick):
    sys.argv = [sys.argv[0]]
    import translate_meeting as t
    if not t.LOCAL_MT_IS_M2M:
        raise RuntimeError(f"找不到 M2M100 模型（{t.M2M_MODEL_DIR}）")
    cases = [("id2zh", "Kita akan rapat besok pagi."),
             ("vi2zh", "Chúng ta sẽ họp vào sáng mai."),
             ("hi2zh", "हम कल सुबह बैठक करेंगे।"),
             ("zh2id", "我們明天早上開會。"),
             ("zh2hi", "我們明天早上開會。")]
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
        out.append(f"{d}: {r}")
    return "\n       " + "\n       ".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    print(f"Python {sys.version.split()[0]}  {sys.executable}")
    check("套件", imports)
    check("ffmpeg", ffmpeg)
    check("語音辨識模型", whisper_model)
    check("本機翻譯 M2M100", lambda: translations(a.quick))
    print("結果：" + ("全部通過" if ok else "有項目沒通過"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
