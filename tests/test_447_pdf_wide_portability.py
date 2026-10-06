"""Minimal numerical/text/image fixtures; no biological inputs or external engine."""
import json,os,subprocess,sys
from pathlib import Path
import pytest
from mamey import markdown_pdf as pdf
ROOT=Path(__file__).resolve().parents[1]


def test_43_columns_and_long_last_cell_are_retained_in_real_pdf(tmp_path):
    headers=[f'Field{i:02}' for i in range(43)]
    values=[f'Value{i:02}' for i in range(43)];values[-1]='x'*650+'TAIL_SENTINEL'
    md=tmp_path/'wide.md';md.write_text('# Wide synthetic table\n\n|'+'|'.join(headers)+'|\n|'+'|'.join(['---']*43)+'|\n|'+'|'.join(values)+'|\n')
    out=tmp_path/'wide.pdf';pdf.render(md,out)
    from pypdf import PdfReader
    extracted='\n'.join(page.extract_text() for page in PdfReader(out).pages)
    assert out.stat().st_size>1000
    for field in headers:assert field in extracted
    for value in values[:-1]:assert value in extracted
    assert 'TAIL_SENTINEL' in extracted


def test_primary_shell_route_different_cwd_and_space_image_path(tmp_path):
    from PIL import Image
    source=tmp_path/'source space';source.mkdir();Image.new('RGB',(100,80),'blue').save(source/'image space.png')
    md=source/'report.md';md.write_text('# Portable\n\n![image](<image space.png>)\n')
    caller=tmp_path/'caller';caller.mkdir();out=caller/'portable.pdf'
    r=subprocess.run(['bash',str(ROOT/'tools/md_to_pdf.sh'),str(md),str(out)],cwd=caller,capture_output=True,text=True)
    assert r.returncode==0,r.stderr
    assert out.is_file()
    from pypdf import PdfReader
    assert any(page.images for page in PdfReader(out).pages)


def test_missing_image_refuses_instead_of_placeholder(tmp_path):
    md=tmp_path/'bad.md';md.write_text('# Image\n\n![missing](missing.png)\n')
    with pytest.raises(ValueError,match='PDF_IMAGE_UNAVAILABLE'):pdf.render(md,tmp_path/'bad.pdf')
    assert not (tmp_path/'bad.pdf').exists()


def test_resource_preflight_preserves_original_relative_image(tmp_path):
    import importlib.util
    spec=importlib.util.spec_from_file_location('pdf_resources',ROOT/'tools/prepare_pdf_resources.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    source=tmp_path/'source';source.mkdir();image=source/'a.png';image.write_bytes(b'fixture')
    md=source/'a.md';md.write_text('![a](a.png)\n');dest=tmp_path/'temp'/'safe.md';dest.parent.mkdir()
    mod.prepare(md,dest);assert str(image.resolve()) in dest.read_text()


def test_extra_table_cells_are_refused_not_clipped():
    with pytest.raises(ValueError,match='COLUMN_MISMATCH'):pdf.md_table([['a'],['1','2']])


def test_fallback_passes_absolute_resources_and_reports_missing_dependencies(tmp_path):
    import shutil
    from PIL import Image
    source=tmp_path/'source space';source.mkdir();Image.new('RGB',(10,10),'red').save(source/'panel.png')
    md=source/'a.md';md.write_text('# Fallback\n\n![panel](panel.png)\n')
    caller=tmp_path/'caller';caller.mkdir();bins=tmp_path/'bin';bins.mkdir();log=tmp_path/'pandoc_log.json'
    wrapper=bins/'python3'
    wrapper.write_text('#!'+sys.executable+'\nimport os,sys\nif len(sys.argv)>1 and sys.argv[1].endswith("render_deliverable_pdf.py"):raise SystemExit(1)\nos.execv('+repr(sys.executable)+', ['+repr(sys.executable)+']+sys.argv[1:])\n');wrapper.chmod(0o755)
    pandoc=bins/'pandoc';pandoc.write_text('#!'+sys.executable+'\nimport sys,json,pathlib\nargs=sys.argv[1:];pathlib.Path('+repr(str(log))+').write_text(json.dumps({"argv":args,"markdown":pathlib.Path(args[0]).read_text()}))\npathlib.Path(args[args.index("-o")+1]).write_text("fixture latex")\n');pandoc.chmod(0o755)
    latex=bins/'xelatex';latex.write_text('#!'+sys.executable+'\nimport pathlib,sys\nout=next(a.split("=",1)[1] for a in sys.argv if a.startswith("-output-directory="))\n(pathlib.Path(out)/"d.pdf").write_bytes(b"%PDF mocked latex output")\n');latex.chmod(0o755)
    env=dict(os.environ,PATH=str(bins)+os.pathsep+os.environ['PATH']);out=caller/'out.pdf'
    r=subprocess.run(['bash',str(ROOT/'tools/md_to_pdf.sh'),str(md),str(out)],cwd=caller,env=env,capture_output=True,text=True)
    assert r.returncode==0,r.stderr
    receipt=json.loads(log.read_text());assert str(source/'panel.png') in receipt['markdown']
    assert '--resource-path='+str(source) in receipt['argv']
    latex.unlink();out.unlink()
    # A forced primary failure cannot claim success when fallback is unavailable.
    r=subprocess.run(['bash',str(ROOT/'tools/md_to_pdf.sh'),str(md),str(out)],cwd=caller,env=env,capture_output=True,text=True)
    assert r.returncode==2 and 'PDF_TOOLCHAIN_UNAVAILABLE' in r.stderr and not out.exists()
