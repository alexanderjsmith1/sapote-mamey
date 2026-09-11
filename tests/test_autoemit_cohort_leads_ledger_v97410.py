"""v9.7.410: the cross-strain priority-leads ledger auto-emits from a multi-strain run.

Premise (verified on .409): ``mamey/cohort_leads_ledger.py`` was reachable ONLY through
the manual ``cohort-leads`` subcommand. The multi-strain auto-emit block in
``mamey.cli.run_batch`` (``if len(results) > 1:``) called ``build_cohort_figures``, the
gold F-series suite and the Figure Factory, but never the leads ledger -- so every
multi-strain run silently shipped without COHORT_PRIORITY_LEADS.csv.

These tests drive ``run_batch`` itself with ``run_one_strain`` stubbed to plant a sealed
triage board per strain (no antiSMASH input needed), and exercise the new helper
``_auto_emit_cohort_leads_ledger`` directly for the typed-skip contract.
"""
from __future__ import annotations

import csv
from pathlib import Path

import pytest

from mamey import cli
from mamey.cohort_leads_ledger import LEDGER_COLUMNS

# Reuse the vetted synthetic-package writer from the ledger's own unit tests.
from tests.test_cohort_leads_ledger import _row, _write_package


def _auto_emit_cohort_leads_ledger(*a, **k):
    # Resolved lazily so the run_batch tests below still COLLECT on an unpatched .409 and
    # fail on the missing CSV (the real gap) rather than on an import error.
    return cli._auto_emit_cohort_leads_ledger(*a, **k)


def _rows_a():
    return [
        _row("BGC001", "NODE_1", "region001", "PKS", "High", "50", "30", "kcbA1"),
        _row("BGC002", "NODE_2", "region001", "NRPS", "Exceptional", "80", "70", "kcbA2"),
        _row("BGC003", "NODE_3", "region001", "RiPP", "Medium", "40", "20"),
    ]


def _rows_b():
    return [
        _row("BGC010", "NODE_9", "region001", "PKS", "High", "60", "55", "kcbB1"),
        _row("BGC011", "NODE_8", "region001", "terpene", "Inventory", "10", "5"),
    ]


def _read_ledger(path: Path) -> tuple[list[str], list[dict]]:
    text = path.read_text(encoding="utf-8").splitlines()
    comments = [ln for ln in text if ln.startswith("#")]
    body = [ln for ln in text if not ln.startswith("#")]
    return comments, list(csv.DictReader(body))


def _stub_run_one_strain(outdir: Path, engine: str = "Mamey v1.9.118"):
    """Stand-in for run_one_strain: seal a tiny package with a triage board and return a
    minimal batch summary dict (the fields the batch footer prints)."""
    def _stub(strain_id, display_name, input_zip, outdir=outdir, **_kw):
        rows = _rows_a() if strain_id.endswith("001") else _rows_b()
        pkg = _write_package(str(outdir), strain_id, engine, rows)
        return {"strain_id": strain_id, "status": "sealed", "raw_bgcs": len(rows),
                "assembly_tier": "draft", "package_zip": str(Path(pkg) / f"{strain_id}.zip")}
    return _stub


def _run_two_strains(tmp_path: Path, monkeypatch, lines: list[str]) -> Path:
    outdir = tmp_path / "runs"
    outdir.mkdir()
    monkeypatch.setattr(cli, "run_one_strain", _stub_run_one_strain(outdir))
    # Keep the batch offline and fast: the figure bridge is not under test here.
    import mamey.cohort_figures as _cf
    monkeypatch.setattr(_cf, "build_cohort_figures",
                        lambda results, outdir, logger=None: {"status": "STUBBED", "figure_count": 0})
    monkeypatch.setattr(cli, "emit", lambda *a, **k: lines.append(" ".join(str(x) for x in a)))
    monkeypatch.delenv("MAMEY_FIGURE_FACTORY_CONFIG", raising=False)
    zips = [str(tmp_path / "AS_001.zip"), str(tmp_path / "AS_002.zip")]  # never opened by the stub
    results = cli.run_batch(zips, str(outdir), "gold", None, [], [])
    assert len(results) == 2
    return outdir


def test_two_strain_run_writes_the_ledger_csv(tmp_path: Path, monkeypatch) -> None:
    """FAIL-BEFORE on .409: run_batch never called the ledger, so this file did not exist."""
    lines: list[str] = []
    outdir = _run_two_strains(tmp_path, monkeypatch, lines)

    ledger = outdir / "COHORT_PRIORITY_LEADS.csv"
    assert ledger.is_file(), "multi-strain run must auto-emit COHORT_PRIORITY_LEADS.csv"

    comments, rows = _read_ledger(ledger)
    assert list(rows[0].keys()) == LEDGER_COLUMNS
    # Exceptional + High only, ranked tier-first then AF desc.
    assert [(r["strain"], r["BGC_ID"], r["Lead_tier_auto"]) for r in rows] == [
        ("AS_001", "BGC002", "Exceptional"),
        ("AS_002", "BGC010", "High"),
        ("AS_001", "BGC001", "High"),
    ]
    assert [r["Cohort_rank"] for r in rows] == ["1", "2", "3"]
    # No stray temp file left beside the crash-safe write.
    assert not (outdir / "COHORT_PRIORITY_LEADS.csv.tmp").exists()

    # One-line announcement in the batch log, in the bridge style.
    hits = [ln for ln in lines if "[cohort-leads-ledger]" in ln]
    assert hits and "3 Exceptional+High lead(s) across 2 strain(s)" in hits[0]
    assert str(ledger) in hits[0]
    # Single-engine cohort: no MIXED caution.
    assert not any("MIXED" in ln for ln in hits)
    assert any("single-engine cohort" in c for c in comments)


def test_ledger_is_claim_safe_prioritization_only(tmp_path: Path, monkeypatch) -> None:
    """The ledger carries capacity/routing columns only -- never product identity,
    production, or activity assertions -- and says so in its header."""
    lines: list[str] = []
    outdir = _run_two_strains(tmp_path, monkeypatch, lines)
    comments, rows = _read_ledger(outdir / "COHORT_PRIORITY_LEADS.csv")

    header = " ".join(comments).lower()
    assert "routing prior" in header
    assert "not a bioactivity/structure claim" in header
    forbidden = {"compound", "product", "produces", "active", "activity", "mic", "structure"}
    for col in LEDGER_COLUMNS:
        assert not any(tok in col.lower() for tok in forbidden), col


def test_single_strain_run_is_a_silent_no_op(tmp_path: Path, monkeypatch) -> None:
    lines: list[str] = []
    outdir = tmp_path / "runs"
    outdir.mkdir()
    monkeypatch.setattr(cli, "run_one_strain", _stub_run_one_strain(outdir))
    monkeypatch.setattr(cli, "emit", lambda *a, **k: lines.append(" ".join(str(x) for x in a)))
    cli.run_batch([str(tmp_path / "AS_001.zip")], str(outdir), "gold", None, [], [])
    assert not (outdir / "COHORT_PRIORITY_LEADS.csv").exists()
    assert not any("[cohort-leads-ledger]" in ln for ln in lines)


def test_helper_typed_skip_when_no_boards(tmp_path: Path) -> None:
    lines: list[str] = []
    res = _auto_emit_cohort_leads_ledger(tmp_path, logger=lines.append)
    assert res == {"status": "SKIPPED_NO_BOARDS", "n_leads": 0}
    assert not (tmp_path / "COHORT_PRIORITY_LEADS.csv").exists()
    assert lines == []


def test_helper_typed_skip_on_single_board(tmp_path: Path) -> None:
    _write_package(str(tmp_path), "AS_001", "Mamey v1.9.118", _rows_a())
    res = _auto_emit_cohort_leads_ledger(tmp_path, logger=lambda *_a: None)
    assert res == {"status": "SKIPPED_SINGLE_BOARD", "n_leads": 0}
    assert not (tmp_path / "COHORT_PRIORITY_LEADS.csv").exists()


def test_helper_mixed_engine_caution_and_determinism(tmp_path: Path) -> None:
    _write_package(str(tmp_path), "AS_001", "Mamey v1.9.118", _rows_a())
    _write_package(str(tmp_path), "AS_002", "Mamey v1.9.200", _rows_b())
    lines: list[str] = []
    first = _auto_emit_cohort_leads_ledger(tmp_path, logger=lines.append)
    assert first["status"] == "EMITTED" and first["mixed_engine"] is True
    assert any("[CLAIM-SAFETY] MIXED engine versions" in ln for ln in lines)
    ledger = tmp_path / "COHORT_PRIORITY_LEADS.csv"
    comments, _ = _read_ledger(ledger)
    assert any("MIXED ENGINE VERSIONS" in c for c in comments)
    # Deterministic re-emit over an existing file: byte-identical.
    before = ledger.read_bytes()
    second = _auto_emit_cohort_leads_ledger(tmp_path, logger=lambda *_a: None)
    assert second["status"] == "EMITTED"
    assert ledger.read_bytes() == before


def test_helper_never_raises(tmp_path: Path, monkeypatch) -> None:
    """A broken ledger module degrades to a typed, announced skip -- never a crash."""
    import mamey.cohort_leads_ledger as _cll
    _write_package(str(tmp_path), "AS_001", "Mamey v1.9.118", _rows_a())
    _write_package(str(tmp_path), "AS_002", "Mamey v1.9.118", _rows_b())

    def _boom(_runs):
        raise RuntimeError("synthetic ledger failure")
    monkeypatch.setattr(_cll, "build_ledger", _boom)
    lines: list[str] = []
    res = _auto_emit_cohort_leads_ledger(tmp_path, logger=lines.append)
    assert res == {"status": "SKIPPED_RuntimeError", "n_leads": 0}
    assert any("[cohort-leads-ledger] SKIPPED (RuntimeError" in ln for ln in lines)
    assert not (tmp_path / "COHORT_PRIORITY_LEADS.csv").exists()
