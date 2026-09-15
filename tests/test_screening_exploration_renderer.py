"""Portable smoke and data-contract regressions; no private data or network."""
import csv
import shutil
import subprocess
from pathlib import Path
import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'tools' / 'render_screening_exploration.R'

@pytest.fixture(scope='module')
def rscript():
    binary = shutil.which('Rscript')
    if not binary:
        pytest.skip('Optional R runtime unavailable')
    p = subprocess.run([binary, '-e', 'quit(status=ifelse(requireNamespace("ggplot2",quietly=TRUE)&&requireNamespace("patchwork",quietly=TRUE),0,1))'], capture_output=True)
    if p.returncode:
        pytest.skip('Optional ggplot2/patchwork unavailable')
    return binary

def write(folder, name, fields, rows):
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / name).open('w', newline='') as f:
        w = csv.writer(f); w.writerow(fields); w.writerows(rows)

def invoke(binary, src, dest):
    return subprocess.run([binary, str(SCRIPT), str(src), str(dest)], capture_output=True, text=True)

def test_generic_render_and_overwrite_refusal(rscript, tmp_path):
    src, out = tmp_path/'inputs', tmp_path/'figures'
    write(src, 'overlap.csv', ['category','count','total'], [['Both positive',2,10],['Candida only',1,10],['MRSA only',2,10],['Neither positive',4,10],['Not tested',1,10]])
    p = invoke(rscript,src,out)
    assert p.returncode == 0, p.stderr
    pdf=out/'01_screening_overlap.pdf'; png=out/'01_screening_overlap.png'
    assert pdf.read_bytes().startswith(b'%PDF-') and png.read_bytes().startswith(b'\x89PNG')
    before=pdf.read_bytes();p=invoke(rscript,src,out)
    assert p.returncode != 0 and 'Output exists' in p.stderr
    assert pdf.read_bytes()==before

def test_bad_denominator_fails(rscript,tmp_path):
    src=tmp_path/'inputs'
    write(src,'overlap.csv',['category','count','total'],[['Only category',2,10]])
    p=invoke(rscript,src,tmp_path/'figures')
    assert p.returncode != 0 and 'denominator' in p.stderr

def test_incomplete_concentrations_fail(rscript,tmp_path):
    src=tmp_path/'inputs'
    write(src,'concentration_observations.csv',['dataset','organism','concentration_ug_ml','inhibition_pct','assay_plate','fraction_plate','source_well'],[['Example','Target',15,20,1,1,'A1']])
    p=invoke(rscript,src,tmp_path/'figures')
    assert p.returncode != 0 and 'Incomplete or duplicate' in p.stderr

def test_complete_concentrations_preserve_out_of_range(rscript,tmp_path):
    src=tmp_path/'inputs'
    write(src,'concentration_observations.csv',['dataset','organism','concentration_ug_ml','inhibition_pct','assay_plate','fraction_plate','source_well'],[['Example','Target',c,v,1,1,'A1'] for c,v in zip([15,30,60,120],[-50,0,60,120])])
    before=(src/'concentration_observations.csv').read_bytes()
    p=invoke(rscript,src,tmp_path/'figures')
    assert p.returncode==0,p.stderr
    assert len(list((tmp_path/'figures').glob('*.pdf')))==2
    assert before==(src/'concentration_observations.csv').read_bytes()

def test_machinery_fraction_mismatch_fails(rscript,tmp_path):
    src=tmp_path/'inputs'
    write(src,'modeb_machinery.csv',['strain','family','loci_with_annotation','loci_in_snapshot','percent_loci'],[['Example','PKS_KS',2,4,99]])
    p=invoke(rscript,src,tmp_path/'figures')
    assert p.returncode != 0 and 'denominator' in p.stderr

def test_bounded_scoring_retains_raw_values(rscript,tmp_path):
    src=tmp_path/'input data';out=tmp_path/'output figures'
    write(src,'concentration_observations.csv',['dataset','organism','concentration_ug_ml','inhibition_pct','assay_plate','fraction_plate','source_well'],[['Example','Target',c,v,1,1,'A1'] for c,v in zip([15,30,60,120],[-50,0,60,120])])
    p=subprocess.run([rscript,str(SCRIPT),str(src),str(out),'--score-0-100'],capture_output=True,text=True)
    assert p.returncode==0,p.stderr
    with (out/'concentration_scored_data.csv').open() as f:rows=list(csv.DictReader(f))
    assert [float(x['raw_inhibition_pct']) for x in rows]==[-50,0,60,120]
    assert [float(x['score_0_100_pct']) for x in rows]==[0,0,60,100]
    assert (out/'03_concentrations_example_scored.pdf').exists()


def test_standalone_theme_and_relocation(rscript, tmp_path):
    import sys, zipfile
    src=tmp_path/'input tables';out=tmp_path/'preview'
    write(src,'overlap.csv',['category','count','total'],[['Both',2,10],['First',1,10],['Second',2,10],['Neither',4,10],['Untested',1,10]])
    result=invoke(rscript,src,out)
    assert result.returncode==0,result.stderr
    caption=out/'01_screening_overlap_caption.txt'
    assert 'Percentages' in caption.read_text()
    receipt=tmp_path/'receipt.json';receipt.write_text('{}')
    packet=tmp_path/'standalone packet'
    command=[sys.executable,str(SCRIPT.with_name('package_screening_figure.py')),'--figure-dir',str(out),'--figure-stem','01_screening_overlap','--data-dir',str(src),'--caption',str(caption),'--receipt',str(receipt),'--renderer',str(SCRIPT),'--session-info',str(out/'R_SESSION.txt'),'--out',str(packet)]
    result=subprocess.run(command,capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert (packet/'sapote_figure_theme.R').read_bytes()==SCRIPT.with_name('sapote_figure_theme.R').read_bytes()
    relocated=tmp_path/'different location'
    with zipfile.ZipFile(packet.with_suffix('.zip')) as z:z.extractall(relocated)
    result=subprocess.run([rscript,str(relocated/packet.name/'reproduce.R')],cwd=tmp_path,capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert (relocated/packet.name/'reproduced/01_screening_overlap.png').read_bytes()==(out/'01_screening_overlap.png').read_bytes()
