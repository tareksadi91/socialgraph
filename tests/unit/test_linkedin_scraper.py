from unittest.mock import MagicMock, patch

from socialgraph.port.linkedin_scraper import LinkedInContactInfoClient


def _make_client(tmp_path) -> LinkedInContactInfoClient:
    return LinkedInContactInfoClient(profile_dir=tmp_path / "profiles" / "linkedin")


def test_discovers_twitter_link_in_contact_info(tmp_path):
    client = _make_client(tmp_path)
    mock_page = MagicMock()
    mock_page.query_selector_all.return_value = [
        MagicMock(**{"get_attribute.return_value": "https://twitter.com/holger_seim"}),
    ]
    with patch.object(client, "_get_page", return_value=mock_page):
        result = client.discover(
            name="Holger Seim",
            company="Blinkist",
            profile_url="https://www.linkedin.com/in/holger-seim",
        )
    assert result.handle == "holger_seim"
    assert result.confidence == 1.0
    assert result.source == "li_contact_info"


def test_discovers_x_com_link(tmp_path):
    client = _make_client(tmp_path)
    mock_page = MagicMock()
    mock_page.query_selector_all.return_value = [
        MagicMock(**{"get_attribute.return_value": "https://x.com/alice_example"}),
    ]
    with patch.object(client, "_get_page", return_value=mock_page):
        result = client.discover("Alice", None, "https://www.linkedin.com/in/alice")
    assert result.handle == "alice_example"
    assert result.source == "li_contact_info"


def test_returns_no_handle_when_no_link(tmp_path):
    client = _make_client(tmp_path)
    mock_page = MagicMock()
    mock_page.query_selector_all.return_value = []
    with patch.object(client, "_get_page", return_value=mock_page):
        result = client.discover("Alice", None, "https://www.linkedin.com/in/alice")
    assert result.handle is None
    assert result.candidates == []


def test_handles_page_error_gracefully(tmp_path):
    client = _make_client(tmp_path)
    with patch.object(client, "_get_page", side_effect=Exception("nav failed")):
        result = client.discover("Alice", None, "https://www.linkedin.com/in/alice")
    assert result.handle is None


def test_extracts_handle_from_various_url_formats(tmp_path):
    from socialgraph.port.linkedin_scraper import _extract_handle_from_social_url

    assert _extract_handle_from_social_url("https://twitter.com/alice") == "alice"
    assert _extract_handle_from_social_url("https://x.com/alice_example/") == "alice_example"
    assert _extract_handle_from_social_url("https://x.com/i/user/12345") is None  # reserved path
    assert _extract_handle_from_social_url("https://linkedin.com/in/alice") is None  # wrong domain
