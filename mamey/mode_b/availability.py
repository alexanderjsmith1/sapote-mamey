"""Portable Mode B evidence-availability audit and writing planner.

This module inventories evidence before any Mode B prose is authored.  It does
not interpret biology.  Exact assembly + node/contig + region is the primary
identity; BGC aliases are secondary.  Missing or unbound evidence is reported
as a workflow state, never as biological absence.

The scanner accepts configured source roots and/or normalized evidence indexes.
It never assumes a user-specific workspace layout and writes only to ``--out``.
"""
from __future__ import annotations

try:  # pragma: no cover - import shape depends on package vs direct-script use
    from ..console import emit
except ImportError:  # direct execution: no parent package to resolve against.
    # v9.7.407: a bare-script run (documented for workbook_schema_check.py) has neither a
    # parent package NOR the bundle root on sys.path, so put the root there first.
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from mamey.console import emit

import argparse
import csv
try:
    from ..csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping, Sequence


CONTRACT_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "mode_b"
    / "modeb_evidence_stream_contract.json"
)

BINDING_SCORE = {
    "ABSENT": 0,
    "UNBOUND": 1,
    "STRAIN_ONLY": 2,
    "ALIAS_BOUND": 3,
    "EXACT_LOCUS": 4,
}

_BGC_RE = re.compile(r"\bBGC[_ -]?(\d{1,4})\b", re.I)
_FULL_NODE_RE = re.compile(r"\b(NODE_\d+_length_\d+_cov_[0-9.]+)", re.I)
_NODE_RE = re.compile(r"\b(NODE_\d+)\b", re.I)
_REGION_RE = re.compile(r"\bregion[_ -]?(\d{1,4})\b", re.I)

_CLASSIFICATION_PRIORITY = (
    "locus_map_data", "locus_map", "blastp_per_gene", "kcb_mibig",
    "clusterblast", "domains_hmm", "selected_gene", "bigscape_gcf",
    "resistance", "prior_modeb_card", "qa_receipt", "literature_context",
    "thesis_context", "strain_phenotype", "antismash_region",
    "gene_inventory", "inventory_identity",
)

_STRAIN_FIELDS = ("strain", "strain_id", "Strain", "Strain_ID")
_BGC_FIELDS = ("bgc", "bgc_id", "BGC", "BGC_ID", "BGC_number")
_NODE_FIELDS = (
    "full_node", "node", "node_id", "contig", "assembly_locator",
    "region_member", "source_gbk",
)
_REGION_FIELDS = ("region", "region_id", "antismash_region", "region_number")


@dataclass(frozen=True)
class InventoryLocus:
    strain: str
    bgc: str
    full_node: str
    region: str
    exact_locus: str
    folder_path: str = ""
    products: str = ""


@dataclass(frozen=True)
class EvidenceObservation:
    channel: str
    source_label: str
    source_path: str
    source_sha256: str
    source_bytes: int
    strain: str = ""
    bgc: str = ""
    full_node: str = ""
    region: str = ""
    binding_state: str = "UNBOUND"
    exact_locus: str = ""
    record_count: int = 1
    freshness_state: str = "UNVERIFIED"
    notes: str = ""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _first(row: Mapping[str, object], names: Sequence[str]) -> str:
    for name in names:
        value = row.get(name)
        if value not in (None, ""):
            return str(value).strip()
    return ""


def normalize_strain(value: object) -> str:
    text = str(value or "").strip()
    # Inventory/evidence-index fields may use any portable public strain label.
    # Do not guess a generic id out of a path; path discovery resolves against
    # the actual inventory labels in _Resolver.find_strain().
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", text):
        return text.upper()
    return ""


def normalize_bgc(value: object) -> str:
    match = _BGC_RE.search(str(value or ""))
    return f"BGC{int(match.group(1)):03d}" if match else ""


def normalize_region(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    match = _REGION_RE.search(text)
    if match:
        return f"region{int(match.group(1)):03d}"
    if text.isdigit():
        return f"region{int(text):03d}"
    return ""


def normalize_node(value: object) -> str:
    text = str(value or "").strip().replace(".region", " region")
    match = _FULL_NODE_RE.search(text)
    return match.group(1).upper() if match else ""


def _node_token(value: str) -> str:
    match = _NODE_RE.search(value or "")
    return match.group(1).upper() if match else ""


def load_contract(path: str | Path | None = None) -> dict:
    contract_path = Path(path) if path else CONTRACT_PATH
    data = json.loads(contract_path.read_text(encoding="utf-8"))
    ids = [stream["id"] for stream in data.get("streams", [])]
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("Mode B evidence contract must contain unique stream ids")
    for stream in data["streams"]:
        if not stream.get("patterns"):
            raise ValueError(f"Stream {stream['id']} has no discovery patterns")
        for pattern in stream["patterns"]:
            re.compile(pattern, re.I)
    return data


def _sniff_delimiter(path: Path) -> str:
    if path.suffix.lower() == ".tsv":
        return "\t"
    try:
        sample = path.read_text(encoding="utf-8", errors="replace")[:8192]
        return csv.Sniffer().sniff(sample, delimiters=",\t").delimiter
    except (csv.Error, OSError):
        return ","


def _read_table(path: Path) -> list[dict[str, str]]:
    delimiter = _sniff_delimiter(path)
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=delimiter))


def load_inventory(path: str | Path) -> list[InventoryLocus]:
    inventory_path = Path(path)
    rows = _read_table(inventory_path)
    loci: list[InventoryLocus] = []
    seen: set[tuple[str, str]] = set()
    exact_seen: set[tuple[str, str, str]] = set()
    for line_number, row in enumerate(rows, 2):
        strain = normalize_strain(_first(row, _STRAIN_FIELDS))
        bgc = normalize_bgc(_first(row, _BGC_FIELDS))
        full_node = normalize_node(_first(row, _NODE_FIELDS))
        region = normalize_region(_first(row, _REGION_FIELDS))
        if not strain or not bgc:
            raise ValueError(f"Inventory row {line_number} lacks strain/BGC identity")
        alias_key = (strain, bgc)
        if alias_key in seen:
            raise ValueError(f"Inventory alias is not unique: {strain} {bgc}")
        seen.add(alias_key)
        if full_node and region:
            exact_key = (strain, full_node, region)
            if exact_key in exact_seen:
                raise ValueError(f"Inventory exact locus is duplicated: {'|'.join(exact_key)}")
            exact_seen.add(exact_key)
        exact_locus = _first(row, ("exact_locus",))
        if exact_locus:
            parts = [part.strip() for part in exact_locus.split("|")]
            if len(parts) != 3:
                raise ValueError(f"Inventory row {line_number} has malformed exact_locus")
            exact_identity = (
                normalize_strain(parts[0]),
                normalize_node(parts[1]),
                normalize_region(parts[2]),
            )
            if exact_identity != (strain, full_node, region):
                raise ValueError(
                    f"Inventory row {line_number} exact_locus conflicts with strain/node/region columns"
                )
        else:
            exact_locus = f"{strain}|{full_node or 'NODE_UNRESOLVED'}|{region or 'REGION_UNRESOLVED'}"
        loci.append(InventoryLocus(
            strain=strain,
            bgc=bgc,
            full_node=full_node,
            region=region,
            exact_locus=exact_locus,
            folder_path=_first(row, ("folder_path", "output_folder")),
            products=_first(row, ("products", "product", "product_class", "Product")),
        ))
    return loci


def _compile_streams(contract: Mapping[str, object]) -> list[tuple[dict, list[re.Pattern[str]]]]:
    return [
        (dict(stream), [re.compile(pattern, re.I) for pattern in stream["patterns"]])
        for stream in contract["streams"]
    ]


def classify_path(path_text: str, contract: Mapping[str, object]) -> str:
    normalized = path_text.replace("\\", "/")
    compiled = {stream["id"]: (stream, patterns) for stream, patterns in _compile_streams(contract)}
    ordered = [compiled[stream_id] for stream_id in _CLASSIFICATION_PRIORITY if stream_id in compiled]
    ordered.extend(value for key, value in compiled.items() if key not in _CLASSIFICATION_PRIORITY)
    for stream, patterns in ordered:
        if any(pattern.search(normalized) for pattern in patterns):
            return stream["id"]
    return ""


def extract_identity(text: str) -> tuple[str, str, str, str]:
    strain = normalize_strain(text)
    bgc = normalize_bgc(text)
    full_node = normalize_node(text)
    region = normalize_region(text)
    return strain, bgc, full_node, region


class _Resolver:
    def __init__(self, loci: Sequence[InventoryLocus]):
        self.by_alias = {(locus.strain, locus.bgc): locus for locus in loci}
        self.by_exact = {
            (locus.strain, locus.full_node, locus.region): locus
            for locus in loci if locus.full_node and locus.region
        }
        self.by_strain: dict[str, list[InventoryLocus]] = defaultdict(list)
        for locus in loci:
            self.by_strain[locus.strain].append(locus)
        self.strain_ids = sorted(self.by_strain, key=len, reverse=True)

    def find_strain(self, text: str) -> str:
        for strain in self.strain_ids:
            if re.search(rf"(?<![A-Za-z0-9]){re.escape(strain)}(?![A-Za-z0-9])", text, re.I):
                return strain
        return normalize_strain(text)

    def bind(
        self,
        strain: str,
        bgc: str,
        full_node: str,
        region: str,
    ) -> tuple[str, InventoryLocus | None, str]:
        strain = normalize_strain(strain)
        bgc = normalize_bgc(bgc)
        full_node = normalize_node(full_node)
        region = normalize_region(region)
        if strain and full_node and region:
            locus = self.by_exact.get((strain, full_node, region))
            if locus:
                if bgc and bgc != locus.bgc:
                    return "UNBOUND", None, "alias conflicts with exact locus"
                return "EXACT_LOCUS", locus, "full assembly node and region match"
        if strain and bgc:
            locus = self.by_alias.get((strain, bgc))
            if locus:
                if full_node and _node_token(full_node) and _node_token(full_node) != _node_token(locus.full_node):
                    return "UNBOUND", None, "node token conflicts with inventory alias"
                if region and locus.region and region != locus.region:
                    return "UNBOUND", None, "region conflicts with inventory alias"
                return "ALIAS_BOUND", locus, "strain and BGC alias match; exact locator not established by artifact"
        if strain and strain in self.by_strain:
            return "STRAIN_ONLY", None, "strain match only; do not localize to a BGC"
        return "UNBOUND", None, "no inventory identity match"


def _observation(
    *,
    channel: str,
    source_label: str,
    path: Path,
    resolver: _Resolver,
    strain: str,
    bgc: str,
    full_node: str,
    region: str,
    record_count: int = 1,
    freshness_state: str = "UNVERIFIED",
    notes: str = "",
    digest: str | None = None,
) -> EvidenceObservation:
    binding, locus, binding_note = resolver.bind(strain, bgc, full_node, region)
    return EvidenceObservation(
        channel=channel,
        source_label=source_label,
        source_path=str(path.resolve()),
        source_sha256=digest or _sha256(path),
        source_bytes=path.stat().st_size,
        strain=locus.strain if locus else normalize_strain(strain),
        bgc=locus.bgc if locus else normalize_bgc(bgc),
        full_node=locus.full_node if locus and binding == "EXACT_LOCUS" else normalize_node(full_node),
        region=locus.region if locus and binding == "EXACT_LOCUS" else normalize_region(region),
        binding_state=binding,
        exact_locus=locus.exact_locus if locus and binding in {"EXACT_LOCUS", "ALIAS_BOUND"} else "",
        record_count=record_count,
        freshness_state=freshness_state or "UNVERIFIED",
        notes="; ".join(item for item in (notes, binding_note) if item),
    )


def _table_identity_groups(path: Path, max_rows: int = 250000) -> Counter[tuple[str, str, str, str]]:
    groups: Counter[tuple[str, str, str, str]] = Counter()
    delimiter = _sniff_delimiter(path)
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        if not reader.fieldnames:
            return groups
        has_identity = any(name in reader.fieldnames for name in _STRAIN_FIELDS + _BGC_FIELDS + _NODE_FIELDS + _REGION_FIELDS)
        if not has_identity:
            return groups
        for index, row in enumerate(reader):
            if index >= max_rows:
                break
            strain = normalize_strain(_first(row, _STRAIN_FIELDS))
            bgc = normalize_bgc(_first(row, _BGC_FIELDS))
            node_value = _first(row, _NODE_FIELDS)
            region_value = _first(row, _REGION_FIELDS)
            full_node = normalize_node(node_value)
            region = normalize_region(region_value or node_value)
            if any((strain, bgc, full_node, region)):
                groups[(strain, bgc, full_node, region)] += 1
    return groups


def discover_evidence(
    loci: Sequence[InventoryLocus],
    contract: Mapping[str, object],
    source_roots: Sequence[tuple[str, Path]],
    *,
    inspect_tables: bool = True,
    table_max_bytes: int = 20_000_000,
) -> list[EvidenceObservation]:
    resolver = _Resolver(loci)
    observations: list[EvidenceObservation] = []
    seen_files: set[Path] = set()
    for source_label, source_root in source_roots:
        root = source_root.resolve()
        if not root.exists():
            raise FileNotFoundError(root)
        if root.is_file():
            files: list[Path] = [root]
        else:
            # RGLOB-SEAL-COVERAGE (v9.7.409): ``Path.rglob`` swallows a per-directory
            # OSError, so an unreadable/unlistable evidence subtree would silently drop out
            # of the scan -- and a Mode B card could then assert the *absence* of evidence
            # that in fact exists but simply could not be read. Walk with an ``onerror`` that
            # re-raises so an unreadable evidence subtree fails closed (matching the existing
            # FileNotFoundError contract for a missing root) instead of under-returning.
            import os  # local: module-level `os` is only imported on the direct-script fallback path.

            def _onerror(exc: OSError) -> None:
                raise exc

            walked: list[Path] = []
            for dirpath, dirnames, filenames in os.walk(root, onerror=_onerror, followlinks=False):
                base = Path(dirpath)
                walked.extend(base / name for name in dirnames)
                walked.extend(base / name for name in filenames)
            files = sorted(walked)
        for path in files:
            if not path.is_file() or path.name.startswith(".") or path.name == ".DS_Store":
                continue
            resolved = path.resolve()
            if resolved in seen_files:
                continue
            seen_files.add(resolved)
            relative = path.name if root.is_file() else str(path.relative_to(root))
            channel = classify_path(relative, contract)
            if not channel:
                continue
            digest = _sha256(path)
            path_identity = extract_identity(relative)
            if not path_identity[0]:
                path_identity = (resolver.find_strain(relative), *path_identity[1:])
            table_groups: Counter[tuple[str, str, str, str]] = Counter()
            if (
                inspect_tables
                and path.suffix.lower() in {".csv", ".tsv"}
                and path.stat().st_size <= table_max_bytes
            ):
                try:
                    table_groups = _table_identity_groups(path)
                except (csv.Error, OSError, UnicodeError):
                    table_groups = Counter()
            if table_groups:
                for identity, count in sorted(table_groups.items()):
                    merged = tuple(identity[i] or path_identity[i] for i in range(4))
                    observations.append(_observation(
                        channel=channel,
                        source_label=source_label,
                        path=path,
                        resolver=resolver,
                        strain=merged[0], bgc=merged[1], full_node=merged[2], region=merged[3],
                        record_count=count,
                        notes="header-aware tabular row binding",
                        digest=digest,
                    ))
            else:
                observations.append(_observation(
                    channel=channel,
                    source_label=source_label,
                    path=path,
                    resolver=resolver,
                    strain=path_identity[0], bgc=path_identity[1],
                    full_node=path_identity[2], region=path_identity[3],
                    notes="path/content-name discovery candidate",
                    digest=digest,
                ))
    return _deduplicate_observations(observations)


def load_evidence_index(
    path: str | Path,
    loci: Sequence[InventoryLocus],
    *,
    source_label: str = "evidence_index",
) -> list[EvidenceObservation]:
    index_path = Path(path)
    resolver = _Resolver(loci)
    rows = _read_table(index_path)
    observations: list[EvidenceObservation] = []
    for line_number, row in enumerate(rows, 2):
        channel = _first(row, ("channel", "evidence_stream", "stream"))
        artifact_text = _first(row, ("source_path", "path", "artifact_path"))
        if not channel or not artifact_text:
            raise ValueError(f"Evidence index row {line_number} lacks channel/path")
        artifact = Path(artifact_text).expanduser()
        if not artifact.is_absolute():
            artifact = index_path.parent / artifact
        if not artifact.is_file():
            raise FileNotFoundError(artifact)
        requested_binding = _first(row, ("binding_state",))
        obs = _observation(
            channel=channel,
            source_label=_first(row, ("source_label",)) or source_label,
            path=artifact,
            resolver=resolver,
            strain=_first(row, _STRAIN_FIELDS),
            bgc=_first(row, _BGC_FIELDS),
            full_node=_first(row, _NODE_FIELDS),
            region=_first(row, _REGION_FIELDS),
            record_count=int(_first(row, ("record_count",)) or 1),
            freshness_state=_first(row, ("freshness_state",)) or "UNVERIFIED",
            notes=_first(row, ("notes",)),
        )
        if requested_binding and requested_binding != obs.binding_state:
            raise ValueError(
                f"Evidence index row {line_number} requested {requested_binding} but resolver established {obs.binding_state}"
            )
        observations.append(obs)
    return _deduplicate_observations(observations)


def _deduplicate_observations(observations: Iterable[EvidenceObservation]) -> list[EvidenceObservation]:
    best: dict[tuple[str, str, str, str, str, str], EvidenceObservation] = {}
    for obs in observations:
        key = (obs.channel, obs.source_path, obs.strain, obs.bgc, obs.full_node, obs.region)
        prior = best.get(key)
        if not prior or BINDING_SCORE[obs.binding_state] > BINDING_SCORE[prior.binding_state]:
            best[key] = obs
    return sorted(best.values(), key=lambda obs: (obs.strain, obs.bgc, obs.channel, obs.source_path))


def _best_state(observations: Iterable[EvidenceObservation]) -> tuple[str, int, str]:
    rows = list(observations)
    if not rows:
        return "ABSENT", 0, "UNVERIFIED"
    best = max(rows, key=lambda obs: BINDING_SCORE[obs.binding_state])
    count = sum(obs.record_count for obs in rows)
    freshness = "CURRENT" if any(obs.freshness_state == "CURRENT" for obs in rows) else (
        "STALE" if rows and all(obs.freshness_state == "STALE" for obs in rows) else "UNVERIFIED"
    )
    return best.binding_state, count, freshness


def build_availability(
    loci: Sequence[InventoryLocus],
    observations: Sequence[EvidenceObservation],
    contract: Mapping[str, object],
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    stream_ids = [stream["id"] for stream in contract["streams"]]
    by_alias: dict[tuple[str, str, str], list[EvidenceObservation]] = defaultdict(list)
    by_strain: dict[tuple[str, str], list[EvidenceObservation]] = defaultdict(list)
    for obs in observations:
        if obs.strain and obs.bgc:
            by_alias[(obs.strain, obs.bgc, obs.channel)].append(obs)
        elif obs.strain and obs.binding_state == "STRAIN_ONLY":
            by_strain[(obs.strain, obs.channel)].append(obs)

    bgc_rows: list[dict[str, object]] = []
    section_rows: list[dict[str, object]] = []
    for locus in loci:
        state_by_stream: dict[str, str] = {}
        count_by_stream: dict[str, int] = {}
        freshness_by_stream: dict[str, str] = {}
        for stream_id in stream_ids:
            alias_rows = by_alias.get((locus.strain, locus.bgc, stream_id), [])
            strain_rows = by_strain.get((locus.strain, stream_id), [])
            state, count, freshness = _best_state(alias_rows or strain_rows)
            state_by_stream[stream_id] = state
            count_by_stream[stream_id] = count
            freshness_by_stream[stream_id] = freshness

        # The authoritative inventory row itself establishes the identity channel.
        state_by_stream["inventory_identity"] = "EXACT_LOCUS" if locus.full_node and locus.region else "ALIAS_BOUND"
        count_by_stream["inventory_identity"] = 1
        freshness_by_stream["inventory_identity"] = "CURRENT"

        gene_source_score = max(
            BINDING_SCORE[state_by_stream.get("gene_inventory", "ABSENT")],
            BINDING_SCORE[state_by_stream.get("antismash_region", "ABSENT")],
        )
        if BINDING_SCORE[state_by_stream["inventory_identity"]] < BINDING_SCORE["EXACT_LOCUS"]:
            writing_gate = "HOLD_IDENTITY_UNRESOLVED"
        elif gene_source_score < BINDING_SCORE["ALIAS_BOUND"]:
            writing_gate = "HOLD_MISSING_GENE_LEVEL_SOURCE"
        else:
            writing_gate = "PASS_FOR_GAP_AWARE_AUTHORING"

        blastp_state = state_by_stream.get("blastp_per_gene", "ABSENT")
        blastp_freshness = freshness_by_stream.get("blastp_per_gene", "UNVERIFIED")
        if BINDING_SCORE[blastp_state] < BINDING_SCORE["ALIAS_BOUND"]:
            promotion_gate = "HOLD_BLASTP_UNAVAILABLE_OR_UNBOUND"
        elif blastp_freshness != "CURRENT":
            promotion_gate = "HOLD_BLASTP_FRESHNESS_UNVERIFIED"
        else:
            promotion_gate = "ELIGIBLE_FOR_SEPARATE_INTERPRETIVE_REVIEW"

        if writing_gate.startswith("HOLD"):
            work_state = "NEEDS_EVIDENCE_ASSEMBLY"
        elif all(BINDING_SCORE[state_by_stream.get(name, "ABSENT")] >= BINDING_SCORE["ALIAS_BOUND"]
                 for name in ("blastp_per_gene", "domains_hmm", "locus_map")):
            work_state = "EVIDENCE_RICH_REVIEW_CANDIDATE"
        else:
            work_state = "GAP_AWARE_REVIEW_CANDIDATE"

        row: dict[str, object] = {
            "strain": locus.strain,
            "bgc": locus.bgc,
            "full_node": locus.full_node,
            "region": locus.region,
            "exact_locus": locus.exact_locus,
            "products": locus.products,
            "folder_path": locus.folder_path,
            "work_state": work_state,
            "writing_gate": writing_gate,
            "promotion_gate": promotion_gate,
        }
        for stream_id in stream_ids:
            row[f"{stream_id}_state"] = state_by_stream[stream_id]
            row[f"{stream_id}_records"] = count_by_stream[stream_id]
        bgc_rows.append(row)

        for section_number in range(1, 31):
            section = str(section_number)
            supporting = [
                stream["id"] for stream in contract["streams"]
                if section in stream.get("sections", [])
            ]
            exact_or_alias = [
                stream_id for stream_id in supporting
                if BINDING_SCORE[state_by_stream.get(stream_id, "ABSENT")] >= BINDING_SCORE["ALIAS_BOUND"]
            ]
            strain_only = [
                stream_id for stream_id in supporting
                if state_by_stream.get(stream_id) == "STRAIN_ONLY"
            ]
            if exact_or_alias:
                section_state = "EVIDENCE_AVAILABLE_REQUIRES_INTERPRETATION"
            elif strain_only:
                section_state = "CONTEXT_ONLY_DO_NOT_LOCALIZE"
            else:
                section_state = "WRITE_EXPLICIT_GAP_OR_HOLD"
            section_rows.append({
                "strain": locus.strain,
                "bgc": locus.bgc,
                "exact_locus": locus.exact_locus,
                "section": section,
                "section_state": section_state,
                "available_streams": ";".join(exact_or_alias),
                "context_only_streams": ";".join(strain_only),
                "claim_ceiling": contract["claim_ceiling"],
            })

    strain_rows: list[dict[str, object]] = []
    loci_by_strain: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in bgc_rows:
        loci_by_strain[str(row["strain"])].append(row)
    for strain, rows in sorted(loci_by_strain.items()):
        strain_row: dict[str, object] = {
            "strain": strain,
            "bgc_count": len(rows),
            "evidence_rich_review_candidates": sum(r["work_state"] == "EVIDENCE_RICH_REVIEW_CANDIDATE" for r in rows),
            "gap_aware_review_candidates": sum(r["work_state"] == "GAP_AWARE_REVIEW_CANDIDATE" for r in rows),
            "needs_evidence_assembly": sum(r["work_state"] == "NEEDS_EVIDENCE_ASSEMBLY" for r in rows),
        }
        for stream_id in stream_ids:
            state_field = f"{stream_id}_state"
            strain_row[f"{stream_id}_exact_or_alias_bgcs"] = sum(
                BINDING_SCORE[str(r[state_field])] >= BINDING_SCORE["ALIAS_BOUND"] for r in rows
            )
            strain_row[f"{stream_id}_context_only_bgcs"] = sum(r[state_field] == "STRAIN_ONLY" for r in rows)
        strain_rows.append(strain_row)
    return bgc_rows, strain_rows, section_rows


def _atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    """AUDIT_374: tmp-sibling + os.replace, so a crash mid-write never leaves a
    truncated Mode B availability deliverable on disk (matches mamey/packaging.py's helper).
    Every write in this module feeds `modeb_availability_manifest.json`'s own sha256 receipt
    (write_outputs() below) -- a half-written sibling file would silently corrupt that receipt
    too, since the manifest is written last and its hashes would describe a file no crash
    actually produced."""
    import os
    path = Path(path)
    tmp = str(path) + ".tmp"
    try:
        with open(tmp, "w", encoding=encoding, newline="") as fh:
            fh.write(text)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    os.replace(tmp, str(path))


def _write_tsv(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    import io as _io
    buf = _io.StringIO()
    writer = _SafeDictWriter(buf, fieldnames=fieldnames, delimiter="\t", lineterminator="\n")
    if fieldnames:
        writer.writeheader()
        writer.writerows(rows)
    _atomic_write_text(path, buf.getvalue())


def _render_summary(
    loci: Sequence[InventoryLocus],
    observations: Sequence[EvidenceObservation],
    bgc_rows: Sequence[Mapping[str, object]],
    strain_rows: Sequence[Mapping[str, object]],
    contract: Mapping[str, object],
) -> str:
    work_counts = Counter(str(row["work_state"]) for row in bgc_rows)
    lines = [
        "# Mode B evidence-availability audit",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "> This is an availability and provenance audit, not a biological interpretation. "
        "Missing or unbound evidence is not biological absence.",
        "",
        "## Coverage",
        "",
        f"- Strains: {len(strain_rows)}",
        f"- BGC loci: {len(loci)}",
        f"- Evidence observations: {len(observations)}",
        f"- Evidence-rich review candidates: {work_counts['EVIDENCE_RICH_REVIEW_CANDIDATE']}",
        f"- Gap-aware review candidates: {work_counts['GAP_AWARE_REVIEW_CANDIDATE']}",
        f"- Need evidence assembly: {work_counts['NEEDS_EVIDENCE_ASSEMBLY']}",
        "",
        "## Stream coverage",
        "",
        "| Stream | Exact/alias BGCs | Context-only BGCs |",
        "|---|---:|---:|",
    ]
    for stream in contract["streams"]:
        stream_id = stream["id"]
        exact_alias = sum(
            BINDING_SCORE[str(row[f"{stream_id}_state"])] >= BINDING_SCORE["ALIAS_BOUND"]
            for row in bgc_rows
        )
        context = sum(row[f"{stream_id}_state"] == "STRAIN_ONLY" for row in bgc_rows)
        lines.append(f"| {stream['label']} | {exact_alias} | {context} |")
    lines.extend([
        "",
        "## Authoring rule",
        "",
        "A card may enter gap-aware authoring only when the canonical exact locus and a gene-level source are bound. "
        "Promotion remains held when exact-current per-gene BLASTp is absent, unbound, stale, or freshness-unverified. "
        "Strain-level phenotype and thesis context may inform context sections but cannot be localized to a BGC without an exact binding.",
        "",
        f"Claim ceiling: {contract['claim_ceiling']}",
        "",
    ])
    return "\n".join(lines)


def write_outputs(
    outdir: str | Path,
    loci: Sequence[InventoryLocus],
    observations: Sequence[EvidenceObservation],
    contract: Mapping[str, object],
) -> dict:
    output = Path(outdir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    bgc_rows, strain_rows, section_rows = build_availability(loci, observations, contract)
    evidence_path = output / "modeb_evidence_observations.tsv"
    bgc_path = output / "modeb_bgc_availability.tsv"
    strain_path = output / "modeb_strain_availability.tsv"
    section_path = output / "modeb_section_plan.tsv"
    summary_path = output / "MODEB_AVAILABILITY_SUMMARY.md"
    _write_tsv(evidence_path, [asdict(obs) for obs in observations])
    _write_tsv(bgc_path, bgc_rows)
    _write_tsv(strain_path, strain_rows)
    _write_tsv(section_path, section_rows)
    _atomic_write_text(
        summary_path,
        _render_summary(loci, observations, bgc_rows, strain_rows, contract),
    )
    files = [evidence_path, bgc_path, strain_path, section_path, summary_path]
    manifest = {
        "contract_id": contract["contract_id"],
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS",
        "strain_count": len(strain_rows),
        "bgc_count": len(bgc_rows),
        "observation_count": len(observations),
        "outputs": [
            {"path": str(path), "sha256": _sha256(path), "bytes": path.stat().st_size}
            for path in files
        ],
        "claim_ceiling": contract["claim_ceiling"],
    }
    manifest_path = output / "modeb_availability_manifest.json"
    _atomic_write_text(manifest_path, json.dumps(manifest, indent=2) + "\n")
    return manifest


def _parse_source_root(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("source root must be LABEL=PATH")
    label, raw_path = value.split("=", 1)
    if not label.strip() or not raw_path.strip():
        raise argparse.ArgumentTypeError("source root must be LABEL=PATH")
    return label.strip(), Path(raw_path).expanduser()


def availability_command(args) -> int:
    contract = load_contract(getattr(args, "contract", None))
    loci = load_inventory(args.inventory)
    observations: list[EvidenceObservation] = []
    source_roots = [_parse_source_root(value) for value in (getattr(args, "source_root", None) or [])]
    if source_roots:
        observations.extend(discover_evidence(
            loci,
            contract,
            source_roots,
            inspect_tables=not getattr(args, "no_table_inspection", False),
            table_max_bytes=getattr(args, "table_max_bytes", 20_000_000),
        ))
    for evidence_index in getattr(args, "evidence_index", None) or []:
        observations.extend(load_evidence_index(evidence_index, loci))
    observations = _deduplicate_observations(observations)
    manifest = write_outputs(args.out, loci, observations, contract)
    emit(json.dumps(manifest, indent=2))
    return 0


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--inventory", required=True, help="Header-keyed per-BGC CSV/TSV inventory")
    parser.add_argument(
        "--source-root", action="append", default=[], metavar="LABEL=PATH",
        help="Configurable evidence root to scan recursively; repeatable",
    )
    parser.add_argument(
        "--evidence-index", action="append", default=[], metavar="PATH",
        help="Normalized evidence index TSV; repeatable",
    )
    parser.add_argument("--contract", default=None, help="Override evidence-stream contract JSON")
    parser.add_argument("--out", required=True, help="Additive output directory")
    parser.add_argument("--no-table-inspection", action="store_true", default=False)
    parser.add_argument("--table-max-bytes", type=int, default=20_000_000)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    add_arguments(parser)
    return availability_command(parser.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
