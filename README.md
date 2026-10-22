# The Community Index (comm-index)

Code, data, and analysis for the paper **"A community index (comm-index) for measuring gender, geographic, and disciplinary plurality in research collaboration: development and bibliometric analysis"**

The comm-index measures how **diverse a researcher's collaborations are**, rather than how often they are cited. It scores each co-authored paper along three dimensions:

| Dimension | Category used | How "different" two categories are |
|---|---|---|
| **Gender** | author gender | 0 if same, 1 if different |
| **Geography** | affiliation country → World Bank income group | `|group_i − group_j| / 3` across the 4 income groups |
| **Discipline** | specialization (small cohorts) or OpenAlex topic hierarchy (extended cohort) | 0 / 0.25 / 0.5 / 1 depending on how far apart the fields are |

A **novelty multiplier** then rewards authors who keep forming *new* partnerships instead of repeating the same co-author group.

The output is a **three-component vector** per author. A geometric-mean scalar is also provided, but the vector is the primary result, so the dimensions are never collapsed with arbitrary weights.

---

## Contents

- [Method](#method)
- [Repository layout](#repository-layout)
- [Installation](#installation)
- [Quickstart](#quickstart)
- [Full pipeline](#full-pipeline)
- [Input data format](#input-data-format)
- [Outputs](#outputs)
- [Tests](#tests)
- [Data sources](#data-sources)
- [Privacy and anonymization](#privacy-and-anonymization)
- [Known limitations](#known-limitations)
- [Citation](#citation)

---

## Method

All of the core math is in [`commindex.py`](commindex.py).

### 1. Paper-level diversity (Rao–Stirling)

For a paper *p* and feature *f*, let *pᵢ* be the share of authors in category *i*, and *dᵢⱼ* the disparity between categories *i* and *j*:

```
Δ_f(p) = Σ_{i≠j} pᵢ · pⱼ · dᵢⱼ
```

`Δ_f(p)` is 0 when every author falls in the same category and grows with both the *spread* of categories and the *distance* between them. Implemented in `rao_stirling()`.

- **Multiple affiliations:** for geography, an author with *k* affiliations adds `1/k` weight to each affiliation country, so every author counts once in total (`paper_country_weights()`). For gender and discipline, each author appears only once per paper.
- **Solo-authored papers** have zero collaboration diversity by definition.

### 2. Disparity functions

| Function | Rule |
|---|---|
| `gender_disparity` | 0 if same, 1 if different (`unknown` is its own category) |
| `country_disparity_income_group` | World Bank group (1 = LIC, 2 = LMIC, 3 = UMIC, 4 = HIC) from `income_group_lookup.json`; disparity `|gᵢ − gⱼ| / 3`. Two countries in the same income group get 0. |
| `discipline_disparity` | Small cohorts. Same specialization → 0; same cluster → 0.25; related clusters → 0.5; otherwise → 1. Clusters and related pairs are set in `SPECIALIZATION_CLUSTERS` / `RELATED_CLUSTER_PAIRS`. |
| `discipline_disparity_topics` | Extended cohort. Uses keys shaped like `domain‖field‖subfield`: same subfield → 0; same field → 0.25; same domain → 0.5; different domain → 1. |

`run_analysis.py` picks the discipline function on its own. If the `specialization` column contains `||`, it uses the topic hierarchy.

### 3. Author-level aggregation

An author's score for a feature is the **unweighted mean** of `Δ_f(p)` across all of their papers (`author_feature_score()`). Team size is deliberately *not* used as a weight, so large consortium papers do not dominate.

### 4. Novelty multiplier

For author *v* on paper *p*, compare *v*'s co-authors on *p* with everyone *v* co-authored with **before** *p*'s publication date:

```
β(v, p) = 1 + δ · (n_new / n_total)
```

`β̄(v)` is the mean of `β` over the author's papers. Each of the three feature scores is multiplied by `β̄(v)`. The parameter `δ ∈ [0, 1]` sets how strongly novelty counts. `δ = 0` gives pure diversity, the primary analysis uses `δ = 0.5`, and the sensitivity analysis also runs `δ = 1.0`.

### 5. Composite

```
comm-index vector  = [Δ_gender, Δ_country, Δ_discipline] · β̄
comm-index scalar  = geometric mean of the vector
```

The geometric mean is zero whenever any one component is zero. For the extended cohort, gender is unknown for every author, so the scalar is always 0 there. Analyses of that cohort use the **2-D composite** `√(Δ_country · Δ_discipline)` instead (see `get_composite_CI_ext_cohort.py`).

---

## Repository layout

### Core code

| File | Purpose |
|---|---|
| `commindex.py` | Core library: disparity functions, Rao–Stirling, author aggregation, novelty, composite |
| `run_analysis.py` | CLI that runs the whole pipeline on a single cohort CSV and writes the results |
| `test_commindex.py` | Unit tests for the core math |
| `enrich_dates.py` | Adds publication dates to a cohort CSV using the Crossref API (results cached in `crossref_date_cache.json`) |
| `build_seed_map.py` | Finds multi-paper "seed" authors in cohorts A/B and writes `seed_authors_for_matching.csv` |
| `get_composite_CI_ext_cohort.py` | Spearman correlation (with a Fisher-z 95% CI) between h-index and the 2-D composite for the extended cohort |
| `bruknow-h-index.py` | Single-author h-index computed from OpenAlex (articles only) |

### Notebooks

| Notebook | Purpose |
|---|---|
| `Data_extraction.ipynb` | Queries the Dimensions API for 2025 multi-country papers, builds the co-authorship graph, and selects the connected components that become cohorts A and B |
| `extended_pull_clean.ipynb` | **Canonical extended pull.** Fetches the seed authors' 2015–2025 publication histories plus each co-author's topics and h-index from OpenAlex |
| `extended_pull.ipynb`, `extended_pull_backup.ipynb` | Earlier versions of the extended pull. Also contain `adapt_extended_for_pipeline()` and the country-coverage check |
| `country_lookup.ipynb` | Turns the World Bank income-group CSV into `income_group_lookup.json` (ISO alpha-2 → group 1–4) |
| `explore_extended.ipynb` | Explores the scores for the small and extended cohorts |
| `plot_extended.ipynb` | Generates the paper figures in `final_figures/` and the exploratory PNGs in the repo root |
| `analysis.ipynb` | The earlier (pre-revision) graph-based implementation, kept for reference |
| `data_check.ipynb` | Quick checks on the gender distribution |

### Data

| File / folder | Contents |
|---|---|
| `data/public/cohortA_with_dates.csv`, `data/public/cohortB_with_dates.csv` | Anonymized pipeline inputs for the small cohorts. **Inputs to `run_analysis.py`** |
| `data/public/cohortA_public_demo.csv`, `data/public/cohortB_public_demo.csv` | Alternative anonymized versions without the date column |
| `data/internal/` | Not committed. Working copies with DOIs, names, and affiliation details. Required to re-enrich dates or re-run manual curation |
| `scripts/make_public_data.py` | Produces the public pipeline CSVs from the internal ones |
| `adapted_extended_cohort.csv` | Extended cohort in pipeline format. **Input to `run_analysis.py`** |
| `extended_cohort_raw.csv` | Combined raw per-seed OpenAlex pulls |
| `author_topics.json` | OpenAlex primary topic and h-index per author |
| `seed_authors_for_matching.csv` | The 10 seed authors with their OpenAlex IDs |
| `income_group_lookup.json` | Country code → World Bank income group (1-4) |
| `world-bank-income-groups/` | Source data from Our World in Data |
| `results_cohortA/`, `results_cohortB/`, `results_extended/` | Pipeline outputs |
| `final_figures/` | Paper figures (PNG and PDF) |

**Cohort sizes**

| Cohort | Papers | Authors | Rows |
|---|---|---|---|
| A (materials / environmental) | 7 | 46 | 80 |
| B (clinical / medical) | 3 | 40 | 55 |
| Extended (10 seeds, 2015–2025) | 2,549 | 6,722 | 22,261 |

---

## Installation

The project uses [uv](https://docs.astral.sh/uv/) and requires **Python ≥ 3.14** (pinned in `.python-version`).

```bash
git clone <this-repo>
cd Community-Index
uv sync
```

Dependencies are declared in `pyproject.toml` and locked in `uv.lock`: pandas, numpy, scipy, networkx, matplotlib, seaborn, plotly, jupyter, pyalex, dimcli, pycountry, and dotenv.

> `enrich_dates.py` also imports `requests`. It is installed as a transitive dependency, but if you see an `ImportError`, run `uv add requests`.

---

## Quickstart

Reproduce the results from the included data:

```bash
# Small cohorts
uv run python run_analysis.py cohortA_with_dates.csv results_cohortA/
uv run python run_analysis.py cohortB_with_dates.csv results_cohortB/

# Extended cohort (takes noticeably longer)
uv run python run_analysis.py adapted_extended_cohort.csv results_extended/

# h-index vs 2-D composite correlation
uv run python get_composite_CI_ext_cohort.py
```

Each run prints a summary of paper-level and author-level scores and writes CSVs to the output directory.

Using the library directly:

```python
from commindex import rao_stirling, country_disparity_income_group

# One US author, one Ugandan author: HIC vs LIC → maximum disparity
rao_stirling(["US", "UG"], country_disparity_income_group)   # 0.5
```

---

## Full pipeline

How the included data was produced, from start to finish:

```
Dimensions API ──► Data_extraction.ipynb ──► cohort{A,B}_internal_with_doi.csv
                                                     │
                                       enrich_dates.py (Crossref)
                                                     ▼
                                          cohort{A,B}_with_dates.csv ──► run_analysis.py ──► results_cohort{A,B}/
                                                     │
                                            build_seed_map.py
                                                     ▼
                                      seed_authors_for_matching.csv
                                                     │
                     OpenAlex ──► extended_pull_clean.ipynb ──► extended_cohort_raw.csv + author_topics.json
                                                     │
                                  adapt_extended_for_pipeline()
                                                     ▼
                                      adapted_extended_cohort.csv ──► run_analysis.py ──► results_extended/
                                                                                              │
                                                     plot_extended.ipynb, get_composite_CI_ext_cohort.py
                                                                                              ▼
                                                                                       final_figures/
```

### Re-running data extraction

- **Dimensions** (`Data_extraction.ipynb`) needs an API key. Put it in a `.env` file in the repo root:
  ```
  DIMENSIONS_API_KEY=your_key_here
  ```
- **OpenAlex** (`extended_pull_clean.ipynb`, `bruknow-h-index.py`) and **Crossref** (`enrich_dates.py`) need no key, but they ask for a contact email to get into the "polite pool". Change `config.email` / `MAILTO` in those files to your own address.
- The OpenAlex author pull resumes from `author_topics.json` if it is interrupted.

---

## Input data format

`run_analysis.py` expects a CSV with **one row per (paper, author, affiliation)**:

| Column | Required | Notes |
|---|---|---|
| `pub_anon_id` | yes | Paper identifier |
| `author_anon_id` | yes | Author identifier |
| `aff_country_code` | yes | ISO 3166-1 alpha-2 code; must be in `income_group_lookup.json` (an unknown code raises `KeyError`) |
| `specialization` | yes | A key from `SPECIALIZATION_CLUSTERS`, **or** a topic key `domain‖field‖subfield` |
| `pub_date` | yes | Any date pandas can parse; used for novelty |
| `gender` | optional | Lower-cased automatically; set to `unknown` if the column is missing |

During loading, rows missing a country or a specialization are dropped and exact duplicates are removed.

**Using your own data:** with free-text specializations, add every value to `SPECIALIZATION_CLUSTERS` (and any natural pairings to `RELATED_CLUSTER_PAIRS`) in `commindex.py`. Otherwise, convert them to the `domain‖field‖subfield` form with `make_topic_key()`.

---

## Outputs

`run_analysis.py` writes five files to the output directory:

| File | Contents |
|---|---|
| `paper_scores.csv` | Per paper: `n_authors`, `delta_gender`, `delta_country`, `delta_discipline` |
| `author_scores_delta0.csv` | Per author, pure diversity (δ = 0) |
| `author_scores_delta05.csv` | Per author, novelty-adjusted (δ = 0.5, **primary**) |
| `author_scores_delta1.csv` | Per author, maximum novelty weight (δ = 1.0) |
| `sensitivity_delta.csv` | Long format: `author_anon_id`, `delta`, `commindex_scalar` |

Author score columns: `n_papers`, `delta_gender`, `delta_country`, `delta_discipline`, `beta_mean`, `commindex_scalar`.

Scores for single-paper authors describe one collaboration only. Most downstream analyses keep only authors with `n_papers ≥ 2`.

---

## Tests

```bash
uv run python test_commindex.py
```

The tests check the Rao–Stirling math (balanced and unbalanced cases, fractional weights), each disparity function, author-level averaging, and the novelty factor (first paper, fully repeated co-authors, partly new co-authors). The file also works with `pytest`.

---

## Data sources

- **[Dimensions](https://www.dimensions.ai/)**: source of the small cohorts A and B (2025 publications)
- **[OpenAlex](https://openalex.org/)**: extended publication histories, author topics, h-index
- **[Crossref](https://www.crossref.org/)**: publication dates
- **[World Bank income groups via Our World in Data](https://ourworldindata.org/grapher/world-bank-income-groups)**: 2025 classification, see `world-bank-income-groups/readme.md`

---

## Privacy and anonymization

There are two versions of each small cohort:

- `*_public_demo.csv`: anonymized IDs only, safe to share
- `*_internal_with_doi.csv` / `*_with_dates.csv`: keep DOIs, names, and Dimensions/OpenAlex identifiers so results can be re-linked and enriched

Author and paper IDs (`A…` / `P…`) are stable hashes, so results stay joinable across files. The extended cohort uses OpenAlex IDs directly.

---

## Known limitations

- **Gender** is binary or unknown in the source data. In the extended cohort it is `unknown` for every author, so `Δ_gender = 0` and the 3-D scalar is 0. Use the 2-D composite for that cohort.
- **Income-group disparity** treats all countries in the same World Bank group as identical (for example US vs DE → 0).
- **Novelty** can mix real new partnerships with ordinary lab turnover, such as graduate students joining and leaving. Normalizing for career stage is future work.
- **Small cohorts** (A: 7 papers, B: 3 papers) are demonstrations of the method, not validation. The extended cohort covers 10 seeds' networks and is not a random sample.

---

## Citation
## Citation

If you use this work, please cite:

> Kumar, A.*, Sabet, C.*, Hammond, A.*, Jain, B., Pradhan, S., Suresha, D., Goode, D., Fiske, A., Lehmann, L. S., Celi, L. A., McCague, N., Abulibdeh, R., Cheruku, S., Bawoke, M. M., Shah, S. (2026). *A community index (comm-index) for measuring gender, geographic, and disciplinary plurality in research collaboration: development and bibliometric analysis.* Manuscript under review.
>
> \*Co-first authors.

```bibtex
@unpublished{kumar2026community,
      title={A community index (comm-index) for measuring gender, geographic, and disciplinary plurality in research collaboration: development and bibliometric analysis},
      author={Kumar, Arav and Sabet, Cameron and Hammond, Alessandro and Jain, Bhav and Pradhan, Sameer and Suresha, Dharaa and Goode, Deirdre and Fiske, Amelia and Lehmann, Lisa Soleymani and Celi, Leo Anthony and McCague, Ned and Abulibdeh, Rawan and Cheruku, Saanvi and Bawoke, Melat Mezgebu and Shah, Sohum},
      year={2026},
      note={Manuscript under review. Kumar, Sabet, and Hammond contributed equally.}
}
```