"""Feed discovery only: verified chronology and conservative source baselines.

This module does NOT summarize, create publishable Markdown or send to Discord.
"""
import datetime as dt
import email.utils
import hashlib
import html
import json
import pathlib
import re
import urllib.parse
import xml.etree.ElementTree as ET

UTC = dt.timezone.utc
ATOM = "{http://www.w3.org/2005/Atom}"
HTML_TAG = re.compile(r"<[^>]+>")


def parse_time(value, *, rss=False):
    if not value or not isinstance(value, str):
        raise ValueError("Missing publication date")
    if rss:
        parsed = email.utils.parsedate_to_datetime(value)
    else:
        parsed = dt.datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if not isinstance(parsed, dt.datetime) or parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Publication date has no timezone")
    return parsed.astimezone(UTC)


def canonical_key(url):
    if not isinstance(url, str):
        raise ValueError("Missing canonical URL")
    parts = urllib.parse.urlsplit(html.unescape(url.strip()))
    if parts.scheme.lower() not in ("http", "https") or not parts.hostname:
        raise ValueError("Expected an HTTP(S) canonical URL")
    host = parts.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    path = urllib.parse.unquote(parts.path or "/").rstrip("/") or "/"
    query = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
    query = [(k, v) for k, v in query if not (k.lower().startswith("utm_") or k.lower() in ("fbclid", "gclid", "ref", "source"))]
    return host + path + ("?" + urllib.parse.urlencode(sorted(query)) if query else "")


def plain(value):
    return " ".join(HTML_TAG.sub(" ", html.unescape(value or "")).split())


def atom_entries(root):
    if root.tag != ATOM + "feed":
        raise ValueError("Not an Atom feed")
    for e in root.findall(ATOM + "entry"):
        link = next((x.get("href", "") for x in e.findall(ATOM + "link")
                     if x.get("rel", "alternate") == "alternate"
                     and x.get("type", "text/html") in ("text/html", "application/xhtml+xml")), "")
        yield {"title": "".join(e.find(ATOM + "title").itertext()) if e.find(ATOM + "title") is not None else "",
               "url": link, "published": e.findtext(ATOM + "published"),
               "excerpt": e.findtext(ATOM + "summary") or ""}


def rss_entries(root):
    if root.tag not in ("rss", "RDF", "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF"):
        raise ValueError("Not an RSS feed")
    for e in root.findall(".//item"):
        yield {"title": e.findtext("title") or "", "url": e.findtext("link") or "",
               "published": e.findtext("pubDate"), "excerpt": e.findtext("description") or ""}


def discover(xml, source, cutoff, known_urls=()):
    """Return original feed metadata for posts published strictly after cutoff."""
    root = ET.fromstring(xml)
    kind = source.get("feed_format")
    if kind == "atom":
        entries = atom_entries(root)
    elif kind == "rss":
        entries = rss_entries(root)
    else:
        raise ValueError("Unsupported declared feed_format")
    seen = set(known_urls)
    output = []
    for entry in entries:
        try:
            when = parse_time(entry["published"], rss=(kind == "rss"))
            key = canonical_key(entry["url"])
        except (ValueError, TypeError, OverflowError):
            # Unverifiable publication provenance is never guessed.
            continue
        if when <= cutoff or key in seen:
            continue
        seen.add(key)
        url = entry["url"].split("#", 1)[0]
        uid = source["id"] + ":" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
        output.append({"id": uid, "source": source["id"],
                       "published_at": when.isoformat().replace("+00:00", "Z"),
                       "date": when.date().isoformat(), "title": plain(entry["title"]),
                       "author": source["author"], "url": url,
                       "excerpt": plain(entry["excerpt"])[:1000],
                       "status": "needs_editorial_review"})
    return output


def monitored_sources(sources):
    return [s for s in sources if s.get("enabled") is True and s.get("feed_url")]


def existing_urls(root, pending):
    urls = set()
    for item in pending:
        url = item.get("url") or item.get("canonical_url")
        if url:
            try:
                urls.add(canonical_key(url))
            except ValueError:
                pass
    # Include every prepared article, not just the new-source pending queue.
    for path in (root / "articles").glob("**/*.md"):
        body = path.read_text(encoding="utf-8")
        for line in body.splitlines()[:25]:
            if line.startswith("canonical_url:"):
                try:
                    urls.add(canonical_key(line.split(":", 1)[1].strip().strip("'\"")))
                except ValueError:
                    pass
                break
    return urls


def run(root, request):
    root = pathlib.Path(root)
    sources = json.loads((root / "sources.json").read_text(encoding="utf-8"))
    state_path = root / "data/monitor-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    global_start = parse_time(state["monitoring_started_at"])
    pending_path = root / "data/pending.json"
    pending = json.loads(pending_path.read_text(encoding="utf-8")) if pending_path.exists() else []
    known = existing_urls(root, pending)
    found = []
    checked = dt.datetime.now(UTC).isoformat().replace("+00:00", "Z")
    for source in monitored_sources(sources):
        sid = source["id"]
        policy = state.get("sources", {}).get(sid, {})
        # New source IDs must have a source-specific baseline; fail closed.
        if not policy.get("monitoring_started_at"):
            raise RuntimeError("Missing per-source monitoring baseline: " + sid)
        cutoff = max(global_start, parse_time(policy["monitoring_started_at"]))
        try:
            new = discover(request(source["feed_url"]), source, cutoff, known)
        except (OSError, ValueError, ET.ParseError) as exc:
            policy["status"] = "feed_unavailable_or_unparseable"
            print("Source unavailable:", sid, type(exc).__name__)
            continue
        for item in new:
            known.add(canonical_key(item["url"]))
        found.extend(new)
        policy["last_checked_at"] = checked
        policy["status"] = "feed_checked_pending_original_verification" if new else "feed_checked_no_new_candidates"
        state["sources"][sid] = policy
    # Do not change the global start, or any old source state.
    if found:
        pending.extend(found)
        pending_path.write_text(json.dumps(pending, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return found
