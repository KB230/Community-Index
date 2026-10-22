import pandas as pd

PIPELINE_COLS = [
    "pub_anon_id", "author_anon_id", "aff_country_code",
    "specialization", "pub_date", "gender"
]

for cohort in ["A", "B"]:
    df = pd.read_csv(f"../data/internal/cohort{cohort}_with_dates_internal.csv")
    # Keep only pipeline-relevant columns, in case any are missing use intersection
    keep = [c for c in PIPELINE_COLS if c in df.columns]
    df[keep].to_csv(f"../data/public/cohort{cohort}_with_dates.csv", index=False)
    print(f"cohort {cohort}: wrote {len(df)} rows, {len(keep)} columns")