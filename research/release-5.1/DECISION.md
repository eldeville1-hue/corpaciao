# CORPACIAO 5.1 — Research Decision

**NO-GO: Do not perform popularity-aware reranking with the available Release 4.6 engagement measurements.**

The existing external acoustic baseline contains 85,490 top-10 recommendation positions across 8,549 held-out queries. Only 342 positions match tracks with observed Jamendo engagement from our earlier 400-track cohort sample. The number of queries with ten measured candidate tracks is zero. A reranking restricted to observed candidates would severely modify candidate sets and risk genre-specific missingness bias.

These source-derived values are descriptive and not a confirmatory analysis. The Jamendo field `rate_listened_total` has not been validated as historical raw plays. Missing API results must not be set to zero. The future collection plan must freeze its retrieval protocol and test missingness by genre and artist before evaluating the earlier FMA hypothesis externally.

This research decision and reproducible files are provided in the Release 5.1 package; acoustic-only baseline findings remain separate from popularity claims.
