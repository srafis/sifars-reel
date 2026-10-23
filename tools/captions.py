"""Writes compositions/captions.html from vo/timeline.json: phrase groups that pop in, words that
light up as they are spoken. Usage: python -I tools/captions.py <reel>"""
import html
import json
import sys
from pathlib import Path

reel = Path(sys.argv[1])
timeline = json.loads((reel / "vo/timeline.json").read_text())
MAX_CHARS = 28  # one pill, at most two lines at 58 px


def chars(ws):
    return len(" ".join(w["w"] for w in ws))


def split_even(ws):
    """Split a phrase that is too long into the fewest pieces of balanced length."""
    if chars(ws) <= MAX_CHARS:
        return [ws]
    best = min(range(1, len(ws)), key=lambda i: max(chars(ws[:i]), chars(ws[i:])))
    return split_even(ws[:best]) + split_even(ws[best:])


script = json.loads((reel / "vo/script.json").read_text())
skip = {l["id"] for l in script["lines"] if l.get("captions") is False}  # lines the picture already says in big type
groups = []
for line in timeline["lines"]:
    if line["id"] in skip:
        continue
    phrases, cur = [], []
    for word in line["words"]:  # break at punctuation first
        cur.append(word)
        if word["w"][-1] in ".,?…!":
            phrases.append(cur)
            cur = []
    if cur:
        phrases.append(cur)
    pieces = [p for ph in phrases for p in split_even(ph)]
    # A lone short word joins a neighbour in the same sentence when they fit together:
    # the next phrase if the previous one ended a sentence, else the previous one.
    ends_sentence = lambda ws: ws[-1]["w"][-1] in ".?…!"
    fits = lambda a, b: chars(a + b) <= MAX_CHARS + 4
    merged, i = [], 0
    while i < len(pieces):
        p = pieces[i]
        short = chars(p) <= 9
        if merged and (short or chars(merged[-1]) <= 9) and not ends_sentence(merged[-1]) and fits(merged[-1], p):
            merged[-1] = merged[-1] + p
        elif short and not ends_sentence(p) and i + 1 < len(pieces) and fits(p, pieces[i + 1]):
            merged.append(p + pieces[i + 1])
            i += 1
        else:
            merged.append(p)
        i += 1
    groups.extend(merged)

markup, tweens = [], []
for gi, g in enumerate(groups):
    start = max(0, g[0]["start"] - 0.06)
    nxt = groups[gi + 1][0]["start"] - 0.06 if gi + 1 < len(groups) else timeline["duration"]
    end = min(nxt, g[-1]["end"] + 0.6)
    gid = f"cap-g{gi + 1:03d}"
    words = " ".join(
        f'<span class="cap-w" id="{gid}-w{wi + 1:02d}">{html.escape(w["w"])}</span>' for wi, w in enumerate(g)
    )
    markup.append(
        f'    <div id="{gid}" class="clip cap-group" data-start="{start:.3f}" data-duration="{end - start:.3f}">'
        f'<div class="cap-pill" id="{gid}-pill">{words}</div></div>'
    )
    tweens.append(
        f'    tl.fromTo("#{gid}-pill", {{ opacity: 0, y: 14, filter: "blur(6px)" }}, '
        f'{{ opacity: 1, y: 0, filter: "blur(0px)", duration: 0.14, ease: "power3.out" }}, {start:.3f});'
    )
    for wi, w in enumerate(g):
        tweens.append(f'    tl.set("#{gid}-w{wi + 1:02d}", {{ color: "#ffffff" }}, {w["start"]:.3f});')

page = f"""<template>
  <style>
    #root {{ position: absolute; inset: 0; pointer-events: none; }}
    .cap-group {{ position: absolute; left: 60px; right: 60px; top: 1172px; height: 158px; display: flex; align-items: center; justify-content: center; }}
    .cap-pill {{ background: rgba(8, 12, 22, 0.88); border-radius: 26px; padding: 16px 32px 20px; text-align: center; max-width: 960px;
      font: 700 58px/1.22 "Poppins", sans-serif; letter-spacing: -0.02em; color: rgba(255, 255, 255, 0.42); }}
  </style>
  <div id="root" data-composition-id="captions" data-width="1080" data-height="1920">
{chr(10).join(markup)}
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
{chr(10).join(tweens)}
    window.__timelines["captions"] = tl;
  </script>
</template>
"""
(reel / "compositions/captions.html").write_text(page)
print(len(groups), "caption groups")
for g in groups:
    print(f'{g[0]["start"]:6.2f}  {" ".join(w["w"] for w in g)}')
