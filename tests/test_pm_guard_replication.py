"""pm_guard second arm — DNA-replication-core family in the primary-metabolism gate.

The v9.7.7 gate keyed housekeeping (topoisomerase/ribosomal/...) + pigment families. The replication-core
machinery (dnaB/E/G/N, primase, replisome, ligase, sliding clamp) slipped past it. The new family plugs into
the same per-BGC, flank=0, weak-overcall-gated mechanism: it floors a region only when the region's OWN class
is a weak/over-call label and no Tier-1 diagnostic fires (curated-list precision — DnaA-like ATPase
regulators are NOT matched).

Standalone: python3 tests/test_pm_guard_replication.py
"""
from __future__ import annotations
import sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mamey.models import BGCRecord, CDSFeature
from mamey.source_scans import scan_primary_metabolism
from mamey.scoring import triage_bgcs


def _bgc(bgc_id, products, start=1, end=9000):
    return BGCRecord(bgc_id=bgc_id, contig="c1", region_number=1, start=start, end=end, contig_length=20000,
                     products=list(products), edge_status="Interior", architecture_confidence="A")


def _cds(product, start, end, contig="c1"):
    return CDSFeature(contig=contig, start=start, end=end, strand=1, locus_tag="x", product=product, translation="M")


def test_replication_core_detected_in_own_region():
    bgcs = [_bgc("BGC043", ["terpene"])]
    cds = [_cds("replicative DNA helicase DnaB", 1000, 2000), _cds("DNA primase", 3000, 4000)]
    per = scan_primary_metabolism(cds, bgcs)["per_bgc"]
    assert "replication_core" in per["BGC043"]["families"]


def test_dnaa_like_regulator_not_matched():
    """Curated precision: a DnaA-like ATPase regulator must NOT trip the replication-core family."""
    bgcs = [_bgc("BGC050", ["terpene"])]
    cds = [_cds("DnaA-like ATPase AAA domain protein", 1000, 2000)]
    per = scan_primary_metabolism(cds, bgcs)["per_bgc"]
    assert per["BGC050"]["families"] == []


def test_gate_floors_replication_core_under_weak_class():
    """replication-core + weak own class (terpene) + no diagnostic -> flagged, AB/AF suppressed."""
    bgcs = [_bgc("BGC043", ["terpene"]), _bgc("BGC900", ["NRPS", "T1PKS"])]
    scans = SimpleNamespace(primary_metabolism={"per_bgc": {"BGC043": {"families": ["replication_core"]}}},
                            cctt={"per_bgc": {}}, resistance_tiers={"per_bgc": {}})
    recs = {r.bgc_id: r for r in triage_bgcs(bgcs, None, scans)}
    assert recs["BGC043"].primary_metabolism_flag is True
    assert recs["BGC043"].ab_score <= 25.0 and recs["BGC043"].ab_score < recs["BGC900"].ab_score


def test_gate_does_not_floor_replication_core_under_real_class():
    """A genuine T1PKS lead with an incidental replication gene is NOT floored (own class not weak)."""
    bgcs = [_bgc("BGC077", ["T1PKS", "NRPS"])]
    scans = SimpleNamespace(primary_metabolism={"per_bgc": {"BGC077": {"families": ["replication_core"]}}},
                            cctt={"per_bgc": {}}, resistance_tiers={"per_bgc": {}})
    recs = {r.bgc_id: r for r in triage_bgcs(bgcs, None, scans)}
    assert recs["BGC077"].primary_metabolism_flag is False


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    p = 0
    for fn in fns:
        try:
            fn(); p += 1; print(f"PASS {fn.__name__}")
        except AssertionError as e:
            print(f"FAIL {fn.__name__}: {e}")
    print(f"\n{p}/{len(fns)} passed")


def test_topoisomerase_gene_symbols_caught():
    """v9.7.16: gene-symbol annotations (gyrA/topA/parC/tmk) are caught, not just descriptive names."""
    import importlib
    from mamey.source_scans import scan_primary_metabolism as _sp
    from mamey.models import BGCRecord as _B, CDSFeature as _C
    b = [_B(bgc_id="BGCt", contig="c1", region_number=1, start=1, end=9000, contig_length=20000,
            products=["NRPS-like"], edge_status="Interior")]
    for prod in ["gyrA", "topA", "parC", "tmk"]:
        c = [_C(contig="c1", start=100, end=400, strand=1, locus_tag="x", product=prod, translation="M")]
        assert "housekeeping" in _sp(c, b)["per_bgc"]["BGCt"]["families"], f"missed {prod}"
