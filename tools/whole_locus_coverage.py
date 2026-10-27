#!/usr/bin/env python3
"""Inventory-side evidence accounting; no search, score, annotation, or adoption.

Inventory TSV: identity, locus_tag, protein_sha256, source_role (optional).
Optional evidence TSV: identity, locus_tag, protein_sha256, state, scope,
reference_id, reference_gene_id, evidence_path, evidence_sha256, reason.
Optional reference TSV: reference_id, reference_gene_id. References are counted
separately, never used as the AS-gene denominator. Read docs before scientific use.
"""
import argparse
import collections
import csv
import hashlib
import json
import re
from pathlib import Path
try:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # run as tools/<name>.py from the bundle root
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter

STATES = {"MATCHED", "SEARCHED_NO_HIT", "EXCLUDED"}
SCOPES = {"FOCAL_REGION", "OUTSIDE_REGION_CANDIDATE", "SPLIT_CANDIDATE"}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def read(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def identity_ok(value):
    if not isinstance(value, str):
        return False
    p = value.split(" / ")
    return (len(p) == 4 and all(part and part == part.strip() for part in p)
            and bool(re.fullmatch(r"region[0-9]{3,}", p[2]))
            and bool(re.fullmatch(r"BGC[0-9]+", p[3])))


def pin_ok(value):
    return isinstance(value, str) and bool(re.fullmatch(r"[0-9a-fA-F]{64}", value))


def audit(inventory, evidence=None, references=None, evidence_requested=False):
    """Pure accounting except byte verification of explicitly supplied evidence paths.

    Caller supplies canonical identity and sequence hashes. This tool validates
    syntax and concordance; it does not re-open canonical GBKs or validate identity
    truth. MATCHED means a bound operator-supplied evidence assertion, not reanalysis.
    """
    genes = {}
    for row in inventory:
        key = row.get("identity", ""), row.get("locus_tag", "")
        if not identity_ok(key[0]) or not key[1]:
            raise ValueError("IDENTITY_HOLD: complete identity and locus_tag required")
        if key in genes:
            raise ValueError("AMBIGUOUS_INVENTORY: repeated identity/locus_tag")
        genes[key] = row
    if not genes:
        raise ValueError("EMPTY_INVENTORY: no denominator admitted")
    refset = None if references is None else set()
    for row in references or []:
        key = row.get("reference_id", ""), row.get("reference_gene_id", "")
        if not all(key) or key in refset:
            raise ValueError("REFERENCE_INVENTORY_HOLD: blank or duplicate gene")
        refset.add(key)
    grouped = collections.defaultdict(list)
    for row in evidence or []:
        key = row.get("identity", ""), row.get("locus_tag", "")
        if key not in genes:
            raise ValueError("EVIDENCE_GENE_NOT_IN_INVENTORY: never silently relocate")
        if row.get("state") not in STATES or row.get("scope") not in SCOPES:
            raise ValueError("UNKNOWN_EVIDENCE_STATE_OR_SCOPE")
        if row["scope"] != "FOCAL_REGION" and row["state"] != "MATCHED":
            raise ValueError("CANDIDATE_SCOPE_REQUIRES_MATCH_ASSERTION")
        if row["state"] == "EXCLUDED" and not row.get("reason", "").strip():
            raise ValueError("EXCLUSION_REASON_REQUIRED")
        if row["state"] == "MATCHED" and not all(row.get(k) for k in ("reference_id", "reference_gene_id")):
            raise ValueError("MATCH_REFERENCE_REQUIRED")
        grouped[key].append(row)
    checks = {}
    rows, per_locus, matched_refs = [], {}, set()
    by_reference = collections.defaultdict(lambda: {"AS_genes": set(), "reference_genes": set()})
    for key, gene in genes.items():
        state, reasons = "UNEXAMINED", []
        accepted, external, splits = [], 0, 0
        if not pin_ok(gene.get("protein_sha256")):
            reasons.append("SEQUENCE_PIN_HOLD: inventory protein hash must be exactly 64 hexadecimal characters")
        if evidence_requested and evidence is None:
            reasons.append("MISSING_EVIDENCE: explicit evidence table unavailable")
        for item in grouped[key]:
            path = Path(item.get("evidence_path", ""))
            declared = item.get("evidence_sha256", "")
            if not item.get("evidence_path") or not path.is_file():
                reasons.append("MISSING_EVIDENCE: declared evidence file unavailable")
                continue
            if str(path) not in checks:
                checks[str(path)] = sha(path)
            if not pin_ok(declared) or checks[str(path)] != declared.lower():
                reasons.append("SOURCE_HASH_HOLD: evidence bytes differ or receipt absent")
                continue
            if (not pin_ok(gene.get("protein_sha256")) or not pin_ok(item.get("protein_sha256"))
                    or item["protein_sha256"].lower() != gene["protein_sha256"].lower()):
                reasons.append("SEQUENCE_BINDING_HOLD: supplied protein hash differs or absent")
                continue
            ref = item.get("reference_id", ""), item.get("reference_gene_id", "")
            if item["state"] == "MATCHED" and refset is not None and ref not in refset:
                reasons.append("REFERENCE_GENE_HOLD: match not in supplied reference inventory")
                continue
            if item["scope"] == "OUTSIDE_REGION_CANDIDATE":
                external += 1
            elif item["scope"] == "SPLIT_CANDIDATE":
                splits += 1
            else:
                accepted.append(item)
        asserted = {x["state"] for x in accepted}
        if len(asserted) > 1:
            reasons.append("CONFLICTING_STATES: no automatic override")
        if reasons:
            state = "MISSING_EVIDENCE" if all(x.startswith("MISSING_EVIDENCE") for x in reasons) else "EVIDENCE_HOLD"
        elif asserted:
            state = next(iter(asserted))
        elif external or splits:
            state = "CANDIDATE_ONLY"
        # Held or candidate-only rows never increase confirmed supplied-evidence counts.
        refs = { (x["reference_id"], x["reference_gene_id"]) for x in accepted if x["state"] == "MATCHED" } if state == "MATCHED" else set()
        matched_refs.update(refs)
        for ref_id, ref_gene in refs:
            by_reference[ref_id]["AS_genes"].add(key)
            by_reference[ref_id]["reference_genes"].add(ref_gene)
        role = gene.get("source_role", "") or "UNKNOWN"
        row = {"identity": key[0], "locus_tag": key[1], "protein_sha256": gene.get("protein_sha256", ""),
               "source_role": role, "evidence_state": state, "distinct_reference_genes_matched": len(refs),
               "outside_candidate_rows": external, "split_candidate_rows": splits,
               "reason": "; ".join(reasons) or "; ".join(sorted({x.get("reason", "") for x in accepted if x.get("reason")}))}
        rows.append(row)
        loc = per_locus.setdefault(key[0], {"supplied_distinct_AS_genes": 0, "states": collections.Counter(), "source_roles": collections.Counter()})
        loc["supplied_distinct_AS_genes"] += 1
        loc["states"][state] += 1
        loc["source_roles"][role] += 1
    counts = collections.Counter(x["evidence_state"] for x in rows)
    summary = {"schema": "whole-locus-coverage-v1", "status": "ACCOUNTED_WITH_HOLDS" if counts["EVIDENCE_HOLD"] or counts["MISSING_EVIDENCE"] else "ACCOUNTED",
               "supplied_loci": len(per_locus), "supplied_distinct_AS_genes": len(rows), "evidence_states": counts,
               "reference_genes_denominator": None if refset is None else len(refset),
               "distinct_supplied_matched_reference_genes": len(matched_refs),
               "outside_candidate_rows": sum(x["outside_candidate_rows"] for x in rows),
               "split_candidate_rows": sum(x["split_candidate_rows"] for x in rows),
               "verified_evidence_files": checks, "loci": per_locus,
               "references": {rid: {"distinct_supplied_AS_genes_matched": len(value["AS_genes"]),
                                    "distinct_reference_genes_matched": len(value["reference_genes"]),
                                    "supplied_reference_gene_denominator": None if refset is None else sum(r == rid for r, g in refset)}
                              for rid, value in by_reference.items()},
               "interpretation": "Counts account for supplied inventories and assertions. Unexamined/missing/held are not no-hit. No biological absence, product identity, physical linkage, completeness, or new search inferred."}
    assert sum(counts.values()) == len(genes)
    return rows, summary


def safe_cell(value):
    text = str(value)
    return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) else text


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--inventory", required=True)
    p.add_argument("--evidence")
    p.add_argument("--references")
    p.add_argument("--out", required=True)
    a = p.parse_args(argv)
    source = {"inventory": {"path": str(Path(a.inventory).resolve()), "sha256": sha(a.inventory)}}
    evidence = None
    refs = None
    for name in ("evidence", "references"):
        value = getattr(a, name)
        if value:
            path = Path(value).resolve()
            source[name] = {"path": str(path), "sha256": sha(path) if path.is_file() else None}
            if name == "references" and not path.is_file():
                p.error("explicit reference inventory unavailable; denominator cannot be silently dropped")
            if path.is_file():
                if name == "evidence": evidence = read(path)
                else: refs = read(path)
    rows, summary = audit(read(a.inventory), evidence, refs, bool(a.evidence))
    summary["sources"] = source
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for filename in ("WHOLE_LOCUS_COVERAGE.tsv", "COVERAGE_SUMMARY.json"):
        if (out / filename).exists():
            p.error("output exists; choose a fresh audit directory, preserve prior evidence")
    with (out / "WHOLE_LOCUS_COVERAGE.tsv").open("w", newline="") as f:
        writer = _SafeDictWriter(f, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows({k: safe_cell(v) for k, v in row.items()} for row in rows)
    (out / "COVERAGE_SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({k: summary[k] for k in ("status", "supplied_loci", "supplied_distinct_AS_genes", "evidence_states")}))


if __name__ == "__main__":
    main()
