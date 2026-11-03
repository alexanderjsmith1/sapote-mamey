"""Reporting-only controls; real admission, stubbed extraction and JSON writers."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import pytest
TARGET=Path(__file__).resolve().parents[1]/'tools/build_deep_data.py'
spec=importlib.util.spec_from_file_location('deep_report_candidate',TARGET);tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(tool)

@pytest.mark.parametrize('modes',[['absent'],['off'],['bounded'],['full'],['absent','off','bounded','full']])
def test_mode_counts_and_unchanged_data_choices(tmp_path,monkeypatch,modes):
    from mamey import gold_bgc_identity
    bank=tmp_path/'bank';bank.mkdir();snaps={};retained=[]
    for i,mode in enumerate(modes):
        sid='SOFTWARE_'+str(i);package=tmp_path/sid;package.mkdir();snap=package/'snapshot.json';snap.write_text(json.dumps({'source_scans':{}}));snaps[sid]=str(snap)
        retained.append({'sid':sid,'software':'retained'})
        if mode!='absent':(package/'SOFTWARE_AntiSMASH_Evidence_Parse.json').write_text(json.dumps({'json_mode':mode}))
    (bank/'bgc_data.json').write_text(json.dumps({'strains':{sid:{} for sid in snaps}}))
    (bank/'deep_data.json').write_text(json.dumps({'bgc_profile':[],'domain_hits':[],'active_sites':retained,'class_pred':[]}))
    (bank/'gene_data.json').write_text(json.dumps({'domain_arch':[],'substrates':retained,'ripp':[]}))
    monkeypatch.setattr(tool,'find_snaps',lambda:snaps)
    monkeypatch.setattr(tool,'extract',lambda *a,**k:([],[],[]))
    calls=[];monkeypatch.setattr(tool,'extract_finer',lambda sid,snap,e:calls.append((sid,e)) or ([],[],[],[]))
    monkeypatch.setattr(gold_bgc_identity,'load_gold_identity_context',lambda *a:{'receipt':{'software':True}})
    writes={};monkeypatch.setattr(tool,'_atomic_dump',lambda data,path:writes.update({Path(path).name:data}))
    messages=[];monkeypatch.setattr(tool,'emit',lambda *a,**k:messages.extend(str(x) for x in a))
    monkeypatch.setattr(sys,'argv',['build_deep_data.py',str(bank)]);tool._main_stage()
    expected=f"{sum(x in ('bounded','full') for x in modes)} bounded/full, {modes.count('off')} offline, {modes.count('absent')} unknown"
    assert any(expected in message for message in messages)
    assert any(message.startswith('  OFFLINE (') for message in messages)==('off' in modes)
    assert [sid for sid,e in calls]==[sid for sid,mode in zip(snaps,modes) if mode!='off']
    remaining=[row for row,mode in zip(retained,modes) if mode in ('off','absent')]
    assert writes['deep_data.json']['active_sites']==remaining
    assert writes['gene_data.json']['substrates']==remaining
    for (sid,e) in calls:
        mode=modes[list(snaps).index(sid)]
        assert e==({} if mode=='absent' else {'json_mode':mode})
