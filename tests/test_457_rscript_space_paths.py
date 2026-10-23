"""Path bootstrap smoke tests; no rendering or optional plotting packages."""
from pathlib import Path
import shutil
import subprocess
import pytest

NAMES = ["render_tree_one_bar_row.R", "render_tree_bar_groups.R"]

@pytest.mark.parametrize("name", NAMES)
def test_real_wrapper_from_space_path(tmp_path, name):
    rscript = shutil.which("Rscript")
    if rscript is None:
        pytest.skip("Rscript unavailable")
    folder = tmp_path / "bundle with spaces"; folder.mkdir()
    source = Path(__file__).parents[1] / "tools" / name
    tool = folder / name; tool.write_bytes(source.read_bytes())
    # A sibling stub isolates the real wrapper's source resolution from render dependencies.
    expected_single = "TRUE" if name == "render_tree_one_bar_row.R" else "FALSE"
    (folder / "tree_track_render.R").write_text(
        'render_tree_tracks <- function(args, single=FALSE) { stopifnot(identical(args, "synthetic")); '
        + 'stopifnot(identical(single, ' + expected_single + ')) }\n')
    result = subprocess.run([rscript, "--vanilla", str(tool), "synthetic"], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr

@pytest.mark.parametrize("name", ['render_tree_one_bar_row.R', 'render_tree_bar_groups.R', 'cohort_tree_ggtree.R', 'sapote_matrix_figure.R', 'sapote_strain_figure.R', 'figure_factory_next_ggplot.R', 'tygs_figures.R', 'sapote_bioassay_figure.R', 'sapote_locus_map.R', 'sapote_tidy_figure.R'])
def test_all_self_path_bootstraps_decode(name):
    text = (Path(__file__).parents[1] / "tools" / name).read_text()
    assert 'gsub(' in text and '~+~' in text and 'fixed=TRUE' in text

@pytest.mark.parametrize("name", ["cohort_tree_ggtree.R", "sapote_matrix_figure.R", "sapote_strain_figure.R", "figure_factory_next_ggplot.R", "tygs_figures.R", "sapote_bioassay_figure.R", "sapote_locus_map.R", "sapote_tidy_figure.R"])
def test_bootstrap_from_space_path(tmp_path, name):
    rscript = shutil.which("Rscript")
    if rscript is None:
        pytest.skip("Rscript unavailable")
    lines = (Path(__file__).parents[1] / "tools" / name).read_text().splitlines()
    start = next(i for i, line in enumerate(lines) if "--file=" in line and "commandArgs" in line)
    stop = next(i for i in range(start, len(lines)) if lines[i].startswith("source("))
    if not lines[stop].rstrip().endswith(")"):
        stop += 1
    folder = tmp_path / "bootstrap with spaces"; folder.mkdir()
    tool = folder / name
    tool.write_text("\n".join(lines[start:stop+1]) + "\nstopifnot(sibling_loaded)\n")
    # Only the genuine self-path bootstrap is executed; rendering and library admission are separate.
    for sibling in ("sapote_figure_theme.R", "sapote_pub_layout.R"):
        (folder / sibling).write_text("sibling_loaded <- TRUE\n")
    result = subprocess.run([rscript, "--vanilla", str(tool)], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
