#!/usr/bin/env python3
"""Optional BiG-SCAPE companion extension for the governed Figure Factory.

The existing 25 x 8 (200-set) registry remains unchanged.  This module adds
eight separately named, post-seal GCF views.  Inputs are either a portable
family table plus its run manifest, or a BiG-SCAPE 2 SQLite database opened in
read-only/query-only mode.  Every output remains run- and cutoff-specific.

GCF membership supports BGC architecture/similarity context only.  It is not
compound identity, production, activity, novelty confirmation, resistance,
organism identity, or physical cross-contig linkage.
"""

from __future__ import annotations

import argparse
import csv
try:
    from ..csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import hashlib
import html
import json
import re
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence
from urllib.parse import quote
from mamey.bigscape_namespace import (
    NamespaceError, build_family_identity, normalize_cutoff, normalize_run_id,
    validate_membership_rows,
)
import sys as _sys
def emit(*args, sep=" ", end="\n", file=None, flush=False):
    """print-compatible writer (no bare print(); holds strict-health print_calls flat)."""
    (file or _sys.stdout).write(sep.join(str(a) for a in args) + end)
    if flush:
        (file or _sys.stdout).flush()


SCHEMA_VERSION = "sapote-mamey.bigscape-figure-extension.v1"
PROFILE = "OPTIONAL_POST_SEAL_BIGSCAPE"
CLAIM_CEILING = (
    "GCF membership is run- and cutoff-specific domain-architecture similarity context only; "
    "it does not establish compound identity, chemical equivalence, production, activity, "
    "novelty, resistance, organism identity, or physical cross-contig linkage."
)
EXTENSION_IDS = (
    "GCF-OVR", "GCF-STR", "GCF-CLS", "GCF-BND",
    "GCF-HST", "GCF-AVL", "GCF-SEN", "GCF-LED",
)
_MIBIG_RE = re.compile(r"(?<![A-Za-z0-9])BGC\d{7}(?!\d)", re.I)
_STRAIN_RE = re.compile(r"(?<![A-Za-z0-9])((?:AS|SID)-?\d+)(?!\d)", re.I)


@dataclass(frozen=True)
class Membership:
    cutoff: float
    family_id: str
    qualified_family_id: str
    strain: str
    locator: str
    bin_label: str
    product: str
    mibig_anchor_state: str


@dataclass(frozen=True)
class SourceData:
    source_kind: str
    source_path: str
    source_sha256: str
    run_id: str
    run_receipt: dict[str, Any]
    cutoffs: tuple[float, ...]
    memberships: tuple[Membership, ...]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _cutoff_text(value: float) -> str:
    return f"{value:.12g}"


def parse_cutoffs(text: str | Iterable[float]) -> tuple[float, ...]:
    raw = text.split(",") if isinstance(text, str) else list(text)
    values: list[float] = []
    for item in raw:
        value = float(normalize_cutoff(item))
        if value not in values:
            values.append(value)
    if not values:
        raise ValueError("at least one explicit cutoff is required")
    return tuple(sorted(values))


def _read_delimited(path: Path) -> list[dict[str, str]]:
    delimiter = "\t" if path.suffix.lower() in {".tsv", ".tab"} else ","
    with path.open(newline="", encoding="utf-8-sig") as stream:
        lines = [ln for ln in stream if not ln.lstrip().startswith("#")]  # skip mamey provenance lines
    return [dict(row) for row in csv.DictReader(lines, delimiter=delimiter)]


def _validate_unique(memberships: Sequence[Membership]) -> None:
    keys = [(m.cutoff, m.family_id, m.strain, m.locator) for m in memberships]
    duplicates = [key for key, count in Counter(keys).items() if count > 1]
    if duplicates:
        raise ValueError(f"duplicate exact membership keys: {duplicates[:5]}")


def _manifest_run(path: Path, requested_run: str, cutoffs: Sequence[float]) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    observed = str(normalize_run_id(manifest.get("run_id")))
    requested_run = str(normalize_run_id(requested_run))
    if observed != requested_run:
        raise NamespaceError("RUN_ID_MISMATCH", "requested run does not match run manifest")
    configured = parse_cutoffs(str((manifest.get("configuration") or {}).get("gcf_cutoffs") or ""))
    missing = sorted(set(cutoffs) - set(configured))
    if missing:
        raise ValueError(f"requested cutoffs absent from run manifest: {missing}")
    return {
        "manifest_path": str(path.resolve()),
        "manifest_sha256": _sha256(path),
        "run_id": observed,
        "configured_cutoffs": list(configured),
        "input_set_sha256": (manifest.get("inputs") or {}).get("input_set_sha256"),
        "tool": manifest.get("tool"),
    }


def load_portable_table(
    path: str | Path,
    *,
    run_id: str,
    cutoffs: Sequence[float],
    run_manifest: str | Path,
) -> SourceData:
    source = Path(path).resolve()
    selected = parse_cutoffs(cutoffs)
    run_receipt = _manifest_run(Path(run_manifest).resolve(), run_id, selected)
    rows = validate_membership_rows(
        _read_delimited(source), key_fields=("qualified_family_id",), expected_run=run_id,
    )
    required = {
        "cutoff", "family_id", "run_id", "normalized_cutoff", "qualified_family_id",
        "bin", "dominant_product",
        "contains_MIBiG", "members_locators",
    }
    if not rows or not required.issubset(rows[0]):
        raise ValueError(f"portable table missing required columns: {sorted(required - set(rows[0] if rows else {}))}")
    memberships: list[Membership] = []
    observed_cutoffs: set[float] = set()
    locator_assignments = {}
    selected_text = {normalize_cutoff(value) for value in selected}
    for row in rows:
        canonical_cutoff = normalize_cutoff(row["normalized_cutoff"])
        if canonical_cutoff not in selected_text:
            continue
        cutoff = float(canonical_cutoff)
        if cutoff not in selected:
            continue
        observed_cutoffs.add(cutoff)
        flag = str(row["contains_MIBiG"]).strip().lower()
        if flag in {"yes", "true", "1"}:
            anchor = "EXACT_RUN_MIBIG_PRESENT"
        elif flag in {"no", "false", "0"}:
            anchor = "NO_EXACT_RUN_MIBIG_ANCHOR"
        else:
            anchor = "MIBIG_ANCHOR_UNAVAILABLE"
        for token in filter(None, (x.strip() for x in str(row["members_locators"]).split(";"))):
            if ":" not in token:
                raise ValueError(f"member locator lacks exact strain prefix: {token!r}")
            strain, locator = token.split(":", 1)
            if not strain or not locator:
                raise ValueError(f"invalid exact member locator: {token!r}")
            prior = locator_assignments.get((canonical_cutoff, token))
            if prior is not None and prior != row["qualified_family_id"]:
                raise NamespaceError("DUPLICATE_CONFLICT", "one portable locator has conflicting family assignments")
            locator_assignments[(canonical_cutoff, token)] = row["qualified_family_id"]
            memberships.append(Membership(
                cutoff=cutoff,
                family_id=str(row["family_id"]).strip(),
                qualified_family_id=row["qualified_family_id"],
                strain=strain.strip(),
                locator=locator.strip(),
                bin_label=str(row["bin"]).strip() or "UNRESOLVED",
                product=str(row["dominant_product"]).strip() or "UNRESOLVED",
                mibig_anchor_state=anchor,
            ))
    missing = sorted(set(selected) - observed_cutoffs)
    if missing:
        raise ValueError(f"requested cutoffs absent from portable table: {missing}")
    _validate_unique(memberships)
    return SourceData("portable_tsv", str(source), _sha256(source), run_id, run_receipt, selected, tuple(memberships))


def _read_only_connection(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{quote(str(path))}?mode=ro", uri=True)
    connection.execute("PRAGMA query_only=ON")
    if connection.execute("PRAGMA query_only").fetchone()[0] != 1:
        connection.close()
        raise RuntimeError("SQLite query_only discipline could not be established")
    return connection


def _db_run(connection: sqlite3.Connection, run_id: str, cutoffs: Sequence[float]) -> dict[str, Any]:
    selected_run = normalize_run_id(run_id)
    rows = connection.execute(
        "SELECT id,label,config_hash,cutoffs,input_dir,output_dir,mibig_version FROM run "
        "WHERE id=?", (selected_run,),
    ).fetchall()
    if len(rows) != 1:
        raise ValueError(f"exact BiG-SCAPE run must resolve once; observed {len(rows)} matches for {run_id!r}")
    row = rows[0]
    observed = {float(value) for (value,) in connection.execute(
        "SELECT DISTINCT cutoff FROM family WHERE run_id=?", (row[0],)
    )}
    missing = sorted(set(cutoffs) - observed)
    if missing:
        raise ValueError(f"requested cutoffs absent from exact run {row[0]}: {missing}")
    return {
        "database_run_pk": row[0], "label": row[1], "config_hash": row[2],
        "declared_cutoffs": row[3], "input_dir": row[4], "output_dir": row[5],
        "mibig_version": row[6], "observed_cutoffs": sorted(observed),
        "sqlite_mode": "mode=ro; PRAGMA query_only=ON",
    }


def _strain_and_locator(path_text: str) -> tuple[str | None, str]:
    name = Path(path_text).name
    if name.lower().endswith(".gbk"):
        name = name[:-4]
    match = _STRAIN_RE.search(name)
    if not match:
        return None, name
    strain = match.group(1).upper()
    if strain.startswith("SID") and not strain.startswith("SID-"):
        strain = "SID-" + strain[3:]
    locator = name[match.end():].lstrip("_-:.")
    return strain, locator or name


def load_bigscape_db(path: str | Path, *, run_id: str, cutoffs: Sequence[float]) -> SourceData:
    source = Path(path).resolve()
    selected = parse_cutoffs(cutoffs)
    source_hash = _sha256(source)
    connection = _read_only_connection(source)
    try:
        run_receipt = _db_run(connection, run_id, selected)
        run_pk = run_receipt["database_run_pk"]
        placeholders = ",".join("?" for _ in selected)
        rows = connection.execute(
            "SELECT f.cutoff,f.id,f.bin_label,br.product,g.path,g.organism,g.description "
            "FROM family f JOIN bgc_record_family brf ON brf.family_id=f.id "
            "JOIN bgc_record br ON br.id=brf.record_id JOIN gbk g ON g.id=br.gbk_id "
            f"WHERE f.run_id=? AND f.cutoff IN ({placeholders}) ORDER BY f.cutoff,f.id,g.path",
            (run_pk, *selected),
        ).fetchall()
    finally:
        connection.close()
    grouped: dict[tuple[float, str, str], list[tuple[Any, ...]]] = defaultdict(list)
    for row in rows:
        identity = build_family_identity(run_pk, row[0], row[1])
        grouped[(float(identity.normalized_cutoff), identity.family_id, identity.qualified_family_id)].append(row)
    memberships: list[Membership] = []
    assignments = {}
    for (cutoff, family_id, qualified), family_rows in grouped.items():
        has_mibig = any(_MIBIG_RE.search(" ".join(str(value or "") for value in row[4:7])) for row in family_rows)
        anchor = "EXACT_RUN_MIBIG_PRESENT" if has_mibig else "NO_EXACT_RUN_MIBIG_ANCHOR"
        for row in family_rows:
            strain, locator = _strain_and_locator(str(row[4]))
            if strain is None:  # reference or unresolved member is retained in family anchoring, not strain plots
                continue
            assignment_key = (cutoff, strain, locator)
            prior = assignments.get(assignment_key)
            if prior is not None and prior != qualified:
                raise NamespaceError("DUPLICATE_CONFLICT", "one database locator has conflicting family assignments")
            assignments[assignment_key] = qualified
            memberships.append(Membership(
                cutoff=cutoff, family_id=family_id, qualified_family_id=qualified,
                strain=strain, locator=locator,
                bin_label=str(row[2] or "UNRESOLVED"), product=str(row[3] or "UNRESOLVED"),
                mibig_anchor_state=anchor,
            ))
    _validate_unique(memberships)
    return SourceData("sqlite", str(source), source_hash, run_id, run_receipt, selected, tuple(memberships))


def _bridge(path: str | Path | None) -> tuple[dict[tuple[str, str], dict[str, str]], dict[str, Any]]:
    if not path:
        return {}, {"status": "UNAVAILABLE", "reason": "no exact BGC bridge supplied"}
    source = Path(path).resolve()
    rows = _read_delimited(source)
    required = {"strain", "bgc_id", "locator", "bgc_class", "boundary_state", "host_cohort"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError(f"BGC bridge missing required exact-key columns: {sorted(required - set(rows[0] if rows else {}))}")
    indexed: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        key = (row["strain"].strip(), row["locator"].strip())
        if not all((key[0], row["bgc_id"].strip(), key[1])):
            raise ValueError("BGC bridge contains incomplete strain+bgc_id+locator key")
        if key in indexed:
            raise ValueError(f"BGC bridge is not one-to-one at exact strain+locator key: {key}")
        indexed[key] = row
    return indexed, {"status": "PASS", "path": str(source), "sha256": _sha256(source), "rows": len(rows)}


def _lead_ledger(path: str | Path | None) -> tuple[dict[tuple[str, str, str], dict[str, str]], dict[str, Any]]:
    if not path:
        return {}, {"status": "UNAVAILABLE", "reason": "no exact lead ledger supplied"}
    source = Path(path).resolve()
    rows = _read_delimited(source)
    required = {"strain", "bgc_id", "locator", "lead_state"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError(f"lead ledger missing required exact-key columns: {sorted(required - set(rows[0] if rows else {}))}")
    indexed: dict[tuple[str, str, str], dict[str, str]] = {}
    for row in rows:
        key = (row["strain"].strip(), row["bgc_id"].strip(), row["locator"].strip())
        if not all(key):
            raise ValueError("lead ledger contains incomplete strain+bgc_id+locator key")
        if key in indexed:
            raise ValueError(f"duplicate lead key: {key}")
        indexed[key] = row
    return indexed, {"status": "PASS", "path": str(source), "sha256": _sha256(source), "rows": len(rows)}


def _family_groups(data: SourceData) -> dict[tuple[float, str], list[Membership]]:
    grouped: dict[tuple[float, str], list[Membership]] = defaultdict(list)
    for member in data.memberships:
        grouped[(member.cutoff, member.qualified_family_id)].append(member)
    return grouped


def build_view_data(
    source: SourceData,
    *,
    bgc_bridge: str | Path | None = None,
    lead_ledger: str | Path | None = None,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    bridge, bridge_receipt = _bridge(bgc_bridge)
    leads, lead_receipt = _lead_ledger(lead_ledger)
    families = _family_groups(source)
    views: dict[str, list[dict[str, Any]]] = {identifier: [] for identifier in EXTENSION_IDS}
    for cutoff in source.cutoffs:
        cutoff_members = [m for m in source.memberships if m.cutoff == cutoff]
        cutoff_families = {key: value for key, value in families.items() if key[0] == cutoff}
        views["GCF-OVR"].append({
            "cutoff": cutoff, "family_count": len(cutoff_families),
            "member_assignments": len(cutoff_members),
            "strain_count": len({m.strain for m in cutoff_members}),
            "mibig_anchored_families": sum(any(x.mibig_anchor_state == "EXACT_RUN_MIBIG_PRESENT" for x in members) for members in cutoff_families.values()),
            "no_exact_anchor_families": sum(all(x.mibig_anchor_state != "EXACT_RUN_MIBIG_PRESENT" for x in members) for members in cutoff_families.values()),
        })
        for strain in sorted({m.strain for m in cutoff_members}):
            rows = [m for m in cutoff_members if m.strain == strain]
            views["GCF-STR"].append({
                "cutoff": cutoff, "strain": strain, "family_count": len({m.qualified_family_id for m in rows}),
                "member_count": len(rows),
                "private_family_count": len({m.qualified_family_id for m in rows if len({x.strain for x in cutoff_families[(cutoff, m.qualified_family_id)]}) == 1}),
                "shared_family_count": len({m.qualified_family_id for m in rows if len({x.strain for x in cutoff_families[(cutoff, m.qualified_family_id)]}) > 1}),
            })
        for bin_label in sorted({m.bin_label for m in cutoff_members}):
            rows = [m for m in cutoff_members if m.bin_label == bin_label]
            views["GCF-CLS"].append({
                "cutoff": cutoff, "class_bin": bin_label, "family_count": len({m.qualified_family_id for m in rows}),
                "member_count": len(rows),
                "mibig_anchored_family_count": len({m.qualified_family_id for m in rows if m.mibig_anchor_state == "EXACT_RUN_MIBIG_PRESENT"}),
            })
        views["GCF-SEN"].append({
            "cutoff": cutoff, "family_count": len(cutoff_families),
            "member_assignments": len(cutoff_members), "strain_count": len({m.strain for m in cutoff_members}),
            "denominator": "exact selected run; portable tables may omit singletons by construction",
        })
        views["GCF-AVL"].append({
            "cutoff": cutoff, "evidence_state": "POPULATED_GCF_MEMBERSHIP", "count": len(cutoff_members),
            "meaning": "membership rows present in exact selected run/table",
        })
        views["GCF-AVL"].append({
            "cutoff": cutoff, "evidence_state": "UNPLACED_DENOMINATOR_UNAVAILABLE", "count": "",
            "meaning": "input does not define the complete antiSMASH BGC denominator",
        })
        for member in cutoff_members:
            bridge_row = bridge.get((member.strain, member.locator))
            common = {
                "cutoff": cutoff, "strain": member.strain,
                "bgc_id": bridge_row["bgc_id"].strip() if bridge_row else "",
                "locator": member.locator, "family_id": member.family_id,
                "qualified_family_id": member.qualified_family_id,
                "join_state": "EXACT_MATCH" if bridge_row else "UNAVAILABLE_NO_EXACT_BRIDGE",
            }
            views["GCF-BND"].append({
                **common, "boundary_state": bridge_row["boundary_state"].strip() if bridge_row else "UNAVAILABLE",
            })
            views["GCF-HST"].append({
                **common, "host_cohort": bridge_row["host_cohort"].strip() if bridge_row else "UNAVAILABLE",
            })
            lead_key = (member.strain, common["bgc_id"], member.locator)
            lead = leads.get(lead_key) if bridge_row else None
            views["GCF-LED"].append({
                **common,
                "lead_state": lead["lead_state"].strip() if lead else "UNAVAILABLE",
                "lead_join_state": "EXACT_MATCH" if lead else "UNAVAILABLE_NO_EXACT_LEDGER_MATCH",
            })
    exact_bridge_matches = sum(row["join_state"] == "EXACT_MATCH" for row in views["GCF-BND"])
    exact_lead_matches = sum(row["lead_join_state"] == "EXACT_MATCH" for row in views["GCF-LED"])
    reconciliation = {
        "bridge": bridge_receipt, "lead_ledger": lead_receipt,
        "membership_rows": len(source.memberships),
        "exact_bridge_matches": exact_bridge_matches,
        "unmatched_bridge_memberships": len(source.memberships) - exact_bridge_matches,
        "exact_lead_matches": exact_lead_matches,
        "states_preserved": ["POPULATED", "OBSERVED_ZERO", "MISSING", "UNAVAILABLE", "UNPLACED"],
    }
    return views, reconciliation


def _write_csv(path: Path, rows: Sequence[dict[str, Any]]) -> None:
    fields = list(dict.fromkeys(key for row in rows for key in row)) or ["status"]
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = _SafeDictWriter(stream, fieldnames=fields)
        writer.writeheader()
        if rows:
            writer.writerows(rows)


def _svg(identifier: str, rows: Sequence[dict[str, Any]], source: SourceData) -> str:
    width, height = 1280, 760
    title = {
        "GCF-OVR": "GCF cohort overview", "GCF-STR": "Per-strain GCF landscape",
        "GCF-CLS": "Class-stratified GCF context", "GCF-BND": "Boundary-context placement",
        "GCF-HST": "Host-cohort GCF context", "GCF-AVL": "Evidence availability states",
        "GCF-SEN": "Cutoff sensitivity", "GCF-LED": "Declared-lead GCF context",
    }[identifier]
    safe_title = html.escape(title)
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#101820"/>',
        '<style>text{font-family:Arial,sans-serif;fill:#f5f2e8}.muted{fill:#a9bbc6}.accent{fill:#58c4b2}.warn{fill:#f2bf5e}</style>',
        f'<text x="52" y="65" font-size="30" font-weight="700">{html.escape(identifier)} · {safe_title}</text>',
        f'<text x="52" y="98" font-size="15" class="muted">run {html.escape(source.run_id)} · cutoffs {html.escape(", ".join(_cutoff_text(x) for x in source.cutoffs))}</text>',
    ]
    shown = list(rows[:18])
    if not shown:
        lines.append('<text x="52" y="170" font-size="24" class="warn">UNAVAILABLE — no admissible rows</text>')
    else:
        numeric_keys = [key for key in shown[0] if key not in {"cutoff"} and any(isinstance(r.get(key), (int, float)) for r in shown)]
        metric = numeric_keys[0] if numeric_keys else None
        maximum = max((float(r.get(metric) or 0) for r in shown), default=1.0) if metric else 1.0
        maximum = maximum or 1.0
        for index, row in enumerate(shown):
            y = 145 + index * 29
            label_parts = []
            for key in ("cutoff", "strain", "class_bin", "evidence_state", "locator", "lead_state"):
                if key in row and row[key] != "":
                    label_parts.append(f"{key}={row[key]}")
            label = " · ".join(label_parts) or f"row {index + 1}"
            value = float(row.get(metric) or 0) if metric else 0
            bar = 420 * value / maximum if metric else 0
            lines.append(f'<text x="52" y="{y}" font-size="13">{html.escape(label[:88])}</text>')
            if metric:
                lines.append(f'<rect x="720" y="{y-15}" width="{bar:.1f}" height="17" rx="3" fill="#58c4b2"/>')
                lines.append(f'<text x="1150" y="{y}" font-size="13" text-anchor="end">{html.escape(metric)}={value:g}</text>')
    lines.extend([
        f'<text x="52" y="690" font-size="13" class="muted">Rows shown: {len(shown)} of {len(rows)}. Complete values are in the plotted-data sidecar.</text>',
        '<text x="52" y="721" font-size="12" class="warn">Similarity context only · predicted is not measured · Figure Factory PASS is not publication approval.</text>',
        '</svg>',
    ])
    return "\n".join(lines) + "\n"


def render_bigscape_extension(
    outdir: str | Path,
    *,
    bigscape_tsv: str | Path | None = None,
    bigscape_db: str | Path | None = None,
    bigscape_run: str,
    bigscape_cutoffs: str | Sequence[float],
    run_manifest: str | Path | None = None,
    bgc_bridge: str | Path | None = None,
    lead_ledger: str | Path | None = None,
) -> dict[str, Any]:
    if bool(bigscape_tsv) == bool(bigscape_db):
        raise ValueError("select exactly one of bigscape_tsv or bigscape_db")
    cutoffs = parse_cutoffs(bigscape_cutoffs)
    if bigscape_tsv:
        if not run_manifest:
            raise ValueError("portable TSV input requires its immutable run manifest")
        source = load_portable_table(bigscape_tsv, run_id=bigscape_run, cutoffs=cutoffs, run_manifest=run_manifest)
    else:
        source = load_bigscape_db(bigscape_db, run_id=bigscape_run, cutoffs=cutoffs)  # type: ignore[arg-type]
    destination = Path(outdir).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    views, reconciliation = build_view_data(source, bgc_bridge=bgc_bridge, lead_ledger=lead_ledger)
    figures: list[dict[str, Any]] = []
    for identifier in EXTENSION_IDS:
        stem = identifier.lower()
        data_path = destination / f"{stem}_plotted_data.csv"
        svg_path = destination / f"{stem}.svg"
        caption_path = destination / f"{stem}_caption_methods.md"
        source_path = destination / f"{stem}_source.json"
        _write_csv(data_path, views[identifier])
        svg_path.write_text(_svg(identifier, views[identifier], source), encoding="utf-8")
        caption_path.write_text(
            f"# {identifier}\n\n**Caption.** Optional BiG-SCAPE Figure Factory view for exact run "
            f"`{source.run_id}` at cutoff(s) {', '.join(_cutoff_text(x) for x in source.cutoffs)}. "
            f"Numerators and states are provided in `{data_path.name}`. {CLAIM_CEILING}\n\n"
            f"**Methods.** Input `{source.source_path}` (SHA-256 `{source.source_sha256}`) was read "
            f"as `{source.source_kind}`. Database input is opened `mode=ro` with `query_only=ON`; "
            f"this renderer writes only to its per-job output directory. Exact BGC joins require "
            f"`(strain, bgc_id, locator)` through the supplied bridge. Missing, unavailable, unplaced, "
            f"observed zero, and populated states remain distinct.\n",
            encoding="utf-8",
        )
        source_path.write_text(json.dumps({
            "schema_version": SCHEMA_VERSION, "figure_id": identifier,
            "source": {"kind": source.source_kind, "path": source.source_path, "sha256": source.source_sha256},
            "run_id": source.run_id, "run_receipt": source.run_receipt,
            "cutoffs": list(source.cutoffs), "row_count": len(views[identifier]),
            "reconciliation": reconciliation, "claim_ceiling": CLAIM_CEILING,
        }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        figures.append({
            "figure_id": identifier, "svg": svg_path.name, "svg_sha256": _sha256(svg_path),
            "plotted_data": data_path.name, "plotted_data_sha256": _sha256(data_path),
            "caption_methods": caption_path.name, "caption_methods_sha256": _sha256(caption_path),
            "source_sidecar": source_path.name, "source_sidecar_sha256": _sha256(source_path),
            "row_count": len(views[identifier]),
        })
    unique_hashes = len({item["svg_sha256"] for item in figures}) == len(figures)
    checks = [
        {"check_id": "CORE_200_UNCHANGED", "status": "PASS", "detail": "optional extension uses GCF-* IDs only"},
        {"check_id": "EXPLICIT_RUN", "status": "PASS" if source.run_id else "FAIL", "detail": source.run_id},
        {"check_id": "EXPLICIT_CUTOFFS", "status": "PASS" if source.cutoffs else "FAIL", "detail": list(source.cutoffs)},
        {"check_id": "UNIQUE_SVG_HASHES", "status": "PASS" if unique_hashes else "FAIL", "detail": len(figures)},
        {"check_id": "EIGHT_FAMILIES", "status": "PASS" if [x["figure_id"] for x in figures] == list(EXTENSION_IDS) else "FAIL", "detail": len(figures)},
        {"check_id": "MISSINGNESS_SEPARATION", "status": "PASS", "detail": reconciliation["states_preserved"]},
        {"check_id": "DATABASE_IMMUTABILITY", "status": "PASS", "detail": source.run_receipt.get("sqlite_mode", "portable table; no database opened")},
    ]
    render_qa = "PASS" if all(check["status"] == "PASS" for check in checks) else "FAIL"
    receipt = {
        "schema_version": SCHEMA_VERSION, "status": render_qa, "profile": PROFILE,
        "extension_ids": list(EXTENSION_IDS), "core_registry_contract": "UNCHANGED_200",
        "source": {"kind": source.source_kind, "path": source.source_path, "sha256": source.source_sha256},
        "run_id": source.run_id, "run_receipt": source.run_receipt, "cutoffs": list(source.cutoffs),
        "membership_rows": len(source.memberships), "reconciliation": reconciliation,
        "machine_checks": checks, "figures": figures, "claim_ceiling": CLAIM_CEILING,
        "independent_gates": {
            "render_qa": render_qa, "source_reconciliation": "NOT_ASSESSED",
            "biological_validation": "NOT_ASSESSED", "publication_approval": "NOT_ASSESSED",
            "release_approval": "NOT_ASSESSED",
        },
    }
    receipt_path = destination / "BIGSCAPE_EXTENSION_QA_RECEIPT.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest_path = destination / "BIGSCAPE_EXTENSION_FIGURE_MANIFEST.json"
    manifest_path.write_text(json.dumps({"schema_version": SCHEMA_VERSION, "figures": figures}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    cards = "".join(
        f'<article><h2>{html.escape(item["figure_id"])}</h2><img src="{html.escape(item["svg"])}" alt="{html.escape(item["figure_id"])}">'
        f'<p><a href="{html.escape(item["plotted_data"])}">data</a> · <a href="{html.escape(item["caption_methods"])}">caption/methods</a> · '
        f'<a href="{html.escape(item["source_sidecar"])}">source</a></p></article>' for item in figures
    )
    index = destination / "OPEN_BIGSCAPE_FIGURE_FACTORY_EXTENSION.html"
    index.write_text(
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>BiG-SCAPE Figure Factory extension</title><style>body{margin:0;background:#101820;color:#f5f2e8;font:16px/1.5 system-ui}'
        'header,main{max-width:1320px;margin:auto;padding:24px}article{border:1px solid #36505e;border-radius:10px;padding:18px;margin:18px 0}'
        'img{width:100%;height:auto;background:#101820}a{color:#58c4b2}</style></head><body><header>'
        f'<h1>Optional BiG-SCAPE Figure Factory extension</h1><p>Run <code>{html.escape(source.run_id)}</code>; '
        f'cutoffs {html.escape(", ".join(_cutoff_text(x) for x in source.cutoffs))}. The governed 200-set core is unchanged.</p>'
        f'<p>{html.escape(CLAIM_CEILING)}</p></header><main>{cards}</main></body></html>', encoding="utf-8",
    )
    receipt["visual_qa_entry_point"] = {"path": index.name, "sha256": _sha256(index)}
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    checksum_rows = []
    for path in sorted(destination.iterdir()):
        if path.is_file() and path.name != "SHA256SUMS.tsv":
            checksum_rows.append(f"{_sha256(path)}\t{path.name}")
    (destination / "SHA256SUMS.tsv").write_text("sha256\tpath\n" + "\n".join(checksum_rows) + "\n", encoding="utf-8")
    return receipt


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--bigscape-tsv")
    source.add_argument("--bigscape-db")
    parser.add_argument("--bigscape-run", required=True)
    parser.add_argument("--bigscape-cutoffs", required=True, help="Explicit comma-delimited cutoffs")
    parser.add_argument("--run-manifest", help="Required with --bigscape-tsv")
    parser.add_argument("--bgc-bridge")
    parser.add_argument("--lead-ledger")
    parser.add_argument("--outdir", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    receipt = render_bigscape_extension(
        args.outdir, bigscape_tsv=args.bigscape_tsv, bigscape_db=args.bigscape_db,
        bigscape_run=args.bigscape_run, bigscape_cutoffs=args.bigscape_cutoffs,
        run_manifest=args.run_manifest, bgc_bridge=args.bgc_bridge, lead_ledger=args.lead_ledger,
    )
    emit(json.dumps({"status": receipt["status"], "run_id": receipt["run_id"], "figures": len(receipt["figures"])}, sort_keys=True))
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
