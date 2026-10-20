"""
run_analysis.py

Run the full comm-index pipeline on one cohort. Produces:
  - Per-paper feature scores
  - Author-level scores (pure diversity, delta=0)
  - Author-level scores (novelty-adjusted, delta=0.5)
  - Composite comm-index (geometric mean of the vector)
  - Sensitivity across delta = {0, 0.5, 1.0}

Usage:
    uv run python run_analysis.py cohortA_with_dates.csv results_cohortA/
    uv run python run_analysis.py cohortB_with_dates.csv results_cohortB/
"""

# TODO: refactor this to not pass disicpline_fn to every function

import sys
from pathlib import Path
import pandas as pd

from commindex import (
    paper_country_weights,
    rao_stirling,
    gender_disparity,
    country_disparity_income_group,
    discipline_disparity,
    discipline_disparity_topics, 
    author_feature_score,
    author_mean_novelty,
    author_commindex_vector,
    author_commindex_scalar,
)

def load_cohort(path):
    df = pd.read_csv(path, parse_dates=["pub_date"])
    df["specialization"] = df["specialization"].str.strip().str.replace(r"\s*/\s*", "/", regex=True)
    df["aff_country_code"] = df["aff_country_code"].str.strip().str.upper()
    if "gender" not in df.columns:
        df["gender"] = "unknown"
    else:
        df["gender"] = df["gender"].str.strip().str.lower()
    
    # Drop rows with missing country OR discipline (extended data has some of these)
    n_before = len(df)
    df = df.dropna(subset=["aff_country_code", "specialization"])
    n_dropped = n_before - len(df)
    if n_dropped:
        print(f"  Dropped {n_dropped:,} rows with missing country or discipline data")
    
    df = df.drop_duplicates(
        subset=["pub_anon_id", "author_anon_id", "aff_country_code", "gender", "specialization"],
        keep="first"
    ).reset_index(drop=True)
    return df

def build_precomputed(df):
    """Build the three lookups from a cohort DataFrame."""
    papers_by_author = {
        aid: set(grp["pub_anon_id"]) for aid, grp in df.groupby("author_anon_id")
    }
    authors_by_paper = {
        pid: set(grp["author_anon_id"]) for pid, grp in df.groupby("pub_anon_id")
    }
    date_by_paper = df.groupby("pub_anon_id")["pub_date"].first().to_dict()
    return papers_by_author, authors_by_paper, date_by_paper


def compute_paper_level_scores(df, discipline_fn):
    """Per-paper Δ_f(p) for each feature."""
    rows = []
    for pid, grp in df.groupby("pub_anon_id"):

        n_unique_authors = grp["author_anon_id"].nunique()
        
        # Solo-author papers: zero collaboration diversity by definition
        if n_unique_authors < 2:
            rows.append({
                "pub_anon_id": pid,
                "n_authors": n_unique_authors,
                "delta_gender": 0.0,
                "delta_country": 0.0,
                "delta_discipline": 0.0,
            })
            continue
        
        country_weights = paper_country_weights(grp)
        one_row_per_author = grp.drop_duplicates(subset=["author_anon_id"], keep="first")
        rows.append({
            "pub_anon_id": pid,
            "n_authors": grp["author_anon_id"].nunique(),
            "delta_gender": rao_stirling(one_row_per_author["gender"].tolist(), gender_disparity),
            "delta_country": rao_stirling(country_weights, lambda i, j: country_disparity_income_group(i, j)),
            "delta_discipline": rao_stirling(one_row_per_author["specialization"].tolist(), lambda i, j: discipline_fn(i, j)),
        })
    return pd.DataFrame(rows).set_index("pub_anon_id")


def compute_author_scores(df, delta, precomputed, discipline_fn):
    """Author-level comm-index at a given novelty parameter delta."""
    papers_by_author, authors_by_paper, date_by_paper = precomputed
    rows = []

    for aid in df["author_anon_id"].unique():
        vec = author_commindex_vector(aid, df, delta=delta, precomputed=precomputed, discipline_fn=discipline_fn)
        scalar = author_commindex_scalar(vec)
        beta_mean = author_mean_novelty(
            aid, papers_by_author, authors_by_paper, date_by_paper, delta
        )
        rows.append({
            "author_anon_id": aid,
            "n_papers": len(papers_by_author.get(aid, set())),
            "delta_gender": vec[0],
            "delta_country": vec[1],
            "delta_discipline": vec[2],
            "beta_mean": beta_mean,
            "commindex_scalar": scalar,
        })
    return pd.DataFrame(rows).set_index("author_anon_id")


def sensitivity_over_delta(df, precomputed, discipline_fn, deltas=(0.0, 0.5, 1.0)):
    """Return one row per (author, delta) with the composite scalar."""
    rows = []
    for delta in deltas:
        for aid in df["author_anon_id"].unique():
            vec = author_commindex_vector(aid, df, delta=delta, precomputed=precomputed, discipline_fn=discipline_fn)
            scalar = author_commindex_scalar(vec)
            rows.append({
                "author_anon_id": aid,
                "delta": delta,
                "commindex_scalar": scalar,
            })
    return pd.DataFrame(rows)


def summarize(paper_scores, author_scores):
    """Print a compact summary to stdout."""
    print(f"\n{'='*60}")
    print(f"Paper-level scores ({len(paper_scores)} papers)")
    print(f"{'='*60}")
    
    # For extended data, printing 2500 papers is way too much
    if len(paper_scores) > 20:
        print(f"(truncated, showing first 10 of {len(paper_scores)})")
        print(paper_scores.head(10).round(4).to_string())
    else:
        print(paper_scores.round(4).to_string())

    print(f"\n{'='*60}")
    print(f"Author-level scores ({len(author_scores)} authors)")
    print(f"{'='*60}")

    multi = author_scores[author_scores["n_papers"] > 1].sort_values(
        "n_papers", ascending=False
    )
    print(f"\nMulti-paper authors ({len(multi)}):")
    
    if len(multi) > 30:
        print(f"(showing top 20 by n_papers)")
        print(multi.head(20).round(4).to_string())
    else:
        print(multi.round(4).to_string())

    single = author_scores[author_scores["n_papers"] == 1]
    print(f"\nSingle-paper authors: {len(single)} (scores reflect one collaboration event)")

    # Distribution only meaningful if scalar isn't uniformly zero
    if (multi["commindex_scalar"] > 0).any():
        print(f"\n{'='*60}")
        print("Composite comm-index distribution (multi-paper authors)")
        print(f"{'='*60}")
        print(multi["commindex_scalar"].describe().round(4).to_string())
    else:
        print(f"\n{'='*60}")
        print("Component distributions (multi-paper authors)")
        print(f"{'='*60}")
        for col in ["delta_country", "delta_discipline", "beta_mean"]:
            print(f"\n{col}:")
            print(multi[col].describe().round(4).to_string())



def main():
    if len(sys.argv) != 3:
        print("Usage: uv run python run_analysis.py <input_csv> <output_dir>")
        sys.exit(1)

    in_path = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading {in_path}...")
    df = load_cohort(in_path)
    print(f"  {len(df)} rows, {df['author_anon_id'].nunique()} unique authors, "
          f"{df['pub_anon_id'].nunique()} unique papers")

    # Coverage sanity check
    missing_dates = df["pub_date"].isna().sum()
    if missing_dates:
        print(f"  WARNING: {missing_dates} rows have no pub_date; novelty may be affected")

    print("Precomputing lookups...")
    precomputed = build_precomputed(df)

    # Detect cohort type by specialization format
    sample_spec = df["specialization"].dropna().iloc[0]
    if "||" in sample_spec:
        print("  Detected extended cohort format (topic hierarchy)")
        discipline_fn = discipline_disparity_topics
    else:
        print("  Detected small cohort format (specialization clusters)")
        discipline_fn = discipline_disparity
    

    print("\nComputing paper-level scores...")
    paper_scores = compute_paper_level_scores(df, discipline_fn)
    paper_scores.to_csv(out_dir / "paper_scores.csv")

    # Sanity check: dual-affiliation authors should have matching paper- and author-level scores
    if "Ad83bc45d319d" in df["author_anon_id"].values:
        from commindex import gender_disparity
        score_paper = paper_scores.loc["P67694f6e606a", "delta_gender"]
        score_author = author_feature_score("Ad83bc45d319d", df, "gender", gender_disparity)
        diff = abs(score_paper - score_author)
        print(f"  Sanity check: paper={score_paper:.4f}, author={score_author:.4f}, diff={diff:.2e}")
        if diff > 1e-9:
            print("  WARNING: paper-level and author-level gender scores diverge")


    print("Computing author scores at delta=0 (pure diversity)...")
    author_scores_d0 = compute_author_scores(df, delta=0.0, precomputed=precomputed, discipline_fn=discipline_fn)
    author_scores_d0.to_csv(out_dir / "author_scores_delta0.csv")

    print("Computing author scores at delta=0.5 (primary)...")
    author_scores_d05 = compute_author_scores(df, delta=0.5, precomputed=precomputed, discipline_fn=discipline_fn)
    author_scores_d05.to_csv(out_dir / "author_scores_delta05.csv")

    print("Computing author scores at delta=1.0 (max novelty)...")
    author_scores_d1 = compute_author_scores(df, delta=1.0, precomputed=precomputed, discipline_fn=discipline_fn)
    author_scores_d1.to_csv(out_dir / "author_scores_delta1.csv")

    print("Running sensitivity across delta...")
    sensitivity = sensitivity_over_delta(df, precomputed, discipline_fn=discipline_fn)
    sensitivity.to_csv(out_dir / "sensitivity_delta.csv", index=False)

    # Print human-readable summary using primary delta
    summarize(paper_scores, author_scores_d05)

    print(f"\nAll outputs written to {out_dir}/")
    print("  paper_scores.csv")
    print("  author_scores_delta0.csv       (pure diversity)")
    print("  author_scores_delta05.csv      (primary, novelty-adjusted)")
    print("  author_scores_delta1.csv       (max novelty)")
    print("  sensitivity_delta.csv          (all authors, all deltas)")


if __name__ == "__main__":
    main()