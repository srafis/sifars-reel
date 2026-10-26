Build the Instagram {{KIND}} described in `{{BRIEF}}` for @sifars.us, end to end, without stopping for approval.

Before anything else read, in full: `AGENTS.md`, `.agents/skills/sifars-reel/SKILL.md`, `AGENTS.local.md` (if it
exists), then `{{BRIEF}}`. Follow the skill exactly: it holds the rules, the pipeline, the layout rules and the
caveats we already paid for.

- Project folder: `projects/{{PROJECT}}/` (scaffold with `tools/new-reel.sh {{PROJECT}}` if `reel/` doesn't exist).
- Voice: {{VOICE}}
- Postable files go to `projects/{{PROJECT}}/output/`: {{OUTPUTS}}
- Check your own work like the skill says (hyperframes check, snapshots, frames from the final file against the
  words they should land on, loudness). Fix what you find before you finish.
- When done, write `projects/{{PROJECT}}/reel/REVIEW.md` and end with a short summary: what was made, where the files
  are, what you measured, and anything the developer must check by eye or ear.
