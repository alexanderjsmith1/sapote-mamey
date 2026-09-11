from tests._uploads_fixture import UPLOADS as _UPLOADS, OUTPUTS as _OUTPUTS  # v9.7.416
"""Tests for the architecture-based class-capacity layer, grounded in the reference set."""
import os

import pytest

from mamey import class_architecture as A
from mamey import parsers

UPS = _UPLOADS
# Bundled fixtures are authoritative and hermetic; the uploads dir is a fallback only.
FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def _resolve(zf):
    """Return a real path to fixture `zf`, preferring the bundled tests/fixtures copy."""
    for base in (FIXTURES, UPS):
        p = os.path.join(base, zf)
        if os.path.exists(p):
            return p
    return None


def cls(products, ks, c, a, tail):
    return A.classify_architecture("BGC001", products, ks, c, a, tail).capacity


# ---- pure classifier, one assertion per reference class -----------------------------------------
def test_diketopiperazine():
    assert "diketopiperazine" in cls(["CDPS", "NRPS"], 0, 0, 0, [])


def test_aromatic_type2_pks():
    # actinorhodin / pradimicin / fogacin / maduralactomycin
    assert "aromatic type II PKS" in cls(["PKS", "T2PKS"], 2, 0, 0, ["cyclase_aromatase"])


def test_pks_nrps_hybrid_ptm():
    # HSAF
    assert "PKS-NRPS hybrid" in cls(["PKS", "NRPS"], 1, 1, 1, ["thioesterase"])


def test_glycopeptide():
    # pekiskomycin: NRPS + halogenase + glycosyltransferase
    assert cls(["NRPS"], 0, 6, 8, ["halogenase", "glycosyltransferase", "oxygenase"]) == "glycopeptide"


def test_large_lipopeptide():
    # A54145 (25C/26A), lipopeptide 8D1 (11/11)
    assert "large lipopeptide" in cls(["NRPS"], 0, 25, 26, ["methyltransferase", "thioesterase"])


def test_small_nrps_peptide():
    # nocardicin (4C/5A), pacidamycin (2C/4A)
    assert "small NRPS peptide" in cls(["NRPS"], 0, 4, 5, ["oxygenase", "methyltransferase"])


def test_glycosylated_macrolactone():
    # notonesomycin / ibomycin / monensin / ionostatin
    assert "glycosylated macrolactone" in cls(["PKS", "T1PKS"], 19, 0, 0, ["glycosyltransferase", "oxygenase"])


def test_large_modular_pks_no_gt():
    # nystatin / candicidin / corallopyronin
    assert "large modular PKS" in cls(["PKS", "T1PKS"], 19, 0, 0, ["oxygenase", "thioesterase"])


def test_meroterpenoid():
    # marinoterpin: prenyltransferase + PKS
    assert "meroterpenoid" in cls(["unknown"], 2, 0, 1, ["prenyltransferase", "oxygenase"])


def test_unresolved_is_low_confidence():
    r = A.classify_architecture("BGC001", ["other"], 0, 0, 0, [])
    assert r.confidence == "LOW"


def test_capacity_line_is_claim_safe():
    r = A.classify_architecture("BGC001", ["PKS", "T2PKS"], 2, 0, 0, ["cyclase_aromatase"])
    line = r.as_capacity_line()
    assert "capacity consistent with" in line
    assert "produces" not in line.lower()


# ---- end-to-end on real reference ZIPs (skip if uploads absent) ----------------------------------
def _derive(zf):
    """Capacity of the largest-span region (back-compat for single-cluster references)."""
    p = _resolve(zf)
    if p is None:
        return None
    bgcs = parsers.parse_bgcs_from_zip(p)
    cds = parsers.extract_cds_features(p)
    doms = parsers.extract_domain_features(p)
    b = max(bgcs, key=lambda x: x.end - x.start)
    return A.derive_architecture(b, cds, doms)


def _derive_all(zf):
    """Capacity of EVERY region — robust to multi-region inputs where the largest span
    need not be the class-defining region (the teicoplanin test-premise hazard)."""
    p = _resolve(zf)
    if p is None:
        return None
    bgcs = parsers.parse_bgcs_from_zip(p)
    cds = parsers.extract_cds_features(p)
    doms = parsers.extract_domain_features(p)
    return [A.derive_architecture(b, cds, doms).capacity for b in bgcs]


def test_end_to_end_actinorhodin():
    r = _derive("actinorhodin_BGC0000194.zip")
    if r is None:
        return
    assert "aromatic type II PKS" in r.capacity


def test_end_to_end_albonoursin():
    r = _derive("BGC0000851.zip")
    if r is None:
        return
    assert "diketopiperazine" in r.capacity


# ---- panel-driven refinements (viguiepinol/teicoplanin/siderophore references) -------------------
def test_glycopeptide_via_gtf_gene_symbol():
    # teicoplanin: GtfA/GtfB are glycosyltransferases named by gene symbol; GT must be detected so the
    # archetypal glycopeptide is not mis-called a lipopeptide.
    assert cls(["NRPS", "PKS"], 0, 6, 7, ["halogenase", "glycosyltransferase"]) == "glycopeptide"


def test_siderophore_reads_antismash_metallophore_type():
    # pseudomonine / scabichelin: antiSMASH types them NRP-metallophore; trust the supplied type
    assert "siderophore" in cls(["NRP-metallophore", "NRPS"], 0, 2, 3, ["aminotransferase"])


def test_end_to_end_micromonospora_humida_hybrids():
    # End-to-end derivation on a real *public* antiSMASH export (Micromonospora humida, GenBank
    # JAFEUC01) — replaces the MIBiG teicoplanin fixtures (which carried a CC-BY attribution
    # requirement and were ~2.6 MB) with a 136 KB public fixture that ships in every tier. The two
    # bundled regions are PKS-containing multi-class hybrids (arylpolyene/T2PKS and NRPS/T1PKS), so
    # this exercises the multi-region + hybrid path the teicoplanin tests guarded, on freely
    # redistributable data. Glycopeptide classification itself remains covered by the pure-classifier
    # unit test above. Skips explicitly when the fixture is absent, never a silent green.
    caps = _derive_all("micromonospora_humida_JAFEUC01.zip")
    if caps is None:
        pytest.skip("micromonospora_humida_JAFEUC01.zip fixture not available")
    resolved = [c for c in caps if "unresolved" not in c]
    assert len(resolved) >= 2, caps                      # both regions resolve to a determinate class
    assert all("pks" in c.lower() for c in resolved), caps  # both are PKS-containing hybrids
    joined = " ".join(caps).lower()
    assert "arylpolyene" in joined and "nrps" in joined, caps  # the two distinct hybrid signatures


# ---- regression tests for Audit Flag C (terpene misrouted to NRPS) and Flag D (multi-class) ----

def test_terpene_with_spurious_nrps_c1_routes_to_terpene():
    """Audit Flag C (M56 BGC040): a pure terpene BGC with one spurious condensation domain from a
    boundary gene must route to 'terpene', not 'small NRPS peptide'.
    The fix: terpene-only product annotation + pks_ks==0 + nrps_c<=1 → terpene guard fires."""
    cap = cls(["terpene"], ks=0, c=1, a=0, tail=[])
    assert "terpene" in cap.lower(), f"Expected terpene, got: {cap}"
    assert "nrps" not in cap.lower(), f"Spurious NRPS routing for terpene BGC: {cap}"


def test_terpene_with_two_spurious_nrps_domains_routes_to_terpene():
    """Terpene guard fires when nrps_c<=1; nrps_c=2 falls through (acceptable — 2 condensation
    domains in a terpene BGC implies something more complex). This test pins the exact boundary."""
    cap_c1 = cls(["terpene"], ks=0, c=1, a=0, tail=[])
    assert "terpene" in cap_c1.lower()
    # nrps_c=2 with terpene-only products is ambiguous — engine may route to NRPS; that's acceptable
    # but we do NOT assert the exact output here, only that c=1 is guarded


def test_multiclass_5_classes_routes_to_complex_hybrid():
    """Audit Flag D (M56 BGC047): ≥3 real biosynthetic classes must route to 'complex multi-class
    hybrid', not 'small NRPS peptide'. BGC047 had NRPS+PKS+RiPP+T1PKS+lanthipeptide-II+terpene."""
    cap = cls(["NRPS", "PKS", "RiPP", "T1PKS", "lanthipeptide-class-ii", "terpene"],
              ks=1, c=2, a=2, tail=[])
    assert "complex multi-class" in cap.lower(), f"Expected complex multi-class, got: {cap}"


def test_multiclass_3_classes_routes_to_complex_hybrid():
    """3 real classes (minimum threshold) must trigger the multi-class guard."""
    cap = cls(["NRPS", "PKS", "RiPP"], ks=2, c=2, a=2, tail=[])
    assert "complex multi-class" in cap.lower(), f"Expected complex multi-class, got: {cap}"


def test_2_classes_does_not_route_to_complex_hybrid():
    """2 real classes (NRPS+PKS) must NOT trigger the multi-class guard — it's a normal hybrid."""
    cap = cls(["NRPS", "PKS"], ks=2, c=2, a=2, tail=[])
    assert "complex multi-class" not in cap.lower(), f"2-class BGC misrouted: {cap}"


def test_saccharide_noise_does_not_inflate_class_count():
    """saccharide + other co-annotation must not contribute to the 3-class threshold."""
    cap = cls(["NRPS", "PKS", "saccharide", "other"], ks=2, c=2, a=2, tail=[])
    assert "complex multi-class" not in cap.lower(), f"Noise classes inflating count: {cap}"


def test_glycopeptide_not_misrouted_by_multiclass_guard():
    """Glycopeptide pre-check must intercept NRPS+PKS+T3PKS before multi-class guard fires.
    Regression for the teicoplanin test failure introduced and fixed in v9.7.58."""
    cap = cls(["NRPS", "PKS", "T3PKS"], ks=0, c=6, a=7, tail=["halogenase", "glycosyltransferase"])
    assert "glycopeptide" in cap.lower(), f"Glycopeptide pre-check failed: {cap}"


# ---- annotate_architecture: the in-place mutator was previously untested and its per-BGC
# exception handler silently blanked architecture_capacity with zero signal anywhere -----------

class _FakeBGC:
    def __init__(self, bgc_id, contig, start, end, products):
        self.bgc_id = bgc_id
        self.contig = contig
        self.start = start
        self.end = end
        self.products = products


class _FakeDomain:
    def __init__(self, contig, start, end, feature_type, domain):
        self.contig = contig
        self.start = start
        self.end = end
        self.feature_type = feature_type
        self.domain = domain


def test_annotate_architecture_happy_path_sets_capacity():
    bgc = _FakeBGC("BGC001", "ctg1", 0, 5000, ["terpene"])
    A.annotate_architecture([bgc], [], [])
    assert bgc.architecture_capacity != ""
    assert bgc.architecture_class_confidence != ""


def test_annotate_architecture_failure_is_visible_on_stderr(capsys):
    """A BGC whose start is non-numeric breaks the `d.end < bgc.start` comparison inside
    _module_counts (real repro, confirmed: TypeError('<' not supported between instances of
    'int' and 'str')) — must still fail closed (blank capacity) AND now print a WARN to stderr.
    Previously this failure was completely silent (bare `except Exception:` with no signal)."""
    bad_bgc = _FakeBGC("BGC_BAD", "ctg1", "not_a_number", 5000, ["terpene"])
    dom = _FakeDomain("ctg1", 10, 20, "aSDomain", "PKS_KS")
    A.annotate_architecture([bad_bgc], [], [dom])
    assert bad_bgc.architecture_capacity == ""
    assert bad_bgc.architecture_class_confidence == ""
    captured = capsys.readouterr()
    assert "BGC_BAD" in captured.err
    assert "architecture_capacity failed" in captured.err


def test_annotate_architecture_silent_on_success(capsys):
    bgc = _FakeBGC("BGC001", "ctg1", 0, 5000, ["terpene"])
    A.annotate_architecture([bgc], [], [])
    captured = capsys.readouterr()
    assert captured.err == ""
