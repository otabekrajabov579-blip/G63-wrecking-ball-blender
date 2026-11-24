"""Sintez qilingan tovush effektlari (48 kHz, 16-bit, WAV).
Ishga tushirish:  E:\\blendr\\5.2\\python\\bin\\python.exe -I scripts\\make_sounds.py assets\\sounds
"""
import sys, os, wave
import numpy as np

SR = 48000
rng = np.random.default_rng(7)
out = sys.argv[1] if len(sys.argv) > 1 else "assets/sounds"
os.makedirs(out, exist_ok=True)


def t(sec):
    return np.arange(int(SR * sec)) / SR


def lowpass(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x); s = 0.0
    for i, v in enumerate(x):
        s = (1 - a) * v + a * s; y[i] = s
    return y


def fft_band(x, lo, hi):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    X[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(X, len(x))


def resonator(x, freq, q):
    # 2-qutbli rezonator (metall / shisha ovozi uchun)
    w = 2 * np.pi * freq / SR; r = np.exp(-w / (2 * q))
    b1, b2 = 2 * r * np.cos(w), -r * r
    y = np.zeros_like(x); y1 = y2 = 0.0
    for i, v in enumerate(x):
        y0 = v + b1 * y1 + b2 * y2; y[i] = y0; y2, y1 = y1, y0
    return y


def norm(x, peak=0.9):
    m = np.max(np.abs(x)) or 1.0
    return x / m * peak


def save(name, x):
    x = np.clip(x, -1, 1)
    with wave.open(os.path.join(out, name), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    print("saved", name, f"{len(x)/SR:.1f}s")


def metal_hit(dur, base, decay, partials=(1, 2.76, 5.40, 8.93, 13.3)):
    tt = t(dur); y = np.zeros_like(tt)
    for k, p in enumerate(partials):
        y += np.sin(2 * np.pi * base * p * tt + rng.uniform(0, 6)) * np.exp(-tt * decay * (1 + k * 0.6)) / (k + 1)
    return y


# 1) Qurilish maydoni foni: shamol + uzoqdagi shovqin (27 s)
tt = t(27.0)
wind = lowpass(rng.normal(size=tt.size), 400)
gust = 0.6 + 0.4 * np.sin(2 * np.pi * 0.11 * tt) * np.sin(2 * np.pi * 0.037 * tt + 1)
rumble = lowpass(rng.normal(size=tt.size), 60) * 2.5
amb = norm(wind * gust + rumble, 0.35)
fade = np.minimum(1, np.minimum(tt / 1.0, (27 - tt) / 1.5))
save("ambient_construction_wind.wav", amb * fade)

# 2) Kran tebranishi - po'lat trosning g'ichirlashi (5 s)
tt = t(5.0); y = np.zeros_like(tt)
for c in (0.6, 2.2, 3.9):
    env = np.exp(-((tt - c) / 0.35) ** 2)
    f0 = 180 + 60 * np.sin(2 * np.pi * 1.3 * (tt - c))
    phase = 2 * np.pi * np.cumsum(f0) / SR
    saw = 2 * ((phase / (2 * np.pi)) % 1) - 1
    y += saw * env * (0.6 + 0.4 * rng.random(tt.size) ** 4)
y = resonator(y, 900, 25) * 0.3 + resonator(y, 2300, 40) * 0.2
save("crane_cable_creak.wav", norm(y, 0.6))

# 3) Ilgak uzilishi - metall "chirq" + zanjir zarbasi (2 s)
tt = t(2.0)
snap = metal_hit(2.0, 420, 4) + 0.6 * metal_hit(2.0, 1130, 7)
click = rng.normal(size=tt.size) * np.exp(-tt * 60)
save("hook_release_snap.wav", norm(snap * 0.7 + click * 0.8, 0.85))

# 4) Tushish - kuchayib boruvchi havo shuvillashi (2.2 s = 25 m erkin tushish)
tt = t(2.2); n = rng.normal(size=tt.size); y = np.zeros_like(tt)
seg = SR // 10
for i in range(0, tt.size, seg):
    p = i / tt.size
    y[i:i + seg] = fft_band(n[i:i + seg], 200 + 1500 * p, 800 + 4000 * p)
env = (tt / 2.2) ** 2
save("ball_fall_whoosh.wav", norm(y * env, 0.75))


# 5) Zarba: og'ir gumburlash + metall ezilishi + shisha sinishi
def crash(dur=4.0):
    tt = t(dur)
    thud = np.sin(2 * np.pi * np.cumsum(30 + 70 * np.exp(-tt * 8)) / SR) * np.exp(-tt * 3)
    crunch = lowpass(rng.normal(size=tt.size), 2500) * np.exp(-tt * 2.5)
    crunch = resonator(crunch, 340, 6) * 0.4 + resonator(crunch, 780, 8) * 0.3 + crunch * 0.3
    glass = np.zeros_like(tt)
    for _ in range(140):
        st = abs(rng.normal(0, 0.45)); f = rng.uniform(2500, 9000)
        i0 = int(st * SR)
        if i0 >= tt.size: continue
        L = min(int(0.25 * SR), tt.size - i0); tl = np.arange(L) / SR
        glass[i0:i0 + L] += np.sin(2 * np.pi * f * tl) * np.exp(-tl * rng.uniform(20, 60)) * rng.uniform(0.2, 1)
    metal = metal_hit(dur, 160, 1.6) * 0.5
    return norm(thud * 1.0 + norm(crunch) * 0.7 + norm(glass) * 0.45 + metal, 0.95)


c = crash()
save("impact_crash.wav", c)
# Slow-motion varianti: 0.35x tezlik (ovoz pastlashadi, cho'ziladi)
idx = np.arange(0, c.size - 1, 0.35)
slow = np.interp(idx, np.arange(c.size), c)
slow = slow + 0.3 * np.concatenate([np.zeros(int(0.12 * SR)), slow[:-int(0.12 * SR)]])  # biroz reverb
save("impact_crash_slowmo.wav", norm(slow * np.minimum(1, (slow.size / SR - idx[:0].size - np.arange(slow.size) / SR) / 2 + 0.0001).clip(0, 1), 0.95))

# 6) Bo'laklar yerga tushib to'xtashi - mayda taqillashlar (5 s)
tt = t(5.0); y = np.zeros_like(tt)
for _ in range(70):
    st = rng.uniform(0, 1) ** 1.8 * 4.2; i0 = int(st * SR)
    L = min(int(0.4 * SR), tt.size - i0)
    hit = metal_hit(L / SR, rng.uniform(600, 3500), rng.uniform(10, 30))
    y[i0:i0 + L] += hit[:L] * rng.uniform(0.1, 1) * (1 - st / 5)
save("debris_settle.wav", norm(y, 0.6))
