# Sapote Mamey Quick Guide

**Version:** v9.7.461 / engine Mamey 1.9.177

Use this page to find the next step for an antiSMASH ZIP or a saved Mamey package.
For a first extraction, use [Your first run](../reader/01_FIRST_RUN.md).
[Your first analysis](../MASTER_WALKTHROUGH.md) adds an assistant request and a results walkthrough.

## 0. Install

You need Python 3.12 or newer to run Mamey. Follow [Install](../INSTALL.md) once,
then activate the same environment when you return. A browser and spreadsheet
reader are enough to open saved results.

## 1. Inspect and run one strain

The [first-run page](../reader/01_FIRST_RUN.md) gives the commands.
Use one antiSMASH result ZIP for the genome and one strain name throughout.
The example uses `EXAMPLE` and writes to `runs/EXAMPLE/`.

Ordinary runs use gold mode, bounded JSON evidence, a standard brief and automatic
locus maps. You do not need flags to request those defaults.

## 2. Review the package

Open `runs/EXAMPLE/package/OPEN_ME_FIRST.html`. Read the issue log, inventory and
triage board, then the workbook. [Read one saved package](../reader/03_READ_RESULTS.md)
explains the values and gives a fresh validation command.

## 3. Process a cohort

The [batch guide](../INTAKE_BATCH_AND_SMALL_N_DIRECTIVES.md) covers a folder of
input ZIPs and resuming a batch. Choose the included strains before comparing them.

## 4. Select a deliverable

Use [Choose a task](../USER_TASK_ROUTER.md) for figures, cards, slides and comparisons.
For figures and writing from existing evidence, see [Evidence to report](../EVIDENCE_TO_REPORT.md).

## 5. Keep the region identifiable

When discussing an individual region, copy **strain / full node-or-contig / region / BGC alias**
from its record. Keep missing inputs, failed checks and completed searches with
no hits separate in your notes.

<a id="2-choose-the-evidence-and-runtime-budget"></a>

## Optional evidence settings

`--capped-session` changes the outputs: it switches the main JSON walker off,
suppresses the brief and automatic locus maps, and requires a workbook.
It does not set a wall-clock timeout. Use it only when those omissions fit your task.

`--json-evidence full` selects the full walker instead of bounded streaming.
It refuses an individual uncompressed JSON file larger than 80 MB; the ZIP's
compressed size is not that limit. See [input evidence](../ANTISMASH_INPUTS_CONSUMED.md)
if a channel is held or truncated.

## Protein search and result import

Use [BLASTp evidence](../ONLINE_BLASTP_PROTOCOL.md) to read saved results or plan a search.

## Fragmented pathway review

Use [expanded-locus evidence](../MODEB_EXPANDED_LOCUS.md) to inspect sequence context around a selected region.

## Trees and heatmap overlays

Use [phylogeny](../PHYLO_AUTOPILOT_WORKFLOW.md) for sequence inputs and [tree figures](../FIGURES_START_HERE.md) for a completed tree.

## Help and reference

- [Recovery](../reader/04_RECOVERY_AND_LIMITS.md) for a failed or incomplete run.
- [User Manual](01_User_Manual.md) for a broader reading guide.
- [Glossary](../GLOSSARY.md) for terms and [citation status](../CITATION_COMPACT_MODE.md)
  for the labels used in compact reports.
