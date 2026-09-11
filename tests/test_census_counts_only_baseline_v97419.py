"""v9.7.419 — a census baseline without nodeid lists must still catch a drop.

The full census embeds every selected nodeid: ~1 MB per cut on v9.7.418 (10,148 nodeids),
of which the counts a drop-check actually needs are ~356 bytes. Tracking the small form per
cut is attractive, but before this change `--against` subscripted `prev["selected_nodeids"]`
directly, so a counts-only baseline raised KeyError and the whole census failed (exit 2).

Degrading gracefully is only safe if the counts are compared. Otherwise a counts-only
baseline would report PASS on a real drop with an empty removed-set — the silent pass this
gate exists to prevent. These tests pin both halves.

Composed with execution-delta accounting, which touches the same block and adds
the `concerns` list; the count drop is reported there rather than in a separate key.
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))

import suite_count_census as scc


def _baseline(tmp_path, now, *, with_nodeids, bump=0):
    data = {k: v for k, v in now.items() if with_nodeids or not k.endswith("nodeids")}
    data["collected"] = now["collected"] + bump
    data["selected"] = now["selected"] + bump
    path = tmp_path / f"base_{with_nodeids}_{bump}.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def _run(scope, against):
    return scc.main(["--tests", scope, "--against", str(against)])


SCOPE = "tests/test_census_counts_only_baseline_v97419.py"


def test_counts_only_baseline_is_accepted(tmp_path, capsys):
    now = scc.census([SCOPE])
    rc = _run(SCOPE, _baseline(tmp_path, now, with_nodeids=False))
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out["status"] == "PASS"
    assert out["nodeid_diff"] == "unavailable_baseline_has_no_nodeids"


def test_counts_only_baseline_still_catches_a_drop(tmp_path, capsys):
    """The load-bearing case: no nodeids to diff, so the COUNTS must fire."""
    now = scc.census([SCOPE])
    rc = _run(SCOPE, _baseline(tmp_path, now, with_nodeids=False, bump=5))
    out = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert out["status"] == "REVIEW_REQUIRED"
    assert any(c.startswith("COLLECTED_DROPPED:") for c in out["concerns"]), out["concerns"]


def test_full_baseline_still_reports_the_nodeid_diff(tmp_path, capsys):
    now = scc.census([SCOPE])
    rc = _run(SCOPE, _baseline(tmp_path, now, with_nodeids=True))
    out = json.loads(capsys.readouterr().out)
    assert rc == 0 and out["nodeid_diff"] == "available"
