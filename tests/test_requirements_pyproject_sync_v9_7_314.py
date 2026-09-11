"""v9.7.285 finding #4 (dropped .285->.292->.314): requirements.txt drifted from pyproject core deps.
reportlab is a pyproject core dep (backs the primary PDF renderer) but was commented out in
requirements.txt with a false "NOT imported anywhere" note. Locks the invariant."""
from __future__ import annotations
import pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from check_requirements_pyproject_sync import check, pyproject_core_deps, requirements_active  # noqa
def test_shipped_tree_is_in_sync():
    assert not check(ROOT), "pyproject core deps missing as active requirements.txt lines: " + ", ".join(check(ROOT))
def test_reportlab_specifically_is_active():
    assert "reportlab" in pyproject_core_deps(ROOT) and "reportlab" in requirements_active(ROOT)
def test_detector_catches_a_commented_core_dep(tmp_path):
    (tmp_path/"pyproject.toml").write_text('[project]\nname="x"\ndependencies=["openpyxl>=3.1","reportlab>=4.0,<5.0"]\n',encoding="utf-8")
    (tmp_path/"requirements.txt").write_text("openpyxl>=3.1.2\n# reportlab>=4.0,<5.0\n",encoding="utf-8")
    assert check(tmp_path) == ["reportlab"]
