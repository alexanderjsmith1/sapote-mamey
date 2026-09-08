"""Generic behavior regressions; no external phylogenetic programs are run."""
import ast
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import shutil
import pytest

SRC = Path(__file__).resolve().parents[1] / "tools" / "phylo_place.py"
spec = importlib.util.spec_from_file_location("audit_phylo", SRC)
pp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pp)

@pytest.mark.parametrize("label,expected", [
    ("NR_123456.1_Genus_species_AS_4", False),
    ("AB123456_Genus_species_AS_4", False),
    ("SID7", True), ("AS-7", True), ("RefAlpha", False),
])
def test_neighborhood_and_figure_classify_same_tip(label, expected):
    # Evaluate the actual local predicate assignments without invoking expensive rendering.
    module = ast.parse(SRC.read_text())
    for name in ("_grafted_neighborhoods", "_render_tree"):
        fn = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == name)
        assignments = [n for n in fn.body if isinstance(n, ast.Assign)
                       and any(isinstance(t, ast.Name) and t.id in ("_is_ref_acc", "is_q") for t in n.targets)]
        ns = dict(pp.__dict__)
        exec(compile(ast.Module(body=assignments, type_ignores=[]), str(SRC), "exec"), ns)
        assert ns["is_q"](SimpleNamespace(name=label)) is expected


def test_successful_iqtree_rebuild_clears_old_raxml_model(tmp_path, monkeypatch):
    fasta = tmp_path / "input.fasta"
    fasta.write_text(">RefA\nACGT\n>RefB\nACGA\n")
    old = tmp_path / "ref.bestModel"
    old.write_text("stale optimized parameters")
    monkeypatch.setattr(pp, "_which", lambda name, *args: name if name in ("mafft", "iqtree3") else None)
    monkeypatch.setattr(pp, "_is_protein", lambda path: False)
    def dedup(src, dst, report, **kw):
        shutil.copy(src, dst)
        return 2, 0
    monkeypatch.setattr(pp, "_dedup_reference", dedup)
    monkeypatch.setattr(pp, "_ref_length_warn", lambda src, *a, **kw: (src, []))
    monkeypatch.setattr(pp, "_sanitize_fasta", lambda src, dst, *a, **kw: shutil.copy(src, dst))
    monkeypatch.setattr(pp, "_stamp", lambda *a: None)
    def call(cmd, **kw):
        if cmd[0] == "mafft":
            kw["stdout"].write(fasta.read_text())
            kw["stdout"].flush()
        else:
            Path(cmd[cmd.index("-pre") + 1] + ".treefile").write_text("(RefA:0.1,RefB:0.2);")
        return 0
    monkeypatch.setattr(pp.subprocess, "call", call)
    args = SimpleNamespace(group="streptomyces", approved_by="generic test", ref_fasta=str(fasta),
                           refpkg=str(tmp_path), bootstrap=100, threads=1, add_outgroup="")
    assert pp.cmd_build_ref(args) == 0
    assert not old.exists(), "placement must not consume parameters from the previous RAxML tree"
    assert (tmp_path / "MODEL").read_text().strip()
