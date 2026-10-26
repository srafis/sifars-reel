"""No-voice reels: builds vo/timeline.json from the script alone, paced for reading, so captions, scenes, cues and
the music bed work exactly as in a voiced reel (the captions become the narration).
Pace: each word ~0.24 s + 0.035 s a letter, +0.25 s after a comma, +0.5 s after a sentence; gaps between lines
come from vo/gaps.json (default 0.6 s). Usage: python -I tools/silent-timeline.py <reel>"""
import json
import sys
from pathlib import Path

reel = Path(sys.argv[1])
script = json.loads((reel / "vo/script.json").read_text())
gaps = json.loads((reel / "vo/gaps.json").read_text()) if (reel / "vo/gaps.json").exists() else {}
t = gaps.get("lead", 0.4)
lines = []
for i, line in enumerate(script["lines"]):
    if i:
        t += gaps.get("gaps", {}).get(line["id"], 0.6)
    words, start = [], t
    for w in line["caption"].split():
        d = 0.24 + 0.035 * len(w.strip(".,?!…"))
        words.append({"w": w, "start": round(t, 3), "end": round(t + d, 3)})
        t += d + (0.5 if w[-1] in ".?!…" else 0.25 if w[-1] in ",;:" else 0.04)
    lines.append({"id": line["id"], "start": round(start, 3), "end": words[-1]["end"], "words": words})
total = round(t + gaps.get("tail", 2.6), 2)
(reel / "vo/timeline.json").write_text(json.dumps({"duration": total, "silent": True, "lines": lines}, indent=1, ensure_ascii=False))
for l in lines:
    print(f"{l['id']:10} {l['start']:6.2f} → {l['end']:6.2f}")
print("total", total, "(no voice: read-paced)")
