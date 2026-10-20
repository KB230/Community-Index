import numpy as np
from scipy import stats
import pandas as pd

scores = pd.read_csv("results_extended/author_scores_delta05.csv")
multi = scores[scores["n_papers"] >= 2].copy()

# Add h-index
import json
with open("author_topics.json") as f:
    topics = json.load(f)
h_lookup = {k: v["h_index"] for k, v in topics.items() if v and v.get("h_index")}
multi["h_index"] = multi["author_anon_id"].map(h_lookup)

# Composite
multi["composite_2d"] = np.sqrt(multi["delta_country"] * multi["delta_discipline"])

# Correlation
valid = multi[["h_index", "composite_2d"]].dropna()
rho, p = stats.spearmanr(valid["h_index"], valid["composite_2d"])
print(f"rho = {rho:.4f}, p = {p:.2e}, n = {len(valid)}")

# CI via Fisher z
z = np.arctanh(rho)
se = 1 / np.sqrt(len(valid) - 3)
ci_low = np.tanh(z - 1.96 * se)
ci_high = np.tanh(z + 1.96 * se)
print(f"95% CI: [{ci_low:.4f}, {ci_high:.4f}]")