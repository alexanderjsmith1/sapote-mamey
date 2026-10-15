"""Card attine_452_caption_type_key_only_when_drawn: the placement caption keys '(T), type strain' only when a drawn
reference or outgroup label carries (T). The short label style with accessions drew no (T) on the attine tree, yet the
caption still printed the key. Synthetic rows only."""
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE / "tools"))
spec = importlib.util.spec_from_file_location("placement_display_452t", HERE / "tools" / "placement_display.py")
pd = importlib.util.module_from_spec(spec); spec.loader.exec_module(pd)


def test_key_only_when_a_tip_carries_T():
    with_t = [{"role": "query", "label": "Synus sp. SYN-970"},
              {"role": "reference", "label": "Synus alpha DSM 1 (T)"},
              {"role": "outgroup", "label": "Synoutgroupia beta SYN 2"}]
    without_t = [{"role": "query", "label": "Synus sp. SYN-970 (T)"},      # a query label never sets the key
                 {"role": "reference", "label": "Synus alpha DSM 1 (NR_000001.1)"},
                 {"role": "outgroup", "label": "Synoutgroupia beta SYN 2"}]
    assert pd.type_key(with_t) == "; (T), type strain"
    assert pd.type_key(without_t) == ""
    assert pd.type_key([{"role": "outgroup", "label": "Synoutgroupia beta SYN 2 (T)"}]) == "; (T), type strain"


def test_caption_uses_the_key_function():
    s = (HERE / "tools" / "placement_display.py").read_text()
    assert "reference strains{type_key(rows)}." in s and "reference strains; (T), type strain." not in s
