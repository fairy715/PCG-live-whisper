"""PCG 集團版：準備「NVIDIA GPU 加速包」的檔案（GitHub Actions 的 gpu-pack.yml 用）。

    python gpu_pack_stage.py <wheel 資料夾> <輸出資料夾> --versions cublas=…,cudnn=…,nvrtc=…
        從 NVIDIA 的 wheel 取出 Windows 用的 DLL 放到 <輸出資料夾>/bin，另寫 VERSION.json
    python gpu_pack_stage.py --verify <輸出資料夾>
        確認 CTranslate2（這台電腦上裝的版本）用顯示卡時要載入的 cuBLAS／cuDNN 都在 bin 裡
"""
import argparse
import json
import os
import re
import sys
import zipfile

# 只取這幾類：cuBLAS（cublas、cublasLt）、cuDNN 9 全部子程式庫、NVRTC（cuDNN 的執行期編譯會用到）
KEEP = re.compile(r"^nvidia/(cublas|cudnn|cuda_nvrtc)/bin/[^/]+\.dll$", re.I)
SKIP = re.compile(r"nvblas", re.I)


def stage(wheels, out, versions):
    bindir = os.path.join(out, "bin")
    os.makedirs(bindir, exist_ok=True)
    got = []
    for w in sorted(os.listdir(wheels)):
        if not w.endswith(".whl"):
            continue
        with zipfile.ZipFile(os.path.join(wheels, w)) as z:
            for n in z.namelist():
                if KEEP.match(n) and not SKIP.search(n):
                    name = os.path.basename(n)
                    with z.open(n) as src, open(os.path.join(bindir, name), "wb") as dst:
                        dst.write(src.read())
                    got.append(name)
    if not got:
        sys.exit("wheel 裡找不到任何 DLL")
    size = sum(os.path.getsize(os.path.join(bindir, f)) for f in got)
    info = {"cuda": 12, "packages": dict(kv.split("=", 1) for kv in versions.split(",") if "=" in kv),
            "files": sorted(got)}
    with open(os.path.join(out, "VERSION.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=1)
    print(f"{len(got)} 個 DLL，共 {size / 1048576:.0f} MB")
    for g in sorted(got):
        print("  " + g)


def ct2_needs():
    """CTranslate2 的 DLL 裡寫到的 cuBLAS／cuDNN 檔名（跟 translate_meeting._ct2_cuda_dll_names 同一個方法）"""
    import importlib.util
    spec = importlib.util.find_spec("ctranslate2")
    if not spec or not spec.submodule_search_locations:
        sys.exit("沒有安裝 ctranslate2")
    d = list(spec.submodule_search_locations)[0]
    names, bundled = set(), set()
    for f in os.listdir(d):
        if f.lower().endswith(".dll"):
            bundled.add(f.lower())
            with open(os.path.join(d, f), "rb") as fh:
                names |= {m.decode().lower() for m in re.findall(rb"(?:cublas|cudnn)[A-Za-z_]*64_\d+\.dll", fh.read(), re.I)}
    return sorted(names), bundled


def verify(out):
    have = {f.lower() for f in os.listdir(os.path.join(out, "bin"))}
    need, bundled = ct2_needs()
    if not need:
        sys.exit("讀不到 CTranslate2 要的 CUDA 檔名（這一版的 CTranslate2 沒有 CUDA？）")
    missing = [n for n in need if n not in have and n not in bundled]
    print("CTranslate2 要的：" + "、".join(need))
    if missing:
        sys.exit("加速包少了：" + "、".join(missing))
    print("都在")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--versions", default="")
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    if a.verify:
        verify(a.paths[0])
    else:
        if len(a.paths) != 2:
            sys.exit("用法：gpu_pack_stage.py <wheel 資料夾> <輸出資料夾>")
        stage(a.paths[0], a.paths[1], a.versions)


if __name__ == "__main__":
    main()
