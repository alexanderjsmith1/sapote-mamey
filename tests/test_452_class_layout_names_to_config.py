"""Layout definitions are data; existing figures and synthetic extensions remain reproducible."""
import shutil
import importlib.util
import json
import os
from pathlib import Path
import pytest
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
m=load(ROOT/"tools/bgc_classes_per_genome.py","config_renderer")
fixture=load(Path(__file__).with_name("test_452_render_B02.py"),"config_inputs")

@pytest.fixture
def inputs(tmp_path):
    g=fixture.put(tmp_path/"genomes.tsv",[dict(strain="SYN-971",genus="Streptomyces",block="GroupA"),dict(strain="SYN-972",genus="Pseudonocardia",block="GroupB")])
    d=fixture.put(tmp_path/"data.tsv",[dict(strain=s,genus=genus,display=c,family=c,count=n) for s,genus,n in [("SYN-971","Streptomyces",3),("SYN-972","Pseudonocardia",0)] for c in ["NRPS","PKS"]])
    t=fixture.put(tmp_path/"totals.tsv",[dict(strain=s,genus=genus,regions=4,contig_edge=1,pct_edge=25) for s,genus in [("SYN-971","Streptomyces"),("SYN-972","Pseudonocardia")]])
    return g,d,t

def args(inputs,out,layout):
    g,d,t=inputs
    return ["--genomes",str(g),"--data",str(d),"--totals",str(t),"--out",str(out),"--layout",layout,"--dpi","100"]

@pytest.mark.parametrize("layout",m.LAYOUTS)
def test_existing_layout_matches_base(inputs,tmp_path,layout):
    path=os.environ.get("LAYOUT_BASE_TOOL")
    if not path: pytest.skip("base-comparison tool supplied by card validator")
    base=load(Path(path),"unmodified_layout")
    old,new=tmp_path/"base",tmp_path/"candidate"
    assert base.main(args(inputs,old,layout))==m.main(args(inputs,new,layout))==0
    assert (old/(m.TOOL+"_numbers.tsv")).read_bytes()==(new/(m.TOOL+"_numbers.tsv")).read_bytes()
    with Image.open(old/(m.TOOL+".png")) as a,Image.open(new/(m.TOOL+".png")) as b:
        assert a.size==b.size and a.tobytes()==b.tobytes()


def test_unknown_layout_is_refused(inputs,tmp_path):
    with pytest.raises(SystemExit) as exc:m.main(args(inputs,tmp_path/"bad","undefined"))
    assert exc.value.code==2 and not (tmp_path/"bad").exists()


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="needs R: Rscript not on PATH (see bundle_support/install_r_figure_packages.R)")
def test_synthetic_config_renders(inputs,tmp_path):
    config=json.loads((ROOT/"mamey/data/bgc_class_layouts.json").read_text())
    spec=next(s for s in config["layouts"].values() if s["mode"]=="grouped")
    custom=tmp_path/"layouts.json";custom.write_text(json.dumps({"default":"fixture","layouts":{"fixture":spec}}))
    out=tmp_path/"custom"
    assert m.main(args(inputs,out,"fixture")+["--layout-config",str(custom)])==0
    receipt=json.loads((out/"RUN_INFO.json").read_text())
    assert receipt["layout"]=="fixture"
    assert any(Path(i["path"])==custom for i in receipt["inputs"])
