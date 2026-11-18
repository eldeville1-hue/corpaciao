"""Audit MTG-Jamendo acoustic rankings or coverage of an authorized count snapshot."""
import argparse
from collections import Counter
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import re
from zipfile import ZipFile

import numpy as np
import pandas as pd


def artist_split(artist):
    digest = hashlib.sha256(f"314159|{artist}".encode()).hexdigest()
    bucket = int(digest[:15], 16) / 16**15
    return "train" if bucket < .7 else "development" if bucket < .85 else "test"


def read_corpus(path):
    with ZipFile(path) as archive:
        report = json.loads(archive.read("FEATURE_COVERAGE_REPORT.json"))
        data = archive.read("acoustic_features_joined.csv")
    digest = hashlib.sha256(data).hexdigest()
    if digest != report["joined_table_sha256"]:
        raise ValueError("joined table checksum mismatch")
    tracks = pd.read_csv(io.BytesIO(data), dtype=str, keep_default_na=False)
    if tracks.track_id.duplicated().any() or not tracks.track_id.str.fullmatch(r"[1-9][0-9]*").all():
        raise ValueError("invalid or duplicate canonical track ID")
    if (tracks[["artist_id", "album_id", "genre_tags"]] == "").any().any():
        raise ValueError("missing track metadata")
    tags = tracks.genre_tags.map(lambda value: frozenset(value.split("|")))
    if tags.map(lambda value: "" in value).any():
        raise ValueError("empty genre label")
    tracks["tags"] = tags
    tracks["split"] = tracks.artist_id.map(artist_split)
    tracks["cohort"] = tags.map(genre_cohort)
    return tracks.set_index("track_id"), digest


def genre_cohort(tags):
    experimental = "experimental" in tags
    electronic = "electronic" in tags
    if experimental and electronic:
        return "both"
    if experimental:
        return "experimental_only"
    if electronic:
        return "electronic_only"
    return "other"


def tag_scores(query, item):
    common = len(query & item)
    return np.array([common > 0, common / len(query | item), query == item])


def bootstrap(values, artists, draws=2500):
    """Query-weighted paired differences with query artists resampled as clusters."""
    index, artists = pd.factorize(artists, sort=True)
    count = np.bincount(index)
    totals = np.column_stack([np.bincount(index, weights=column) for column in values.T])
    rng = np.random.default_rng(314160)
    samples = rng.integers(len(count), size=(draws, len(count)))
    means = totals[samples].sum(axis=1) / count[samples].sum(axis=1)[:, None]
    return np.quantile(means, [.025, .975], axis=0)


def audit_rankings(tracks, rankings):
    train = tracks.loc[tracks.split.eq("train")]
    test = tracks.loc[tracks.split.eq("test")]
    rec = pd.read_csv(rankings, dtype={"query_track_id": str, "recommended_track_id": str})
    query, item = "query_track_id", "recommended_track_id"
    if set(rec[query]) != set(test.index) or not set(rec[item]) <= set(train.index):
        raise ValueError("recommendations violate train/test membership")
    if (rec.duplicated([query, item]).any() or rec.duplicated([query, "rank"]).any()
            or not rec["rank"].isin(range(1, 11)).all()
            or not rec.groupby(query).size().eq(10).all()):
        raise ValueError("invalid top-10 lists")
    if (rec.empty or
            (test.loc[rec[query], "album_id"].to_numpy() ==
             train.loc[rec[item], "album_id"].to_numpy()).any()):
        raise ValueError("empty rankings or same-album recommendation")
    scores = np.stack([tag_scores(q, t) for q, t in zip(test.loc[rec[query], "tags"],
                                                       train.loc[rec[item], "tags"], strict=True)])
    if not np.array_equal(scores[:, 0], rec.any_genre_overlap.to_numpy()):
        raise ValueError("saved agreement labels disagree with source tags")
    observed = pd.DataFrame(scores, index=rec[query]).groupby(level=0).mean().reindex(test.index)
    label_counts = Counter(train.tags)
    frequencies = np.array(list(label_counts.values())) / len(train)
    expected_by_label = {
        query_tags: frequencies @ np.stack([tag_scores(query_tags, item_tags) for item_tags in label_counts])
        for query_tags in set(test.tags)
    }
    expected = np.stack([expected_by_label[label] for label in test.tags])
    actual = observed.to_numpy()
    cohorts = {"all": np.ones(len(test), dtype=bool)}
    cohorts.update({cohort: test.cohort.eq(cohort).to_numpy() for cohort in sorted(set(test.cohort))})
    results = []
    for cohort, mask in cohorts.items():
        delta = actual[mask] - expected[mask]
        artists = test.artist_id.to_numpy()[mask]
        intervals = bootstrap(delta, artists)
        for i, metric in enumerate(("any_tag", "jaccard", "exact_tag_set")):
            results.append({
                "cohort": cohort, "metric": metric, "queries": int(mask.sum()),
                "artists": len(set(artists)), "acoustic_pct": 100 * actual[mask, i].mean(),
                "uniform_expected_pct": 100 * expected[mask, i].mean(),
                "difference_pp": 100 * delta[:, i].mean(),
                "ci_low_pp": 100 * intervals[0, i], "ci_high_pp": 100 * intervals[1, i],
            })
    return results


def coverage(tracks, snapshot):
    counts = pd.read_csv(snapshot, dtype=str, keep_default_na=False).set_index("track_id")
    if counts.index.has_duplicates or not set(counts.index) <= set(tracks.index):
        raise ValueError("duplicate or out-of-corpus count IDs")
    counts = counts.reindex(tracks.index, fill_value="")
    statuses = {"matched", "not_returned", "missing_field", "request_failed", ""}
    if not set(counts.status) <= statuses or (counts.loc[counts.status.ne("matched"), "listens_total"] != "").any():
        raise ValueError("invalid coverage status or counts on unmatched rows")
    for row in counts.loc[counts.status.ne("")].itertuples():
        when = datetime.fromisoformat(row.retrieved_at_utc)
        if when.utcoffset() is None or when.utcoffset().total_seconds() != 0:
            raise ValueError("timezone-aware UTC retrieval time required")
        if row.status == "matched":
            if (row.returned_track_id != row.Index or
                    row.returned_artist_id != tracks.at[row.Index, "artist_id"].removeprefix("artist_") or
                    not re.fullmatch(r"[0-9]+", row.listens_total)):
                raise ValueError("count row lacks exact track/artist identity or an integer count")
    joined = tracks[["split", "cohort"]].join(counts[["status"]])
    joined["status"] = joined.status.replace("", "not_requested")
    cells = joined.groupby(["split", "cohort", "status"]).size().rename("tracks").reset_index()
    return {"source": "Jamendo tracks API / stats.listens_total",
            "snapshot_sha256": hashlib.sha256(snapshot.read_bytes()).hexdigest(),
            "corpus_tracks": len(tracks), "tracks_with_counts": int(joined.status.eq("matched").sum()),
            "by_split_and_cohort": cells.to_dict(orient="records")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus", type=Path)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--rankings", type=Path)
    source.add_argument("--snapshot", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    tracks, digest = read_corpus(args.corpus)
    if args.rankings:
        result = {"rankings_sha256": hashlib.sha256(args.rankings.read_bytes()).hexdigest(),
                  "acoustic_only": audit_rankings(tracks, args.rankings)}
    else:
        result = coverage(tracks, args.snapshot)
    result["corpus_csv_sha256"] = digest
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
