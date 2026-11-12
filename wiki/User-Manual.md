<!-- Mirror of docs/GUIDE/01_User_Manual.md, made by tools/sync_wiki_mirrors.py. Edit the source, then run: python3 tools/sync_wiki_mirrors.py --apply -->
# The Sapote-Mamey User Manual

This manual is a table of contents. Each section says what the step is for and links
the page that explains it. The facts live on those pages, so they are written once.

*Current to bundle v9.7.465 / engine Mamey 1.9.181*

## 1 · What Sapote-Mamey is

Mamey reads antiSMASH results and writes a package of tables, a workbook and an issue
log; Sapote is the interpretation and writing workflow that uses them.
[What Sapote-Mamey offers](../docs/PRODUCT_MAP.md) maps the parts.

## 2 · Setup and installation

Install Python 3.12 or newer and the core package with the
[installation guide](../docs/INSTALL.md); the [prerequisites guide](Prerequisites.md)
separates Python extras from external programs and databases.

## 3 · Running a strain

[Your first run](../docs/reader/01_FIRST_RUN.md) gives the `doctor`, `inspect`, `run` and
`validate` steps, what the capped command turns off and what each exit code means.
For a folder of ZIPs, use the [batch guide](../docs/INTAKE_BATCH_AND_SMALL_N_DIRECTIVES.md).

## 4 · Reading the output

[Read one saved package](../docs/reader/03_READ_RESULTS.md) is the short tour of a package,
and [Reading your results](../docs/READING_YOUR_RESULTS.md) explains selected result files, identity fields and evidence states. Use the
relevant data dictionary and source tables for other columns.
The [glossary](Glossary.md) defines the fields.

### Read a Mode B card

The [profile guide](../docs/MODEB_PROFILE_MATRIX.md) tells short candidates from finished
cards, and the [authoring walkthrough](../docs/MODE_B_USER_WALKTHROUGH.md) covers writing,
verifying and saving one.

## 5 · Deepen the evidence

Pick the question first, then the guide:
[BLASTp evidence](../docs/ONLINE_BLASTP_PROTOCOL.md) for what a protein resembles,
[companion class evidence](../docs/COMPANION_CLASS_EVIDENCE.md) and
[expanded-locus evidence](../docs/MODEB_EXPANDED_LOCUS.md) for a possibly fragmented region,
the [BiG-SCAPE walkthrough](../docs/BIGSCAPE_COHORT_WALKTHROUGH.md) for families, and the
[phylogeny guide](../docs/PHYLO_AUTOPILOT_WORKFLOW.md) for trees.

## 6 · Make figures

[Make and review Mamey figures](../docs/FIGURES_START_HERE.md) maps common figure tasks to their routes
and checks, and links specialist catalogs and workflows.

## 7 · Keep and share results

[Files and storage](../docs/FILES_STORAGE_AND_HANDOFF.md) explains how to keep and move a
result. For reporting, use [Evidence to report](../docs/EVIDENCE_TO_REPORT.md);
[citation status](../docs/CITATION_COMPACT_MODE.md) explains the labels in compact reports.

## 8 · Recover a failed step

[Recovery and limits](../docs/reader/04_RECOVERY_AND_LIMITS.md) covers failed runs,
status values, JSON evidence modes and a retry that keeps the first attempt.

## Reference

The [command catalog](../docs/COMMAND_CATALOG.generated.md) lists the full interface.
The [current documentation index](../CURRENT_DOCS_INDEX.md) lists the specialized
guides. [Engine lineage](../docs/ENGINE_LINEAGE.md) says what changed in each engine version
and whether results from different versions can be compared.
