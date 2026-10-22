"""Target eligibility and actual print output for the optional three-panel layout."""
import pytest
import shutil
import json,os,subprocess,sys,math
from pathlib import Path
from PIL import Image,ImageChops
from pypdf import PdfReader
from mamey.bioassay_paper import cli,prepare,sha,write,LAYOUTS,CANDIDA
ROOT=Path(__file__).resolve().parents[1]

def inputs(tmp_path,split):
    profile=dict(next(v for k,v in json.loads(LAYOUTS.read_text()).items() if not k.startswith("_")))
    for k in ("a04_pool_candida", "a04_candida_axis_label"): profile.pop(k, None)   # these tests cover the split and pooled defaults
    for k in ("print_width_in", "a04_text_pt", "a04_point_size", "a04_axis_ticks", "a04_height_in", "a04_label_column", "a04_label_max", "a04_legend_compact"): profile.pop(k, None)   # the default print size and label/legend options (card 472)
    profile.update(split_candida=split,a04_source_shape=False,unassigned_label="Unassigned")
    profile.pop("a04_point_labels",None)   # the pixel comparison is of the earlier label rule (default "all")
    cfg=tmp_path/"profiles.json";cfg.write_text(json.dumps({"synthetic":profile}))
    table=tmp_path/"assay.tsv";roster=tmp_path/"roster.tsv";aliases=tmp_path/"aliases.json";lock=tmp_path/"lock.json"
    aliases.write_text("{}");lock.write_text("{}")
    write(roster,[dict(strain=f"SYN-{970+i}",genus="Streptomyces",group="Group A") for i in range(3)])
    values=((20,50,90,0),(30,"n.t.","+",40),(80,70,60,"−"))
    write(table,[dict(strain=f"SYN-{970+i}",organism=t,material="Crude extract",best_pct=v) for i,vals in enumerate(values) for t,v in zip((*CANDIDA,"MRSA"),vals)])
    args=["--table",str(table),"--roster",str(roster),"--aliases",str(aliases),"--lock",str(lock),"--table-sha256",sha(table),"--lock-sha256",sha(lock),"--layout","synthetic","--layout-config",str(cfg)]
    return (table,roster,aliases,cfg),args

def test_target_pairs(tmp_path):
    (t,r,a,c),_=inputs(tmp_path,True)
    plot=prepare(t,r,a,"A04","synthetic",layouts=c)["plot"]
    assert [(p["strain"],p["target"],p["x"],p["y"]) for p in plot]==[
        ("SYN-970","C. albicans",20,0),("SYN-970","C. auris",50,0),
        ("SYN-970","C. albicans or C. auris (not recorded)",90,0),("SYN-971","C. albicans",30,40)]

@pytest.mark.skipif(shutil.which("Rscript") is None, reason="needs R: Rscript not on PATH (see bundle_support/install_r_figure_packages.R)")
def test_three_panels_printed(tmp_path):
    _,args=inputs(tmp_path,True);out=tmp_path/"split"
    cli("A04",ROOT/"tools/bioassay_a04.R",args+["--out",str(out)])
    pdf=next(out.glob("*.pdf"));sizes=[];page=PdfReader(pdf).pages[0]
    text=page.extract_text(visitor_text=lambda t,cm,tm,font,size:sizes.append(size*math.hypot(tm[0]*cm[0]+tm[1]*cm[2],tm[0]*cm[1]+tm[1]*cm[3])) if t.strip() else None)
    # 7.2 in = 518.4 pt, the double-column width (card 018c0f08_453_bioassay_print_width_and_centering). Linux cairo writes
    # whole points (518), macOS writes 518.4; half a point either way is the same page.
    assert abs(float(page.mediabox.width)-518.4)<=0.5
    assert all(t in text for t in ("C. albicans","C. auris","(not recorded)"))
    code="import json,pdfplumber,sys;p=pdfplumber.open(sys.argv[1]).pages[0];print(json.dumps(p.chars))"
    chars=json.loads(subprocess.run([os.environ.get("PDF_CHECK_PYTHON",sys.executable),"-c",code,str(pdf)],check=True,capture_output=True,text=True).stdout)
    assert sizes and min(sizes)>=7.95
    assert all(-.2<=c["x0"] and c["x1"]<=518.6 for c in chars)

@pytest.mark.skipif(shutil.which("Rscript") is None, reason="needs R: Rscript not on PATH (see bundle_support/install_r_figure_packages.R)")
def test_default_pooled_pixels_unchanged(tmp_path):
    (t,r,a,c),args=inputs(tmp_path,False)
    plot=prepare(t,r,a,"A04","synthetic",layouts=c)["plot"]
    assert [(p["x"],p["y"]) for p in plot]==[(90,0),(30,40)]
    assert all("target" not in p for p in plot)
    old=Path(__file__).parent/"fixtures/bioassay_a04_pooled.R"
    for folder,renderer in (("new",ROOT/"tools/bioassay_a04.R"),("old",Path(old))):
        cli("A04",renderer,args+["--out",str(tmp_path/folder)])
    a=Image.open(next((tmp_path/"new").glob("*.png"))).convert("RGB")
    b=Image.open(next((tmp_path/"old").glob("*.png"))).convert("RGB")
    assert ImageChops.difference(a,b).getbbox() is None
