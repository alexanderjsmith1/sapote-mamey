"""Text drawn on cohort figures never says "novel".

Owner ruling (G1, row 20): a plot carries no interpretive text; interpretation goes in the caption. The .459
card made the KCB and GCF figures neutral, but mamey/cohort_figures.py still drew "all BGCs novelty-leaning",
"'no-hit' count noted = novelty-leaning" and "'No hit' is novelty-leaning, not proof of novelty" on the
plots. This reads every string passed to ax.text, set_title, suptitle and the hmap title, so it does not
depend on how the code is laid out.
"""
import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "mamey" / "cohort_figures.py"
DRAW = {"text", "set_title", "suptitle", "set_xlabel", "set_ylabel", "annotate"}


def _strings(node):
    return [n.value for n in ast.walk(node) if isinstance(n, ast.Constant) and isinstance(n.value, str)]


def test_no_novelty_word_in_on_plot_text():
    tree = ast.parse(SRC.read_text(encoding="utf-8"))
    drawn = []
    for call in (n for n in ast.walk(tree) if isinstance(n, ast.Call)):
        name = getattr(call.func, "attr", None) or getattr(call.func, "id", None)
        if name in DRAW:
            drawn += [s for a in call.args for s in _strings(a)]
        elif name == "hmap" and len(call.args) >= 4:      # hmap(mat, rowlabs, order, title, ...)
            drawn += _strings(call.args[3])
    assert drawn, "found no drawing calls; the reader no longer matches the source"
    offenders = [s for s in drawn if "novel" in s.lower()]
    assert not offenders, offenders
