"""Caption counts follow the bound complete roster and included plotted rows."""
import importlib.util
import json
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location("overlay_test_fixture", Path(__file__).with_name("test_tree_bgc_overlay.py"))
t = importlib.util.module_from_spec(spec)
spec.loader.exec_module(t)

@pytest.mark.parametrize("include", [False, True])
def test_benchmark_counts_match_bound_roster(tmp_path, monkeypatch, include):
    cfg = t._fixture(tmp_path)
    c = json.loads(cfg.read_text())
    cw = Path(c["external_data_root"]) / "crosswalk.tsv"
    text = cw.read_text().replace("Genus alpha held\tSTUDY", "Genus alpha held\tEXTERNAL_BENCHMARK")
    if include:
        text = text.replace("Genus alpha strain two\tSTUDY", "Genus alpha strain two\tEXTERNAL_BENCHMARK")
    cw.write_text(text)
    next(x for x in c["inputs"] if x["role"] == "tip_crosswalk")["sha256"] = t._sha(cw)
    cfg.write_text(json.dumps(c))
    monkeypatch.setattr(t.ov, "_render", lambda *a: ([], {}))
    t.ov.build_publication(cfg)
    caption = json.loads((tmp_path / "tree-output-a" / "tree_bgc_overlay_caption_methods.json").read_text())
    assert f"available={1 + int(include)}; selected={int(include)};" in caption["benchmark_sensitivity"]
    assert caption["denominator"] == "3 included tree tips"
    assert "strain-held" not in caption["group_denominators"]
