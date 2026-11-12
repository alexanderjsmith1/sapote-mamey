"""The compiled report says "no KCB hit" and "Dereplicate: no" only when KnownClusterBlast reported no hit.

A blank KCB top hit with KCB_evidence_state UNKNOWN_KCB means the comparison is not in the package.
The report used to write "no KCB hit" and "Dereplicate: no" for every blank.
"""
import csv
import inspect

from mamey import compile_report as CR
from mamey.missing_values import KCB_NO_HIT_STATES, kcb_evidence_states


def _inventory(tmp_path, rows, with_state=True):
    fields = ["BGC_ID", "KCB_top"] + (["KCB_evidence_state"] if with_state else [])
    with open(tmp_path / "S1_2_inventory.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for bgc, state in rows:
            row = {"BGC_ID": bgc, "KCB_top": ""}
            if with_state:
                row["KCB_evidence_state"] = state
            w.writerow(row)
    return tmp_path


def test_shared_reader(tmp_path):
    pkg = _inventory(tmp_path, [("BGC001", "knownclusterblast_no_hits_unvalidated"), ("BGC002", "")])
    assert kcb_evidence_states(pkg) == {"BGC001": "KNOWNCLUSTERBLAST_NO_HITS_UNVALIDATED", "BGC002": ""}
    assert "KNOWNCLUSTERBLAST_NO_HITS_UNVALIDATED" in KCB_NO_HIT_STATES
    assert kcb_evidence_states(tmp_path / "nowhere") is None


def test_states_map_to_text_and_dereplicate_value(tmp_path):
    pkg = _inventory(tmp_path, [("BGC001", "KNOWNCLUSTERBLAST_NO_HITS_UNVALIDATED"),
                                ("BGC002", "UNKNOWN_KCB"), ("BGC003", "CLUSTERBLAST_FALLBACK_OBSERVED")])
    states = CR._kcb_states(pkg)
    assert CR._kcb_absent(states, "BGC001") == ("no KCB hit reported", "no")
    assert CR._kcb_absent(states, "BGC002") == ("KCB comparison not in package", "unknown")
    assert CR._kcb_absent(states, "BGC003")[1] == "unknown"
    assert CR._kcb_absent(states, "BGC999") == ("KCB comparison not in package", "unknown")


def test_older_inventory_without_state_column(tmp_path):
    pkg = _inventory(tmp_path, [("BGC001", "")], with_state=False)
    assert CR._kcb_states(pkg) is None
    text, derep = CR._kcb_absent(None, "BGC001")
    assert derep == "unknown" and "not recorded" in text


def test_report_code_uses_the_state():
    src = inspect.getsource(CR)
    assert 'or "no KCB hit"' not in src
    assert 'else "no"\n' not in inspect.getsource(CR._decision_matrix)
