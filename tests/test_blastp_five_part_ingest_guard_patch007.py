"""Patch 007: exact-current five-part BLASTP ingest guards and deterministic quarantine."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest

from mamey.blastp_gate import ingested
from mamey import blastp_ingest as bi
from mamey.blastp_ingest import (
    BlastpIngestLedgerError,
    _update_ingest_ledger,
    ingest_blastp_trove,
    install_channel_top10,
)


def _sha(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _package(tmp_path: Path, strain: str = "AS-162") -> Path:
    pkg = tmp_path / "package"
    pkg.mkdir(parents=True)
    (pkg / "manifest.json").write_text(json.dumps({"strain_id": strain}), encoding="utf-8")
    records = [
        {"bgc_id": "BGC007", "cds": [
            {"locus_tag": "ctg1_1", "aa_length": 300, "sec_met_domains": []},
            {"locus_tag": "ctg1_2", "aa_length": 250, "sec_met_domains": []},
        ]},
        {"bgc_id": "BGC008", "cds": [
            {"locus_tag": "ctg2_1", "aa_length": 410, "sec_met_domains": []},
        ]},
    ]
    (pkg / f"{strain}_gene_context.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in records), encoding="utf-8"
    )
    return pkg


def _trove(tmp_path: Path, rows: list[dict], *, top10: bool = False) -> Path:
    root = tmp_path / ("top10_trove" if top10 else "overlay_trove")
    bgc = root / "AS-162" / "BGC007"
    bgc.mkdir(parents=True)
    name = "BGC007_blastp_top10.csv" if top10 else "BGC007_top_hit_per_gene.csv"
    fields = sorted({key for row in rows for key in row})
    with (bgc / name).open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return root


def _row(**overrides) -> dict:
    row = {
        "strain": "AS-162", "bgc_id": "BGC007", "gene": "ctg1_1",
        "aa_length": "300", "subject_acc": "WP_1", "subject_organism": "Other species",
        "subject_def": "similar protein", "pct_identity": "72.0", "pct_positives": "81.0",
        "query_coverage": "98.0", "evalue": "1e-40", "bitscore": "200", "hit_rank": "1",
    }
    row.update(overrides)
    return row


def _quarantine(result: dict) -> list[dict]:
    with Path(result["quarantine"]).open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


@pytest.mark.parametrize(("overrides", "reason"), [
    ({"strain": "AS-190"}, "FOREIGN_STRAIN"),
    ({"bgc_id": "BGC008"}, "FOREIGN_BGC"),
    ({"gene": "ctg1_999"}, "NONCURRENT_LOCUS"),
    ({"aa_length": ""}, "ZERO_OR_BLANK_AA_LENGTH"),
    ({"aa_length": "0"}, "ZERO_OR_BLANK_AA_LENGTH"),
    ({"aa_length": "299"}, "QUERY_CURRENT_AA_LENGTH_MISMATCH"),
])
def test_overlay_rejects_non_exact_rows(tmp_path, overrides, reason):
    pkg = _package(tmp_path)
    trove = _trove(tmp_path, [_row(**overrides)])
    result = ingest_blastp_trove(pkg, trove, "nr", "AS-162")
    assert result["genes"] == 0 and result["quarantined"] == 1
    assert _quarantine(result)[0]["reason"] == reason
    assert not (pkg / "blastp_online" / "BGC007_online_blastp.csv").exists()
    assert "nr" not in ingested(pkg).get("BGC007", set())


def test_exact_row_is_admitted_with_durable_unmixed_provenance(tmp_path):
    pkg = _package(tmp_path)
    source = _trove(tmp_path, [_row()])
    result = ingest_blastp_trove(pkg, source, "nr", "AS-162")
    assert result["genes"] == 1 and result["quarantined"] == 0
    with (pkg / "blastp_online" / "BGC007_online_blastp.csv").open(newline="") as fh:
        row = next(csv.DictReader(fh))
    assert (row["query_strain"], row["query_bgc"], row["query_locus"],
            row["query_aa_length"]) == ("AS-162", "BGC007", "ctg1_1", "300")
    assert row["channel"] == row["source_channel"] == "nr"
    assert len(row["source_file_sha256"]) == 64
    assert "nr" in ingested(pkg)["BGC007"]


def test_pipe_query_provenance_is_accepted(tmp_path):
    pkg = _package(tmp_path)
    row = _row()
    row.pop("strain"); row.pop("bgc_id"); row.pop("gene"); row.pop("aa_length")
    row["query_locus"] = "AS-162|BGC007|ctg1_1|300"
    result = ingest_blastp_trove(pkg, _trove(tmp_path, [row]), "nr")
    assert result["genes"] == 1 and result["quarantined"] == 0


def test_legacy_overlay_is_quarantined_not_carried_forward(tmp_path):
    pkg = _package(tmp_path)
    overlay = pkg / "blastp_online"
    overlay.mkdir()
    (overlay / "BGC007_online_blastp.csv").write_text(
        "locus_tag,aa_length,blastp_accession,channel\nctg1_2,250,OLD,ebi\n",
        encoding="utf-8",
    )
    result = ingest_blastp_trove(pkg, _trove(tmp_path, [_row()]), "nr", "AS-162")
    rows = list(csv.DictReader((overlay / "BGC007_online_blastp.csv").open(newline="")))
    assert [r["locus_tag"] for r in rows] == ["ctg1_1"]
    assert any(r["reason"] == "LEGACY_PROVENANCE_HOLD" for r in _quarantine(result))


def test_missing_row_strain_and_bgc_is_legacy_provenance_hold(tmp_path):
    pkg = _package(tmp_path)
    row = _row()
    row.pop("strain"); row.pop("bgc_id")
    result = ingest_blastp_trove(pkg, _trove(tmp_path, [row]), "nr")
    assert result["genes"] == 0
    assert _quarantine(result)[0]["reason"] == "LEGACY_PROVENANCE_HOLD"


def test_conflicting_explicit_strain_fails_before_any_write(tmp_path):
    pkg = _package(tmp_path)
    trove = _trove(tmp_path, [_row()])
    before = sorted(p.relative_to(pkg) for p in pkg.rglob("*"))
    with pytest.raises(ValueError, match="conflicts with package manifest"):
        ingest_blastp_trove(pkg, trove, "nr", "AS-190")
    assert sorted(p.relative_to(pkg) for p in pkg.rglob("*")) == before
    assert not (pkg / "blastp_online").exists()


def test_top10_conflicting_strain_also_fails_before_any_write(tmp_path):
    pkg = _package(tmp_path)
    trove = _trove(tmp_path, [_row()], top10=True)
    before = sorted(p.relative_to(pkg) for p in pkg.rglob("*"))
    with pytest.raises(ValueError, match="conflicts with package manifest"):
        install_channel_top10(pkg, trove, "nr", "AS-190")
    assert sorted(p.relative_to(pkg) for p in pkg.rglob("*")) == before
    assert not (pkg / "blastp_nr").exists()


def test_top10_store_applies_same_guard_and_all_rejected_is_incomplete(tmp_path):
    pkg = _package(tmp_path)
    source = _trove(tmp_path, [_row(), _row(strain="AS-190", subject_acc="BAD")], top10=True)
    result = install_channel_top10(pkg, source, "nr", "AS-162")
    assert result["hits"] == 1 and result["quarantined"] == 1
    rows = list(csv.DictReader((pkg / "blastp_nr" / "BGC007_top10.csv").open(newline="")))
    assert len(rows) == 1 and rows[0]["subject_acc"] == "WP_1" and rows[0]["channel"] == "nr"

    pkg2 = _package(tmp_path / "second")
    source2 = _trove(tmp_path / "second", [_row(strain="AS-190")], top10=True)
    result2 = install_channel_top10(pkg2, source2, "nr", "AS-162")
    assert result2["hits"] == 0 and result2["quarantined"] == 1
    assert not (pkg2 / "blastp_nr" / "BGC007_top10.csv").exists()
    assert "nr" not in ingested(pkg2).get("BGC007", set())


def test_clean_reingest_is_idempotent_and_guard_artifacts_have_stable_hashes(tmp_path):
    pkg = _package(tmp_path)
    source = _trove(tmp_path, [_row()])
    first = ingest_blastp_trove(pkg, source, "nr", "AS-162")
    hashes1 = {_sha(first["quarantine"]), _sha(first["receipt"]),
               _sha(pkg / "blastp_online" / "_ingest_ledger.json")}
    second = ingest_blastp_trove(pkg, source, "nr", "AS-162")
    hashes2 = {_sha(second["quarantine"]), _sha(second["receipt"]),
               _sha(pkg / "blastp_online" / "_ingest_ledger.json")}
    assert first["quarantine"] == second["quarantine"]
    assert first["receipt"] == second["receipt"]
    assert hashes1 == hashes2


@pytest.mark.parametrize("original", [b"{not-json", b"[]"])
def test_ledger_update_refuses_to_replace_corrupt_prior_channels(tmp_path, original):
    """A corrupt multi-channel ledger is immutable evidence until an owner repairs it."""
    store = tmp_path / "package" / "blastp_online"
    store.mkdir(parents=True)
    ledger = store / "_ingest_ledger.json"
    ledger.write_bytes(original)

    with pytest.raises(BlastpIngestLedgerError, match="BLASTP_INGEST_LEDGER_HOLD"):
        _update_ingest_ledger(
            store, "nr", {"BGC001": 1}, [], "STRAIN-TEST", [], "receipt.json"
        )

    assert ledger.read_bytes() == original


def test_top10_install_propagates_configured_root_discovery_hold(tmp_path, monkeypatch):
    """STRAIN-TEST / NODE_1_length_1000_cov_20 / region001 / BGC007 cannot bypass a root hold."""
    pkg = _package(tmp_path)
    source = _trove(tmp_path, [_row()], top10=True)
    from mamey import blastp_gate

    def refuse_discovery(*_args, **_kwargs):
        raise blastp_gate.BlastpDiscoveryError(
            "BLASTP_DISCOVERY_HOLD: injected configured-root refusal"
        )

    monkeypatch.setattr(blastp_gate, "_strain_dirs_in", refuse_discovery)
    with pytest.raises(blastp_gate.BlastpDiscoveryError, match="BLASTP_DISCOVERY_HOLD"):
        install_channel_top10(pkg, source, "nr", "AS-162")
    assert not (pkg / "blastp_nr").exists()


def test_manual_binding_guard_refuses_corrupt_existing_manifest(tmp_path):
    """An existing corrupt package identity cannot degrade to legacy unbound admission."""
    from mamey.blastp_ingest import _manual_binding_guard
    pkg = tmp_path / "package"
    pkg.mkdir()
    (pkg / "manifest.json").write_text("{not-json", encoding="utf-8")
    source = tmp_path / "hits.csv"
    source.write_text("fixture\n", encoding="utf-8")
    with pytest.raises(ValueError, match="BLASTP_PACKAGE_MANIFEST_HOLD"):
        _manual_binding_guard(pkg, "STRAIN-TEST", [], source)


@pytest.mark.parametrize("installer,top10", [
    (ingest_blastp_trove, False),
    (install_channel_top10, True),
])
def test_bgc_file_discovery_traversal_error_is_a_typed_hold(
        tmp_path, monkeypatch, installer, top10):
    """AS-162 / NODE_1_length_1000_cov_20 / region007 / BGC007 cannot become absence."""
    pkg = _package(tmp_path)
    source = _trove(tmp_path, [_row()], top10=top10)
    bgc_dir = source / "AS-162" / "BGC007"
    original_iterdir = Path.iterdir

    def refuse_bgc_traversal(path):
        if path == bgc_dir:
            raise PermissionError("fixture denies BGC traversal")
        return original_iterdir(path)

    monkeypatch.setattr(Path, "iterdir", refuse_bgc_traversal)
    with pytest.raises(bi.BlastpTroveDiscoveryError, match="BLASTP_TROVE_DISCOVERY_HOLD"):
        installer(pkg, source, "nr", "AS-162")
    assert not (pkg / "blastp_online").exists()
    assert not (pkg / "blastp_nr").exists()


def test_missing_channel_pattern_remains_truthful_absence(tmp_path):
    """A readable BGC directory without the requested channel file is not a traversal hold."""
    pkg = _package(tmp_path)
    source = tmp_path / "trove" / "AS-162" / "BGC007"
    source.mkdir(parents=True)
    (source / "notes.txt").write_text("no BLASTp table\n", encoding="utf-8")
    result = ingest_blastp_trove(pkg, source.parents[1], "nr", "AS-162")
    assert result["genes"] == 0


def test_manual_binding_cannot_treat_unreadable_package_as_legacy(tmp_path, monkeypatch):
    """AS-162 / NODE_1_length_1000_cov_20 / region007 / BGC007 must remain bound."""
    from mamey.blastp_ingest import _manual_binding_guard
    pkg = _package(tmp_path)
    source = tmp_path / "hits.csv"
    source.write_text("fixture\n", encoding="utf-8")
    original_iterdir = Path.iterdir

    def refuse_package(path):
        if path == pkg:
            raise PermissionError("fixture denies package traversal")
        return original_iterdir(path)

    monkeypatch.setattr(Path, "iterdir", refuse_package)
    with pytest.raises(ValueError, match="BLASTP_PACKAGE_DISCOVERY_HOLD"):
        _manual_binding_guard(pkg, "AS-162", [], source)


def test_nr_clustered_nr_and_swissprot_remain_separate_offline_stores(tmp_path):
    """AS-162 / NODE_1_length_1000_cov_20 / region007 / BGC007 keeps channel identity."""
    pkg = _package(tmp_path)
    cases = [
        ("nr", "BGC007_blastp_top10.csv", "ACC_NR", "blastp_nr"),
        ("clustered_nr", "BGC007_blastp_top10_clustered.csv", "ACC_CLUSTERED", "blastp_clustered_nr"),
        ("swissprot", "BGC007_blastp_top10_local.csv", "ACC_SWISSPROT", "blastp_swissprot"),
    ]
    for channel, filename, accession, _store_name in cases:
        bgc_dir = tmp_path / f"trove_{channel}" / "AS-162" / "BGC007"
        bgc_dir.mkdir(parents=True)
        row = _row(subject_acc=accession)
        with (bgc_dir / filename).open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(row))
            writer.writeheader()
            writer.writerow(row)
        result = install_channel_top10(pkg, bgc_dir.parents[1], channel, "AS-162")
        assert result["hits"] == 1

    for channel, _filename, accession, store_name in cases:
        with (pkg / store_name / "BGC007_top10.csv").open(newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        assert len(rows) == 1
        assert rows[0]["channel"] == channel
        assert rows[0]["subject_acc"] == accession

    ledger = json.loads((pkg / "blastp_online" / "_ingest_ledger.json").read_text())
    assert set(ledger) >= {"nr", "clustered_nr", "swissprot"}
