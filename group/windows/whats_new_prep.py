"""PCG 集團版：發布時準備這一版的 whats-new.json（同仁頁面「有新版本」視窗顯示的新功能）。

    python group/windows/whats_new_prep.py <版本，例如 2026.11.8.r19> <輸出檔>

group/whats-new.json 的 release 要等於這一次的 rN 才輸出（填上完整版本號）；
不一樣代表這次發布前忘了更新說明，就不附（視窗只說「這一版有改進與修正」），不讓舊說明配到新版本。
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def prepare(version, out, src=ROOT / "group" / "whats-new.json"):
    try:
        data = json.loads(Path(src).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"[注意] 讀不到 {src}：{e}，這次不附新功能說明")
        return False
    want = "r" + str(version).rsplit(".r", 1)[-1]
    if str(data.get("release") or "") != want:
        print(f"[注意] group/whats-new.json 是 {data.get('release')} 的說明，這次是 {want}：不附新功能說明")
        return False
    data = {k: v for k, v in data.items() if not k.startswith("_")}
    data["version"] = version
    Path(out).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"新功能說明：{out}（{', '.join(k for k in ('zh', 'en', 'id', 'vi', 'hi') if data.get(k))}）")
    return True


if __name__ == "__main__":
    prepare(sys.argv[1], sys.argv[2])
