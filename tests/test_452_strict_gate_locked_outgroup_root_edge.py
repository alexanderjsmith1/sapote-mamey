"""Card attine_452_strict_gate_locked_outgroup_root_edge.

A genus 16S tree rooted on a distant outgroup that the outgroup registry LOCKS has a long root edge; after the outgroup
is split from the root, the ingroup half of that edge is an internal branch that dominates a shallow ingroup, and the
strict gate refused every such tree. With the locked accession, that one branch is exempt (long_root=true, the full
edge length stated); every other DOMINATING_BRANCH and every LONG_TERMINAL still fails. A non-LOCKED registry row gives
no exemption. The renderer draws the edge shortened with a break mark and its true length. Synthetic trees only.
"""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE / "tools"))


def _load(name):
    spec = importlib.util.spec_from_file_location(f"{name}_452lr", HERE / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


tsc = _load("tree_sanity_check")
OG = "NR_000001_1_Synoutgroupia_alpha_SYN_1_OUTGROUP"


def _registry(tmp_path, status="LOCKED"):
    p = tmp_path / "registry.tsv"
    p.write_text("# synthetic registry\n"
                 f"genus\tSyngenus\tSynaceae\tSynoutgroupia\tSynoutgroupia alpha SYN 1 (NR_000001.1)\t16S_local\t{status}\tsynthetic\n")
    return p


def _tree(tmp_path, name, newick):
    p = tmp_path / name; p.write_text(newick + "\n"); return p


SHALLOW = f"((SYN_970:0.010,SYN_971:0.012,(SYN_972:0.010,SYN_973:0.011):0.005):0.700,{OG}:0.0);"


def test_locked_outgroup_root_edge_passes_and_is_reported(tmp_path):
    t = _tree(tmp_path, "shallow.nwk", SHALLOW)
    acc = tsc.registry_locked_accession(_registry(tmp_path), "Syngenus")
    assert acc == "NR_000001.1"
    ok, report = tsc.check(t)                                   # without the registry: the root edge dominates
    assert not ok and "DOMINATING_BRANCH" in report
    ok, report = tsc.check(t, locked_root_accession=acc)
    assert ok, report
    assert "long_root=true" in report and "root edge 0.7000" in report


def test_a_non_locked_outgroup_gets_no_exemption(tmp_path):
    t = _tree(tmp_path, "shallow.nwk", SHALLOW)
    assert tsc.registry_locked_accession(_registry(tmp_path, "PROVISIONAL"), "Syngenus") is None
    ok, report = tsc.check(t, locked_root_accession=None)
    assert not ok and "DOMINATING_BRANCH" in report
    ok, report = tsc.check(t, locked_root_accession="NR_999999.1")   # an outgroup that is not the locked one
    assert not ok and "not applied" in report and "DOMINATING_BRANCH" in report


def test_a_long_terminal_or_another_dominating_branch_still_fails(tmp_path):
    acc = "NR_000001.1"
    tips = ",".join(f"SYN_9{80 + i}:0.0{10 + i % 5}" for i in range(11))       # 12 tips: p90 stays a short branch
    long_tip = _tree(tmp_path, "long.nwk", f"(({tips},SYN_971:0.300):0.700,{OG}:0.0);")
    ok, report = tsc.check(long_tip, locked_root_accession=acc)
    assert not ok and "LONG_TERMINAL" in report and "SYN_971" in report
    inner = _tree(tmp_path, "inner.nwk", f"((SYN_970:0.010,SYN_971:0.012,(SYN_972:0.010,SYN_973:0.011):0.900):0.100,{OG}:0.0);")
    ok, report = tsc.check(inner, locked_root_accession=acc)
    assert not ok and "DOMINATING_BRANCH" in report             # an ingroup internal branch is not the root edge


def test_cli_reads_the_registry(tmp_path, capsys):
    t = _tree(tmp_path, "shallow.nwk", SHALLOW)
    reg = _registry(tmp_path)
    assert tsc.main([str(t), "--locked-outgroup-group", "Syngenus", "--outgroup-registry", str(reg)]) == 0
    with pytest.raises(SystemExit):
        tsc.main([str(t), "--locked-outgroup-group", "Syngenus", "--outgroup-registry", str(_registry(tmp_path, "CONFIRM"))])


def test_root_variants_record_the_lock_and_the_display_gate_reads_it_from_the_receipt(tmp_path):
    prv = _load("placement_root_variants"); gsa = _load("gate_stem_aware")
    src = _tree(tmp_path, "pruned.nwk", SHALLOW)
    split, receipt, record = prv.prepare(src, tmp_path / "syn", [OG], locked_accession="NR_000001.1")
    assert record["locked_outgroup_accession"] == "NR_000001.1"
    assert record["variants"]["display_rooted_split"]["gate_pass"] is True
    sha = hashlib.sha256(receipt.read_bytes()).hexdigest()
    assert gsa.locked_root_from_receipt(receipt, sha, split) == "NR_000001.1"
    with pytest.raises(ValueError, match="HASH_MISMATCH"):
        gsa.locked_root_from_receipt(receipt, "0" * 64, split)
    with pytest.raises(ValueError, match="TREE_MISMATCH"):
        gsa.locked_root_from_receipt(receipt, sha, src)
    split2, receipt2, record2 = prv.prepare(src, tmp_path / "syn_nolock", [OG])
    assert record2["locked_outgroup_accession"] is None
    assert record2["variants"]["display_rooted_split"]["gate_pass"] is False


def test_renderer_draws_the_break_and_the_true_length():
    r = (HERE / "tools" / "ggtree_rect_heatmap.R").read_text()
    assert 'Sys.getenv("GG_LOCKED_ROOT_EDGE")' in r and 'label = "//"' in r and "LOCKED_ROOT_EDGE_SHAPE" in r
    assert '"--locked-root-receipt"' in r
    d = (HERE / "tools" / "placement_display.py").read_text()
    assert "--outgroup-registry" in d and "is drawn shortened, with a break mark" in d
