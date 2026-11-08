"""PCG 集團版：在 GitHub Actions 上製作離線資源包（包一層 build_bundle.py，下載比較耐操）。

    python group/windows/bundle_ci.py --out dist/PCG-offline [build_bundle.py 的其他參數]

2026-11-08：BtbN 的 ffmpeg「latest」下載點一直回 504 Gateway Time-out，資源包做不出來，
安裝測試與發布全部停住。這裡把 build_bundle.py 的下載換成：
  1. 每個網址失敗會重試（等 15、45 秒）
  2. ffmpeg 的「latest」不能用時，用 GitHub API 找 BtbN 最近幾次自動建置裡同一種檔案
     （master、win64、LGPL、shared），一樣是 LGPL 版
不直接改 build_bundle.py：它的內容（指紋）決定已裝的電腦能不能用小更新包，改了就要全部重裝完整安裝檔。
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_bundle as bb  # noqa: E402

BTBN_API = "https://api.github.com/repos/BtbN/FFmpeg-Builds/releases?per_page=10"
FFMPEG_ASSET = re.compile(r"^ffmpeg-(?:master-latest|N-[\w.-]+)-win64-lgpl-shared\.zip$")
WAITS = (15, 45)
_orig_download = bb.download


def _api_json(url):
    headers = {"User-Agent": "pcg-bundle-builder", "Accept": "application/vnd.github+json"}
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def ffmpeg_fallbacks(api_json=_api_json):
    """BtbN 最近幾次自動建置裡的 master／win64／LGPL／shared 壓縮檔（新的在前）"""
    try:
        releases = api_json(BTBN_API)
    except Exception as e:  # noqa: BLE001
        print(f"   [注意] 查不到 BtbN 的版本清單：{e}", flush=True)
        return []
    out = []
    for rel in releases or []:
        for a in rel.get("assets") or []:
            name = a.get("name") or ""
            url = a.get("browser_download_url") or ""
            if FFMPEG_ASSET.match(name) and url and url != bb.FFMPEG_URL and url not in out:
                out.append(url)
    return out


def download(url, dest, sleep=time.sleep, fallbacks=ffmpeg_fallbacks):
    last = None
    urls = [url]
    tried_fallbacks = False
    i = 0
    while i < len(urls):
        u = urls[i]
        for n, wait in enumerate((0,) + WAITS):
            if wait:
                print(f"   {wait} 秒後重試（第 {n + 1} 次）", flush=True)
                sleep(wait)
            try:
                return _orig_download(u, dest)
            except (urllib.error.URLError, OSError) as e:   # HTTPError 也是 URLError
                last = e
                print(f"   [注意] 下載失敗：{e}", flush=True)
        if url == bb.FFMPEG_URL and not tried_fallbacks:
            tried_fallbacks = True
            more = fallbacks()
            if more:
                print(f"   改用 BtbN 最近的自動建置：{more[0]}", flush=True)
            urls += more[:3]
        i += 1
    raise last


def main(argv=None):
    bb.download = download
    sys.argv = ["build_bundle.py"] + list(sys.argv[1:] if argv is None else argv)
    bb.main()


if __name__ == "__main__":
    main()
