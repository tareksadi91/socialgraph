"""Score an X search result against a LinkedIn person.

Pure function — same input always produces same output. The scoring weights:

  0.6 * name_similarity
  + 0.3 if LinkedIn company appears in X bio
  + 0.1 if X bio contains a linkedin.com/in/ URL

Clamped to [0.0, 1.0]. Rationale string lists which signals fired.
"""

from __future__ import annotations

from dataclasses import dataclass

from socialgraph.identity.fuzzy import name_similarity


@dataclass
class XSearchResult:
    """One result from X's user search."""

    handle: str
    display_name: str
    bio_preview: str


def score_candidate(
    linkedin_name: str,
    linkedin_company: str | None,
    x_result: XSearchResult,
) -> tuple[float, str]:
    """Return (score, rationale) for a candidate match."""
    parts: list[str] = []

    name_sim = name_similarity(linkedin_name, x_result.display_name)
    score = 0.6 * name_sim
    parts.append(f"name={name_sim:.2f}")

    bio = x_result.bio_preview or ""
    bio_lower = bio.lower()

    if linkedin_company and linkedin_company.lower() in bio_lower:
        score += 0.3
        parts.append("bio_company_match")

    if "linkedin.com/in/" in bio_lower:
        score += 0.1
        parts.append("bio_linkedin_link")

    score = min(max(score, 0.0), 1.0)
    return score, ",".join(parts)
