"""PCG 集團版：製作模型包（GitHub Actions 的 model-packs.yml 用；Linux 也可以）。

    python group/build_model_packs.py --out dist/packs [--packs phowhisper-small,madlad400-3b] [--old-catalog 舊.json]

語音辨識：從 Hugging Face 下載 Whisper 的語言加強版 → 轉成 CTranslate2 int8（faster-whisper 直接載入）
         → 補齊 tokenizer.json、preprocessor_config.json（離線載入一定要有）→ 用合成語音試辨識一次
翻譯：MADLAD-400 3B 已經是 CTranslate2 int8 → 整理檔名 → 試翻幾個方向
授權：一律從 Hugging Face 讀模型的授權，不是可商用的（Apache-2.0、MIT、BSD）就停下來
打包：<id>.zip（裡面是 <id>/pack.json ＋ 模型檔），超過 GitHub 單檔上限就切成 .001、.002…；寫 catalog.json
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

PART = 1900 * 1048576           # GitHub 單檔上限 2 GB，留一點空間
OK_LICENSES = {"apache-2.0", "mit", "bsd-3-clause", "bsd-2-clause", "bsd"}
ALL_LANGS = ["zh", "en", "id", "vi", "hi", "ja", "ko"]

PACKS = [
    {"id": "phowhisper-small", "repo": "vinai/PhoWhisper-small", "base": "openai/whisper-small",
     "name": "PhoWhisper small（越南文）", "languages": ["vi"],
     "note": "越南 VinAI 用大量越南語錄音加強訓練的 Whisper。CPU 上即時字幕也跑得動"},
    {"id": "phowhisper-medium", "repo": "vinai/PhoWhisper-medium", "base": "openai/whisper-medium",
     "name": "PhoWhisper medium（越南文）", "languages": ["vi"],
     "note": "比 small 準、慢約 2～3 倍：建議錄音檔用；有 NVIDIA 顯示卡時即時字幕也可以用"},
    {"id": "whisper-id-small", "repo": "cahya/whisper-small-id", "base": "openai/whisper-small",
     "name": "Whisper small 印尼文（cahya）", "languages": ["id"],
     "note": "用印尼語資料加強訓練（Common Voice、FLEURS 等）。CPU 上即時字幕也跑得動"},
    {"id": "whisper-id-medium", "repo": "cahya/whisper-medium-id", "base": "openai/whisper-medium",
     "name": "Whisper medium 印尼文（cahya）", "languages": ["id"],
     "note": "比 small 準、慢約 2～3 倍：建議錄音檔用；有 NVIDIA 顯示卡時即時字幕也可以用"},
    {"id": "whisper-hi-small", "repo": "vasista22/whisper-hindi-small", "base": "openai/whisper-small",
     "name": "Whisper small 印地語（vasista22）", "languages": ["hi"],
     "note": "用印地語資料加強訓練。CPU 上即時字幕也跑得動"},
    {"id": "whisper-hi-medium", "repo": "vasista22/whisper-hindi-medium", "base": "openai/whisper-medium",
     "name": "Whisper medium 印地語（vasista22）", "languages": ["hi"],
     "note": "比 small 準、慢約 2～3 倍：建議錄音檔用；有 NVIDIA 顯示卡時即時字幕也可以用"},
    {"id": "madlad400-3b", "repo": "Nextcloud-AI/madlad400-3b-mt-ct2-int8", "type": "mt", "engine": "madlad",
     "name": "MADLAD-400 3B 翻譯（Google）", "languages": ALL_LANGS, "license_fallback": "apache-2.0",
     "note": "400 多種語言的翻譯模型，印尼文、越南文、印地語比內建的 M2M100 好；約 3 GB，CPU 上一句要幾秒：適合錄音檔、效能好的電腦"},
]
# 試辨識用的句子（espeak-ng 合成，聲音很機械，只確認模型載得起來、輸出是那個語言）
SAY = {"vi": "Xin chào mọi người, hôm nay chúng ta kiểm tra máy móc mới.",
       "id": "Selamat pagi semua, hari ini kita memeriksa mesin baru.",
       "hi": "सभी को नमस्ते, आज हम नई मशीनों की जांच करेंगे।"}
TRY_MT = [("zh", "id", "設備要先關電源，再做安全檢查。"), ("id", "zh", "Apakah sarung tangan juga wajib?"),
          ("zh", "vi", "請大家戴上安全帽。"), ("vi", "zh", "Mũ bảo hộ để ở đâu ạ?"), ("hi", "zh", "मशीन अगले शुक्रवार को लगाई जाएगी।")]


def log(msg):
    print(msg, flush=True)


def hf_license(repo):
    from huggingface_hub import HfApi
    info = HfApi().model_info(repo)
    lic = (getattr(info, "card_data", None) or {}).get("license") if getattr(info, "card_data", None) else None
    if not lic:
        lic = next((t.split(":", 1)[1] for t in (info.tags or []) if t.startswith("license:")), None)
    return (lic or "").lower()


def read_wav16k(path):
    """讀 WAV 成 16 kHz 單聲道 float32（自己讀，不經過 PyAV：新版 PyAV 與 faster-whisper 的 decode_audio 不相容）"""
    import wave
    import numpy as np
    with wave.open(str(path), "rb") as w:
        sr, ch, n = w.getframerate(), w.getnchannels(), w.getnframes()
        a = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768.0
    if ch > 1:
        a = a.reshape(-1, ch).mean(axis=1)
    if sr != 16000:
        x = np.arange(0, len(a), sr / 16000.0)
        a = np.interp(x, np.arange(len(a)), a).astype(np.float32)
    return a


def build_asr(spec, work, out):
    from huggingface_hub import snapshot_download
    import ctranslate2
    src = Path(snapshot_download(spec["repo"], local_dir=str(work / "src"),
                                 allow_patterns=["*.json", "*.txt", "*.bin", "*.safetensors", "*.model"]))
    # 離線載入要 tokenizer.json 與 preprocessor_config.json：模型裡沒有就用 transformers 產生／從原版 Whisper 補
    if not (src / "tokenizer.json").is_file():
        from transformers import WhisperTokenizerFast
        try:
            WhisperTokenizerFast.from_pretrained(str(src)).save_pretrained(str(src))
        except Exception:
            WhisperTokenizerFast.from_pretrained(spec["base"]).save_pretrained(str(src))
    if not (src / "preprocessor_config.json").is_file():
        from huggingface_hub import hf_hub_download
        shutil.copy(hf_hub_download(spec["base"], "preprocessor_config.json"), src / "preprocessor_config.json")
    dest = out / spec["id"]
    conv = ctranslate2.converters.TransformersConverter(
        str(src), copy_files=["tokenizer.json", "preprocessor_config.json"])
    conv.convert(str(dest), quantization="int8", force=True)
    shutil.rmtree(src, ignore_errors=True)
    # 試辨識一次（合成語音）：載得起來、不出錯；印出結果給人看
    from faster_whisper import WhisperModel
    lang = spec["languages"][0]
    wav = work / "say.wav"
    try:
        subprocess.run(["espeak-ng", "-v", lang, "-w", str(wav), SAY[lang]], check=True, capture_output=True)
        m = WhisperModel(str(dest), device="cpu", compute_type="int8")
        segs, _ = m.transcribe(read_wav16k(wav), language=lang, beam_size=1)
        text = " ".join(s.text.strip() for s in segs)
        log(f"   試辨識（{lang}）：{text or '（沒有文字）'}")
    except FileNotFoundError:
        log("   （沒有 espeak-ng，略過試辨識）")
    return dest


def build_mt(spec, work, out):
    from huggingface_hub import snapshot_download
    dest = out / spec["id"]
    snapshot_download(spec["repo"], local_dir=str(dest), allow_patterns=["*.bin", "*.json", "*.model"])
    for junk in (dest / ".cache",):
        shutil.rmtree(junk, ignore_errors=True)
    if (dest / "spiece.model").is_file() and not (dest / "sentencepiece.model").is_file():
        (dest / "spiece.model").rename(dest / "sentencepiece.model")
    if not (dest / "model.bin").is_file() or not (dest / "sentencepiece.model").is_file():
        sys.exit(f"[錯誤] {spec['repo']} 缺 model.bin 或 sentencepiece.model")
    import ctranslate2
    import sentencepiece
    sp = sentencepiece.SentencePieceProcessor()
    sp.Load(str(dest / "sentencepiece.model"))
    tr = ctranslate2.Translator(str(dest), device="cpu", compute_type="int8")
    for src_l, tgt, text in TRY_MT:
        r = tr.translate_batch([sp.Encode(f"<2{tgt}> {text}", out_type=str)], beam_size=1, max_decoding_length=128)
        out_text = sp.Decode(r[0].hypotheses[0])
        log(f"   試翻 {src_l}→{tgt}：{text} → {out_text}")
        if not out_text.strip():
            sys.exit(f"[錯誤] {spec['id']} 翻譯沒有結果（{src_l}→{tgt}）")
    return dest


def package(spec, dest, out, lic, version):
    meta = {"id": spec["id"], "name": spec["name"], "type": spec.get("type", "asr"),
            "engine": spec.get("engine", "faster-whisper"), "languages": spec["languages"],
            "purpose": ["live", "file"], "version": version, "license": lic, "source": f"https://huggingface.co/{spec['repo']}",
            "note": spec["note"]}
    size = sum(f.stat().st_size for f in dest.rglob("*") if f.is_file())
    meta["size_mb"] = round(size / 1048576)
    (dest / "pack.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    zpath = out / f"{spec['id']}.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_STORED, allowZip64=True) as z:     # 模型檔壓不太小，不壓縮比較快
        for f in sorted(dest.rglob("*")):
            if f.is_file():
                z.write(f, f"{spec['id']}/{f.relative_to(dest).as_posix()}")
    shutil.rmtree(dest)
    parts = []
    total = zpath.stat().st_size
    if total <= PART:
        names = [zpath]
    else:
        names = []
        with open(zpath, "rb") as src:
            i = 1
            while True:
                chunk = src.read(PART)
                if not chunk:
                    break
                p = out / f"{zpath.name}.{i:03d}"
                p.write_bytes(chunk)
                names.append(p)
                i += 1
        zpath.unlink()
    for p in names:
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for c in iter(lambda: f.read(1 << 20), b""):
                h.update(c)
        parts.append({"name": p.name, "size": p.stat().st_size, "sha256": h.hexdigest()})
    log(f"   {spec['id']}：{meta['size_mb']} MB，{len(parts)} 個檔案")
    return dict(meta, parts=parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--packs", default="")
    ap.add_argument("--version", default="1")
    ap.add_argument("--old-catalog", default="")
    a = ap.parse_args()
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    want = [x.strip() for x in a.packs.split(",") if x.strip()] or [p["id"] for p in PACKS]
    unknown = set(want) - {p["id"] for p in PACKS}
    if unknown:
        sys.exit(f"[錯誤] 不認得的模型包：{', '.join(sorted(unknown))}")
    old = {}
    if a.old_catalog and os.path.isfile(a.old_catalog):
        old = {p["id"]: p for p in json.load(open(a.old_catalog, encoding="utf-8")).get("packs", [])}
    built = {}
    for spec in PACKS:
        if spec["id"] not in want:
            continue
        log(f"▶ {spec['id']}（{spec['repo']}）")
        lic = hf_license(spec["repo"]) or spec.get("license_fallback", "")
        if lic not in OK_LICENSES:
            sys.exit(f"[錯誤] {spec['repo']} 的授權是「{lic or '沒寫'}」，不確定能商用，不打包")
        log(f"   授權：{lic}")
        work = Path(tempfile.mkdtemp(dir=out))
        try:
            dest = build_mt(spec, work, out) if spec.get("type") == "mt" else build_asr(spec, work, out)
        finally:
            shutil.rmtree(work, ignore_errors=True)
        built[spec["id"]] = package(spec, dest, out, lic, a.version)
    catalog = {"format": 1, "packs": [built.get(p["id"]) or old.get(p["id"]) for p in PACKS
                                      if built.get(p["id"]) or old.get(p["id"])]}
    (out / "catalog.json").write_text(json.dumps(catalog, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"完成：{', '.join(built)}；清單共 {len(catalog['packs'])} 個模型包")


if __name__ == "__main__":
    main()
