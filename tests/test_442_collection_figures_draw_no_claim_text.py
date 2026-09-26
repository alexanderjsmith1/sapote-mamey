"""Collection figures carry provenance on the page, not claim wording, and their save path refuses it.

Alex, 2026-09-24: claim-safety statements come off figures entirely, footers included. The engine's
`run` renders collection figures from strain metadata (mamey/cli.py). Every one of them drew
"Claim-safe: activity=observation; capacity≠production; KCB=similarity not identity" in its footer,
over the x tick labels, and the Candida/MRSA titles added "(observation, not compound identity)".
They save with a direct fig.savefig, so the save-path refusal in mamey/figure_save.py never saw them.
Generic strain ids, synthetic metadata.
"""
from __future__ import annotations

import pytest

pytest.importorskip("matplotlib")
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from mamey import collection_figures as cf  # noqa: E402
from mamey.figure_policy import FigureTextRefusal, figure_text_violations, matplotlib_visible_text  # noqa: E402

# Phrases the 2026-09-24 ruling removes that the save-path list does not yet hold.
ALSO_BANNED = ("claim-safe", "not compound identity", "capacity≠production", "activity=observation")


def _rows():
    genera = ["Streptomyces", "Streptomyces", "Nocardia", "Micromonospora", "Actinomadura", "Kribbella"]
    return [dict(strain_id=f"REF-{i}", genus=genera[i % 6], source=["soil", "nest", "cuticle"][i % 3],
                 host=["bee", "wasp"][i % 2], location=["Site A", "Site B"][i % 2],
                 collection_date=f"20{15 + i % 5}-06-01", accession=f"GCA_0000000{i:02d}.1",
                 closest_type_strain=f"Type {i % 4}", closest_type_similarity=f"{97 + (i % 3) * 0.8:.1f}",
                 candida_tested="yes", candida_call=["+", "-", "n.t."][i % 3], mrsa_tested="yes",
                 mrsa_call=["-", "+"][i % 2], chemistry_done=["yes", "no"][i % 2], priority=["high", "low"][i % 2])
            for i in range(1, 13)]


def test_no_collection_figure_draws_claim_wording(tmp_path, monkeypatch):
    drawn = {}
    real_save = cf._save

    def spy(fig, png_path):
        drawn[png_path] = matplotlib_visible_text(fig)
        real_save(fig, png_path)

    monkeypatch.setattr(cf, "_save", spy)
    result = cf.render_collection_figures(_rows(), tmp_path / "figs", source_file="synthetic.csv")
    assert result["n_generated"] >= 15 and len(drawn) == result["n_generated"]
    for png, texts in drawn.items():
        assert figure_text_violations(texts) == [], png
        low = " ".join(texts).lower()
        assert not [p for p in ALSO_BANNED if p in low], (png, low)
        assert any(t.startswith("Source: synthetic.csv") for t in texts), png


def test_collection_save_refuses_banned_wording(tmp_path):
    fig, ax = plt.subplots()
    ax.set_title("Top genera (similarity is not identity)")
    with pytest.raises(FigureTextRefusal):
        cf._save(fig, str(tmp_path / "x.png"))
    assert not (tmp_path / "x.png").exists()
