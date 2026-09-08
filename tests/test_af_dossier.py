"""Antifungal (AF) Lead Dossier — cohort deliverable joining the AF lead board to
MEASURED strain-level Candida activity. Tests the join, the graceful no-crosswalk path,
and the claim-safety framing text.
"""
import json

from mamey.af_dossier import (
    run,
    build_dossier,
    load_crosswalk,
    _measured_flag,
    _find_packages,
    _clean_kcb,
    CLAIM_SAFETY_LINES,
)


def test_clean_kcb_null_placeholders():
    # board null placeholders count as reference-dark (absent anchor)
    assert _clean_kcb("UNRESOLVED", "") == ""
    assert _clean_kcb("", "none") == ""
    assert _clean_kcb("-", "n/a") == ""
    # a real anchor wins over a null placeholder
    assert _clean_kcb("UNRESOLVED", "rhizocticin A") == "rhizocticin A"
    assert _clean_kcb("rhizocticin A", "") == "rhizocticin A"


def _pkg(tmp_path, strain, taxonomy, af_rows, triage_rows):
    """Synthesize a minimal sealed package: manifest + AF lead board + triage board."""
    pkg = tmp_path / strain / "package"
    pkg.mkdir(parents=True)
    (pkg / "manifest.json").write_text(json.dumps(
        {"strain_id": strain, "taxonomy": taxonomy, "release": "PRIVATE"}))
    # AF lead board: Board_rank,BGC_ID,Contig,Node_ID,Products,AF_score,Lead_tier,KCB_top,Downgrade,Corrected_rank
    afh = "Board_rank,BGC_ID,Contig,Node_ID,Products,AF_score,Lead_tier,KCB_top,Downgrade,Corrected_rank\n"
    afb = "".join(
        f"{i+1},{b},ctg,ctg,{p},{s},{t},{k},,{i+1}\n"
        for i, (b, p, s, t, k) in enumerate(af_rows))
    (pkg / f"{strain}_4c_AF_lead_board.csv").write_text(afh + afb)
    # triage board (only the columns af_dossier reads)
    th = "BGC_ID,Products,AF_auto,Novelty_auto,Lead_tier_auto,KCB_top\n"
    tb = "".join(f"{b},{p},{af},{nov},{lt},{k}\n" for b, p, af, nov, lt, k in triage_rows)
    (pkg / f"{strain}_4_triage_board.csv").write_text(th + tb)
    return pkg


def _crosswalk(tmp_path, rows):
    p = tmp_path / "crosswalk.csv"
    header = "strain,genus,host,anti_MRSA,anti_Candida,closest_type\n"
    body = "".join(f"{s},{g},{h},{mr},{ca},{ct}\n" for s, g, h, mr, ca, ct in rows)
    p.write_text(header + body)
    return p


def test_measured_flag_normalization():
    assert _measured_flag("+") == "positive (+)"
    assert _measured_flag("-") == "negative (-)"
    assert _measured_flag("") == "no measured data"
    assert _measured_flag("screen-positive") == "screen-positive"  # free text passthrough


def test_load_crosswalk_missing_path():
    # graceful: no path / missing file -> empty dict, engine still runs
    assert load_crosswalk(None) == {}
    assert load_crosswalk("/no/such/file.csv") == {}


def test_join_measured_candida(tmp_path):
    """A Candida-positive strain with a High AF lead becomes a standout, joined to measured."""
    _pkg(tmp_path, "AS-168", "Streptomyces sp.",
         af_rows=[("BGC004", "phosphonate", "28.0", "High", "rhizocticin A"),
                  ("BGC020", "NRPS", "12.0", "Inventory", "")],
         triage_rows=[("BGC004", "phosphonate", "28.0", "53.0", "High", "rhizocticin A"),
                      ("BGC020", "NRPS", "12.0", "30.0", "Inventory", "")])
    xw = _crosswalk(tmp_path, [("AS-168", "Streptomyces sp.", "Bombus sp.", "+", "+", "S. xylanilyticus")])
    res = run(tmp_path, activity_table=xw, depth=3)

    assert res["packages"] == 1
    assert res["lead_rows"] == 2
    assert res["measured_join"] == 1
    assert res["standout_strains"] == ["AS-168"]

    rows = {r["bgc_id"]: r for r in res["rows"]}
    # measured activity is STRAIN-level and joined onto every BGC row
    assert rows["BGC004"]["measured_candida_strain"] == "positive (+)"
    assert rows["BGC020"]["measured_candida_strain"] == "positive (+)"
    assert rows["BGC004"]["host"] == "Bombus sp."
    assert rows["BGC004"]["standout_strain"] == "yes"
    # capacity kept in separate columns
    assert rows["BGC004"]["af_capacity_score"] == 28.0
    assert rows["BGC004"]["af_lead_tier"] == "High"
    assert rows["BGC004"]["novelty_prior"] == "53.0"
    # reference-dark derives from an empty KCB anchor
    assert rows["BGC004"]["reference_dark"] == "no"
    assert rows["BGC020"]["reference_dark"] == "yes"


def test_ranking_standout_first(tmp_path):
    """Standout strain (Candida+ AND High lead) ranks above an untested strain with a higher AF score."""
    _pkg(tmp_path, "AS-untested", "Streptomyces sp.",
         af_rows=[("BGC001", "T1PKS", "99.0", "High", "kcbX")],
         triage_rows=[("BGC001", "T1PKS", "99.0", "40.0", "High", "kcbX")])
    _pkg(tmp_path, "AS-standout", "Streptomyces sp.",
         af_rows=[("BGC001", "phosphonate", "30.0", "High", "kcbY")],
         triage_rows=[("BGC001", "phosphonate", "30.0", "50.0", "High", "kcbY")])
    xw = _crosswalk(tmp_path, [("AS-standout", "Streptomyces sp.", "Bombus sp.", "-", "+", "S. foo")])
    res = run(tmp_path, activity_table=xw, depth=3)
    # despite a lower AF score, the standout strain's row comes first
    assert res["rows"][0]["strain"] == "AS-standout"


def test_graceful_no_crosswalk(tmp_path):
    """No crosswalk -> capacity-only dossier; measured columns say 'no measured data'."""
    _pkg(tmp_path, "AS-320", "Streptomyces sp.",
         af_rows=[("BGC001", "terpene", "20.0", "Medium", "kcbZ")],
         triage_rows=[("BGC001", "terpene", "20.0", "35.0", "Medium", "kcbZ")])
    res = run(tmp_path, depth=3)  # no activity_table
    assert res["measured_join"] == 0
    assert res["standout_strains"] == []
    r = res["rows"][0]
    assert r["measured_candida_strain"] == "no measured data"
    assert r["genus"] == "Streptomyces"          # falls back to manifest taxonomy
    assert r["af_capacity_score"] == 20.0        # capacity still present
    assert "capacity-only dossier" in res["markdown"]


def test_triage_fallback_when_no_af_board(tmp_path):
    """When the AF lead board file is absent, AF leads come from the triage AF_auto column."""
    pkg = tmp_path / "AS-777" / "package"
    pkg.mkdir(parents=True)
    (pkg / "manifest.json").write_text(json.dumps(
        {"strain_id": "AS-777", "taxonomy": "Nocardia sp.", "release": "PRIVATE"}))
    (pkg / "AS-777_4_triage_board.csv").write_text(
        "BGC_ID,Products,AF_auto,Novelty_auto,Lead_tier_auto,KCB_top\n"
        "BGC001,NRPS,18.0,44.0,Medium,anchorA\n"
        "BGC002,terpene,0.0,20.0,Inventory,\n")  # AF_auto 0 -> not a lead
    res = run(tmp_path, depth=3)
    assert res["lead_rows"] == 1
    assert res["rows"][0]["bgc_id"] == "BGC001"
    assert res["rows"][0]["af_capacity_score"] == 18.0


def test_claim_safety_framing_present(tmp_path):
    """The dossier must carry the strain-vs-BGC claim-safety framing text."""
    _pkg(tmp_path, "AS-168", "Streptomyces sp.",
         af_rows=[("BGC004", "phosphonate", "28.0", "High", "rhizocticin A")],
         triage_rows=[("BGC004", "phosphonate", "28.0", "53.0", "High", "rhizocticin A")])
    xw = _crosswalk(tmp_path, [("AS-168", "Streptomyces sp.", "Bombus sp.", "+", "+", "S. xylanilyticus")])
    out = tmp_path / "dossier"
    res = run(tmp_path, out_dir=out, activity_table=xw, depth=3)
    md = (out / "AF_LEAD_DOSSIER.md").read_text()
    # explicit claim-safety framing: hypothesis, not production claim; strain vs class level
    assert "hypothesis for what MIGHT underlie" in md or "hypothesis for what might underlie" in md.lower()
    assert "STRAIN-level" in md
    assert "NOT" in md
    assert "produces the active compound" in md
    # every claim-safety line survives into the rendered header
    for line in CLAIM_SAFETY_LINES:
        assert line in res["claim_safety"]
    assert (out / "AF_LEAD_DOSSIER.csv").is_file()


def test_find_packages_direct_and_nested(tmp_path):
    pkg = _pkg(tmp_path, "AS-1", "Streptomyces sp.",
               af_rows=[("BGC001", "NRPS", "10.0", "Medium", "k")],
               triage_rows=[("BGC001", "NRPS", "10.0", "30.0", "Medium", "k")])
    # nested scan finds it
    assert pkg in _find_packages(tmp_path, depth=3)
    # pointing directly at the package dir also works
    assert _find_packages(pkg, depth=3) == [pkg]
