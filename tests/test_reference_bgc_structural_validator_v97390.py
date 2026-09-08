from __future__ import annotations

import csv
import hashlib
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


TOOL = Path(__file__).parents[1] / "tools" / "reference_bgc_structural_validator.py"
TEMPLATE = (
    Path(__file__).parents[1]
    / "resources"
    / "reference_seed_inputs"
    / "reference_bgc_validation_manifest.template.tsv"
)
SEED_TOOL = Path(__file__).parents[1] / "tools" / "seed_reference_library.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("reference_bgc_structural_validator_v97390", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_seed_tool():
    spec = importlib.util.spec_from_file_location("seed_reference_library_v97390", SEED_TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_manifest(path: Path, source_sha: str, **overrides: str) -> None:
    row = {
        "source_zip": "reference.zip",
        "source_zip_sha256": source_sha,
        "compound": "compound-X",
        "accession": "ACC0001",
        "strain": "Reference strain X",
        "full_contig": "NODE_1_length_1000_cov_10.0",
        "region": "region001",
        "bgc_alias": "BGC001",
        "evidence_citation": "MIBiG:TEST0001; DOI:10.example/test",
        "expected_size_kb_MIBIG": "0.011",
        "expected_core_genes": "coreA;coreB",
        "reference_marker_set": "T43-A;T43-B",
    }
    row.update(overrides)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerow(row)


class _Parsers:
    @staticmethod
    def parse_bgcs_from_zip(_path):
        return [
            SimpleNamespace(
                bgc_id="BGC001",
                contig="NODE_1_length_1000_cov_10.0",
                node_id="NODE_1_length_1000_cov_10.0",
                antismash_region="region001",
                region_number=1,
                start=10,
                end=20,
                closest_candidate_kcb_product="full anchor / supporting detail that must not be discarded",
                kcb_top="",
            )
        ]

    @staticmethod
    def extract_cds_features(_path):
        # Inclusive endpoint contact counts; an adjacent non-overlap does not.
        return [
            SimpleNamespace(contig="NODE_1_length_1000_cov_10.0", start=1, end=10),
            SimpleNamespace(contig="NODE_1_length_1000_cov_10.0", start=20, end=25),
            SimpleNamespace(contig="NODE_1_length_1000_cov_10.0", start=21, end=30),
        ]

    @staticmethod
    def extract_domain_features(_path):
        return [SimpleNamespace(contig="NODE_1_length_1000_cov_10.0", start=12, end=15)]

    @staticmethod
    def extract_contig_sequences(_path):
        return {"NODE_1_length_1000_cov_10.0": "A" * 1000}


def _run_source_scans(_bgcs, _cds, _contigs, _domains):
    # Deliberately duplicated and unsorted to verify deterministic output.
    return SimpleNamespace(cctt={"per_bgc": {"BGC001": ["T43-B", "T43-A", "T43-A"]}})


def test_success_is_exact_bound_inclusive_and_provenance_complete(tmp_path, monkeypatch):
    tool = _load_tool()
    source = tmp_path / "reference.zip"
    source.write_bytes(b"immutable fake reference")
    manifest = tmp_path / "references.tsv"
    _write_manifest(manifest, hashlib.sha256(source.read_bytes()).hexdigest())
    output = tmp_path / "out" / "structural.tsv"
    failures = tmp_path / "out" / "holds.tsv"
    monkeypatch.setattr(
        tool,
        "_load_engine",
        lambda: (_Parsers, _run_source_scans, "1.9.test", "9.7.test"),
    )

    assert tool.run_panel(manifest, tmp_path, output, failures) == 0
    with output.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    row = rows[0]
    assert row["exact_locus"] == (
        "Reference strain X / NODE_1_length_1000_cov_10.0 / region001 / BGC001"
    )
    assert row["found_size_bp"] == "11"
    assert row["found_size_kb"] == "0.011"
    assert row["found_n_cds"] == "2"
    assert row["found_n_domains"] == "1"
    assert row["engine_markers_fired"] == "T43-A, T43-B"
    assert row["n_markers_fired"] == "2"
    assert row["marker_scope"] == "CCTT_PER_BGC_ONLY"
    assert row["markers_present_of_expected"] == "T43-A, T43-B"
    assert row["kcb_anchor"] == "full anchor"
    assert row["kcb_anchor_raw"].endswith("must not be discarded")
    assert row["source_zip_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert row["authority"] == tool.AUTHORITY
    with failures.open(newline="") as handle:
        assert list(csv.DictReader(handle, delimiter="\t")) == []


def test_missing_source_writes_typed_hold_and_preserves_existing_output(tmp_path, monkeypatch):
    tool = _load_tool()
    manifest = tmp_path / "references.tsv"
    _write_manifest(manifest, "0" * 64)
    output = tmp_path / "structural.tsv"
    output.write_text("preserve-existing-output\n")
    failures = tmp_path / "holds.tsv"
    monkeypatch.setattr(
        tool,
        "_load_engine",
        lambda: (_Parsers, _run_source_scans, "1.9.test", "9.7.test"),
    )

    assert tool.run_panel(manifest, tmp_path, output, failures) == 2
    assert output.read_text() == "preserve-existing-output\n"
    with failures.open(newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert len(rows) == 1
    assert rows[0]["hold_code"] == "SOURCE_ZIP_MISSING"
    assert rows[0]["exact_locus"].endswith("region001 / BGC001")


def test_sha_mismatch_is_typed_and_never_replaces_output(tmp_path, monkeypatch):
    tool = _load_tool()
    source = tmp_path / "reference.zip"
    source.write_bytes(b"different bytes")
    manifest = tmp_path / "references.tsv"
    _write_manifest(manifest, "0" * 64)
    output = tmp_path / "structural.tsv"
    output.write_text("old\n")
    failures = tmp_path / "holds.tsv"
    monkeypatch.setattr(
        tool,
        "_load_engine",
        lambda: (_Parsers, _run_source_scans, "1.9.test", "9.7.test"),
    )

    assert tool.run_panel(manifest, tmp_path, output, failures) == 2
    assert output.read_text() == "old\n"
    with failures.open(newline="") as handle:
        hold = next(csv.DictReader(handle, delimiter="\t"))
    assert hold["hold_code"] == "SOURCE_ZIP_SHA256_MISMATCH"
    assert "expected=" in hold["detail"] and "observed=" in hold["detail"]


def test_exact_selector_refuses_alias_only_and_parse_order_fallback():
    tool = _load_tool()
    spec = tool.ReferenceSpec(
        source_zip="reference.zip",
        source_zip_sha256="0" * 64,
        compound="compound-X",
        accession="ACC0001",
        strain="Reference strain X",
        full_contig="NODE_EXPECTED",
        region="region001",
        bgc_alias="BGC001",
        evidence_citation="citation",
    )
    wrong = SimpleNamespace(
        bgc_id="BGC001",
        contig="NODE_WRONG",
        node_id="NODE_WRONG",
        antismash_region="region001",
        region_number=1,
    )
    with pytest.raises(tool.ManifestError, match="exact target matched 0 records"):
        tool.select_exact_bgc(spec, [wrong])


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"strain": ""}, "required field 'strain' is empty"),
        ({"region": "1"}, "region must be formatted like region001"),
        ({"bgc_alias": "cluster1"}, "bgc_alias must be formatted like BGC001"),
        ({"source_zip": "../escape.zip"}, "relative locator inside --input-dir"),
        ({"source_zip_sha256": "not-a-hash"}, "not a lowercase SHA-256"),
    ],
)
def test_manifest_fails_closed_on_identity_and_source_defects(tmp_path, override, message):
    tool = _load_tool()
    manifest = tmp_path / "references.tsv"
    _write_manifest(manifest, "0" * 64, **override)
    with pytest.raises(tool.ManifestError, match=message):
        tool.load_reference_manifest(manifest)


def test_manifest_refuses_duplicate_exact_locus(tmp_path):
    tool = _load_tool()
    manifest = tmp_path / "references.tsv"
    header = list(tool.REQUIRED_MANIFEST_FIELDS)
    row = {
        "source_zip": "reference.zip",
        "source_zip_sha256": "0" * 64,
        "compound": "compound-X",
        "accession": "ACC0001",
        "strain": "Reference strain X",
        "full_contig": "NODE_1",
        "region": "region001",
        "bgc_alias": "BGC001",
        "evidence_citation": "citation",
    }
    with manifest.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerow(row)
        writer.writerow(row)
    with pytest.raises(tool.ManifestError, match="duplicate exact locus"):
        tool.load_reference_manifest(manifest)


def test_output_and_failure_paths_must_be_distinct(tmp_path):
    tool = _load_tool()
    path = tmp_path / "collision.tsv"
    assert tool.run_panel(tmp_path / "unused.tsv", tmp_path, path, path) == 2
    assert not path.exists()


def test_outputs_must_not_overwrite_manifest(tmp_path):
    tool = _load_tool()
    manifest = tmp_path / "references.tsv"
    manifest.write_text("preserve-manifest\n")
    failure = tmp_path / "holds.tsv"
    assert tool.run_panel(manifest, tmp_path, manifest, failure) == 2
    assert manifest.read_text() == "preserve-manifest\n"
    assert not failure.exists()


def test_shipped_manifest_template_has_exact_identity_and_provenance_columns():
    tool = _load_tool()
    with TEMPLATE.open(newline="") as handle:
        header = next(csv.reader(handle, delimiter="\t"))
    assert set(tool.REQUIRED_MANIFEST_FIELDS).issubset(header)
    assert {"strain", "full_contig", "region", "bgc_alias", "evidence_citation"}.issubset(header)


def test_tool_source_has_no_private_runtime_path_or_model_truth_language():
    text = TOOL.read_text()
    assert "/mnt/user-data" not in text
    assert "/Users/" not in text
    assert "ChatGPT work order" not in text
    assert "bare WGS" not in text


def test_primary_tool_and_seed_contract_use_generic_reference_bgc_names():
    seed = _load_seed_tool()
    assert TOOL.name == "reference_bgc_structural_validator.py"
    assert Path(seed._DEFAULT_STRUCT).name == "reference_bgc_structural.csv"
    assert TEMPLATE.name == "reference_bgc_validation_manifest.template.tsv"


def test_seed_tool_accepts_legacy_filename_only_as_warned_fallback(tmp_path, monkeypatch, capsys):
    seed = _load_seed_tool()
    current = tmp_path / "reference_bgc_structural.csv"
    legacy = tmp_path / "legacy.csv"
    legacy.write_text("legacy\n", encoding="utf-8")
    monkeypatch.setattr(seed, "_DEFAULT_STRUCT", str(current))
    monkeypatch.setattr(seed, "_LEGACY_STRUCT", str(legacy))
    monkeypatch.delenv("MAMEY_SEED_STRUCT", raising=False)

    assert seed._resolve_struct([]) == str(legacy)
    assert "DEPRECATION" in capsys.readouterr().err


def test_explicit_seed_path_never_falls_back(tmp_path, monkeypatch):
    seed = _load_seed_tool()
    explicit = tmp_path / "missing.csv"
    legacy = tmp_path / "legacy.csv"
    legacy.write_text("legacy\n", encoding="utf-8")
    monkeypatch.setattr(seed, "_LEGACY_STRUCT", str(legacy))
    with pytest.raises(SystemExit, match="seed input not found"):
        seed._resolve_struct([str(explicit)])
