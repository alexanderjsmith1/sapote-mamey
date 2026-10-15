"""Russia colours the geography strip as Europe (owner ruling) while labels keep the deposited 'Russia'."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import _phylo_metadata as m  # noqa: E402
import build_placement_ggtree_inputs as b  # noqa: E402


def test_strip_uses_the_ruled_region():
    assert m.strip_geography("Russia")["display_location"] == "Europe"
    assert m.strip_geography("Russia: Moscow")["display_location"] == "Europe"
    assert m.strip_geography("Russia")["state"] == "STRIP_REGION_RULED"


def test_labels_keep_the_deposited_country():
    assert m.normalize_geography("Russia")["display_location"] == "Russia"


def test_other_countries_unchanged_in_the_strip():
    for c in ("USA", "Canada", "Japan", "Norway", "Turkey", ""):
        assert m.strip_geography(c) == m.normalize_geography(c)


def test_rect_rows_use_the_strip_region():
    row = b._rect_metadata_row("t1", "label", "soil", "Russia")
    assert row[3] == "Europe" and row[6] == "Russia"
