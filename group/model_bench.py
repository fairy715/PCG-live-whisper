"""PCG 集團版 r33：各個辨識模型的實測錯誤率（給 IT 設定頁的「模型管理」顯示在每個模型旁邊）。

數字來自 group/bench_asr.py 在 GitHub 上跑的結果（2026-11-19，公開資料集 FLEURS 與 ASCEND，每種語言 50 句，
錯的字或詞 ÷ 標準答案的字／詞數，越低越好）。完整的表與限制在 IT 必讀的「實測：各模型的錯誤率」。
重跑之後請把新的數字填回這裡，並改 DATE。

cpu＝在沒有顯示卡的 4 核心機器上，處理時間 ÷ 聲音長度（接近或超過 1 就跟不上即時字幕）。
"""
DATE = "2026-11-19"
SENTENCES = 50
BUILTIN = "small"                    # 安裝檔內建的模型（不是模型包）
LANGS = ("zh", "id", "vi", "hi", "en", "zh-en")

RESULTS = {
    "small": {"cpu": 0.3, "zh": 10.6, "id": 16.1, "vi": 20.7, "hi": 55.9, "en": 6.1, "zh-en": 28.1},
    "whisper-base": {"cpu": 0.1, "zh": 17.2, "id": 30.6, "vi": 40.1, "hi": 105.7, "en": 8.9, "zh-en": 37.6},
    "whisper-medium": {"cpu": 0.85, "zh": 6.0, "id": 9.1, "vi": 14.0, "hi": 36.7, "en": 4.4, "zh-en": 26.8},
    "whisper-large-v3-turbo": {"cpu": 1.0, "zh": 5.9, "id": 7.6, "vi": 10.2, "hi": 30.5, "en": 4.8, "zh-en": 20.9},
    "breeze-asr-25": {"cpu": 1.6, "zh": 5.3, "zh-en": 17.8},
    "phowhisper-small": {"cpu": 0.3, "vi": 13.1},
    "phowhisper-medium": {"cpu": 0.85, "vi": 9.7},
    "whisper-id-small": {"cpu": 0.3, "id": 9.2},
    "whisper-id-medium": {"cpu": 0.85, "id": 7.1},
    "whisper-hi-small": {"cpu": 0.6, "hi": 14.8},
    "whisper-hi-medium": {"cpu": 1.5, "hi": 11.2},
}


def for_pack(pack_id):
    """某個模型包的實測結果：{"cpu": …, "rates": [[語言, 錯誤率, 內建 small 在同一種語言的錯誤率], …]}；沒測過回 None"""
    r = RESULTS.get(str(pack_id or ""))
    if not r:
        return None
    base = RESULTS[BUILTIN]
    return {"cpu": r.get("cpu"), "rates": [[l, r[l], base.get(l)] for l in LANGS if l in r]}


def summary():
    """給畫面的整包資料"""
    return {"date": DATE, "sentences": SENTENCES, "builtin": for_pack(BUILTIN),
            "packs": {k: for_pack(k) for k in RESULTS if k != BUILTIN}}
