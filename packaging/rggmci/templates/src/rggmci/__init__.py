"""RG-GMCI: reference-guided linkage candidates for fragmented antiSMASH assemblies.

A homology-guided candidate-linkage method, not a physical contig joiner. A linked pair is a
hypothesis to check at gene level, not evidence that two fragments are one pathway.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .core import compute_rggmci, parse_clusterblast_reference_map, run_rggmci, run_archive  # noqa: F401


def _provenance() -> dict[str, Any]:
    import json
    from importlib import resources
    try:
        return json.loads(resources.files(__package__).joinpath("PROVENANCE.json").read_text())
    except (FileNotFoundError, ValueError, OSError):
        return {}


__version__ = _provenance().get("package_version", "unknown")
from .groups import both_at_contig_ends, candidate_groups
from .reader import read_regions


def run(zip_path: str | Path, **options: Any) -> dict[str, Any]:
    """Use the shared actual program path, including automatic archive sequence context.

    Explicit contigs=None retains unavailable-context semantics. Distribution
    provenance lives in wrapper_context; scientific data/config are common.
    """
    if "core_snapshot" in options:
        raise ValueError("RGGMCI_PUBLIC_SNAPSHOT_OVERRIDE_REFUSED")
    result = run_archive(zip_path, **options)
    result.setdefault("wrapper_context", {}).update(distribution="rggmci", provenance=_provenance())
    return result
