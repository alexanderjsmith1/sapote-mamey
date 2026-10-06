"""Companion admission tests use subprocess fakes; no installs/HMMER/R jobs."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace
import pytest
from mamey import optional_r

ROOT=Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('rc,state',[(0,'READY'),(10,'UNAVAILABLE'),(1,'UNVERIFIED'),(2,'UNVERIFIED')])
def test_r_package_availability_typed(monkeypatch,rc,state):
    calls=[]
    def probe(command,**kwargs):
        calls.append(command); assert kwargs['timeout']==10
        return SimpleNamespace(returncode=rc, stdout="SAPOTE_R_MISSING:ggtree\n" if rc==10 else "")
    monkeypatch.setattr(optional_r.subprocess,'run',probe)
    assert optional_r.r_package_status(('ggtree',), executable='fakeR')[0]==state
    assert 'requireNamespace("ggtree"' in calls[0][-1]


def test_r_missing_and_timed_out_are_visible(monkeypatch):
    monkeypatch.setattr(optional_r.shutil,'which',lambda x:None)
    assert optional_r.r_package_status()[0]=='UNAVAILABLE'
    def timeout(*a,**kw): raise subprocess.TimeoutExpired('fakeR',10)
    monkeypatch.setattr(optional_r.subprocess,'run',timeout)
    assert optional_r.r_package_status(executable='fakeR')[0]=='UNVERIFIED'
    with pytest.raises(ValueError):optional_r.r_package_status(('ggtree";stop(1)',),executable='fakeR')


def scanner(tmp,monkeypatch,mode='good'):
    spec=importlib.util.spec_from_file_location('scanner_builder_test',ROOT/'tools/build_scanner_hmm.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    source=tmp/'synthetic.hmm';source.write_text('synthetic source only')
    selectors=tmp/'selectors.txt';selectors.write_text('PF00001.2\nPF00002.3\n')
    monkeypatch.setattr(mod.shutil,'which',lambda p:'/fake/'+p)
    def run(cmd,**kwargs):
        if cmd[0]=='hmmfetch':
            acc='PF99999.1' if mode=='wrong' else cmd[-1]
            return SimpleNamespace(stdout=f'HMMER3/f\nNAME SYNTHETIC\nACC {acc}\n//\n'.encode())
        if mode=='mutate': source.write_text('changed during fetch')
        for suffix in ('.h3f','.h3i','.h3m','.h3p'):
            if mode=='missing' and suffix=='.h3p':continue
            Path(cmd[-1]+suffix).write_bytes(b'fake-index')
        return SimpleNamespace(stdout=b'')
    monkeypatch.setattr(mod.subprocess,'run',run)
    return mod,source,selectors,tmp/'output.hmm'


def test_scanner_build_publishes_bound_subset_and_all_indices(tmp_path,monkeypatch):
    mod,src,selectors,out=scanner(tmp_path,monkeypatch)
    receipt=mod.build(src,out,selectors)
    assert receipt['status']=='COMPLETE_NEW_SOURCE_BUILD'
    assert len(receipt['outputs'])==5
    for item in receipt['outputs']:
        assert hashlib.sha256(Path(item['path']).read_bytes()).hexdigest()==item['sha256']
    assert json.loads(Path(str(out)+'.build_receipt.json').read_text())==receipt
    with pytest.raises(ValueError,match='existing output'):mod.build(src,out,selectors)


@pytest.mark.parametrize('mode,match',[('wrong','one pinned model'),('missing','four index'),('mutate','changed during build')])
def test_scanner_failed_build_leaves_no_published_output(tmp_path,monkeypatch,mode,match):
    mod,src,selectors,out=scanner(tmp_path,monkeypatch,mode)
    with pytest.raises(ValueError,match=match):mod.build(src,out,selectors)
    assert not list(tmp_path.glob('output.hmm*'))


def test_scanner_publication_failure_rolls_back(tmp_path,monkeypatch):
    mod,src,selectors,out=scanner(tmp_path,monkeypatch)
    original=mod.os.link; n=0
    def fail(a,b):
        nonlocal n
        n+=1
        if n==3:raise OSError('synthetic link failure')
        original(a,b)
    monkeypatch.setattr(mod.os,'link',fail)
    with pytest.raises(OSError):mod.build(src,out,selectors)
    assert not list(tmp_path.glob('output.hmm*'))


def test_scanner_preset_lists_match_shipped_source_pins():
    pins=json.loads((ROOT/'bundle_support/scanner_accession_source_pins.json').read_text())
    for preset in ('35','148'):
        data=(ROOT/f'bundle_support/scanner_pfam_{preset}_accessions.txt').read_bytes()
        values=[x for x in data.decode().splitlines() if x and not x.startswith('#')]
        assert len(values)==len(set(values))==int(preset)
        # Source manifests and exact source model digests are recorded by provisioning evidence.
        assert hashlib.sha256(data).hexdigest()==pins[preset]['accession_file_sha256']


def installer(tmp_path,mode,wheels=True):
    repo=tmp_path/'repo';(repo/'bundle_support').mkdir(parents=True)
    script=repo/'bundle_support/install_sapote_addons.sh'
    script.write_bytes((ROOT/'bundle_support/install_sapote_addons.sh').read_bytes())
    if wheels:(repo/'synthetic.whl').write_bytes(b'not a real wheel; fake interpreter only')
    log=tmp_path/'pip.log'; fake=tmp_path/'fake-python'
    fake.write_text('''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
if sys.argv[1:2]==['-c']:print(1);sys.exit(0)
if sys.argv[1:3]==['-m','pip']:
    with Path(os.environ['FAKE_LOG']).open('a') as f:f.write(json.dumps(sys.argv[1:])+'\\n')
    if '--no-index' in sys.argv and os.environ['FAKE_MODE']!='good':
        print('No matching distribution found' if os.environ['FAKE_MODE']=='missing' else 'invalid wheel archive',file=sys.stderr)
        sys.exit(1)
sys.exit(0)
''');fake.chmod(0o755)
    env=dict(os.environ,PYTHON=str(fake),FAKE_LOG=str(log),FAKE_MODE=mode)
    return script,repo,env,log


@pytest.mark.parametrize('online,mode,expected',[(False,'missing',1),(True,'missing',0),(True,'invalid',1),(False,'good',0)])
def test_installer_network_fallback_is_explicit_and_missing_wheel_only(tmp_path,online,mode,expected):
    script,cwd,env,log=installer(tmp_path,mode)
    process=subprocess.run(['bash',str(script)]+(['--online'] if online else []),cwd=cwd,env=env,capture_output=True,text=True)
    assert process.returncode==expected,process.stderr
    calls=[json.loads(line) for line in log.read_text().splitlines()]
    indexed=[call for call in calls if '--no-index' not in call]
    assert bool(indexed)==(online and mode=='missing')
    assert '--no-index' in calls[0]


def test_installer_public_clone_needs_explicit_online(tmp_path):
    # Script searches neighbour roots; isolated copy has no actual wheels.
    script,cwd,env,log=installer(tmp_path,'missing',wheels=False)
    # /tmp sibling fixture wheel pools may be present: restrict only discovery, not installer routing.
    text=script.read_text();start=text.index('SEARCH_ROOTS+=(\n');end=text.index('\n)\n',start)+3
    script.write_text(text[:start]+'SEARCH_ROOTS+=("$HERE")\n'+text[end:])
    offline=subprocess.run(['bash',str(script)],cwd=cwd,env=env,capture_output=True,text=True)
    assert offline.returncode==1 and not log.exists()
    online=subprocess.run(['bash',str(script),'--online'],cwd=cwd,env=env,capture_output=True,text=True)
    assert online.returncode==0 and 'explicitly authorized' in online.stdout
    assert all('--no-index' not in json.loads(line) for line in log.read_text().splitlines())


def test_shared_r_fixture_skips_missing_package_and_admits_ready(monkeypatch):
    from tests.conftest import require_r_packages
    calls=[]
    def unavailable(packages):
        calls.append(packages); return 'UNAVAILABLE','ggtree unavailable; integration unverified','fakeR'
    monkeypatch.setattr(optional_r,'r_package_status',unavailable)
    require=require_r_packages.__wrapped__()
    with pytest.raises(pytest.skip.Exception,match='integration unverified'):require()
    assert calls==[optional_r.TREE_RENDER_PACKAGES]
    monkeypatch.setattr(optional_r,'r_package_status',lambda p:('READY','available','fakeR'))
    assert require_r_packages.__wrapped__()()=='fakeR'


def test_optional_r_unverified_probe_fails_instead_of_skipping(monkeypatch):
    from tests.conftest import require_r_packages
    monkeypatch.setattr(optional_r, 'r_package_status', lambda p: ('UNVERIFIED', 'synthetic probe error', 'fakeR'))
    with pytest.raises(pytest.fail.Exception, match='probe error'):
        require_r_packages.__wrapped__()()
