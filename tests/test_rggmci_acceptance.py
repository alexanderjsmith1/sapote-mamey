"""Acceptance-discriminator matrix for RG-GMCI (v9.7.22-m).

Covers the two failure modes the v9.2 review flagged: (1) a nominal 1-bp overlap scoring as full
OVERLAPPING geometry, and (2) convergence count (many shared references) inflating a geometry-less
pair to HIGH/MODERATE. Both are now gated at acceptance.
"""
import mamey.rggmci as rg

def _ref(start, end, contig="c", rank=1, nprot=5, ident=70.0):
    return rg.ClusterBlastReference(bgc_id="b", contig=contig, region_number=1, region_key=None, ref="R",
        source="s", reference_type="t1pks", rank=rank, nprot=nprot, cumulative_score=100.0,
        mean_identity=ident, interval_start=start, interval_end=end, source_file="f")

# --- overlap-fraction in _adjacency ---
def test_tiny_overlap_is_adjacent_not_overlapping():
    cls, gap, ov, ofrac, basis, span = rg._adjacency(_ref(0, 10000), _ref(9999, 20000))
    assert cls == "ADJACENT_OR_NEARBY_REFERENCE_SEGMENTS"
    assert ofrac < rg.OVERLAP_FRACTION_MIN and basis == "COORDINATE"

def test_real_overlap_stays_overlapping():
    cls, gap, ov, ofrac, basis, span = rg._adjacency(_ref(0, 10000), _ref(2000, 12000))
    assert cls == "OVERLAPPING_REFERENCE_SEGMENTS" and ofrac >= rg.OVERLAP_FRACTION_MIN

def test_distant_segments_classified_distant():
    cls, gap, ov, ofrac, basis, span = rg._adjacency(_ref(0, 5000), _ref(40000, 45000))
    assert cls in ("DISTANT_ON_REFERENCE_CAUTION", "SAME_REFERENCE_ONLY_DISTANT") and ov == 0

def test_no_interval_no_subjects_returns_no_interval():
    # no coordinates AND no subject loci -> stays NO_INTERVAL, basis NONE (six-tuple now)
    cls, gap, ov, ofrac, basis, span = rg._adjacency(_ref(None, None), _ref(0, 100))
    assert cls == "SHARED_REFERENCE_NO_INTERVAL" and ofrac is None and basis == "NONE"

# --- geometry acceptance gate ---
def test_gate_demotes_high_without_geometry_or_split_to_low():
    # HIGH driven by convergence count but zero geometry and no cross-scaffold split -> shared-ref-only
    c, g = rg._geometry_gate("HIGH_RG_GMCI_RESCUE", good_geometry_references=0, split_signature=False)
    assert c == "LOW_SHARED_REFERENCE_SIGNAL" and g.startswith("DEMOTED")

def test_gate_high_without_geometry_but_split_caps_at_moderate():
    # no reference geometry, but a genuine cross-scaffold physical split keeps it as a MODERATE candidate
    c, g = rg._geometry_gate("HIGH_RG_GMCI_RESCUE", good_geometry_references=0, split_signature=True)
    assert c == "MODERATE_RG_GMCI_CANDIDATE" and g.startswith("DEMOTED")

def test_gate_demotes_moderate_without_geometry_or_split():
    c, g = rg._geometry_gate("MODERATE_RG_GMCI_CANDIDATE", 0, False)
    assert c == "LOW_SHARED_REFERENCE_SIGNAL" and g.startswith("DEMOTED")

def test_gate_keeps_high_with_geometry():
    c, g = rg._geometry_gate("HIGH_RG_GMCI_RESCUE", good_geometry_references=2, split_signature=False)
    assert c == "HIGH_RG_GMCI_RESCUE" and g == "OK"

def test_gate_spares_moderate_when_split_signal_present():
    # a real cross-scaffold physical split keeps MODERATE even with no reference geometry
    c, g = rg._geometry_gate("MODERATE_RG_GMCI_CANDIDATE", 0, split_signature=True)
    assert c == "MODERATE_RG_GMCI_CANDIDATE" and g == "OK"

def test_low_is_untouched():
    c, g = rg._geometry_gate("LOW_SHARED_REFERENCE_SIGNAL", 0, False)
    assert c == "LOW_SHARED_REFERENCE_SIGNAL" and g == "OK"
