"""cov-.200: hermetic test for build_card_workbook E5 provenance (CW-1) + de-dup (CW-2)."""
import importlib.util, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
_s = importlib.util.spec_from_file_location("build_card_workbook", ROOT/"tools"/"build_card_workbook.py")
bcw = importlib.util.module_from_spec(_s); _s.loader.exec_module(bcw)

def _pkg(d):
    p = Path(d); (p/"judgment").mkdir(); (p/"mode_b_templates").mkdir()
    # authored card (judgment/) carries the store header AND the surviving template header
    (p/"judgment"/"AS-660_BGC049_mode_b.md").write_text(
        "<!-- MODE B: BGC049 | authored -->\n<!-- MODE B TEMPLATE | bgc: BGC049 -->\n"
        "## §1 Identity\nbgc: BGC049\nreal authored content\n")
    # template of the SAME BGC, different filename
    (p/"mode_b_templates"/"BGC049_template.md").write_text(
        "<!-- MODE B TEMPLATE | bgc: BGC049 -->\n## §1 Identity\nbgc: BGC049\n")
    return p

def test_cw2_dedup_by_bgc_id():
    with tempfile.TemporaryDirectory() as d:
        cards = bcw._find_modeb_cards(_pkg(d))
        # same BGC via two filenames -> 1 card, preferring judgment/ (authored)
        assert len(cards) == 1, [c.name for c in cards]
        assert "judgment" in str(cards[0])

def test_cw1_authored_not_skeleton():
    with tempfile.TemporaryDirectory() as d:
        rows = bcw.modeb_section_rows(_pkg(d), "AS-660")
        labels = {str(x) for r in rows for x in r if "AUTHORED" in str(x) or "SKELETON" in str(x)}
        assert any("AUTHORED" in l for l in labels), labels
        assert not any("SKELETON" in l for l in labels), labels
