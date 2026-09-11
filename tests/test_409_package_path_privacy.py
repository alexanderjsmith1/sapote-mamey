"""TESTS — CLAUDE_409_package_path_privacy (DEEP_AUDIT3 F1/F2/F5).

One file proves BOTH directions via env vars, like CLAUDE_409_release_leakgate:

  SAPOTE_RENDER_PY      -> path to mamey/render_all_figures.py under test
  SAPOTE_SEAL_SWEEP_PY  -> path to tools/seal_sweep.py under test
  SAPOTE_LAYPERSON_PY   -> path to mamey/layperson_guide.py under test

FAIL-BEFORE  (env vars point at the pristine v9.7.408 bundle files):
  * the render summary the module ships still embeds `<home>/<user>/...`
  * the package path-scrub QA function does not exist yet

PASS-AFTER   (env vars point at the .409-patched copies):
  * the shipped render summary carries package-RELATIVE paths, no `/Users/`
  * the QA function flags a planted absolute path and stays quiet on a clean package

Every module is loaded from its file path with a stubbed `mamey.console`, so the
tests run standalone (no full mamey package or figure stack needed). No private
literal is embedded — the "operator" path used here is a synthetic fixture.
"""
import importlib.util
import json
import os
import sys
import types
from pathlib import Path

import pytest


# --------------------------------------------------------------------------- #
# module loading helpers
# --------------------------------------------------------------------------- #
def _default(rel_from_bundle: str) -> str:
    # tests/ sits directly under the bundle root; the targets are one level up.
    return str(Path(__file__).resolve().parents[1] / rel_from_bundle)


def _install_console_stub() -> None:
    """Register minimal `mamey.*` submodule stubs so the modules under test load from a
    file path without the full package/figure stack. Only the symbols the targets import
    at module top-level are provided; none is exercised by the pure helpers we test."""
    if "mamey" not in sys.modules:
        pkg = types.ModuleType("mamey")
        # v9.7.416: this was `__path__ = []`, which marks it a package but gives submodule import
        # NOWHERE to look — so the real `mamey.csv_safety` that render_all_figures.py imports at
        # module top level could not resolve, and this file failed 4/7 when run on its own against
        # the sealed v9.7.415 tree. It passed in a full-suite run only because some earlier test had
        # already imported the real `mamey`, so this stub was never installed: the file's green
        # depended on another test polluting the interpreter first. Point `__path__` at the real
        # package directory. The explicit stubs below still win — they are pre-registered in
        # sys.modules — while everything NOT stubbed resolves to the real module it always meant.
        pkg.__path__ = [str(Path(__file__).resolve().parents[1] / "mamey")]
        sys.modules["mamey"] = pkg
    if "mamey.console" not in sys.modules:
        console = types.ModuleType("mamey.console")
        def _noop_emit(*a, **k):
            return None
        console.emit = _noop_emit  # no-op emitter on a SYNTHETIC module (not a real module attribute)
        sys.modules["mamey.console"] = console
    # v9.7.416: `mamey.exact_identity` is NO LONGER stubbed. The stub carried exactly two symbols
    # (ExactLocusIdentityError, exact_locus_display) and the real module has since grown
    # exact_locus_from_mapping / exact_locus_from_native_manifest_bgc /
    # exact_locus_from_native_inventory_row, which mamey/layperson_guide.py imports at module top
    # level -- so the stub broke the very load it existed to enable, and this file's
    # test_layperson_receipt_relativizer failed on the sealed v9.7.415 tree both alone and in a full
    # run. The real module is import-cheap on purpose (re + dataclasses + collections.abc; its one
    # heavy dependency, .crosswalk, is imported inside a function), so with `mamey.__path__` now
    # pointing at the real package there is nothing left for a stub to buy. A synthetic stub of a
    # module that keeps growing is a maintenance debt that fails closed at best and lies at worst.
    if "mamey.figure_theme" not in sys.modules:
        ft = types.ModuleType("mamey.figure_theme")
        ft.CLAIM_SAFETY = "CLAIM-SAFETY"
        def _footer_passthrough(text, *a, **k):
            return text
        ft.add_claim_safety_footer = _footer_passthrough  # synthetic module stub
        sys.modules["mamey.figure_theme"] = ft


# --------------------------------------------------------------------------- #
# stub containment (v9.7.416)
# --------------------------------------------------------------------------- #
# `_install_console_stub` plants synthetic modules under REAL dotted names in the process-wide
# `sys.modules`, and `_load` registers more. Nothing removed them, so every later test in the same
# interpreter that imported `mamey.*` got the stub instead of the real module. Measured on the
# sealed v9.7.415 tree:
#
#     pytest tests/test_409_package_path_privacy.py tests/test_cut415_repair_regressions.py
#         -> 10 failed, 6 passed
#     pytest tests/test_cut415_repair_regressions.py          (alone)  -> 9 passed
#
# with `ImportError: cannot import name 'exact_locus_from_native_inventory_row' from
# 'mamey.exact_identity' (unknown location)` — "unknown location" because the stub is a bare
# `types.ModuleType`. The `mamey` stub is worse than the leaf ones: it sets `__path__ = []`, so
# ANY subsequent `import mamey.<anything>` fails, not only the names stubbed here.
#
# The danger is not the noisy failure. It is the quiet case: a later test that imports one of these
# names and asserts on a stub's behaviour (`exact_locus_display` here returns "") can go GREEN
# while testing nothing. Contain the stubs to this module.
_ABSENT = object()

_STUBBED_NAMES = (
    "mamey", "mamey.console", "mamey.exact_identity", "mamey.figure_theme",
    "mamey.render_all_figures", "mamey.layperson_guide", "seal_sweep_under_test",
)


@pytest.fixture(autouse=True, scope="module")
def _contain_stub_modules():
    """Restore `sys.modules` for every name this file stubs or reloads.

    Module-scoped and autouse: the stubs are installed lazily inside `_load`, so the snapshot has
    to be taken before the first test and the restore has to outlive the last one.
    """
    before = {name: sys.modules.get(name, _ABSENT) for name in _STUBBED_NAMES}
    yield
    for name, prior in before.items():
        if prior is _ABSENT:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = prior


def _load(path: str, name: str):
    """Load a module from a file path. `name` may be dotted (e.g. ``mamey.foo``) so a
    target with unwrapped relative imports resolves them against the stub package."""
    _install_console_stub()
    if name in sys.modules:
        del sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod  # register before exec so relative imports resolve
    spec.loader.exec_module(mod)
    return mod


def _render_mod():
    return _load(os.environ.get("SAPOTE_RENDER_PY", _default("mamey/render_all_figures.py")),
                 "mamey.render_all_figures")


def _seal_mod():
    return _load(os.environ.get("SAPOTE_SEAL_SWEEP_PY", _default("tools/seal_sweep.py")),
                 "seal_sweep_under_test")


def _layperson_mod():
    return _load(os.environ.get("SAPOTE_LAYPERSON_PY", _default("mamey/layperson_guide.py")),
                 "mamey.layperson_guide")


# A synthetic operator root — NOT a real path (safe to embed in a test).
FAKE_ROOT = "/Users/testoperator/PrivateWorkspace/runs/AS-TEST/package"


def _summary_fixture(root: str) -> dict:
    """A render-all summary shaped like the real one, with the same absolute-path
    fields DEEP_AUDIT3 F1 flagged (package / out / figures_dir / manifest)."""
    return {
        "package": root,
        "requested": ["smoke"],
        "sets": {
            "smoke": {"status": "RAN", "figures": 3, "out": root + "/smoke_figures"},
            "locus-maps": {"status": "RAN", "figures": 2, "out": root + "/locus_maps"},
        },
        "ok": True,
        "gathered": {
            "gathered": 5,
            "figures_dir": root + "/figures",
            "manifest": root + "/figures/FIGURE_INDEX.csv",
        },
    }


def _shipped_summary_json(mod, summary: dict, root: str) -> str:
    """Reproduce exactly what render_all_figures_command writes to
    render_all_figures_summary.json for the module under test."""
    fn = getattr(mod, "_relativize_paths", None)
    if fn is None:  # pristine module: ships the raw resolved summary
        return json.dumps(summary, indent=2, default=str)
    return json.dumps(fn(summary, Path(root)), indent=2, default=str)


# --------------------------------------------------------------------------- #
# F1 — render summary must not ship absolute operator paths
# --------------------------------------------------------------------------- #
def test_relativizer_exists():
    """FAIL-BEFORE: the pristine module has no _relativize_paths at all."""
    assert getattr(_render_mod(), "_relativize_paths", None) is not None, \
        "render_all_figures.py has no _relativize_paths — summary ships absolute paths"


def test_shipped_summary_has_no_absolute_operator_path():
    """FAIL-BEFORE: shipped summary JSON embeds `/Users/...`.
       PASS-AFTER:  the same fields are package-relative."""
    mod = _render_mod()
    shipped = _shipped_summary_json(mod, _summary_fixture(FAKE_ROOT), FAKE_ROOT)
    assert "/Users/" not in shipped, "shipped render summary still embeds an operator /Users/ path"
    doc = json.loads(shipped)
    assert doc["package"] == ".", "package field should relativize to '.'"
    assert doc["sets"]["smoke"]["out"] == "smoke_figures"
    assert doc["sets"]["locus-maps"]["out"] == "locus_maps"
    assert doc["gathered"]["figures_dir"] == "figures"
    assert doc["gathered"]["manifest"] == "figures/FIGURE_INDEX.csv"


def test_relativizer_leaves_foreign_and_plain_strings_untouched():
    """Behavior-preservation: values that are not under the package root pass through."""
    mod = _render_mod()
    fn = getattr(mod, "_relativize_paths", None)
    if fn is None:
        pytest.skip("pristine module: no relativizer to exercise")
    got = fn({"status": "RAN", "note": "smoke", "elsewhere": "/opt/other/thing"}, Path(FAKE_ROOT))
    assert got == {"status": "RAN", "note": "smoke", "elsewhere": "/opt/other/thing"}


# --------------------------------------------------------------------------- #
# F5 — package path-scrub QA gate
# --------------------------------------------------------------------------- #
def test_qa_scan_exists():
    """FAIL-BEFORE: pristine seal_sweep has no package path-scrub."""
    assert getattr(_seal_mod(), "scan_package_personal_paths", None) is not None, \
        "seal_sweep.py has no scan_package_personal_paths QA gate"


def test_qa_scan_flags_planted_absolute_path(tmp_path):
    """PASS-AFTER: a planted `<home>/<user>/` path in a shipped package file is flagged."""
    mod = _seal_mod()
    scan = getattr(mod, "scan_package_personal_paths", None)
    assert scan is not None, "no QA gate present (fail-before)"
    pkg = tmp_path / "package"
    pkg.mkdir()
    # Plant the exact leak shape DEEP_AUDIT3 found in a shipped summary JSON.
    (pkg / "render_all_figures_summary.json").write_text(
        json.dumps({"package": FAKE_ROOT, "sets": {}}, indent=2), encoding="utf-8")
    (pkg / "manifest.json").write_text(json.dumps({"strain_id": "AS-TEST"}), encoding="utf-8")
    findings = scan(pkg)
    codes = {f["code"] for f in findings}
    hit_files = {f["path"] for f in findings}
    assert "PERSONAL_PATH_IN_PACKAGE" in codes, f"planted operator path not flagged: {findings}"
    assert "render_all_figures_summary.json" in hit_files
    # The finding must NOT echo the operator's actual path (no re-leak into logs/receipts).
    # A generic pattern description like "<home>/<user>/" is fine; the real username is not.
    assert all("testoperator" not in f["detail"] and FAKE_ROOT not in f["detail"]
               for f in findings)


def test_qa_scan_clean_package_no_findings(tmp_path):
    """False-positive guard: a package with only relative paths yields zero findings."""
    mod = _seal_mod()
    scan = getattr(mod, "scan_package_personal_paths", None)
    if scan is None:
        pytest.skip("pristine module: no QA gate to exercise")
    pkg = tmp_path / "package"
    pkg.mkdir()
    (pkg / "render_all_figures_summary.json").write_text(
        json.dumps({"package": ".", "sets": {"smoke": {"out": "smoke_figures"}}}, indent=2),
        encoding="utf-8")
    (pkg / "GOLD_FIGURES_SKIPPED.md").write_text(
        "Re-render: python -m mamey cohort-figures --runs-dir <runs_dir> "
        "--out <package_dir>/gold_figures --strains AS-TEST\n", encoding="utf-8")
    assert scan(pkg) == []


# --------------------------------------------------------------------------- #
# F1 — layperson receipt output paths
# --------------------------------------------------------------------------- #
def test_layperson_receipt_relativizer(tmp_path):
    """FAIL-BEFORE: no _relativize_receipt_path helper.
       PASS-AFTER:  an absolute output path becomes run-relative, basename fallback otherwise."""
    mod = _layperson_mod()
    fn = getattr(mod, "_relativize_receipt_path", None)
    assert fn is not None, "layperson_guide.py has no _relativize_receipt_path helper"
    run_dir = tmp_path / "AS-TEST"
    guide_dir = run_dir / "layperson_guide"
    guide_dir.mkdir(parents=True)
    md = guide_dir / "AS_TEST_LAYPERSON_GUIDE.md"
    md.write_text("x", encoding="utf-8")
    rel = fn(str(md), run_dir)
    assert rel == os.path.join("layperson_guide", "AS_TEST_LAYPERSON_GUIDE.md")
    assert "/Users/" not in rel and not os.path.isabs(rel)
