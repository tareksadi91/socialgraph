"""Contract tests for FakeXSearchClient (used by integration tests)."""

from socialgraph.port.x_search import FakeXSearchClient, XSearchResult


def test_fake_returns_seeded_results():
    fake = FakeXSearchClient(
        responses={
            '"Holger Seim" Blinkist': [
                XSearchResult(
                    handle="holger_seim",
                    display_name="Holger Seim",
                    bio_preview="CEO @ Blinkist",
                ),
            ],
        },
    )
    results = fake.search('"Holger Seim" Blinkist')
    assert len(results) == 1
    assert results[0].handle == "holger_seim"


def test_fake_returns_empty_for_unknown_query():
    fake = FakeXSearchClient(responses={})
    assert fake.search("anything") == []


def test_fake_records_queries():
    fake = FakeXSearchClient(responses={})
    fake.search("query one")
    fake.search("query two")
    assert fake.queries == ["query one", "query two"]
