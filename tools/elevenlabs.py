"""Small ElevenLabs client. Reads ELEVEN_LABS_API_KEY from the repo's .env (last definition wins).

  python -I tools/elevenlabs.py models
  python -I tools/elevenlabs.py voices
  python -I tools/elevenlabs.py tts <reel_dir>     # voices every line in <reel_dir>/vo/script.json
"""
import base64
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = "https://api.elevenlabs.io"


def key():
    found = None
    for line in (ROOT / ".env").read_text().splitlines():
        if line.strip().startswith("ELEVEN_LABS_API_KEY="):
            found = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not found:
        sys.exit("ELEVEN_LABS_API_KEY missing from .env")
    return found


def call(path, body=None):
    req = urllib.request.Request(API + path, method="POST" if body is not None else "GET")
    req.add_header("xi-api-key", key())
    if body is not None:
        req.add_header("Content-Type", "application/json")
        req.data = json.dumps(body).encode()
    try:
        with urllib.request.urlopen(req, timeout=120) as res:
            return json.loads(res.read())
    except urllib.error.HTTPError as err:
        sys.exit(f"{err.code} {err.read().decode()[:500]}")


def words_from(alignment, offset=0.0):
    """Character alignment -> [{w, start, end}] in seconds."""
    chars = alignment["characters"]
    starts = alignment["character_start_times_seconds"]
    ends = alignment["character_end_times_seconds"]
    words, cur = [], None
    for c, s, e in zip(chars, starts, ends):
        if c.isspace():
            if cur:
                words.append(cur)
            cur = None
            continue
        if cur is None:
            cur = {"w": "", "start": s + offset, "end": e + offset}
        cur["w"] += c
        cur["end"] = e + offset
    if cur:
        words.append(cur)
    return words


def tts(reel):
    reel = Path(reel)
    spec = json.loads((reel / "vo" / "script.json").read_text())
    lines = spec["lines"]
    out = reel / "assets" / "vo"
    out.mkdir(parents=True, exist_ok=True)
    for i, line in enumerate(lines):
        mp3 = out / f"{line['id']}.mp3"
        meta = out / f"{line['id']}.json"
        if mp3.exists() and meta.exists() and json.loads(meta.read_text()).get("text") == line["text"]:
            continue
        body = {
            "text": line["text"],
            "model_id": spec["model"],
            "voice_settings": spec.get("voice_settings", {}),
        }
        if i > 0:
            body["previous_text"] = lines[i - 1]["text"]
        if i + 1 < len(lines):
            body["next_text"] = lines[i + 1]["text"]
        res = call(f"/v1/text-to-speech/{spec['voice_id']}/with-timestamps?output_format=mp3_44100_128", body)
        mp3.write_bytes(base64.b64decode(res["audio_base64"]))
        align = res.get("normalized_alignment") or res["alignment"]
        meta.write_text(json.dumps({"text": line["text"], "words": words_from(res["alignment"])}, indent=1))
        print("voiced", line["id"])


def take(reel):
    """Voices the whole script in ONE request (natural flow, no joins) and keeps the word timings.
    Lines are separated by blank lines so the voice pauses between them."""
    reel = Path(reel)
    spec = json.loads((reel / "vo" / "script.json").read_text())
    text = "\n\n".join(line["text"] for line in spec["lines"])
    out = reel / "assets" / "vo"
    out.mkdir(parents=True, exist_ok=True)
    body = {"text": text, "model_id": spec["model"], "voice_settings": spec.get("voice_settings", {})}
    res = call(f"/v1/text-to-speech/{spec['voice_id']}/with-timestamps?output_format=mp3_44100_128", body)
    (out / "take.mp3").write_bytes(base64.b64decode(res["audio_base64"]))
    (out / "take.json").write_text(json.dumps({"text": text, "voice_id": spec["voice_id"], "words": words_from(res["alignment"])}, indent=1, ensure_ascii=False))
    print("voiced take:", len(text), "chars")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "models":
        for m in call("/v1/models"):
            print(m["model_id"], "|", m.get("name"), "| tts:", m.get("can_do_text_to_speech"))
    elif cmd == "voices":
        for v in call("/v1/voices")["voices"]:
            labels = v.get("labels") or {}
            print(v["voice_id"], "|", v["name"], "|", v.get("category"), "|", ", ".join(f"{k}={val}" for k, val in labels.items()))
    elif cmd == "take":
        take(sys.argv[2])
    elif cmd == "tts":
        tts(sys.argv[2])
