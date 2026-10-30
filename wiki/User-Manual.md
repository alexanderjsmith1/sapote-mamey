<!-- Mirror of docs/GUIDE/01_User_Manual.md, made by tools/sync_wiki_mirrors.py. Edit the source, then run: python3 tools/sync_wiki_mirrors.py --apply -->
# The Sapote-Mamey User Manual

Use this guide to run one strain, read its evidence and choose a next analysis.
You need an antiSMASH result ZIP for extraction, or a saved Mamey package for
review. For installation and the shortest command sequence, follow
[Your first run](../docs/reader/01_FIRST_RUN.md).

*Current to bundle v9.7.461 / engine Mamey 1.9.177*

## 1 · What Sapote-Mamey is

Mamey reads antiSMASH results and writes tables, workbooks, figures and a portable
package. Sapote is the interpretation and writing workflow that uses those results.

The region inventory answers what antiSMASH found. The triage board helps choose
what to inspect next. A Mode B card combines the evidence for one region into a
written interpretation. [Choose a task](../docs/USER_TASK_ROUTER.md) lists other outputs.

## 2 · Setup and installation

Use Python 3.12 or newer and the [installation guide](../docs/INSTALL.md).
Install the core package first; add optional features when you need them.
The [prerequisites guide](Prerequisites.md) separates Python extras from
external programs and databases.

Open a terminal in the folder containing `mamey_run.py`. Activate the environment
you installed there. For results you already have, open `OPEN_ME_FIRST.html`
without running Python.

## 3 · Running a strain

Follow the [first-run commands](../docs/reader/01_FIRST_RUN.md), replacing `EXAMPLE`
with your strain name and the input path with your antiSMASH ZIP.
Use the whole genome's antiSMASH result from one job.

The default run uses gold mode and bounded JSON evidence. It writes to
`runs/EXAMPLE/`; `--outdir` selects another parent folder. Add taxonomy and isolation
source only when you have records for them. The [Quick Guide](Quick-Guide.md#2-choose-the-evidence-and-runtime-budget)
explains the capped-session output tradeoff.

When extraction finishes, the terminal prints the package path and workbook
status. `MAMEY_COMPLETE_WITH_ISSUES` means the run completed with warnings.
Read them in `issue_log.md`; validation can pass while those warnings remain.

For a folder of input ZIPs, follow the [batch guide](../docs/INTAKE_BATCH_AND_SMALL_N_DIRECTIVES.md).
Its resume option skips matching completed inputs. It does not restart every
partly finished step.

## 4 · Reading the output

Open `runs/EXAMPLE/package/OPEN_ME_FIRST.html`. The
[saved-result guide](../docs/reader/03_READ_RESULTS.md) walks through the workbook
and gives an optional strict validation check.

### Read the region inventory and triage board

The inventory contains the region coordinates and annotations. The triage board
adds ranking fields. Match their rows by the same complete identity:
**strain / full node-or-contig / region / BGC alias**.

- **Rank:** the order for closer inspection.
- **AB / AF:** antibacterial and antifungal priority scores, rather than measured activity.
- **Boundary:** Interior, Edge, Full-contig or Unknown describes the region's
  position on its contig; a truncated assembly can split a pathway across contigs.
- **KCB:** KnownClusterBlast reference matches. Compare the shared genes and
  coverage before using the reference's product name in an interpretation.
- **Exclusion:** why a region was left out of a ranked list. Read the excluded
  rows as well as the lead rows.

Use [the glossary](Glossary.md) for field definitions and
[the detailed result guide](../docs/READING_YOUR_RESULTS.md) for evidence files.
A missing input, failed analysis and completed search with no hits are different
states; use their recorded statuses rather than a blank cell alone.

### Ask the package what it contains

From the program folder, with your own strain name:

```bash
python mamey_run.py explain runs/EXAMPLE/package
python mamey_run.py list-bgcs runs/EXAMPLE/package --include-dropped
```

`explain` describes the saved package. `--include-dropped` makes the list include
excluded rows, which it normally hides.

### Read a Mode B card

A card should identify its region, describe the available evidence and explain
its interpretation. The [profile guide](../docs/MODEB_PROFILE_MATRIX.md) distinguishes
short candidates from finished cards. The [authoring walkthrough](../docs/MODE_B_USER_WALKTHROUGH.md)
uses the same selected contract for template creation and verification:
`full48` by default, or `current50_v2` when you choose that profile.

Save the written card as a file. To put it into the package, follow the
[receipt workflow](../docs/DELIVERABLE_CONTRACT.md), which also explains master-workbook updates.
Keep the original package ZIP when updating a working copy.

## 5 · Deepen the evidence

Choose the question before adding a tool:

- **What does a protein resemble?** Read existing [BLASTp evidence](../docs/ONLINE_BLASTP_PROTOCOL.md)
  before starting a search. A live search uploads the selected sequences.
- **Could a region be fragmented?** Read its reference coverage and contig
  boundaries together. [Reference completion](../docs/COMPANION_CLASS_EVIDENCE.md)
  and [expanded-locus evidence](../docs/MODEB_EXPANDED_LOCUS.md) describe the available checks.
- **Which regions belong to a family?** Use the [BiG-SCAPE walkthrough](../docs/BIGSCAPE_COHORT_WALKTHROUGH.md)
  with the chosen regions and comparison set.
- **Where does the strain fit in a tree?** Use the [phylogeny guide](../docs/PHYLO_AUTOPILOT_WORKFLOW.md)
  with the sequence and reference inputs it requests.

A reference match supports a similarity statement; identifying a compound or
assigning activity to a particular region needs evidence for that link.

## 6 · Make figures

First look at the images already in the package. The brief's plots, gold figures
and locus maps have separate file lists. Check those lists before regenerating them.

[Make and review Mamey figures](../docs/FIGURES_START_HERE.md) maps each figure to its
renderer, source tables and checks. Keep a figure with its plotted data and methods.
For post-run rendering, use a working package copy because some commands update
its integrity records even when images go to another folder.

Before comparing counts across strains, check that their antiSMASH detection
settings match. Loose runs can call more regions than default runs.

## 7 · Keep and share results

Keep the original antiSMASH ZIP, the Complete_Package ZIP and any written cards
or reports. The package manifest records the input and producing versions.
[Files and storage](../docs/FILES_STORAGE_AND_HANDOFF.md) explains how to transfer a
result while keeping its links and evidence together.

For reporting, use [Evidence to report](../docs/EVIDENCE_TO_REPORT.md).
[Citation status](../docs/CITATION_COMPACT_MODE.md) explains labels used in compact reports.

## 8 · Recover a failed step

Keep the output folder, command and last error. Follow
[Recovery](../docs/reader/04_RECOVERY_AND_LIMITS.md) and use a fresh output folder for a retry.
If an outer tool times out, check whether the process is still running before
starting another writer.

## Reference

The [command catalog](../docs/COMMAND_CATALOG.generated.md) lists the full interface.
Use the [current documentation index](../CURRENT_DOCS_INDEX.md) for specialized
guides and the [changelog](../CHANGELOG.md) for older behavior.
