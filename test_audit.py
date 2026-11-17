import tempfile
import unittest
from pathlib import Path
from audit_cohorts import parse, cohort, split, audit

class CohortTests(unittest.TestCase):
    def test_cohorts(self):
        self.assertEqual(cohort({"experimental"}),"experimental_only")
        self.assertEqual(cohort({"electronic"}),"electronic_only")
        self.assertEqual(cohort({"experimental","electronic"}),"both")
        self.assertEqual(cohort(set()),"other")
    def test_split_determinism(self):
        self.assertEqual(split("artist123",314159),split("artist123",314159))
    def test_valid_fixture(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"fixture.tsv"
            p.write_text("track_id\tartist_id\talbum_id\tpath\tduration\ttag\n1\tA\tB\tx\t10\tgenre---experimental\n2\tC\tD\tx\t20\tgenre---electronic\n",encoding="utf8")
            r=audit(p,Path(d)/"out")
            self.assertEqual(r["experimental_tag"]["tracks"],1)
            self.assertEqual(r["electronic_tag"]["tracks"],1)
            self.assertEqual(r["artist_split_leakage_count"],0)
    def test_duplicate_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"dup.tsv"
            p.write_text("1\tA\tB\tx\t10\tgenre---experimental\n1\tC\tD\tx\t20\tgenre---electronic\n")
            with self.assertRaises(ValueError):audit(p,Path(d)/"out")
if __name__=="__main__":unittest.main()
