#!/usr/bin/env python3
"""Copy content/state into the private checkout without overwriting divergent data."""
from pathlib import Path
import shutil
import sys

source, target = map(Path, sys.argv[1:3])
required = ("data/discord-deliveries.json", "data/monitor-state.json")
for item in required:
    if not (source / item).is_file():
        raise SystemExit(f"Missing required source: {item}")
if not (source / "articles").is_dir():
    raise SystemExit("Missing articles source directory")

paths = []
for directory in ("articles", "reports", "data"):
    base = source / directory
    if base.is_dir():
        paths.extend(p for p in base.rglob("*") if p.is_file())
if (source / "sources.json").is_file():
    paths.append(source / "sources.json")
# Preflight all paths before writing any files.
for origin in paths:
    destination = target / origin.relative_to(source)
    if destination.exists() and destination.read_bytes() != origin.read_bytes():
        raise SystemExit(f"Conflict, migration stopped: {origin.relative_to(source)}")
copied = 0
for origin in paths:
    destination = target / origin.relative_to(source)
    if not destination.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origin, destination)
        copied += 1
print(f"Private migration prepared: {copied} new files; {len(paths)} source files checked")
