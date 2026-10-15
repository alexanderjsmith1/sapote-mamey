"""Card attine_452_b03_height_from_rows: B03 page height grows with the genus rows, and isolate labels split into two tiers.

At a fixed 0.40 in per row, a genus with five isolates pushed five boxed labels into one line, crowding the next row
(owner, 13 Oct: "too scrunched ... widen it all vertically"). The height is now ROW_IN per row plus FRAME_IN; a
--print-height below MIN_ROW_IN per row is refused before anything is written. Isolate labels are plain text,
alternating above and below the row by value within each genus. Synthetic data only.
"""
import importlib.util
import json
import shutil
from pathlib import Path

import pytest
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("b03_height", ROOT / "tools/region_protein_by_genus.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


def test_height_grows_with_rows_and_refuses_squeezing():
    assert m.print_height(2) == 3.0                                    # floor for small figures
    assert m.print_height(6) == round(0.62 * 6 + 1.1, 2)
    assert m.print_height(10) > m.print_height(6)
    assert m.print_height(6, 5.0) == 5.0
    with pytest.raises(ValueError, match="less than 0.5 in per row"):
        m.print_height(6, 3.0)


def _data(tmp_path, n_genera):
    rows = []
    for k in range(n_genera):
        g = f"Genus{chr(97 + k)}"
        rows += [(f"SYN-97{k}{j}", g, 150000 + 20000 * j, "isolate") for j in range(3 if k == 0 else 1)]
        rows += [(f"REF{k}_{i}", g, 100000 + 10000 * i, "reference") for i in range(5)]
    d = tmp_path / "d.tsv"
    d.write_text("strain\tgenus\tamino_acids\tmissing_CDS_lengths\trole\n" + "".join(f"{s}\t{g}\t{a}\t0\t{r}\n" for s, g, a, r in rows))
    c = tmp_path / "c.md"; c.write_text("Synthetic caption.\n")
    return d, c


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript unavailable")
def test_page_height_follows_rows_and_labels_are_split(tmp_path):
    d, c = _data(tmp_path, 6)
    out = tmp_path / "out"
    assert m.main(["--data", str(d), "--caption", str(c), "--out", str(out)]) == 0
    cfg = json.loads((out / "render_config.json").read_text())
    assert cfg["print_height"] == m.print_height(6) and cfg["label_offset"] == m.LABEL_OFFSET
    page = PdfReader(out / "region_protein_by_genus.pdf").pages[0]
    h = float(page.mediabox.height) / 72          # mt_save may add a little fixed height for the text; never less
    assert m.print_height(6) - 0.01 <= h <= m.print_height(6) + 0.2
    text = page.extract_text().replace(" ", "")
    assert all(s in text for s in ("SYN-9700", "SYN-9701", "SYN-9702"))
    r = (out / "render.R").read_text()
    assert "geom_label_repel" not in r and "tier %% 2 == 1" in r


def test_a_squeezed_height_is_refused_before_writing(tmp_path):
    d, c = _data(tmp_path, 6)
    with pytest.raises(ValueError, match="per row"):
        m.main(["--data", str(d), "--caption", str(c), "--out", str(tmp_path / "out"), "--print-height", "3"])
    assert not (tmp_path / "out").exists()
