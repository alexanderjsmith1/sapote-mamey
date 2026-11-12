"""A path-qualified tool reference that exists exactly in the bundle is not dangling.

The lenient scan matched names only inside SEARCH_DIRS, so a correct reference such as
`examples/token_light_documents/build_pilot_inputs.py` was reported as dangling while the
strict scan accepted it. That broke the rule that strict never drops a lenient finding.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from check_dangling_refs import scan_tools  # noqa: E402


def _tree(tmp_path: pathlib.Path, doc: str) -> pathlib.Path:
    (tmp_path / "tools").mkdir()
    (tmp_path / "examples" / "kit").mkdir(parents=True)
    (tmp_path / "examples" / "kit" / "builder.py").write_text("print('x')\n")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "PAGE.md").write_text(doc)
    return tmp_path


def test_exact_path_outside_search_dirs_is_not_dangling(tmp_path):
    root = _tree(tmp_path, "Run `examples/kit/builder.py`.\n")
    assert "builder.py" not in scan_tools(root)
    assert "examples/kit/builder.py" not in scan_tools(root, strict_paths=True)


def test_wrong_folder_still_dangles(tmp_path):
    root = _tree(tmp_path, "Run `examples/other/builder.py` and `tools/missing_tool.py`.\n")
    assert "missing_tool.py" in scan_tools(root)
    strict = scan_tools(root, strict_paths=True)
    assert "examples/other/builder.py" in strict
    assert "tools/missing_tool.py" in strict


def test_reference_escaping_the_bundle_is_not_exempted(tmp_path):
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    _tree(bundle, "See `../outside_tool.py`.\n")
    (tmp_path / "outside_tool.py").write_text("print('x')\n")
    assert "outside_tool.py" in scan_tools(bundle)
