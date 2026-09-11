"""v9.7.412 — manual BLASTp-ingest binding + numeric + self-hit guard (F1–F10).

Spec origin: the laptop lane CLAUDE_409_blastp_ingest_binding shipped these tests without the code (its patch held
only the two B1 baseline edits, which .411 already carries). The guard was built here against this spec.

Regression pins for DEEP_AUDIT2 (development/DEEP_AUDIT2_blastp_ingest.md). The manual overlay
write path (ingest_blastp -> build_b5_rows -> write_nr_overlay) previously applied NONE of the
trove path's ingest guards, so a wrong/phantom BGC token, a foreign --strain, or a
physically-impossible row wrote straight into <package>/blastp_online/<BGC>_online_blastp.csv —
the exact file authored_verify / genome_explore trust for conservation_median_id /
NOVELTY_CONTRADICTION.

FAIL-BEFORE (unpatched v9.7.408): F1/F2 mis-bound rows silently written; F3 foreign --strain
silently accepted; F5-F7 impossible numerics admitted; F4 XML/HitTable BGC conflict resolved by
silent precedence; F10 self-hit retained because display_name masked the binomial.
PASS-AFTER (this patch): refused (F3, F4) or quarantined (F1/F2/F5-F7); self-hit excluded (F10);
correctly-bound rows still admitted (no false positive).

To run against the patched tree in a scratch bundle copy without touching the real bundle:
    MAMEY_TREE=/path/to/bundlecopy python -m pytest test_blastp_ingest_binding_409.py -q
When the patch is applied into the bundle, drop the file into tests/ and run pytest normally.
"""
from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path

import pytest

_TREE = os.environ.get("MAMEY_TREE")
if _TREE and _TREE not in sys.path:
    sys.path.insert(0, _TREE)

import openpyxl  # noqa: E402

import mamey.blastp_ingest as bi  # noqa: E402
from mamey.master_workbook import CANONICAL_V1_HEADERS  # noqa: E402


# --- fixtures: a package shaped like the real Actinomadura_RB68 ------------------------
# manifest carries display_name "Actinomadura RB68" (Genus + StrainCode, masks the binomial)
# and taxonomy "Actinomadura macrotermitis" (the real binomial the genome hits itself under).
def _package(tmp: Path, strain: str = "Actinomadura_RB68",
             display: str = "Actinomadura RB68",
             taxonomy: str | None = "Actinomadura macrotermitis") -> Path:
    pkg = tmp / "package"
    pkg.mkdir(parents=True, exist_ok=True)
    man = {"strain_id": strain, "display_name": display}
    if taxonomy:
        man["taxonomy"] = taxonomy
    (pkg / "manifest.json").write_text(json.dumps(man), encoding="utf-8")
    records = [
        {"bgc_id": "BGC008", "cds": [
            {"locus_tag": "ctg162_3", "aa_length": 340, "sec_met_domains": []}]},
        {"bgc_id": "BGC027", "cds": [
            {"locus_tag": "ctg5_1136", "aa_length": 300, "sec_met_domains": []}]},
    ]
    (pkg / f"{strain}_gene_context.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    return pkg


def _master(tmp: Path) -> Path:
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    ws = wb.create_sheet("B5_BLASTp_Hits")
    ws.append(CANONICAL_V1_HEADERS["B5_BLASTp_Hits"])
    p = tmp / "m.xlsx"
    wb.save(p)
    return p


def _hits(tmp: Path, name: str, lines: str) -> Path:
    p = tmp / name
    p.write_text(lines, encoding="utf-8")
    return p


def _overlay_rows(pkg: Path, bgc: str) -> list[dict]:
    p = pkg / "blastp_online" / f"{bgc}_online_blastp.csv"
    return list(csv.DictReader(p.open())) if p.exists() else []


# --- F1: WRONG bind — locus belongs to a DIFFERENT BGC (bgcs>0, the B1 blind spot) -----
def test_f1_wrong_bind_locus_of_a_different_bgc_is_quarantined(tmp_path):
    pkg = _package(tmp_path)
    # query id claims BGC008, but ctg5_1136 is BGC027's locus
    ht = _hits(tmp_path, "f1.csv",
               "BGC008_ctg5_1136,WP_1.1,66.0,340,0,0,1,340,1,340,1e-50,441,75\n")
    res = bi.ingest_blastp(_master(tmp_path), "Actinomadura_RB68", ht, None, package=str(pkg))
    # FAIL-BEFORE: BGC008_online_blastp.csv was written with the mis-bound row.
    assert _overlay_rows(pkg, "BGC008") == []
    guard = res["binding_guard"]
    assert guard["quarantined"] >= 1
    # the quarantine records the load-bearing reason
    q = list(csv.DictReader(Path(guard["quarantine"]).open()))
    assert q[0]["reason"] == "NONCURRENT_LOCUS"


# --- F2: phantom BGC not in the package ------------------------------------------------
def test_f2_phantom_bgc_not_in_package_is_quarantined(tmp_path):
    pkg = _package(tmp_path)
    ht = _hits(tmp_path, "f2.csv",
               "BGC099_ctg5_1136,WP_1.1,66.0,300,0,0,1,300,1,300,1e-50,441,75\n"
               "BGC500_ctg99_9,WP_2.1,66.0,300,0,0,1,300,1,300,1e-50,441,75\n")
    res = bi.ingest_blastp(_master(tmp_path), "Actinomadura_RB68", ht, None, package=str(pkg))
    assert not (pkg / "blastp_online" / "BGC099_online_blastp.csv").exists()
    assert not (pkg / "blastp_online" / "BGC500_online_blastp.csv").exists()
    assert res["binding_guard"]["quarantined"] == 2
    reasons = {r["reason"] for r in csv.DictReader(Path(res["binding_guard"]["quarantine"]).open())}
    assert reasons == {"FOREIGN_BGC"}


# --- F3: foreign --strain -> typed REFUSAL before anything is written -------------------
def test_f3_foreign_strain_is_refused(tmp_path):
    pkg = _package(tmp_path)
    ht = _hits(tmp_path, "f3.csv",
               "BGC027_ctg5_1136,WP_1.1,66.0,300,0,0,1,300,1,300,1e-50,441,75\n")
    with pytest.raises(ValueError, match="conflicts with package manifest"):
        bi.ingest_blastp(_master(tmp_path), "AS-999-FOREIGN", ht, None, package=str(pkg))
    # nothing written to the evidence store on refusal
    assert not (pkg / "blastp_online").exists() or _overlay_rows(pkg, "BGC027") == []


# --- Correctly-bound row is still admitted (no false positive) -------------------------
def test_good_row_is_admitted(tmp_path):
    pkg = _package(tmp_path)
    ht = _hits(tmp_path, "good.csv",
               "BGC027_ctg5_1136,WP_OTHER.1,66.0,300,0,0,1,300,1,300,1e-50,441,75\n")
    res = bi.ingest_blastp(_master(tmp_path), "Actinomadura_RB68", ht, None, package=str(pkg))
    kept = _overlay_rows(pkg, "BGC027")
    assert len(kept) == 1 and kept[0]["blastp_accession"] == "WP_OTHER.1"
    assert res["binding_guard"]["quarantined"] == 0
    assert res["binding_guard"]["binding_validated"] is True


# --- F5/F6/F7: numeric/physical sanity gate --------------------------------------------
@pytest.mark.parametrize("line,reason", [
    # pct_identity 150 (impossible)
    ("BGC027_ctg5_1136,WP_A.1,150.0,300,0,0,1,300,1,300,1e-50,441,75\n", "IMPOSSIBLE_PCT_IDENTITY"),
    # pct_identity -5 (impossible)
    ("BGC027_ctg5_1136,WP_A.1,-5.0,300,0,0,1,300,1,300,1e-50,441,75\n", "IMPOSSIBLE_PCT_IDENTITY"),
    # evalue "N/A" (non-numeric)
    ("BGC027_ctg5_1136,WP_A.1,66.0,300,0,0,1,300,1,300,N/A,441,75\n", "NONNUMERIC_EVALUE"),
    # align_len 999999 >> the sealed gene length (300)
    ("BGC027_ctg5_1136,WP_A.1,66.0,999999,0,0,1,300,1,999999,1e-50,441,75\n", "HIT_LONGER_THAN_QUERY"),
])
def test_f5_f6_f7_numeric_sanity_quarantines(tmp_path, line, reason):
    pkg = _package(tmp_path)
    ht = _hits(tmp_path, "num.csv", line)
    res = bi.ingest_blastp(_master(tmp_path), "Actinomadura_RB68", ht, None, package=str(pkg))
    assert _overlay_rows(pkg, "BGC027") == []
    q = list(csv.DictReader(Path(res["binding_guard"]["quarantine"]).open()))
    assert q and q[0]["reason"] == reason


# --- F10: self-hit exclusion works once the binomial is read from taxonomy --------------
def test_f10_self_binomial_prefers_taxonomy_over_display_name(tmp_path):
    pkg = _package(tmp_path)  # display "Actinomadura RB68", taxonomy "Actinomadura macrotermitis"
    # FAIL-BEFORE: display_name "Actinomadura RB68" -> species token "RB68" not islower -> None.
    assert bi._self_binomial(pkg) == "actinomadura macrotermitis"


def test_f10_self_hit_excluded_and_comparator_retained(tmp_path):
    pkg = _package(tmp_path)
    rows = [
        {"BGC_ID": "BGC027", "query_locus": "BGC027|gene=ctg5_1136|aa=300",
         "sciname": "Actinomadura macrotermitis", "pct_identity": "100.000", "hit_rank": 1,
         "subject_acc": "WP_SELF.1", "subject_desc": "PKS", "bitscore": "600",
         "evalue": "0.0", "query_len": "300"},
        {"BGC_ID": "BGC027", "query_locus": "BGC027|gene=ctg5_1136|aa=300",
         "sciname": "Nocardia sp. NPDC1", "pct_identity": "77.300", "hit_rank": 2,
         "subject_acc": "WP_OTHER.1", "subject_desc": "PKS", "bitscore": "480",
         "evalue": "0.0", "query_len": "300"},
    ]
    res = bi.write_nr_overlay(pkg, rows)
    assert res["self_hits_excluded"] == 1
    kept = _overlay_rows(pkg, "BGC027")
    assert len(kept) == 1 and kept[0]["blastp_accession"] == "WP_OTHER.1"


def test_f10_unnamed_sp_strain_excludes_nothing(tmp_path):
    # regression pin: AS-series unnamed "<Genus> sp." strains still resolve to None (nothing dropped)
    pkg = _package(tmp_path, strain="AS-421", display="Streptomyces sp. AS-421", taxonomy=None)
    assert bi._self_binomial(pkg) is None


# --- F4: XML vs HitTable BGC disagreement -> typed hold, not silent precedence ----------
def test_f4_xml_hittable_bgc_conflict_is_a_typed_hold(tmp_path):
    ht = _hits(tmp_path, "f4.csv",
               "BGC027_ctg5_1136,WP_1.1,66.0,300,0,0,1,300,1,300,1e-50,441,75\n")
    xml = tmp_path / "f4.xml"
    xml.write_text(
        "<BlastOutput2><Report><Results><Search>"
        "<query-id>BGC027_ctg5_1136</query-id><query-len>300</query-len>"
        "<query-title>BGC013_ctg5_1136 node=NODE_5 bgc=BGC013</query-title>"
        "<hits></hits></Search></Results></Report></BlastOutput2>", encoding="utf-8")
    with pytest.raises(bi.BlastpBindingConflict, match="XML_HITTABLE_BGC_CONFLICT"):
        bi.build_b5_rows("Actinomadura_RB68", ht, xml, top_n=10)


# --- fail-open: a minimal/legacy package with no sealed context is not broken -----------
def test_no_sealed_context_fails_open_and_still_writes(tmp_path):
    # manifest with no strain identity and no gene_context -> cannot cross-check; must not crash,
    # and the legitimate overlay is still written (preserves pre-.409 behaviour for such packages).
    pkg = tmp_path / "package"
    pkg.mkdir()
    (pkg / "manifest.json").write_text(json.dumps({"bgcs": [{"bgc_id": "BGC043"}]}), encoding="utf-8")
    ht = _hits(tmp_path, "open.csv",
               "AS-696|BGC043|gene=ctg66_5|aa=420,WP_1.1,90.0,420,0,0,1,420,1,420,0.0,800,95\n")
    res = bi.ingest_blastp(_master(tmp_path), "AS-696", ht, None, package=str(pkg))
    assert res["binding_guard"]["binding_validated"] is False
    assert res["overlay"]["genes"] == 1
