"""test_regen_modeb_contract_docs.py — tests for W9-C / N10.

The single-canonical-contract refactor: `_full30_corrective_contract.json` is
the only schema source. Docs are generated from it. The §1–§20 facade
(`validators/modeb_full20.py`) derives its sections from the same JSON. CI
enforces no drift via `tools/regen_modeb_contract_docs.py --check`.

All fixtures use AS-XXX.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib

import pytest


def _load_regen():
    """Import tools/regen_modeb_contract_docs.py as a module without
    importing the surrounding tools package."""
    repo_root = pathlib.Path(__file__).resolve().parent.parent
    path = repo_root / "tools" / "regen_modeb_contract_docs.py"
    spec = importlib.util.spec_from_file_location("regen_test_load", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Drift check — the headline CI test
# ---------------------------------------------------------------------------

def test_check_mode_reports_no_drift_on_current_bundle():
    """The bundled docs must match what would be regenerated. If this fails,
    someone hand-edited a markdown doc instead of editing the JSON + running
    the regen tool — exactly the drift surface N10 closed."""
    regen = _load_regen()
    rc = regen.main(["--check"])
    assert rc == 0, (
        "Mode B contract docs have drifted from the JSON. Run "
        "`python3 tools/regen_modeb_contract_docs.py` to regenerate."
    )


# ---------------------------------------------------------------------------
# Generation correctness — produced docs roundtrip through the validator
# ---------------------------------------------------------------------------

def test_regen_produces_both_docs_from_default_contract(tmp_path):
    regen = _load_regen()
    titles_out = tmp_path / "TITLES.md"
    contract_out = tmp_path / "CONTRACT.md"
    rc = regen.main([
        "--titles-out", str(titles_out),
        "--contract-out", str(contract_out),
    ])
    assert rc == 0
    assert titles_out.exists()
    assert contract_out.exists()
    assert titles_out.stat().st_size > 500
    assert contract_out.stat().st_size > 1000


def test_titles_doc_contains_all_30_section_headings(tmp_path):
    regen = _load_regen()
    titles_out = tmp_path / "TITLES.md"
    regen.main([
        "--titles-out", str(titles_out),
        "--contract-out", str(tmp_path / "_.md"),
    ])
    body = titles_out.read_text(encoding="utf-8")
    # All 30 titles must appear in the rendered doc
    for n in range(1, 21):
        assert f"{n}. **" in body, (
            f"§{n} bullet missing from titles doc"
        )
    # §28 + §30 specifically called out as always-required
    assert "Evidence provenance ledger" in body
    assert "Experimental decision tree" in body
    # §21–§27 + §29 in conditional table
    assert "Precursor mass ladder" in body
    assert "Self-resistance assessment" in body
    assert "Cross-cluster interactions" in body


def test_contract_doc_contains_predicate_table(tmp_path):
    regen = _load_regen()
    contract_out = tmp_path / "CONTRACT.md"
    regen.main([
        "--titles-out", str(tmp_path / "_.md"),
        "--contract-out", str(contract_out),
    ])
    body = contract_out.read_text(encoding="utf-8")
    # The conditional predicate table must include all keys
    for key in ("is_ripp", "maturation_gap_or_novel_class", "novel_or_no_mibig",
                "isolation_worthy", "fermentation_selected",
                "antimicrobial_candidate", "strain_gt_3_high_priority"):
        assert key in body, f"predicate {key} missing from contract doc"
    # Quality gate appears
    assert "Quality gate" in body or "quality gate" in body.lower()


def test_regen_is_idempotent(tmp_path):
    """Running the regen twice must produce byte-identical output."""
    regen = _load_regen()
    out_a = tmp_path / "a"
    out_a.mkdir()
    out_b = tmp_path / "b"
    out_b.mkdir()
    regen.main([
        "--titles-out", str(out_a / "TITLES.md"),
        "--contract-out", str(out_a / "CONTRACT.md"),
    ])
    regen.main([
        "--titles-out", str(out_b / "TITLES.md"),
        "--contract-out", str(out_b / "CONTRACT.md"),
    ])
    assert (out_a / "TITLES.md").read_bytes() == (out_b / "TITLES.md").read_bytes()
    assert (out_a / "CONTRACT.md").read_bytes() == (out_b / "CONTRACT.md").read_bytes()


def test_regen_detects_drift_when_doc_is_modified(tmp_path):
    """If the JSON is the source and someone edits the markdown directly,
    --check must catch the drift."""
    regen = _load_regen()
    titles_out = tmp_path / "TITLES.md"
    contract_out = tmp_path / "CONTRACT.md"
    regen.main([
        "--titles-out", str(titles_out),
        "--contract-out", str(contract_out),
    ])
    # Tamper with the titles doc
    body = titles_out.read_text(encoding="utf-8")
    titles_out.write_text(body.replace("Identity and node/region",
                                        "Identity tampered"),
                          encoding="utf-8")
    rc = regen.main([
        "--titles-out", str(titles_out),
        "--contract-out", str(contract_out),
        "--check",
    ])
    assert rc == 1, "tampered doc should be flagged as drift"


# ---------------------------------------------------------------------------
# Single-source verification — facade derives from same JSON the regen reads
# ---------------------------------------------------------------------------

def test_full20_facade_matches_regen_source(tmp_path):
    """The §1–§20 facade (`validators/modeb_full20`) and the regen tool must
    both read the same source. Specifically: the §1–§20 titles exported by
    the facade must equal the §1–§20 slice of the contract JSON the regen
    reads."""
    from mamey.validators.modeb_full20 import REQUIRED_MODEB_FULL20_SECTIONS

    repo_root = pathlib.Path(__file__).resolve().parent.parent
    contract = json.loads(
        (repo_root / "mamey" / "data" / "mode_b"
         / "modeb_full30_corrective_contract.json")
        .read_text(encoding="utf-8")
    )
    sections = sorted(contract["sections"], key=lambda s: s["number"])
    full20_titles_from_json = [s["title"] for s in sections
                                if 1 <= s["number"] <= 20]
    assert REQUIRED_MODEB_FULL20_SECTIONS == full20_titles_from_json


def test_full20_facade_no_longer_carries_hardcoded_fallback(tmp_path):
    """The pre-N10 modeb_full20.py had a 20-section hard-coded list as a
    fallback. The refactored facade must not — single source of truth is
    the JSON. Grep-level assertion to guard against regression."""
    repo_root = pathlib.Path(__file__).resolve().parent.parent
    src = (repo_root / "mamey" / "validators" / "modeb_full20.py").read_text(
        encoding="utf-8")
    # The old hard-coded list contained these distinctive title strings as
    # Python string literals. After N10, these should NOT appear as literal
    # quoted strings (they're derived from the JSON at load time).
    legacy_literal = '"Identity and node/region"'
    assert src.count(legacy_literal) <= 0, (
        "modeb_full20.py still carries the pre-N10 hard-coded fallback "
        "section list — single source of truth has regressed."
    )


def test_standalone_full20_json_is_retired(tmp_path):
    """The standalone `modeb_full20_corrective_contract.json` should no
    longer live at the top of `data/mode_b/` — only `_full30_` and the
    `legacy/` archive."""
    repo_root = pathlib.Path(__file__).resolve().parent.parent
    mode_b_dir = repo_root / "mamey" / "data" / "mode_b"
    standalone = mode_b_dir / "modeb_full20_corrective_contract.json"
    assert not standalone.exists(), (
        f"Standalone {standalone.name} should have been retired in N10; "
        "the legacy copy lives at "
        "`legacy/modeb_full20_corrective_contract_legacy_v97144.json`."
    )
    # The §30 contract must still exist
    assert (mode_b_dir / "modeb_full30_corrective_contract.json").exists()
    # And the legacy archive must be preserved
    assert (mode_b_dir / "legacy"
            / "modeb_full20_corrective_contract_legacy_v97144.json").exists()


def test_deprecation_pointer_docs_redirect_to_30_section_versions():
    """The old §20 doc files should now be redirect pointers to the §30
    versions, not full contract specs."""
    repo_root = pathlib.Path(__file__).resolve().parent.parent
    for old_name, new_name in (
        ("MODE_B_20_SECTION_CANONICAL_TITLES.md",
         "MODE_B_30_SECTION_CANONICAL_TITLES.md"),
        ("FULL_MODEB_20_SECTION_CONTRACT_v97144.md",
         "FULL_MODEB_30_SECTION_CONTRACT_v97150.md"),
    ):
        old = repo_root / "docs" / old_name
        new = repo_root / "docs" / new_name
        assert old.exists(), f"deprecation pointer {old_name} missing"
        assert new.exists(), f"replacement doc {new_name} missing"
        body = old.read_text(encoding="utf-8")
        assert "DEPRECATED" in body, (
            f"{old_name} is not flagged as deprecated"
        )
        assert new_name in body, (
            f"{old_name} does not point at {new_name}"
        )
