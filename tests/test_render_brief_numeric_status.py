import json
import sys
import types
from unittest.mock import MagicMock

import pytest

from mamey import render_brief as RB


def test_load_facts_separates_invalid_unbound_and_measured_zero(tmp_path):
    (tmp_path / "manifest.json").write_text(
        json.dumps({"strain_id": "TEST-STRAIN", "release": "PRIVATE"}), encoding="utf-8"
    )
    (tmp_path / "TEST-STRAIN_4_triage_board.csv").write_text(
        "Rank,BGC_ID,Contig,antiSMASH_Region,Products,AB_auto,AF_auto,Novelty_auto\n"
        "1,BGC001,NODE_1,region001,NRPS,not-a-number,0,\n"
        "2,BGC002,NODE_2,region002,PKS,0,0,0\n",
        encoding="utf-8",
    )
    rows = RB.load_facts(str(tmp_path))["rows"]
    assert rows[0]["ab_input_state"] == "INVALID"
    assert rows[0]["af_input_state"] == "MEASURED"
    assert rows[0]["novelty_input_state"] == "UNBOUND"
    assert rows[1]["ab_input_state"] == "MEASURED"
    assert rows[1]["af_input_state"] == "MEASURED"
    assert rows[1]["novelty_input_state"] == "MEASURED"


def test_landscape_marks_invalid_ab_but_plots_measured_zero_af(tmp_path):
    row = {
        "rank": "1", "bgc_id": "BGC001", "contig": "NODE_1", "region": "region001",
        "products": "NRPS", "boundary": "Interior", "arch": "", "ab": 0.0, "af": 0.0,
        "novelty": 0.0, "lead_tier": "Low", "kcb_top": "", "kcb_score": "0", "cctt": "",
        "ab_input_state": "INVALID", "af_input_state": "MEASURED",
        "novelty_input_state": "MEASURED",
    }
    plot, fig, ax = MagicMock(), MagicMock(), MagicMock()
    plot.subplots.return_value = (fig, ax)
    png = tmp_path / "landscape.png"
    RB.fig_landscape([row], str(png), "TEST-STRAIN", plot)
    assert ax.barh.call_count == 1
    assert ax.scatter.call_args_list[0].args[0] == 1
    sidecar = (tmp_path / "landscape_data.csv").read_text(encoding="utf-8")
    assert "ab_input_state" in sidecar
    assert "0.0,INVALID,0.0,MEASURED,0.0,MEASURED" in sidecar


@pytest.mark.parametrize("ab_state, novelty_state, expect_sapote, expected_issue, register", [
    ("INVALID", "MEASURED", False, "ab=INVALID", {}),
    ("MEASURED", "UNBOUND", True, "novelty=UNBOUND", {}),
    ("MEASURED", "MEASURED", True, None, {}),
    ("MEASURED", "MEASURED", True, None,
     {"judgment_status": "CORRUPT", "load_errors": [{"error_type": "JSONDecodeError"}]}),
])
def test_render_brief_gates_score_figures_but_preserves_measured_zero(
        tmp_path, monkeypatch, ab_state, novelty_state, expect_sapote, expected_issue, register):
    row = {
        "rank": "1", "bgc_id": "BGC001", "contig": "NODE_1", "region": "region001",
        "products": "NRPS", "boundary": "Interior", "arch": "", "ab": 0.0, "af": 0.0,
        "novelty": 0.0, "lead_tier": "Low", "kcb_top": "", "kcb_score": "0", "cctt": "",
        "ab_input_state": ab_state, "af_input_state": "MEASURED",
        "novelty_input_state": novelty_state,
    }
    facts = {"manifest": {"strain_id": "TEST-STRAIN"}, "rows": [row],
             "strain_label": "TEST-STRAIN", "release": "PRIVATE"}
    monkeypatch.setattr(RB, "load_facts", lambda pkg: facts)
    fake_plot = MagicMock()
    monkeypatch.setattr(RB, "_setup_mpl", lambda: fake_plot)
    monkeypatch.setattr(RB, "fig_landscape", lambda *args: MagicMock())
    monkeypatch.setattr(RB, "fig_composition", lambda *args: MagicMock())
    monkeypatch.setattr(RB, "_text_page", lambda *args, **kwargs: None)

    class FakePdfPages:
        def __init__(self, path): self.path = path
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def savefig(self, *args): return None

    backend = types.ModuleType("matplotlib.backends.backend_pdf")
    backend.PdfPages = FakePdfPages
    monkeypatch.setitem(sys.modules, "matplotlib", types.ModuleType("matplotlib"))
    monkeypatch.setitem(sys.modules, "matplotlib.backends", types.ModuleType("matplotlib.backends"))
    monkeypatch.setitem(sys.modules, "matplotlib.backends.backend_pdf", backend)
    monkeypatch.setitem(sys.modules, "matplotlib.image", types.ModuleType("matplotlib.image"))

    calls = []
    sapote = types.ModuleType("mamey.figures_sapote")
    monkeypatch.setattr(sapote, "render_sapote_figures", lambda *args: calls.append("render") or [], raising=False)
    monkeypatch.setattr(sapote, "write_print_figure_pack", lambda *args: {}, raising=False)
    extra = types.ModuleType("mamey.figures_extra")
    monkeypatch.setattr(extra, "render_extra_figures", lambda *args: [], raising=False)
    split = types.ModuleType("mamey.figures_split")
    monkeypatch.setattr(split, "render_split_figures", lambda *args: [], raising=False)
    judgment = types.ModuleType("mamey.judgment_store")
    monkeypatch.setattr(judgment, "read_laypersons", lambda pkg: "", raising=False)
    monkeypatch.setattr(judgment, "read_fermentation", lambda pkg: "", raising=False)
    monkeypatch.setattr(judgment, "read_register", lambda pkg: register, raising=False)
    monkeypatch.setitem(sys.modules, "mamey.figures_sapote", sapote)
    monkeypatch.setitem(sys.modules, "mamey.figures_extra", extra)
    monkeypatch.setitem(sys.modules, "mamey.figures_split", split)
    monkeypatch.setitem(sys.modules, "mamey.judgment_store", judgment)

    messages = []
    result = RB.render_brief(str(tmp_path), logger=messages.append)
    assert result["status"] == "COMPLETE", (result, messages)
    assert bool(calls) is expect_sapote
    if expected_issue:
        assert any(message.startswith(
            "BRIEF_NUMERIC_INPUT_UNRESOLVED: TEST-STRAIN / NODE_1 / region001 / BGC001:"
        ) and expected_issue in message for message in messages)
    if ab_state == "INVALID":
        assert any(message.startswith(
            "SAPOTE_FIGS_SKIPPED: BRIEF_NUMERIC_INPUT_UNRESOLVED"
        ) for message in messages)
    else:
        assert not any(message.startswith("SAPOTE_FIGS_SKIPPED: BRIEF_NUMERIC_INPUT_UNRESOLVED")
                       for message in messages)
    if expected_issue is None:
        assert not any("BRIEF_NUMERIC_INPUT_UNRESOLVED" in message for message in messages)
    if register.get("judgment_status") == "CORRUPT":
        assert any(message.startswith("JUDGMENT_REGISTER_CORRUPT: CORRUPT:")
                   for message in messages)
        assert result["judgment_complete"] is None
        assert result["judgment_pct"] is None
    else:
        assert not any("JUDGMENT_REGISTER_CORRUPT" in message for message in messages)
