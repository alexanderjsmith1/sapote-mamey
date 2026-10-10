"""Renderer fixes for the gap-rescue locus map: every core row drawn, honest titles and labels.

Each test asserts on the figure's data or on a pure helper, never on pixels.
"""
import re
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "work" / "tools"
if TOOLS.is_dir():                 # running against the card's own copy
    sys.path.insert(0, str(TOOLS))
else:                              # running inside the bundle, after the diff is applied
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

# These tools import the mamey package. Find a bundle root that provides it, walking up from here and taking the
# newest bundle first: several cuts sit side by side and the older ones predate the modules the tools import.
if "mamey" not in sys.modules:
    for parent in Path(__file__).resolve().parents:
        cands = [parent] + sorted((d for d in parent.glob("sapote-mamey-v*") if d.is_dir()), reverse=True)
        hit = next((c for c in cands if (c / "mamey" / "path_safety.py").exists()), None)
        if hit:
            sys.path.insert(0, str(hit))
            break

import gap_rescue_locus_map as M          # noqa: E402
import gap_directed_rescue as D           # noqa: E402

try:
    import gap_rescue_gene_table as T     # noqa: E402
except ModuleNotFoundError as exc:        # the mamey package is not on the path here
    T = None
    _TABLE_SKIP = f"gap_rescue_gene_table needs the mamey package: {exc}"
else:
    _TABLE_SKIP = ""


def _ref(n):
    return [{"name": f"ref{i}", "product": "", "s": i * 1000, "e": i * 1000 + 800,
             "strand": 1, "kind": "biosynthetic"} for i in range(n)]


def _prots(ids, contig="ctgA"):
    return {p: {"contig": contig, "start": i * 900, "end": i * 900 + 700, "strand": 1,
                "tag": p, "contig_len": 50000} for i, p in enumerate(ids)}


def _row(status, pid, ident, reciprocal):
    return {"status": status, "best_protein": pid, "best_identity_pct": str(ident),
            "reciprocal_best": reciprocal, "best_locus": pid}


class TestCoreRowsAreAllDrawn:
    """(a) One protein can be the best match for two reference genes. Only one of those rows can be reciprocal
    best, so the other used to be dropped and its reference gene drawn grey while the table still counted it."""

    def test_shared_protein_gives_one_ribbon_per_counted_core_row(self):
        ref = _ref(2)
        prots = _prots(["p1"])
        rows = [_row("PRESENT_IN_CORE", "p1", 62.0, "True"),
                _row("PRESENT_IN_CORE", "p1", 37.0, "False")]
        drawn, _, _, not_drawn, _ = M.choose(ref, rows, [], prots, "ctgA")
        assert len(drawn) == 2, "both core rows the table counts must reach the figure"
        assert {k for k, _, _ in drawn} == {0, 1}
        assert {pid for _, pid, _ in drawn} == {"p1"}, "both ribbons land on the same local gene"
        assert not_drawn == 0

    def test_a_find_elsewhere_still_needs_reciprocal_best(self):
        """The guard is right outside the core: there a paralog can pose as the missing gene."""
        ref = _ref(2)
        prots = _prots(["p1"]) | {"p9": {"contig": "ctgB", "start": 10, "end": 900, "strand": 1,
                                         "tag": "p9", "contig_len": 20000}}
        rows = [_row("PRESENT_IN_CORE", "p1", 62.0, "True"),
                _row("MISSING_FOUND_CLEAR", "p9", 55.0, "False")]
        drawn, _, _, _, _ = M.choose(ref, rows, [], prots, "ctgA")
        assert {pid for _, pid, _ in drawn} == {"p1"}, "a non-reciprocal find outside the core stays out"

    def test_core_row_without_a_protein_is_not_invented(self):
        ref = _ref(1)
        rows = [_row("PRESENT_IN_CORE", "", 50.0, "True")]
        drawn, _, _, _, _ = M.choose(ref, rows, [], _prots(["p1"]), "ctgA")
        assert drawn == []


class TestTitle:
    """(c) A long compound list was cut at 60 characters, mid-word, and a GenBank accession was titled MIBiG."""

    def test_names_index_keeps_the_whole_compound_list(self, tmp_path):
        import json
        long_name = ["everninomicin D", "everninomicin E", "everninomicin G", "everninomicin H"]
        p = tmp_path / "names.json"
        p.write_text(json.dumps({"entries": [{"accession": "BGC0002085", "compounds": long_name}]}))
        got = D.load_mibig_names(p)["BGC0002085"]
        assert got == "/".join(long_name)
        assert len(got) > 60, "the value must not be cut back to 60 characters"
        assert not got.endswith("everninomici"), "the old cut landed mid-word"


class TestGeneNaming:
    """(e) The table prints the reference accession; the map printed only a product, so rows and arrows could
    not be matched up."""

    def test_unnamed_gene_label_carries_the_accession_the_table_prints(self):
        g = {"name": "QCT05736.1", "product": "acyl-CoA synthetase"}
        lab = M.short(g)
        assert lab.startswith("QCT05736.1"), lab
        assert "acyl-CoA synthetase" in lab

    def test_named_gene_is_unchanged(self):
        assert M.short({"name": "valC", "product": "anything"}) == "ValC"

    def test_accession_only_gene_needs_no_brackets(self):
        assert M.short({"name": "QCT05736.1", "product": ""}) == "QCT05736.1"


@pytest.mark.skipif(bool(_TABLE_SKIP), reason=_TABLE_SKIP or "")
class TestAnnotation:
    """(f) A GenBank evidence note says how a record was annotated, not what a gene does."""

    @pytest.mark.parametrize("note", [
        "Derived by automated computational analysis using gene prediction method: Protein Homology.",
        "derived by automated computational analysis",
        "Evidence: inferred from similarity",
    ])
    def test_evidence_boilerplate_is_dropped(self, note):
        assert T.tidy_annotation(note) == ""

    def test_a_real_annotation_survives(self):
        assert T.tidy_annotation("probable phytoene synthase") == "probable phytoene synthase"

    def test_real_text_in_front_of_the_boilerplate_is_kept(self):
        """A note can open with something worth keeping and then run into the evidence clause."""
        got = T.tidy_annotation("frameshifted; Derived by automated computational analysis using gene "
                                "prediction method: Protein Homology.")
        assert got == "frameshifted"

    def test_a_cog_description_still_wins(self):
        assert "dehydrogenase" in T.tidy_annotation("COG: COG1234 short-chain dehydrogenase.")


class TestClaimSafety:
    """The fixes are presentation only: no status, identity or count may move."""

    def test_identities_are_passed_through_untouched(self):
        ref = _ref(2)
        prots = _prots(["p1"])
        rows = [_row("PRESENT_IN_CORE", "p1", 62.4, "True"),
                _row("PRESENT_IN_CORE", "p1", 37.4, "False")]
        drawn, _, _, _, _ = M.choose(ref, rows, [], prots, "ctgA")
        assert sorted(round(i, 1) for _, _, i in drawn) == [37.4, 62.4]


# ---------------------------------------------------------------------------------------------------------------------
# (b) A distant match on the same contig set the window, so the cluster was drawn as slivers. The contig is now drawn
#     as separate parts with the omitted stretch cut out and its length printed at the cut.
# ---------------------------------------------------------------------------------------------------------------------

def _ref_gbk(tmp_path, n=6):
    pytest.importorskip("Bio.SeqIO")
    from Bio import SeqIO
    from Bio.Seq import Seq
    from Bio.SeqFeature import FeatureLocation, SeqFeature
    from Bio.SeqRecord import SeqRecord
    rec = SeqRecord(Seq("A" * (n * 1000)), id="REF1", name="REF1", description="test cluster",
                    annotations={"molecule_type": "DNA"})
    for i in range(n):
        rec.features.append(SeqFeature(FeatureLocation(i * 1000, i * 1000 + 900, strand=1), type="CDS",
                                       qualifiers={"gene": ["abc" + "ABCDEF"[i]], "translation": ["M" * 290]}))
    gbk = tmp_path / "REF1.gbk"
    SeqIO.write(rec, str(gbk), "genbank")
    return gbk


def _gp(tag, contig, start, strand=1, length=200000):
    return {"tag": tag, "contig": contig, "start": start, "end": start + 900, "strand": strand, "contig_len": length}


def _core_row(pid, ident=70.0):
    return {"status": "PRESENT_IN_CORE", "best_protein": pid, "best_identity_pct": str(ident), "reciprocal_best": "True"}


CORE_A = {"contig": "ctgA", "start": 10000, "end": 20000, "identity": "S / ctgA / region001 / BGC001"}


def _draw(tmp_path, prots, rows, splits=(), regions=None):
    pytest.importorskip("matplotlib")
    gbk = _ref_gbk(tmp_path)
    return M.draw_locus_map(gbk, rows, list(splits), prots, regions or [CORE_A], CORE_A, "S", "test",
                            tmp_path / "m.png", tmp_path / "m.pdf")


class TestContigParts:
    def test_genes_close_together_keep_one_window(self):
        assert M.contig_parts(7500, 30000, 200000, [(10000, 20000), (24000, 24900)]) == [(7500, 30000)]

    def test_a_long_empty_stretch_cuts_the_window_in_two(self):
        parts = M.contig_parts(7500, 73400, 200000, [(10000, 20000), (70000, 70900)])
        assert parts == [(7500, 22500), (67500, 73400)]

    def test_a_short_contig_is_never_cut(self):
        assert M.contig_parts(0, 11000, 11000, [(100, 1000), (9000, 9900)]) == [(0, 11000)]

    def test_the_core_region_bridges_matches_inside_it(self):
        # two matches 18 kb apart, both inside the core region: one part
        assert M.contig_parts(7500, 32500, 200000, [(10000, 30000), (11000, 11900), (29000, 29900)]) == [(7500, 32500)]


class TestOneContigTwoSegments:
    def _two_block_contig(self, strand=1):
        prots = {f"q{i}": _gp(f"a_{i}", "ctgA", 11000 + i * 1000, strand) for i in range(4)}   # abcA-abcD in the core
        prots["q9"] = _gp("a_9", "ctgA", 70000, strand)                                       # abcE, 50 kb along
        rows = [_core_row(f"q{i}") for i in range(4)] + [_core_row("q9"), {"status": "MISSING_NOT_FOUND"}]
        return prots, rows

    def test_ordering_two_parts_in_contig_order_with_the_cut_between(self, tmp_path):
        prots, rows = self._two_block_contig()
        res = _draw(tmp_path, prots, rows)
        segs = res["segments"]
        assert [(s["contig"], s["part"], s["parts"]) for s in segs] == [("ctgA", 1, 2), ("ctgA", 2, 2)]
        assert (segs[0]["lo"], segs[0]["hi"]) == (7500, 22500)
        assert (segs[1]["lo"], segs[1]["hi"]) == (67500, 73400)
        assert segs[1]["lo"] - segs[0]["hi"] > M.SEG_BREAK_KB * 1000, "the omitted stretch is really omitted"
        assert res["contigs_drawn"] == ["ctgA"], "one contig, however many parts"

    def test_flipping_turns_every_part_and_reverses_their_order(self, tmp_path):
        prots, rows = self._two_block_contig(strand=-1)   # every match on the strand opposite its reference gene
        res = _draw(tmp_path, prots, rows)
        segs = res["segments"]
        assert all(s["flip"] for s in segs), "parts of one contig share its turn"
        assert [s["lo"] for s in segs] == [67500, 7500], "a turned contig reads from its far end"
        assert res["flipped"] == {"ctgA": True}

    def test_captions_name_the_part_and_call_only_the_core_part_core(self, tmp_path):
        prots, rows = self._two_block_contig()
        segs = _draw(tmp_path, prots, rows)["segments"]
        assert segs[0]["caption"] == "ctgA (part 1 of 2)\ncore, BGC001"
        assert segs[1]["caption"] == "ctgA (part 2 of 2)\nno antiSMASH region"

    def test_a_region_in_the_far_part_is_named_by_its_own_alias(self, tmp_path):
        prots, rows = self._two_block_contig()
        far_region = {"contig": "ctgA", "start": 69000, "end": 72000, "identity": "S / ctgA / region002 / BGC002"}
        segs = _draw(tmp_path, prots, rows, regions=[CORE_A, far_region])["segments"]
        assert segs[1]["caption"].endswith("\nBGC002")

    def test_a_compact_contig_keeps_its_old_single_caption(self, tmp_path):
        prots = {f"q{i}": _gp(f"a_{i}", "ctgA", 11000 + i * 1000) for i in range(4)}
        rows = [_core_row(f"q{i}") for i in range(4)] + [{"status": "MISSING_NOT_FOUND"}] * 2
        segs = _draw(tmp_path, prots, rows)["segments"]
        assert len(segs) == 1 and segs[0]["parts"] == 1
        assert segs[0]["caption"] == "ctgA (part)\ncore, BGC001"

    def test_split_pairing_puts_the_gap_between_the_right_parts(self, tmp_path):
        """The split gene's piece sits at the far end of the core contig; its other piece starts the next contig. The
        split gap must join the part holding the piece to the next contig, not the core part."""
        prots = {f"q{i}": _gp(f"a_{i}", "ctgA", 11000 + i * 1000) for i in range(4)}
        prots["p1"] = _gp("a_end", "ctgA", 199000)                          # piece 1 at ctgA's right end
        prots["p2"] = _gp("b_start", "ctgB", 100, length=20000)             # piece 2 at ctgB's left end
        rows = [_core_row(f"q{i}") for i in range(4)] + [{"status": "MISSING_NOT_FOUND"}] * 2
        split = {"reference_gene": "6", "piece1_locus": "a_end", "piece2_locus": "b_start", "split_call": "CLEAR",
                 "piece1_identity_pct": "60", "piece2_identity_pct": "55"}
        res = _draw(tmp_path, prots, rows, splits=[split])
        segs = res["segments"]
        assert [(s["contig"], s["part"]) for s in segs] == [("ctgA", 1), ("ctgA", 2), ("ctgB", 1)]
        assert res["split_gaps"] == [(1, 2)], "the split gap sits after ctgA's last part"
        assert segs[1]["lo"] <= 199000 < segs[1]["hi"], "the piece is in the part beside the gap"

    def test_a_pair_map_is_never_cut(self, tmp_path):
        pytest.importorskip("matplotlib")
        prots, rows = self._two_block_contig()
        prots["b1"] = _gp("b_1", "ctgB", 500, length=20000)
        partner = {"contig": "ctgB", "start": 0, "end": 3000, "identity": "S / ctgB / region001 / BGC002"}
        rows_b = [{"status": "MISSING_NOT_FOUND"}] * 5 + [_core_row("b1")]
        res = M.draw_locus_map(_ref_gbk(tmp_path), rows, [], prots, [CORE_A, partner], CORE_A, "S", "test",
                               tmp_path / "m.png", tmp_path / "m.pdf", partner=partner, pair_note="pair",
                               partner_rows=rows_b)
        assert all(s["parts"] == 1 for s in res["segments"])


# ---------------------------------------------------------------------------------------------------------------------
# Counts. The owner's ruling (7 Oct): print the reference-gene count and the distinct-protein count together. The old
# footnote also printed "set aside" beside the statuses as a peer, so its numbers summed past the reference total.
# ---------------------------------------------------------------------------------------------------------------------

def _st(status, pid="", verdict=""):
    return {"status": status, "best_protein": pid, "partner_verdict": verdict}


class TestCounts:
    def test_two_core_rows_on_one_protein_print_both_numbers(self):
        rows = [_st("PRESENT_IN_CORE", "p1"), _st("PRESENT_IN_CORE", "p1"), _st("MISSING_NOT_FOUND")]
        c = M.count_summary(rows)
        assert (c["core"], c["core_proteins"]) == (2, 1)
        assert M.count_sentence(c).startswith("2 of 3 reference genes in the core, on 1 distinct protein;")

    def test_unshared_core_rows_give_equal_numbers(self):
        rows = [_st("PRESENT_IN_CORE", "p1"), _st("PRESENT_IN_CORE", "p2"), _st("MISSING_FOUND_CLEAR", "p3")]
        c = M.count_summary(rows)
        assert (c["core"], c["core_proteins"]) == (2, 2)
        assert "on 2 distinct proteins" in M.count_sentence(c)

    def test_the_statuses_always_sum_to_the_reference_total(self):
        rows = ([_st("PRESENT_IN_CORE", f"p{i}") for i in range(31)] + [_st("MISSING_FOUND_CLEAR", f"c{i}") for i in range(20)]
                + [_st("MISSING_FOUND_AMBIGUOUS")] * 6 + [_st("MISSING_NOT_FOUND")] * 3)
        for r in rows[31:47]:   # 16 set aside, 11 of them clear finds: the old footnote printed 31 + 20 + 16 = 67 of 60
            r["partner_verdict"] = "PARALOG_FAMILY"
        c = M.count_summary(rows)
        assert c["core"] + c["clear"] + c["ambiguous"] + c["not_found"] + c["other"] == c["reference_genes"] == 60
        text = M.count_sentence(c)
        assert "Of these, 16 were set aside" in text, "set aside is printed as a subset"
        assert "; 16 set aside" not in text, "never as a peer of the statuses"
        assert "6 found ambiguously" in text and "3 not found" in text

    def test_a_split_gene_is_explained(self):
        c = M.count_summary([_st("PRESENT_IN_CORE", "p1"), _st("MISSING_NOT_FOUND")], [_split(name="", ref_gene="2")])
        assert ("1 reference gene is split across contigs, with both pieces listed together in one row per reference "
                "gene") in M.count_sentence(c)

    def test_the_map_footnote_uses_the_same_sentence(self, tmp_path):
        prots = {"q1": _gp("a_1", "ctgA", 11000), "q2": _gp("a_2", "ctgA", 12000)}
        rows = [_core_row("q1"), _core_row("q1"), _core_row("q2")] + [{"status": "MISSING_NOT_FOUND"}] * 3
        res = _draw(tmp_path, prots, rows)
        assert res["footnote"].startswith("3 of 6 reference genes in S / ctgA / region001 / BGC001, on 2 distinct proteins;")

    @pytest.mark.skipif(bool(_TABLE_SKIP), reason=_TABLE_SKIP or "")
    def test_the_gene_table_writes_the_same_counts(self, tmp_path):
        import csv as _csv
        gbk = _ref_gbk(tmp_path)
        rows = [dict(_core_row("q1"), name="abcA", best_locus="a_1", best_identity_pct="70"),
                dict(_core_row("q1"), name="abcB", best_locus="a_1", best_identity_pct="40"),
                dict(_core_row("q2"), name="abcC", best_locus="a_2", best_identity_pct="60")] + \
               [{"status": "MISSING_NOT_FOUND", "name": n} for n in ("abcD", "abcE", "abcF")]
        res = T.write_gene_table(tmp_path, rows, [], "S / ctgA / region001 / BGC001", "S", gbk, {}, "test")
        got = next(_csv.DictReader(open(tmp_path / "gene_table_counts.tsv"), delimiter="\t"))
        assert (got["reference_genes"], got["core"], got["core_proteins"]) == ("6", "3", "2")
        assert res["counts"]["core_proteins"] == 2


# ---------------------------------------------------------------------------------------------------------------------
# Review acceptance: one rule decides which split records are drawn and counted; the captions name exact units; the map
# footnote, the table caption and the table's own rows agree. A shared match is an observation; whether it reflects a
# fused gene, a duplication or a paralog is a hypothesis these figures do not decide.
# ---------------------------------------------------------------------------------------------------------------------

def _split(name="abcF", ref_gene="6", call="CLEAR", status="SPLIT_ACROSS_CONTIG_ENDS", p1="a_end", p2="b_start"):
    x = {"name": name, "reference_gene": ref_gene, "split_call": call, "piece1_locus": p1, "piece2_locus": p2,
         "piece1_identity_pct": "60", "piece2_identity_pct": "55",
         "piece1_region_identity": "S / ctgA / region001 / BGC001", "piece2_region_identity": "S / ctgB / region001 / BGC002"}
    if status is not None:
        x["status"] = status
    return x


class TestSplitEligibility:
    def test_a_complete_clear_record_is_eligible(self):
        assert M.split_eligible(_split())

    def test_a_record_without_a_status_column_is_eligible(self):
        assert M.split_eligible(_split(status=None))

    @pytest.mark.parametrize("kw", [{"p2": ""}, {"p1": ""}, {"call": "WEAK"}, {"call": "RIVAL_STRONGER"},
                                    {"call": "MODULAR_UNRESOLVED"}, {"status": "SOMETHING_ELSE"}])
    def test_incomplete_or_inconsistent_records_are_not(self, kw):
        assert not M.split_eligible(_split(**kw))

    @pytest.mark.parametrize("n, phrase", [(0, None), (1, "1 reference gene is split"), (3, "3 reference genes are split")])
    def test_zero_one_and_many_split_records(self, n, phrase):
        splits = [_split(name="", ref_gene=str(i + 2)) for i in range(n)] + [_split(name="", call="WEAK")]
        c = M.count_summary([_st("PRESENT_IN_CORE", "p1")] + [_st("MISSING_NOT_FOUND")] * n, splits)
        text = M.count_sentence(c)
        assert c["split"] == n
        if phrase is None:
            assert "split" not in text
        else:
            assert phrase in text and "both pieces listed together in one row per reference gene" in text

    def test_the_map_draws_exactly_the_eligible_splits(self):
        prots = {"p1": _gp("a_end", "ctgA", 199000), "p2": _gp("b_start", "ctgB", 100, length=20000),
                 "q1": _gp("a_1", "ctgA", 11000)}
        rows = [_core_row("q1")] + [{"status": "MISSING_NOT_FOUND"}] * 5
        _, info, *_ = M.choose(_ref(6), rows, [_split(), _split(name="abcE", ref_gene="5", call="WEAK")], prots, "ctgA")
        assert set(info) == {5}, "only the eligible record (reference gene 6) is drawn as a split"


class TestCountUnits:
    def test_reference_rows_distinct_proteins_and_split_pieces_are_counted_apart(self):
        rows = [_st("PRESENT_IN_CORE", "p1"), _st("PRESENT_IN_CORE", "p1"), _st("MISSING_NOT_FOUND")]
        c = M.count_summary(rows, [_split(name="", ref_gene="3")])
        assert c["core"] == 2, "core counts reference genes (table rows)"
        assert c["core_proteins"] == 1, "core_proteins counts distinct local proteins"
        assert c["split"] == 1, "a split counts once per reference gene, not once per piece"

    def test_an_unknown_status_is_counted_and_named(self):
        c = M.count_summary([_st("PRESENT_IN_CORE", "p1"), _st("SOMETHING_NEW")])
        assert c["other"] == 1
        assert "1 with another status" in M.count_sentence(c)
        assert c["core"] + c["clear"] + c["ambiguous"] + c["not_found"] + c["other"] == c["reference_genes"]

    def test_set_aside_is_a_subset_of_the_partition(self):
        rows = [_st("MISSING_FOUND_CLEAR", "c1", "PARALOG_FAMILY"), _st("MISSING_FOUND_CLEAR", "c2"), _st("MISSING_NOT_FOUND")]
        c = M.count_summary(rows)
        assert c["set_aside"] == 1 and c["clear"] == 2
        assert "Of these, 1 was set aside" in M.count_sentence(c)


@pytest.mark.skipif(bool(_TABLE_SKIP), reason=_TABLE_SKIP or "")
class TestCaptionsAgreeWithRows:
    """A synthetic run with a shared protein, a set-aside find, an unknown status and one split gene."""

    def _run(self, tmp_path):
        prots = {"q1": _gp("a_1", "ctgA", 11000), "q2": _gp("a_2", "ctgA", 12000),
                 "q3": _gp("c_1", "ctgC", 5000, length=20000),
                 "p1": _gp("a_end", "ctgA", 199000), "p2": _gp("b_start", "ctgB", 100, length=20000)}

        def row(i, name, status, pid="", tag="", ident="0", recip="False", verdict="", contig=""):
            return {"reference_gene": str(i), "name": name, "status": status, "best_protein": pid, "best_locus": tag,
                    "best_identity_pct": ident, "reciprocal_best": recip, "partner_verdict": verdict,
                    "best_contig": contig, "best_len_aa": "300", "best_region_identity": ""}
        rows = [row(1, "abcA", "PRESENT_IN_CORE", "q1", "a_1", "70", "True", contig="ctgA"),
                row(2, "abcB", "PRESENT_IN_CORE", "q1", "a_1", "40", "False", contig="ctgA"),    # shared protein
                row(3, "abcC", "PRESENT_IN_CORE", "q2", "a_2", "60", "True", contig="ctgA"),
                row(4, "abcD", "MISSING_FOUND_CLEAR", "q3", "c_1", "55", "True", "PARALOG_FAMILY", "ctgC"),  # set aside
                row(5, "abcE", "SOMETHING_NEW"),                                                     # unknown status
                row(6, "abcF", "MISSING_NOT_FOUND")]                                                 # split gene
        splits = [_split(), _split(name="abcE", ref_gene="5", call="WEAK")]
        return prots, rows, splits

    def test_map_caption_equals_table_caption_equals_rows(self, tmp_path):
        import csv as _csv
        prots, rows, splits = self._run(tmp_path)
        gbk = _ref_gbk(tmp_path)
        res_map = M.draw_locus_map(gbk, rows, splits, prots, [CORE_A], CORE_A, "S", "test",
                                   tmp_path / "m.png", tmp_path / "m.pdf")
        res_tab = T.write_gene_table(tmp_path, rows, splits, CORE_A["identity"], "S", gbk, {}, "test")
        c = res_tab["counts"]
        assert (c["reference_genes"], c["core"], c["core_proteins"], c["clear"], c["ambiguous"], c["not_found"],
                c["other"], c["set_aside"], c["split"]) == (6, 4, 3, 1, 0, 0, 1, 1, 1), \
            "abcF is shown as a split with a piece in the core, so it counts in the core, never as not found"
        assert res_map["footnote"].startswith(res_tab["caption"].rstrip(".")), "map footnote opens with the table caption"
        table = list(_csv.DictReader(open(tmp_path / "gene_table.tsv"), delimiter="\t"))
        assert len(table) == c["reference_genes"], "one table row per reference gene"
        split_rows = [r for r in table if r["Reference gene"] == "abcF"]
        assert len(split_rows) == 1 and split_rows[0]["CDS"] == "a_end + b_start", "both pieces in one row"
        assert "same protein as abcA" in next(r for r in table if r["Reference gene"] == "abcB")["Location"]
        assert "both pieces listed together in one row per reference gene" in res_tab["caption"]
        unknown = next(r for r in table if r["Reference gene"] == "abcE")
        assert unknown["Location"].startswith("status something new"), "an unknown status is named, not called not found"
        assert unknown["CDS"] == "-"


class TestSharedGeneNotes:
    def _notes(self, tmp_path, second_start):
        tmp_path.mkdir(parents=True, exist_ok=True)
        prots = {"q1": _gp("a_1", "ctgA", 11000, length=40000), "q2": _gp("a_2", "ctgA", second_start, length=40000)}
        rows = [_core_row("q1"), _core_row("q1"), _core_row("q2"), _core_row("q2")] + [{"status": "MISSING_NOT_FOUND"}] * 2
        return _draw(tmp_path, prots, rows)["shared_notes"]

    def test_notes_that_would_sit_flush_go_to_another_row(self, tmp_path):
        """The case that went wrong: two notes that do not overlap but would be drawn flush, reading as one run-on
        line. Measure a note's width, then place the second shared gene so the two notes would sit 7% of a note
        width apart on one row. They must not share the row with so small a gap."""
        # measure one note with both genes inside the core window, so the axis (and with it a note's width in plot
        # units) is the same as in the close placement below; plot units are kb along the contig, unturned here
        _, l, r, _ = self._notes(tmp_path / "a", 18000)[0]
        w = r - l
        notes = self._notes(tmp_path / "b", int(11000 + 1000 * w * 1.07))
        assert len(notes) == 2
        (_, l1, r1, row1), (_, l2, r2, row2) = sorted(notes, key=lambda n: n[1])
        assert row1 != row2 or (l2 - r1) > 0.1 * w, "notes on one row keep a visible gap"


# ---------------------------------------------------------------------------------------------------------------------
# The counts describe the rows the table shows (review A01, item 7 and counterexample 2; the owner's ruling of 8 Oct).
# A split shown in the table counts once: in the core when a piece lies there, otherwise as found clearly elsewhere,
# never as not found. A split never overrides a core call. The split count is the reference genes shown as split rows.
# A split whose pieces are not both in the genome leaves its gene with its own status everywhere. These tests were
# written first and failed on the earlier patch.
# ---------------------------------------------------------------------------------------------------------------------

def _table_row(i, name, status, pid="", tag="", ident="0", recip="False", contig=""):
    return {"reference_gene": str(i), "name": name, "status": status, "best_protein": pid, "best_locus": tag,
            "best_identity_pct": ident, "reciprocal_best": recip, "partner_verdict": "", "best_contig": contig,
            "best_len_aa": "300", "best_region_identity": ""}


class TestCountsBindToTheRowsShown:
    @pytest.mark.skipif(bool(_TABLE_SKIP), reason=_TABLE_SKIP or "")
    def test_not_found_counts_only_rows_the_table_shows_as_not_found(self, tmp_path):
        """Counterexample 1: abcF is called not found, but an eligible split record makes the table show it as a split
        row. The caption must not still count it as not found."""
        import csv as _csv
        _, rows, splits = TestCaptionsAgreeWithRows()._run(tmp_path)
        res = T.write_gene_table(tmp_path, rows, splits, CORE_A["identity"], "S", _ref_gbk(tmp_path), {}, "test")
        table = list(_csv.DictReader(open(tmp_path / "gene_table.tsv"), delimiter="\t"))
        shown = sum(1 for r in table if r["CDS"] == "not found")
        assert res["counts"]["not_found"] == shown, (
            f"caption counts {res['counts']['not_found']} not found; the table shows {shown} not-found rows")

    @pytest.mark.skipif(bool(_TABLE_SKIP), reason=_TABLE_SKIP or "")
    @pytest.mark.parametrize("names, shown_expected", [(("absent_name", "absent_name"), 0), (("abcB", "abcB"), 1)],
                             ids=["duplicate_orphan_records", "duplicate_records_for_a_shown_gene"])
    def test_split_count_is_the_unique_genes_shown_as_split_rows(self, tmp_path, names, shown_expected):
        """Counterexample 2: duplicate eligible split records, naming a reference gene that has no row or one that has,
        must not count more split genes than the table shows as split rows."""
        import csv as _csv
        rows = [_table_row(1, "abcA", "PRESENT_IN_CORE", "q1", "a_1", "70", "True", "ctgA"),
                _table_row(2, "abcB", "MISSING_NOT_FOUND")]
        splits = [_split(name=n, ref_gene="2" if n == "abcB" else "999") for n in names]
        res = T.write_gene_table(tmp_path, rows, splits, CORE_A["identity"], "S", _ref_gbk(tmp_path), {}, "test")
        table = list(_csv.DictReader(open(tmp_path / "gene_table.tsv"), delimiter="\t"))
        shown = sum(1 for r in table if r["Location"].startswith("split across"))
        assert shown == shown_expected
        assert res["counts"]["split"] == shown, (
            f"caption counts {res['counts']['split']} split genes; the table shows {shown} split rows")


class TestTheSplitRuleIsShared:
    def _core_and_split_elsewhere(self):
        rows = [_table_row(1, "abcA", "PRESENT_IN_CORE", "q1", "a_1", "45", "True", "ctgA"),
                _table_row(2, "abcB", "MISSING_NOT_FOUND")]
        far = dict(_split(name="abcA", ref_gene="1"), piece1_region_identity="S / ctgB / region001 / BGC002",
                   piece2_region_identity="S / ctgC (no antiSMASH region)", piece1_locus="b_start", piece2_locus="c_1")
        prots = {"q1": _gp("a_1", "ctgA", 11000), "p2": _gp("b_start", "ctgB", 100, length=20000),
                 "p3": _gp("c_1", "ctgC", 5000, length=20000)}
        return rows, [far], prots

    @pytest.mark.skipif(bool(_TABLE_SKIP), reason=_TABLE_SKIP or "")
    def test_a_split_never_overrides_a_core_call(self, tmp_path):
        import csv as _csv
        rows, splits, prots = self._core_and_split_elsewhere()
        res = T.write_gene_table(tmp_path, rows, splits, CORE_A["identity"], "S", _ref_gbk(tmp_path), {}, "test",
                                 known_tags={p["tag"] for p in prots.values()})
        table = list(_csv.DictReader(open(tmp_path / "gene_table.tsv"), delimiter="\t"))
        a = next(r for r in table if r["Reference gene"] == "abcA")
        assert a["CDS"] == "a_1" and "(core)" in a["Location"], "the core row stands"
        assert "also a clear split across BGC002" in a["Location"], "and the split is noted beside it"
        assert (res["counts"]["core"], res["counts"]["split"]) == (1, 0)
        drawn, info, *_ = M.choose(_ref(6), rows, splits, prots, "ctgA")
        assert info == {} and (0, "q1", 45.0) in drawn, "the map draws the core match, not the split"

    @pytest.mark.skipif(bool(_TABLE_SKIP), reason=_TABLE_SKIP or "")
    def test_a_split_with_a_piece_not_in_the_genome_keeps_the_gene_s_own_status(self, tmp_path):
        import csv as _csv
        rows = [_table_row(1, "abcA", "PRESENT_IN_CORE", "q1", "a_1", "70", "True", "ctgA"),
                _table_row(2, "abcB", "MISSING_NOT_FOUND")]
        splits = [_split(name="abcB", ref_gene="2")]
        known = {"a_1", "a_end"}                       # b_start, the second piece, is not in this genome
        res = T.write_gene_table(tmp_path, rows, splits, CORE_A["identity"], "S", _ref_gbk(tmp_path), {}, "test",
                                 known_tags=known)
        table = list(_csv.DictReader(open(tmp_path / "gene_table.tsv"), delimiter="\t"))
        b = next(r for r in table if r["Reference gene"] == "abcB")
        assert b["CDS"] == "not found" and "a piece is not in this genome" in b["Location"]
        assert (res["counts"]["not_found"], res["counts"]["split"]) == (1, 0)
        assert M.count_summary(rows, splits, CORE_A["identity"], known)["not_found"] == 1
        prots = {"q1": _gp("a_1", "ctgA", 11000), "p1": _gp("a_end", "ctgA", 199000)}
        _, info, *_ = M.choose(_ref(6), rows, splits, prots, "ctgA")
        assert info == {}, "the map does not draw a split it cannot place"

    @pytest.mark.skipif(bool(_TABLE_SKIP), reason=_TABLE_SKIP or "")
    def test_the_piece_in_the_core_is_marked_core(self, tmp_path):
        import csv as _csv
        rows = [_table_row(1, "abcA", "PRESENT_IN_CORE", "q1", "a_1", "70", "True", "ctgA"),
                _table_row(2, "abcB", "MISSING_FOUND_AMBIGUOUS", "q9", "z_9", "35", "False", "ctgZ")]
        res = T.write_gene_table(tmp_path, rows, [_split(name="abcB", ref_gene="2")], CORE_A["identity"], "S",
                                 _ref_gbk(tmp_path), {}, "test")
        table = list(_csv.DictReader(open(tmp_path / "gene_table.tsv"), delimiter="\t"))
        loc = next(r for r in table if r["Reference gene"] == "abcB")["Location"]
        first, second = loc[len("split across "):].split(" + ")
        assert first.endswith("(core)") and "(core)" not in second
        assert (res["counts"]["core"], res["counts"]["ambiguous"], res["counts"]["split"]) == (2, 0, 1)
