"""Tests for the read-only inspector subcommands (P-G): list-bgcs, inspect, explain.

These run against a synthetic minimal package built in a tmp dir so they do not depend
on any uploaded fixture. They cover the JSON-shape contract that downstream scripts rely
on (P-B added novelty_auto + cctt_triggers) and the exit codes for the error paths.
"""

import argparse
import contextlib
import io
import json
from pathlib import Path

import pytest

from mamey.package_inspector import list_bgcs_command, inspect_command, inspect_command


TRIAGE_HEADER = (
    "BGC_ID,Contig,Node_ID,antiSMASH_Region,Products,Boundary,AB_auto,AF_auto,Novelty_auto,"
    "CCTT_triggers,Lead_tier_auto,KCB_top,Depth_floor,Standing_rule,Primary_metab_flag\n"
)
TRIAGE_ROWS = (
    "BGC001,NODE_1_length_50000,NODE_1_length_50000,region001,NRPS;thioamide-NRP,Interior,70.0,28.0,45.0,"
    "T43-THA_thioamide,High,enteromycin,,,\n"
    "BGC002,NODE_2_length_40000,NODE_2_length_40000,region001,saccharide,Edge,63.0,30.0,50.0,"
    ",Inventory,natronosporangium,,saccharide-exclusion,\n"
    "BGC003,NODE_3_length_30000,NODE_3_length_30000,region001,RiPP;triceptide,Interior,55.0,38.0,56.0,"
    "T43-LAN_lanthipeptide,Medium,micromonospora,,,\n"
)


def _make_pkg(tmp_path: Path, strain="TEST-STRAIN") -> Path:
    pkg = tmp_path / strain
    pkg.mkdir()
    (pkg / f"{strain}_4_triage_board.csv").write_text("Strain," + TRIAGE_HEADER + "".join(strain + "," + line + "\n" for line in TRIAGE_ROWS.splitlines()))
    return pkg


def _run_json(pkg: Path, axis="rank", top_n=None, include_dropped=False):
    ns = argparse.Namespace(
        package_dir=str(pkg), axis=axis, top_n=top_n, json=True,
        include_dropped=include_dropped,
    )
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = list_bgcs_command(ns)
    return rc, json.loads(buf.getvalue())


def test_list_bgcs_json_includes_pb_fields(tmp_path):
    """P-B: --json must emit novelty_auto and cctt_triggers."""
    pkg = _make_pkg(tmp_path)
    rc, out = _run_json(pkg)
    assert rc == 0
    assert out, "expected at least one BGC row"
    for row in out:
        assert "novelty_auto" in row
        assert "cctt_triggers" in row
    first = next(r for r in out if r["bgc_id"] == "BGC001")
    assert first["novelty_auto"] == 45.0
    assert first["cctt_triggers"] == "T43-THA_thioamide"


def test_list_bgcs_excludes_dropped_by_default(tmp_path):
    """Standing-rule / primary-metab rows are filtered unless --include-dropped."""
    pkg = _make_pkg(tmp_path)
    _, out = _run_json(pkg)
    ids = {r["bgc_id"] for r in out}
    assert "BGC002" not in ids  # saccharide-exclusion standing rule
    _, out_all = _run_json(pkg, include_dropped=True)
    ids_all = {r["bgc_id"] for r in out_all}
    assert "BGC002" in ids_all


def test_list_bgcs_axis_sort_ab(tmp_path):
    pkg = _make_pkg(tmp_path)
    _, out = _run_json(pkg, axis="ab")
    scores = [r["ab_score"] for r in out]
    assert scores == sorted(scores, reverse=True)


def test_list_bgcs_top_n(tmp_path):
    pkg = _make_pkg(tmp_path)
    _, out = _run_json(pkg, axis="ab", top_n=1)
    assert len(out) == 1


def test_list_bgcs_missing_board_exits_1(tmp_path):
    empty = tmp_path / "empty_pkg"
    empty.mkdir()
    ns = argparse.Namespace(package_dir=str(empty), axis="rank", top_n=None,
                            json=True, include_dropped=False)
    with contextlib.redirect_stderr(io.StringIO()):
        rc = list_bgcs_command(ns)
    assert rc == 1


def test_list_bgcs_bad_path_exits_1(tmp_path):
    ns = argparse.Namespace(package_dir=str(tmp_path / "nope"), axis="rank",
                            top_n=None, json=True, include_dropped=False)
    with contextlib.redirect_stderr(io.StringIO()):
        rc = list_bgcs_command(ns)
    assert rc == 1


def test_inspect_command_suggests_gold_direct_not_smoke(tmp_path):
    """v9.7.163: inspect must suggest the gold-direct capped-session command — smoke removed v9.7.161."""
    import zipfile

    zp = tmp_path / "TEST-STRAIN.zip"
    with zipfile.ZipFile(zp, "w") as zf:
        for i in range(1, 42):
            zf.writestr(f"region{i:03d}.gbk", "LOCUS       TEST\nCOMMENT     antiSMASH 8.0.0\n")
        zf.writestr("knownclusterblast/region001.txt", "placeholder\n")

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = inspect_command(argparse.Namespace(zip=str(zp)))
    out = buf.getvalue()
    assert rc == 0
    assert "--mode gold" in out
    assert "--capped-session" in out
    assert "--release" in out
    # the removed surface must not reappear
    assert "--mode smoke" not in out
    assert "--chatgpt-safe" not in out
    assert "--chatgpt-followup" not in out
