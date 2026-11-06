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
        k32.SetPriorityClass(me, before)
        pri = "，低於標準優先順序 OK"
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
    print("結果：" + ("全部通過" if ok else "有項目沒通過"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
