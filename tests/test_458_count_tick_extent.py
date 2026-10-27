"""Native SVG regression for a clipped outer count-axis label."""
from pathlib import Path
import os,re,shutil,subprocess,xml.etree.ElementTree as ET
import pytest
pytestmark=pytest.mark.slow
@pytest.mark.parametrize('profile',['SINGLE_COLUMN','DOUBLE_COLUMN'])
def test_numeric_text_fits_saved_canvas(tmp_path,profile):
 if not shutil.which('Rscript'):pytest.skip('Native Rscript required')
 tools=Path(os.environ.get('SAPOTE_STRAIN_TOOLS',Path(__file__).resolve().parents[1]/'tools'))
 source=tmp_path/'generic.csv';source.write_text('category,count\nAlpha,24\nBeta,22\nGamma,101\nDelta,71\n')
 out=tmp_path/'count'
 r=subprocess.run(['Rscript',str(tools/'sapote_strain_figure.R'),str(source),str(out),profile,'Generic counts'],capture_output=True,text=True,cwd=tmp_path)
 assert r.returncode==0,r.stdout+r.stderr
 assert not (tmp_path/'Rplots.pdf').exists(),'Text sizing must not open a default device'
 assert 'font family' not in r.stderr,r.stderr
 root=ET.parse(out.with_suffix('.svg')).getroot();width=float(root.get('width').removesuffix('pt'));labels=[]
 for t in root.iter('{http://www.w3.org/2000/svg}text'):
  if not re.fullmatch(r'\d+',t.text or ''):continue
  x=float(t.get('x'));length=float(t.get('textLength').removesuffix('px'));anchor=t.get('text-anchor','start');left=x-length*(.5 if anchor=='middle' else 1 if anchor=='end' else 0)
  assert 0<=left and left+length<=width,(t.text,left,left+length,width)
  labels.append(t.text)
 assert all(str(n) in labels for n in [24,22,101,71]),'Count annotations must remain intact'
 assert '125' in labels,'Preserve the original terminal tick rather than suppressing it'
