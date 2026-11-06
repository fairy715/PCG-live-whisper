"""PCG 集團版：檢查這台電腦能不能用 NVIDIA 顯示卡做語音辨識（GPU 加速包裝好後自動執行；IT 也可以手動執行）。

    python\\python.exe gpu\\gpu_check.py              # 印出結果
    python\\python.exe gpu\\gpu_check.py --out 檔案   # 另外把結果寫成 JSON（安裝程式讀）

結束代碼：0＝可以用顯示卡；2＝這台電腦不能用（原因寫在結果裡，程式會照常用 CPU）；1＝檢查本身出錯。
"""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE) if os.path.basename(HERE).lower() == "gpu" else os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT)
os.environ.setdefault("HF_HUB_CACHE", os.path.join(ROOT, "hf_cache"))
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")


def gpu_name():
    try:
        import ctypes
        lib = ctypes.WinDLL("nvcuda.dll")
        if lib.cuInit(0) != 0:
            return ""
        dev = ctypes.c_int()
        if lib.cuDeviceGet(ctypes.byref(dev), 0) != 0:
            return ""
        buf = ctypes.create_string_buffer(256)
        lib.cuDeviceGetName(buf, 256, dev)
        return buf.value.decode(errors="replace")
    except Exception:
        return ""


def driver_version():
    try:
        import ctypes
        v = ctypes.c_int()
        if ctypes.WinDLL("nvcuda.dll").cuDriverGetVersion(ctypes.byref(v)) == 0:
            return f"{v.value // 1000}.{(v.value % 1000) // 10}"
    except Exception:
        pass
    return ""


def check():
    res = {"ok": False, "gpu": "", "cc": None, "compute_type": "", "driver_cuda": "", "reason": "", "reason_en": "",
           "seconds": None}
    if sys.platform != "win32":
        res.update(reason="只支援 Windows", reason_en="Windows only")
        return res
    if not os.path.isfile(os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "nvcuda.dll")):
        res.update(reason="這台電腦沒有 NVIDIA 顯示卡或驅動，會照常用 CPU",
                   reason_en="No NVIDIA graphics card or driver on this computer; the CPU is used as before")
        return res
    sys.argv = [sys.argv[0]]
    import translate_meeting as t
    res["gpu"], res["driver_cuda"] = gpu_name(), driver_version()
    if not hasattr(t, "_cuda_compute_capability"):
        res.update(reason="PCG 會議翻譯的版本太舊，請先更新到 r13 以上（頁面最下方「檢查更新」），再重新執行 GPU 加速包",
                   reason_en="PCG Meeting Translator is too old: update it to r13 or newer first, then run the GPU pack again")
        return res
    cc = t._cuda_compute_capability()
    res["cc"] = f"{cc[0]}.{cc[1]}" if cc else None
    if res["driver_cuda"] and float(res["driver_cuda"]) < 12.0:
        res.update(reason=f"顯示卡驅動太舊（支援到 CUDA {res['driver_cuda']}，需要 12 以上）：請 IT 更新 NVIDIA 驅動",
                   reason_en=f"The graphics driver is too old (CUDA {res['driver_cuda']}, 12 or newer needed): ask IT to update the NVIDIA driver")
        return res
    ok, missing = t._win_cuda_libs_ok()
    if not ok:
        res.update(reason="CUDA 函式庫載入失敗：" + "、".join(missing[:3]) + "（請重新安裝 GPU 加速包，或更新 NVIDIA 驅動）",
                   reason_en="Could not load the CUDA libraries: " + ", ".join(missing[:3]) +
                             " (reinstall the GPU pack or update the NVIDIA driver)")
        return res
    if not t._fw_local_cuda_ok():
        res.update(reason="這張顯示卡不能用來辨識（" + (t._FW_CUDA_OFF.get("reason") or "不支援") + "）",
                   reason_en="This graphics card cannot be used for recognition")
        return res
    kw = t._fw_device_kwargs()
    res["compute_type"] = kw.get("compute_type", "")
    import numpy as np
    from faster_whisper import WhisperModel
    m = WhisperModel(t._resolve_fw_model("small"), **kw)
    audio = (np.sin(np.arange(16000 * 3) * 2 * np.pi * 220 / 16000) * 0.05).astype(np.float32)
    list(m.transcribe(audio, language="zh", beam_size=1)[0])          # 第一次會比較慢（載入）
    t0 = time.time()
    list(m.transcribe(audio, language="zh", beam_size=1)[0])
    res["seconds"] = round(time.time() - t0, 2)
    res["ok"] = True
    return res


def main():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    ap.add_argument("--lang", default="zh")
    ap.add_argument("--msgbox", action="store_true", help="用 Windows 視窗告訴使用者結果（安裝程式用）")
    a = ap.parse_args()
    code = 0
    try:
        res = check()
        code = 0 if res["ok"] else 2
    except Exception as e:
        res = {"ok": False, "reason": f"檢查出錯：{type(e).__name__}: {e}", "reason_en": f"Check failed: {type(e).__name__}: {e}"}
        code = 1
    if res.get("ok"):
        print(f"[OK] 可以用顯示卡辨識：{res['gpu']}（計算能力 {res['cc']}，{res['compute_type']}，"
              f"3 秒聲音 {res['seconds']} 秒）")
    else:
        print(f"[不能用] {res.get('reason')}")
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False)
    if a.msgbox:
        msgbox(res, a.lang)
    sys.exit(code)


def msgbox(res, lang):
    zh = lang != "en"
    if res.get("ok"):
        detail = f"{res['gpu']}（{res['compute_type']}）" if zh else f"{res['gpu']} ({res['compute_type']})"
        text = (f"已啟用顯示卡加速。\n\n{detail}\n\n重新打開 PCG 會議翻譯就會使用顯示卡。" if zh else
                f"GPU acceleration is on.\n\n{detail}\n\nOpen PCG Meeting Translator again to use it.")
    else:
        why = res.get("reason") if zh else res.get("reason_en")
        text = (f"GPU 加速包已安裝，但這台電腦目前不能用顯示卡：\n\n{why}\n\nPCG 會議翻譯會照常用 CPU。" if zh else
                f"The GPU pack is installed, but this computer cannot use the graphics card yet:\n\n{why}\n\n"
                "PCG Meeting Translator keeps working on the CPU.")
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, text, "PCG GPU", 0x40 | 0x10000 | 0x40000)   # 資訊、拿到前景、最上層
    except Exception:
        pass


if __name__ == "__main__":
    main()
