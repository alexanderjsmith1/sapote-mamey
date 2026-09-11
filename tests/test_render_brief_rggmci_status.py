import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from mamey import render_brief as RB
from mamey.render_brief import fig_rggmci_rescue


HEADERS = "bgc_a,bgc_b,rggmci_score,rggmci_confidence\n"


def test_unreadable_rggmci_source_is_typed(tmp_path):
    source = tmp_path / "pairs.csv"
    source.write_bytes(b"\xff\xfe")
    messages = []
    assert fig_rggmci_rescue(source, tmp_path / "out.png", "TEST-STRAIN", None,
                             logger=messages.append) is None
    assert messages and messages[0].startswith("RESCUE_FIG_INVALID_SOURCE: UnicodeDecodeError:")


def test_valid_empty_rggmci_source_is_not_invalid(tmp_path):
    source = tmp_path / "pairs.csv"
    source.write_text(HEADERS, encoding="utf-8")
    messages = []
    assert fig_rggmci_rescue(source, tmp_path / "out.png", "TEST-STRAIN", None,
                             logger=messages.append) is None
    assert messages == ["RESCUE_FIG_NO_ROWS: valid RG-GMCI source contains no ranked pairs"]


def test_missing_rggmci_source_remains_explicit_invalid_state(tmp_path):
    messages = []
    assert fig_rggmci_rescue(tmp_path / "missing.csv", tmp_path / "out.png", "TEST-STRAIN", None,
                             logger=messages.append) is None
    assert messages and messages[0].startswith("RESCUE_FIG_INVALID_SOURCE: FileNotFoundError:")


def test_header_only_arbitrary_columns_are_invalid_schema(tmp_path):
    source = tmp_path / "pairs.csv"
    source.write_text("arbitrary,columns\n", encoding="utf-8")
    messages = []
    assert fig_rggmci_rescue(source, tmp_path / "out.png", "TEST-STRAIN", None,
                             logger=messages.append) is None
    assert messages == [
        "RESCUE_FIG_INVALID_SCHEMA: missing columns: bgc_a,bgc_b,rggmci_confidence,rggmci_score"
    ]


def test_invalid_score_is_not_rendered_as_measured_zero(tmp_path):
    source = tmp_path / "pairs.csv"
    source.write_text(HEADERS + "left,right,not-a-number,HIGH_RG_GMCI_RESCUE\n", encoding="utf-8")
    messages = []
    assert fig_rggmci_rescue(source, tmp_path / "out.png", "TEST-STRAIN", None,
                             logger=messages.append) is None
    assert messages == ["RESCUE_FIG_INVALID_SCORE: row 2: ValueError"]


def test_measured_zero_score_remains_renderable(tmp_path, monkeypatch):
    source = tmp_path / "pairs.csv"
    source.write_text(HEADERS + "left,right,0,MODERATE_RG_GMCI_CANDIDATE\n", encoding="utf-8")
    plot = MagicMock()
    fig, ax = MagicMock(), MagicMock()
    plot.subplots.return_value = (fig, ax)
    patches = types.ModuleType("matplotlib.patches")
    patches.Patch = MagicMock()
    monkeypatch.setitem(sys.modules, "matplotlib.patches", patches)
    messages = []
    assert fig_rggmci_rescue(str(source), str(tmp_path / "out.png"), "TEST-STRAIN", plot,
                             logger=messages.append) is fig
    assert not any("INVALID" in message for message in messages)


@pytest.mark.parametrize("with_invalid_rg, expected_prefix", [
    (True, "RESCUE_FIG_INVALID_SOURCE: UnicodeDecodeError:"),
    (False, "BRIEF_IMAGE_SKIPPED: TEST-STRAIN_8a_fig_landscape.png: RuntimeError:"),
])
def test_render_brief_caller_surfaces_nonblocking_failures(
        tmp_path, monkeypatch, with_invalid_rg, expected_prefix):
    if with_invalid_rg:
        (tmp_path / "TEST-STRAIN_4A_RGGMCI_ranked_pairs.csv").write_bytes(b"\xff\xfe")
    facts = {"manifest": {"strain_id": "TEST-STRAIN"}, "rows": [],
             "strain_label": "TEST-STRAIN", "release": "PRIVATE"}
    monkeypatch.setattr(RB, "load_facts", lambda pkg: facts)
    fake_plot = MagicMock()
    monkeypatch.setattr(RB, "_setup_mpl", lambda: fake_plot)
    def fake_landscape(rows, path, *args):
        Path(path).write_bytes(b"not-an-image")
        return MagicMock()
    monkeypatch.setattr(RB, "fig_landscape", fake_landscape)
    monkeypatch.setattr(RB, "fig_composition", lambda *args: MagicMock())
    monkeypatch.setattr(RB, "_text_page", lambda *args, **kwargs: None)

    class FakePdfPages:
        def __init__(self, path): self.path = path
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def savefig(self, *args): return None

    backend = types.ModuleType("matplotlib.backends.backend_pdf")
    backend.PdfPages = FakePdfPages
    matplotlib = types.ModuleType("matplotlib")
    backends = types.ModuleType("matplotlib.backends")
    image = types.ModuleType("matplotlib.image")
    image.imread = MagicMock(side_effect=RuntimeError("image unreadable"))
    monkeypatch.setitem(sys.modules, "matplotlib", matplotlib)
    monkeypatch.setitem(sys.modules, "matplotlib.backends", backends)
    monkeypatch.setitem(sys.modules, "matplotlib.backends.backend_pdf", backend)
    monkeypatch.setitem(sys.modules, "matplotlib.image", image)
    sapote = types.ModuleType("mamey.figures_sapote")
    monkeypatch.setattr(sapote, "render_sapote_figures", lambda *args: [], raising=False)
    monkeypatch.setattr(sapote, "write_print_figure_pack", lambda *args: {}, raising=False)
    extra = types.ModuleType("mamey.figures_extra")
    monkeypatch.setattr(extra, "render_extra_figures", lambda *args: [], raising=False)
    split = types.ModuleType("mamey.figures_split")
    monkeypatch.setattr(split, "render_split_figures", lambda *args: [], raising=False)
    judgment = types.ModuleType("mamey.judgment_store")
    monkeypatch.setattr(judgment, "read_laypersons", lambda pkg: "", raising=False)
    monkeypatch.setattr(judgment, "read_fermentation", lambda pkg: "", raising=False)
    monkeypatch.setattr(judgment, "read_register", lambda pkg: {}, raising=False)
    monkeypatch.setitem(sys.modules, "mamey.figures_sapote", sapote)
    monkeypatch.setitem(sys.modules, "mamey.figures_extra", extra)
    monkeypatch.setitem(sys.modules, "mamey.figures_split", split)
    monkeypatch.setitem(sys.modules, "mamey.judgment_store", judgment)
    messages = []
    result = RB.render_brief(str(tmp_path), logger=messages.append)
    assert result["status"] == "COMPLETE", (result, messages)
    assert any(message.startswith(expected_prefix) for message in messages)
    assert not any(name.endswith("_8n_fig_rggmci_rescue.png") for name in result["files"])
