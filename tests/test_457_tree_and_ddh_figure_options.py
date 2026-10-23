"""Card 457 tree and dDDH figure options: tools/max4_tree_figure.py, the render_max4_tree.R options it drives, and the
taxonomy_T05_figures.py genus highlight. Synthetic data only; the two drawing tests skip without R and its packages."""
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "max4_tree_figure.py"
RENDERER = ROOT / "tools" / "render_max4_tree.R"
T05 = ROOT / "tools" / "taxonomy_T05_figures.py"
TREE = "((SYN-1:0.1,GCF_000000001.1:0.12)88/95:0.05,(GCF_000000002.1:0.2,GCF_000000003.1:0.15)70/60:0.1,GCF_000000009.1:0.6);\n"


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


M4 = _load(TOOL, "max4_tree_figure_uut")


def _tsv(path, rows):
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return path


def _rows(path):
    with path.open(newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def _ncbi(tmp_path):
    data = {
        "GCF_000000001.1": {"organism": "Synthetica alpha", "strain": "DSM 1", "fromtype": "assembly from type material",
                            "isolation_source": "soil", "geo_loc_name": "Chile: Atacama"},
        "GCF_000000002.1": {"organism": "Synthetica beta X2", "strain": "X2", "fromtype": "",
                            "isolation_source": "missing", "host": "Apis mellifera", "geo_loc_name": "not applicable"},
        "GCF_000000003.1": {"organism": "Synthetica gamma", "strain": "", "fromtype": "",
                            "isolation_source": "", "geo_loc_name": ""},
        "GCF_000000009.1": {"organism": "Outgroupia remota", "strain": "Z9", "fromtype": "assembly from type material",
                            "isolation_source": "marine sediment", "geo_loc_name": "Japan"},
    }
    p = tmp_path / "ncbi.json"
    p.write_text(json.dumps(data))
    q = _tsv(tmp_path / "queries.tsv", [{"tip": "SYN-1", "label_concise": "Synthetica sp. SYN-1 [host; place]",
                                         "source_display": "Honeybees", "geography_display": "USA", "genus": "Streptomyces"}])
    return p, q


def test_metadata_from_ncbi_records_follows_tip_label_rules(tmp_path):
    ncbi, queries = _ncbi(tmp_path)
    tree = tmp_path / "t.treefile"
    tree.write_text(TREE)
    out = tmp_path / "meta.tsv"
    rc = M4.main(["metadata", "--out", str(out), "--queries", str(queries), "--ncbi-json", str(ncbi), "--tree", str(tree),
                  "--outgroup", "GCF_000000009.1", "--country-part", "--source-from-host", "--strip-query-brackets"])
    assert rc == 0
    rows = {r["tip"]: r for r in _rows(out)}
    assert [r["tip"] for r in _rows(out)] == ["SYN-1", "GCF_000000001.1", "GCF_000000002.1", "GCF_000000003.1", "GCF_000000009.1"]
    assert rows["GCF_000000001.1"]["label_concise"] == "Synthetica alpha DSM 1 [Type] (GCF_000000001.1)"
    assert rows["GCF_000000002.1"]["label_concise"] == "Synthetica beta X2 (GCF_000000002.1)"   # strain already in the name
    assert "[Type]" not in rows["GCF_000000003.1"]["label_concise"]
    assert rows["GCF_000000001.1"]["geography_display"] == "Chile"
    assert rows["GCF_000000002.1"]["source_display"] == "host: Apis mellifera"
    assert rows["GCF_000000002.1"]["geography_display"] == ""        # no placeholder for "not applicable"
    assert rows["GCF_000000009.1"]["role"] == "OUTGROUP" and rows["SYN-1"]["role"] == "QUERY"
    assert rows["SYN-1"]["label_concise"] == "Synthetica sp. SYN-1"
    receipt = json.loads((tmp_path / "meta_receipt.json").read_text())
    assert receipt["summary"]["no_deposited_source_or_country"] == ["Synthetica gamma (GCF_000000003.1)"]
    out_hash = {Path(o["path"]).name: o["sha256"] for o in receipt["outputs"]}
    assert out_hash["meta.tsv"] == hashlib.sha256(out.read_bytes()).hexdigest()
    assert any(Path(i["path"]).name == "ncbi.json" for i in receipt["inputs"])
    kinds = [r["kind"] for r in _rows(tmp_path / "meta_changes.tsv")]
    assert kinds == ["label"]


def test_metadata_edits_are_explicit_and_logged(tmp_path):
    table = _tsv(tmp_path / "in.tsv", [
        {"tip": "Q1", "role": "QUERY", "label_concise": "Synthetica sp. Q1 [Bees; USA]", "source_display": "Bees",
         "geography_display": ""},
        {"tip": "R1", "role": "REFERENCE", "label_concise": "Synthetica alpha DSM 1 (GCF_000000001.1)",
         "source_display": "not deposited", "geography_display": "Chile"},
        {"tip": "R2", "role": "OUTGROUP", "label_concise": "Outgroupia remota Z9 [outgroup] (GCF_000000009.1)",
         "source_display": "sediment from a very deep marine trench near an island", "geography_display": "Japan"}])
    over = _tsv(tmp_path / "over.tsv", [{"tip": "Q1", "field": "geography_display", "value": "USA", "reason": "owner ruling"}])
    fill = _tsv(tmp_path / "fill.tsv", [
        {"accession": "GCF_000000001.1", "field": "source_display", "value": "soil", "evidence": "culture collection record"},
        {"accession": "GCF_000000009.1", "field": "geography_display", "value": "China", "evidence": "other record"}])
    out = tmp_path / "meta.tsv"
    rc = M4.main(["metadata", "--out", str(out), "--table", str(table), "--overrides", str(over), "--fill-blank", str(fill),
                  "--strip-query-brackets", "--strip-text", " [outgroup]", "--shorten", "20"])
    assert rc == 0
    rows = {r["tip"]: r for r in _rows(out)}
    assert rows["Q1"]["label_concise"] == "Synthetica sp. Q1" and rows["Q1"]["geography_display"] == "USA"
    assert rows["R1"]["source_display"] == "soil"
    assert rows["R2"]["geography_display"] == "Japan"                   # deposited value is never overwritten
    assert rows["R2"]["label_concise"] == "Outgroupia remota Z9 (GCF_000000009.1)"
    assert rows["R2"]["source_display"].endswith("...") and len(rows["R2"]["source_display"]) <= 23
    short = _rows(tmp_path / "meta_shortened.tsv")
    assert short[0]["full"] == "sediment from a very deep marine trench near an island"
    kinds = sorted(r["kind"] for r in _rows(tmp_path / "meta_changes.tsv"))
    assert kinds == ["filled", "kept_deposited", "label", "label", "override", "shortened"]
    again = M4.main(["metadata", "--out", str(out), "--table", str(table)])
    assert again == 2                                                     # refuses to overwrite


def test_metadata_refusals(tmp_path):
    base = {"tip": "R1", "role": "REFERENCE", "label_concise": "Synthetica alpha DSM 1 [Type] (GCF_000000001.1)",
            "source_display": "soil", "geography_display": "Chile"}
    bad_type = _tsv(tmp_path / "type.tsv", [dict(base, type_material="")])
    assert M4.main(["metadata", "--out", str(tmp_path / "a.tsv"), "--table", str(bad_type)]) == 0   # unverifiable: listed
    assert json.loads((tmp_path / "a_receipt.json").read_text())["type_label_without_ncbi_field"] == ["R1"]
    wrong = _tsv(tmp_path / "wrong.tsv", [dict(base, type_material="assembly from synonym type material")])
    assert M4.main(["metadata", "--out", str(tmp_path / "b.tsv"), "--table", str(wrong)]) == 2
    refs = [dict(base, tip=f"R{i}", label_concise=f"Synthetica alpha S{i} (GCF_00000000{i}.1)", anchor="Q1") for i in range(5)]
    many = _tsv(tmp_path / "many.tsv", [{"tip": "Q1", "role": "QUERY", "label_concise": "Synthetica sp. Q1",
                                         "source_display": "", "geography_display": "", "anchor": ""}] + refs)
    assert M4.main(["metadata", "--out", str(tmp_path / "c.tsv"), "--table", str(many), "--max-refs-per-query", "4"]) == 2
    assert M4.main(["metadata", "--out", str(tmp_path / "d.tsv"), "--table", str(many)]) == 0
    assert json.loads((tmp_path / "d_receipt.json").read_text())["summary"]["references_per_query"] == {"Q1": 5}
    tree = tmp_path / "t.nwk"
    tree.write_text("(R0:0.1,R1:0.1,MISSING:0.2);")
    assert M4.main(["metadata", "--out", str(tmp_path / "e.tsv"), "--table", str(many), "--tree", str(tree)]) == 2
    bad_role = _tsv(tmp_path / "role.tsv", [dict(base, role="Reference")])
    assert M4.main(["metadata", "--out", str(tmp_path / "f.tsv"), "--table", str(bad_role)]) == 2


def _meta_for_tree(tmp_path):
    ncbi, queries = _ncbi(tmp_path)
    tree = tmp_path / "t.treefile"
    tree.write_text(TREE)
    meta = tmp_path / "meta.tsv"
    assert M4.main(["metadata", "--out", str(meta), "--queries", str(queries), "--ncbi-json", str(ncbi),
                    "--outgroup", "GCF_000000009.1"]) == 0
    rows = _rows(meta)
    for r in rows:
        r["genus"] = r["genus"] or r["label_concise"].split()[0]
    _tsv(meta, rows)
    return tree, meta


def test_render_dry_run_receipt_options_and_palette(tmp_path):
    tree, meta = _meta_for_tree(tmp_path)
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps({"options": {"width": 9.6, "max4_root": "GCF_000000009.1", "support_bg": True,
                                            "SUPPORT_MIN": 70, "lab": 8}}))
    stem = tmp_path / "fig" / "tree"
    rc = M4.main(["render", "--tree", str(tree), "--metadata", str(meta), "--out", str(stem), "--spec", str(spec),
                  "--set", "WIDTH=7.3", "--genus-dots", "--genus-colour", "Streptomyces=0f4c5c", "--dry-run"])
    assert rc == 0
    receipt = json.loads((tmp_path / "fig" / "tree_receipt.json").read_text())
    assert receipt["status"] == "DRY_RUN"
    opts = receipt["options"]
    assert opts["MAX4_WIDTH"] == "7.3" and opts["MAX4_ROOT"] == "GCF_000000009.1" and opts["MAX4_SUPPORT_BG"] == "1"
    assert opts["MAX4_GENUS_DOTS"].endswith("tree_genus_palette.tsv")
    pal = {r["genus"]: r["colour"] for r in _rows(tmp_path / "fig" / "tree_genus_palette.tsv")}
    assert pal["Streptomyces"] == "#0f4c5c" and "Synthetica" in pal
    names = {Path(i["path"]).name for i in receipt["inputs"]}
    assert {"t.treefile", "meta.tsv", "spec.json", "render_max4_tree.R", "max4_tree_figure.py", "genus_palette.json"} <= names
    assert receipt["command"][1].endswith("render_max4_tree.R")


def test_render_refuses_small_text_unknown_options_and_overwrite(tmp_path):
    tree, meta = _meta_for_tree(tmp_path)
    stem = tmp_path / "tree"
    base = ["render", "--tree", str(tree), "--metadata", str(meta), "--out", str(stem), "--dry-run"]
    assert M4.main(base + ["--set", "SMALL=6"]) == 2
    assert M4.main(base + ["--set", "COLOUR_BY_HOPE=1"]) == 2
    assert M4.main(base) == 0
    assert M4.main(base) == 2


def test_renderer_and_driver_share_one_option_set():
    r = RENDERER.read_text()
    used = set(re.findall(r"(?:Sys\.getenv|env|num|on)\('MAX4_([A-Z_]+)'", r))
    assert used == M4.OPTIONS
    assert "MAX4_TEXT_BELOW_8PT" in r and "num('MAX4_LAB','8')" in r and "num('MAX4_SMALL','8')" in r
    assert "value_as_deposited" in r and "sapote_stamp_files" in r and "MAX4_REFUSE_OVERWRITE" in r
    for text in (r, TOOL.read_text()):
        assert "/Users/" not in text and "Claude_Alex" not in text and not re.search(r"\bAS-\d", text)


def test_driver_house_conventions():
    code = TOOL.read_text()
    assert "from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter" in code
    assert "from mamey.logging_setup import get_logger" in code
    assert not re.search(r"(?<![\w.])print\(", code)


def test_t05_highlight_parse_and_validation(tmp_path):
    pytest.importorskip("pypdf")
    t05 = _load(T05, "t05_uut")
    assert t05.parse_highlight(["Streptomyces=0f4c5c"]) == {"Streptomyces": "#0F4C5C"}
    for bad in (["Streptomyces"], ["=0F4C5C"], ["Streptomyces=#12345"], ["Streptomyces=GGGGGG"]):
        with pytest.raises(ValueError):
            t05.parse_highlight(bad)
    text = T05.read_text()
    assert "hybridisation" not in text and "--highlight-genus" in text and "ref_accession" in text
    assert not re.search(r"#[0-9A-Fa-f]{6}", text.split("R_SCRIPT =")[0])


def _r_has(*pkgs):
    rs = shutil.which("Rscript")
    if not rs:
        return False
    probe = "quit(status=as.integer(!all(sapply(c(%s),requireNamespace,quietly=TRUE))))" % ",".join(f"'{p}'" for p in pkgs)
    return subprocess.run([rs, "-e", probe], capture_output=True).returncode == 0


def test_t05_highlight_renders(tmp_path):
    if not _r_has("ggplot2", "dplyr", "ggrepel", "ggtext", "svglite"):
        pytest.skip("R packages for T05 not installed")
    cohort = _tsv(tmp_path / "cohort.tsv", [
        {"strain": "SYN-971", "genus": "Streptomyces", "block": "isolates", "label_md": ""},
        {"strain": "SYN-972", "genus": "Nocardia", "block": "isolates", "label_md": "Nocardiaceae bacterium SYN-972"}])
    data = _tsv(tmp_path / "data.tsv", [
        {"strain": "SYN-971", "d4": "77.6", "d4_ci_low": "76", "d4_ci_high": "79", "type_strain": "Streptomyces example",
         "ref_name": "Streptomyces example", "ref_strain": "DSM 1", "ref_accession": "GCA_000000001"},
        {"strain": "SYN-972", "d4": "30", "d4_ci_low": "29", "d4_ci_high": "31", "type_strain": "Nocardia example",
         "ref_name": "", "ref_strain": "", "ref_accession": ""}])
    out = tmp_path / "fig"
    cmd = [sys.executable, str(T05), "--cohort", str(cohort), "--data", str(data), "--out", str(out), "--dpi", "72",
           "--highlight-genus", "Streptomyces=0F4C5C", "--legend-title", "Genus", "--legend-rows", "1", "--x-max", "101"]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    assert res.returncode == 0, res.stdout + res.stderr
    run = json.loads((tmp_path / "fig_run.json").read_text())
    assert run["highlight_genus"] == {"Streptomyces": "#0F4C5C"} and run["settings"]["x_max"] == 101
    bad = subprocess.run(cmd[:-8] + ["--out", str(tmp_path / "g"), "--highlight-genus", "Kribbella=0F4C5C"],
                         capture_output=True, text=True, timeout=180)
    assert bad.returncode != 0 and "not among plotted genera" in bad.stderr


def test_tree_renders_with_new_options(tmp_path):
    if not _r_has("ape", "ggtree", "ggplot2", "patchwork", "phangorn"):
        pytest.skip("R tree packages not installed")
    tree, meta = _meta_for_tree(tmp_path)
    rows = _rows(meta)
    for r in rows:
        r["host_group"] = "Bees" if r["role"] == "QUERY" else ""
    rows.append({k: "" for k in rows[0]} | {"tip": "NOT_IN_TREE", "role": "REFERENCE", "label_concise": "Extra x (GCF_1.1)"})
    _tsv(meta, rows)
    groups = _tsv(tmp_path / "groups.tsv", [{"group": "Bees", "colour": "#E69F00"}])
    stem = tmp_path / "tree"
    rc = M4.main(["render", "--tree", str(tree), "--metadata", str(meta), "--out", str(stem), "--genus-dots",
                  "--query-groups", str(groups), "--set", "ROOT=GCF_000000009.1", "--set", "DROP_ROOT=1",
                  "--set", "META_EXTRA=1", "--set", "SP_ROMAN=1", "--set", "WIDTH=7.5", "--set", "PAD=0.6",
                  "--set", "MIN_BRANCH=1.0", "--set", "DPI=150"])
    receipt = json.loads((tmp_path / "tree_receipt.json").read_text())
    assert rc == 0, receipt
    assert receipt["status"] == "PASS" and receipt["min_text"]["smallest_pt"] >= 8 - 0.05
    for suffix in ("pdf", "png"):
        assert b"Sapote-Mamey render_max4_tree.R" in (tmp_path / f"tree.{suffix}").read_bytes()
    assert any("rooted on, not drawn" in line for line in receipt["renderer_stdout"])
