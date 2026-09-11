"""LQ-STRAIN-01/02 (v9.7.330): strain-level Mode B (Full Strain Sapote, S1-S8).

Tests that the generator emits the full S1-S8 skeleton from a minimal sealed package (degrading
gracefully where cohort data is absent), that the strain-structure gate accepts a complete card and
flags a truncated one, and that the release tag derives via the dedup_and_guard SSOT (AS- is PUBLIC per
the v9.7.236 PI decision; AJS-/PENDING-/unrecognized still fail safe to PRIVATE).
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mamey.strain_modeb import (  # noqa: E402
    build_strain_sapote, validate_strain_card, REQUIRED_STRAIN_SECTIONS,
)


def _minimal_package(tmp_path, strain="AS-999", release=None):
    pkg = tmp_path / strain / "package"
    pkg.mkdir(parents=True)
    manifest = {
        "strain_id": strain, "display_name": strain,
        "taxonomy": "Streptomyces sp.", "source": "bee-associated",
        "workflow_version": "1.9.112", "mode": "gold",
        "assembly": {"genome_size_mb": 8.0, "contigs": 300, "n50": 100000, "gc_percent": 71.0},
        "bgc_counts": {"raw": 12, "assembly_tier": "MODERATE"},
    }
    (pkg / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    intake = {"strain_id": strain, "release": release} if release else {"strain_id": strain}
    (pkg / f"{strain}_1_intake.json").write_text(json.dumps(intake), encoding="utf-8")
    return pkg


def test_generator_emits_all_s1_s8_and_gate_passes(tmp_path):
    pkg = _minimal_package(tmp_path)
    md, meta = build_strain_sapote(pkg)
    for tag, _ in REQUIRED_STRAIN_SECTIONS:
        assert f"## {tag} " in md or f"## {tag}·" in md, f"missing {tag}"
    rc, problems = validate_strain_card(md)
    assert rc == 0, problems
    assert meta["strain"] == "AS-999"


def test_gate_flags_truncated_card():
    truncated = "# card\n## S1 · identity\n## S2 · portfolio\ncapacity-level similarity extract-level"
    rc, problems = validate_strain_card(truncated)
    assert rc == 1
    assert any("S8" in p for p in problems)


def test_gate_flags_missing_claim_ceiling():
    # all sections present but no claim-safety markers -> gate flags the claim ceiling
    body = "\n".join(f"## {tag} · x" for tag, _ in REQUIRED_STRAIN_SECTIONS)
    rc, problems = validate_strain_card(body)
    assert rc == 1
    assert any("CLAIM_CEILING" in p for p in problems)


def test_release_derives_via_ssot_as_is_public(tmp_path):
    # AMBER_RELEASE_DRIFT: release now derives from dedup_and_guard.derive_release (the SSOT),
    # not a stale inline AS->PRIVATE rule. Per the v9.7.236 PI decision the AS- cohort is PUBLIC,
    # so a digit-bearing AS strain with no intake release emits PUBLIC.
    pkg = _minimal_package(tmp_path, strain="AS-777", release=None)
    md, _ = build_strain_sapote(pkg)
    assert "release **PUBLIC**" in md


def test_release_failsafe_private_on_ajs_and_pending(tmp_path):
    # The fail-safe is preserved for AJS-/PENDING- (and unrecognized) identifiers.
    for strain in ("AJS-777", "PENDING-777"):
        pkg = _minimal_package(tmp_path, strain=strain, release=None)
        md, _ = build_strain_sapote(pkg)
        assert "release **PRIVATE**" in md, strain


def test_release_honors_explicit_intake_tag(tmp_path):
    # An explicit intake release always wins over derivation.
    pkg = _minimal_package(tmp_path, strain="AS-777", release="PRIVATE")
    md, _ = build_strain_sapote(pkg)
    assert "release **PRIVATE**" in md
