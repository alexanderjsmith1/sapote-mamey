"""v9.7.283: the four pre-release fixes that got lost in the .276->.282 stream and were
re-verified against .282 (fix1 pangenome NameError, fix2 EXCEPTIONAL leads, fix3 verify-guide
dir crash, fix4 rggmci mkdir). Red-first regression guards."""
from __future__ import annotations
import inspect
from pathlib import Path

import mamey.bgc_guide as bgc_guide
import mamey.modeb_template_emitter as mte


def test_fix1_pangenome_uses_core_min_not_CORE_MIN():
    src = Path("tools/build_pangenome.py").read_text(encoding="utf-8")
    # the executable f-string must use {core_min}; CORE_MIN may only survive in a comment
    assert "{core_min} strains" in src
    for ln in src.splitlines():
        if "CORE_MIN" in ln:
            assert ln.lstrip().startswith("#"), f"executable CORE_MIN ref: {ln!r}"


def test_fix2_exceptional_is_selected_in_leads():
    src = inspect.getsource(mte._select_scope)
    assert '"EXCEPTIONAL"' in src, "EXCEPTIONAL tier missing from leads selection"
    # order: EXCEPTIONAL must be inside the same tier tuple as HIGH
    assert '("EXCEPTIONAL", "HIGH"' in src


def test_fix3_verify_guide_rejects_directory_cleanly(tmp_path):
    d = tmp_path / "a_directory"
    d.mkdir()
    ok, errs, *_ = bgc_guide.verify_authored_guide(str(d))
    assert ok is False
    assert any("directory" in e.lower() for e in errs), errs


def test_fix4_rggmci_makedirs_parent():
    src = Path("tools/rggmci_cohort_rollup.py").read_text(encoding="utf-8")
    assert "os.makedirs(_parent, exist_ok=True)" in src
    assert "import os" in src
