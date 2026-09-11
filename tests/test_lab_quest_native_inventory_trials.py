import csv
import json
import pytest
from mamey import lab_quest


def package(tmp_path, monkeypatch, change=None, target='inventory'):
    monkeypatch.setattr(lab_quest, 'validate_package', lambda *a, **k: {'status': 'PASS'})
    (tmp_path/'manifest.json').write_text(json.dumps({'strain_id':'TEST-01'}))
    (tmp_path/'TEST-01_1_intake.json').write_text('{}')
    row={'BGC_ID':'BGC001','Contig':'NODE_1_length_12345_cov_20.5','Node_ID':'NODE_1_length_12345_cov_20','Region':'1','antiSMASH_Region':'region001'}
    for role, suffix in [('inventory','2_inventory'),('triage','4_triage_board')]:
        data=dict(row)
        if role==target and change: data.update(change)
        with (tmp_path/f'TEST-01_{suffix}.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(data));w.writeheader();w.writerow(data)
    return tmp_path


def test_native_inventory_snapshot(tmp_path, monkeypatch):
    snap=lab_quest.load_package_snapshot(package(tmp_path,monkeypatch))
    expected='TEST-01 / NODE_1_length_12345_cov_20.5 / region001 / BGC001'
    assert snap.inventory[0]['exact_locus']==expected
    assert snap.triage[0]['exact_locus']==expected


@pytest.mark.parametrize('change',[{'Node_ID':'NODE_2'}, {'Region':'2'}, {'Contig':''}, {'Full_Node_ID':'NODE_2_length_12345_cov_20.5'}])
def test_native_identity_conflicts_refused(tmp_path,monkeypatch,change):
    with pytest.raises(ValueError):
        lab_quest.load_package_snapshot(package(tmp_path,monkeypatch,change))


def test_triage_locus_disagrees_with_inventory(tmp_path,monkeypatch):
    with pytest.raises(ValueError):
        lab_quest.load_package_snapshot(package(tmp_path,monkeypatch,{'Contig':'NODE_2_length_12345_cov_20.5','Node_ID':'NODE_2_length_12345_cov_20'},'triage'))
