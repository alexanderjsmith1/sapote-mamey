"""RAZZLE_416 — the canonical-deliverable guard only recognised UNDERSCORE-dated folders.

`DATED_DIR_RE` was `.*_\\d{4}-\\d{2}-\\d{2}$`, but this project names deliverable folders with a
space or a hyphen just as often. Measured over the workspace: 1,589 date-suffixed folders, 25 of
them invisible to the underscore-only pattern (13 space-separated, 10 hyphen-separated, 2 bare).
On those the guard silently no-opped -- the exact silent degradation it exists to stop.

Scope note: this widens the SEPARATOR only. A bare date stays OUT deliberately;
tests/test_canonical_write_guard_v97413.py pins ("2026-08-05", False) and is right to, since both
bare-date folders here are backup dirs, not deliverables.
"""
import pytest

from mamey import canonical_write_guard as g


@pytest.mark.parametrize("folder,expected", [
    # the separators that were missing -- drawn from real folder names in this workspace
    ("BGC Cohort Standout Roundups 2026-08-02", True),
    ("BLASTp FASTA sets 2026-07-28", True),  # NB: avoid the substring "figure" (conftest auto-skips by name)
    ("Gap Audit 2026-07-28", True),
    ("sapote-mamey-repo-v9_3-2026-06-09", True),
    ("sapote-mamey-v9_4_1-B2phase1-2026-06-10", True),
    # unchanged behaviour
    ("whole_bgc_majority_read_2026-08-05", True),
    ("flagged_lead_surfacing_2026-08-05", True),
    ("2026-08-05", False),           # bare date stays out, by standing contract
    ("report_2026_08_05", False),    # not an ISO date
    ("run-2026-06-09-scratch", False),  # date not at the end
    ("runs", False),
])
def test_dated_folder_predicate_covers_every_separator(tmp_path, folder, expected):
    assert g.is_canonical_dated_path(tmp_path / folder / "file.md") is expected


def test_space_dated_deliverable_is_actually_protected(tmp_path):
    d = tmp_path / "BGC Cohort Standout Roundups 2026-08-02"
    d.mkdir(parents=True)
    f = d / "roundup.csv"
    f.write_text("existing", encoding="utf-8")
    with pytest.raises(g.CanonicalOverwriteRefused):
        g.guard_canonical_write(f)


def test_the_escape_hatches_still_work(tmp_path, monkeypatch):
    d = tmp_path / "Gap Audit 2026-07-28"
    d.mkdir(parents=True)
    f = d / "x.md"
    f.write_text("x", encoding="utf-8")
    g.guard_canonical_write(f, force=True)          # explicit --force
    monkeypatch.setenv(g.ENV_ALLOW, "1")
    g.guard_canonical_write(f)                       # env escape hatch


def test_a_new_file_in_a_space_dated_folder_is_still_allowed(tmp_path):
    d = tmp_path / "Gap Audit 2026-07-28"
    d.mkdir(parents=True)
    g.guard_canonical_write(d / "brand_new.md")      # first write must not be refused
