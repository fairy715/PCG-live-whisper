"""PCG 集團版 r21：依這台電腦的規格自動選即時字幕的語音辨識模型（IT 設定頁「本機即時字幕模型」＝自動，預設）。

概念參考 tinglongWu 的 hwprobe.py（https://github.com/sunososobro-hub/tinglongwu ，MIT License，(c) 2026 Alonso），
規則依集團版的模型包與實測改寫：
  - 有 GPU 加速包、而且裝好時檢查通過（group_data/gpu_check.json 的 ok）→ 顯示卡跑得動大模型：
    large-v3-turbo 模型包 > medium 模型包 > 內建 small
  - 雙核心的電腦（例如 i3-10110U；2026-11-11 同仁實測開 Teams 時 small 完全跟不上）→ base 模型包（較快、錯字較多）；
    沒裝 base 就照舊用 small，並在 IT 設定頁建議安裝
  - 其他 → 內建 small
只讀這台電腦的資訊，不連網。語言專用的模型包（IT 指定「對方說越南文用 PhoWhisper」等）照舊優先。
"""
import json
import os
import sys
from pathlib import Path

from group import model_packs

GPU_ORDER = ("whisper-large-v3-turbo", "whisper-medium")
WEAK_PACK = "whisper-base"


def physical_cores():
    """實體核心數（Windows）；查不到回 None"""
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        class _SLPI(ctypes.Structure):          # SYSTEM_LOGICAL_PROCESSOR_INFORMATION（64 位元 32 bytes）
            _fields_ = [("mask", ctypes.c_size_t), ("rel", ctypes.c_int), ("_u", ctypes.c_byte * 16)]
        k32 = ctypes.windll.kernel32
        size = wintypes.DWORD(0)
        k32.GetLogicalProcessorInformation(None, ctypes.byref(size))
        cnt = size.value // ctypes.sizeof(_SLPI)
        if cnt <= 0:
            return None
        buf = (_SLPI * cnt)()
        if not k32.GetLogicalProcessorInformation(buf, ctypes.byref(size)):
            return None
        return sum(1 for x in buf if x.rel == 0) or None
    except Exception:  # noqa: BLE001
        return None


def gpu_ok(base_dir):
    """GPU 加速包裝好、而且檢查通過"""
    try:
        if not (Path(base_dir) / "gpu").is_dir():
            return False
        data = json.loads((Path(base_dir) / "group_data" / "gpu_check.json").read_text(encoding="utf-8"))
        return bool(data.get("ok"))
    except (OSError, ValueError):
        return False


def probe(base_dir):
    return {"logical": os.cpu_count() or 0, "physical": physical_cores(), "gpu": gpu_ok(base_dir)}


def weak(hw):
    phys, logical = hw.get("physical"), hw.get("logical") or 0
    return (phys is not None and phys <= 2) or (phys is None and 0 < logical <= 2)


def pick(base_dir, hw=None, has_pack=None):
    """{"model": 給主程式 -m 的名稱, "reason": "gpu"/"weak"/"normal", "suggest": 建議安裝的模型包 id 或 "", "hw": …}"""
    hw = hw if hw is not None else probe(base_dir)
    if has_pack is None:
        def has_pack(pid):
            return bool(model_packs.find(base_dir, pid, "asr", purpose="live"))
    if hw.get("gpu"):
        for pid in GPU_ORDER:
            if has_pack(pid):
                return {"model": f"pack:{pid}", "reason": "gpu", "suggest": "", "hw": hw}
        return {"model": "small", "reason": "gpu", "suggest": GPU_ORDER[0], "hw": hw}
    if weak(hw):
        if has_pack(WEAK_PACK):
            return {"model": f"pack:{WEAK_PACK}", "reason": "weak", "suggest": "", "hw": hw}
        return {"model": "small", "reason": "weak", "suggest": WEAK_PACK, "hw": hw}
    return {"model": "small", "reason": "normal", "suggest": "", "hw": hw}
