<!-- Mirror of docs/GUIDE/02_Quick_Guide.md, made by tools/sync_wiki_mirrors.py. Edit the source, then run: python3 tools/sync_wiki_mirrors.py --apply -->
# Sapote Mamey Quick Guide

**Version:** v9.7.464 / engine Mamey 1.9.180

Use this page to find the next step for an antiSMASH ZIP or a saved Mamey package.
For a first extraction, use [Your first run](../docs/reader/01_FIRST_RUN.md).
[Your first analysis](../docs/MASTER_WALKTHROUGH.md) adds an assistant request and a results walkthrough.

## 0. Install

You need Python 3.12 or newer to run Mamey. Follow [Install](../docs/INSTALL.md) once,
then activate the same environment when you return. A browser and spreadsheet
reader are enough to open saved results.

## 1. Inspect and run one strain

[Your first run](../docs/reader/01_FIRST_RUN.md) gives the commands and how to tell
success from failure. Use one antiSMASH result ZIP for the genome and one strain name
throughout. The example uses `EXAMPLE` and writes to `runs/EXAMPLE/`.

The command that `inspect` prints is a capped run. It finishes faster, and it skips
the written brief, the JSON evidence and the automatic gene maps. For a full run,
delete `--capped-session`, `--json-evidence off` and `--brief none` from that command.
A full run then uses bounded JSON evidence, a standard brief and automatic gene maps.

## 2. Review the package

Open `runs/EXAMPLE/package/OPEN_ME_FIRST.html`. Read the issue log, inventory and
triage board, then the workbook. [Read one saved package](../docs/reader/03_READ_RESULTS.md)
explains the values and gives a fresh validation command.

## 3. Process a cohort

The [batch guide](../docs/INTAKE_BATCH_AND_SMALL_N_DIRECTIVES.md) covers a folder of
input ZIPs and resuming a batch. Choose the included strains before comparing them.

## 4. Select a deliverable

Use [Choose a task](../docs/USER_TASK_ROUTER.md) for figures, cards, slides and comparisons.
For figures and writing from existing evidence, see [Evidence to report](../docs/EVIDENCE_TO_REPORT.md).

## 5. Keep the region identifiable

When discussing an individual region, copy **strain / full node-or-contig / region / BGC alias**
from its record. Keep missing inputs, failed checks and completed searches with
no hits separate in your notes.

<a id="2-choose-the-evidence-and-runtime-budget"></a>

## Optional evidence settings

`--capped-session` turns off the JSON evidence, the brief and the automatic gene maps,
and it requires the workbook. It does not set a time limit.

`--json-evidence full` reads the whole antiSMASH JSON instead of a bounded stream.
It refuses any single JSON file larger than 80 MB uncompressed. The ZIP's compressed
size is not that limit. See [input evidence](../docs/ANTISMASH_INPUTS_CONSUMED.md)
if a channel is held or truncated.

## Protein search and result import

Use [BLASTp evidence](../docs/ONLINE_BLASTP_PROTOCOL.md) to read saved results or plan a search.

## Fragmented pathway review

A poor assembly can split one pathway across several contigs. `run` includes an RG-GMCI pass
for this. It compares fragments against the ClusterBlast and KnownClusterBlast references they
share, checks where their hits fall, and tests whether they cover complementary parts of the
reference pathway. A supported link is a candidate relationship between fragments. It is
homology-guided linkage, not a joined sequence. Read the ranked pairs in the package's
`_4A_RGGMCI_ranked_pairs.csv`; the [glossary](Glossary.md#7-rg-gmci-and-the-rescue-layer)
explains the confidence labels. To look at the sequence around one region, use
[expanded-locus evidence](../docs/MODEB_EXPANDED_LOCUS.md).

## Trees and heatmap overlays

Use [phylogeny](../docs/PHYLO_AUTOPILOT_WORKFLOW.md) for sequence inputs and [tree figures](../docs/FIGURES_START_HERE.md) for a completed tree.

## Help and reference

- [Recovery](../docs/reader/04_RECOVERY_AND_LIMITS.md) for a failed or incomplete run.
- [User Manual](User-Manual.md) for a broader reading guide.
- [Glossary](Glossary.md) for terms and [citation status](../docs/CITATION_COMPACT_MODE.md)
  for the labels used in compact reports.
