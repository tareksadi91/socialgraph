from socialgraph.port.scoring import XSearchResult, score_candidate


def test_strong_name_match_boosts_score():
    result = XSearchResult(handle="holger_seim", display_name="Holger Seim", bio_preview="")
    score, _ = score_candidate(
        linkedin_name="Holger Seim",
        linkedin_company=None,
        x_result=result,
    )
    assert score >= 0.55  # 0.6 * ~1.0 from name


def test_company_match_boosts_score():
    result = XSearchResult(
        handle="holger_seim", display_name="Holger Seim", bio_preview="CEO @ Blinkist | books"
    )
    score, rationale = score_candidate(
        linkedin_name="Holger Seim",
        linkedin_company="Blinkist",
        x_result=result,
    )
    assert "bio_company_match" in rationale
    assert score > 0.85


def test_linkedin_cross_link_in_bio():
    result = XSearchResult(
        handle="holger_seim",
        display_name="Holger Seim",
        bio_preview="More on linkedin.com/in/holger-seim",
    )
    _, rationale = score_candidate(
        linkedin_name="Holger Seim",
        linkedin_company=None,
        x_result=result,
    )
    assert "bio_linkedin_link" in rationale


def test_unrelated_name_low_score():
    result = XSearchResult(handle="xyz_user", display_name="Some Other Person", bio_preview="")
    score, _ = score_candidate(
        linkedin_name="Holger Seim",
        linkedin_company=None,
        x_result=result,
    )
    assert score < 0.4


def test_score_capped_at_one():
    result = XSearchResult(
        handle="holger_seim",
        display_name="Holger Seim",
        bio_preview="CEO @ Blinkist linkedin.com/in/holger-seim",
    )
    score, _ = score_candidate(
        linkedin_name="Holger Seim",
        linkedin_company="Blinkist",
        x_result=result,
    )
    assert 0.0 <= score <= 1.0
