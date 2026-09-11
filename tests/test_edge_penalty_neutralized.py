"""AMBER_07 (v9.7.349): lock in the fragment-surfacing invariant — edge_penalty == 0.

Since v9.7.84 the edge/full-contig penalty is NEUTRALIZED to zero: it had no measurement basis
(Edge/FC BGCs show no truncation signature in their base score) and had buried real high-value
fragments (e.g. selvamicin BGC0001773, a Full-contig attine antifungal polyene). Truncation
uncertainty is preserved as a CONFIDENCE signal, not a score penalty, and RG-GMCI raises priority for
fragmented regions. This project SURFACES fragments; it does not penalise them.

This guard fails the moment a future cut silently reintroduces a boundary-status score penalty. If a
calibrated, outcome-grounded penalty is ever deliberately reintroduced, update this test in the same
change (so the reintroduction is explicit and reviewed), never silently.
"""
from mamey.scoring import edge_penalty


def test_edge_penalty_is_zero_for_every_status():
    for status in ("Interior", "Edge", "Full-contig", "Unknown", "", "anything-else", None):
        assert edge_penalty(status) == 0.0, (
            f"edge_penalty({status!r}) must be 0.0 — the fragment-surfacing invariant "
            f"(neutralised in v9.7.84) has regressed; a blanket boundary penalty is back.")


def test_no_boundary_status_changes_the_penalty():
    # all statuses return the identical value (no relative penalty between boundary classes)
    vals = {edge_penalty(s) for s in ("Interior", "Edge", "Full-contig", "Unknown")}
    assert vals == {0.0}
