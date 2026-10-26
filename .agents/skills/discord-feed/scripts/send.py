#!/usr/bin/env python3
"""Send final Markdown to Discord with durable per-chunk deduplication."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import pathlib
import re
import tempfile
import time
import unicodedata
import urllib.error
import urllib.request


TABLE_FENCE_LIMIT = 1650
TABLE_SEPARATOR_CELL = re.compile(r"^:?-{3,}:?$")


def units(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2


def _plain_chunks(text: str, limit: int) -> list[str]:
    """Split plain Markdown while preserving every source byte."""
    out: list[str] = []
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
    return out


def _markdown_segments(text: str) -> list[tuple[bool, str]]:
    """Return (is_fenced, text) segments without changing their bytes."""
    segments: list[tuple[bool, str]] = []
    plain: list[str] = []
    fenced: list[str] = []
    fence_marker: str | None = None

    for line in text.splitlines(keepends=True):
        stripped = line.lstrip()
        marker = "```" if stripped.startswith("```") else "~~~" if stripped.startswith("~~~") else None
        if fence_marker is None and marker:
            if plain:
                segments.append((False, "".join(plain)))
                plain = []
            fence_marker = marker
            fenced = [line]
        elif fence_marker is not None:
            fenced.append(line)
            if stripped.startswith(fence_marker):
                segments.append((True, "".join(fenced)))
                fenced = []
                fence_marker = None
        else:
            plain.append(line)

    if fenced:
        segments.append((True, "".join(fenced)))
    if plain:
        segments.append((False, "".join(plain)))
    return segments


def chunks(text: str, limit: int = 1900) -> list[str]:
    """Split Discord content without cutting a valid fenced code block."""
    if not text.strip():
        raise ValueError("Empty Markdown")

    atoms: list[str] = []
    for is_fenced, segment in _markdown_segments(text):
        if is_fenced:
            if units(segment) > limit:
                raise ValueError("Fenced code block exceeds Discord chunk limit")
            atoms.append(segment)
        else:
            atoms.extend(_plain_chunks(segment, limit))

    out: list[str] = []
    current = ""
    for atom in atoms:
        if units(current + atom) <= limit:
            current += atom
            continue
        if current:
            out.append(current)
        current = atom
    if current:
        out.append(current)

    assert "".join(out) == text
    assert all(units(part) <= limit for part in out)
    return out


def _table_cells(line: str) -> list[str]:
    """Parse GFM cells, retaining escaped literal pipes."""
    row = line.strip()
    if row.startswith("|"):
        row = row[1:]
    if row.endswith("|") and not row.endswith(r"\|"):
        row = row[:-1]
    return [value.strip().replace(r"\|", "|") for value in re.split(r"(?<!\\)\|", row)]


def _is_table_separator(line: str) -> bool:
    cells = _table_cells(line)
    return len(cells) >= 2 and all(TABLE_SEPARATOR_CELL.fullmatch(cell) for cell in cells)


def _display_width(text: str) -> int:
    return sum(2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in text)


def _number_like(value: str) -> bool:
    cleaned = value.strip()
    if cleaned.lower() in {"na", "n/a", "—", "–", "-"}:
        return True
    return bool(re.fullmatch(
        r"(?:약\s*|[~≈]\s*)?[+-]?\s*[$€£₩]?\s*\d[\d,]*(?:\.\d+)?\s*(?:%|bp|bps|억|만|조|달러|원)?",
        cleaned, flags=re.IGNORECASE
    ))


def _compact_numeric_table(lines: list[str], max_columns: int = 36) -> list[str] | None:
    """Use an aligned table only when it fits a narrow mobile screen."""
    header = _table_cells(lines[0])
    records = [_table_cells(line) for line in lines[2:]]
    if not records or not 2 <= len(header) <= 3:
        return None
    if any(len(row) != len(header) for row in records):
        return None
    all_cells = [cell for row in [header, *records] for cell in row]
    if any("**" in cell or "`" in cell or "](" in cell for cell in all_cells):
        return None
    measures = [cell for row in records for cell in row[1:]]
    if sum(_number_like(value) for value in measures) / len(measures) < 0.8:
        return None
    widths = [max(_display_width(row[col]) for row in [header, *records])
              for col in range(len(header))]
    if sum(widths) + 2 * (len(widths) - 1) > max_columns:
        return None

    def format_row(values: list[str]) -> str:
        cells = []
        for col, value in enumerate(values):
            padding = " " * (widths[col] - _display_width(value))
            cells.append((padding + value) if col else (value + padding))
        return "  ".join(cells).rstrip()

    rule = "  ".join("─" * width for width in widths)
    return [format_row(header), rule, *(format_row(record) for record in records)]


def _fenced_table_blocks(lines: list[str], limit: int) -> list[str]:
    """Split aligned numeric tables into complete code blocks with headers."""
    numeric = _compact_numeric_table(lines)
    if numeric is None:
        raise ValueError("Not a compact numeric table")
    header = numeric[:2]
    groups: list[list[str]] = []
    current = list(header)
    for row in numeric[2:]:
        candidate = current + [row]
        block = "```text\n" + "\n".join(candidate) + "\n```"
        if units(block) <= limit:
            current = candidate
            continue
        if len(current) == len(header):
            raise ValueError("Markdown table row exceeds Discord code-block limit")
        groups.append(current)
        current = list(header) + [row]
        if units("```text\n" + "\n".join(current) + "\n```") > limit:
            raise ValueError("Markdown table row exceeds Discord code-block limit")
    groups.append(current)
    return ["```text\n" + "\n".join(group) + "\n```" for group in groups]


def _vertical_table_rows(lines: list[str]) -> list[str]:
    """Use individual labeled Markdown entries for wide/descriptive tables."""
    labels = _table_cells(lines[0])
    data = [_table_cells(row) for row in lines[2:]]
    if not data or any(len(row) != len(labels) for row in data):
        return list(lines)
    output: list[str] = []
    for row in data:
        output.append(f"**{row[0]}**")
        for key, value in zip(labels[1:], row[1:]):
            output.append(f"- **{key}:** {value}")
        output.append("")
    return output


def render_for_discord(markdown: str, table_limit: int = TABLE_FENCE_LIMIT) -> str:
    """Adaptive mobile table renderer; preserve original source for hashing."""
    lines = markdown.splitlines()
    output: list[str] = []
    in_fence = False
    fence_marker: str | None = None
    i = 0
    while i < len(lines):
        stripped = lines[i].lstrip()
        marker = "```" if stripped.startswith("```") else "~~~" if stripped.startswith("~~~") else None
        if marker:
            output.append(lines[i])
            if not in_fence:
                in_fence, fence_marker = True, marker
            elif marker == fence_marker:
                in_fence, fence_marker = False, None
            i += 1
            continue
        if (
            not in_fence
            and i + 1 < len(lines)
            and "|" in lines[i]
            and _is_table_separator(lines[i + 1])
            and len(_table_cells(lines[i])) == len(_table_cells(lines[i + 1]))
        ):
            end = i + 2
            while end < len(lines) and lines[end].strip() and "|" in lines[end]:
                end += 1
            table = lines[i:end]
            if _compact_numeric_table(table) is not None:
                for block in _fenced_table_blocks(table, table_limit):
                    output.extend((block, ""))
            else:
                output.extend(_vertical_table_rows(table))
            i = end
            continue
        output.append(lines[i])
        i += 1
    rendered = "\n".join(output)
    if markdown.endswith("\n") and not rendered.endswith("\n"):
        rendered += "\n"
    return rendered


def atomic(path: pathlib.Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        json.dump(obj, handle, ensure_ascii=False, indent=2)
        handle.flush()
        os.fsync(handle.fileno())
        temporary = handle.name
    os.replace(temporary, path)


def validate_existing_record(
    record: dict[str, object], source_digest: str, rendered_digest: str, total: int
) -> str:
    """Validate whether a durable record can be skipped or safely resumed."""
    if record.get("sha256") != source_digest:
        raise RuntimeError("Changed article: explicit revision approval required")
    status = record.get("status")
    if status == "complete":
        return "complete"
    if status == "uncertain":
        raise RuntimeError("Uncertain previous delivery; manual reconciliation required")
    if status != "pending":
        raise RuntimeError("Invalid previous delivery state; manual reconciliation required")
    if record.get("rendered_sha256") != rendered_digest or record.get("total") != total:
        raise RuntimeError(
            "Rendered content changed during pending delivery; manual reconciliation required"
        )
    return "pending"


def send(url: str, content: str) -> str:
    if not url.startswith("https://discord.com/api/webhooks/") and not url.startswith(
        "https://discordapp.com/api/webhooks/"
    ):
        raise ValueError("Invalid Discord webhook URL")
    separator = "&" if "?" in url else "?"
    endpoint = url + separator + "wait=true"
    payload = json.dumps(
        {"content": content, "allowed_mentions": {"parse": []}}
    ).encode()
    for _attempt in range(5):
        request = urllib.request.Request(
            endpoint,
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json", "User-Agent": "discord-feed/1.0"},
        )
        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                result = json.load(response)
            if not result.get("id"):
                raise RuntimeError("Ambiguous success: missing Discord message ID")
            return str(result["id"])
        except urllib.error.HTTPError as error:
            if error.code == 429:
                try:
                    retry = float(json.loads(error.read()).get("retry_after", 2))
                except (ValueError, TypeError):
                    retry = 2
                time.sleep(min(max(retry, 1), 30))
                continue
            if error.code in (500, 502, 503, 504):
                raise RuntimeError(
                    "Uncertain delivery: server error; reconcile before retry"
                ) from error
            raise RuntimeError("Permanent Discord HTTP error " + str(error.code)) from error
        except (urllib.error.URLError, TimeoutError) as error:
            raise RuntimeError(
                "Uncertain delivery: network failure; reconcile before retry"
            ) from error
    raise RuntimeError("Discord rate limit retry budget exhausted")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    parser.add_argument("--id", required=True)
    parser.add_argument("--state", required=True)
    parser.add_argument(
        "--webhook-env",
        choices=(
            "DISCORD_WEBHOOK_URL",
            "DISCORD_WEBHOOK_URL_FINANCE",
            "DISCORD_WEBHOOK_URL_GENERAL",
        ),
        default="DISCORD_WEBHOOK_URL",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    source_text = pathlib.Path(args.file).read_text(encoding="utf-8")
    rendered_text = render_for_discord(source_text)
    parts = chunks(rendered_text)
    digest = hashlib.sha256(source_text.encode()).hexdigest()
    rendered_digest = hashlib.sha256(rendered_text.encode()).hexdigest()
    if args.dry_run:
        print(
            json.dumps(
                {
                    "id": args.id,
                    "sha256": digest,
                    "rendered_sha256": rendered_digest,
                    "chunks": len(parts),
                    "utf16_units": [units(part) for part in parts],
                }
            )
        )
        return

    url = os.environ.get(args.webhook_env)
    if not url:
        raise RuntimeError("Missing " + args.webhook_env)
    state_path = pathlib.Path(args.state)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    with open(str(state_path) + ".lock", "a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = json.loads(state_path.read_text()) if state_path.exists() else {}
        record = state.get(args.id)
        if record:
            if not isinstance(record, dict):
                raise RuntimeError("Invalid previous delivery record")
            status = validate_existing_record(
                record, digest, rendered_digest, len(parts)
            )
            if status == "complete":
                print("Already delivered")
                return
        else:
            record = {
                "sha256": digest,
                "rendered_sha256": rendered_digest,
                "status": "pending",
                "messages": [],
                "total": len(parts),
            }
            state[args.id] = record
            atomic(state_path, state)
        for index in range(len(record["messages"]), len(parts)):
            try:
                message_id = send(url, parts[index])
            except Exception:
                record["status"] = "uncertain"
                atomic(state_path, state)
                raise
            record["messages"].append({"index": index, "message_id": message_id})
            atomic(state_path, state)
        record["status"] = "complete"
        atomic(state_path, state)
        print("Delivered", len(parts), "messages")


if __name__ == "__main__":
    main()
