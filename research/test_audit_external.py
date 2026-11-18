from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import pandas as pd

from audit_external import coverage, tag_scores


class AuditTests(unittest.TestCase):
    def test_partial_overlap_is_not_exact_agreement(self):
        scores = tag_scores({"experimental", "electronic"}, {"experimental"})
        self.assertEqual(scores.tolist(), [1, .5, 0])

    def test_count_coverage_distinguishes_observed_zero_and_missing(self):
        tracks = pd.DataFrame({
            "artist_id": ["artist_8", "artist_9", "artist_9"],
            "split": ["train", "test", "test"],
            "cohort": ["other", "both", "both"],
        }, index=["42", "43", "44"])
        header = "track_id,status,returned_track_id,returned_artist_id,listens_total,retrieved_at_utc\n"
        with TemporaryDirectory() as directory:
            path = Path(directory) / "counts.csv"
            path.write_text(header + "42,matched,42,8,0,2026-11-18T12:00:00+00:00\n"
                            "43,not_returned,,,,2026-11-18T12:00:00+00:00\n")
            result = coverage(tracks, path)
            self.assertEqual(result["tracks_with_counts"], 1)
            self.assertEqual({r["status"] for r in result["by_split_and_cohort"]},
                             {"matched", "not_returned", "not_requested"})
            path.write_text(header + "42,matched,42,9,0,2026-11-18T12:00:00+00:00\n")
            with self.assertRaisesRegex(ValueError, "identity"):
                coverage(tracks, path)
