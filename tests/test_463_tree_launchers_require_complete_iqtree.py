"""Every IQ-TREE launcher refuses a bare .treefile.

House rule: a tree build is complete only when .contree exists, supports are on the
.treefile, and the IQ-TREE log says "Total wall-clock time". A .treefile alone means
the run was interrupted.
"""
from pathlib import Path

import pytest

from mamey import domain_tree as DT
from mamey.phylo_evidence import iqtree_prefix_completion as prefix_completion, require_complete_iqtree as require_complete

SUPPORTED = "((a:0.1,b:0.1)100:0.0);"


def _write(pre, treefile=SUPPORTED, contree=SUPPORTED, log="Total wall-clock time used: 1.0 sec\n"):
    for ext, text in ((".treefile", treefile), (".contree", contree), (".log", log)):
        if text is not None:
            Path(str(pre) + ext).write_text(text)


@pytest.mark.parametrize("kw,reason", [
    (dict(contree=None), "CONTREE_MISSING"),
    (dict(treefile="(a:0.1,b:0.1);"), "TREEFILE_NO_SUPPORT"),
    (dict(log="ModelFinder running\n"), "LOG_NO_WALLCLOCK"),
])
def test_require_complete_names_what_is_missing(tmp_path, kw, reason):
    _write(tmp_path / "t", **kw)
    with pytest.raises(ValueError, match=reason):
        require_complete(tmp_path / "t", "test")


def test_complete_run_passes(tmp_path):
    _write(tmp_path / "t")
    assert prefix_completion(tmp_path / "t")["status"] == "COMPLETE"


def test_domain_tree_refuses_a_bare_treefile(tmp_path):
    fa = tmp_path / "s.fasta"
    fa.write_text(">a\nMKV\n>b\nMKI\n")

    def run(cmd, **kw):
        if cmd[0] == "iqtree":
            Path(str(tmp_path / "s.iq") + ".treefile").write_text("(a:0.1,b:0.1);")

    with pytest.raises(DT.DomainTreeError, match="IQTREE_INCOMPLETE"):
        DT.build_tree(fa, tmp_path, approved_by="Someone", runner=run)


def test_gate_and_launchers_share_one_rule():
    from tools import gtotree_execution_gate as gate
    from mamey import phylo_evidence as IC
    assert gate.WALL_CLOCK_MARKER == IC.IQTREE_WALL_CLOCK_MARKER
    assert gate.support_node_count is IC.iqtree_support_node_count
    for path in ("tools/build_mlsa.py", "tools/phylo_place.py", "mamey/domain_tree.py"):
        src = (Path(__file__).resolve().parents[1] / path).read_text()
        assert "require_complete(" in src, path
