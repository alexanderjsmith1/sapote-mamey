"""M5_452_class_renderers_palette_fallback: the class renderers (B01 bgc_class_groups, B02 bgc_classes_per_genome, B04
public_genome_families) drew no genus colour but refused genera absent from mamey/data/genus_palette.json, whose own contract
says unknown genera take the fallback colour. Paper 4 (1,232 public references, 96 genera) was refused on 75 genera. Unknown
genera are now recorded in RUN_INFO.json as fallback_genera. Synthetic genus names only."""
import csv, importlib.util, json, shutil
from pathlib import Path
import pytest
ROOT = Path(__file__).resolve().parents[1]
TOOLS = ["bgc_class_groups", "bgc_classes_per_genome", "public_genome_families"]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"tools/{name}.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def put(path, rows):
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter="\t"); w.writeheader(); w.writerows(rows)
    return path


@pytest.mark.parametrize("name", TOOLS)
def test_no_palette_refusal_left(name):
    code = (ROOT / f"tools/{name}.py").read_text()
    assert "genera absent from bundle palette" not in code
    assert '"fallback_genera":sorted(unknown)' in code


def test_b01_renders_unknown_genus_and_records_it(tmp_path):
    if not shutil.which("Rscript"): pytest.skip("Rscript unavailable")
    m = load("bgc_class_groups")
    g = put(tmp_path / "genomes.tsv", [dict(strain="SYN-981", genus="Synthgenusa", block="All"), dict(strain="SYN-982", genus="Streptomyces", block="All")])
    d = put(tmp_path / "data.tsv", [dict(display="NRPS", family="NRPS", regions=3, genomes=2), dict(display="Terpene", family="Terpene", regions=2, genomes=1)])
    out = tmp_path / "out"
    assert m.main(["--genomes", str(g), "--data", str(d), "--out", str(out), "--layout", "bee", "--dpi", "100"]) == 0
    assert json.loads((out / "RUN_INFO.json").read_text())["fallback_genera"] == ["Synthgenusa"]
