"""Card 458_placement_activity_three_state: the placement-tree activity strip gets an opt-in three-state mode.

The strip knew two states for a numeric reading: 80% or more was strong and everything else "tested, below 80%" (card f51fc51a_458_activity_legend_ruling_314 renamed them).
The thesis classes (rulings 314-316) are strong 80% or more, moderate 50-79%, low/weak 25-49%, and "active" means 50%
or more, so a 50-79% reading is not inactive. `--activity-states three` draws strong / moderate / tested, below 50% /
not tested (blank). The default stays two-state with the ruling-314 words. Synthetic data only; the readings are 95, 65, 30 and n.t.
"""
import csv
import importlib.util
import shutil
from pathlib import Path

import pytest

from .test_452_rect02_shipping import toy_run

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("placement_activity_458", ROOT / "tools" / "_placement_activity.py")
act = importlib.util.module_from_spec(spec); spec.loader.exec_module(act)

READINGS = ["95", "65", "30", "n.t."]
TWO = ["strong (≥80%)", "tested, below 80%", "tested, below 80%", "n.t."]
THREE = ["strong (≥80%)", "moderate (50–79%)", "tested, below 50%", "n.t."]
RENDER = pytest.mark.skipif(shutil.which("Rscript") is None, reason="needs R: Rscript not on PATH")


def _table(tmp_path):
    p = tmp_path / "split.tsv"
    p.write_text("strain\tC. albicans\tC. auris\n" + "".join(f"SYN-97{i}\t{v}\t{v}\n" for i, v in enumerate(READINGS)))
    return p


def _pdf_text(path):
    return _plain(_raw_pdf_text(path))


def _plain(text):
    # PDF text extraction turns the "≥" glyph into ">=" and the en dash into a minus sign.
    return text.replace("≥", ">=").replace("–", "−")


def _raw_pdf_text(path):
    try:
        import pypdf
        return "\n".join(page.extract_text() for page in pypdf.PdfReader(str(path)).pages)
    except ImportError:
        pass
    try:
        import pdfplumber
    except ImportError:
        pytest.skip("needs pypdf or pdfplumber to read the legend")
    with pdfplumber.open(str(path)) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def test_readings_95_65_30_nt_get_the_states_of_each_mode(tmp_path):
    res, _ = act.load(_table(tmp_path))
    assert [res[f"SYN-97{i}"]["C. albicans"] for i in range(4)] == TWO
    res, _ = act.load(_table(tmp_path), states="three")
    assert [res[f"SYN-97{i}"]["C. albicans"] for i in range(4)] == THREE
    for edge, want in (("80", "strong (≥80%)"), ("79", "moderate (50–79%)"), ("50", "moderate (50–79%)"),
                       ("49", "tested, below 50%"), ("0", "tested, below 50%")):
        assert act.state(edge, "three") == want
    assert act.state("79") == "tested, below 80%" and act.state("80") == "strong (≥80%)"
    for given in ("+", "−", "n.t.", ""):                      # the four recorded states never change with the mode
        assert act.state(given, "three") == act.state(given) == given
    with pytest.raises(ValueError, match="ACTIVITY_STATES_UNKNOWN"):
        act.state("65", "four")


def test_pooled_candida_ranks_three_state_labels_by_strength(tmp_path):
    p = tmp_path / "long.tsv"
    p.write_text("strain\torganism\tmaterial\tbest_pct\n" + "".join(
        f"SYN-970\t{o}\tCrude extract\t{v}\n" for o, v in
        (("C. albicans", "65"), ("C. auris", "30"), ("MRSA", "95"))))
    res, _ = act.load(p, pool=True, states="three")
    assert res["SYN-970"]["*Candida*"] == "moderate (50–79%)" and res["SYN-970"]["MRSA"] == "strong (≥80%)"
    res, _ = act.load(p, pool=True)
    assert res["SYN-970"]["*Candida*"] == "tested, below 80%"


def test_palette_legend_text_per_mode():
    rows = list(csv.DictReader((ROOT / "tools" / "phylo_display_palette.tsv").open(encoding="utf-8"), delimiter="\t"))
    by = lambda field: [r["value"] for r in rows if r["field"] == field]
    assert by("activity") == ["strong (≥80%)", "tested, below 80%", "not tested"] == by("activity_calm")
    assert by("activity_3state") == ["strong (≥80%)", "moderate (50–79%)", "tested, below 50%", "not tested"]
    assert by("activity_3state_calm") == by("activity_3state")
    for field in ("activity_3state", "activity_3state_calm"):
        colours = [r["color"] for r in rows if r["field"] == field]
        assert len(set(colours)) == 4


def test_gate_accepts_three_state_values_and_still_refuses_unknown():
    import sys
    sys.path.insert(0, str(ROOT / "tools"))
    import tree_annotation_gate as gate
    rows = [dict(tip="SYN-970", role="query", category=THREE[1], source=THREE[2]),
            dict(tip="REF-1", role="reference", category="", source="")]
    assert gate.validate_activity(rows)["status"] == "ANNOTATION_ACTIVITY_METADATA_VALIDATED"
    rows[0]["category"] = "tested, inactive"
    with pytest.raises(ValueError, match="ANNOTATION_ACTIVITY_UNSUPPORTED"):
        gate.validate_activity(rows)


def _display(tmp_path, monkeypatch, states):
    from tools import placement_display as display
    run, _ = toy_run(tmp_path, monkeypatch)
    ids = [line[1:] for line in (run / "query.aligned.fasta").read_text().splitlines() if line.startswith(">")]
    (run / "split.tsv").write_text("strain\tC. albicans\tC. auris\tanti_Candida_unspecified\tanti_MRSA\n"
                                   f"{ids[0]}\t95\t30\t\t95\n{ids[1]}\t65\tn.t.\t\t\n")
    config = run / "layouts.json"; config.write_text('{"synthetic":{"split_candida":true}}')
    out = tmp_path / f"out_{states}"
    args = [str(run), "--name", "toy", "--group", "Example", "--host-table", str(run / "hosts.tsv"),
            "--ref-source-db", str(run / "refs.sqlite"), "--strip-set", "activity", "--bioassay-table", str(run / "split.tsv"),
            "--layout", "synthetic", "--layout-config", str(config), "--label-style", "short", "--keep-all-references",
            "--out", str(out)] + (["--activity-states", states] if states else [])
    assert display.main(args) == 0
    audit = {(r["tip"], r["strip"]): r["value"] for r in
             csv.DictReader((out / "toy_rect02.activity_audit.tsv").open(), delimiter="\t")}
    return out, ids, audit


@RENDER
def test_three_state_render_draws_the_four_states_and_legend(tmp_path, monkeypatch):
    out, ids, audit = _display(tmp_path, monkeypatch, "three")
    assert [audit[(ids[0], "C. albicans")], audit[(ids[0], "C. auris")], audit[(ids[0], "MRSA")]] == [THREE[0], THREE[2], THREE[0]]
    assert [audit[(ids[1], "C. albicans")], audit[(ids[1], "C. auris")]] == [THREE[1], "n.t."]
    text = _pdf_text(out / "toy_rect02.pdf")
    for label in THREE[:3]:
        assert _plain(label) in text
    assert "inactive" not in text
    assert "Active means 50% or more" in (out / "CAPTION.md").read_text()
    script = (out / "standalone_R_package" / "toy_rerender_captioned.sh").read_text()
    assert "export GG_ACTIVITY_STATES=three" in script


@RENDER
def test_default_stays_two_state_with_the_corrected_second_label(tmp_path, monkeypatch):
    out, ids, audit = _display(tmp_path, monkeypatch, None)
    assert [audit[(ids[0], "C. albicans")], audit[(ids[0], "C. auris")]] == [TWO[0], TWO[1]]
    assert audit[(ids[1], "C. albicans")] == TWO[1]          # the 65% reading is one of the two states, as before
    text = _pdf_text(out / "toy_rect02.pdf")
    assert _plain("strong (≥80%)") in text and "tested, below 80%" in text
    assert "inactive" not in text and "moderate" not in text
    assert "Active means 50%" not in (out / "CAPTION.md").read_text()


def test_three_state_needs_activity_strips_with_split_layout(tmp_path, monkeypatch, caplog):
    from tools import placement_display as display
    run, _ = toy_run(tmp_path, monkeypatch)
    base = [str(run), "--name", "toy", "--group", "Example", "--host-table", str(run / "hosts.tsv"),
            "--ref-source-db", str(run / "refs.sqlite")]
    assert display.main(base + ["--activity-states", "three", "--out", str(tmp_path / "a")]) != 0
    assert "ACTIVITY_STATES_NEEDS_ACTIVITY_STRIPS" in caplog.text
    caplog.clear()
    assert display.main(base + ["--strip-set", "activity", "--bioassay-table", str(run / "bio.tsv"),
                                "--activity-states", "three", "--out", str(tmp_path / "b")]) != 0
    assert "ACTIVITY_STATES_NEEDS_SPLIT_CANDIDA_LAYOUT" in caplog.text
