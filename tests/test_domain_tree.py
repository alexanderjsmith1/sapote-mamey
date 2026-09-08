"""Engine tests for mamey/domain_tree.py — the gated BGC-machinery domain-tree builder (VGP-400).

IN-TREE: imports the INSTALLED module, so these assert the behavior of the tree they ship in (the
packet-relative variant that only tested the packet's own copy is kept as packet evidence only).
No CPU inference runs here — mafft/IQ-TREE are exercised through the injectable `runner`; the sanity
gate calls the real in-tree tools/tree_sanity_check.py.

Class-level homology context; the builder assigns no score and mints no rescue; judgment deferred.
"""
from pathlib import Path

import pytest

from mamey import domain_tree as DT

GOOD = "M" + "AKLVEGD" * 50   # 351 aa — inside the PKS_KS length window


def _dom(i, seq, **kw):
    d = {"strain": "AS-1", "node": f"NODE_{i}", "region": "region001",
         "locus_tag": f"ctg{i}_1", "domain_id": f"d{i}", "translation": seq}
    d.update(kw)
    return d


def test_spec_refusals_are_typed_and_name_the_known_set(tmp_path):
    with pytest.raises(DT.DomainTreeError, match="SPEC_MISSING"):
        DT.load_spec(tmp_path / "nope.json")
    p = tmp_path / "s.json"
    p.write_text('{"domain_class": "PKS_KS"}')
    with pytest.raises(DT.DomainTreeError, match="SPEC_INCOMPLETE"):
        DT.load_spec(p)
    p.write_text('{"domain_class": "NOT_A_CLASS", "gbk_dir": "x", "outdir": "y",'
                 '"title": "t", "approved_by": "Someone"}')
    with pytest.raises(DT.DomainTreeError, match="SPEC_UNKNOWN_CLASS.*PKS_KS"):
        DT.load_spec(p)
    # v9.7.413: a spec that neither names an outgroup nor declares itself outgroup-less is refused
    # HERE, before the CPU-heavy inference, because the tree it produces cannot pass the sanity gate.
    p.write_text('{"domain_class": "PKS_KS", "gbk_dir": "x", "outdir": "y",'
                 '"title": "t", "approved_by": "Someone"}')
    with pytest.raises(DT.DomainTreeError, match="SPEC_NO_OUTGROUP_UNDECLARED"):
        DT.load_spec(p)
    p.write_text('{"domain_class": "PKS_KS", "gbk_dir": "x", "outdir": "y",'
                 '"title": "t", "approved_by": "Someone", "allow_no_outgroup": true}')
    spec = DT.load_spec(p)
    assert spec["min_tips"] == DT.MIN_TIPS and spec["outgroup"] is None
    assert spec["allow_no_outgroup"] is True


def test_staging_dedups_flags_lengths_and_keeps_receipts(tmp_path):
    doms = [_dom(1, GOOD), _dom(2, GOOD),              # 2 duplicates 1 byte-for-byte
            _dom(3, "MKV"),                            # fragment -> SHORT_EXCLUDED
            _dom(4, GOOD + "A" * 500),                 # over-long -> LONG_FLAGGED (kept)
            _dom(5, "M" + "PQRSTVW" * 50),
            _dom(6, "M" + "GHIKLMN" * 50)]
    out = DT.stage_domains(doms, "PKS_KS", tmp_path / "o", min_tips=4)
    assert (out["n_dedup"], out["n_short_excluded"], out["n_long_flagged"]) == (1, 1, 1)
    assert out["n_staged"] == 4                        # staged == records entering the tree
    prov = Path(out["provenance"]).read_text()
    for token in ("SHORT_EXCLUDED", "LONG_FLAGGED", "DUP_OF:"):
        assert token in prov, f"provenance must record {token}"
    assert Path(out["fasta"]).read_text().count(">") == 4


def test_thin_tree_is_refused_not_drawn(tmp_path):
    with pytest.raises(DT.DomainTreeError, match="STAGE_TOO_FEW_TIPS"):
        DT.stage_domains([_dom(1, GOOD), _dom(2, "MKV")], "PKS_KS", tmp_path / "o2", min_tips=4)


def test_staging_is_deterministic(tmp_path):
    doms = [_dom(i, "M" + "ACDEFGH" * (45 + i)) for i in range(1, 6)]
    a = DT.stage_domains(list(reversed(doms)), "PKS_KS", tmp_path / "a")
    b = DT.stage_domains(doms, "PKS_KS", tmp_path / "b")
    assert Path(a["fasta"]).read_text() == Path(b["fasta"]).read_text()
    assert Path(a["provenance"]).read_text() == Path(b["provenance"]).read_text()


def test_cpu_run_requires_approval_and_pins_the_seed(tmp_path):
    fa = tmp_path / "s.fasta"
    fa.write_text(">a\nMKV\n")
    with pytest.raises(DT.DomainTreeError, match="APPROVAL_REQUIRED"):
        DT.build_tree(fa, tmp_path, approved_by="")          # tree-approval gate parity
    calls = []

    def fake_run(cmd, **kw):
        calls.append(cmd)
        if cmd[0] == "iqtree":
            Path(str(tmp_path / "s.iq") + ".treefile").write_text("(a:0.1,b:0.1);")

    tre = DT.build_tree(fa, tmp_path, approved_by="Someone", runner=fake_run)
    assert calls[0][0] == "mafft" and calls[1][0] == "iqtree"
    assert "-seed" in calls[1] and "12345" in calls[1]        # reproducible inference
    assert tre.endswith(".treefile")


def test_gate_delegates_to_the_installed_outgroup_aware_checker(tmp_path):
    ok_t = tmp_path / "ok.treefile"
    ok_t.write_text("((A:0.01,B:0.01):0.01,(C:0.01,D:0.01):0.01,Ref_OUTGROUP:0.31);")
    bad_t = tmp_path / "bad.treefile"
    bad_t.write_text("((A:0.01,B:0.01):0.01,(C:0.01,D:0.01):0.01,E:0.40);")
    ok, msg = DT.gate_tree(ok_t)
    assert ok and "outgroup-exempt" in msg      # correct outgroup is exempt, not a FAIL
    bad_ok, bad_msg = DT.gate_tree(bad_t)
    # v9.7.413 addendum: `bad_t` carries no outgroup tag, so NO_OUTGROUP fires -- and fires ALONE,
    # not alongside a DOMINATING_BRANCH finding on the same untrusted branch (see the suppression
    # fix in tools/tree_sanity_check.py::check()).
    assert not bad_ok and "NO_OUTGROUP" in bad_msg and "DOMINATING_BRANCH" not in bad_msg
    # v9.7.413: the declaration reaches the gate, and it still catches a real dominator.
    dec_ok, dec_msg = DT.gate_tree(bad_t, require_outgroup=False)
    assert not dec_ok and "DOMINATING_BRANCH" in dec_msg
    assert "declared outgroup-less" in dec_msg


def test_summary_and_clade_table_schemas(tmp_path):
    p = DT.write_summary([{"domain_class": "PKS_KS", "strain": "AS-1", "tip": "t1"}], tmp_path, "PKS_KS")
    assert Path(p).read_text().splitlines()[0].split("\t") == DT.SUMMARY_FIELDS
    # the clade table must satisfy tools/domain_phylo_rescue.py::load_clades() exactly
    c = DT.write_clade_table(
        [{"domain_id": "d2", "bgc_id": "BGC002", "domain_class": "PKS_KS", "clade_id": "KC2",
          "shalrt": "95", "ufboot": "99"},
         {"domain_id": "d1", "bgc_id": "BGC001", "domain_class": "PKS_KS", "clade_id": "KC1",
          "shalrt": "", "ufboot": ""}],
        tmp_path, "PKS_KS")
    lines = Path(c).read_text().splitlines()
    assert {"domain_id", "bgc_id", "domain_class", "clade_id", "shalrt", "ufboot"}.issubset(
        set(lines[0].split("\t")))
    assert lines[1].startswith("d1\tBGC001")     # deterministic: clade_id then domain_id


def test_clade_table_is_accepted_by_the_in_tree_rescue_reader(tmp_path):
    """End-to-end contract check: the emitted table loads in tools/domain_phylo_rescue.py without the
    'clade table missing columns' refusal — the wiring this packet exists to close."""
    import importlib.util
    import sys
    tools = Path(DT.__file__).resolve().parent.parent / "tools" / "domain_phylo_rescue.py"
    if not tools.exists():
        pytest.skip("tools/domain_phylo_rescue.py not present in this tree")
    spec = importlib.util.spec_from_file_location("_dpr_contract", tools)
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("_dpr_contract", mod)
    spec.loader.exec_module(mod)
    c = DT.write_clade_table(
        [{"domain_id": "d1", "bgc_id": "BGC001", "domain_class": "PKS_KS", "clade_id": "KC1",
          "shalrt": "95", "ufboot": "99"}], tmp_path, "PKS_KS")
    rows = mod.load_clades(Path(c))
    assert rows and rows[0]["clade_id"] == "KC1"
