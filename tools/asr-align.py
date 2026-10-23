"""Replaces the ElevenLabs word timings in assets/vo/take.json with ones measured from the audio
(ElevenLabs' alignment runs 0.25-0.5 s late). Needs assets/vo/transcript.json from:
  bin/hf transcribe assets/vo/take.mp3 --engine parakeet --json      (run inside the reel)
Usage: python -I tools/asr-align.py <reel>"""
import difflib
import json
import re
import sys
from pathlib import Path

reel = Path(sys.argv[1])
aw = json.loads((reel / "assets/vo/transcript.json").read_text())
tk = json.loads((reel / "assets/vo/take.json").read_text())
take = tk.get("words_el") or tk["words"]
norm = lambda w: re.sub(r"[^a-z0-9]", "", w.lower())
A, B = [norm(w["text"]) for w in aw], [norm(w["w"]) for w in take]
sm = difflib.SequenceMatcher(a=B, b=A, autojunk=False)
match = {blk.a + k: blk.b + k for blk in sm.get_matching_blocks() for k in range(blk.size)}
for tag, i1, i2, j1, j2 in sm.get_opcodes():  # "ten" vs "10", a native-script name vs its romanisation: same-length gaps pair up
    if tag == "replace" and i2 - i1 == j2 - j1:
        for k in range(i2 - i1):
            match[i1 + k] = j1 + k
out = [{"w": w["w"], "start": aw[match[i]]["start"], "end": aw[match[i]]["end"]} if i in match else None for i, w in enumerate(take)]
for i, w in enumerate(out):  # leftovers keep the voice's own spacing, shifted to their measured neighbour
    if w is None:
        prev = next((k for k in range(i - 1, -1, -1) if out[k]), None)
        shift = (out[prev]["start"] - take[prev]["start"]) if prev is not None else 0
        out[i] = {"w": take[i]["w"], "start": round(take[i]["start"] + shift, 3), "end": round(take[i]["end"] + shift, 3)}
tk["words_el"], tk["words"] = take, out
tk["timing_source"] = "parakeet ASR on take.mp3"
(reel / "assets/vo/take.json").write_text(json.dumps(tk, indent=1, ensure_ascii=False))
print(f"measured {len(match)} of {len(take)} words; the rest interpolated")
