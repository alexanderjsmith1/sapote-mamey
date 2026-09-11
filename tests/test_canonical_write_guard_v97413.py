"""v9.7.413 (BC2) — the canonical-overwrite guard.

Behavioural contract for `mamey/canonical_write_guard.py`. The guard exists because a per-command
`--out` flag fixes one command at a time while the next one-off script repeats the same mistake;
see the module docstring for the incident that motivated it.

The tests pin BOTH directions deliberately — a guard that fires on correct usage is worse than no
guard, because it trains people to disable it.
"""
import os

import pytest

from mamey import canonical_write_guard as g


# ---- fires (the observed failure mode) -------------------------------------------------------

def test_refuses_overwriting_an_existing_dated_deliverable(tmp_path):
    d = tmp_path / "strain_data" / "flagged_lead_surfacing_2026-08-05"
    d.mkdir(parents=True)
    f = d / "FLAGGED_LEAD_SURFACING.md"
    f.write_text("real deliverable", encoding="utf-8")
    with pytest.raises(g.CanonicalOverwriteRefused) as exc:
        g.guard_canonical_write(f)
    # the refusal must tell the operator how to proceed, not just say no
    msg = str(exc.value)
    assert "--out" in msg and "--force" in msg


def test_fires_for_nested_files_inside_a_dated_folder(tmp_path):
    d = tmp_path / "modeb_compilation_2026-08-05" / "sub"
    d.mkdir(parents=True)
    f = d / "AS-000_ModeB_compilation.md"
    f.write_text("x", encoding="utf-8")
    with pytest.raises(g.CanonicalOverwriteRefused):
        g.guard_canonical_write(f)


# ---- does NOT fire (everything legitimate) ---------------------------------------------------

def test_allows_creating_a_new_file_in_a_dated_folder(tmp_path):
    """First-time generation in a fresh workspace must not be blocked."""
    d = tmp_path / "flagged_lead_surfacing_2026-08-05"
    d.mkdir(parents=True)
    g.guard_canonical_write(d / "does_not_exist_yet.md")  # must not raise


def test_allows_overwriting_outside_a_dated_folder(tmp_path):
    f = tmp_path / "scratch" / "output.md"
    f.parent.mkdir(parents=True)
    f.write_text("x", encoding="utf-8")
    g.guard_canonical_write(f)  # must not raise


def test_force_overrides(tmp_path):
    d = tmp_path / "flagged_lead_surfacing_2026-08-05"
    d.mkdir(parents=True)
    f = d / "x.md"
    f.write_text("x", encoding="utf-8")
    g.guard_canonical_write(f, force=True)  # must not raise


def test_env_escape_hatch_overrides(tmp_path, monkeypatch):
    d = tmp_path / "flagged_lead_surfacing_2026-08-05"
    d.mkdir(parents=True)
    f = d / "x.md"
    f.write_text("x", encoding="utf-8")
    monkeypatch.setenv(g.ENV_ALLOW, "1")
    g.guard_canonical_write(f)  # must not raise


# ---- the dated-folder predicate itself -------------------------------------------------------

@pytest.mark.parametrize("folder,expected", [
    ("flagged_lead_surfacing_2026-08-05", True),
    ("modeb_compilation_2026-08-05", True),
    ("whole_bgc_majority_read_2026-08-05", True),
    ("_AF_LEADS_2026-08-05", True),
    ("runs", False),
    ("AS-747", False),
    ("plots", False),          # NB: avoid the substring "figure" — conftest auto-skips by test name
    ("package", False),
    ("2026-08-05", False),          # bare date, no underscore-prefixed name
    ("report_2026_08_05", False),   # underscores, not a real ISO date
])
def test_dated_folder_predicate(tmp_path, folder, expected):
    p = tmp_path / folder / "file.md"
    assert g.is_canonical_dated_path(p) is expected
