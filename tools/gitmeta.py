#!/usr/bin/env python3
"""Emit data/gitmeta.json — per-entry {start, commits, lastmod} straight from git history.
Keys match Hugo's .File.Path (relative to content/). Run before `hugo` (CI does)."""
import json, pathlib, subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
out = {}
for p in sorted((ROOT / "content").rglob("*.md")):
    rel = p.relative_to(ROOT).as_posix()
    r = subprocess.run(["git", "log", "--follow", "--format=%aI", "--", rel],
                       cwd=ROOT, capture_output=True, text=True)
    dates = [l for l in r.stdout.splitlines() if l.strip()]
    if not dates:
        continue
    out[p.relative_to(ROOT / "content").as_posix()] = {
        "start": dates[-1], "commits": len(dates), "lastmod": dates[0]}
(ROOT / "data").mkdir(exist_ok=True)
(ROOT / "data" / "gitmeta.json").write_text(json.dumps(out, indent=1) + "\n")
print(f"gitmeta: {len(out)} tracked entries")
