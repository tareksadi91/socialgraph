"""RawContact — canonical per-person record produced by ingest pipeline.

Each ingest run (import or scrape) writes one RawContact per person observed.
Provenance (platform, source, run_id, observed_at, raw_blob_path) is recorded
on every record so any attribute can be traced back to its raw source.

Schema is versioned via `schema_version` field. Migrations apply on read,
not on disk (snapshots remain immutable).
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Platform = Literal["linkedin", "x"]
Source = Literal["import", "scrape"]
FollowDirection = Literal["following", "follower", "mutual"]


class RawContact(BaseModel):
    """One observation of one person, sourced from one platform via one path.

    Identity fields (raw_id, platform, platform_native_id) uniquely identify
    the observation. Person-level fields capture what was visible at observed_at.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1

    raw_id: str
    platform: Platform
    source: Source
    platform_native_id: str
    profile_url: str
    observed_at: datetime
    run_id: str

    full_name: str
    first_name: str | None = None
    last_name: str | None = None
    display_name: str | None = None
    handle: str | None = None
    email: str | None = None
    verified: bool | None = None

    headline: str | None = None
    bio: str | None = None
    location_raw: str | None = None
    location_city: str | None = None
    location_country: str | None = None
    photo_url: str | None = None
    language: str | None = None

    current_company: str | None = None
    current_company_url: str | None = None
    current_title: str | None = None
    industry: str | None = None

    connected_on: datetime | None = None
    follow_direction: FollowDirection | None = None
    mutual_count: int | None = None
    mutual_names_sample: list[str] = Field(default_factory=list)

    follower_count: int | None = None
    following_count: int | None = None

    topics: list[str] = Field(default_factory=list)
    seniority: str | None = None
    function: str | None = None

    raw_blob_path: str | None = None

    def to_jsonl_line(self) -> str:
        """Serialize to a single JSON line (no trailing newline)."""
        return self.model_dump_json(exclude_none=False)

    @classmethod
    def from_jsonl_line(cls, line: str) -> "RawContact":
        """Deserialize from a single JSON line."""
        return cls.model_validate(json.loads(line))
