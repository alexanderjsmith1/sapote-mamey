"""The stop guard's header (copied into the tools inventory) describes the burst rule it implements."""
from pathlib import Path

GUARD = Path(__file__).resolve().parents[1] / "tools" / "blastp_monitoring" / "blastp_stop_guard.sh"


def test_header_states_burst_threshold_not_single_row():
    head = "\n".join(GUARD.read_text().splitlines()[:12])
    assert "failure-status ledger row, OR" not in head
    assert "FAIL_THRESHOLD" in head and "FAIL_WINDOW_H" in head
    assert "lone expired or failed RID" in head
