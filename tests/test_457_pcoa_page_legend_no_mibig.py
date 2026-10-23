"""tools/protein_pcoa_render.py page legend: a page with no MIBiG point has no MIBiG key and says "best reference match";
a page with MIBiG points keeps the bee Fig. S9 wording. Synthetic arguments only."""
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
spec = importlib.util.spec_from_file_location("ppr_legend", ROOT / "tools" / "protein_pcoa_render.py")
ppr = importlib.util.module_from_spec(spec); spec.loader.exec_module(ppr)


def args():
    return SimpleNamespace(panel_label=["P=panel isolates"], reference_label=None, label_below=70.0, mid_below=85.0)


def panels(*layers):
    return [{"spec": {"points": [{"layer": x} for x in layers]}}]


def test_no_mibig_drops_key_and_wording():
    leg = ppr.page_legend(args(), {}, 12, has_mibig=ppr._page_has_mibig(panels("ref", "iso_low")))
    assert "mibig" not in leg
    assert all("MIBiG" not in v for v in leg.values())
    assert leg["iso_low"] == "panel isolates, best reference match < 70% identity"
    assert leg["ref"] == "reference genomes, n = 12 (cluster centroids)"


def test_mibig_present_keeps_bee_wording():
    leg = ppr.page_legend(args(), {}, None, has_mibig=ppr._page_has_mibig(panels("ref", "mibig")))
    assert leg["mibig"] == "MIBiG characterized clusters"
    assert leg["iso_high"] == "panel isolates, best reference/MIBiG match ≥ 85% identity"


def test_zoomed_page_counts_all_points():
    p = [{"spec": {"points": [{"layer": "ref"}], "points_all": [{"layer": "ref"}, {"layer": "mibig"}]}}]
    assert ppr._page_has_mibig(p) is True


def test_default_keeps_old_behaviour():
    assert "mibig" in ppr.page_legend(args(), {}, None)
