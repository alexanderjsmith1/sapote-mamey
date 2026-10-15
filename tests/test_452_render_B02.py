import csv, importlib.util, shutil
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("renderer", ROOT/"tools/bgc_classes_per_genome.py")
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

def put(path, rows):
    with path.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),delimiter="\t");w.writeheader();w.writerows(rows)
    return path

@pytest.fixture
def inputs(tmp_path):
    g=put(tmp_path/"genomes.tsv",[dict(strain="SYN-971",genus="Streptomyces",block="Group A"),dict(strain="SYN-972",genus="Pseudonocardia",block="Group B")])
    d=put(tmp_path/"data.tsv",[dict(strain=s,genus=g,display=c,family=f,count=n) for s,g,n in [("SYN-971","Streptomyces",3),("SYN-972","Pseudonocardia",0)] for c,f in [("NRPS","NRPS"),("PKS","PKS")]]); t=put(tmp_path/"totals.tsv",[dict(strain=s,genus=g,regions=4,contig_edge=1,pct_edge=25) for s,g in [("SYN-971","Streptomyces"),("SYN-972","Pseudonocardia")]])
    return g,d,t

@pytest.mark.parametrize("layout",m.LAYOUTS)
def test_render_all_layouts(tmp_path, inputs,layout):
    if not shutil.which("Rscript"): pytest.skip("Rscript unavailable")
    g,d,t=inputs;out=tmp_path/layout
    args=["--genomes",str(g),"--data",str(d),"--out",str(out),"--layout",layout,"--palette-set","moss","--dpi","100"]
    if t: args += ["--totals",str(t)]
    assert m.main(args)==0
    for ext in [".png",".pdf"]:
        assert ("Sapote-Mamey "+m.TOOL).encode() in (out/(m.TOOL+ext)).read_bytes()
    numbers=m.table(out/(m.TOOL+"_numbers.tsv"),[])
    assert sum(int(r["value"]) for r in numbers if r["kind"]=="regions")==8
    assert sum(int(r["value"]) for r in numbers if r["kind"]=="class_count")==6
    with pytest.raises(FileExistsError): m.main(args)

def test_invalid_data_refused_before_output(tmp_path,inputs):
    g,d,t=inputs; rows=m.table(d,[]); rows[0][m.NUMERIC[0]]="-1";put(d,rows)
    args=["--genomes",str(g),"--data",str(d),"--out",str(tmp_path/"bad")]
    if t:args += ["--totals",str(t)]
    with pytest.raises(ValueError):m.main(args)
    assert not (tmp_path/"bad").exists()

def test_palette_and_paths():
    code=(ROOT/"tools/bgc_classes_per_genome.py").read_text()
    assert "genus_palette.json" in code
    assert "/Users/" not in code
    assert "quartz" not in code
