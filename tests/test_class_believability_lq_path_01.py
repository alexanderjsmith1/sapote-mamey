"""LQ-PATH-01 (v9.7.330): committed-step class-believability engine.

Exercises the uniform tier logic (HIGH/MEDIUM/LOW/SUSPECT/NONE) on the validated phosphonate module,
and the net-new POOLED per-strain pass that flags a split pathway when the gateway and its committed
pull sit on different BGCs (the "best gene is an orphan the BGC-local view rates LOW" case).
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mamey.class_believability import (  # noqa: E402
    scan_bgc, classify, scan_package, PHOSPHONATE,
)


def _cds(lt, domains=(), product="", gene_functions=""):
    return {"locus_tag": lt, "sec_met_domains": list(domains),
            "product": product, "gene_functions": gene_functions}


def _tier(cds_list):
    return classify(scan_bgc(cds_list, PHOSPHONATE), PHOSPHONATE)[0]


def test_high_full_committed_signature():
    # PepM gateway (good bit) + TPP decarboxylase committed pull + aminotransferase warhead
    cds = [
        _cds("g1", ["PEP_mutase (E-value: 1e-70, bitscore: 210.0)"]),
        _cds("g2", ["TPP_enzyme_N"]),
        _cds("g3", ["Aminotran_1_2"]),
    ]
    assert _tier(cds) == "HIGH"


def test_low_weak_gateway_only_is_named_fp():
    # PepM only, weak (<60), no committed pull, no warheads -> LOW (isocitrate-lyase superfamily FP)
    cds = [_cds("g1", ["PEP_mutase (E-value: 0.1, bitscore: 55.0)"])]
    assert _tier(cds) == "LOW"


def test_suspect_class_flag_without_gateway():
    # antiSMASH/CCTT flags phosphonate but no PepM gateway captured -> SUSPECT
    cds = [_cds("g1", product="phosphonate", gene_functions="hypothetical protein")]
    assert _tier(cds) == "SUSPECT"


def test_none_when_neither_gateway_nor_flag():
    cds = [_cds("g1", ["Condensation"], product="NRPS")]
    assert _tier(cds) == "NONE"


def _write_pkg(tmp_path, strain, bgcs, inv_rows):
    pkg = tmp_path / strain / "package"
    pkg.mkdir(parents=True)
    with open(pkg / f"{strain}_gene_context.jsonl", "w", encoding="utf-8") as f:
        for bid, cds in bgcs:
            f.write(json.dumps({"bgc_id": bid, "cds": cds}) + "\n")
    with open(pkg / f"{strain}_2_inventory.csv", "w", encoding="utf-8") as f:
        f.write("BGC_ID,Products,Boundary,Length_kb,KCB_top,Contig\n")
        for r in inv_rows:
            f.write(r + "\n")
    return pkg


def test_pooled_split_pathway_candidate(tmp_path):
    # Gateway (PepM) on BGC001 alone -> LOW locally; committed pull + warhead on BGC002 (no gateway)
    # -> NONE locally. Pooled union has gateway + committed + warhead -> HIGH, stronger than any single
    # BGC, so it must flag a split-pathway candidate.
    pkg = _write_pkg(
        tmp_path, "AS-TEST",
        bgcs=[
            ("BGC001", [_cds("a1", ["PEP_mutase (E-value: 1e-70, bitscore: 200.0)"])]),
            ("BGC002", [_cds("b1", ["TPP_enzyme_N"]), _cds("b2", ["Aminotran_1_2"])]),
        ],
        inv_rows=["BGC001,phosphonate,Edge,20,,ctgA", "BGC002,other,Interior,15,,ctgB"],
    )
    res = scan_package(pkg, PHOSPHONATE)
    # locally, no BGC is HIGH
    assert all(r["believability"] != "HIGH" for r in res["local"])
    # pooled reaches HIGH and is flagged as a split candidate
    assert res["pooled"] is not None
    assert res["pooled"]["believability"] == "HIGH"
    assert res["pooled"]["split_pathway_candidate"] is True


def test_pooled_not_split_when_single_bgc_already_high(tmp_path):
    pkg = _write_pkg(
        tmp_path, "AS-WHOLE",
        bgcs=[("BGC001", [
            _cds("a1", ["PEP_mutase (E-value: 1e-70, bitscore: 210.0)"]),
            _cds("a2", ["TPP_enzyme_N"]),
            _cds("a3", ["Aminotran_1_2"]),
        ])],
        inv_rows=["BGC001,phosphonate,Interior,46,rhizocticin A,ctg1"],
    )
    res = scan_package(pkg, PHOSPHONATE)
    assert res["local"][0]["believability"] == "HIGH"
    assert res["pooled"]["split_pathway_candidate"] is False
