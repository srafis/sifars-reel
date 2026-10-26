#!/usr/bin/env bash
# Measures when each word of the voice take is spoken and writes the timings into assets/vo/take.json.
# Parakeet (local, ~640 MB, downloaded on first use) is the accurate path; if it can't be installed or run,
# ElevenLabs Scribe is used instead (median +0.06 s, but ~1 word in 10 lands 0.2-0.4 s late).
# Usage: tools/measure-words.sh projects/<name>/reel
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REEL="$(cd "${1:?usage: tools/measure-words.sh <reel>}" && pwd)"
HF="$ROOT/bin/hf"
PY="$ROOT/.venv/bin/python"

parakeet_ready() { "$HF" models list --json 2>/dev/null | grep -q '"installed":true'; }

if ! parakeet_ready; then
  echo "Downloading the Parakeet speech model (one time, ~640 MB)..."
  "$HF" models install parakeet --json >/dev/null 2>&1 || true
fi

rm -f "$REEL/assets/vo/transcript.json"
if parakeet_ready && (cd "$REEL" && "$HF" transcribe assets/vo/take.mp3 --engine parakeet --json >/dev/null 2>&1) \
   && [ -s "$REEL/assets/vo/transcript.json" ]; then
  echo "word timings: parakeet"
else
  echo "Parakeet unavailable; falling back to ElevenLabs Scribe (timing may be up to 0.4 s late on some words)." >&2
  "$PY" -I "$ROOT/tools/elevenlabs.py" stt "$REEL"
fi
"$PY" -I "$ROOT/tools/asr-align.py" "$REEL"
