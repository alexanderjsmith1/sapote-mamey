#!/usr/bin/env python3
"""Standalone tests for the clade deep-dive apparatus. Stdlib only; NO external tools/network.

Covers:
  * clade_ani  — fastANI output parsing, matrix build, sign-off boundary flags, nearest-named.
  * clade_decontam — binning logic on a synthetic contig set (GC/cov + summed-bitscore rules).
  * clade_nt_core_bgc — codon syn/nonsyn counter on tiny codon pairs; RBH; weighted identity.
  * clade_deepdive — orchestrator writes a synthesis with all six section headers and skips
                     each track with a note when its input is absent (no external tool called).

Run:  python3 tests/test_clade_deepdive.py
"""
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(os.path.dirname(HERE), "deliverable_tools")
sys.path.insert(0, TOOLS)

import clade_ani          # noqa: E402
import clade_decontam     # noqa: E402
import clade_nt_core_bgc as ntc  # noqa: E402
import clade_deepdive     # noqa: E402


class TestCladeAni(unittest.TestCase):
    def test_boundary_flags(self):
        self.assertTrue(clade_ani.boundary_flag(98.0).startswith("same_species"))
        self.assertTrue(clade_ani.boundary_flag(94.65).startswith("BOUNDARY"))  # Nocardia 188/932
        self.assertTrue(clade_ani.boundary_flag(95.5).startswith("BOUNDARY"))
        self.assertTrue(clade_ani.boundary_flag(89.72).startswith("candidate_distinct"))
        self.assertEqual(clade_ani.boundary_flag(None), "no_alignment")

    def test_parse_and_matrix(self):
        # tab-separated fastANI output: query ref ani mapped total (paths -> basenames)
        text = "\t".join(["AS-188.fna", "AS-932.fna", "94.65", "900", "1000"]) + "\n" + \
               "\t".join(["AS-932.fna", "AS-188.fna", "94.60", "890", "1000"]) + "\n" + \
               "\t".join(["AS-188.fna", "Nocardia_farcinica_type.fna", "88.10", "700", "1000"])
        pairs = clade_ani.parse_fastani(text)
        self.assertAlmostEqual(pairs[("AS-188", "AS-932")]["ani"], 94.65)
        self.assertEqual(pairs[("AS-188", "AS-932")]["mapped"], 900)
        labels = sorted({l for pr in pairs for l in pr})
        mat = clade_ani.build_matrix(pairs, labels)
        self.assertEqual(mat["AS-188"]["AS-188"], 100.0)
        self.assertAlmostEqual(mat["AS-188"]["AS-932"], 94.65)

    def test_nearest_named(self):
        text = "\t".join(["AS-188.fna", "Nocardia_farcinica_type.fna", "88.10", "700", "1000"]) + "\n" + \
               "\t".join(["AS-188.fna", "AS-932.fna", "94.65", "900", "1000"])
        pairs = clade_ani.parse_fastani(text)
        labels = sorted({l for pr in pairs for l in pr})
        rows = clade_ani.nearest_named(pairs, labels)
        # only AS-188 is a query; its nearest NAMED type is the farcinica type (AS-932 is a query)
        r = [x for x in rows if x["strain"] == "AS-188"][0]
        self.assertEqual(r["nearest_named"], "Nocardia_farcinica_type")
        self.assertTrue(r["flag"].startswith("candidate_distinct"))

    def test_is_named_type(self):
        self.assertFalse(clade_ani.is_named_type("AS-188"))
        self.assertFalse(clade_ani.is_named_type("SID1234"))
        self.assertTrue(clade_ani.is_named_type("Nocardia_farcinica_type"))


class TestDecontam(unittest.TestCase):
    def test_gc_and_cov(self):
        self.assertAlmostEqual(clade_decontam.gc_percent("GGCC"), 100.0)
        self.assertAlmostEqual(clade_decontam.gc_percent("ATAT"), 0.0)
        self.assertAlmostEqual(clade_decontam.cov_from_header("NODE_1_length_290000_cov_7.9"), 7.9)
        self.assertIsNone(clade_decontam.cov_from_header("contig_no_cov_field_here_x"))

    def test_assign_contig_rules(self):
        # strong target reference match -> target (KEEP)
        self.assertEqual(clade_decontam.assign_contig(68.0, 3.6, 5000, 100, target_gc=68), "target")
        # strong contaminant reference match -> contaminant (REMOVE)
        self.assertEqual(clade_decontam.assign_contig(71.7, 9.2, 100, 5000, target_gc=68),
                         "contaminant")
        # neither ref decisive, GC ~ target -> keep (target-like)
        self.assertEqual(clade_decontam.assign_contig(67.9, 3.8, 0, 0, target_gc=68),
                         "unassigned_target_like")
        # neither ref, low GC incompatible with target -> unknown other (REMOVE)
        self.assertEqual(clade_decontam.assign_contig(35.3, 7.9, 0, 0, target_gc=68),
                         "other_lowGC")

    def test_bin_synthetic_contigs(self):
        # a synthetic 3-way mixture like AS-922: Nocardia (keep), Micromonospora (remove),
        # low-GC third organism (remove).
        contigs = [
            ("NODE_1_length_290000_cov_7.9", "AT" * 60),          # ~0% GC, low-GC third organism
            ("NODE_2_length_50000_cov_3.6", "GC" * 60),           # 100% GC placeholder Nocardia
            ("NODE_3_length_40000_cov_9.2", "GCGC" * 30),         # high GC Micromonospora
        ]
        target_bits = {"NODE_2_length_50000_cov_3.6": 6000.0}     # matches Nocardia ref
        contam_bits = {"NODE_3_length_40000_cov_9.2": 6000.0}     # matches Micromonospora ref
        rows = clade_decontam.bin_contigs(contigs, target_bits, contam_bits,
                                          target_gc=68.0, gc_tol=10.0)
        by = {r["contig"]: r for r in rows}
        self.assertEqual(by["NODE_2_length_50000_cov_3.6"]["assignment"], "target")
        self.assertTrue(by["NODE_2_length_50000_cov_3.6"]["keep"])
        self.assertEqual(by["NODE_3_length_40000_cov_9.2"]["assignment"], "contaminant")
        self.assertFalse(by["NODE_3_length_40000_cov_9.2"]["keep"])
        self.assertEqual(by["NODE_1_length_290000_cov_7.9"]["assignment"], "other_lowGC")
        self.assertFalse(by["NODE_1_length_290000_cov_7.9"]["keep"])
        # cov parsed on every contig
        self.assertAlmostEqual(by["NODE_1_length_290000_cov_7.9"]["cov"], 7.9)

    def test_parse_summed_bitscores(self):
        text = "c1\tref1\t99\t500\t800\nc1\tref1\t98\t400\t600\nc2\tref1\t95\t300\t400"
        sums = clade_decontam.parse_summed_bitscores(text)
        self.assertAlmostEqual(sums["c1"], 1400.0)
        self.assertAlmostEqual(sums["c2"], 400.0)


class TestNtCoreBgc(unittest.TestCase):
    def test_codon_syn_nonsyn(self):
        # AAA(Lys) vs AAG(Lys) = synonymous; second codon identical
        diff, syn, nonsyn = ntc.codon_syn_nonsyn("ATGAAA", "ATGAAG")
        self.assertEqual((diff, syn, nonsyn), (1, 1, 0))
        # AAA(Lys) vs GAA(Glu) = non-synonymous
        diff, syn, nonsyn = ntc.codon_syn_nonsyn("ATGAAA", "ATGGAA")
        self.assertEqual((diff, syn, nonsyn), (1, 0, 1))
        # identical -> nothing
        self.assertEqual(ntc.codon_syn_nonsyn("ATGAAA", "ATGAAA"), (0, 0, 0))

    def test_translate(self):
        self.assertEqual(ntc.translate_codon("ATG"), "M")
        self.assertEqual(ntc.translate_codon("TAA"), "*")

    def test_nt_identity_and_weighted(self):
        ident, aln, pid = ntc.nt_identity("ACGTACGT", "ACGAACGT")  # 1 mismatch / 8
        self.assertEqual((ident, aln), (7, 8))
        self.assertAlmostEqual(pid, 87.5)
        pid, tid, taln = ntc.weighted_identity([(90, 100), (180, 200)])
        self.assertAlmostEqual(pid, 100.0 * 270 / 300)

    def test_reciprocal_best_hits(self):
        # A genes a1,a2 ; B genes b1,b2. a1<->b1 reciprocal; a2->b1 but b2->a1 (not reciprocal)
        cols = "\t".join
        ab = ntc.parse_blast_tab(
            cols(["a1", "b1", "99", "500", "500", "500", "495", "900"]) + "\n" +
            cols(["a2", "b1", "80", "400", "500", "500", "320", "300"]),
            min_pident=50, min_cov=0.5)
        ba = ntc.parse_blast_tab(
            cols(["b1", "a1", "99", "500", "500", "500", "495", "900"]) + "\n" +
            cols(["b2", "a1", "80", "400", "500", "500", "320", "300"]),
            min_pident=50, min_cov=0.5)
        rbh = ntc.reciprocal_best_hits(ab, ba)
        self.assertIn(("a1", "b1"), rbh)
        self.assertEqual(len(rbh), 1)

    def test_blast_coverage_filter(self):
        # a hit below coverage 0.7 is dropped
        row = "\t".join(["a1", "b1", "99", "100", "500", "500", "99", "180"])  # cov 0.2
        self.assertEqual(ntc.parse_blast_tab(row), [])


class TestOrchestrator(unittest.TestCase):
    def test_synthesis_skeleton_all_headers_and_skips(self):
        with tempfile.TemporaryDirectory() as d:
            empty_genomes = os.path.join(d, "genomes")   # exists but no FASTAs
            os.makedirs(empty_genomes)
            out = os.path.join(d, "out")
            # everything absent -> every track must skip-with-note, no external tool invoked
            results, synth = clade_deepdive.run(
                "Nocardia", empty_genomes, db=None,
                strains="AS-188,AS-190,AS-932", out=out)
            self.assertTrue(os.path.exists(synth))
            with open(synth) as fh:
                text = fh.read()
            # all six section headers present
            for _key, header, _desc in clade_deepdive.SECTIONS:
                self.assertIn(header, text, f"missing section header: {header}")
            # every track skipped with a note
            self.assertEqual(len(results), 6)
            for key in [k for k, _h, _d in clade_deepdive.SECTIONS]:
                self.assertEqual(results[key]["status"], "skipped", f"{key} should skip")
                self.assertIn("note", results[key])
            self.assertIn("SKIPPED", text)
            # claim-safety + sign-off gate present
            self.assertIn("Judgment deferred", text)
            self.assertIn("sister group", text)

    def test_write_synthesis_fills_ok_metrics(self):
        with tempfile.TemporaryDirectory() as d:
            results = {
                "ani": {"status": "ok", "n_pairs": 10, "n_boundary": 2},
                "bigscape_matrix": {"status": "skipped", "note": "no DB"},
                "conserved_dark": {"status": "skipped", "note": "no proteomes"},
                "nt_core_bgc": {"status": "ok", "n_strains": 5},
                "decontam": {"status": "skipped", "note": "not flagged"},
                "clinker": {"status": "skipped", "note": "no DB"},
            }
            synth = os.path.join(d, "X_SYNTHESIS.md")
            clade_deepdive.write_synthesis("X", results, synth, strains=["AS-1"])
            with open(synth) as fh:
                text = fh.read()
            self.assertIn("Tracks completed:** 2/6", text)
            self.assertIn("n_boundary", text)
            self.assertIn("[DONE]", text)
            self.assertIn("[SKIPPED]", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
