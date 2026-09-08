"""Wire + behaviour test for tools/check_provenance_columns.py (v9.7.218 emergency patch).

Fixes the AS-421 status-manifest failure: a per-BGC TSV that dropped strain/contig/region,
leaving BGC### rows untraceable. The gate enforces the master_workbook provenance convention
(strain, assembly_locator, contig, region, BGC_ID lead every per-BGC table) on any emitted
per-BGC CSV/TSV.
"""
import csv
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GATE = REPO / "tools" / "check_provenance_columns.py"


def _run(path: Path):
    return subprocess.run([sys.executable, str(GATE), str(path)], capture_output=True, text=True)


def _write(tmp_path, name, header, rows, delim="\t"):
    p = tmp_path / name
    with p.open("w", newline="") as f:
        w = csv.writer(f, delimiter=delim)
        w.writerow(header)
        for r in rows:
            w.writerow(r)
    return p


def test_gate_exists():
    assert GATE.is_file(), "check_provenance_columns.py must exist"


def test_bad_per_bgc_table_fails(tmp_path):
    """A per-BGC table with a bare bgc column and no strain/contig/region must FAIL."""
    p = _write(tmp_path, "bad.tsv", ["bgc", "verify_modeb", "chars"],
               [["BGC001", "PASS", "38137"], ["BGC002", "PASS", "21515"]])
    r = _run(p)
    assert r.returncode == 1, r.stderr
    assert "missing a strain column" in r.stderr
    assert "missing contig/node" in r.stderr
    assert "missing region" in r.stderr


def test_good_per_bgc_table_passes(tmp_path):
    """The canonical strain/assembly_locator/contig/region/BGC_ID lead order must PASS."""
    p = _write(tmp_path, "good.tsv",
               ["strain", "assembly_locator", "contig", "region", "BGC_ID", "products"],
               [["AS-421", "NODE_13 region001 (BGC001)", "NODE_13", "region001", "BGC001", "RiPP"]])
    r = _run(p)
    assert r.returncode == 0, r.stderr


def test_assembly_locator_alone_satisfies_contig_region(tmp_path):
    """assembly_locator encodes node+region, so it satisfies both without separate columns."""
    p = _write(tmp_path, "loc.tsv", ["strain", "assembly_locator", "BGC_ID"],
               [["AS-421", "NODE_6 region002 (BGC041)", "BGC041"]])
    r = _run(p)
    assert r.returncode == 0, r.stderr


def test_non_bgc_table_is_ignored(tmp_path):
    """A table with no BGC id (header or cells) is out of scope and must PASS."""
    p = _write(tmp_path, "other.tsv", ["metric", "value"], [["coverage", "54.3"]])
    r = _run(p)
    assert r.returncode == 0, r.stderr


def test_bgc_id_in_cells_only_is_detected(tmp_path):
    """A table whose BGC ids live in cells under a generic header is still per-BGC and must FAIL."""
    p = _write(tmp_path, "cells.tsv", ["id", "score"], [["BGC003", "55"]])
    r = _run(p)
    assert r.returncode == 1, r.stderr


def test_registered_in_gate_registry():
    """Registry meta-rule: a new check_ tool must have a gate_registry row."""
    reg = (REPO / "tools" / "gate_registry.tsv").read_text()
    assert "check_provenance_columns" in reg, "gate must be registered in gate_registry.tsv"
