"""Tests for the compound-family report layer (roadmap #10). Freeze-safe: asserts classification +
that a bogus anchor never fabricates a structure."""
import csv
import os

try:
    from mamey import compound_family_report as cfr
    from mamey import npatlas_structure as nps
except ImportError:  # standalone (conftest puts mamey/ on path)
    import compound_family_report as cfr
    import npatlas_structure as nps


def test_housekeeping_tokens_are_housekeeping():
    for anchor in ("geosmin", "2-methylisoborneol", "isorenieratene", "ectoine"):
        fam, target, _ = cfr.classify(anchor)
        assert target == "housekeeping", (anchor, target)


def test_polyene_is_antifungal_and_gpa_is_antibacterial():
    assert cfr.classify("nystatin")[1] == "AF"
    assert cfr.classify("candicidin A")[1] == "AF"
    fam, target, _ = cfr.classify("balhimycin")
    assert target == "AB" and "Glycopeptide" in fam


def test_arylpolyene_not_confused_with_polyene_macrolide():
    # a non-polyene-macrolide arylpolyene anchor must NOT resolve to the AF polyene family
    fam, target, _ = cfr.classify("pepticinnamin")
    assert "Polyene" not in fam


def test_unmapped_anchor_is_other():
    fam, target, _ = cfr.classify("zzz-not-a-real-compound-anchor")
    assert target == "other" and fam.startswith("(unmapped")


def test_rules_file_loads_and_is_ordered():
    rules = cfr.load_rules()
    assert len(rules) >= 30
    # first rule must be the polyene AF family (most specific membrane-active macrolides first)
    assert rules[0][1][1] == "AF"


def test_bogus_name_never_fabricates_structure():
    # claim-safety: a name not in NP Atlas returns match none/unavailable, empty inchikey
    r = nps.resolve_name_to_structure("definitely-not-a-real-compound-zzz-000")
    assert r["match_type"] in ("none", "unavailable")
    assert r["inchikey"] == ""


def test_run_on_synthetic_package(tmp_path):
    # minimal sealed-package fixture: a triage board with three anchored BGCs
    board = tmp_path / "SYN-1_4_triage_board.csv"
    with open(board, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["BGC_ID", "KCB_top", "Products", "AF_auto", "AB_auto", "Novelty_auto",
                    "Lead_tier_auto", "KCB_score"])
        w.writerow(["BGC001", "BGC0001.1 | nystatin | knownclusterblast #1", "T1PKS", "60", "20", "", "AF_LEAD", "80"])
        w.writerow(["BGC002", "BGC0002.1 | geosmin | knownclusterblast #1", "terpene", "10", "10", "", "", "90"])
        w.writerow(["BGC003", "", "other", "10", "10", "", "", ""])  # no anchor -> skipped
    res = cfr.run(str(tmp_path), out_dir=str(tmp_path), with_structures=False)
    assert res["status"] == "ok"
    assert res["rows"] == 2  # BGC003 has no anchor
    out = tmp_path / "COMPOUND_FAMILIES" / "ANCHORED_BGC_COMPOUND_FAMILIES.tsv"
    assert out.exists()
    with open(out) as fh:
        rows = [r for r in csv.DictReader((l for l in fh if not l.startswith("#")), delimiter="\t")]
    tc = {r["bgc_id"]: r["target_class"] for r in rows}
    assert tc["BGC001"] == "AF" and tc["BGC002"] == "housekeeping"


def test_excluded_strain_emits_no_family_map(tmp_path):
    board = tmp_path / "AS-920_4_triage_board.csv"
    with open(board, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["BGC_ID", "KCB_top", "Products", "AF_auto", "AB_auto"])
        w.writerow(["BGC001", "BGC0001.1 | nystatin | kcb", "T1PKS", "60", "20"])
    res = cfr.run(str(tmp_path), out_dir=str(tmp_path))
    assert res["status"] == "excluded_strain" and res["rows"] == 0

