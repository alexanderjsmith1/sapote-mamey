"""v9.7.403 — cover the tree-overlay bottom-margin repair that FF402-PHYLO-LAYOUT-01 (R06) adds.

An independent review of the R06 packet reported that the new pre-gate margin-growth heuristic in
``tools/tree_bgc_overlay.py`` was unexercised: no test anywhere mentions ``bottom_margin``,
``lowest_tick_y``, or the refusal string. Grepping the test tree confirms that — but "no test
names it" is not the same as "no test runs it", and the stronger claim turned out to be wrong.
Measured on the shipped fixture, ``bottom_margin_fraction`` comes back at ~0.479 against a base
of 0.28/0.20, so the repair branch **already executes** inside
``test_hash_bound_tree_consumer_is_deterministic_vector_and_explicit``.

What is genuinely missing is an *assertion*: the repair runs unobserved, so it could silently stop
running — or start refusing figures that should render — without turning any test red. That is the
worse failure mode of the two, because the layout gate downstream would still report PASS on a
figure whose labels were never given room. And the refusal arm (``bottom_margin >= 0.80``) is
reached by nothing at all.

Both arms are reachable from the public API with fixture data alone, so this file locks them
without touching the renderer. Deliberately no exact-pixel expectations: the .402 seal was slowed
by a sibling test that asserted a raw pixel bound written for a ~150-DPI world and then went red
when the publication raster moved to 300 DPI. These assert *direction and bounds* instead.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")

from tests.test_tree_bgc_overlay import _fixture, _tsv, ov  # noqa: E402

# tools/tree_bgc_overlay.py: `bottom_margin = 0.28 if profile == "SINGLE_COLUMN" else 0.20`,
# and the repair refuses once the grown margin would reach 0.80 of the canvas.
BASE_MARGIN_MAX = 0.28
REFUSAL_CEILING = 0.80


def _rebind_annotations(config_path: Path, rows: list[list[object]]) -> Path:
    """Rewrite the annotation matrix and re-bind its hash, the way a real operator would.

    The consumer is hash-bound on purpose, so an edited input with a stale digest is refused
    before rendering — re-hashing here keeps the test exercising layout, not the hash guard.
    """
    config = json.loads(config_path.read_text(encoding="utf-8"))
    source = Path(config["external_data_root"])
    matrix = source / "annotations.tsv"
    _tsv(matrix, ["strain", "channel", "feature", "value", "state"], rows)
    digest = hashlib.sha256(matrix.read_bytes()).hexdigest()
    for row in config["inputs"]:
        if row["logical_locator"] == "annotations.tsv":
            row["sha256"] = digest
    config_path.write_text(json.dumps(config), encoding="utf-8")
    return config_path


def test_bottom_margin_repair_fires_and_is_recorded_in_the_layout(tmp_path: Path) -> None:
    """The rotated annotation-track tick labels need more room than the base margin gives, the
    renderer grows the margin to make it, and the grown value is recorded in the layout."""
    result = ov.build_publication(_fixture(tmp_path, "margin-repair"))
    assert result["profiles"], "fixture should render at least one profile"
    for profile in result["profiles"]:
        recorded = profile["layout"]["bottom_margin_fraction"]
        assert recorded > BASE_MARGIN_MAX, (
            f"{profile['profile']}: bottom_margin_fraction {recorded} did not grow past the base "
            f"{BASE_MARGIN_MAX} — the tick-label margin repair did not fire"
        )
        assert recorded < REFUSAL_CEILING, (
            f"{profile['profile']}: bottom_margin_fraction {recorded} reached the refusal ceiling "
            f"{REFUSAL_CEILING} on the ordinary fixture; the repair should leave data room"
        )
        # The repair must not be a substitute for the canonical clearance gate — both hold.
        assert profile["layout"]["tick_label_data_clearance"]["status"] == "PASS"


def test_margin_repair_converges_both_profiles_to_the_same_clearance(tmp_path: Path) -> None:
    """SINGLE_COLUMN starts at 0.28 and DOUBLE_COLUMN at 0.20, yet both are driven to the same
    grown margin: the repair targets a geometric clearance, not a per-profile constant. Locking
    this keeps a future edit from making the two profiles disagree about how much room a label
    needs, which would let one profile ship crowded while the other looked fine."""
    result = ov.build_publication(_fixture(tmp_path, "margin-converge"))
    margins = {p["profile"]: float(p["layout"]["bottom_margin_fraction"]) for p in result["profiles"]}
    assert len(margins) >= 2, f"expected both profiles, got {sorted(margins)}"
    assert max(margins.values()) - min(margins.values()) < 1e-6, (
        f"profiles disagree on the repaired margin: {margins}"
    )


def test_labels_too_tall_to_leave_data_height_are_refused_not_rendered(tmp_path: Path) -> None:
    """The refusal arm. When the labels cannot be given room without consuming the data
    rectangle, the renderer must refuse rather than emit a figure whose data area has been
    squeezed to nothing — a silently-tiny data rectangle is exactly the publication defect the
    R06 invariant exists to prevent, and it is far harder to notice than a crash."""
    config = _rebind_annotations(
        _fixture(tmp_path, "margin-refusal"),
        [
            ["strain-one", "ANI", "x" * 200, 94.1, "OBSERVED"],
            ["strain-two", "ANI", "x" * 200, 93.8, "OBSERVED"],
            ["strain-out", "ANI", "x" * 200, "", "NOT_APPLICABLE"],
        ],
    )
    with pytest.raises(ValueError, match="insufficient data height"):
        ov.build_publication(config)
