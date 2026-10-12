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
_FULL_NODE_RE = re.compile(r"NODE_\d+_length_\d+_cov_\d+(?:\.\d+)?", re.I)

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
    "full_node", "contig", "Contig", "node", "node_id", "Node_ID",
    "assembly_locator", "Assembly_Locator", "region_member", "source_gbk", "Source_GBK",
)
_REGION_FIELDS = ("region", "Region", "region_id", "antismash_region", "antiSMASH_Region", "region_number")
_ATOMIC_NODE_FIELDS = ("full_node", "contig", "Contig", "node", "node_id", "Node_ID")
_DISPLAY_NODE_FIELDS = ("assembly_locator", "Assembly_Locator")
_MEMBER_FIELDS = ("region_member", "source_gbk", "Source_GBK")
_ATOM_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:+-]*")
_MEMBER_RE = re.compile(r"(.+)\.region(\d+)\.gbk", re.I)
_PATH_BGC_RE = re.compile(r"(?<![A-Za-z0-9])BGC[_ -]?(\d{1,4})(?![A-Za-z0-9])", re.I)
_UNRESOLVED_NODES = {"NODE_UNRESOLVED", "UNKNOWN_LOCUS", "UNRESOLVED"}


@dataclass(frozen=True)
class _Identity:
    """Typed identity before binding; invalid input is never reduced to missing.

    Raw identity fields stay internal, so fixed diagnostics do not echo an
    invalid/private payload into logs. Source rows remain the immutable record.
    """
    strain: str = ""
    bgc: str = ""
    full_node: str = ""
    region: str = ""
    node_token: str = ""
    diagnostics: tuple[str, ...] = ()
    supplied: frozenset[str] = frozenset()
    raw_fields: tuple[tuple[str, str], ...] = ()
    field_states: tuple[tuple[str, str], ...] = ()

    @property
    def components(self) -> tuple[str, str, str, str]:
        return self.strain, self.bgc, self.full_node, self.region



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
    identity_diagnostics: str = ""
    identity_field_states: str = ""


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
    # Portable strain labels are exact identifiers, including their spelling.
    # Case folding would silently merge independently named inventory strains.
    # Do not guess a generic id out of a path; path discovery resolves against
    # the actual inventory labels in _Resolver.find_strain().
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", text):
        return text
    return ""


def normalize_bgc(value: object) -> str:
    match = _BGC_RE.search(str(value or ""))
    return f"BGC{int(match.group(1)):03d}" if match else ""


def normalize_region(value: object) -> str:
    text = str(value or "").strip()
    match = re.fullmatch(r"(?:region[_ -]?)?(\d+)", text, re.I)
    return f"region{int(match.group(1)):03d}" if match and int(match.group(1)) > 0 else ""


def _atomic_node(value: object) -> tuple[str, str, str]:
    text = str(value or "").strip()
    if not text:
        return "", "", ""
    if _FULL_NODE_RE.fullmatch(text):
        return text.upper(), "", ""
    if re.fullmatch(r"NODE_\d+", text, re.I):
        return "", text.upper(), ""
    if re.match(r"NODE_\d+(?:_|$)", text, re.I):
        return "", "", "INCOMPLETE_NODE"
    if text.upper() in _UNRESOLVED_NODES:
        return "", "", "UNRESOLVED_SENTINEL"
    if not _ATOM_RE.fullmatch(text) or re.match(r"[A-Za-z]:", text):
        return "", "", "INVALID_CONTIG_ATOM"
    if _MEMBER_RE.fullmatch(text):
        return "", "", "MEMBER_IN_ATOMIC_FIELD"
    # Generic identifiers are exact, case-sensitive labels. In particular,
    # accession version and namespace are not guessed or coalesced.
    return text, "", ""


def normalize_node(value: object) -> str:
    """Normalize a complete *atomic field*, never search a filesystem path."""
    return _atomic_node(value)[0]


def _node_token(value: str) -> str:
    match = re.match(r"(NODE_\d+)(?:_length_|$)", value or "", re.I)
    return match.group(1).upper() if match else ""


def _member_identity(value: str) -> tuple[str, str, str, str]:
    """Return contig, region, short token, error from a region-member basename.

    Opaque whole-record names carry provenance only. Directory components can
    locate a file but never contribute contig identity.
    """
    if any(ord(c) < 32 for c in value) or "://" in value or "|" in value or "?" in value or "#" in value:
        return "", "", "", "INVALID_MEMBER_PATH"
    basename = value.replace("\\", "/").rsplit("/", 1)[-1]
    match = _MEMBER_RE.fullmatch(basename)
    if not match:
        error = "MALFORMED_REGION_MEMBER" if re.search(r"\.region\d+", basename, re.I) else ""
        return "", "", "", error
    if re.search(r"\.region\d+", match.group(1), re.I):
        return "", "", "", "AMBIGUOUS_REGION_MEMBER"
    node, token, error = _atomic_node(match.group(1))
    region = normalize_region(match.group(2))
    return node, region, token, error or ("INVALID_REGION" if not region else "")


def _collect_identity(row: Mapping[str, object]) -> _Identity:
    candidates: dict[str, list[str]] = {k: [] for k in ("strain", "bgc", "full_node", "region", "node_token")}
    diagnostics: list[str] = []
    raw: list[tuple[str, str]] = []
    states: list[tuple[str, str]] = []
    supplied: set[str] = set()
    native = None
    native_node_fields: set[str] = set()
    native_strain = _first(row, _STRAIN_FIELDS)
    inventory_roles = ("Contig", "Node_ID", "antiSMASH_Region", "BGC_ID")
    manifest_roles = ("contig", "node_id", "antismash_region", "bgc_id")
    if native_strain and (all(str(row.get(k) or "").strip() for k in inventory_roles)
                          or all(str(row.get(k) or "").strip() for k in manifest_roles)):
        try:
            try:
                from ..exact_identity import (ExactLocusIdentityError,
                    exact_locus_from_native_inventory_row, exact_locus_from_native_manifest_bgc)
            except ImportError:  # supported direct-script import shape
                from mamey.exact_identity import (ExactLocusIdentityError,
                    exact_locus_from_native_inventory_row, exact_locus_from_native_manifest_bgc)
            if all(str(row.get(k) or "").strip() for k in inventory_roles):
                native = exact_locus_from_native_inventory_row(native_strain, row)
                native_node_fields = {"Node_ID", "node_id"}
            else:
                native = exact_locus_from_native_manifest_bgc(native_strain, row)
                native_node_fields = {"node_id"}
        except ExactLocusIdentityError:
            # Do not echo the helper exception: diagnostics contain field roles,
            # never a potentially private raw locator or source payload.
            diagnostics.append("native_identity:PRODUCER_ROLE_CONFLICT")

    def add(field: str, component: str, value: str, error: str = "") -> None:
        supplied.add(component)
        if value:
            candidates[component].append(value)
        if error:
            diagnostics.append(f"{field}:{error}")

    for fields, component, normalizer in (
        (_STRAIN_FIELDS, "strain", normalize_strain),
        (_BGC_FIELDS, "bgc", normalize_bgc),
        (_REGION_FIELDS, "region", normalize_region),
    ):
        for field in fields:
            value = str(row.get(field) or "").strip()
            if not value:
                continue
            raw.append((field, value))
            normalized = normalizer(value)
            if component == "bgc" and not _BGC_RE.fullmatch(value):
                normalized = ""
            error = "INVALID_" + component.upper() if not normalized else ""
            add(field, component, normalized, error)
            states.append((field, "invalid" if error else "complete"))

    for field in _ATOMIC_NODE_FIELDS + _DISPLAY_NODE_FIELDS + _MEMBER_FIELDS:
        value = str(row.get(field) or "").strip()
        if not value:
            continue
        raw.append((field, value))
        if native and field in native_node_fields:
            states.append((field, "producer_normalized"))
            continue
        node = token = region = bgc = error = ""
        producer_display = False
        if field in _MEMBER_FIELDS:
            node, region, token, error = _member_identity(value)
            if not any((node, token, region, error)):
                states.append((field, "provenance_only"))
                continue
        elif field in _DISPLAY_NODE_FIELDS and " " in value:
            match = re.fullmatch(r"(\S+) (region\d+)(?: \((BGC\d{1,4})\))?", value, re.I)
            if match:
                display_node = match.group(1)
                region = normalize_region(match.group(2))
                bgc = normalize_bgc(match.group(3)) if match.group(3) else ""
                if (native and display_node == native.normalized_node_id
                        and region == normalize_region(native.region)
                        and (not bgc or bgc == normalize_bgc(native.bgc_alias))):
                    # Native display labels use the separately validated join
                    # token; the physical locator still comes from Contig.
                    node = normalize_node(native.full_contig)
                    producer_display = True
                else:
                    node, token, error = _atomic_node(display_node)
                if not region:
                    error = error or "INVALID_REGION"
            else:
                error = "INVALID_DISPLAY_LOCATOR"
        else:
            # Bare atomic assembly_locator is a supported legacy table shape.
            node, token, error = _atomic_node(value)
        add(field, "full_node", node, error)
        if token:
            candidates["node_token"].append(token)
        if region:
            add(field, "region", region)
        if bgc:
            add(field, "bgc", bgc)
        states.append((field, "invalid" if error else "producer_display" if producer_display
                       else "partial" if token else "complete"))

    values: dict[str, str] = {}
    for component, items in candidates.items():
        values[component] = items[0] if items else ""
        if len(set(items)) > 1:
            diagnostics.append(f"{component}:CONFLICT")
    if values["node_token"] and values["full_node"]:
        if _node_token(values["full_node"]) != values["node_token"]:
            diagnostics.append("full_node:SHORT_NODE_CONFLICT")
    exact = str(row.get("exact_locus") or "").strip()
    if exact:
        raw.append(("exact_locus", exact))
        parts = exact.split("|")
        expected = (values["strain"], values["full_node"], values["region"])
        if len(parts) != 3:
            diagnostics.append("exact_locus:MALFORMED")
        else:
            claimed = (normalize_strain(parts[0]), normalize_node(parts[1]), normalize_region(parts[2]))
            if not all(claimed) or claimed != expected:
                diagnostics.append("exact_locus:CONFLICT")
        states.append(("exact_locus", "invalid" if any(d.startswith("exact_locus:") for d in diagnostics) else "complete"))
    return _Identity(**values, diagnostics=tuple(sorted(set(diagnostics))),
                     supplied=frozenset(supplied), raw_fields=tuple(raw), field_states=tuple(states))


def _merge_identity(row: _Identity, path: _Identity) -> _Identity:
    """Fill genuinely missing components only; contradictions remain visible."""
    diagnostics = list(row.diagnostics + path.diagnostics)
    values: dict[str, str] = {}
    for component in ("strain", "bgc", "full_node", "region"):
        explicit, candidate = getattr(row, component), getattr(path, component)
        if explicit and candidate and explicit != candidate:
            diagnostics.append(f"{component}:PATH_CONFLICT")
        values[component] = explicit if component in row.supplied else candidate
    token = row.node_token or path.node_token
    if row.node_token and path.full_node and _node_token(path.full_node) != row.node_token:
        diagnostics.append("full_node:PATH_SHORT_NODE_CONFLICT")
    if token and values["full_node"] and _node_token(values["full_node"]) != token:
        diagnostics.append("full_node:SHORT_NODE_CONFLICT")
    return _Identity(**values, node_token=token,
                     diagnostics=tuple(sorted(set(diagnostics))), supplied=row.supplied | path.supplied,
                     raw_fields=row.raw_fields + path.raw_fields,
                     field_states=row.field_states + tuple(("path." + f, state) for f, state in path.field_states))


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
        identity = _collect_identity(row)
        strain, bgc, full_node, region = identity.components
        if identity.diagnostics:
            detail = "; ".join(identity.diagnostics)
            if any(d.startswith("exact_locus:") for d in identity.diagnostics):
                raise ValueError(f"Inventory row {line_number} exact_locus conflicts or is malformed: {detail}")
            raise ValueError(f"Inventory row {line_number} has invalid/conflicting identity fields: {detail}")
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


def _path_wrapper_end(text: str, strain: str = "", bgc: str = "") -> int:
    """Match exact strain spelling while retaining typed BGC case handling."""
    pattern = re.escape(strain) + "_" if strain else ""
    if bgc:
        pattern += "(?i:" + re.escape(bgc) + ")_"
    match = re.match(pattern, text) if pattern else None
    return match.end() if match else 0


def _path_identity(text: str, resolver: "_Resolver | None" = None) -> _Identity:
    """Inventory-bounded path discovery, separate from explicit row fields."""
    normalized = text.replace("\\", "/")
    basename = normalized.rsplit("/", 1)[-1]
    strains = resolver.find_strains(normalized) if resolver else []
    node, region, token, error = _member_identity(basename)
    literal_known = bool(resolver and any(l.full_node == node for l in resolver.by_alias.values()))
    alias_text = normalized.rsplit("/", 1)[0] if "/" in normalized else ""
    if not _MEMBER_RE.fullmatch(basename):
        alias_text += "/" + basename
    elif resolver and not literal_known:
        # A known BGC wrapper is metadata; an embedded BGC-looking substring in
        # a complete contig name is not. Match wrappers only at the beginning.
        for strain, bgc in resolver.by_alias:
            if (_path_wrapper_end(basename, strain, bgc)
                    or _path_wrapper_end(basename, bgc=bgc)):
                alias_text += "/" + bgc
    aliases = sorted({f"BGC{int(m.group(1)):03d}" for m in _PATH_BGC_RE.finditer(alias_text)})
    row: dict[str, str] = {}
    diagnostics: list[str] = []
    if len(strains) == 1:
        row["strain"] = strains[0]
    elif len(strains) > 1:
        diagnostics.append("path_strain:AMBIGUOUS")
    if len(aliases) == 1:
        row["bgc"] = aliases[0]
    elif len(aliases) > 1:
        diagnostics.append("path_bgc:AMBIGUOUS")
    # First prefer a literal member contig that exists in the inventory. For
    # legacy prefixed filenames, only strip an exact known strain/BGC wrapper.
    if resolver and not literal_known and _MEMBER_RE.fullmatch(basename):
        wrappers: set[tuple[str, str]] = set()
        if row.get("strain") and row.get("bgc"):
            wrappers.add((row["strain"], row["bgc"]))
        if row.get("bgc"):
            wrappers.add(("", row["bgc"]))
        if row.get("strain"):
            wrappers.add((row["strain"], ""))
        for strain, bgc in sorted(wrappers, key=lambda pair: sum(map(len, pair)), reverse=True):
            end = _path_wrapper_end(basename, strain, bgc)
            if end:
                node, region, token, error = _member_identity(basename[end:])
                break
    if node or token:
        row["full_node"] = node or token
    if region:
        row["region"] = region
    identity = _collect_identity(row)
    if error:
        diagnostics.append("path_member:" + error)
    return _Identity(**dict(zip(("strain", "bgc", "full_node", "region"), identity.components)),
                     node_token=identity.node_token,
                     diagnostics=tuple(sorted(set(identity.diagnostics + tuple(diagnostics)))),
                     supplied=identity.supplied, raw_fields=identity.raw_fields,
                     field_states=identity.field_states)


def extract_identity(text: str) -> tuple[str, str, str, str]:
    """Compatibility path candidate; generic strain is never guessed from a path."""
    return _path_identity(text).components


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

    def find_strains(self, text: str) -> list[str]:
        return [strain for strain in self.strain_ids
                if re.search(rf"(?<![A-Za-z0-9]){re.escape(strain)}(?![A-Za-z0-9])", text)]

    def find_strain(self, text: str) -> str:
        matches = self.find_strains(text)
        return matches[0] if len(matches) == 1 else ""

    def bind(
        self,
        strain: str,
        bgc: str,
        full_node: str,
        region: str,
        *,
        identity: _Identity | None = None,
    ) -> tuple[str, InventoryLocus | None, str, str]:
        identity = identity or _collect_identity({"strain": strain, "bgc": bgc, "full_node": full_node, "region": region})
        strain, bgc, full_node, region = identity.components
        supplied_node_token = identity.node_token
        if identity.diagnostics:
            return "UNBOUND", None, "identity fields invalid/conflicting: " + "; ".join(identity.diagnostics), ""
        if strain and full_node and region:
            locus = self.by_exact.get((strain, full_node, region))
            if locus:
                if bgc and bgc != locus.bgc:
                    return "UNBOUND", None, "alias conflicts with exact locus", "inventory:ALIAS_CONFLICT"
                return "EXACT_LOCUS", locus, "full contig label and region match", ""
        if strain and bgc:
            locus = self.by_alias.get((strain, bgc))
            if locus:
                if full_node and locus.full_node and full_node != locus.full_node:
                    return "UNBOUND", None, "full node conflicts with inventory alias", "inventory:FULL_CONTIG_CONFLICT"
                if supplied_node_token and locus.full_node and supplied_node_token != _node_token(locus.full_node):
                    return "UNBOUND", None, "node token conflicts with inventory alias or requires a contig crosswalk", "inventory:NODE_TOKEN_CONFLICT"
                if region and locus.region and region != locus.region:
                    return "UNBOUND", None, "region conflicts with inventory alias", "inventory:REGION_CONFLICT"
                return "ALIAS_BOUND", locus, "strain and BGC alias match; exact locator not established by artifact", ""
        if strain and strain in self.by_strain:
            return "STRAIN_ONLY", None, "strain match only; do not localize to a BGC", ""
        return "UNBOUND", None, "no inventory identity match", "inventory:NO_IDENTITY_MATCH"


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
    identity: _Identity | None = None,
) -> EvidenceObservation:
    identity = identity or _collect_identity({"strain": strain, "bgc": bgc, "full_node": full_node, "region": region})
    strain, bgc, full_node, region = identity.components
    binding, locus, binding_note, binding_diagnostic = resolver.bind(strain, bgc, full_node, region, identity=identity)
    return EvidenceObservation(
        channel=channel,
        source_label=source_label,
        source_path=str(path.resolve()),
        source_sha256=digest or _sha256(path),
        source_bytes=path.stat().st_size,
        strain=locus.strain if locus else normalize_strain(strain),
        bgc=locus.bgc if locus else normalize_bgc(bgc),
        full_node=locus.full_node if locus and binding == "EXACT_LOCUS" else full_node,
        region=locus.region if locus and binding == "EXACT_LOCUS" else normalize_region(region),
        binding_state=binding,
        exact_locus=locus.exact_locus if locus and binding in {"EXACT_LOCUS", "ALIAS_BOUND"} else "",
        record_count=record_count,
        freshness_state=freshness_state or "UNVERIFIED",
        notes="; ".join(item for item in (notes, binding_note) if item),
        identity_diagnostics="; ".join(identity.diagnostics + ((binding_diagnostic,) if binding_diagnostic else ())),
        identity_field_states="; ".join(f"{field}={state}" for field, state in identity.field_states),
    )


def _table_identity_groups(path: Path, max_rows: int = 250000) -> Counter[_Identity]:
    groups: Counter[_Identity] = Counter()
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
            identity = _collect_identity(row)
            if identity.raw_fields:
                groups[identity] += 1
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
            path_identity = _path_identity(relative, resolver)
            table_groups: Counter[_Identity] = Counter()
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
                for identity, count in sorted(table_groups.items(), key=lambda item: (item[0].components, item[0].diagnostics)):
                    merged = _merge_identity(identity, path_identity)
                    observations.append(_observation(
                        channel=channel,
                        source_label=source_label,
                        path=path,
                        resolver=resolver,
                        strain=merged.strain, bgc=merged.bgc, full_node=merged.full_node, region=merged.region,
                        identity=merged,
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
                    strain=path_identity.strain, bgc=path_identity.bgc,
                    full_node=path_identity.full_node, region=path_identity.region,
                    identity=path_identity,
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
        identity = _collect_identity(row)
        # Only a recognized region-member basename contributes source-path
        # identity. Arbitrary directory names and opaque files do not.
        member = _collect_identity({"region_member": artifact_text})
        identity = _merge_identity(identity, member)
        obs = _observation(
            channel=channel,
            source_label=_first(row, ("source_label",)) or source_label,
            path=artifact,
            resolver=resolver,
            strain=identity.strain, bgc=identity.bgc,
            full_node=identity.full_node, region=identity.region,
            identity=identity,
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
    best: dict[tuple[str, ...], EvidenceObservation] = {}
    for obs in observations:
        key = (obs.channel, obs.source_path, obs.strain, obs.bgc, obs.full_node, obs.region, obs.identity_diagnostics)
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
