"""The tree-figure exporter has to actually run, and its generated helper has to be inert.

Two tests in the bundle reference `tools/export_tree_figure_source_package.py`, and both only
call `.read_text()` on it and assert that strings appear. Nothing executes it. That is how a
`NameError` on the last statement of `main()` — `sys.stdout.write(...)` with `sys` never
imported — survived from v9.7.431 to v9.7.438 while every one of those cuts shipped green.

`tools/placement_display.py` invokes this tool through `_run`, which raises on a non-zero
return code, and the caller turns that into `DISPLAY_REFUSED` / exit 2. So the crash is not
cosmetic: it fails the whole placement-display path at its last step, after the package has
already been written to disk.

The second test covers the generated `_rerender_captioned.sh`. Its values come from a filename
and from receipt JSON, and they were interpolated into the script unquoted, so a `$( )` in
either was executed when an operator ran the helper. `sh -n` accepts such a script, which is
why this needs a canary rather than a syntax check.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/export_tree_figure_source_package.py"


def _make_source(src: Path, stem: str, analysis_name: str = "analysis.nwk") -> None:
    src.mkdir(parents=True)
    (src / f"{stem}_display.nwk").write_text("(A:0.1,B:0.1);\n")
    (src / f"{stem}_rect02.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (src / f"{stem}_rect02.pdf").write_bytes(b"%PDF-1.4\n")
    (src / f"{stem}_rect02.methods.txt").write_text("caption text\n")
    (src / "display_input.tsv").write_text("label\tsource\nA\tbee\n")
    (src / "display_input.fasta").write_text(">A\nACGT\n")
    (src / "METHODS.md").write_text("# methods\n")
    (src / analysis_name).write_text("(A:0.1,B:0.1);\n")
    (src / "display_tree.nwk").write_text("(A:0.1,B:0.1);\n")
    (src / "display_meta.tsv").write_text("label\nA\n")
    (src / f"{stem}_display_receipt.json").write_text(json.dumps({
        "inputs": {"analysis_tree": {"path": analysis_name}},
        "outputs": {"tree": {"path": "display_tree.nwk"},
                    "metadata": {"path": "display_meta.tsv"}},
    }))


def _export(tmp_path: Path, stem: str, analysis_name: str = "analysis.nwk"):
    src, out = tmp_path / "src", tmp_path / "out"
    _make_source(src, stem, analysis_name)
    return subprocess.run([sys.executable, str(TOOL), str(src), "--out", str(out)],
                          capture_output=True, text=True), out


def test_exporter_exits_zero_and_prints_the_package_path(tmp_path):
    """The defect: rc=1 with NameError on the final line, after writing the whole package."""
    result, out = _export(tmp_path, "AS-705_rect_v1")
    assert result.returncode == 0, result.stderr
    assert "NameError" not in result.stderr
    assert result.stdout.strip() == str(out)


def test_exporter_writes_the_package_it_advertises(tmp_path):
    result, out = _export(tmp_path, "AS-705_rect_v1")
    assert result.returncode == 0, result.stderr
    for name in ("AS-705_rect_v1_tree.nwk", "AS-705_rect_v1_analysis_tree.nwk",
                 "AS-705_rect_v1_caption.txt", "AS-705_rect_v1_render_figure.R",
                 "AS-705_rect_v1_rerender_captioned.sh", "MANIFEST.json"):
        assert (out / name).is_file(), name


@pytest.mark.parametrize("stem,analysis", [
    ('AS-705_$(touch STEM_CANARY)', "analysis.nwk"),
    ("AS-705_rect_v1", 'analysis_$(touch RECEIPT_CANARY).nwk'),
])
def test_generated_helper_does_not_execute_interpolated_values(tmp_path, stem, analysis):
    """A `$( )` in a filename or a receipt path must not run when the helper runs."""
    result, out = _export(tmp_path, stem, analysis)
    assert result.returncode == 0, result.stderr
    helper = next(out.glob("*_rerender_captioned.sh"))

    assert subprocess.run(["sh", "-n", str(helper)]).returncode == 0, "helper is not valid sh"

    # The helper fails at Rscript (absent in CI) or at cat; either way the substitutions
    # would already have run by then if the values were unquoted.
    subprocess.run(["sh", str(helper)], cwd=str(out), capture_output=True, text=True)
    for canary in ("STEM_CANARY", "RECEIPT_CANARY"):
        assert not list(out.rglob(canary)), f"{canary} fired — value was executed, not quoted"


def test_helper_quotes_every_interpolated_value(tmp_path):
    """Read the generated script: no bare `$(` outside the two intended constructs."""
    result, out = _export(tmp_path, "AS-705_rect_v1")
    assert result.returncode == 0, result.stderr
    helper = next(out.glob("*_rerender_captioned.sh"))
    for line in helper.read_text().splitlines():
        if line.startswith(("export GG_GATE_TREE", "export GG_DISPLAY_RECEIPT", "Rscript ")):
            assert "$(" not in line, line
