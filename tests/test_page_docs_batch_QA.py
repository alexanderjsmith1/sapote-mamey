"""All page companions are available before the one folder-wide QA operation."""
from pathlib import Path
import json,sys,pytest
from tools import protein_pcoa_page_docs as docs
from tests.test_page_receipt_finalization import attempt,ppr

def test_multiple_sets_write_all_companions_then_QA_once(attempt,monkeypatch):
    run,out,meta,names,root,original_qc=attempt
    kit=meta.parent
    # Small second set; no rendering or numerical fitting.
    (kit/'out_KS2').mkdir()
    (kit/'out_KS2/PCOA_KS2.tsv').write_bytes((kit/'out_KS/PCOA_KS.tsv').read_bytes())
    (kit/'out_KS2/RUN_KS2.json').write_bytes((kit/'out_KS/RUN_KS.json').read_bytes())
    (kit/'KS2_META.tsv').write_bytes(meta.read_bytes())
    created=[];calls=[]
    def page(a,s,*args,**kw):
        (out/f'{s}.svg').write_text('<svg/>');return dict(set=s,prefix=s)
    monkeypatch.setattr(ppr,'build_page',page)
    def write(out,rec,*args):
        paths={key:out/f'{rec["set"]}_{key}.md' for key in ['caption','methods','genomes']}
        for path in paths.values():path.write_text('Synthetic companion.\n')
        created.append(rec['set']);return dict(paths,print_width_in=7.2)
    def check(out,root,pages):
        assert set(created)=={'KS','KS2'} and len(pages)==2
        assert all(page[key].is_file() for page in pages for key in ['caption','methods','genomes'])
        calls.append(pages);return original_qc(out,root,pages)
    monkeypatch.setattr(docs,'write_page_docs',write);monkeypatch.setattr(docs,'check_page_docs',check)
    assert run()==0 and len(calls)==1
    assert json.loads((out/'render_receipt.json').read_text())['completion_state']=='COMPLETE'

def test_batch_checks_all_text_paths_and_runs_one_process(tmp_path,monkeypatch):
    import caption_guard
    pages=[]
    for name in ['first','second']:
        page={key:tmp_path/f'{name}_{key}.md' for key in ['caption','methods']}
        for path in page.values():path.write_text('Synthetic text.\n')
        pages.append(dict(page,print_width_in=7.2))
    scans=[];commands=[]
    monkeypatch.setattr(caption_guard,'scan_paths',lambda paths:scans.append(paths) or {})
    def subprocess(command,**kw):
        commands.append(command);return docs.subprocess.CompletedProcess(command,0,'checked 2; errors 0, warnings 0','')
    monkeypatch.setattr(docs.subprocess,'run',subprocess)
    assert docs.check_page_docs(tmp_path,tmp_path,pages)['figure_render_qc_exit']==0
    assert len(scans[0])==4 and len(commands)==1
    assert commands[0][0]==sys.executable

def test_mixed_page_widths_refuse_before_QA(tmp_path):
    with pytest.raises(ValueError,match='common declared page width'):
        docs.check_page_docs(tmp_path,tmp_path,[dict(print_width_in=7.2),dict(print_width_in=6.6)])
