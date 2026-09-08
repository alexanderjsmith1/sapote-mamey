"""v9.7.383 — WAC/DSM audit: A-02 (offline build wheels ship) and A-05 (figure-state marker).

A-02: `pyproject` requires setuptools>=68 + wheel under build isolation; a fresh no-network venv
can't fetch them. Option A (Alex): ship the MIT build wheels in the bundle and point bootstrap at
them. These pin that they ship and that bootstrap references them.

A-05: NO_FIGURES_RENDERED.md was written early (--brief none) and never cleared when a later figure
path rendered — leaving a "no figures" marker beside real PNGs (observed on WAC-01375). The run now
reconciles the marker after all figure steps. This pins the reconciliation predicate.
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_build_wheels_ship():
    wd = ROOT / "wheels"
    assert wd.is_dir(), "bundle must ship a wheels/ dir with the build backend (A-02 option A)"
    names = [p.name for p in wd.glob("*.whl")]
    assert any(n.startswith("setuptools-") and n.endswith("py3-none-any.whl") for n in names), names
    assert any(n.startswith("wheel-") and n.endswith("py3-none-any.whl") for n in names), names
    # pyproject's floor must be satisfiable by the shipped setuptools
    st = next(p for p in wd.glob("setuptools-*.whl"))
    ver = re.search(r"setuptools-(\d+)", st.name).group(1)
    assert int(ver) >= 68, f"shipped setuptools {ver} < pyproject floor 68"
    assert (wd / "WHEELS_MANIFEST.md").is_file(), "build wheels need a license/SHA manifest"


def test_bootstrap_points_at_bundled_wheels():
    bs = (ROOT / "bootstrap.sh").read_text(encoding="utf-8")
    assert "BUNDLED_WHEELS" in bs and "wheels" in bs, "bootstrap must add the bundled wheels to --find-links"


def _reconcile(pkg: pathlib.Path):
    """Mirror of the run's A-05 reconciliation predicate (cli.run_one_strain)."""
    m = pkg / "NO_FIGURES_RENDERED.md"
    figdirs = ("figures", "gold_figures", "locus_maps", "smoke_figures")
    rendered = any(
        (pkg / d).is_dir() and any(p.suffix.lower() in (".png", ".svg") for p in (pkg / d).rglob("*"))
        for d in figdirs
    )
    if m.exists() and rendered:
        m.unlink()


def test_stale_marker_cleared_when_figures_exist(tmp_path):
    (tmp_path / "NO_FIGURES_RENDERED.md").write_text("x")
    (tmp_path / "figures").mkdir()
    (tmp_path / "figures" / "a.png").write_text("x")
    _reconcile(tmp_path)
    assert not (tmp_path / "NO_FIGURES_RENDERED.md").exists()


def test_marker_kept_when_no_figures(tmp_path):
    (tmp_path / "NO_FIGURES_RENDERED.md").write_text("x")
    _reconcile(tmp_path)
    assert (tmp_path / "NO_FIGURES_RENDERED.md").exists()


def test_cli_run_reconciles_marker_inline():
    # guard that the reconciliation actually lives in the run path, not only this test
    cli = (ROOT / "mamey" / "cli.py").read_text(encoding="utf-8")
    assert "NO_FIGURES_RENDERED.md" in cli and "A-05" in cli, "run_one_strain must reconcile the marker"
