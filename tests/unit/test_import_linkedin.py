from pathlib import Path

import pytest

from socialgraph.ingest.import_linkedin import LinkedInImportError, import_linkedin_csv

FIXTURES = Path(__file__).parents[1] / "fixtures" / "linkedin"


def test_imports_canonical_csv(tmp_path: Path):
    out = tmp_path / "out.jsonl"
    contacts = import_linkedin_csv(FIXTURES / "connections_small.csv", out, run_id="r1")
    assert len(contacts) == 3
    alice = contacts[0]
    assert alice.full_name == "Alice Example"
    assert alice.first_name == "Alice"
    assert alice.last_name == "Example"
    assert alice.email == "alice@example.com"
    assert alice.current_company == "Acme Co"
    assert alice.current_title == "Founder"
    assert alice.profile_url == "https://www.linkedin.com/in/alice-example"
    assert alice.platform == "linkedin"
    assert alice.source == "import"
    assert alice.run_id == "r1"
    assert alice.connected_on is not None
    assert alice.connected_on.year == 2024


def test_writes_jsonl_one_record_per_line(tmp_path: Path):
    out = tmp_path / "out.jsonl"
    contacts = import_linkedin_csv(FIXTURES / "connections_small.csv", out, run_id="r1")
    lines = out.read_text().splitlines()
    assert len(lines) == len(contacts)


def test_locale_french(tmp_path: Path):
    out = tmp_path / "out.jsonl"
    contacts = import_linkedin_csv(FIXTURES / "connections_locale_fr.csv", out, run_id="rfr")
    assert len(contacts) == 1
    pierre = contacts[0]
    assert pierre.full_name == "Pierre Martin"
    assert pierre.current_company == "Société Générale"
    assert pierre.current_title == "Ingénieur"


def test_unicode_names_preserved(tmp_path: Path):
    out = tmp_path / "out.jsonl"
    contacts = import_linkedin_csv(FIXTURES / "connections_unicode.csv", out, run_id="ru")
    assert len(contacts) == 3
    assert contacts[0].first_name == "محمد"
    assert contacts[1].first_name == "李"
    assert contacts[2].first_name == "François"


def test_missing_email_is_none(tmp_path: Path):
    out = tmp_path / "out.jsonl"
    contacts = import_linkedin_csv(FIXTURES / "connections_small.csv", out, run_id="r")
    bob = next(c for c in contacts if c.first_name == "Bob")
    assert bob.email is None


def test_missing_file_raises():
    with pytest.raises(LinkedInImportError):
        import_linkedin_csv(Path("/nonexistent.csv"), Path("/tmp/x.jsonl"), run_id="r")
