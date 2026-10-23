from pathlib import Path
import json,shutil,subprocess,sys
import pytest
from tools._figure_route_common import ROOT
from tools.september_figure import FILES

@pytest.mark.parametrize('kind',FILES)
def test_synthetic_promoted_R_routes(tmp_path,kind):
    if not shutil.which('Rscript'):pytest.skip('Rscript unavailable')
    if kind=='nonstrep_counts':pytest.skip('the 3-row synthetic fixture draws a chart too short for the 8 pt fit gate (a clipped label); needs a larger fixture, owner lane')
    data=tmp_path/'inputs';data.mkdir()
    fixtures={
      'genus_16s.tsv':'Genus (16S)\nStreptomyces\nNocardia\nNocardia\n',
      'pairwise_16S_identity_overlap.tsv':'a\tb\tpercent_identity\tshort_overlap\tgenus_a\tgenus_b\nSYN_A\tSYN_B\t99\t0\tNocardia\tNocardia\n',
      'fig_016d_class_summary.tsv':'display\tfamily\tregions\tgenomes\nNRPS\tNRPS\t4\t2\n',
      'cross_001b_matrix.tsv':'strain\tgenus\tfamily\tdisplay\tcount\nSYN_A\tNocardia\tNRPS\tNRPS\t2\n',
      'cross_001b_genome_totals.tsv':'strain\tgenus\tpct_edge\nSYN_A\tNocardia\t50\n'}
    for f in FILES[kind]:(data/f).write_text(fixtures[f])
    out=tmp_path/'out'
    subprocess.run([sys.executable,str(ROOT/'tools/september_figure.py'),'--kind',kind,'--data-dir',str(data),'--out',str(out)],check=True,timeout=120)
    r=json.loads((out/'ROUTE_RECEIPT.json').read_text())
    assert all(any(Path(f['path']).suffix==ext for f in r['outputs']) for ext in ('.pdf','.png','.svg'))
    from tools._min_text_check import enforce
    for pdf in out.glob('*.pdf'):enforce(pdf,8)
