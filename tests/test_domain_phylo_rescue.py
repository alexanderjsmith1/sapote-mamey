"""test_domain_phylo_rescue.py — P358-003 (Aquarius, 2026-08-10).

Pins the two-proof discipline of the advisory domain-phylogeny corroborator (Idea A.2 + guard E):
  * a supported cross-BGC KS clade WITH an RG-GMCI homology row  -> CORROBORATED_SPLIT (rescue).
  * a supported cross-BGC KS clade WITHOUT RG-GMCI               -> DOMAIN_ONLY_HINT (never a rescue).
  * FAS / fatty_acid (outgroup) and DROP-class domains never corroborate.
  * a low-support clade never corroborates.
Fixtures mirror Amber's AS-705 KS tree (NODE_24/NODE_30 trans-AT; NODE_58/NODE_216 cis-AT; NODE_74/72 FAS).
"""
from __future__ import annotations

import csv
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tools" / "domain_phylo_rescue.py"
_spec = importlib.util.spec_from_file_location("domain_phylo_rescue", TOOL)
dpr = importlib.util.module_from_spec(_spec)
sys.modules["domain_phylo_rescue"] = dpr
_spec.loader.exec_module(dpr)


def _write_tsv(path: Path, fieldnames, rows):
    with path.open("w", encoding="utf-8", newline="") as h:
        w = csv.DictWriter(h, fieldnames=fieldnames, delimiter="\t", lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def _write_csv(path: Path, fieldnames, rows):
    with path.open("w", encoding="utf-8", newline="") as h:
        w = csv.DictWriter(h, fieldnames=fieldnames, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow(r)


class DomainPhyloRescueTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        clade_fields = ["domain_id", "bgc_id", "domain_class", "clade_id", "shalrt", "ufboot", "label"]
        clade_rows = [
            # trans-AT clade: two distinct BGCs, high support -> co-cluster
            {"domain_id": "NODE_24_transAT_KS2", "bgc_id": "BGC_A", "domain_class": "PKS_KS",
             "clade_id": "C_transAT", "shalrt": 99.7, "ufboot": 100, "label": "transAT-PKS"},
            {"domain_id": "NODE_30_transAT_KS1", "bgc_id": "BGC_B", "domain_class": "PKS_KS",
             "clade_id": "C_transAT", "shalrt": 99.7, "ufboot": 100, "label": "transAT-PKS-like"},
            # cis-AT clade: two distinct BGCs, high support -> co-cluster (no RG-GMCI corroboration)
            {"domain_id": "NODE_58_T1PKS_KS5", "bgc_id": "BGC_C", "domain_class": "PKS_KS",
             "clade_id": "C_cisAT", "shalrt": 100, "ufboot": 99, "label": "T1PKS"},
            {"domain_id": "NODE_216_T1PKS_KS2", "bgc_id": "BGC_D", "domain_class": "PKS_KS",
             "clade_id": "C_cisAT", "shalrt": 100, "ufboot": 99, "label": "T1PKS"},
            # FAS outgroup clade: two BGCs but must be EXCLUDED by the convergence guard
            {"domain_id": "NODE_74_fatty_acid_KS2", "bgc_id": "BGC_E", "domain_class": "fatty_acid_KS",
             "clade_id": "C_FAS", "shalrt": 99, "ufboot": 100, "label": "fatty_acid"},
            {"domain_id": "NODE_72_fatty_acid_KS1", "bgc_id": "BGC_F", "domain_class": "fatty_acid_KS",
             "clade_id": "C_FAS", "shalrt": 99, "ufboot": 100, "label": "fatty_acid"},
            # low-support clade: two BGCs but below thresholds -> must NOT corroborate
            {"domain_id": "NODE_40_T1PKS_KS1", "bgc_id": "BGC_G", "domain_class": "PKS_KS",
             "clade_id": "C_weak", "shalrt": 30.9, "ufboot": 41, "label": "T1PKS"},
            {"domain_id": "NODE_17_KS2", "bgc_id": "BGC_H", "domain_class": "PKS_KS",
             "clade_id": "C_weak", "shalrt": 30.9, "ufboot": 41, "label": "T1PKS"},
        ]
        self.clades = self.d / "clades.tsv"
        _write_tsv(self.clades, clade_fields, clade_rows)

        # RG-GMCI corroborates ONLY {BGC_A, BGC_B}
        self.rggmci = self.d / "pkg_4A_RGGMCI_ranked_pairs.csv"
        _write_csv(self.rggmci, ["query_bgc", "partner_bgc", "rggmci_confidence"], [
            {"query_bgc": "BGC_A", "partner_bgc": "BGC_B", "rggmci_confidence": "HIGH_RG_GMCI_RESCUE"},
            {"query_bgc": "BGC_C", "partner_bgc": "BGC_X", "rggmci_confidence": "LOW"},  # unrelated
        ])

    def tearDown(self):
        self.tmp.cleanup()

    def _verdicts(self):
        clades = dpr.load_clades(self.clades)
        pairs = dpr.load_rggmci_pairs(self.rggmci)
        return {(_v["bgc_a"], _v["bgc_b"]): _v for _v in dpr.assess(clades, pairs)}

    def test_two_proof_corroboration(self):
        v = self._verdicts()
        self.assertIn(("BGC_A", "BGC_B"), v)
        self.assertEqual(v[("BGC_A", "BGC_B")]["verdict"], "CORROBORATED_SPLIT")
        self.assertTrue(v[("BGC_A", "BGC_B")]["is_rescue"])

    def test_domain_only_is_never_a_rescue(self):
        v = self._verdicts()
        self.assertIn(("BGC_C", "BGC_D"), v)
        self.assertEqual(v[("BGC_C", "BGC_D")]["verdict"], "DOMAIN_ONLY_HINT")
        self.assertFalse(v[("BGC_C", "BGC_D")]["is_rescue"])

    def test_fas_outgroup_excluded(self):
        v = self._verdicts()
        self.assertNotIn(("BGC_E", "BGC_F"), v)

    def test_low_support_excluded(self):
        v = self._verdicts()
        self.assertNotIn(("BGC_G", "BGC_H"), v)

    def test_no_verdict_is_scored(self):
        # Non-scoring contract: verdict dicts never carry a score/tier field.
        clades = dpr.load_clades(self.clades)
        for verdict in dpr.assess(clades, dpr.load_rggmci_pairs(self.rggmci)):
            self.assertFalse(any(k in verdict for k in ("score", "tier", "priority", "triage")))


if __name__ == "__main__":
    unittest.main()
