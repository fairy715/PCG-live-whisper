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


# ─── 偵測到 NVIDIA 顯示卡、還沒裝 GPU 加速包：建議安裝（r25） ───────────────────────────
# 加速包只支援 NVIDIA（CUDA）；AMD、Intel 的獨立顯示卡用不到，不提醒。顯示記憶體太小（2 GB 的 MX 系列）多半跑不動，也不提醒。
GPU_PACK_URL = "https://github.com/fairy715/PCG-live-whisper/releases/download/gpu-cuda12-v1/PCG-GPU-Pack-cuda12-v1.exe"
GPU_PACK_PAGE = "https://github.com/fairy715/PCG-live-whisper/releases/tag/gpu-cuda12-v1"
GPU_PACK_MB = 706
MIN_VRAM_MB = 3500              # 4 GB 的顯示卡回報 4096 MiB
HINT_LATER_DAYS = 7


def nvidia_gpus(run=None):
    """這台電腦的 NVIDIA 顯示卡 [{"name", "vram_mb"}]（問 nvidia-smi：有裝 NVIDIA 驅動才有）。沒有、問不到回 []"""
    import subprocess
    if run is None:
        if sys.platform != "win32":
            return []
        run = subprocess.run
    root = os.environ.get("SystemRoot", r"C:\Windows")
    exes = ["nvidia-smi", os.path.join(root, "System32", "nvidia-smi.exe"),
            os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "NVIDIA Corporation", "NVSMI", "nvidia-smi.exe")]
    for exe in exes:
        try:
            r = run([exe, "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, timeout=8, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except (OSError, subprocess.SubprocessError, ValueError):
            continue
        if getattr(r, "returncode", 1) != 0:
            continue
        out = []
        for line in str(r.stdout or "").splitlines():
            name, _, mem = line.rpartition(",")
            try:
                out.append({"name": name.strip()[:80], "vram_mb": int(float(mem.strip()))})
            except ValueError:
                continue
        return [g for g in out if g["name"]]
    return []


def gpu_pack_installed(base_dir):
    """GPU 加速包裝了沒（安裝資料夾的 gpu\\cuda*）；裝了但檢查沒過也算裝了，不再提醒"""
    d = Path(base_dir) / "gpu"
    try:
        return d.is_dir() and any(x.is_dir() and x.name.startswith("cuda") for x in d.iterdir())
    except OSError:
        return False


def gpu_hint(base_dir, settings, now, gpus):
    """要不要建議安裝 GPU 加速包 → {"show", "why", "name", "vram_mb"}。
    settings 是 config.json 的 pcg_simple；gpu_hint 記同仁選的「下次再說」（until）或「不要再提醒」（off）"""
    h = (settings or {}).get("gpu_hint") or {}
    best = max(gpus or [], key=lambda g: g.get("vram_mb") or 0, default=None)
    out = {"show": False, "why": "", "name": (best or {}).get("name", ""), "vram_mb": (best or {}).get("vram_mb", 0)}
    if not best:
        out["why"] = "no_gpu"
    elif gpu_pack_installed(base_dir):
        out["why"] = "installed"
    elif best["vram_mb"] < MIN_VRAM_MB:
        out["why"] = "small"
    elif h.get("off"):
        out["why"] = "off"
    elif float(h.get("until") or 0) > now:
        out["why"] = "later"
    else:
        out["show"] = True
    return out

