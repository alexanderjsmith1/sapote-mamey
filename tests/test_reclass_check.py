"""reclass-check (L1): antiSMASH label vs diagnostic-domain discrepancy. Hermetic.

Matches the .204 landed test convention (cf. test_arts_ingest.py): synthetic fixtures
in a tempdir, importlib-loaded tool, assertions on the analyze() return structure.
No dependency on private strain data.
"""
import importlib.util, json, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_s = importlib.util.spec_from_file_location("reclass_check", ROOT / "tools" / "reclass_check.py")
rc = importlib.util.module_from_spec(_s); _s.loader.exec_module(rc)


# minimal curated map exercising the three finding kinds + the FP guards
_MAP = {
    "_meta": {"purpose": "test fixture map"},
    "classes": {
        "thiopeptide": {
            "discriminating_domains": ["YcaO", "TIGR03882", "Thiopeptide_F_RRE"],
            "specific_domains": ["Thiopeptide_F_RRE", "TIGR03882"],
            "min_domains": 1, "require_specific": True, "in_sec_met_domains": True,
        },
        "T1PKS": {
            "discriminating_domains": ["PKS_KS", "PKS_AT", "PKSI-KS_m3"],
            "specific_domains": ["PKS_KS", "PKS_AT", "PKSI-KS_m3"],
            "min_domains": 2, "require_specific": True, "in_sec_met_domains": True,
        },
        "NRP-metallophore": {
            "discriminating_domains": ["MbtH"], "specific_domains": ["MbtH"],
            "min_domains": 1, "require_specific": True, "in_sec_met_domains": True,
        },
    },
    "skip_domain_check": {"classes": ["terpene", "ectoine", "saccharide"]},
}


def _write_pkg(d):
    p = Path(d)
    # triage board: 4 BGCs
    (p / "AS-TEST_4_triage_board.csv").write_text(
        "Rank,BGC_ID,Node_ID,antiSMASH_Region,Products\n"
        "1,BGC001,NODE_1_length_100000_cov_50,region001,RiPP; azole-containing-RiPP\n"   # thiopeptide undersell
        "2,BGC002,NODE_2_length_90000_cov_50,region001,PKS; T1PKS\n"                      # concordant, no flag
        "3,BGC003,NODE_3_length_80000_cov_50,region001,NRPS\n"                            # MbtH -> undeclared metallophore
        "4,BGC004,NODE_4_length_70000_cov_50,region001,terpene\n"                         # skip-domain, no flag
    )
    # gene_by_gene: domains per BGC. BGC004 carries a TatD_DNase to test the substring guard
    (p / "AS-TEST_gene_by_gene_all_bgcs.csv").write_text(
        "bgc_id,locus_tag,sec_met_domains\n"
        "BGC001,ctg1_1,YcaO;TIGR03882;Thiopeptide_F_RRE\n"   # thiopeptide markers under azole label
        "BGC002,ctg2_1,PKS_KS;PKS_AT;PKSI-KS_m3\n"           # T1PKS markers, label already T1PKS -> concordant
        "BGC003,ctg3_1,AMP-binding;MbtH\n"                    # MbtH metallophore marker, label bare NRPS
        "BGC004,ctg4_1,TatD_DNase;Terpene_synth\n"           # TatD must NOT match a 'TD' signature; terpene skipped
    )
    return str(p)


def test_thiopeptide_undersell_flagged():
    with tempfile.TemporaryDirectory() as d:
        pkg = _write_pkg(d)
        out, summary = rc.analyze(pkg, _MAP)
        b001 = [e for e in out if e["bgc_id"] == "BGC001"]
        assert b001, "BGC001 azole-RiPP with Thiopeptide_F_RRE should flag"
        kinds = {f["cls"] for f in b001[0]["findings"]}
        assert "thiopeptide" in kinds


def test_concordant_bgc_not_flagged():
    with tempfile.TemporaryDirectory() as d:
        pkg = _write_pkg(d)
        out, summary = rc.analyze(pkg, _MAP)
        assert not any(e["bgc_id"] == "BGC002" for e in out), "T1PKS-labelled T1PKS should not flag"


def test_undeclared_metallophore_flagged():
    with tempfile.TemporaryDirectory() as d:
        pkg = _write_pkg(d)
        out, summary = rc.analyze(pkg, _MAP)
        b003 = [e for e in out if e["bgc_id"] == "BGC003"]
        assert b003 and any(f["cls"] == "NRP-metallophore" for f in b003[0]["findings"])


def test_skip_domain_and_substring_guard():
    with tempfile.TemporaryDirectory() as d:
        pkg = _write_pkg(d)
        out, summary = rc.analyze(pkg, _MAP)
        # BGC004 is terpene (skip-domain) AND carries TatD_DNase which must not match a bare 'TD'.
        # It should NOT be flagged.
        assert not any(e["bgc_id"] == "BGC004" for e in out), \
            "terpene (skip) + TatD_DNase substring must not flag"


def test_summary_structure():
    with tempfile.TemporaryDirectory() as d:
        pkg = _write_pkg(d)
        out, summary = rc.analyze(pkg, _MAP)
        assert summary["n_bgc"] == 4
        assert summary["n_flagged"] == 2          # BGC001 + BGC003
        assert "undeclared_strong" in summary["kinds"]


def test_missing_inputs_degrades_honestly():
    with tempfile.TemporaryDirectory() as d:
        out, summary = rc.analyze(d, _MAP)         # empty dir
        assert summary["n_flagged"] == 0 and "error" in summary
