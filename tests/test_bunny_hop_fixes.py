"""test_bunny_hop_fixes.py — regression tests for the W9 follow-up + 60-file bunny-hop CHANGE fixes (v9.7.151).

Covers:
  - #9 (20-file) sapote_judgment_receipt regex extension + register path
  - #2 (60-file) evidence_ledgers pandas fallback
  - #3 (60-file) compilation_gate §1–§30 update (regex + threshold)
  - #14 (20-file) check_chatgpt_next_paths expanded GENERIC set
  - Other XS fixes (build_panel_figure, sapote_markers prov note)

All fixtures use AS-XXX. py_compile clean on every touched file.
"""
from __future__ import annotations

import builtins
import importlib
import importlib.util
import json
import pathlib
import sys

import pytest


def _load_tool(path: str):
    """Load a tools/ script as a module."""
    repo_root = pathlib.Path(__file__).resolve().parent.parent
    p = repo_root / path
    spec = importlib.util.spec_from_file_location(f"_tool_{p.stem}", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# 20-file #9 — sapote_judgment_receipt extended regex + register
# ---------------------------------------------------------------------------

def test_judgment_receipt_counts_legacy_card_heading(tmp_path):
    """Pre-W9 cards used `## BGC001` style headings. The fix must still
    count these — it extended the regex, not replaced it."""
    sjr = _load_tool("tools/sapote_judgment_receipt.py")
    f = tmp_path / "legacy.md"
    f.write_text("## BGC001 — NRPS\nstuff\n## BGC002 — PKS\nmore stuff\n")
    assert sjr.count_modeb_cards([str(f)]) == 2


def test_judgment_receipt_counts_w9_title(tmp_path):
    """W9 template emitter writes `# Mode B — BGC033 (NODE_7) — AS-XXX`
    as the card title. The pre-fix regex missed this entirely (single `#`
    + 'Mode B' between hash and BGC)."""
    sjr = _load_tool("tools/sapote_judgment_receipt.py")
    f = tmp_path / "w9.md"
    f.write_text("# Mode B — BGC033 (NODE_7) — AS-XXX\n## §1 Identity and node/region\nprose\n")
    assert sjr.count_modeb_cards([str(f)]) == 1


def test_judgment_receipt_counts_w9_persisted_header(tmp_path):
    """`mamey.judgment_store.record_mode_b` writes
    `<!-- MODE B: BGC001 | strain: ... | session: ... -->` at the top of
    every persisted card. The fix must count these too."""
    sjr = _load_tool("tools/sapote_judgment_receipt.py")
    f = tmp_path / "persisted.md"
    f.write_text("<!-- MODE B: BGC044 | strain: AS-XXX | session: s1 -->\n## §1 ...\n")
    assert sjr.count_modeb_cards([str(f)]) == 1


def test_judgment_receipt_dedupes_same_card_with_multiple_headers(tmp_path):
    """A single card carrying both the persisted comment header AND the
    title (the canonical post-record state) must count as ONE card, not
    two."""
    sjr = _load_tool("tools/sapote_judgment_receipt.py")
    f = tmp_path / "both.md"
    f.write_text(
        "<!-- MODE B: BGC055 | strain: AS-XXX | session: s1 -->\n"
        "# Mode B — BGC055 (NODE_3) — AS-XXX\n"
        "## §1 Identity and node/region\nprose\n"
    )
    assert sjr.count_modeb_cards([str(f)]) == 1


def test_judgment_receipt_register_path_reads_complete_bgcs(tmp_path):
    """When --register points at the package, the canonical
    `<strain>_judgment_register.json` `complete_bgcs` field is the
    source of truth."""
    sjr = _load_tool("tools/sapote_judgment_receipt.py")
    pkg = tmp_path / "AS-XXX" / "package"
    pkg.mkdir(parents=True)
    (pkg / "AS-XXX_judgment_register.json").write_text(
        json.dumps({"strain_id": "AS-XXX", "complete_bgcs": 7,
                    "total_bgcs": 12, "bgcs": {}})
    )
    complete, total = sjr.cards_from_register(str(pkg))
    assert complete == 7
    assert total == 12


def test_judgment_receipt_register_missing_returns_none(tmp_path):
    sjr = _load_tool("tools/sapote_judgment_receipt.py")
    pkg = tmp_path / "AS-XXX" / "package"
    pkg.mkdir(parents=True)
    complete, total = sjr.cards_from_register(str(pkg))
    assert complete is None
    assert total is None


# ---------------------------------------------------------------------------
# 60-file #2 — evidence_ledgers pandas fallback
# ---------------------------------------------------------------------------

def test_evidence_ledger_pandas_path_returns_dataframe():
    """The happy path: pandas available, returns a real DataFrame."""
    pd = pytest.importorskip("pandas")
    from mamey.mode_b.evidence_ledgers import build_evidence_ledger
    r = build_evidence_ledger([
        {"claim": "biosynthetic capacity consistent with NRPS",
         "evidence_type": "KCB", "strength": "B"},
    ])
    assert hasattr(r, "iloc"), "expected real pandas DataFrame in pandas path"
    assert len(r) == 1


def test_evidence_ledger_fallback_when_pandas_absent():
    """With pandas blocked at import time, the builders must NOT raise —
    they must return a _RowList fallback."""
    _real_import = builtins.__import__

    def _no_pandas(name, *args, **kwargs):
        if name == "pandas" or name.startswith("pandas."):
            raise ImportError("pandas blocked for this test")
        return _real_import(name, *args, **kwargs)

    # Snapshot cached pandas + the ledgers module so the import fires fresh,
    # and so we can restore the EXACT prior objects afterward (popping without
    # restoring leaves a stale entry; a later fresh `import pandas` then
    # creates a second, incompatible copy of pandas' compiled classes that
    # collides with the original copy other already-imported modules hold
    # references to -- see PATCH_TESTISOLATION_SYSMODULES_v9_7_154.md).
    _saved_modules = {
        k: sys.modules[k] for k in list(sys.modules)
        if k == "pandas" or k.startswith("pandas.")
        or k == "mamey.mode_b.evidence_ledgers"
    }
    for key in _saved_modules:
        sys.modules.pop(key, None)

    builtins.__import__ = _no_pandas
    try:
        mod = importlib.import_module("mamey.mode_b.evidence_ledgers")
        r = mod.build_evidence_ledger([
            {"claim": "biosynthetic capacity consistent with PKS",
             "evidence_type": "KCB"},
        ])
        assert isinstance(r, mod._RowList)
        assert len(r) == 1
        assert r[0]["claim"].startswith("biosynthetic capacity")
        assert r.columns[0] == "claim"
    finally:
        builtins.__import__ = _real_import
        # Restore the EXACT prior module objects (not just re-import) so
        # every already-imported module's bound `pandas` reference stays
        # consistent with sys.modules.
        sys.modules.pop("mamey.mode_b.evidence_ledgers", None)
        for k in [k for k in sys.modules if k == "pandas" or k.startswith("pandas.")]:
            sys.modules.pop(k, None)
        sys.modules.update(_saved_modules)


def test_user_action_queue_fallback_sorts_by_priority():
    """The sort_values pandas call must have a working fallback that
    still produces sorted output."""
    _real_import = builtins.__import__

    def _no_pandas(name, *args, **kwargs):
        if name == "pandas" or name.startswith("pandas."):
            raise ImportError("pandas blocked")
        return _real_import(name, *args, **kwargs)

    _saved_modules = {
        k: sys.modules[k] for k in list(sys.modules)
        if k == "pandas" or k.startswith("pandas.")
        or k == "mamey.mode_b.evidence_ledgers"
    }
    for key in _saved_modules:
        sys.modules.pop(key, None)

    builtins.__import__ = _no_pandas
    try:
        mod = importlib.import_module("mamey.mode_b.evidence_ledgers")
        q = mod.build_user_action_queue([
            {"priority": "C", "action": "z"},
            {"priority": "A", "action": "x"},
            {"priority": "B", "action": "y"},
        ])
        assert [r["priority"] for r in q] == ["A", "B", "C"]
    finally:
        builtins.__import__ = _real_import
        sys.modules.pop("mamey.mode_b.evidence_ledgers", None)
        for k in [k for k in sys.modules if k == "pandas" or k.startswith("pandas.")]:
            sys.modules.pop(k, None)
        sys.modules.update(_saved_modules)


# ---------------------------------------------------------------------------
# 60-file #3 — compilation_gate §1–§30 update
# ---------------------------------------------------------------------------

def test_compilation_gate_carded_ids_detects_legacy_heading():
    cg = _load_tool("tools/compilation_gate.py")
    md = "## BGC001 — NRPS\n### BGC002 — PKS\n"
    assert cg._carded_bgc_ids(md) == {"BGC001", "BGC002"}


def test_compilation_gate_carded_ids_detects_w9_title():
    """G2's _CARD_HEAD had to be extended to match the W9 single-`#`
    title format. Without this, a fully W9-compliant compendium would
    fail G2 with `0/N cards present`."""
    cg = _load_tool("tools/compilation_gate.py")
    md = "# Mode B — BGC033 (NODE_7) — AS-XXX\n## §1 Identity and node/region\n"
    assert cg._carded_bgc_ids(md) == {"BGC033"}


def test_compilation_gate_carded_ids_detects_w9_persisted_header():
    cg = _load_tool("tools/compilation_gate.py")
    md = "<!-- MODE B: BGC044 | strain: AS-XXX | session: s1 -->\n## §1 ...\n"
    assert cg._carded_bgc_ids(md) == {"BGC044"}


def test_compilation_gate_section_regex_covers_full_30():
    """Pre-fix the regex was `§\\s*(10|[1-9])(?!\\d)` — missed §11–§30
    entirely. The fix must accept any §1–§99."""
    cg = _load_tool("tools/compilation_gate.py")
    md = "§1 §10 §11 §20 §28 §30"
    found = cg._SECTION.findall(md)
    assert "1" in found
    assert "10" in found
    assert "11" in found
    assert "20" in found
    assert "28" in found
    assert "30" in found


def test_compilation_gate_g5_threshold_raised_for_w9():
    """G5's _MIN_SECTIONS_PER_CARD was 6 (appropriate for §1–§8). The
    W9 contract requires §1–§20 + §28 + §30 = 22 mandatory sections;
    floor raised to 18 (catches stub cards, tolerates conditional
    omissions of §21–§27/§29)."""
    cg = _load_tool("tools/compilation_gate.py")
    assert cg._MIN_SECTIONS_PER_CARD >= 18, (
        f"_MIN_SECTIONS_PER_CARD = {cg._MIN_SECTIONS_PER_CARD}; "
        f"too low for §1–§30 contract — a card with only §1–§17 would pass G5"
    )


def test_compilation_gate_g2_message_no_longer_says_section_1_to_8():
    """G2 docstring + error message must reflect §1–§30, not §1–§8."""
    repo_root = pathlib.Path(__file__).resolve().parent.parent
    body = (repo_root / "tools" / "compilation_gate.py").read_text(encoding="utf-8")
    # The G2 error string used to say "§1–§8" — must now say "§1–§30"
    assert "§1–§30" in body, "G2 contract update missing"


# ---------------------------------------------------------------------------
# 20-file #14 — check_chatgpt_next_paths expanded GENERIC set
# ---------------------------------------------------------------------------

def test_check_chatgpt_next_paths_generic_set_expanded():
    cnp = _load_tool("tools/check_chatgpt_next_paths.py")
    for word in ("execute", "perform", "build", "implement", "handle"):
        assert word in cnp.GENERIC, f"{word!r} missing from GENERIC filler set"


# ---------------------------------------------------------------------------
# 60-file #2 (efls.py) — orphan constant removed
# ---------------------------------------------------------------------------

def test_efls_no_orphan_forbidden_node_constant():
    """The pre-fix module top carried `FORBIDDEN_PRIMARY_BACKGROUND_NODES =
    {"NODE_11"}` with no readers. The strain-specific NODE_11 rule lives
    inside `forbidden_node_merge`
    and uses the literal inline. The orphan constant must be gone."""
    from mamey import efls
    assert not hasattr(efls, "FORBIDDEN_PRIMARY_BACKGROUND_NODES"), (
        "FORBIDDEN_PRIMARY_BACKGROUND_NODES is still defined at module top"
    )
    # The real rule still works
    assert efls.forbidden_node_merge("NODE_11", "NODE_96") is True
    assert efls.forbidden_node_merge("NODE_50", "NODE_96") is False


# ---------------------------------------------------------------------------
# 20-file #7 — dataclasses.replace
# ---------------------------------------------------------------------------

def test_directed_pks_runner_uses_dataclasses_replace():
    """Grep-level guard: the hand-rolled `type(spec)(study_id=..., ...)`
    pattern is gone, replaced with `dataclasses.replace`. Future fields
    added to DirectedPKSStudySpec will be preserved automatically."""
    repo_root = pathlib.Path(__file__).resolve().parent.parent
    body = (repo_root / "tools" / "run_directed_pks_study.py").read_text(encoding="utf-8")
    assert "dataclasses.replace" in body
    # The old hand-rolled reconstruction pattern is gone — check non-comment
    # lines only (the explanatory comment still mentions the historical form).
    code_only = "\n".join(
        line for line in body.splitlines() if not line.lstrip().startswith("#")
    )
    assert "type(spec)(" not in code_only, (
        "old hand-rolled reconstruction still present in code — fields "
        "could silently drop on a dataclass extension"
    )


# ---------------------------------------------------------------------------
# 60-file XS — build_panel_figure fails loudly
# ---------------------------------------------------------------------------

def test_build_panel_figure_fails_on_missing_panels():
    """Pre-fix: silent `return` (exit 0). Post-fix: sys.exit(1)."""
    repo_root = pathlib.Path(__file__).resolve().parent.parent
    body = (repo_root / "tools" / "build_panel_figure.py").read_text(encoding="utf-8")
    assert "sys.exit(1)" in body, (
        "build_panel_figure should sys.exit(1) on missing inputs, not "
        "return silently"
    )
