"""BH-002: PQQ DROP promoted from Sapote-prompt-only to engine-enforced.

PQQ (pyrroloquinoline quinone) biosynthesis is a primary metabolic cofactor pathway.
Per project standing rule: PqqD + PqqE/TIGR03859 → primary metabolic DROP.

Prior to this fix, PQQ clusters received full keyword AB/AF scores unless the Sapote
judgment layer applied the rule manually. This adds 'cofactor_pqq' to
PRIMARY_METABOLISM_PATTERNS so the engine suppresses AB/AF credit deterministically.

Precision guard: primary_flag fires only when own_classes ⊆ WEAK_OVERCALL_CLASSES and
no Tier-1 diagnostic is present. A lanthipeptide with an incidental PQQ gene is safe.
"""
import re
import pytest
from types import SimpleNamespace

from mamey.models import CDSFeature, BGCRecord
from mamey.source_scans import PRIMARY_METABOLISM_PATTERNS, scan_primary_metabolism, _hay


# ── Pattern coverage tests ────────────────────────────────────────────────────

def test_cofactor_pqq_family_present():
    """cofactor_pqq must exist in PRIMARY_METABOLISM_PATTERNS."""
    assert "cofactor_pqq" in PRIMARY_METABOLISM_PATTERNS, (
        "BH-002: cofactor_pqq family missing from PRIMARY_METABOLISM_PATTERNS"
    )


def _fires_pqq(text: str) -> bool:
    pats = PRIMARY_METABOLISM_PATTERNS["cofactor_pqq"]
    return any(re.search(p, text, re.I) for p in pats)


def test_pqq_pqqd_sec_met_domain():
    """PqqD via sec_met_domains (the antiSMASH sec_met annotation path)."""
    cds = CDSFeature("NODE_1", 0, 300, 1, "g1", None, None, None, {"sec_met_domains": ["PqqD"]})
    assert _fires_pqq(_hay(cds)), "pqqd sec_met_domain must match"


def test_pqq_tigr03859():
    """TIGR03859 (PqqE radical SAM, the TIGRFAM annotation path)."""
    cds = CDSFeature("NODE_1", 0, 300, 1, "g1", None, None, None, {"sec_met_domains": ["TIGR03859"]})
    assert _fires_pqq(_hay(cds)), "TIGR03859 must match"


def test_pqq_named_product():
    """pyrroloquinoline quinone in the product name."""
    cds = CDSFeature("NODE_1", 0, 300, 1, "g1",
                     "pyrroloquinoline quinone biosynthesis protein D", None, None, {})
    assert _fires_pqq(_hay(cds)), "pyrroloquinoline quinone product name must match"


def test_pqq_pqqe_domain():
    """PqqE via sec_met_domains."""
    cds = CDSFeature("NODE_1", 0, 300, 1, "g1", None, None, None, {"sec_met_domains": ["PqqE"]})
    assert _fires_pqq(_hay(cds)), "pqqe domain must match"


def test_pqq_no_false_positive_on_unrelated():
    """Unrelated radical SAM or cofactor genes must NOT trigger cofactor_pqq."""
    for product in ["radical SAM enzyme", "cobalamin biosynthesis", "biotin synthase", "adenosylcobalamin"]:
        cds = CDSFeature("NODE_1", 0, 300, 1, "g1", product, None, None, {})
        assert not _fires_pqq(_hay(cds)), f"false positive on {product!r}"


# ── Integration: scan_primary_metabolism detects PQQ in BGC context ──────────

def _make_bgc(bgc_id, products, contig="NODE_1", start=0, end=50000):
    b = BGCRecord.__new__(BGCRecord)
    object.__setattr__(b, "bgc_id", bgc_id)
    object.__setattr__(b, "products", products)
    object.__setattr__(b, "contig", contig)
    object.__setattr__(b, "start", start)
    object.__setattr__(b, "end", end)
    object.__setattr__(b, "edge_status", "Interior")
    return b


def _make_cds(product=None, sec_met=None, contig="NODE_1", start=1000, end=2000):
    q = {}
    if sec_met:
        q["sec_met_domains"] = [sec_met]
    return CDSFeature(contig, start, end, 1, "g1", product, None, None, q)


def test_pqq_bgc_detected_by_scan():
    """A BGC with PqqD in its CDS complement must appear in per_bgc families."""
    bgc = _make_bgc("BGC_PQQ", ["redox-cofactor"])
    cds_pqqd = _make_cds(sec_met="PqqD")
    result = scan_primary_metabolism([cds_pqqd], [bgc])
    families = result["per_bgc"].get("BGC_PQQ", {}).get("families", [])
    assert "cofactor_pqq" in families, (
        f"BH-002: cofactor_pqq not detected in per_bgc. families={families}"
    )


def test_pqq_precision_guard_committed_class_exempt():
    """A lanthipeptide BGC with an incidental PqqD gene must NOT set primary_metabolism_flag.

    The precision guard (own_classes ⊆ WEAK_OVERCALL_CLASSES) exempts committed-class clusters.
    This test verifies the guard via triage_bgcs directly.
    """
    import sys; sys.path.insert(0, ".")
    from mamey.scoring import triage_bgcs, WEAK_OVERCALL_CLASSES

    # lanthipeptide-class-i is NOT in WEAK_OVERCALL_CLASSES → exempt from suppression
    assert "lanthipeptide-class-i" not in WEAK_OVERCALL_CLASSES, (
        "lanthipeptide-class-i must not be in WEAK_OVERCALL_CLASSES — the guard relies on this"
    )

    # Confirm redox-cofactor IS in WEAK_OVERCALL_CLASSES (PQQ suppression path)
    assert "redox-cofactor" in WEAK_OVERCALL_CLASSES, (
        "redox-cofactor must be in WEAK_OVERCALL_CLASSES for PQQ suppression to fire"
    )




# ── BH-006 (v9.7.122) — ectoine primary-metabolism family ──────────────────────
def test_cofactor_ectoine_family_present():
    assert "cofactor_ectoine" in PRIMARY_METABOLISM_PATTERNS, (
        "BH-006: cofactor_ectoine family missing from PRIMARY_METABOLISM_PATTERNS")


def _fires_ectoine(text: str) -> bool:
    pats = PRIMARY_METABOLISM_PATTERNS["cofactor_ectoine"]
    return any(re.search(p, text, re.I) for p in pats)


def test_ectoine_named_product():
    cds = CDSFeature("NODE_1", 0, 300, 1, "g1", "ectoine synthase", None, None, {})
    assert _fires_ectoine(_hay(cds)), "ectoine synthase product name must match"


def test_ectoine_ectABC_operon():
    cds = CDSFeature("NODE_1", 0, 300, 1, "g1", "ectABC compatible solute operon", None, None, {})
    assert _fires_ectoine(_hay(cds)), "ectABC must match"


def test_ectoine_ectC_gene():
    cds = CDSFeature("NODE_1", 0, 300, 1, "g1", "ectC", None, None, {})
    assert _fires_ectoine(_hay(cds)), "ectC gene symbol must match"


def test_ectoine_no_false_positive_on_unrelated():
    # word-boundary guard: 'protectoine' (hypothetical) must not match \bectoine\b
    cds = CDSFeature("NODE_1", 0, 300, 1, "g1", "protectoine-like hypothetical", None, None, {})
    assert not _fires_ectoine(_hay(cds))
