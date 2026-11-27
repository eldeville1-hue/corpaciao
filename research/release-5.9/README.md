# CORPACIAO 5.9 — Verified acoustic feature ablation

**Status:** Successful GitHub Actions run [45926532856](https://github.com/eldeville1-hue/corpaciao/actions/runs/45926532856). Real MTG-Jamendo features; no Jamendo API/popularity data.

Full 55,213-track catalog; artist-disjoint 38,200 training and 8,549 test tracks; fixed 800-query genre-stratified test subset; six prespecified cosine nearest-neighbor variants.

| Model | Features | Shared-genre agreement | Top-10 overlap with 28-feature model |
|---|---:|---:|---:|
| Full | 28 | 39.75% | 100% |
| Correlation-pruned | 25 | 39.81% | 88.53% |
| Equal-weight feature groups | 28 | 39.74% | 50.18% |
| Low-level only | 18 | 36.28% | 9.03% |
| Rhythm only | 3 | 29.05% | 0.34% |
| Tonal only | 7 | 31.31% | 2.24% |

Paired artist-cluster bootstrap 95% difference intervals relative to full: pruned +0.063 pp [−0.416,+0.534]; equal groups −0.012 pp [−1.064,+1.075]; low-level −3.475 pp [−4.866,−1.991]; rhythm −10.700 pp [−13.136,−8.506]; tonal −8.438 pp [−10.544,−6.242].

**Conclusions:** Results are fairly robust to correlation pruning; strong dependence on feature family; equal-weight groups largely preserve the score but reorder about half the recommended tracks. Genre agreement is not a user relevance outcome. This stratified experiment must not be conflated with the 8,549-query full baseline. No popularity hypothesis or independent external replication was tested.

Raw machine-readable report and per-query top-ten outputs are in the Release 5.9 artifact attached to the chat. [Reproduction script](../../acoustic_ablation_59.py); [workflow](../../.github/workflows/acoustic-ablation-59.yml).
