"""
build_seed_map.py

Identifies multi-paper authors ("seeds") from both cohorts and pulls their
real names, affiliations, and DOIs from the internal DOI-preserving CSVs.

Output: seed_authors_for_matching.csv
Columns: cohort, author_anon_id, first_name, last_name, n_papers,
         affiliations, dois, researcher_id (if available)

Usage:
    uv run python build_seed_map.py
"""

import pandas as pd
from pathlib import Path


COHORT_FILES = {
    "A": "cohortA_internal_with_doi.csv",
    "B": "cohortB_internal_with_doi.csv",
}

OUTPUT_PATH = "seed_authors_for_matching.csv"


def identify_seeds(df):
    """Return set of author_anon_ids appearing on 2+ unique papers."""
    per_author = df.groupby("author_anon_id")["pub_anon_id"].nunique()
    return set(per_author[per_author > 1].index)


def build_seed_row(cohort, author_id, author_rows):
    """Extract identifying info for one seed author.
    
    Handles multiple affiliations and picks first non-null name variant.
    """
    # Name: first non-null occurrence (should be consistent across rows)
    first_name = author_rows["first_name"].dropna().iloc[0] if author_rows["first_name"].notna().any() else ""
    last_name = author_rows["last_name"].dropna().iloc[0] if author_rows["last_name"].notna().any() else ""
    
    # Affiliations: unique institution names across all their papers
    if "aff_name" in author_rows.columns:
        affs = sorted(author_rows["aff_name"].dropna().unique().tolist())
    else:
        affs = []
    
    # DOIs: unique DOIs of papers they're on
    dois = sorted(author_rows["doi"].dropna().unique().tolist()) if "doi" in author_rows.columns else []
    
    # Dimensions researcher_id if present
    rid = ""
    if "researcher_id" in author_rows.columns and author_rows["researcher_id"].notna().any():
        rid = author_rows["researcher_id"].dropna().iloc[0]
    
    return {
        "cohort": cohort,
        "author_anon_id": author_id,
        "first_name": first_name,
        "last_name": last_name,
        "n_papers": author_rows["pub_anon_id"].nunique(),
        "affiliations": " | ".join(affs),
        "dois": " | ".join(dois),
        "researcher_id": rid,
    }


def main():
    rows = []
    for cohort_label, path in COHORT_FILES.items():
        if not Path(path).exists():
            print(f"WARNING: {path} not found, skipping cohort {cohort_label}")
            continue
        
        df = pd.read_csv(path)
        print(f"Cohort {cohort_label}: {len(df)} rows loaded from {path}")
        
        seeds = identify_seeds(df)
        print(f"  {len(seeds)} multi-paper (seed) authors identified")
        
        for author_id in sorted(seeds):
            author_rows = df[df["author_anon_id"] == author_id]
            rows.append(build_seed_row(cohort_label, author_id, author_rows))
    
    out = pd.DataFrame(rows).sort_values(["cohort", "n_papers"], ascending=[True, False])
    out.to_csv(OUTPUT_PATH, index=False)
    print(f"\nWrote {len(out)} seed author records to {OUTPUT_PATH}")
    print("\nPreview:")
    print(out[["cohort", "author_anon_id", "first_name", "last_name", "n_papers"]].to_string(index=False))


if __name__ == "__main__":
    main()