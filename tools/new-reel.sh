#!/usr/bin/env bash
# Scaffolds a reel with the shared kit: layout CSS, fonts, logos, GSAP, fixed outro, music plan and
# voice script skeleton, into projects/<name>/reel (git-ignored: projects never enter the repo).
# Postable files go to projects/<name>/output. Usage: tools/new-reel.sh <name>
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NAME="${1:?usage: tools/new-reel.sh <name>}"
DIR="$ROOT/projects/$NAME/reel"
[ -e "$DIR" ] && { echo "projects/$NAME/reel already exists"; exit 1; }
mkdir -p "$ROOT/projects/$NAME/output"
mkdir -p "$DIR"/{compositions,vo,assets/{fonts,img,vendor,sfx,vo,music}}
cp "$ROOT/templates/reel/hyperframes.json" "$DIR/"
sed "s/REEL_NAME/$NAME/" "$ROOT/templates/reel/package.json" > "$DIR/package.json"
cp "$ROOT/templates/reel/kit.css" "$DIR/assets/kit.css"
cp "$ROOT/templates/reel/compositions/outro.html" "$DIR/compositions/"
cp "$ROOT/templates/reel/vo/"*.json "$DIR/vo/"
cp "$ROOT"/brand/fonts/{poppins-latin-{500,600,700},ibm-plex-mono-latin-{400,500,600}}-normal.woff2 "$DIR/assets/fonts/"
cp "$ROOT"/node_modules/@fontsource/lato/files/lato-latin-{400,700,900}-normal.woff2 "$DIR/assets/fonts/"
cp "$ROOT"/brand/logo/sifars-{full,mark,wordmark}-white.png "$DIR/assets/img/"
cp "$ROOT/node_modules/gsap/dist/gsap.min.js" "$DIR/assets/vendor/"
echo "[]" > "$DIR/cues.json"
echo "scaffolded projects/$NAME/reel"
echo "next: write vo/script.json, then: .venv/bin/python -I tools/elevenlabs.py take projects/$NAME/reel"
echo "      (soft SFX need the take first: .venv/bin/python -I tools/sound.py sfx projects/$NAME/reel)"
