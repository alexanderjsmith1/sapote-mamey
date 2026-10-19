"""Read-only shell admission prefix; a marker replaces all preparation/build work."""
import os,subprocess,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('case,expected',[
    ('missing_path','RELEASE-RECEIPT-001'),('relative_path','RELEASE-RECEIPT-001'),
    ('missing_hash','RELEASE-RECEIPT-002'),('malformed_hash','RELEASE-RECEIPT-002'),
    ('missing_file','RELEASE-RECEIPT-003'),('valid_settings',None),('ordinary_tests',None)])
def test_skip_receipt_settings_admitted_before_preparation_marker(tmp_path,case,expected):
    source=tmp_path/'source';source.mkdir();(source/'sentinel').write_bytes(b'unchanged source')
    output=tmp_path/'fresh output';receipt=tmp_path/'receipt.json';receipt.write_text('{"fixture":"not admitted evidence"}\n')
    text=(ROOT/'tools/release_cut.sh').read_text()
    # Use the actual admission prefix only, followed by its actual preparation
    # dispatch header. No cut hooks, generators, identity changes or suite execute.
    prefix=text.split('\nif [[ "$PYTEST_MODE" == partitioned && -z "$PHASE" ]]; then',1)[0]
    dispatch=text.split('# Keep the default path in execution order; internal phases skip its suite.\n',1)[1]
    assert dispatch.startswith('if [[ -z "$PHASE" ]]; then\nprepare_release\n')
    script=prefix+'\nprepare_release(){ printf "PREPARATION_MARKER\\n"; exit 93; }\n'+dispatch.split('mkdir -p "$OUT"',1)[0]+'fi\n'
    env=dict(os.environ,PYTHON=sys.executable,PYTHONDONTWRITEBYTECODE='1',RELEASE_PYTEST_MODE='monolithic',RELEASE_WORKFLOW_PHASE='')
    for key in ['PYTEST_ADDOPTS','PYTEST_RECEIPT','PYTEST_RECEIPT_SHA256']:env.pop(key,None)
    if case not in ['missing_path','ordinary_tests']:env['PYTEST_RECEIPT']=str(receipt)
    if case=='relative_path':env['PYTEST_RECEIPT']='receipt.json'
    if case=='missing_file':env['PYTEST_RECEIPT']=str(tmp_path/'not-present.json')
    if case not in ['missing_hash','ordinary_tests']:env['PYTEST_RECEIPT_SHA256']='a'*64
    if case=='malformed_hash':env['PYTEST_RECEIPT_SHA256']='bad'
    args=['bash','-s','--','9.7.452',str(source),str(output)]
    if case!='ordinary_tests':args.append('--skip-tests')
    result=subprocess.run(args,input=script,cwd=tmp_path,env=env,capture_output=True,text=True,timeout=5)
    if expected:
        assert result.returncode==2,(result.stdout,result.stderr)
        assert expected in result.stderr and 'before source preparation' in result.stderr
        assert 'PREPARATION_MARKER' not in result.stdout
    else:
        assert result.returncode==93 and 'PREPARATION_MARKER' in result.stdout
    assert (source/'sentinel').read_bytes()==b'unchanged source' and not output.exists()
    assert receipt.read_text()=='{"fixture":"not admitted evidence"}\n'

def test_valid_settings_still_require_real_exact_source_receipt_gate(tmp_path):
    import hashlib,shutil
    source=tmp_path/'source';(source/'tools').mkdir(parents=True)
    # Actual unmodified verifier, deliberately invalid fabricated receipt.
    shutil.copyfile(ROOT/'tools/verify_external_validation_receipt.py',source/'tools/verify_external_validation_receipt.py')
    receipt=tmp_path/'receipt.json';receipt.write_text('{"fixture":"not evidence"}\n')
    text=(ROOT/'tools/release_cut.sh').read_text()
    prefix=text.split('\nif [[ "$PYTEST_MODE" == partitioned && -z "$PHASE" ]]; then',1)[0]
    gate=text.split('  say "gate: verify exact-source external full-suite receipt"\n',1)[1].split('\nfi\ngrep -qE',1)[0]
    env=dict(os.environ,PYTHON=sys.executable,PYTHONDONTWRITEBYTECODE='1',RELEASE_PYTEST_MODE='monolithic',RELEASE_WORKFLOW_PHASE='',
             PYTEST_RECEIPT=str(receipt),PYTEST_RECEIPT_SHA256=hashlib.sha256(receipt.read_bytes()).hexdigest())
    env.pop('PYTEST_ADDOPTS',None)
    before=receipt.read_bytes()
    result=subprocess.run(['bash','-s','--','9.7.452',str(source),str(tmp_path/'output'),'--skip-tests'],
                          input=prefix+'\n'+gate+'\n',cwd=tmp_path,env=env,capture_output=True,text=True,timeout=5)
    assert result.returncode!=0
    assert 'receipt schema must be' in result.stderr
    assert 'external full-suite receipt is invalid; refusing --skip-tests.' in result.stderr
    assert 'external validation receipt: PASS' not in result.stdout
    assert receipt.read_bytes()==before and not (tmp_path/'output').exists()
