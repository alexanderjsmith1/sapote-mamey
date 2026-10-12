"""Primary CLI output admission, with independent byte snapshots and actual zero-row runs."""
import csv
import hashlib
import json
import os
from pathlib import Path
import zipfile

import pytest

from rggmci import cli


def snapshot(root):
    entries = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            entries[relative] = ("symlink", os.readlink(path))
        elif path.is_file():
            entries[relative] = ("file", hashlib.sha256(path.read_bytes()).hexdigest())
        else:
            entries[relative] = ("directory",)
    return entries


def input_file(root, name="inputs/one.zip"):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"admission-only fixture: must not reach analysis")
    return path


def refuse_without_changes(monkeypatch, capsys, root, args, reason):
    def forbidden(*args, **kwargs):
        pytest.fail("roster refusal must happen before run()")
    monkeypatch.setattr(cli, "run", forbidden)
    before = snapshot(root)
    assert cli.main([*map(str, args), "--reference-completion", "off"]) == 2
    assert reason in capsys.readouterr().err
    assert snapshot(root) == before


@pytest.mark.parametrize("stems", [("sample", "sample"), ("Sample", "sample"), ("caf\u00e9", "cafe\u0301")])
def test_batch_stem_collisions_refuse_before_any_output(monkeypatch, capsys, tmp_path, stems):
    a = input_file(tmp_path, f"a/{stems[0]}.zip")
    b = input_file(tmp_path, f"b/{stems[1]}.zip")
    refuse_without_changes(monkeypatch, capsys, tmp_path,
                           [a, b, "--out-dir", tmp_path / "uncreated/results"], "stems collide")


@pytest.mark.parametrize("alias", ["repeat", "symlink", "hardlink", "directory_overlap"])
def test_duplicate_physical_inputs_refuse(monkeypatch, capsys, tmp_path, alias):
    source = input_file(tmp_path)
    if alias == "repeat":
        other = source
    elif alias == "directory_overlap":
        other = source.parent
    else:
        other = tmp_path / "alias.zip"
        if alias == "symlink":
            other.symlink_to(source)
        else:
            os.link(source, other)
    refuse_without_changes(monkeypatch, capsys, tmp_path,
                           [source, other, "--out-dir", tmp_path / "new/results"], "duplicate input")


@pytest.mark.parametrize("flag", ["--out", "--pairs"])
def test_batch_cannot_share_single_file_destination(monkeypatch, capsys, tmp_path, flag):
    a = input_file(tmp_path, "inputs/a.zip")
    b = input_file(tmp_path, "inputs/b.zip")
    refuse_without_changes(monkeypatch, capsys, tmp_path,
                           [a, b, "--out-dir", tmp_path / "new/results", flag, tmp_path / "one"],
                           "single-genome destinations")


def test_missing_later_input_refuses_before_first_analysis_or_parent_creation(monkeypatch, capsys, tmp_path):
    first = input_file(tmp_path)
    refuse_without_changes(monkeypatch, capsys, tmp_path,
                           [first, tmp_path / "missing/later.zip", "--out-dir", tmp_path / "new/results"],
                           "not found")


def test_later_generated_output_alias_refuses_entire_roster(monkeypatch, capsys, tmp_path):
    first = input_file(tmp_path, "inputs/first.zip")
    later = input_file(tmp_path, "inputs/later.zip")
    folder = tmp_path / "results"
    folder.mkdir()
    (folder / "later_partner_contigs.tsv").write_bytes(b"prior later-input evidence")
    refuse_without_changes(monkeypatch, capsys, tmp_path,
                           [first, later, "--out-dir", folder], "occupied")


@pytest.mark.parametrize("kind", ["same", "canonical_alias", "symlink_parent", "portable_case", "ancestor",
                                  "reserved_summary", "generated", "directory_itself"])
def test_entire_output_roster_overlap_refuses(monkeypatch, capsys, tmp_path, kind):
    source = input_file(tmp_path)
    folder = tmp_path / "new/results"
    first, second = tmp_path / "new/result", tmp_path / "new/result"
    if kind == "canonical_alias":
        second = tmp_path / "new/../new/result"
    elif kind == "symlink_parent":
        parent = tmp_path / "real"
        parent.mkdir()
        alias = tmp_path / "alias"
        alias.symlink_to(parent, target_is_directory=True)
        first, second = parent / "result", alias / "result"
    elif kind == "portable_case":
        first, second = tmp_path / "new/RESULT", tmp_path / "new/result"
    elif kind == "ancestor":
        second = first / "child"
    elif kind == "reserved_summary":
        first, second = folder / "SUMMARY.tsv", tmp_path / "new/pairs"
    elif kind == "generated":
        first, second = folder / "one_reference_completion.tsv", tmp_path / "new/pairs"
    elif kind == "directory_itself":
        first, second = folder, tmp_path / "new/pairs"
    refuse_without_changes(monkeypatch, capsys, tmp_path,
                           [source, "--out", first, "--pairs", second, "--out-dir", folder], "overlap")


@pytest.mark.parametrize("kind", ["exact_input", "symlink_input", "input_parent", "input_in_out_dir"])
def test_outputs_cannot_alias_or_contain_inputs(monkeypatch, capsys, tmp_path, kind):
    source = input_file(tmp_path)
    if kind == "input_in_out_dir":
        args, reason = [source, "--out-dir", source.parent], "occupied"
    else:
        target = source if kind == "exact_input" else source.parent
        if kind == "symlink_input":
            target = tmp_path / "input_alias.json"
            target.symlink_to(source)
        args, reason = [source, "--out", target, "--pairs", tmp_path / "new/pairs.tsv"], "overlaps an input"
    refuse_without_changes(monkeypatch, capsys, tmp_path, args, reason)


@pytest.mark.parametrize("kind", ["out", "pairs", "directory", "unrelated", "symlink_dir", "dangling",
                                  "parent_file"])
def test_occupied_or_invalid_destination_preserves_all_bytes(monkeypatch, capsys, tmp_path, kind):
    source = input_file(tmp_path)
    out, pairs, folder = tmp_path / "new/result.json", tmp_path / "new/pairs.tsv", tmp_path / "results"
    args, reason = [source, "--out", out, "--pairs", pairs], "occupied"
    if kind in ("out", "pairs"):
        target = out if kind == "out" else pairs
        target.parent.mkdir()
        target.write_bytes(b"previous output must remain exact\n")
    elif kind in ("directory", "unrelated"):
        folder.mkdir()
        (folder / ("one.json" if kind == "directory" else ".unrelated_evidence")).write_bytes(b"keep\x00exact")
        args = [source, "--out-dir", folder, "--out", out]
    elif kind == "symlink_dir":
        target = tmp_path / "empty"
        target.mkdir()
        folder.symlink_to(target, target_is_directory=True)
        args, reason = [source, "--out-dir", folder], "ordinary new or empty"
    elif kind == "dangling":
        out.parent.mkdir()
        out.symlink_to(tmp_path / "absent")
    else:
        (tmp_path / "new").write_bytes(b"not a directory")
        reason = "parent is not a directory"
    refuse_without_changes(monkeypatch, capsys, tmp_path, args, reason)


def synthetic_archive(path, label="zero", count=1):
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "x") as archive:
        for i in range(1, count + 1):
            contig = f"SYNTH_{label}_{i}.1"
            text = "\n".join([
                f"LOCUS       {contig:<16}     120 bp    DNA     linear   BCT 01-JAN-2000",
                "DEFINITION  Synthetic nonfunctional CLI fixture.",
                f"ACCESSION   {contig.split('.')[0]}", f"VERSION     {contig}",
                "FEATURES             Location/Qualifiers", "     region          1..120",
                '                     /product="other"', '                     /region_number="1"',
                '                     /contig_edge="True"', "ORIGIN", "        1 " + "n" * 60,
                "       61 " + "n" * 60, "//", ""])
            archive.writestr(f"{contig}.region001.gbk", text)
    return path


def read_table(path):
    with path.open(newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        return reader.fieldnames, list(reader)


@pytest.mark.parametrize("existing_empty", [False, True])
def test_actual_zero_pair_batch_has_bound_json_and_header_only_tables(tmp_path, existing_empty):
    a = synthetic_archive(tmp_path / "inputs/a.zip", "a", 1)
    b = synthetic_archive(tmp_path / "inputs/b.zip", "b", 2)
    folder = tmp_path / "results"
    if existing_empty:
        folder.mkdir()
    input_hashes = {p.stem: hashlib.sha256(p.read_bytes()).hexdigest() for p in (a, b)}
    assert cli.main([str(a), str(b), "--out-dir", str(folder), "--reference-completion", "off"]) == 0
    assert len(list(folder.glob("*.json"))) == 2
    for source in (a, b):
        result = json.loads((folder / f"{source.stem}.json").read_text())
        assert result["input"]["antismash_zip_sha256"] == input_hashes[source.stem]
        assert result["ranked_pairs"] == [] and result["related_locus_pairs"] == []
        assert result["reference_completion"]["completion_tier"] == "OFF"
        for suffix in ("pairs", "related_loci"):
            headers, rows = read_table(folder / f"{source.stem}_{suffix}.tsv")
            assert {"pair", "bgc_a", "contig_a", "bgc_b", "contig_b", "rggmci_confidence"} <= set(headers)
            assert rows == []
        for suffix in ("reference_completion", "split_genes", "partner_contigs"):
            _, rows = read_table(folder / f"{source.stem}_{suffix}.tsv")
            assert len(rows) == 1 and rows[0]["completion_tier"] == "OFF"
    _, summary = read_table(folder / "SUMMARY.tsv")
    assert [(r["genome"], r["regions"], r["scored_pairs"]) for r in summary] == [("a", "1", "0"), ("b", "2", "0")]
    assert read_table(folder / "CANDIDATE_GROUPS.tsv")[1] == []
    assert {p.stem: hashlib.sha256(p.read_bytes()).hexdigest() for p in (a, b)} == input_hashes
    before = snapshot(tmp_path)
    assert cli.main([str(a), "--out-dir", str(folder), "--reference-completion", "off"]) == 2
    assert snapshot(tmp_path) == before


def test_actual_explicit_zero_pair_table_and_rerun_refusal(tmp_path):
    source = synthetic_archive(tmp_path / "inputs/zero.zip")
    out, pairs = tmp_path / "new/result.json", tmp_path / "new/pairs.tsv"
    args = [str(source), "--out", str(out), "--pairs", str(pairs), "--reference-completion", "off"]
    assert cli.main(args) == 0
    assert json.loads(out.read_text())["ranked_pairs"] == []
    assert read_table(pairs)[1] == []
    before = snapshot(tmp_path)
    assert cli.main(args) == 2
    assert snapshot(tmp_path) == before


def test_populated_table_keeps_engine_columns_values_and_options(monkeypatch, tmp_path):
    source = input_file(tmp_path)
    row = {"pair": "A+B", "bgc_a": "A", "contig_a": "nodeA", "bgc_b": "B", "contig_b": "nodeB",
           "rggmci_score": 17.25, "rggmci_confidence": "MODERATE_RG_GMCI_CANDIDATE", "future_engine_field": "retained"}
    related = {**row, "rggmci_confidence": "RELATED_LOCUS_NOT_A_RESCUE", "related_because": "same contig"}
    result = {"regions": [{}, {}], "ranked_pairs": [row], "related_locus_pairs": [related],
              "candidate_groups": [], "reference_completion": {"completion_tier": "OFF"}}
    calls = []
    def observed_run(path, **kwargs):
        calls.append((path, kwargs))
        return result
    monkeypatch.setattr(cli, "run", observed_run)
    folder = tmp_path / "results"
    assert cli.main([str(source), "--out-dir", str(folder), "--reference-completion", "off", "--threads", "1"]) == 0
    assert calls == [(source, {"reference_completion": "off", "mibig_db": None, "diamond": None,
                              "sensitivity": "sensitive", "threads": 1, "pfam_hmm": None})]
    assert json.loads((folder / "one.json").read_text()) == result
    headers, rows = read_table(folder / "one_pairs.tsv")
    assert headers == list(row)
    assert rows == [{k: str(v) for k, v in row.items()}]
    assert read_table(folder / "one_related_loci.tsv")[0] == list(related)
    _, summary = read_table(folder / "SUMMARY.tsv")
    assert summary[0]["scored_pairs"] == "1" and summary[0]["moderate"] == "1" and summary[0]["related_loci"] == "1"


@pytest.mark.parametrize("suffix", [".json", "_pairs.tsv", "_reference_completion.tsv"])
def test_late_file_arrival_is_not_overwritten(monkeypatch, capsys, tmp_path, suffix):
    source = input_file(tmp_path)
    folder = tmp_path / "results"
    target = folder / (source.stem + suffix)
    def concurrent_writer(*args, **kwargs):
        target.write_bytes(b"concurrent evidence\x00unchanged")
        return {"regions": [], "ranked_pairs": [], "related_locus_pairs": [], "reference_completion": {"completion_tier": "OFF"}}
    monkeypatch.setattr(cli, "run", concurrent_writer)
    assert cli.main([str(source), "--out-dir", str(folder), "--reference-completion", "off"]) == 2
    assert "output error:" in capsys.readouterr().err
    assert target.read_bytes() == b"concurrent evidence\x00unchanged"
    assert not (folder / "SUMMARY.tsv").exists()


def test_analysis_error_still_keeps_successful_batch_and_reports_failure(monkeypatch, tmp_path):
    good = input_file(tmp_path, "inputs/good.zip")
    bad = input_file(tmp_path, "inputs/bad.zip")
    def run(path, **kwargs):
        if path == bad:
            raise ValueError("deliberate invalid archive")
        return {"regions": [], "ranked_pairs": [], "reference_completion": {"completion_tier": "OFF"}}
    monkeypatch.setattr(cli, "run", run)
    folder = tmp_path / "results"
    assert cli.main([str(good), str(bad), "--out-dir", str(folder), "--reference-completion", "off"]) == 1
    _, rows = read_table(folder / "SUMMARY.tsv")
    assert rows[0]["error"] == "" and rows[1]["error"] == "ValueError: deliberate invalid archive"
    assert (folder / "good.json").is_file() and not (folder / "bad.json").exists()
