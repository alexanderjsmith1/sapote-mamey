"""build_placement_ggtree_inputs --query-tips: query roles come from an exact tip list, so query tips
need not be renamed to an AS/SID prefix. Listed names must be tips of the graft tree."""
import csv
import os
import subprocess
import sys
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tools" / "build_placement_ggtree_inputs.py"
TREE = "(((ISOLATE_7:0.05,Genus_alpha_RefA:0.1):0.1,Genus_alpha_RefB:0.2):0.3,outgroup_X:0.4);\n"


def _run(tmp_path, *extra):
    tree = tmp_path / "input.nwk"
    tree.write_text(TREE)
    hosts = tmp_path / "hosts.tsv"
    hosts.write_text("strain\thost_raw\n")
    return subprocess.run([sys.executable, str(TOOL), "--graft", str(tree), "--host-table", str(hosts),
                           "--out-prefix", str(tmp_path / "result"), "--keep-all-refs", *extra],
                          cwd=tmp_path, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
                          capture_output=True, text=True, timeout=60)


def _kinds(tmp_path):
    with open(tmp_path / "result_ggtree_annotation.tsv") as fh:
        return {r["tip"]: r["kind"] for r in csv.DictReader(fh, delimiter="\t")}


def test_listed_tip_is_a_query_without_renaming(tmp_path):
    qt = tmp_path / "queries.txt"
    qt.write_text("ISOLATE_7\n")
    r = _run(tmp_path, "--query-tips", str(qt))
    assert r.returncode == 0, r.stderr
    assert _kinds(tmp_path)["ISOLATE_7"] == "query"


def test_without_the_list_the_prefix_rule_still_applies(tmp_path):
    r = _run(tmp_path)
    assert r.returncode == 0, r.stderr
    assert _kinds(tmp_path)["ISOLATE_7"] != "query"


def test_unknown_or_repeated_query_tip_is_refused(tmp_path):
    qt = tmp_path / "queries.txt"
    qt.write_text("ISOLATE_9\n")
    r = _run(tmp_path, "--query-tips", str(qt))
    assert r.returncode == 2 and "QUERY_TIPS_NOT_IN_TREE" in r.stderr
    qt.write_text("ISOLATE_7\nISOLATE_7\n")
    r = _run(tmp_path, "--query-tips", str(qt))
    assert r.returncode == 2 and "QUERY_TIPS_DUPLICATE" in r.stderr
