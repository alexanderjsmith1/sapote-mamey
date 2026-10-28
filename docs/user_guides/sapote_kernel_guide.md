# Sapote–Mamey: The Kernel and Evidence Gates
**Sapote–Mamey v9.7.460 · Engine 1.9.177 · build 20261027v97460a**

## Extraction and interpretation

Mamey reads antiSMASH results and produces structured evidence, routing scores, tables and a package manifest. Sapote is the interpretation workflow that uses those outputs to author cards and reports. An extracted field, routing score or template is not a finished biological interpretation.

Start with [the Master Walkthrough](../MASTER_WALKTHROUGH.md). The [current documentation index](../../CURRENT_DOCS_INDEX.md) selects the operational guides; the [engine lineage](../ENGINE_LINEAGE.md) records historical changes that may affect comparisons between runs.

## Gates apply to different objects

- Environment diagnostics report selected dependency discovery and tool checks. Read [doctor’s reserved write-probe scope](../INSTALL.md#doctor-scope-and-write-probe) before invoking it.
- Package validation checks the selected package's declared files, identity and evidence contract.
- Evidence admission binds external results to their source and exact locus.
- Card verification checks the selected authoring profile and its required content.
- Figure and document checks assess generated deliverables and their supporting data.

A pass at one level does not imply a pass at the next, and exit 0 does not mean an optional output was made. Validation rewrites a status file inside the package, so work on a copy when the original must not change. Read the reported findings; a file existing is not the same as its contents being right.

## Work from a complete identity

Cite each locus as **strain / full node-or-contig / region / BGC alias**, copied from the package. Do not transfer an alias between package versions or select evidence by a matching filename alone. Preserve the query sequence and source hashes for protein evidence; keep nr, ClusteredNR and Swiss-Prot results distinct.

## Authoring and unresolved evidence

Choose the [Mode B profile](../MODEB_PROFILE_MATRIX.md), then follow the [authoring walkthrough](../MODE_B_USER_WALKTHROUGH.md) with the active package/profile contract. The [gate-clean recipe](../MODEB_GATE_CLEAN_AUTHORING.md) is for full48; current50 v2 uses its own template and verifier path. Keep their section maps separate. Attach only evidence that applies to this locus, distinguish candidate citations from reviewed passages, and preserve missing or contradictory evidence.

## Diagnose failures at their source

If package validation fails, retain the package and inspect the named failure before proceeding. If result import binds no queries, check query identifiers and provenance instead of treating an empty overlay as a negative result. If an export fails, retain the authored source and inspect renderer diagnostics. Re-running a command or editing a receipt is not proof that its original failure is resolved.

For figures and exports, begin at [Figures Start Here](../FIGURES_START_HERE.md) and [the deliverable menu](../DELIVERABLE_MENU.md). [Figure Factory development records](../figure_factory/README.md) describe specialized proposals and implementations. For dated fixes and comparisons, use [the changelog](../../CHANGELOG.md); internal version-by-version narratives are not installation instructions.
