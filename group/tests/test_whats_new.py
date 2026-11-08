"""集團版 r19：打開頁面時「有新版本、這次新增了什麼」——whats-new.json 的讀取與發布時的準備。

執行（在專案根目錄）：
    python3 -m unittest group/tests/test_whats_new.py -v
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "group" / "windows"))

from group import updater  # noqa: E402
import whats_new_prep  # noqa: E402

VER = "2026.11.8.r19"
WN = {"version": VER, "zh": ["多語字幕", " ", "<b>不是 HTML</b>", 3], "en": ["Multi-language subtitles"],
      "xx": ["ignored"], "id": "not a list"}


class Highlights(unittest.TestCase):
    def test_clean(self):
        self.assertEqual(updater.highlights(WN, VER),
                         {"zh": ["多語字幕", "<b>不是 HTML</b>"], "en": ["Multi-language subtitles"]})

    def test_other_version_is_ignored(self):
        self.assertEqual(updater.highlights(WN, "2026.11.9.r20"), {})
        self.assertEqual(updater.highlights("nope", VER), {})

    def test_limits(self):
        h = updater.highlights({"version": VER, "zh": ["x" * 999] * 20}, VER)
        self.assertEqual(len(h["zh"]), updater.WN_MAX_ITEMS)
        self.assertEqual(len(h["zh"][0]), updater.WN_MAX_CHARS)

    def test_from_share(self):
        d = Path(tempfile.mkdtemp())
        (d / f"PCG-Update-{VER}.exe").write_bytes(b"x")
        (d / f"PCG-Update-{VER}.whats-new.json").write_text(json.dumps(WN, ensure_ascii=False), encoding="utf-8")
        got = updater.from_share(str(d))
        self.assertEqual(got["highlights"]["zh"][0], "多語字幕")
        (d / f"PCG-Update-{VER}.whats-new.json").unlink()
        self.assertEqual(updater.from_share(str(d))["highlights"], {})        # 沒放說明照常更新

    def test_from_github(self):
        wn_url = updater.GITHUB_DL_PREFIX + f"v{VER}/whats-new.json"
        rel = {"tag_name": "v" + VER, "html_url": "https://x", "assets": [
            {"name": f"PCG-Update-{VER}.exe", "browser_download_url": updater.GITHUB_DL_PREFIX + f"v{VER}/PCG-Update-{VER}.exe",
             "digest": "sha256:" + "a" * 64, "size": 1},
            {"name": "whats-new.json", "browser_download_url": wn_url}]}
        seen = []

        def fetch(url):
            seen.append(url)
            return rel if url == updater.GITHUB_API else WN
        got = updater.from_github(fetch=fetch)
        self.assertEqual((got["kind"], got["highlights"]["en"]), ("patch", ["Multi-language subtitles"]))
        self.assertEqual(seen, [updater.GITHUB_API, wn_url])

        def broken(url):
            if url == updater.GITHUB_API:
                return rel
            raise OSError("timeout")
        self.assertEqual(updater.from_github(fetch=broken)["highlights"], {})   # 說明讀不到也照常更新
        rel["assets"][1]["browser_download_url"] = "https://evil.example/whats-new.json"
        seen.clear()
        self.assertEqual(updater.from_github(fetch=fetch)["highlights"], {})     # 只讀這個 repo 的附檔
        self.assertEqual(seen, [updater.GITHUB_API])


class Prepare(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.src = self.d / "whats-new.json"
        self.src.write_text(json.dumps({"_說明": "x", "release": "r19", "zh": ["a"]}, ensure_ascii=False), encoding="utf-8")

    def test_matching_release(self):
        out = self.d / "out.json"
        self.assertTrue(whats_new_prep.prepare(VER, out, src=self.src))
        data = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(data, {"release": "r19", "zh": ["a"], "version": VER})
        self.assertEqual(updater.highlights(data, VER), {"zh": ["a"]})

    def test_stale_notes_not_attached(self):
        out = self.d / "out.json"
        self.assertFalse(whats_new_prep.prepare("2026.11.9.r20", out, src=self.src))
        self.assertFalse(out.exists())

    def test_repo_file_is_valid(self):
        data = json.loads((ROOT / "group" / "whats-new.json").read_text(encoding="utf-8"))
        self.assertRegex(data["release"], r"^r\d+$")
        for L in updater.WN_LANGS:
            self.assertTrue(2 <= len(data[L]) <= updater.WN_MAX_ITEMS, L)
            self.assertTrue(all(len(x) <= updater.WN_MAX_CHARS for x in data[L]), L)


if __name__ == "__main__":
    unittest.main()
