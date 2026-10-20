"""--source-style colour options: --source-style-fill and --mibig-fill let the user choose the genus fill and the MIBiG
triangle fill (defaults unchanged: the genus palette colour and #3a78b5). Bad colours and use without --source-style
are refused. Synthetic data only."""
import csv, importlib.util, json
from pathlib import Path
import pytest
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("ppr_co", ROOT / "tools" / "protein_pcoa_render.py"); ppr = importlib.util.module_from_spec(spec); spec.loader.exec_module(ppr)


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


def test_bad_colour_refused(kit):
    with pytest.raises(SystemExit):
        ppr.main(["--kit", str(kit / "kit"), "--out", str(kit / "out"), "--source-style", "Streptomyces", "--mibig-fill", "blue"])


def test_fill_flags_need_source_style(kit):
    with pytest.raises(SystemExit):
        ppr.main(["--kit", str(kit / "kit"), "--out", str(kit / "out"), "--mibig-fill", "#4D4D4D"])


@pytest.mark.skipif(not ppr.r_available(), reason="Rscript with ggplot2, ggrepel, jsonlite and svglite not available")
def test_chosen_colours_drawn(kit):
    assert ppr.main(["--kit", str(kit / "kit"), "--out", str(kit / "out"), "--source-style", "Streptomyces", "--renderer", "r",
                     "--source-style-fill", "#F28E2B", "--mibig-fill", "#4D4D4D"]) == 0
    svg = (kit / "out/PCOA_KS_references.svg").read_text().upper()
    assert "#F28E2B" in svg and "#4D4D4D" in svg and "#3A78B5" not in svg


@pytest.mark.skipif(not ppr.r_available(), reason="Rscript with ggplot2, ggrepel, jsonlite and svglite not available")
def test_chosen_outlines_drawn(kit):
    assert ppr.main(["--kit", str(kit / "kit"), "--out", str(kit / "out"), "--source-style", "Streptomyces", "--renderer", "r",
                     "--source-style-fill", "#F28E2B", "--source-style-outline", "#F28E2B",
                     "--mibig-fill", "#D9D9D9", "--mibig-outline", "#A6A6A6"]) == 0
    svg = (kit / "out/PCOA_KS_references.svg").read_text().upper()
    assert "#A6A6A6" in svg and "#D9D9D9" in svg


@pytest.mark.skipif(not ppr.r_available(), reason="Rscript with ggplot2, ggrepel, jsonlite and svglite not available")
def test_default_is_paper_ready_option_f(kit):
    """Owner ruling 15 Oct (Fig. 7 option F): genus fill with no dark rim, MIBiG pale grey."""
    assert ppr.main(["--kit", str(kit / "kit"), "--out", str(kit / "out"), "--source-style", "Streptomyces", "--renderer", "r"]) == 0
    svg = (kit / "out/PCOA_KS_references.svg").read_text().upper()
    assert "#D9D9D9" in svg and "#A6A6A6" in svg and "#3A78B5" not in svg
