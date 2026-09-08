"""v9.7.239: `ingest-blastp --package` must write the nr overlay that arms NOVELTY_CONTRADICTION.

Background. `authored_verify._bgc_context_from_package` and `genome_explore._conservation_median`
both prefer `<package>/blastp_online/<BGC>_online_blastp.csv` over ClusterBlast when computing
`conservation_median_id`, which is the sole input to `modeb_structure_gate._novelty_conservation_findings`
(floor: 90.0% median per-gene identity). That preference was added because ClusterBlast's median for a
genus-conserved cluster can sit near 62% while nr says ~100% — using ClusterBlast alone lets a novelty
over-claim pass the lint.

The bug: through v9.7.238 NOTHING wrote that overlay. `blastp-online` writes to `--outdir` (default
cwd); `ingest-blastp` wrote only to the workbook's `B5_BLASTp_Hits` sheet, which no code reads back.
So for any operator running BLASTp themselves, the guard silently fell back to ClusterBlast.

These tests pin the write path end-to-end against the real readers, not a proxy.
"""
import csv
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

openpyxl = pytest.importorskip("openpyxl")

# ClusterBlast per-gene hits: distant, median 62% -> below the 90.0 novelty floor.
_CLUSTERBLAST_IDS = [58.0, 62.0, 66.0]
# nr hits: genus-conserved, median ~100% -> at/above the floor. One divergent gene, as in real data.
_NR_ROWS = [
    ("ctg66_5", 420, "100.000"),
    ("ctg66_6", 380, "99.800"),
    ("ctg66_7", 512, "100.000"),
    ("ctg66_8", 640, "52.500"),
]


def _make_package(tmp_path: pathlib.Path) -> pathlib.Path:
    pkg = tmp_path / "package"
    pkg.mkdir()
    manifest = {
        "bgcs": [{
            "bgc_id": "BGC043",
            "edge_status": "Full-contig",
            "single_protocluster_count": 2,
            "kcb_top": "NA02020",
            "novelty_auto": "MODERATE",
        }],
        "source_scans": {"clusterblast_genes": {"per_gene_best_hit": {
            "BGC043": [{"pct_identity": v, "reference_organism": "Streptomyces sp."}
                       for v in _CLUSTERBLAST_IDS]
        }}},
    }
    (pkg / "manifest.json").write_text(json.dumps(manifest))
    return pkg


def _make_master(tmp_path: pathlib.Path) -> pathlib.Path:
    wb = openpyxl.Workbook()
    wb.active.title = "A1_Placeholder"
    p = tmp_path / "Mamey_Master.xlsx"
    wb.save(p)
    return p


def _make_hit_table(tmp_path: pathlib.Path) -> pathlib.Path:
    """NCBI -outfmt 10 HitTable. Query titles use the canonical panel deflines that
    bgc_blastp_panel.fasta_header emits (pipe-delimited, carrying gene= and node=)."""
    p = tmp_path / "hits.csv"
    with p.open("w", newline="") as fh:
        w = csv.writer(fh)
        for locus, aa, pid in _NR_ROWS:
            qid = (f"AS-696|BGC043|slot=1|role=core|gene={locus}"
                   f"|node=NODE_67_length_41143_cov_68|region=region001"
                   f"|coords=1-100|aa={aa}|reason=halogenase")
            # query, subject, %id, alnlen, mismatch, gapopen, qs, qe, ss, se, evalue, bits, %pos
            w.writerow([qid, "WP_000000001.1", pid, aa, 0, 0, 1, aa, 1, aa, "0.0", 800, pid])
    return p


def _median_and_armed(pkg: pathlib.Path):
    from mamey.authored_verify import _bgc_context_from_package
    from mamey.modeb_structure_gate import _NOVELTY_ID_FLOOR
    ctx = _bgc_context_from_package(str(pkg), "BGC043") or {}
    med = ctx.get("conservation_median_id")
    armed = med is not None and float(med) >= _NOVELTY_ID_FLOOR
    return med, armed, ctx


def test_without_package_arg_the_guard_falls_back_to_clusterblast(tmp_path):
    """Regression pin for the pre-.239 behaviour: workbook-only ingest leaves the guard disarmed."""
    from mamey.blastp_ingest import ingest_blastp
    pkg = _make_package(tmp_path)
    res = ingest_blastp(_make_master(tmp_path), "AS-696", _make_hit_table(tmp_path))
    assert res["rows"] == len(_NR_ROWS)
    assert not (pkg / "blastp_online").exists(), "no overlay should be written without --package"
    med, armed, _ = _median_and_armed(pkg)
    assert med == 62.0, f"expected the ClusterBlast median, got {med}"
    assert armed is False, "ClusterBlast median 62% must NOT arm the novelty guard"


def test_package_arg_writes_the_overlay_the_readers_expect(tmp_path):
    from mamey.blastp_ingest import ingest_blastp, _OVERLAY_COLS
    pkg = _make_package(tmp_path)
    res = ingest_blastp(_make_master(tmp_path), "AS-696", _make_hit_table(tmp_path), package=str(pkg))

    overlay = pkg / "blastp_online" / "BGC043_online_blastp.csv"
    assert overlay.exists(), "ingest-blastp --package must write the nr overlay"
    # v9.7.252: the return grew `self_hits_excluded`. Assert the fields this test is about, not
    # exact dict equality — a contract that forbids adding a field forbids fixing a bug.
    ov = res["overlay"]
    assert ov["bgcs"] == 1 and ov["genes"] == 4 and ov["outdir"] == str(pkg / "blastp_online")
    assert ov["self_hits_excluded"] == 0, "no self-hits in this fixture"

    rows = list(csv.DictReader(overlay.open()))
    assert list(rows[0].keys()) == _OVERLAY_COLS, "overlay header must match blastp_online's writer"
    assert [r["locus_tag"] for r in rows] == [lt for lt, _, _ in _NR_ROWS], \
        "gene locus tag must be recovered from the panel defline's gene= field, not the raw query id"
    assert rows[0]["query_coverage"] == "100.0"


def test_overlay_arms_the_novelty_guard(tmp_path):
    """The point of the whole patch: after ingest, nr wins over ClusterBlast."""
    from mamey.blastp_ingest import ingest_blastp
    pkg = _make_package(tmp_path)
    ingest_blastp(_make_master(tmp_path), "AS-696", _make_hit_table(tmp_path), package=str(pkg))
    med, armed, ctx = _median_and_armed(pkg)
    assert med == 99.9, f"nr median expected 99.9, got {med} (ClusterBlast leaked through?)"
    assert armed is True, "nr median >= 90.0 must arm NOVELTY_CONTRADICTION"
    assert ctx["conservation_n_genes"] == 4


def test_genome_explore_reads_the_same_overlay(tmp_path):
    """The second reader must agree, or the two surfaces disagree about the same BGC."""
    from mamey.blastp_ingest import ingest_blastp
    from mamey import genome_explore
    pkg = _make_package(tmp_path)
    ingest_blastp(_make_master(tmp_path), "AS-696", _make_hit_table(tmp_path), package=str(pkg))
    man = json.loads((pkg / "manifest.json").read_text())
    med, n, _ms = genome_explore._conservation_median(pkg, man, "BGC043")
    assert med == 99.9 and n == 4


def test_only_rank_1_hits_land_and_unknown_bgcs_are_skipped(tmp_path):
    """Fail-closed: the overlay is best-hit-per-gene, and a query with no resolvable BGC
    is dropped rather than invented into a file."""
    from mamey.blastp_ingest import ingest_blastp
    pkg = _make_package(tmp_path)
    ht = tmp_path / "hits2.csv"
    with ht.open("w", newline="") as fh:
        w = csv.writer(fh)
        good = "AS-696|BGC043|slot=1|role=core|gene=ctg66_5|node=NODE_67|region=region001|aa=420"
        w.writerow([good, "WP_1.1", "100.000", 420, 0, 0, 1, 420, 1, 420, "0.0", 800, "100.000"])
        w.writerow([good, "WP_2.1", "40.000", 420, 0, 0, 1, 420, 1, 420, "1e-5", 100, "40.000"])
        w.writerow(["orphan_query_no_bgc", "WP_3.1", "99.0", 100, 0, 0, 1, 100, 1, 100, "0.0", 200, "99.0"])
    ingest_blastp(_make_master(tmp_path), "AS-696", ht, package=str(pkg))
    rows = list(csv.DictReader((pkg / "blastp_online" / "BGC043_online_blastp.csv").open()))
    assert len(rows) == 1 and rows[0]["pct_identity"] == "100.000", "only hit_rank 1 is mirrored"
    assert not list((pkg / "blastp_online").glob("*orphan*")), "unresolvable BGC must not create a file"
