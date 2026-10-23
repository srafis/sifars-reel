#!/usr/bin/env node
// Writes a reel's sound-effect <audio> tags from its cues.json.
// Usage: node tools/sfx.mjs projects/<name>/reel
//
// cues.json: [{ "t": 12.1, "sfx": "k-error-006", "vol": 0.8, "at": "peak" | "onset", "why": "..." }]
// `t` is when the event happens on screen (seconds, film time). Each file's peak (or onset) is
// measured once with `hyperframes audio` and cached in assets/sfx/peaks.json, so the clip starts
// early enough for its hit to land one frame after the picture.
import { execFileSync } from "node:child_process";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";

const reel = resolve(process.argv[2] ?? ".");
const hf = resolve(import.meta.dirname, "..", "bin", "hf");
const cues = JSON.parse(readFileSync(join(reel, "cues.json"), "utf8"));
const peaksPath = join(reel, "assets", "sfx", "peaks.json");
const peaks = existsSync(peaksPath) ? JSON.parse(readFileSync(peaksPath, "utf8")) : {};

for (const name of new Set(cues.map(c => c.sfx))) {
  if (peaks[name]) continue;
  const out = execFileSync(hf, ["audio", `assets/sfx/${name}.mp3`, "--json"], { cwd: reel, encoding: "utf8" });
  const item = JSON.parse(out).items[0];
  peaks[name] = { peak: item.moments.peak, onset: item.moments.onset, duration: item.duration };
}
writeFileSync(peaksPath, JSON.stringify(peaks, null, 2) + "\n");

const frame = 1 / 30;
// Each clip gets its own length and the first lane that is free by its start, so no two clips share a lane at once.
const laneEnds = [];
const tags = cues
  .sort((a, b) => a.t - b.t)
  .map((c, i) => {
    const p = peaks[c.sfx];
    const start = Math.max(0, c.t + frame - p[c.at ?? "peak"]);
    let lane = laneEnds.findIndex(end => end <= start);
    if (lane === -1) lane = laneEnds.push(0) - 1;
    laneEnds[lane] = start + p.duration;
    const why = c.why ? ` <!-- ${c.why} -->` : "";
    return `      <audio id="sfx-${String(i + 1).padStart(2, "0")}" class="clip" src="assets/sfx/${c.sfx}.mp3" data-start="${start.toFixed(3)}" data-duration="${p.duration.toFixed(3)}" data-volume="${c.vol ?? 1}" data-track-index="${10 + lane}"></audio>${why}`;
  });

const indexPath = join(reel, "index.html");
const html = readFileSync(indexPath, "utf8").replace(
  /<!--SFX-START-->[\s\S]*<!--SFX-END-->/,
  `<!--SFX-START-->\n${tags.join("\n")}\n      <!--SFX-END-->`,
);
writeFileSync(indexPath, html);
console.log(`${tags.length} cues written to ${indexPath}`);
