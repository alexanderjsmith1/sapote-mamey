#!/usr/bin/env python3
"""Offer a five-locus MLSA screen from a verified antiSMASH assembly.

The antiSMASH ZIP is an input container, not itself a genome FASTA. This tool
admits one full-assembly FASTA member, or full-assembly GenBank records when no
FASTA exists. Clipped region records are never promoted to a whole genome.
Reference acquisition and the later GToTree run remain separate decisions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from mamey.parsers import _guarded_read_bytes, read_genbank_records
from mamey.ziputil import duplicate_member_names, regular_file_names


DNA = set("ACGTRYSWKMBDHVN")
LABEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
FASTA_EXT = (".fna", ".fasta", ".fa")
GBK_EXT = (".gbk", ".gbff", ".gb")
ROOT = Path(__file__).resolve().parent.parent


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fasta_records(data: bytes, source: str) -> list[tuple[str, str]]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"ASSEMBLY_FASTA_INVALID: {source}: non-UTF-8 data") from exc
    records: list[tuple[str, str]] = []
    current: str | None = None
    pieces: list[str] = []
    seen: set[str] = set()

    def finish() -> None:
        if current is None:
            return
        seq = "".join(pieces).upper()
        if not seq or set(seq) - DNA:
            raise ValueError(f"ASSEMBLY_FASTA_INVALID: {source}: empty or non-DNA sequence")
        records.append((current, seq))

    for line in text.splitlines():
        if line.startswith(">"):
            finish()
            tokens = line[1:].split()
            if not tokens or not LABEL.fullmatch(tokens[0]) or tokens[0] in seen:
                raise ValueError(f"ASSEMBLY_FASTA_INVALID: {source}: unsafe or duplicate contig ID")
            current = tokens[0]
            seen.add(current)
            pieces = []
        elif line.strip():
            if current is None or any(c.isspace() for c in line.strip()):
                raise ValueError(f"ASSEMBLY_FASTA_INVALID: {source}: sequence before header or embedded whitespace")
            pieces.append(line.strip())
    finish()
    if not records:
        raise ValueError(f"ASSEMBLY_FASTA_INVALID: {source}: no records")
    return records


def assembly_from_zip(path: Path, *, member: str | None = None,
                      min_bp: int = 1_000_000) -> dict:
    """Return source-bound full assembly records; fail closed on region-only ZIPs."""
    if min_bp <= 0:
        raise ValueError("min_bp must be positive")
    if not path.is_file():
        raise ValueError("antiSMASH ZIP does not exist")
    try:
        with zipfile.ZipFile(path) as zf:
            duplicates = duplicate_member_names(zf)
            if duplicates:
                raise ValueError("AMBIGUOUS_ANTISMASH_ZIP: duplicate member name")
            names = sorted(regular_file_names(zf))
            full_fasta = [n for n in names if n.lower().endswith(FASTA_EXT)
                          and "region" not in Path(n).name.lower()]
            full_gbk = [n for n in names if n.lower().endswith(GBK_EXT)
                        and "region" not in Path(n).name.lower()]
            if member is not None:
                if member not in full_fasta and member not in full_gbk:
                    raise ValueError("ASSEMBLY_MEMBER_NOT_FULL: selected member is absent or region-scoped")
                chosen = [member]
            elif full_fasta:
                if len(full_fasta) != 1:
                    raise ValueError("AMBIGUOUS_ASSEMBLY_FASTA: specify --assembly-member")
                chosen = full_fasta
            else:
                chosen = full_gbk
            if not chosen:
                raise ValueError("NO_FULL_ASSEMBLY: antiSMASH ZIP has no full-assembly FASTA or GenBank record")
            if all(n.lower().endswith(FASTA_EXT) for n in chosen):
                records = fasta_records(_guarded_read_bytes(zf, chosen[0]), chosen[0])
            else:
                # The existing parser has bounded GenBank reads. Require every
                # selected full-assembly member to yield at least one record.
                parsed = read_genbank_records(path, exclude_regions=True)
                by_name: dict[str, list[tuple[str, str]]] = {n: [] for n in chosen}
                for name, record in parsed:
                    if name not in by_name:
                        continue
                    contig = str(record.id).split()[0]
                    seq = str(record.seq).upper()
                    if not LABEL.fullmatch(contig) or not seq or set(seq) - DNA:
                        raise ValueError("ASSEMBLY_GENBANK_INVALID: unsafe contig ID or sequence")
                    by_name[name].append((contig, seq))
                if any(not rows for rows in by_name.values()):
                    raise ValueError("ASSEMBLY_GENBANK_INCOMPLETE: a full-assembly member did not parse")
                records = [row for n in chosen for row in by_name[n]]
    except zipfile.BadZipFile as exc:
        raise ValueError("ANTISMASH_ZIP_INVALID: not a readable ZIP") from exc
    ids = [name for name, _ in records]
    if len(set(ids)) != len(ids):
        raise ValueError("ASSEMBLY_CONTIG_DUPLICATE: full records reuse a contig ID")
    total_bp = sum(len(seq) for _, seq in records)
    if total_bp < min_bp:
        raise ValueError(f"ASSEMBLY_TOO_SHORT: {total_bp} bp below --min-bp {min_bp}")
    content = "".join(
        f">{name}\n" + "\n".join(seq[i:i + 80] for i in range(0, len(seq), 80)) + "\n"
        for name, seq in records
    ).encode("ascii")
    return {
        "members": chosen,
        "records": records,
        "total_bp": total_bp,
        "fasta_bytes": content,
        "fasta_sha256": sha256(content),
        "source_zip_sha256": file_sha256(path),
    }


def reference_roster(directory: Path | None, query_sha: str) -> list[tuple[Path, str]]:
    if directory is None:
        return []
    if not directory.is_dir():
        raise ValueError("REFERENCE_DIR_MISSING: provide a directory of local .fna genomes")
    refs = sorted(directory.glob("*.fna"))
    if not refs:
        raise ValueError("REFERENCE_DIR_EMPTY: no .fna genomes")
    roster = []
    seen_content = {query_sha}
    seen_names: set[str] = set()
    for path in refs:
        if not path.is_file() or not LABEL.fullmatch(path.stem):
            raise ValueError("REFERENCE_INVALID: each .fna must be a regular file with a safe basename")
        key = path.name.casefold()
        data = path.read_bytes()
        fasta_records(data, path.name)
        digest = sha256(data)
        if key in seen_names or digest in seen_content:
            raise ValueError("REFERENCE_DUPLICATE: name or content duplicates another genome")
        seen_names.add(key)
        seen_content.add(digest)
        roster.append((path, digest))
    return roster


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    ap.add_argument("--input-zip", required=True, type=Path)
    ap.add_argument("--query-label", required=True)
    ap.add_argument("--references-dir", type=Path)
    ap.add_argument("--outdir", type=Path)
    ap.add_argument("--assembly-member", default=None)
    ap.add_argument("--min-bp", type=int, default=1_000_000)
    ap.add_argument("--mode", choices=("plan", "prepare", "run"), default="plan")
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--bin-dir", type=Path)
    args = ap.parse_args(argv)
    if not LABEL.fullmatch(args.query_label) or args.threads <= 0:
        ap.error("query label must be filename-safe and threads positive")
    if args.mode != "plan" and args.outdir is None:
        ap.error("--outdir is required for prepare/run")
    if args.mode == "run" and args.references_dir is None:
        ap.error("--references-dir is required for run")
    try:
        assembly = assembly_from_zip(args.input_zip, member=args.assembly_member,
                                     min_bp=args.min_bp)
        refs = reference_roster(args.references_dir, assembly["fasta_sha256"])
        if any(p.stem.casefold() == args.query_label.casefold() for p, _ in refs):
            raise ValueError("QUERY_REFERENCE_NAME_COLLISION: query label matches a reference")
        if args.mode == "run" and (len(refs) < 2 or sum("OUTGROUP" in p.stem.upper() for p, _ in refs) != 1):
            raise ValueError("MLSA_PANEL_INCOMPLETE: run requires at least two references and one named _OUTGROUP")
        plan = {
            "schema": "mamey.phylo_mlsa_antismash.v1",
            "mode": args.mode,
            "query_label": args.query_label,
            "input_zip_name": args.input_zip.name,
            "input_zip_sha256": assembly["source_zip_sha256"],
            "assembly_members": assembly["members"],
            "assembly_scope": "NON_REGION_SEQUENCE_MEMBER; completeness requires user review",
            "query_contigs": len(assembly["records"]),
            "query_bp": assembly["total_bp"],
            "query_fasta_sha256": assembly["fasta_sha256"],
            "references": [{"name": p.name, "sha256": h} for p, h in refs],
            "claim_ceiling": "MLSA is a comparator screen, not species identity; core-genome inference and ANI are separate.",
        }
        if args.mode == "plan":
            sys.stdout.write(json.dumps(plan, indent=2) + "\n")
            return 0
        out = args.outdir.resolve()
        if out.exists() and (not out.is_dir() or any(out.iterdir())):
            raise ValueError("OUTPUT_NOT_EMPTY: use a new or empty output directory")
        if args.references_dir is not None and out.is_relative_to(args.references_dir.resolve()):
            raise ValueError("OUTPUT_WITHIN_REFERENCES: choose a distinct output directory")
        genomes = out / "genomes"
        genomes.mkdir(parents=True, exist_ok=True)
        query = genomes / f"{args.query_label}.fna"
        query.write_bytes(assembly["fasta_bytes"])
        for source, digest in refs:
            dest = genomes / source.name
            shutil.copyfile(source, dest)
            if sha256(dest.read_bytes()) != digest:
                raise ValueError("REFERENCE_CHANGED_DURING_STAGE: staged hash mismatch")
        if file_sha256(args.input_zip) != assembly["source_zip_sha256"]:
            raise ValueError("ANTISMASH_INPUT_CHANGED_DURING_STAGE")
        plan["status"] = "PREPARED"
        plan["genomes_dir"] = "genomes"
        receipt = out / "mlsa_antismash_receipt.json"
        if args.mode == "run":
            cmd = [sys.executable, str(ROOT / "tools/build_mlsa.py"), str(genomes),
                   str(out / "mlsa"), "--threads", str(args.threads)]
            if args.bin_dir is not None:
                cmd += ["--bin-dir", str(args.bin_dir)]
            plan["status"] = "RUNNING"
            receipt.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
            try:
                completed = subprocess.run(cmd, check=False)
            except OSError as exc:
                plan["status"] = "MLSA_LAUNCH_FAILED"
                plan["launch_error"] = f"{type(exc).__name__}: {exc}"
                receipt.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
                raise ValueError("MLSA_LAUNCH_FAILED: see receipt for the retained error") from exc
            tree = out / "mlsa/tree.treefile"
            plan["status"] = ("COMPLETE" if completed.returncode == 0
                              and tree.is_file() and tree.stat().st_size else "MLSA_FAILED")
            plan["mlsa_exit_code"] = completed.returncode
            plan["mlsa_tree"] = "mlsa/tree.treefile" if plan["status"] == "COMPLETE" else None
            plan["mlsa_tree_sha256"] = file_sha256(tree) if plan["status"] == "COMPLETE" else None
        receipt.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
        sys.stdout.write(str(receipt) + "\n")
        return 0 if plan["status"] in ("PREPARED", "COMPLETE") else 1
    except (ValueError, OSError, zipfile.BadZipFile) as exc:
        sys.stderr.write(f"phylo-mlsa: {exc}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
