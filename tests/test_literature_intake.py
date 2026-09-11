from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


MODULE = Path(__file__).parents[1] / "mamey" / "literature_intake.py"
SPEC = importlib.util.spec_from_file_location("candidate_literature_intake", MODULE)
assert SPEC and SPEC.loader
LI = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = LI
SPEC.loader.exec_module(LI)


FIXTURE = """1. J Test. 2020;1:1-2. doi: 10.1/test. Online ahead
of print.

Characterization of a biosynthetic gene cluster.

Alpha A(1).

Author information:
(1)Example Institute.

The cluster was deleted and heterologously expressed.

DOI: 10.1/test
PMID: 100


2. J Struct. 2021;2:3-4.

Structural basis for inhibition of chitin synthase.

Beta B(1).

Author information:
(1)Example Institute.

A structure with inhibitor was determined.

PMCID: PMC200
PMID: 200
"""


class LiteratureIntakeTests(unittest.TestCase):
    def test_sequential_records_and_scopes(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "set.txt"
            path.write_text(FIXTURE, encoding="utf-8")
            rows = LI.parse_pubmed_text(path)
        self.assertEqual([row.record_number for row in rows], [1, 2])
        self.assertEqual(rows[0].record_class, "PATHWAY_BIOSYNTHESIS")
        self.assertEqual(rows[1].record_class, "ENZYME_OR_STRUCTURE")
        self.assertEqual(rows[0].title, "Characterization of a biosynthetic gene cluster.")
        self.assertIn("Online ahead of print", rows[0].citation_line)
        self.assertEqual(rows[0].pmid, "100")
        self.assertEqual(rows[1].pmcid, "PMC200")

    def test_parser_does_not_admit_to_bgc(self):
        self.assertIn("does not establish", LI.CLAIM_CEILING)
        self.assertNotIn("bgc_id", LI.LiteratureRecord.__dataclass_fields__)


if __name__ == "__main__":
    unittest.main()
