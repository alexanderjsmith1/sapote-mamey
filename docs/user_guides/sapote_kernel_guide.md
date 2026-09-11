# Sapote–Mamey: The Kernel and Evidence Gates
**Sapote–Mamey v9.7.428 · Engine 1.9.163 · build 20260911v97428a**

## Extraction and interpretation

Mamey reads antiSMASH results and produces structured evidence, routing scores, tables and a package manifest. Sapote is the interpretation workflow that uses those outputs to author cards and reports. An extracted field, routing score or template is not a finished biological interpretation.

Start with [the Master Walkthrough](../MASTER_WALKTHROUGH.md). The [current documentation index](../../CURRENT_DOCS_INDEX.md) selects the operational guides; the [engine lineage](../ENGINE_LINEAGE.md) records historical changes that may affect comparisons between runs.

## Gates apply to different objects

- Environment diagnostics report available dependencies and tools.
- Package validation checks the selected package's declared files, identity and evidence contract.
- Evidence admission binds external results to their source and exact locus.
- Card verification checks the selected authoring profile and its required content.
- Figure and document checks assess generated deliverables and their supporting data.

A pass at one level does not imply a pass at the next. Read the reported scope and unresolved findings. Do not substitute the existence of an output file for validation of its contents.

## Work from a complete identity

Use **strain / full node-or-contig / region / BGC alias** from the bound package. Do not transfer an alias between package versions or select evidence by a matching filename alone. Preserve the query sequence and source hashes for protein evidence; keep nr, ClusteredNR and Swiss-Prot results distinct.

## Authoring and unresolved evidence

Follow [Mode B authoring](../MODEB_GATE_CLEAN_AUTHORING.md) and the active package/profile contract. Do not combine section numbering from historical profiles. Attach only evidence admitted for the intended scope, distinguish candidate citations from reviewed passages, and preserve missing or contradictory evidence.

## Diagnose failures at their source

If package validation fails, retain the package and inspect the named failure before proceeding. If result import binds no queries, check query identifiers and provenance instead of treating an empty overlay as a negative result. If an export fails, retain the authored source and inspect renderer diagnostics. Re-running a command or editing a receipt is not proof that its original failure is resolved.

For figures and exports, use [Figure Factory](../figure_factory/README.md) and [the deliverable menu](../DELIVERABLE_MENU.md). For dated fixes and comparisons, use [the changelog](../../CHANGELOG.md); internal version-by-version narratives are not installation instructions.
