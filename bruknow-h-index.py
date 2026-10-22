from pyalex import Works, config

config.email = "arav.kumar910@gmail.com"

# Fetch all Brunkow's articles (type=article only), with citation counts
articles = []
for page in Works().filter(
    author={"id": "A5072638080"},
    type="article"
).paginate(per_page=200, n_max=None):
    for w in page:
        articles.append(w.get("cited_by_count", 0))

# Compute h-index
articles_sorted = sorted(articles, reverse=True)
h = 0
for i, citations in enumerate(articles_sorted, start=1):
    if citations >= i:
        h = i
    else:
        break

print(f"Articles only: n = {len(articles)}, h-index = {h}")


articles = []
for page in Works().filter(
    author={"id": "A5072638080"},
    type="article",
    publication_year="-2025"  # up to and including 2025
).paginate(per_page=200, n_max=None):
    for w in page:
        articles.append(w.get("cited_by_count", 0))

articles_sorted = sorted(articles, reverse=True)
h = 0
for i, c in enumerate(articles_sorted, start=1):
    if c >= i:
        h = i
    else:
        break

print(f"Articles ≤2025: n = {len(articles)}, h-index = {h}")