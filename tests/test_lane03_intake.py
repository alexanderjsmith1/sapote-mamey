"""Small artificial intake regressions; no biological submissions or private inputs."""
import csv
from pathlib import Path
import warnings
import zipfile
from types import SimpleNamespace

import pytest
import mamey
from mamey import parsers
from mamey.ziputil import safe_extract_all
from mamey.blastp_ingest import parse_hit_table

def archive(tmp_path, members):
    path = tmp_path / "synthetic.zip"
    with zipfile.ZipFile(path, "w") as zf:
        for name, payload in members:
            zf.writestr(name, payload)
    return path

@pytest.mark.parametrize("same_member", [True, False])
@pytest.mark.parametrize("reverse", [True, False])
def test_conflicting_fasta_identity_is_held(tmp_path, same_member, reverse):
    entries = [">contig_a\nACGT\n", ">contig_a\nAGGT\n"]
    if reverse:
        entries.reverse()
    members = [("assembly.fna", "".join(entries))] if same_member else list(zip(["a.fna", "b.fasta"], entries))
    path = archive(tmp_path, members)
    with pytest.raises(ValueError, match="FASTA_IDENTITY_CONFLICT") as caught:
        parsers.read_fasta_sequences_from_zip(path)
    assert "contig_a" in str(caught.value)
    assert "ACGT" not in str(caught.value) and "AGGT" not in str(caught.value)

def test_identical_fasta_duplicates_remain_admitted(tmp_path):
    path = archive(tmp_path, [("a.fna", ">contig_a\nACGT\n"), ("b.fa", ">contig_a\nACGT\n>contig_b\nAGGT\n")])
    assert parsers.read_fasta_sequences_from_zip(path) == {"contig_a": "ACGT", "contig_b": "AGGT"}

def test_conflicting_fasta_cannot_produce_assembly_metrics(tmp_path):
    path = archive(tmp_path, [("a.fna", ">contig_a\nACGT\n>contig_a\nACGTACGT\n")])
    with pytest.raises(ValueError, match="FASTA_IDENTITY_CONFLICT"):
        parsers.assembly_metrics_from_zip(path)

def test_cli_identity_hold_precedes_all_package_work(tmp_path, monkeypatch):
    import mamey.cli as cli
    path = archive(tmp_path, [("a.fna", ">contig_a\nACGT\n>contig_a\nACGTACGT\n")])
    monkeypatch.setattr(cli, "identify_antismash_input", lambda *_a, **_k: SimpleNamespace(
        is_antismash=True, warnings=[], strictness="strict"))
    monkeypatch.setattr(cli, "_acquire_package_lock", lambda *_a, **_k: object())
    monkeypatch.setattr(cli, "_phase_environment", lambda *_a, **_k: (
        object(), False, "Streptomyces sp.", "Synthetic strain", SimpleNamespace(strain_id="SYNTH")))
    monkeypatch.setattr(cli, "emit", lambda *_a, **_k: None)
    def forbidden(*_a, **_k):
        pytest.fail("downstream evidence, scans or publication ran after an identity hold")
    for name in ("extract_antismash_version", "parse_bgcs_from_zip", "extract_cds_features",
                 "extract_contig_sequences", "run_source_scans", "zip_package"):
        monkeypatch.setattr(cli, name, forbidden)
    output = tmp_path / "out"
    master = tmp_path / "must-not-exist.xlsx"
    result = cli.run_one_strain(strain_id="SYNTH", display_name="Synthetic strain", input_zip=str(path),
        outdir=str(output), mode="gold", taxonomy="Streptomyces sp.", source="not supplied", master_path=str(master))
    assert result["status"] == "MAMEY_FAILED"
    assert result["package_zip"] is None and result["master_updated"] is False
    assert len(result["issues"]) == 1 and "FASTA_IDENTITY_CONFLICT" in result["issues"][0]
    assert not list(output.rglob("manifest.json")) and not list(output.rglob("*.zip"))
    assert not master.exists()

GOOD = ("LOCUS       SYNTH_A                   12 bp    DNA     linear   BCT 01-JAN-2000\n"
        "FEATURES             Location/Qualifiers\n"
        "     source          1..12\n"
        "ORIGIN\n        1 acgtacgtacgt\n//\n")
BAD = "LOCUS       SYNTH_BAD not_a_number bp DNA linear BCT\nFEATURES             Location/Qualifiers\nORIGIN\n//\n"

@pytest.mark.parametrize("backend", ["bio", "shim"])
def test_partial_genbank_member_never_supersedes_complete_input(tmp_path, monkeypatch, backend):
    if backend == "shim":
        monkeypatch.setattr(parsers, "_require_seqio", lambda: None)
    else:
        seqio = pytest.importorskip("Bio.SeqIO")
        monkeypatch.setattr(parsers, "_require_seqio", lambda: seqio)
    path = archive(tmp_path, [("output.gbk", GOOD + BAD), ("input/original.gbk", GOOD)])
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        rows = parsers.read_genbank_records(path, exclude_regions=True)
    assert [name for name, _ in rows] == ["input/original.gbk"]
    assert any("errored" in str(w.message) and "output.gbk" in str(w.message) for w in caught)
    assert not any("superseded" in str(w.message) for w in caught)

@pytest.mark.parametrize("kind", ["file-parent", "target-directory", "directory-target-file"])
def test_existing_destination_conflict_refuses_before_any_write(tmp_path, kind):
    dest = tmp_path / "destination"
    dest.mkdir()
    if kind == "file-parent":
        (dest / "blocker").write_text("unchanged")
        late = "blocker/child.txt"
    elif kind == "target-directory":
        (dest / "blocker").mkdir()
        late = "blocker"
    else:
        (dest / "blocker").write_text("unchanged")
        late = "blocker/"
    path = archive(tmp_path, [("first.txt", "must never be written"), (late, "")])
    with zipfile.ZipFile(path) as zf:
        with pytest.raises(ValueError, match="existing.*(collision|non-regular)"):
            safe_extract_all(zf, dest)
    assert not (dest / "first.txt").exists()
    if kind != "target-directory":
        assert (dest / "blocker").read_text() == "unchanged"

def test_existing_regular_file_can_be_replaced_after_preflight(tmp_path):
    dest = tmp_path / "destination"
    dest.mkdir()
    (dest / "existing.txt").write_text("old")
    path = archive(tmp_path, [("existing.txt", "replacement"), ("sub/new.txt", "new")])
    with zipfile.ZipFile(path) as zf:
        safe_extract_all(zf, dest)
    assert (dest / "existing.txt").read_text() == "replacement"
    assert (dest / "sub/new.txt").read_text() == "new"

def test_headerless_blast_quoted_comma_keeps_exact_ids_and_source_line(tmp_path):
    path = tmp_path / "hits.csv"
    query = "SYNTH|NODE_1_length_12_cov_1.2|region001|BGC001|gene,one"
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        handle.write("# BLASTP synthetic\r\n\r\n")
        csv.writer(handle).writerow([query, "subject,one", 90, 12, 0, 0, 1, 12, 1, 12, "1e-9", 40])
    lines = []
    rows = parse_hit_table(path, source_rows=lines)
    assert len(rows) == 1 and rows[0]["query_id"] == query
    assert rows[0]["subject_acc"] == "subject,one"
    assert rows[0]["positives_pct"] == ""
    assert lines == [3]

def test_shipped_generic_single_contig_fixture_keeps_guard_and_regions(monkeypatch):
    fixture = Path(mamey.__file__).resolve().parents[1] / "tests/fixtures/synthetic_single_contig_antismash.zip"
    assert parsers.region_gbk_count(fixture) == 3
    assert len(parsers.read_genbank_records(fixture, region_only=True)) == 3
    # This known 100 kb artificial fixture compresses at 268x. Default refusal
    # is intentional; a test-local override exercises the admitted route only.
    monkeypatch.setenv("MAMEY_GBK_MAX_RATIO", "200")
    with pytest.raises(parsers.GbkSizeGuardRefusal, match="compression ratio"):
        parsers.assembly_metrics_from_zip(fixture)
    monkeypatch.setenv("MAMEY_GBK_MAX_RATIO", "1000")
    metrics = parsers.assembly_metrics_from_zip(fixture)
    assert metrics.genome_bp == 100000 and metrics.contigs == 1

def test_shipped_generic_json_fixture_keeps_record_namespace():
    from mamey import antismash_evidence as ae
    fixture = Path(mamey.__file__).resolve().parents[1] / "tests/fixtures/synthetic_tigrfam_antismash.zip"
    with zipfile.ZipFile(fixture) as zf:
        records = list(ae._iter_records(zf, "synthetic_tigrfam.json"))
    assert len(records) == 2
    assert all(isinstance(rec.get("id"), str) and rec["id"] for rec in records)
    assert len({rec["id"] for rec in records}) == 2
