"""Genome export must preserve explicit contigs and refuse sequence-less records."""
import builtins
import csv
import hashlib
import importlib.util
from pathlib import Path
import sys
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
HELPER_PATH = ROOT / "tools/antismash_input_genome.py"


@pytest.fixture(params=["biopython", "shim"])
def reader(request, monkeypatch):
    spec = importlib.util.spec_from_file_location("genome_sequence_preservation", HELPER_PATH)
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    if request.param == "biopython":
        pytest.importorskip("Bio", reason="native Biopython backend unavailable")
    else:
        original = builtins.__import__

        def no_bio(name, *args, **kwargs):
            if name == "Bio" or name.startswith("Bio."):
                raise ImportError("Biopython intentionally hidden")
            return original(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", no_bio)
    return tool


def _gbk(name, sequence=None):
    result = (f"LOCUS       {name:<16}{4:>12} bp    DNA     linear   UNK 01-JAN-2026\n"
              "FEATURES             Location/Qualifiers\n")
    if sequence is not None:
        result += "ORIGIN\n        1 " + sequence.lower() + "\n"
    return result + "//\n"


def _run(tmp_path, reader, member, text):
    archive = tmp_path / "synthetic.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED) as zf:
        zf.writestr("input/" + member, text)
    output = tmp_path / "output"
    result = reader.main(["--zip", str(archive), "--out", str(output)])
    with (output / "MANIFEST.tsv").open(newline="") as handle:
        row, = list(csv.DictReader(handle, delimiter="\t"))
    return result, output, row


@pytest.mark.parametrize("fmt", ["fasta", "genbank"])
def test_explicit_all_n_contig_is_not_dropped(reader, tmp_path, fmt):
    text = ">uncertain\nNNNN\n" if fmt == "fasta" else _gbk("uncertain", "NNNN")
    member = "genome.fna" if fmt == "fasta" else "genome.gbk"
    result, output, row = _run(tmp_path, reader, member, text)
    assert result == 0, row
    fasta = output / "synthetic.fasta"
    assert fasta.read_text() == ">uncertain\nNNNN\n"
    assert row["contigs"] == "1" and row["total_bp"] == "4"
    assert row["fasta_sha256"] == hashlib.sha256(fasta.read_bytes()).hexdigest()


@pytest.mark.parametrize("fmt", ["fasta", "genbank"])
def test_mixed_assembly_keeps_all_contigs_and_length(reader, tmp_path, fmt):
    text = ">resolved\nACGT\n>uncertain\nNNNN\n" if fmt == "fasta" else (
        _gbk("resolved", "ACGT") + _gbk("uncertain", "NNNN"))
    member = "genome.fna" if fmt == "fasta" else "genome.gbk"
    result, output, row = _run(tmp_path, reader, member, text)
    assert result == 0, row
    assert (output / "synthetic.fasta").read_text() == ">resolved\nACGT\n>uncertain\nNNNN\n"
    assert row["contigs"] == "2" and row["total_bp"] == "8"


@pytest.mark.parametrize("fmt", ["fasta", "genbank"])
def test_missing_sequence_in_any_record_refuses_complete_export(reader, tmp_path, fmt):
    text = ">resolved\nACGT\n>missing\n" if fmt == "fasta" else (
        _gbk("resolved", "ACGT") + _gbk("missing"))
    member = "genome.fna" if fmt == "fasta" else "genome.gbk"
    result, output, row = _run(tmp_path, reader, member, text)
    assert result == 1
    assert not (output / "synthetic.fasta").exists()
    assert row["fasta_sha256"] == ""
    assert "unreadable input file" in row["note"]


def test_legacy_shim_default_and_strict_sequence_mode_are_distinct():
    from mamey._gbk_shim import parse_genbank_text
    text = _gbk("missing")
    assert parse_genbank_text(text)[0].seq == "NNNN"
    with pytest.raises(ValueError, match="GBK_SHIM_NO_SEQUENCE"):
        parse_genbank_text(text, require_sequence=True)
    assert parse_genbank_text(_gbk("explicit", "NNNN"), require_sequence=True)[0].seq == "nnnn"
