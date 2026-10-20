"""
enrich_dates.py

Enrich a cohort CSV with publication dates from Crossref.

Usage:
    uv run enrich_dates.py cohortA_internal_with_doi.csv cohortA_with_dates.csv
    uv run enrich_dates.py cohortB_internal_with_doi.csv cohortB_with_dates.csv
"""

import json
import sys
import time
from pathlib import Path
import requests
import pandas as pd

CACHE_PATH = Path("crossref_date_cache.json")
MAILTO = "arav_kumar@berkeley.edu"  # <-- REPLACE with your real email


def load_cache():
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text())
    return {}


def save_cache(cache):
    CACHE_PATH.write_text(json.dumps(cache, indent=2))


def fetch_pub_date(doi, mailto=MAILTO, timeout=10):
    """Query Crossref for publication date. Returns dict or None."""
    url = f"https://api.crossref.org/works/{doi}"
    headers = {"User-Agent": f"CommIndex-Research/1.0 (mailto:{mailto})"}
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
    except requests.RequestException as e:
        print(f"  ! network error for {doi}: {e}")
        return None

    if r.status_code == 404:
        print(f"  ! DOI not found in Crossref: {doi}")
        return None
    if r.status_code != 200:
        print(f"  ! HTTP {r.status_code} for {doi}")
        return None

    data = r.json().get("message", {})
    # Prefer published-print, then published-online, then created
    for key in ("published-print", "published-online", "published", "created"):
        if key in data and "date-parts" in data[key]:
            parts = data[key]["date-parts"][0]
            year = parts[0] if len(parts) > 0 else None
            month = parts[1] if len(parts) > 1 else 1
            day = parts[2] if len(parts) > 2 else 1
            if year is None:
                continue
            return {"year": year, "month": month, "day": day, "source": key}
    return None


def enrich_dataframe(df, doi_col="doi"):
    """Add pub_year, pub_month, pub_day, pub_date, date_source columns."""
    cache = load_cache()
    unique_dois = df[doi_col].dropna().unique().tolist()
    print(f"Found {len(unique_dois)} unique DOIs. {sum(1 for d in unique_dois if d in cache)} already cached.")

    for i, doi in enumerate(unique_dois, 1):
        if doi in cache:
            continue
        print(f"[{i}/{len(unique_dois)}] fetching {doi}")
        cache[doi] = fetch_pub_date(doi)
        save_cache(cache)  # save incrementally in case of crash
        time.sleep(0.1)  # polite pacing

    def lookup(d, field):
        entry = cache.get(d)
        if entry is None:
            return None
        return entry.get(field)

    df = df.copy()
    df["pub_year"] = df[doi_col].map(lambda d: lookup(d, "year"))
    df["pub_month"] = df[doi_col].map(lambda d: lookup(d, "month"))
    df["pub_day"] = df[doi_col].map(lambda d: lookup(d, "day"))
    df["date_source"] = df[doi_col].map(lambda d: lookup(d, "source"))
    df["pub_date"] = pd.to_datetime(
        df[["pub_year", "pub_month", "pub_day"]].rename(
            columns={"pub_year": "year", "pub_month": "month", "pub_day": "day"}
        ),
        errors="coerce",
    )
    return df


def main():
    if len(sys.argv) != 3:
        print("Usage: python enrich_dates.py <input_csv> <output_csv>")
        sys.exit(1)
    in_path, out_path = sys.argv[1], sys.argv[2]

    df = pd.read_csv(in_path)
    print(f"Loaded {len(df)} rows from {in_path}")

    df = enrich_dataframe(df)

    # Report on missing dates
    missing = df["pub_date"].isna().sum()
    if missing:
        print(f"WARNING: {missing} rows have no publication date")

    df.to_csv(out_path, index=False)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()