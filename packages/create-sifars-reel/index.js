#!/usr/bin/env bun
// `bun create sifars-reel [folder]` — installs or updates the sifars-reel framework in ~/.sifars-reel, then starts
// its launcher. The framework repo is private: cloning uses your own GitHub access (gh login or git credentials).
//
//   SIFARS_REEL_HOME   where the framework lives (default ~/.sifars-reel)
//   SIFARS_REEL_REPO   owner/name or a git URL (default below)
//   [folder]           the folder to make a post about (default: where you ran the command)
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { homedir } from "node:os";
import { join, resolve } from "node:path";

const REPO = process.env.SIFARS_REEL_REPO || "OWNER/sifars-reel";
const HOME = resolve(process.env.SIFARS_REEL_HOME || join(homedir(), ".sifars-reel"));
const args = process.argv.slice(2);
const positional = args.filter((a) => !a.startsWith("-"));
const passthrough = args.filter((a) => a.startsWith("-"));
const source = resolve(positional[0] ?? process.cwd());

const quiet = (cmd, argv, cwd) => spawnSync(cmd, argv, { cwd, encoding: "utf8" });
const loud = (cmd, argv, cwd) => spawnSync(cmd, argv, { cwd, stdio: "inherit" }).status === 0;
const has = (cmd) => quiet("sh", ["-c", `command -v ${cmd}`]).status === 0;
const isUrl = /^(https?:|git@|ssh:|file:|\/)/.test(REPO);

function clone() {
  console.log(`Installing sifars-reel into ${HOME} ...`);
  const tries = isUrl
    ? [["git", ["clone", "--depth", "50", REPO, HOME]]]
    : [
        ...(has("gh") && quiet("gh", ["auth", "status"]).status === 0 ? [["gh", ["repo", "clone", REPO, HOME, "--", "--depth", "50"]]] : []),
        ["git", ["clone", "--depth", "50", `git@github.com:${REPO}.git`, HOME]],
        ["git", ["clone", "--depth", "50", `https://github.com/${REPO}.git`, HOME]],
      ];
  for (const [cmd, argv] of tries) {
    if (loud(cmd, argv)) return;
    quiet("rm", ["-rf", HOME]);
  }
  console.error(`\nCould not clone ${REPO}. It's a private repo: ask for access, then log in with \`gh auth login\` (or set up git credentials) and run this again.`);
  process.exit(1);
}

function update() {
  if (!existsSync(join(HOME, ".git"))) {
    console.error(`${HOME} exists but isn't a sifars-reel checkout. Move it away or set SIFARS_REEL_HOME.`);
    process.exit(1);
  }
  const r = quiet("git", ["pull", "--ff-only", "--quiet"], HOME);
  if (r.status !== 0) console.warn(`! Couldn't update ${HOME} (${(r.stderr || "").trim().split("\n").pop() || "offline?"}); using the copy you have.`);
}

if (!has("git")) { console.error("git is required."); process.exit(1); }
existsSync(HOME) ? update() : clone();

const r = spawnSync("bun", [join(HOME, "launcher/main.ts"), "--source", source, ...passthrough], { stdio: "inherit", cwd: source });
process.exit(r.status ?? 1);
