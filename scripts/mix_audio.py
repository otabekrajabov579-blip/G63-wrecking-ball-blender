"""Haqiqiy (BBC Sound Effects) yozuvlardan videoga mos ovoz miksi.
    E:\\blendr\\5.2\\python\\bin\\python.exe -I scripts\\mix_audio.py
Natija: assets/sounds/final_mix.wav (48 kHz, stereo, 27 s)
Manba: BBC Sound Effects (sound-effects.bbcrewind.co.uk), RemArc litsenziyasi - shaxsiy, ta'lim va tadqiqot maqsadida.
"""
import wave, os, numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B = os.path.join(ROOT, "assets", "sounds", "bbc")
SR = 48000
DUR = 27.0
FPS = 24
rng = np.random.default_rng(4)


def T(frame):                       # kadr -> soniya
    return (frame - 1) / FPS


RELEASE, IMPACT, SLOW_END = T(240), T(291), T(525)


def load(name):
    w = wave.open(os.path.join(B, name + ".wav"))
    sr, ch, n = w.getframerate(), w.getnchannels(), w.getnframes()
    a = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768
    a = a.reshape(-1, ch)
    if ch == 1:
        a = np.repeat(a, 2, 1)
    t_old = np.arange(len(a)) / sr
    t_new = np.arange(int(len(a) / sr * SR)) / SR
    return np.stack([np.interp(t_new, t_old, a[:, c]) for c in range(2)], 1)


def seg(a, t0, t1):
    return a[int(t0 * SR):int(t1 * SR)].copy()


def speed(a, f):                    # f < 1: sekinroq va pastroq (slow-mo)
    n = int(len(a) / f)
    x = np.linspace(0, len(a) - 1, n)
    return np.stack([np.interp(x, np.arange(len(a)), a[:, c]) for c in range(2)], 1)


def fade(a, fi=0.01, fo=0.05):
    n = len(a); e = np.ones(n)
    i = min(int(fi * SR), n); o = min(int(fo * SR), n)
    if i: e[:i] = np.linspace(0, 1, i)
    if o: e[-o:] = np.minimum(e[-o:], np.linspace(1, 0, o))
    return a * e[:, None]


def lowpass(a, fc):
    X = np.fft.rfft(a, axis=0); f = np.fft.rfftfreq(len(a), 1 / SR)
    X *= (1 / np.sqrt(1 + (f / fc) ** 4))[:, None]
    return np.fft.irfft(X, len(a), axis=0)


def highpass(a, fc):
    X = np.fft.rfft(a, axis=0); f = np.fft.rfftfreq(len(a), 1 / SR)
    X *= (1 / np.sqrt(1 + (fc / np.maximum(f, 1e-3)) ** 4))[:, None]
    return np.fft.irfft(X, len(a), axis=0)


def db(x):
    return 10 ** (x / 20)


mix = np.zeros((int(DUR * SR), 2))


def place(a, t, gain_db=0.0, align=0.0):
    """a ni shunday joylashtiradiki, a ichidagi 'align' soniya videodagi t soniyaga to'g'ri kelsin."""
    s = int((t - align) * SR)
    a = a * db(gain_db)
    if s < 0:
        a = a[-s:]; s = 0
    e = min(len(mix), s + len(a))
    if e > s:
        mix[s:e] += a[:e - s]


def reverb(a, rt=1.2, wet=0.25):
    """Qurilish maydoni: binolardan qaytgan aks-sado (erta qaytishlar + so'nuvchi dum)."""
    n = int(rt * SR); t = np.arange(n) / SR
    ir = rng.normal(size=(n, 2)) * np.exp(-6.9 * t / rt)[:, None] * 0.25
    for d, g in ((0.11, 0.5), (0.19, 0.35), (0.27, 0.25)):
        ir[int(d * SR)] += g
    ir[0] = 0
    L = len(a) + n - 1; F = 1 << (L - 1).bit_length()
    wet_sig = np.zeros((L, 2))
    for c in range(2):
        wet_sig[:, c] = np.fft.irfft(np.fft.rfft(a[:, c], F) * np.fft.rfft(ir[:, c], F), F)[:L]
    wet_sig *= np.abs(a).max() / (np.abs(wet_sig).max() + 1e-9)
    dry = np.concatenate([a, np.zeros((n - 1, 2))])
    return dry * (1 - wet) + wet_sig * wet


# ---------------------------------------------------------------- 1) qurilish maydoni foni (slow-mo da bo'g'iqlashadi)
amb = load("00008018")[:int(DUR * SR)]
if len(amb) < len(mix):
    amb = np.concatenate([amb, amb[:len(mix) - len(amb)]])
amb_lp = lowpass(amb, 500)
k = np.ones(len(mix))
t = np.arange(len(mix)) / SR
k = np.clip((t - IMPACT) / 0.25, 0, 1) * np.clip((SLOW_END - t) / 0.6, 0, 1)    # 0 - oddiy, 1 - slow-mo
amb_mix = amb * (1 - k)[:, None] + amb_lp * db(-6) * k[:, None]
env = np.clip(t / 1.5, 0, 1) * np.clip((DUR - t) / 2.0, 0, 1)
place(amb_mix * env[:, None], 0.0, 0)

# ---------------------------------------------------------------- 2) kran: mexanizm g'uvillashi (kamera kranga yaqinlashganda kuchayadi)
crane = fade(seg(load("07032345"), 60.0, 66.0), 1.2, 1.5)
ce = np.clip((np.arange(len(crane)) / SR) / 3.0, 0.3, 1.0)
place(crane * ce[:, None], T(132), -10)
sq1 = fade(seg(load("07037370"), 2.6, 6.6), 0.2, 0.6)        # trosning metall g'ichirlashi
sq2 = fade(seg(load("07037373"), 0.6, 2.9), 0.05, 0.5)
place(highpass(sq1, 300), T(190), -14)
place(highpass(sq2, 300), T(225), -15)

# ---------------------------------------------------------------- 3) tros uzilishi: zanjir bolti + metall chirq + uchqun shitirlashi
bolt = load("07011077")
place(fade(seg(bolt, 1.25, 2.6), 0.003, 0.4), RELEASE, -2, align=1.46 - 1.25)
clank = fade(seg(load("07022373"), 0.85, 2.0), 0.003, 0.5)
place(highpass(clank, 800), RELEASE + 0.02, -12, align=0.98 - 0.85)
cr = rng.normal(size=(int(0.5 * SR), 2)) * (rng.random((int(0.5 * SR), 1)) > 0.985)
cr *= np.exp(-np.arange(len(cr)) / SR * 7)[:, None]
place(highpass(cr, 2500), RELEASE, -10)

# ---------------------------------------------------------------- 4) tushish: kuchayib boruvchi havo shuvillashi (zarbada keskin uziladi)
n = int((IMPACT - RELEASE) * SR)
w = rng.normal(size=(n, 2)); tt = np.arange(n) / SR
w = lowpass(w, 900) * 0.6 + highpass(lowpass(w, 3500), 600) * 0.4
w *= ((tt / tt[-1]) ** 2.2)[:, None]
w[-int(0.01 * SR):] *= np.linspace(1, 0, int(0.01 * SR))[:, None]
place(w / np.abs(w).max(), RELEASE, -9)

# ---------------------------------------------------------------- 5) ZARBA (12,08 s): qatlamli
imp = np.zeros((int(14 * SR), 2))


def ip(a, t, g=0.0, align=0.0):
    s = int((t - align) * SR); e = min(len(imp), s + len(a))
    if s < 0:
        a = a[-s:]; s = 0
    if e > s:
        imp[s:e] += a[:e - s] * db(g)


demo = load("07065153")
hit = fade(seg(demo, 0.85, 6.5), 0.002, 1.5)                  # haqiqiy buzish shari zarbasi
ip(hit, 0.0, 0, align=1.0 - 0.85)
ip(lowpass(speed(hit, 0.5), 180), 0.0, 2, align=(1.0 - 0.85) / 0.5)   # og'irlik uchun past gumburlash
car = fade(seg(load("07022351"), 0.7, 5.0), 0.002, 1.2)        # mashina ezilishi
ip(car, 0.0, -1, align=0.76 - 0.7)                             # birinchi tegish 0,76 s da
mcr = fade(seg(load("07022366"), 0.75, 3.4), 0.002, 0.8)
ip(mcr, 0.03, -3, align=1.16 - 0.75)
mim = fade(seg(load("07054042"), 0.6, 3.6), 0.002, 0.8)
ip(mim, 0.06, -6, align=0.86 - 0.6)
g1 = fade(seg(load("07022393"), 1.9, 5.2), 0.002, 0.8)         # shisha sinishi (eng baland)
ip(g1, 0.02, -2, align=2.22 - 1.9)
g2 = fade(seg(load("07022488"), 0.9, 4.0), 0.002, 0.8)
ip(g2, 0.06, -4, align=1.12 - 0.9)
g3 = fade(seg(load("07022493"), 1.2, 4.5), 0.002, 0.8)
ip(g3, 0.14, -6, align=1.42 - 1.2)
# slow-mo: sinish ovozlarining sekinlashtirilgan "dumi" (kino uslubi)
slow_tail = speed(fade(seg(load("07022393"), 2.0, 5.2), 0.05, 1.0), 0.45)
ip(lowpass(slow_tail, 5000), 0.25, -9)
slow_metal = speed(fade(seg(load("07022318"), 1.0, 7.0), 0.05, 1.5), 0.5)
ip(lowpass(slow_metal, 2500), 0.35, -14)
imp = reverb(imp, rt=1.4, wet=0.22)
place(imp, IMPACT, 0)

# ---------------------------------------------------------------- 6) slow-mo davomida: bo'laklar va qismlar yerga tushadi (sekinlashtirilgan)
for i, (tm, g) in enumerate(((13.4, -16), (14.6, -15), (15.9, -17), (17.3, -16), (18.8, -18), (20.2, -19))):
    src = ["07022488", "07022493", "07022393"][i % 3]
    piece = fade(seg(load(src), 2.0, 4.2), 0.02, 0.8)
    place(lowpass(speed(piece, 0.6), 6000), tm, g)
for tm, g in ((14.2, -12), (16.6, -13)):                          # og'ir qismlar (fara, zaxira g'ildirak) yerga uriladi
    thud = fade(seg(load("07054042"), 2.3, 3.6), 0.003, 0.6)
    place(lowpass(speed(thud, 0.55), 1500), tm, g)
ball2 = fade(seg(demo, 46.2, 48.5), 0.003, 0.8)                   # shar qaytib qayta tushishi
place(lowpass(speed(ball2, 0.6), 900), 13.0, -10)

# ---------------------------------------------------------------- 7) real vaqtga qaytish: signalizatsiya va oxirgi bo'laklar
alarm = fade(seg(load("07043175"), 0.2, 0.2 + (DUR - SLOW_END) + 0.3), 0.4, 1.8)
place(highpass(alarm, 250), SLOW_END - 0.2, -15)
for tm, g in ((SLOW_END + 0.3, -20), (SLOW_END + 1.1, -22), (SLOW_END + 2.4, -24)):
    place(fade(seg(load("07022488"), 2.0, 3.2), 0.01, 0.4), tm, g)

# ---------------------------------------------------------------- yakuniy: yumshoq limiter va normalizatsiya
peak = np.abs(mix).max()
mix = mix / peak * db(-1.0)
mix = np.tanh(mix * 1.4) / np.tanh(1.4)                     # yumshoq cheklash (tepa qismlar silliq)
mix = mix / np.abs(mix).max() * db(-1.0)
out = os.path.join(ROOT, "assets", "sounds", "final_mix.wav")
with wave.open(out, "wb") as wv:
    wv.setnchannels(2); wv.setsampwidth(2); wv.setframerate(SR)
    wv.writeframes((mix * 32767).astype(np.int16).tobytes())
rms = 20 * np.log10(np.sqrt((mix ** 2).mean()) + 1e-9)
print(f"MIX OK {out} dur={len(mix)/SR:.2f}s rms={rms:.1f}dB release={RELEASE:.2f}s impact={IMPACT:.2f}s slow_end={SLOW_END:.2f}s")
