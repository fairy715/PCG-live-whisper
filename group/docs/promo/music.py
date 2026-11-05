"""推廣動畫的配樂：程式自己合成（沒有任何外部音源，不會有版權問題）。
120 BPM、C–G–Am–F，約 61 秒：前奏 → 主歌（鼓、貝斯、琶音）→ 中段放輕 → 尾奏。
執行：python3 music.py music.wav
"""
import sys
import wave
import numpy as np

SR = 44100
BPM = 120
BEAT = 60 / BPM
BAR = BEAT * 4
DUR = 61.0
N = int(SR * DUR)
L = np.zeros(N)
R = np.zeros(N)
rng = np.random.default_rng(7)


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


CHORDS = [(48, (0, 4, 7)), (43, (0, 4, 7)), (45, (0, 3, 7)), (41, (0, 4, 7))]   # C G Am F（根音 MIDI、組成音）


def add(sig, start, pan=0.0, gain=1.0):
    i = int(start * SR)
    if i >= N:
        return
    sig = sig[: N - i] * gain
    L[i:i + len(sig)] += sig * (1 - max(pan, 0))
    R[i:i + len(sig)] += sig * (1 + min(pan, 0))


def env(n, a=0.01, d=0.2, s=0.6, r=0.3):
    t = np.arange(n) / SR
    tot = n / SR
    e = np.where(t < a, t / a, np.where(t < a + d, 1 - (1 - s) * (t - a) / d, s))
    rel = np.clip((tot - t) / r, 0, 1)
    return e * rel


def lowpass(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):          # 單極點低通（只用在短的音符上，速度還可以）
        acc = (1 - a) * x[i] + a * acc
        y[i] = acc
    return y


def saw(f, n, detune=0.0):
    t = np.arange(n) / SR
    ph = (t * f * (1 + detune)) % 1.0
    return 2 * ph - 1


def pad(root, tones, length):
    n = int(length * SR)
    s = np.zeros(n)
    for k in tones:
        f = hz(root + 12 + k)
        s += saw(f, n, 0.003) + saw(f, n, -0.004)
    s = s[::1]
    s = lowpass(s / len(tones), 900)
    return s * env(n, a=0.4, d=0.5, s=0.8, r=0.6)


def pluck(f, length=0.35):
    n = int(length * SR)
    t = np.arange(n) / SR
    s = 0.7 * np.sin(2 * np.pi * f * t) + 0.3 * np.sign(np.sin(2 * np.pi * f * t)) * 0.4
    return s * np.exp(-t * 9)


def bass(f, length):
    n = int(length * SR)
    t = np.arange(n) / SR
    s = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * 2 * f * t)
    return s * env(n, a=0.005, d=0.1, s=0.7, r=0.05)


def kick():
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    f = 45 + 110 * np.exp(-t * 30)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t * 8)


def noise_hit(length, decay, hp=True):
    n = int(length * SR)
    t = np.arange(n) / SR
    s = rng.standard_normal(n)
    if hp:
        s = s - np.convolve(s, np.ones(8) / 8, mode="same")
    return s * np.exp(-t * decay)


def section(bar):
    if bar < 4:
        return "intro"
    if 14 <= bar < 16:
        return "break"
    if bar >= 27:
        return "outro"
    return "main"


nbars = int(DUR / BAR) + 1
duck = np.ones(N)
for b in range(nbars):
    t0 = b * BAR
    sec = section(b)
    root, tones = CHORDS[b % 4]
    add(pad(root, tones, BAR + 0.5), t0, gain=0.22 if sec != "outro" else 0.26)
    # 琶音（16 分音符，左右交替）
    if sec in ("main", "break", "intro") and not (sec == "intro" and b < 2):
        seq = [0, 1, 2, 1, 2, 3, 2, 1]
        notes = [root + 24 + tones[i % 3] + (12 if i == 3 else 0) for i in seq]
        for i in range(16):
            m = notes[i % 8]
            add(pluck(hz(m)), t0 + i * BEAT / 4, pan=(0.35 if i % 2 else -0.35),
                gain=0.10 if sec != "break" else 0.07)
    if sec == "main":
        for q in range(4):
            tq = t0 + q * BEAT
            add(kick(), tq, gain=0.9)
            i = int(tq * SR)
            duck[i:i + int(0.25 * SR)] = np.minimum(duck[i:i + int(0.25 * SR)], np.linspace(0.45, 1, int(0.25 * SR))[: max(0, min(int(0.25 * SR), N - i))])
            add(noise_hit(0.08, 60), tq + BEAT / 2, pan=0.2, gain=0.08)         # 反拍腳踏鈸
            if q in (1, 3):
                add(noise_hit(0.2, 18, hp=False) * 0.6, tq, gain=0.18)           # 拍手
            f = hz(root - 12)
            add(bass(f, BEAT / 2 - 0.02), tq, gain=0.35)
            add(bass(f, BEAT / 2 - 0.02), tq + BEAT / 2, gain=0.28)
    if sec == "break":
        add(kick(), t0, gain=0.6)
    if sec == "outro" and b == 27:
        add(kick(), t0, gain=1.0)
        add(noise_hit(1.5, 2.5, hp=False) * 0.5, t0, gain=0.15)                  # 收尾的鈸聲

L *= duck ** 0.6
R *= duck ** 0.6
mix = np.stack([L, R], axis=1)
mix = np.tanh(mix * 1.4)
fade_in = np.clip(np.arange(N) / (SR * 1.0), 0, 1)
fade_out = np.clip((N - np.arange(N)) / (SR * 3.0), 0, 1)
mix *= (fade_in * fade_out)[:, None]
mix /= np.max(np.abs(mix)) / 0.89
pcm = (mix * 32767).astype("<i2")
with wave.open(sys.argv[1] if len(sys.argv) > 1 else "music.wav", "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print("ok", DUR, "s")
