# commindex.py -- Author: Arav Kumar  
# --- Imports --- 
import collections 
import json
from pathlib import Path
import pandas as pd
from math import prod

# --- Config ---
COL = {
    "PUB": "pub_anon_id",
    "AUTH": "author_anon_id",
    "FIRST": None,
    "LAST": None,
    "COUNTRY": "aff_country",
    "CCODE": "aff_country_code",
    "GENDER": "gender",
    "SPEC": "specialization",
}  


UNKNOWN_GENDER = "unknown"

_LOOKUP_PATH = Path(__file__).parent / "income_group_lookup.json"
with open(_LOOKUP_PATH) as f:
    INCOME_GROUP_LOOKUP = json.load(f)

# 4x4 disparity matrix 
INCOME_DISPARITY_MATRIX = {
    i : {j: abs(i-j)/3 for j in range(1, 5)} 
    for i in range (1, 5)
}

# Specialization -> cluster
SPECIALIZATION_CLUSTERS = {
    # Cohort A: materials/environmental sciences
    "Chemistry":                "physical_chemical",
    "Materials Science":        "physical_chemical",
    "Physics":                  "physical_chemical",
    "Computational/Modeling":   "physical_chemical",
    "Environmental Science":    "environmental_engineering",
    "Environmental Engineering":"environmental_engineering",
    "Civil Engineering":        "environmental_engineering",
    
    # Cohort B: clinical/medical
    "Cardiology":               "clinical",
    "Clinical Medicine":        "clinical",
    "Clinical Pharmacy":        "clinical",
    "Internal Medicine":        "clinical",
    "Biostatistics":            "quantitative_health",
    "Epidemiology":             "quantitative_health",
    "Statistics":               "quantitative_health",
    "Business":                 "adjacent",
    "Finance":                  "adjacent",
}

# Related-cluster pairs (order-independent). Everything else is unrelated.
RELATED_CLUSTER_PAIRS = {
    frozenset(["clinical", "quantitative_health"]),
    frozenset(["physical_chemical", "environmental_engineering"]),
    # add more if there are natural adjacencies
}

# --- Disparity definitions ---
#TODO: sensitivity analysis where we drop unknown gender authors
def gender_disparity(cat_i, cat_j):
    return 0.0 if cat_i == cat_j else 1.0

def country_disparity_income_group(cc_i, cc_j, lookup=INCOME_GROUP_LOOKUP, matrix=INCOME_DISPARITY_MATRIX):
    group_i = lookup.get(cc_i)
    group_j = lookup.get(cc_j)
    if group_i is None or group_j is None:
        raise KeyError(f"Country code {cc_i} or {cc_j} not found in income lookup") 
    return matrix[group_i][group_j]

def paper_country_weights(paper_group): 
    """Return {country_code: weight} where each author contributes 1.0 total, split evenly across their affiliations."""
    weights ={}
    for author_id, author_rows in paper_group.groupby("author_anon_id"):
        countries = author_rows["aff_country_code"].tolist()
        weight_per = 1.0 / len(countries)
        for c in countries:
            weights[c] = weights.get(c, 0.0) + weight_per
    return weights 

def discipline_disparity(spec_i, spec_j, clusters=SPECIALIZATION_CLUSTERS, related_pairs=RELATED_CLUSTER_PAIRS):
    if spec_i == spec_j:
        return 0.0
    cluster_i = clusters.get(spec_i)
    cluster_j = clusters.get(spec_j)
    if cluster_i is None or cluster_j is None:
        raise KeyError(f"Specialization {spec_i} or {spec_j} not found in specialization clusters")
    if cluster_i == cluster_j:
        return 0.25
    if frozenset([cluster_i, cluster_j]) in related_pairs:
        return 0.5
    return 1.0

def make_topic_key(subfield, field, domain):
    return f"{domain}||{field}||{subfield}"

def discipline_disparity_topics(topic_i, topic_j):
    """Hierarchical disparity for OpenAlex topic strings of form 'domain||field||subfield'.
    Returns:
      0.0 if same subfield (same string)
      0.25 if same field, different subfield
      0.5 if same domain, different field
      1.0 if different domain
    """
    if topic_i == topic_j:
        return 0.0
    
    parts_i = topic_i.split("||")
    parts_j = topic_j.split("||")
    if len(parts_i) != 3 or len(parts_j) != 3:
        raise ValueError(f"Malformed topic key: {topic_i} or {topic_j}")
    
    domain_i, field_i, sub_i = parts_i
    domain_j, field_j, sub_j = parts_j
    
    if field_i == field_j:
        return 0.25
    if domain_i == domain_j:
        return 0.5
    return 1.0


# --- Core Rao-Stirling ---
def rao_stirling(categories, disparity_fn: callable):
    """Given a list (or dict {category: weight}) of categories (one per author on a paper), return Δ_f(p)."""
    # Count proportions p_i
    if isinstance(categories, dict):
        counter = dict(categories)
    else: 
        counter = collections.Counter(categories)

    total = sum(counter.values())
    if total == 0: 
        return 0.0 # no authors -> no diversity
    
    proportions = {cat: count / total for cat, count in counter.items()}

    # Compute Σ_{i≠j} p_i p_j d_ij
    diversity = 0.0
    for cat_i, p_i in proportions.items():
        for cat_j, p_j in proportions.items():
            if cat_i != cat_j:
                d_ij = disparity_fn(cat_i, cat_j)
                diversity += p_i * p_j * d_ij
    return diversity

# --- Author-level aggregation ---
def author_feature_score(author_id, df, feature_col, disparity_fn: callable, paper_preprocessor=None):
    """
    Compute Δ_f(v_i) as the unweighted mean of Δ_f(p) across the author's papers. 
    author_id: the anonymized ID of the author
    df: the full cohort DataFrame (with pub_anon_id, author_anon_id, and feature_columns)
    feature_col: the column name for the feature (e.g., 'gender', 'aff_country_code', 'specialization')
    disparity_fn: the disparity funciton for this feature 

    Returns: float in [0, 1]. or None if author has no papers
    """
    author_paper_ids = df.loc[df["author_anon_id"] == author_id, "pub_anon_id"].unique()
    if len(author_paper_ids) == 0:
        return None  # author has no papers

    diversity_scores = []
    for paper_id in author_paper_ids:
        paper_group = df[df["pub_anon_id"] == paper_id]
        if paper_preprocessor is None:
            # Dedupe rows within a paper so multi-affiliation authors count once
            deduped = paper_group.drop_duplicates(subset=["author_anon_id"], keep="first")
            categories = deduped[feature_col].tolist()
        else:
            categories = paper_preprocessor(paper_group)
        diversity = rao_stirling(categories, disparity_fn)
        diversity_scores.append(diversity)
    return sum(diversity_scores) / len(diversity_scores)

# --- Novelty ---
def build_prior_graph(author_id, paper_date, papers_by_author, authors_by_paper, date_by_paper):
    """Return the set of co-author IDs that author_id collaborated with before paper_date."""
    prior_papers = [
        p for p in papers_by_author.get(author_id, set())
        if pd.notna(date_by_paper.get(p)) and date_by_paper[p] < paper_date
    ]
    prior_collaborators = set()
    for p in prior_papers:
        prior_collaborators.update(authors_by_paper[p])
    prior_collaborators.discard(author_id)
    return prior_collaborators


def novelty_factor(author_id, paper_id, papers_by_author, authors_by_paper, date_by_paper, delta):
    """Compute β(v_i, p) = 1 + delta * (n_new / n_total)."""
    paper_date = date_by_paper[paper_id]
    prior_coauthors = build_prior_graph(author_id, paper_date, papers_by_author, authors_by_paper, date_by_paper)
    current_coauthors = authors_by_paper[paper_id] - {author_id}
    n_total = len(current_coauthors)
    if n_total == 0:
        return 1.0
    n_new = len(current_coauthors - prior_coauthors)
    return 1.0 + delta * (n_new / n_total)

def author_mean_novelty(author_id, papers_by_author, authors_by_paper, date_by_paper, delta):
    """Compute β̄(v_i) as the mean novelty factor across author_id's publications."""
    author_papers = papers_by_author.get(author_id, set())
    if not author_papers:
        return 1.0  # No papers -> no adjustment
    betas = [
        novelty_factor(author_id, p, papers_by_author, authors_by_paper, date_by_paper, delta)
        for p in author_papers
    ]
    return sum(betas) / len(betas)

# --- Composite ---
def author_commindex_vector(author_id, df, delta=0.5, precomputed=None, discipline_fn=None):
    """Return novelty-adjusted Δ_f(v_i)."""
    if precomputed is None:
        papers_by_author = {aid: set(grp["pub_anon_id"]) for aid, grp in df.groupby("author_anon_id")}
        authors_by_paper = {pid: set(grp["author_anon_id"]) for pid, grp in df.groupby("pub_anon_id")}
        date_by_paper = df.groupby("pub_anon_id")["pub_date"].first().to_dict()
    else:
        papers_by_author, authors_by_paper, date_by_paper = precomputed

    if discipline_fn is None: 
        discipline_fn = discipline_disparity
    
    g = author_feature_score(author_id, df, "gender", gender_disparity)
    c = author_feature_score(author_id, df, "aff_country_code",
                            lambda i, j: country_disparity_income_group(i, j),
                            paper_preprocessor=paper_country_weights)
    d = author_feature_score(author_id, df, "specialization",
                            lambda i, j: discipline_fn(i, j))
    if delta > 0:
        beta_mean = author_mean_novelty(author_id, papers_by_author, authors_by_paper, date_by_paper, delta)
        g = g * beta_mean if g is not None else None
        c = c * beta_mean if c is not None else None
        d = d * beta_mean if d is not None else None
    
    return [g, c, d]

def author_commindex_scalar(vector):
    """Geometric mean of the three feature scores."""
    # Handle None values (author has no papers for some feature)
    if any(v is None for v in vector):
        return None
    return prod(vector) ** (1.0 / len(vector))


