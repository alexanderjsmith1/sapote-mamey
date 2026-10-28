#!/usr/bin/env python3
"""Fail-closed admission gate for 16S placement and whole-genome tree inputs.

This gate validates scientific input identity before inference.  It does not fetch
records or infer missing metadata.  A successful result means the supplied roster,
FASTA and evidence fields agree mechanically; it is not a taxonomic conclusion.

Geography is admitted as deposited.  The `geography` cell is carried unchanged on each
tip of the receipt.  `geography_region` is a separate display field from the ten-value
list below, filled only from an exact list value or the bundle's country table, and
blank otherwise.  A tip with no deposited geography is admitted with it blank and listed
in `figure_omissions` by full name, so figures can omit it.

Isolation source follows the same rule (owner ruling, .460).  It is carried unchanged on each
tip as `isolation_source`; a tip with none deposited is admitted and listed in
`figure_omissions` with reason NO_DEPOSITED_SOURCE.  A tip missing both is listed twice.
"""
from __future__ import annotations

import argparse, csv, hashlib, json, re, sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # resolve the tools-local country table from any cwd
from _phylo_metadata import _COUNTRY_TO_CONTINENT, _GEO_PLACEHOLDERS, _country_name  # noqa: E402

ROLES = {"query", "reference", "outgroup"}
TYPE_STATUS = {"type", "non_type", "not_applicable"}
# Display regions only, never a refusal: deposited geography is admitted unchanged (owner ruling, .459 row 20).
GEOGRAPHY_REGIONS = ("US", "Canada", "North America (other)", "South America", "Europe",
                     "Asia", "Africa", "Oceania", "Antarctica", "Indian Ocean")
GEOGRAPHY = set(GEOGRAPHY_REGIONS)
GEOGRAPHY_NOTE = ("geography is the deposited text and is the record; "
                  "geography_region is display-only and is never written back.")
_CONTINENT_REGION = {"North America": "North America (other)", "South America": "South America",
                     "Europe": "Europe", "Asia": "Asia", "Africa": "Africa", "Oceania": "Oceania"}
MISSING = {"", "na", "n/a", "not applicable", "not recorded", "unknown", "unverified"}
REQUIRED = {"tip", "role", "organism", "expected_genus", "accession", "sequence_sha256",
            "type_status", "isolation_source", "geography", "sequence_evidence",
            "metadata_evidence", "biological_sample_id", "admission"}


def _missing(value: str | None) -> bool:
    return (value or "").strip().lower() in MISSING


def geography_missing(value: str | None) -> bool:
    """True for a blank cell, a roster placeholder, or an INSDC missing term such as "missing: lab stock"."""
    text = (value or "").strip()
    return _missing(text) or text.split(":", 1)[0].strip().lower() in _GEO_PLACEHOLDERS


def geography_region(deposited: str | None) -> tuple[str, str]:
    """Return (display region, basis) for a deposited geography; never changes the deposited text.

    Basis LIST_VALUE: the deposited text, or its country part before ':', is already a list value.
    Basis COUNTRY_TABLE: the country part is in the bundle's country table (USA -> US, Canada,
    otherwise its continent; North America other than the US and Canada -> "North America (other)").
    Basis NOT_DERIVED: anything else, for example "North America", "USSR", a province name or an
    ocean outside the list. The region stays blank rather than guessed.
    Basis NOT_RECORDED: no deposited geography; the region stays blank.
    """
    text = (deposited or "").strip()
    if geography_missing(text):
        return "", "NOT_RECORDED"
    prefix = text.split(":", 1)[0].strip()
    for candidate in (text, prefix):
        for region in GEOGRAPHY_REGIONS:
            if candidate.casefold() == region.casefold():
                return region, "LIST_VALUE"
    country = _country_name(prefix)
    if country in {"USA", "Canada"}:
        return ("US" if country == "USA" else "Canada"), "COUNTRY_TABLE"
    region = _CONTINENT_REGION.get(_COUNTRY_TO_CONTINENT.get(country or "", ""), "")
    return (region, "COUNTRY_TABLE") if region else ("", "NOT_DERIVED")


def _full_name(row) -> str:
    """Organism as given, plus a `strain` cell when the roster has one that the organism lacks."""
    organism, strain = row["organism"].strip(), (row.get("strain") or "").strip()
    return f"{organism} {strain}" if strain and strain not in organism else organism


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
    tip_records, omissions = [], []
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
        for field in ("accession", "sequence_evidence", "metadata_evidence"):
            if _missing(row[field]):
                raise ValueError(f"METADATA_INCOMPLETE: {tip} field={field}")
        deposited = row["geography"].strip()          # as deposited; never binned or filled in
        region, basis = geography_region(deposited)
        source = row["isolation_source"].strip()     # as deposited; never categorized or filled in
        tip_records.append({"tip": tip, "organism": organism, "accession": row["accession"].strip(),
                            "isolation_source": source,
                            "geography": deposited, "geography_region": region,
                            "geography_region_basis": basis})
        if geography_missing(source):                  # same missing test: blank, placeholder, INSDC term
            omissions.append({"tip": tip, "name": _full_name(row), "accession": row["accession"].strip(),
                              "reason": "NO_DEPOSITED_SOURCE"})
        if basis == "NOT_RECORDED":
            omissions.append({"tip": tip, "name": _full_name(row), "accession": row["accession"].strip(),
                              "reason": "NO_DEPOSITED_GEOGRAPHY"})
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
    # any digest repeated within one sample, even when the sample also holds other sequences
    same_sample = {}
    for s, vals in sample_seq.items():
        counts = Counter(h for _, h in vals)
        dup = [t for t, h in vals if counts[h] > 1]
        if dup:
            same_sample[s] = dup
    if same_sample:
        raise ValueError("DUPLICATE_QUERY_SAME_SAMPLE_SEQUENCE: " + json.dumps(same_sample, sort_keys=True))
    exact = {h:[t for t,_,_ in vals] for h,vals in seq_groups.items() if len(vals) > 1}
    return {"status":"ADMISSION_PASS", "rows":len(rows), "molecule":molecule,
            "exact_sequence_groups":exact, "tips":tip_records, "figure_omissions":omissions, "geography_note":GEOGRAPHY_NOTE,
            "ceiling":"Mechanical admission only; taxonomy and metadata remain source-dependent."}


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("--roster", required=True); p.add_argument("--fasta", required=True)
    p.add_argument("--molecule", choices=("16S","genome"), default="16S")
    p.add_argument("--min-length", type=int, default=900); p.add_argument("--max-length", type=int, default=2000)
    p.add_argument("--json")
    a=p.parse_args(argv)
    if a.json and Path(a.json).exists():   # a receipt is evidence; never replace one silently
        sys.stderr.write(f"ADMISSION_REFUSED: --json receipt already exists: {a.json}\n")  # direct write keeps the strict-health print_calls ratchet flat
        return 2
    with open(a.roster, newline="", encoding="utf-8-sig") as h:
        rows=list(csv.DictReader(h, delimiter="\t"))
    try:
        result=validate(rows, read_fasta(Path(a.fasta)), molecule=a.molecule,
                        min_length=a.min_length, max_length=a.max_length)
        rc=0
    except ValueError as e:   # a refusal is an outcome, not a crash: typed, receipted, exit 2
        result={"status":"ADMISSION_FAIL", "reason":str(e), "rows":len(rows), "molecule":a.molecule}
        sys.stderr.write(f"ADMISSION_FAIL: {e}\n")
        rc=2
    text=json.dumps(result, indent=2, sort_keys=True)+"\n"
    if a.json:
        try:
            with Path(a.json).open("x", encoding="utf-8") as receipt:
                receipt.write(text)
        except FileExistsError:
            sys.stderr.write(f"ADMISSION_REFUSED: --json receipt already exists: {a.json}\n")
            return 2
    print(text, end="")
    return rc

if __name__ == "__main__": raise SystemExit(main())
