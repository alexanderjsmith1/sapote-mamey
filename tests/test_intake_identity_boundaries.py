"""Portable fabricated-input guards for GenBank, BLAST CSV and exact-locus identity."""
import csv
from pathlib import Path
import zipfile

import pytest
from mamey import parsers
from mamey import blastp_ingest as blast
from mamey import exact_identity as identity

CONTIG = "SYNTHETIC_CONTIG_A.1"
ROW = ["SYNTHETIC_QUERY", "synthetic_subject", 90, 20, 0, 0, 1, 20, 1, 20, "1e-9", 40]


def gbk(sequence):
    return (f"LOCUS       {CONTIG}         12 bp    DNA     linear   BCT 01-JAN-2000\n"
            f"ACCESSION   {CONTIG}\nVERSION     {CONTIG}\n"
            "FEATURES             Location/Qualifiers\n"
            '     region          1..12\n                     /product="NRPS"\n'
            "ORIGIN\n        1 " + sequence + "\n//\n")


def source_zip(tmp_path, second="tcgtacgtacgt", *, full=True):
    path = tmp_path / "synthetic_intake.zip"
    with zipfile.ZipFile(path, "w") as z:
        if full:
            z.writestr("a.gbk", gbk("acgtacgtacgt"))
            z.writestr("b.gbk", gbk(second))
        z.writestr("source.region001.gbk", gbk("acgtacgtacgt"))
    return path


@pytest.fixture(params=["bio", "fallback"])
def backend(request, monkeypatch):
    if request.param == "bio":
        pytest.importorskip("Bio.SeqIO")
    else:
        monkeypatch.setattr(parsers, "_require_seqio", lambda: None)
    return request.param


@pytest.mark.parametrize("reader", ["assembly", "length_map", "bgc_parse"])
def test_conflicting_full_genbank_identity_propagates(tmp_path, backend, reader):
    path = source_zip(tmp_path)
    with pytest.raises(ValueError, match="GENBANK_IDENTITY_CONFLICT") as failure:
        if reader == "assembly":
            parsers.assembly_metrics_from_zip(path)
        elif reader == "length_map":
            parsers._contig_length_map_from_zip(path)
        else:
            parsers.parse_bgcs_from_zip(path, evidence={})
    assert type(failure.value).__name__ == "GenbankIdentityConflict"
    message = str(failure.value)
    assert "a.gbk" in message and "b.gbk" in message and CONTIG in message
    assert "acgtacgtacgt" not in message and "tcgtacgtacgt" not in message


@pytest.mark.parametrize("second", ["acgtacgtacgt", "ACGTACGTACGT"])
def test_identical_case_varied_full_records_remain_admitted(tmp_path, backend, second):
    path = source_zip(tmp_path, second)
    metrics = parsers.assembly_metrics_from_zip(path)
    assert metrics.genome_bp == 12 and metrics.contigs == 1 and metrics.n50 == 12
    assert parsers._contig_length_map_from_zip(path) == {CONTIG: 12}
    records = parsers.parse_bgcs_from_zip(path, evidence={})
    assert len(records) == 1 and records[0].contig == CONTIG
    assert records[0].contig_length == 12


def test_region_only_records_do_not_fabricate_assembly_metrics(tmp_path, backend):
    path = source_zip(tmp_path, full=False)
    assert parsers.assembly_metrics_from_zip(path).genome_bp == 0
    assert parsers._contig_length_map_from_zip(path) == {}
    records = parsers.parse_bgcs_from_zip(path, evidence={})
    assert len(records) == 1 and records[0].contig_length == 0


def csv_file(tmp_path, rows, *, prefix=""):
    path = tmp_path / "synthetic_hits.csv"
    with path.open("w", newline="", encoding="utf-8") as stream:
        stream.write(prefix)
        csv.writer(stream).writerows(rows)
    return path


@pytest.mark.parametrize("column", [0, 1])
@pytest.mark.parametrize("control", ["\t", "\n", "\r", "\x7f", "\x00"])
def test_csv_identity_control_characters_are_refused(tmp_path, column, control):
    row = ROW.copy(); row[column] = "synthetic" + control + "identity"
    physical_rows = [99]
    with pytest.raises(blast.BlastpHitTableError, match="BLASTP_HIT_TABLE_INVALID"):
        blast.parse_hit_table(csv_file(tmp_path, [row]), source_rows=physical_rows)
    assert physical_rows == [99]


@pytest.mark.parametrize("extra_column", [False, True])
def test_quoted_commas_and_physical_source_rows_are_preserved(tmp_path, extra_column):
    row = ROW.copy(); row[:2] = ["query,with,commas", "subject,with,commas"]
    if extra_column:
        row.append(95)
    physical_rows = [99]
    path = csv_file(tmp_path, [row, row], prefix="# fabricated comment\n\n")
    records = blast.parse_hit_table(path, source_rows=physical_rows)
    assert len(records) == 2 and physical_rows == [99, 3, 4]
    assert records[0]["query_id"] == "query,with,commas"
    assert records[0]["subject_acc"] == "subject,with,commas"


@pytest.mark.parametrize("bad_row", [["ragged"], ROW + [1, 2],
    ["query", "subject", *["header"] * 10],
    ["query", "subject", "nan", *ROW[3:]],
    ["query", "subject", "inf", *ROW[3:]]])
def test_later_csv_refusal_does_not_publish_partial_physical_rows(tmp_path, bad_row):
    physical_rows = [99]
    with pytest.raises(blast.BlastpHitTableError):
        blast.parse_hit_table(csv_file(tmp_path, [ROW, bad_row]), source_rows=physical_rows)
    assert physical_rows == [99]


def test_flag_numeric_semantics_and_later_refusal_are_transactional(tmp_path):
    row = ROW.copy(); row[2] = "not_numeric"
    physical_rows = [99]
    records = blast.parse_hit_table(csv_file(tmp_path, [row]), numeric_policy="flag", source_rows=physical_rows)
    assert len(records) == 1 and records[0]["_bad_numeric"] == "pct_identity"
    assert physical_rows == [99, 1]
    physical_rows = [99]
    with pytest.raises(blast.BlastpHitTableError):
        blast.parse_hit_table(csv_file(tmp_path, [row, ["ragged"]]), numeric_policy="flag", source_rows=physical_rows)
    assert physical_rows == [99]


def test_unknown_numeric_blanks_remain_unknown(tmp_path):
    row = ROW.copy(); row[4] = ""
    records = blast.parse_hit_table(csv_file(tmp_path, [row]))
    assert len(records) == 1 and records[0]["mismatches"] == ""


EXACT = ["SYNTHETIC_CASE", "SYNTHETIC_CONTIG_A.1", "region001", "BGC001"]


@pytest.mark.parametrize("column", [0, 1, 3])
@pytest.mark.parametrize("unsafe", [" / ", "\t", "\n", "\r", "\x00", "\x7f"])
def test_exact_locus_components_reject_delimiter_and_controls(column, unsafe):
    values = EXACT.copy(); values[column] += unsafe + "fabricated"
    with pytest.raises(identity.ExactLocusIdentityError):
        identity.exact_locus_display(*values)


@pytest.mark.parametrize("extra", [{"Region": "region0001"}, {"Region": "Region001"},
    {"Contig": "SYNTHETIC_CONTIG_B.1"}, {"strain": "SYNTHETIC_OTHER"}, {"BGC_ID": "BGC0001"}])
def test_exact_aliases_case_zero_padding_and_cross_record_conflicts_are_held(extra):
    row = {"contig": EXACT[1], "region": EXACT[2], "bgc_id": EXACT[3], **extra}
    with pytest.raises(identity.ExactLocusIdentityError):
        identity.exact_locus_from_mapping(EXACT[0], row)


def test_exact_synonyms_preserve_source_spelling_and_slash_without_display_delimiter():
    row = {"contig": EXACT[1], "Contig": EXACT[1], "region": EXACT[2],
           "Region": EXACT[2], "bgc_id": EXACT[3], "BGC_ID": EXACT[3]}
    assert identity.exact_locus_from_mapping(EXACT[0], row) == " / ".join(EXACT)
    assert identity.exact_locus_display(EXACT[0], "synthetic/contig.1", *EXACT[2:]).split(" / ")[1] == "synthetic/contig.1"


def test_cli_conflict_refuses_before_package_or_workbook_publication(tmp_path, monkeypatch, capsys):
    from mamey import cli
    path = source_zip(tmp_path)
    outdir = tmp_path / "runs"
    master = tmp_path / "master.xlsx"
    sentinel = b"synthetic existing workbook publication sentinel"
    master.write_bytes(sentinel)
    monkeypatch.setattr(cli, "_dependency_banner", lambda: "synthetic fixture dependency banner")

    def downstream_must_not_run(*args, **kwargs):
        pytest.fail("conflicted intake reached downstream evidence/scientific processing")

    monkeypatch.setattr(cli, "_parse_evidence_with_budget", downstream_must_not_run)
    code = cli.main(["run", "--strain", "SYNTHETIC-CASE-CLI-CONFLICT", "--input-zip", str(path),
                     "--outdir", str(outdir), "--master", str(master), "--brief", "none", "--json-evidence", "off"])
    assert code == 1
    assert "GENBANK_INPUT_REFUSED" in capsys.readouterr().out
    assert master.read_bytes() == sentinel
    assert not list(outdir.rglob("*.zip")) and not list(outdir.rglob("*.xlsx"))
    assert not list(outdir.rglob("manifest.json")) and not list(outdir.rglob("commit_receipt.json"))
    assert not (outdir / "HANDBACK.json").exists()
