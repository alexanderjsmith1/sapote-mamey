"""Byte/channel parity against frozen parent functions, with synthetic inputs only."""
import ast
import builtins
import copy
import importlib
import io
import json
from pathlib import Path
import sys
from types import SimpleNamespace, ModuleType
from contextlib import redirect_stdout, redirect_stderr

import pytest

ROOT = Path(__file__).resolve().parents[1]
PARENT = json.loads((ROOT / 'tests/fixtures/report_output_parent_447.json').read_text())['functions']


class Stream(io.StringIO):
    def __init__(self, channel, events):
        super().__init__(); self.channel = channel; self.events = events
    def write(self, text):
        if text:
            if self.events and self.events[-1][0] == self.channel:
                self.events[-1][1] += text
            else:
                self.events.append([self.channel, text])
        return super().write(text)


def current_source(name, module):
    source = Path(module.__file__).read_text()
    if name == 'doctor_summary':
        start = source.index('    # Summary\n', source.index('def doctor_command'))
        return 'def doctor_summary():\n' + source[start:source.index('\n\ndef cohort_command', start)] + '\n'
    for node in ast.parse(source).body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.get_source_segment(source, node) + '\n'
    raise AssertionError(name)


def parity(name, module_name, args=None, extras=None):
    module = importlib.import_module(module_name)
    outputs = []
    for source in (PARENT[name], current_source(name, module)):
        namespace = dict(module.__dict__)
        namespace.update(extras or {})
        exec(compile(source, '<frozen report parity>', 'exec'), namespace)
        events = []; stdout = Stream('stdout', events); stderr = Stream('stderr', events)
        with redirect_stdout(stdout), redirect_stderr(stderr):
            result = namespace[name]() if args is None else namespace[name](args)
        outputs.append((result, stdout.getvalue(), stderr.getvalue(), events))
    assert outputs[0] == outputs[1]
    return outputs[1]


def stub(monkeypatch, name, function, result):
    mod = ModuleType(name)
    setattr(mod, function, lambda *a, **kw: copy.deepcopy(result))
    monkeypatch.setitem(sys.modules, name, mod)


@pytest.mark.parametrize('case', ['minimal', 'full', 'missing', 'corrupt_fallback', 'issues'])
def test_explain(case, tmp_path):
    package = tmp_path / 'package'; package.mkdir()
    if case != 'missing':
        data = {'strain_id':'SYNTH', 'status':'fixture', 'mode':'gold'}
        if case in {'full','issues'}:
            data.update(top_3_ab=[{'bgc_id':'BGC001','contig':'NODE_fixture','ab_score':2}],
                        top_3_af=[{'bgc_id':'BGC002','contig':'NODE_other','af_score':1}], interior_pct=50)
        (package/'manifest.json').write_text(json.dumps(data))
        if case == 'corrupt_fallback': (package/'manifest_short.json').write_text('{broken')
        else: (package/'manifest_short.json').write_text(json.dumps(data))
        if case == 'issues': (package/'issue_log.md').write_text('\n'.join('- fixture issue '+str(i) for i in range(7)))
    parity('explain_command','mamey.package_inspector',SimpleNamespace(package_dir=str(package)))


@pytest.mark.parametrize('count,json_output', [(0,False),(1,False),(2,False),(1,True)])
def test_list_bgcs(count, json_output, tmp_path):
    package=tmp_path/'package';package.mkdir();(package/'SYNTH_4_triage_board.csv').write_text('mocked')
    row={'exact_locus':'SYNTH | NODE_fixture_length_1_cov_1 | region001 | BGC001',
         'products':'class-level fixture','boundary':'fixture','ab_score':2.5,'af_score':1.5,'lead_tier':'fixture'}
    result=parity('list_bgcs_command','mamey.package_inspector',
                  SimpleNamespace(package_dir=str(package),json=json_output),
                  {'bgc_json_list_from_board':lambda *a,**kw:[row]*count})
    if count: assert row['exact_locus'] in result[1]


@pytest.mark.parametrize('case',['missing','bad_zip','no_regions','ordinary','accession','large'])
def test_inspect(case, tmp_path, monkeypatch):
    import zipfile
    import mamey.parsers as parsers
    monkeypatch.setattr(parsers,'_gbk_size_guard',lambda *a:None)
    monkeypatch.setattr(parsers,'extract_antismash_version',lambda *a,**kw:'fixture-version')
    archive=tmp_path/'fixture.zip'
    if case=='bad_zip':archive.write_bytes(b'not a ZIP')
    elif case!='missing':
        with zipfile.ZipFile(archive,'w') as z:
            z.writestr('index.html','fixture')
            if case!='no_regions':
                for i in range(41 if case=='large' else 1):z.writestr(f'fixture.region{i+1:03}.gbk','opaque nonbiological fixture')
    shape={'summary':'synthetic fixture','accession_like':case=='accession',
           'shape':'single_region_antismash_accession' if case=='accession' else 'genome','accession':'FIXTURE'}
    parity('inspect_command','mamey.package_inspector',SimpleNamespace(zip=str(archive)),
           {'classify_antismash_zip':lambda *a:shape})


@pytest.mark.parametrize('ok,warn,fail',[([],[],[]),(['fixture'],[],[]),([],['warning'],[]),([],[],['failure']),(['ok'],['warn'],['fail'])])
def test_doctor_summary(ok,warn,fail):
    parity('doctor_summary','mamey.cli',extras={'ok':ok,'warn':warn,'fail':fail,'plat':'fixture',
           'BUNDLE_ROOT':Path('/fixture/bundle'), 'sys':sys})


@pytest.mark.parametrize('present,challenge',[(False,False),(True,False),(True,True)])
def test_chatgpt_init(present, challenge, tmp_path):
    (tmp_path/'mamey').mkdir()
    if present:(tmp_path/'AGENTS.md').write_text('bundle / engine: fixture\nknown gotcha (this build): fixture\n'+('challenge phrase: test-marker\n' if challenge else ''))
    (tmp_path/'README.md').write_text('fixture')
    parity('chatgpt_init_command','mamey.cli',SimpleNamespace(),{'__file__':str(tmp_path/'mamey/cli.py')})


@pytest.mark.parametrize('kind,mode',[('receipt','empty'),('receipt','full'),('receipt','identity'),('receipt','structure'),
                                     ('receipt','coverage'),('receipt','advisory'),('auto','empty'),('auto','full'),
                                     ('auto','unreadable'),('auto','persistence')])
def test_ingest_final_reports(kind,mode,tmp_path,monkeypatch):
    package=tmp_path/'package';package.mkdir()
    summary={'strain_id':'SYNTH','recorded':[],'skipped_unknown':[],'skipped_no_content':[],
             'complete_bgcs':0,'total_bgcs':0,'register_status':'fixture','e1_updated':False,
             'scanned_count':0,'skipped_already_complete':[],'judgment_status':'COMPLETE'}
    if mode=='full':summary.update(recorded=['BGC001'],recorded_with_structure_override=['BGC001'],
       skipped_unknown=['BGC002'],skipped_no_content=['BGC003'],skipped_already_complete=['BGC004'],
       skipped_structure_invalid=[['BGC005',1]],e1_updated=True,e1_summary={'bgcs_complete':1,'bgcs_written':2},
       skipped_misnamed=[['BGC006','fixture.md']])
    if mode=='identity':summary['skipped_identity_mismatch']=[{'receipt_bgc_id':'BGC001','reason':'fixture conflict'}]
    if mode=='structure':summary['skipped_structure_invalid']=[['BGC001',1]]
    if mode=='coverage':summary['coverage_receipt']={'coverage_only':True,'coverage_status':'fixture','emitted_card_count':0,'inventory_bgc_count':1}
    if mode=='advisory':summary['persistence_warnings']=[{'identity':'SYNTH | NODE_fixture | region001 | BGC001','stage':'fixture','message':'fixture'}]
    if mode=='unreadable':summary['skipped_unreadable']=['BGC001']
    if mode=='persistence':summary['record_failures']=['BGC001']
    stub(monkeypatch,'mamey.judgment_store','judgment_status_blocks_ingest',False)
    # The called admission/storage engines are mocked, so no package mutation occurs.
    args=SimpleNamespace(package=str(package),auto_detect=kind=='auto',receipt='fixture.json' if kind=='receipt' else None)
    parity('ingest_receipts_command','mamey.mode_b_receipt',args,
           {'ingest_receipt':lambda *a,**kw:copy.deepcopy(summary),
            'auto_detect_ingest':lambda *a,**kw:copy.deepcopy(summary)})
    assert list(package.iterdir())==[]


@pytest.mark.parametrize('ok,warnings,figures',[(True,[],0),(True,['fixture warning'],2),(False,['fixture warning'],0)])
def test_cohort_status(ok,warnings,figures,monkeypatch):
    result=SimpleNamespace(warnings=warnings,synthesis_report='fixture.md' if ok else None,
                          figures_dir='fixture-figures',figure_count=figures,ok=ok,
                          out_dir='fixture-out',deliverables=['fixture.md'],strains=['SYNTH'])
    stub(monkeypatch,'mamey.cohort_deliverable','run_cohort_deliverable',result)
    parity('cohort_command','mamey.cli',SimpleNamespace(runs_dir='fixture',out='fixture'))


@pytest.mark.parametrize('count,mixed',[(0,False),(1,False),(1,True)])
def test_cohort_leads_status(count,mixed,monkeypatch):
    result={'n_leads':count,'n_strains':1,'out_path':'fixture.csv','mixed_engine':mixed,'engine_versions':['fixtureA','fixtureB']}
    stub(monkeypatch,'mamey.cohort_leads_ledger','run',result)
    parity('cohort_leads_command','mamey.cli',SimpleNamespace(runs_dir='fixture',out='fixture'))


@pytest.mark.parametrize('count,mixed,extras',[(0,False,False),(1,False,False),(1,True,True)])
def test_cohort_assembly_report(count,mixed,extras,monkeypatch):
    paths={'main':'fixture.csv'}
    if extras:paths.update(strain_summary='summary.csv',class_by_strain='classes.csv',xlsx='fixture.xlsx')
    result={'n_strains':count,'n_bgcs':1,'paths':paths,'mixed_engine':mixed,'engine_versions':['fixtureA','fixtureB']}
    stub(monkeypatch,'mamey.cohort_assemble','run',result)
    parity('cohort_assemble_command','mamey.cli',SimpleNamespace(runs_dir='fixture',out='fixture'))


@pytest.mark.parametrize('complete,mixed,unbound,count',[(True,False,0,1),(True,True,1,1),(False,True,1,1),(True,False,0,0)])
def test_activity_lead_status(complete,mixed,unbound,count,monkeypatch):
    result={'n_rows':1,'n_strains':count,'paths':{'report_md':'fixture.md','unbound_csv':'fixture.csv'},
            'mixed_engine':mixed,'engine_versions':['fixtureA','fixtureB'],'unbound_rows':unbound,'complete':complete}
    stub(monkeypatch,'mamey.activity_lead_report','run',result)
    parity('activity_leads_command','mamey.cli',SimpleNamespace(runs_dir='fixture',out='fixture',top_n=1))
