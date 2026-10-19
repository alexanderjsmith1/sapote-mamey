"""Public-gate controls using only generic toy files under tmp_path.

Native artifact/ledger writers are used; no ingest/re-key resolver, report, CLI,
analysis, sequence parser, renderer, transport or subprocess is invoked.
Managed case supplies a minimal synthetic output/authority hash binding, not a
physical-locus validation claim or full native PhysicalAdmission.prepare proof."""
import csv
import hashlib
import io
import json
from pathlib import Path

import pytest
from mamey import blastp_gate as gate
from mamey import blastp_ingest as ingest
from mamey.blastp_physical_binding import POLICY
from tests.source_change_helpers import replace_after_first_binary_read


STRAIN = "toy-strain"
SOURCE_ALIAS = "BGC900"
HELD_ALIAS = "BGC901"
REPLACEMENT_ALIAS = "BGC902"


def _native_artifact_fixture(tmp_path, managed):
    package = tmp_path / "package"
    package.mkdir()
    trove = tmp_path / "trove"
    source = trove / STRAIN / SOURCE_ALIAS / (SOURCE_ALIAS + "_top_hit_per_gene.csv")
    source.parent.mkdir(parents=True)
    source.write_bytes(b"gene,aa_length\ntoy_locus,5\n")
    source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    source_file = source.relative_to(trove / STRAIN).as_posix()
    sources = [{"bgc": SOURCE_ALIAS, "file": source_file, "sha256": source_sha,
                "destination_bgcs": []}]
    keys = {"query_strain": STRAIN, "query_bgc": SOURCE_ALIAS,
            "query_locus": "toy_locus", "query_aa_length": "5",
            "current_aa_length": "5", "source_bgc": SOURCE_ALIAS,
            "source_query_bgc": SOURCE_ALIAS, "resolved_bgc": HELD_ALIAS,
            "resolution_state": "TOY_SOFTWARE_CONTROL"}
    rejected = [ingest._quarantine_row(
        "LEGACY_PROVENANCE_HOLD", "nr", STRAIN, HELD_ALIAS, keys,
        source_file, source_sha, 2, {"gene": "toy_locus"})]
    binding = None
    if managed:
        authority = package / "toy-authority.txt"
        authority.write_bytes(b"synthetic hash prerequisite only\n")
        overlay = package / "blastp_online" / (HELD_ALIAS + "_online_blastp.csv")
        overlay.parent.mkdir()
        overlay.write_bytes(b"locus_tag,channel\ntoy_locus,nr\n")
        binding = {"policy": POLICY,
                   "authority_sources": [{"path": authority.name,
                       "sha256": hashlib.sha256(authority.read_bytes()).hexdigest()}],
                   "output_sha256": {overlay.relative_to(package).as_posix():
                       hashlib.sha256(overlay.read_bytes()).hexdigest()},
                   "deleted_outputs": []}
    quarantine_name, receipt_name = ingest._write_guard_artifacts(
        package, "nr", "overlay", STRAIN, sources, {}, rejected,
        {"enabled": True, "authority": "synthetic software control only",
         "resolution_counts": {}, "admitted_current_bgcs": {}},
        physical_binding=binding)
    ingest._update_ingest_ledger(package / "blastp_online", "nr", {}, rejected,
                                STRAIN, sources, receipt_name, physical_binding=binding)
    quarantine = Path(quarantine_name)
    original = quarantine.read_bytes()
    receipt = json.loads(Path(receipt_name).read_bytes())
    assert receipt["quarantine_sha256"] == hashlib.sha256(original).hexdigest()
    ledger = json.loads((package / "blastp_online" / "_ingest_ledger.json").read_bytes())
    record = ledger["nr"][HELD_ALIAS]
    assert record["evidence_complete"] is False
    assert ("physical_generations" in record) is managed
    before = {p: p.read_bytes() for p in package.rglob("*") if p.is_file() and p != quarantine}
    before[source] = source.read_bytes()
    return package, trove, quarantine, original, before


def _replace_only_resolved_alias(original):
    rows = list(csv.DictReader(io.StringIO(original.decode("utf-8"), newline="")))
    assert len(rows) == 1 and rows[0]["resolved_bgc"] == HELD_ALIAS
    rows[0]["resolved_bgc"] = REPLACEMENT_ALIAS
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    replacement = buffer.getvalue().encode("utf-8")
    assert replacement != original
    assert len(replacement) == len(original)
    return replacement


def _assert_typed_reconciliation(result):
    assert result["ok"] is True and result["blocked"] is False
    assert result["waived"] is False and result["missing"] == []
    row, = result["source_reconciliation"]
    assert row["state"] == "REKEYED_SOURCE_WITH_TYPED_HOLDS_ONLY"
    assert row["admitted_current_bgcs"] == []
    assert row["held_current_bgcs"] == [HELD_ALIAS]
    assert row["current_bgcs"] == [HELD_ALIAS]
    assert row["source_hold_reasons"] == {"LEGACY_PROVENANCE_HOLD": 1}
    assert REPLACEMENT_ALIAS not in result["message"]
    summary, = result["rekey_receipt_summaries"]
    assert summary["admitted_total"] == 0 and summary["quarantined_total"] == 1


@pytest.mark.parametrize("managed", [False, True])
def test_public_gate_replacement_keeps_verified_rows_or_refuses(tmp_path, monkeypatch, managed):
    package, trove, quarantine, original, before = _native_artifact_fixture(tmp_path, managed)
    replacement = _replace_only_resolved_alias(original)
    changed = replace_after_first_binary_read(
        monkeypatch, quarantine, replacement, binary_only=False)
    result = None
    refusal = None
    try:
        result = gate.gate(package, STRAIN, trove_roots={"nr": [trove]})
    except gate.BlastpDiscoveryError as exc:
        refusal = str(exc)
    assert changed == [True]
    assert quarantine.read_bytes() == replacement
    assert all(p.read_bytes() == data for p, data in before.items())
    if refusal is None:
        _assert_typed_reconciliation(result)
    else:
        assert "HOLD" in refusal


@pytest.mark.parametrize("managed", [False, True])
def test_public_gate_unchanged_valid_receipt_preserves_typed_holds(tmp_path, managed):
    package, trove, quarantine, original, before = _native_artifact_fixture(tmp_path, managed)
    result = gate.gate(package, STRAIN, trove_roots={"nr": [trove]})
    _assert_typed_reconciliation(result)
    assert quarantine.read_bytes() == original
    assert all(p.read_bytes() == data for p, data in before.items())
