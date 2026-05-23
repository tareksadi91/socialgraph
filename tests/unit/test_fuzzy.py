from socialgraph.identity.fuzzy import name_similarity, normalize_name


def test_normalize_removes_non_alpha():
    assert normalize_name("alice_example") == "aliceexample"
    assert normalize_name("Alice Example") == "aliceexample"


def test_normalize_strips_accents():
    assert normalize_name("François") == "francois"


def test_normalize_strips_digits():
    assert normalize_name("tareksadi91") == "tareksadi"


def test_similarity_exact_after_normalize():
    # "Alice Example" vs "alice_example" — both normalize to "aliceexample"
    score = name_similarity("Alice Example", "alice_example")
    assert score >= 0.99


def test_similarity_partial_match():
    score = name_similarity("Bob Sample", "bob_s")
    assert score < 0.85  # too short to be a confident match


def test_similarity_different_names():
    score = name_similarity("Carol Test", "zoran_xyz")
    assert score < 0.5
