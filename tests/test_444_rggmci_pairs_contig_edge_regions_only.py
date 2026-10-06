"""RG-GMCI rescues pair only regions antiSMASH places on a contig edge; interior pairs are a separate list.

2026-09-27: "we don't want to waste our time on any BGCs that antismash deems internal and not on a contig
edge, ever" and "if the assembly puts a bgc internal, then we are not going to be able to confidently over-ride
that". Interior pairs may still be worth a look as related loci, "but not as a strong, sane contig rescue".
The edge test is antiSMASH's own `/contig_edge` flag on the region feature; the engine's edge status is the fallback
for a region file without it.
"""
import zipfile

from mamey.models import BGCRecord
from mamey.rggmci import (RELATED_LOCUS_LABEL, _contig_edge_bgcs, compute_rggmci, related_locus_pairs,
                          run_rggmci)


def _bgc(bid, contig, products, edge, start, end, clen, gbk=""):
    return BGCRecord(bgc_id=bid, contig=contig, region_number=1, start=start, end=end,
                     contig_length=clen, products=list(products), edge_status=edge, source_gbk=gbk)


def _ref(bgc_id, contig, ref, subjects):
    return {"bgc_id": bgc_id, "contig": contig, "region_number": 1, "region_key": contig + "_c1", "ref": ref,
            "source": ref, "reference_type": "nrps", "rank": 1, "nprot": len(subjects), "cumulative_score": 1000.0,
            "mean_identity": 60.0, "interval_start": None, "interval_end": None,
            "source_file": f"knownclusterblast/{contig}_c1.txt", "subjects": tuple(subjects),
            "db_kind": "knownclusterblast"}


# three regions that tile the same references with complementary genes; C is interior
BGCS = [
    _bgc("A", "ctgA", ["NRPS"], "Edge", 90001, 100000, 100000),
    _bgc("B", "ctgB", ["NRPS"], "Full-contig", 1, 9000, 9000),
    _bgc("C", "ctgC", ["NRPS"], "Interior", 40001, 60000, 100000),
]
REFMAP = {"reference_records": [
    _ref(b, f"ctg{b}", ref, genes)
    for ref in ("BGC0000001", "BGC0000002", "BGC0000003")
    for b, genes in (("A", ["g1", "g2", "g3"]), ("B", ["g4", "g5", "g6"]), ("C", ["g7", "g8", "g9"]))
]}


def _pairs(result):
    return {p["pair"] for p in result["ranked_pairs"]}


def test_interior_regions_are_never_paired_as_rescues():
    out = compute_rggmci(BGCS, REFMAP)
    assert _pairs(out) == {"A+B"}
    assert out["contig_edge_regions"] == 2 and out["interior_regions_not_paired"] == 1


def test_interior_pairs_are_listed_apart_and_labelled():
    rel = related_locus_pairs(BGCS, REFMAP, {"A", "B"})
    assert {p["pair"] for p in rel} == {"A+C", "B+C"}
    for p in rel:
        assert p["rggmci_confidence"] == RELATED_LOCUS_LABEL
        assert p["shared_reference_grade"].startswith(("HIGH", "MODERATE"))
        assert "C" in (p["bgc_a"], p["bgc_b"])


def _zip(tmp_path, flags):
    z = tmp_path / "t.zip"
    with zipfile.ZipFile(z, "w") as zf:
        for name, flag in flags.items():
            qual = f'                     /contig_edge="{flag}"\n' if flag else ""
            zf.writestr(name, "LOCUS       X 100 bp DNA\nFEATURES             Location/Qualifiers\n"
                              f"     region          1..100\n{qual}ORIGIN\n//\n")
    return z


def test_antismash_flag_decides_and_the_engine_status_is_only_a_fallback(tmp_path):
    bgcs = [
        _bgc("A", "ctgA", ["NRPS"], "Edge", 1, 100, 100, gbk="a.gbk"),          # engine: edge; antiSMASH: not
        _bgc("B", "ctgB", ["NRPS"], "Interior", 1, 100, 100, gbk="b.gbk"),      # engine: interior; antiSMASH: edge
        _bgc("C", "ctgC", ["NRPS"], "Full-contig", 1, 100, 100, gbk="c.gbk"),   # no flag: engine status used
        _bgc("D", "ctgD", ["NRPS"], "Interior", 1, 100, 100, gbk="d.gbk"),      # no flag, interior
    ]
    z = _zip(tmp_path, {"a.gbk": "False", "b.gbk": "True", "c.gbk": "", "d.gbk": ""})
    assert _contig_edge_bgcs(z, bgcs) == {"B", "C"}


def test_run_rggmci_reports_both_lists(tmp_path):
    z = _zip(tmp_path, {})
    out = run_rggmci(z, BGCS)
    assert "related_locus_pairs" in out
    assert all(p["rggmci_confidence"] != RELATED_LOCUS_LABEL for p in out["ranked_pairs"])


def test_engine_package_lists_related_loci_in_their_own_table(tmp_path):
    """The engine writes interior-region pairs to _4A_RGGMCI_related_loci.csv, never to the ranked pairs."""
    import csv
    import os
    import pathlib
    import subprocess
    import sys
    root = pathlib.Path(__file__).resolve().parents[1]
    fixture = root / "tests" / "fixtures" / "rggmci_public_VWPH00000000.1_subset.zip"
    env = dict(os.environ, PYTHONPATH=str(root), PYTHONHASHSEED="0")
    subprocess.run([sys.executable, "-m", "mamey", "run", "--strain", "EDGE_T", "--input-zip", str(fixture),
                    "--taxonomy", "Saccharopolyspora sp.", "--source", "public test fixture", "--outdir", str(tmp_path),
                    "--mode", "standard", "--release", "PUBLIC", "--brief", "none", "--json-evidence", "off"],
                   check=True, capture_output=True, timeout=600, env=env, text=True)
    pkg = next(tmp_path.rglob("EDGE_T_4A_RGGMCI_related_loci.csv")).parent
    related = list(csv.DictReader(open(pkg / "EDGE_T_4A_RGGMCI_related_loci.csv", encoding="utf-8")))
    ranked = list(csv.DictReader(open(pkg / "EDGE_T_4A_RGGMCI_ranked_pairs.csv", encoding="utf-8")))
    assert all(r["rggmci_confidence"] == RELATED_LOCUS_LABEL for r in related)
    assert all(r["rggmci_confidence"] != RELATED_LOCUS_LABEL for r in ranked)
    assert related, "the fixture has interior-region pairs; the table must not be empty"
    assert not {r["pair"] for r in related} & {r["pair"] for r in ranked}
