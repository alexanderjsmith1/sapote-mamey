"""Exercise F13 through the shipped, documented ``python -m mamey`` route.

The fixtures are generic and govern only their own synthetic two-strain denominator.
They do not select a scientific cohort or accept source artwork scientifically.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


pytest.importorskip("matplotlib")
pytestmark = pytest.mark.slow

from tests.test_cohort_figures_v9792 import _make_pkg


ROOT = Path(__file__).resolve().parents[1]


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _governed_cli_fixture(tmp_path: Path) -> tuple[Path, Path, str, Path, str]:
    runs = tmp_path / "runs"
    for strain, cohort in (("SYN-01", "BEE"), ("SYN-02", "WASP")):
        package = Path(_make_pkg(
            str(runs), strain, "GOOD", "PUBLIC", "Streptomyces sp.", 4
        ))
        _write_json(package / "manifest.json", {
            "strain_id": strain,
            "workflow_version": "1.9.99",
            "bgcs": [
                {
                    "bgc_id": f"BGC{index:03d}",
                    "node_id": f"NODE_{index:04d}",
                    "antismash_region": f"region{index:03d}",
                }
                for index in range(1, 5)
            ],
        })
        _write_json(package / f"{strain}_1_intake.json", {
            "strain_id": strain,
            "taxonomy": "Streptomyces sp.",
            "antismash_version": "8.0.1",
        })

    cohort_manifest = tmp_path / "cohort.json"
    _write_json(cohort_manifest, {
        "schema_version": "sapote-mamey.figure-cohort-manifest.v1",
        "denominator_scope": "GENERIC_TWO_STRAIN_FIXTURE",
        "rows": [
            {
                "identity": strain,
                "role": "STUDY",
                "include_by_default": True,
                "genus": "Streptomyces",
                "cohort": cohort,
                "assembly_state": "PASS",
                "assembly_reason": "generic fixture passed",
            }
            for strain, cohort in (("SYN-01", "BEE"), ("SYN-02", "WASP"))
        ],
    })
    denominator_registry = tmp_path / "denominators.json"
    _write_json(denominator_registry, {
        "schema_version": "sapote-mamey.cohort-denominator-registry.v1",
        "scopes": [{
            "scope": "GENERIC_TWO_STRAIN_FIXTURE",
            "strains": 2,
            "regions": 8,
        }],
    })
    return (
        runs,
        cohort_manifest,
        _digest(cohort_manifest),
        denominator_registry,
        _digest(denominator_registry),
    )


def _run_documented_route(
    runs: Path,
    output: Path,
    cohort_manifest: Path,
    cohort_digest: str,
    *extra: str,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["MPLBACKEND"] = "Agg"
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "mamey",
            "cohort-figures",
            "--runs-dir",
            str(runs),
            "--out",
            str(output),
            "--f13-cohort-manifest",
            str(cohort_manifest),
            "--f13-cohort-manifest-sha256",
            cohort_digest,
            "--f13-profile",
            "SINGLE_COLUMN",
            *extra,
        ],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


def test_documented_route_without_denominator_binding_stays_held(tmp_path):
    """Negative control: omission must remain a governed HOLD, never a default."""
    runs, cohort, cohort_digest, _registry, _registry_digest = _governed_cli_fixture(tmp_path)
    output = tmp_path / "held"

    completed = _run_documented_route(runs, output, cohort, cohort_digest)

    assert completed.returncode == 0, completed.stderr
    hold = json.loads((output / "F13_bgc_domain_pca_2d_HOLD.json").read_text())
    assert hold["status"] == "HOLD"
    assert hold["code"] == "DENOMINATOR_UNGOVERNED"
    assert not (output / "F13_bgc_domain_pca_2d.svg").exists()


def test_documented_route_accepts_hash_bound_denominator_and_renders(tmp_path):
    runs, cohort, cohort_digest, registry, registry_digest = _governed_cli_fixture(tmp_path)
    output = tmp_path / "rendered"

    completed = _run_documented_route(
        runs,
        output,
        cohort,
        cohort_digest,
        "--f13-denominator-registry",
        str(registry),
        "--f13-denominator-registry-sha256",
        registry_digest,
    )

    assert completed.returncode == 0, completed.stderr
    assert (output / "F13_bgc_domain_pca_2d.svg").is_file()
    provenance = json.loads(
        (output / "F13_bgc_domain_pca_2d_provenance.json").read_text()
    )
    assert provenance["denominator_policy"] == {
        "registry_filename": "denominators.json",
        "registry_sha256": registry_digest,
        "regions": 8,
        "scope": "GENERIC_TWO_STRAIN_FIXTURE",
        "status": "PASS",
        "strains": 2,
    }
    assert not (output / "F13_bgc_domain_pca_2d_HOLD.json").exists()
