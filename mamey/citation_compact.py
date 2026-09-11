"""Citation-compact helpers for Sapote-Mamey reports.

This module is intentionally small and output-layer focused. It does not alter
scoring, BGC classification, cassette calls, or triage order.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Iterable, Any
import csv
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import json
import os
import re


def _atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    """AUDIT_374: tmp-sibling + os.replace, so a crash mid-write never leaves a
    truncated citation-compact deliverable on disk (matches mamey/packaging.py's helper)."""
    path = Path(path)
    tmp = str(path) + ".tmp"
    try:
        with open(tmp, "w", encoding=encoding) as fh:
            fh.write(text)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    os.replace(tmp, str(path))

GLOBAL_BGC_CAVEAT = (
    "Genome mining identifies biosynthetic gene-cluster capacity and prioritizes "
    "hypotheses for chemistry and bioassay work. It does not by itself prove "
    "production, structure, or activity of a purified compound."
)

METHOD_CITATION_REGISTRY = {
    "antismash_8": {
        "citation_id": "CIT-METHOD-ANTISMASH-8",
        "source_status": "verified",
        "citation_label": "antiSMASH 8.0: extended gene cluster detection capabilities and analyses of chemistry, enzymology and regulation",
        "doi": "10.1093/nar/gkaf334",
        "supports": ["BGC detection", "antiSMASH product and region calls"],
    },
    "mibig_4": {
        "citation_id": "CIT-DB-MIBIG-4",
        "source_status": "verified",
        "citation_label": "MIBiG 4.0: advancing biosynthetic gene cluster curation through global collaboration",
        "doi": "10.1093/nar/gkae1115",
        "supports": ["MIBiG reference entries", "KnownClusterBlast dereplication context"],
    },
}

PRIORITY_TIERS_REQUIRING_CITATION = {"EXCEPTIONAL", "HIGH"}


@dataclass
class CitationRecord:
    citation_id: str
    scope: str
    source_status: str
    citation_label: str
    doi: str = ""
    pmid: str = ""
    url: str = ""
    mibig_id: str = ""
    accession: str = ""
    supports: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class CompactLeadRecord:
    lead_id: str
    strain_id: str
    lead_priority: str
    interpretation_scope: str
    evidence_basis: list[str]
    citation_basis: list[dict[str, Any]]
    uncertainty_flags: list[str]
    next_experiment: str
    bgc_id: str = ""
    stable_locus: str = ""


@dataclass
class LiteratureSearchTask:
    task_id: str
    strain_id: str
    bgc_id: str
    stable_locus: str
    candidate_class: str
    evidence_basis: list[str]
    citation_need: str
    search_instruction: str
    must_find: list[str]
    do_not_infer: str
    output_format: str
    source_status: str = "citation_needed"


def normalize_citation_basis(value: Any) -> list[dict[str, Any]]:
    """Return citation_basis as a list of dicts; malformed/missing values become []."""
    if not value:
        return []
    if isinstance(value, list):
        return [v for v in value if isinstance(v, dict)]
    return []


def priority_requires_citation(priority: str, required: set[str] | None = None) -> bool:
    tiers = required or PRIORITY_TIERS_REQUIRING_CITATION
    return (priority or "").upper() in tiers


def validate_priority_citation_coverage(
    leads: Iterable[dict[str, Any]],
    required_tiers: set[str] | None = None,
) -> list[dict[str, str]]:
    """Return coverage errors for priority leads missing citation_basis.

    Missing citations should be represented explicitly with a citation record whose
    source_status is citation_needed. Silent omission fails.
    """
    errors: list[dict[str, str]] = []
    for lead in leads:
        priority = str(lead.get("lead_priority", "")).upper()
        if not priority_requires_citation(priority, required_tiers):
            continue
        basis = normalize_citation_basis(lead.get("citation_basis"))
        if not basis:
            errors.append({
                "lead_id": str(lead.get("lead_id", "")),
                "severity": "HIGH",
                "error": "priority lead missing citation_basis",
            })
            continue
        for idx, citation in enumerate(basis):
            if not citation.get("citation_id"):
                errors.append({
                    "lead_id": str(lead.get("lead_id", "")),
                    "severity": "MEDIUM",
                    "error": f"citation_basis[{idx}] missing citation_id",
                })
            if citation.get("source_status") not in {"verified", "citation_needed", "not_applicable", "operator_supplied"}:
                errors.append({
                    "lead_id": str(lead.get("lead_id", "")),
                    "severity": "MEDIUM",
                    "error": f"citation_basis[{idx}] has invalid source_status",
                })
    return errors


def caveat_count(text: str, caveat: str = GLOBAL_BGC_CAVEAT) -> int:
    """Count exact global caveat occurrences, ignoring repeated whitespace."""
    def norm(s: str) -> str:
        return re.sub(r"\s+", " ", s.strip())
    return norm(text).count(norm(caveat))


def validate_global_caveat_count(text: str, max_count: int = 1) -> list[dict[str, str]]:
    count = caveat_count(text)
    if count > max_count:
        return [{
            "severity": "HIGH",
            "error": "global BGC caveat repeated",
            "count": str(count),
            "max_allowed": str(max_count),
        }]
    return []


def write_citation_ledger_csv(records: Iterable[CitationRecord], path: str | Path) -> Path:
    path = Path(path)
    rows = [asdict(r) for r in records]
    fieldnames = [
        "citation_id", "scope", "source_status", "citation_label", "doi", "pmid",
        "url", "mibig_id", "accession", "supports", "notes",
    ]
    import io as _io
    _buf = _io.StringIO()
    writer = _SafeDictWriter(_buf, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        row = dict(row)
        row["supports"] = "; ".join(row.get("supports") or [])
        writer.writerow(row)
    _atomic_write_text(path, _buf.getvalue())
    return path


def write_citation_ledger_json(
    records: Iterable[CitationRecord],
    path: str | Path,
    *,
    bundle_version: str = "",
    strain_id: str = "",
) -> Path:
    path = Path(path)
    payload = {
        "schema_version": "citation_ledger_v1",
        "bundle_version": bundle_version,
        "strain_id": strain_id,
        "records": [asdict(r) for r in records],
    }
    _atomic_write_text(path, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    return path


def compact_interpretation_scope(default: str = "genome-mining interpretation") -> str:
    """Shared compact wording for lead tables.

    This replaces older reader-facing scope prose with citation-first interpretation language.
    Uncertainty belongs in uncertainty_flags; citations belong in citation_basis.
    """
    return default


# ---------------------------------------------------------------------------
# Runtime package emission
# ---------------------------------------------------------------------------

def _find_triage_csv(package_dir: Path) -> Path | None:
    hits = sorted(package_dir.glob("*_4_triage_board.csv"))
    return hits[0] if hits else None


def _read_triage_rows(package_dir: str | Path) -> list[dict[str, str]]:
    package_dir = Path(package_dir)
    triage = _find_triage_csv(package_dir)
    if not triage:
        return []
    with triage.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _lead_priority(row: dict[str, str]) -> str:
    raw = (
        row.get("Lead_tier_auto")
        or row.get("Lead_Tier")
        or row.get("lead_tier")
        or row.get("Tier")
        or row.get("Priority")
        or "INVENTORY"
    )
    val = str(raw).strip()
    mapping = {
        "exceptional": "EXCEPTIONAL",
        "high": "HIGH",
        "medium": "MEDIUM",
        "med": "MEDIUM",
        "inventory": "INVENTORY",
        "low": "LOW",
    }
    return mapping.get(val.lower(), val.upper() if val else "INVENTORY")


def _safe_cell(row: dict[str, str], *names: str) -> str:
    for name in names:
        val = row.get(name)
        if val not in (None, ""):
            return str(val)
    return ""


def _evidence_basis(row: dict[str, str]) -> list[str]:
    bits = []
    for label, cols in [
        ("KCB", ("KCB_top", "kcb_top", "Closest_product", "Top_KCB")),
        ("CCTT", ("CCTT_triggers", "cctt_triggers")),
        ("AB", ("AB_auto", "ab_score")),
        ("AF", ("AF_auto", "af_score")),
        ("Boundary", ("Boundary", "boundary")),
        ("Products", ("Products", "products")),
    ]:
        val = _safe_cell(row, *cols)
        if val:
            bits.append(f"{label}: {val}")
    return bits or ["inventory/triage row present"]


def _citation_basis(row: dict[str, str]) -> list[dict[str, Any]]:
    """Build a compact citation basis without inventing literature.

    If a package has no verified external reference record, emit an explicit
    citation_needed marker. This satisfies the compact-mode requirement that
    missing citations be visible rather than silent.
    """
    basis: list[dict[str, Any]] = []
    kcb = _safe_cell(row, "KCB_top", "kcb_top", "Closest_product", "Top_KCB")
    mibig = _safe_cell(row, "MIBiG", "mibig_id", "MIBIG_ID")
    accession = _safe_cell(row, "accession", "Reference_accession", "KCB_accession")
    bgc_id = _safe_cell(row, "BGC_ID", "bgc_id") or "BGC"
    if kcb or mibig or accession:
        basis.append({
            "citation_id": f"CIT-{bgc_id}-KCB",
            "source_status": "operator_supplied",
            "citation_label": kcb or mibig or accession,
            "supports": ["similarity anchor", "dereplication context"],
        })
    else:
        basis.append({
            "citation_id": f"CIT-{bgc_id}-NEEDED",
            "source_status": "citation_needed",
            "citation_label": "primary family/reference citation needed",
            "supports": ["class/family interpretation"],
        })
    # Always seed method/database citations from the verified internal registry.
    # These are method/database provenance records, not literature support for a
    # named compound-family claim.
    existing_ids = {str(x.get("citation_id")) for x in basis}
    for key in ("antismash_8", "mibig_4"):
        rec = dict(METHOD_CITATION_REGISTRY[key])
        if rec["citation_id"] not in existing_ids:
            basis.insert(0, rec)
    return basis


def _uncertainty_flags(row: dict[str, str]) -> list[str]:
    flags = []
    for col in ["Standing_rule", "Standing_rule_flag", "Primary_metab_flag", "Misanchor_Flag", "Two_Model_Flag", "Downgrade"]:
        val = row.get(col)
        if val not in (None, "", "0", "False", "false", "NO", "No"):
            flags.append(f"{col}: {val}")
    if not flags:
        flags.append("none recorded")
    return flags


def leads_from_triage(package_dir: str | Path, strain_id: str = "") -> list[CompactLeadRecord]:
    """Create compact lead records from an existing package triage board."""
    rows = _read_triage_rows(package_dir)
    leads: list[CompactLeadRecord] = []
    for idx, row in enumerate(rows, start=1):
        bgc_id = _safe_cell(row, "BGC_ID", "bgc_id") or f"BGC{idx:03d}"
        priority = _lead_priority(row)
        lead_id = f"{priority[:3] or 'LED'}-{idx:02d}"
        locus = _safe_cell(row, "Assembly_Locator", "Node_ID", "Contig", "contig", "node_id")
        products = _safe_cell(row, "Products", "products") or "biosynthetic region"
        leads.append(CompactLeadRecord(
            lead_id=lead_id,
            strain_id=strain_id,
            bgc_id=bgc_id,
            stable_locus=locus,
            lead_priority=priority,
            interpretation_scope=products or "biosynthetic region",
            evidence_basis=_evidence_basis(row),
            citation_basis=_citation_basis(row),
            uncertainty_flags=_uncertainty_flags(row),
            next_experiment="LC-MS/MS detection plus targeted bioassay or expression check",
        ))
    return leads


def citation_records_from_leads(leads: Iterable[CompactLeadRecord]) -> list[CitationRecord]:
    records: dict[str, CitationRecord] = {}
    for lead in leads:
        for citation in lead.citation_basis:
            cid = str(citation.get("citation_id") or "")
            if not cid or cid in records:
                continue
            records[cid] = CitationRecord(
                citation_id=cid,
                scope="reference_cluster" if "KCB" in cid else "compound_family",
                source_status=str(citation.get("source_status") or "citation_needed"),
                citation_label=str(citation.get("citation_label") or "citation needed"),
                supports=[str(x) for x in citation.get("supports", [])],
            )
    if not records:
        records["CIT-METHOD-NEEDED"] = CitationRecord(
            citation_id="CIT-METHOD-NEEDED",
            scope="method",
            source_status="citation_needed",
            citation_label="project-level method citation needed",
            supports=["genome-mining method"],
        )
    return list(records.values())


def _join_list(value: list[str] | list[dict[str, Any]]) -> str:
    if not value:
        return ""
    if isinstance(value[0], dict):  # type: ignore[index]
        return "; ".join(str(v.get("citation_id", v)) for v in value)  # type: ignore[union-attr]
    return "; ".join(str(v) for v in value)


def _template_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "templates" / "citation_compact"


def _load_template(name: str) -> str:
    path = _template_dir() / name
    return path.read_text(encoding="utf-8")


def _lead_table_markdown(leads: list[CompactLeadRecord]) -> str:
    lines = [
        "| lead_id | strain_id | bgc_id | stable_locus | lead_priority | interpretation_scope | evidence_basis | citation_basis | uncertainty_flags | next_experiment |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for lead in leads:
        lines.append(
            "| " + " | ".join([
                lead.lead_id,
                lead.strain_id,
                lead.bgc_id,
                lead.stable_locus,
                lead.lead_priority,
                lead.interpretation_scope.replace("|", "/"),
                _join_list(lead.evidence_basis).replace("|", "/"),
                _join_list(lead.citation_basis).replace("|", "/"),
                _join_list(lead.uncertainty_flags).replace("|", "/"),
                lead.next_experiment.replace("|", "/"),
            ]) + " |"
        )
    return "\n".join(lines) + "\n"


def render_citation_compact_reports(
    package_dir: str | Path,
    strain_id: str = "",
    *,
    bundle_version: str = "",
) -> dict[str, Any]:
    """Emit citation-compact ledger and Markdown reports into a sealed package dir.

    Called before final manifest/checksum/zip so outputs are tracked.
    """
    package_dir = Path(package_dir)
    strain_id = strain_id or package_dir.parent.name or package_dir.name
    out_dir = package_dir / "citation_compact"
    out_dir.mkdir(exist_ok=True)

    leads = leads_from_triage(package_dir, strain_id=strain_id)
    citation_records = citation_records_from_leads(leads)
    literature_tasks = literature_search_tasks_from_leads(leads)
    ledger_csv = write_citation_ledger_csv(citation_records, package_dir / "Citation_Ledger.csv")
    ledger_json = write_citation_ledger_json(
        citation_records,
        package_dir / "Citation_Ledger.json",
        bundle_version=bundle_version,
        strain_id=strain_id,
    )
    workorder_md = write_literature_search_workorder_md(
        literature_tasks,
        out_dir / "Literature_Search_WorkOrder.md",
        strain_id=strain_id,
    )
    workorder_json = write_literature_search_workorder_json(
        literature_tasks,
        out_dir / "Literature_Search_WorkOrder.json",
        bundle_version=bundle_version,
        strain_id=strain_id,
    )

    lead_table = _lead_table_markdown(leads)
    lead_table_path = out_dir / f"{strain_id}_lead_table_citation_compact.md"
    _atomic_write_text(
        lead_table_path,
        _load_template("lead_table.md") + "\n\n## Rendered Lead Table\n\n" + lead_table,
    )

    replacements = {
        "{{GLOBAL_BGC_CAVEAT}}": GLOBAL_BGC_CAVEAT,
        "{{lead_id}}": leads[0].lead_id if leads else "no-priority-lead",
        "{{stable_locus}}": leads[0].stable_locus if leads else "",
        "{{lead_priority}}": leads[0].lead_priority if leads else "",
        "{{interpretation_scope}}": leads[0].interpretation_scope if leads else "",
        "{{evidence_basis}}": _join_list(leads[0].evidence_basis) if leads else "",
        "{{citation_basis}}": _join_list(leads[0].citation_basis) if leads else "",
        "{{uncertainty_flags}}": _join_list(leads[0].uncertainty_flags) if leads else "",
        "{{next_experiment}}": leads[0].next_experiment if leads else "",
        "{{target_hypothesis}}": "testable biosynthetic-capacity hypothesis",
        "{{detection_method}}": "LC-MS/MS or targeted metabolomics",
        "{{primary_assay}}": "matched antimicrobial / antifungal assay",
        "{{decision_threshold}}": "detect compound-family signal and reproducible activity",
        "{{plain_language_value}}": "a genome-mining lead worth testing",
    }

    outputs = [ledger_csv, ledger_json, workorder_md, workorder_json, lead_table_path]
    for name, suffix in [
        ("technical_report.md", "technical_report_citation_compact.md"),
        ("bench_guide.md", "bench_guide_citation_compact.md"),
        ("layperson_guide.md", "layperson_guide_citation_compact.md"),
    ]:
        text = _load_template(name)
        for key, val in replacements.items():
            text = text.replace(key, str(val))
        text += "\n\n## Rendered Citation-Compact Lead Table\n\n" + lead_table
        path = out_dir / f"{strain_id}_{suffix}"
        _atomic_write_text(path, text)
        outputs.append(path)

    lead_dicts = [asdict(lead) for lead in leads]
    coverage_errors = validate_priority_citation_coverage(lead_dicts)
    report_text = "\n\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in outputs if p.suffix == ".md")
    # Package-level policy: one global genome-mining caveat total across all
    # citation-compact Markdown outputs. Do not allow one caveat per report.
    caveat_errors = validate_global_caveat_count(report_text, max_count=1)
    qa = {
        "status": "PASS_STRUCTURE" if not coverage_errors and not caveat_errors else "WARN",
        "strain_id": strain_id,
        "lead_count": len(leads),
        "citation_count": len(citation_records),
        "literature_task_count": len(literature_tasks),
        "literature_workorder_md": str(workorder_md.relative_to(package_dir)),
        "literature_workorder_json": str(workorder_json.relative_to(package_dir)),
        "outputs": [str(p.relative_to(package_dir)) for p in outputs],
        "coverage_errors": coverage_errors,
        "caveat_errors": caveat_errors,
        "note": "citation-compact outputs are reader-facing supplements; scoring unchanged",
    }
    qa_path = out_dir / "CITATION_COMPACT_QA.json"
    _atomic_write_text(qa_path, json.dumps(qa, indent=2))
    outputs.append(qa_path)
    qa["outputs"] = [str(p.relative_to(package_dir)) for p in outputs]
    return qa


def _citation_needed_items(lead: CompactLeadRecord) -> list[dict[str, Any]]:
    needed = []
    for citation in lead.citation_basis:
        if citation.get("source_status") == "citation_needed":
            needed.append(citation)
    return needed


def literature_search_tasks_from_leads(leads: Iterable[CompactLeadRecord]) -> list[LiteratureSearchTask]:
    """Create web-chat-ready literature search tasks for citation_needed leads.

    This intentionally does not invent citations. It invents search instructions.
    """
    tasks: list[LiteratureSearchTask] = []
    for lead in leads:
        for idx, citation in enumerate(_citation_needed_items(lead), start=1):
            task_id = f"LIT-{lead.bgc_id or lead.lead_id}-{idx:03d}".replace(" ", "_")
            candidate_class = lead.interpretation_scope.split(";")[0].strip() or "biosynthetic lead"
            need = str(citation.get("citation_label") or "primary literature citation needed")
            instruction = (
                "Find the primary literature reference supporting this BGC-family or method interpretation.\n\n"
                f"Strain: {lead.strain_id}\n"
                f"BGC: {lead.bgc_id}\n"
                f"Locus: {lead.stable_locus}\n"
                f"Candidate class: {candidate_class}\n"
                f"Evidence basis: {'; '.join(lead.evidence_basis)}\n"
                f"Need: {need}\n\n"
                "Return only: citation_id | citation_label | DOI | PMID | source_status | one-sentence relevance.\n"
                "Do not infer activity from class. If no primary reference is found, write citation_needed."
            )
            tasks.append(LiteratureSearchTask(
                task_id=task_id,
                strain_id=lead.strain_id,
                bgc_id=lead.bgc_id,
                stable_locus=lead.stable_locus,
                candidate_class=candidate_class,
                evidence_basis=list(lead.evidence_basis),
                citation_need=need,
                search_instruction=instruction,
                must_find=["primary article if available", "DOI", "PMID", "one-sentence relevance"],
                do_not_infer="Do not infer activity, target, or product identity from class alone.",
                output_format="citation_id | citation_label | DOI | PMID | source_status | one-sentence relevance",
            ))
    return tasks


def write_literature_search_workorder_json(
    tasks: Iterable[LiteratureSearchTask],
    path: str | Path,
    *,
    bundle_version: str = "",
    strain_id: str = "",
) -> Path:
    path = Path(path)
    payload = {
        "schema_version": "literature_search_workorder_v1",
        "bundle_version": bundle_version,
        "strain_id": strain_id,
        "tasks": [asdict(task) for task in tasks],
    }
    _atomic_write_text(path, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    return path


def write_literature_search_workorder_md(
    tasks: Iterable[LiteratureSearchTask],
    path: str | Path,
    *,
    strain_id: str = "",
) -> Path:
    path = Path(path)
    tasks = list(tasks)
    lines = [
        "# Literature Search Work Order — Citation Compact",
        "",
        f"Strain: `{strain_id}`" if strain_id else "Strain: not supplied",
        "",
        "Purpose: fill `citation_needed` rows from `Citation_Ledger.csv/json` without inventing citations.",
        "",
        "Rules for the web/literature chat:",
        "",
        "1. Find primary literature when possible.",
        "2. Return DOI and PMID when available.",
        "3. Do not infer activity, target, or product identity from compound/BGC class alone.",
        "4. If no primary reference is found, return `citation_needed`.",
        "5. Keep output ledger-ready.",
        "",
    ]
    if not tasks:
        lines.extend(["No citation-needed tasks were generated.", ""])
    for task in tasks:
        lines.extend([
            f"## {task.task_id}",
            "",
            f"- Strain: `{task.strain_id}`",
            f"- BGC: `{task.bgc_id}`",
            f"- Locus: `{task.stable_locus}`",
            f"- Candidate class: {task.candidate_class}",
            f"- Citation need: {task.citation_need}",
            f"- Evidence basis: {'; '.join(task.evidence_basis)}",
            "",
            "### Search instruction",
            "",
            "```text",
            task.search_instruction,
            "```",
            "",
            "### Required output format",
            "",
            "```text",
            task.output_format,
            "```",
            "",
        ])
    _atomic_write_text(path, "\n".join(lines))
    return path


def emit_citation_compact_outputs(
    package_dir: str | Path,
    strain_id: str = "",
    *,
    bundle_version: str = "",
) -> dict[str, Any]:
    """Public wrapper used by CLI/package writers."""
    return render_citation_compact_reports(package_dir, strain_id, bundle_version=bundle_version)
