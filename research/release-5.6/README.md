# CORPACIAO Research Release 5.6 — Prospective coverage feasibility

**Status:** completed real recommendation-graph audit + hypothetical track-observability simulation. **No new Jamendo API calls.**

Data inputs:
- Release 4.1: 8,549 actual queries; 85,490 recommendation positions; 29,259 unique recommended tracks.
- Release 5.2: 2,000 sampled tracks; 1,065 measured Jamendo engagement rates, covering 560 unique recommended tracks and **0 complete 10-item lists**.

We modeled *hypothetical independent per-track observability*, maintaining shared status whenever the same track appears in different queries. For track coverage probability `p`, expected completely measured top-10 lists are `8,549 × p^10`. Reproducible simulation used 800 iterations per scenario and seed `2026112756`.

| Hypothetical per-track coverage | Expected complete 10-item lists |
| --- | ---: |
| 53.25% | 15.7 |
| 60.25% | 53.9 |
| 70% | 241.5 |
| 75% | 481.4 |
| 80% | 917.9 |
| 81% | 1,039.4 |
| 85% | 1,683.1 |
| 90% | 2,980.9 |

**Operational threshold:** `(1000/8549)^(1/10) = 80.6879%` independent per-track observability for an *expected* 1,000 completely measured lists. This is **not** a statistical power guarantee, observed Jamendo coverage estimate, or license to collect more data. Dependence by artist, genre and API response can yield substantially different results.

Gmail check 2026-11-27: original inquiry sent to Jamendo on November 19 (two copies); no substantive reply located. Follow-up prepared in the original thread as Gmail draft, **not sent**.

**Decision:** maintain NO-GO for confirmatory reranking and broad Jamendo acquisition. Resolve research permission and metric semantics; consider prospective power analysis and missingness-aware redesign. Full executable analysis and input SHA-256 are in the Release 5.6 artifact accompanying the chat.
