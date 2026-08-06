from app.services.readiness_scorer import calculate_hiring_readiness


def test_calculate_hiring_readiness_perfect_scores():
    result = calculate_hiring_readiness(ats_score=100, match_score=100, skill_score=100, writing_score=100)
    assert result == 100


def test_calculate_hiring_readiness_zero_scores():
    result = calculate_hiring_readiness(ats_score=0, match_score=0, skill_score=0, writing_score=0)
    assert result == 0


def test_calculate_hiring_readiness_weighted_blend():
    result = calculate_hiring_readiness(ats_score=90, match_score=60, skill_score=28, writing_score=100)
    expected = round(90 * 0.25 + 60 * 0.35 + 28 * 0.20 + 100 * 0.20, 2)
    assert result == expected
