# CORPACIAO Release 6.2 — Transfer to instrument and mood/theme annotation tasks

**Completed real-data workflow:** [GitHub Actions 45927886892](https://github.com/eldeville1-hue/corpaciao/actions/runs/45927886892).

Frozen recommendations from six methods, the same 800 artist-disjoint test queries as Releases 5.9–6.1, and official [MTG-Jamendo instrument](https://github.com/MTG/mtg-jamendo-dataset/blob/master/data/autotagging_instrument.tsv) and [mood/theme](https://github.com/MTG/mtg-jamendo-dataset/blob/master/data/autotagging_moodtheme.tsv) annotation tasks. No new model training or Jamendo engagement-statistics API calls.

| Method | Instrument overlap, conditional on both labels present | Mood/theme overlap, conditional on both labels present |
| --- | ---: | ---: |
| Cosine z-score | **52.02%** | **12.29%** |
| Euclidean z-score | 52.60% | 12.25% |
| Manhattan z-score | 51.81% | 11.58% |
| Cosine robust | 52.48% | 11.60% |
| Supervised Ridge (genre-trained) | 50.95% | 11.68% |
| Uniform random, one sample | 31.34% | 5.03% |

**Missing annotations strongly limit interpretation.** Only **327/800 test queries have nonempty instrument labels**, **226/800 have mood/theme labels**. Under cosine z-score, just **1,532/8,000** instrument pair positions and **846/8,000** mood/theme pair positions have usable labels on both sides. Conditional rates *exclude* unlabelled comparisons and are susceptible to selection effects.

For an all-position count retaining annotation absence as missing matches, cosine z-score had 9.963% instrument-tag matches and 1.30% mood/theme matches across all 8,000 positions; these are not estimates of actual relevance when labels are missing. Versus cosine z-score, Ridge's paired artist-cluster interval was [−0.654,+0.906] pp for instrument and [−0.424,+0.345] pp for mood/theme; neither shows a clear advantage. The uniform-random variant was lower by −4.538 pp for instrument and −0.838 pp for mood/theme on the all-position metric, with exploratory bootstrap intervals excluding zero.

**Conclusion:** the acoustic ranking signal transfers beyond genre labels, but these annotations originate from the same parent dataset; this is *cross-task tag consistency*, not independent listener preference judgments or popularity-bias validation. Future research needs a legally grounded external human/listening relevance criterion before claims about recommendation quality for listeners.

Complete Report, JSON, 12 per-query CSVs, source checksums and methodology are in the Release 6.2 ZIP linked in the research conversation. Source code: [cross_task_evaluation_62.py](../../cross_task_evaluation_62.py). Workflow: [.github/workflows/cross-task-evaluation-62.yml](../../.github/workflows/cross-task-evaluation-62.yml).
