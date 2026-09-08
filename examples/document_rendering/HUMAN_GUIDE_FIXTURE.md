---
schema_version: sapote-markdown-1.0
document_type: human_guide
title: Sapote-Mamey in Five Minutes
subtitle: A compact guide to extraction, interpretation, and safe next steps
audience: New users, collaborators, and reviewers
authority: User documentation; not a biological result
render_profile: human_guide
claim_safety_footer: Software guidance only; biological conclusions require source review and appropriate experiments.
---

# What Sapote-Mamey does

Sapote-Mamey helps a user turn antiSMASH output into a traceable evidence package and then conduct a governed interpretation. The program keeps deterministic extraction separate from scientific judgment.

> [LEAD] The short version
> Mamey extracts and packages source-derived facts. Sapote helps a human or governed author interpret those facts without converting similarity, capacity, or missing evidence into stronger claims.

## A five-minute quickstart

1. Inspect the antiSMASH ZIP before a full run.
2. Run Mamey in `gold` mode with a strain identifier, taxonomy, and source context.
3. Validate the sealed package and read `manifest.json` first.
4. Use post-seal figures or Mode B only after deterministic extraction completes.
5. Preserve claim ceilings when sharing any downstream report.

<!-- sapote:table id=quickstart layout=portrait repeat_header=true widths=1.3,2.4,3.5 -->
| Stage | Tool responsibility | Reader decision |
|---|---|---|
| Inspect | Preview inputs and likely package structure | Confirm the intended strain and source files |
| Extract | Parse regions, scans, scores, and provenance deterministically | Check source and gate states |
| Interpret | Present evidence for governed post-extraction judgment | Decide what is supported, held, or experimentally testable |

## Mamey versus Sapote

Mamey is the deterministic extraction layer. Sapote-slim and Sapote full are judgment protocols operating on the sealed evidence handoff. Mode B authoring therefore belongs after extraction; it is not another deterministic fact generator.

## Installation choices

- **Core:** extraction, packaging, and validation.
- **Figures:** scientific plots and figure-rich reports.
- **Documents:** governed DOCX/PDF export using `python-docx`, `lxml`, and ReportLab.
- **All:** a convenience profile when the complete offline wheelhouse is available.

> [CLAIM CEILING] What the output can establish
> A clean software gate demonstrates mechanical integrity of the package. It does not prove product identity, production, activity, ecological function, or publication readiness.

## Where to go next

- Read the package manifest and gate validation report.
- Open the analysis report for figures, captions, and methods.
- Open a Mode B card only when the complete exact-locus identity and evidence bindings are available.

