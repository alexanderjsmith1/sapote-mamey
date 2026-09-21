#!/usr/bin/env python3
"""Build portable, exact-identity-aware BiG-SCAPE cohort tables.

The database is opened read-only. Missing aliases are recorded as holds, and
``--require-complete-alias`` refuses every output when any selected record
lacks the complete ``strain / node-or-contig / region / BGC alias`` identity.
Direct BiG-SCAPE distances are exported without converting them into identity,
product, activity, or ecological claims.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

try:  # governed CSV/TSV writer with bare-script fallback
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter

REGION_GBK_RE = re.compile(r"^(.+)\.region(\d{3})\.gbk$", re.I)
CLAIM_CEILING = (
    "GCF membership and direct edge distance are run- and cutoff-specific "
    "region-similarity context only; they do not establish pathway completeness, "
    "a shared or exact product, expression, production, activity, novelty, "
    "enrichment, host adaptation, or physical cross-contig linkage."
)
VOCABULARY_PATH = Path(__file__).resolve().parents[1] / "mamey" / "data" / "bigscape_class_vocabulary.json"


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_tsv(path):
    with open(path, newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def write_tsv(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8") as stream:
        writer = _SafeDictWriter(stream, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def host_group(text):
    value = (text or "").casefold()
    if value == "ant":
        return "ant"
    if value == "wasp":
        return "wasp"
    if "bee or wasp" in value or "hymenoptera confirmed" in value or "hymenoptera unidentified" in value:
        return "bee_or_wasp"
    if "bombus" in value or "apis" in value or "apidae" in value:
        return "bee"
    return "other"


def node_number(node):
    match = re.match(r"NODE_(\d+)_", node, re.I)
    return match.group(1) if match else ""


def admitted_alias(value):
    alias = str(value or "").strip()
    if not alias or alias.upper() in {"UNRESOLVED_BGC_ALIAS", "UNRESOLVED", "UNKNOWN", "NA", "N/A"}:
        return ""
    return alias


def parse_admitted_gbk_name(path, admitted_strains):
    """Resolve a GBK filename through admitted metadata, never a fixed prefix.

    Matching is case-insensitive for filesystem portability, but the canonical
    strain spelling comes from the input table. The longest exact ``strain_``
    prefix wins. Canonical IDs that collapse to an equal-length match are
    ambiguous and fail closed.
    """
    filename = Path(path).name
    folded = filename.casefold()
    candidates = sorted({str(value).strip() for value in admitted_strains if str(value).strip()})
    matches = [strain for strain in candidates if folded.startswith((strain + "_").casefold())]
    if not matches:
        raise ValueError(f"STRAIN_PREFIX_GATE: no admitted strain prefix for {filename}")
    longest = max(map(len, matches))
    winners = [strain for strain in matches if len(strain) == longest]
    if len(winners) != 1:
        raise ValueError(f"STRAIN_PREFIX_GATE: ambiguous admitted strain prefix for {filename}")
    strain = winners[0]
    remainder = filename[len(strain) + 1:]
    match = REGION_GBK_RE.match(remainder)
    if not match:
        raise ValueError(f"STRAIN_PREFIX_GATE: invalid node-or-contig and region suffix for {filename}")
    node, region_number = match.groups()
    return strain, node, region_number


def load_class_vocabulary(path=VOCABULARY_PATH):
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    entries = payload.get("entries") or []
    codes = [entry.get("code") for entry in entries]
    if not entries or any(not code for code in codes) or len(codes) != len(set(codes)):
        raise ValueError("CLASS_GLOSSARY_GATE: vocabulary codes must be present and unique")
    required = {"code", "full_name", "plain_language_meaning", "source_basis", "claim_ceiling"}
    for entry in entries:
        if not required.issubset(entry) or any(not str(entry[field]).strip() for field in required):
            raise ValueError(f"CLASS_GLOSSARY_GATE: incomplete entry for {entry.get('code', 'UNKNOWN')}")
    return payload


def _class_code_for_text(text, vocabulary=None):
    vocabulary = vocabulary or load_class_vocabulary()
    value = (text or "").casefold().replace("_", "-")
    padded = f" {value} "
    for entry in sorted(vocabulary["entries"], key=lambda item: int(item.get("priority", 500))):
        groups = entry.get("match_all_any_groups") or []
        if groups and all(any(term in value for term in group) for group in groups):
            return entry["code"]
        terms = entry.get("match_any") or []
        if any(term in padded if term.startswith(" ") or term.endswith(" ") else term in value for term in terms):
            return entry["code"]
    return "UNK"


def classify_family(rows):
    vocabulary = load_class_vocabulary()
    by_code = {entry["code"]: entry for entry in vocabulary["entries"]}
    codes = {
        _class_code_for_text(
            ";".join((row.get("bin_label", ""), row.get("category", ""), row.get("product", ""))),
            vocabulary,
        )
        for row in rows
    }
    informative = codes - {"UNK"}
    if len(informative) > 1:
        code = "MIX"
    elif informative:
        code = next(iter(informative))
    else:
        code = "UNK"
    return code, by_code[code]["full_name"]


def _reviewed_subtypes(path):
    if not path:
        return {}
    rows = read_tsv(path)
    vocabulary = load_class_vocabulary()
    required = set(vocabulary["reviewed_subtype_policy"]["required_fields"])
    if rows and not required.issubset(rows[0]):
        raise ValueError("REVIEWED_SUBTYPE_GATE: table requires family_id and reviewed_subtype_code")
    mapping = {}
    for row in rows:
        family_id = str(row["family_id"]).strip()
        record = {field: str(row[field]).strip() for field in required if field != "family_id"}
        if not family_id or any(not value for value in record.values()):
            raise ValueError("REVIEWED_SUBTYPE_GATE: blank required field")
        if family_id in mapping and mapping[family_id] != record:
            raise ValueError(f"REVIEWED_SUBTYPE_GATE: conflicting subtype for family {family_id}")
        mapping[family_id] = record
    return mapping


def _alias_overlay(path):
    """Load an exact-identity alias overlay without weakening held rows.

    Overlay rows are keyed by the complete locus coordinates available before
    alias recovery. A resolved row is admitted only when the recorded complete
    identity exactly agrees with those coordinates and the recovered alias.
    Every other overlay status is an explicit hold and therefore overrides any
    older crosswalk value for the same locus.
    """
    if not path:
        return {}, {"rows": 0, "resolved": 0, "held": 0}
    required = {
        "strain", "full_node_or_contig", "region", "recovered_bgc_alias",
        "complete_identity", "recovery_status",
    }
    rows = read_tsv(path)
    if rows and not required.issubset(rows[0]):
        raise ValueError("ALIAS_OVERLAY_GATE: missing required exact-identity fields")
    mapping = {}
    resolved = 0
    held = 0
    for row in rows:
        strain = str(row["strain"]).strip()
        node = str(row["full_node_or_contig"]).strip()
        region = str(row["region"]).strip()
        status = str(row["recovery_status"]).strip()
        alias = str(row["recovered_bgc_alias"]).strip()
        key = (strain, node, region)
        if not all(key):
            raise ValueError("ALIAS_OVERLAY_GATE: blank locus coordinate")
        if status == "RESOLVED_EXACT_CURRENT_PACKAGE":
            expected = f"{strain} / {node} / {region} / {alias}"
            if not alias or alias == "UNRESOLVED_BGC_ALIAS" or row["complete_identity"].strip() != expected:
                raise ValueError(f"ALIAS_OVERLAY_GATE: invalid resolved identity for {strain} / {node} / {region}")
            record = {"alias": alias, "status": status, "resolved": True}
            resolved += 1
        else:
            record = {"alias": "", "status": status or "UNSPECIFIED_OVERLAY_HOLD", "resolved": False}
            held += 1
        if key in mapping and mapping[key] != record:
            raise ValueError(f"ALIAS_OVERLAY_GATE: conflicting rows for {strain} / {node} / {region}")
        mapping[key] = record
    return mapping, {"rows": len(rows), "resolved": resolved, "held": held}


def _table_exists(connection, name):
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def _edge_param_id(connection):
    if not _table_exists(connection, "edge_params"):
        return None
    rows = connection.execute(
        "SELECT id, weights, alignment_mode, extend_strategy FROM edge_params ORDER BY id"
    ).fetchall()
    if len(rows) == 1:
        return rows[0][0]
    if not rows:
        return None
    raise ValueError("DIRECT_EDGE_GATE: database contains multiple edge parameter sets")


def _direct_edges(connection, members, cutoff):
    if not _table_exists(connection, "distance"):
        return [], None
    edge_param_id = _edge_param_id(connection)
    if edge_param_id is None:
        return [], None
    identity = {int(row["record_id"]): row["locus_display_with_hold"] for row in members}
    grouped = defaultdict(list)
    for row in members:
        grouped[int(row["family_id"])].append(int(row["record_id"]))
    edges = []
    for family_id, record_ids in sorted(grouped.items()):
        if len(record_ids) < 2:
            continue
        placeholders = ",".join("?" for _ in record_ids)
        sql = (
            "SELECT record_a_id,record_b_id,distance,jaccard,adjacency,dss "
            f"FROM distance WHERE record_a_id IN ({placeholders}) "
            f"AND record_b_id IN ({placeholders}) AND edge_param_id=? "
            "ORDER BY distance,record_a_id,record_b_id"
        )
        for a, b, distance, jaccard, adjacency, dss in connection.execute(
            sql, [*record_ids, *record_ids, edge_param_id]
        ):
            edges.append({
                "family_id": family_id,
                "cutoff": f"{cutoff:.12g}",
                "record_a_id": a,
                "record_b_id": b,
                "source_identity": identity[a],
                "target_identity": identity[b],
                "distance": f"{distance:.12g}",
                "jaccard": f"{jaccard:.12g}",
                "adjacency": f"{adjacency:.12g}",
                "dss": f"{dss:.12g}",
            })
    return edges, edge_param_id


def build(
    db, run_id, cutoff, host_table, crosswalk, outdir,
    require_complete_alias=False, reviewed_subtypes=None, alias_overlay=None,
):
    host_rows = read_tsv(host_table)
    crosswalk_rows = read_tsv(crosswalk)
    hosts = {
        row["strain"]: {**row, "host_group": host_group(row.get("host_as_deposited", ""))}
        for row in host_rows
    }
    aliases = {
        (row["strain"], str(row["node_num"]), str(row["region"]).replace("region", "")): row["legacy_bgc"]
        for row in crosswalk_rows
    }
    overlay, overlay_summary = _alias_overlay(alias_overlay)
    admitted_strains = {
        str(row.get("strain", "")).strip() for row in [*host_rows, *crosswalk_rows]
    } | {key[0] for key in overlay}
    admitted_strains.discard("")
    if not admitted_strains:
        raise ValueError("STRAIN_PREFIX_GATE: no admitted strain identifiers")
    connection = sqlite3.connect(f"file:{Path(db).resolve()}?mode=ro", uri=True)
    connection.execute("PRAGMA query_only=ON")
    try:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise RuntimeError(f"database integrity_check: {integrity}")
        raw = connection.execute(
            """SELECT f.id,f.bin_label,b.id,g.path,b.product,b.category,b.contig_edge
               FROM family f JOIN bgc_record_family rf ON rf.family_id=f.id
               JOIN bgc_record b ON b.id=rf.record_id JOIN gbk g ON g.id=b.gbk_id
               WHERE f.run_id=? AND abs(f.cutoff-?)<1e-9 ORDER BY f.id,b.id""",
            (run_id, cutoff),
        ).fetchall()
        members = []
        excluded_unadmitted_records = 0
        for family_id, bin_label, record_id, path, product, category, contig_edge in raw:
            try:
                strain, node, region_number = parse_admitted_gbk_name(path, admitted_strains)
            except ValueError as error:
                if str(error).startswith("STRAIN_PREFIX_GATE: no admitted strain prefix"):
                    excluded_unadmitted_records += 1
                    continue
                raise
            region = f"region{region_number}"
            overlay_record = overlay.get((strain, node, region))
            if overlay_record is not None:
                alias = overlay_record["alias"]
                status = "COMPLETE" if overlay_record["resolved"] else "ALIAS_OVERLAY_HOLD"
                alias_source = "EXACT_ALIAS_OVERLAY" if overlay_record["resolved"] else "EXACT_ALIAS_OVERLAY_HOLD"
                alias_recovery_status = overlay_record["status"]
            else:
                alias = admitted_alias(aliases.get((strain, node_number(node), region_number), ""))
                status = "COMPLETE" if alias else "MISSING_BGC_ALIAS_HOLD"
                alias_source = "BASE_CROSSWALK" if alias else "UNRESOLVED"
                alias_recovery_status = "NOT_PRESENT_IN_OVERLAY"
            shown = alias or "UNRESOLVED_BGC_ALIAS"
            metadata = hosts.get(strain, {})
            members.append({
                "family_id": family_id,
                "cutoff": f"{cutoff:.12g}",
                "bin_label": bin_label or "",
                "record_id": record_id,
                "strain": strain,
                "full_node_or_contig": node,
                "region": region,
                "bgc_alias": shown,
                "identity_status": status,
                "alias_source": alias_source,
                "alias_recovery_status": alias_recovery_status,
                "locus_display_with_hold": f"{strain} / {node} / {region} / {shown}",
                "genus": metadata.get("genus", "UNRESOLVED"),
                "host_as_deposited": metadata.get("host_as_deposited", "UNRESOLVED"),
                "host_group": metadata.get("host_group", "other"),
                "product": product or "",
                "category": category or "",
                "boundary_state": "CONTIG_EDGE" if contig_edge == 1 else "INTERIOR" if contig_edge == 0 else "UNRESOLVED",
                "contig_edge": "" if contig_edge is None else int(contig_edge),
                "source_path": Path(path).name,
            })
        unresolved = sum(row["identity_status"] != "COMPLETE" for row in members)
        if require_complete_alias and unresolved:
            raise ValueError(f"EXACT_ALIAS_GATE: {unresolved} records lack authoritative BGC aliases")
        direct_edges, edge_param_id = _direct_edges(connection, members, cutoff)
    finally:
        connection.close()

    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    member_fields = list(members[0]) if members else ["family_id"]
    write_tsv(out / "BIGSCAPE_LOCUS_MEMBERSHIP.tsv", members, member_fields)
    grouped = defaultdict(list)
    for row in members:
        grouped[int(row["family_id"])].append(row)
    subtype_by_family = _reviewed_subtypes(reviewed_subtypes)
    summaries = []
    for family_id, rows in sorted(grouped.items()):
        strains = sorted({row["strain"] for row in rows})
        groups = Counter(row["host_group"] for row in rows)
        class_code, class_nickname = classify_family(rows)
        summaries.append({
            "family_id": family_id,
            "cutoff": f"{cutoff:.12g}",
            "gcf_label": f"GCF_{family_id:04d}",
            "bin_label": rows[0]["bin_label"],
            "class_code": class_code,
            "class_nickname": class_nickname,
            "reviewed_subtype_code": subtype_by_family.get(str(family_id), {}).get("reviewed_subtype_code", ""),
            "reviewed_subtype_full_name": subtype_by_family.get(str(family_id), {}).get("full_name", ""),
            "reviewed_subtype_plain_language_meaning": subtype_by_family.get(str(family_id), {}).get("plain_language_meaning", ""),
            "reviewed_subtype_source_basis": subtype_by_family.get(str(family_id), {}).get("source_basis", ""),
            "reviewed_subtype_claim_ceiling": subtype_by_family.get(str(family_id), {}).get("claim_ceiling", ""),
            "n_records": len(rows),
            "n_strains": len(strains),
            "strains": ";".join(strains),
            "n_bee_records": groups["bee"],
            "n_wasp_records": groups["wasp"],
            "n_bee_or_wasp_records": groups["bee_or_wasp"],
            "n_ant_records": groups["ant"],
            "n_other_records": groups["other"],
            "products": ";".join(sorted({row["product"] for row in rows if row["product"]})),
            "alias_hold_records": sum(row["identity_status"] != "COMPLETE" for row in rows),
        })
    write_tsv(out / "BIGSCAPE_GCF_SUMMARY.tsv", summaries, list(summaries[0]) if summaries else ["family_id"])
    cross_strain_family_ids = {
        int(row["family_id"]) for row in summaries if int(row["n_strains"]) >= 2
    }
    cross_strain_members = [row for row in members if int(row["family_id"]) in cross_strain_family_ids]
    presence = defaultdict(set)
    for row in members:
        presence[row["strain"]].add(int(row["family_id"]))
    pairs = []
    strains = sorted(presence)
    for index, strain_a in enumerate(strains):
        for strain_b in strains[index + 1:]:
            intersection = presence[strain_a] & presence[strain_b]
            union = presence[strain_a] | presence[strain_b]
            pairs.append({
                "strain_a": strain_a,
                "strain_b": strain_b,
                "shared_gcf_count": len(intersection),
                "union_gcf_count": len(union),
                "jaccard": f"{len(intersection) / len(union) if union else 0:.6f}",
            })
    write_tsv(out / "BIGSCAPE_STRAIN_PAIRWISE_JACCARD.tsv", pairs, list(pairs[0]) if pairs else ["strain_a"])
    edge_fields = [
        "family_id", "cutoff", "record_a_id", "record_b_id", "source_identity",
        "target_identity", "distance", "jaccard", "adjacency", "dss",
    ]
    write_tsv(out / "BIGSCAPE_DIRECT_EDGES.tsv", direct_edges, edge_fields)
    receipt = {
        "status": "PASS",
        "run_id": run_id,
        "cutoff": cutoff,
        "records": len(members),
        "strains": len(presence),
        "families": len(grouped),
        "excluded_unadmitted_records": excluded_unadmitted_records,
        "cross_strain_families": sum(int(row["n_strains"]) >= 2 for row in summaries),
        "complete_alias_records": len(members) - unresolved,
        "unresolved_alias_records": unresolved,
        "cross_strain_records": len(cross_strain_members),
        "cross_strain_complete_alias_records": sum(
            row["identity_status"] == "COMPLETE" for row in cross_strain_members
        ),
        "cross_strain_unresolved_alias_records": sum(
            row["identity_status"] != "COMPLETE" for row in cross_strain_members
        ),
        "alias_overlay_summary": overlay_summary,
        "strict_alias_gate": require_complete_alias,
        "direct_edges": len(direct_edges),
        "edge_param_id": edge_param_id,
        "claim_ceiling": CLAIM_CEILING,
        "sources": [
            {
                "role": role,
                "locator": Path(path).name,
                "sha256": sha256(path),
                "bytes": Path(path).stat().st_size,
            }
            for role, path in [
                ("bigscape_sqlite", db),
                ("host_metadata", host_table),
                ("base_alias_crosswalk", crosswalk),
                *(([("exact_alias_overlay", alias_overlay)]) if alias_overlay else []),
            ]
        ],
    }
    (out / "BIGSCAPE_COHORT_REPORT_RECEIPT.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True)
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--cutoff", type=float, default=0.3)
    parser.add_argument("--host-table", required=True)
    parser.add_argument("--crosswalk", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--require-complete-alias", action="store_true")
    parser.add_argument("--reviewed-subtypes")
    parser.add_argument("--alias-overlay")
    args = parser.parse_args(argv)
    try:
        result = build(
            args.db, args.run_id, args.cutoff, args.host_table, args.crosswalk,
            args.out, args.require_complete_alias, args.reviewed_subtypes, args.alias_overlay,
        )
    except (ValueError, RuntimeError) as error:
        sys.stderr.write(str(error) + "\n")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
