"""tools/region_protein_by_genus.py: an isolate and its comparators in one row (owner, ruling 289: AS-103, Sciscionella and
Goodfellowiella "can all be grouped together", references as open circles).

In a row shared with an isolate, the comparator labels go below the row in two staggered tiers, so they cannot meet the
isolate labels (the two layers are repelled separately), and the panel is extended so the lower tier is drawn. Any label
the figure must carry but did not draw (ggrepel drops a label outside the panel without an error) refuses the render."""
import importlib.util
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("rpg457", ROOT / "tools/region_protein_by_genus.py")
rpg = importlib.util.module_from_spec(spec); spec.loader.exec_module(rpg)
needs_r = pytest.mark.skipif(not shutil.which("Rscript"), reason="Rscript unavailable")

HEAD = "strain\tgenus\tamino_acids\tmissing_CDS_lengths\trole\tname\tstrain_label\topen\tlabel\n"


def table(tmp_path, comparators):
    refs = "".join(f"r{k}\tExample\t{100000 + 20000 * k}\t0\treference\t\t\t\t\n" for k in range(6))
    text = HEAD + refs + "iso_a\tExample\t180000\t0\tisolate\t\t\t\t\niso_b\tFamilyrow\t250000\t0\tisolate\t\t\t\t\n" + comparators
    p = tmp_path / "data.tsv"; p.write_text(text)
    c = tmp_path / "caption.md"; c.write_text("Synthetic totals; the shared row holds one isolate and its comparators.\n")
    return p, c


def test_labels_not_drawn_finds_a_missing_comparator_label():
    rows = [dict(strain="iso_b", role="isolate"),
            dict(strain="c1", role="comparator", name="S. alpha", strain_label="DSM 1", label="yes"),
            dict(strain="c2", role="comparator", name="S. beta", strain_label="", label="yes"),
            dict(strain="c3", role="comparator", name="S. gamma", strain_label="DSM 3", label="no")]
    svg = "<text>iso_b</text><text>S. alpha</text><text> DSM 1</text>"
    assert rpg.labels_not_drawn(rows, svg) == ["S. beta"]            # label = no is never required
    assert rpg.labels_not_drawn(rows, svg + "<text>S. beta</text>") == []


@needs_r
def test_shared_row_draws_every_comparator_label(tmp_path):
    comps = "".join(f"c{k}\tFamilyrow\t{v}\t0\tcomparator\tS. sp{k}\tSTRAIN {k}\tyes\tyes\n"
                    for k, v in enumerate((260000, 410000, 425000, 680000)))
    data, cap = table(tmp_path, comps)
    assert rpg.main(["--data", str(data), "--caption", str(cap), "--out", str(tmp_path / "out"), "--print-width", "6.0",
                     "--row-order", "Example,Familyrow"]) == 0
    svg = (tmp_path / "out" / "region_protein_by_genus.svg").read_text()
    for k in range(4):
        assert f"STRAIN {k}" in svg
    assert "iso_b" in svg


@needs_r
def test_rows_without_an_isolate_keep_alternating_labels(tmp_path):
    """Comparators in their own row (no isolate there) are unchanged: tiers alternate above and below."""
    comps = "c0\tOwnrow\t300000\t0\tcomparator\tS. one\tA1\tno\tyes\nc1\tOwnrow\t600000\t0\tcomparator\tS. two\tA2\tno\tyes\n"
    data, cap = table(tmp_path, comps)
    assert rpg.main(["--data", str(data), "--caption", str(cap), "--out", str(tmp_path / "out"), "--print-width", "6.0",
                     "--row-order", "Example,Familyrow,Ownrow"]) == 0
    r = (tmp_path / "out" / "render.R").read_text()
    assert "shared <- cmpl$genus %in% iso$genus" in r
