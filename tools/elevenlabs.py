"""Small ElevenLabs client. The key comes from $ELEVEN_LABS_API_KEY or the repo's .env (last definition wins).

  python -I tools/elevenlabs.py check                 # key works? characters left this month?
  python -I tools/elevenlabs.py take <reel>           # voices <reel>/vo/script.json as ONE take (Henry)
  python -I tools/elevenlabs.py say <out.mp3> <text>  # one short sample (pronunciation tests)
  python -I tools/elevenlabs.py stt <reel>            # Scribe word timings -> assets/vo/transcript.json (fallback for Parakeet)
  python -I tools/elevenlabs.py voices | models
"""
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = "https://api.elevenlabs.io"
HENRY = "991lF4hc0xxfec4Y6B0i"
FORMAT = "mp3_44100_128"  # higher bitrates are refused below the Creator tier


def key():
    found = os.environ.get("ELEVEN_LABS_API_KEY")
    env = ROOT / ".env"
    if not found and env.exists():
        for line in env.read_text().splitlines():
            if line.strip().startswith("ELEVEN_LABS_API_KEY="):
                found = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not found:
        sys.exit('ELEVEN_LABS_API_KEY is not set. Add ELEVEN_LABS_API_KEY="..." to .env (the launcher can do it for you).')
    return found


def request(path, body=None, data=None, content_type=None, raw=False, tries=5):
    """POST when body/data is given, else GET. Retries rate limits, server errors and dropped connections."""
    for attempt in range(tries):
        req = urllib.request.Request(API + path, method="POST" if (body is not None or data is not None) else "GET")
        req.add_header("xi-api-key", key())
        if body is not None:
            req.add_header("Content-Type", "application/json")
            req.data = json.dumps(body).encode()
        elif data is not None:
            req.add_header("Content-Type", content_type)
            req.data = data
        try:
            with urllib.request.urlopen(req, timeout=300) as res:
                payload = res.read()
                return payload if raw else json.loads(payload)
        except urllib.error.HTTPError as err:
            text = err.read().decode()[:500]
            if err.code in (429, 500, 502, 503, 504) and attempt + 1 < tries:
                wait = int(err.headers.get("retry-after") or 0) or 2 ** attempt * 3
                print(f"ElevenLabs {err.code}, retrying in {wait}s", file=sys.stderr)
                time.sleep(wait)
                continue
            if err.code == 401:
                sys.exit("ElevenLabs rejected the key (401). Check ELEVEN_LABS_API_KEY in .env.")
            sys.exit(f"ElevenLabs {err.code}: {text}")
        except (urllib.error.URLError, TimeoutError, ConnectionError) as err:
            if attempt + 1 < tries:
                print(f"ElevenLabs unreachable ({err}), retrying", file=sys.stderr)
                time.sleep(2 ** attempt * 3)
                continue
            sys.exit(f"ElevenLabs unreachable: {err}")


def call(path, body=None):  # kept for older scripts
    return request(path, body)


def words_from(alignment, offset=0.0):
    """Character alignment -> [{w, start, end}] in seconds."""
    words, cur = [], None
    for c, s, e in zip(alignment["characters"], alignment["character_start_times_seconds"], alignment["character_end_times_seconds"]):
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


def chars_left():
    sub = request("/v1/user/subscription")
    return sub.get("character_limit", 0) - sub.get("character_count", 0), sub


def check():
    left, sub = chars_left()
    print(json.dumps({"ok": True, "tier": sub.get("tier"), "characters_left": left}))


def take(reel):
    """Voices the whole script in ONE request (natural flow, no joins). Blank lines between script lines make the
    voice pause. The returned word timings run late; tools/measure-words.sh replaces them with measured ones."""
    reel = Path(reel)
    spec = json.loads((reel / "vo" / "script.json").read_text())
    text = "\n\n".join(line["text"] for line in spec["lines"])
    left, _ = chars_left()
    if left < len(text):
        sys.exit(f"ElevenLabs has {left} characters left this month; this script needs {len(text)}.")
    out = reel / "assets" / "vo"
    out.mkdir(parents=True, exist_ok=True)
    body = {"text": text, "model_id": spec.get("model", "eleven_v4"), "voice_settings": spec.get("voice_settings", {})}
    res = request(f"/v1/text-to-speech/{spec.get('voice_id', HENRY)}/with-timestamps?output_format={FORMAT}", body)
    (out / "take.mp3").write_bytes(base64.b64decode(res["audio_base64"]))
    (out / "take.json").write_text(json.dumps({"text": text, "voice_id": spec.get("voice_id", HENRY), "words": words_from(res["alignment"])}, indent=1, ensure_ascii=False))
    print("voiced take:", len(text), "chars")


def say(out, text, voice=HENRY):
    body = {"text": text, "model_id": "eleven_v4", "voice_settings": {"stability": 0.5, "similarity_boost": 0.8}}
    Path(out).write_bytes(request(f"/v1/text-to-speech/{voice}?output_format={FORMAT}", body, raw=True))
    print("wrote", out)


def stt(reel):
    """Scribe word timings in the same shape `hf transcribe` writes (assets/vo/transcript.json)."""
    reel = Path(reel)
    audio = (reel / "assets/vo/take.mp3").read_bytes()
    b = uuid.uuid4().hex
    part = lambda n, v: f'--{b}\r\nContent-Disposition: form-data; name="{n}"\r\n\r\n{v}\r\n'.encode()
    data = part("model_id", "scribe_v2") + part("timestamps_granularity", "word") + part("tag_audio_events", "false")
    data += f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="take.mp3"\r\nContent-Type: audio/mpeg\r\n\r\n'.encode()
    data += audio + f"\r\n--{b}--\r\n".encode()
    res = request("/v1/speech-to-text", data=data, content_type=f"multipart/form-data; boundary={b}")
    words = [{"id": f"w{i}", "text": w["text"], "start": w["start"], "end": w["end"]}
             for i, w in enumerate(x for x in res["words"] if x.get("type") == "word")]
    (reel / "assets/vo/transcript.json").write_text(json.dumps(words, indent=1, ensure_ascii=False))
    print("scribe:", len(words), "words")


if __name__ == "__main__":
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "check":
        check()
    elif cmd == "take":
        take(args[0])
    elif cmd == "say":
        say(args[0], " ".join(args[1:]))
    elif cmd == "stt":
        stt(args[0])
    elif cmd == "models":
        for m in request("/v1/models"):
            print(m["model_id"], "|", m.get("name"), "| tts:", m.get("can_do_text_to_speech"))
    elif cmd == "voices":
        for v in request("/v1/voices")["voices"]:
            print(v["voice_id"], "|", v["name"], "|", v.get("category"))
    else:
        sys.exit(__doc__)
