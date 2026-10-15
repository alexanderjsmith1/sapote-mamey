"""All rendered text, including the final colour-bar tick, stays in the page."""
import pytest
import shutil
import json,os,subprocess,sys,math
from pathlib import Path
from pypdf import PdfReader
from mamey.bioassay_paper import cli,sha,write,LAYOUTS
ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.skipif(shutil.which("Rscript") is None, reason="needs R: Rscript not on PATH (see bundle_support/install_r_figure_packages.R)")
def test_colourbar_inside_frame(tmp_path):
    profile=dict(next(v for k,v in json.loads(LAYOUTS.read_text()).items() if not k.startswith("_")))
    profile.update(a02_width_in=5.6,group_axis_label="Source group")
    config=tmp_path/"profile.json";config.write_text(json.dumps({"synthetic":profile}))
    roster=tmp_path/"roster.tsv";table=tmp_path/"assay.tsv";aliases=tmp_path/"aliases.json";lock=tmp_path/"lock.json"
    aliases.write_text("{}");lock.write_text("{}")
    write(roster,[dict(strain=f"SYN-{970+i}",genus="Streptomyces",group=f"Group {i}") for i in range(4)])
    write(table,[dict(strain=f"SYN-{970+i}",organism=target,material=material,best_pct=str(20+20*i)) for i in range(4) for target in ("Candida albicans","Candida auris","E. coli","MRSA","Foulbrood 818") for material in ("Crude extract","Fraction")])
    out=tmp_path/"out"
    cli("A02",ROOT/"tools/bioassay_a02.R",["--table",str(table),"--roster",str(roster),"--aliases",str(aliases),"--lock",str(lock),"--table-sha256",sha(table),"--lock-sha256",sha(lock),"--layout","synthetic","--layout-config",str(config),"--out",str(out)])
    pdf=next(out.glob("*.pdf"))
    script="import json,pdfplumber,sys; p=pdfplumber.open(sys.argv[1]).pages[0]; print(json.dumps({'width':p.width,'chars':p.chars,'text':p.extract_text()}))"
    r=subprocess.run([os.environ.get("PDF_CHECK_PYTHON",sys.executable),"-c",script,str(pdf)],check=True,capture_output=True,text=True)
    result=json.loads(r.stdout)
    assert "100%" in result["text"]
    assert all(c["x0"]>=-0.2 and c["x1"]<=result["width"]+0.2 for c in result["chars"])
    sizes=[]
    PdfReader(pdf).pages[0].extract_text(visitor_text=lambda t,cm,tm,font,size:sizes.append(size*math.hypot(tm[0]*cm[0]+tm[1]*cm[2],tm[0]*cm[1]+tm[1]*cm[3])) if t.strip() else None)
    assert sizes and min(sizes)>=7.95
