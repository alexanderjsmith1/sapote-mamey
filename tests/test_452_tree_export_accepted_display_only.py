"""Card attine_452_tree_export_accepted_display_only: the tree source-package export binds the accepted display tree by
its exact name ({stem}_display.nwk) and skips the root-as-built *_GATE_FAIL_diagnostic_* files that placement_display
writes beside a long-rooted figure (#482). Before this, the export refused with "expected exactly one '*_display.nwk'"
after the figures were written. The package README lists the diagnostics as not figure sources. Synthetic files only."""
import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/export_tree_figure_source_package.py"
spec = importlib.util.spec_from_file_location("export_runs_452d", ROOT / "tests/test_export_tree_source_package_runs_v97439.py")
base = importlib.util.module_from_spec(spec); spec.loader.exec_module(base)
DIAG = "SYN_tree_root_as_built_GATE_FAIL_diagnostic"


def _diagnostic(src):
    (src / f"{DIAG}_display.nwk").write_text("(A:0.5,B:0.1);\n")
    (src / f"{DIAG}_rect02.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (src / f"{DIAG}_rect02.pdf").write_bytes(b"%PDF-1.4\n")
    (src / f"{DIAG}_rect02.methods.txt").write_text("diagnostic\n")
    (src / f"{DIAG}_display_receipt.json").write_text("{}")


def _run(src, out):
    return subprocess.run([sys.executable, str(TOOL), str(src), "--out", str(out)], capture_output=True, text=True)


def test_accepted_plus_diagnostic_exports_the_accepted_tree(tmp_path):
    src = tmp_path / "src"; base._make_source(src, "SYN_tree"); _diagnostic(src)
    r = _run(src, tmp_path / "out")
    assert r.returncode == 0, r.stderr
    out = tmp_path / "out"
    assert (out / "SYN_tree_tree.nwk").read_text() == "(A:0.1,B:0.1);\n"
    assert not any("GATE_FAIL_diagnostic" in p.name for p in out.rglob("*"))
    readme = (out / "README.md").read_text()
    assert "Diagnostics (not figure sources)" in readme and f"{DIAG}_display.nwk" in readme


def test_two_accepted_figures_still_refuse(tmp_path):
    src = tmp_path / "src"; base._make_source(src, "SYN_tree")
    (src / "SYN_other_rect02.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (src / "SYN_other_display.nwk").write_text("(A:0.1,B:0.1);\n")
    r = _run(src, tmp_path / "out")
    assert r.returncode != 0 and "expected exactly one" in (r.stderr + r.stdout)


def test_the_diagnostic_alone_refuses(tmp_path):
    src = tmp_path / "src"; src.mkdir(); _diagnostic(src)
    for name in ("display_input.tsv", "display_input.fasta", "METHODS.md"):
        (src / name).write_text("x\n")
    r = _run(src, tmp_path / "out")
    assert r.returncode != 0 and not (tmp_path / "out").exists()
