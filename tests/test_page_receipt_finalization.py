from pathlib import Path
import os,sys,json,hashlib,importlib.util
import pytest
from tools import protein_pcoa_render as current
from tools import protein_pcoa_page_docs as page_docs
p=Path(os.environ.get('LANE06_FINAL_CANDIDATE',current.__file__))
spec=importlib.util.spec_from_file_location('page_final_candidate',p)
ppr=importlib.util.module_from_spec(spec);spec.loader.exec_module(ppr)

@pytest.fixture
def attempt(tmp_path,monkeypatch):
    root=tmp_path/'root'
    for name in ['mamey/figure_policy.py','tools/protein_pcoa_page.R','tools/protein_pcoa_page_docs.py','tools/protein_pcoa_render.R']:
        path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('producer fixture\n')
    monkeypatch.setattr(ppr,'_ROOT',root);monkeypatch.setattr(ppr,'R_SCRIPT',root/'tools/protein_pcoa_render.R')
    monkeypatch.setattr(ppr,'discover_rscript',lambda:sys.executable)
    d=tmp_path/'kit/out_KS';d.mkdir(parents=True)
    (d/'PCOA_KS.tsv').write_text('id\tPC1\tPC2\tn_represented\tsource\tstrain\np1\t0\t0\t1\treference\tR\np2\t1\t1\t1\treference\tR\np3\t2\t2\t1\tisolate\tSYN_Q\n')
    (d/'RUN_KS.json').write_text('{"pct_axes":[40,20]}')
    meta=tmp_path/'kit/KS_META.tsv';meta.write_text('strain\tsource\nR\treference\n')
    names=tmp_path/'names.tsv';names.write_text('strain\tdisplay\nSYN_Q\tSynthetic Q\n')
    (tmp_path/'cohort.tsv').write_text('strain\tcohort\nSYN_Q\tg\n')
    out=tmp_path/'out'
    def page(*a,**kw):
        out.joinpath('figure.svg').write_text('<svg/>');return {'set':'KS','prefix':'TEST'}
    monkeypatch.setattr(ppr,'build_page',page)
    def docs(out,rec,render,rows,names,note,stamp):
        # Final receipt must not exist while companions are incomplete.
        out.joinpath('receipt_during_docs.txt').write_text(str((out/'render_receipt.json').exists()))
        paths={k:out/(k+'.md') for k in ['caption','methods','genomes']}
        for path in paths.values():path.write_text('synthetic companion\n')
        return paths
    def qc(out,root,docs):
        out.joinpath('receipt_during_qc.txt').write_text(str((out/'render_receipt.json').exists()))
        (out/'QC_RENDER').mkdir();(out/'QC_RENDER/result.json').write_text('{}')
        (out/'QC_SUMMARY.json').write_text('{}')
        return dict(caption_guard={},figure_render_qc_exit=0,figure_render_qc='errors 0, warnings 0')
    monkeypatch.setattr(page_docs,'write_page_docs',docs);monkeypatch.setattr(page_docs,'check_page_docs',qc)
    def run():return ppr.main(['--kit',str(tmp_path/'kit'),'--out',str(out),'--panel','g=g','--cohort-table',str(tmp_path/'cohort.tsv'),'--page','pcoa','--renderer','r','--label-names',str(names)])
    return run,out,meta,names,root,qc

def test_success_receipt_written_last_hashes_all_companions(attempt):
    run,out,*_=attempt;assert run()==0
    assert (out/'receipt_during_docs.txt').read_text()=='False'
    assert (out/'receipt_during_qc.txt').read_text()=='False'
    receipt=json.loads((out/'render_receipt.json').read_text());assert receipt['completion_state']=='COMPLETE'
    bindings={Path(x['path']).relative_to(out).as_posix():x for x in receipt['outputs']}
    assert {'caption.md','methods.md','genomes.md','QC_SUMMARY.json','QC_RENDER/result.json'}<=bindings.keys()
    assert 'render_receipt.json' not in bindings
    for name,b in bindings.items():assert b['sha256']==hashlib.sha256((out/name).read_bytes()).hexdigest()

@pytest.mark.parametrize('bad',[dict(caption_guard={'bad':['finding']},figure_render_qc_exit=0,figure_render_qc='errors 0,'),dict(caption_guard={},figure_render_qc_exit=1,figure_render_qc='errors 0,'),dict(caption_guard={},figure_render_qc_exit=0,figure_render_qc='errors 1,')])
def test_failed_qc_has_no_completion_receipt(attempt,monkeypatch,bad):
    run,out,*_=attempt;monkeypatch.setattr(page_docs,'check_page_docs',lambda *a:bad)
    assert run()==2 and not (out/'render_receipt.json').exists()
    assert (out/'caption.md').is_file()

@pytest.mark.parametrize('changed',['metadata','names','producer'])
def test_late_drift_has_no_completion_receipt(attempt,monkeypatch,changed):
    run,out,meta,names,root,qc=attempt
    path={'metadata':meta,'names':names,'producer':root/'tools/protein_pcoa_page_docs.py'}[changed]
    def changed_qc(*a):
        result=qc(*a);path.write_text(path.read_text()+'\n');return result
    monkeypatch.setattr(page_docs,'check_page_docs',changed_qc)
    assert run()==2 and not (out/'render_receipt.json').exists()

def test_companion_refusal_has_no_completion_receipt(attempt,monkeypatch):
    run,out,*_=attempt
    def fail(*a):raise ppr.RenderRefusal('companion fixture refused')
    monkeypatch.setattr(page_docs,'write_page_docs',fail)
    assert run()==2 and not (out/'render_receipt.json').exists()
    assert (out/'figure.svg').is_file()
