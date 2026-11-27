# CORPACIAO Release 6.0 — Controlled acoustic distance benchmark

**Status:** Successful real-data GitHub Actions run [45927274022](https://github.com/eldeville1-hue/corpaciao/actions/runs/45927274022). No Jamendo statistics API requests or popularity-related outcome testing.

All methods evaluated on the *same* 800 stratified, artist-disjoint test queries as Release 5.9, with identical 38,200-track training catalog. Genre agreement is any-overlapping-label precision@10, **not human preference**.

| Method | Shared genre agreement | Avg distinct artists / 10 | Top-10 overlap with cosine z-score |
|---|---:|---:|---:|
| Cosine, z-score | 39.75% | 8.82 | 100% |
| Euclidean, z-score | 39.10% | 9.02 | 58.43% |
| Manhattan, z-score | 39.21% | 9.03 | 45.16% |
| Cosine, robust scaling | 40.41% | 8.77 | 64.19% |
| Random catalog, single sample | 22.35% | 9.91 | 0.04% |

Exact query-conditioned random-catalog agreement expectation: 22.8972% (the single sampled random output was 22.35%).

Paired artist-cluster bootstrap 95% difference intervals relative to the cosine-z baseline, pp: Euclidean −0.650 [−1.634,+0.404]; Manhattan −0.537 [−1.668,+0.511]; robust cosine +0.662 [−0.185,+1.646]; uniform random −17.400 [−20.351,−14.673].

Audit: the independently recomputed cosine-z nearest-neighbor lists were **exactly identical for 799/800 queries** to Release 5.9. One list differs; its exact numerical/tie cause was not established. Do not silently call 800/800 reproduced.

Takeaway: Different acoustic distance metrics deliver similar label-agreement averages but substantial recommendation turnover. None of the three acoustic distance alternatives shows a clearly positive or negative paired difference from baseline at this uncertainty level. A stronger learned/embedding baseline, human preference or retrieval evaluation, and review of the 1/800 discrepancy are required for a publishable state-of-the-art claim.

Data: [reproduction script](../../acoustic_benchmark_60.py), [GitHub workflow](../../.github/workflows/acoustic-benchmark-60.yml). Full per-query outputs, JSON, CSV and report accompany the Release 6.0 artifact attached to the research conversation.
