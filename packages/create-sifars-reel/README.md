# create-sifars-reel

```bash
bun create sifars-reel            # from inside the project you want to post about
bun create sifars-reel ~/code/x   # or point at a folder
```

Installs (or updates) the sifars-reel framework in `~/.sifars-reel`, then:

1. checks your machine (git, Node 22+, ffmpeg, uv, Chrome, Claude Code; Codex and OpenCode are optional),
2. sets up its dependencies inside `~/.sifars-reel` (nothing global),
3. opens Claude (Opus 5.5, high effort) to read your code, commits and Claude/Codex sessions and suggest post ideas,
4. asks for an ElevenLabs API key if you chose a voiced reel,
5. hands the brief to Claude, Codex or OpenCode in yolo mode to build the post into
   `~/.sifars-reel/projects/<name>/output/`.

The framework repo is private: you need access to it and a GitHub login (`gh auth login` or git credentials).
Override with `SIFARS_REEL_HOME` (install folder) and `SIFARS_REEL_REPO` (`owner/name` or a git URL).
