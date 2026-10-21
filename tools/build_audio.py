"""Sound effects for the viewer (viewer/audio.js): one mono MP3 sprite of every one-shot sound
plus its manifest.

  assets/audio/sfx.mp3    every one-shot, back to back (a marker click first: audio.js finds it
                          after decoding and corrects every offset for the decoder's delay)
  assets/audio/sfx.json   name -> variants [[start, duration], ...] in seconds, mix gain (dB),
                          distance (ref m), category, and the measured levels

Sources: Kenney's CC0 audio packs (Impact, RPG, Interface, Sci-fi; downloaded once into
build/audio_src/) and numpy synthesis (glass tinkle, sub thumps, the Grimble's voice, beeps,
whooshes). Loops (wind, room tone, motors, TV, fire) aren't here: audio_synth.js makes them in
the browser (no download, and MP3 can't loop gaplessly). Credits: assets/audio/CREDITS.md.

Every sound is normalised to the same short-term loudness (max 50 ms RMS, roughly K-weighted,
-14 dBFS) with peaks under -1 dBFS; how loud each plays is its mix gain (`MIX`), applied in the
engine. `--report` decodes the finished MP3 and prints each entry's length, peak and loudness.

Run with a Python that has numpy (Blender's) and with sox + lame on the PATH:
  /Applications/Blender.app/Contents/Resources/5.0/python/bin/python3.11 -I tools/build_audio.py [--report]
"""
import json
import os
import subprocess
import sys
import wave
import zipfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "build" / "audio_src"
OUT = ROOT / "assets" / "audio"
SR = 44100
BITRATE = 64            # kbps, mono CBR
MARK = 0.05             # s: the marker click's position in the sprite
GAP = 0.08              # s of silence before each sound
TARGET = -14.0          # dBFS short-term loudness every sound is normalised to
CEIL = -1.0             # dBFS peak ceiling

PACKS = {
    "impact": "https://kenney.nl/media/pages/assets/impact-sounds/87b4ddecda-1677589768/kenney_impact-sounds.zip",
    "rpg": "https://kenney.nl/media/pages/assets/rpg-audio/8e99002d76-1677590336/kenney_rpg-audio.zip",
    "ui": "https://kenney.nl/media/pages/assets/interface-sounds/fa43c1dd4d-1677589452/kenney_interface-sounds.zip",
    "scifi": "https://kenney.nl/media/pages/assets/sci-fi-sounds/6b296f9ecf-1677589334/kenney_sci-fi-sounds.zip",
}

rng = np.random.default_rng(1234)


# ---------------------------------------------------------------- sources
def fetch():
    for name, url in PACKS.items():
        d = SRC / name
        if (d / "Audio").exists():
            continue
        d.mkdir(parents=True, exist_ok=True)
        z = SRC / f"{name}.zip"
        print("downloading", url)
        # (curl: Blender's Python has no CA certificates for urllib)
        subprocess.run(["curl", "-sSfL", "-o", str(z), url], check=True)
        with zipfile.ZipFile(z) as f:
            for m in f.namelist():
                # only the sounds and the licence (nothing that could run)
                if m.endswith(".ogg") or m.endswith("License.txt"):
                    f.extract(m, d)


_cache = {}
def load(pack, name):
    key = (pack, name)
    if key not in _cache:
        path = SRC / pack / "Audio" / f"{name}.ogg"
        raw = subprocess.run(["sox", str(path), "-t", "f32", "-r", str(SR), "-c", "1", "-"],
                             capture_output=True, check=True).stdout
        _cache[key] = np.frombuffer(raw, np.float32).astype(np.float64)
    return _cache[key].copy()


# ---------------------------------------------------------------- dsp
def secs(n): return n / SR
def N(s): return int(round(s * SR))
def t_axis(n): return np.arange(n) / SR
def db(g): return 20 * np.log10(max(g, 1e-12))
def undb(d): return 10 ** (d / 20)


def speed(x, k):
    """Play k times faster (k < 1: slower and lower), like a tape."""
    n = int(len(x) / k)
    return np.interp(np.arange(n) * k, np.arange(len(x)), x)


def ffilt(x, gain):
    """Zero-phase filter by an FFT magnitude curve gain(freqs)."""
    pad = N(0.06)
    y = np.concatenate([np.zeros(pad), x, np.zeros(pad)])
    n = 1 << int(np.ceil(np.log2(len(y))))
    f = np.fft.rfftfreq(n, 1 / SR)
    return np.fft.irfft(np.fft.rfft(y, n) * gain(f), n)[pad:pad + len(x)]


def lp(fc, order=2): return lambda f: 1 / np.sqrt(1 + (f / fc) ** (2 * order))
def hp(fc, order=2): return lambda f: 1 / np.sqrt(1 + (fc / np.maximum(f, 1e-3)) ** (2 * order))
def bp(fc, q): return lambda f: 1 / np.sqrt(1 + (q * (f / fc - fc / np.maximum(f, 1e-3))) ** 2)
def chain(*gs): return lambda f: np.prod([g(f) for g in gs], axis=0)


def stft_filter(x, gain_t, win=1024, hop=256):
    """Time-varying filter: gain_t(t, freqs) per frame (overlap-add, Hann windows)."""
    w = np.hanning(win + 1)[:-1]
    pad = np.concatenate([np.zeros(win), x, np.zeros(win)])
    out = np.zeros_like(pad)
    f = np.fft.rfftfreq(win, 1 / SR)
    for s in range(0, len(pad) - win, hop):
        t = (s + win / 2 - win) / SR
        X = np.fft.rfft(pad[s:s + win] * w)
        out[s:s + win] += np.fft.irfft(X * gain_t(t, f), win) * w
    return out[win:win + len(x)] / 1.5


def noise(s): return rng.standard_normal(N(s))
def pink(s): return ffilt(noise(s), lambda f: 1 / np.sqrt(np.maximum(f, 20) / 20))
def brown(s): return ffilt(noise(s), lambda f: 20 / np.maximum(f, 20))


def env(n, attack=0.005, decay=None, hold=0.0, release=0.01):
    """Attack, optional hold, then exponential decay (decay = time constant) or a release."""
    t = t_axis(n)
    e = np.minimum(1, t / max(attack, 1e-4))
    if decay:
        e = e * np.exp(-np.maximum(0, t - attack - hold) / decay)
    r = N(release)
    if r:
        e[-r:] *= np.linspace(1, 0, r)
    return e


def fade(x, fin=0.002, fout=0.02):
    x = x.copy()
    a, b = N(fin), N(fout)
    if a: x[:a] *= np.linspace(0, 1, a)
    if b: x[-b:] *= np.linspace(1, 0, b)
    return x


def mix(length, *parts):
    """parts: (signal, start_s, gain) -> one signal of `length` s (or as long as needed)."""
    n = max([N(length)] + [N(s) + len(x) for x, s, _ in parts])
    out = np.zeros(n)
    for x, s, g in parts:
        i = N(s)
        out[i:i + len(x)] += x * g
    return out


def norm_peak(x): return x / (np.abs(x).max() + 1e-12)


def trim(x, head_db=-45, tail_db=-60):
    """Drop leading and trailing silence (keeps 2 ms before the onset), fade the end."""
    a = np.abs(x) / (np.abs(x).max() + 1e-12)
    on = np.nonzero(a > undb(head_db))[0]
    if not len(on):
        return x
    i0 = max(0, on[0] - N(0.002))
    off = np.nonzero(a > undb(tail_db))[0][-1]
    return fade(x[i0:off + 1], 0.001, min(0.03, secs(off - i0) / 4))


def cut(x, s): return fade(x[:N(s)], 0.0, min(0.05, s / 4))


# a sine (or partials) with a pitch glide and decay
def tone(s, f0, f1=None, decay=None, partials=((1, 1.0),), attack=0.003):
    n = N(s)
    t = t_axis(n)
    f = f0 if f1 is None else f0 * (f1 / f0) ** (t / s)
    ph = 2 * np.pi * np.cumsum(np.broadcast_to(f, (n,))) / SR
    y = sum(a * np.sin(k * ph) for k, a in partials)
    return y * env(n, attack, decay, release=0.01)


def sub_thump(s=0.5, f0=70, f1=32, decay=0.14):
    return tone(s, f0, f1, decay, partials=((1, 1.0), (2, 0.25)), attack=0.004)


def tinkle(s, count, lo=2500, hi=9000, first=0.0, power=2.0):
    """Glass shards: short inharmonic pings scattered over `s` seconds, densest at the start."""
    out = np.zeros(N(s) + N(0.5))
    for _ in range(count):
        t0 = first + (s - first) * rng.random() ** power
        f = lo * (hi / lo) ** rng.random()
        d = 0.015 + 0.06 * rng.random()
        a = (0.25 + 0.75 * rng.random()) * (1 - 0.7 * (t0 / s))
        p = tone(d * 5, f, decay=d, partials=((1, 1.0), (2.76, 0.4), (5.4, 0.15)), attack=0.0005)
        i = N(t0)
        out[i:i + len(p)] += p * a
    # tiny grit between the pings
    grit = ffilt(noise(len(out) / SR), hp(4000)) * np.exp(-t_axis(len(out)) / (s * 0.3)) * 0.05
    return out + grit


def whoosh(s, f_lo=250, f_hi=1800, q=1.2, peak_at=0.5):
    """Air moved fast: noise through a band-pass sweeping up to f_hi at `peak_at` and back."""
    x = noise(s)
    def g(t, f):
        k = np.clip(t / s, 0, 1)
        c = f_lo * (f_hi / f_lo) ** (np.sin(np.pi * min(1, k / (2 * peak_at))) if k < peak_at else
                                     np.cos(0.5 * np.pi * (k - peak_at) / (1 - peak_at)))
        return bp(c, q)(f)
    y = stft_filter(x, g)
    t = t_axis(len(y))
    e = np.sin(np.pi * np.clip(t / s, 0, 1)) ** 1.5
    return y * e


def click(f=3800, s=0.03, decay=0.004, body=900, body_amp=0.3):
    """A small plastic/metal click: a resonant transient and a little body."""
    n = N(s)
    imp = noise(s) * env(n, 0.0003, decay)
    y = ffilt(imp, bp(f, 2.0)) * 3 + ffilt(imp, bp(body, 3.0)) * body_amp * 4
    return y


def beep(seq, level=1.0):
    """[(freq, dur, gap), ...] soft-edged sine beeps (a keycard reader)."""
    parts, t = [], 0.0
    for f, d, gap in seq:
        b = tone(d, f, partials=((1, 1.0), (2, 0.12), (3, 0.05)), attack=0.004) * env(N(d), 0.004, release=0.012)
        parts.append((b, t, level))
        t += d + gap
    return mix(t, *parts)


def friction(s, fc=1400, q=0.9, grain=45, rough=0.6):
    """Something sliding (a drawer on its runners): band-passed noise with an uneven grain."""
    x = ffilt(noise(s), bp(fc, q))
    g = ffilt(noise(s), lp(grain, 1))
    g = 1 - rough + rough * np.abs(g) / (np.abs(g).max() + 1e-9) * 2.2
    t = t_axis(len(x))
    e = np.minimum(1, t / 0.04) * np.minimum(1, (s - t) / 0.06)
    return x * g * np.clip(e, 0, 1)


# --- the Grimble's voice: a huge, slow throat
def voiced(s, f0, jitter=0.06, sub=0.6, formants=((280, 4), (620, 5), (1350, 6), (2600, 7)),
           fry=22, fry_depth=0.5, breath=0.25, glide=(1.0, 1.0)):
    n = N(s)
    t = t_axis(n)
    drift = ffilt(rng.standard_normal(n), lp(3, 1))
    drift = drift / (np.abs(drift).max() + 1e-9)
    f = f0 * (glide[0] + (glide[1] - glide[0]) * t / s) * (1 + jitter * drift)
    ph = np.cumsum(f) / SR
    saw = 2 * (ph % 1) - 1                              # glottal buzz (rich in harmonics)
    sub_ = np.sign(np.sin(np.pi * ph)) * sub            # a subharmonic an octave down: a rasp
    src = saw + sub_
    am = 1 - fry_depth + fry_depth * (0.5 + 0.5 * np.sin(2 * np.pi * np.cumsum(fry * (1 + 0.3 * drift)) / SR))
    src = src * am + noise(s) * breath
    y = sum(ffilt(src, bp(fc, q)) * (1.0 / (i + 1)) for i, (fc, q) in enumerate(formants))
    return ffilt(y, lp(3200, 2))


def breath(s, inhale, size=1.0):
    """One breath of something huge: in (higher, rising hiss) or out (lower, with a rasp)."""
    n = N(s)
    t = t_axis(n)
    x = noise(s)
    if inhale:
        y = stft_filter(x, lambda tt, f: bp(700 * (1 + 0.5 * tt / s) / size, 1.4)(f) + 0.5 * bp(1900 / size, 2.5)(f))
        e = np.sin(np.pi * np.clip(t / s, 0, 1) ** 0.7) ** 1.2
    else:
        y = stft_filter(x, lambda tt, f: bp(420 * (1 - 0.3 * tt / s) / size, 1.1)(f) + 0.35 * bp(1100 / size, 3)(f))
        y = y + voiced(s, 38, jitter=0.1, breath=0.1, fry=17, fry_depth=0.7) * 0.18
        e = np.sin(np.pi * np.clip(t / s, 0, 1) ** 0.45) ** 1.5
    return y * e


def sniff(count=3, size=1.0):
    parts = []
    t = 0.0
    for i in range(count):
        d = 0.07 + 0.03 * rng.random()
        b = ffilt(noise(d), chain(bp(1700 / size, 1.6), hp(500))) * env(N(d), 0.008, d / 2.5, release=0.01)
        parts.append((b, t, 1.0 - 0.15 * i))
        t += d + 0.06 + 0.04 * rng.random()
    return mix(t + 0.1, *parts)


# ---------------------------------------------------------------- the sounds
# name -> list of variant signals; each recipe is a function so the build is one pass
def k(pack, name, rate=1.0, gain=1.0, filt=None):
    x = load(pack, name)
    if rate != 1.0:
        x = speed(x, rate)
    if filt:
        x = ffilt(x, filt)
    return x * gain


def door_locked(v):
    r = [1.0, 1.08, 0.94] if v == 0 else [0.97, 0.9, 1.05, 1.0]
    parts = []
    for i, rate in enumerate(r):
        t = [0, 0.11, 0.23, 0.33][i] + 0.015 * rng.random()
        parts.append((k("rpg", "metalLatch", rate * 0.9, filt=lp(5000)), t, 0.9 - 0.12 * i))
        parts.append((k("impact", f"impactWood_light_00{(i + v) % 5}", 1.1), t + 0.004, 0.35))
    return trim(mix(0.6, *parts))


def drawer(opening, v):
    s = 0.34 if opening else 0.26
    slide = friction(s, fc=1100 + 300 * v, q=0.8, grain=40 + 10 * v)
    rumble = friction(s, fc=300, q=0.7, grain=25) * 0.5
    stop = k("impact", f"impactWood_{'light' if opening else 'medium'}_00{v + 1}", 1.15 if opening else 1.0)
    return trim(mix(s + 0.3, (slide, 0, 0.5), (rumble, 0, 0.6), (stop, s - 0.03, 0.35 if opening else 0.9)))


def cabinet(opening, v):
    if opening:
        return trim(mix(0.5, (click(2600, 0.04, 0.005, 700, 0.4), 0, 0.6),
                        (k("rpg", "creak3", 1.35 + 0.1 * v, filt=lp(4500)), 0.03, 0.25)))
    return trim(mix(0.5, (k("impact", f"impactWood_medium_00{v + 2}", 1.2), 0, 1.0),
                    (click(3000, 0.03, 0.004), 0.02, 0.4)))


def switch(on):
    # a rocker: two quick transients (the rocker, then it seats)
    a = click(4200 if on else 3600, 0.03, 0.003, 1100, 0.35)
    b = click(2900 if on else 2500, 0.03, 0.004, 800, 0.5)
    return trim(mix(0.08, (a, 0, 1.0), (b, 0.007, 0.6)))


def breaker(on):
    parts = [(k("impact", "impactMetal_heavy_001", 0.72, filt=lp(4000)), 0, 0.9),
             (k("rpg", "metalLatch", 0.62), 0.012, 0.8),
             (sub_thump(0.25, 90, 50, 0.05), 0, 0.6)]
    if on:   # contacts closing under load: a short electric buzz
        z = ffilt(np.sign(np.sin(2 * np.pi * 120 * t_axis(N(0.12)))) + 0.3 * noise(0.12), chain(lp(3000), hp(100)))
        parts.append((z * env(N(0.12), 0.002, 0.03), 0.02, 0.25))
    return trim(mix(0.6, *parts))


def breaker_dead():
    return trim(mix(0.4, (k("rpg", "metalLatch", 0.7), 0, 0.8), (k("impact", "impactMetal_light_002", 0.8), 0.01, 0.4)))


def power_down():
    s = 2.2
    n = N(s)
    t = t_axis(n)
    f = 60 * (1 - 0.65 * (t / s) ** 0.8)
    ph = np.cumsum(f) / SR
    hum = sum(a * np.sin(2 * np.pi * h * ph) for h, a in ((1, 1), (2, 0.6), (3, 0.35), (5, 0.15)))
    whine = np.sin(2 * np.pi * np.cumsum(1250 * (1 - 0.85 * t / s)) / SR) * 0.12
    e = np.exp(-t / 0.75) * np.minimum(1, t / 0.01)
    return trim(mix(s, ((hum + whine) * e, 0, 1.0), (k("impact", "impactMetal_medium_001", 0.6), 0, 0.3)))


def power_up():
    s = 1.2
    n = N(s)
    t = t_axis(n)
    ph = np.cumsum(60 * (0.6 + 0.4 * np.minimum(1, t / 0.4))) / SR
    hum = sum(a * np.sin(2 * np.pi * h * ph) for h, a in ((1, 1), (2, 0.6), (3, 0.3)))
    e = np.minimum(1, t / 0.3) * np.exp(-np.maximum(0, t - 0.3) / 0.35)
    relays = [(click(2400 + 600 * i, 0.03, 0.004, 600, 0.5), 0.05 + 0.13 * i + 0.05 * rng.random(), 0.5) for i in range(3)]
    return trim(mix(s, (hum * e, 0, 0.8), *relays))


def shatter(v):
    heavy = ["impactGlass_heavy_001", "impactGlass_heavy_004", "impactGlass_heavy_000"][v]
    return trim(mix(1.4, (k("impact", heavy), 0, 1.0),
                    (k("impact", f"impactGlass_medium_00{v}", 1.05), 0.025, 0.55),
                    (tinkle(1.1, 45), 0.03, 0.5),
                    (sub_thump(0.3, 120, 60, 0.05), 0, 0.25)), tail_db=-55)


def grimble_step(v):
    return trim(mix(1.6, (k("impact", f"impactPunch_heavy_00{v}", 0.42, filt=lp(900)), 0, 1.0),
                    (sub_thump(0.8, 55, 28, 0.2), 0, 1.2),
                    (k("impact", f"footstep_grass_00{v}", 0.5, filt=lp(1500)), 0.01, 0.45)))


def grimble_knock(v):
    ring = sum(tone(1.0, f, decay=d, attack=0.001) * a for f, d, a in ((310, 0.35, 0.5), (845, 0.25, 0.3), (1630, 0.18, 0.2), (2950, 0.1, 0.1)))
    return trim(mix(1.2, (k("impact", f"impactWood_heavy_00{v}", 0.72, filt=lp(3000)), 0, 1.0),
                    (k("impact", f"impactGlass_heavy_00{[0, 2, 3][v]}", 0.68), 0.003, 0.6),
                    (sub_thump(0.6, 75, 38, 0.12), 0, 1.1),
                    (ring, 0.002, 0.35)))


def grimble_smash():
    s = 3.2
    debris = []
    for i in range(14):
        t0 = 0.25 + 2.3 * rng.random() ** 1.6
        name = f"impactGlass_{'light' if rng.random() < 0.6 else 'medium'}_00{rng.integers(5)}"
        debris.append((k("impact", name, 0.9 + 0.3 * rng.random()), t0, 0.5 * (1 - t0 / 3.0)))
    return trim(mix(s, (k("impact", "impactGlass_heavy_001", 0.8), 0, 1.0),
                    (k("impact", "impactGlass_heavy_004", 0.7), 0.02, 0.9),
                    (k("impact", "impactGlass_heavy_002", 0.6), 0.06, 0.7),
                    (k("scifi", "explosionCrunch_002", 0.85, filt=lp(3500)), 0, 0.7),
                    (sub_thump(1.2, 60, 25, 0.35), 0, 1.4),
                    (tinkle(2.6, 220, first=0.02, power=1.6), 0.02, 0.8),
                    *debris), tail_db=-55)


def crawl_hand(v):
    claws = k("impact", f"impactGeneric_light_00{v}", 0.85, filt=hp(1800)) * 0.18
    return trim(mix(0.9, (k("impact", f"impactPunch_medium_00{v}", 0.55, filt=lp(1300)), 0, 1.0),
                    (k("impact", f"impactSoft_heavy_00{v}", 0.6, filt=lp(900)), 0.005, 0.6),
                    (sub_thump(0.4, 70, 40, 0.07), 0, 0.5),
                    (claws, 0.012, 1.0)))


def crawl_foot(v):
    return trim(mix(0.8, (k("impact", f"impactSoft_heavy_00{v + 2}", 0.62, filt=lp(800)), 0, 1.0),
                    (k("rpg", f"cloth{v + 2}", 0.7, filt=lp(2500)), 0.0, 0.5)))


def growl(s, f0, seed):
    global rng
    old, rng = rng, np.random.default_rng(seed)
    n = N(s)
    t = t_axis(n)
    v = voiced(s, f0, jitter=0.09, sub=0.7, fry=19, fry_depth=0.6, breath=0.35, glide=(1.0, 0.82))
    e = np.minimum(1, t / 0.25) * np.minimum(1, (s - t) / 0.5) * (0.75 + 0.25 * np.sin(2 * np.pi * 1.3 * t))
    y = v * np.clip(e, 0, 1)
    rng = old
    return trim(y)


def snarl():
    s = 0.85
    t = t_axis(N(s))
    v = voiced(s, 72, jitter=0.15, sub=0.5, fry=28, fry_depth=0.7, breath=0.6,
               formants=((380, 3), (900, 4), (1900, 5), (3100, 6)), glide=(0.9, 1.25))
    e = np.minimum(1, t / 0.06) * np.exp(-np.maximum(0, t - 0.25) / 0.25)
    return trim(v * e)


def g_swipe():
    return trim(mix(0.8, (whoosh(0.55, 180, 1500, 1.0, 0.55), 0, 1.0),
                    (k("rpg", "cloth1", 0.62, filt=lp(3000)), 0.05, 0.6)))


def g_rear():
    return trim(mix(1.6, (k("rpg", "creak2", 0.5, filt=lp(2500)), 0, 0.8),
                    (whoosh(1.1, 120, 700, 0.8, 0.6), 0.1, 0.8),
                    (k("rpg", "cloth1", 0.5), 0.2, 0.5)))


def throw():
    return trim(mix(0.4, (whoosh(0.28, 400, 2600, 1.3, 0.4), 0, 1.0), (k("rpg", "cloth4", 1.2), 0, 0.6)))


def keycard(ok):
    seq = [(1760, 0.07, 0.04), (2349, 0.11, 0.0)] if ok else [(2349, 0.07, 0.04), (1568, 0.11, 0.0)]
    return trim(mix(0.5, (beep(seq), 0, 1.0), (k("rpg", "metalLatch", 1.45), 0.24, 0.35)))


def footstep(src, v, rate=1.0, filt=None, length=None, gain=1.0):
    x = k("impact", f"footstep_{src}_00{v}", rate, filt=filt) * gain
    return trim(cut(x, length) if length else x)


def tile_step(v):
    # a hard heel on tile / marble: the concrete step, brighter, plus the click of the heel
    return trim(mix(0.3, (footstep("concrete", v, 1.12, hp(250)), 0, 1.0), (click(5200, 0.02, 0.002, 1800, 0.2), 0.002, 0.25)))


SOUNDS = {
    # name: (recipe -> [variants], mix dB, ref distance m (None = non-spatial), category)
    "door_open":      (lambda: [trim(k("rpg", "doorOpen_1", filt=lp(7000))), trim(cut(k("rpg", "doorOpen_2", filt=lp(7000)), 1.0))], -12, 2.5, "world"),
    "door_close":     (lambda: [trim(k("rpg", f"doorClose_{i}")) for i in (1, 2, 3, 4)], -10, 2.5, "world"),
    "door_locked":    (lambda: [door_locked(0), door_locked(1)], -12, 2.0, "world"),
    "drawer_open":    (lambda: [drawer(True, 0), drawer(True, 1)], -14, 1.5, "world"),
    "drawer_close":   (lambda: [drawer(False, 0), drawer(False, 1)], -13, 1.5, "world"),
    "cabinet_open":   (lambda: [cabinet(True, 0), cabinet(True, 1)], -15, 1.5, "world"),
    "cabinet_close":  (lambda: [cabinet(False, 0), cabinet(False, 1)], -14, 1.5, "world"),
    "switch_on":      (lambda: [switch(True)], -15, 1.2, "world"),
    "switch_off":     (lambda: [switch(False)], -15, 1.2, "world"),
    "breaker_on":     (lambda: [breaker(True)], -7, 2.5, "world"),
    "breaker_off":    (lambda: [breaker(False)], -7, 2.5, "world"),
    "breaker_dead":   (lambda: [breaker_dead()], -10, 2.0, "world"),
    "power_down":     (lambda: [power_down()], -16, None, "ui"),
    "power_up":       (lambda: [power_up()], -18, None, "ui"),
    "fuse_insert":    (lambda: [trim(mix(0.6, (k("rpg", "metalClick"), 0, 1.0), (k("rpg", "metalLatch", 1.3), 0.14, 0.7)))], -12, 1.5, "world"),
    "use":            (lambda: [trim(k("rpg", "metalClick", 1.1))], -14, 1.5, "world"),
    "keycard_unlock": (lambda: [keycard(True)], -14, 1.5, "world"),
    "keycard_lock":   (lambda: [keycard(False)], -14, 1.5, "world"),
    "key_turn":       (lambda: [trim(mix(0.4, (k("rpg", "metalLatch", 1.1), 0, 1.0), (k("rpg", "metalClick", 1.3), 0.08, 0.6)))], -13, 1.5, "world"),
    "pickup":         (lambda: [trim(k("rpg", "handleSmallLeather")), trim(k("rpg", "handleSmallLeather2")), trim(cut(k("rpg", "cloth3"), 0.3))], -14, 1.5, "world"),
    "pickup_glass":   (lambda: [trim(mix(0.4, (k("impact", f"impactGlass_light_00{i}", 1.2), 0, 0.5), (k("rpg", "cloth4"), 0.02, 0.6))) for i in (0, 2)], -16, 1.5, "world"),
    "pickup_book":    (lambda: [trim(k("rpg", "bookFlip3")), trim(k("rpg", "bookClose"))], -15, 1.5, "world"),
    "pickup_metal":   (lambda: [trim(k("rpg", "handleCoins2")), trim(mix(0.4, (k("rpg", "metalClick", 1.2), 0, 0.6), (k("rpg", "handleSmallLeather"), 0, 0.8)))], -15, 1.5, "world"),
    "ui_open":        (lambda: [trim(mix(0.4, (k("ui", "open_001"), 0, 0.5), (k("rpg", "cloth2"), 0, 0.8)))], -22, None, "ui"),
    "ui_close":       (lambda: [trim(mix(0.4, (k("ui", "close_001"), 0, 0.5), (k("rpg", "cloth3"), 0, 0.6)))], -22, None, "ui"),
    "ui_move":        (lambda: [trim(k("ui", "tick_002"))], -26, None, "ui"),
    "ui_arm":         (lambda: [trim(mix(0.4, (k("ui", "select_001"), 0, 0.4), (k("rpg", "cloth4"), 0, 0.9)))], -20, None, "ui"),
    "ui_holster":     (lambda: [trim(cut(k("rpg", "cloth3"), 0.3))], -22, None, "ui"),
    "tablet_open":    (lambda: [trim(k("ui", "maximize_001"))], -22, None, "ui"),
    "tablet_close":   (lambda: [trim(k("ui", "minimize_001"))], -22, None, "ui"),
    "tablet_move":    (lambda: [trim(k("ui", "tick_001"))], -26, None, "ui"),
    "tablet_toggle":  (lambda: [trim(k("ui", "toggle_001"))], -22, None, "ui"),
    "tablet_offline": (lambda: [trim(k("ui", "error_004"))], -22, None, "ui"),
    "throw":          (lambda: [throw()], -16, None, "self"),
    "shatter":        (lambda: [shatter(0), shatter(1), shatter(2)], -3, 4.0, "world"),
    "thud":           (lambda: [trim(k("impact", f"impactSoft_heavy_00{i}")) for i in (0, 1)], -9, 3.0, "world"),
    "thud_book":      (lambda: [trim(mix(0.4, (k("rpg", f"bookPlace{i}"), 0, 1.0), (k("impact", f"impactSoft_medium_00{i}", 0.8), 0, 0.5))) for i in (1, 2, 3)], -9, 3.0, "world"),
    "flashlight":     (lambda: [trim(mix(0.08, (click(5200, 0.025, 0.002, 1500, 0.3), 0, 1.0), (click(3400, 0.025, 0.003, 900, 0.3), 0.012, 0.5))), trim(click(4600, 0.03, 0.003, 1200, 0.4))], -20, None, "self"),
    "battery":        (lambda: [trim(mix(0.5, (k("impact", "impactPlate_light_000", 1.6, filt=hp(500)), 0, 0.4), (k("rpg", "metalLatch", 1.5), 0.12, 0.8)))], -16, None, "self"),
    # the player
    "step_wood":      (lambda: [footstep("wood", i) for i in range(5)], -17, None, "self"),
    "step_stone":     (lambda: [footstep("concrete", i, 0.94) for i in range(5)], -17, None, "self"),
    "step_tile":      (lambda: [tile_step(i) for i in range(5)], -17, None, "self"),
    "step_concrete":  (lambda: [footstep("concrete", i, 0.88, lp(5000)) for i in range(5)], -17, None, "self"),
    "step_rug":       (lambda: [footstep("carpet", i) for i in range(5)], -20, None, "self"),
    "step_rubber":    (lambda: [footstep("carpet", i, 0.85, lp(2500)) for i in range(5)], -19, None, "self"),
    "step_grass":     (lambda: [footstep("grass", i, length=0.34) for i in range(5)], -18, None, "self"),
    "step_gravel":    (lambda: [footstep("snow", i) for i in range(5)], -17, None, "self"),
    "jump":           (lambda: [trim(mix(0.35, (cut(k("rpg", "cloth1"), 0.3), 0, 0.8), (k("rpg", "footstep05", 1.1), 0, 0.4))), trim(cut(k("rpg", "clothBelt2"), 0.3))], -20, None, "self"),
    "land":           (lambda: [trim(k("impact", f"impactSoft_heavy_00{i}", 0.8, filt=lp(2000))) for i in (2, 4)], -15, None, "self"),
    "hit":            (lambda: [trim(mix(0.7, (k("impact", "impactPunch_heavy_000", 0.9), 0, 1.0), (k("rpg", "cloth1"), 0, 0.5)))], -6, None, "self"),
    "fall":           (lambda: [trim(mix(0.8, (k("impact", "impactSoft_heavy_003", 0.75), 0, 1.0), (k("rpg", "dropLeather"), 0.03, 0.6)))], -9, None, "self"),
    # the Grimble
    "g_step":         (lambda: [grimble_step(i) for i in range(3)], -3, 12.0, "grimble"),
    "g_knock":        (lambda: [grimble_knock(i) for i in range(3)], -1, 10.0, "grimble"),
    "g_smash":        (lambda: [grimble_smash()], 0, 14.0, "grimble"),
    "g_hand":         (lambda: [crawl_hand(i) for i in range(4)], -7, 6.0, "grimble"),
    "g_foot":         (lambda: [crawl_foot(i) for i in range(3)], -11, 5.0, "grimble"),
    "g_growl":        (lambda: [growl(1.9, 50, 11), growl(2.5, 44, 12)], -4, 8.0, "grimble"),
    "g_snarl":        (lambda: [snarl()], -5, 6.0, "grimble"),
    "g_swipe":        (lambda: [g_swipe()], -5, 4.0, "grimble"),
    "g_rear":         (lambda: [g_rear()], -6, 6.0, "grimble"),
    "g_breath_in":    (lambda: [trim(breath(1.3, True, 1.2)), trim(breath(1.1, True, 1.35))], -16, 3.5, "grimble"),
    "g_breath_out":   (lambda: [trim(breath(1.7, False, 1.2)), trim(breath(1.5, False, 1.35))], -13, 3.5, "grimble"),
    "g_sniff":        (lambda: [trim(sniff(3, 1.3)), trim(sniff(4, 1.2))], -12, 4.0, "grimble"),
}


# ---------------------------------------------------------------- levels
def kweight(x):
    """Roughly K-weighted (the loudness standard's curve): less bass, a little more top."""
    return ffilt(x, lambda f: hp(60, 2)(f) * (1 + 0.58 * (1 - lp(1500, 2)(f))))


def loudness(x, win=0.05):
    """Max short-term RMS (dBFS) over `win` s windows of the K-weighted signal."""
    y = kweight(x) ** 2
    w = max(1, N(win))
    c = np.concatenate([[0], np.cumsum(y)])
    if len(y) <= w:
        return db(np.sqrt(c[-1] / max(1, len(y))))
    rms = np.sqrt((c[w:] - c[:-w]) / w)
    return db(rms.max())


def normalise(x):
    x = x * undb(TARGET - loudness(x))
    pk = np.abs(x).max()
    if pk > undb(CEIL):
        x = x * undb(CEIL) / pk
    return x


def write_wav(path, x):
    pcm = np.clip(np.round(x * 32767), -32768, 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def decode_mp3(path):
    raw = subprocess.run(["sox", str(path), "-t", "f32", "-r", str(SR), "-c", "1", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).astype(np.float64)


def build():
    fetch()
    OUT.mkdir(parents=True, exist_ok=True)
    parts = [np.zeros(N(MARK))]
    mark = np.zeros(N(0.05))
    mark[0], mark[1] = 0.9, -0.45            # the marker: one sharp click
    parts.append(mark)
    pos = sum(len(p) for p in parts)
    manifest = {"_": "built by tools/build_audio.py; times in s; gain in dB (applied by viewer/audio.js); "
                     "ref = distance (m) at which it plays at its gain (null = not positional); v = [start, duration, "
                     "make-up dB] per variant",
                "sampleRate": SR, "mark": MARK, "sounds": {}}
    for name, (recipe, gain, ref, cat) in SOUNDS.items():
        variants = []
        for x in recipe():
            x = normalise(x)
            parts.append(np.zeros(N(GAP)))
            pos += N(GAP)
            variants.append([round(pos / SR, 4), round(len(x) / SR, 4), 0.0])
            parts.append(x)
            pos += len(x)
        manifest["sounds"][name] = {"v": variants, "gain": gain, "ref": ref, "cat": cat}
    parts.append(np.zeros(N(0.3)))
    sprite = np.concatenate(parts)
    wav = ROOT / "build" / "sfx.wav"
    write_wav(wav, sprite)
    mp3 = OUT / "sfx.mp3"
    subprocess.run(["lame", "--silent", "-m", "m", "-b", str(BITRATE), "-q", "2", "--resample", "44.1", str(wav), str(mp3)], check=True)
    # A short click can't reach the target loudness under the peak ceiling, and the encoder
    # shaves a little off the rest: each variant's shortfall, measured on the decoded MP3, is
    # made up at playback (its third value, dB)
    x = decode_mp3(mp3)
    delay = np.nonzero(np.abs(x) > 0.3)[0][0] / SR - MARK
    for m in manifest["sounds"].values():
        for v in m["v"]:
            v[2] = round(TARGET - loudness(x[N(v[0] + delay):N(v[0] + delay + v[1])]), 1)
    (OUT / "sfx.json").write_text(json.dumps(manifest, indent=1) + "\n")
    print(f"sfx.mp3: {sum(len(m['v']) for m in manifest['sounds'].values())} clips in {len(manifest['sounds'])} sounds, "
          f"{len(sprite) / SR:.1f} s, {mp3.stat().st_size / 1024:.0f} KB")
    return manifest


def report():
    """Decode the MP3 as a browser would and measure every clip: length, peak, loudness, and the
    level it plays at (loudness + mix gain, at its ref distance)."""
    man = json.loads((OUT / "sfx.json").read_text())
    x = decode_mp3(OUT / "sfx.mp3")
    on = np.nonzero(np.abs(x) > 0.3)[0][0]
    delay = on / SR - man["mark"]
    print(f"decoder delay {delay * 1000:.1f} ms (audio.js measures it from the marker)")
    rows = []
    for name, m in man["sounds"].items():
        for i, (s, d, adj) in enumerate(m["v"]):
            seg = x[N(s + delay):N(s + delay + d)]
            pk = db(np.abs(seg).max())
            ld = loudness(seg)
            rows.append((name, i, d, pk, ld, ld + adj + m["gain"], m["cat"], m["ref"]))
    print(f"{'sound':16s} {'#':>2s} {'len s':>6s} {'peak':>6s} {'loud':>6s} {'plays':>6s}  cat      ref")
    for r in rows:
        print(f"{r[0]:16s} {r[1]:2d} {r[2]:6.2f} {r[3]:6.1f} {r[4]:6.1f} {r[5]:6.1f}  {r[6]:8s} {r[7]}")
    # clipped, too long, or (after make-up) more than 0.5 dB off its intended level
    bad = [r for r in rows if r[3] > -0.3 or r[2] > 3.5 or abs(r[5] - TARGET - man["sounds"][r[0]]["gain"]) > 0.5]
    print("all clips within limits" if not bad else f"OUT OF LIMITS: {[(r[0], r[1]) for r in bad]}")
    return not bad


if __name__ == "__main__":
    if "--report-only" not in sys.argv:
        build()
    if "--report" in sys.argv or "--report-only" in sys.argv:
        sys.exit(0 if report() else 1)
