"""Card attine_452_blastp_gene_points_darker.

Panel A of the BLASTp by-genome figure draws one point per gene under each box. The first draft drew them at 0.5 pt^2 and
alpha 0.25, a pale haze at print size; the owner asked for darker points (13 Oct). The default is now 1.5 pt^2 at alpha
0.6. Numbers, boxes and bands are unchanged. Synthetic data only.
"""
import importlib.util
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"


def _tool():
    if str(TOOLS) not in sys.path:
        sys.path.insert(0, str(TOOLS))
    spec = importlib.util.spec_from_file_location("bif_t452p", TOOLS / "blastp_identity_figures.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_gene_points_use_the_darker_defaults(tmp_path, monkeypatch):
    bif = _tool()
    assert (bif.GENE_POINT_SIZE, bif.GENE_POINT_ALPHA) == (1.5, 0.6)
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib.axes import Axes
    seen = []
    real = Axes.scatter

    def spy(self, *a, **kw):
        seen.append(kw)
        return real(self, *a, **kw)

    monkeypatch.setattr(Axes, "scatter", spy)
    genomes = [{"strain": "SYN-970", "genus": "Streptomyces", "block": "A"}, {"strain": "SYN-971", "genus": "Pseudonocardia", "block": "A"}]
    region = {"SYN-970": ["g1", "g2", "g3"], "SYN-971": ["g4", "g5"]}
    best = {("SYN-970", "g1"): 45.0, ("SYN-970", "g2"): 72.0, ("SYN-970", "g3"): 91.0,
            ("SYN-971", "g4"): 66.0, ("SYN-971", "g5"): 88.0}
    colours = {"Streptomyces": "#1B7837", "Pseudonocardia": "#14325C"}
    (tmp_path / "out").mkdir()
    bif.by_genome(genomes, region, best, colours, "top10", "best", tmp_path / "out")
    gene_pts = [kw for kw in seen if kw.get("s") == bif.GENE_POINT_SIZE]
    assert len(gene_pts) == 2 and all(kw["alpha"] == bif.GENE_POINT_ALPHA for kw in gene_pts)
