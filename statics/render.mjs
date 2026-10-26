#!/usr/bin/env node
// Renders a post file (posts/*.json) to PNG slides with headless Chrome.
// Usage: node statics/render.mjs <post.json> [outDir]   (outDir default: projects/<name>/output/<post name>)
// A post is { "template": "<name>", "slides": [ {...}, ... ] }; each slide is
// rendered through statics/templates/<template>.html, which reads window.SLIDE.
import { execFileSync } from "node:child_process";
import { mkdirSync, readFileSync, writeFileSync, existsSync } from "node:fs";
import { basename, dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "..");
const postPath = process.argv[2];
if (!postPath) {
  console.error("usage: node statics/render.mjs <post.json> [outDir]");
  process.exit(1);
}

const post = JSON.parse(readFileSync(postPath, "utf8"));
const width = post.width ?? 1080;
const height = post.height ?? 1350;
const template = readFileSync(join(here, "templates", `${post.template}.html`), "utf8");
const name = basename(postPath, ".json");
const outDir = resolve(process.argv[3] ?? join(dirname(resolve(postPath)), "..", "output", name));
const buildDir = join(root, ".cache", "statics", name);
mkdirSync(outDir, { recursive: true });
mkdirSync(buildDir, { recursive: true });

const chrome = process.env.CHROME ?? ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "/usr/bin/google-chrome-stable", "/usr/bin/google-chrome", "/usr/bin/chromium"].find(existsSync);
const profile = join(root, ".local-home", "chrome-statics");

post.slides.forEach((slide, i) => {
  const data = { ...slide, index: i + 1, total: post.slides.length, shared: post.shared ?? {} };
  const html = template
    .replaceAll("{{ROOT}}", `file://${root}`)
    .replace("/*{{SLIDE}}*/", `window.SLIDE = ${JSON.stringify(data)};`);
  const page = join(buildDir, `slide-${i + 1}.html`);
  writeFileSync(page, html);
  const out = join(outDir, `${String(i + 1).padStart(2, "0")}.png`);
  execFileSync(chrome, [
    "--headless=new",
    `--user-data-dir=${profile}`,
    "--hide-scrollbars",
    "--force-device-scale-factor=1",
    "--allow-file-access-from-files",
    "--virtual-time-budget=4000",
    `--window-size=${width},${height}`,
    `--screenshot=${out}`,
    `file://${page}`,
  ], { stdio: "ignore" });
  console.log(out);
});
