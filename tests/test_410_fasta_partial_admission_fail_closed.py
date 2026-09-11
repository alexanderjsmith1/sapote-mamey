"""Regression tests for fail-closed FASTA admission after a guarded member refusal."""
from __future__ import annotations

from types import SimpleNamespace
import zipfile

import pytest


def _write_zip(path, members):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as zf:
        for name, data in members:
            zf.writestr(name, data)
    return path


def _small_fasta(name="admitted"):
    return f">{name}\n".encode() + b"ACGT" * 10 + b"\n"


def _large_fasta(name="refused"):
    return f">{name}\n".encode() + b"G" * 800 + b"\n"


@pytest.mark.parametrize("refused_first", [True, False])
def test_mixed_fasta_refuses_whole_result_in_either_member_order(
    tmp_path, monkeypatch, refused_first
):
    from mamey.parsers import GbkSizeGuardRefusal, read_fasta_sequences_from_zip

    monkeypatch.setenv("MAMEY_GBK_MAX_BYTES", "512")
    monkeypatch.setenv("MAMEY_GBK_MAX_RATIO", "100000")
    members = [
        ("refused.fna", _large_fasta()),
        ("admitted.fna", _small_fasta()),
    ]
    if not refused_first:
        members.reverse()
    archive = _write_zip(tmp_path / "mixed.zip", members)

    with pytest.raises(GbkSizeGuardRefusal) as caught:
        read_fasta_sequences_from_zip(archive)
    assert caught.value.member == "refused.fna"
    assert "GBK_SIZE_GUARD_REFUSED" in str(caught.value)


def test_all_refused_fasta_propagates_typed_refusal(tmp_path, monkeypatch):
    from mamey.parsers import GbkSizeGuardRefusal, read_fasta_sequences_from_zip

    monkeypatch.setenv("MAMEY_GBK_MAX_BYTES", "512")
    monkeypatch.setenv("MAMEY_GBK_MAX_RATIO", "100000")
    archive = _write_zip(tmp_path / "all-refused.zip", [
        ("first.fna", _large_fasta("first")),
        ("second.fasta", _large_fasta("second")),
    ])

    with pytest.raises(GbkSizeGuardRefusal) as caught:
        read_fasta_sequences_from_zip(archive)
    assert caught.value.member == "first.fna"


def test_assembly_metrics_propagates_mixed_fasta_refusal(tmp_path, monkeypatch):
    from mamey.parsers import GbkSizeGuardRefusal, assembly_metrics_from_zip

    monkeypatch.setenv("MAMEY_GBK_MAX_BYTES", "512")
    monkeypatch.setenv("MAMEY_GBK_MAX_RATIO", "100000")
    archive = _write_zip(tmp_path / "mixed.zip", [
        ("admitted.fna", _small_fasta()),
        ("refused.fna", _large_fasta()),
    ])

    with pytest.raises(GbkSizeGuardRefusal, match="refused.fna"):
        assembly_metrics_from_zip(archive)


def test_all_admitted_fasta_metrics_are_unchanged(tmp_path, monkeypatch):
    from mamey.parsers import assembly_metrics_from_zip, read_fasta_sequences_from_zip

    monkeypatch.setenv("MAMEY_GBK_MAX_BYTES", "512")
    monkeypatch.setenv("MAMEY_GBK_MAX_RATIO", "100000")
    archive = _write_zip(tmp_path / "admitted.zip", [
        ("one.fna", b">one\n" + b"ACGT" * 10 + b"\n"),
        ("two.fasta", b">two\n" + b"GCGC" * 5 + b"\n"),
    ])

    assert read_fasta_sequences_from_zip(archive) == {
        "one": "ACGT" * 10,
        "two": "GCGC" * 5,
    }
    metrics = assembly_metrics_from_zip(archive)
    assert (metrics.genome_bp, metrics.contigs, metrics.n50, metrics.largest_contig) == (60, 2, 40, 40)


def test_no_fasta_still_uses_genbank_fallback(tmp_path, monkeypatch):
    import mamey.parsers as parsers

    archive = _write_zip(tmp_path / "no-fasta.zip", [("note.txt", b"not FASTA")])
    record = SimpleNamespace(id="contig_gbk", name="contig_gbk", seq="ACGT" * 7)
    monkeypatch.setattr(parsers, "read_genbank_records", lambda *_a, **_k: [("record.gbk", record)])

    metrics = parsers.assembly_metrics_from_zip(archive)
    assert (metrics.genome_bp, metrics.contigs, metrics.n50) == (28, 1, 28)


def test_cli_returns_structured_failure_before_downstream_work(tmp_path, monkeypatch):
    import mamey.cli as cli

    monkeypatch.setenv("MAMEY_GBK_MAX_BYTES", "512")
    monkeypatch.setenv("MAMEY_GBK_MAX_RATIO", "100000")
    archive = _write_zip(tmp_path / "mixed.zip", [
        ("admitted.fna", _small_fasta()),
        ("refused.fna", _large_fasta()),
    ])
    monkeypatch.setattr(cli, "identify_antismash_input", lambda *_a, **_k: SimpleNamespace(
        is_antismash=True, warnings=[], strictness="strict"
    ))
    monkeypatch.setattr(cli, "_acquire_package_lock", lambda *_a, **_k: object())
    monkeypatch.setattr(cli, "_phase_environment", lambda *_a, **_k: (
        object(), False, "Streptomyces sp.", "Test strain", object()
    ))
    monkeypatch.setattr(cli, "emit", lambda *_a, **_k: None)

    called = []

    def must_not_run(*_args, **_kwargs):
        called.append(True)
        raise AssertionError("downstream parsing/scanning/sealing must not run")

    for name in (
        "extract_antismash_version",
        "parse_antismash_evidence_status",
        "parse_bgcs_from_zip",
        "extract_cds_features",
        "extract_contig_sequences",
        "run_source_scans",
        "zip_package",
    ):
        monkeypatch.setattr(cli, name, must_not_run)

    outdir = tmp_path / "out"
    result = cli.run_one_strain(
        strain_id="TEST-STRAIN",
        display_name="Test strain",
        input_zip=str(archive),
        outdir=str(outdir),
        mode="gold",
        taxonomy="Streptomyces sp.",
        source="not supplied",
        master_path=str(tmp_path / "must-not-exist.xlsx"),
    )

    assert result["status"] == "MAMEY_FAILED"
    assert result["package_zip"] is None
    assert result["master_updated"] is False
    assert len(result["issues"]) == 1
    assert result["issues"][0].startswith("FASTA_INPUT_REFUSED: GBK_SIZE_GUARD_REFUSED: refused.fna:")
    assert "rejected as incomplete" in result["issues"][0]
    assert called == []
    assert not list(outdir.rglob("manifest.json"))
    assert not list(outdir.rglob("*.zip"))
    assert not (tmp_path / "must-not-exist.xlsx").exists()
