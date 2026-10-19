from pathlib import Path
import os,importlib.util,json,hashlib
import pytest
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
qc=load('native_raster_qc',ROOT/'tools/figure_render_qc.py')
ppr=load('native_raster_page',ROOT/'tools/protein_pcoa_render.py')
def png(path,width=2160,dpi=300):
    im=Image.new('RGB',(width,1200),'#336699');im.save(path,**({'dpi':(dpi,dpi)} if dpi else {}));return path

def test_high_metadata_dpi_meets_minimum_without_warning(tmp_path):
    p=png(tmp_path/'hi.png',4320,600);f=qc.check_image(p,300)
    assert not any(lv=='warn' and 'dpi' in text.lower() for lv,text in f)
    assert any('effective DPI NOT_CHECKED' in text for _,text in f)

def test_thumbnail_metadata_does_not_rescue_declared_width(tmp_path):
    p=png(tmp_path/'thumb.png',300,600);f=qc.check_image(p,300,7.2)
    assert any(lv=='error' and 'effective DPI 41.67' in text for lv,text in f)

@pytest.mark.parametrize('width,dpi',[(2160,600),(4320,None),(2160,300)])
def test_native_pixel_floor_independent_of_metadata(tmp_path,width,dpi):
    p=png(tmp_path/'native.png',width,dpi);f=qc.check_image(p,300,7.2)
    assert not any(lv=='error' for lv,_ in f)
    assert any('native render provenance not verified' in text for _,text in f)

def test_low_metadata_is_reported_separately_from_sufficient_pixels(tmp_path):
    p=png(tmp_path/'low_meta.png',2160,72);f=qc.check_image(p,300,7.2)
    assert any(lv=='warn' and 'metadata DPI' in text for lv,text in f)
    assert not any(lv=='error' for lv,_ in f)

@pytest.mark.parametrize('width',['nan','inf','0','-1'])
def test_invalid_cli_width_refuses_before_qa_write(tmp_path,width):
    p=png(tmp_path/'native.png');out=tmp_path/'qa'
    with pytest.raises(SystemExit) as e:qc.main([str(p),'--out',str(out),'--print-width-in',width])
    assert e.value.code==2 and not out.exists()

def test_page_raster_binding_covers_direct_outputs(tmp_path):
    prefix=tmp_path/'PAGE';paths=[png(Path(str(prefix)+'.png'),4320,600),png(Path(str(prefix)+'_plot_only.png'),2160,300)]
    hashes=[hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
    rec=ppr.page_raster_artifacts(prefix,7.2)
    assert [r['sha256'] for r in rec]==hashes and [r['effective_dpi_by_width'] for r in rec]==[600,300]
    assert [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]==hashes
    assert all(r['provenance']=='DIRECT_NATIVE_R_RENDER_BY_BOUND_SOURCE' for r in rec)

def test_missing_plot_only_refuses_instead_of_copying_png(tmp_path):
    prefix=tmp_path/'PAGE';png(Path(str(prefix)+'.png'),4320,600)
    with pytest.raises(ppr.RenderRefusal,match='native raster missing'):ppr.page_raster_artifacts(prefix,7.2)
    assert not Path(str(prefix)+'_plot_only.png').exists()

def test_native_page_thumbnail_is_refused(tmp_path):
    prefix=tmp_path/'PAGE';png(Path(str(prefix)+'.png'),4320,600);png(Path(str(prefix)+'_plot_only.png'),300,600)
    with pytest.raises(ppr.RenderRefusal,match='native-pixel floor'):ppr.page_raster_artifacts(prefix,7.2)
