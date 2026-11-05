"""CLI integration checks with synthetic bytes, not biological fixtures."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / 'tools/phylo_crossgroup_intake.py'
REGISTRY = ROOT / 'mamey/data/fungal_outgroup_registry.tsv'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_all_requested_branches_remain_review_holds(tmp_path):
    inputs = []
    for role in ('query', 'ingroup', 'outgroup'):
        source = tmp_path / (role + '.dat')
        source.write_text('synthetic fixture ' + role)
        inputs.append({'id': role, 'role': role, 'taxon_label': 'synthetic ' + role,
                       'source': 'synthetic', 'accession': role, 'kind': 'marker',
                       'path': str(source), 'sha256': sha(source),
                       'file_scope': 'single_record', 'sequence_extent': 'single_marker'})
    cases = [('fungi', 'synthetic fungi'), ('algae', 'Trebouxia'),
             ('algae', 'Chlorella'), ('algae', 'Coccomyxa'), ('cyanobacteria', 'synthetic cyanobacteria')]
    env = os.environ.copy(); env.pop('PYTHONPATH', None)
    for index, (group, lineage) in enumerate(cases):
        records = [dict(item) for item in inputs]
        for item in records:
            item['compartment'] = 'bacterial' if group == 'cyanobacteria' else 'nuclear'
        manifest = {'schema': 'cross-group-phylo-intake-v1', 'group': group,
                    'question': 'synthetic test only', 'lineage': lineage,
                    'tree_scope': 'synthetic', 'method_description': 'no analysis',
                    'data_kind': 'marker', 'marker': 'synthetic', 'records': records}
        if group == 'fungi':
            records[2]['accession'] = 'NG_061119.1'
            manifest['fungal_registry'] = {'path': str(REGISTRY), 'sha256': sha(REGISTRY),
                'selection': {'tree_scope': 'family', 'ingroup_taxon': 'Trichomeriaceae', 'accession': 'NG_061119.1'}}
        file = tmp_path / f'manifest-{index}.json'; file.write_text(json.dumps(manifest))
        cmd = [sys.executable, str(TOOL), str(file), '--allow-root', str(tmp_path), '--allow-root', str(REGISTRY.parent)]
        estimated = subprocess.run(cmd + ['--estimate-only'], cwd=tmp_path, env=env, capture_output=True, text=True, timeout=20)
        assert estimated.returncode == 0
        assert json.loads(estimated.stdout)['status'] == 'ESTIMATE_ONLY'
        run = subprocess.run(cmd, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=20)
        result = json.loads(run.stdout)
        assert run.returncode == 0 and result['status'] == 'HOLD' and not result['errors']
        assert any('Scientific suitability' in hold for hold in result['holds'])
        if group == 'fungi':
            assert any('selected row bound' in item for item in result['observations'])
        elif group == 'algae':
            assert any('Algal lineage-specific' in hold for hold in result['holds'])
        else:
            assert any('Cyanobacteria are bacteria' in hold for hold in result['holds'])
    # The metadata-only estimate is not a hash check; the full intake must
    # refuse changed bytes rather than preserving the earlier HOLD.
    Path(inputs[0]['path']).write_text('changed synthetic fixture')
    estimated = subprocess.run(cmd + ['--estimate-only'], cwd=tmp_path, env=env, capture_output=True, text=True, timeout=20)
    assert estimated.returncode == 0 and json.loads(estimated.stdout)['status'] == 'ESTIMATE_ONLY'
    changed = subprocess.run(cmd, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=20)
    assert changed.returncode == 2 and json.loads(changed.stdout)['status'] == 'ERROR'


def test_zip_fasta_member_header_via_cli(tmp_path):
    import zipfile
    archive = tmp_path / 'input.zip'
    member = b'>record.1 description\nACGT\n>other.1\nTT\n'
    with zipfile.ZipFile(archive, 'w') as z:
        z.writestr('input/genome.fna', member)
    records = []
    for role in ('query', 'ingroup', 'outgroup'):
        source = tmp_path / (role + '.dat'); source.write_text('synthetic ' + role)
        records.append({'id':role,'role':role,'taxon_label':'synthetic', 'source':'synthetic',
                        'accession':role,'kind':'genome','path':str(source),'sha256':sha(source),
                        'file_scope':'single_record','sequence_extent':'unknown','compartment':'unknown'})
    records[0].update(path=str(archive),sha256=sha(archive),file_scope='archive',source_format='zip',
        record_locator='input/genome.fna',member_sha256=hashlib.sha256(member).hexdigest(),
        member_format='fasta',member_record_locator='record.1')
    manifest={'schema':'cross-group-phylo-intake-v1','group':'algae','question':'synthetic only',
              'lineage':'Trebouxia label only','tree_scope':'synthetic','method_description':'no analysis',
              'data_kind':'genome','records':records}
    file=tmp_path/'manifest.json';file.write_text(json.dumps(manifest))
    env=os.environ.copy();env.pop('PYTHONPATH',None)
    cmd=[sys.executable,str(TOOL),str(file),'--allow-root',str(tmp_path)]
    result=subprocess.run(cmd,cwd=tmp_path,env=env,capture_output=True,text=True,timeout=20)
    parsed=json.loads(result.stdout)
    assert result.returncode==0 and parsed['status']=='HOLD'
    assert any('ZIP FASTA header token occurs exactly once' in x for x in parsed['observations'])
    records[0]['member_record_locator']='missing';file.write_text(json.dumps(manifest))
    result=subprocess.run(cmd,cwd=tmp_path,env=env,capture_output=True,text=True,timeout=20)
    parsed=json.loads(result.stdout)
    assert result.returncode==2 and parsed['status']=='ERROR'
    assert any('occurs 0 times' in x for x in parsed['errors'])


def test_gzip_fasta_header_via_cli(tmp_path):
    import gzip
    source=tmp_path/'input.fna.gz';source.write_bytes(gzip.compress(b'>record.1 description\nACGT\n>other.1\nTT\n'))
    records=[]
    for role in ('query','ingroup','outgroup'):
        path=tmp_path/(role+'.dat');path.write_text('synthetic '+role)
        records.append({'id':role,'role':role,'taxon_label':'synthetic','source':'synthetic','accession':role,
                        'kind':'genome','path':str(path),'sha256':sha(path),'file_scope':'single_record',
                        'sequence_extent':'unknown','compartment':'unknown'})
    records[0].update(path=str(source),sha256=sha(source),file_scope='multi_record',source_format='fasta_gzip',record_locator='record.1')
    manifest={'schema':'cross-group-phylo-intake-v1','group':'algae','question':'synthetic only',
              'lineage':'Chlorella label only','tree_scope':'synthetic','method_description':'no analysis',
              'data_kind':'genome','records':records}
    path=tmp_path/'manifest.json';path.write_text(json.dumps(manifest))
    env=os.environ.copy();env.pop('PYTHONPATH',None)
    cmd=[sys.executable,str(TOOL),str(path),'--allow-root',str(tmp_path)]
    estimated=subprocess.run(cmd+['--estimate-only'],cwd=tmp_path,env=env,capture_output=True,text=True,timeout=20)
    assert estimated.returncode==0 and json.loads(estimated.stdout)['records'][0]['planned_full_file_scans']==3
    result=subprocess.run(cmd,cwd=tmp_path,env=env,capture_output=True,text=True,timeout=20);parsed=json.loads(result.stdout)
    assert result.returncode==0 and parsed['status']=='HOLD'
    assert any('gzip FASTA header token occurs exactly once' in x for x in parsed['observations'])
    records[0]['record_locator']='missing';path.write_text(json.dumps(manifest))
    result=subprocess.run(cmd,cwd=tmp_path,env=env,capture_output=True,text=True,timeout=20);parsed=json.loads(result.stdout)
    assert result.returncode==2 and any('occurs 0 times' in x for x in parsed['errors'])
