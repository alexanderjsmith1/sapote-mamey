"""B3 — betalactone over-call suppression tests.

Fast-partition unit tests (no network). Verifies that a betalactone architecture
call combined with a terpene KCB anchor (e.g. geosmin) is flagged as a suspected
over-call, while genuine betalactone (non-terpene KCB) and non-betalactone calls
are left untouched.
"""
from mamey.architecture_first import (
    ArchitectureReport, ConcordanceResult, PathwayType, Concordance,
    make_assignment, _is_terpene_kcb,
)


def _arch(ptype):
    return ArchitectureReport(pathway_type=ptype, confidence="MEDIUM")


def _conc(compound, cls="", conc=Concordance.WEAK_SIGNAL):
    return ConcordanceResult(concordance=conc, kcb_compound=compound, kcb_class=cls)


def test_terpene_kcb_detector():
    assert _is_terpene_kcb("geosmin")
    assert _is_terpene_kcb("2-methylisoborneol")
    assert _is_terpene_kcb("hopene")
    assert _is_terpene_kcb("something", "Terpene")
    assert not _is_terpene_kcb("microansamycin")
    assert not _is_terpene_kcb("")


def test_betalactone_with_geosmin_flagged():
    a = make_assignment(_arch(PathwayType.BETALACTONE), _conc("geosmin"))
    assert a.betalactone_overcall_suspected is True
    assert "OVER-CALL SUSPECTED" in a.kcb_note


def test_betalactone_with_terpene_mibig_class_flagged():
    a = make_assignment(_arch(PathwayType.BETALACTONE), _conc("unknown_cmpd", cls="Terpene"))
    assert a.betalactone_overcall_suspected is True


def test_betalactone_with_nonterpene_kcb_not_flagged():
    # a real betalactone-ish anchor should NOT be flagged
    a = make_assignment(_arch(PathwayType.BETALACTONE), _conc("lactonamycin"))
    assert a.betalactone_overcall_suspected is False


def test_nonbetalactone_with_geosmin_not_flagged():
    # geosmin KCB on a genuine terpene architecture is fine — no betalactone to suppress
    a = make_assignment(_arch(PathwayType.TERPENE_CYCLIZED), _conc("geosmin"))
    assert a.betalactone_overcall_suspected is False
