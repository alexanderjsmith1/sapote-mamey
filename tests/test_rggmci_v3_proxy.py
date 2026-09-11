"""v9.7.39 — locus-number proxy (P-4') + identity-column parse (P-1') regression."""
import mamey.rggmci as rg


def _ref(subjects=(), start=None, end=None, ident=None):
    return rg.ClusterBlastReference(bgc_id="b", contig="c", region_number=1, region_key=None, ref="R",
        source="s", reference_type="t1pks", rank=1, nprot=5, cumulative_score=100.0,
        mean_identity=ident, interval_start=start, interval_end=end, source_file="f", subjects=tuple(subjects))


def test_proxy_adjacent_when_no_coordinates():
    cls, gap, ov, ofrac, basis, span = rg._adjacency(
        _ref(("X_RS30040", "X_RS30045")), _ref(("X_RS30050", "X_RS30055")))
    assert cls == "ADJACENT_OR_NEARBY_REFERENCE_SEGMENTS"
    assert basis == "LOCUS_PROXY" and gap == 5 and span == 15


def test_proxy_distant_when_no_coordinates():
    cls, gap, ov, ofrac, basis, span = rg._adjacency(
        _ref(("X_RS30040",)), _ref(("X_RS99000",)))
    assert cls == "DISTANT_ON_REFERENCE_CAUTION" and basis == "LOCUS_PROXY"


def test_no_subjects_stays_no_interval():
    cls, *_ , basis, span = rg._adjacency(_ref(()), _ref(()))
    assert cls == "SHARED_REFERENCE_NO_INTERVAL" and basis == "NONE"


def test_coordinates_take_priority_over_proxy():
    # when real intervals exist, basis must be COORDINATE even if subjects are present
    *_, basis, span = rg._adjacency(_ref(("X_RS1",), 0, 10000), _ref(("X_RS2",), 2000, 12000))
    assert basis == "COORDINATE"


def test_blast_hits_parses_subjects_and_bare_identity():
    block = ("Table of Blast hits (query gene, subject gene, %identity, blast score, %coverage, e-value):\n"
             "ctg1_2\tAMK_RS30055\t63\t398\t84.4\t6e-134\n"
             "ctg1_3\tAMK_RS30050\t67\t476\t87.0\t9e-166\n")
    hits = rg._blast_hits(block)
    assert [s for s, _ in hits] == ["AMK_RS30055", "AMK_RS30050"]
    assert rg._extract_mean_identity(block) == 65.0  # mean(63,67); NO '%' sign present


def test_identity_format_without_percent_sign():
    # the old scan required a '%'; the format has none -> must still parse from col 3
    block = "Table of Blast hits (...):\nctg9_1\tREF_001\t71\t500\t90.0\t1e-99\n"
    assert rg._extract_mean_identity(block) == 71.0


def test_proxy_ignores_cross_namespace_loci():
    # b mixes two locus-tag namespaces; only the SHARED prefix (X_RS) must be compared
    a = _ref(("X_RS30040", "X_RS30045"))
    b = _ref(("X_RS30050", "X_RS30055", "Q_RS0106330", "Q_RS0106550"))  # Q_RS* must be ignored
    cls, gap, ov, ofrac, basis, span = rg._adjacency(a, b)
    assert cls == "ADJACENT_OR_NEARBY_REFERENCE_SEGMENTS"  # NOT distant (span would be ~76k if cross-namespace)
    assert gap == 5 and span == 15 and basis == "LOCUS_PROXY"


def test_extract_interval_ignores_coverage_decimal():
    # v9.7.40 Fix-1: a Blast-hits %coverage like 101.5625 must NOT be read as coords (101, 5625)
    block = ("Table of Blast hits (query gene, subject gene, %identity, blast score, %coverage, e-value):\n"
             "ctg13_74\tHUT19_RS24925\t47\t162\t101.5625\t5.8e-47\n")
    assert rg._extract_interval(block) == (None, None)


def test_extract_interval_keeps_real_hyphen_range():
    assert rg._extract_interval("Subject location 1234-5678\n") == (1234, 5678)


def test_extract_interval_keeps_genbank_double_dot():
    assert rg._extract_interval("spans 100200..100800 here\n") == (100200, 100800)
