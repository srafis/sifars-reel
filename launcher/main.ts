#!/usr/bin/env bun
// sifars-reel launcher: checks the machine, sets up the framework (once), plans a post with Claude, collects the
// ElevenLabs key if the post is voiced, then hands the brief to a builder agent (claude / codex / opencode).
//
//   bun launcher/main.ts                      full flow (plan, then build)
//   bun launcher/main.ts --build <project>    build an existing brief again (e.g. after a crash)
//   bun launcher/main.ts --doctor             check prerequisites only
//   bun launcher/main.ts --setup-only         check + install dependencies, then stop
//   bun launcher/main.ts --dry-run            print the agent commands instead of running them
//   --source <dir>                            folder to suggest to the planner (default: where you ran the command)
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, readdirSync, readFileSync, statSync, writeFileSync, chmodSync, mkdirSync } from "node:fs";
import { homedir } from "node:os";
import { join, resolve } from "node:path";

const ROOT = resolve(import.meta.dir, "..");
const MODEL = "claude-opus-5-5";
const EFFORT = "high";
const args = process.argv.slice(2);
const flag = (name: string) => args.includes(name);
const opt = (name: string) => (args.includes(name) ? args[args.indexOf(name) + 1] : undefined);
const DRY = flag("--dry-run");

const c = { dim: "\x1b[2m", bold: "\x1b[1m", red: "\x1b[31m", green: "\x1b[32m", yellow: "\x1b[33m", off: "\x1b[0m" };
const say = (msg = "") => console.log(msg);
const fail = (msg: string): never => { console.error(`${c.red}✗${c.off} ${msg}`); process.exit(1); };

// Every cache and download stays inside the framework folder.
const ENV = {
  ...process.env,
  BUN_INSTALL_CACHE_DIR: join(ROOT, ".cache/bun"),
  UV_CACHE_DIR: join(ROOT, ".cache/uv"),
  UV_PYTHON_INSTALL_DIR: join(ROOT, ".cache/uv-python"),
  npm_config_cache: join(ROOT, ".cache/npm"),
};

function which(cmd: string): string | null {
  const r = spawnSync("sh", ["-c", `command -v ${cmd}`], { encoding: "utf8" });
  return r.status === 0 ? r.stdout.trim() : null;
}

function run(cmd: string, argv: string[], opts: { cwd?: string; quiet?: boolean } = {}) {
  const r = spawnSync(cmd, argv, { cwd: opts.cwd ?? ROOT, env: ENV, stdio: opts.quiet ? "pipe" : "inherit", encoding: "utf8" });
  return { ok: r.status === 0, out: `${r.stdout ?? ""}${r.stderr ?? ""}` };
}

// ---------- doctor ----------
function chromePath(): string | null {
  const candidates = [
    process.env.CHROME,
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
  ];
  for (const p of candidates) if (p && existsSync(p)) return p;
  for (const n of ["google-chrome-stable", "google-chrome", "chromium", "chromium-browser"]) {
    const p = which(n);
    if (p) return p;
  }
  return null;
}

type Check = { name: string; ok: boolean; detail: string; fix?: string; optional?: boolean };

function doctor(): { checks: Check[]; builders: string[] } {
  const v = (cmd: string, flagArg = "--version") => {
    const r = spawnSync(cmd, [flagArg], { encoding: "utf8" });
    return r.status === 0 ? (r.stdout || r.stderr).split("\n")[0].trim() : "";
  };
  const nodeMajor = Number((v("node").match(/v(\d+)/) ?? [])[1] ?? 0);
  const free = Number(spawnSync("sh", ["-c", `df -Pk "${ROOT}" | awk 'NR==2{print $4}'`], { encoding: "utf8" }).stdout.trim()) / 1048576;
  const checks: Check[] = [
    { name: "git", ok: !!which("git"), detail: v("git"), fix: "install git" },
    { name: "node ≥ 22", ok: nodeMajor >= 22, detail: v("node") || "missing", fix: "HyperFrames runs on Node 22+: https://nodejs.org" },
    { name: "ffmpeg", ok: !!which("ffmpeg") && !!which("ffprobe"), detail: v("ffmpeg", "-version").slice(0, 40) || "missing", fix: "brew install ffmpeg / pacman -S ffmpeg / apt install ffmpeg" },
    { name: "uv", ok: !!which("uv"), detail: v("uv") || "missing", fix: "https://docs.astral.sh/uv/getting-started/installation/" },
    { name: "Chrome", ok: !!chromePath(), detail: chromePath() ?? "missing", fix: "install Google Chrome (rendering uses it headless)" },
    { name: "claude", ok: !!which("claude"), detail: v("claude") || "missing", fix: "https://docs.claude.com/en/docs/claude-code" },
    { name: "disk ≥ 3 GB free", ok: free >= 3, detail: `${free.toFixed(1)} GB free`, fix: "free some disk space" },
  ];
  const builders = ["claude", "codex", "opencode"].filter((b) => which(b));
  for (const b of ["codex", "opencode"]) checks.push({ name: b, ok: builders.includes(b), detail: builders.includes(b) ? v(b) : "not installed", optional: true });
  return { checks, builders };
}

function printDoctor(checks: Check[]) {
  for (const ch of checks) {
    const mark = ch.ok ? `${c.green}✓${c.off}` : ch.optional ? `${c.dim}–${c.off}` : `${c.red}✗${c.off}`;
    say(`  ${mark} ${ch.name.padEnd(18)} ${c.dim}${ch.detail}${c.off}${!ch.ok && ch.fix ? `  → ${ch.fix}` : ""}`);
  }
}

// ---------- setup (idempotent) ----------
function setup() {
  const inputs = ["package.json", "bun.lock", "requirements.txt"].map((f) => (existsSync(join(ROOT, f)) ? readFileSync(join(ROOT, f)) : ""));
  const hash = createHash("sha256").update(inputs.join("\0")).digest("hex").slice(0, 16);
  const stamp = join(ROOT, ".cache/setup-stamp");
  const ready = existsSync(stamp) && readFileSync(stamp, "utf8") === hash && existsSync(join(ROOT, "node_modules/.bin/hyperframes")) && existsSync(join(ROOT, ".venv/bin/python"));
  if (ready) return;
  say(`${c.bold}Setting up${c.off} ${c.dim}(first run or after an update; everything stays in ${ROOT})${c.off}`);
  mkdirSync(join(ROOT, ".cache"), { recursive: true });
  if (!run("bun", ["install", "--frozen-lockfile"]).ok && !run("bun", ["install"]).ok) fail("bun install failed (see above).");
  if (!existsSync(join(ROOT, ".venv/bin/python")) && !run("uv", ["venv", "--python", "3.12", ".venv"]).ok) fail("could not create the Python venv.");
  if (!run("uv", ["pip", "install", "--python", ".venv/bin/python", "-r", "requirements.txt"]).ok) fail("pip install failed (see above).");
  if (!run(join(ROOT, "bin/hf"), ["--version"], { quiet: true }).ok) fail("HyperFrames CLI did not start (node_modules/.bin/hyperframes).");
  writeFileSync(stamp, hash);
  say(`${c.green}✓${c.off} setup done`);
}

// ---------- ElevenLabs key ----------
function readEnvKey(): string | null {
  if (process.env.ELEVEN_LABS_API_KEY) return process.env.ELEVEN_LABS_API_KEY;
  const env = join(ROOT, ".env");
  if (!existsSync(env)) return null;
  const line = readFileSync(env, "utf8").split("\n").reverse().find((l) => l.trim().startsWith("ELEVEN_LABS_API_KEY="));
  return line ? line.split("=").slice(1).join("=").trim().replace(/^["']|["']$/g, "") || null : null;
}

function checkKey(key: string): { ok: boolean; left?: number; msg: string } {
  const r = spawnSync(join(ROOT, ".venv/bin/python"), ["-I", "tools/elevenlabs.py", "check"], { cwd: ROOT, env: { ...ENV, ELEVEN_LABS_API_KEY: key }, encoding: "utf8" });
  if (r.status !== 0) return { ok: false, msg: (r.stderr || r.stdout).trim().split("\n").pop() ?? "check failed" };
  const j = JSON.parse(r.stdout.trim().split("\n").pop()!);
  return { ok: true, left: j.characters_left, msg: `${j.tier} plan, ${j.characters_left} characters left` };
}

async function readSecret(prompt: string): Promise<string> {
  process.stdout.write(prompt);
  const stdin = process.stdin;
  if (!stdin.isTTY) {
    for await (const chunk of stdin) return String(chunk).trim();
    return "";
  }
  stdin.setRawMode(true);
  stdin.resume();
  let value = "";
  return new Promise((done) => {
    const onData = (buf: Buffer) => {
      for (const ch of buf.toString("utf8")) {
        if (ch === "\r" || ch === "\n") {
          stdin.setRawMode(false); stdin.pause(); stdin.off("data", onData); process.stdout.write("\n"); return done(value.trim());
        }
        if (ch === "\u0003") { stdin.setRawMode(false); process.stdout.write("\n"); process.exit(130); }
        if (ch === "\u007f") { if (value) { value = value.slice(0, -1); process.stdout.write("\b \b"); } continue; }
        value += ch; process.stdout.write("•");
      }
    };
    stdin.on("data", onData);
  });
}

function saveKey(key: string) {
  const env = join(ROOT, ".env");
  const lines = existsSync(env) ? readFileSync(env, "utf8").split("\n").filter((l) => l.trim() && !l.trim().startsWith("ELEVEN_LABS_API_KEY=")) : [];
  lines.push(`ELEVEN_LABS_API_KEY="${key}"`);
  writeFileSync(env, lines.join("\n") + "\n");
  chmodSync(env, 0o600);
}

async function ensureVoiceKey(needed: number): Promise<boolean> {
  let key = readEnvKey();
  if (key) {
    const r = checkKey(key);
    if (r.ok) {
      say(`${c.green}✓${c.off} ElevenLabs: ${r.msg}`);
      if ((r.left ?? 0) < needed) say(`${c.yellow}!${c.off} A reel script needs ~${needed} characters; top up or the voice step will stop.`);
      return true;
    }
    say(`${c.yellow}!${c.off} The saved ElevenLabs key doesn't work: ${r.msg}`);
  }
  say(`\n${c.bold}This reel is voiced, so it needs an ElevenLabs API key.${c.off}`);
  say(`${c.dim}Create one at https://elevenlabs.io/app/settings/api-keys (text-to-speech + speech-to-text + user read).`);
  say(`It is saved to ${join(ROOT, ".env")} (git-ignored, readable only by you). Leave empty to make the reel without voice.${c.off}`);
  for (let i = 0; i < 3; i++) {
    key = await readSecret("ElevenLabs API key: ");
    if (!key) return false;
    const r = checkKey(key);
    if (r.ok) { saveKey(key); say(`${c.green}✓${c.off} saved (${r.msg})`); return true; }
    say(`${c.red}✗${c.off} ${r.msg}`);
  }
  return false;
}

// ---------- agents ----------
const fill = (tpl: string, vars: Record<string, string>) => tpl.replace(/\{\{(\w+)\}\}/g, (_, k) => vars[k] ?? "");

function agentCommand(builder: string, prompt: string, yolo: boolean, extra: string[] = []): [string, string[]] {
  // the prompt goes first: --add-dir and --allowedTools take lists and would swallow a trailing prompt
  if (builder === "claude") return ["claude", [prompt, "--model", MODEL, "--effort", EFFORT, ...(yolo ? ["--dangerously-skip-permissions"] : []), ...extra]];
  if (builder === "codex") return ["codex", [...(yolo ? ["--dangerously-bypass-approvals-and-sandbox"] : []), prompt]];
  if (builder === "opencode") return ["opencode", [...(yolo ? ["--auto"] : []), "--prompt", prompt, ROOT]];
  return fail(`unknown builder "${builder}"`);
}

function launch(cmd: string, argv: string[]) {
  if (DRY) {
    const shown = argv.map((a) => (a.length > 120 ? JSON.stringify(a.slice(0, 117) + "...") : /\s/.test(a) ? JSON.stringify(a) : a));
    say(`${c.dim}[dry-run]${c.off} ${cmd} ${shown.join(" ")}`);
    return 0;
  }
  return spawnSync(cmd, argv, { cwd: ROOT, env: ENV, stdio: "inherit" }).status ?? 1;
}

type Handoff = { project: string; kind: "reel" | "carousel"; voice: boolean; builder: string; brief: string };

function newestHandoff(since: number): Handoff | null {
  const dir = join(ROOT, "projects");
  if (!existsSync(dir)) return null;
  const found = readdirSync(dir)
    .map((p) => join(dir, p, "handoff.json"))
    .filter((f) => existsSync(f) && statSync(f).mtimeMs >= since)
    .sort((a, b) => statSync(b).mtimeMs - statSync(a).mtimeMs);
  return found.length ? (JSON.parse(readFileSync(found[0], "utf8")) as Handoff) : null;
}

function readHandoff(project: string): Handoff {
  const f = join(ROOT, "projects", project, "handoff.json");
  if (!existsSync(f)) fail(`no brief for "${project}" (expected ${f})`);
  return JSON.parse(readFileSync(f, "utf8"));
}

function validate(h: Handoff, builders: string[]): Handoff {
  if (!/^[a-z0-9][a-z0-9-]*$/.test(h.project ?? "")) fail(`handoff.json has a bad project name: ${h.project}`);
  if (!existsSync(join(ROOT, h.brief ?? ""))) fail(`the brief ${h.brief} is missing`);
  if (!["reel", "carousel"].includes(h.kind)) h.kind = "reel";
  if (!builders.includes(h.builder)) {
    say(`${c.yellow}!${c.off} "${h.builder}" isn't installed; building with claude instead.`);
    h.builder = "claude";
  }
  return h;
}

// ---------- main ----------
async function main() {
  say(`${c.bold}sifars-reel${c.off} ${c.dim}${ROOT}${c.off}`);
  const { checks, builders } = doctor();
  const missing = checks.filter((ch) => !ch.ok && !ch.optional);
  if (flag("--doctor") || missing.length) printDoctor(checks);
  if (missing.length) fail(`install the missing tools above, then run this again.`);
  if (flag("--doctor")) return;

  if (!DRY) setup();
  if (flag("--setup-only")) return;

  let h: Handoff | null;
  const build = opt("--build");
  if (build) {
    h = readHandoff(build);
  } else {
    const source = resolve(opt("--source") ?? process.env.SIFARS_REEL_SOURCE ?? process.cwd());
    const started = Date.now() - 1000;
    const plan = readFileSync(join(ROOT, "launcher/prompts/plan.md"), "utf8");
    const keyNote = readEnvKey() ? "An ElevenLabs key is already saved." : "No ElevenLabs key is saved yet; the launcher will ask for one if a voiced reel is chosen.";
    const first = `Help me make an Instagram post for @sifars.us from real work. Suggested folder: ${source}. ` +
      `Builders installed: ${builders.join(", ")}. ${keyNote}`;
    const sessionDirs = [join(homedir(), ".claude/projects"), join(homedir(), ".codex/sessions")].filter(existsSync);
    const extra = ["--append-system-prompt", plan, "--add-dir", source, ...sessionDirs.flatMap((d) => ["--add-dir", d]),
      "--allowedTools", ["Read", "Grep", "Glob", "Bash(git log:*)", "Bash(git show:*)", "Bash(git -C:*)", "Bash(ls:*)", "Bash(jq:*)",
        "Bash(grep:*)", "Bash(rg:*)", "Bash(find:*)", "Bash(head:*)", "Bash(tail:*)", "Bash(wc:*)", "Edit(projects/**)"].join(",")];
    say(`\n${c.bold}Step 1/2 · Plan${c.off} ${c.dim}Claude (${MODEL}, ${EFFORT}) will look at your work and suggest ideas.${c.off}\n`);
    const [cmd, argv] = agentCommand("claude", first, false, extra);
    launch(cmd, argv);
    if (DRY) return;
    h = newestHandoff(started);
    if (!h) {
      say(`\nNo brief was saved, so there's nothing to build yet. Run ${c.bold}bun create sifars-reel${c.off} again when you're ready.`);
      return;
    }
  }
  h = validate(h, builders);

  if (h.kind === "reel" && h.voice) {
    const ok = await ensureVoiceKey(1500);
    if (!ok) {
      say(`${c.yellow}!${c.off} No working key: the reel will be made without voice (captions + music + sound effects).`);
      h.voice = false;
      writeFileSync(join(ROOT, "projects", h.project, "handoff.json"), JSON.stringify(h, null, 2) + "\n");
    }
  }

  const outputs = h.kind === "carousel"
    ? "the slide PNGs (1080×1350), a cover and `<name>-caption.txt`."
    : "`<name>.mp4` (−14 LUFS), `<name>-cover.png` (1080×1440) and `<name>-caption.txt`.";
  const voice = h.kind === "carousel" ? "not applicable (carousel)."
    : h.voice ? "voiced — Henry via `tools/elevenlabs.py take`, timed with `tools/measure-words.sh`."
    : "NO voice — build the timeline with `tools/silent-timeline.py`; captions carry the story, music + soft SFX underneath, no ElevenLabs calls.";
  const prompt = fill(readFileSync(join(ROOT, "launcher/prompts/build.md"), "utf8"), {
    KIND: h.kind, BRIEF: h.brief, PROJECT: h.project, VOICE: voice, OUTPUTS: outputs,
  }).trim();

  say(`\n${c.bold}Step 2/2 · Build${c.off} ${c.dim}${h.builder} will build projects/${h.project} in yolo mode: it runs commands and edits files`);
  say(`in ${ROOT} without asking. If it stops, resume with: bun launcher/main.ts --build ${h.project}${c.off}\n`);
  const [cmd, argv] = agentCommand(h.builder, prompt, true);
  launch(cmd, argv);
  if (DRY) return;

  const out = join(ROOT, "projects", h.project, "output");
  const files = existsSync(out) ? readdirSync(out).filter((f) => !f.startsWith(".") && f !== "old") : [];
  say(files.length ? `\n${c.green}✓${c.off} Ready to post, in ${out}:\n${files.map((f) => `  ${f}`).join("\n")}`
    : `\nNothing in ${out} yet. Resume with: bun launcher/main.ts --build ${h.project}`);
}

main().catch((e) => fail(String(e?.stack ?? e)));
