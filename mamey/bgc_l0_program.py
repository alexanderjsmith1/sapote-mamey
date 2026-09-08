"""Portable, config-driven L0 BGC draft program.

The module belongs in the Sapote-Mamey bundle. User workspaces are external
evidence roots resolved through :mod:`mamey.evidence_roots`; no personal path
or workspace name is part of the program contract.
"""

from __future__ import annotations

try:  # pragma: no cover - import shape depends on package vs direct-script use
    from .console import emit
except ImportError:  # direct execution: no parent package to resolve against.
    # v9.7.407: a bare-script run (documented for workbook_schema_check.py) has neither a
    # parent package NOR the bundle root on sys.path, so put the root there first.
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from mamey.console import emit

import argparse
import csv
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import hashlib
import json
import os
import re
import shutil
import sqlite3
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .bgc_draft_queue import build_queue, write_queue
from .comparator_evidence import (
    COMPARATOR_FORMATS,
    COMPARATOR_OUTPUT_FIELDS,
    normalize_comparator_children,
    read_comparator_source,
)
from .evidence_roots import (
    EvidenceRootError, load_json, require_source_discovery_preflight, resolve_output, resolve_roots,
    resolve_sources,
)
from .prior_report_corpus import (
    MODULE_FORMATS,
    MODULE_STATES,
    REPORT_MODULE_CATALOG,
    module_consistency_issues,
    parse_module_source,
)


SPEC_SCHEMA = "sapote_l0_report_program_spec_v2"
ROSTER_REQUIRED = {
    "strain", "strain_queue_rank", "primary_user_locator",
    "source_scoped_bgc_alias", "products", "length_kb", "boundary",
    "selection_lane", "activity_route", "prior_activity_routing_score",
}
CHANNELS = (
    ("Swiss-Prot", "local_swissprot"),
    ("nr", "ncbi_nr"),
    ("ClusteredNR", "ncbi_clustered_nr"),
    ("EBI UniProt", "ebi_uniprot"),
    ("Merged multi-channel", "merged_multi"),
)
CLAIM_CEILING = (
    "This L0 draft supports source navigation, exact-locus identity where the join passes, "
    "antiSMASH class context, and observed protein-similarity routing. It does not establish "
    "product identity, production, activity, novelty, completeness, physical linkage, "
    "resistance or immunity, phenotype causality, or publication readiness."
)
MODEB_BRIDGE_STATES = {
    "PASS_EXACT_BODY_LOCATOR_AND_GENE_TABLE_BRIDGE",
    "HOLD_PARTIAL_GENE_TABLE_BRIDGE",
    "HOLD_CONTRADICTION",
    "HOLD_MISSING_REQUIRED_EVIDENCE",
}
MODEB_BRIDGE_REASON_CODES = {
    "PASS_EXACT_BODY_LOCATOR_AND_GENE_TABLE_BRIDGE": {
        "EXACT_IDENTITY_AND_COMPLETE_GENE_TABLE_MATCH",
    },
    "HOLD_PARTIAL_GENE_TABLE_BRIDGE": {
        "EXACT_LOCUS_IDENTITY_SUPPORTED_GENE_DENOMINATOR_DIFFERS",
    },
    "HOLD_CONTRADICTION": {
        "GENE_TABLE_COORDINATE_STRAND_OR_LENGTH_CONTRADICTION",
    },
    "HOLD_MISSING_REQUIRED_EVIDENCE": {
        "HASH_TABLE_OR_SHARED_GENE_EVIDENCE_MISSING",
    },
}
MODEB_BRIDGE_REQUIRED = {
    "strain", "primary_user_locator", "source_scoped_bgc_alias",
    "assembly_sha256", "exact_region_key", "compilation_source_sha256",
    "bridge_state", "historical_gene_rows", "current_gene_rows",
    "shared_locus_tags", "coordinate_mismatches", "strand_mismatches",
    "aa_length_mismatches", "reason_code",
}
MODEB_BRIDGE_COUNT_FIELDS = {
    "historical_gene_rows", "current_gene_rows", "shared_locus_tags",
    "coordinate_mismatches", "strand_mismatches", "aa_length_mismatches",
}
SOURCE_LOCAL_REFERENCE_PATTERNS = (
    re.compile(r"`(?:strain_data|Blastp RESULTS(?: \(clustered nr\))?|Antismash|Zotero)/[^`\n]+`"),
    re.compile(r"`/(?:Users|home)/[^`\n]+`"),
    re.compile(r"`[A-Za-z]:\\[^`\n]+`"),
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read(path: Path, delimiter: str = "\t") -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return [dict(row) for row in csv.DictReader(handle, delimiter=delimiter)]


def _md(value: object) -> str:
    return str(value if value is not None else "").replace("|", "\\|").replace("\n", " ")


def _table(headers: list[str], rows: list[list[object]]) -> list[str]:
    return [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
        *("| " + " | ".join(_md(item) for item in row) + " |" for row in rows),
    ]


def _parse_overrides(values: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError("--evidence-root values must be ROOT_ID=/absolute/path")
        root_id, raw = value.split("=", 1)
        if not root_id or not raw or root_id in out:
            raise ValueError(f"Invalid or duplicate evidence-root override: {value!r}")
        out[root_id] = raw
    return out


def _one_source(resolved: dict[str, Path], source_id: str, role: str) -> Path:
    if source_id not in resolved:
        raise ValueError(f"Required {role} source did not resolve: {source_id!r}")
    return resolved[source_id]


def _read_modeb_bridge(path: Path) -> dict[tuple[str, str, str], dict[str, str]]:
    rows = _read(path)
    if not rows or not MODEB_BRIDGE_REQUIRED.issubset(rows[0]):
        missing = sorted(MODEB_BRIDGE_REQUIRED - set(rows[0] if rows else {}))
        raise ValueError(f"Mode B exact-locus bridge is empty or missing columns: {missing}")
    out: dict[tuple[str, str, str], dict[str, str]] = {}
    for row in rows:
        state = row["bridge_state"]
        if state not in MODEB_BRIDGE_STATES:
            raise ValueError(f"Invalid Mode B bridge state: {state!r}")
        counts: dict[str, int] = {}
        for field in MODEB_BRIDGE_COUNT_FIELDS:
            raw = row[field]
            if not raw.isdigit():
                raise ValueError(
                    f"Mode B bridge count must be a non-negative integer: {field}={raw!r}"
                )
            counts[field] = int(raw)
        historical = counts["historical_gene_rows"]
        current = counts["current_gene_rows"]
        shared = counts["shared_locus_tags"]
        mismatch_total = sum(
            counts[field] for field in (
                "coordinate_mismatches", "strand_mismatches", "aa_length_mismatches"
            )
        )
        if shared > historical or shared > current:
            raise ValueError(
                "Mode B bridge shared_locus_tags cannot exceed either gene denominator"
            )
        invariant_ok = {
            "PASS_EXACT_BODY_LOCATOR_AND_GENE_TABLE_BRIDGE": (
                historical > 0 and historical == current == shared and mismatch_total == 0
            ),
            "HOLD_PARTIAL_GENE_TABLE_BRIDGE": (
                historical > 0 and current > 0 and shared > 0 and mismatch_total == 0
                and not (historical == current == shared)
            ),
            "HOLD_CONTRADICTION": mismatch_total > 0,
            "HOLD_MISSING_REQUIRED_EVIDENCE": (
                historical == 0 or current == 0 or shared == 0
            ),
        }[state]
        if not invariant_ok:
            raise ValueError(
                f"Mode B bridge state/count invariant failed for {state}: {counts!r}"
            )
        reason_code = row["reason_code"].strip()
        if reason_code not in MODEB_BRIDGE_REASON_CODES[state]:
            raise ValueError(
                f"Invalid Mode B bridge reason_code for {state}: {reason_code!r}"
            )
        key = (
            row["strain"], row["primary_user_locator"],
            row["source_scoped_bgc_alias"],
        )
        if key in out:
            raise ValueError(f"Duplicate Mode B exact-locus bridge key: {key!r}")
        out[key] = row
    return out


def _portable_module_content(content: str, source_id: str) -> tuple[str, int]:
    """Replace source-local file references with portable logical evidence URIs."""
    redaction_count = 0

    def replacement(_match: re.Match[str]) -> str:
        nonlocal redaction_count
        redaction_count += 1
        return f"`evidence://{source_id}#source-local-reference-{redaction_count}`"

    portable = content
    for pattern in SOURCE_LOCAL_REFERENCE_PATTERNS:
        portable = pattern.sub(replacement, portable)
    return portable, redaction_count


def _validate_spec(spec: dict) -> None:
    if spec.get("schema_version") != SPEC_SCHEMA:
        raise ValueError("Invalid L0 report-program spec schema")
    if spec.get("release", "INTERNAL") not in {"INTERNAL", "PUBLIC"}:
        raise ValueError("release must be INTERNAL or PUBLIC")
    bridge_source_id = spec.get("modeb_exact_locus_bridge_source_id")
    if bridge_source_id is not None and not isinstance(bridge_source_id, str):
        raise ValueError("modeb_exact_locus_bridge_source_id must be a logical source ID")
    modules = spec.get("evidence_modules", [])
    if not isinstance(modules, list):
        raise ValueError("evidence_modules must be an array")
    if spec.get("release", "INTERNAL") == "PUBLIC" and modules:
        raise ValueError("PUBLIC builds cannot consume raw preliminary legacy modules")
    module_keys: set[tuple[str, str]] = set()
    for module in modules:
        required = {"strain", "source_id", "module_type", "format", "verification_state"}
        if not isinstance(module, dict) or not required.issubset(module):
            raise ValueError(
                "Each evidence module requires strain/source_id/module_type/format/verification_state"
            )
        if module["format"] not in MODULE_FORMATS:
            raise ValueError(f"Invalid evidence-module format: {module['format']!r}")
        if module["verification_state"] not in MODULE_STATES:
            raise ValueError(
                f"Invalid evidence-module verification state: {module['verification_state']!r}"
            )
        key = (module["strain"], module["module_type"])
        if key in module_keys:
            raise ValueError(f"Duplicate evidence module type for strain: {key!r}")
        module_keys.add(key)
    comparator_sources = spec.get("comparator_sources", [])
    if not isinstance(comparator_sources, list):
        raise ValueError("comparator_sources must be an array")
    if spec.get("release", "INTERNAL") == "PUBLIC" and comparator_sources:
        raise ValueError("PUBLIC builds cannot consume preliminary comparator sources")
    comparator_keys: set[tuple[str, str]] = set()
    for source in comparator_sources:
        required = {"strain", "source_id", "format"}
        if not isinstance(source, dict) or not required.issubset(source):
            raise ValueError("Each comparator source requires strain/source_id/format")
        if source["format"] not in COMPARATOR_FORMATS:
            raise ValueError(f"Invalid comparator format: {source['format']!r}")
        key = (source["strain"], source["format"])
        if key in comparator_keys:
            raise ValueError(f"Duplicate comparator source for strain/format: {key!r}")
        comparator_keys.add(key)
    inventories = spec.get("inventories", [])
    roster_source_id = spec.get("roster_source_id")
    if bool(inventories) == bool(roster_source_id):
        raise ValueError("Specify exactly one of inventories or roster_source_id")
    if not isinstance(inventories, list):
        raise ValueError("inventories must be an array")
    strains: set[str] = set()
    for row in inventories:
        required = {"strain", "source_id", "profile", "allocation"}
        if not isinstance(row, dict) or not required.issubset(row):
            raise ValueError("Each inventory requires strain/source_id/profile/allocation")
        if row["strain"] in strains:
            raise ValueError(f"Duplicate inventory strain: {row['strain']}")
        strains.add(row["strain"])
        if row["profile"] not in {"strict", "relaxed", "loose", "unknown"}:
            raise ValueError(f"Invalid inventory profile for {row['strain']}")
        if not isinstance(row["allocation"], int) or row["allocation"] <= 0:
            raise ValueError(f"Invalid allocation for {row['strain']}")
    if roster_source_id:
        profiles = spec.get("strain_profiles")
        if not isinstance(profiles, dict) or not profiles:
            raise ValueError("roster_source_id requires nonempty strain_profiles")
        for strain, profile in profiles.items():
            if not isinstance(strain, str) or profile not in {"strict", "relaxed", "loose", "unknown"}:
                raise ValueError(f"Invalid roster profile binding: {strain!r}={profile!r}")
    timestamp = datetime.fromisoformat(str(spec.get("captured_at_utc", "")).replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        raise ValueError("captured_at_utc must include timezone")
    deepening = int(spec.get("deepening_per_strain", 0))
    if deepening < 0:
        raise ValueError("deepening_per_strain cannot be negative")


def _exact_region(
    db: sqlite3.Connection, *, strain: str, node: str, region_id: str, profile: str
) -> tuple[dict | None, str]:
    if profile == "unknown":
        return None, "SOURCE_PROFILE_UNKNOWN_EXACT_REGION_JOIN_HELD"
    rows = db.execute(
        """
        SELECT r.region_key,r.assembly_sha256,rc.products_json,rc.contig_edge,
               s.archive_sha256,s.antismash_version
        FROM regions r JOIN region_calls rc ON rc.region_key=r.region_key
        JOIN sources s ON s.source_id=rc.source_id
        WHERE r.strain=? AND r.node_id=? AND rc.region_id=? AND rc.profile=?
        ORDER BY r.region_key
        """,
        (strain, node, region_id, profile),
    ).fetchall()
    if len(rows) == 1:
        return dict(rows[0]), "EXACT_ASSEMBLY_NODE_REGION_PROFILE_BOUND"
    if not rows:
        return None, "SOURCE_LOCATOR_BOUND_EXACT_REGION_JOIN_MISSING"
    return None, f"SOURCE_LOCATOR_AMBIGUOUS_{len(rows)}_EXACT_REGION_CANDIDATES"


def _channel_rows(db: sqlite3.Connection, strain: str, alias: str) -> list[dict]:
    out: list[dict] = []
    for display, stored in CHANNELS:
        count = db.execute(
            "SELECT count(*),count(DISTINCT gene),sum(query_coverage IS NULL) "
            "FROM hits WHERE strain=? AND bgc_id=? AND channel=?",
            (strain, alias, stored),
        ).fetchone()
        top = db.execute(
            """SELECT gene,subject_acc,subject_def,pct_identity,query_coverage,provenance_suspect
               FROM hits WHERE strain=? AND bgc_id=? AND channel=?
               ORDER BY COALESCE(provenance_suspect,0) ASC,
                        CASE WHEN hit_rank IS NULL THEN 1 ELSE 0 END,hit_rank,
                        pct_identity DESC,subject_acc LIMIT 1""",
            (strain, alias, stored),
        ).fetchone()
        out.append({
            "display_channel": display,
            "stored_channel": stored,
            "hit_rows": int(count[0]),
            "genes": int(count[1]),
            "missing_query_coverage_rows": int(count[2] or 0),
            "top": dict(top) if top else None,
            "state": (
                "OBSERVED_ROWS_QUERY_AND_RUN_RECEIPTS_UNBOUND_NOT_ADMITTED"
                if count[0] else "ZERO_OBSERVED_ROWS_NOT_BIOLOGICAL_ABSENCE"
            ),
        })
    return out


def _write_rows(path: Path, rows: list[dict], fields: list[str]) -> None:
    # AUDIT_377: tmp-sibling + os.replace, so a crash/kill mid-write (out of disk,
    # OOM-kill, SIGTERM) never leaves a truncated/partial table at the real path that a
    # later run could treat as already-written output. Same-directory tmp guarantees the
    # rename is a same-filesystem atomic replace. Mirrors
    # comparators/antismash_ingest._atomic_write_text and packaging.py's helper.
    tmp = str(path) + ".tmp"
    try:
        with open(tmp, "w", newline="", encoding="utf-8") as handle:
            writer = _SafeDictWriter(
                handle, fieldnames=fields, delimiter="\t", lineterminator="\n",
                extrasaction="ignore",
            )
            writer.writeheader()
            writer.writerows(rows)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    os.replace(tmp, str(path))


def _module_status_rows(
    *, strain: str, locator: str, alias: str, identity_state: str,
    gene_rows: list[dict], profile_rows: list[dict], blastp_rows: list[dict],
    attached: list[dict], stage2_states: dict[str, str] | None = None,
) -> list[dict]:
    """Build the two-stage module dashboard without promoting prior evidence."""
    attached_states = {row["module_type"]: row["module_state"] for row in attached}
    observed = {
        "EXACT_IDENTITY": (
            "VERIFIED_CURRENT" if identity_state == "EXACT_ASSEMBLY_NODE_REGION_PROFILE_BOUND"
            else "HOLD_IDENTITY_REMAP"
        ),
        "EXACT_GENE_DOMAIN_INVENTORY": (
            "VERIFIED_CURRENT" if gene_rows else "HOLD_IDENTITY_REMAP"
        ),
        "EXACT_PROFILE_CALLS": (
            "VERIFIED_CURRENT" if profile_rows else "HOLD_IDENTITY_REMAP"
        ),
        "OBSERVED_BLASTP_CHANNELS": (
            "PRELIMINARY_SOURCE_BOUND_NOT_VERIFIED" if blastp_rows
            else "CHANNEL_MISSING_NOT_BIOLOGICAL_ABSENCE"
        ),
        **attached_states,
        **(stage2_states or {}),
    }
    rows: list[dict] = []
    for definition in REPORT_MODULE_CATALOG:
        module_type = definition["module_type"]
        state = observed.get(module_type, "QUEUED_NOT_YET_ASSEMBLED")
        rows.append({
            "strain": strain,
            "primary_user_locator": locator,
            "source_scoped_bgc_alias": alias,
            "module_type": module_type,
            "phase": definition["phase"],
            "current_state": state,
            "tool_or_input": definition["tool_or_input"],
            "promotion_gate": definition["promotion_gate"],
            "next_action": (
                "PRESERVE_AND_REVALIDATE_ON_SOURCE_CHANGE"
                if state == "VERIFIED_CURRENT"
                else "VERIFY_OR_SUPERSEDE_WITHOUT_REWRITING_OTHER_MODULES"
                if state == "PRELIMINARY_SOURCE_BOUND_NOT_VERIFIED"
                else "RESOLVE_HOLD_OR_ASSEMBLE_MODULE"
            ),
        })
    return rows


def _exact_gene_domain_rows(db: sqlite3.Connection, region_key: str) -> list[dict]:
    rows = db.execute(
        """
        SELECT g.locus_tag,g.strand,g.protein_sha256,g.aa_length,
               g.nucleotide_sha256,g.nucleotide_length,g.product,g.gene_kind,
               g.gene_functions,m.start_region_record_relative,m.end_region_record_relative,
               count(d.domain_key) AS domain_feature_count,
               group_concat(DISTINCT d.label) AS domain_labels
        FROM gene_region_membership m JOIN genes g ON g.gene_key=m.gene_key
        LEFT JOIN domains d ON d.region_key=m.region_key AND d.gene_key=g.gene_key
        WHERE m.region_key=?
        GROUP BY g.gene_key
        ORDER BY m.start_region_record_relative,m.end_region_record_relative,g.locus_tag
        """,
        (region_key,),
    ).fetchall()
    return [dict(row) for row in rows]


def _profile_call_rows(db: sqlite3.Connection, region_key: str) -> list[dict]:
    rows = db.execute(
        """
        SELECT rc.profile,rc.region_id,rc.products_json,rc.contig_edge,
               rc.region_gbk_sha256,s.archive_sha256,s.embedded_assembly_sha256,
               s.antismash_version
        FROM region_calls rc JOIN sources s ON s.source_id=rc.source_id
        WHERE rc.region_key=? ORDER BY rc.profile,rc.region_id,rc.call_key
        """,
        (region_key,),
    ).fetchall()
    return [dict(row) for row in rows]


def _per_gene_channel_rows(db: sqlite3.Connection, strain: str, alias: str) -> list[dict]:
    rows = db.execute(
        """
        SELECT gene,channel,count(*) AS observed_hit_rows,
               sum(query_coverage IS NULL) AS missing_query_coverage_rows
        FROM hits WHERE strain=? AND bgc_id=?
        GROUP BY gene,channel ORDER BY gene,channel
        """,
        (strain, alias),
    ).fetchall()
    out: list[dict] = []
    for row in rows:
        top = db.execute(
            """
            SELECT aa_length,role,domains,subject_acc,subject_organism,subject_def,
                   pct_identity,query_coverage,evalue,bitscore,hit_rank,provenance_suspect
            FROM hits WHERE strain=? AND bgc_id=? AND gene=? AND channel=?
            ORDER BY COALESCE(provenance_suspect,0) ASC,
                     CASE WHEN hit_rank IS NULL THEN 1 ELSE 0 END,hit_rank,
                     pct_identity DESC,subject_acc LIMIT 1
            """,
            (strain, alias, row["gene"], row["channel"]),
        ).fetchone()
        record = dict(row); record.update(dict(top) if top else {})
        record["evidence_state"] = "OBSERVED_ALIAS_SCOPED_QUERY_AND_RUN_RECEIPTS_UNBOUND"
        out.append(record)
    return out


def _build(
    *, spec: dict, resolved: dict[str, Path], resolution_receipt: dict, out_root: Path
) -> dict:
    inventory_specs = spec.get("inventories", [])
    inventories = {
        row["strain"]: _one_source(resolved, row["source_id"], f"inventory:{row['strain']}")
        for row in inventory_specs
    }
    if spec.get("roster_source_id"):
        roster_path = _one_source(resolved, spec["roster_source_id"], "report_roster")
        roster = _read(roster_path)
        if not roster or not ROSTER_REQUIRED.issubset(roster[0]):
            missing = sorted(ROSTER_REQUIRED - set(roster[0] if roster else {}))
            raise ValueError(f"Report roster is empty or missing columns: {missing}")
        profiles = dict(spec["strain_profiles"])
        roster_strains = {row["strain"] for row in roster}
        if roster_strains != set(profiles):
            raise ValueError("Roster strain set differs from strain_profiles")
        rank_keys = {(row["strain"], row["strain_queue_rank"]) for row in roster}
        if len(rank_keys) != len(roster):
            raise ValueError("Duplicate strain/rank keys in report roster")
    else:
        allocations = {row["strain"]: row["allocation"] for row in inventory_specs}
        profiles = {row["strain"]: row["profile"] for row in inventory_specs}
        routing = [
            _one_source(resolved, source_id, "routing")
            for source_id in spec.get("routing_source_ids", [])
        ]
        roster = build_queue(
            inventories=inventories, allocations=allocations, routing_paths=routing,
            modeb_census_path=(
                _one_source(resolved, spec["modeb_census_source_id"], "modeb_census")
                if spec.get("modeb_census_source_id") else None
            ),
        )
    modeb_id = spec.get("modeb_census_source_id")
    modeb_path = _one_source(resolved, modeb_id, "modeb_census") if modeb_id else None
    bridge_id = spec.get("modeb_exact_locus_bridge_source_id")
    bridge_path = (
        _one_source(resolved, bridge_id, "modeb_exact_locus_bridge")
        if bridge_id else None
    )
    bridge_source_sha256 = sha256_file(bridge_path) if bridge_path else ""
    modeb_bridge = _read_modeb_bridge(bridge_path) if bridge_path else {}
    identity_path = _one_source(resolved, spec["identity_db_source_id"], "identity_db")
    blastp_path = _one_source(resolved, spec["blastp_db_source_id"], "blastp_db")
    module_sources: dict[tuple[str, str], dict] = {}
    for module_spec in spec.get("evidence_modules", []):
        source_id = module_spec["source_id"]
        source_path = _one_source(
            resolved, source_id, f"evidence_module:{module_spec['module_type']}"
        )
        module_sources[(module_spec["strain"], module_spec["module_type"])] = {
            "spec": module_spec,
            "path": source_path,
            "sha256": sha256_file(source_path),
            "records": parse_module_source(
                source_path, module_spec["format"], module_spec["strain"]
            ),
        }
    comparator_sources: dict[tuple[str, str], dict] = {}
    for source_spec in spec.get("comparator_sources", []):
        source_id = source_spec["source_id"]
        source_path = _one_source(
            resolved, source_id, f"comparator_source:{source_spec['format']}"
        )
        comparator_sources[(source_spec["strain"], source_spec["format"])] = {
            "spec": source_spec,
            "path": source_path,
            "sha256": sha256_file(source_path),
            "rows": read_comparator_source(source_path, source_spec["format"]),
        }
    roster_path = out_root / "REPORT_ROSTER.tsv"
    write_queue(roster, roster_path)

    first_per_strain = int(spec.get("first_batch_per_strain", 0))
    selected = (
        [row for row in roster if int(row["strain_queue_rank"]) <= first_per_strain]
        if first_per_strain else list(roster)
    )
    selected.sort(key=lambda row: (int(row["strain_queue_rank"]), row["strain"]))
    inventory_rows = {
        strain: {row["BGC_ID"]: row for row in _read(path, ",")}
        for strain, path in inventories.items()
    }
    modeb = (
        {row["strain"]: row for row in _read(modeb_path)} if modeb_path else {}
    )
    identity = sqlite3.connect(f"file:{identity_path.resolve()}?mode=ro", uri=True)
    identity.row_factory = sqlite3.Row
    blastp = sqlite3.connect(f"file:{blastp_path.resolve()}?mode=ro", uri=True)
    blastp.row_factory = sqlite3.Row
    if identity.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        raise ValueError("Identity database integrity failed")
    if blastp.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        raise ValueError("BLASTP database integrity failed")
    reports_root = out_root / "reports"
    reports_root.mkdir()
    modules_root = out_root / "modules"
    modules_root.mkdir()
    tables_root = out_root / "tables"
    tables_root.mkdir()
    index: list[dict] = []
    module_ledger: list[dict] = []
    module_status_ledger: list[dict] = []
    comparator_ledger: list[dict] = []
    for rank, row in enumerate(selected, start=1):
        strain, alias = row["strain"], row["source_scoped_bgc_alias"]
        if inventory_rows:
            inv = inventory_rows[strain][alias]
            # v9.7.374: identity-DB exact joins bind on the canonical `node_id` column
            # (coverage-decimal suffix stripped by infer_node_id() — see crosswalk.py /
            # tab_reconcile.py._node_core), not the raw `Contig` value, which still carries
            # that suffix on SPAdes-style assemblies. Prefer Node_ID; fall back to Contig for
            # legacy inventories that predate the Node_ID column.
            node, region_id = (inv.get("Node_ID") or inv["Contig"]), inv["antiSMASH_Region"]
            products, length_kb, boundary = inv["Products"], inv["Length_kb"], inv["Boundary"]
            interval = f"{inv.get('Start', 'unknown')}–{inv.get('End', 'unknown')}"
        else:
            locator_parts = row["primary_user_locator"].split(" / ")
            if len(locator_parts) != 2 or not all(locator_parts):
                raise ValueError(f"Invalid primary_user_locator: {row['primary_user_locator']!r}")
            node, region_id = locator_parts
            products, length_kb, boundary = row["products"], row["length_kb"], row["boundary"]
            interval = "not carried in roster snapshot"
        locator = f"{node} / {region_id}"
        exact, identity_state = _exact_region(
            identity, strain=strain, node=node,
            region_id=region_id, profile=profiles[strain],
        )
        genes = domains = 0
        if exact:
            genes = identity.execute(
                "SELECT count(DISTINCT gene_key) FROM gene_region_membership WHERE region_key=?",
                (exact["region_key"],),
            ).fetchone()[0]
            domains = identity.execute(
                "SELECT count(*) FROM domains WHERE region_key=?", (exact["region_key"],)
            ).fetchone()[0]
        channels = _channel_rows(blastp, strain, alias)
        table_dir = tables_root / strain / node / region_id
        table_dir.mkdir(parents=True, exist_ok=True)
        gene_rows = _exact_gene_domain_rows(identity, exact["region_key"]) if exact else []
        profile_rows = _profile_call_rows(identity, exact["region_key"]) if exact else []
        gene_channel_rows = _per_gene_channel_rows(blastp, strain, alias)
        gene_table = table_dir / "exact_gene_domain_inventory.tsv"
        profile_table = table_dir / "exact_region_profile_calls.tsv"
        blastp_table = table_dir / "observed_per_gene_channel_summary.tsv"
        _write_rows(gene_table, gene_rows, [
            "locus_tag", "strand", "protein_sha256", "aa_length", "nucleotide_sha256",
            "nucleotide_length", "product", "gene_kind", "gene_functions",
            "start_region_record_relative", "end_region_record_relative",
            "domain_feature_count", "domain_labels",
        ])
        _write_rows(profile_table, profile_rows, [
            "profile", "region_id", "products_json", "contig_edge", "region_gbk_sha256",
            "archive_sha256", "embedded_assembly_sha256", "antismash_version",
        ])
        _write_rows(blastp_table, gene_channel_rows, [
            "gene", "channel", "observed_hit_rows", "missing_query_coverage_rows",
            "aa_length", "role", "domains", "subject_acc", "subject_organism",
            "subject_def", "pct_identity", "query_coverage", "evalue", "bitscore",
            "hit_rank", "provenance_suspect", "evidence_state",
        ])
        exact_genes = {str(item["locus_tag"]): item for item in gene_rows}
        comparator_rows_by_type: dict[str, list[dict[str, str]]] = {}
        comparator_paths: dict[str, Path] = {}
        comparator_filename = {
            "MIBIG_PER_GENE_CSV": "mibig_knownclusterblast_children.tsv",
            "CLUSTERBLAST_PER_GENE_CSV": "clusterblast_children.tsv",
        }
        comparator_module = {
            "MIBIG_PER_GENE_CSV": "MIBIG_KCB_COMPARATOR_CHILDREN",
            "CLUSTERBLAST_PER_GENE_CSV": "CLUSTERBLAST_COMPARATOR_CHILDREN",
        }
        stage2_states: dict[str, str] = {}
        for source_format in COMPARATOR_FORMATS:
            source = comparator_sources.get((strain, source_format))
            if source is None:
                continue
            children = normalize_comparator_children(
                source["rows"], source_format=source_format, alias=alias,
                exact_genes=exact_genes,
            )
            table_path = table_dir / comparator_filename[source_format]
            _write_rows(table_path, children, COMPARATOR_OUTPUT_FIELDS)
            comparator_rows_by_type[source_format] = children
            comparator_paths[source_format] = table_path
            module_type = comparator_module[source_format]
            stage2_states[module_type] = (
                "PRELIMINARY_SOURCE_BOUND_QUERY_AND_RUN_RECEIPTS_UNBOUND"
                if children else "ZERO_OBSERVED_ROWS_NOT_BIOLOGICAL_ABSENCE"
            )
            comparator_ledger.extend({
                "strain": strain,
                "primary_user_locator": locator,
                **child,
                "source_logical_id": source["spec"]["source_id"],
                "source_sha256": source["sha256"],
                "artifact_path": str(table_path.relative_to(out_root)),
            } for child in children)
        draft_state = (
            "L0_EXACT_REGION_BOUND_VERIFIABLE_DRAFT"
            if exact else "L0_SOURCE_BOUND_DRAFT_EXACT_IDENTITY_HOLD"
        )
        title = f"# {strain} — {locator}"
        lines = [
            title, "",
            f"Source-scoped alias: `{alias}` · State: `{draft_state}`", "",
            "> The exact node/contig plus antiSMASH region is the primary locator. The BGC ordinal is a source-scoped alias. Similarity is not identity; biosynthetic capacity is not production.", "",
            "## Fast evidence summary", "",
            f"- Source inventory products/classes: `{products}`",
            f"- Inventory interval: `{interval}`; `{length_kb} kb`; boundary `{boundary}`",
            f"- Selection: `{row['selection_lane']}` / `{row['activity_route']}`; prior routing score `{row['prior_activity_routing_score'] or 'not routed'}`",
            f"- Exact identity join: `{identity_state}`",
        ]
        if exact:
            lines += [
                f"- Assembly SHA-256: `{exact['assembly_sha256']}`",
                f"- Exact region key: `{exact['region_key']}`",
                f"- Source archive SHA-256: `{exact['archive_sha256']}`; antiSMASH `{exact['antismash_version']}`; profile `{profiles[strain]}`",
                f"- Exact-region denominator: `{genes}` CDS; `{domains}` domain/motif features",
                f"- Exact source products/classes: `{'; '.join(json.loads(exact['products_json']))}`",
                f"- Contig-edge field: `{exact['contig_edge']}` (not a biological-completeness conclusion)",
            ]
        lines += ["", "## Current BLASTP channel snapshot", ""]
        lines += _table(
            ["Channel", "Observed rows", "Genes", "Missing qcov", "Top navigation hit", "State"],
            [[
                c["display_channel"], c["hit_rows"], c["genes"], c["missing_query_coverage_rows"],
                (f"{c['top']['gene']} to {c['top']['subject_acc']} — {c['top']['subject_def']} "
                 f"({c['top']['pct_identity']}% identity; qcov "
                 f"{c['top']['query_coverage'] if c['top']['query_coverage'] is not None else 'missing'})")
                if c["top"] else "no observed row",
                c["state"],
            ] for c in channels],
        )
        modeb_row = modeb.get(strain, {})
        lines += [
            "", "Observed rows are navigation evidence only; zero rows are channel missingness, not biological absence.",
            "", "## Deterministic evidence tables", "",
            f"- Exact gene/domain inventory: `{gene_table.relative_to(out_root)}` ({len(gene_rows)} exact-region CDS rows)",
            f"- Exact region profile calls: `{profile_table.relative_to(out_root)}` ({len(profile_rows)} call rows)",
            f"- Observed per-gene/channel BLASTP summary: `{blastp_table.relative_to(out_root)}` ({len(gene_channel_rows)} alias-scoped gene/channel rows)",
            "- The BLASTP table remains query/run-receipt unbound and does not confer exact-locus membership by itself.",
        ]
        for source_format in ("MIBIG_PER_GENE_CSV", "CLUSTERBLAST_PER_GENE_CSV"):
            if source_format not in comparator_paths:
                continue
            children = comparator_rows_by_type[source_format]
            lines.append(
                f"- {comparator_module[source_format]}: "
                f"`{comparator_paths[source_format].relative_to(out_root)}` "
                f"({len(children)} preliminary child rows; query/run receipts unbound)"
            )
        lines += [
            "", "## Prior Mode B material", "",
            f"- Logical source: `evidence://{modeb_id}`" if modeb_id else "- Mode B source: `CHANNEL_NOT_CONSUMED`",
            f"- Reported strain card count: `{modeb_row.get('mode_b_card_count', 'unknown')}`",
            "- Reuse state: `PRIOR_SOURCE_POINTER_ONLY_PARAGRAPH_RECONCILIATION_PENDING`",
            "", "## Attached evidence modules", "",
        ]
        attached: list[dict] = []
        for (module_strain, module_type), source in sorted(module_sources.items()):
            if module_strain != strain:
                continue
            record = source["records"].get(alias)
            if record is None:
                continue
            module_dir = modules_root / strain / node / region_id
            module_dir.mkdir(parents=True, exist_ok=True)
            module_path = module_dir / f"{module_type.lower()}.md"
            portable_content, redaction_count = _portable_module_content(
                record["content_markdown"], source["spec"]["source_id"]
            )
            portable_content_state = (
                "REDACTED_SOURCE_LOCAL_REFERENCES"
                if redaction_count else "PASS_NO_SOURCE_LOCAL_REFERENCES"
            )
            module_text = "\n".join([
                f"# {strain} — {locator} — {module_type}", "",
                f"- Source-scoped alias: `{alias}`",
                f"- Module state: `{source['spec']['verification_state']}`",
                f"- Logical source: `evidence://{source['spec']['source_id']}`",
                f"- Source SHA-256: `{source['sha256']}`",
                f"- Source rank: `{record['source_rank'] or 'not applicable'}`",
                f"- Source locator text: `{record['source_locator_text'] or 'not supplied'}`",
                f"- Portable content state: `{portable_content_state}`",
                f"- Source-local references replaced: `{redaction_count}`",
                "- Authority: prior source material only; current identity and claims are governed independently.",
                "", "---", "", portable_content,
            ])
            consistency_state = "NOT_APPLICABLE_TO_MODULE_FORMAT"
            exact_locus_bridge_state = "BRIDGE_SOURCE_NOT_CONFIGURED"
            historical_gene_table_completeness_state = "NOT_EVALUATED"
            prose_currentness_state = "HISTORICAL_SOURCE_ONLY_NOT_CURRENT"
            bridge_reason_code = "BRIDGE_SOURCE_NOT_CONFIGURED"
            if module_type == "PRELIMINARY_MODE_B":
                issues = module_consistency_issues(
                    module_text,
                    expected_alias=alias,
                    expected_strain=strain,
                    expected_source_locator=record["source_locator_text"],
                )
                if issues:
                    raise ValueError(
                        f"Report consistency gate failed for {strain} {locator} {alias}: "
                        + ",".join(issues)
                    )
                consistency_state = "PASS_SINGLE_LOCUS_STRUCTURAL_IDENTITY"
                if bridge_path:
                    bridge_row = modeb_bridge.get((strain, locator, alias))
                    if bridge_row is None:
                        exact_locus_bridge_state = "HOLD_BRIDGE_ROW_MISSING"
                        historical_gene_table_completeness_state = "MISSING_BRIDGE_ROW"
                        bridge_reason_code = "EXACT_BRIDGE_ROW_MISSING"
                    elif exact is None:
                        exact_locus_bridge_state = "HOLD_CURRENT_IDENTITY_MISSING"
                        historical_gene_table_completeness_state = "NOT_EVALUATED"
                        bridge_reason_code = "CURRENT_EXACT_REGION_IDENTITY_MISSING"
                    else:
                        mismatches = []
                        if bridge_row["assembly_sha256"] != exact["assembly_sha256"]:
                            mismatches.append("ASSEMBLY_SHA256")
                        if bridge_row["exact_region_key"] != exact["region_key"]:
                            mismatches.append("EXACT_REGION_KEY")
                        if bridge_row["compilation_source_sha256"] != source["sha256"]:
                            mismatches.append("COMPILATION_SOURCE_SHA256")
                        if bridge_row["primary_user_locator"] != locator:
                            mismatches.append("PRIMARY_USER_LOCATOR")
                        if bridge_row["source_scoped_bgc_alias"] != alias:
                            mismatches.append("SOURCE_SCOPED_BGC_ALIAS")
                        if bridge_row["strain"] != strain:
                            mismatches.append("STRAIN")
                        if mismatches:
                            raise ValueError(
                                f"Mode B exact-locus bridge binding mismatch for "
                                f"{strain} {locator} {alias}: {','.join(mismatches)}"
                            )
                        exact_locus_bridge_state = bridge_row["bridge_state"]
                        bridge_reason_code = bridge_row["reason_code"]
                        historical_gene_table_completeness_state = {
                            "PASS_EXACT_BODY_LOCATOR_AND_GENE_TABLE_BRIDGE":
                                "COMPLETE_HISTORICAL_CURRENT_GENE_TABLE_MATCH",
                            "HOLD_PARTIAL_GENE_TABLE_BRIDGE":
                                "PARTIAL_HISTORICAL_SELECTED_GENE_TABLE",
                            "HOLD_CONTRADICTION": "CONTRADICTION",
                            "HOLD_MISSING_REQUIRED_EVIDENCE": "MISSING_REQUIRED_EVIDENCE",
                        }[exact_locus_bridge_state]
            module_path.write_text(module_text, encoding="utf-8")
            entry = {
                "strain": strain,
                "primary_user_locator": locator,
                "source_scoped_bgc_alias": alias,
                "module_type": module_type,
                "module_state": source["spec"]["verification_state"],
                "source_logical_id": source["spec"]["source_id"],
                "source_sha256": source["sha256"],
                "source_rank": record["source_rank"],
                "source_locator_text": record["source_locator_text"],
                "consistency_gate_state": consistency_state,
                "exact_locus_bridge_state": exact_locus_bridge_state,
                "historical_gene_table_completeness_state": historical_gene_table_completeness_state,
                "prose_currentness_state": prose_currentness_state,
                "bridge_reason_code": bridge_reason_code,
                "portable_content_state": portable_content_state,
                "source_local_reference_redaction_count": str(redaction_count),
                "bridge_source_logical_id": bridge_id or "",
                "bridge_source_sha256": bridge_source_sha256,
                "module_path": str(module_path.relative_to(out_root)),
                "module_sha256": sha256_file(module_path),
            }
            attached.append(entry)
            module_ledger.append(entry)
        if attached:
            lines += _table(
                ["Module", "State", "Exact-locus bridge", "Gene-table completeness",
                 "Prose currentness", "Portable content", "Prior locator/rank", "Artifact"],
                [[item["module_type"], item["module_state"],
                  item["exact_locus_bridge_state"],
                  item["historical_gene_table_completeness_state"],
                  item["prose_currentness_state"], item["portable_content_state"],
                  item["source_locator_text"] or item["source_rank"] or "not supplied",
                  item["module_path"]] for item in attached],
            )
        else:
            lines += ["- No alias-matched prior module was available in the configured sources."]
        status_rows = _module_status_rows(
            strain=strain, locator=locator, alias=alias, identity_state=identity_state,
            gene_rows=gene_rows, profile_rows=profile_rows, blastp_rows=gene_channel_rows,
            attached=attached, stage2_states=stage2_states,
        )
        module_status_ledger.extend(status_rows)
        status_table = table_dir / "report_module_status.tsv"
        _write_rows(status_table, status_rows, [
            "strain", "primary_user_locator", "source_scoped_bgc_alias", "module_type",
            "phase", "current_state", "tool_or_input", "promotion_gate", "next_action",
        ])
        lines += [
            "", "## Two-stage module dashboard", "",
            "Stage 1 assembles a useful internal report immediately. Stage 2 verifies, "
            "supersedes, or holds each module independently; it does not force a full rewrite.", "",
        ]
        lines += _table(
            ["Module", "Phase", "Current state", "Next tool/input"],
            [[item["module_type"], item["phase"], item["current_state"],
              item["tool_or_input"]] for item in status_rows],
        )
        lines += [
            "", f"Machine-readable module status: `{status_table.relative_to(out_root)}`",
        ]
        lines += [
            "", "## Next deterministic overlays", "",
            "1. Bind submitted protein queries and channel run receipts.",
            "2. Add MIBiG per-gene, KnownClusterBlast, and ClusterBlast child rows.",
            "3. Add the exact editable locus/domain map and boundary/overmerge screen.",
            "4. Reconcile prior Mode B paragraphs without silent overwrite.",
            "5. Add relaxed/loose comparison only when exact assembly/version gates pass.",
            "", "## Claim ceiling", "", CLAIM_CEILING, "",
        ]
        report = reports_root / f"{strain}__{node}__{region_id}.md"
        report.write_text("\n".join(lines), encoding="utf-8")
        index.append({
            "batch_rank": rank, "strain": strain,
            "strain_queue_rank": int(row["strain_queue_rank"]),
            "primary_user_locator": locator,
            "source_scoped_bgc_alias": alias,
            "products": products,
            "selection_lane": row["selection_lane"],
            "activity_route": row["activity_route"],
            "prior_activity_routing_score": row["prior_activity_routing_score"],
            "region_key": exact["region_key"] if exact else "",
            "assembly_sha256": exact["assembly_sha256"] if exact else "",
            "identity_state": identity_state,
            "observed_channel_count": sum(c["hit_rows"] > 0 for c in channels),
            "observed_hit_rows": sum(c["hit_rows"] for c in channels),
            "observed_gene_channel_pairs": sum(c["genes"] for c in channels),
            "missing_query_coverage_rows": sum(c["missing_query_coverage_rows"] for c in channels),
            "exact_gene_inventory_rows": len(gene_rows),
            "exact_profile_call_rows": len(profile_rows),
            "observed_gene_channel_summary_rows": len(gene_channel_rows),
            "mibig_kcb_child_rows": len(comparator_rows_by_type.get("MIBIG_PER_GENE_CSV", [])),
            "clusterblast_child_rows": len(comparator_rows_by_type.get("CLUSTERBLAST_PER_GENE_CSV", [])),
            "attached_module_count": len(attached),
            "report_path": str(report.relative_to(out_root)),
            "report_sha256": sha256_file(report),
            "draft_state": draft_state,
        })
    identity.close()
    blastp.close()
    index_path = out_root / "REPORT_INDEX.tsv"
    with index_path.open("w", newline="", encoding="utf-8") as handle:
        writer = _SafeDictWriter(handle, fieldnames=list(index[0]), delimiter="\t", lineterminator="\n")
        writer.writeheader(); writer.writerows(index)
    deepening_n = int(spec.get("deepening_per_strain", 0))
    deepening_rows: list[dict] = []
    if deepening_n:
        for row in index:
            if int(row["strain_queue_rank"]) > deepening_n:
                continue
            exact_ready = row["identity_state"] == "EXACT_ASSEMBLY_NODE_REGION_PROFILE_BOUND"
            deepening_rows.append({
                "strain": row["strain"],
                "strain_queue_rank": row["strain_queue_rank"],
                "primary_user_locator": row["primary_user_locator"],
                "source_scoped_bgc_alias": row["source_scoped_bgc_alias"],
                "products": row["products"],
                "activity_route": row["activity_route"],
                "prior_activity_routing_score": row["prior_activity_routing_score"],
                "identity_state": row["identity_state"],
                "preliminary_module_count": row["attached_module_count"],
                "exact_gene_inventory_rows": row["exact_gene_inventory_rows"],
                "observed_gene_channel_summary_rows": row["observed_gene_channel_summary_rows"],
                "deepening_state": (
                    "READY_FOR_EXACT_LOCUS_OVERLAYS" if exact_ready
                    else "IDENTITY_HOLD_PRELIMINARY_MODULES_ONLY"
                ),
                "required_next_modules": (
                    "MIBIG_KCB_CLUSTERBLAST_CHILDREN;LOCUS_DOMAIN_WIDGET;PROFILE_DELTA;"
                    "PARAGRAPH_DISPOSITION"
                    if exact_ready else "EXACT_IDENTITY_REMAP"
                ),
            })
    deepening_path = out_root / "SELECTIVE_DEEPENING_QUEUE.tsv"
    _write_rows(deepening_path, deepening_rows, [
        "strain", "strain_queue_rank", "primary_user_locator", "source_scoped_bgc_alias",
        "products", "activity_route", "prior_activity_routing_score", "identity_state",
        "preliminary_module_count", "exact_gene_inventory_rows",
        "observed_gene_channel_summary_rows", "deepening_state", "required_next_modules",
    ])
    module_ledger_path = out_root / "EVIDENCE_MODULE_LEDGER.tsv"
    module_fields = [
        "strain", "primary_user_locator", "source_scoped_bgc_alias", "module_type",
        "module_state", "source_logical_id", "source_sha256", "source_rank",
        "source_locator_text", "consistency_gate_state", "module_path", "module_sha256",
        "exact_locus_bridge_state", "historical_gene_table_completeness_state",
        "prose_currentness_state", "bridge_reason_code", "portable_content_state",
        "source_local_reference_redaction_count", "bridge_source_logical_id",
        "bridge_source_sha256",
    ]
    with module_ledger_path.open("w", newline="", encoding="utf-8") as handle:
        writer = _SafeDictWriter(
            handle, fieldnames=module_fields, delimiter="\t", lineterminator="\n"
        )
        writer.writeheader(); writer.writerows(module_ledger)
    module_status_path = out_root / "REPORT_MODULE_STATUS.tsv"
    module_status_fields = [
        "strain", "primary_user_locator", "source_scoped_bgc_alias", "module_type",
        "phase", "current_state", "tool_or_input", "promotion_gate", "next_action",
    ]
    _write_rows(module_status_path, module_status_ledger, module_status_fields)
    comparator_ledger_path = out_root / "COMPARATOR_EVIDENCE_LEDGER.tsv"
    comparator_ledger_fields = [
        "strain", "primary_user_locator", *COMPARATOR_OUTPUT_FIELDS,
        "source_logical_id", "source_sha256", "artifact_path",
    ]
    _write_rows(comparator_ledger_path, comparator_ledger, comparator_ledger_fields)
    manifest = {
        "schema_version": "sapote_l0_report_program_manifest_v1",
        "status": "DRAFT_BUILT_NOT_ACCEPTED_NOT_INTEGRATED",
        "captured_at_utc": spec["captured_at_utc"],
        "release": spec.get("release", "INTERNAL"),
        "roster_rows": len(roster), "report_rows": len(index),
        "allocation_by_strain": dict(Counter(row["strain"] for row in roster)),
        "identity_state_counts": dict(Counter(row["identity_state"] for row in index)),
        "draft_state_counts": dict(Counter(row["draft_state"] for row in index)),
        "evidence_module_rows": len(module_ledger),
        "evidence_module_state_counts": dict(
            Counter(row["module_state"] for row in module_ledger)
        ),
        "evidence_module_consistency_gate_counts": dict(
            Counter(row["consistency_gate_state"] for row in module_ledger)
        ),
        "evidence_module_exact_locus_bridge_counts": dict(
            Counter(row["exact_locus_bridge_state"] for row in module_ledger)
        ),
        "evidence_module_prose_currentness_counts": dict(
            Counter(row["prose_currentness_state"] for row in module_ledger)
        ),
        "evidence_module_portable_content_counts": dict(
            Counter(row["portable_content_state"] for row in module_ledger)
        ),
        "evidence_module_source_local_reference_redactions": sum(
            int(row["source_local_reference_redaction_count"]) for row in module_ledger
        ),
        "report_module_status_rows": len(module_status_ledger),
        "report_module_phase_counts": dict(
            Counter(row["phase"] for row in module_status_ledger)
        ),
        "report_module_state_counts": dict(
            Counter(row["current_state"] for row in module_status_ledger)
        ),
        "comparator_evidence_rows": len(comparator_ledger),
        "comparator_channel_counts": dict(
            Counter(row["comparator_channel"] for row in comparator_ledger)
        ),
        "comparator_query_join_state_counts": dict(
            Counter(row["query_join_state"] for row in comparator_ledger)
        ),
        "comparator_coverage_state_counts": dict(
            Counter(row["coverage_state"] for row in comparator_ledger)
        ),
        "selective_deepening_rows": len(deepening_rows),
        "selective_deepening_per_strain": deepening_n,
        "portable_resolution_receipt": resolution_receipt,
        "reports": index, "claim_ceiling": CLAIM_CEILING,
    }
    manifest_path = out_root / "REPORT_PROGRAM_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def run(config_path: Path, manifest_path: Path, spec_path: Path, overrides: dict[str, str]) -> dict:
    config, source_manifest, spec = map(load_json, (config_path, manifest_path, spec_path))
    _validate_spec(spec)
    roots = resolve_roots(config, config_path, cli_roots=overrides)
    resolved, receipt = resolve_sources(source_manifest, roots, spec.get("release", "INTERNAL"))
    if isinstance(spec.get("strain_profiles"), dict) and spec["strain_profiles"]:
        strain_keys = list(spec["strain_profiles"])
    else:
        strain_keys = [item.get("strain", "") for item in spec.get("inventories", [])]
    source_preflight_receipt = require_source_discovery_preflight(
        source_manifest=source_manifest,
        resolved_sources=resolved,
        spec=spec,
        strain_keys=strain_keys,
    )
    receipt["source_discovery_preflight"] = source_preflight_receipt
    output = spec.get("output", {})
    final = resolve_output(roots, output.get("root_id", ""), output.get("relative_path", ""))
    if final.exists():
        raise FileExistsError(f"Final output already exists: {final}")
    final.parent.mkdir(parents=True, exist_ok=True)
    staging = final.with_name(f".{final.name}.staging-{uuid.uuid4().hex}")
    staging.mkdir()
    try:
        result = _build(spec=spec, resolved=resolved, resolution_receipt=receipt, out_root=staging)
        resolved_after, _receipt_after = resolve_sources(
            source_manifest, roots, spec.get("release", "INTERNAL")
        )
        if {
            key: str(path.resolve()) for key, path in resolved_after.items()
        } != {
            key: str(path.resolve()) for key, path in resolved.items()
        }:
            raise EvidenceRootError("Resolved source set changed during report build")
        source_preflight_after = require_source_discovery_preflight(
            source_manifest=source_manifest,
            resolved_sources=resolved_after,
            spec=spec,
            strain_keys=strain_keys,
        )
        if source_preflight_after != source_preflight_receipt:
            raise EvidenceRootError("Source-discovery preflight changed during report build")
        os.replace(staging, final)
        return result
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def command(args: argparse.Namespace) -> int:
    result = run(
        Path(args.evidence_root_config), Path(args.source_manifest), Path(args.program_spec),
        _parse_overrides(list(args.evidence_root or [])),
    )
    emit(json.dumps(result, indent=2))
    return 0


def add_cli_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    """Register the portable report-program command on Sapote-Mamey's CLI."""
    parser = subparsers.add_parser(
        "build-bgc-drafts",
        help="Build locator-first L0 BGC drafts from hash-bound external evidence roots",
    )
    parser.add_argument(
        "--evidence-root-config", required=True,
        help="portable JSON configuration declaring logical evidence and output roots",
    )
    parser.add_argument(
        "--source-manifest", required=True,
        help="hash-bound logical-source manifest; paths remain relative to declared roots",
    )
    parser.add_argument(
        "--program-spec", required=True,
        help="five-strain allocations, profiles, source IDs, and output destination",
    )
    parser.add_argument(
        "--evidence-root", action="append", default=[], metavar="ROOT_ID=/ABSOLUTE/PATH",
        help="override one declared root (repeatable); never written into public reports",
    )
    parser.set_defaults(func=command)
    return parser


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    add_cli_parser(subparsers)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
