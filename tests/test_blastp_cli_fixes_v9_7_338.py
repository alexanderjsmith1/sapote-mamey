"""Companion tests for the v9.7.338 BLASTp-channel + CLI-usage fixes (L5 staged patch).

Covers:
  BLP-01  first-pass BLASTp panel must not drop a flagship giant-core BGC.
  BLP-02  product-novelty cross-check inputs resolve (explicit + auto-derived), no longer dead.
  BLP-03  CSV-only self-hit exclusion for a NAMED query genome (XML-free rank-1 heuristic).
  BLP-04  query coverage is emitted NA (not an inflated ~1.0) when query length is unknown.
  E2E-01  `explain` resolves the run mode from the manifest instead of printing "?".
"""
import argparse
import csv

from mamey.bgc_blastp_panel import first_pass_rows
from mamey.blastp_online import _derive_kcb_anchor
from mamey.blastp_ingest import _is_self_hit, write_nr_overlay
from mamey.blastp_followup import HitRecord, summarize_results
from mamey.package_inspector import explain_command


# --- BLP-01 -----------------------------------------------------------------

def _row(bgc, slot, aa, role, score):
    return {"bgc_id": bgc, "slot": slot, "aa_len": aa, "selection_role": role,
            "selection_score": score, "locus_tag": f"{bgc}_{slot}", "protein_id": ""}


def test_blp01_giant_core_bgc_kept_in_first_pass():
    # Three ordinary non-giant-core BGCs plus one flagship whose ONLY core is a giant PKS.
    curated = [
        _row("B1", 1, 300, "core", 121),
        _row("B2", 1, 310, "core", 121),
        _row("B3", 1, 305, "core", 121),
        _row("BGCG", 1, 3116, "core", 131),   # giant-only core (the AS-421 BGC041 shape)
    ]
    fp = first_pass_rows(curated, first_pass_size=3)
    bgcs = {r["bgc_id"] for r in fp}
    assert "BGCG" in bgcs, "giant-core flagship BGC must not be pushed off the first pass"
    assert len(fp) == 3


def test_blp01_giant_bgc_with_nongiant_core_is_not_exempted():
    # If the BGC already has a non-giant core representative it is not exempted; the giant row
    # keeps its penalty, and the BGC is still represented by its small core.
    curated = [
        _row("B1", 1, 300, "core", 121),
        _row("B2", 1, 300, "core", 121),
        _row("B3", 1, 300, "core", 121),
        _row("BX", 1, 3116, "core", 131),   # giant core ...
        _row("BX", 2, 250, "core", 118),    # ... but also a small core -> no exemption
    ]
    fp = first_pass_rows(curated, first_pass_size=4)
    bx = [r for r in fp if r["bgc_id"] == "BX"]
    assert bx and all(int(r["aa_len"]) < 2500 for r in bx), "represented by the non-giant core"


# --- BLP-02 -----------------------------------------------------------------

def _mk_profile(tmp_path, bgc, compound, cov):
    p = tmp_path / "AS-X_3_mibig_profile.csv"
    with p.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["bgc_id", "dominant_mibig_accession", "dominant_mibig_compound",
                    "dominant_distinct_query_genes"])
        w.writerow([bgc, "BGC0001043", compound, cov])
    return p


def test_blp02_auto_derive_from_mibig_profile(tmp_path):
    _mk_profile(tmp_path, "BGC041", "SGR PTMs", 4)
    args = argparse.Namespace(package=str(tmp_path), crosswalk=None, bgc="BGC041",
                              kcb_top=None, kcb_coverage_genes=None)
    top, cov = _derive_kcb_anchor(args)
    assert top == "SGR PTMs"
    assert cov == 4


def test_blp02_explicit_args_win_and_no_bgc_is_undetermined(tmp_path):
    _mk_profile(tmp_path, "BGC041", "SGR PTMs", 4)
    explicit = argparse.Namespace(package=str(tmp_path), crosswalk=None, bgc="BGC041",
                                  kcb_top="anchorX", kcb_coverage_genes=9)
    assert _derive_kcb_anchor(explicit) == ("anchorX", 9)
    nobgc = argparse.Namespace(package=str(tmp_path), crosswalk=None, bgc=None,
                               kcb_top=None, kcb_coverage_genes=None)
    assert _derive_kcb_anchor(nobgc) == ("", None)   # -> function_and_novelty UNDETERMINED


# --- BLP-03 -----------------------------------------------------------------

def test_blp03_is_self_hit_xmlfree_rank1_heuristic():
    # No sciname (CSV-only ingest) + named genome: rank-1 >=99% is a probable self-hit.
    assert _is_self_hit("", 100.0, "streptomyces coelicolor", hit_rank=1) is True
    # A lower-ranked hit is a real comparator, retained.
    assert _is_self_hit("", 100.0, "streptomyces coelicolor", hit_rank=2) is False
    # Unnamed ("sp.") query -> self_binomial is None -> never excluded (moot for AS strains).
    assert _is_self_hit("", 100.0, None, hit_rank=1) is False
    # Backward compatible default (no hit_rank) stays False when sciname is empty.
    assert _is_self_hit("", 100.0, "streptomyces coelicolor") is False


def test_blp03_overlay_excludes_csv_only_selfhit_for_named_strain(tmp_path):
    (tmp_path / "manifest.json").write_text(
        '{"display_name": "Streptomyces coelicolor A3(2)"}', encoding="utf-8")
    rows = [
        {"BGC_ID": "BGC001", "query_locus": "AS|BGC001|gene=ctg1_5|aa=300",
         "sciname": "", "pct_identity": "100.0", "hit_rank": 1,
         "subject_acc": "WP_SELF.1", "subject_desc": "polyketide synthase",
         "bitscore": "600", "evalue": "0.0", "query_len": "300"},
        {"BGC_ID": "BGC001", "query_locus": "AS|BGC001|gene=ctg1_5|aa=300",
         "sciname": "", "pct_identity": "77.0", "hit_rank": 2,
         "subject_acc": "WP_OTHER.1", "subject_desc": "polyketide synthase",
         "bitscore": "480", "evalue": "0.0", "query_len": "300"},
    ]
    res = write_nr_overlay(tmp_path, rows)
    assert res["self_hits_excluded"] == 1
    assert res["self_hits_excluded_heuristic"] == 1
    assert res["self_exclusion_mode"] == "rank1_heuristic_no_xml"
    # the retained overlay row is the rank-2 comparator, not the 100% self-hit
    with (tmp_path / "blastp_online" / "BGC001_online_blastp.csv").open() as fh:
        kept = list(csv.DictReader(fh))
    assert len(kept) == 1
    assert kept[0]["blastp_accession"] == "WP_OTHER.1"


def test_blp03_unnamed_strain_excludes_nothing(tmp_path):
    (tmp_path / "manifest.json").write_text(
        '{"display_name": "Streptomyces sp. AS-421"}', encoding="utf-8")
    rows = [{"BGC_ID": "BGC001", "query_locus": "AS|BGC001|gene=ctg1_5|aa=300",
             "sciname": "", "pct_identity": "100.0", "hit_rank": 1,
             "subject_acc": "WP_A.1", "subject_desc": "synthase",
             "bitscore": "600", "evalue": "0.0", "query_len": "300"}]
    res = write_nr_overlay(tmp_path, rows)
    assert res["self_hits_excluded"] == 0
    assert res["self_exclusion_mode"] == "not_applicable"


# --- BLP-04 -----------------------------------------------------------------

def test_blp04_unknown_qlen_coverage_is_none_not_inflated():
    r = HitRecord(query_id="totally_opaque_token", subject_id="WP_X.1", pct_identity=90.0,
                  align_len=100, mismatches=2, gap_opens=0, qstart=1, qend=100,
                  sstart=1, send=100, evalue="1e-9", bitscore=200.0, query_len=None)
    assert r.query_coverage is None   # was min(1.0, 100/100)=1.0 before the fix


def test_blp04_summary_emits_na_for_unknown_coverage():
    r = HitRecord(query_id="totally_opaque_token", subject_id="WP_X.1", pct_identity=90.0,
                  align_len=100, mismatches=2, gap_opens=0, qstart=1, qend=100,
                  sstart=1, send=100, evalue="1e-9", bitscore=200.0, query_len=None)
    hit_rows, query_rows = summarize_results([r])
    assert hit_rows[0]["query_coverage"] == "NA"
    assert query_rows[0]["top_query_coverage"] == "NA"


def test_blp04_known_qlen_still_computes_coverage():
    r = HitRecord(query_id="AS|BGC001|gene=ctg1_5|aa=200", subject_id="WP_X.1",
                  pct_identity=90.0, align_len=100, mismatches=2, gap_opens=0, qstart=1,
                  qend=100, sstart=1, send=100, evalue="1e-9", bitscore=200.0, query_len=200)
    assert abs(r.query_coverage - 0.5) < 1e-9


# --- E2E-01 -----------------------------------------------------------------

def test_e2e01_explain_resolves_mode_from_manifest(tmp_path, capsys):
    (tmp_path / "manifest.json").write_text(
        '{"strain_id": "AS-T", "mode": "gold", "version": "1.9.118", '
        '"taxonomy": "Streptomyces sp."}', encoding="utf-8")
    rc = explain_command(argparse.Namespace(package_dir=str(tmp_path)))
    out = capsys.readouterr().out
    assert rc == 0
    mode_line = next(ln for ln in out.splitlines() if ln.strip().startswith("Mode"))
    assert "gold" in mode_line
    assert "?" not in mode_line
