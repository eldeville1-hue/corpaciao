# CORPACIAO Release 5.5 — Measured-candidate coverage

**Status: completed real-data cross-release audit; no-go for popularity reranking with the current pilot.**

The project audited the actual Release 4.1 `recommendations_top10.csv` (8,549 queries, 85,490 positions) against Release 5.2 `pilot_observations.csv` (2,000 sampled tracks; 1,065 numeric Jamendo rates). No API calls or popularity reranking were made.

- Distinct recommended track IDs: **29,259**
- Distinct recommended tracks matched to measured API rates: **560**
- Matched recommendation positions: **1,653 / 85,490 = 1.9336%**
- Queries with at least one measured recommended item: **1,536 / 8,549**
- Queries with all ten recommendations measured: **0 / 8,549**

| Query cohort | Queries | Measured positions | Total positions |
| --- | ---: | ---: | ---: |
| Experimental-only | 170 | 33 | 1,700 |
| Electronic-only | 2,192 | 375 | 21,920 |
| Both | 207 | 38 | 2,070 |
| Other | 5,980 | 1,207 | 59,800 |

Source SHA-256:
- `pilot_observations.csv`: `2ce894f6469ddb981280883ee8a4ba34d5f79f06ad86f8ef417bc34056e7df69`
- `recommendations_top10.csv`: `5830fb0a16ab87f933f38b77ff09d4945e77a1fc1152caba4219bf0d4a60a3e3`
- `query_metrics.csv`: `d1b95955a5fc51e45f6de8d3ea713493957e57789f166ec0787975a8ec78aebd`

**Correspondence:** Gmail confirmed two sent inquiries to `api@jamendo.com` on November 19, 2026; no substantive reply was visible on November 27. A follow-up is saved as a draft in the same Gmail thread; it has **not** been sent.

**Research decision:** The current 5.2 pilot is not sufficient to evaluate popularity-aware reranking on complete 4.1 candidate sets. Do not equate missing values with zero listening activity. Do not interpret `rate_listened_total` as historical raw plays without documented semantics. Do not initiate bulk metadata collection until legal/permission scope is clarified.

The complete reproducible source script, full query-level table, JSON results and report are supplied as a Release 5.5 ZIP in the accompanying research conversation.
