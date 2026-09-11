#!/usr/bin/env python3
"""schema_deployed_audit.py — reconcile the coded sheets in WORKBOOK_SCHEMA.md against what the
workbook builder actually emits. Buckets every sheet as MATCHED / MAPPED / SCHEMA-ONLY (deferred or
build) / DEPLOYED-ONLY, and emits a markdown report + JSON.

Usage: python tools/schema_deployed_audit.py <workbook.xlsx> <WORKBOOK_SCHEMA.md> [out.md]
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import sys, re, json
import openpyxl

# deployed sheet name -> coded schema equivalent (curated). Names that differ but mean the same sheet.
DEPLOYED_TO_CODE = {
    "TFBS_Motifs": "F2_Regulatory_TFBS",
}
# deployed sheets that are legitimate detail/overlay sheets not in the coded A–H index.
DEPLOYED_OVERLAY = {
    "About": "metadata banner",
    "BGC_Scan_Profile": "Tier-1 per-BGC scan detail (Mamey)",
    "BGC_Domain_Architecture": "per-BGC domain arch detail (Mamey)",
    "BGC_Class_Predictions": "per-BGC class predictions (Mamey)",
    "Gene_NRPS_PKS_Substrates": "gene-level substrate detail (Mamey)",
    "Gene_Active_Sites": "gene-level active-site detail (Mamey)",
    "Gene_RiPP_Cores": "RiPP core detail (Mamey)",
    "Gene_Domain_Hits": "gene-level domain-hit detail (Mamey)",
    "Cross_Strain_Compare": "cross-strain comparison overlay",
    "TIGRFAM_Check": "curated TIGRFAM diagnostic panel (4 markers)",
    "Strain_Catalog": "full strain catalog (banked + pending)",
    "Cross_Strain_Class_Prevalence": "v1.2-recognized cross-strain overlay",
    "Cross_Strain_Findings": "v1.2-recognized cross-strain overlay",
    "Strain_Cohort_Context": "v1.2-recognized cross-strain overlay",
}
# schema-only coded sheets: disposition (DEFER reason or BUILD).
SCHEMA_ONLY_DISPOSITION = {
    "A3_Run_Manifest": ("DEFER", "runner per-run log; not required for cross-strain workbook"),
    "C3_Lead_Tier_Summary": ("DEFER", "Sapote judgment summary; on-demand"),
    "C4_Strain_Decision_Table": ("DEFER", "Sapote composite decision; on-demand"),
    "D3_RGGMCI_Promoted": ("DEFER", "Sapote-promoted rescue groups; on-demand"),
    "E1_Mode_B_Index": ("DEFER", "deep Mode-B; per-analysis"),
    "E2_Comparative_Pairs": ("DEFER", "deep Mode-B; per-analysis"),
    "E3_Megacluster_Registry": ("BUILD", "deterministic (BGCs >150 kb) — buildable from B1"),
    "E4_A_Domain_Summary": ("DEFER", "deep Mode-B; per-analysis"),
    "F1_Ecology_Readiness": ("DEFER", "ecology layer; on-demand"),
    "F3_Ecology_Theme_Board": ("DEFER", "Sapote ecological themes; on-demand"),
    "G1_Literature_Index": ("BUILD", "seed from Lit_Verification_* docs"),
    "G2_Validation_Roles": ("DEFER", "manuscript validation assignment; on-demand"),
    "G3_Hallucination_Trap_Audit": ("DEFER", "per-analysis judgment sheet"),
    "H1_Handoff_Log": ("DEFER", "handoff events; populated at handoff"),
    "H2_Gap_Queue": ("DEFER", "gap tracking; on-demand"),
    "H3_Schema_Version": ("BUILD", "fixed metadata sheet — buildable"),
}


def parse_schema_codes(md_path):
    coded = {}
    for line in open(md_path):
        m = re.match(r"\|\s*([A-H]\d)\s*\|\s*`([^`]+)`", line)
        if m:
            coded[m.group(1)] = m.group(2)
    return coded  # code -> canonical sheet name


def main(wb_path, md_path, out=None):
    coded = parse_schema_codes(md_path)
    coded_names = set(coded.values())
    wb = openpyxl.load_workbook(wb_path, read_only=True)
    deployed = set(wb.sheetnames); wb.close()

    matched, mapped, schema_only, deployed_only = [], [], [], []
    for code, name in sorted(coded.items()):
        if name in deployed:
            matched.append((code, name))
        elif any(DEPLOYED_TO_CODE.get(d) == name for d in deployed):
            src = next(d for d in deployed if DEPLOYED_TO_CODE.get(d) == name)
            mapped.append((code, name, src))
        else:
            disp, why = SCHEMA_ONLY_DISPOSITION.get(name, ("DEFER", "unclassified"))
            schema_only.append((code, name, disp, why))
    for d in sorted(deployed):
        if d in coded_names or d in DEPLOYED_TO_CODE:
            continue
        deployed_only.append((d, DEPLOYED_OVERLAY.get(d, "uncatalogued — review")))

    report = []
    report.append("# Schema-vs-Deployed Audit (WORKBOOK_SCHEMA.md v1.2)\n")
    report.append(f"Coded sheets in schema: **{len(coded)}** · deployed sheets: **{len(deployed)}**\n")
    report.append(f"MATCHED **{len(matched)}** · MAPPED **{len(mapped)}** · SCHEMA-ONLY **{len(schema_only)}** · DEPLOYED-ONLY **{len(deployed_only)}**\n")

    report.append("\n## MATCHED — coded sheet exists in the build\n")
    for code, name in matched:
        report.append(f"- `{code}` `{name}`")
    report.append("\n## MAPPED — deployed under a different name (reconcile the name)\n")
    for code, name, src in mapped:
        report.append(f"- `{code}` `{name}`  ⇐ deployed as `{src}`")
    report.append("\n## SCHEMA-ONLY — in schema, not built (disposition)\n")
    for code, name, disp, why in schema_only:
        report.append(f"- `{code}` `{name}` — **{disp}**: {why}")
    report.append("\n## DEPLOYED-ONLY — built but not in the coded index\n")
    for d, desc in deployed_only:
        report.append(f"- `{d}` — {desc}")

    builds = [n for _, n, d, _ in schema_only if d == "BUILD"]
    report.append("\n## Recommended actions\n")
    report.append(f"1. **BUILD next** (deterministic / seedable): {', '.join('`'+b+'`' for b in builds) or '(none)'}.")
    report.append("2. **Reconcile MAPPED names**: either rename deployed sheets to coded names or add the deployed name as an accepted alias in the schema.")
    report.append("3. **Accept DEPLOYED-ONLY detail/overlay sheets** in the schema (assign codes or list as recognized overlays) so the validator stops flagging them as extra.")
    report.append("4. **DEFER** the remaining Sapote judgment / per-analysis sheets — they populate on demand, not on every build.")
    report.append("5. **Column-name divergence** (e.g. A2 `strain`/`taxonomy` in schema vs `SID`/`Organism` deployed) is the larger reconciliation: pick one canonical naming and update either the builder or the schema column specs. Tracked separately from sheet presence.")

    text = "\n".join(report) + "\n"
    out = out or "SCHEMA_DEPLOYED_AUDIT.md"
    open(out, "w").write(text)
    js = {"matched": [list(x) for x in matched], "mapped": [list(x) for x in mapped],
          "schema_only": [list(x) for x in schema_only], "deployed_only": [list(x) for x in deployed_only]}
    open(out.replace(".md", ".json"), "w").write(json.dumps(js, indent=2))
    emit(f"audit: MATCHED {len(matched)} | MAPPED {len(mapped)} | SCHEMA-ONLY {len(schema_only)} | DEPLOYED-ONLY {len(deployed_only)} -> {out}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("usage: schema_deployed_audit.py <workbook.xlsx> <WORKBOOK_SCHEMA.md> [out.md]")
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
