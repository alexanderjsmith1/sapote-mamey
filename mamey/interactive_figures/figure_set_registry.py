#!/usr/bin/env python3
"""Governed 200-set Figure Factory registry for the Codex presentation layer.

The registry is a deterministic design and planning layer.  It defines 25
scientific figure families across eight distinct analytical lenses, yielding
200 non-identical figure-set specifications.  A specification is not evidence
that its source layer exists: readiness, required gates, denominator policy,
missingness semantics, caption text, and claim ceilings remain explicit.

This module is post-seal and additive.  It never changes extraction, scoring,
release state, biological validation, or publication approval.
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
import html
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence


SCHEMA_VERSION = "sapote-mamey.codex-figure-set-registry.v1"
PROFILE = "CODEX_OPTIONAL_POST_SEAL"
GLOBAL_CLAIM_CEILING = (
    "Similarity is not identity. Genomic capacity is not expression, production, activity, "
    "validated novelty, ecological function, host causality, organism identity, or physical "
    "linkage. Missing evidence is not a biological negative."
)


@dataclass(frozen=True)
class Family:
    code: str
    name: str
    measure: str
    unit: str
    source_artifacts: tuple[str, ...]
    gate: str
    readiness: str
    shape: str
    family_ceiling: str


@dataclass(frozen=True)
class Lens:
    code: str
    name: str
    question: str
    transform: str
    form: str
    role: str
    scope: str


FAMILIES: tuple[Family, ...] = (
    Family("BND", "BGC boundary context", "boundary-state burden", "physical BGC/class membership",
           ("*_2_inventory.csv",), "physical_bgc_identity+boundary_denominator", "IMPLEMENTABLE_NOW", "state",
           "Assembly-boundary context does not establish complete pathway extent."),
    Family("CLS", "BGC class composition", "nonexclusive class capacity", "BGC-class membership",
           ("*_2_inventory.csv", "B2_Product_Class_Matrix"), "class_token_registry", "IMPLEMENTABLE_NOW", "matrix",
           "Product classes are nonexclusive hypotheses and are not exact products."),
    Family("COC", "BGC class co-occurrence", "class co-membership", "physical BGC",
           ("*_2_inventory.csv",), "physical_bgc_identity+class_token_registry", "IMPLEMENTABLE_NOW", "relation",
           "Class co-membership is not biochemical interaction or physical linkage beyond the source BGC row."),
    Family("LEN", "Reported BGC length", "reported-region length", "physical BGC",
           ("*_2_inventory.csv", "deep_data.json"), "boundary_stratification", "READY_SOURCE", "scalar",
           "Reported antiSMASH region length is not necessarily complete pathway size."),
    Family("CDS", "Physical CDS density", "deduplicated CDS density", "physical BGC",
           ("*_cds_table.csv", "*_2_inventory.csv"), "physical_gene_deduplication+physical_bgc_join", "READY_SOURCE", "scalar",
           "Annotation density is descriptive capacity, not expression or productivity."),
    Family("MLN", "Machinery gene length", "machinery-gene amino-acid length", "deduplicated physical CDS",
           ("*_cds_table.csv", "AS_All_Strains_Widget_Data.json"), "physical_gene_deduplication+role_precedence", "IMPLEMENTABLE_NOW", "scalar",
           "Length and annotation role do not confirm biochemical function."),
    Family("MRB", "Machinery role burden", "machinery-role gene burden", "strain/BGC/role",
           ("*_cds_table.csv", "AS_All_Strains_Widget_Data.json"), "physical_gene_deduplication+role_precedence", "IMPLEMENTABLE_NOW", "matrix",
           "Role labels are annotation-supported capacity categories, not confirmed activities."),
    Family("TAL", "Tailoring capacity", "tailoring-family burden", "deduplicated physical CDS/BGC",
           ("*_cds_table.csv", "PHYSICAL_GENE_ANNOTATION_ROWS.csv"), "tailoring_token_registry+physical_gene_deduplication", "READY_SOURCE", "matrix",
           "Tailoring annotations do not establish a final scaffold or product."),
    Family("REG", "Regulatory capacity", "regulator-family burden", "deduplicated physical CDS/BGC",
           ("*_cds_table.csv", "PHYSICAL_GENE_ANNOTATION_ROWS.csv"), "regulator_token_registry+physical_gene_deduplication", "READY_SOURCE", "matrix",
           "Regulator annotations do not establish expression state or causal control."),
    Family("RES", "Resistance and self-protection capacity", "resistance-tier burden", "BGC/trigger membership",
           ("gene_data.json", "deep_data.json", "*_4_triage_board.csv"), "cctt_class_compatibility+resistance_tier_guard", "READY_SOURCE", "state",
           "Resistance-like context is a routing signal, not confirmed self-protection or activity."),
    Family("TRN", "Transport capacity", "transporter-family burden", "deduplicated physical CDS/BGC",
           ("*_cds_table.csv", "PHYSICAL_GENE_ANNOTATION_ROWS.csv"), "transporter_token_registry+physical_gene_deduplication", "READY_SOURCE", "matrix",
           "Transport annotations do not establish substrate, direction, or export of a product."),
    Family("TTA", "TTA and bldA context", "TTA-bearing gene burden", "deduplicated physical CDS/BGC",
           ("*_cds_table.csv", "deep_data.json"), "tta_join_key+physical_gene_deduplication", "READY_SOURCE", "scalar",
           "TTA occurrence is a regulatory-context signal, not evidence of expression."),
    Family("MPG", "Per-gene MIBiG convergence", "rank-depth MIBiG support", "exact query gene/locus",
           ("mibig_per_gene.json", "mibig_per_gene.tsv", "knownclusterblast"), "exact_query_locus+rank_uncapped_provenance", "REQUIRES_CURATED_INGRESS", "relation",
           "Per-gene similarity supports convergence context only, not compound identity."),
    Family("KCB", "KnownClusterBlast anchors", "known-cluster similarity support", "BGC/reference hit",
           ("deep_data.json", "KnownClusterBlast", "*_8l_fig_kcb_anchors_data.csv"), "kcb_provenance_and_rank", "READY_SOURCE", "relation",
           "Known-cluster similarity is not identity, production, or activity."),
    Family("MOD", "NRPS/PKS module architecture", "module-domain burden and order", "module/domain row",
           ("*_domains.csv", "deep_data.json", "module tables"), "module_order+domain_provenance", "READY_SOURCE", "sequence",
           "Predicted module order and domains are capacity hypotheses, not confirmed products."),
    Family("SUB", "Module substrate calls", "substrate-call burden and uncertainty", "populated substrate call",
           ("*_domains.csv", "module tables"), "substrate_vocab+uncertainty_preservation", "READY_SOURCE", "matrix",
           "Substrate predictions are uncertain computational calls, not incorporated residues."),
    Family("DOM", "Domain architecture", "physical domain-family architecture", "deduplicated domain/BGC",
           ("*_domains.csv", "PHYSICAL_ASDOMAIN_ROWS.csv", "domain_level"), "physical_domain_deduplication+domain_synonym_registry", "READY_SOURCE", "sequence",
           "Domain annotations support capacity/architecture only, not product identity."),
    Family("ACT", "Active-site motif evidence", "active-site completeness", "BGC/motif row",
           ("deep_data.json", "active_site tables"), "motif_definition+source_availability", "READY_SOURCE", "state",
           "Motif presence or completeness is not direct catalytic validation."),
    Family("CCT", "Rare diagnostic chemistry", "diagnostic trigger evidence", "BGC/trigger membership",
           ("deep_data.json", "gene_data.json", "*_8h_fig_cctt_map_data.csv"), "cctt_class_compatibility+multi_marker_guard", "READY_SOURCE", "state",
           "Diagnostic markers are routing evidence and do not by themselves define a pathway."),
    Family("MIS", "Misanchor and primary-metabolism guards", "guard reason and disposition", "flagged BGC",
           ("*_4_triage_board.csv", "deep_data.json", "rules_registry.json"), "misanchor_guard+rules_registry_version", "READY_SOURCE", "state",
           "Guard status explains routing and does not establish biological absence."),
    Family("PRI", "AB/AF routing priors", "antibacterial/antifungal routing prior", "BGC/strain",
           ("*_4_triage_board.csv", "*_8c_fig_dapr_scatter_data.csv"), "prior_label_guard+score_version", "READY_SOURCE", "relation",
           "AB/AF values are deterministic routing priors, not measured bioactivity."),
    Family("NOV", "Novelty routing prior", "novelty-routing prior", "BGC/strain",
           ("*_4_triage_board.csv", "*_8k_fig_novelty_ranked_data.csv"), "prior_label_guard+score_version", "READY_SOURCE", "scalar",
           "The novelty prior is not a novelty claim."),
    Family("RGG", "RG-GMCI cross-contig evidence", "cross-contig evidence state", "candidate BGC pair",
           ("rggmci tables", "*_8n_fig_rggmci_rescue_data.csv"), "rggmci_gate+pair_identity", "READY_SOURCE", "relation",
           "RG-GMCI indicates a linkage candidate, not a physically validated pathway."),
    Family("HST", "Host and niche cohorts", "host-stratified capacity context", "provenance-supported strain/cohort",
           ("STRAIN_HOST_REGISTRY.csv", "AS_All_Strains_Widget_Data.json"), "host_provenance+unresolved_preservation", "IMPLEMENTABLE_NOW", "group",
           "Host association is descriptive context, not host causality or ecological function."),
    Family("EVD", "Evidence completeness and governance", "channel availability and gate state", "strain/BGC/evidence channel",
           ("manifest.json", "gate_validation.json", "*_7_missing_data_worklist.csv", "release manifests"), "channel_separation+independent_gate_manifest", "READY_SOURCE", "state",
           "Missing evidence is not a biological negative; engineering and science gates remain separate."),
)


LENSES: tuple[Lens, ...] = (
    Lens("OVR", "Cohort overview", "How is {measure} distributed across the governed cohort?",
         "preserve raw values; report governed denominator", "shape-aware overview", "MAIN", "cohort"),
    Lens("STR", "Per-strain labelled landscape", "How does {measure} vary for every included strain, including non-outliers?",
         "aggregate by strain; label every strain adjacent to its mark with vertical collision offsets", "label-rich dot plot", "MAIN", "strain"),
    Lens("CLS", "Class-stratified profile", "How does {measure} vary across governed BGC product-class memberships?",
         "explode nonexclusive class memberships; preserve physical-BGC key", "shared-scale small multiples", "SUPPLEMENT", "class"),
    Lens("BND", "Boundary and assembly context", "How does assembly boundary state change the observed {measure} profile?",
         "stratify Edge, Full-contig, and Interior; do not collapse missing boundary", "paired distribution facets", "METHODS", "boundary"),
    Lens("HST", "Host-cohort comparison", "How does {measure} compare across provenance-supported host cohorts and unresolved strains?",
         "use explicit host crosswalk; retain UNRESOLVED; show numerator and denominator", "point-range cohort comparison", "SUPPLEMENT", "host"),
    Lens("AVL", "Evidence availability", "Where is {measure} populated, observed-zero, missing, gated, or structurally unavailable?",
         "five-state evidence projection; never coerce missing to zero", "availability state matrix", "METHODS", "evidence"),
    Lens("SEN", "Denominator sensitivity", "How stable is {measure} under declared cohort, exclusion, boundary, and completeness sensitivities?",
         "paired governed estimates with explicit variant ledger; no silent denominator changes", "paired slope and interval plot", "METHODS", "sensitivity"),
    Lens("LED", "Lead-context without outlier filtering", "Where do declared lead strains/BGCs sit within the full {measure} denominator?",
         "show complete denominator; highlight only ledger-declared leads; label leads and nearest peers", "full-denominator contextual plot", "MAIN", "lead_context"),
)


def _recommended_form(family: Family, lens: Lens) -> str:
    if lens.code != "OVR":
        return lens.form
    return {
        "scalar": "ECDF with rug and raw-count sidecar",
        "matrix": "zero-aware heatmap with raw annotations",
        "relation": "labelled scatter or evidence network",
        "sequence": "ordered architecture strips",
        "state": "categorical state matrix",
        "group": "composition and point-range overview",
    }.get(family.shape, "shape-aware overview")


def _status_for(family: Family, lens: Lens) -> str:
    if family.readiness.startswith("REQUIRES_"):
        return family.readiness
    if lens.code == "HST" and family.code not in {"BND", "CLS", "MLN", "MRB", "TAL", "REG", "HST", "EVD"}:
        return "READY_SOURCE_REQUIRES_HOST_JOIN"
    if lens.code == "LED":
        return "READY_SOURCE_REQUIRES_LEAD_LEDGER"
    return family.readiness


def build_registry() -> list[dict[str, Any]]:
    """Return the deterministic 25 × 8 = 200 specification registry."""
    records: list[dict[str, Any]] = []
    serial = 0
    for family in FAMILIES:
        for lens in LENSES:
            serial += 1
            figure_id = f"FS{serial:03d}"
            title = f"{family.name} — {lens.name.lower()}"
            question = lens.question.format(measure=family.measure)
            status = _status_for(family, lens)
            caption = (
                f"{title}. The figure summarizes {family.measure} at the {family.unit} level using "
                f"the declared {lens.scope} scope. Raw numerator, denominator, missingness state, "
                f"and source provenance accompany the figure. {family.family_ceiling} {GLOBAL_CLAIM_CEILING}"
            )
            methods = (
                f"Source artifacts: {', '.join(family.source_artifacts)}. {lens.transform}. "
                f"Required gate: {family.gate}. The output must include a plotted-data sidecar, "
                f"caption/methods text, source fingerprints, and a render receipt."
            )
            records.append({
                "schema_version": SCHEMA_VERSION,
                "figure_set_id": figure_id,
                "family_id": family.code,
                "family": family.name,
                "lens_id": lens.code,
                "lens": lens.name,
                "title": title,
                "scientific_question": question,
                "unit": family.unit,
                "denominator_policy": "resolve at runtime; report included, excluded, missing, and gated counts",
                "source_artifacts": list(family.source_artifacts),
                "transform": lens.transform,
                "visual_form": _recommended_form(family, lens),
                "label_policy": (
                    "every included strain labelled adjacent to its mark; offset vertically without remote label rails"
                    if lens.code == "STR" else
                    "readable adjacent row/column/mark labels; no unlabeled highlighted point"
                ),
                "publication_role": lens.role,
                "status": status,
                "required_gates": sorted(set((family.gate + "+missingness_state+claim_ceiling").split("+"))),
                "missing_policy": "missing, unavailable, gated, observed zero, and populated are distinct states",
                "claim_ceiling": f"{family.family_ceiling} {GLOBAL_CLAIM_CEILING}",
                "caption_template": caption,
                "methods_template": methods,
                "codex_profile": PROFILE,
            })
    return records


def validate_registry(records: Sequence[dict[str, Any]]) -> list[str]:
    problems: list[str] = []
    if len(records) != 200:
        problems.append(f"expected 200 records, observed {len(records)}")
    required = {
        "figure_set_id", "family_id", "lens_id", "title", "scientific_question", "unit",
        "source_artifacts", "visual_form", "status", "required_gates", "missing_policy",
        "claim_ceiling", "caption_template", "methods_template", "codex_profile",
    }
    ids = [r.get("figure_set_id") for r in records]
    titles = [r.get("title") for r in records]
    signatures = [
        (r.get("family_id"), r.get("lens_id"), r.get("scientific_question"), r.get("visual_form"))
        for r in records
    ]
    for label, values in (("id", ids), ("title", titles), ("signature", signatures)):
        dupes = [value for value, count in Counter(values).items() if count > 1]
        if dupes:
            problems.append(f"duplicate {label}: {dupes[:5]}")
    for i, record in enumerate(records, 1):
        missing = sorted(required - set(record))
        if missing:
            problems.append(f"record {i} missing fields: {missing}")
        expected = f"FS{i:03d}"
        if record.get("figure_set_id") != expected:
            problems.append(f"record {i} id {record.get('figure_set_id')} != {expected}")
        if record.get("codex_profile") != PROFILE:
            problems.append(f"{expected} profile is not {PROFILE}")
        if not record.get("source_artifacts"):
            problems.append(f"{expected} has no source artifact contract")
        if not record.get("required_gates"):
            problems.append(f"{expected} has no required gates")
        ceiling = str(record.get("claim_ceiling", "")).lower()
        if "not identity" not in ceiling or "missing evidence" not in ceiling:
            problems.append(f"{expected} claim ceiling incomplete")
        if record.get("lens_id") == "STR" and "every included strain" not in record.get("label_policy", ""):
            problems.append(f"{expected} lacks all-strain adjacent-label policy")
    family_counts = Counter(r.get("family_id") for r in records)
    if set(family_counts.values()) != {8} or len(family_counts) != 25:
        problems.append(f"expected 25 families × 8 lenses, observed {dict(family_counts)}")
    return problems


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_csv(path: Path, records: Sequence[dict[str, Any]]) -> None:
    columns = [
        "figure_set_id", "family_id", "family", "lens_id", "lens", "title",
        "scientific_question", "unit", "denominator_policy", "source_artifacts", "transform",
        "visual_form", "label_policy", "publication_role", "status", "required_gates",
        "missing_policy", "claim_ceiling", "codex_profile",
    ]
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = _SafeDictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for record in records:
            row = dict(record)
            row["source_artifacts"] = "; ".join(record["source_artifacts"])
            row["required_gates"] = "; ".join(record["required_gates"])
            writer.writerow({key: row.get(key, "") for key in columns})


def _write_text(path: Path, records: Sequence[dict[str, Any]]) -> None:
    lines = [
        "# Sapote-Mamey 200 additional figure sets",
        "",
        f"Profile: `{PROFILE}`",
        "",
        f"> {GLOBAL_CLAIM_CEILING}",
        "",
    ]
    current = None
    for record in records:
        if record["family_id"] != current:
            current = record["family_id"]
            lines.extend([f"## {current} — {record['family']}", ""])
        lines.extend([
            f"### {record['figure_set_id']} — {record['lens']}",
            "",
            f"**Caption.** {record['caption_template']}",
            "",
            f"**Methods.** {record['methods_template']}",
            "",
            f"**Status.** `{record['status']}` · **Form.** {record['visual_form']}",
            "",
        ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _catalog_html(records: Sequence[dict[str, Any]]) -> str:
    payload = json.dumps(list(records), separators=(",", ":")).replace("</", "<\\/")
    families = "".join(
        f'<option value="{html.escape(f.code)}">{html.escape(f.code)} — {html.escape(f.name)}</option>'
        for f in FAMILIES
    )
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Sapote-Mamey 200 figure-set registry</title>
<style>:root{{--ink:#17212b;--muted:#596672;--line:#d8dee5;--paper:#f5f7f9;--card:#fff;--accent:#31688e}}*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:14px/1.45 system-ui,-apple-system,Segoe UI,sans-serif}}header,main{{max-width:1500px;margin:auto;padding:18px 22px}}h1{{margin:0 0 4px;font-size:25px}}.muted{{color:var(--muted)}}.controls{{display:flex;gap:10px;flex-wrap:wrap;margin:18px 0}}input,select{{font:inherit;padding:8px;border:1px solid var(--line);border-radius:6px;background:white}}input{{min-width:280px}}.stats{{display:flex;gap:16px;flex-wrap:wrap;font-weight:650;margin:10px 0}}.table-wrap{{overflow:auto;background:var(--card);border:1px solid var(--line);border-radius:8px}}table{{border-collapse:collapse;width:100%;min-width:1200px}}th,td{{padding:8px 9px;border-bottom:1px solid var(--line);vertical-align:top;text-align:left}}th{{position:sticky;top:0;background:#eaf0f4;z-index:2}}code{{white-space:nowrap}}.status{{font-weight:700;color:var(--accent)}}details{{max-width:560px}}summary{{cursor:pointer;color:var(--accent)}}@media(max-width:600px){{header,main{{padding:14px}}input{{min-width:100%}}}}</style></head><body><header><h1>Sapote-Mamey 200 figure-set registry</h1><div class="muted">25 scientific families × 8 analytical lenses · {html.escape(PROFILE)}</div><p>{html.escape(GLOBAL_CLAIM_CEILING)}</p></header><main><div class="controls"><label>Search <input id="q" type="search" placeholder="family, question, source, gate"></label><label>Family <select id="family"><option value="">All families</option>{families}</select></label><label>Status <select id="status"><option value="">All statuses</option></select></label></div><div class="stats"><span id="shown"></span><span id="families"></span></div><div class="table-wrap"><table><thead><tr><th>ID</th><th>Family</th><th>Lens</th><th>Question</th><th>Form</th><th>Status</th><th>Sources and gates</th></tr></thead><tbody id="rows"></tbody></table></div></main><script id="data" type="application/json">{payload}</script><script>
const data=JSON.parse(document.getElementById('data').textContent),q=document.getElementById('q'),family=document.getElementById('family'),status=document.getElementById('status'),rows=document.getElementById('rows');
[...new Set(data.map(d=>d.status))].sort().forEach(x=>status.insertAdjacentHTML('beforeend',`<option>${{x}}</option>`));
function esc(x){{return String(x).replace(/[&<>\"]/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}}[c]))}}
function render(){{const term=q.value.trim().toLowerCase(),view=data.filter(d=>(!family.value||d.family_id===family.value)&&(!status.value||d.status===status.value)&&(!term||JSON.stringify(d).toLowerCase().includes(term)));rows.innerHTML=view.map(d=>`<tr><td><code>${{esc(d.figure_set_id)}}</code></td><td><strong>${{esc(d.family_id)}}</strong><br>${{esc(d.family)}}</td><td>${{esc(d.lens)}}</td><td>${{esc(d.scientific_question)}}<details><summary>Caption and methods</summary><p>${{esc(d.caption_template)}}</p><p>${{esc(d.methods_template)}}</p></details></td><td>${{esc(d.visual_form)}}</td><td class="status">${{esc(d.status)}}</td><td>${{esc(d.source_artifacts.join('; '))}}<br><span class="muted">${{esc(d.required_gates.join('; '))}}</span></td></tr>`).join('');document.getElementById('shown').textContent=`${{view.length}} of ${{data.length}} sets`;document.getElementById('families').textContent=`${{new Set(view.map(d=>d.family_id)).size}} families`}}
[q,family,status].forEach(x=>x.addEventListener('input',render));render();</script></body></html>"""


def emit_registry(outdir: str | Path, *, family: str | None = None, status: str | None = None) -> dict[str, Any]:
    destination = Path(outdir).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    all_records = build_registry()
    problems = validate_registry(all_records)
    selected = [
        record for record in all_records
        if (not family or record["family_id"] == family.upper())
        and (not status or record["status"] == status)
    ]
    json_path = destination / "FIGURE_SET_REGISTRY_200.json"
    csv_path = destination / "FIGURE_SET_REGISTRY_200.csv"
    text_path = destination / "CAPTIONS_METHODS_200.md"
    html_path = destination / "OPEN_200_FIGURE_SET_REGISTRY.html"
    json_path.write_text(json.dumps(selected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_csv(csv_path, selected)
    _write_text(text_path, selected)
    html_path.write_text(_catalog_html(selected), encoding="utf-8")
    family_counts = Counter(record["family_id"] for record in selected)
    status_counts = Counter(record["status"] for record in selected)
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if not problems else "FAIL",
        "profile": PROFILE,
        "registry_count": len(selected),
        "full_registry_count": len(all_records),
        "family_count": len(family_counts),
        "lens_count": len({record["lens_id"] for record in selected}),
        "family_counts": dict(sorted(family_counts.items())),
        "status_counts": dict(sorted(status_counts.items())),
        "validation_problems": problems,
        "claim_ceiling": GLOBAL_CLAIM_CEILING,
        "filters": {"family": family, "status": status},
        "outputs": [],
    }
    receipt_path = destination / "REGISTRY_QA_RECEIPT.json"
    for path in (json_path, csv_path, text_path, html_path):
        receipt["outputs"].append({"path": path.name, "sha256": _sha256(path)})
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--family", choices=[family.code for family in FAMILIES], default=None)
    parser.add_argument("--status", default=None)
    args = parser.parse_args(argv)
    result = emit_registry(args.outdir, family=args.family, status=args.status)
    emit(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
