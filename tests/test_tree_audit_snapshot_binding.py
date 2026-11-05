import hashlib
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / 'tools'
sys.path.insert(0, str(TOOLS))
from tree_trust_audit import audit
from gate_snapshot_invocation import GATE_SHA256


def test_opt_in_native_gate_roster(tmp_path):
    gate = TOOLS / 'tree_sanity_check.py'
    assert hashlib.sha256(gate.read_bytes()).hexdigest() == GATE_SHA256
    (tmp_path / 'tree.nwk').write_text('((A:0.1,B:0.1):0.1,C_OUTGROUP:0.1);')
    (tmp_path / 'meta.tsv').write_text('tip\tlabel\nA\tA\nB\tB\nC_OUTGROUP\tC\n')
    entry = {'tree':'tree.nwk','metadata':'meta.tsv','outgroups':['C_OUTGROUP']}
    legacy = audit(entry,tmp_path,gate_path=gate)
    assert 'snapshot_gate_binding' not in legacy['checks']
    matching = audit(entry,tmp_path,gate_path=gate,snapshot_gate=True)
    assert matching['snapshot_gate_observation']['status'] == 'HOLD'
    assert matching['checks']['snapshot_gate_binding']['status'] == 'UNVERIFIED'
    entry['outgroups'] = ['B']
    mismatch = audit(entry,tmp_path,gate_path=gate,snapshot_gate=True)
    assert mismatch['snapshot_gate_observation']['status'] == 'MISMATCH'
    assert mismatch['checks']['snapshot_gate_binding']['status'] == 'FAIL'


def test_invalid_child_json_leaves_audit_unverified(tmp_path, monkeypatch):
    import subprocess
    from types import SimpleNamespace
    import gate_snapshot_invocation
    gate = TOOLS / 'tree_sanity_check.py'
    (tmp_path/'tree.nwk').write_text('((A:0.1,B:0.1):0.1,C_OUTGROUP:0.1);')
    (tmp_path/'meta.tsv').write_text('tip\tlabel\nA\tA\nB\tB\nC_OUTGROUP\tC\n')
    entry={'tree':'tree.nwk','metadata':'meta.tsv','outgroups':['C_OUTGROUP']}
    original=subprocess.run
    def simulated_child(command, *args, **kwargs):
        if len(command)>1 and Path(command[1]).name == 'gate_structured_snapshot.py':
            return SimpleNamespace(stdout=b'[]',stderr=b'',returncode=0)
        return original(command,*args,**kwargs)
    monkeypatch.setattr(gate_snapshot_invocation.subprocess,'run',simulated_child)
    row=audit(entry,tmp_path,gate_path=gate,snapshot_gate=True)
    assert row['snapshot_gate_observation']['status'] == 'ERROR'
    assert row['checks']['snapshot_gate_binding']['status'] == 'UNVERIFIED'
    assert row['verdict'] == 'UNVERIFIED'


def test_opt_in_rejects_oversized_tree_before_native_gate(tmp_path):
    tree=tmp_path/'large.nwk'
    with tree.open('wb') as handle: handle.truncate(8 * 1024 * 1024 + 1)
    (tmp_path/'meta.tsv').write_text('tip\tlabel\nA\tA\n')
    row=audit({'tree':'large.nwk','metadata':'meta.tsv','outgroups':['A']},tmp_path,gate_path=TOOLS/'tree_sanity_check.py',snapshot_gate=True)
    assert row['checks']['tree']['status'] == 'FAIL'
    assert '8 MiB' in row['checks']['tree']['detail']
    assert 'gate_exit' not in row
    assert row['checks']['snapshot_gate_binding']['status'] == 'UNVERIFIED'


def test_deep_tree_is_reported_instead_of_crashing(tmp_path):
    deep='('*1500 + 'A:0.1' + '):0.1'*1500 + ';'
    (tmp_path/'deep.nwk').write_text(deep)
    (tmp_path/'meta.tsv').write_text('tip\tlabel\nA\tA\n')
    entry={'tree':'deep.nwk','metadata':'meta.tsv','outgroups':['A']}
    row=audit(entry,tmp_path,gate_path=TOOLS/'tree_sanity_check.py',snapshot_gate=True)
    assert row['checks']['tree']['status'] == 'FAIL'
    assert 'recursion' in row['checks']['tree']['detail'].lower()
    assert 'gate_exit' not in row
