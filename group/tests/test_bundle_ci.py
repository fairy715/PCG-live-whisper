"""集團版：CI 製作資源包時的下載重試與 ffmpeg 備援（group/windows/bundle_ci.py）。

執行（在專案根目錄）：
    python3 -m unittest group/tests/test_bundle_ci.py -v
"""
import sys
import unittest
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "group" / "windows"))

import bundle_ci  # noqa: E402

LATEST = bundle_ci.bb.FFMPEG_URL


def err504(u):
    return urllib.error.HTTPError(u, 504, "Gateway Time-out", {}, None)


class Download(unittest.TestCase):
    def setUp(self):
        self.calls, self.slept = [], []
        self._orig = bundle_ci._orig_download

    def tearDown(self):
        bundle_ci._orig_download = self._orig

    def fake(self, bad):
        def dl(u, dest):
            self.calls.append(u)
            if u in bad:
                raise err504(u)
            return "ok"
        bundle_ci._orig_download = dl

    def test_mirror_first_when_hash_known(self):
        self.fake(set())
        self._sha = bundle_ci.bb.sha256
        bundle_ci.bb.sha256 = lambda p: "a" * 64
        try:
            self.assertEqual(bundle_ci.download(LATEST, Path("d"), sleep=self.slept.append, fallbacks=lambda: [],
                                                mirror_hash=lambda: "a" * 64), "ok")
            self.assertEqual(self.calls, [bundle_ci.MIRROR])
            # 指紋不符：不用備份，改 BtbN
            self.calls.clear()
            self.assertEqual(bundle_ci.download(LATEST, Path("d"), sleep=self.slept.append, fallbacks=lambda: [],
                                                mirror_hash=lambda: "b" * 64), "ok")
            self.assertEqual(self.calls, [bundle_ci.MIRROR, LATEST])
        finally:
            bundle_ci.bb.sha256 = self._sha

    def test_404_is_not_retried(self):
        def dl(u, dest):
            self.calls.append(u)
            if u == bundle_ci.MIRROR:
                raise urllib.error.HTTPError(u, 404, "Not Found", {}, None)
            return "ok"
        bundle_ci._orig_download = dl
        self.assertEqual(bundle_ci.download(LATEST, Path("d"), sleep=self.slept.append, fallbacks=lambda: [],
                                            mirror_hash=lambda: "a" * 64), "ok")
        self.assertEqual(self.calls, [bundle_ci.MIRROR, LATEST])
        self.assertEqual(self.slept, [])

    def test_mirror_hash_parsing(self):
        self.assertEqual(bundle_ci.mirror_sha256(lambda u: "A" * 64 + "  f.zip\n"), "a" * 64)
        self.assertEqual(bundle_ci.mirror_sha256(lambda u: "nope"), "")

        def boom(u):
            raise OSError("404")
        self.assertEqual(bundle_ci.mirror_sha256(boom), "")

    def test_retries_then_succeeds(self):
        n = {"i": 0}

        def dl(u, dest):
            n["i"] += 1
            self.calls.append(u)
            if n["i"] < 3:
                raise err504(u)
        bundle_ci._orig_download = dl
        bundle_ci.download("https://x/model.bin", Path("d"), sleep=self.slept.append, fallbacks=lambda: [])
        self.assertEqual(len(self.calls), 3)
        self.assertEqual(self.slept, [15, 45])

    def test_ffmpeg_falls_back_to_recent_build(self):
        alt = "https://github.com/BtbN/FFmpeg-Builds/releases/download/autobuild-x/ffmpeg-N-1-gabc-win64-lgpl-shared.zip"
        self.fake({LATEST})
        self.assertEqual(bundle_ci.download(LATEST, Path("d"), sleep=self.slept.append, fallbacks=lambda: [alt],
                                            mirror_hash=lambda: ""), "ok")
        self.assertEqual(self.calls, [LATEST] * 3 + [alt])

    def test_other_files_have_no_fallback(self):
        self.fake({"https://x/a"})
        with self.assertRaises(urllib.error.HTTPError):
            bundle_ci.download("https://x/a", Path("d"), sleep=self.slept.append, fallbacks=lambda: ["https://y"])
        self.assertEqual(self.calls, ["https://x/a"] * 3)

    def test_gives_up_with_last_error(self):
        self.fake({LATEST, "https://alt"})
        with self.assertRaises(urllib.error.HTTPError):
            bundle_ci.download(LATEST, Path("d"), sleep=self.slept.append, fallbacks=lambda: ["https://alt"],
                               mirror_hash=lambda: "")


class Fallbacks(unittest.TestCase):
    def test_only_master_win64_lgpl_shared_zip(self):
        rel = [{"assets": [
            {"name": "ffmpeg-master-latest-win64-gpl-shared.zip", "browser_download_url": "https://g/gpl"},
            {"name": "ffmpeg-N-121-gabc-win64-lgpl-shared.zip", "browser_download_url": "https://g/ok1"},
            {"name": "ffmpeg-n7.1-123-win64-lgpl-shared-7.1.zip", "browser_download_url": "https://g/branch"},
            {"name": "ffmpeg-N-121-gabc-linux64-lgpl-shared.tar.xz", "browser_download_url": "https://g/linux"},
            {"name": "ffmpeg-master-latest-win64-lgpl-shared.zip", "browser_download_url": bundle_ci.bb.FFMPEG_URL},
        ]}, {"assets": [{"name": "ffmpeg-master-latest-win64-lgpl-shared.zip",
                         "browser_download_url": "https://g/ok2"}]}]
        self.assertEqual(bundle_ci.ffmpeg_fallbacks(lambda u: rel), ["https://g/ok1", "https://g/ok2"])

    def test_api_failure(self):
        def boom(u):
            raise OSError("403")
        self.assertEqual(bundle_ci.ffmpeg_fallbacks(boom), [])


if __name__ == "__main__":
    unittest.main()
