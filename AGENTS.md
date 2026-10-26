# sifars-insta

A framework for turning real engineering work into Instagram posts for @sifars.us. Point an agent at a folder
(a repo, logs, notes) or describe a problem we solved, and it produces postable content: a faceless story reel
(9:16 MP4 + cover + caption) and, optionally, a carousel.

## How to use it

- Developers start with `bun create sifars-reel` (package in `packages/create-sifars-reel/`): it installs or updates
  this repo in `~/.sifars-reel` and runs `launcher/main.ts` — doctor → setup → plan with Claude (Opus 5.5, high) →
  ElevenLabs key if voiced → build with Claude, Codex or OpenCode in yolo mode. Inside a checkout: `bun run reel`
  (`--build <project>` resumes a build, `--doctor`, `--dry-run`).

- "Make a reel from ~/code/<project>" or "make a reel about how we fixed X" → follow the `sifars-reel` skill
  (`.agents/skills/sifars-reel/SKILL.md`). Read it in full before starting.
- Everything for one piece of work goes in `projects/<name>/` (git-ignored): `reel/` (the HyperFrames project),
  `output/` (what gets posted), plus any samples or notes. Projects never enter git.
- Project-specific knowledge (names and how to pronounce them, people to keep off screen, where the sources were)
  goes in `AGENTS.local.md` (git-ignored). Read it before starting; update it when you learn something.

## Layout

| Path                             | What                                                                                                                                                                                                                  |
| -------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `.agents/skills/`                | Agent skills. `sifars-reel` = the reel pipeline, rules and caveats.                                                                                                                                                   |
| `tools/`                         | `new-reel.sh` (scaffold), `elevenlabs.py` (voice), `asr-align.py` + `vo-timeline.py` (word timing), `captions.py`, `sound.py` (soft SFX + music bed), `sfx.mjs` (cue tags), `retime.py` (move a reel onto a new take) |
| `templates/reel/`                | Layout kit (`kit.css`), fixed Sifars outro, voice script + music plan skeletons                                                                                                                                       |
| `templates/statics/`, `statics/` | Carousel template and its renderer (HTML → PNG with headless Chrome)                                                                                                                                                  |
| `brand/`                         | Tokens, fonts, logo (`brand/logo/`, current single-colour mark; source in `brand/logo/v2/`)                                                                                                                           |
| `bin/hf`                         | HyperFrames CLI with every cache kept inside the repo                                                                                                                                                                 |
| `launcher/`                      | `main.ts` (the flow above) and `prompts/` (planner system prompt, builder prompt)                                                                                                                                       |
| `packages/create-sifars-reel/`   | The npm package behind `bun create sifars-reel` (published separately)                                                                                                                                                  |

## Setup (nothing global)

```bash
bun run reel --setup-only                     # node_modules (bun), .venv (uv, requirements.txt); caches in .cache/
echo 'ELEVEN_LABS_API_KEY="..."' > .env       # only for voiced reels; the launcher asks for it when needed
```

Prerequisites (checked by `bun run doctor`, never installed for you): git, Node 22+, Bun, ffmpeg, uv, Chrome,
Claude Code; Codex and OpenCode are optional builders. The Parakeet speech model (~640 MB, word timing for voiced
reels) downloads into `.local-home/` on first use.

Never install anything globally: no `npm -g`, no system pip, no global skills, no browser downloads (system Chrome
is used). Caches stay in `.cache/` and `.local-home/`.

## Sifars-wide rules

- Voice: ElevenLabs Henry (`991lF4hc0xxfec4Y6B0i`, `eleven_v4`). Say "Sifars" as **Siffars** in any TTS text.
- Logo: only from `brand/logo/`. The website still shows an old dual-tone logo.
- Brand: blue `#005ef8`, ink `#080c16`, Poppins (headlines), IBM Plex Mono (code, numbers), Lato (rebuilt Slack UI).
  Tagline: "We build AI systems that run in production."
- Content: one real problem per reel, every fact traceable to a source, no private data on screen, client names only
  with written permission.

## Rules

- Env files: always quote values, `ABC="xyz"`.
- Commits: no `Co-Authored-By` trailers or other AI attribution in commit messages.
