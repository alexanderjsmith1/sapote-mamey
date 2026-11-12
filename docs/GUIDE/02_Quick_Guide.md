# Sapote Mamey Quick Guide

**Version:** v9.7.465 / engine Mamey 1.9.181

This page is a command map. Each row names the command for a task and the page that
explains it. Flags and behavior live on those pages, not here.
For the complete sequence, start with [Your first run](../reader/01_FIRST_RUN.md).
[Your first analysis](../MASTER_WALKTHROUGH.md) has the request to give an assistant.


## Commands by task

| Task | Command | Page |
|---|---|---|
| Install and check the setup <a id="0-install"></a> | `doctor` | [Install](../INSTALL.md), then [Your first run](../reader/01_FIRST_RUN.md#1-check-the-install) |
| Look inside an antiSMASH ZIP | `inspect` | [Your first run](../reader/01_FIRST_RUN.md#2-look-inside-the-zip) |
| Run one strain, capped or full <a id="1-inspect-and-run-one-strain"></a> | `run` | [Your first run](../reader/01_FIRST_RUN.md#3-run-the-command-that-inspect-printed) |
| Check a package | `validate` | [Your first run](../reader/01_FIRST_RUN.md#4-check-that-the-run-worked) |
| Read a package <a id="2-review-the-package"></a> | `explain`, `list-bgcs` | [Read one saved package](../reader/03_READ_RESULTS.md) |
| Fix a failed or incomplete run | `run --outdir` | [Recovery](../reader/04_RECOVERY_AND_LIMITS.md) |
| Choose JSON evidence settings <a id="2-choose-the-evidence-and-runtime-budget"></a> <a id="optional-evidence-settings"></a> | `run --json-evidence` | [JSON evidence modes](../reader/04_RECOVERY_AND_LIMITS.md#json-evidence-modes) |
| Run a folder of ZIPs <a id="3-process-a-cohort"></a> | `tools/intake_harness.py` | [Batch guide](../INTAKE_BATCH_AND_SMALL_N_DIRECTIVES.md) |
| Read or run protein searches <a id="protein-search-and-result-import"></a> | `ingest-blastp`, `blastp-online`, `auto-blastp` | [BLASTp evidence](../ONLINE_BLASTP_PROTOCOL.md) |
| Write a Mode B card | `emit-modeb-template`, `verify-modeb` | [Mode B walkthrough](../MODE_B_USER_WALKTHROUGH.md) |
| Make figures and short findings <a id="4-select-a-deliverable"></a> | `render-figures` and others | [Figures](../FIGURES_START_HERE.md), [Evidence to report](../EVIDENCE_TO_REPORT.md) |
| Any other task | | [Choose a task](../USER_TASK_ROUTER.md) |

The single-strain first-run example writes to `runs/EXAMPLE/`. Other guides use
illustrative names and paths. Follow each guide's declared inputs
and output location, and choose a fresh authorized destination.
<a id="5-keep-the-region-identifiable"></a>

When you discuss one region, copy **strain / full node-or-contig / region / BGC alias**
from its record.

## Fragmented pathway review

A poor assembly can split one pathway across several contigs. `run` includes an RG-GMCI
pass for this. Its candidate links between fragments are homology-guided, not joined
sequence. Read the ranked pairs in the package's `_4A_RGGMCI_ranked_pairs.csv`; the
[glossary](../GLOSSARY.md#7-rg-gmci-and-the-rescue-layer) explains the confidence labels.
Inspect pass and source-evidence states: missing, failed or empty input is not a
validated negative. Keep both endpoints' full strain / contig / region / BGC identities.
To look at the sequence around one region, use
[expanded-locus evidence](../MODEB_EXPANDED_LOCUS.md).

## Trees and heatmap overlays

Use [phylogeny](../PHYLO_AUTOPILOT_WORKFLOW.md) for sequence inputs and [tree figures](../FIGURES_START_HERE.md) for a completed tree.

## Help and reference

- [User Manual](01_User_Manual.md) for the manual's table of contents.
- [Glossary](../GLOSSARY.md) for terms and [citation status](../CITATION_COMPACT_MODE.md)
  for the labels used in compact reports.
