"""Reader/build ownership and retained captions; synthetic fixtures, no engine runs."""
import io
import importlib.util
import json
from contextlib import redirect_stdout,redirect_stderr
from pathlib import Path
from types import SimpleNamespace

import pytest

from mamey import compile_report as cr
from mamey import validate, blastp_gate, postseal_output, sapote_workflow

ROOT=Path(__file__).resolve().parents[1]


def mocked_report_engine(monkeypatch):
    monkeypatch.setattr(blastp_gate,'gate',lambda *a,**kw:{'blocked':False,'message':''})
    monkeypatch.setattr(cr,'build_report',lambda *a,**kw:'# SYNTH\n\nClass-level synthetic evidence report.\n')


def package(tmp_path,sealed=False):
    p=tmp_path/'package';p.mkdir()
    (p/'manifest.json').write_text(json.dumps({'strain_id':'TEST-01'}))
    (p/'TEST-01_4_triage_board.csv').write_text('BGC_ID,Class\nBGC001,fixture\n')
    if sealed:(p/'checksums_sha256.txt').write_text('synthetic marker; validator is mocked\n')
    return p


@pytest.mark.parametrize('sealed',[False,True])
def test_internal_preseal_report_and_external_sealed_reader_both_reach_workflow(tmp_path,monkeypatch,sealed):
    p=package(tmp_path,sealed);before={f.name:f.read_bytes() for f in p.iterdir()}
    monkeypatch.setattr(validate,'validate_package',lambda *a:{'identity_binding':'PASS','manifest_parse':'PASS','checksum_integrity':'PASS'})
    mocked_report_engine(monkeypatch)
    args=SimpleNamespace(package_dir=str(p),out=None,no_figures=True,pdf=False,strict=False,toc_depth=1)
    assert cr.compile_report_command(args)==0
    internal=p/'TEST-01_compiled_report.md'
    if sealed:
        assert not internal.exists()
        assert {f.name:f.read_bytes() for f in p.iterdir()}==before
        external=postseal_output.output_file(p,'compile-report',internal.name)
        assert external.is_file() and external.with_suffix('.source_receipt.json').is_file()
    else:
        assert internal.is_file()
        assert not postseal_output.output_file(p,'compile-report',internal.name).exists()
    assert sapote_workflow.s7_compile(str(p),None,{})[0]==sapote_workflow.PASS


@pytest.mark.parametrize('case',['identity','checksum','manifest'])
def test_validation_refusal_keeps_field_and_validate_command(tmp_path,monkeypatch,case):
    p=package(tmp_path,True);before={f.name:f.read_bytes() for f in p.iterdir()}
    result={'identity_binding':'PASS','manifest_parse':'PASS','checksum_integrity':'PASS'}
    if case=='identity':result.update(identity_binding='FAIL',identity_binding_detail='synthetic identity conflict')
    if case=='checksum':result.update(checksum_integrity='FAIL',checksum_errors=['missing synthetic board'])
    if case=='manifest':result['manifest_parse']='FAIL'
    monkeypatch.setattr(validate,'validate_package',lambda *a:result)
    with pytest.raises(SystemExit) as error:cr.compile_report_command(SimpleNamespace(package_dir=str(p)))
    message=str(error.value)
    field={'identity':'identity_binding','checksum':'checksum_integrity','manifest':'manifest_parse'}[case]
    assert 'REFUSED' in message and field in message and f'mamey validate {p}' in message
    assert {f.name:f.read_bytes() for f in p.iterdir()}==before


@pytest.mark.parametrize('name',['test_compile_report_refuses_a_package_that_no_longer_validates',
                                'test_compile_report_refuses_manifest_identity_swap',
                                'test_compile_report_still_runs_on_a_valid_package'])
def test_original_hostile_reader_assertions_with_mocked_engine_boundary(tmp_path,monkeypatch,name):
    spec=importlib.util.spec_from_file_location('legacy_hostile_reader',ROOT/'tests/test_hostile_gates_round4_v97409.py')
    legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
    mocked_report_engine(monkeypatch)
    def validation(p):
        manifest=json.loads((p/'manifest.json').read_text())
        return {'identity_binding':'PASS' if manifest.get('strain_id')=='TEST-01' else 'FAIL',
                'identity_binding_detail':'synthetic identity fixture', 'manifest_parse':'PASS',
                'checksum_integrity':'PASS' if (p/'TEST-01_4_triage_board.csv').exists() else 'FAIL',
                'checksum_errors':[] if (p/'TEST-01_4_triage_board.csv').exists() else ['missing triage board']}
    monkeypatch.setattr(validate,'validate_package',validation)
    monkeypatch.setattr(legacy,'_package',lambda path:package(path,True))
    def run(args):
        assert args[0]=='compile-report'
        out,err=io.StringIO(),io.StringIO()
        with redirect_stdout(out),redirect_stderr(err):
            try:rc=cr.compile_report_command(SimpleNamespace(package_dir=args[1],out=None,no_figures=True,pdf=False,strict=False,toc_depth=1))
            except SystemExit as error:rc=1;err.write(str(error))
        return SimpleNamespace(returncode=rc,stdout=out.getvalue(),stderr=err.getvalue())
    monkeypatch.setattr(legacy,'_run',run)
    getattr(legacy,name)(tmp_path)


def test_summary_reading_guard_is_retained_in_pdf_caption_receipt(tmp_path):
    from matplotlib.backends.backend_pdf import PdfPages
    from mamey import render_brief as rb
    from mamey.figure_policy import matplotlib_visible_text, figure_text_violations
    from pypdf import PdfReader
    plt=rb._setup_mpl()
    facts={'manifest':{'strain_id':'SYNTH'},'strain_label':'SYNTH','release':'fixture','rows':[]}
    seen=[]
    original=plt.close
    def capture(fig):
        if hasattr(fig,'texts'):seen.extend(matplotlib_visible_text(fig))
        original(fig)
    plt.close=capture
    buffer=io.BytesIO()
    try:
        with PdfPages(buffer) as pdf:caption=rb._text_page(pdf,plt,facts,'brief')
    finally:plt.close=original
    assert not figure_text_violations(seen)
    assert rb.KCB_NOTE not in '\n'.join(seen)
    assert caption['reading_guards']==[rb.KCB_NOTE]
    reader=PdfReader(buffer)
    notes=[str(annotation.get_object().get('/Contents','')) for page in reader.pages for annotation in page.get('/Annots',[])]
    assert any(rb.KCB_NOTE in note for note in notes)


def test_dangling_seal_marker_cannot_select_mutable_construction_route(tmp_path,monkeypatch):
    p=package(tmp_path)
    (p/'checksums_sha256.txt').symlink_to(p/'missing-checksum-target')
    monkeypatch.setattr(validate,'validate_package',lambda *a:{'identity_binding':'PASS','manifest_parse':'PASS','checksum_integrity':'PASS'})
    def forbidden(*a,**kw):raise AssertionError('mutable builder must not run')
    monkeypatch.setattr(cr,'build_report',forbidden)
    with pytest.raises(ValueError,match='POSTSEAL_PACKAGE_SYMLINK'):
        cr.compile_report_command(SimpleNamespace(package_dir=str(p),out=None))
    assert not (p/'TEST-01_compiled_report.md').exists()
    assert (p/'checksums_sha256.txt').is_symlink()


def test_mutable_workflow_report_is_not_hidden_by_stale_external_reader(tmp_path,monkeypatch):
    p=package(tmp_path)
    monkeypatch.setattr(validate,'validate_package',lambda *a:{'identity_binding':'PASS','manifest_parse':'PASS','checksum_integrity':'PASS'})
    mocked_report_engine(monkeypatch)
    old=postseal_output.output_file(p,'compile-report','TEST-01_compiled_report.md')
    old.parent.mkdir(parents=True);old.write_text('# obsolete unbound reader\n')
    old.with_suffix('.source_receipt.json').write_text('{}')
    assert cr.compile_report_command(SimpleNamespace(package_dir=str(p),out=None,no_figures=True,pdf=False,strict=False,toc_depth=1))==0
    assert sapote_workflow.s7_compile(str(p),None,{})[0]==sapote_workflow.PASS
    assert old.read_text()=='# obsolete unbound reader\n'
