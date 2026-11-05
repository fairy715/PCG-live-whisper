"""把 PCG-offline 資源包壓成兩個 zip（GitHub Releases 單一檔案上限 2 GB）。

    python group/windows/pack_release.py dist/PCG-offline dist/release

產出：
  PCG-offline-1-runtime.zip  Python、套件、ffmpeg、語音辨識模型、manifest
  PCG-offline-2-m2m100.zip   翻譯模型 M2M100
兩個 zip 裡都是 PCG-offline/ 開頭：解壓縮到同一個地方就會合成一個完整的 PCG-offline 資料夾。
"""
import sys
import zipfile
from pathlib import Path

LIMIT = 2 * 1024 ** 3 - 16 * 1024 ** 2          # 留一點餘裕


def pack(src: Path, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    parts = {"PCG-offline-1-runtime.zip": [], "PCG-offline-2-m2m100.zip": []}
    for p in sorted(src.rglob("*")):
        if p.is_file():
            rel = p.relative_to(src)
            key = "PCG-offline-2-m2m100.zip" if rel.parts[0] == "models" else "PCG-offline-1-runtime.zip"
            parts[key].append((p, Path("PCG-offline") / rel))
    for name, files in parts.items():
        z = out / name
        with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as zf:
            for p, arc in files:
                # 模型與套件本身多半已壓縮，再壓省不了多少：大檔直接存放，加快打包與解壓縮
                kind = zipfile.ZIP_STORED if p.stat().st_size > 50 * 1024 ** 2 else zipfile.ZIP_DEFLATED
                zf.write(p, arc.as_posix(), compress_type=kind)
        size = z.stat().st_size
        print(f"{name}: {len(files)} 個檔案、{size / 1024 ** 2:.0f} MB")
        if size > LIMIT:
            raise SystemExit(f"[錯誤] {name} 超過 GitHub Releases 的 2 GB 上限")


if __name__ == "__main__":
    pack(Path(sys.argv[1]), Path(sys.argv[2]))
