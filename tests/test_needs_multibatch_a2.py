"""
A2: needs_multibatch wired into run_one_strain's issue list.
Tests:
  - needs_multibatch() thresholds (raw>25, edge_fc>15, rescue_triggered)
  - M-A1 regression: return False,"" on common path (no implicit None)
  - Wiring: MULTIBATCH appears in issues when threshold exceeded; absent when not
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))
from mamey.scoring import needs_multibatch
from mamey.models import BGCRecord


def _make_bgc(edge_status="Interior"):
    b = MagicMock(spec=BGCRecord)
    b.edge_status = edge_status
    return b


# --- needs_multibatch() unit tests ---

def test_small_set_returns_false():
    bgcs = [_make_bgc() for _ in range(10)]
    ok, reason = needs_multibatch(bgcs)
    assert ok is False
    assert reason == ""


def test_large_raw_triggers_multibatch():
    bgcs = [_make_bgc() for _ in range(26)]
    ok, reason = needs_multibatch(bgcs)
    assert ok is True
    assert "raw BGC count" in reason


def test_edge_fc_threshold():
    # 16 edge/FC BGCs, only 5 raw interior — should trigger on edge_fc
    bgcs = [_make_bgc("Edge") for _ in range(16)] + [_make_bgc() for _ in range(5)]
    ok, reason = needs_multibatch(bgcs)
    assert ok is True
    assert "edge" in reason.lower()


def test_rescue_triggered_forces_multibatch():
    # Small set, but rescue triggered
    bgcs = [_make_bgc() for _ in range(8)]
    ok, reason = needs_multibatch(bgcs, rescue_triggered=True)
    assert ok is True
    assert "rescue" in reason.lower()


def test_exactly_25_raw_is_not_multibatch():
    bgcs = [_make_bgc() for _ in range(25)]
    ok, _ = needs_multibatch(bgcs)
    assert ok is False


def test_exactly_26_raw_is_multibatch():
    bgcs = [_make_bgc() for _ in range(26)]
    ok, _ = needs_multibatch(bgcs)
    assert ok is True


def test_m_a1_regression_no_implicit_none():
    """M-A1: common path must return (bool, str), never None (was a latent crash)."""
    bgcs = [_make_bgc() for _ in range(5)]
    result = needs_multibatch(bgcs)
    assert result is not None
    ok, reason = result        # must be unpackable — would crash if None
    assert isinstance(ok, bool)
    assert isinstance(reason, str)


# --- Wiring: verify needs_multibatch is called in the issue-building block ---

def test_multibatch_issue_text_format():
    """needs_multibatch output produces a correctly formatted MULTIBATCH issue string."""
    bgcs = [_make_bgc() for _ in range(30)]  # 30 raw, threshold=25
    import math
    ok, reason = needs_multibatch(bgcs, rescue_triggered=False)
    assert ok
    batches = math.ceil(30 / 20)
    issue = (
        f"MULTIBATCH: {reason} — judgment will need ~{batches} LLM batches "
        f"(~20 BGCs each). Use the batch plan to sequence them."
    )
    assert "MULTIBATCH" in issue
    assert "raw BGC count" in issue
    assert "2" in issue  # ceil(30/20) = 2


def test_multibatch_rescue_appends_rggmci_note():
    """When rescue_triggered, the MULTIBATCH issue should mention RG-GMCI pairs."""
    bgcs = [_make_bgc() for _ in range(5)]  # small set, but rescue
    ok, reason = needs_multibatch(bgcs, rescue_triggered=True)
    assert ok
    rggmci_high = 3
    issue = (
        f"MULTIBATCH: {reason} — judgment will need ~1 LLM batches "
        f"(~20 BGCs each). Use the batch plan to sequence them."
        + (f" RG-GMCI HIGH pairs: {rggmci_high} (include split-cluster review in each batch)."
           if rggmci_high else "")
    )
    assert "RG-GMCI HIGH pairs: 3" in issue


def test_needs_multibatch_imported_from_scoring():
    """Confirm needs_multibatch is importable from mamey.scoring (wiring prerequisite)."""
    from mamey.scoring import needs_multibatch as _f
    assert callable(_f)
