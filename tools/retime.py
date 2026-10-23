"""Moves every film time in a reel from one voice take to another. The script's words are the anchors:
a time between two words in the old take lands at the same proportion between them in the new one.
Rewrites `const S = x`, `at(x...)`, the time arguments of `counter(...)` in compositions/*.html, and
`t` in cues.json. Usage: python -I tools/retime.py <reel> <old timeline.json> <new timeline.json>"""
import bisect
import json
import re
import sys
from pathlib import Path

reel, old_p, new_p = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
old, new = json.loads(old_p.read_text()), json.loads(new_p.read_text())
xs, ys = [0.0], [0.0]
for lo, ln in zip(old["lines"], new["lines"]):
    for wo, wn in zip(lo["words"], ln["words"]):
        if wo["start"] > xs[-1] and wn["start"] > ys[-1]:
            xs.append(wo["start"]); ys.append(wn["start"])
    xs.append(lo["end"]); ys.append(ln["end"])
xs.append(old["duration"]); ys.append(new["duration"])


def remap(t):
    if t >= xs[-1]:
        return ys[-1] + (t - xs[-1])
    i = max(1, bisect.bisect_right(xs, t))
    x0, x1, y0, y1 = xs[i - 1], xs[i], ys[i - 1], ys[i]
    return y0 + (t - x0) * (y1 - y0) / (x1 - x0) if x1 > x0 else y0


fmt = lambda t: f"{remap(t):.2f}".rstrip("0").rstrip(".")
for page in sorted((reel / "compositions").glob("*.html")):
    if page.name == "captions.html":
        continue
    s = page.read_text()
    s = re.sub(r"const S = ([0-9.]+)", lambda m: f"const S = {fmt(float(m.group(1)))}", s)
    s = re.sub(r"\bat\(([0-9.]+)", lambda m: f"at({fmt(float(m.group(1)))}", s)
    s = re.sub(r'(counter\("[^"]+", [0-9.]+, [0-9.]+, )([0-9.]+), ([0-9.]+)',
               lambda m: f"{m.group(1)}{fmt(float(m.group(2)))}, {fmt(float(m.group(3)))}", s)
    # helpers that take a film time: arrive("#id", t), done(n, t), words("#sel", t, gap)
    s = re.sub(r'(\b(?:arrive|words|one)\("[^"]+", )([0-9.]+)', lambda m: f"{m.group(1)}{fmt(float(m.group(2)))}", s)
    s = re.sub(r'(\bdone\([0-9]+, )([0-9.]+)', lambda m: f"{m.group(1)}{fmt(float(m.group(2)))}", s)
    page.write_text(s)
    print("retimed", page.name)
cues_p = reel / "cues.json"
if cues_p.exists():
    cues = json.loads(cues_p.read_text())
    for c in cues:
        c["t"] = round(remap(c["t"]), 3)
    cues_p.write_text(json.dumps(cues, indent=1))
    print("retimed cues.json")
index = reel / "index.html"
if index.exists():  # scene hosts: move each start, then make each one run until the next begins
    h = index.read_text()
    hosts = re.findall(r'<div id="(\w+)" data-composition-id="\w+" data-composition-src="compositions/\w+\.html" data-start="([0-9.]+)"', h)
    hosts = [(k, v) for k, v in hosts if k != "captions"]
    starts = [(k, round(remap(float(v)), 2) if float(v) > 0 else 0) for k, v in hosts]
    for n, (k, st) in enumerate(starts):
        end = starts[n + 1][1] if n + 1 < len(starts) else new["duration"]
        h = re.sub(rf'(<div id="{k}" [^>]*?)data-start="[0-9.]+" data-duration="[0-9.]+"', lambda m: f'{m.group(1)}data-start="{st}" data-duration="{round(end - st, 3)}"', h)
    index.write_text(h)
    print("scene starts", starts)
print(json.dumps({"scene_bounds_example": [round(remap(t), 2) for t in (7.95, 17.75, 30.45, 36.1, 45.8, 51.9, 67.7, 73.65)]}))
