"""v9.7.455: tools/paper_cohort_registry.py builds a strain roster from the union of member tables, maps
where each strain's evidence is stored, and lists, without resolving, every disagreement between sources.
Synthetic strain IDs only (AS-970..AS-999)."""
import csv
import hashlib
import importlib.util
import json
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "paper_cohort_registry.py"
spec = importlib.util.spec_from_file_location("paper_cohort_registry", TOOL)
reg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reg)

ID = "^\\W*(?P<strain>AS-\\d+)(?!\\d)"
ANYWHERE = "(?<![A-Za-z0-9-])(?P<strain>AS-\\d+)(?!\\d)"


def _tsv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        csv.writer(stream, delimiter="\t", lineterminator="\n").writerows(rows)
    return path


def _zip(path, members):
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as zf:
        for name in members:
            zf.writestr(name, "{}")


def _read(path):
    with path.open(encoding="utf-8") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


@pytest.fixture
def cohort(tmp_path, monkeypatch):
    monkeypatch.delenv("SAPOTE_ASSEMBLY_AUTHORITY", raising=False)
    monkeypatch.delenv("MAMEY_PACKAGE_HOMES", raising=False)
    _tsv(tmp_path / "paper.tsv", [
        ["isolate", "paper", "genus"],
        ["AS-971", "P1", "Streptomyces"],
        ["AS-972", "P2", "Nocardia"],
        ["AS-990", "P1", "Streptomyces"],
    ])
    _tsv(tmp_path / "table.tsv", [
        ["Strain Number", "Genus (16S)", "% similarity", "Genbank Accession"],
        ["AS-971 ‡", "S.", "0.986", "px000001"],
        ["AS-972", "Rhodococcus sp.", "789/790", "PX000002"],
        ["AS-973", "Unassigned", "N/A", ""],
        ["AS-991", "Streptomyces", "", ""],
        ["AS-990", "Streptomyces", "", ""],
        ["Footnote: AS-972 was re-tested", "", "", ""],
    ])
    _tsv(tmp_path / "check.tsv", [
        ["strain", "pct", "acc"],
        ["AS-971", "98.6", "PX000001"],
        ["AS-972", "99.9", "PX000002"],
        ["AS-973", "97.0", "PX000003"],
    ])
    _tsv(tmp_path / "meta.tsv", [
        ["tip_label", "excluded", "exclusion_reason"],
        ["AS-971", "", ""],
        ["AS-972", "yes", "contaminated assembly"],
    ])
    (tmp_path / "excl.json").write_text(json.dumps({"hard_excluded": ["AS-971", "AS-980"]}))
    _tsv(tmp_path / "assay.tsv", [
        ["isolate", "material", "organism", "class"],
        ["AS-971", "crude", "MRSA", "strong"],
        ["AS-971", "crude", "C. albicans", "weak"],
        ["AS-971", "fraction", "MRSA", "strong"],
        ["SID1", "crude", "MRSA", "strong"],
    ])
    _tsv(tmp_path / "s16" / "a.tsv", [["strain", "identity"], ["AS-971", "99.1"]])
    _tsv(tmp_path / "s16" / "b.tsv", [["strain", "identity"], ["AS-972", "98.2"]])
    for folder in ("Strains/AS-971/mode_b_a", "Strains/AS-971/mode_b_b", "Strains/AS-9710/mode_b_x"):
        (tmp_path / folder).mkdir(parents=True)
    _zip(tmp_path / "Home" / "_ANTISMASH_CANONICAL" / "loose" / "AS-971.zip", ["AS-971.json"])
    _zip(tmp_path / "Home" / "_ANTISMASH_CANONICAL" / "loose" / "AS-972.zip", ["input/AS-972.json"])
    _zip(tmp_path / "mamey_packages" / "AS-971" / "AS-971_SapoteMamey_v9.7.448_engine1.9.173_loose_Complete_Package.zip",
         ["manifest.json"])
    s = {"schema": "sapote.paper-cohort-spec.v2", "cohort": "synthetic", "root": ".", "strain_regex": ID,
         "aliases": {"AS-991": "AS-990"}, "not_recorded": ["N/A", "Unassigned"], "summary_by": "paper",
         "members": [
             {"name": "paper", "path": "paper.tsv", "strain_column": "isolate", "label_column": "paper",
              "fields": {"genus_16s": "genus"}, "compare": {"genus_16s": "genus"}},
             {"name": "table", "path": "table.tsv", "strain_column": "Strain Number",
              "fields": {"genus_16s": "Genus (16S)", "pct_16s": "% similarity", "accession_16s": "Genbank Accession"},
              "compare": {"genus_16s": "genus", "pct_16s": "percent", "accession_16s": "accession"}},
             {"name": "check", "path": "check.tsv", "strain_column": "strain", "covers_cohort": True,
              "fields": {"pct_16s": "pct", "accession_16s": "acc"},
              "compare": {"pct_16s": "percent", "accession_16s": "accession"}}],
         "exclusions": [
             {"name": "meta", "path": "meta.tsv", "strain_column": "tip_label", "flag_column": "excluded",
              "reason_column": "exclusion_reason"},
             {"name": "json", "path": "excl.json", "json_keys": ["hard_excluded"]}],
         "evidence": [
             {"name": "assay_crude", "kind": "table", "stage": "bioassay", "path": "assay.tsv", "strain_column": "isolate",
              "filter": {"material": "crude"}, "value_columns": ["organism", "class"], "meaning": "best reading"},
             {"name": "s16", "kind": "table", "stage": "16S", "paths": ["s16/a.tsv", "s16/b.tsv"], "strain_column": "strain",
              "value": "rows"},
             {"name": "cards", "kind": "files", "stage": "cards", "glob": "Strains/AS-*/mode_b*", "strain_regex": ANYWHERE},
             {"name": "antismash_loose", "kind": "bundle_home", "item": "antismash_zip", "flavor": "loose"},
             {"name": "package", "kind": "bundle_home", "item": "mamey_package"}]}
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(s))
    return tmp_path, spec_path


def test_roster_is_the_union_with_membership_and_field_sources(cohort):
    tmp, spec_path = cohort
    receipt = reg.build(spec_path, tmp / "out")
    roster = {r["strain"]: r for r in _read(tmp / "out" / "ROSTER.tsv")}
    assert list(roster) == ["AS-971", "AS-972", "AS-973", "AS-990"]
    assert roster["AS-971"]["in_paper"] == "P1" and roster["AS-973"]["in_paper"] == "no"
    assert roster["AS-971"]["in_table"] == "yes ‡"  # text around the ID is kept
    assert roster["AS-990"]["in_table"] == "yes (recorded as AS-991)"
    assert roster["AS-971"]["genus_16s"] == "Streptomyces" and roster["AS-971"]["genus_16s_from"] == "paper"
    assert roster["AS-973"]["genus_16s"] == "Unassigned" and roster["AS-973"]["genus_16s_from"] == "table"
    assert roster["AS-971"]["pct_16s"] == "0.986"  # stored exactly as written
    assert receipt["strains"] == 4 and receipt["aliases_applied"] == {"AS-991": 1}


def test_held_lists_real_differences_only(cohort):
    tmp, spec_path = cohort
    reg.build(spec_path, tmp / "out")
    held = _read(tmp / "out" / "HELD.tsv")
    kinds = {(h["kind"], h["strain"], h["field"]) for h in held}
    assert ("FIELD_DIFFERS", "AS-972", "genus_16s") in kinds  # Nocardia vs Rhodococcus
    assert ("DUPLICATE_IN_SOURCE", "AS-990", "Strain Number") in kinds  # AS-991 is an alias of AS-990
    assert ("NOT_IN_SOURCE", "AS-990", "") in kinds  # check covers the cohort
    assert any(h["kind"] == "UNRECOGNISED_ID" and h["other_source"] == "table" for h in held)
    # format only: 0.986 = 98.6, 789/790 = 99.9, "S." = Streptomyces, case of accession, N/A not compared
    assert not any(h["kind"] == "FIELD_DIFFERS" and h["strain"] in ("AS-971", "AS-973") for h in held)
    assert not any(h["kind"] == "FIELD_DIFFERS" and h["field"] == "pct_16s" for h in held)


def test_exclusions_never_drop_rows_and_disagreement_is_held(cohort):
    tmp, spec_path = cohort
    reg.build(spec_path, tmp / "out")
    roster = {r["strain"]: r for r in _read(tmp / "out" / "ROSTER.tsv")}
    assert roster["AS-972"]["excluded_by"] == "meta" and "contaminated" in roster["AS-972"]["exclusion_reasons"]
    assert roster["AS-971"]["excluded_by"] == "json"
    held = _read(tmp / "out" / "HELD.tsv")
    assert any(h["kind"] == "EXCLUSION_DISAGREES" and h["strain"] == "AS-971" for h in held)
    assert len(roster) == 4


def test_evidence_map_values_and_where(cohort):
    tmp, spec_path = cohort
    receipt = reg.build(spec_path, tmp / "out")
    roster = {r["strain"]: r for r in _read(tmp / "out" / "ROSTER.tsv")}
    a = roster["AS-971"]
    assert a["assay_crude"] == "C. albicans/weak; MRSA/strong" and a["assay_crude_where"] == "assay.tsv"
    assert a["s16"] == "1" and a["s16_where"] == "s16/a.tsv" and roster["AS-972"]["s16_where"] == "s16/b.tsv"
    assert a["cards"] == "2" and "Strains/AS-971/mode_b_a" in a["cards_where"]  # AS-9710 is not AS-971
    assert a["antismash_loose"] == "yes" and a["antismash_loose_where"] == "Home/_ANTISMASH_CANONICAL/loose/AS-971.zip"
    assert roster["AS-972"]["antismash_loose"] == "no"  # a zip holding only input/ JSON is not a result
    assert a["package"] == "9.7.448" and a["package_where"].startswith("mamey_packages/AS-971/")
    assert roster["AS-973"]["assay_crude"] == "no" and roster["AS-973"]["assay_crude_where"] == ""
    assay = next(i for i in receipt["inputs"] if i.get("name") == "assay_crude")
    assert assay["rows_for_other_strains"] == 1
    columns = {r["column"]: r for r in _read(tmp / "out" / "COLUMNS.tsv")}
    assert "not a negative result" in columns["assay_crude"]["meaning"] and columns["assay_crude"]["stage"] == "bioassay"
    summary = (tmp / "out" / "SUMMARY.md").read_text(encoding="utf-8")
    assert "| `in_table` | 2 | 1 | 1 | 4 |" in summary and "not listed (1)" in summary


def test_receipt_binds_inputs_and_output_is_deterministic(cohort):
    tmp, spec_path = cohort
    r1 = reg.build(spec_path, tmp / "out1")
    reg.build(spec_path, tmp / "out2")
    for name in ("ROSTER.tsv", "HELD.tsv", "COLUMNS.tsv", "SUMMARY.md"):
        assert (tmp / "out1" / name).read_bytes() == (tmp / "out2" / name).read_bytes()
    member = next(i for i in r1["inputs"] if i["name"] == "table")
    assert member["sha256"] == hashlib.sha256((tmp / "table.tsv").read_bytes()).hexdigest()
    assert r1["spec"]["sha256"] == hashlib.sha256(spec_path.read_bytes()).hexdigest()
    assert r1["tool"]["sha256"] == hashlib.sha256(TOOL.read_bytes()).hexdigest()
    assert r1["present"]["in_check"] == 3 and r1["present"]["package"] == 1
    package = next(i for i in r1["inputs"] if i.get("name") == "package")
    assert "mamey_packages" in package["searched_homes"]


@pytest.mark.parametrize("change, message", [
    (lambda s: s["members"][0].update(strain_column="Nope"), "strain column"),
    (lambda s: s["members"][1].update(strain_regex="AS-\\d+"), "named group"),
    (lambda s: s["evidence"][0].update(kind="guess"), "kind must be"),
    (lambda s: s["evidence"][1].update(name="assay_crude"), "used twice"),
    (lambda s: s.update(summary_by="nobody"), "summary_by"),
    (lambda s: s["members"][1]["compare"].update(pct_16s="fuzzy"), "normaliser"),
])
def test_refusals(cohort, change, message):
    tmp, spec_path = cohort
    bad = json.loads(spec_path.read_text())
    change(bad)
    (tmp / "bad.json").write_text(json.dumps(bad))
    with pytest.raises(reg.Refused, match=message):
        reg.build(tmp / "bad.json", tmp / "out_bad")


def test_occupied_output_and_cli_exit(cohort):
    tmp, spec_path = cohort
    (tmp / "busy").mkdir()
    (tmp / "busy" / "x").write_text("x")
    with pytest.raises(reg.Refused, match="not empty"):
        reg.build(spec_path, tmp / "busy")
    with pytest.raises(SystemExit) as refused:
        reg.main(["build", "--spec", str(spec_path), "--out-dir", str(tmp / "busy")])
    assert refused.value.code == 2
    assert reg.main(["build", "--spec", str(spec_path), "--out-dir", str(tmp / "fresh")]) == 0
    assert (tmp / "fresh" / "SUMMARY.md").is_file()


def test_xlsx_member_with_title_row_and_dates(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    import datetime
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Strains"
    ws.append(["Table S1. Isolates"])
    ws.append(["Strain Number", "Collection Date"])
    ws.append(["AS-981", datetime.datetime(2023, 11, 1)])
    wb.save(tmp_path / "record.xlsx")
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps({"schema": "sapote.paper-cohort-spec.v2", "cohort": "x", "strain_regex": ID,
                                     "members": [{"name": "s1", "path": "record.xlsx", "sheet": "Strains", "header_row": 2,
                                                  "strain_column": "Strain Number",
                                                  "fields": {"collection_date": "Collection Date"}}]}))
    reg.build(spec_path, tmp_path / "out")
    assert _read(tmp_path / "out" / "ROSTER.tsv")[0]["collection_date"] == "2023-11-01"


def test_tool_names_no_study_or_strain():
    text = TOOL.read_text(encoding="utf-8").lower()
    for word in ("moss", "attine", "bryophyte", "hymenoptera", "bombus", "as-"):
        assert word not in text, word
