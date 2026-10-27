"""B04 options (card 452_b04_axis_title_and_count_labels): a plain x-axis title in the ink colour, and the
'N of M' count labels optional. Without the options the original output is unchanged."""
import csv, importlib.util, json, shutil
from pathlib import Path
import pytest
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("renderer_b04_opts", ROOT / "tools/public_genome_families.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
pypdf = pytest.importorskip("pypdf")


def put(path, rows):
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter="\t"); w.writeheader(); w.writerows(rows)
    return path


@pytest.fixture
def inputs(tmp_path):
    g = put(tmp_path / "genomes.tsv", [dict(strain="SYN-970", genus="Streptomyces", block="Bryophyte"),
                                       dict(strain="SYN-971", genus="Pseudonocardia", block="Lichen")])
    d = put(tmp_path / "data.tsv", [dict(strain="SYN-970", genus="Streptomyces", families=4, in_public=3, not_in_public=1),
                                    dict(strain="SYN-971", genus="Pseudonocardia", families=3, in_public=1, not_in_public=2)])
    return g, d


def text(out):
    return " ".join(p.extract_text() for p in pypdf.PdfReader(str(out / (m.TOOL + ".pdf"))).pages)


def run(tmp_path, inputs, name, *extra):
    if not shutil.which("Rscript"):
        pytest.skip("Rscript unavailable")
    g, d = inputs; out = tmp_path / name
    assert m.main(["--genomes", str(g), "--data", str(d), "--out", str(out), "--layout", "moss", "--palette-set", "moss",
                   "--dpi", "100", *extra]) == 0
    return out


def test_default_keeps_the_original_title_and_labels(tmp_path, inputs):
    out = run(tmp_path, inputs, "default")
    t = text(out)
    assert "1 of 4" in t and "2 of 3" in t and "public genomes, of all" in t
    cfg = json.loads((out / "render_config.json").read_text())
    assert cfg["x_title"] is None and cfg["count_labels"] == "of-total"


def test_plain_title_and_no_count_labels(tmp_path, inputs):
    out = run(tmp_path, inputs, "plain", "--x-title", "BiG-SCAPE families\\n(cutoff 0.7)", "--count-labels", "none")
    t = text(out)
    assert "BiG-SCAPE families" in t and "(cutoff 0.7)" in t
    assert "1 of 4" not in t and "of all" not in t
    assert json.loads(next(out.glob("*_min_text_check.json")).read_text())["status"] == "PASS"


def test_plain_title_with_count_labels(tmp_path, inputs):
    out = run(tmp_path, inputs, "labels", "--x-title", "Families", "--count-labels", "of-total")
    t = text(out)
    assert "1 of 4" in t and "Families" in t and "of all" not in t


def test_source_tags_ink_option(tmp_path, inputs):
    out = run(tmp_path, inputs, "ink", "--source-tags", "ink")
    r = (out / "render.R").read_text(); cfg = __import__("json").loads((out / "render_config.json").read_text())
    assert cfg["source_tags"] == "ink" and "TAGC" in r
    out2 = run(tmp_path, inputs, "grey")
    assert __import__("json").loads((out2 / "render_config.json").read_text())["source_tags"] == "grey"
