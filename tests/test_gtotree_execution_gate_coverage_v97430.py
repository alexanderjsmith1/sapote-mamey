"""Additional negative controls for gtotree_execution_gate.py validation branches.

v9.7.430 coverage audit: 8 of 10 validation branches had no test coverage.
These 10 tests lock down every previously untested branch.
"""
import hashlib
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from gtotree_execution_gate import validate, digest


def make_file(tmp_path, name, content="data"):
    p = tmp_path / name
    p.write_text(content)
    return p


def make_packet(tmp_path):
    """Minimal valid packet with all required fields."""
    root = tmp_path / "runroot"
    work = root / "jobs" / "p1"
    out = root / "outputs" / "p1"
    work.mkdir(parents=True)
    out.mkdir(parents=True)

    gt = make_file(tmp_path, "GToTree", "gtotree-binary")
    hmm = make_file(tmp_path, "Actinobacteria.hmm", "hmm-data")
    genome = make_file(tmp_path, "g1.fna", ">tip1\nACGT\n")

    return {
        "run_id": "test-run",
        "gtotree": {"path": str(gt), "sha256": digest(gt), "version": "GToTree v1.8.19"},
        "hmm": {"path": str(hmm), "sha256": digest(hmm)},
        "panel": [{"tip": "tip1", "genome_path": str(genome), "sha256": digest(genome)}],
        "working_directory": str(work),
        "output_directory": str(out),
        "max_concurrent_jobs": 2,
    }, root


def test_packet_field_missing(tmp_path):
    """PACKET_FIELD_MISSING branch — no prior test."""
    packet, root = make_packet(tmp_path)
    del packet["panel"]
    with pytest.raises(ValueError, match="PACKET_FIELD_MISSING"):
        validate(packet, root)


def test_gtotree_identity_mismatch(tmp_path):
    """GTOTREE_IDENTITY branch — sha256 mismatch."""
    packet, root = make_packet(tmp_path)
    packet["gtotree"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="GTOTREE_IDENTITY"):
        validate(packet, root)


def test_hmm_identity_mismatch(tmp_path):
    """HMM_IDENTITY branch — sha256 mismatch."""
    packet, root = make_packet(tmp_path)
    packet["hmm"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="HMM_IDENTITY"):
        validate(packet, root)


def test_run_directory_isolation(tmp_path):
    """RUN_DIRECTORY_ISOLATION branch — work/out not under root."""
    packet, root = make_packet(tmp_path)
    packet["working_directory"] = str(tmp_path / "elsewhere")
    (tmp_path / "elsewhere").mkdir()
    with pytest.raises(ValueError, match="RUN_DIRECTORY_ISOLATION"):
        validate(packet, root)


def test_concurrency_cap_zero(tmp_path):
    """CONCURRENCY_CAP branch — jobs=0."""
    packet, root = make_packet(tmp_path)
    packet["max_concurrent_jobs"] = 0
    with pytest.raises(ValueError, match="CONCURRENCY_CAP"):
        validate(packet, root)


def test_concurrency_cap_five(tmp_path):
    """CONCURRENCY_CAP branch — jobs=5 (above max)."""
    packet, root = make_packet(tmp_path)
    packet["max_concurrent_jobs"] = 5
    with pytest.raises(ValueError, match="CONCURRENCY_CAP"):
        validate(packet, root)


def test_panel_identity_duplicate_tips(tmp_path):
    """PANEL_IDENTITY branch — duplicate tip names."""
    packet, root = make_packet(tmp_path)
    genome = make_file(tmp_path, "g2.fna", ">tip1\nGGGG\n")
    packet["panel"].append(
        {"tip": "tip1", "genome_path": str(genome), "sha256": digest(genome)}
    )
    with pytest.raises(ValueError, match="PANEL_IDENTITY"):
        validate(packet, root)


def test_genome_identity_mismatch(tmp_path):
    """GENOME_IDENTITY branch — genome sha256 mismatch."""
    packet, root = make_packet(tmp_path)
    packet["panel"][0]["sha256"] = "f" * 64
    with pytest.raises(ValueError, match="GENOME_IDENTITY"):
        validate(packet, root)


def test_duplicate_genome_content(tmp_path):
    """DUPLICATE_GENOME_CONTENT branch — two tips with same sha256."""
    packet, root = make_packet(tmp_path)
    # Second tip pointing to a file with identical content (same hash)
    genome2 = make_file(tmp_path, "g2.fna", ">tip1\nACGT\n")  # same content as g1.fna
    packet["panel"].append(
        {"tip": "tip2", "genome_path": str(genome2), "sha256": digest(genome2)}
    )
    with pytest.raises(ValueError, match="DUPLICATE_GENOME_CONTENT"):
        validate(packet, root)


def test_alignment_missing_postflight(tmp_path):
    """ALIGNMENT_MISSING branch — postflight with no alignment file."""
    packet, root = make_packet(tmp_path)
