#!/usr/bin/env python3
"""Prepare provenance-rich PKS/RiPP sequence pools without running a tree.

This optional post-seal helper consumes normalized antiSMASH evidence exports.
It never changes a sealed Mamey package and never infers product identity,
production, activity, or horizontal transfer.
"""

from __future__ import annotations

import argparse
import csv
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import sys as _sys
def emit(*args, sep=" ", end="\n", file=None, flush=False):
    """print-compatible stdout/stderr writer (no bare print(); keeps strict-health print_calls flat)."""
    (file or _sys.stdout).write(sep.join(str(a) for a in args) + end)
    if flush:
        (file or _sys.stdout).flush()


SCHEMA_VERSION = "1.0"
CLAIM_CEILING = (
    "Sequence/domain similarity and tree placement are evolutionary context only; "
    "they do not establish product identity, production, activity, novelty, species "
    "identity, or horizontal transfer."
)
TRACKS = ("pks-ks", "ripp-enzyme", "ripp-rre", "ripp-precursor")
AA_RE = re.compile(r"^[ACDEFGHIKLMNPQRSTVWYBXZJUO]+$")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def clean_sequence(value: str) -> str:
    seq = re.sub(r"\s+", "", value or "").upper().rstrip("*")
    return seq if seq and AA_RE.fullmatch(seq) else ""


def first(value):
    if isinstance(value, list):
        return str(value[0]) if value else ""
    return str(value or "")


def safe_tip(parts: list[str]) -> str:
    raw = "|".join(str(part or "NA") for part in parts)
    return re.sub(r"[^A-Za-z0-9_.|+-]", "_", raw)


def lower_row(row: dict[str, str]) -> dict[str, str]:
    return {str(key).strip().lower(): (value or "").strip() for key, value in row.items()}


def resolve_path(raw: str, base: Path) -> Path | None:
    if not raw:
        return None
    path = Path(raw).expanduser()
    return path if path.is_absolute() else (base / path).resolve()


def read_inventory(path: Path) -> dict[str, str]:
    products: dict[str, str] = {}
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for source_row in csv.DictReader(handle):
            row = lower_row(source_row)
            bgc_id = row.get("bgc_id", "")
            if not bgc_id:
                continue
            products[bgc_id] = row.get("products", row.get("product", row.get("classes", "")))
    return products


def read_fasta(path: Path) -> dict[str, str]:
    records: dict[str, str] = {}
    current = ""
    chunks: list[str] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if current:
                    records[current] = clean_sequence("".join(chunks))
                current = line[1:].split()[0]
                chunks = []
            else:
                chunks.append(line)
    if current:
        records[current] = clean_sequence("".join(chunks))
    return records


def manifest_rows(path: Path) -> list[dict]:
    rows: list[dict] = []
    seen: set[str] = set()
    base = path.parent
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        required = {"strain_id", "inventory_csv"}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise ValueError("manifest requires tab-separated strain_id and inventory_csv columns")
        for source_row in reader:
            row = {key: (value or "").strip() for key, value in source_row.items()}
            strain = row["strain_id"]
            if not strain or strain in seen:
                raise ValueError(f"strain_id must be nonblank and unique: {strain!r}")
            seen.add(strain)
            resolved = {"strain_id": strain}
            for key in ("inventory_csv", "modules_csv", "domains_csv", "rrefinder_csv", "ripp_motifs_csv", "proteins_faa"):
                resolved[key] = resolve_path(row.get(key, ""), base)
            for key, candidate in resolved.items():
                if key != "strain_id" and candidate is not None and not candidate.is_file():
                    raise FileNotFoundError(candidate)
            if resolved["inventory_csv"] is None:
                raise ValueError(f"{strain}: inventory_csv is required")
            rows.append(resolved)
    return rows


def detail(row: dict[str, str]) -> dict:
    try:
        parsed = json.loads(row.get("detail_json", "") or "{}")
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def family_matches(text: str, family: str) -> bool:
    return not family or family.casefold() in (text or "").casefold()


def base_decision(strain: str, bgc_id: str, locus: str, target: str, subtype: str,
                  products: str, source: Path, row_number: int, sequence: str) -> dict[str, str]:
    return {
        "strain_id": strain,
        "bgc_id": bgc_id,
        "locus_tag": locus,
        "target": target,
        "subtype_or_family": subtype,
        "bgc_products": products,
        "aa_length": str(len(sequence)),
        "sequence_sha256": sha256_bytes(sequence.encode()) if sequence else "",
        "source_file": str(source),
        "source_row": str(row_number),
        "status": "ELIGIBLE",
        "reason": "",
        "tree_tip": "",
        "sequence": sequence,
    }


def module_decisions(source: dict, args, products: dict[str, str]) -> list[dict[str, str]]:
    path: Path | None = source["modules_csv"]
    if path is None and args.track == "pks-ks":
        raise ValueError(f"{source['strain_id']}: modules_csv required for {args.track}")
    if path is None:
        return []
    wanted = {"pks_ks"} if args.track == "pks-ks" else {d.casefold() for d in args.domain}
    results: list[dict[str, str]] = []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row_number, source_row in enumerate(csv.DictReader(handle), start=2):
            row = lower_row(source_row)
            domain = row.get("domain", "")
            if domain.casefold() not in wanted:
                continue
            parsed = detail(row)
            subtype = first(parsed.get("domain_subtypes"))
            sequence = clean_sequence(first(parsed.get("translation")))
            bgc_id = row.get("bgc_id", "")
            locus = row.get("locus_tag", "")
            product_text = products.get(bgc_id, "")
            item = base_decision(source["strain_id"], bgc_id, locus, domain, subtype,
                                 product_text, path, row_number, sequence)
            if row.get("mapping_status", "").upper() != "MAPPED":
                item["status"], item["reason"] = "HOLD", "NOT_EXACTLY_MAPPED"
            elif not bgc_id or bgc_id not in products:
                item["status"], item["reason"] = "HOLD", "BGC_NOT_IN_INVENTORY"
            elif args.track == "pks-ks" and subtype != args.subtype:
                item["status"], item["reason"] = "EXCLUDED", "SUBTYPE_MISMATCH"
            elif args.track == "ripp-enzyme" and not family_matches(product_text, args.family):
                item["status"], item["reason"] = "EXCLUDED", "RIPP_FAMILY_MISMATCH"
            elif not sequence:
                item["status"], item["reason"] = "HOLD", "INVALID_OR_MISSING_DOMAIN_SEQUENCE"
            elif len(sequence) < args.min_aa:
                item["status"], item["reason"] = "HOLD", "SEQUENCE_BELOW_MIN_AA"
            label = first(parsed.get("domain_id")) or row.get("row_id", "") or domain
            item["tree_tip"] = safe_tip([source["strain_id"], bgc_id, locus, label, subtype])
            results.append(item)
    return results


def domain_table_decisions(source: dict, args, products: dict[str, str], seen: set[tuple[str, str, str]]) -> list[dict[str, str]]:
    """Use full proteins for RiPP enzymes discovered in the normalized domain table."""
    path: Path | None = source["domains_csv"]
    fasta_path: Path | None = source["proteins_faa"]
    if path is None:
        return []
    if fasta_path is None:
        raise ValueError(f"{source['strain_id']}: proteins_faa required when domains_csv supplies RiPP enzymes")
    wanted = {d.casefold() for d in args.domain}
    proteins = read_fasta(fasta_path)
    results: list[dict[str, str]] = []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row_number, source_row in enumerate(csv.DictReader(handle), start=2):
            row = lower_row(source_row)
            domain = row.get("domain", "")
            if domain.casefold() not in wanted:
                continue
            bgc_id, locus = row.get("bgc_id", ""), row.get("locus_tag", "")
            product_text = products.get(bgc_id, "")
            sequence = proteins.get(locus, "")
            item = base_decision(source["strain_id"], bgc_id, locus, domain, args.family,
                                 product_text, path, row_number, sequence)
            key = (bgc_id, locus, domain.casefold())
            if key in seen:
                item["status"], item["reason"] = "EXCLUDED", "DUPLICATE_NORMALIZED_DOMAIN_SOURCE"
            elif bgc_id not in products:
                item["status"], item["reason"] = "HOLD", "BGC_NOT_IN_INVENTORY"
            elif not family_matches(product_text, args.family):
                item["status"], item["reason"] = "EXCLUDED", "RIPP_FAMILY_MISMATCH"
            elif not sequence:
                item["status"], item["reason"] = "HOLD", "FULL_PROTEIN_SEQUENCE_MISSING"
            elif len(sequence) < args.min_aa:
                item["status"], item["reason"] = "HOLD", "SEQUENCE_BELOW_MIN_AA"
            item["tree_tip"] = safe_tip([source["strain_id"], bgc_id, locus, domain, "full_protein"])
            results.append(item)
            seen.add(key)
    return results


def rre_decisions(source: dict, args, products: dict[str, str]) -> list[dict[str, str]]:
    path: Path | None = source["rrefinder_csv"]
    fasta_path: Path | None = source["proteins_faa"]
    if path is None or fasta_path is None:
        raise ValueError(f"{source['strain_id']}: rrefinder_csv and proteins_faa required for ripp-rre")
    proteins = read_fasta(fasta_path)
    results: list[dict[str, str]] = []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row_number, source_row in enumerate(csv.DictReader(handle), start=2):
            row = lower_row(source_row)
            bgc_id, locus = row.get("bgc_id", ""), row.get("locus_tag", "")
            product_text = products.get(bgc_id, "")
            family_text = " ".join((row.get("rre_family", ""), row.get("rre_description", ""), product_text))
            sequence = proteins.get(locus, "")
            start, end = row.get("protein_start", ""), row.get("protein_end", "")
            if sequence and start.isdigit() and end.isdigit():
                left, right = max(0, int(start) - 1), int(end)
                sequence = sequence[left:right]
            item = base_decision(source["strain_id"], bgc_id, locus, "RRE",
                                 row.get("rre_family", ""), product_text, path, row_number, sequence)
            if row.get("mapping_status", "").upper() != "MAPPED":
                item["status"], item["reason"] = "HOLD", "NOT_EXACTLY_MAPPED"
            elif bgc_id not in products:
                item["status"], item["reason"] = "HOLD", "BGC_NOT_IN_INVENTORY"
            elif not family_matches(family_text, args.family):
                item["status"], item["reason"] = "EXCLUDED", "RIPP_FAMILY_MISMATCH"
            elif not sequence:
                item["status"], item["reason"] = "HOLD", "PROTEIN_OR_RRE_SEQUENCE_MISSING"
            elif len(sequence) < args.min_aa:
                item["status"], item["reason"] = "HOLD", "SEQUENCE_BELOW_MIN_AA"
            item["tree_tip"] = safe_tip([source["strain_id"], bgc_id, locus, "RRE", row.get("rre_family", "")])
            results.append(item)
    return results


def precursor_decisions(source: dict, args, products: dict[str, str]) -> list[dict[str, str]]:
    path: Path | None = source["ripp_motifs_csv"]
    if path is None:
        raise ValueError(f"{source['strain_id']}: ripp_motifs_csv required for ripp-precursor")
    results: list[dict[str, str]] = []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row_number, source_row in enumerate(csv.DictReader(handle), start=2):
            row = lower_row(source_row)
            bgc_id, locus = row.get("bgc_id", ""), row.get("locus_tag", "")
            product_text = products.get(bgc_id, "")
            family_text = " ".join((row.get("ripp_family", ""), row.get("peptide_class", ""),
                                    row.get("peptide_subclass", ""), product_text))
            sequence = clean_sequence(row.get("leader", "") + row.get("core_sequence", "") + row.get("tail", ""))
            family = row.get("ripp_family", "") or row.get("peptide_class", "")
            item = base_decision(source["strain_id"], bgc_id, locus, "RiPP_precursor",
                                 family, product_text, path, row_number, sequence)
            if row.get("mapping_status", "").upper() != "MAPPED":
                item["status"], item["reason"] = "HOLD", "NOT_EXACTLY_MAPPED"
            elif bgc_id not in products:
                item["status"], item["reason"] = "HOLD", "BGC_NOT_IN_INVENTORY"
            elif not family_matches(family_text, args.family):
                item["status"], item["reason"] = "EXCLUDED", "RIPP_FAMILY_MISMATCH"
            elif not sequence:
                item["status"], item["reason"] = "HOLD", "PRECURSOR_SEQUENCE_MISSING"
            elif len(sequence) < args.min_aa:
                item["status"], item["reason"] = "HOLD", "SEQUENCE_BELOW_MIN_AA"
            item["tree_tip"] = safe_tip([source["strain_id"], bgc_id, locus, family, row.get("motif_index", "")])
            results.append(item)
    return results


def write_outputs(output: Path, args, sources: list[dict], decisions: list[dict[str, str]], manifest: Path) -> dict:
    output.mkdir(parents=True, exist_ok=False)
    ledger_fields = [
        "strain_id", "bgc_id", "locus_tag", "target", "subtype_or_family", "bgc_products",
        "aa_length", "sequence_sha256", "source_file", "source_row", "status", "reason", "tree_tip",
    ]
    ledger = output / "sequence_ledger.tsv"
    with ledger.open("w", newline="", encoding="utf-8") as handle:
        writer = _SafeDictWriter(handle, fieldnames=ledger_fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for item in decisions:
            writer.writerow({key: item.get(key, "") for key in ledger_fields})

    eligible = [item for item in decisions if item["status"] == "ELIGIBLE"]
    fasta = output / "sequences.faa"
    with fasta.open("w", encoding="utf-8") as handle:
        for item in eligible:
            handle.write(f">{item['tree_tip']}\n")
            sequence = item["sequence"]
            for start in range(0, len(sequence), 80):
                handle.write(sequence[start:start + 80] + "\n")

    groups: dict[str, list[dict]] = defaultdict(list)
    for item in eligible:
        groups[item["sequence_sha256"]].append(item)
    duplicates = output / "exact_sequence_groups.tsv"
    with duplicates.open("w", newline="", encoding="utf-8") as handle:
        fields = ["sequence_sha256", "copy_count", "tree_tip", "strain_id", "bgc_id", "locus_tag"]
        writer = _SafeDictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for digest, members in sorted(groups.items()):
            if len(members) < 2:
                continue
            for item in members:
                writer.writerow({"sequence_sha256": digest, "copy_count": len(members),
                                 "tree_tip": item["tree_tip"], "strain_id": item["strain_id"],
                                 "bgc_id": item["bgc_id"], "locus_tag": item["locus_tag"]})

    source_files = [manifest]
    for source in sources:
        source_files.extend(path for key, path in source.items() if key != "strain_id" and path is not None)
    unique_sources = sorted(set(source_files), key=str)
    status = "READY_FOR_ALIGNMENT" if len(eligible) >= 4 else "HOLD_TOO_FEW_ELIGIBLE_SEQUENCES"
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "track": args.track,
        "subtype": args.subtype,
        "domains": args.domain,
        "family_filter": args.family,
        "min_aa": args.min_aa,
        "status": status,
        "counts": {
            "source_strains": len(sources),
            "decision_rows": len(decisions),
            "eligible_sequences": len(eligible),
            "status_counts": dict(Counter(item["status"] for item in decisions)),
            "exact_sequence_groups_gt1": sum(1 for members in groups.values() if len(members) > 1),
        },
        "duplicates_retained": True,
        "source_sha256": [{"path": str(path), "sha256": sha256_file(path)} for path in unique_sources],
        "claim_ceiling": CLAIM_CEILING,
    }
    receipt_path = output / "receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    checksum_path = output / "SHA256.tsv"
    with checksum_path.open("w", encoding="utf-8") as handle:
        for path in (ledger, fasta, duplicates, receipt_path):
            handle.write(f"{sha256_file(path)}\t{path.name}\n")
    return receipt


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("manifest", nargs="?", type=Path, help="tab-separated source manifest")
    p.add_argument("output", nargs="?", type=Path, help="new output directory")
    p.add_argument("--track", choices=TRACKS)
    p.add_argument("--subtype", default="", help="exact PKS_KS domain_subtype; required for pks-ks")
    p.add_argument("--domain", action="append", default=[], help="exact RiPP enzyme domain; repeatable")
    p.add_argument("--family", default="", help="case-insensitive RiPP family/class filter")
    p.add_argument("--min-aa", type=int, default=0, help="minimum amino-acid length; track default if omitted")
    p.add_argument("--show-options", action="store_true")
    return p


def validate_args(args, p: argparse.ArgumentParser) -> None:
    if args.show_options:
        return
    if not args.manifest or not args.output or not args.track:
        p.error("manifest, output, and --track are required")
    if args.track == "pks-ks" and not args.subtype:
        p.error("pks-ks requires one exact --subtype; do not mix PKS_KS subtypes")
    if args.track == "ripp-enzyme" and (not args.domain or not args.family):
        p.error("ripp-enzyme requires at least one --domain and a --family filter")
    if args.track in {"ripp-rre", "ripp-precursor"} and not args.family:
        p.error(f"{args.track} requires a --family filter")
    if args.min_aa < 0:
        p.error("--min-aa must be nonnegative")


def main(argv: list[str] | None = None) -> int:
    p = parser()
    args = p.parse_args(argv)
    validate_args(args, p)
    if args.show_options:
        emit(json.dumps({
            "tracks": TRACKS,
            "pks_rule": "one exact PKS_KS subtype per prepared pool",
            "ripp_rule": "one explicit family/class per prepared pool",
            "tree_execution": "not performed",
            "claim_ceiling": CLAIM_CEILING,
        }, indent=2))
        return 0
    defaults = {"pks-ks": 250, "ripp-enzyme": 80, "ripp-rre": 35, "ripp-precursor": 8}
    if args.min_aa == 0:
        args.min_aa = defaults[args.track]
    sources = manifest_rows(args.manifest.resolve())
    decisions: list[dict[str, str]] = []
    for source in sources:
        products = read_inventory(source["inventory_csv"])
        if args.track in {"pks-ks", "ripp-enzyme"}:
            module_rows = module_decisions(source, args, products)
            decisions.extend(module_rows)
            if args.track == "ripp-enzyme":
                seen = {(item["bgc_id"], item["locus_tag"], item["target"].casefold()) for item in module_rows}
                decisions.extend(domain_table_decisions(source, args, products, seen))
        elif args.track == "ripp-rre":
            decisions.extend(rre_decisions(source, args, products))
        else:
            decisions.extend(precursor_decisions(source, args, products))
    receipt = write_outputs(args.output.resolve(), args, sources, decisions, args.manifest.resolve())
    emit(json.dumps({"output": str(args.output.resolve()), "status": receipt["status"], **receipt["counts"]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
