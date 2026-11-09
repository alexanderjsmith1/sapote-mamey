from pathlib import Path
import builtins,hashlib,importlib.util,json,os,sys,types
import pytest
import shutil

pytestmark=pytest.mark.skipif(not (os.environ.get('PANDOC') or shutil.which('pandoc')),reason='pandoc not installed')

HERE=Path(__file__).resolve().parent
from tools import prepare_pdf_resources as module
def setup(tmp_path):
 source=tmp_path/'source';source.mkdir();svg=source/'panel.svg';svg.write_text('<svg><!-- Sapote-Mamey R figure theme --></svg>')
 md=source/'source.md';md.write_text('![panel](panel.svg)\n');destination=tmp_path/'work'/'safe.md';destination.parent.mkdir();return svg,md,destination
def fake_converter(url,write_to):Path(write_to).write_bytes(b'%PDF-1.4 synthetic test bytes')
def test_receipt_binds_source_and_converted_bytes(tmp_path,monkeypatch):
 svg,md,dest=setup(tmp_path);monkeypatch.setitem(sys.modules,'cairosvg',types.SimpleNamespace(svg2pdf=fake_converter))
 module.prepare(md,dest);receipt=next(dest.parent.glob('*.pdf.conversion.json'));r=json.loads(receipt.read_text());pdf=Path(r['converted_pdf'])
 assert r['source_svg']==str(svg.resolve()) and r['source_svg_sha256']==hashlib.sha256(svg.read_bytes()).hexdigest()
 assert r['converted_pdf_sha256']==hashlib.sha256(pdf.read_bytes()).hexdigest() and r['converter']=='cairosvg'
 assert 'neither renderer provenance' in r['scope']
 assert dest.read_text()==md.read_text()
 assert json.loads(dest.with_suffix('.resource_map.json').read_text())['targets']=={'panel.svg':str(pdf)}
def test_source_change_is_refused(tmp_path,monkeypatch):
 svg,md,dest=setup(tmp_path)
 def changed(url,write_to):fake_converter(url,write_to);Path(url).write_text('<svg>changed</svg>')
 monkeypatch.setitem(sys.modules,'cairosvg',types.SimpleNamespace(svg2pdf=changed))
 with pytest.raises(ValueError,match='PDF_SVG_SOURCE_CHANGED_DURING_CONVERSION'):module.prepare(md,dest)
 assert not dest.exists() and not list(dest.parent.glob('*.conversion.json'))
def test_non_svg_resource_does_not_gain_conversion_receipt(tmp_path):
 svg,md,dest=setup(tmp_path);im=svg.with_name('a.png');im.write_bytes(b'fixture');md.write_text('![a](a.png)')
 module.prepare(md,dest);assert dest.read_text()==md.read_text() and not list(dest.parent.glob('*.conversion.json'))
 assert json.loads(dest.with_suffix('.resource_map.json').read_text())['targets']=={'a.png':str(im.resolve())}
def test_local_fallback_reports_actual_converter(tmp_path,monkeypatch):
 svg,md,dest=setup(tmp_path);original=builtins.__import__
 def fail_cairo(name,*args,**kwargs):
  if name=='cairosvg':raise ImportError('simulated')
  return original(name,*args,**kwargs)
 real_run=module.subprocess.run;real_which=module.shutil.which
 # The preparer parses with pandoc first; only the SVG converter lookup is simulated.
 def run(args,*args2,**kwargs):
  if args[0]=='rsvg-convert':
   assert kwargs.get('check');Path(args[4]).write_bytes(b'%PDF fallback test');return None
  return real_run(args,*args2,**kwargs)
 monkeypatch.setattr(builtins,'__import__',fail_cairo);monkeypatch.setattr(module.shutil,'which',lambda n:'/local/rsvg-convert' if n=='rsvg-convert' else (real_which(n) if n=='pandoc' else None));monkeypatch.setattr(module.subprocess,'run',run)
 module.prepare(md,dest);r=json.loads(next(dest.parent.glob('*.pdf.conversion.json')).read_text());assert r['converter']=='rsvg-convert'
