"""B4_Cross_Strain_Scans.KCB_status must be the KCB_sweep state the run recorded, not a literal PASS."""
import inspect
from types import SimpleNamespace

from mamey import master_workbook as MW


def _run(scans):
    return SimpleNamespace(scan_status={"scans": scans})


def test_recorded_states_pass_through():
    for state in ("PASS", "NULL", "FAILED"):
        run = _run([("RG_GMCI", "PASS", ""), ("KCB_sweep", state, "detail")])
        assert MW._kcb_sweep_state(run) == state


def test_missing_state_is_not_pass():
    assert MW._kcb_sweep_state(_run([("RG_GMCI", "PASS", "")])) == "NOT_RECORDED"
    assert MW._kcb_sweep_state(SimpleNamespace()) == "NOT_RECORDED"
    assert MW._kcb_sweep_state(SimpleNamespace(scan_status=None)) == "NOT_RECORDED"


def test_b4_row_uses_the_recorded_state():
    src = inspect.getsource(MW)
    assert '"KCB_status": _kcb_sweep_state(run)' in src
    assert '"KCB_status": "PASS"' not in src
