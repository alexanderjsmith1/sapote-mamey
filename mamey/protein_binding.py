"""Bind a BLASTp result or a gene-name row to a gene by its protein sequence, not by its locus tag.

Locus tags (ctgN_M) are numbered per antiSMASH run. A result computed on one run of a genome can carry the tag of a
different gene in another run of the same genome (one case seen: the same tag was 635 aa in the canonical run and 1,574 aa
in an older search). So a row binds to a gene only by evidence about the protein:

  1. protein_sha256: the SHA-256 of the protein sequence searched (upper case, no stop, no whitespace). The row binds to
     every gene of the target genome whose translation has the same SHA-256, whatever its tag.
  2. Without a sha: the row binds to the gene with its own tag only when the protein lengths agree within 1 aa.
  3. Otherwise the row is not bound. It is counted, never guessed.

Identical proteins at several tags all receive the row: the evidence cannot tell them apart, and the name or identity is
the same for each.
"""
from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from pathlib import Path

LENGTH_SLACK_AA = 1
_AS = re.compile(r"^(AS-\d+)")


def protein_sha256(seq: str) -> str:
    """SHA-256 of a protein sequence: upper case, whitespace and a trailing stop removed."""
    s = re.sub(r"\s+", "", seq or "").upper().rstrip("*")
    return hashlib.sha256(s.encode()).hexdigest() if s else ""


def read_fasta(path) -> list[tuple[str, str]]:
    """[(header without '>', sequence)] in file order."""
    out, head, seq = [], None, []
    with open(path, errors="replace") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if line.startswith(">"):
                if head is not None:
                    out.append((head, "".join(seq)))
                head, seq = line[1:].strip(), []
            elif head is not None:
                seq.append(line.strip())
    if head is not None:
        out.append((head, "".join(seq)))
    return out


def norm_strain(s: str) -> str:
    """'AS-<n>_loose' -> 'AS-<n>'; other names unchanged."""
    m = _AS.match((s or "").strip())
    return m.group(1) if m else (s or "").strip()


def tag_of(gene: str) -> str:
    """The locus tag inside a query or result gene id ('SYN-971__BGC011__ctg4_14' -> 'ctg4_14'; 'ctg4_14' unchanged)."""
    return header_key(gene or "")[1]


def header_key(header: str, default_strain: str = "") -> tuple[str, str]:
    """(strain, locus tag) of a saved query FASTA header, in any of the panel formats in use:
    'SYN-973__BGC019__ctg19_74 aa=…', 'SYN-974|BGC063|slot=4|…|gene=ctg87_20|…', 'SYN-975|ctg4_218|541aa', 'SYN-976__ctg18_7',
    'ctg25_47' (strain from default_strain)."""
    hid = header.split()[0] if header.split() else ""
    fields = hid.split("|")
    gene = next((f[5:] for f in fields if f.startswith("gene=")), "")
    if gene:
        return norm_strain(fields[0]) or default_strain, gene
    if "__" in hid:
        parts = hid.split("__")
        return norm_strain(parts[0]) or default_strain, parts[-1]
    if len(fields) > 1:
        tag = next((f for f in fields[1:] if re.fullmatch(r"[A-Za-z0-9.]+_\d+", f)), fields[1])
        return norm_strain(fields[0]) or default_strain, tag
    return default_strain, hid


def genome_index(seq_by_tag: dict[str, str]) -> tuple[dict[str, list[str]], dict[str, int]]:
    """{sha: [tags]} and {tag: aa length} for the genes of the genome being drawn."""
    by_sha, length = {}, {}
    for tag, seq in seq_by_tag.items():
        sha = protein_sha256(seq)
        if sha:
            by_sha.setdefault(sha, []).append(tag)
        length[tag] = len(re.sub(r"\s+", "", seq or "").rstrip("*"))
    return by_sha, length


def bind_one(tag: str, sha: str, query_len, by_sha: dict, length: dict) -> tuple[list[str], str]:
    """-> (genome tags the row binds to, how). how is 'sha', 'length', or the reason it is unbound."""
    if sha:
        tags = by_sha.get(sha.lower(), [])
        return (list(tags), "sha") if tags else ([], "unbound_sha_not_in_genome")
    try:
        parsed = float(query_len)
    except (TypeError, ValueError, OverflowError):
        return [], "unbound_no_sha_no_length"
    # Amino-acid counts are positive integers. Never truncate a fractional
    # value into the one-aa legacy slack or let nonfinite input crash a reader.
    if (isinstance(query_len, bool) or not math.isfinite(parsed)
            or not parsed.is_integer() or parsed <= 0):
        return [], "unbound_invalid_length"
    q = int(parsed)
    if tag not in length:
        return [], "unbound_tag_not_in_genome"
    if abs(length[tag] - q) <= LENGTH_SLACK_AA:
        return [tag], "length"
    return [], "unbound_length_differs"


def bind_name_rows(rows, seq_by_tag: dict[str, str], tag_key: str = "gene", sha_key: str = "protein_sha256",
                   len_key: str = "aa_length") -> tuple[dict, Counter, set]:
    """Rows in priority order -> ({genome tag: first row bound to it}, Counter of how each row bound or why not,
    the tags of rows that did not bind)."""
    by_sha, length = genome_index(seq_by_tag)
    out, how, lost = {}, Counter(), set()
    for r in rows:
        tag = tag_of(r.get(tag_key, ""))
        tags, h = bind_one(tag, (r.get(sha_key) or "").strip(), r.get(len_key), by_sha, length)
        how[h] += 1
        if not tags:
            lost.add(tag)
        for t in tags:
            out.setdefault(t, r)
    return out, how, lost - set(out)


def unbound(how: Counter) -> int:
    return sum(n for k, n in how.items() if k.startswith("unbound"))


def proteins_from_faa(path) -> dict[str, str]:
    """{locus tag: sequence} from a Mamey package <strain>_proteins.faa (headers 'ctg4_14 bgc=BGC011')."""
    return {h.split()[0]: s for h, s in read_fasta(Path(path))}
