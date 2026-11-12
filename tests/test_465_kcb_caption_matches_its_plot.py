"""9.7.465: the KCB band figure's caption describes the bands the plot draws.

The plot (G03, kcb_similarity_strength) labels its rows "no KCB hit" and three cohort thirds of the cumulative
BLAST score, and its title says the bands are "not similarity thresholds" (B1 ruling, 9.7.404). The caption still
called them "reference-similarity strength" and the empty row a "'no-hit' (novelty-leaning) bin". Pass-after: the
caption names the cohort-third bands and the plot's own row label, and makes no novelty reading.
"""
import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "mamey" / "cohort_figures.py"


def _captions():
    tree = ast.parse(SRC.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "CAPTIONS" for t in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError("no CAPTIONS dict in mamey/cohort_figures.py")


def test_kcb_caption_names_the_cohort_bands_and_the_plot_row_label():
    cap = _captions()["kcb_similarity_strength"]
    assert "not similarity thresholds" in cap and "cohort" in cap
    assert "'no KCB hit'" in cap                       # the row label the plot draws
    assert "similarity strength" not in cap and "novel" not in cap.lower()
