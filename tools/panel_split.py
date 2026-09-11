#!/usr/bin/env python3
"""Split a panel into reference and query FASTAs using its explicit tip-role table."""
import argparse, csv, hashlib, json, os, sys
import logging
_LOG = logging.getLogger(__name__)


def read_fasta(path):
    rows, name = [], None
    with open(path) as fh:
        for line in fh:
            line = line.rstrip("\n")
            if line.startswith(">"):
                names = line[1:].split()
                if not names or names[0] in {n for n, _ in rows}:
                    raise ValueError("PANEL_FASTA_DUPLICATE_OR_EMPTY_TIP")
                name = names[0]; rows.append((name, []))
            elif rows:
                rows[-1][1].append(line.strip())
            elif line.strip():
                raise ValueError("PANEL_FASTA_SEQUENCE_BEFORE_HEADER")
    if not rows or any(not "".join(s) for n, s in rows):
        raise ValueError("PANEL_FASTA_EMPTY_SEQUENCE")
    return [(n, "".join(s)) for n, s in rows]


def split_panel(fasta, meta):
    """Return (references, queries) as [(tip, seq)], by declared role. Refuses any mismatch."""
    with open(meta) as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        fields = reader.fieldnames or []
        if len(fields) != len(set(fields)):
            raise ValueError("PANEL_META_DUPLICATE_HEADER")
        rows = list(reader)
    if not rows or "role" not in rows[0] or "tip" not in rows[0]:
        raise ValueError("PANEL_META_REQUIRES_tip_role")
    if any(None in row or not row.get("tip") or not row.get("role") for row in rows):
        raise ValueError("PANEL_META_INVALID_ROW")
    if len({row["tip"] for row in rows}) != len(rows):
        raise ValueError("PANEL_META_DUPLICATE_TIP")
    role = {r["tip"]: r["role"] for r in rows}
    records = read_fasta(fasta)
    unknown = [n for n, _ in records if n not in role]
    if unknown:
        raise ValueError(f"PANEL_RECORD_WITHOUT_ROLE: {unknown[:3]}")
    missing = [t for t in role if t not in {n for n, _ in records}]
    if missing:
        raise ValueError(f"PANEL_ROLE_WITHOUT_RECORD: {missing[:3]}")
    bad = sorted({v for v in role.values()} - {"query", "reference", "outgroup"})
    if bad:
        raise ValueError(f"PANEL_ROLE_UNKNOWN: {bad}")
    refs = [(n, s) for n, s in records if role[n] in ("reference", "outgroup")]
    queries = [(n, s) for n, s in records if role[n] == "query"]
    if not refs or not queries:
        raise ValueError(f"PANEL_SPLIT_EMPTY: {len(refs)} reference(s), {len(queries)} query(ies)")
    return refs, queries


def write_fasta(path, records):
    with open(path, "w") as fh:
        for n, s in records:
            fh.write(f">{n}\n{s}\n")
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    ap.add_argument("fasta"); ap.add_argument("meta"); ap.add_argument("--out-prefix", required=True)
    a = ap.parse_args(argv)
    refs_path, q_path = a.out_prefix + "_refs.fasta", a.out_prefix + "_queries.fasta"
    for p in (refs_path, q_path, a.out_prefix + "_split_receipt.json"):
        if os.path.exists(p):
            sys.exit(f"[panel-split] output exists, choose a new prefix: {p}")
    try:
        refs, queries = split_panel(a.fasta, a.meta)
    except (ValueError, OSError) as exc:
        sys.exit(f"[panel-split] REFUSED: {exc}")
    receipt = {"schema": "panel-split-v1", "panel_fasta_sha256": hashlib.sha256(open(a.fasta, "rb").read()).hexdigest(),
               "panel_metadata_sha256": hashlib.sha256(open(a.meta, "rb").read()).hexdigest(),
               "references": len(refs), "queries": len(queries),
               "references_sha256": write_fasta(refs_path, refs), "queries_sha256": write_fasta(q_path, queries)}
    json.dump(receipt, open(a.out_prefix + "_split_receipt.json", "w"), indent=2)
    _LOG.info(f"[panel-split] {len(refs)} reference(s) -> {refs_path}\n"
                     f"[panel-split] {len(queries)} query(ies)  -> {q_path}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
