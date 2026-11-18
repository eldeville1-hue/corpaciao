# MTG-Jamendo data audit

With Python 3.11 or later, install the dependencies in `research/requirements.txt`.
The corpus input is the `corpaciao-mtg-full-acoustic-features` ZIP from
[Actions run 44115559873](https://github.com/eldeville1-hue/corpaciao/actions/runs/44115559873).
The identical ZIP is also archived as `CORPACIAO_4_0_verified_external_features.zip`.
Use the archived Release 4.1 script `run_external_baseline.py --source CORPUS.zip --output replay`
to regenerate the rankings.

```sh
python research/audit_external.py CORPUS.zip --rankings replay/recommendations_top10.csv --output tag_audit.json
python -m unittest discover -s research
```

The audit validates the input checksum, the fixed artist split, membership,
unique top-10 lists, album separation, and every saved binary genre indicator.
It calculates query-weighted any-tag agreement, tag-set Jaccard similarity and
exact-set equality, plus their uniform-catalog expectations. Intervals resample
query artists and hold the training catalog fixed.

## Count coverage

The count audit accepts an authorized, timestamped Jamendo snapshot CSV. It
does not contact the service. Required columns are `track_id,status,
returned_track_id,returned_artist_id,listens_total,retrieved_at_utc`.
Use numeric Jamendo IDs without MTG prefixes. Explicit statuses are
`matched`, `not_returned`, `missing_field` and `request_failed`. Omitted
tracks are counted as `not_requested`. Only `matched` rows may supply a
nonnegative integer count. Preserve source responses, request provenance and
authorization separately and record their digests with the snapshot.
A syntactically valid row alone cannot establish source provenance.

```sh
python research/audit_external.py CORPUS.zip --snapshot COUNTS.csv --output count_coverage.json
```
