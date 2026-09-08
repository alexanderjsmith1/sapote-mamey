#!/usr/bin/env python3
"""external_data.py — resolve USER-PROVISIONED third-party datasets. Nothing here is redistributed.

Why this exists
---------------
Sapote-Mamey is MIT-licensed CODE. Third-party reference datasets carry their own licences and their
own citation requirements, and several of them (publisher abstracts in particular) are simply not ours
to redistribute. Bundling them also made the release 34% third-party data by size and silently coupled
the bundle to one frozen snapshot of a database that upstream keeps updating.

So the bundle now ships the CODE that consumes these datasets, plus a documented contract for where to
put them. The operator downloads the real thing from upstream, once, and points the engine at it.

Resolution order (first hit wins), per dataset:
  1. the dataset's own env var          e.g. MAMEY_MIBIG_DIR
  2. <MAMEY_DATA_ROOT>/<default subdir> (the .352 H1 convention, one root for everything)
  3. the in-tree legacy path            only if it still exists (pre-.362 trees; never shipped now)

Every accessor FAILS LOUD and ACTIONABLE when a dataset is absent: a `MissingExternalData` naming the
dataset, the env var, the expected layout and the upstream URL. Callers that can legitimately degrade
(the literature enrichment is optional) use `optional=True` and get None instead — but they must then
render NOT MEASURED, never an empty result that reads like a measured zero.

See docs/EXTERNAL_DATA.md for the per-dataset licence, size and download instructions.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

__all__ = ["DATASETS", "MissingExternalData", "resolve", "require", "status", "Dataset"]


class MissingExternalData(RuntimeError):
    """Raised when a required user-provisioned dataset is not present."""


@dataclass(frozen=True)
class Dataset:
    key: str
    env_var: str
    default_subdir: str
    legacy_path: str          # where it used to ship in-tree (<= v9.7.361)
    probe: str                # a relative path that must exist for the dataset to count as present
    upstream: str
    licence: str
    approx_size: str
    what: str


DATASETS: dict[str, Dataset] = {
    "mibig": Dataset(
        key="mibig",
        env_var="MAMEY_MIBIG_DIR",
        default_subdir="mibig",
        legacy_path="mamey/data/mibig",
        probe="mibig_reference_index.bacterial.json",
        upstream="https://mibig.secondarymetabolites.org/download",
        licence="MIBiG data are CC BY 4.0 — attribution required; redistribution inside an MIT bundle "
                "misrepresents the licence. Download the release you intend to cite.",
        approx_size="~2.3 MB index (full GenBank release is much larger)",
        what="MIBiG reference index + antimicrobial neighborhood partitions",
    ),
    "mibig_neighborhoods": Dataset(
        key="mibig_neighborhoods",
        env_var="MAMEY_MIBIG_NEIGHBORHOODS_DIR",
        default_subdir="mibig/neighborhoods",
        legacy_path="mamey/data/mibig/neighborhoods",
        probe="PROVENANCE.md",
        upstream="derived from MIBiG; rebuild with tools/mibig_neighborhoods.py --faa <MIBiG_<FAM>.faa> --fam <FAM> --thresh 1.5",
        licence="Derived from MIBiG (CC BY 4.0). Rebuildable locally — deterministic given the same "
                "panel + MUSCLE/FastTree versions (see PROVENANCE.md).",
        approx_size="~0.1 MB",
        what="KS/AT/C/A/glyc/resi neighborhood partitions + medoid representatives",
    ),
    "literature": Dataset(
        key="literature",
        env_var="MAMEY_LITERATURE_CORPUS",
        default_subdir="literature",
        legacy_path="mamey/data/literature/_corpus",
        probe="literature_corpus.jsonl",
        upstream="build locally with mamey/data/literature/_corpus/pubmed_ingest.py (NCBI E-utilities)",
        licence="PubMed RECORDS are US-Government-funded metadata, but ABSTRACTS are copyrighted by "
                "their publishers and are NOT redistributable. Build the corpus locally from "
                "E-utilities under your own institutional access.",
        approx_size="~10.8 MB for ~7.6k records",
        what="PMID/DOI/title/abstract corpus for §5 literature enrichment",
    ),
    "hmm": Dataset(
        key="hmm",
        env_var="MAMEY_HMM_DIR",
        default_subdir="hmm",
        legacy_path="Wheelhouse/hmm",
        probe="scanner_pfam.hmm",
        upstream="https://www.ebi.ac.uk/interpro/download/pfam/",
        licence="Pfam is CC0, but the profile set is large, versioned, and upstream-maintained — pin "
                "the Pfam release you cite rather than freezing a copy in a code release.",
        approx_size="~4.4 MB (subset) / much larger for full Pfam-A",
        what="Pfam profile HMMs for the biosynthetic domain scanner",
    ),
    # Codex .363 review finding (2026-08-12): OFFICIAL_DATA is a GOVERNANCE input — it sets the
    # governed denominator — yet exclusions.py resolves it by walking UP from the bundle and is SILENT
    # on success, so the same sealed engine reports a different denominator depending on where it was
    # extracted. Registering it here makes the resolution explicit and puts it in `mamey doctor`, so an
    # operator can see which denominator is in force BEFORE generating a governed claim.
    "official_data": Dataset(
        key="official_data",
        env_var="MAMEY_OFFICIAL_DATA",
        default_subdir="OFFICIAL_DATA",
        legacy_path="OFFICIAL_DATA",
        probe="exclusions.json",
        upstream="workspace governance record — authored by the release owner, not downloaded",
        licence="Project governance data. Not third-party; not redistributed. The in-module _DEFAULT "
                "mirrors it verbatim so behaviour is deterministic when it is absent.",
        approx_size="< 1 MB",
        what="governed denominator + exclusion SSOT (exclusions.json / EXCLUSIONS.md)",
    ),
    "npatlas": Dataset(
        key="npatlas",
        env_var="MAMEY_NPATLAS_DIR",
        default_subdir="npatlas",
        legacy_path="",           # never shipped in-tree
        probe="np_atlas.json",
        upstream="https://www.npatlas.org/download",
        # NPA-02 (v9.7.405): the official v2024_09 download page (https://www.npatlas.org/download)
        # states CC BY-NC 4.0, not CC BY 4.0 -- this string previously understated the noncommercial
        # restriction. Corrected; carry this exact licence text into any receipt an NP Atlas adapter
        # emits (see mamey/npatlas_provision.py). Never redistribute the actual database.
        licence="NP Atlas is CC BY-NC 4.0 (noncommercial) — attribution required, download directly "
                "from https://www.npatlas.org/download; do not redistribute.",
        approx_size="~50-200 MB depending on release (official full JSON is ~475 MB)",
        what="Natural-product structure database for dereplication (optional; not previously bundled)",
    ),
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def resolve(key: str) -> Path | None:
    """Return the directory for `key`, or None if not provisioned. Never raises for an unknown layout."""
    ds = DATASETS.get(key)
    if ds is None:
        raise ValueError(f"unknown dataset {key!r}; known: {sorted(DATASETS)}")

    env = os.environ.get(ds.env_var)
    if env:
        p = Path(env).expanduser()
        if (p / ds.probe).exists():
            return p

    root = os.environ.get("MAMEY_DATA_ROOT")
    if root:
        p = Path(root).expanduser() / ds.default_subdir
        if (p / ds.probe).exists():
            return p

    if ds.legacy_path:
        p = _repo_root() / ds.legacy_path
        if (p / ds.probe).exists():
            return p

    return None


def require(key: str) -> Path:
    """Resolve or raise a MissingExternalData carrying actionable provisioning instructions."""
    p = resolve(key)
    if p is not None:
        return p
    ds = DATASETS[key]
    raise MissingExternalData(
        f"external dataset {ds.key!r} is not provisioned ({ds.what}).\n"
        f"  This bundle does NOT redistribute it. {ds.licence}\n"
        f"  Obtain it from: {ds.upstream}   (size: {ds.approx_size})\n"
        f"  Then point the engine at it, either:\n"
        f"     export {ds.env_var}=/path/to/{ds.key}\n"
        f"  or place it at $MAMEY_DATA_ROOT/{ds.default_subdir}/ (must contain {ds.probe!r}).\n"
        f"  See docs/EXTERNAL_DATA.md."
    )


def status() -> dict[str, dict]:
    """{key: {...}} provisioning report — powers `mamey doctor` and the operator-facing check."""
    out = {}
    for key, ds in DATASETS.items():
        p = resolve(key)
        out[key] = {
            "provisioned": p is not None,
            "path": str(p) if p else None,
            "env_var": ds.env_var,
            "what": ds.what,
            "upstream": ds.upstream,
            "licence": ds.licence,
        }
    return out
