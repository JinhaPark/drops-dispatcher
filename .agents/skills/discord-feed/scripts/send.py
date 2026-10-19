#!/usr/bin/env python3
"""Send final Markdown to Discord with durable per-chunk deduplication."""
import argparse, contextlib, hashlib, json, os, pathlib, sys, tempfile, time, urllib.error, urllib.parse, urllib.request
import fcntl

def units(s):
    return len(s.encode("utf-16-le")) // 2

def chunks(text, limit=1900):
    if not text.strip():
        raise ValueError("Empty Markdown")
    out = []
    remaining = text
    while remaining:
        if units(remaining) <= limit:
            out.append(remaining)
            break
        pos = 0
        count = 0
        for i, char in enumerate(remaining):
            count += units(char)
            if count > limit:
                break
            pos = i + 1
        candidate = remaining[:pos]
        cut = candidate.rfind("\n\n")
        if cut > pos // 3:
            cut += 2
        else:
            cut = candidate.rfind("\n")
            if cut > pos // 3:
                cut += 1
            else:
                cut = candidate.rfind(" ")
                if cut > pos // 3:
                    cut += 1
                else:
                    cut = pos
        if cut == 0:
            raise ValueError("Cannot split message")
        out.append(remaining[:cut])
        remaining = remaining[cut:]
    assert "".join(out) == text
    assert all(units(x) <= limit for x in out)
    return out

def atomic(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
        tmp = f.name
    os.replace(tmp, path)

def send(url, content):
    if not url.startswith("https://discord.com/api/webhooks/") and not url.startswith("https://discordapp.com/api/webhooks/"):
        raise ValueError("Invalid Discord webhook URL")
    sep = "&" if "?" in url else "?"
    endpoint = url + sep + "wait=true"
    payload = json.dumps({"content": content, "allowed_mentions": {"parse": []}}).encode()
    for attempt in range(5):
        req = urllib.request.Request(endpoint, data=payload, method="POST", headers={"Content-Type":"application/json","User-Agent":"discord-feed/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=25) as response:
                result = json.load(response)
            if not result.get("id"):
                raise RuntimeError("Ambiguous success: missing Discord message ID")
            return str(result["id"])
        except urllib.error.HTTPError as e:
            if e.code == 429:
                try:
                    retry = float(json.loads(e.read()).get("retry_after", 2))
                except (ValueError, TypeError):
                    retry = 2
                time.sleep(min(max(retry, 1), 30))
                continue
            if e.code in (500, 502, 503, 504):
                raise RuntimeError("Uncertain delivery: server error; reconcile before retry") from e
            raise RuntimeError("Permanent Discord HTTP error " + str(e.code)) from e
        except (urllib.error.URLError, TimeoutError) as e:
            raise RuntimeError("Uncertain delivery: network failure; reconcile before retry") from e
    raise RuntimeError("Discord rate limit retry budget exhausted")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    parser.add_argument("--id", required=True)
    parser.add_argument("--state", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    text = pathlib.Path(args.file).read_text(encoding="utf-8")
    parts = chunks(text)
    digest = hashlib.sha256(text.encode()).hexdigest()
    if args.dry_run:
        print(json.dumps({"id":args.id,"sha256":digest,"chunks":len(parts),"utf16_units":[units(p) for p in parts]}))
        return
    url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not url:
        raise RuntimeError("Missing DISCORD_WEBHOOK_URL")
    state_path = pathlib.Path(args.state)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    with open(str(state_path)+".lock","a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = json.loads(state_path.read_text()) if state_path.exists() else {}
        record = state.get(args.id)
        if record:
            if record["sha256"] != digest:
                raise RuntimeError("Changed article: explicit revision approval required")
            if record["status"] == "complete":
                print("Already delivered")
                return
            if record["status"] == "uncertain":
                raise RuntimeError("Uncertain previous delivery; manual reconciliation required")
        else:
            record = {"sha256":digest,"status":"pending","messages":[],"total":len(parts)}
            state[args.id] = record
            atomic(state_path,state)
        for index in range(len(record["messages"]),len(parts)):
            try:
                message_id = send(url, parts[index])
            except Exception:
                record["status"] = "uncertain"
                atomic(state_path,state)
                raise
            record["messages"].append({"index":index,"message_id":message_id})
            atomic(state_path,state)
        record["status"] = "complete"
        atomic(state_path,state)
        print("Delivered",len(parts),"messages")

if __name__ == "__main__":
    main()
