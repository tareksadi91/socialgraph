from unittest.mock import MagicMock, patch

from socialgraph.port.enrichment import ApolloClient, FakeApolloClient


def test_fake_returns_seeded_handle():
    fake = FakeApolloClient(
        responses={"Alice Example|Acme Co": "alice_example"},
    )
    result = fake.discover("Alice Example", "Acme Co", "https://linkedin.com/in/alice")
    assert len(result.candidates) == 1
    assert result.candidates[0].handle == "alice_example"
    assert result.candidates[0].source == "apollo"


def test_fake_returns_empty_for_unknown():
    fake = FakeApolloClient(responses={})
    result = fake.discover("Unknown", None, "https://linkedin.com/in/unknown")
    assert result.handle is None
    assert result.candidates == []


def test_apollo_client_parses_twitter_url():
    client = ApolloClient(api_key="test_key")
    with patch("httpx.post") as mock_post:
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"person": {"twitter_url": "https://twitter.com/alice_example"}},
        )
        result = client.discover("Alice Example", "Acme", "https://linkedin.com/in/alice")
    assert len(result.candidates) == 1
    assert result.candidates[0].handle == "alice_example"
    assert result.candidates[0].source == "apollo"


def test_apollo_client_returns_empty_on_no_twitter_url():
    client = ApolloClient(api_key="test_key")
    with patch("httpx.post") as mock_post:
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"person": {"twitter_url": None}},
        )
        result = client.discover("Alice", None, "https://linkedin.com/in/alice")
    assert result.candidates == []


def test_apollo_client_returns_empty_on_api_error():
    client = ApolloClient(api_key="bad_key")
    with patch("httpx.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=401, json=lambda: {"error": "unauthorized"})
        result = client.discover("Alice", None, "https://linkedin.com/in/alice")
    assert result.candidates == []
