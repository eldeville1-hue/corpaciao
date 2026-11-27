# CORPACIAO Release 6.1 — Supervised acoustic baseline and ranking stability

**Completed real-data workflow:** [GitHub Actions 45927573678](https://github.com/eldeville1-hue/corpaciao/actions/runs/45927573678). Original source catalog 55,213 MTG-Jamendo tracks. Artist-disjoint train/development/test: 38,200 / 8,464 / 8,549; fixed same 800 held-out queries as Release 6.0.

A Ridge linear model was fit using only the training partition to predict **95 genre labels** from 28 acoustic features. Ridge alpha 100.0 was selected using development artists by top-five true-genre recall; no test-query tuning. Predicted normalized label profiles were used for exact cosine retrieval.

| Method | Shared genre agreement top-10 |
|---|---:|
| Unsupervised cosine z-score | 39.75% |
| Train-genre-supervised Ridge | 40.862% |

Paired artist-cluster bootstrap difference: **+1.113 percentage points**, 95% exploratory interval **[−0.368, +2.433] pp**, spanning zero. Top-10 item overlap between methods: **8.625%**. The supervised model is directly trained on genre labels and evaluated on genre overlap; it is **not** a relevance or user preference benchmark and does not prove a stronger overall recommender.

**6.0 reproduction discrepancy explained:** 799/800 top-10 **orders** match the original 5.9; 800/800 top-10 **candidate sets** match. The one difference is a swap of ranks 7 and 8 for query 1381982, consistent with tiny float32 standardization-order effects on two near-tied cosine scores. No substantive candidate-set discrepancy.

The full reproducible package (per-query CSV, report, JSON, numerical audit) is included in the Release 6.1 downloadable artifact in ChatGPT. Source: [acoustic_supervised_61.py](../../acoustic_supervised_61.py); workflow: [.github/workflows/acoustic-supervised-61.yml](../../.github/workflows/acoustic-supervised-61.yml).

**No Jamendo statistics calls, popularity analysis or independent user relevance measurements occurred.**
