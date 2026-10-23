"""tools/hplc_trace_panels.py and tools/novel_and_active_figure.py on synthetic data only (no network, no private data).

HPLC: the native display rule keeps every source extreme and never smooths; panels and pages draw from argument folders
with argument colours; one material per figure, named in the file name; label, channel and material refusals.
Novel and active: the four assay states stay distinct; a rounded label never crosses a tier; selection uses only the
drawn material; the material is in the title and file name; 8 pt floor, stamps and receipt hashes.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("matplotlib")
pytest.importorskip("pypdf")

from tools import hplc_trace_panels as H  # noqa: E402
from tools import novel_and_active_figure as N  # noqa: E402
from tools.check_figure_provenance import stamp  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CHANNELS = ["254 nm", "210 nm", "280 nm", "330 nm"]


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _tsv(path, rows):
    with Path(path).open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]), delimiter="\t")
        w.writeheader()
        w.writerows(rows)
    return Path(path)


def _run(meta_dir, native_dir, run_id, label, points=900, channels=CHANNELS, seed=0):
    meta_dir.mkdir(exist_ok=True)
    native_dir.mkdir(exist_ok=True)
    rng = np.random.default_rng(seed)
    arrays, proof = {}, []
    for i, name in enumerate(channels):
        x = np.linspace(0.0, 20.0, points)
        y = 50 * np.exp(-((x - 5 - i) ** 2) / 0.05) + rng.normal(0, 0.5, points)
        arrays[f"x{i}"], arrays[f"y{i}"] = x, y
        proof.append({"name": name, "member": f"synthetic/{run_id}/ch{i}", "native_points": points})
    np.savez(native_dir / f"{run_id}.npz", **arrays)
    (native_dir / f"{run_id}.json").write_text(json.dumps(proof))
    (meta_dir / f"{run_id}.json").write_text(json.dumps({
        "label": label, "xmin": 0.0, "xmax": 20.0, "method": "synthetic.M", "flow": "1.000", "injection": "10.00",
        "series": [{"name": c} for c in channels]}))


@pytest.fixture
def hplc(tmp_path):
    md, nd = tmp_path / "meta", tmp_path / "native"
    _run(md, nd, "RUN_A1", "SYN-1 F3 1", seed=1)
    _run(md, nd, "RUN_B1", "SYN-2 F5 2", seed=2)
    _run(md, nd, "RUN_C1", "SYN-3 crude 1", seed=3)
    rep = _tsv(tmp_path / "REPRESENTATIVE.tsv", [
        dict(strain="SYN-1", run_id="RUN_A1", sample_label="SYN-1 F3 1", acquired="2024-01-02T10:00:00",
             material="fraction", genus="Streptomyces", chosen_by="synthetic"),
        dict(strain="SYN-2", run_id="RUN_B1", sample_label="SYN-2 F5 2", acquired="", material="fraction",
             genus="Nocardia", chosen_by="synthetic"),
        dict(strain="SYN-3", run_id="RUN_C1", sample_label="SYN-3 crude 1", acquired="2024-01-03T09:00:00",
             material="crude_extract", genus="Micromonospora", chosen_by="synthetic")])
    return tmp_path, md, nd, rep


def _common(md, nd, out):
    return ["--run-meta-dir", str(md), "--native-dir", str(nd), "--out", str(out), "--dpi", "300"]


# ------------------------------------------------------------------------------------------------- HPLC display rule

def test_display_keeps_short_channels_point_for_point():
    x = np.arange(100.0)
    y = np.sin(x)
    dx, dy = H.display(x, y, 6002, 3000)
    assert np.array_equal(dx, x) and np.array_equal(dy, y)


def test_display_keeps_every_bin_extreme_and_only_source_points():
    rng = np.random.default_rng(7)
    n = 20000
    x = np.linspace(0, 10, n)
    y = rng.normal(0, 1, n)
    y[1234] = 99.0
    y[17777] = -99.0
    y[5000:5010] = np.nan
    dx, dy = H.display(x, y, 6002, 3000)
    assert len(dx) < n
    assert np.nanmax(dy) == 99.0 and np.nanmin(dy) == -99.0
    idx = np.searchsorted(x, dx)
    assert np.array_equal(x[idx], dx)                       # only source points, nothing interpolated
    assert np.array_equal(y[idx], dy, equal_nan=True)       # values untouched, no smoothing
    edges = np.linspace(0, n, 3001, dtype=int)
    kept = set(idx.tolist())
    for a, b in zip(edges[:-1], edges[1:]):
        v = y[a:b]
        if np.isfinite(v).any():
            assert a + int(np.nanargmin(v)) in kept and a + int(np.nanargmax(v)) in kept


# ------------------------------------------------------------------------------------------------------ HPLC panels

def test_panels_draw_one_material_with_argument_colours(hplc):
    tmp, md, nd, rep = hplc
    out = tmp / "panels"
    colors = "210=#111111,254=#222222,280=#333333,330=#444444"
    rc = H.main(["panels", "--representative", str(rep), "--strains", "SYN-1,SYN-2", "--channel-colors", colors,
                 "--name", "Synthetic", *_common(md, nd, out)])
    assert rc == 0
    stem = out / "Synthetic_fraction_HPLC_UV_panels"
    for ext in (".png", ".pdf", ".svg"):
        assert stem.with_suffix(ext).is_file()
        assert stamp(stem.with_suffix(ext))[0] == "PASS"
    svg = stem.with_suffix(".svg").read_text().lower()
    assert all(c in svg for c in ("#111111", "#222222", "#333333", "#444444"))
    assert "#087c87" not in svg
    runs = list(csv.DictReader((out / "Synthetic_fraction_HPLC_UV_panels_runs.tsv").open(), delimiter="\t"))
    assert [r["panel"] for r in runs] == ["A", "B"] and {r["material"] for r in runs} == {"fraction"}
    rec = json.loads((out / "receipt.json").read_text())
    assert rec["inputs"][str(rep)] == _sha(rep)
    assert rec["inputs"][str(nd / "RUN_A1.npz")] == _sha(nd / "RUN_A1.npz")
    assert rec["outputs"][stem.name + ".png"] == _sha(stem.with_suffix(".png"))
    assert rec["min_text"][0]["status"] == "PASS" and rec["min_text"][0]["smallest_pt"] >= 8
    assert rec["display_rule"]["smoothing"] == "none"
    assert "fraction" in (out / "Synthetic_fraction_HPLC_UV_panels_CAPTION.md").read_text()


def test_panels_refuse_mixed_material_before_writing(hplc):
    tmp, md, nd, rep = hplc
    out = tmp / "mixed"
    assert H.main(["panels", "--representative", str(rep), *_common(md, nd, out)]) == H.EXIT_INPUT
    assert not out.exists()


def test_panels_refuse_label_mismatch_and_unknown_channel(hplc):
    tmp, md, nd, rep = hplc
    bad = _tsv(tmp / "bad.tsv", [dict(strain="SYN-1", run_id="RUN_A1", sample_label="wrong", acquired="",
                                      material="fraction", genus="Streptomyces")])
    assert H.main(["panels", "--representative", str(bad), *_common(md, nd, tmp / "o1")]) == H.EXIT_INPUT
    assert H.main(["panels", "--representative", str(rep), "--strains", "SYN-1",
                   "--channel-colors", "210=#111111,254=#222222", *_common(md, nd, tmp / "o2")]) == H.EXIT_INPUT
    assert not (tmp / "o1").exists() and not (tmp / "o2").exists()


def test_panels_refuse_missing_genus_and_bad_material(hplc):
    tmp, md, nd, _ = hplc
    nog = _tsv(tmp / "nog.tsv", [dict(strain="SYN-1", run_id="RUN_A1", sample_label="SYN-1 F3 1", acquired="",
                                      material="fraction")])
    assert H.main(["panels", "--representative", str(nog), *_common(md, nd, tmp / "o3")]) == H.EXIT_INPUT
    assert H.main(["panels", "--representative", str(nog), "--genus", "SYN-1=Streptomyces",
                   *_common(md, nd, tmp / "o4")]) == 0
    pooled = _tsv(tmp / "pooled.tsv", [dict(strain="SYN-1", run_id="RUN_A1", sample_label="SYN-1 F3 1", acquired="",
                                            material="pooled", genus="Streptomyces")])
    assert H.main(["panels", "--representative", str(pooled), *_common(md, nd, tmp / "o5")]) == H.EXIT_INPUT


# ------------------------------------------------------------------------------------------------------- HPLC pages

def test_pages_split_by_four_and_order_by_acquisition(tmp_path):
    md, nd = tmp_path / "meta", tmp_path / "native"
    rows = []
    times = ["2024-03-01T10:00:00", "", "2024-01-01T10:00:00", "2024-02-01T10:00:00", "2024-01-15T10:00:00"]
    for i, t in enumerate(times):
        rid = f"RUN_{i}"
        _run(md, nd, rid, f"SYN-9 F{i}", points=7000 if i == 0 else 500, seed=i)
        rows.append(dict(strain="SYN-9", run_id=rid, sample_label=f"SYN-9 F{i}", acquired=t, material="fraction",
                         pick_number=str(i + 1)))
    runs = _tsv(tmp_path / "runs.tsv", rows)
    out = tmp_path / "pages"
    assert H.main(["pages", "--runs", str(runs), *_common(md, nd, out)]) == 0
    sd = out / "SYN-9"
    assert (sd / "SYN-9_fraction_HPLC_UV_chromatograms_page_a.pdf").is_file()
    assert (sd / "SYN-9_fraction_HPLC_UV_chromatograms_page_b.png").is_file()
    got = list(csv.DictReader((sd / "runs.tsv").open(), delimiter="\t"))
    assert [r["run_id"] for r in got] == ["RUN_2", "RUN_4", "RUN_3", "RUN_0", "RUN_1"]   # undated run last
    assert [r["page"] for r in got] == ["a", "a", "a", "a", "b"]
    rec = json.loads((out / "receipt.json").read_text())
    assert all(m["status"] == "PASS" for m in rec["min_text"])


def test_pages_single_page_without_letter(tmp_path):
    md, nd = tmp_path / "meta", tmp_path / "native"
    _run(md, nd, "RUN_X", "SYN-8 F1")
    runs = _tsv(tmp_path / "runs.tsv", [dict(strain="SYN-8", run_id="RUN_X", sample_label="SYN-8 F1",
                                             acquired="", material="crude_extract")])
    out = tmp_path / "one"
    assert H.main(["pages", "--runs", str(runs), "--single-page-without-letter", *_common(md, nd, out)]) == 0
    assert (out / "SYN-8" / "SYN-8_crude_extract_HPLC_UV_chromatograms.svg").is_file()


def test_no_built_in_data_paths():
    for tool in ("hplc_trace_panels.py", "novel_and_active_figure.py"):
        src = (ROOT / "tools" / tool).read_text()
        assert "/Users/" not in src and "Codex" not in src and "print(" not in src


# --------------------------------------------------------------------------------------------- novel-and-active


def _iso(strain, genus, ident, rar, dd="", **assays):
    row = dict(strain=strain, genus_as_deposited=genus, id16s_pct=ident, genbank_strains_ge98_65=rar, dddh_d4=dd)
    for t in ("MRSA", "C. albicans", "C. auris", "E. coli", "P. larvae"):
        for m in ("crude", "fraction"):
            row[f"{t}|{m}"] = "n.t."
    for k, v in assays.items():
        t, m = k.rsplit("__", 1)
        row[f"{t.replace('_', ' ').replace('Cx', 'C.').replace('Ex', 'E.').replace('Px', 'P.')}|{m}"] = v
    return row


@pytest.fixture
def novel_table(tmp_path):
    rows = [
        _iso("SYN-10", "Streptomyces", "97.50", "5", "45.2", MRSA__crude="85.00", MRSA__fraction="12.00"),
        _iso("SYN-2", "Streptomyces", "99.10", "1", "", Cx_albicans__fraction="62.40", Cx_albicans__crude=""),
        _iso("SYN-3", "Nocardia", "99.50", "40", "", MRSA__crude="95.00"),              # active, not novel
        _iso("SYN-4", "Kribbella", "", "", "", MRSA__crude="70.00"),                     # no 16S, no rarity: n.a.
    ]
    return _tsv(tmp_path / "table.tsv", rows)


def test_tile_states_keep_four_states_and_refuse_tier_crossing():
    assert N.tile_state("n.t.", 50, 80, "x") == ("n.t.", "n.t.")
    assert N.tile_state("", 50, 80, "x") == ("blank", "")
    assert N.tile_state("80.0", 50, 80, "x") == ("strong", "80")
    assert N.tile_state("50", 50, 80, "x") == ("moderate", "50")
    assert N.tile_state("0", 50, 80, "x") == ("below", "0")
    with pytest.raises(N.InputError):
        N.tile_state("79.6", 50, 80, "x")      # moderate, but the label would read 80
    with pytest.raises(N.InputError):
        N.tile_state("49.5", 50, 80, "x")      # below, but the label would read 50


def test_selection_uses_only_the_drawn_material(novel_table, tmp_path):
    def drawn(material):
        out = tmp_path / f"o_{material}"
        assert N.main(["--table", str(novel_table), "--material", material, "--out", str(out), "--dpi", "300"]) == 0
        tag = N.FILE_TAG[material]
        rows = list(csv.DictReader((out / f"NOVEL_AND_ACTIVE_{tag}_plot_data_left_columns.tsv").open(), delimiter="\t"))
        return [r["strain"] for r in rows], out, tag
    crude, _, _ = drawn("crude_extract")
    frac, _, _ = drawn("fraction")
    both, out, tag = drawn("side_by_side")
    assert crude == ["SYN-10"]                  # SYN-2 is active only as a fraction
    assert frac == ["SYN-2"]                    # SYN-10's fraction is 12 %
    assert both == ["SYN-2", "SYN-10"]          # by genus, then strain in natural order
    tiles = list(csv.DictReader((out / f"NOVEL_AND_ACTIVE_{tag}_plot_data_tiles.tsv").open(), delimiter="\t"))
    assert {t["material"] for t in tiles} == {"crude_extract", "fraction"}
    syn2 = {(t["target"], t["material"]): t["state"] for t in tiles if t["strain"] == "SYN-2"}
    assert syn2[("C. albicans", "crude_extract")] == "blank" and syn2[("MRSA", "crude_extract")] == "n.t."


def test_outputs_name_material_and_pass_text_floor(novel_table, tmp_path):
    out = tmp_path / "fig"
    assert N.main(["--table", str(novel_table), "--material", "side_by_side", "--out", str(out), "--dpi", "300",
                   "--name", "SYN_FIG"]) == 0
    stem = out / "SYN_FIG_crude_extract_and_fraction"
    for ext in (".png", ".pdf", ".svg"):
        assert stamp(stem.with_suffix(ext))[0] == "PASS"
    svg = stem.with_suffix(".svg").read_text()
    assert "Crude extract and fraction" in svg
    rec = json.loads((out / "receipt.json").read_text())
    assert rec["min_text"]["status"] == "PASS" and rec["min_text"]["smallest_pt"] >= 8
    assert rec["inputs"][str(novel_table)] == _sha(novel_table)
    assert rec["outputs"][stem.name + ".pdf"] == _sha(stem.with_suffix(".pdf"))
    assert json.loads(stem.with_name(stem.name + "_PRINT_SIZE.json").read_text())["width_in"] == 6.5
    assert N.main(["--table", str(novel_table), "--material", "fraction", "--out", str(out)]) == N.EXIT_INPUT


def test_all_rows_print_na_for_missing_values(novel_table, tmp_path):
    out = tmp_path / "all"
    assert N.main(["--table", str(novel_table), "--material", "crude_extract", "--rows", "all", "--out", str(out),
                   "--dpi", "300"]) == 0
    left = {r["strain"]: r for r in csv.DictReader(
        (out / "NOVEL_AND_ACTIVE_crude_extract_plot_data_left_columns.tsv").open(), delimiter="\t")}
    assert left["SYN-4"]["id16s_pct"] == "n.a." and left["SYN-4"]["genbank_strains"] == "n.a."
    assert left["SYN-4"]["dddh_d4"] == "" and left["SYN-10"]["dddh_d4"] == "45.2"


def test_refusals(novel_table, tmp_path):
    base = ["--table", str(novel_table), "--dpi", "300"]
    assert N.main(base + ["--material", "fraction", "--title", "Isolates", "--out", str(tmp_path / "t1")]) == N.EXIT_INPUT
    assert N.main(base + ["--material", "side_by_side", "--title", "Fraction", "--out", str(tmp_path / "t2")]) == N.EXIT_INPUT
    assert N.main(base + ["--material", "fraction", "--active-pct", "90", "--out", str(tmp_path / "t3")]) == N.EXIT_INPUT
    flagged = list(csv.DictReader(novel_table.open(), delimiter="\t"))
    for r in flagged:
        r["novel_by_identity"] = "no"          # SYN-10 is 97.50 %: the flag disagrees with the value
    bad = _tsv(tmp_path / "flag.tsv", flagged)
    assert N.main(["--table", str(bad), "--material", "fraction", "--out", str(tmp_path / "t4")]) == N.EXIT_INPUT
    assert not any((tmp_path / f"t{i}").exists() for i in range(1, 5))
