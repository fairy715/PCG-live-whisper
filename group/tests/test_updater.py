"""一鍵更新（updater.py 與 /api/simple/update）的檢查。不連網：GitHub 回應與啟動安裝程式都用假的。"""
import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
from group import updater  # noqa: E402

PATCH = b"MZ fake patch"
SHA = hashlib.sha256(PATCH).hexdigest()


def gh_release(ver, patch=True, digest=True, url=None):
    assets = [{"name": f"PCG-Meeting-Translator-Setup-{ver}.exe",
               "browser_download_url": f"{updater.GITHUB_DL_PREFIX}v{ver}/PCG-Meeting-Translator-Setup-{ver}.exe"}]
    if patch:
        assets.append({"name": f"PCG-Update-{ver}.exe", "size": len(PATCH),
                       "browser_download_url": url or f"{updater.GITHUB_DL_PREFIX}v{ver}/PCG-Update-{ver}.exe",
                       "digest": f"sha256:{SHA}" if digest else None})
    return {"tag_name": f"v{ver}", "html_url": "https://github.com/x", "assets": assets}


class Updater(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def test_versions(self):
        self.assertEqual(updater.parse_ver("v2026.11.5.r7"), (2026, 11, 5, 7))
        self.assertIsNone(updater.parse_ver("dev"))
        self.assertGreater(updater.parse_ver("2026.11.5.r10"), updater.parse_ver("2026.11.5.r9"))

    def test_github(self):
        r = updater.check("2026.11.5.r6", github_fetch=lambda u: gh_release("2026.11.5.r7"))
        self.assertTrue(r["available"])
        self.assertEqual((r["latest"]["kind"], r["latest"]["sha256"]), ("patch", SHA))
        # 已經最新、dev 版、只有完整安裝檔、沒有指紋、網址不是這個 repo、連不上
        self.assertFalse(updater.check("2026.11.5.r7", github_fetch=lambda u: gh_release("2026.11.5.r7"))["available"])
        self.assertFalse(updater.check("dev", github_fetch=lambda u: gh_release("2026.11.5.r7"))["available"])
        self.assertEqual(updater.check("2026.11.5.r6", github_fetch=lambda u: gh_release("2026.11.5.r7", patch=False))
                         ["latest"]["kind"], "full")
        self.assertFalse(updater.check("2026.11.5.r6", github_fetch=lambda u: gh_release("2026.11.5.r7", digest=False))
                         ["available"])
        self.assertFalse(updater.check("2026.11.5.r6", github_fetch=lambda u: gh_release(
            "2026.11.5.r7", url="https://evil.example/PCG-Update-2026.11.5.r7.exe"))["available"])

        def down(u):
            raise OSError("offline")
        self.assertFalse(updater.check("2026.11.5.r6", github_fetch=down)["available"])

    def test_share_and_download(self):
        share = self.tmp / "share"
        share.mkdir()
        (share / "PCG-Update-2026.11.5.r8.exe").write_bytes(PATCH)
        (share / "PCG-Update-2026.11.5.r8.exe.sha256").write_text(SHA + "  PCG-Update-2026.11.5.r8.exe\n")
        (share / "PCG-Meeting-Translator-Setup-2026.11.5.r8.exe").write_bytes(b"full")
        (share / "readme.txt").write_text("x")
        r = updater.check("2026.11.5.r6", share=str(share), github_fetch=lambda u: gh_release("2026.11.5.r7"))
        self.assertEqual((r["latest"]["version"], r["latest"]["source"], r["latest"]["kind"]), ("2026.11.5.r8", "share", "patch"))
        exe = updater.download(r["latest"], self.tmp / "dl")
        self.assertEqual(exe.read_bytes(), PATCH)
        # 指紋不符：刪掉、不安裝
        (share / "PCG-Update-2026.11.5.r8.exe").write_bytes(b"tampered")
        with self.assertRaises(RuntimeError):
            updater.download(updater.from_share(str(share)), self.tmp / "dl2")
        self.assertFalse(any((self.tmp / "dl2").glob("*.exe")))
        # GitHub 下載：照 digest 比對
        latest = updater.check("2026.11.5.r6", github_fetch=lambda u: gh_release("2026.11.5.r7"))["latest"]
        exe = updater.download(latest, self.tmp / "dl3", opener=lambda u: io.BytesIO(PATCH))
        self.assertEqual(exe.name, "PCG-Update-2026.11.5.r7.exe")
        with self.assertRaises(RuntimeError):
            updater.download(latest, self.tmp / "dl4", opener=lambda u: io.BytesIO(b"other"))


if __name__ == "__main__":
    unittest.main()
