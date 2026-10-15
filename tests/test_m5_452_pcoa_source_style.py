"""M5_452_pcoa_source_style: tools/protein_pcoa_render.py --source-style GENUS draws a reference-only panel with no cohort table
(reference points outlined in the genus's palette colour above MIBiG triangles, boxed legend; R only). Without the flag the
cohort table and --panel stay required. Synthetic data only."""
import csv, importlib.util, json
from pathlib import Path
import pytest
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("ppr_ss", ROOT / "tools" / "protein_pcoa_render.py"); ppr = importlib.util.module_from_spec(spec); spec.loader.exec_module(ppr)


@pytest.fixture
def kit(tmp_path):
    out = tmp_path / "kit/out_KS"; out.mkdir(parents=True)
    rows = [["id", "PC1", "PC2", "PC3", "n_represented", "source", "group", "genus", "strain", "subtype", "region_product", "locus_tag", "origin", "length"]]
    for n in range(24):
        rows.append([f"r{n}", (n % 6) / 10, (n // 6) / 10, 0, 1 + n % 3, "reference_held" if n % 3 else "MIBiG", "", "Synthgenusa", f"SYN-{900 + n}", "", "", "", "", 300])
    with open(out / "PCOA_KS.tsv", "w", newline="") as fh:
        csv.writer(fh, delimiter="\t").writerows(rows)
    (out / "RUN_KS.json").write_text(json.dumps({"pct_axes": [30.0, 20.0, 10.0]}))
    return tmp_path


def test_cohort_still_required_without_flag(kit):
    with pytest.raises(SystemExit):
        ppr.main(["--kit", str(kit / "kit"), "--out", str(kit / "out")])


def test_source_style_refuses_matplotlib(kit):
    with pytest.raises(SystemExit):
        ppr.main(["--kit", str(kit / "kit"), "--out", str(kit / "out"), "--source-style", "Streptomyces", "--renderer", "matplotlib"])


@pytest.mark.skipif(not ppr.r_available(), reason="Rscript with ggplot2, ggrepel, jsonlite and svglite not available")
def test_source_style_draws_without_cohort(kit):
    assert ppr.main(["--kit", str(kit / "kit"), "--out", str(kit / "out"), "--source-style", "Streptomyces", "--renderer", "r"]) == 0
    for ext in ("pdf", "svg", "png"):
        assert (kit / f"out/PCOA_KS_references.{ext}").stat().st_size > 0
    receipt = json.loads((kit / "out/panel_KS_references.json").read_text())
    assert receipt["n_cohort_points"] == 0 and receipt["n_ref"] > 0 and receipt["n_mibig"] > 0
    pal = json.loads((ROOT / "mamey/data/genus_palette.json").read_text())
    assert pal["default"]["Streptomyces"].lower() in (kit / "out/PCOA_KS_references.svg").read_text().lower()
