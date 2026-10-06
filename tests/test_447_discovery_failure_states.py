"""Mocked service outcomes; no online submissions or biological inputs."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import pytest

ROOT=Path(__file__).resolve().parents[1]

def load(monkeypatch):
    spec=importlib.util.spec_from_file_location('discovery_failure_test',ROOT/'tools/cluster_discovery.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    # Replace only this fresh tool module's clock, never the shared stdlib time module.
    monkeypatch.setattr(m, 'time', SimpleNamespace(sleep=lambda _: None))
    return m

HITS='Sequences producing significant alignments:\n\nXP_123.1 synthetic 100%\n\n'
IPG='Assembly\tOrganism\tStrain\nGCF_000001.1\tSynthetic fixture\tFIXTURE\n'

class Fake:
    poll=0
    def __init__(self,state='READY',hits=HITS,ipg=IPG):self.state=state;self.hits=hits;self.ipg_text=ipg;self.fetches=0
    def blast_put(self,*args):return 'SYNTHETIC_RID'
    def blast_ready(self,*args):return self.state
    def blast_hits(self,*args):self.fetches+=1;return self.hits
    def ipg(self,*args):
        if isinstance(self.ipg_text,Exception):raise self.ipg_text
        return self.ipg_text

def test_exhausted_search_never_retrieves_results(monkeypatch):
    m=load(monkeypatch);net=Fake(state='WAITING')
    with pytest.raises(m.DiscoveryFailure,match='TIMEOUT'):m.discover('fixture',net,log=lambda *args:None)
    assert net.fetches==0

@pytest.mark.parametrize('text',['server error','Sequences producing significant alignments:\nunknown row\n','',
    'server error: No hits found is not a completed result', HITS+'***** No hits found *****'])
def test_unparsed_text_is_not_completed_no_hits(text,monkeypatch):
    m=load(monkeypatch)
    with pytest.raises(m.DiscoveryFailure,match='RESULT_PARSE_UNVERIFIED'):m.discover('fixture',Fake(hits=text),log=lambda *args:None)

@pytest.mark.parametrize('text',['invalid','Assembly\tOrganism\n','Assembly\tOrganism\nNA\tfixture\n',RuntimeError('mock failure')])
def test_unresolved_assemblies_are_incomplete(text,monkeypatch):
    m=load(monkeypatch)
    with pytest.raises(m.DiscoveryFailure,match='ASSEMBLY_UNRESOLVED'):m.discover('fixture',Fake(ipg=text),log=lambda *args:None)

def test_partial_rows_survive_only_as_incomplete_evidence(monkeypatch):
    m=load(monkeypatch);net=Fake(hits=HITS.replace('XP_123.1 synthetic 100%', 'XP_123.1 synthetic 100%\nYP_456.1 synthetic 95%'))
    monkeypatch.setattr(net,'ipg',lambda acc:IPG if acc=='XP_123.1' else 'invalid')
    with pytest.raises(m.DiscoveryFailure) as error:m.discover('fixture',net,log=lambda *args:None)
    assert error.value.status=='PARTIAL' and len(error.value.partial_rows)==1

def test_explicit_no_hits_and_valid_filtered_hits_controls(monkeypatch):
    m=load(monkeypatch)
    assert m.discover('fixture',Fake(hits='***** No hits found *****'),log=lambda *args:None)==[]
    assert m.discover('fixture',Fake(hits=HITS.replace('100%', '79%')),min_identity=90,log=lambda *args:None)==[]
    assert len(m.discover('fixture',Fake(),log=lambda *args:None))==1

def test_main_failure_does_not_create_output(tmp_path,monkeypatch):
    m=load(monkeypatch);marker=tmp_path/'synthetic.faa';marker.write_text('>fixture\nA\n');out=tmp_path/'output'
    monkeypatch.setattr(m,'Net',lambda:Fake(state='WAITING'))
    assert m.main(['--marker',str(marker),'--outdir',str(out)])==2
    assert not out.exists()
