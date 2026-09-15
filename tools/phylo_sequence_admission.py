#!/usr/bin/env python3
"""Fail-closed admission gate for 16S placement and whole-genome tree inputs.

This gate validates scientific input identity before inference.  It does not fetch
records or infer missing metadata.  A successful result means the supplied roster,
FASTA and evidence fields agree mechanically; it is not a taxonomic conclusion.
"""
from __future__ import annotations

import argparse, csv, hashlib, json, re
from collections import defaultdict
from pathlib import Path

ROLES = {"query", "reference", "outgroup"}
TYPE_STATUS = {"type", "non_type", "not_applicable"}
GEOGRAPHY = {"US", "Canada", "North America (other)", "South America", "Europe",
             "Asia", "Africa", "Oceania", "Antarctica", "Indian Ocean"}
MISSING = {"", "na", "n/a", "not applicable", "not recorded", "unknown", "unverified"}
REQUIRED = {"tip", "role", "organism", "expected_genus", "accession", "sequence_sha256",
            "type_status", "isolation_source", "geography", "sequence_evidence",
            "metadata_evidence", "biological_sample_id", "admission"}


def _missing(value: str | None) -> bool:
    return (value or "").strip().lower() in MISSING


def _canonical(sequence: str) -> str:
    """The canonical stored form: upper-case, U->T, and BOTH gap characters removed.

    v9.7.430: `.` was not stripped here while `-` was, so a dot-gapped FASTA (MUSCLE/Clustal and
    several aligned reference formats emit `.`) kept its dots in the stored sequence even though the
    symbol validator below explicitly admits `.`. Two consequences, both measurable:

      * `validate()` measures `len(seq)`, so a 1990-base query arriving with 100 `.` placeholders
        was rejected as `SEQUENCE_LENGTH: tip length=2090`; the converse (a short sequence padded
        with dots into the accepted window) was also reachable.
      * `sequence_sha256` is computed over THIS string, so the same biological sequence hashed
        differently depending on which gap character its alignment used.

    The bundle's own convention was already ungapped and is not being changed here, only applied
    consistently: `tools/_phylo16s.py::screen_query_records` strips both (`seq.replace("-", "")
    .replace(".", "")`, line 51) under the docstring "Lengths exclude gap punctuation".

    HASH SEMANTICS, stated so the next reader does not have to re-derive them. There are two
    different sha256 species in this area and they bind different things:
      * `sequence_sha256` (this module, validate()) binds the NORMALIZED UNGAPPED sequence — a
        biological identity that must not change when an alignment is re-gapped.
      * the `sha256` bindings in `tools/tree_series_contract.py` bind RAW FILE BYTES — a provenance
        identity that must change when the file changes at all.
    Neither is wrong; they answer different questions. This change makes the first one actually
    behave as described for dot-gapped input.
    """
    return sequence.upper().replace("U", "T").replace("-", "").replace(".", "")


def read_fasta(path: Path) -> dict[str, str]:
    records, name, parts = {}, None, []
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith(">"):
            if name is not None:
                records[name] = _canonical("".join(parts))
            name = line[1:].split()[0]
            if not name or name in records:
                raise ValueError("FASTA_IDENTITY: empty or duplicate header")
            parts = []
        else:
            if name is None:
                raise ValueError("FASTA_FORMAT: sequence before first header")
            seq = re.sub(r"\s+", "", line).upper()
            if not re.fullmatch(r"[ACGTURYSWKMBDHVN.-]+", seq):
                raise ValueError(f"FASTA_SYMBOL: {name}")
            parts.append(seq)
    if name is not None:
        records[name] = _canonical("".join(parts))
    if not records:
        raise ValueError("FASTA_EMPTY: no sequence records")
    return records


def validate(rows, sequences, *, molecule="16S", min_length=900, max_length=2000):
    rows = list(rows)
    if not rows:
        raise ValueError("ROSTER_EMPTY: no admission rows")
    missing_cols = REQUIRED - set(rows[0])
    if missing_cols:
        raise ValueError("ROSTER_COLUMNS: " + ",".join(sorted(missing_cols)))
    tips, species_types, seq_groups, sample_seq = set(), defaultdict(list), defaultdict(list), defaultdict(list)
    for line, row in enumerate(rows, 2):
        tip = row["tip"].strip()
        role = row["role"].strip().lower()
        if not tip or tip in tips:
            raise ValueError(f"TIP_IDENTITY: row {line}")
        tips.add(tip)
        if role not in ROLES:
            raise ValueError(f"ROLE: {tip}")
        if row["admission"].strip().lower() != "admitted":
            raise ValueError(f"NOT_ADMITTED: {tip}")
        organism = row["organism"].strip()
        genus = organism.split()[0] if organism else ""
        expected = row["expected_genus"].strip()
        if not expected or genus.casefold() != expected.casefold():
            raise ValueError(f"GENUS_CONTRADICTION: {tip} observed={genus} expected={expected}")
        for field in ("accession", "isolation_source", "geography", "sequence_evidence", "metadata_evidence"):
            if _missing(row[field]):
                raise ValueError(f"METADATA_INCOMPLETE: {tip} field={field}")
        if row["geography"].strip() not in GEOGRAPHY:
            raise ValueError(f"GEOGRAPHY_VOCABULARY: {tip} value={row['geography']}")
        status = row["type_status"].strip().lower()
        if status not in TYPE_STATUS or (role in {"reference", "outgroup"} and status == "not_applicable"):
            raise ValueError(f"TYPE_STATUS: {tip}")
        if tip not in sequences:
            raise ValueError(f"SEQUENCE_MISSING: {tip}")
        seq = sequences[tip]
        digest = hashlib.sha256(seq.encode("ascii")).hexdigest()
        if digest != row["sequence_sha256"].strip().lower():
            raise ValueError(f"SEQUENCE_HASH: {tip}")
        if molecule == "16S" and not min_length <= len(seq) <= max_length:
            raise ValueError(f"SEQUENCE_LENGTH: {tip} length={len(seq)}")
        seq_groups[digest].append((tip, role, row["biological_sample_id"].strip()))
        if role == "query":
            if _missing(row["biological_sample_id"]):
                raise ValueError(f"SAMPLE_ID_MISSING: {tip}")
            sample_seq[row["biological_sample_id"].strip()].append((tip, digest))
        if status == "type":
            tokens = organism.split()
            if len(tokens) < 2 or tokens[1].lower() in {"sp.", "sp", "spp."}:
                raise ValueError(f"TYPE_SPECIES_UNRESOLVED: {tip}")
            species_types[" ".join(tokens[:2]).casefold()].append(tip)
    if set(sequences) != tips:
        raise ValueError("ROSTER_FASTA_MISMATCH")
    duplicated_types = {k:v for k,v in species_types.items() if len(v) > 1}
    if duplicated_types:
        raise ValueError("DUPLICATE_TYPE_REPRESENTATIVE: " + json.dumps(duplicated_types, sort_keys=True))
    same_sample = {s:[t for t,_ in vals] for s,vals in sample_seq.items()
                   if len(vals) > 1 and len({h for _,h in vals}) == 1}
    if same_sample:
        raise ValueError("DUPLICATE_QUERY_SAME_SAMPLE_SEQUENCE: " + json.dumps(same_sample, sort_keys=True))
    exact = {h:[t for t,_,_ in vals] for h,vals in seq_groups.items() if len(vals) > 1}
    return {"status":"ADMISSION_PASS", "rows":len(rows), "molecule":molecule,
            "exact_sequence_groups":exact,
            "ceiling":"Mechanical admission only; taxonomy and metadata remain source-dependent."}


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("--roster", required=True); p.add_argument("--fasta", required=True)
    p.add_argument("--molecule", choices=("16S","genome"), default="16S")
    p.add_argument("--min-length", type=int, default=900); p.add_argument("--max-length", type=int, default=2000)
    p.add_argument("--json")
    a=p.parse_args(argv)
    with open(a.roster, newline="", encoding="utf-8-sig") as h:
        rows=list(csv.DictReader(h, delimiter="\t"))
    result=validate(rows, read_fasta(Path(a.fasta)), molecule=a.molecule,
                    min_length=a.min_length, max_length=a.max_length)
    text=json.dumps(result, indent=2, sort_keys=True)+"\n"
    if a.json: Path(a.json).write_text(text, encoding="utf-8")
    print(text, end="")
    return 0

if __name__ == "__main__": raise SystemExit(main())
