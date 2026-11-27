# CORPACIAO Research Release 5.8 — Acoustic benchmark manuscript

**Status:** Exploratory scientific paper draft based on preserved verified acoustic-only real data. No popularity statistics or Jamendo API acquisition in this release.

**Paper title:** *Acoustic Similarity, Genre-Tag Agreement, and Artist Exposure in an Artist-Disjoint Music Recommendation Benchmark.*

## Verified results

| Statistic | Result |
| --- | ---: |
| Real MTG-Jamendo tracks with acoustic descriptors | 55,213 |
| Artist-disjoint training / development / test tracks | 38,200 / 8,464 / 8,549 |
| Recommendation positions | 85,490 |
| Any-shared-genre acoustic agreement | 37.74% |
| Exact query-conditioned uniform-catalog expectation | 19.63% |
| Uplift | +18.11 percentage points |
| Exploratory artist-cluster bootstrap 95% CI | +15.70 to +20.87 pp |
| Distinct artists actually recommended | 2,348 |
| Share of exposure positions received by top 100 artists | 35.25% |
| Gini across artists receiving at least one recommendation | 0.664 |
| Mean distinct artists per ten-track list | 8.75 |

The new 5.8 recomputation independently checked the original 4.1/4.2 files and reproduced their aggregate statistics. The complete manuscript, styled standalone HTML with embedded figures, code, SHA-256 source manifest and three figures are included in **CORPACIAO_Research_Release_5_8.zip** supplied in the research conversation.

### Scientific qualifications

- Genre-label agreement is *not* human recommendation relevance or listening preference.
- A uniform-catalog comparator is *not* a competitive recommender baseline.
- Artist recommendation exposure is *not* a measure of artist popularity.
- Multi-label overlap differs from the earlier primary-genre FMA outcome.
- This is not a popularity-reranking study or a confirmatory external replication.
- The Gini excludes training artists never recommended and understates total inequality including zero-exposure artists.
- Submission requires independent review, stronger comparisons and feature ablations.

**Reproduction:** run `reproduce_58.py --baseline <Release 4.1 folder> --robustness <Release 4.2 folder> --out <new output folder>`.

**References:** [MTG-Jamendo dataset](https://github.com/MTG/mtg-jamendo-dataset), [AcousticBrainz](https://acousticbrainz.org/).
