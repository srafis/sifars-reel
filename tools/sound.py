"""Soft, synthesised sound for a reel: a UI sound-effect set and a quiet music bed, both levelled
against the voice take so nothing shouts over the narration.

  python -I tools/sound.py sfx <reel>     -> assets/sfx/soft-*.mp3
  python -I tools/sound.py bed <reel>     -> assets/music/bed.mp3 (follows vo/timeline.json, ducks under the voice)
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt

SR = 48000
rng = np.random.default_rng(7)  # seeded: every render sounds the same


def t_(dur):
    return np.arange(int(dur * SR)) / SR


def env(dur, attack, decay):
    t = t_(dur)
    a = np.clip(t / max(attack, 1e-4), 0, 1)
    return a * np.exp(-np.maximum(t - attack, 0) / decay)


def lp(x, hz, order=2):
    return sosfilt(butter(order, hz, "low", fs=SR, output="sos"), x)


def hp(x, hz, order=2):
    return sosfilt(butter(order, hz, "high", fs=SR, output="sos"), x)


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], "band", fs=SR, output="sos"), x)


def sine(freq, dur, phase=0.0):
    f = np.broadcast_to(np.asarray(freq, dtype=float), (int(dur * SR),))
    return np.sin(2 * np.pi * np.cumsum(f) / SR + phase)


def glide(f0, f1, dur, curve=3.0):
    t = t_(dur) / dur
    return f1 + (f0 - f1) * np.exp(-curve * t)


def noise(dur):
    return rng.standard_normal(int(dur * SR))


def room(x, size=0.6, wet=0.18):
    ir_t = t_(size * 3)
    ir = rng.standard_normal(len(ir_t)) * np.exp(-ir_t / size)
    ir = lp(ir, 5000) / np.sqrt(np.sum(ir ** 2))
    tail = np.convolve(x, ir)[: len(x) + len(ir_t)]
    dry = np.pad(x, (0, len(tail) - len(x)))
    return dry * (1 - wet) + tail * wet


def voice_level(reel):
    """Peak and active RMS of the voice take, so everything else is set relative to it."""
    wav = reel / "assets" / "vo" / "take.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(reel / "assets/vo/take.mp3"), "-ac", "1", "-ar", str(SR), str(wav)], check=True)
    v, _ = sf.read(wav)
    win = int(0.05 * SR)
    rms = np.sqrt(np.convolve(v ** 2, np.ones(win) / win, "same"))
    active = rms[rms > rms.max() * 0.1]
    return float(np.abs(v).max()), float(np.sqrt(np.mean(active ** 2))), v


# ---------- sound effects ----------
def sfx_set():
    s = {}
    def tick(f):  # soft wooden tick
        d = 0.12
        x = sine(f, d) * env(d, 0.002, 0.022) + 0.25 * sine(f * 2.76, d) * env(d, 0.001, 0.01)
        return lp(x, 4000)
    s["tick-a"], s["tick-b"] = tick(1050), tick(880)
    d = 0.16  # tap: a card landing on a table
    s["tap"] = lp(sine(glide(240, 120, d, 6), d) * env(d, 0.002, 0.045) + 0.35 * lp(noise(d), 1800) * env(d, 0.001, 0.012), 3000)
    d = 0.35  # thump: something heavier landing (the mascot, a new message)
    s["thump"] = lp(sine(glide(170, 72, d, 5), d) * env(d, 0.003, 0.11) + 0.3 * lp(noise(d), 900) * env(d, 0.001, 0.03), 2500)
    d = 0.2  # pop: a chip or badge appearing
    s["pop"] = lp(sine(glide(480, 820, d, 9), d) * env(d, 0.002, 0.05), 3500)
    for name, (f0, f1, dur) in {"whoosh-1": (350, 1900, 0.5), "whoosh-2": (1600, 380, 0.42), "whoosh-3": (250, 1300, 0.9)}.items():
        n, t = noise(dur), t_(dur) / dur
        centre = f0 * (f1 / f0) ** t
        out = np.zeros_like(n)
        for i in range(0, len(n), 960):  # swept band, block by block
            c = centre[i]
            seg = bp(n[max(0, i - 2048): i + 960], c * 0.6, min(c * 1.6, SR / 2 - 100))
            out[i: i + 960] = seg[-len(out[i: i + 960]):]
        shape = np.sin(np.pi * np.clip(t, 0, 1)) ** 1.6
        s[name] = lp(out * shape, 3200)
    d = 0.45  # bonk: something went wrong, without a harsh beep
    s["bonk"] = lp((sine(196, d) + 0.8 * sine(233, d)) * env(d, 0.004, 0.11), 1400)
    s["bonk-low"] = lp((sine(147, d) + 0.8 * sine(175, d)) * env(d, 0.004, 0.14), 1200)
    def note(f, d=0.6, dec=0.18):  # soft mallet
        return lp(sine(f, d) * env(d, 0.003, dec) + 0.12 * sine(f * 4, d) * env(d, 0.001, 0.03), 3500)
    s["mallet"] = note(523.25)
    s["mallet-low"] = note(392.0)
    up = np.zeros(int(0.8 * SR)); a, b = note(659.25, 0.7, 0.2), note(987.77, 0.7, 0.24)
    up[: len(a)] += a; up[int(0.09 * SR): int(0.09 * SR) + len(b)] += b
    s["chime-up"] = up
    d = 0.18  # strike: a pen line through a word
    s["strike"] = bp(noise(d), 900, 4200) * np.sin(np.pi * t_(d) / d) ** 2 * 0.6
    sc = np.zeros(int(0.7 * SR))
    for k in range(8):  # scroll: tiny ticks, slowing down
        o = int((0.06 * k + 0.004 * k * k) * SR)
        tk = tick(1300) * 0.5
        sc[o: o + len(tk)] += tk[: len(sc) - o]
    s["scroll"] = sc
    d = 1.6  # boom: the logo landing (body at 110-220 Hz so phones still hear it)
    s["boom"] = lp(sine(glide(110, 52, d, 4), d) * env(d, 0.004, 0.45) + 0.5 * sine(glide(220, 110, d, 4), d) * env(d, 0.003, 0.25)
                   + 0.2 * lp(noise(d), 700) * env(d, 0.002, 0.08), 2000)
    return s


def write_sfx(reel):
    peak, _, _ = voice_level(reel)
    target = peak * 10 ** (-12 / 20)  # every effect peaks 12 dB under the loudest syllable
    out = reel / "assets" / "sfx"
    for name, x in sfx_set().items():
        x = room(x, 0.35, 0.12)
        x = x / np.abs(x).max() * target
        st = np.stack([x, x], 1)
        wav = out / f"soft-{name}.wav"
        sf.write(wav, st, SR)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-b:a", "192k", str(wav.with_suffix(".mp3"))], check=True)
        wav.unlink()
        print("sfx", f"soft-{name}")
    peaks = out / "peaks.json"
    if peaks.exists():  # the cue tool re-measures anything new
        p = json.loads(peaks.read_text()); p = {k: v for k, v in p.items() if not k.startswith("soft-")}; peaks.write_text(json.dumps(p, indent=2))


# ---------- music bed ----------
NOTE = {n: i for i, n in enumerate(["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"])}


def hz(name):
    n, o = name[:-1], int(name[-1])
    return 440.0 * 2 ** ((NOTE[n] + 12 * (o + 1) - 69) / 12)


CHORDS = {
    "Am": ["A2", "E3", "A3", "C4", "E4"], "F": ["F2", "C3", "F3", "A3", "C4"], "C": ["C3", "G3", "C4", "E4", "G4"],
    "G": ["G2", "D3", "G3", "B3", "D4"], "Em": ["E2", "B2", "E3", "G3", "B3"], "Dm": ["D3", "A3", "D4", "F4", "A4"],
    "Fmaj7": ["F2", "C3", "E3", "A3", "C4"],
}


def pad(chord, dur, cutoff):
    x = np.zeros(int(dur * SR))
    for n in CHORDS[chord]:
        for cents in (-7, 0, 6):  # three detuned saws per note
            f = hz(n) * 2 ** (cents / 1200)
            ph = (np.arange(len(x)) * f / SR + rng.random()) % 1.0
            x += (2 * ph - 1) * (0.8 if cents else 1.0)
    x = lp(x, cutoff, 2)
    fade = min(0.9, dur / 3)
    e = np.ones(len(x)); k = int(fade * SR)
    e[:k] = np.linspace(0, 1, k) ** 1.5; e[-k:] = np.linspace(1, 0, k) ** 1.5
    return x * e / len(CHORDS[chord])


def pluck(f, d=0.5):
    return lp(sine(f, d) * env(d, 0.004, 0.16) + 0.3 * sine(2 * f, d) * env(d, 0.002, 0.06), 2600)


def write_bed(reel):
    """Sections come from <reel>/vo/music.json (see templates/reel/vo/music.json); without it, one calm loop.
    Each section: {"from": anchor, "chords": [...], "cutoff": Hz, "density": 0-1}; a section runs until the next
    one's anchor. An anchor is seconds, "start", or {"line": id, "word": text?, "offset": s?} (word start, else
    line start). Density 0 = pad only (e.g. silence-ish while something on screen freezes)."""
    tl = json.loads((reel / "vo/timeline.json").read_text())
    L = {l["id"]: l for l in tl["lines"]}
    T = tl["duration"]

    def anchor(a):
        if a == "start":
            return 0.0
        if isinstance(a, (int, float)):
            return float(a)
        line = L[a["line"]]
        t = line["start"]
        if a.get("word"):
            t = next(x["start"] for x in line["words"] if x["w"].strip(".,?!…").lower() == a["word"].lower())
        return t + a.get("offset", 0.0)

    plan_p = reel / "vo/music.json"
    plan = json.loads(plan_p.read_text()) if plan_p.exists() else {"sections": [
        {"from": "start", "chords": ["Am", "F", "C", "G"] * max(1, round(T / 23)), "cutoff": 1200, "density": 0.55}]}
    starts = [anchor(sec["from"]) for sec in plan["sections"]]
    sections = [(s0, starts[i + 1] if i + 1 < len(starts) else T, sec["chords"], sec["cutoff"], sec["density"])
                for i, (s0, sec) in enumerate(zip(starts, plan["sections"]))]
    spb = 60 / plan.get("bpm", 84)
    out = np.zeros(int((T + 3) * SR))
    for s0, s1, chords, cutoff, density in sections:
        seg = (s1 - s0) / len(chords)
        for i, ch in enumerate(chords):
            a = s0 + i * seg
            p = pad(ch, seg + 1.2, cutoff)  # overlap 1.2 s into the next chord
            o = int(a * SR); out[o: o + len(p)] += p[: len(out) - o] * 0.5
            if density:
                notes = CHORDS[ch][2:] + [CHORDS[ch][3]]
                beat = 0.5 * spb  # eighth notes
                k = 0
                while a + k * beat < a + seg:
                    if (k % 2 == 0) or rng.random() < density * 0.6:
                        f = hz(notes[k % len(notes)]) * 2
                        pl = pluck(f) * (0.55 if k % 4 == 0 else 0.35) * density
                        o = int((a + k * beat) * SR); out[o: o + len(pl)] += pl[: len(out) - o]
                    k += 1
    out = out[: int(T * SR)]
    out = room(out, 0.9, 0.3)[: int(T * SR)]
    out = hp(out, 110)  # nothing a phone speaker cannot play
    # fade in, and out under the logo's last second
    t = np.arange(len(out)) / SR
    out *= np.clip(t / 1.2, 0, 1) * np.clip((T - t) / 1.5, 0, 1)

    # duck under the voice: -7 dB while Henry speaks, back up in the gaps
    _, vrms, v = voice_level(reel)
    lead = tl["take_start"]
    vv = np.zeros(len(out)); o = int(lead * SR); vv[o: o + len(v)] = np.abs(v[: len(out) - o])
    win = int(0.08 * SR)
    venv = np.sqrt(np.convolve(vv ** 2, np.ones(win) / win, "same"))
    speaking = (venv > vrms * 0.25).astype(float)
    att, rel = np.exp(-1 / (0.04 * SR)), np.exp(-1 / (0.45 * SR))
    g = np.zeros_like(speaking); cur = 0.0
    for i, x in enumerate(speaking):
        cur = att * cur + (1 - att) * x if x > cur else rel * cur + (1 - rel) * x
        g[i] = cur
    out *= 1 - g * (1 - 10 ** (-7 / 20))

    # bed sits 20 dB under the voice's active level (before ducking)
    w = int(0.4 * SR)
    brms = np.sqrt(np.convolve(out ** 2, np.ones(w) / w, "same"))
    loud = np.percentile(brms[brms > 0], 90)
    out *= (vrms * 10 ** (-20 / 20)) / loud
    (reel / "assets" / "music").mkdir(exist_ok=True)
    wav = reel / "assets/music/bed.wav"
    sf.write(wav, np.stack([out, out], 1), SR)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-b:a", "192k", str(wav.with_suffix(".mp3"))], check=True)
    wav.unlink()
    print("bed", round(T, 2), "s;", len(sections), "sections at", [round(x[0], 2) for x in sections])


if __name__ == "__main__":
    reel = Path(sys.argv[2])
    {"sfx": write_sfx, "bed": write_bed}[sys.argv[1]](reel)
