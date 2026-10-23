---
name: sifars-reel
description: Make a Sifars Instagram reel end to end — a faceless 9:16 story video (motion graphics in HyperFrames, ElevenLabs Henry voice, burned captions, soft synthesised SFX, quiet music bed, fixed Sifars outro). Use when pointed at a project folder or given a problem/fix/result to turn into a "stuck → unstuck", "what we cooked" or client-win reel for @sifars.us.
---

# Sifars reel

Input: a folder (repo, notes, logs) or a description of a problem we solved. Output: a postable reel in
`projects/<name>/output/`. A reel tells ONE story end to end so a stranger on a muted phone understands it.
Before starting, read `AGENTS.local.md` if it exists: it holds project notes, names and pronunciations that must
not be committed.

## Non-negotiables

- **One problem per reel.** Hook → setup → symptom → wrong guess → clue → cause → fix → result → payoff line → outro.
  A reel listing several bugs with stats was rejected: "no one would understand what was even the issue".
- **Facts only from sources:** the folder's git log and code, its docs, and agent session logs
  (`~/.claude/projects/<path with / as ->/*.jsonl`, `~/.codex/sessions/**` filtered by cwd). Every number on screen
  must be traceable. If a fix wasn't confirmed live, say what the code does, not a measured result. Ask only for what
  the sources can't answer.
- **Keep private things off screen:** real names/faces (ask first), private channels, hostnames, IPs, tokens, client
  names (written permission only), workspace names. Rebuild UI with neutral data instead of raw screenshots.
- **Voice is Henry:** ElevenLabs `eleven_v4`, voice_id `991lF4hc0xxfec4Y6B0i` ("Henry – Confident and Clear").
  Library voices work by ID; nothing needs adding to the account. Key: `ELEVEN_LABS_API_KEY` in `.env`.
- **Pronunciation:** the spoken spelling goes in the script's `text`, the real one in `caption`.
  - Sifars → `Siffars` (rhymes with "differs"; ਸਿਫ਼ਰ). Rejected: Sephers, Seffers, Seefers, Sifars as written.
  - Numbers and symbols as words ("ten sixteen", "three-D", "two-hour"); caption word count must stay IDENTICAL.
  - Names from Indian languages: try the native script (Gurmukhi/Devanagari) — it beat every romanisation so far.
  - Any new name: record 8–12 numbered samples in Henry (`Number N. This is X, …`), let the user pick, then save the
    winner in `AGENTS.local.md` under the project.
- **Record the whole script as ONE take** (`tools/elevenlabs.py take`). Lines recorded separately and joined sounded cut.
- **Never trust ElevenLabs' word timestamps** — they run 0.25–0.5 s late. Measure with Parakeet (`asr-align.py`) and
  time every visual, caption and cue from the measured words. Big type that mirrors the voice is pinned per word.
- **Sound must never hurt:** effects are synthesised soft sounds peaking 12 dB under the loudest syllable; the music
  bed sits ~19–20 dB under the voice and ducks while it speaks. Sample-pack SFX were "overpowering… hurting the ears".
- **Logo:** use `brand/logo/` (single-colour, from the Illustrator source in `brand/logo/v2/`). sifars.com still shows
  the OLD dual-tone logo — never take the logo from the website.
- **Nothing installed globally.** Project-local `node_modules`, `.venv` (uv), caches in `.cache/`, HyperFrames via
  `bin/hf` (forces HOME/XDG into `.local-home`), Chrome = system Chrome.
- **Projects never enter git.** Everything for a project lives in `projects/<name>/` (git-ignored).

## Pipeline

```bash
cd ~/code/sifars-insta
tools/new-reel.sh <name>; R=projects/<name>/reel; HF=$PWD/bin/hf
# 1. story: mine sources, write 3 one-line storylines, pick one, write $R/vo/script.json (text = spoken, caption = shown)
.venv/bin/python -I tools/elevenlabs.py take $R            # one take, Henry
(cd $R && $HF transcribe assets/vo/take.mp3 --engine parakeet --json >/dev/null)
.venv/bin/python -I tools/asr-align.py $R                  # measured word times
.venv/bin/python -I tools/vo-timeline.py $R                # vo/timeline.json: line + word film times
# 2. print word times (jq '.lines[] | …' $R/vo/timeline.json), plan scene bounds + the word each visual lands on
# 3. write $R/index.html (scene hosts, captions host, vo-take <audio>, music-bed <audio>, SFX markers) + compositions/*.html
.venv/bin/python -I tools/captions.py $R                   # captions.html (skips lines with "captions": false)
.venv/bin/python -I tools/sound.py sfx $R                  # soft-*.mp3, levelled to this voice
.venv/bin/python -I tools/sound.py bed $R                  # music bed from $R/vo/music.json (sections anchored to words)
node tools/sfx.mjs $R                                      # cues.json -> <audio> tags, peak-aligned, own lanes
(cd $R && $HF check --json)                                # must be ok; read every warning
(cd $R && $HF render -q delivery -o renders/<name>.mp4)
ffmpeg -i $R/renders/<name>.mp4 -c:v copy -af "loudnorm=I=-14:TP=-1.2:LRA=11,aresample=48000" -c:a aac -b:a 256k \
  -movflags +faststart projects/<name>/output/<name>.mp4
```

Re-recorded the voice? Don't retime by hand: keep the old `vo/timeline.json`, rebuild the new one, then
`tools/retime.py $R <old timeline> <new timeline>` moves every `const S`, `at(t)`, helper time (`arrive`, `words`,
`done`, `one`, `counter`), cue and scene host word by word. Re-derive fixed-interval cues afterwards.

Music plan (`vo/music.json`): sections anchored to a line or word, each with chords, filter cutoff and pluck density.
Let the music act the story: sparse and minor on the problem, drop to a bare pad (density 0) when something on screen
freezes or breaks, open into major at the fix.

## Layout rules (the user checks spacing frame by frame — check before showing)

- 1080×1920, 30 fps. Words only in y 250–1330 (Reels UI + 3:4 grid crop). Stage = `.stage` (250–1130, flex column,
  56 px gaps, vertically centred); captions own 1172–1330 (dark pill, active word white). Never hand-place by `top:`.
- Never let a headline touch the block under it; labels ≥24 px from shapes; no crammed rows; no empty bottom half.
- Side-by-side items of different heights (icon, line, card) go in a flex row with `align-items: center`.
- A card that only states a number reads flat: give it a header + chip, a labelled stat and a small picture of the
  number (e.g. a flat chart for a zero). Leave clear space between a big value and the lines under it.
- Two states in one area → two absolutely stacked stages, crossfaded. Reserve space for elements that arrive later
  and centre with a translate that animates away when they arrive.
- Type floor 28 px; product/Slack UI rebuilt at ~1.7× (Lato for Slack); headlines Poppins 700; code/numbers IBM Plex Mono.
- One accent per frame: red `#ff4d5e` = the failure, blue `#5b8cff`/`#005ef8` = the fix, green = still alive.
- Frame 0 is the thumbnail: the hook must already read. Cover = a 1080×1440 crop of the twist frame.

## HyperFrames caveats

- Every scene root is styled by `#root`; put scene classes on an inner `<div class="scene …">`.
- Fonts: `assets/kit.css` declares `@font-face` for Poppins, Lato and Plex from local files. The automatic Google Fonts
  injection worked in snapshots but NOT in the full render (headlines fell back to Arial).
- No `tl.call()` for state (seeks don't replay it) — drive counters with `onUpdate` on a tween (pure function of time).
- No CSS `transform` on anything GSAP animates. A scene's base colour must match the previous scene where a flood or
  iris starts, or the jump shows.
- Write film times as `const S = <scene start>` + `at(<film time>)` so `retime.py` can move them.
- Snapshot before rendering (`$HF snapshot --at …`), then pull frames from the FINAL mp4 and check each against the
  word it should land on. Measure loudness with `$HF audio` and say it was measured, not heard.

## Fixed outro

The last spoken line is always `That's what we build, at Siffars.` (captions off). `compositions/outro.html` (from
the template): blue flood on "That's", the mark turns in and lands on "Sifars" (`soft-boom` there), wordmark wipes,
tagline "We build AI systems that run in production.", `sifars.com`. Hold ≥2 s after the tagline lands. The line
before it is the reel's payoff in big type, each word pinned to its measured start.

## Deliver

In `projects/<name>/output/`: `<name>.mp4` (−14 LUFS, ≤ −1 dBTP), `<name>-cover.png` (1080×1440), `<name>-caption.txt`
(the story in 4–6 short lines + hashtags); superseded versions in `output/old/`. Write `REVIEW.md` in the reel:
sources, creative calls, measured vs looked at, kept warnings. Optional carousel: `node statics/render.mjs <post.json>`
(see `templates/statics/example-carousel.json`). ElevenLabs free tier: `mp3_44100_128` only.
