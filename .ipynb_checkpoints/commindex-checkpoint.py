# commindex.py

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

# --- Disparity definitions ---
def gender_disparity(cat_i, cat_j): ...
def country_disparity_income_group(cc_i, cc_j, lookup, matrix): ...
def discipline_disparity_for(for_i, for_j): ...  # uses FoR hierarchy

# --- Core Rao-Stirling ---
def rao_stirling(categories, disparity_fn):
    """Given a list of categories (one per author on a paper), return Δ_f(p).
    Categories with value None or 'unknown' get their own category."""
    # Count proportions p_i
    # Compute Σ_{i≠j} p_i p_j d_ij

# --- Per-paper feature scores ---
def paper_diversity_gender(paper_authors): ...
def paper_diversity_country(paper_authors, income_lookup, disparity_matrix): ...
def paper_diversity_discipline(paper_authors): ...

# --- Author-level aggregation ---
def author_feature_score(author_id, papers_by_author, feature_fn):
    """Unweighted mean of paper-level scores."""
    ...

# --- Novelty ---
def build_prior_graph(author_id, papers_by_author, before_date):
    """Returns set of co-author IDs v_i has published with strictly before `before_date`."""
    ...

def novelty_factor(author_id, paper, papers_by_author, delta):
    """Compute β(v_i, p) for author v_i on paper p."""
    ...

def author_mean_novelty(author_id, papers_by_author, delta): ...

# --- Composite ---
def author_commindex_vector(author_id, papers_by_author, delta):
    """Returns dict: {gender: Δ̃, country: Δ̃, discipline: Δ̃}"""
    ...

def author_commindex_scalar(vec):
    """Geometric mean."""
    ...