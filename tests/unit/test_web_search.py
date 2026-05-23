from unittest.mock import MagicMock, patch

from socialgraph.port.web_search import (
    FakeGoogleCSEClient,
    GoogleCSEClient,
    _parse_handles_from_cse_response,
)


def test_fake_returns_seeded_results():
    fake = FakeGoogleCSEClient(
        responses={'"Alice Example" "Acme Co" site:x.com': ["alice_example"]},
    )
    result = fake.discover("Alice Example", "Acme Co", "https://linkedin.com/in/alice")
    assert len(result.candidates) == 1
    assert result.candidates[0].handle == "alice_example"
    assert result.candidates[0].source == "google_cse"


def test_fake_returns_empty_for_unknown():
    fake = FakeGoogleCSEClient(responses={})
    result = fake.discover("Unknown Person", None, "https://linkedin.com/in/unknown")
    assert result.handle is None
    assert result.candidates == []


def test_parse_handles_from_cse_response():
    response = {
        "items": [
            {"link": "https://x.com/alice_example", "title": "Alice Example (@alice_example)"},
            {"link": "https://twitter.com/bob_sample", "title": "Bob Sample"},
            {"link": "https://x.com/i/user/12345", "title": "reserved"},  # should skip
        ]
    }
    handles = _parse_handles_from_cse_response(response)
    assert handles == ["alice_example", "bob_sample"]


def test_google_cse_client_builds_correct_query():
    client = GoogleCSEClient(api_key="test_key", cse_id="test_cx")
    with patch("httpx.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: {"items": []})
        client.discover("Alice Example", "Acme Co", "https://linkedin.com/in/alice")
        assert mock_get.called
        url, kwargs = mock_get.call_args[0][0], mock_get.call_args[1]
        assert "alice" in url.lower() or "Alice" in kwargs.get("params", {}).get("q", "")


def test_google_cse_returns_no_results_on_api_error():
    client = GoogleCSEClient(api_key="bad_key", cse_id="cx")
    with patch("httpx.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=403, json=lambda: {"error": "forbidden"})
        result = client.discover("Alice", None, "https://linkedin.com/in/alice")
    assert result.handle is None
    assert result.candidates == []
