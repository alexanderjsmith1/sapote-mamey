"""Claim-safe, package-only layperson guide renderer.

This is a post-seal presentation layer.  It reads an existing Mamey package,
preserves its routing order, and writes one governed Markdown source.  The
canonical document exporter consumes that same source for DOCX output; this
module does not create a competing document model or scientific scorer.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any

try:  # pragma: no cover - import shape depends on package vs direct-script use
    from .console import emit
except ImportError:  # direct execution has no parent package
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from mamey.console import emit

from .exact_identity import (
    ExactLocusIdentityError,
    exact_locus_from_mapping,
    exact_locus_from_native_manifest_bgc,
)
from .figure_theme import CLAIM_SAFETY, add_claim_safety_footer


def _relativize_receipt_path(path_value: str, base: Path) -> str:
    """Store a shipped-receipt output path relative to the run directory ``base``.

    The layperson-guide receipt is a SHIPPED artifact, so its ``outputs[].path`` must
    never embed the operator's absolute ``<home>/<user>/...`` layout (DEEP_AUDIT3 F1).
    Falls back to the basename if the path resolves outside ``base``.
    """
    try:
        return str(Path(path_value).resolve().relative_to(Path(base).resolve()))
    except (ValueError, OSError):
        return Path(path_value).name


class LaypersonGuideError(ValueError):
    """Raised when the package cannot support a fail-closed guide."""


CLASS_EXPLANATIONS = {
    "NRPS": "a non-ribosomal peptide assembly-line class",
    "NRPS-like": "a region with some features of a non-ribosomal peptide assembly line",
    "T1PKS": "a type I polyketide assembly-line class",
    "T2PKS": "a type II polyketide class often used to build ring-rich molecules",
    "T3PKS": "a compact type III polyketide class",
    "transAT-PKS": "a trans-acyltransferase polyketide assembly-line class",
    "terpene": "a terpene-building class",
    "saccharide": "a carbohydrate-related biosynthetic class",
    "lassopeptide": "a ribosomally made lasso-peptide class",
    "lanthipeptide-class-i": "a class I lanthipeptide pathway",
    "lanthipeptide-class-ii": "a class II lanthipeptide pathway",
    "lanthipeptide-class-iii": "a class III lanthipeptide pathway",
    "betalactone": "a beta-lactone biosynthetic class",
    "NAPAA": "a non-alpha poly-amino-acid biosynthetic class",
    "ectoine": "an ectoine biosynthetic class",
    "butyrolactone": "a butyrolactone-related biosynthetic class",
    "PKS": "a polyketide-building enzyme class",
    "arylpolyene": "an aryl-polyene pigment-related class",
    "fatty_acid": "a fatty-acid-related biosynthetic class",
    "hglE-KS": "a ketosynthase-related biosynthetic class",
    "other": "another class that antiSMASH does not resolve more specifically here",
}

CLASS_LABELS = {
    "NRPS": "NRPS (non-ribosomal peptide)",
    "NRPS-like": "NRPS-like (non-ribosomal peptide-like)",
    "PKS": "PKS (polyketide synthase)",
    "T1PKS": "type I PKS (polyketide synthase)",
    "T2PKS": "type II PKS (polyketide synthase)",
    "T3PKS": "type III PKS (polyketide synthase)",
    "transAT-PKS": "trans-AT PKS (polyketide synthase)",
    "hglE-KS": "hglE-KS (ketosynthase-related)",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _emit_receipt(receipt: dict[str, Any], receipt_path: Path) -> None:
    """Emit either terminal receipt through the single console seam."""
    emit(json.dumps({**receipt, "receipt": str(receipt_path)}, indent=2))


def _load_manifest(package: Path) -> tuple[Path, dict[str, Any]]:
    package = package.resolve()
    manifest_path = package / "manifest.json"
    if not package.is_dir() or not manifest_path.is_file():
        raise LaypersonGuideError(f"SEALED_PACKAGE_REQUIRED:{package}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LaypersonGuideError(f"MANIFEST_UNREADABLE:{manifest_path}") from exc
    if not isinstance(manifest, dict) or not isinstance(manifest.get("bgcs"), list):
        raise LaypersonGuideError("MANIFEST_BGC_ROWS_REQUIRED")
    strain = str(manifest.get("strain_id") or "").strip()
    if not strain:
        raise LaypersonGuideError("MANIFEST_STRAIN_REQUIRED")
    return manifest_path, manifest


def _cell(value: Any) -> str:
    text = " ".join(str(value if value is not None else "").split())
    return text.replace("|", "&#124;") or "Not supplied"


def _number(value: Any, digits: int = 1) -> str:
    try:
        return f"{float(value):,.{digits}f}"
    except (TypeError, ValueError):
        return "Not supplied"


def _megabases(value: Any) -> str:
    try:
        number = float(value)
        return _number(number / 1_000_000, 2) if number > 0 else "Not supplied"
    except (TypeError, ValueError):
        return "Not supplied"


def _positive(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "Not supplied"
    if number <= 0:
        return "Not supplied"
    return f"{number:,.0f}"


def _percent(value: Any) -> str:
    rendered = _number(value)
    return f"{rendered}%" if rendered != "Not supplied" else rendered


def _region(row: dict[str, Any]) -> str:
    # Do not infer the canonical region identity from a number.  The complete
    # source-bound token must already be present in the package.
    return str(row.get("antismash_region") or "").strip()


def _identity(strain: str, row: dict[str, Any]) -> str:
    try:
        if "node_id" in row:
            return exact_locus_from_native_manifest_bgc(strain, row).exact_locus
        return exact_locus_from_mapping(strain, row)
    except ExactLocusIdentityError as exc:
        raise LaypersonGuideError(f"EXACT_LOCUS_IDENTITY_REQUIRED:{exc}") from None


def _validated_rows(
    strain: str,
    rows: list[dict[str, Any]],
) -> list[tuple[dict[str, Any], str]]:
    """Validate every raw row before selection and preserve complete identities."""
    validated: list[tuple[dict[str, Any], str]] = []
    aliases: set[str] = set()
    physical_loci: set[str] = set()
    for position, row in enumerate(rows, 1):
        identity = _identity(strain, row)
        physical_locus, alias = identity.rsplit(" / ", 1)
        if alias in aliases:
            raise LaypersonGuideError(
                f"DUPLICATE_BGC_ALIAS_AT_MANIFEST_RECORD:{position}"
            )
        if physical_locus in physical_loci:
            raise LaypersonGuideError(
                f"DUPLICATE_PHYSICAL_LOCUS_AT_MANIFEST_RECORD:{position}"
            )
        aliases.add(alias)
        physical_loci.add(physical_locus)
        validated.append((row, identity))
    return validated


def _class_text(products: Any) -> tuple[str, str]:
    if isinstance(products, str):
        labels = [item.strip() for item in products.split(";") if item.strip()]
    elif isinstance(products, list):
        labels = [str(item).strip() for item in products if str(item).strip()]
    else:
        labels = []
    recognized = [label for label in labels if label in CLASS_EXPLANATIONS]
    withheld = len(labels) - len(recognized)
    if not recognized:
        if withheld:
            return "Unreviewed package label withheld", "an unreviewed package-supplied label that this guide does not interpret"
        return "Unresolved", "an unresolved biosynthetic class"
    rendered = " + ".join(CLASS_LABELS.get(label, label.replace("_", " ")) for label in recognized)
    explanations = [CLASS_EXPLANATIONS[label] for label in recognized]
    if withheld:
        rendered += f" + {withheld} unreviewed label{'s' if withheld != 1 else ''} withheld"
        explanations.append(f"{withheld} unreviewed package label{'s' if withheld != 1 else ''} that this guide does not interpret")
    return rendered, " combined with ".join(explanations)


def _comparison_text(row: dict[str, Any]) -> str:
    state = str(row.get("kcb_evidence_state") or "").upper()
    top = row.get("kcb_top") or row.get("closest_candidate_kcb_product")
    locator = row.get("source_kcb_locator") or row.get("source_kcb_file")
    has_top = top not in {None, "", "UNRESOLVED"}
    has_locator = locator not in {None, "", "UNRESOLVED", "UNBOUND"}
    if state in {"MATCH", "KNOWNCLUSTERBLAST_OBSERVED"}:
        if not (has_top and has_locator):
            return "PARTIAL: comparison state is recorded, but the package does not contain a complete bound comparison."
        return "MATCH: the package contains a bound comparison. The source label is withheld here; similarity does not establish product identity, production, or activity."
    if state in {"PARTIAL", "CLUSTERBLAST_FALLBACK_OBSERVED"}:
        return "PARTIAL: some comparison evidence is present, but this package cannot support a complete comparison."
    if state in {"", "MISSING", "UNKNOWN_KCB", "NOT_RUN", "UNBOUND"}:
        return "MISSING: the expected comparison field is absent or unbound in this package; this is not biological absence."
    if state == "CANNOT_FROM_PACKAGE":
        return "CANNOT_FROM_PACKAGE: this package cannot determine a comparison outcome."
    return "CANNOT_FROM_PACKAGE: the package contains an unrecognized comparison state, so this guide will not interpret it."


def _controlled_state(value: Any, allowed: set[str], *, label: str) -> str:
    state = str(value or "").strip().upper()
    if not state:
        return "Not supplied"
    if state in allowed:
        return state.replace("_", " ").title()
    return f"Unrecognized {label} state withheld"


def _package_status(value: Any) -> str:
    state = str(value or "").strip().upper()
    if state == "MAMEY_COMPLETE":
        return "MAMEY_COMPLETE: mechanical package validation completed; this is not scientific acceptance"
    if state == "MAMEY_COMPLETE_WITH_ISSUES":
        return "MAMEY_COMPLETE_WITH_ISSUES: mechanical packaging completed with recorded issues; this is not scientific acceptance"
    if state in {"PASS", "PASS_WITH_ISSUES"}:
        return f"{state}: mechanical package-check state; this is not scientific acceptance"
    if not state:
        return "Not supplied"
    return "Unrecognized mechanical package state withheld; scientific acceptance is not implied"


def _boundary_text(value: Any) -> str:
    state = str(value or "").strip().lower()
    if state == "interior":
        return "Interior"
    if state == "edge":
        return "Edge"
    if state in {"full", "full-contig", "full_contig"}:
        return "Full-contig"
    if state == "unknown":
        return "Unknown in package"
    return "Not supplied" if not state else "Unrecognized boundary state withheld"


def _headline(row: dict[str, Any]) -> str:
    _, explanation = _class_text(row.get("products"))
    boundary = str(row.get("edge_status") or "").lower()
    qualifier = (
        " The region touches a contig boundary, so its sequence may be incomplete."
        if boundary in {"edge", "full", "full-contig", "full_contig"} else ""
    )
    return f"antiSMASH reports these broad classes: {explanation}. The region may contain machinery from those families, but the product is not established.{qualifier}"


def add_guide_figure_footer(fig: Any, *, manifest_sha256: str) -> None:
    """Apply the canonical footer if a future package-bound figure is supplied.

    The Day 5 structure contains no analytical figure, so this renderer does
    not invent one.  Keeping this thin adapter makes any later, authorized
    figure use the existing figure-theme owner.
    """
    add_claim_safety_footer(fig, provenance=f"manifest sha256 {manifest_sha256}", authority="Post-seal guide")


def validate_locus_mentions(markdown: str, *, strain: str, rows: list[dict[str, Any]]) -> None:
    """Reject an alias mention that is not inside its complete display identity.

    The governed Markdown schema serves several document types and therefore
    does not require an exact-locus field for a multi-region human guide.  This
    producer applies the narrower permanent contract to every row it emits.
    """
    remainder = markdown
    for row in rows:
        identity = _identity(strain, row)
        alias = str(row.get("bgc_id") or "").strip()
        if identity not in remainder:
            raise LaypersonGuideError(f"COMPLETE_IDENTITY_NOT_RENDERED:{identity}")
        remainder = remainder.replace(identity, "")
        if alias and re.search(rf"(?<![A-Za-z0-9]){re.escape(alias)}(?![A-Za-z0-9])", remainder):
            raise LaypersonGuideError(f"BARE_BGC_ALIAS_FORBIDDEN:{alias}")


def render_markdown(package: str | Path, *, top_n: int = 5) -> str:
    """Render one governed Markdown source from a sealed package."""
    if top_n < 1:
        raise LaypersonGuideError("TOP_N_MUST_BE_POSITIVE")
    package_path = Path(package)
    manifest_path, manifest = _load_manifest(package_path)
    strain = str(manifest["strain_id"]).strip()
    if not manifest["bgcs"]:
        raise LaypersonGuideError("PACKAGE_BGC_DATA_GAP:NO_BGC_ROWS")
    if any(not isinstance(row, dict) for row in manifest["bgcs"]):
        raise LaypersonGuideError("PACKAGE_BGC_DATA_GAP:NON_MAPPING_BGC_ROW")
    rows_with_identities = _validated_rows(strain, list(manifest["bgcs"]))
    rows_with_identities.sort(key=lambda item: (
        int(item[0].get("corrected_rank")) if str(item[0].get("corrected_rank", "")).isdigit() else 10**9,
        str(item[0].get("bgc_id") or ""),
    ))
    selected_rows = rows_with_identities[:top_n]
    selected = [row for row, _ in selected_rows]
    identities = [identity for _, identity in selected_rows]

    assembly = manifest.get("assembly") if isinstance(manifest.get("assembly"), dict) else {}
    counts = manifest.get("bgc_counts") if isinstance(manifest.get("bgc_counts"), dict) else {}
    quality = assembly.get("quality") if isinstance(assembly.get("quality"), dict) else {}
    bioactivity = manifest.get("bioactivity") if isinstance(manifest.get("bioactivity"), dict) else {}
    bioassay_scope = manifest.get("bioassay_scope") if isinstance(manifest.get("bioassay_scope"), dict) else {}
    actions = manifest.get("recommended_next_steps") if isinstance(manifest.get("recommended_next_steps"), list) else []

    title = f"Plain Language BGC Guide for {strain}"
    lines = [
        "---",
        "schema_version: sapote-markdown-1.0",
        "document_type: human_guide",
        f"title: {json.dumps(title)}",
        'subtitle: "A plain-language summary of an already completed package"',
        'audience: "Biology undergraduates, non-specialist collaborators, and reviewers"',
        'authority: "Deterministic package summary; scientific judgment and experiment authorization are not supplied"',
        "render_profile: human_guide",
        f"claim_safety_footer: {json.dumps(CLAIM_SAFETY)}",
        'source_manifest: "manifest.json"',
        "---",
        "",
        "This guide translates fields already present in one sealed Mamey package. It does not identify a compound, predict production, establish biological activity, change the package ranking, or authorize an experiment.",
        "",
        "## Package context",
        "",
        "<!-- sapote:table id=package_context layout=portrait repeat_header=true widths=2.1,4.9 -->",
        "| Field | Package value |",
        "|---|---|",
        f"| Strain | {_cell(strain)} |",
        f"| Taxonomy | {_cell(manifest.get('taxonomy'))} |",
        f"| Source context | {_cell(manifest.get('source'))} |",
        f"| Run mode | {_cell(manifest.get('mode'))} |",
        f"| Workflow version | {_cell(manifest.get('workflow_version'))} |",
        f"| Analysis date | {_cell(manifest.get('analysis_date'))} |",
        f"| antiSMASH profile | {_cell(manifest.get('antismash_profile'))} |",
        f"| Package status | {_cell(_package_status(manifest.get('terminal_status') or manifest.get('package_status')))} |",
        "",
        "antiSMASH is software that marks genome regions with gene patterns associated with broad biosynthetic classes. Its labels are starting points for review, not compound identifications.",
        "",
        "## Assembly context",
        "",
        "<!-- sapote:table id=assembly_size_counts layout=portrait repeat_header=true widths=1.7,1.7,1.7,1.7 -->",
        "| Genome Mb | Contigs | N50 bp | Raw regions |",
        "|---|---|---|---|",
        f"| {_megabases(assembly.get('genome_bp'))} | {_positive(assembly.get('contigs'))} | {_positive(assembly.get('n50'))} | {_positive(counts.get('raw'))} |",
        "",
        "<!-- sapote:table id=assembly_interpretation layout=portrait repeat_header=true widths=1.7,1.7,1.7,1.7 -->",
        "| Corrected count | Interior percent | Assembly tier | Bioassay state |",
        "|---|---|---|---|",
        f"| {_number(counts.get('corrected'))} | {_percent(counts.get('interior_pct'))} | {_cell(_controlled_state(counts.get('assembly_tier'), {'GOOD', 'MODERATE', 'POOR', 'VERY_POOR'}, label='assembly tier'))} | {_cell(_controlled_state(bioassay_scope.get('assay_data_state') or bioactivity.get('metadata_state'), {'AVAILABLE', 'NOT_PROVIDED', 'NOT_SUPPLIED', 'UNBOUND', 'UNKNOWN', 'PARTIAL'}, label='bioassay'))} |",
        "",
        "N50 is an assembly-contiguity summary: half of the assembled genome lies in contigs at least this long. An interior region stays away from a contig end; an edge or full-contig region touches a sequence boundary and may be incomplete.",
        "",
        "The corrected count is a boundary-aware estimate from the sealed package, not a count of produced compounds. Assembly and region-boundary limitations can make the raw count an overstatement.",
        "",
        "## How to read the region table",
        "",
        "A biosynthetic gene cluster is a nearby group of genes that may work together to make or modify a molecule. The package lists these regions in the order chosen for later review; that order is not a scientific verdict.",
        "",
        "### Boundary-based count tiers used by the source format",
        "",
        "<!-- sapote:table id=assembly_tiers layout=portrait repeat_header=true widths=1.2,1.3,4.5 -->",
        "| Tier | Interior percent | Plain interpretation |",
        "|---|---|---|",
        "| Good | 70% or more | Raw and corrected counts should be close; every region still needs review. |",
        "| Moderate | 45% to 69% | Boundary effects may modestly change the count. |",
        "| Poor | 20% to 44% | Use the corrected count; treat boundary-touching regions cautiously. |",
        "| Very poor | Less than 20% | Boundary effects dominate; the raw count is not a reliable total. |",
        "",
        "## Regions in package review order (not a scientific ranking)",
        "",
    ]
    if selected:
        lines += [
            "<!-- sapote:table id=ranked_regions layout=landscape repeat_header=true widths=2.7,0.8,1.0,1.1,1.8,3.5 -->",
            "| Complete identity | Class label | Size kb | Boundary | Comparison state | Plain-language reading |",
            "|---|---|---|---|---|---|",
        ]
        for identity, row in zip(identities, selected):
            class_label, _ = _class_text(row.get("products"))
            lines.append(
                f"| {_cell(identity)} | {_cell(class_label)} | {_number(row.get('length_kb'))} | "
                f"{_cell(_boundary_text(row.get('edge_status')))} | {_cell(_comparison_text(row))} | {_cell(_headline(row))} |"
            )

    caveat_state = (
        "PRESENT_BUT_NOT_LOCUS_BOUND. The original package note is withheld because it is not tied to complete locus identities and has not passed claim-safe review."
        if str(quality.get("caveat") or "").strip()
        else "NOT_SUPPLIED. No assembly-quality caveat is present in this package."
    )
    action_text = (
        f"The package contains {len(actions)} unstructured next-step entr{'y' if len(actions) == 1 else 'ies'}, but this guide does not reproduce them because an exact-locus binding and an authorization state are not guaranteed."
        if actions else
        "This package does not contain a reviewed next step. A qualified project owner must decide what, if anything, to do next."
    )
    lines += [
        "",
        "## Assembly and claim caveat",
        "",
        f"> [CAUTION] Why restraint is required\n> Package caveat state: {caveat_state} Product identity, production, activity, ecological function, and structural novelty remain unestablished unless separately supported by bound evidence.",
        "",
        "## Immediate next action",
        "",
        action_text,
        "",
        "## What this package cannot supply",
        "",
        "- A cohort-wide rank or cross-habitat comparison from a single package.",
        "- Verified discovery, mechanism, cluster, or recent-work citations.",
        "- A measured bioassay interpretation when assay evidence is absent or unbound.",
        "- A product-specific experiment, target mass, solvent, time point, or authorized wet-lab action.",
        "- A Day 5 analytical figure set; the reference document contains styled tables and text but no analytical plots to reproduce.",
        "",
        "## Claim ceiling",
        "",
        f"> [CLAIM CEILING] Package-bound interpretation limit\n> {CLAIM_SAFETY} Any class label above is a broad, source-derived hypothesis and must remain hedged until stronger evidence is bound.",
        "",
        f"Source receipt: manifest SHA-256 `{_sha256(manifest_path)}`.",
        "",
    ]
    rendered = "\n".join(lines)
    validate_locus_mentions(rendered, strain=strain, rows=selected)
    return rendered


def layperson_command(args: Any) -> int:
    """CLI adapter; post-seal and non-blocking to the core extraction run."""
    package = Path(args.package).resolve()
    # v9.7.409 (AUDIT_cli_edgecases): pointing the reader at a run dir / unsealed package (a common
    # mistake) made _load_manifest raise LaypersonGuideError (SEALED_PACKAGE_REQUIRED) straight to
    # the terminal as a raw traceback — before outdir is known, so no receipt can be written here.
    # Every sibling reader prints a one-line ERROR and returns non-zero; mirror that.
    try:
        manifest_path, manifest = _load_manifest(package)
    except LaypersonGuideError as exc:
        import sys
        emit(f"ERROR: {exc}", file=sys.stderr)
        return 1
    strain = str(manifest["strain_id"]).strip()
    safe_strain = re.sub(r"[^A-Za-z0-9_.-]+", "_", strain).strip("_") or "strain"
    outdir = Path(args.outdir).resolve() if args.outdir else package.parent / "layperson_guide"
    outdir.mkdir(parents=True, exist_ok=True)
    markdown_path = outdir / f"{safe_strain}_LAYPERSON_GUIDE.md"
    receipt_path = outdir / f"{safe_strain}_LAYPERSON_GUIDE_RECEIPT.json"
    try:
        rendered = render_markdown(package, top_n=args.top_n)
    except (LaypersonGuideError, ExactLocusIdentityError) as exc:
        receipt = {
            "schema_version": "mamey_layperson_guide_receipt_v1",
            "status": "CANNOT_FROM_PACKAGE",
            "package": package.name,
            "source_manifest": manifest_path.name,
            "source_manifest_sha256": _sha256(manifest_path),
            "claim_safety_footer": CLAIM_SAFETY,
            "producer": "mamey.layperson_guide via mamey.document_export",
            "outputs": [],
            "warnings": [],
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        _emit_receipt(receipt, receipt_path)
        return 2
    markdown_path.write_text(rendered, encoding="utf-8")

    outputs = [{"format": "md", "path": str(markdown_path), "sha256": _sha256(markdown_path),
                "bytes": markdown_path.stat().st_size}]
    status = "PASS"
    warnings: list[str] = []
    try:
        from .sapote_markdown import parse_path, validate_model
        model = parse_path(markdown_path)
        validation = validate_model(model, require_assets=True)
        validation.raise_for_errors()
    except ModuleNotFoundError as exc:
        status = "PASS_WITH_DOCUMENT_VALIDATION_UNAVAILABLE"
        warnings.append(f"DOCUMENT_VALIDATION_UNAVAILABLE:{exc.name}")
    if args.format in {"docx", "both"}:
        try:
            from .document_export import export_document
            document_receipt = export_document(markdown_path, outdir=outdir, output_format="docx")
            outputs.extend(document_receipt.outputs)
            warnings.extend(document_receipt.warnings)
        except Exception as exc:  # post-seal document failure must not affect the sealed package
            status = "PASS_WITH_DOCX_UNAVAILABLE"
            warnings.append(f"DOCX_UNAVAILABLE:{type(exc).__name__}:{exc}")

    if args.format == "docx":
        outputs = [row for row in outputs if row["format"] == "docx"]
    # CLAUDE_409: the receipt ships in the package; store run-relative output paths so
    # the on-disk JSON never embeds the operator's absolute <home>/<user>/... layout
    # (DEEP_AUDIT3 F1). Base is the run directory (parent of package/ and layperson_guide/).
    _rel_base = package.parent
    for _row in outputs:
        if isinstance(_row, dict) and _row.get("path"):
            _row["path"] = _relativize_receipt_path(_row["path"], _rel_base)
    receipt = {
        "schema_version": "mamey_layperson_guide_receipt_v1",
        "status": status,
        "package": package.name,
        "source_manifest": manifest_path.name,
        "source_manifest_sha256": _sha256(manifest_path),
        "claim_safety_footer": CLAIM_SAFETY,
        "producer": "mamey.layperson_guide via mamey.document_export",
        "outputs": outputs,
        "warnings": warnings,
    }
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _emit_receipt(receipt, receipt_path)
    return 0
