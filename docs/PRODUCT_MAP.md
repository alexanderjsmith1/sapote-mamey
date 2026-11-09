# What Sapote-Mamey offers

Start with an antiSMASH result ZIP to make a region inventory, workbook and
figures, or open a saved package to continue an analysis. Mamey is the program that extracts the
evidence. Sapote is the workflow that turns that evidence into an interpretation and written report;
it is not a second program. Terms such as BGC (biosynthetic gene cluster) and package are in the
[glossary](GLOSSARY.md).

## Start or read a run

[Your first run](reader/01_FIRST_RUN.md) shows the extraction commands.
[Read one saved package](reader/03_READ_RESULTS.md) explains the workbook,
rankings and warnings. Set up Python first with [Install](INSTALL.md).

## Explore the evidence

- [Protein searches](ONLINE_BLASTP_PROTOCOL.md) compare translated genes with
  reference proteins and reuse saved BLASTp results. A new search sends sequences to a public server: NCBI for `blastp-online`, or EMBL-EBI for `blastp-ebi`. `blastp-round` without `--run` only plans a round and sends nothing (`mamey/cli.py:8601-8602`). Read the protocol first.
- [Fragmented pathway review](MODEB_EXPANDED_LOCUS.md) brings nearby or separate
  sequence context into a region review.
- [BiG-SCAPE](BIGSCAPE_COHORT_WALKTHROUGH.md) groups selected regions into families.
- [Phylogeny](PHYLO_AUTOPILOT_WORKFLOW.md) places sequences or builds a tree from
  the inputs listed in that guide.

Each optional analysis needs its own inputs and tools. Choose the question you
want to answer before installing them.

## Make something to read or share

[Figures](FIGURES_START_HERE.md), [Mode B cards](MODE_B_USER_WALKTHROUGH.md),
[strain slides](STRAIN_SLIDES.md) and [interactive readers](WIDGET_DELIVERABLES.md)
use the evidence already available. [Evidence to report](EVIDENCE_TO_REPORT.md)
connects figures and source tables to short findings and Methods text.

Use [Choose a task](USER_TASK_ROUTER.md) for a complete list of outputs and required inputs.
