import pandas as pd
from commindex import author_feature_score, rao_stirling, gender_disparity, country_disparity_income_group, discipline_disparity, build_prior_graph, novelty_factor, author_commindex_vector, author_commindex_scalar


def test_rao_stirling():
    # All same category -> 0 (no diversity)
    result = rao_stirling(["US", "US", "US"], lambda i, j: 1.0)
    assert abs(result - 0.0) < 1e-9, f"all same: Expected 0.0, got {result}"

    # Two categories, balanced, max disparity -> 0.5
    result = rao_stirling(["US", "US", "CA", "CA"], lambda i, j: 1.0)
    assert abs(result - 0.5) < 1e-9, f"two balanced: Expected 0.5, got {result}"

    # Three categories, balanced, max disparity -> 2/3
    result = rao_stirling(["US", "US", "CA", "CA", "MX", "MX"], lambda i, j: 1.0)
    assert abs(result - 2/3) < 1e-9, f"three balanced: Expected 2/3, got {result}"

    # Two categories, unbalanced -> 0.48
    result = rao_stirling(["US", "US", "US", "CA", "CA"], lambda i, j: 1.0)
    assert abs(result - 0.48) < 1e-9, f"two unbalanced: Expected 0.48, got {result}"

    # Disparity is actually applied (not just ignored)
    result = rao_stirling(["A", "B"], lambda i, j: 0.5)
    assert abs(result - 0.25) < 1e-9, f"disparity applied: Expected 0.25, got {result}"

    print("rao_stirling tests passed")

def test_gender_disparity():
    assert gender_disparity("male", "male") == 0.0
    assert gender_disparity("female", "female") == 0.0
    assert gender_disparity("male", "female") == 1.0
    assert gender_disparity("unknown", "male") == 1.0
    assert gender_disparity("unknown", "unknown") == 0.0

    print("gender_disparity tests passed")

def test_country_disparity():
    
    # Same country -> 0
    assert country_disparity_income_group("US", "US") == 0.0
    
    # Same group, different country -> 0
    assert country_disparity_income_group("US", "DE") == 0.0
    
    # Adjacent groups (HIC vs UMIC) -> 1/3
    assert abs(country_disparity_income_group("US", "CN") - 1/3) < 1e-9
    
    # Extreme groups (HIC vs LIC) -> 1
    assert country_disparity_income_group("US", "UG") == 1.0
    
    # Missing country -> raise
    try:
        country_disparity_income_group("ZZZ", "US")
        assert False, "expected KeyError"
    except KeyError:
        pass

    print("country_disparity tests passed")

def test_discipline_disparity():
    # Same specialization => 0 
    assert discipline_disparity("Cardiology", "Cardiology") == 0.0

    # Same cluster => 0.25 
    assert abs(discipline_disparity("Cardiology", "Clinical Medicine") - 0.25) < 1e-9

    # Related clusters => 0.5
    assert abs(discipline_disparity("Cardiology", "Biostatistics") - 0.5) < 1e-9

    # Different clusters => 1.0
    assert discipline_disparity("Cardiology", "Chemistry") == 1.0

    # Check reverse pairs
    # Order doesn't matter for related clusters
    assert (discipline_disparity("Cardiology", "Biostatistics") ==
        discipline_disparity("Biostatistics", "Cardiology"))

    try: 
        discipline_disparity("Cardiology", "Unknown Specialization")
        assert False, "expected KeyError"
    except KeyError:
        pass
    print("discipline_disparity tests passed")


def test_author_feature_score():
    # Author X is on both papers. P1: all-US (score 0). P2: US+CA (score 0.5 with max disparity).
    # X's author-level score should be (0 + 0.5) / 2 = 0.25
    df = pd.DataFrame({
        "pub_anon_id":     ["P1", "P1", "P2", "P2"],
        "author_anon_id":  ["X",  "Y",  "X",  "Z"],
        "test_feature":    ["US", "US", "US", "CA"],
    })
    score = author_feature_score("X", df, "test_feature", lambda i, j: 1.0)
    assert abs(score - 0.25) < 1e-9, f"expected 0.25, got {score}"

    print("author_feature_score tests passed")

def test_novelty_cold_start():
    """Author on their first paper: all co-authors are new, β = 1 + δ."""
    df = pd.DataFrame({
        "pub_anon_id":    ["P1", "P1", "P1"],
        "author_anon_id": ["X",  "Y",  "Z"],
        "pub_date":       pd.to_datetime(["2025-01-01"] * 3),
    })
    papers_by_author = {aid: set(grp["pub_anon_id"]) for aid, grp in df.groupby("author_anon_id")}
    authors_by_paper = {pid: set(grp["author_anon_id"]) for pid, grp in df.groupby("pub_anon_id")}
    date_by_paper = df.groupby("pub_anon_id")["pub_date"].first().to_dict()
    
    beta = novelty_factor("X", "P1", papers_by_author, authors_by_paper, date_by_paper, delta=0.5)
    # 2 co-authors (Y, Z), both new, β = 1 + 0.5 * (2/2) = 1.5
    assert abs(beta - 1.5) < 1e-9, f"cold start: expected 1.5, got {beta}"


def test_novelty_full_repeat():
    """Author X on two papers with same co-author: second has 0 new."""
    df = pd.DataFrame({
        "pub_anon_id":    ["P1", "P1", "P2", "P2"],
        "author_anon_id": ["X",  "Y",  "X",  "Y"],
        "pub_date":       pd.to_datetime(["2025-01-01", "2025-01-01", "2025-06-01", "2025-06-01"]),
    })
    papers_by_author = {aid: set(grp["pub_anon_id"]) for aid, grp in df.groupby("author_anon_id")}
    authors_by_paper = {pid: set(grp["author_anon_id"]) for pid, grp in df.groupby("pub_anon_id")}
    date_by_paper = df.groupby("pub_anon_id")["pub_date"].first().to_dict()
    
    # For P2: X's prior graph is {Y}, current co-authors {Y}, n_new=0, β=1.0
    beta = novelty_factor("X", "P2", papers_by_author, authors_by_paper, date_by_paper, delta=0.5)
    assert abs(beta - 1.0) < 1e-9, f"full repeat: expected 1.0, got {beta}"

def test_novelty_partial_new():
    """X on P1 with Y; then P2 with Y and Z: Y is repeat, Z is new. β = 1 + 0.5 * (1/2) = 1.25"""
    df = pd.DataFrame({
        "pub_anon_id":    ["P1", "P1", "P2", "P2", "P2"],
        "author_anon_id": ["X",  "Y",  "X",  "Y",  "Z"],
        "pub_date":       pd.to_datetime(["2025-01-01", "2025-01-01", "2025-06-01", "2025-06-01", "2025-06-01"]),
    })
    papers_by_author = {aid: set(grp["pub_anon_id"]) for aid, grp in df.groupby("author_anon_id")}
    authors_by_paper = {pid: set(grp["author_anon_id"]) for pid, grp in df.groupby("pub_anon_id")}
    date_by_paper = df.groupby("pub_anon_id")["pub_date"].first().to_dict()
    
    beta = novelty_factor("X", "P2", papers_by_author, authors_by_paper, date_by_paper, delta=0.5)
    # co-authors on P2: {Y, Z}, n_total=2, prior {Y}, n_new=1, β = 1 + 0.5 * (1/2) = 1.25
    assert abs(beta - 1.25) < 1e-9, f"partial new: expected 1.25, got {beta}"

def test_rao_stirling_weighted_dict():
    # Dict input equivalent to a paper with 3 authors: A=1, B=1, C=1
    result = rao_stirling({"A": 1, "B": 1, "C": 1}, lambda i, j: 1.0)
    assert abs(result - 2/3) < 1e-9

def test_rao_stirling_fractional_weights():
    # One dual-affiliation author (0.5 US + 0.5 LB) plus one full US author
    # Weights: US = 1.5, LB = 0.5, total = 2.0
    # Proportions: p_US = 0.75, p_LB = 0.25
    # Score = 2 * 0.75 * 0.25 * 1.0 = 0.375
    result = rao_stirling({"US": 1.5, "LB": 0.5}, lambda i, j: 1.0)
    assert abs(result - 0.375) < 1e-9

if __name__ == "__main__":
    test_rao_stirling()
    test_rao_stirling_weighted_dict()
    test_rao_stirling_fractional_weights()
    test_gender_disparity()
    test_country_disparity()
    test_discipline_disparity()
    test_author_feature_score()
    test_novelty_cold_start()
    test_novelty_full_repeat()
    test_novelty_partial_new()
    print("all tests passed")