"""Check file metadata at actual R export boundaries, not just source tokens."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import pytest
from PIL import Image
from tools.check_figure_provenance import stamp

ROOT=Path(__file__).resolve().parents[1]

def module(name,filename):
    spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name(filename))
    obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj);return obj

def run_r(script,tmp_path,extra=None):
    env=dict(os.environ,**(extra or {}))
    result=subprocess.run(['Rscript','-e',script,str(ROOT),str(tmp_path)],cwd=tmp_path,env=env,capture_output=True,text=True)
    return result

def assert_stamped(paths,tool):
    for p in paths:
        verdict,evidence=stamp(p)
        assert verdict=='PASS' and tool in evidence,(p,verdict,evidence)

@pytest.mark.skipif(shutil.which("Rscript") is None, reason="needs R: Rscript not on PATH (see bundle_support/install_r_figure_packages.R)")
def test_shared_export_and_probe_stamp(tmp_path):
    result=run_r('''
      a<-commandArgs(TRUE); root<-a[1]; out<-a[2]
      library(ggplot2)
      source(file.path(root,"tools/sapote_pub_layout.R"))
      source(file.path(root,"tools/sapote_min_text.R"))
      p<-ggplot(data.frame(x=c(1,2),y=c(2,1)),aes(x,y))+geom_point()+theme_classic(base_size=8)+labs(title="Synthetic")
      mt_probe(p,file.path(out,"probe"),7.2,3,list(min_text_pt=8))
      mt_save(p,file.path(out,"saved"),7.2,3,list(min_text_pt=8,dpi=300))
    ''',tmp_path)
    assert result.returncode==0,result.stdout+result.stderr
    assert_stamped([tmp_path/'probe.pdf'],'sapote_min_text_probe')
    assert_stamped([tmp_path/'saved.png',tmp_path/'saved.pdf'],'sapote_min_text')
    assert_stamped([tmp_path/'saved_text_check.svg'],'sapote_min_text_check')

@pytest.mark.skipif(shutil.which("Rscript") is None, reason="needs R: Rscript not on PATH (see bundle_support/install_r_figure_packages.R)")
@pytest.mark.parametrize('failure',['missing_script','nonzero_exit'])
def test_required_stamper_fails_closed(tmp_path,failure):
    target=tmp_path/'plain.png';Image.new('RGB',(10,10),'white').save(target)
    script=tmp_path/'stamp.py'
    if failure=='nonzero_exit':script.write_text('raise SystemExit(7)\n')
    result=run_r('''a<-commandArgs(TRUE);source(file.path(a[1],"tools/sapote_stamp_required.R"));sapote_stamp_files_required(file.path(a[2],"plain.png"),"synthetic")''',tmp_path,{'SAPOTE_STAMP_SCRIPT':str(script)})
    assert result.returncode!=0 and 'FIGURE_STAMP_REQUIRED' in result.stderr
    assert stamp(target)[0]!='PASS'

@pytest.mark.skipif(shutil.which("Rscript") is None, reason="needs R: Rscript not on PATH (see bundle_support/install_r_figure_packages.R)")
def test_direct_bioassay_r_stamps(tmp_path):
    fixture=module('stamp_a04_fixture','test_452_a04_split.py')
    _,args=fixture.inputs(tmp_path,False);out=tmp_path/'out'
    from mamey.bioassay_paper import cli
    cli('A04',ROOT/'tools/bioassay_a04.R',args+['--out',str(out),'--prepare-only'])
    env=dict(os.environ,BIOASSAY_THEME=str(ROOT/'tools/bioassay_paper_theme.R'),BIOASSAY_CONFIG=str(out/'render_config.json'))
    r=subprocess.run(['Rscript',str(ROOT/'tools/bioassay_a04.R')],cwd=tmp_path,env=env,capture_output=True,text=True)
    assert r.returncode==0,r.stdout+r.stderr
    assert_stamped([*out.glob('*.png'),*out.glob('*.pdf'),*out.glob('*.svg')],'bioassay_a04')
    assert len(list(out.glob('*.pdf')))==1

@pytest.mark.skipif(shutil.which("Rscript") is None, reason="needs R: Rscript not on PATH (see bundle_support/install_r_figure_packages.R)")
def test_page_final_preview_keeps_stamp(tmp_path,monkeypatch):
    fixture=module('stamp_page_fixture','test_m5_452_pcoa_page_defaults.py');ppr=fixture.ppr
    root=fixture.make_kit(tmp_path,[('SYN-970',2.5,2.5,95.0),('SYN-971',.5,.5,30.0)])
    which=shutil.which;run=subprocess.run;replaced=[]
    monkeypatch.setattr(shutil,'which',lambda cmd,*a,**k: 'synthetic-preview' if cmd=='qlmanage' else which(cmd,*a,**k))
    def preview(cmd,*a,**k):
        if cmd[0]=='qlmanage':
            pdf=Path(cmd[-1]);folder=Path(cmd[cmd.index('-o')+1]);target=folder/(pdf.name+'.png')
            with Image.open(pdf.with_suffix('.png')) as im:im.save(target)
            assert stamp(target)[0]!='PASS'
            replaced.append(target)
            return subprocess.CompletedProcess(cmd,0,b'',b'')
        return run(cmd,*a,**k)
    monkeypatch.setattr(subprocess,'run',preview)
    assert fixture.page(root)==0
    assert replaced
    out=root/'out';prefix=out/'PAGE_KS_query_PCOA_TRIMAP'
    assert_stamped([Path(str(prefix)+ext) for ext in ('.png','.pdf','.svg')],'protein_pcoa_page')
    assert_stamped(list((out/'fit_trials_KS').glob('*.pdf')),'protein_pcoa_page')

@pytest.mark.parametrize('renderer',['matplotlib',pytest.param('r',marks=pytest.mark.skipif(shutil.which("Rscript") is None, reason="needs R: Rscript not on PATH (see bundle_support/install_r_figure_packages.R)"))])
def test_single_panel_stamps(tmp_path,renderer):
    fixture=module('stamp_panel_fixture','test_m5_452_pcoa_page_defaults.py')
    root=fixture.make_kit(tmp_path,[('SYN-970',2.5,2.5,95.0)])
    assert fixture.ppr.main(['--kit',str(root/'kit'),'--out',str(root/'out'),'--cohort-table',str(root/'cohorts.tsv'),'--panel','query=query','--panel-label','query=synthetic','--label-names',str(root/'names.tsv'),'--renderer',renderer])==0
    assert_stamped([root/'out'/('PCOA_KS_query'+ext) for ext in ('.png','.pdf','.svg')],'protein_pcoa_render')
