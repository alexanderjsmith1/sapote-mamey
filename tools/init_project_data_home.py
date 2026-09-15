#!/usr/bin/env python3
"""Create a portable, pointer-first scientific project data home."""
from __future__ import annotations
import argparse, csv, json, os
from pathlib import Path
import sys
# Keep direct script execution bound to this source tree.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mamey.csv_safety import SafeDictWriter, SafeWriter

from tempfile import NamedTemporaryFile

DIRS = (
    "00_INBOX", "01_AUTHORITY", "02_STRAINS", "03_PHYLOGENY", "04_GENOMICS",
    "05_BIOASSAYS", "06_CITATIONS", "07_MANUSCRIPTS", "08_DELIVERABLES", "09_SUPERSEDED",
)
REGISTERS = {
    "01_AUTHORITY/AUTHORITY_INDEX.tsv": ("artifact_id", "role", "locator", "sha256", "authority", "status", "notes"),
    "02_STRAINS/GENOME_REGISTER.tsv": ("strain_id", "assembly_id", "organism", "locator", "sha256", "metadata_status", "authority", "notes"),
    "03_PHYLOGENY/PHYLOGENY_REGISTER.tsv": ("analysis_id", "method", "version", "input_manifest", "output_locator", "status", "notes"),
    "04_GENOMICS/ANTISMASH_REGISTER.tsv": ("strain_id", "antismash_version", "locator", "sha256", "status", "notes"),
    "04_GENOMICS/MAMEY_PACKAGE_REGISTER.tsv": ("strain_id", "bundle_version", "engine_version", "locator", "manifest_sha256", "status", "notes"),
    "05_BIOASSAYS/BIOASSAY_REGISTER.tsv": ("dataset_id", "assay", "locator", "sha256", "authority", "status", "notes"),
    "06_CITATIONS/CITATION_REGISTER.tsv": ("citation_id", "locator", "doi_or_accession", "status", "notes"),
    "07_MANUSCRIPTS/MANUSCRIPT_REGISTER.tsv": ("document_id", "locator", "sha256", "status", "notes"),
    "08_DELIVERABLES/DELIVERABLE_REGISTER.tsv": ("artifact_id", "locator", "sha256", "status", "notes"),
}

def _write_tsv(path: Path, header: tuple[str, ...]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        SafeWriter(handle, delimiter="\t", lineterminator="\n").writerow(header)

def create_home(root: Path, project_id: str) -> None:
    root = root.expanduser().resolve()
    if root.exists():
        raise FileExistsError(f"refusing existing target: {root}")
    root.mkdir(parents=True)
    try:
        for name in DIRS: (root/name).mkdir()
        for rel, header in REGISTERS.items(): _write_tsv(root/rel, header)
        (root/"PROJECT_HOME.json").write_text(json.dumps({
            "schema_version": 1, "project_id": project_id,
            "storage_model": "pointer-first", "status": "INITIALIZED",
            "portable_locator_policy": "Use relative, logical, or configurable locators; do not hardcode developer workspace paths.",
        }, indent=2)+"\n", encoding="utf-8")
        (root/"README.md").write_text(f"""# {project_id} project data home

This pointer-first home indexes genomes, antiSMASH results, Mamey packages, phylogeny inputs and outputs, bioassays, citations, manuscripts, and deliverables without copying large evidence stores.

Add an artifact only after recording its locator, checksum when available, authority, and status in the matching register. Keep superseded material under `09_SUPERSEDED` with a pointer to its replacement. Scientific admission and release authority remain separate from storage.
""", encoding="utf-8")
    except Exception:
        import shutil
        shutil.rmtree(root, ignore_errors=True)
        raise

def main(argv=None) -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--root", required=True, type=Path)
    p.add_argument("--project-id", required=True)
    a=p.parse_args(argv)
    create_home(a.root, a.project_id)
    print(a.root.expanduser().resolve())
    return 0

if __name__ == "__main__": raise SystemExit(main())
