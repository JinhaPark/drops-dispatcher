#!/usr/bin/env python3
"""Fail-closed check that public data is identical to migrated private data."""
from pathlib import Path
import hashlib
import sys

public, private = (Path(p) for p in sys.argv[1:3])
for name in ("articles", "reports", "data"):
    directory = public / name
    if not directory.is_dir():
        continue
    files = [p for p in directory.rglob("*") if p.is_file()]
    for path in files:
        rel = path.relative_to(public)
        counterpart = private / rel
        if not counterpart.is_file():
            raise SystemExit(f"Private counterpart missing: {rel}")
        if hashlib.sha256(path.read_bytes()).digest() != hashlib.sha256(counterpart.read_bytes()).digest():
            raise SystemExit(f"Private counterpart differs: {rel}")
for item in ("sources.json",):
    p = public / item
    if p.is_file() and (not (private/item).is_file() or p.read_bytes() != (private/item).read_bytes()):
        raise SystemExit(f"Private counterpart absent or different: {item}")
print("Verified public data files have matching copies in private repository.")
