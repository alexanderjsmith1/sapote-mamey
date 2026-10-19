from pathlib import Path
import os,json,sys,subprocess
import pytest
ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.parametrize("offline,core_only",[(False,False),(True,False),(True,True)])
def test_offline_pip_ignores_ambient_configuration_only_when_selected(tmp_path,offline,core_only):
    log=tmp_path/"pip.jsonl";config=tmp_path/"pip.conf"
    config.write_text('[global]\nfind-links = https://example.invalid/wheels\n')
    wheels=tmp_path/"empty local wheels";wheels.mkdir()
    shim=tmp_path/"fake python"
    shim.write_text("#!"+sys.executable+"\nimport json,os,sys\na=sys.argv[1:]\nif a==['--version']:print('Python 3.13.13')\nif a[:2]==['-m','pip']:\n with open(os.environ['BOOTSTRAP_SHIM_LOG'],'a') as f:f.write(json.dumps({'args':a,'config':os.environ.get('PIP_CONFIG_FILE')})+'\\n')\n if '.[all]' in a and os.environ['FAKE_CORE_ONLY']=='1':sys.exit(1)\n")
    shim.chmod(0o755)
    command=['bash',str(ROOT/'bootstrap.sh')]+(['--wheels',str(wheels)] if offline else [])
    env=dict(os.environ,PYTHON=str(shim),PIP_CONFIG_FILE=str(config),PIP_FIND_LINKS='https://example.invalid/wheels',BOOTSTRAP_SHIM_LOG=str(log),FAKE_CORE_ONLY=str(int(core_only)))
    r=subprocess.run(command,env=env,capture_output=True,text=True,timeout=15)
    assert r.returncode==0,r.stdout+r.stderr
    calls=[json.loads(row) for row in log.read_text().splitlines()]
    assert calls
    probes=[call for call in calls if '--version' in call['args']]
    assert len(probes)==1
    assert ('--isolated' in probes[0]['args'])==offline
    assert probes[0]['config']==(os.devnull if offline else str(config))
    calls=[call for call in calls if 'install' in call['args']]
    assert len(calls)==(3 if core_only else 2)
    for call in calls:
        if offline:assert '--isolated' in call['args'] and '--no-index' in call['args'] and call['config']==os.devnull
        else:assert '--isolated' not in call['args'] and call['config']==str(config)
    if core_only:assert 'bootstrap done: CORE_ONLY' in r.stdout
