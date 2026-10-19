#!/usr/bin/env python3
"""Dispatch already reviewed Markdown; never generate or rewrite summaries."""
import json,os,pathlib,re,subprocess,sys
root=pathlib.Path(__file__).resolve().parents[1]
state=root/"data/discord-deliveries.json"
for p in sorted((root/"articles").glob("**/*.md")):
 text=p.read_text(encoding="utf-8")
 if not text.startswith("---\n") or "\n---\n" not in text[4:]:
  raise SystemExit(f"Missing YAML front matter: {p}")
 meta=text.split("---",2)[1]
 fields={}
 for line in meta.splitlines():
  if ":" in line:
   k,v=line.split(":",1);fields[k.strip()]=v.strip().strip('"').strip("'")
 if fields.get("status")!="ready":continue
 if not fields.get("id") or not fields.get("canonical_url") or not fields.get("author") or not re.fullmatch(r"\d{4}-\d{2}-\d{2}",fields.get("published_at","")):
  raise SystemExit(f"Missing or invalid provenance: {p}")
 args=[sys.executable,str(root/".agents/skills/discord-feed/scripts/send.py"),"--file",str(p),"--id",fields["id"],"--state",str(state)]
 result=subprocess.run(args,cwd=root)
 if result.returncode:
  raise SystemExit(f"Discord delivery failed for {p}; preserve ledger and inspect uncertain state")
