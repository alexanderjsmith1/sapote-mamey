"""antiSMASH writes a GenBank partial marker on Orig. start / Orig. end; the bounds must survive it.

The defect (found 2026-09-21 on engine 1.9.167): `_region_orig_bounds_from_zip` matched
`Orig\\.\\s*end\\s*::\\s*(\\d+)`, which will not match across the `>` in `Orig. end :: >247156`.
The pair was then dropped, `parse_bgcs_from_zip` fell back to the clipped region GBK's LOCAL
coordinates — which restart at 1 — and `_edge_status` returned Edge for a region sitting 180 kb
clear of both ends of a 428 kb contig. `interior_pct` is computed from `edge_status`, and
`interior_pct` is the caliper variable for fragmentation-matched comparison, so the bias landed
straight on the number the comparison depends on.

Observed live in 3 of 969 region GBKs across 18 reference packages; 2 changed classification. The
third was on a circular record, where `_edge_status` returns Interior before it reads the start
coordinate — that case is covered here too, so a later change to the circular branch cannot quietly
re-open the hole.
"""
import zipfile

from mamey.parsers import _edge_status, _region_orig_bounds_from_zip

HEADER = """LOCUS       {locus}        {span} bp    DNA     {topo} CON 30-NOV-2025
DEFINITION  synthetic region record for the partial-marker regression.
ACCESSION   {locus}
COMMENT     ##antiSMASH-Data-START##
            Version                           :: 8.0.0
            Orig. start                       :: {start}
            Orig. end                         :: {end}
            ##antiSMASH-Data-END##
FEATURES             Location/Qualifiers
     source          1..{span}
ORIGIN
//
"""


def _zip_with(tmp_path, name, start, end, span, topo="linear"):
    z = tmp_path / "regions.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr(name, HEADER.format(locus="NZ_TEST01000006", span=span,
                                        start=start, end=end, topo=topo))
    return str(z)


def test_plain_numeric_bounds_are_read(tmp_path):
    z = _zip_with(tmp_path, "NZ_TEST01000006.1.region003.gbk", "180524", "247156", 66632)
    assert _region_orig_bounds_from_zip(z) == {
        "NZ_TEST01000006.1.region003.gbk": (180524, 247156)}


def test_greater_than_marker_on_orig_end_does_not_drop_the_pair(tmp_path):
    """The real shape: `Orig. end :: >247156`. The coordinate after the marker is the real one."""
    z = _zip_with(tmp_path, "NZ_TEST01000006.1.region003.gbk", "180524", ">247156", 66632)
    assert _region_orig_bounds_from_zip(z) == {
        "NZ_TEST01000006.1.region003.gbk": (180524, 247156)}


def test_less_than_marker_on_orig_start_does_not_drop_the_pair(tmp_path):
    z = _zip_with(tmp_path, "NZ_TEST01000006.1.region001.gbk", "<1", "44210", 44210)
    assert _region_orig_bounds_from_zip(z) == {
        "NZ_TEST01000006.1.region001.gbk": (1, 44210)}


def test_absolute_bounds_keep_an_interior_region_interior(tmp_path):
    """The consequence the regex controls: with the bounds recovered, a region 180 kb from either
    end of a 428 kb contig is Interior. Without them the caller uses local coordinates starting at
    1 and `_edge_status` calls it Edge."""
    z = _zip_with(tmp_path, "NZ_TEST01000006.1.region003.gbk", "180524", ">247156", 66632)
    start, end = _region_orig_bounds_from_zip(z)["NZ_TEST01000006.1.region003.gbk"]
    assert _edge_status(start, end, 428276, is_circular=False) == "Interior"
    # the fallback path, spelled out so the cost of losing the bounds stays visible
    assert _edge_status(1, 66632, 428276, is_circular=False) == "Edge"


def test_circular_record_was_never_affected_and_still_is_not(tmp_path):
    """A closed replicon returns Interior before the start coordinate is read (the v9.7.87 origin
    fix), which is why the one circular case in the live corpus showed no error."""
    z = _zip_with(tmp_path, "NZ_TEST01000006.1.region003.gbk", "946949", ">1049634", 102685,
                  topo="circular")
    start, end = _region_orig_bounds_from_zip(z)["NZ_TEST01000006.1.region003.gbk"]
    assert (start, end) == (946949, 1049634)
    assert _edge_status(1, 102685, 5000000, is_circular=True) == "Interior"


def test_a_header_with_no_orig_lines_still_yields_nothing(tmp_path):
    """The warning path must stay reachable: a region GBK that genuinely lacks the lines is not
    given invented bounds."""
    z = tmp_path / "regions.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("NZ_TEST01000006.1.region003.gbk",
                    "LOCUS       NZ_TEST01000006        66632 bp    DNA     linear   CON\n//\n")
    assert _region_orig_bounds_from_zip(str(z)) == {}
