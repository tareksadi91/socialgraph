"""X archive (ZIP) → RawContact ingest.

X data exports are ZIPs containing data/*.js files with JS wrappers around
JSON payloads. This importer:

  1. Validates that following.js and follower.js are present.
  2. Strips the `window.YTD.<var>.partN = ` wrapper.
  3. Extracts handle from userLink (twitter.com or x.com).
  4. Emits one RawContact per follower/following entry.
  5. Selectively ignores tweets.js, direct-messages.js, etc. (privacy + scope).
"""

from __future__ import annotations

import json
import re
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from socialgraph.schema.raw_contact import RawContact


class XArchiveError(Exception):
    """Raised when X archive ZIP is missing required files or malformed."""


_REQUIRED_FILES = {"data/following.js", "data/follower.js"}
_HANDLE_RE = re.compile(r"(?:twitter|x)\.com/([A-Za-z0-9_]+)")


def _strip_js_wrapper(text: str) -> Any:
    # X archive .js files: `window.YTD.{var}.partN = <JSON>`
    eq_idx = text.find("=")
    if eq_idx == -1:
        raise XArchiveError("JS wrapper missing '='")
    payload = text[eq_idx + 1 :].strip()
    return json.loads(payload)


def _handle_from_user_link(link: str) -> str | None:
    m = _HANDLE_RE.search(link or "")
    return m.group(1) if m else None


def import_x_archive(src: Path, dst: Path, run_id: str) -> list[RawContact]:
    """Parse X archive ZIP → list[RawContact] + write JSONL to dst."""
    if not src.is_file():
        raise XArchiveError(f"file not found: {src}")
    with zipfile.ZipFile(src, "r") as z:
        names = set(z.namelist())
        missing = _REQUIRED_FILES - names
        if missing:
            raise XArchiveError(f"X archive missing required file(s): {sorted(missing)}")
        following_raw = z.read("data/following.js").decode("utf-8", errors="replace")
        follower_raw = z.read("data/follower.js").decode("utf-8", errors="replace")

    following = _strip_js_wrapper(following_raw)
    follower = _strip_js_wrapper(follower_raw)

    contacts: list[RawContact] = []
    now = datetime.now(UTC)

    def _emit(entries: Any, key: str, direction: str) -> None:
        for entry in entries:
            inner = entry.get(key, {})
            account_id = str(inner.get("accountId", "")).strip()
            user_link = inner.get("userLink", "")
            handle = _handle_from_user_link(user_link)
            if not handle and not account_id:
                continue
            slug = handle or account_id
            profile_url = user_link or f"https://x.com/{slug}"
            contacts.append(
                RawContact(
                    raw_id=f"{run_id}#{slug}",
                    platform="x",
                    source="import",
                    platform_native_id=slug,
                    profile_url=profile_url,
                    observed_at=now,
                    run_id=run_id,
                    full_name=handle or slug,
                    handle=handle,
                    follow_direction=direction,  # type: ignore[arg-type]
                )
            )

    _emit(following, "following", "following")
    _emit(follower, "follower", "follower")

    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open("w", encoding="utf-8") as out:
        for c in contacts:
            out.write(c.to_jsonl_line() + "\n")
    return contacts
