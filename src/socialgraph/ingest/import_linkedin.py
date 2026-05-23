"""LinkedIn Connections.csv → RawContact ingest.

The official LinkedIn data export is a CSV with a header row that may be
preceded by a free-form notes preamble (sometimes containing an orphan
double-quote that would confuse a naive csv.reader by opening a multi-line
quoted field). Locale variants change column names but keep order. This
module:

  1. Detects encoding (UTF-8 with optional BOM).
  2. Reads the file as lines and seeks past the notes preamble by scanning
     for the real header row.
  3. Normalizes headers via header_aliases.
  4. Emits one RawContact per row (source="import", platform="linkedin").
  5. Writes JSONL to the destination path.
"""

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime
from pathlib import Path

import chardet
from dateutil import parser as dateparser

from socialgraph.ingest.header_aliases import normalize_linkedin_headers
from socialgraph.schema.raw_contact import RawContact


class LinkedInImportError(Exception):
    """Raised when the LinkedIn CSV cannot be located, decoded, or parsed."""


HEADER_SENTINEL_TOKENS = {"first_name", "last_name", "profile_url"}


def _detect_encoding(path: Path) -> str:
    blob = path.read_bytes()[:4096]
    if blob.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    guess = chardet.detect(blob).get("encoding") or "utf-8"
    return guess


def _slug_from_url(url: str) -> str:
    return url.rstrip("/").rsplit("/", 1)[-1]


def _parse_connected_on(value: str) -> datetime | None:
    value = value.strip()
    if not value:
        return None
    try:
        return dateparser.parse(value).astimezone(UTC)
    except (ValueError, TypeError):
        return None


def _looks_like_header(line: str) -> bool:
    """True if a single CSV line normalizes to canonical LinkedIn headers."""
    try:
        first_row = next(csv.reader(io.StringIO(line)))
    except StopIteration:
        return False
    normalized = normalize_linkedin_headers(first_row, strict=False)
    return bool(HEADER_SENTINEL_TOKENS & set(normalized))


def _seek_header_and_body(text: str) -> tuple[list[str], str]:
    """Scan lines for the header row; return (headers, remaining_csv_body).

    Skips any free-form notes preamble (including orphan quote characters
    that would otherwise break csv.reader by opening a multi-line quoted
    field).
    """
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if _looks_like_header(line):
            header_row = next(csv.reader(io.StringIO(line)))
            headers = normalize_linkedin_headers(header_row, strict=False)
            body = "".join(lines[i + 1 :])
            return headers, body
    raise LinkedInImportError("could not locate a header row containing First Name/Last Name/URL")


def import_linkedin_csv(src: Path, dst: Path, run_id: str) -> list[RawContact]:
    """Parse LinkedIn Connections.csv → list[RawContact] + write JSONL to dst."""
    if not src.is_file():
        raise LinkedInImportError(f"file not found: {src}")
    encoding = _detect_encoding(src)
    contacts: list[RawContact] = []
    now = datetime.now(UTC)

    text = src.read_text(encoding=encoding)
    headers, body = _seek_header_and_body(text)

    reader = csv.reader(io.StringIO(body))
    for row in reader:
        if not any(cell.strip() for cell in row):
            continue
        record = {h: (row[i] if i < len(row) else "") for i, h in enumerate(headers)}
        first = record.get("first_name", "").strip()
        last = record.get("last_name", "").strip()
        url = record.get("profile_url", "").strip()
        if not first and not last and not url:
            continue
        full_name = (first + " " + last).strip() or url
        slug = _slug_from_url(url) if url else f"unknown-{len(contacts)}"
        contacts.append(
            RawContact(
                raw_id=f"{run_id}#{slug}",
                platform="linkedin",
                source="import",
                platform_native_id=slug,
                profile_url=url or f"https://www.linkedin.com/in/{slug}",
                observed_at=now,
                run_id=run_id,
                full_name=full_name,
                first_name=first or None,
                last_name=last or None,
                email=(record.get("email", "").strip() or None),
                current_company=(record.get("company", "").strip() or None),
                current_title=(record.get("title", "").strip() or None),
                connected_on=_parse_connected_on(record.get("connected_on", "")),
            )
        )

    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open("w", encoding="utf-8") as out:
        for c in contacts:
            out.write(c.to_jsonl_line() + "\n")
    return contacts
