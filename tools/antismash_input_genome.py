#!/usr/bin/env python3
"""Write the genome an antiSMASH run was given, as nucleotide FASTA, from its result ZIP.

An antiSMASH result ZIP keeps the submitted genome under ``input/``: a FASTA (``.fna``/``.fasta``/``.fa``/``.fas``)
or a GenBank file (``.gbk``/``.gb``/``.gbff``). A strain whose only local copy is its antiSMASH ZIP therefore still
has its assembly. Use this when a tool or web service needs the genome (TYGS, GTDB-Tk, ANI, GToTree).

Each ZIP gives ``<name>.fasta`` (contig ids kept, 80-column lines), ``<name>`` being the ZIP's file stem, and one
``MANIFEST.tsv`` row: zip, input file, input format, contig count, total length and the FASTA's SHA-256. A ZIP with
no ``input/`` genome, or with more than one, is reported and skipped. An existing FASTA is never overwritten.

For a phylogeny panel, ``tools/build_phylo_panel.py`` already reads an assembly member from an antiSMASH ZIP inside
its own panel workflow; this tool is the standalone route for any other consumer.

Claim safety: the FASTA is the sequence antiSMASH was run on, not a fresh NCBI download. When an analysis needs the
deposited assembly version, check it against the accession.

Usage:
  python tools/antismash_input_genome.py --zip <result.zip> [--zip ...] --out <folder>
  python tools/antismash_input_genome.py --zips-dir <folder of result ZIPs> --out <folder>
"""
from __future__ import annotations

import argparse
import hashlib
import io
import os as _os
import sys as _sys
import zipfile
from pathlib import Path

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from _console import emit  # noqa: E402
from mamey.csv_safety import SafeWriter  # noqa: E402
from mamey.parsers import GbkSizeGuardRefusal, _guarded_read_bytes  # noqa: E402
from mamey.path_safety import assert_output_outside_bundle  # noqa: E402
from mamey.ziputil import regular_file_names  # noqa: E402

FASTA_EXT = (".fna", ".fasta", ".fa", ".fas")
GENBANK_EXT = (".gbk", ".gb", ".gbff")
COLUMNS = ["name", "source_zip", "input_file", "input_format", "contigs", "total_bp", "fasta_sha256", "note"]


def input_member(zf: zipfile.ZipFile) -> tuple[str | None, str]:
    """The single genome file directly under an ``input/`` folder, and a note when there is none or more than one.

    ``regular_file_names`` already drops directories, special entries, ``__MACOSX/`` trees and ``._`` sidecars.
    """
    names = [n for n in regular_file_names(zf)
             if n.split("/")[-2:-1] == ["input"] and n.lower().endswith(FASTA_EXT + GENBANK_EXT)]
    if len(names) == 1:
        return names[0], ""
    return None, ("no input/ genome file" if not names else f"{len(names)} input/ genome files")


def _fasta_records(text: str) -> list[tuple[str, str]]:
    """Plain FASTA reader: (id, sequence) per record, the id being the header's first word, as Biopython gives it."""
    out, rid, parts = [], None, []
    for line in text.splitlines():
        if line.startswith(">"):
            if rid is not None:
                out.append((rid, "".join(parts).upper()))
            rid, parts = (line[1:].split() or [""])[0], []
        elif rid is not None:
            parts.append(line.strip())
    if rid is not None:
        out.append((rid, "".join(parts).upper()))
    return out


def records(data: bytes, member: str) -> tuple[str, list[tuple[str, str]]]:
    """(format, [(id, sequence)]) for one input file.

    Biopython when present. Without it, GenBank goes through the bundle's GBK shim (``mamey._gbk_shim``) and FASTA
    through a plain reader. Only ids and sequences are used, so no rich qualifier is lost.
    """
    fmt = "genbank" if member.lower().endswith(GENBANK_EXT) else "fasta"
    text = data.decode("utf-8", "replace")
    try:
        from Bio import SeqIO
    except ImportError:
        if fmt == "genbank":
            from mamey._gbk_shim import parse_genbank_text
            out = [(r.id, str(r.seq).upper()) for r in parse_genbank_text(text, require_sequence=True)]
        else:
            out = _fasta_records(text)
    else:
        out = [(r.id, str(r.seq).upper()) for r in SeqIO.parse(io.StringIO(text), fmt)]
    # Explicit N bases belong to the submitted assembly. A sequence-less
    # record is different: refuse the file rather than exporting a subset.
    if any(not sequence for _, sequence in out):
        raise ValueError("input genome contains an empty sequence record")
    return fmt, out


def extract(zip_path: Path, out: Path) -> list:
    """Write one ZIP's input genome as ``<stem>.fasta``; return its manifest row."""
    name = zip_path.stem
    with zipfile.ZipFile(zip_path) as zf:
        member, note = input_member(zf)
        if member is None:
            return [name, zip_path.name, "", "", 0, 0, "", note]
        try:
            data = _guarded_read_bytes(zf, member)
        except GbkSizeGuardRefusal as exc:
            return [name, zip_path.name, member, "", 0, 0, "", f"refused by size guard: {exc}"]
    try:
        fmt, recs = records(data, member)
    except ValueError as exc:  # Biopython UndefinedSequenceError, GBK_SHIM_NO_SEQUENCE, malformed FASTA/GenBank
        return [name, zip_path.name, member, "", 0, 0, "", f"unreadable input file: {exc}"]
    if not recs:
        return [name, zip_path.name, member, fmt, 0, 0, "", "input file has no sequence"]
    total = sum(len(s) for _, s in recs)
    dst = out / f"{name}.fasta"
    if dst.exists():
        return [name, zip_path.name, member, fmt, len(recs), total, "", "exists; not overwritten"]
    with open(dst, "x", encoding="ascii") as fh:
        for rid, seq in recs:
            fh.write(f">{rid}\n" + "\n".join(seq[i:i + 80] for i in range(0, len(seq), 80)) + "\n")
    return [name, zip_path.name, member, fmt, len(recs), total, hashlib.sha256(dst.read_bytes()).hexdigest(), ""]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--zip", action="append", default=[], help="antiSMASH result ZIP (repeatable)")
    ap.add_argument("--zips-dir", help="folder of antiSMASH result ZIPs (every *.zip in it)")
    ap.add_argument("--out", required=True, help="output folder for <name>.fasta and MANIFEST.tsv")
    a = ap.parse_args(argv)
    zips = [Path(z) for z in a.zip] + (sorted(Path(a.zips_dir).glob("*.zip")) if a.zips_dir else [])
    if not zips:
        ap.error("give --zip or --zips-dir")
    out = assert_output_outside_bundle(Path(a.out), __file__)
    out.mkdir(parents=True, exist_ok=True)
    rows = [extract(z, out) for z in zips]
    man = out / "MANIFEST.tsv"
    new = not man.exists()
    with open(man, "a", newline="", encoding="utf-8") as fh:
        w = SafeWriter(fh, delimiter="\t", lineterminator="\n")
        if new:
            w.writerow(COLUMNS)
        w.writerows(rows)
    done = sum(1 for r in rows if r[6])
    lines = [f"[antismash_input_genome] {r[0]}: {r[7]}" for r in rows if r[7]]
    emit("\n".join(lines + [f"[antismash_input_genome] {done} of {len(rows)} FASTA written -> {out}"]))
    return 0 if done == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
