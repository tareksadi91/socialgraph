import json

import pytest
from pydantic import ValidationError

from socialgraph.schema.raw_contact import RawContact


def _minimal_kwargs(**over) -> dict:
    base = {
        "raw_id": "r#abc",
        "platform": "linkedin",
        "source": "import",
        "platform_native_id": "abc",
        "profile_url": "https://linkedin.com/in/abc",
        "observed_at": "2026-05-23T10:00:00+00:00",
        "run_id": "r123",
        "full_name": "Alice Example",
    }
    base.update(over)
    return base


def test_minimal_record_valid():
    rc = RawContact(**_minimal_kwargs())
    assert rc.schema_version == 1
    assert rc.platform == "linkedin"
    assert rc.email is None


def test_invalid_platform_rejected():
    with pytest.raises(ValidationError):
        RawContact(**_minimal_kwargs(platform="myspace"))


def test_invalid_source_rejected():
    with pytest.raises(ValidationError):
        RawContact(**_minimal_kwargs(source="invented"))


def test_to_jsonl_round_trip():
    rc = RawContact(**_minimal_kwargs(email="a@b.com"))
    s = rc.to_jsonl_line()
    parsed = json.loads(s)
    assert parsed["email"] == "a@b.com"
    rc2 = RawContact.from_jsonl_line(s)
    assert rc2 == rc


def test_observation_default_topics_empty():
    rc = RawContact(**_minimal_kwargs())
    assert rc.topics == []
    assert rc.mutual_names_sample == []
