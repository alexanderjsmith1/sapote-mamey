import hashlib,json
from pathlib import Path
from urllib.parse import unquote,urlsplit
from PIL import Image
from pypdf import PdfReader
import pytest
from mamey import compile_report,markdown_pdf

@pytest.mark.parametrize('absolute_companions',[False,True])
def test_primary_pdf_companion_targets_source_relative_to_output(tmp_path,absolute_companions):
    pkg=tmp_path/'source package';folder=pkg/'figure folder';folder.mkdir(parents=True)
    png=folder/'one.png';svg=folder/'one.svg';Image.new('RGB',(12,12),'red').save(png);svg.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
    def info(p):return {'logical_locator':p.relative_to(pkg).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
    (pkg/'figure_receipts.jsonl').write_text(json.dumps({'outputs':{'png':info(png),'svg':info(svg)}})+'\n')
    report=pkg/'report.md';report.write_text('# Synthetic report\n\n'+compile_report._figures(pkg,generate=False,absolute_companions=absolute_companions))
    out=tmp_path/'elsewhere'/'report.pdf';out.parent.mkdir();markdown_pdf.render(report,out)
    uris=[]
    for page in PdfReader(str(out)).pages:
        for raw in page.get('/Annots',[]):
            annotation=raw.get_object();action=annotation.get('/A',{}).get_object()
            if '/URI' in action:uris.append(str(action['/URI']))
    assert len(uris)==1,uris
    url=urlsplit(uris[0]);assert not url.scheme and not url.netloc
    target=out.parent/unquote(url.path)
    assert target.resolve()==svg.resolve() and target.is_file()

def test_primary_wrapper_rebases_link_for_final_output_and_portable_tree(tmp_path):
    import os,shutil,subprocess,sys
    root=Path(__file__).resolve().parents[1];tree=tmp_path/'tree';pkg=tree/'source package';folder=pkg/'figure & folder';folder.mkdir(parents=True)
    png=folder/'one.png';svg=folder/'one.svg';Image.new('RGB',(12,12),'blue').save(png);svg.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
    def info(p):return {'logical_locator':p.relative_to(pkg).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
    (pkg/'figure_receipts.jsonl').write_text(json.dumps({'outputs':{'png':info(png),'svg':info(svg)}})+'\n')
    report=pkg/'report.md';report.write_text('# Synthetic report\n\n'+compile_report._figures(pkg,generate=False))
    out=tree/'elsewhere'/'report.pdf';out.parent.mkdir();env=dict(os.environ,PYTHON=sys.executable,PYTHONPATH=str(root));q=subprocess.run(['bash',str(root/'tools/md_to_pdf.sh'),str(report),str(out)],env=env,capture_output=True,text=True)
    assert q.returncode==0,(q.stdout,q.stderr);assert 'colorful reportlab' in q.stdout
    annotations=[v.get_object() for page in PdfReader(str(out)).pages for v in page.get('/Annots',[])];uris=[str(a['/A']['/URI']) for a in annotations if '/A' in a and '/URI' in a['/A']];assert len(uris)==1
    assert (out.parent/unquote(urlsplit(uris[0]).path)).resolve()==svg.resolve()
    moved=tmp_path/'moved tree';shutil.copytree(tree,moved);moved_out=moved/'elsewhere/report.pdf';moved_svg=moved/'source package/figure & folder/one.svg';assert (moved_out.parent/unquote(urlsplit(uris[0]).path)).resolve()==moved_svg.resolve() and moved_svg.exists()

def test_unverified_or_nonlocal_companions_stay_plain_text(tmp_path):
    s=markdown_pdf.inline('[SVG version](<missing.svg>) and [SVG version](<https://example.org/x.svg>)',companion_base=tmp_path,link_output_dir=tmp_path)
    assert '<link ' not in s and s.count('SVG version')==2
