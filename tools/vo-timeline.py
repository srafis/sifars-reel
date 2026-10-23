"""Builds vo/timeline.json from the single voice take (assets/vo/take.json): film-time start/end per
line and every caption word with its film time. Usage: python -I tools/vo-timeline.py <reel>"""
import json
import subprocess
import sys
from pathlib import Path

reel = Path(sys.argv[1])
script = json.loads((reel / "vo/script.json").read_text())
gaps = json.loads((reel / "vo/gaps.json").read_text())
lead = gaps["lead"]
take = json.loads((reel / "assets/vo/take.json").read_text())
spoken = take["words"]
dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(reel / "assets/vo/take.mp3")]))

lines, i = [], 0
for line in script["lines"]:
    shown = line["caption"].split()
    mine = spoken[i:i + len(shown)]
    i += len(shown)
    assert [w["w"] for w in mine] == line["text"].split(), line["id"]
    words = [{"w": c, "start": round(lead + s["start"], 3), "end": round(lead + s["end"], 3)} for c, s in zip(shown, mine)]
    lines.append({"id": line["id"], "start": words[0]["start"], "end": words[-1]["end"], "words": words})
assert i == len(spoken)
total = round(lead + dur + gaps["tail"], 2)
(reel / "vo/timeline.json").write_text(json.dumps({"duration": total, "take_start": lead, "take_duration": dur, "lines": lines}, indent=1))
prev = None
for l in lines:
    pause = f"  (pause {l['start'] - prev:.2f})" if prev is not None else ""
    print(f"{l['id']:10} {l['start']:6.2f} → {l['end']:6.2f}{pause}")
    prev = l["end"]
print("total", total)
