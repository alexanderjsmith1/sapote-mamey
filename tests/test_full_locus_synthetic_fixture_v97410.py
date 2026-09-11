from __future__ import annotations

import hashlib
import importlib
import os
from pathlib import Path
import sys
import zipfile


SOURCE_ARCHIVE_SHA256 = "bd6422d403d0b019c14f0d8c13dbfe2898b7e5afb0a4d43bf58fb083fdc9fde8"


def _root() -> Path:
    override = os.environ.get("SYNTHETIC_FIXTURE_SOURCE_ROOT")
    return Path(override).resolve() if override else Path(__file__).resolve().parents[1]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sequence(payload: bytes) -> str:
    lines = payload.decode("ascii").splitlines()
    return "".join(line.strip() for line in lines if line and not line.startswith(">"))


def test_separate_full_locus_generator_preserves_source_and_semantics(tmp_path: Path) -> None:
    root = _root()
    sys.path.insert(0, str(root))
    fixture_inputs = importlib.import_module("tools.fixture_inputs")
    assert hasattr(fixture_inputs, "prepare_full_locus_single_contig_fixture")
    assert fixture_inputs.SYNTHETIC_FULL_CONTIG_ID == "SYNTHETIC_CONTIG_000001"

    source = root / "tests" / "fixtures" / "synthetic_single_contig_antismash.zip"
    original_bytes = source.read_bytes()
    assert hashlib.sha256(original_bytes).hexdigest() == SOURCE_ARCHIVE_SHA256

    old_prepared = tmp_path / "old-control-admitted.zip"
    full_prepared = tmp_path / "synthetic_single_contig_full_locus_antismash.zip"
    fixture_inputs.prepare_single_contig_fixture(source, old_prepared)
    receipt = fixture_inputs.prepare_full_locus_single_contig_fixture(source, full_prepared)

    assert source.read_bytes() == original_bytes
    assert receipt["policy"] == "single_contig_full_locus_runtime_v1"
    assert receipt["source_sha256"] == SOURCE_ARCHIVE_SHA256
    assert receipt["prepared_sha256"] == _sha(full_prepared)
    assert receipt["declared_full_contig"] == fixture_inputs.SYNTHETIC_FULL_CONTIG_ID
    assert len(receipt["member_mapping"]) == 7

    with zipfile.ZipFile(source) as old_zip, zipfile.ZipFile(full_prepared) as new_zip:
        old_names = old_zip.namelist()
        new_names = new_zip.namelist()
        assert new_names == [receipt["member_mapping"][name] for name in old_names]
        assert len(set(new_names)) == 7
        assert all("NODE_1" not in name for name in new_names)
        fasta_name = "syn/SYNTHETIC_CONTIG_000001.fasta"
        fasta_info = new_zip.getinfo(fasta_name)
        assert fasta_info.compress_type == zipfile.ZIP_STORED
        old_sequence = _sequence(old_zip.read("syn/NODE_1.fasta"))
        new_sequence = _sequence(new_zip.read(fasta_name))
        assert old_sequence == new_sequence
        assert len(new_sequence) == 100000
        assert set(new_sequence) == {"A"}
        assert new_zip.read(fasta_name).splitlines()[0] == b">SYNTHETIC_CONTIG_000001"
        for region in (1, 2, 3):
            gbk = new_zip.read(
                f"syn/SYNTHETIC_CONTIG_000001.region{region:03d}.gbk"
            ).decode("ascii")
            assert f"LOCUS       SYNTHETIC_CONTIG_000001" in gbk
            assert "ACCESSION   SYNTHETIC_CONTIG_000001" in gbk
            assert "VERSION     SYNTHETIC_CONTIG_000001" in gbk
            kcb = new_zip.read(
                f"syn/knownclusterblast/SYNTHETIC_CONTIG_000001_c{region}.txt"
            ).decode("ascii")
            assert kcb.startswith("ClusterBlast scores for SYNTHETIC_CONTIG_000001\n")
            assert "CP073042.1" not in kcb

    from mamey.exact_identity import exact_locus_display, exact_locus_from_native_manifest_bgc
    from mamey.parsers import assembly_metrics_from_zip, parse_bgcs_from_zip, read_genbank_records

    records = read_genbank_records(full_prepared, region_only=True)
    assert len(records) == 3
    assert {record.id for _, record in records} == {fixture_inputs.SYNTHETIC_FULL_CONTIG_ID}

    assembly = assembly_metrics_from_zip(full_prepared)
    assert (assembly.contigs, assembly.genome_bp, assembly.n50) == (1, 100000, 100000)
    old_bgcs = parse_bgcs_from_zip(old_prepared)
    new_bgcs = parse_bgcs_from_zip(full_prepared)
    assert len(old_bgcs) == len(new_bgcs) == 3
    semantic_fields = (
        "bgc_id", "region_number", "start", "end", "contig_length", "products",
        "edge_status", "kcb_top", "kcb_cumulative", "kcb_protein_hits",
    )
    assert [tuple(getattr(row, key) for key in semantic_fields) for row in old_bgcs] == [
        tuple(getattr(row, key) for key in semantic_fields) for row in new_bgcs
    ]
    assert {row.contig for row in new_bgcs} == {fixture_inputs.SYNTHETIC_FULL_CONTIG_ID}
    displays = [
        exact_locus_display("SMOKE", row.contig, row.antismash_region, row.bgc_id)
        for row in new_bgcs
    ]
    assert displays == [
        "SMOKE / SYNTHETIC_CONTIG_000001 / region001 / BGC001",
        "SMOKE / SYNTHETIC_CONTIG_000001 / region002 / BGC002",
        "SMOKE / SYNTHETIC_CONTIG_000001 / region003 / BGC003",
    ]
    native = exact_locus_from_native_manifest_bgc("SMOKE", new_bgcs[0].crosswalk_dict())
    assert native.full_contig == "SYNTHETIC_CONTIG_000001"
    assert native.normalized_node_id == "CONTIG_000001"
    assert native.exact_locus == displays[0]


def test_full_locus_generator_refuses_unbound_and_existing_targets(tmp_path: Path) -> None:
    root = _root()
    sys.path.insert(0, str(root))
    fixture_inputs = importlib.import_module("tools.fixture_inputs")
    assert hasattr(fixture_inputs, "prepare_full_locus_single_contig_fixture")
    source = root / "tests" / "fixtures" / "synthetic_single_contig_antismash.zip"

    altered = tmp_path / "altered.zip"
    altered.write_bytes(source.read_bytes() + b"changed")
    refused_target = tmp_path / "refused.zip"
    try:
        fixture_inputs.prepare_full_locus_single_contig_fixture(altered, refused_target)
    except ValueError as exc:
        assert "source hash" in str(exc)
    else:
        raise AssertionError("unbound source was accepted")
    assert not refused_target.exists()

    existing = tmp_path / "existing.zip"
    existing.write_bytes(b"keep")
    try:
        fixture_inputs.prepare_full_locus_single_contig_fixture(source, existing)
    except FileExistsError:
        pass
    else:
        raise AssertionError("existing output was clobbered")
    assert existing.read_bytes() == b"keep"


def test_full_locus_transform_refuses_duplicate_anchored_field() -> None:
    root = _root()
    sys.path.insert(0, str(root))
    fixture_inputs = importlib.import_module("tools.fixture_inputs")
    duplicate = (
        b"LOCUS       NODE_1             10 bp    DNA              UNK 01-JAN-1980\n"
        b"ACCESSION   NODE_1\n"
        b"ACCESSION   NODE_1\n"
        b"VERSION     NODE_1\n"
        b"ORIGIN\n//\n"
    )
    try:
        fixture_inputs._transform_region_gbk(duplicate)
    except ValueError as exc:
        assert "ACCESSION" in str(exc) and "found 2" in str(exc)
    else:
        raise AssertionError("duplicate anchored ACCESSION field was accepted")
