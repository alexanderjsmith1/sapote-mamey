"""Attach hash-bound scientific-review overlays to a locator-first report cohort.

This module does not rewrite the base reports or promote reviewer prose to
accepted biology.  It verifies exact strain/assembly/node/region/region-key
identity, preserves comparator/profile channel states, and emits an additive
module-state delta plus one claim-safe Markdown overlay per reviewed locus.
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
from collections import Counter
from pathlib import Path


LOCATOR = re.compile(r"^(?P<node>.+?) / (?P<region>region\d+)$")
ANALYSIS_FIELDS = {
    "strain", "primary_user_locator", "source_scoped_bgc_alias",
    "assembly_sha256", "exact_region_key", "current_bgc_class",
    "current_cds_denominator", "exact_profile_call_basis",
    "machinery_domain_architecture", "observed_blastp_channels",
    "mibig_kcb_interpretation", "clusterblast_interpretation",
    "biosynthetic_logic_and_routing_hypothesis",
    "alternatives_counterevidence_and_holds",
    "paragraph_disposition_recommendation", "claim_ceiling",
}
DISPOSITION_FIELDS = {
    "strain", "primary_user_locator", "source_scoped_bgc_alias",
    "assembly_sha256", "exact_region_key", "module", "disposition",
    "recommendation", "claim_ceiling",
}
TARGET_FIELDS = {
    "strain", "primary_user_locator", "source_scoped_bgc_alias",
    "module_type", "module_state", "artifact_path", "artifact_sha256",
    "claim_ceiling",
}
DISPOSITION_MODULE_ALIASES = {"V7": "V7_LITERATURE_ATLAS"}
REQUIRED_CLAIM_CEILING_TERMS = (
    "similarity is not identity", "capacity is not production",
)
UNSAFE_REVIEW_PATTERNS = (
    re.compile(r"(?m)^##+\s+(?:mode\s+b|\d+(?:\.\d+)*\s+BGC\d+)", re.I),
    re.compile(r"<!--\s*MODE\s+B\s+TEMPLATE\b", re.I),
    re.compile(r"(?m)^#{1,6}\s+.*\bNODE_[^\n]*\s/\s*region\d+\b", re.I),
    re.compile(
        r"\b(?:the\s+)?(?:strain|organism|isolate)\s+"
        r"(?:produces|produced|makes|made)\b",
        re.I,
    ),
    re.compile(
        r"\b(?:product identity|production|activity|physical linkage) (?:is )?established\b",
        re.I,
    ),
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _rows(path: Path, required: set[str]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            missing = sorted(required - set(reader.fieldnames or []))
            raise ValueError(f"Missing required columns in {path.name}: {missing}")
        return list(reader)


def _write_rows(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = _SafeDictWriter(
            handle, fieldnames=fields, delimiter="\t", lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def verify_coverage_quarantine(path: Path) -> None:
    """Reject source-reported coverage above 100 unless it is explicitly held.

    Some legacy comparator exports contain aggregate or denominator-ambiguous
    coverage values above 100 percent.  Those bytes may remain as provenance,
    but they must not be exposed as usable comparison metrics.
    """
    if path.suffix.lower() != ".tsv":
        return
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fields = set(reader.fieldnames or [])
        if "pct_coverage" not in fields:
            return
        for line_number, row in enumerate(reader, start=2):
            raw = (row.get("pct_coverage") or "").strip()
            usable = (row.get("usable_pct_coverage") or "").strip()
            if raw:
                try:
                    coverage = float(raw)
                except ValueError as exc:
                    raise ValueError(
                        f"Non-numeric pct_coverage in {path.name}:{line_number}"
                    ) from exc
                if coverage > 100.0:
                    state = (row.get("coverage_state") or "").upper()
                    if "HOLD" not in state or usable:
                        raise ValueError(
                            f"Coverage above 100 is not quarantined in {path.name}:{line_number}"
                        )
            if usable:
                try:
                    usable_coverage = float(usable)
                except ValueError as exc:
                    raise ValueError(
                        f"Non-numeric usable_pct_coverage in {path.name}:{line_number}"
                    ) from exc
                if usable_coverage > 100.0:
                    raise ValueError(
                        f"Usable coverage above 100 in {path.name}:{line_number}"
                    )


def verify_base_boundary(
    root: Path, control_paths: tuple[Path, ...], base_index: list[dict[str, str]],
) -> dict[str, str]:
    """Bind control files and every indexed base report without mutating them."""
    root = root.resolve()
    snapshot = {str(path.relative_to(root)): sha256_file(path) for path in control_paths}
    for row in base_index:
        report = (root / row["report_path"]).resolve()
        try:
            report.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"Base report path escapes root: {row['report_path']}") from exc
        if not report.is_file():
            raise ValueError(f"Base report missing: {row['report_path']}")
        observed = sha256_file(report)
        if observed != row["report_sha256"]:
            raise ValueError(f"Base report hash mismatch: {row['report_path']}")
        snapshot[row["report_path"]] = observed
    return snapshot


def verify_target_artifacts(
    target_root: Path, targets: list[dict[str, str]],
) -> dict[str, str]:
    """Verify target bytes and evidence-safety invariants as one snapshot."""
    target_root = target_root.resolve()
    snapshot: dict[str, str] = {}
    for row in targets:
        artifact = (target_root / row["artifact_path"]).resolve()
        try:
            artifact.relative_to(target_root)
        except ValueError as exc:
            raise ValueError("Target artifact escapes target-ledger root") from exc
        if not artifact.is_file() or sha256_file(artifact) != row["artifact_sha256"]:
            raise ValueError(f"Target artifact hash mismatch: {row['artifact_path']}")
        verify_coverage_quarantine(artifact)
        snapshot[row["artifact_path"]] = row["artifact_sha256"]
    return snapshot


def verify_source_manifest(
    root: Path, manifest: Path,
) -> tuple[int, str, dict[Path, dict[str, str]]]:
    """Verify every materialized review artifact before consuming any row."""
    rows = _rows(manifest, {"path", "role", "sha256", "bytes", "status"})
    root = root.resolve()
    admitted: dict[Path, dict[str, str]] = {}
    for row in rows:
        candidate = (root / row["path"]).resolve()
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"Source-manifest path escapes root: {row['path']}") from exc
        if not candidate.is_file():
            raise ValueError(f"Source-manifest artifact missing: {row['path']}")
        if candidate.stat().st_size != int(row["bytes"]):
            raise ValueError(f"Source-manifest byte mismatch: {row['path']}")
        if sha256_file(candidate) != row["sha256"]:
            raise ValueError(f"Source-manifest hash mismatch: {row['path']}")
        admitted[candidate] = row
    return len(rows), sha256_file(manifest), admitted


def _unique(rows: list[dict[str, str]], fields: tuple[str, ...], label: str) -> None:
    keys = [tuple(row[field] for field in fields) for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError(f"Duplicate {label} identity")


def _key(row: dict[str, str]) -> tuple[str, str]:
    """Exact overlay join key; the source-scoped alias is metadata only."""
    return row["strain"], row["primary_user_locator"]


def _validate_source_preflight(
    *, catalog: Path, expected_catalog_sha256: str, decisions: Path,
    expected_decisions_sha256: str, strains: set[str],
    required_collection_types: set[str],
) -> list[dict]:
    try:
        from .workspace_source_discovery import validate_report_source_preflight
    except ImportError:
        from workspace_source_discovery import validate_report_source_preflight
    if not required_collection_types:
        raise ValueError("Stage 2 requires non-empty source collection types")
    results = []
    for strain in sorted(strains):
        result = validate_report_source_preflight(
            catalog_path=catalog,
            expected_catalog_sha256=expected_catalog_sha256,
            decisions_path=decisions,
            expected_decisions_sha256=expected_decisions_sha256,
            strain_key=strain,
            required_collection_types=required_collection_types,
        )
        if result.get("status") != "PASS_SOURCE_DISCOVERY_AND_DECISIONS_BOUND":
            reason = result.get("reason_code", "UNSPECIFIED_SOURCE_DISCOVERY_FAILURE")
            raise ValueError(f"SOURCE_DISCOVERY_PREFLIGHT_FAILED:{strain}:{reason}")
        results.append(result)
    return results


def _module_markdown(row: dict[str, str], dispositions: list[dict[str, str]]) -> str:
    lines = [
        f"# {row['strain']} — {row['primary_user_locator']} — scientific reconciliation",
        "",
        f"- Source-scoped alias: `{row['source_scoped_bgc_alias']}`",
        f"- Assembly SHA-256: `{row['assembly_sha256']}`",
        f"- Exact region key: `{row['exact_region_key']}`",
        "- Module state: `PROPOSAL_SOURCE_BOUND_NOT_ACCEPTED`",
        "- Authority: additive scientific review; base report and source evidence remain immutable.",
        "",
        "## Exact current locus summary", "",
        f"- antiSMASH class: {row['current_bgc_class']}",
        f"- Exact CDS denominator: {row['current_cds_denominator']}",
        f"- Profile-call basis: {row['exact_profile_call_basis']}",
        "",
        "## Machinery and domain architecture", "",
        row["machinery_domain_architecture"], "",
        "## Observed BLASTP channels", "",
        row["observed_blastp_channels"], "",
        "> Observed rows remain distinct from admitted query/run evidence.", "",
        "## Comparator interpretation", "",
        f"- MiBIG / KnownClusterBlast: {row['mibig_kcb_interpretation']}",
        f"- ClusterBlast: {row['clusterblast_interpretation']}",
        "",
        "## Biosynthetic hypothesis", "",
        row["biosynthetic_logic_and_routing_hypothesis"], "",
        "## Alternatives, counter-evidence, and holds", "",
        row["alternatives_counterevidence_and_holds"], "",
        "## Paragraph disposition", "",
        row["paragraph_disposition_recommendation"], "",
    ]
    for disposition in sorted(dispositions, key=lambda item: item["module"]):
        lines += [
            f"### {disposition['module']}", "",
            f"- Disposition: `{disposition['disposition']}`",
            f"- Recommendation: {disposition['recommendation']}", "",
        ]
    lines += ["## Claim ceiling", "", row["claim_ceiling"], ""]
    return "\n".join(lines)


def validate_review_content(rows: list[dict[str, str]], label: str) -> None:
    """Apply a small claim-safe structural policy to manifested review prose."""
    for index, row in enumerate(rows, start=2):
        ceiling = (row.get("claim_ceiling") or "").lower()
        if not all(term in ceiling for term in REQUIRED_CLAIM_CEILING_TERMS):
            raise ValueError(f"Claim ceiling missing required terms in {label}:{index}")
        content = "\n".join(row.values())
        for pattern in UNSAFE_REVIEW_PATTERNS:
            if pattern.search(content):
                raise ValueError(f"Claim-unsafe or foreign structural content in {label}:{index}")


def _markdown_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _front_door_markdown(rows: list[dict[str, str]]) -> str:
    base_count = int(rows[0]["base_cohort_loci"])
    reviewed_count = len(rows)
    lines = [
        "# Scientific reconciliation overlay", "",
        "This is an additive, proposal-only front door. The linked base reports remain "
        "immutable preliminary drafts; reconciliation does not establish product, production, "
        "activity, novelty, completeness, physical linkage, acceptance, integration, or release.",
        "",
        f"Coverage: **{reviewed_count} reviewed of {base_count} base-report loci**; "
        f"{base_count - reviewed_count} remain unreconciled preliminary drafts.", "",
        "| Exact antiSMASH locus | Source alias | Current class/capacity | Profile basis | Source receipt | Base draft | Reconciliation |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| {locator} | `{alias}` | {bgc_class} | {profile} | [antiSMASH receipt]({source}) | [base]({base}) | [review]({review}) |".format(
                locator=_markdown_cell(row["primary_user_locator"]),
                alias=_markdown_cell(row["source_scoped_bgc_alias"]),
                bgc_class=_markdown_cell(row["current_bgc_class"]),
                profile=_markdown_cell(row["exact_profile_call_basis"]),
                source=row["profile_table_link"], base=row["base_report_link"],
                review=row["reconciliation_path"],
            )
        )
    lines += [
        "", "Missing or held channels are evidence states, not biological negatives. "
        "A source-scoped BGC alias is navigation metadata, never the primary locus identity.", "",
    ]
    return "\n".join(lines)


def build(
    *, base_report_root: Path, target_ledger: Path, expected_target_sha256: str,
    review_root: Path, source_manifest: Path, expected_manifest_sha256: str,
    analysis_paths: list[Path], disposition_paths: list[Path], out_root: Path,
    expected_reviewed_loci: int, required_disposition_modules: set[str],
    allowed_review_roles: set[str],
    source_discovery_catalog: Path, expected_source_discovery_catalog_sha256: str,
    source_discovery_decisions: Path, expected_source_discovery_decisions_sha256: str,
    required_collection_types: set[str],
) -> dict:
    """Build one additive, receipt-bound 15-locus scientific overlay package."""
    base_report_root = base_report_root.resolve()
    review_root = review_root.resolve()
    out_root = out_root.resolve()
    if out_root.exists():
        raise FileExistsError(f"Output already exists: {out_root}")
    if sha256_file(target_ledger) != expected_target_sha256:
        raise ValueError("Target-ledger SHA-256 mismatch")
    if sha256_file(source_manifest) != expected_manifest_sha256:
        raise ValueError("Review source-manifest SHA-256 mismatch")
    source_count, manifest_sha, admitted_review_paths = verify_source_manifest(
        review_root, source_manifest,
    )
    for input_path in [*analysis_paths, *disposition_paths]:
        resolved = input_path.resolve()
        try:
            resolved.relative_to(review_root)
        except ValueError as exc:
            raise ValueError(f"Review input escapes review root: {input_path}") from exc
        if resolved not in admitted_review_paths:
            raise ValueError(f"Review input is not admitted by source manifest: {input_path.name}")
        admission = admitted_review_paths[resolved]
        if admission["role"] not in allowed_review_roles:
            raise ValueError(f"Review input role is not allowed: {input_path.name}")
        if admission["status"] != "PRESENT_HASH_BOUND":
            raise ValueError(f"Review input is not in PRESENT_HASH_BOUND state: {input_path.name}")

    base_index_path = base_report_root / "REPORT_INDEX.tsv"
    base_status_path = base_report_root / "REPORT_MODULE_STATUS.tsv"
    base_program_manifest = base_report_root / "REPORT_PROGRAM_MANIFEST.json"
    for path in (base_index_path, base_status_path, base_program_manifest):
        if not path.is_file():
            raise ValueError(f"Base report control missing: {path.name}")
    base_index = _rows(
        base_index_path,
        {"strain", "primary_user_locator", "source_scoped_bgc_alias",
         "assembly_sha256", "region_key", "report_path", "report_sha256"},
    )
    base_by_key = {_key(row): row for row in base_index}
    if len(base_by_key) != len(base_index):
        raise ValueError("Duplicate exact locator in base report index")
    base_snapshot = verify_base_boundary(
        base_report_root,
        (base_index_path, base_status_path, base_program_manifest),
        base_index,
    )

    targets = _rows(target_ledger, TARGET_FIELDS)
    _unique(targets, ("strain", "primary_user_locator", "module_type"), "target module")
    target_keys = {_key(row) for row in targets}
    if len(target_keys) != expected_reviewed_loci:
        raise ValueError(
            f"Reviewed-locus count mismatch: expected {expected_reviewed_loci}, observed {len(target_keys)}"
        )
    target_root = target_ledger.resolve().parent
    target_snapshot = verify_target_artifacts(target_root, targets)

    analyses: list[dict[str, str]] = []
    for path in analysis_paths:
        incoming = _rows(path, ANALYSIS_FIELDS)
        validate_review_content(incoming, path.name)
        analyses.extend(incoming)
    _unique(analyses, ("strain", "primary_user_locator"), "analysis")
    analysis_keys = {_key(row) for row in analyses}
    if analysis_keys != target_keys:
        raise ValueError("Analysis targets do not exactly match frozen target ledger")

    dispositions: list[dict[str, str]] = []
    for path in disposition_paths:
        incoming = _rows(path, DISPOSITION_FIELDS)
        for row in incoming:
            row["module"] = DISPOSITION_MODULE_ALIASES.get(row["module"], row["module"])
        validate_review_content(incoming, path.name)
        dispositions.extend(incoming)
    _unique(dispositions, ("strain", "primary_user_locator", "module"), "paragraph disposition")
    if {_key(row) for row in dispositions} != target_keys:
        raise ValueError("Paragraph dispositions do not cover exactly the target loci")

    base_program = json.loads(base_program_manifest.read_text(encoding="utf-8"))
    upstream_preflight = (
        base_program.get("portable_resolution_receipt", {})
        .get("source_discovery_preflight", {})
    )
    if upstream_preflight.get("status") != "PASS_SOURCE_DISCOVERY_AND_DECISIONS_BOUND":
        raise ValueError("UPSTREAM_BASE_PREFLIGHT_UNBOUND")
    source_preflight = _validate_source_preflight(
        catalog=source_discovery_catalog,
        expected_catalog_sha256=expected_source_discovery_catalog_sha256,
        decisions=source_discovery_decisions,
        expected_decisions_sha256=expected_source_discovery_decisions_sha256,
        strains={row["strain"] for row in analyses},
        required_collection_types=required_collection_types,
    )
    disposition_sets: dict[tuple[str, str, str], set[str]] = {}
    for row in dispositions:
        disposition_sets.setdefault(_key(row), set()).add(row["module"])
    for key in target_keys:
        if disposition_sets.get(key, set()) != required_disposition_modules:
            raise ValueError(f"Required disposition module set mismatch for {key!r}")

    for row in dispositions:
        base = base_by_key.get(_key(row))
        if not base:
            raise ValueError(f"Disposition locus absent from base report index: {_key(row)!r}")
        if base["assembly_sha256"] != row["assembly_sha256"]:
            raise ValueError(f"Disposition assembly mismatch for {_key(row)!r}")
        if base["region_key"] != row["exact_region_key"]:
            raise ValueError(f"Disposition exact region-key mismatch for {_key(row)!r}")
        if not LOCATOR.fullmatch(row["primary_user_locator"]):
            raise ValueError(f"Invalid disposition primary locator: {row['primary_user_locator']}")

    for row in analyses:
        base = base_by_key.get(_key(row))
        if not base:
            raise ValueError(f"Reviewed locus absent from base report index: {_key(row)!r}")
        if base["assembly_sha256"] != row["assembly_sha256"]:
            raise ValueError(f"Assembly mismatch for {_key(row)!r}")
        if base["region_key"] != row["exact_region_key"]:
            raise ValueError(f"Exact region-key mismatch for {_key(row)!r}")
        if not LOCATOR.fullmatch(row["primary_user_locator"]):
            raise ValueError(f"Invalid primary locator: {row['primary_user_locator']}")

    staging = out_root.with_name(f".{out_root.name}.staging-{os.getpid()}")
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    try:
        modules: list[dict[str, str]] = []
        front_rows: list[dict[str, str]] = []
        status_delta: list[dict[str, str]] = []
        dispositions_by_key: dict[tuple[str, str, str], list[dict[str, str]]] = {}
        for row in dispositions:
            dispositions_by_key.setdefault(_key(row), []).append(row)
        target_by_key: dict[tuple[str, str, str], list[dict[str, str]]] = {}
        for row in targets:
            target_by_key.setdefault(_key(row), []).append(row)

        for row in sorted(analyses, key=lambda item: _key(item)):
            match = LOCATOR.fullmatch(row["primary_user_locator"])
            assert match is not None
            module_path = (
                staging / "modules" / row["strain"] / match.group("node") /
                match.group("region") / "scientific_reconciliation.md"
            )
            module_path.parent.mkdir(parents=True, exist_ok=True)
            module_path.write_text(
                _module_markdown(row, dispositions_by_key[_key(row)]), encoding="utf-8",
            )
            relative = str(module_path.relative_to(staging))
            modules.append({
                "strain": row["strain"],
                "primary_user_locator": row["primary_user_locator"],
                "source_scoped_bgc_alias": row["source_scoped_bgc_alias"],
                "assembly_sha256": row["assembly_sha256"],
                "exact_region_key": row["exact_region_key"],
                "module_type": "PARAGRAPH_DISPOSITION",
                "module_state": "PROPOSAL_SOURCE_BOUND_NOT_ACCEPTED",
                "module_path": relative,
                "module_sha256": sha256_file(module_path),
                "claim_ceiling": row["claim_ceiling"],
            })
            base = base_by_key[_key(row)]
            base_report = (base_report_root / base["report_path"]).resolve()
            profile_table_path = (
                Path("tables") / row["strain"] / match.group("node") /
                match.group("region") / "exact_region_profile_calls.tsv"
            )
            profile_table = (base_report_root / profile_table_path).resolve()
            if not profile_table.is_file():
                raise ValueError(f"Exact antiSMASH profile table missing: {profile_table_path}")
            front_rows.append({
                "strain": row["strain"],
                "primary_user_locator": row["primary_user_locator"],
                "source_scoped_bgc_alias": row["source_scoped_bgc_alias"],
                "base_source_scoped_bgc_alias": base["source_scoped_bgc_alias"],
                "source_alias_relation_state": (
                    "SOURCE_ALIAS_MATCH"
                    if row["source_scoped_bgc_alias"] == base["source_scoped_bgc_alias"]
                    else "SOURCE_ALIAS_MISMATCH_HELD_METADATA_ONLY"
                ),
                "assembly_sha256": row["assembly_sha256"],
                "exact_region_key": row["exact_region_key"],
                "current_bgc_class": row["current_bgc_class"],
                "exact_profile_call_basis": row["exact_profile_call_basis"],
                "reconciliation_state": "PROPOSAL_SOURCE_BOUND_NOT_ACCEPTED",
                "base_cohort_loci": str(len(base_index)),
                "base_report_path": base["report_path"],
                "base_report_sha256": base["report_sha256"],
                "base_report_link": os.path.relpath(base_report, start=out_root),
                "profile_table_path": str(profile_table_path),
                "profile_table_sha256": sha256_file(profile_table),
                "profile_table_link": os.path.relpath(profile_table, start=out_root),
                "source_navigation_state": "HASH_BOUND_PROFILE_TABLE_SOURCE_CATALOG_RESOLUTION_REQUIRED",
                "reconciliation_path": relative,
                "reconciliation_sha256": sha256_file(module_path),
                "claim_ceiling": row["claim_ceiling"],
            })
            for target in sorted(target_by_key[_key(row)], key=lambda item: item["module_type"]):
                target_artifact = (target_root / target["artifact_path"]).resolve()
                status_delta.append({
                    "strain": row["strain"],
                    "primary_user_locator": row["primary_user_locator"],
                    "source_scoped_bgc_alias": row["source_scoped_bgc_alias"],
                    "module_type": target["module_type"],
                    "prior_state": "QUEUED_NOT_YET_ASSEMBLED",
                    "proposed_state": target["module_state"],
                    "artifact_path": target["artifact_path"],
                    "artifact_sha256": target["artifact_sha256"],
                    "artifact_content_id": f"sha256:{target['artifact_sha256']}",
                    "artifact_link": os.path.relpath(target_artifact, start=out_root),
                    "artifact_resolution_state": "EXTERNAL_CONTENT_ADDRESSED_LINK_VERIFIED",
                    "authority_state": "PROPOSAL_ONLY_NOT_ACCEPTED",
                })
            status_delta.append({
                "strain": row["strain"],
                "primary_user_locator": row["primary_user_locator"],
                "source_scoped_bgc_alias": row["source_scoped_bgc_alias"],
                "module_type": "PARAGRAPH_DISPOSITION",
                "prior_state": "QUEUED_NOT_YET_ASSEMBLED",
                "proposed_state": "PROPOSAL_SOURCE_BOUND_NOT_ACCEPTED",
                "artifact_path": relative,
                "artifact_sha256": sha256_file(module_path),
                "artifact_content_id": f"sha256:{sha256_file(module_path)}",
                "artifact_link": relative,
                "artifact_resolution_state": "LOCAL_OVERLAY_ARTIFACT_VERIFIED",
                "authority_state": "PROPOSAL_ONLY_NOT_ACCEPTED",
            })

        module_fields = list(modules[0])
        delta_fields = list(status_delta[0])
        disposition_fields = list(dispositions[0])
        _write_rows(staging / "SCIENTIFIC_OVERLAY_LEDGER.tsv", modules, module_fields)
        _write_rows(staging / "REVIEW_INDEX.tsv", front_rows, list(front_rows[0]))
        _write_rows(staging / "MODULE_STATE_DELTA.tsv", status_delta, delta_fields)
        _write_rows(staging / "PARAGRAPH_DISPOSITION.tsv", dispositions, disposition_fields)
        (staging / "INDEX.md").write_text(
            _front_door_markdown(front_rows), encoding="utf-8",
        )

        control = {
            "schema_version": "sapote_stage2_scientific_overlay_v1",
            "state": "PROPOSAL_SOURCE_BOUND_NOT_ACCEPTED_NOT_INTEGRATED",
            "base_report": {
                "report_index_sha256": sha256_file(base_index_path),
                "module_status_sha256": sha256_file(base_status_path),
                "program_manifest_sha256": sha256_file(base_program_manifest),
            },
            "inputs": {
                "target_ledger_sha256": expected_target_sha256,
                "review_source_manifest_sha256": manifest_sha,
                "review_source_artifact_count": source_count,
                "analysis_sha256": [sha256_file(path) for path in analysis_paths],
                "paragraph_disposition_sha256": [sha256_file(path) for path in disposition_paths],
                "allowed_review_roles": sorted(allowed_review_roles),
                "required_disposition_modules": sorted(required_disposition_modules),
                "source_discovery_catalog_sha256": expected_source_discovery_catalog_sha256,
                "source_discovery_decisions_sha256": expected_source_discovery_decisions_sha256,
                "required_collection_types": sorted(required_collection_types),
                "source_discovery_preflight": source_preflight,
            },
            "counts": {
                "base_report_loci": len(base_index),
                "reviewed_loci": len(modules),
                "unreviewed_loci": len(base_index) - len(modules),
                "overlay_coverage_state": f"PARTIAL_{len(modules)}_OF_{len(base_index)}",
                "paragraph_dispositions": len(dispositions),
                "module_state_delta_rows": len(status_delta),
                "state_counts": dict(Counter(row["proposed_state"] for row in status_delta)),
            },
            "claim_ceiling": (
                "Reviewer synthesis and module-routing proposal only; no product, production, "
                "activity, novelty, completeness, linkage, validation, acceptance, integration, "
                "release, or publication promotion."
            ),
        }
        control_path = staging / "OVERLAY_MANIFEST.json"
        control_path.write_text(json.dumps(control, indent=2, sort_keys=True) + "\n")

        material = sorted(
            path for path in staging.rglob("*")
            if path.is_file() and path.name not in {"ARTIFACT_MANIFEST.tsv", "QA_RECEIPT.json"}
        )
        artifact_rows = [{
            "path": str(path.relative_to(staging)),
            "role": "SCIENTIFIC_OVERLAY_MATERIAL",
            "sha256": sha256_file(path),
            "bytes": str(path.stat().st_size),
            "state": "PROPOSAL_NOT_ACCEPTED",
        } for path in material]
        _write_rows(
            staging / "ARTIFACT_MANIFEST.tsv", artifact_rows,
            ["path", "role", "sha256", "bytes", "state"],
        )
        qa = {
            "schema_version": "sapote_stage2_scientific_overlay_qa_v1",
            "status": "PASS_PROPOSAL_ONLY_NOT_ACCEPTED_NOT_INTEGRATED",
            "reviewed_loci": len(modules),
            "exact_target_match": f"PASS_{len(modules)}_OF_{len(modules)}",
            "source_manifest_rows": source_count,
            "paragraph_disposition_rows": len(dispositions),
            "module_state_delta_rows": len(status_delta),
            "artifact_manifest_rows": len(artifact_rows),
            "artifact_manifest_sha256": sha256_file(staging / "ARTIFACT_MANIFEST.tsv"),
            "manifest_self_state": "SELF_EXCLUDED_RECURSIVE",
            "qa_receipt_state": "EXCLUDED_FROM_PRIOR_MATERIAL_MANIFEST_BY_DESIGN",
            "claim_ceiling": control["claim_ceiling"],
        }
        (staging / "QA_RECEIPT.json").write_text(
            json.dumps(qa, indent=2, sort_keys=True) + "\n", encoding="utf-8",
        )
        # Rehash all four authority layers immediately before atomic publication.
        if sha256_file(target_ledger) != expected_target_sha256:
            raise ValueError("Target ledger drifted during build")
        verify_source_manifest(review_root, source_manifest)
        if verify_target_artifacts(target_root, targets) != target_snapshot:
            raise ValueError("Target artifacts drifted during build")
        if verify_base_boundary(
            base_report_root,
            (base_index_path, base_status_path, base_program_manifest),
            base_index,
        ) != base_snapshot:
            raise ValueError("Base report boundary drifted during build")
        for row in front_rows:
            profile_table = base_report_root / row["profile_table_path"]
            if sha256_file(profile_table) != row["profile_table_sha256"]:
                raise ValueError("Exact antiSMASH profile table drifted during build")
        source_preflight_after = _validate_source_preflight(
            catalog=source_discovery_catalog,
            expected_catalog_sha256=expected_source_discovery_catalog_sha256,
            decisions=source_discovery_decisions,
            expected_decisions_sha256=expected_source_discovery_decisions_sha256,
            strains={row["strain"] for row in analyses},
            required_collection_types=required_collection_types,
        )
        if source_preflight_after != source_preflight:
            raise ValueError("Source-discovery preflight changed during Stage 2 build")
        staging.rename(out_root)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise
    return {
        "status": "PASS_PROPOSAL_ONLY_NOT_ACCEPTED_NOT_INTEGRATED",
        "output": str(out_root),
        "reviewed_loci": len(analyses),
        "module_state_delta_rows": len(targets) + len(analyses),
        "qa_receipt_sha256": sha256_file(out_root / "QA_RECEIPT.json"),
    }


def command(args: argparse.Namespace) -> int:
    result = build(
        base_report_root=Path(args.base_report_root),
        target_ledger=Path(args.target_ledger),
        expected_target_sha256=args.expected_target_sha256,
        review_root=Path(args.review_root),
        source_manifest=Path(args.source_manifest),
        expected_manifest_sha256=args.expected_manifest_sha256,
        analysis_paths=[Path(path) for path in args.analysis],
        disposition_paths=[Path(path) for path in args.paragraph_disposition],
        out_root=Path(args.out),
        expected_reviewed_loci=args.expected_reviewed_loci,
        required_disposition_modules=set(args.required_disposition_module),
        allowed_review_roles=set(args.allowed_review_role),
        source_discovery_catalog=Path(args.source_discovery_catalog),
        expected_source_discovery_catalog_sha256=args.expected_source_discovery_catalog_sha256,
        source_discovery_decisions=Path(args.source_discovery_decisions),
        expected_source_discovery_decisions_sha256=args.expected_source_discovery_decisions_sha256,
        required_collection_types=set(args.required_collection_type),
    )
    emit(json.dumps(result, indent=2, sort_keys=True))
    return 0


def add_cli_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(
        "attach-bgc-overlays",
        help="Attach locator-first, hash-bound scientific-review overlays additively",
    )
    parser.add_argument("--base-report-root", required=True)
    parser.add_argument("--target-ledger", required=True)
    parser.add_argument("--expected-target-sha256", required=True)
    parser.add_argument("--review-root", required=True)
    parser.add_argument("--source-manifest", required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    parser.add_argument("--analysis", action="append", required=True)
    parser.add_argument("--paragraph-disposition", action="append", required=True)
    parser.add_argument("--expected-reviewed-loci", type=int, required=True)
    parser.add_argument("--required-disposition-module", action="append", required=True)
    parser.add_argument("--allowed-review-role", action="append", required=True)
    parser.add_argument("--source-discovery-catalog", required=True)
    parser.add_argument("--expected-source-discovery-catalog-sha256", required=True)
    parser.add_argument("--source-discovery-decisions", required=True)
    parser.add_argument("--expected-source-discovery-decisions-sha256", required=True)
    parser.add_argument("--required-collection-type", action="append", required=True)
    parser.add_argument("--out", required=True)
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
