"""Name normalization and similarity scoring for cross-platform identity matching.

Uses stdlib difflib (no new dependencies). normalize_name() converts both
"Alice Example" and "alice_example" to "aliceexample" for comparison.
name_similarity() returns [0.0, 1.0] using SequenceMatcher ratio.
"""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher


def normalize_name(name: str) -> str:
    """Normalize a display name or handle for cross-platform comparison.

    - Removes accents (François → francois)
    - Lowercases
    - Strips trailing digits (handles often end in year: tareksadi91 → tareksadi)
    - Keeps only lowercase ASCII letters
    """
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    name = name.lower()
    name = re.sub(r"\d+$", "", name)
    name = re.sub(r"[^a-z]", "", name)
    return name


def name_similarity(a: str, b: str) -> float:
    """Return similarity between two display names/handles in [0.0, 1.0].

    Both inputs are normalized before comparison. Returns 1.0 when they are
    identical after normalization (e.g. "Alice Example" vs "alice_example").
    """
    na = normalize_name(a)
    nb = normalize_name(b)
    if not na or not nb:
        return 0.0
    return SequenceMatcher(None, na, nb).ratio()
