import csv
from pathlib import Path
import pytest
from mamey import stage2_overlay as tool
import tests.test_stage2_overlay as fixtures


def arguments(tmp_path):
    f=fixtures.Stage2OverlayTests().fixture(tmp_path)
    return f,dict(base_report_root=f['base'],target_ledger=f['target'],
                  expected_target_sha256=tool.sha256_file(f['target']),review_root=f['review'],
                  source_manifest=f['manifest'],expected_manifest_sha256=tool.sha256_file(f['manifest']),
                  analysis_paths=[f['analysis']],disposition_paths=[f['disposition']],out_root=tmp_path/'out',
                  **fixtures.POLICY,**f['source_preflight'])

@pytest.mark.parametrize('mutation',['blank_line','reordered_rows'])
def test_manifest_byte_drift_after_admission_refuses_publication(tmp_path,monkeypatch,mutation):
    f,args=arguments(tmp_path);original=tool._front_door_markdown;called=[]
    base=f['base']/'reports/x.md';base_hash=tool.sha256_file(base)
    def mutate(rows):
        text=original(rows)
        if not called:
            if mutation=='blank_line':f['manifest'].write_text(f['manifest'].read_text()+'\n')
            else:
                with f['manifest'].open() as stream:records=list(csv.DictReader(stream,delimiter='\t'))
                fixtures.write_tsv(f['manifest'],list(reversed(records)))
            called.append(True)
        return text
    monkeypatch.setattr(tool,'_front_door_markdown',mutate)
    with pytest.raises(ValueError,match='Review source-manifest drifted'):
        tool.build(**args)
    assert called and not args['out_root'].exists()
    assert tool.sha256_file(base)==base_hash

def test_unchanged_manifest_keeps_proposal_contract(tmp_path):
    f,args=arguments(tmp_path)
    result=tool.build(**args)
    assert result['status']=='PASS_PROPOSAL_ONLY_NOT_ACCEPTED_NOT_INTEGRATED'
    assert args['out_root'].is_dir()
