#!/usr/bin/env python3
"""PCG 集團版：製作 Windows 離線資源包（給沒有網路的同仁電腦安裝用）。

在一台「能上網」的電腦執行（Windows、Mac、Linux 都可以，需要 Python 3.9 以上）：

    python group/windows/build_bundle.py                 # 產生 PCG-offline/（約 2 GB）
    python group/windows/build_bundle.py --models small,medium

產出的 PCG-offline 資料夾跟 PCG會議翻譯-Setup.exe 放在同一層（共用資料夾或 USB），
同仁執行 Setup.exe 時會自動找到它，完全不連網就能安裝。

資源包內容：
  python/      Python 3.12（NuGet 免安裝版，不寫登錄檔、不影響電腦上其他 Python）
  wheels/      所有套件（Windows 64 位元、Python 3.12 的預先編譯版）
  hf_cache/    語音辨識模型（faster-whisper，Hugging Face 快取格式）
  models/m2m100_418m/  本機翻譯模型 M2M100 418M（CTranslate2，MIT 授權）
  tools/ffmpeg/        音訊轉檔（BtbN 的 LGPL 版）
  requirements-lock.txt  套件的確切版本（安裝時照這份裝）
  manifest.json        版本、檔案大小與 SHA-256
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY_VERSION = "3.12.10"
PY_URL = f"https://www.nuget.org/api/v2/package/python/{PY_VERSION}"
FFMPEG_URL = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-lgpl.zip"
M2M_CT2_REPO = "michaelfeil/ct2fast-m2m100_418M"       # 已轉好的 CTranslate2 格式
M2M_SRC_REPO = "facebook/m2m100_418M"                   # 原始模型（MIT），取 sentencepiece 分詞檔；轉檔備援也用它
# faster-whisper 的模型名稱 → Hugging Face repo（與 faster_whisper.utils._MODELS 相同）
FW_REPOS = {
    "tiny": "Systran/faster-whisper-tiny", "base": "Systran/faster-whisper-base",
    "small": "Systran/faster-whisper-small", "medium": "Systran/faster-whisper-medium",
    "large-v3": "Systran/faster-whisper-large-v3",
    "large-v3-turbo": "mobiuslabsgmbh/faster-whisper-large-v3-turbo",
}
PIP_PLATFORM = ["--platform", "win_amd64", "--python-version", "3.12", "--implementation", "cp",
                "--abi", "cp312", "--only-binary=:all:"]


def step(msg):
    print(f"\n== {msg}", flush=True)


def run(cmd):
    print("   $ " + " ".join(str(c) for c in cmd), flush=True)
    subprocess.run([str(c) for c in cmd], check=True)


def download(url, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"   下載 {url}", flush=True)
    req = urllib.request.Request(url, headers={"User-Agent": "pcg-bundle-builder"})
    with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
        shutil.copyfileobj(r, f, length=1 << 20)
    print(f"   → {dest.name}（{dest.stat().st_size / 1048576:.1f} MB）", flush=True)


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_hf():
    import importlib.util
    if importlib.util.find_spec("huggingface_hub") is None:
        run([sys.executable, "-m", "pip", "install", "--quiet", "huggingface_hub"])


def build_python(out):
    step(f"Python {PY_VERSION}（NuGet 免安裝版）")
    nupkg = out / "python" / f"python-{PY_VERSION}.nupkg"
    download(PY_URL, nupkg)
    with zipfile.ZipFile(nupkg) as z:
        names = z.namelist()
    need = ["tools/python.exe", "tools/Lib/ensurepip/__init__.py", "tools/Lib/venv/__init__.py"]
    missing = [n for n in need if n not in names]
    if missing:
        raise SystemExit(f"[錯誤] Python 套件內容不符預期，缺：{missing}")


def build_wheels(out):
    """先用 uv 以「Windows、Python 3.12」解出完整清單（pip 跨平台下載時會用執行這台電腦的平台判斷
    「只有 Windows 才要」的相依，例如 colorama 會漏掉、Linux 的 NVIDIA 套件反而被算進來），再逐一下載"""
    step("套件（Windows 64 位元、Python 3.12）")
    import importlib.util
    if importlib.util.find_spec("uv") is None:
        run([sys.executable, "-m", "pip", "install", "--quiet", "uv"])
    wheels = out / "wheels"
    wheels.mkdir(parents=True, exist_ok=True)
    lock = out / "requirements-lock.txt"
    run([sys.executable, "-m", "uv", "pip", "compile", HERE / "requirements-cpu.txt",
         "--python-platform", "x86_64-pc-windows-msvc", "--python-version", "3.12",
         "--only-binary", ":all:", "--no-header", "--no-annotate", "--quiet", "-o", lock])
    run([sys.executable, "-m", "pip", "download", "--quiet", *PIP_PLATFORM, "--no-deps",
         "-r", lock, "-d", wheels])
    run([sys.executable, "-m", "pip", "download", "--quiet", *PIP_PLATFORM, "--no-deps",
         "resemblyzer", "-d", wheels])
    # 安裝時 ensurepip 會裝它自己帶的 pip；這裡再放一份新版 pip，避免舊版 pip 的已知問題
    run([sys.executable, "-m", "pip", "download", "--quiet", *PIP_PLATFORM, "--no-deps",
         "pip>=26.2.2", "-d", wheels])
    n = len(list(wheels.glob("*.whl")))
    print(f"   共 {n} 個套件（清單：{lock.name}）", flush=True)


def build_whisper(out, models):
    ensure_hf()
    from huggingface_hub import snapshot_download
    for m in models:
        repo = FW_REPOS.get(m)
        if not repo:
            raise SystemExit(f"[錯誤] 不認得的辨識模型：{m}（可用：{', '.join(FW_REPOS)}）")
        step(f"語音辨識模型 {m}（{repo}）")
        snapshot_download(repo, cache_dir=str(out / "hf_cache"))


def build_m2m(out):
    ensure_hf()
    from huggingface_hub import hf_hub_download, snapshot_download
    step("翻譯模型 M2M100 418M（CTranslate2，MIT 授權）")
    dest = out / "models" / "m2m100_418m"
    dest.mkdir(parents=True, exist_ok=True)
    try:
        snapshot_download(M2M_CT2_REPO, local_dir=str(dest),
                          allow_patterns=["model.bin", "*.json", "*.txt", "*.model"])
    except Exception as e:
        print(f"   [提示] 下載轉好的版本失敗（{type(e).__name__}: {e}），改為自行轉檔", flush=True)
    hf_hub_download(M2M_SRC_REPO, "sentencepiece.bpe.model", local_dir=str(dest))
    if not (dest / "model.bin").is_file():
        convert_m2m(dest)
    for need in ("model.bin", "sentencepiece.bpe.model"):
        if not (dest / need).is_file():
            raise SystemExit(f"[錯誤] M2M100 模型缺 {need}")


def convert_m2m(dest):
    """備援：用 ctranslate2 的轉檔工具把原始模型轉成 int8（需要 transformers＋torch，約 3 GB 暫存）"""
    step("M2M100 轉檔（備援）")
    venv = Path(tempfile.mkdtemp(prefix="m2m-convert-"))
    run([sys.executable, "-m", "venv", venv])
    py = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    run([py, "-m", "pip", "install", "--quiet", "ctranslate2", "transformers[torch]", "sentencepiece"])
    conv = venv / ("Scripts/ct2-transformers-converter.exe" if os.name == "nt" else "bin/ct2-transformers-converter")
    run([conv, "--model", M2M_SRC_REPO, "--output_dir", dest, "--quantization", "int8", "--force"])
    shutil.rmtree(venv, ignore_errors=True)


def build_ffmpeg(out):
    step("ffmpeg（LGPL 版）")
    tmp = Path(tempfile.mkdtemp(prefix="ffmpeg-"))
    zp = tmp / "ffmpeg.zip"
    download(FFMPEG_URL, zp)
    bin_dir = out / "tools" / "ffmpeg" / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zp) as z:
        for n in z.namelist():
            base = n.rsplit("/", 1)[-1]
            if base in ("ffmpeg.exe", "ffprobe.exe") or (n.endswith("LICENSE.txt") and n.count("/") == 1):
                with z.open(n) as src, open(bin_dir / base, "wb") as dst:
                    shutil.copyfileobj(src, dst)
    shutil.rmtree(tmp, ignore_errors=True)
    for need in ("ffmpeg.exe", "ffprobe.exe"):
        if not (bin_dir / need).is_file():
            raise SystemExit(f"[錯誤] ffmpeg 壓縮檔裡找不到 {need}")


def write_manifest(out, models):
    step("manifest.json")
    files = {}
    for p in sorted(out.rglob("*")):
        if p.is_file() and p.name != "manifest.json":
            rel = p.relative_to(out).as_posix()
            files[rel] = {"size": p.stat().st_size}
            if p.stat().st_size > 5 * 1048576 or rel.endswith((".nupkg", ".exe")):
                files[rel]["sha256"] = sha256(p)
    req = (HERE / "requirements-cpu.txt").read_bytes()
    manifest = {"format": 1, "created": time.strftime("%Y-%m-%d %H:%M:%S"), "python": PY_VERSION,
                "whisper_models": models, "requirements_sha256": hashlib.sha256(req).hexdigest(),
                "total_mb": round(sum(f["size"] for f in files.values()) / 1048576), "files": files}
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"   共 {len(files)} 個檔案、{manifest['total_mb']} MB", flush=True)


def main():
    ap = argparse.ArgumentParser(description="製作 PCG 集團版的 Windows 離線資源包")
    ap.add_argument("--out", default="PCG-offline", help="輸出資料夾（預設 PCG-offline）")
    ap.add_argument("--models", default="small",
                    help="語音辨識模型，逗號分隔（預設 small；可加 base、medium、large-v3-turbo）")
    ap.add_argument("--skip", default="", help="略過的項目（測試用）：python,wheels,whisper,m2m,ffmpeg")
    a = ap.parse_args()
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    models = [m.strip() for m in a.models.split(",") if m.strip()]
    skip = set(filter(None, a.skip.split(",")))
    t0 = time.time()
    if "python" not in skip:
        build_python(out)
    if "wheels" not in skip:
        build_wheels(out)
    if "whisper" not in skip:
        build_whisper(out, models)
    if "m2m" not in skip:
        build_m2m(out)
    if "ffmpeg" not in skip:
        build_ffmpeg(out)
    write_manifest(out, models)
    print(f"\n完成（{(time.time() - t0) / 60:.1f} 分鐘）：{out}")
    print("把這個資料夾跟 PCG會議翻譯-Setup.exe 放在同一層，同仁執行 Setup.exe 即可離線安裝。")


if __name__ == "__main__":
    main()
