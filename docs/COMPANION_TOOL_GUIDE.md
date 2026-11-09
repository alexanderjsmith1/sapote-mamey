# Choose a companion tool

A companion tool is a separate program that adds evidence to a Mamey run: protein
searches, cluster families, trees, genome similarity and figures. Mamey is the
extraction engine in this bundle; see the [glossary](GLOSSARY.md) for other terms.
A first extraction needs only the core install. Follow
[the first-run recipe](reader/01_FIRST_RUN.md), and add a companion only when you need its result.

## Check what you have

```bash
python mamey_run.py doctor --companions
```

You should see one row per optional tool with its probe state. A `detected <version>` row means
a local version probe succeeded; it still says `workflow NOT_ASSESSED`. `WEB_OR_MANUAL_NOT_PROBED`
and `MANUAL_NOT_PROBED` rows were not checked, which is not the same as missing. Other states, such
as `MISSING_EXECUTABLE` or `PROBE_NONZERO_EXIT`, say local detection was not established, and those
rows print an install hint. A tool that is not detected does not fail the check. Install only the
tools your question needs.

Project sites, licenses, Python extras, reference datasets and online services are in
the [README table](../README.md#tool-downloads-and-licenses).

## Run these outside Mamey

- **SPAdes** assembles reads into contigs. Mamey never runs it. Run antiSMASH on the assembly.
- **Galaxy** can host upstream workflows. Download the finished files and their settings before you start Mamey.
- **antiSMASH** produces the annotated archive Mamey reads. Mamey does not run it. Download the full result ZIP; see [input contents](ANTISMASH_INPUTS_CONSUMED.md).

## Pick a tool by question

| You want to | Tool | Where to go |
|---|---|---|
| Compare a protein against NCBI databases | NCBI web BLASTp or local BLAST+ | [BLASTp protocol](ONLINE_BLASTP_PROTOCOL.md) |
| Search UniProt when NCBI is unreachable | EMBL-EBI Job Dispatcher (`blastp-ebi`) | [BLASTp protocol](ONLINE_BLASTP_PROTOCOL.md) |
| Group regions into gene-cluster families | BiG-SCAPE | [cohort walkthrough](BIGSCAPE_COHORT_WALKTHROUGH.md) |
| Draw gene-cluster comparisons | clinker | [clinker pages](BIGSCAPE_COHORT_WALKTHROUGH.md#optional-clinker-pages) |
| Build a genome-marker tree | GToTree, with MAFFT or MUSCLE, trimAl and IQ-TREE | [GToTree workflow](GTOTREE_WORKFLOW.md) |
| Place queries on a fixed reference tree | MAFFT, RAxML-NG, EPA-ng, gappa | [phylogeny workflow](PHYLO_AUTOPILOT_WORKFLOW.md) |
| Compare two genomes' proteins, with optional ANI | `python mamey_run.py compare` | [compare settings](COMPARE_RESOURCE_CONTROL.md) |
| Compare many genomes by ANI inside a tree run | FastANI, through `phylo-run --ani-refs` | [run contracts](COMPANION_RUN_CONTRACTS.md#checking-outputs) |
| Cross-check regions with GECCO, export metabolomics tables, or rescue split regions | `gecco-crosscheck`, `export-metabolomics`, `two-proof-rescue` | [class evidence](COMPANION_CLASS_EVIDENCE.md) |
| Compare one locus against public genomes (advanced) | CORASON | [CORASON workflow](CORASON_WORKFLOW.md) |
| Draw figures | R with ggplot2, ggtree, patchwork, svglite | [R figure workflows](R_FIGURE_WORKFLOWS.md) |

Other tools in the README table (HMMER, pyhmmer, Prodigal, FastTree, DIAMOND) are called by
the workflows above. Follow the workflow rather than running them by hand.

## Notes that change the result

- NCBI web BLASTp and EBI send your selected sequences to a public server. Review the query list first.
- EBI searches UniProt databases, not nr, and needs a real contact email. Do not compare EBI hits with nr hits as if they were the same search.
- DIAMOND is used by pairwise comparison when `diamond4py` or a `diamond` executable is present. `diamond4py` is not in any extra. Check the row backend and log for the aligner that ran. See [offline analysis](../sapote_addons/README_OFFLINE_ANALYSIS.md).
- IQ-TREE trees: record the model, support method, seed and thread count with the tree.
- `Rscript bundle_support/install_r_figure_packages.R` installs the R packages the figure scripts use.

## Before you run a companion

State the question, the input files, the database, the output folder and the expected result.
Check whether the command analyzes or only prepares or imports files. Save the command,
tool versions, input hashes and log with the result. The [run contracts](COMPANION_RUN_CONTRACTS.md)
give the detailed input and write rules.

For a region, name it **strain / full node-or-contig / region / BGC alias**
(BGC means biosynthetic gene cluster). For a gene, also keep its locus tag. Keep
coverage and search status beside scores. For clusters, keep each label mapped to its
full locus identity. For trees and ANI, keep the genome panel, references, alignment and
settings with the output. For figures, keep the plotted table and inspect the finished image.

Keep database versions and hashes with the analysis.
