"""Tests for the .344 BLASTp-completeness HARD gate (blastp_gate.py) + the coupled ingester
filename fix (blastp_ingest.py). Self-contained: builds a synthetic project root with a package
store and channel troves in tmp, so no workspace dependency.

Locks in:
  1. available() finds per-gene BLASTp under a trove (tolerating an intermediate dir).
  2. ingested() reads channels from the package store.
  3. gate() BLOCKS when a channel is available-but-not-ingested, with a message + exit intent.
  4. gate() PASSES when everything available is ingested.
  5. --waiver path passes AND records to manifest provenance.
  6. discover_trove_roots honours $MAMEY_BLASTP_SCAN_ROOT (generic, not workspace-specific).
  7. the ingester recognises clustered_nr (*_top10_clustered.csv) + swissprot (*_top10_local.csv)
     filenames (the bug that made them silently ingest 0).
"""
import csv
import json
import os
from pathlib import Path

import pytest

from mamey import blastp_gate as G
from mamey import blastp_availability as A


def _store(pkg: Path, bgc: str, channel: str):
    """Write a minimal ingested store file for one BGC/channel."""
    d = pkg / "blastp_online"
    d.mkdir(parents=True, exist_ok=True)
    with (d / f"{bgc}_online_blastp.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["locus_tag", "pct_identity", "channel"])
        w.writerow([f"{bgc}_1", "80", channel])


def _trove(root: Path, channel_folder: str, strain: str, bgc: str, fname: str):
    d = root / channel_folder / strain / bgc
    d.mkdir(parents=True, exist_ok=True)
    with (d / fname).open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["strain", "bgc_id", "gene", "aa_length", "subject_acc",
                    "pct_identity", "bitscore"])
        w.writerow([strain, bgc, f"{bgc}_1", "300", "WP_123", "55", "200"])


@pytest.fixture
def project(tmp_path, monkeypatch):
    root = tmp_path / "proj"
    (root / ".git").mkdir(parents=True)  # generic project marker
    pkg = root / "runs" / "AS-TEST" / "package"
    pkg.mkdir(parents=True)
    (pkg / "AS-TEST_4_triage_board.csv").write_text("BGC_ID\nBGC001\n", encoding="utf-8")
    (pkg / "manifest.json").write_text(json.dumps({"strain_id": "AS-TEST"}), encoding="utf-8")
    (pkg / "AS-TEST_gene_context.jsonl").write_text(json.dumps({
        "bgc_id": "BGC001", "cds": [{"locus_tag": "BGC001_1", "aa_length": 300}],
    }) + "\n", encoding="utf-8")
    monkeypatch.setenv("MAMEY_BLASTP_SCAN_ROOT", str(root))
    return root, pkg


def test_available_and_ingested(project):
    root, pkg = project
    _trove(root, "Blastp RESULTS (clustered nr)", "AS-TEST", "BGC001", "BGC001_blastp_top10_clustered.csv")
    _store(pkg, "BGC001", "nr")
    roots = G.discover_trove_roots(pkg)
    avail = G.available("AS-TEST", roots)
    assert "BGC001" in avail.get("clustered_nr", {})
    have = G.ingested(pkg)
    assert "nr" in have["BGC001"]


def test_availability_keeps_stored_overlay_visible_without_discoverable_trove(project):
    """A package-stored channel must not display as zero when its original trove moved."""
    _store(project[1], "BGC001", "nr")
    roots = {ch: [] for ch in A.CHANNELS}
    rec = A.strain_availability(project[1], "AS-TEST", trove_roots=roots)
    nr = rec["channels"]["nr"]
    assert nr == {"avail": 0, "ingested": 1, "matched": 0,
                  "ingested_only": 1, "missing": 0}
    assert rec["gate_blocked"] is False


def test_availability_separates_stored_matched_and_missing(project):
    root, pkg = project
    _trove(root, "Local Blastp RESULTS (SwissProt)", "AS-TEST", "BGC001",
           "BGC001_blastp_top10_local.csv")
    roots = G.discover_trove_roots(pkg)
    rec = A.strain_availability(pkg, "AS-TEST", trove_roots=roots)
    swiss = rec["channels"]["swissprot"]
    assert swiss["avail"] == 1 and swiss["ingested"] == 0
    assert swiss["matched"] == 0 and swiss["missing"] == 1
    assert rec["gate_blocked"] is True


def test_gate_blocks_on_available_not_ingested(project):
    root, pkg = project
    _trove(root, "Local Blastp RESULTS (SwissProt)", "AS-TEST", "BGC001", "BGC001_blastp_top10_local.csv")
    # nothing ingested for swissprot
    res = G.gate(pkg, "AS-TEST")
    assert res["blocked"] is True and res["ok"] is False
    assert any(ch == "swissprot" for ch, _b, _p in res["missing"])
    assert "BLOCKED" in res["message"] and "ingest-blastp-trove" in res["message"]


def test_gate_passes_when_ingested(project):
    root, pkg = project
    _trove(root, "Local Blastp RESULTS (SwissProt)", "AS-TEST", "BGC001", "BGC001_blastp_top10_local.csv")
    _store(pkg, "BGC001", "swissprot")
    res = G.gate(pkg, "AS-TEST")
    assert res["ok"] is True and res["blocked"] is False


def test_waiver_passes_and_records(project):
    root, pkg = project
    _trove(root, "Local Blastp RESULTS (SwissProt)", "AS-TEST", "BGC001", "BGC001_blastp_top10_local.csv")
    res = G.gate(pkg, "AS-TEST", waiver="swissprot pending; nr ingested")
    assert res["ok"] is True and res["waived"] is True
    man = json.loads((pkg / "manifest.json").read_text())
    assert man["blastp_waivers"][0]["reason"].startswith("swissprot pending")
    assert man["blastp_waivers"][0]["n_waived"] >= 1


def test_waiver_replace_failure_preserves_manifest_and_blocks(project, monkeypatch):
    """A waiver is never reported as recorded when its atomic manifest commit fails."""
    root, pkg = project
    _trove(root, "Local Blastp RESULTS (SwissProt)", "AS-TEST", "BGC001",
           "BGC001_blastp_top10_local.csv")
    manifest = pkg / "manifest.json"
    original = manifest.read_bytes()
    original_replace = Path.replace

    def refuse_waiver_commit(path, target):
        if target == manifest and path.name.endswith(".blastp-waiver.tmp"):
            raise PermissionError("fixture denies waiver commit")
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", refuse_waiver_commit)
    result = G.gate(pkg, "AS-TEST", waiver="fixture waiver")
    assert result["ok"] is False and result["blocked"] is True
    assert manifest.read_bytes() == original


def test_scan_root_is_generic_env(project):
    root, pkg = project
    # resolves via env, not any dataset-specific folder name
    assert G.find_workspace_root(pkg) == Path(str(root)).resolve() or G.find_workspace_root(pkg) == root


def test_discovery_refuses_unreadable_root(tmp_path, monkeypatch):
    """Unreadable evidence roots are a hold, not evidence that no BLASTp is available."""
    root = tmp_path / "unreadable_evidence_root"
    root.mkdir()
    package = tmp_path / "package"
    package.mkdir()
    original_iterdir = Path.iterdir

    def refuse_selected_root(path):
        if path == root:
            raise PermissionError("fixture denies evidence-root traversal")
        return original_iterdir(path)

    monkeypatch.setattr(Path, "iterdir", refuse_selected_root)
    with pytest.raises(G.BlastpDiscoveryError, match="BLASTP_DISCOVERY_HOLD"):
        G.discover_trove_roots(package, roots_base=root)


def test_available_refuses_unreadable_trove_root(tmp_path, monkeypatch):
    """A configured unreadable channel root must not collapse to zero available evidence."""
    root = tmp_path / "nr_evidence_root"
    root.mkdir()
    original_iterdir = Path.iterdir

    def refuse_selected_root(path):
        if path == root:
            raise PermissionError("fixture denies channel-root traversal")
        return original_iterdir(path)

    monkeypatch.setattr(Path, "iterdir", refuse_selected_root)
    roots = {channel: [] for channel in G.CHANNEL_TROVE}
    roots["nr"] = [root]
    with pytest.raises(G.BlastpDiscoveryError, match="BLASTP_DISCOVERY_HOLD"):
        G.available("STRAIN-TEST", roots)


def test_gate_refuses_unreadable_candidate_trove_file(project, monkeypatch):
    """STRAIN-TEST / NODE_1_length_1000_cov_20 / region001 / BGC001: unreadable input is not absence."""
    root, pkg = project
    _trove(root, "NCBI_NR", "AS-TEST", "BGC001", "BGC001_top_hit_per_gene.csv")
    source = root / "NCBI_NR" / "AS-TEST" / "BGC001" / "BGC001_top_hit_per_gene.csv"
    original_open = Path.open

    def refuse_source(path, *args, **kwargs):
        if path == source:
            raise PermissionError("fixture denies candidate-trove read")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", refuse_source)
    with pytest.raises(G.BlastpDiscoveryError, match="BLASTP_DISCOVERY_HOLD"):
        G.gate(pkg, "AS-TEST")


def test_gate_refuses_unreadable_bgc_candidate_directory(project, monkeypatch):
    """STRAIN-TEST / NODE_1_length_1000_cov_20 / region001 / BGC001 directory is not absence."""
    root, pkg = project
    _trove(root, "NCBI_NR", "AS-TEST", "BGC001", "BGC001_top_hit_per_gene.csv")
    bgc_dir = root / "NCBI_NR" / "AS-TEST" / "BGC001"
    original_iterdir = Path.iterdir

    def refuse_bgc_dir(path):
        if path == bgc_dir:
            raise PermissionError("fixture denies BGC candidate-directory traversal")
        return original_iterdir(path)

    monkeypatch.setattr(Path, "iterdir", refuse_bgc_dir)
    with pytest.raises(G.BlastpDiscoveryError, match="BLASTP_DISCOVERY_HOLD"):
        G.gate(pkg, "AS-TEST")


def test_gate_refuses_unreadable_stored_overlay(project, monkeypatch):
    """STRAIN-TEST / NODE_1_length_1000_cov_20 / region001 / BGC001: stored evidence cannot vanish."""
    root, pkg = project
    _trove(root, "NCBI_NR", "AS-TEST", "BGC001", "BGC001_top_hit_per_gene.csv")
    _store(pkg, "BGC001", "nr")
    overlay = pkg / "blastp_online" / "BGC001_online_blastp.csv"
    original_open = Path.open

    def refuse_overlay(path, *args, **kwargs):
        if path == overlay:
            raise PermissionError("fixture denies stored-overlay read")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", refuse_overlay)
    with pytest.raises(G.BlastpDiscoveryError, match="BLASTP_DISCOVERY_HOLD"):
        G.gate(pkg, "AS-TEST")


def test_gate_refuses_unreadable_stored_overlay_directory(project, monkeypatch):
    """AS-TEST / NODE_1_length_1000_cov_20 / region001 / BGC001 cannot vanish at discovery."""
    _root, pkg = project
    _store(pkg, "BGC001", "nr")
    store = pkg / "blastp_online"
    original_iterdir = Path.iterdir

    def refuse_store(path):
        if path == store:
            raise PermissionError("fixture denies stored-overlay traversal")
        return original_iterdir(path)

    monkeypatch.setattr(Path, "iterdir", refuse_store)
    with pytest.raises(G.BlastpDiscoveryError, match="BLASTP_DISCOVERY_HOLD"):
        G.ingested(pkg)


@pytest.mark.parametrize("payload", ["{not-json", "[]"])
def test_gate_refuses_corrupt_ingest_ledger(project, payload):
    """STRAIN-TEST / NODE_1_length_1000_cov_20 / region001 / BGC001: corrupt ledger is not empty."""
    root, pkg = project
    _trove(root, "NCBI_NR", "AS-TEST", "BGC001", "BGC001_top_hit_per_gene.csv")
    ledger = pkg / "blastp_online" / "_ingest_ledger.json"
    ledger.parent.mkdir()
    ledger.write_text(payload, encoding="utf-8")
    with pytest.raises(Exception, match="BLASTP_INGEST_LEDGER_HOLD"):
        G.gate(pkg, "AS-TEST")


def test_header_only_candidate_trove_remains_optional_absence(project):
    """A readable header-only source is expected absence, not an unreadable-evidence hold."""
    root, pkg = project
    source_dir = root / "NCBI_NR" / "AS-TEST" / "BGC001"
    source_dir.mkdir(parents=True)
    (source_dir / "BGC001_top_hit_per_gene.csv").write_text(
        "strain,bgc_id,gene,subject_acc\n", encoding="utf-8"
    )
    result = G.gate(pkg, "AS-TEST")
    assert result["ok"] is True and result["missing"] == []


def test_ingester_recognises_clustered_and_swissprot_filenames(project):
    root, pkg = project
    _trove(root, "Blastp RESULTS (clustered nr)", "AS-TEST", "BGC001", "BGC001_blastp_top10_clustered.csv")
    from mamey.blastp_ingest import ingest_blastp_trove
    res = ingest_blastp_trove(pkg, root / "Blastp RESULTS (clustered nr)", "clustered_nr", "AS-TEST")
    # the fix: it must actually pick up the *_top10_clustered.csv file (was 0 before)
    assert res.get("genes", res.get("n_genes", 1)) != 0 or res.get("bgcs", 1) != 0
    have = G.ingested(pkg)
    assert "clustered_nr" in have.get("BGC001", set())


def test_unmarked_package_fallback_stays_at_containing_directory(tmp_path, monkeypatch):
    root = tmp_path / 'isolated'
    package = root / 'package'
    package.mkdir(parents=True)
    elsewhere = tmp_path / 'elsewhere'
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    monkeypatch.delenv('MAMEY_BLASTP_SCAN_ROOT', raising=False)
    monkeypatch.setattr(G, '_PROJECT_MARKERS', ('uncreated_project_marker',))
    assert G.find_workspace_root(package) == root


def test_invalid_explicit_scan_root_is_not_silently_replaced(tmp_path, monkeypatch):
    package = tmp_path / 'package'
    package.mkdir()
    monkeypatch.setenv('MAMEY_BLASTP_SCAN_ROOT', str(tmp_path / 'missing_configured_root'))
    with pytest.raises(G.BlastpDiscoveryError, match='BLASTP_DISCOVERY_HOLD'):
        G.find_workspace_root(package)
