# CORPACIAO 5.7 — Alternative Designs and Selection Audit

**Release 5.7 is a real cross-release analysis of actual Release 4.1 top-10 recommendations and Release 5.2 API-observed rate values. No new Jamendo API requests, no reranking effect estimated.**

| Cohort | Queries | ≥1 measured candidate | ≥2 | ≥3 | ≥5 | Complete top-10 |
|---|---:|---:|---:|---:|---:|---:|
| Experimental-only | 170 | 30 | 3 | 0 | 0 | 0 |
| Electronic-only | 2,192 | 356 | 18 | 1 | 0 | 0 |
| Both | 207 | 37 | 1 | 0 | 0 | 0 |
| Other | 5,980 | 1,113 | 93 | 1 | 0 | 0 |
| **Total** | **8,549** | **1,536** | **115** | **2** | **0** | **0** |

Across 85,490 recommendation positions, 1,653 (1.93%) have a measured numeric Jamendo `rate_listened_total` value from 5.2. There are only 119 observable within-top-10 candidate pairs, which can overlap across queries. No full candidate sets are measured.

Descriptive selection warning: measured positions within Electronic-only queries show any-shared-genre agreement of 62.4% (n=375) versus 53.1% (n=21,545) for unmeasured positions. Experimental-only: 39.4% (n=33) vs 27.8% (n=1,667). This is not a causal finding.

**Decision:** no-go for complete top-10 popularity reranking, partial top-5 reranking, and intended cross-genre pairwise reranking with the current observed subset. Acoustic-only analyses remain feasible but cannot establish effects of popularity. Prospective power cannot be responsibly quantified without a validated popularity measure, qualified candidate sampling, artist-cluster outcome variance, and a preselected target effect.

The Release 5.7 ZIP provided in the conversation includes the Python reproduction script, per-query eligibility table, descriptive selection diagnostics, hypothetical binomial coverage scenarios, machine-readable report, and SHA-256 source provenance.

**Permission gate remains in effect** pending Jamendo's response. Missing is not zero; engagement rate is not verified as raw plays.
