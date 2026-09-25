"""The .442 stack pays back the silent swallows it added, without changing output.

Three `except ...: pass` handlers arrived with the .442 candidates. Two were control flow and are
rewritten without a swallow; one hid an unreadable intake file, and now leaves a breadcrumb.
"""
from pathlib import Path

from mamey import degradation
from mamey import modeb_template_emitter as mte


def test_pct_or_none_keeps_numbers_and_drops_blanks_and_text():
    assert mte._pct_or_none("98.5") == 98.5
    assert mte._pct_or_none(71) == 71.0
    assert mte._pct_or_none("") is None
    assert mte._pct_or_none(None) is None
    assert mte._pct_or_none("n/a") is None


def test_unreadable_intake_json_leaves_a_breadcrumb(tmp_path):
    pkg = tmp_path / "package"
    pkg.mkdir()
    (pkg / "S1_1_intake.json").write_text("{not json", encoding="utf-8")
    degradation.drain()
    facts = mte._bgc_facts(pkg, "S1_BGC001")
    events = degradation.drain()
    assert (facts.get("antismash_profile") or "unrecorded") == "unrecorded"
    assert any(e.get("site") == "modeb_template_emitter.antismash_profile.intake_json" for e in events), events


def test_readable_intake_json_records_nothing(tmp_path):
    pkg = tmp_path / "package"
    pkg.mkdir()
    (pkg / "S1_1_intake.json").write_text('{"antismash_profile": "relaxed"}', encoding="utf-8")
    degradation.drain()
    facts = mte._bgc_facts(pkg, "S1_BGC001")
    events = degradation.drain()
    assert facts["antismash_profile"] == "relaxed"
    assert not [e for e in events if e.get("site", "").startswith("modeb_template_emitter.antismash_profile")]


def test_render_qc_relative_paths_unchanged(tmp_path):
    import importlib.util
    import sys
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "tools"))
    spec = importlib.util.spec_from_file_location("figure_render_qc", root / "tools" / "figure_render_qc.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["figure_render_qc"] = mod
    spec.loader.exec_module(mod)
    inside = tmp_path / "figs" / "a" / "F1.png"
    inside.parent.mkdir(parents=True)
    inside.write_bytes(b"")
    outside = tmp_path / "elsewhere" / "F2.png"
    outside.parent.mkdir(parents=True)
    outside.write_bytes(b"")
    mod.write_reports([(inside, [("info", "x")]), (outside, [("info", "y")])], tmp_path / "out", [tmp_path / "figs"])
    tsv = (tmp_path / "out" / "RENDER_QC.tsv").read_text()
    assert "a/F1.png" in tsv
    assert str(outside) in tsv
