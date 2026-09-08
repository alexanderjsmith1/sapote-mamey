"""Optional, offline, exact-locus Mode B gene-first exploration composer.

This module composes already-sealed package evidence.  It does not author a
Mode B card, perform biological inference, contact a network service, or change
the source package.  It emits a deterministic review surface only:

* a concise exploration synthesis;
* a transparently ranked important-gene review table;
* a channel-separated availability table; and
* exactly one highest-information next analysis.

The command fails before creating its output directory unless the complete
``strain / full node-or-contig / region / BGC alias`` identity matches the
package manifest and the target has a real, non-placeholder gene roster.
"""
from __future__ import annotations

import argparse
import csv
try:
    from ..csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import hashlib
import io
import json
import sys
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence


SCHEMA = "mamey.modeb-gene-first-exploration/1"
CLAIM_CEILING = (
    "Engineering exploration only. Similarity is not identity; capacity is not "
    "production; missing or unbound evidence is a workflow gap, not biological "
    "absence. Scientific acceptance, integration, release, and publication are "
    "separate owner decisions."
)

# Output order is the permanent channel-separation contract for this tool.
CHANNELS: tuple[tuple[str, str], ...] = (
    ("nr", "NCBI nr"),
    ("clusterednr", "ClusteredNR"),
    ("local_swissprot", "Local Swiss-Prot"),
    ("mibig", "MIBiG / KnownClusterBlast"),
    ("clusterblast", "ClusterBlast"),
    ("bigscape", "BiG-SCAPE"),
    ("rggmci", "RG-GMCI"),
    ("cohort", "Cohort comparison"),
    ("domain", "Domain / HMM"),
    ("literature", "Literature context"),
)
CHANNEL_IDS = {channel for channel, _label in CHANNELS}
HISTORICAL_CHANNEL = "historical_card"
EVIDENCE_STATES = {"BOUND", "UNBOUND", "MISSING", "NOT_RUN", "LEAD_ONLY"}

_NEXT_ANALYSIS_ORDER = (
    "nr", "local_swissprot", "clusterednr", "domain", "mibig",
    "clusterblast", "bigscape", "rggmci", "cohort", "literature",
)
_NEXT_ACTION = {
    "nr": "Ingest an offline, query-bound nr result for the highest-ranked unresolved gene.",
    "local_swissprot": "Compare the highest-ranked unresolved gene against the governed local Swiss-Prot snapshot.",
    "clusterednr": "Ingest a query-bound ClusteredNR result for the highest-ranked unresolved gene, keeping it separate from nr.",
    "domain": "Run or ingest the local domain/HMM pass for the highest-ranked gene lacking domain evidence.",
    "mibig": "Inspect the exact-locus per-gene MIBiG/KnownClusterBlast correspondence without converting similarity into product identity.",
    "clusterblast": "Inspect the exact-locus per-gene ClusterBlast correspondence as a separate comparison channel.",
    "bigscape": "Add the exact-locus BiG-SCAPE/GCF membership record as neighborhood context only.",
    "rggmci": "Review the exact-locus RG-GMCI pair evidence and its split-versus-paralogy guard.",
    "cohort": "Run the portable exact-locus cohort-protein comparison for the highest-ranked unresolved gene.",
    "literature": "Attach a hash-bound literature-context record at class or component scope without localizing phenotype to the locus.",
}


class GeneFirstHold(ValueError):
    """Typed, fail-closed refusal for an incomplete or conflicting input."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_write(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, path)
    except BaseException:
        if tmp.exists():
            tmp.unlink()
        raise


def _canonical_alias(value: object) -> str:
    text = str(value or "").strip().upper()
    if not re.fullmatch(r"BGC\d{3,4}", text):
        raise GeneFirstHold(
            "MODEB_GENE_FIRST_IDENTITY_HOLD: BGC alias must be canonical BGC### or BGC####"
        )
    return text


def _canonical_region(value: object) -> str:
    text = str(value or "").strip()
    match = re.fullmatch(r"region[_ -]?(\d{1,4})", text, re.I)
    if not match:
        raise GeneFirstHold(
            "MODEB_GENE_FIRST_IDENTITY_HOLD: antiSMASH region is missing or malformed"
        )
    return f"region{int(match.group(1)):03d}"


def _full_node_or_contig(value: object) -> str:
    text = str(value or "").strip()
    if not text or "/" in text or "\\" in text or re.search(r"[\x00-\x1f]", text):
        raise GeneFirstHold(
            "MODEB_GENE_FIRST_IDENTITY_HOLD: full node-or-contig is missing or unsafe"
        )
    if text.upper().startswith("NODE_") and not re.fullmatch(
        r"NODE_\d+_length_\d+_cov_[0-9.]+", text, re.I
    ):
        raise GeneFirstHold(
            "MODEB_GENE_FIRST_IDENTITY_HOLD: shortened NODE token is prohibited"
        )
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:+-]{1,254}", text):
        raise GeneFirstHold(
            "MODEB_GENE_FIRST_IDENTITY_HOLD: full node-or-contig token is malformed"
        )
    return text


def _manifest_region(bgc: Mapping[str, Any]) -> str:
    region_text = bgc.get("antismash_region") or bgc.get("region")
    region_number = bgc.get("region_number")
    from_text = _canonical_region(region_text) if region_text else ""
    from_number = _canonical_region(f"region{int(region_number):03d}") if region_number not in (None, "") else ""
    if from_text and from_number and from_text != from_number:
        raise GeneFirstHold(
            "MODEB_GENE_FIRST_IDENTITY_HOLD: manifest region fields conflict"
        )
    if not (from_text or from_number):
        raise GeneFirstHold(
            "MODEB_GENE_FIRST_IDENTITY_HOLD: manifest lacks antiSMASH region"
        )
    return from_text or from_number


def _identity_token(identity: Mapping[str, str]) -> str:
    """Filesystem-safe four-field identity in permanent display order."""
    parts = [identity["strain"], identity["full_node"], identity["region"], identity["bgc_alias"]]
    token = "__".join(re.sub(r"[^A-Za-z0-9_.-]+", "_", part) for part in parts)
    if len(token) > 180:
        raise GeneFirstHold(
            "MODEB_GENE_FIRST_OUTPUT_REFUSED: exact identity is too long for portable artifact names"
        )
    return token


def resolve_identity(
    package: Path, *, strain: str, full_node: str, region: str, bgc_alias: str
) -> tuple[dict[str, str], dict[str, Any], dict[str, Any]]:
    manifest_path = package / "manifest.json"
    if not manifest_path.is_file():
        raise GeneFirstHold("MODEB_GENE_FIRST_SOURCE_HOLD: manifest.json is missing")
    from ..scan_channel_alias import load_bound_scan_manifest, ScanChannelBindingError
    try:
        manifest, _, _ = load_bound_scan_manifest(manifest_path)
    except (OSError, ScanChannelBindingError) as exc:
        raise GeneFirstHold(
            f"MODEB_GENE_FIRST_SOURCE_HOLD: manifest.json is unreadable ({type(exc).__name__})"
        ) from exc
    requested_strain = str(strain or "").strip()
    manifest_strain = str(manifest.get("strain_id") or "").strip()
    if not requested_strain or requested_strain != manifest_strain:
        raise GeneFirstHold(
            "MODEB_GENE_FIRST_IDENTITY_HOLD: strain is missing or conflicts with manifest"
        )
    requested_node = _full_node_or_contig(full_node)
    requested_region = _canonical_region(region)
    requested_alias = _canonical_alias(bgc_alias)
    matches = [
        bgc for bgc in (manifest.get("bgcs") or [])
        if str(bgc.get("bgc_id") or "").strip().upper() == requested_alias
    ]
    if len(matches) != 1:
        raise GeneFirstHold(
            "MODEB_GENE_FIRST_IDENTITY_HOLD: BGC alias does not resolve uniquely in manifest"
        )
    bgc = matches[0]
    manifest_node = _full_node_or_contig(bgc.get("contig") or bgc.get("node_id"))
    manifest_region = _manifest_region(bgc)
    if requested_node != manifest_node or requested_region != manifest_region:
        raise GeneFirstHold(
            "MODEB_GENE_FIRST_IDENTITY_HOLD: node-or-contig or region conflicts with manifest"
        )
    identity = {
        "strain": manifest_strain,
        "full_node": manifest_node,
        "region": manifest_region,
        "bgc_alias": requested_alias,
        "exact_identity": " / ".join(
            (manifest_strain, manifest_node, manifest_region, requested_alias)
        ),
    }
    return identity, dict(bgc), manifest


def _one_gene_table(package: Path, explicit: str | Path | None) -> Path:
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if not path.is_file():
            raise GeneFirstHold("MODEB_GENE_FIRST_SOURCE_HOLD: --gene-table is not a file")
        return path
    candidates = sorted(package.glob("*_gene_by_gene_all_bgcs.csv"))
    if len(candidates) != 1:
        raise GeneFirstHold(
            "MODEB_GENE_FIRST_SOURCE_HOLD: expected exactly one *_gene_by_gene_all_bgcs.csv"
        )
    return candidates[0]


def load_gene_rows(path: Path, identity: Mapping[str, str]) -> list[dict[str, str]]:
    required = {
        "bgc_id", "locus_tag", "contig", "aa_length", "product_qualifier",
        "gene_function_inference", "sec_met_domains",
    }
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise GeneFirstHold(
                f"MODEB_GENE_FIRST_SOURCE_HOLD: gene table missing columns {sorted(missing)}"
            )
        rows = [dict(row) for row in reader if str(row.get("bgc_id") or "").upper() == identity["bgc_alias"]]
    if not rows:
        raise GeneFirstHold("MODEB_GENE_FIRST_SOURCE_HOLD: target has no gene rows")
    seen: set[str] = set()
    for row in rows:
        gene = str(row.get("locus_tag") or "").strip()
        if not gene or gene.endswith("_NOLOCUS"):
            raise GeneFirstHold(
                "MODEB_GENE_FIRST_SOURCE_HOLD: placeholder or missing locus tag is prohibited"
            )
        if gene in seen:
            raise GeneFirstHold(
                f"MODEB_GENE_FIRST_SOURCE_HOLD: duplicate target locus tag {gene}"
            )
        seen.add(gene)
        if str(row.get("contig") or "").strip() != identity["full_node"]:
            raise GeneFirstHold(
                f"MODEB_GENE_FIRST_IDENTITY_HOLD: gene {gene} contig conflicts with exact identity"
            )
        try:
            if int(float(str(row.get("aa_length") or ""))) <= 0:
                raise ValueError
        except ValueError as exc:
            raise GeneFirstHold(
                f"MODEB_GENE_FIRST_SOURCE_HOLD: gene {gene} lacks positive aa_length"
            ) from exc
    return rows


def _portable_locator(value: str) -> bool:
    text = value.strip()
    if text.startswith(("evidence://", "package://")):
        return True
    path = Path(text)
    return bool(text) and not path.is_absolute() and ".." not in path.parts and "://" not in text


def _observation(
    channel: str, gene: str, state: str, locator: str, sha256: str, note: str, origin: str
) -> dict[str, str]:
    return {
        "channel": channel,
        "gene": gene,
        "evidence_state": state,
        "source_locator": locator,
        "source_sha256": sha256,
        "note": note,
        "origin": origin,
    }


def load_evidence_index(
    path: Path | None, identity: Mapping[str, str], known_genes: set[str]
) -> tuple[list[dict[str, str]], int]:
    if path is None:
        return [], 0
    if not path.is_file():
        raise GeneFirstHold("MODEB_GENE_FIRST_SOURCE_HOLD: evidence index is not a file")
    required = {
        "channel", "strain", "full_node", "region", "bgc_alias", "gene",
        "evidence_state", "source_locator", "source_sha256", "note",
    }
    observations: list[dict[str, str]] = []
    historical_count = 0
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise GeneFirstHold(
                f"MODEB_GENE_FIRST_SOURCE_HOLD: evidence index missing columns {sorted(missing)}"
            )
        for line_number, row in enumerate(reader, 2):
            row_identity = (
                str(row.get("strain") or "").strip(),
                _full_node_or_contig(row.get("full_node")),
                _canonical_region(row.get("region")),
                _canonical_alias(row.get("bgc_alias")),
            )
            expected = (
                identity["strain"], identity["full_node"], identity["region"], identity["bgc_alias"]
            )
            if row_identity != expected:
                raise GeneFirstHold(
                    f"MODEB_GENE_FIRST_IDENTITY_HOLD: evidence row {line_number} conflicts with target"
                )
            channel = str(row.get("channel") or "").strip().lower()
            if channel not in CHANNEL_IDS | {HISTORICAL_CHANNEL}:
                raise GeneFirstHold(
                    f"MODEB_GENE_FIRST_SOURCE_HOLD: evidence row {line_number} has unknown channel"
                )
            state = str(row.get("evidence_state") or "").strip().upper()
            if state not in EVIDENCE_STATES:
                raise GeneFirstHold(
                    f"MODEB_GENE_FIRST_SOURCE_HOLD: evidence row {line_number} has invalid state"
                )
            if channel == HISTORICAL_CHANNEL:
                if state != "LEAD_ONLY":
                    raise GeneFirstHold(
                        "MODEB_GENE_FIRST_SOURCE_HOLD: historical cards must be LEAD_ONLY"
                    )
                historical_count += 1
            elif state == "LEAD_ONLY":
                raise GeneFirstHold(
                    "MODEB_GENE_FIRST_SOURCE_HOLD: LEAD_ONLY is reserved for historical cards"
                )
            gene = str(row.get("gene") or "").strip()
            if gene and gene not in known_genes:
                raise GeneFirstHold(
                    f"MODEB_GENE_FIRST_SOURCE_HOLD: evidence row {line_number} names unknown gene {gene}"
                )
            locator = str(row.get("source_locator") or "").strip()
            digest = str(row.get("source_sha256") or "").strip().lower()
            if state == "BOUND":
                if not _portable_locator(locator) or not re.fullmatch(r"[0-9a-f]{64}", digest):
                    raise GeneFirstHold(
                        f"MODEB_GENE_FIRST_SOURCE_HOLD: BOUND row {line_number} lacks portable locator or SHA-256"
                    )
            observations.append(_observation(
                channel, gene, state, locator, digest,
                str(row.get("note") or "").strip(), "evidence_index",
            ))
    return observations, historical_count


def _manifest_hits(
    manifest: Mapping[str, Any], identity: Mapping[str, str], known_genes: set[str], manifest_sha: str,
    *, channel_sources: Mapping[str, Mapping[str, str]] | None = None,
) -> list[dict[str, str]]:
    scans = manifest.get("source_scans") or {}
    alias = identity["bgc_alias"]
    token = _identity_token(identity)
    observations: list[dict[str, str]] = []

    def source(channel_key: str) -> tuple[str, str]:
        if channel_sources is None:
            return (f"package://manifest.json#exact_locus={token}/source_scans/{channel_key}", manifest_sha)
        bound = channel_sources.get(channel_key)
        if not bound:
            raise GeneFirstHold('MODEB_GENE_FIRST_SOURCE_HOLD: missing channel provenance')
        return (f"{bound['locator']}#exact_locus={token}{bound['pointer']}", bound['sha256'])

    def add_gene_hits(channel: str, values: Any, key: str) -> None:
        for hit in values if isinstance(values, list) else []:
            gene = str(hit.get(key) or "").strip()
            if not gene:
                continue
            if gene not in known_genes:
                raise GeneFirstHold(
                    f"MODEB_GENE_FIRST_SOURCE_HOLD: manifest {channel} row names unknown gene {gene}"
                )
            locator, digest = source({'mibig': 'mibig_per_gene', 'clusterblast': 'clusterblast_genes'}[channel])
            observations.append(_observation(
                channel, gene, "BOUND",
                f"{locator}/gene={gene}",
                digest, "Package-bound comparison row; interpretation deferred.", "manifest",
            ))

    mibig = ((scans.get("mibig_per_gene") or {}).get("per_gene_mibig") or {}).get(alias, [])
    add_gene_hits("mibig", mibig, "query_gene")
    clusterblast = ((scans.get("clusterblast_genes") or {}).get("per_gene_best_hit") or {}).get(alias, [])
    add_gene_hits("clusterblast", clusterblast, "query_gene")
    rggmci = scans.get("rggmci") or {}
    pairs = list(rggmci.get("ranked_pairs") or []) + list(rggmci.get("split_candidates") or [])
    if any(alias in (str(pair.get("bgc_a") or ""), str(pair.get("bgc_b") or "")) for pair in pairs):
        locator, digest = source('rggmci')
        observations.append(_observation(
            "rggmci", "", "BOUND",
            locator,
            digest, "Package-bound BGC-level pair evidence; not a gene-specific hit.", "manifest",
        ))
    return observations


def _auto_observations(
    gene_rows: Sequence[Mapping[str, str]], gene_table: Path, identity: Mapping[str, str],
    manifest: Mapping[str, Any], manifest_path: Path,
) -> list[dict[str, str]]:
    from ..scan_channel_alias import load_bound_scan_manifest, ScanChannelBindingError
    try:
        current, sources, manifest_sha = load_bound_scan_manifest(manifest_path)
    except (OSError, ScanChannelBindingError) as exc:
        raise GeneFirstHold('MODEB_GENE_FIRST_SOURCE_HOLD: ' + str(exc)) from exc
    if current != manifest:
        raise GeneFirstHold('MODEB_GENE_FIRST_SOURCE_HOLD: source changed after identity resolution')
    gene_sha = _sha256(gene_table)
    token = _identity_token(identity)
    observations: list[dict[str, str]] = []
    for row in gene_rows:
        gene = str(row["locus_tag"]).strip()
        if str(row.get("sec_met_domains") or "").strip():
            observations.append(_observation(
                "domain", gene, "BOUND",
                f"package://{gene_table.name}#exact_locus={token}&locus_tag={gene}", gene_sha,
                "Sealed per-gene domain annotation; interpretation deferred.", "gene_table",
            ))
    observations.extend(_manifest_hits(
        current, identity, {str(row["locus_tag"]).strip() for row in gene_rows}, manifest_sha,
        channel_sources=sources,
    ))
    return observations


def _channel_summary(observations: Sequence[Mapping[str, str]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    precedence = {"BOUND": 4, "UNBOUND": 3, "NOT_RUN": 2, "MISSING": 1}
    for channel, label in CHANNELS:
        matches = [row for row in observations if row["channel"] == channel]
        states = [row["evidence_state"] for row in matches if row["evidence_state"] != "LEAD_ONLY"]
        status = max(states, key=lambda state: precedence.get(state, 0)) if states else "MISSING"
        rows.append({
            "channel": channel,
            "label": label,
            "status": status,
            "record_count": len(matches),
            "gene_specific_records": sum(bool(row.get("gene")) for row in matches),
            "source_locators": ";".join(sorted({row["source_locator"] for row in matches if row.get("source_locator")})),
            "scope_note": "SEPARATE_CHANNEL_NO_SUBSTITUTION",
        })
    return rows


def _role_bucket(row: Mapping[str, str]) -> tuple[int, str]:
    text = " ".join((
        str(row.get("gene_function_inference") or ""),
        str(row.get("product_qualifier") or ""),
        str(row.get("sec_met_domains") or ""),
    )).lower()
    if "core biosynthetic" in text:
        return 1, "CORE_BIOSYNTHETIC_REVIEW"
    if any(token in text for token in ("resistance", "self-resistance", "efflux", "export")):
        return 2, "RESISTANCE_OR_EXPORT_REVIEW"
    if any(token in text for token in (
        "tailoring", "halogen", "glycosyl", "maturation", "proteolysis", "chain release"
    )):
        return 3, "TAILORING_OR_MATURATION_REVIEW"
    if any(token in text for token in ("unknown", "hypothetical", "uncharacterized")):
        return 4, "UNRESOLVED_FUNCTION_REVIEW"
    if "regulation" in text or "regulator" in text:
        return 5, "REGULATORY_CONTEXT_REVIEW"
    return 6, "OTHER_LOCUS_CONTEXT_REVIEW"


def rank_genes(
    gene_rows: Sequence[Mapping[str, str]], observations: Sequence[Mapping[str, str]],
    identity: Mapping[str, str],
) -> list[dict[str, Any]]:
    support: dict[str, set[str]] = {}
    for obs in observations:
        gene = str(obs.get("gene") or "")
        if gene and obs.get("evidence_state") == "BOUND" and obs.get("channel") in CHANNEL_IDS:
            support.setdefault(gene, set()).add(str(obs["channel"]))
    sortable: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
    for row in gene_rows:
        gene = str(row["locus_tag"]).strip()
        role_order, category = _role_bucket(row)
        bound = sorted(support.get(gene, set()))
        record = {
            **identity,
            "locus_tag": gene,
            "cds_start": row.get("cds_start", ""),
            "cds_end": row.get("cds_end", ""),
            "strand": row.get("strand", ""),
            "aa_length": row.get("aa_length", ""),
            "product_qualifier": row.get("product_qualifier", ""),
            "gene_function_inference": row.get("gene_function_inference", ""),
            "sec_met_domains": row.get("sec_met_domains", ""),
            "review_priority_category": category,
            "bound_gene_channels": ";".join(bound),
            "bound_gene_channel_count": len(bound),
            "gene_channel_gap_count": len(CHANNELS) - len(bound),
            "priority_basis": (
                "Deterministic review order: role category, then bound gene-channel count, "
                "then coordinates and locus tag; not a biological-importance score."
            ),
            "claim_ceiling": CLAIM_CEILING,
        }
        try:
            start_key = int(float(str(row.get("cds_start") or "999999999")))
        except ValueError:
            start_key = 999999999
        sortable.append(((role_order, -len(bound), start_key, gene), record))
    ranked = [record for _key, record in sorted(sortable, key=lambda item: item[0])]
    for index, record in enumerate(ranked, 1):
        record["rank"] = index
    return ranked


def choose_next_analysis(
    channels: Sequence[Mapping[str, Any]], ranked_genes: Sequence[Mapping[str, Any]],
    identity: Mapping[str, str],
) -> dict[str, str]:
    by_id = {str(row["channel"]): row for row in channels}
    top_gene = str(ranked_genes[0]["locus_tag"])
    for channel in _NEXT_ANALYSIS_ORDER:
        if by_id[channel]["status"] != "BOUND":
            return {
                "analysis_id": f"FILL_{channel.upper()}_GAP",
                "channel": channel,
                "target": f"{identity['exact_identity']} / {top_gene}",
                "action": _NEXT_ACTION[channel],
                "selection_basis": (
                    "First unresolved channel in the fixed offline information-gain order; "
                    "this is a workflow routing rule, not a scientific priority score."
                ),
            }
    return {
        "analysis_id": "RECONCILE_TOP_GENE_CHANNELS",
        "channel": "cross_channel_reconciliation",
        "target": f"{identity['exact_identity']} / {top_gene}",
        "action": (
            "Reconcile the separately retained channels for the highest-ranked gene and record "
            "agreement, conflict, and claim holds without merging their measurements."
        ),
        "selection_basis": "All ten channel families are bound; reconciliation is the remaining information step.",
    }


def _tsv(rows: Sequence[Mapping[str, Any]]) -> str:
    if not rows:
        return ""
    buf = io.StringIO()
    writer = _SafeDictWriter(buf, fieldnames=list(rows[0].keys()), delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


# v9.7.409 (DEEP_AUDIT2_resource_dos #2): antiSMASH-derived /product and /translation qualifiers reach
# Mode-B markdown table cells uncapped; a crafted 5 MB qualifier lands whole in one cell. Bound every
# rendered cell to a sane length with an explicit [truncated] marker. Env-overridable.
_QUALIFIER_MAX_CHARS = 20_000


def _md_escape(value: object) -> str:
    text = str(value or "")
    try:
        cap = int(os.environ.get("MAMEY_QUALIFIER_MAX_CHARS", str(_QUALIFIER_MAX_CHARS)))
    except (TypeError, ValueError):
        cap = _QUALIFIER_MAX_CHARS
    if len(text) > cap:
        text = text[:cap] + f" …[truncated {len(text) - cap} of {len(text)} chars]"
    return text.replace("|", "\\|").replace("\n", " ")


def _render_synthesis(
    identity: Mapping[str, str], bgc: Mapping[str, Any], ranked: Sequence[Mapping[str, Any]],
    channels: Sequence[Mapping[str, Any]], next_analysis: Mapping[str, str], historical_count: int,
) -> str:
    role_counts = Counter(str(row["review_priority_category"]) for row in ranked)
    bound_channels = [str(row["label"]) for row in channels if row["status"] == "BOUND"]
    gap_channels = [str(row["label"]) for row in channels if row["status"] != "BOUND"]
    products = bgc.get("products") or []
    if isinstance(products, str):
        products = [products]
    lines = [
        "# Mode B gene-first exploration synthesis",
        "",
        f"**Exact identity:** `{identity['exact_identity']}`",
        "",
        "> Engineering exploration only. This is not a Mode B card, biological finding, scientific acceptance, integration, release, or publication decision.",
        "",
        "## Concise synthesis",
        "",
        f"The sealed exact-locus roster contains {len(ranked)} non-placeholder genes. The package class labels are `{'; '.join(map(str, products)) or 'UNREPORTED'}` and the boundary state is `{bgc.get('edge_status') or 'UNREPORTED'}`. These are source fields, not product or activity claims.",
        f"Deterministic review categories: {', '.join(f'{key}={value}' for key, value in sorted(role_counts.items()))}.",
        f"Bound channel families: {', '.join(bound_channels) if bound_channels else 'none'}.",
        f"Workflow gaps retained separately: {', '.join(gap_channels) if gap_channels else 'none'}.",
        f"Historical cards registered as leads only: {historical_count}; they do not contribute evidence or ranking support.",
        "",
        "## Ranked important-gene review table",
        "",
        "The order is a transparent inspection order, not a biological-importance score.",
        "",
        "| Rank | Gene | Review category | Product qualifier | Domains | Bound gene channels |",
        "|---:|---|---|---|---|---|",
    ]
    for row in ranked[:12]:
        lines.append(
            f"| {row['rank']} | {_md_escape(row['locus_tag'])} | {_md_escape(row['review_priority_category'])} | "
            f"{_md_escape(row['product_qualifier'])} | {_md_escape(row['sec_met_domains'])} | "
            f"{_md_escape(row['bound_gene_channels']) or 'none'} |"
        )
    lines.extend([
        "",
        "## Evidence channels",
        "",
        "| Channel | Status | Records | Gene-specific records | Contract |",
        "|---|---|---:|---:|---|",
    ])
    for row in channels:
        lines.append(
            f"| {_md_escape(row['label'])} | {row['status']} | {row['record_count']} | "
            f"{row['gene_specific_records']} | {row['scope_note']} |"
        )
    lines.extend([
        "",
        "## One highest-information next analysis",
        "",
        f"- Analysis: `{next_analysis['analysis_id']}`",
        f"- Target: `{next_analysis['target']}`",
        f"- Action: {next_analysis['action']}",
        f"- Selection basis: {next_analysis['selection_basis']}",
        "",
        "## Claim ceiling",
        "",
        CLAIM_CEILING,
        "",
    ])
    return "\n".join(lines)


def run_gene_first_exploration(
    *, package: str | Path, strain: str, full_node: str, region: str, bgc_alias: str,
    out: str | Path, gene_table: str | Path | None = None,
    evidence_index: str | Path | None = None,
    database_selection: str | Path | None = None,
) -> dict[str, Any]:
    package_path = Path(package).expanduser().resolve()
    if not package_path.is_dir():
        raise GeneFirstHold("MODEB_GENE_FIRST_SOURCE_HOLD: package is not a directory")
    identity, bgc, manifest = resolve_identity(
        package_path, strain=strain, full_node=full_node, region=region, bgc_alias=bgc_alias
    )
    gene_path = _one_gene_table(package_path, gene_table)
    gene_rows = load_gene_rows(gene_path, identity)
    known_genes = {str(row["locus_tag"]).strip() for row in gene_rows}
    index_path = Path(evidence_index).expanduser().resolve() if evidence_index else None
    indexed, historical_count = load_evidence_index(index_path, identity, known_genes)
    database_bridge = None
    if database_selection:
        from .gene_first_database import join_selected_databases
        database_bridge, db_observations = join_selected_databases(
            Path(database_selection), package_path, gene_path, identity, bgc, manifest, gene_rows)
        if any(row["channel"] in {"nr", "clusterednr", "local_swissprot"} for row in indexed):
            raise GeneFirstHold("DATABASE_INDEX_CHANNEL_CONFLICT")
        indexed += db_observations
    observations = _auto_observations(
        gene_rows, gene_path, identity, manifest, package_path / "manifest.json"
    ) + indexed
    channels = _channel_summary(observations)
    ranked = rank_genes(gene_rows, observations, identity)
    if database_bridge:
        states = {(row["gene"], row["channel"]): row for row in database_bridge["genes"]}
        for row in ranked:
            for channel in ("nr", "clusterednr", "local_swissprot"):
                match = states[(row["locus_tag"], channel)]
                row[channel + "_database_state"] = match["state"]
                row[channel + "_search_count"] = len(match["search_history"])
    next_analysis = choose_next_analysis(channels, ranked, identity)
    synthesis = _render_synthesis(identity, bgc, ranked, channels, next_analysis, historical_count)

    if database_bridge:
        synthesis += "\n## Selected database bindings\n\n" + database_bridge["rendered_markdown"]

    # All validation and composition above occurs before the first output write.
    out_parent = Path(out).expanduser().resolve()
    if not out_parent.is_dir():
        raise GeneFirstHold(
            "MODEB_GENE_FIRST_OUTPUT_REFUSED: --out must be an existing additive output root"
        )
    token = _identity_token(identity)
    outdir = out_parent / token
    names = (
        f"{token}__MODEB_GENE_FIRST_EXPLORATION.md",
        f"{token}__important_genes.tsv",
        f"{token}__evidence_channels.tsv",
        f"{token}__exploration_receipt.json",
    )
    existing = [name for name in names if (outdir / name).exists()]
    if existing:
        raise GeneFirstHold(
            f"MODEB_GENE_FIRST_OUTPUT_REFUSED: output artifacts already exist: {existing}"
        )
    outdir.mkdir()
    synthesis_path = outdir / names[0]
    genes_path = outdir / names[1]
    channels_path = outdir / names[2]
    _atomic_write(synthesis_path, synthesis)
    _atomic_write(genes_path, _tsv(ranked))
    _atomic_write(channels_path, _tsv(channels))
    manifest_sha = _sha256(package_path / "manifest.json")
    receipt = {
        "schema": SCHEMA,
        "status": "ENGINEERING_EXPLORATION_ONLY",
        "exact_identity": identity,
        "inputs": {
            "manifest": {"locator": "package://manifest.json", "sha256": manifest_sha},
            "gene_table": {"locator": f"package://{gene_path.name}", "sha256": _sha256(gene_path)},
            "evidence_index": (
                {"locator": "input://evidence_index.tsv", "sha256": _sha256(index_path)}
                if index_path else None
            ),
        },
        "database_bridge": database_bridge,
        "gene_count": len(ranked),
        "evidence_observations": observations,
        "historical_lead_count": historical_count,
        "channel_status": {row["channel"]: row["status"] for row in channels},
        "highest_information_next_analysis": next_analysis,
        "outputs": [
            {"path": path.name, "sha256": _sha256(path), "bytes": path.stat().st_size}
            for path in (synthesis_path, genes_path, channels_path)
        ],
        "claim_ceiling": CLAIM_CEILING,
    }
    _atomic_write(outdir / names[3], json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return receipt


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--package", required=True, help="Sealed Mamey package directory")
    parser.add_argument("--strain", required=True)
    parser.add_argument("--node", required=True, dest="full_node", help="Full node-or-contig token")
    parser.add_argument("--region", required=True, help="antiSMASH region, e.g. region002")
    parser.add_argument("--bgc", required=True, dest="bgc_alias", help="Secondary BGC alias")
    parser.add_argument("--gene-table", default=None, help="Override sealed all-BGC gene table")
    parser.add_argument("--database-selection", default=None, help="Explicit pinned database selection JSON")
    parser.add_argument("--evidence-index", default=None, help="Optional normalized, exact-locus TSV")
    parser.add_argument(
        "--out", required=True,
        help="Existing additive output root; a four-field exact-identity child is created",
    )


def gene_first_command(args: argparse.Namespace) -> int:
    try:
        receipt = run_gene_first_exploration(
            package=args.package, strain=args.strain, full_node=args.full_node,
            region=args.region, bgc_alias=args.bgc_alias, out=args.out,
            gene_table=args.gene_table, evidence_index=args.evidence_index,
            database_selection=getattr(args, "database_selection", None),
        )
    except GeneFirstHold as exc:
        raise SystemExit(str(exc)) from exc
    sys.stdout.write(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    add_arguments(parser)
    return gene_first_command(parser.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
