"""Content-addressed protein FASTA signatures for assembly and query provenance.

This tool compares sequences and gene labels. It does not admit BLASTp hits:
that requires a receipt tying each submitted query hash to its result.
"""

from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile


SCHEMA = "mamey_protein_signature_v1"
PACKAGE_SCHEMA = "mamey_bgc_protein_package_signature_v1"
_GENE = re.compile(r"(?:^|[|\s])gene=([A-Za-z0-9_.-]+)(?=$|[|\s])")
_AA = re.compile(r"^[A-Z]+$")


class SignatureError(ValueError):
    """Invalid FASTA or ambiguous gene identity."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _gene_label(header: str) -> str:
    match = _GENE.search(header)
    if match:
        return match.group(1)
    token = header.split(None, 1)[0] if header.strip() else ""
    if not token or any(c in token for c in "|="):
        raise SignatureError(f"Cannot identify gene from FASTA header: {header[:100]!r}")
    return token


def read_proteins(path: str | Path) -> tuple[dict[str, str], str]:
    """Read a protein FASTA; uppercase and remove one terminal stop marker."""
    path = Path(path)
    raw = path.read_bytes()
    try:
        lines = raw.decode("ascii").splitlines()
    except UnicodeDecodeError as exc:
        raise SignatureError(f"Protein FASTA is not ASCII: {path}") from exc
    proteins: dict[str, str] = {}
    header: str | None = None
    chunks: list[str] = []

    def add() -> None:
        if header is None:
            return
        gene = _gene_label(header)
        sequence = "".join(chunks).upper()
        if sequence.endswith("*"):
            sequence = sequence[:-1]
        if not sequence or not _AA.fullmatch(sequence):
            raise SignatureError(f"Invalid amino-acid sequence for {gene} in {path}")
        if gene in proteins:
            raise SignatureError(f"Duplicate gene label {gene} in {path}")
        proteins[gene] = sequence

    for line in lines:
        if line.startswith(">"):
            add()
            header = line[1:].strip()
            chunks = []
        elif line.strip():
            if header is None:
                raise SignatureError(f"Sequence before first FASTA header in {path}")
            chunks.append("".join(line.split()))
    add()
    if not proteins:
        raise SignatureError(f"No protein records in {path}")
    return proteins, _sha(raw)


def signature(path: str | Path) -> dict:
    proteins, raw_sha = read_proteins(path)
    records = sorted((gene, _sha(seq.encode("ascii"))) for gene, seq in proteins.items())
    sequence_hashes = sorted(sha for _, sha in records)  # preserves repeated sequences
    return {
        "schema": SCHEMA,
        "path": str(Path(path).resolve()),
        "raw_fasta_sha256": raw_sha,
        "protein_count": len(records),
        "unique_sequence_count": len(set(sequence_hashes)),
        "gene_sequence_signature": _sha(json.dumps(records, separators=(",", ":")).encode()),
        "sequence_multiset_signature": _sha(json.dumps(sequence_hashes, separators=(",", ":")).encode()),
        "records": records,
    }


def package_signature(package_dir: str | Path) -> dict:
    """Describe the existing BGC protein FASTA with exact package locus anchors.

    This is BGC-scoped, not a whole-genome proteome or BLASTp-result receipt.
    """
    package = Path(package_dir)
    manifest_path = package / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SignatureError(f"Cannot read package manifest: {manifest_path}") from exc
    strain = manifest.get("strain_id")
    input_sha = manifest.get("input_zip_sha256")
    if not isinstance(strain, str) or not strain or not isinstance(input_sha, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", input_sha):
        raise SignatureError("Package manifest lacks strain_id or input_zip_sha256")
    manifest_loci = {
        (str(b.get("contig") or ""), str(b.get("antismash_region") or ""), str(b.get("bgc_id") or ""))
        for b in manifest.get("bgcs", []) if isinstance(b, dict)
    }
    if not manifest_loci or any(not all(locus) for locus in manifest_loci):
        raise SignatureError("Package manifest lacks complete BGC identities")
    fasta = package / f"{strain}_proteins.faa"
    cds_path = package / f"{strain}_cds_table.csv"
    proteins, raw_sha = read_proteins(fasta)
    try:
        cds_raw = cds_path.read_bytes()
        reader = csv.DictReader(cds_raw.decode("utf-8-sig").splitlines())
        required = {"strain", "contig", "region", "bgc_id", "locus_tag"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise SignatureError(f"CDS table lacks required identity columns: {cds_path}")
        loci: dict[str, set[tuple[str, str, str]]] = {}
        for row in reader:
            gene = (row.get("locus_tag") or "").strip()
            if gene not in proteins:
                continue
            if (row.get("strain") or "").strip() != strain:
                raise SignatureError(f"CDS strain differs from manifest for {gene}")
            identity = tuple((row.get(key) or "").strip() for key in ("contig", "region", "bgc_id"))
            if not all(identity):
                raise SignatureError(f"Incomplete locus identity for {gene}")
            if identity not in manifest_loci:
                raise SignatureError(f"CDS locus identity differs from manifest for {gene}")
            loci.setdefault(gene, set()).add(identity)
    except UnicodeDecodeError as exc:
        raise SignatureError(f"CDS table is not UTF-8: {cds_path}") from exc
    missing = sorted(set(proteins) - set(loci))
    if missing:
        raise SignatureError(f"{len(missing)} FASTA protein(s) lack complete CDS identity; first: {missing[0]}")
    records = []
    for gene, sequence in sorted(proteins.items()):
        records.append({
            "gene": gene,
            "protein_sha256": _sha(sequence.encode("ascii")),
            "aa_length": len(sequence),
            "loci": [{"strain": strain, "contig": node, "region": region, "bgc_alias": alias}
                     for node, region, alias in sorted(loci[gene])],
        })
    digests = signature(fasta)
    return {
        "schema": PACKAGE_SCHEMA,
        "scope": "BGC_MEMBER_PROTEINS_ONLY",
        "strain_display": strain,
        "input_zip_sha256": input_sha.lower(),
        "manifest_sha256": _sha(manifest_path.read_bytes()),
        "protein_fasta": fasta.name,
        "protein_fasta_sha256": raw_sha,
        "cds_table": cds_path.name,
        "cds_table_sha256": _sha(cds_raw),
        "protein_count": len(records),
        "gene_sequence_signature": digests["gene_sequence_signature"],
        "sequence_multiset_signature": digests["sequence_multiset_signature"],
        "proteins": records,
        "claim_ceiling": "BGC protein and locus provenance only; BLASTp admission requires a result-to-query-hash receipt.",
    }


def compare(left: str | Path, right: str | Path) -> dict:
    a, b = signature(left), signature(right)
    ad, bd = dict(a.pop("records")), dict(b.pop("records"))
    names = set(ad) & set(bd)
    matching = sorted(g for g in names if ad[g] == bd[g])
    changed = sorted(g for g in names if ad[g] != bd[g])
    shared_sequence_count = sum(
        (Counter(ad.values()) & Counter(bd.values())).values()
    )
    if a["gene_sequence_signature"] == b["gene_sequence_signature"]:
        state = "EXACT_GENE_AND_SEQUENCE"
    elif a["sequence_multiset_signature"] == b["sequence_multiset_signature"]:
        state = "SAME_SEQUENCE_MULTISET_RELABELED"
    elif all(bd.get(gene) == sha for gene, sha in ad.items()):
        state = "LEFT_GENE_SEQUENCE_SUBSET"
    elif all(ad.get(gene) == sha for gene, sha in bd.items()):
        state = "RIGHT_GENE_SEQUENCE_SUBSET"
    else:
        state = "PARTIAL_OR_DIFFERENT"
    return {
        "schema": SCHEMA,
        "state": state,
        "left": a,
        "right": b,
        "shared_gene_labels": len(names),
        "same_gene_and_sequence": len(matching),
        "same_gene_changed_sequence": len(changed),
        "shared_sequence_copies": shared_sequence_count,
        "left_only_gene_labels": len(ad) - len(names),
        "right_only_gene_labels": len(bd) - len(names),
        "claim_ceiling": "Protein provenance comparison only; BLASTp admission requires a result-to-query-hash receipt.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("left", nargs="?", help="First protein FASTA for comparison")
    parser.add_argument("right", nargs="?", help="Second protein FASTA for comparison")
    parser.add_argument("--package", help="Export a structured signature for one Mamey package")
    parser.add_argument("--out", required=True, help="New JSON output path")
    args = parser.parse_args(argv)
    out = Path(args.out)
    if out.exists():
        parser.error(f"Output already exists: {out}")
    if bool(args.package) == bool(args.left or args.right):
        parser.error("Provide either --package or two protein FASTAs")
    if not args.package and (not args.left or not args.right):
        parser.error("Comparison requires two protein FASTAs")
    try:
        result = package_signature(args.package) if args.package else compare(args.left, args.right)
    except (OSError, SignatureError) as exc:
        parser.error(str(exc))
    out.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=out.name + ".", suffix=".tmp", dir=out.parent)
    try:
        with os.fdopen(fd, "w") as handle:
            json.dump(result, handle, indent=2)
            handle.write("\n")
        os.replace(temporary, out)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
