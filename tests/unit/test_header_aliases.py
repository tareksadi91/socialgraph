import pytest

from socialgraph.ingest.header_aliases import (
    UnknownHeaderError,
    normalize_linkedin_headers,
)


def test_normalize_canonical_english():
    headers = ["First Name", "Last Name", "URL", "Email Address", "Company", "Position", "Connected On"]
    result = normalize_linkedin_headers(headers)
    assert result == ["first_name", "last_name", "profile_url", "email", "company", "title", "connected_on"]


def test_normalize_lowercase():
    headers = ["first name", "last name", "url", "email address", "company", "position", "connected on"]
    result = normalize_linkedin_headers(headers)
    assert result == ["first_name", "last_name", "profile_url", "email", "company", "title", "connected_on"]


def test_normalize_french_locale():
    headers = ["Prénom", "Nom", "URL", "Adresse e-mail", "Entreprise", "Poste", "Date de connexion"]
    result = normalize_linkedin_headers(headers)
    assert result == ["first_name", "last_name", "profile_url", "email", "company", "title", "connected_on"]


def test_normalize_unknown_header_raises():
    headers = ["First Name", "Last Name", "MysteryColumn"]
    with pytest.raises(UnknownHeaderError, match="MysteryColumn"):
        normalize_linkedin_headers(headers, strict=True)


def test_normalize_unknown_header_passes_through_non_strict():
    headers = ["First Name", "MysteryColumn"]
    result = normalize_linkedin_headers(headers, strict=False)
    assert result == ["first_name", "MysteryColumn"]
