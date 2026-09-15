# Companion tools: what they do and where Sapote–Mamey uses them

This guide explains the tools in the README's workflow table, plus the web-search and upstream
services they connect to. Some are websites, some are local programs, and some are libraries
used by programs. Downloading a tool from a website does not make its analysis an online
service. You do not need all of them for a first antiSMASH extraction.

The integration descriptions are grounded in this bundle's code and its referenced protocols.

Use the [README download table](../README.md#tool-downloads-and-licenses) for upstream project
links. External sites, versions, service limits and licenses change without notice. Record the
actual installed version and database release when you use a tool.

## Choose a stage

| Stage | Tools | Relationship to Sapote–Mamey |
|---|---|---|
| Assemble or annotate a genome | Galaxy, SPAdes, antiSMASH | Upstream; supply their appropriate results |
| Read antiSMASH results | Python and declared core libraries | Mamey's local extraction runtime |
| Investigate protein evidence | NCBI web BLASTp, BLAST+, EBI, DIAMOND, HMMER, pyhmmer | Separate evidence channels; some have runners/importers |
| Compare cluster families | BiG-SCAPE, clinker | Optional cohort computation and visualization |
| Build or place sequences on trees | GToTree, Prodigal, MAFFT, MUSCLE, trimAl, IQ-TREE, FastTree, RAxML-NG, EPA-ng, gappa | Companion workflows with explicit inputs and configuration |
| Compare genomes | FastANI, skani/pyskani | Genome similarity evidence, separate from a cluster score |
| Draw selected results | R, ggplot2, ggtree, patchwork, svglite | Optional rendering stack; most core figures use Python instead |

### Python — the runtime for Mamey

**Standalone.** Python runs programs and libraries; it is not itself a BGC detector. A project
environment holds the libraries that a particular program needs. Selecting that environment
matters because two Terminal windows can use different Python installations. An environment
copied from another laptop may contain incompatible paths or compiled packages.

**In Sapote–Mamey.** Python 3.12 or newer runs `mamey_run.py`. The core dependency list is in
`pyproject.toml`; figure, document and biological parsing extras add capabilities. Use the local
launcher from the chosen source folder so a previously installed `mamey` command does not select
another version. `start` reports the loaded program, while `doctor` checks capabilities.

**Keep/check.** Save the interpreter version, selected environment, installed dependency record
and source revision with a run. Core installation is different from installing an external
binary or database. A successful import does not demonstrate a complete analysis. Follow
[INSTALL](INSTALL.md), rather than treating a historical wheel list as a portable recipe.

### Galaxy — an upstream workflow service or local platform

**Standalone.** Galaxy provides a graphical interface for running bioinformatics tools through
histories and workflows. It is useful when the researcher prefers selecting inputs and options
in a browser to assembling command lines. Available tools, resource quotas and data retention
depend on the particular Galaxy installation; a tool shown in one instance is not guaranteed in
another. A local Galaxy installation is also possible.

**In Sapote–Mamey.** Galaxy is an upstream work environment, not a required Mamey component. If
an appropriate tool is available there, it may help produce assemblies or antiSMASH results.
Export the actual result files and the history or settings needed to explain their origin.
Mamey's input remains the antiSMASH result archive; it does not reconstruct a Galaxy history
from a filename or submit Galaxy jobs through the core extraction command.

**Keep/check.** Retain input identities, tool/version, chosen parameters and downloaded outputs.
Uploading sequences to a public instance is a separate sharing decision. The current local
walkthroughs begin with existing antiSMASH archives, so they do not require Galaxy access.

### SPAdes — genome assembly upstream of this program

**Standalone.** SPAdes builds candidate genome assemblies from sequencing reads using a selected
assembly workflow. The output is a set of sequence contigs and associated assembly records. It
works upstream of annotation: obtaining contigs does not establish that every chromosome or
plasmid is complete, correctly joined, or uncontaminated. Its suitable mode and resource needs
depend on the sequencing input and analysis question.

**In Sapote–Mamey.** SPAdes is not called by the ordinary Mamey run. A suitable assembly can be
an input to antiSMASH, whose result archive is then supplied to Mamey. Assemblies produced by
other appropriate methods can serve that role too; a SPAdes-specific origin is not required.
Fragmented assemblies later affect region boundaries and the interpretation of candidate links.
Mamey's fragment analysis does not repair the original assembly or create missing sequence.

**Keep/check.** Preserve read/assembly provenance and quality assessment separately from the
antiSMASH settings. Do not use a weighted BGC count as an assembly-quality measurement. This
upstream context is described in the recovered assembly/gene-calling explainer; no assembly was
performed in the Type Strain walkthroughs.

### antiSMASH — produces the annotated input archive

**Standalone.** antiSMASH examines an assembled genome for biosynthetic-region signatures and
writes region annotations, comparison results and visualizations. It can be run in an
appropriate local environment or through an available web service. Selected options determine
which comparisons and evidence channels are included. A detected region is an annotation unit;
it is not automatically one complete pathway or one identified molecule.

**In Sapote–Mamey.** This is the upstream tool whose results Mamey consumes. Supply the complete
result ZIP where possible, including region GenBank files and available JSON/TXT evidence.
Mamey extracts and organizes those records; it does not rerun antiSMASH detection. The inspector
reports the archive's contents, and the run records its antiSMASH profile when available.
Different profiles and upstream versions matter to comparisons across strains.

**Keep/check.** Retain the original ZIP, hash, assembly identity, antiSMASH version and profile.
Do not mistake the code ZIP for this biological input. Empty metadata fields require source
review: some supplied archives put `.` in ORGANISM while useful identity remains in DEFINITION.
See [the first-run walkthrough](MASTER_WALKTHROUGH.md).

### NCBI web BLASTp — remote protein similarity search

**Standalone.** Web BLASTp searches submitted amino-acid sequences against a selected NCBI
protein database and reports local sequence alignments. A useful result includes the query,
subject accession, aligned region, identity, coverage, score and database context. The best
listed hit may represent a conserved domain rather than the entire protein or its exact
biological function. Protein length and coverage therefore matter alongside percent identity.

**In Sapote–Mamey.** Mamey can export representative proteins, plan a search campaign, submit
selected supported searches, or import saved results. `bgc-blastp-panel` is an export step;
`blastp-round` is a plan until execution is selected. The online runner and saved-result
importer are different operations. A representative sample of proteins is not a complete
per-gene investigation. Keep nr and ClusteredNR as distinct recorded channels.

**Keep/check.** Preserve FASTA headers, query manifest, database/date/settings, hit tables and
alignment files. A failed submission is not a no-hit search. Submission leaves the local
workspace and must be part of the chosen task. See [ONLINE_BLASTP_PROTOCOL](ONLINE_BLASTP_PROTOCOL.md).

### NCBI BLAST+ — the local search programs

**Standalone.** BLAST+ supplies command-line search tools such as blastp and blastn, together
with database-building utilities. Local searches use a database prepared on the analysis
machine. Installing the executable does not install nr, Swiss-Prot or a 16S reference set.
The query alphabet and database must match the intended operation; nucleotide and protein
searches answer different questions.

**In Sapote–Mamey.** Local BLAST supports selected protein-evidence and sequence-routing
workflows. A local Swiss-Prot search is a curated-reference channel; it cannot be relabeled as
an nr search. The placement workflow can use a prepared 16S database for routing before more
detailed placement. Merely exporting proteins or reading an antiSMASH package does not require
a BLAST+ installation.

**Keep/check.** Record executable version, database construction/release, query identity,
parameters and raw results. Use the actual database prefix expected by the command, not an
arbitrary FASTA path. Review coverage and query mapping before importing results. See the
[protein protocol](ONLINE_BLASTP_PROTOCOL.md) and [placement workflow](PHYLO_AUTOPILOT_WORKFLOW.md).

### EMBL-EBI Job Dispatcher — a separate remote protein-search channel

**Standalone.** A Job Dispatcher service accepts a configured sequence-search job, returns a
job identifier, and makes results available when processing finishes. Database choice is part
of the experiment. A UniProt-based result from this service is not equivalent to an NCBI nr
result, even when both searches use BLASTp. Service limits and required contact information
must be checked for the actual submission.

**In Sapote–Mamey.** The program has a dedicated EBI transport in `mamey/blastp_ebi.py`. It
keeps job state so submitted queries can be tracked and requires valid contact information for
submission. Its batching and provenance are separate from the NCBI runner. Selecting this
channel should be explicit; the existence of an EBI option does not mean an unavailable NCBI
search has silently been completed elsewhere.

**Keep/check.** Retain query identifiers, job IDs, database, transport, settings and returned
files. Distinguish waiting, failed, completed-with-no-hits and imported results. This guide
explains the integration but does not execute or verify the live service. Consult the current
CLI help and the transport source before a planned submission.

### DIAMOND — accelerated protein comparisons

**Standalone.** DIAMOND is a local protein-search/alignment program suited to larger sequence
collections. It needs translated protein queries and an appropriate reference/database setup.
The executable and the Python binding named diamond4py are different installation routes;
installing an unrelated Python package with a similar name does not establish either route.
As with BLAST, alignment evidence must be interpreted with lengths and coverage.

**In Sapote–Mamey.** The current `compare` implementation can detect the DIAMOND executable or
a working compiled binding, then use fallback backends if needed. This corrects the recovered
historical guide, which said the executable could not help `compare`. Selection and per-row
backend receipts matter more than a remembered installation failure on one Mac. The comparison
is directional evidence, not an automatic statement that both proteomes are equivalent.

**Keep/check.** Inspect the summary backend and row-level backend, warnings and input
translations. The current integration has a documented zero-hit/failure-reporting limitation;
confirm execution before interpreting an empty result. See [DIAMOND status](../sapote_addons/DIAMOND_STATUS.md)
and [offline comparison](../sapote_addons/README_OFFLINE_ANALYSIS.md).

### HMMER — profile-based protein-domain search

**Standalone.** HMMER compares sequences with profile models built from related sequences.
A profile represents a family's characteristic pattern rather than one reference protein.
`hmmscan` and `hmmsearch` arrange sequences and model collections differently; `hmmpress`
prepares a model database for relevant search workflows. The model release, thresholds and
alignment coverage are essential parts of the evidence.

**In Sapote–Mamey.** HMM-related work can mean reading domains already reported by antiSMASH,
running an optional independent scan, or supplying Pfam to a companion such as BiG-SCAPE.
Those are separate operations. Reading antiSMASH domain annotations does not prove that a new
local HMMER scan ran. Some integration paths use the Python interface pyhmmer instead of the
standalone command-line binaries.

**Keep/check.** Preserve the profile set and hash, program/version, sequence identities and
raw domain tables. A domain hit supports a sequence/architecture hypothesis; it does not
confirm the product of an entire region. Missing profiles should be reported as missing
capability. See [PREREQUISITES](PREREQUISITES.md) and [external assets](EXTERNAL_ASSETS_GUIDE.md).

### pyhmmer — access to HMMER operations from Python

**Standalone.** pyhmmer exposes HMMER functionality through Python, allowing a script to manage
sequences, profiles and searches directly. It is a library rather than a web service. A working
import confirms that the library loads, but a real scan additionally needs compatible inputs,
models and settings. Do not confuse it with a Python rewrite that has automatically validated
all possible HMMER workflows.

**In Sapote–Mamey.** The optional registry-backed HMM pass can use pyhmmer; the result must be
identified as a performed scan or an explicit unavailable state. Relevant companions may have
their own pyhmmer requirements and database preparation. The ordinary core run can also consume
antiSMASH-reported domains without performing that independent scan. These sources should
remain distinguishable in the evidence record.

**Keep/check.** Record the model collection, query mapping, selected thresholds and scan receipt.
A missing database is not a no-hit result. Historic claims that one particular curated panel
was present do not establish today's installed assets. Use doctor and the selected scan's
actual output. See [PREREQUISITES](PREREQUISITES.md) for the supported local setup.

### BiG-SCAPE — gene-cluster family analysis

**Standalone.** BiG-SCAPE compares annotated biosynthetic regions and groups related regions
into gene-cluster families under a selected analysis configuration. It uses domain-level
information and produces machine-readable results plus views suitable for inspecting family
relationships. Changing the input cohort, reference panel or cutoff can change family
membership. A family is not a chemical identification, and a singleton is not proof of novelty.

**In Sapote–Mamey.** The `bigscape` command stages region GenBank inputs and invokes the
external tool through `deliverable_tools/bigscape_run.py`. Pfam and the external executable
must be supplied appropriately. A dry run helps inspect staging before computation. The
workflow can attempt matrix and clinker-related widgets after the family computation;
success at the compute stage does not prove those later views succeeded.

**Keep/check.** Retain exact region identities, cohort membership, tool/database versions,
cutoffs, reference provenance, logs and the resulting database. Family identifiers belong to
that run. For comparison, inspect edge fragments and reference composition alongside family
assignments. See [BIGSCAPE_GCF_WORKFLOW](BIGSCAPE_GCF_WORKFLOW.md).

### clinker — gene-cluster comparison pictures

**Standalone.** clinker draws gene-arrow comparisons from annotated cluster records, using
sequence relationships to connect genes across the displayed regions. The useful product is
an inspectable comparison of gene order, orientation and similarity. It is a visualization
and comparison aid, not a chemical structure predictor. Region selection and label clarity
strongly influence what the viewer can reasonably infer.

**In Sapote–Mamey.** The BiG-SCAPE-related workflow includes a clinker view through
`deliverable_tools/bigscape_clinker_widget.py`. A related family can provide a sensible subset
to compare, but the actual regions and reference records still need to be identified. Keep
the complete strain/contig/region/alias mapping rather than relying on shortened picture
labels. A widget stage may be unavailable even when the family database exists.

**Keep/check.** Preserve input GenBank files, region mapping, similarity settings and the HTML
or image output. Review gene arrows, clipping and what sequence segments were included.
Missing or truncated genes may reflect assembly boundaries. Consult the [GCF workflow](BIGSCAPE_GCF_WORKFLOW.md)
for staging and distinguish a rendered view from a fully interpreted pathway comparison.

### GToTree — coordinates a genome-marker phylogeny workflow

**Standalone.** GToTree organizes several operations needed to build a phylogenomic analysis,
such as obtaining gene information, finding a selected marker set, aligning retained markers
and preparing tree inference. It is a workflow orchestrator with dependencies, not a single
measurement that makes every upstream choice automatically correct. Marker choice, quality
filters, references and missing data determine what the resulting tree represents.

**In Sapote–Mamey.** The genome-phylogeny route can invoke a configured GToTree workflow and
retain its outputs for later tree/track figures. Whole-genome FASTAs and reference metadata
are separate inputs; an antiSMASH result ZIP is not a substitute for the required genome
input. Installation alone is not an executed tree, and a staged command is not a completed
phylogeny.

**Keep/check.** Save the marker panel, genomes, filtering decisions, alignment/partition files,
reference roster, tree command and logs. Inspect missing-marker and contamination concerns
before interpreting branches. Toolchain versions must match the invoked command syntax.
See [GTOTREE_WORKFLOW](GTOTREE_WORKFLOW.md) and the current phylogenetic command help.

### Prodigal — predicts protein-coding genes

**Standalone.** Prodigal predicts likely protein-coding regions in suitable prokaryotic genome
sequences and can emit gene coordinates and translations. These are computational gene
predictions. Sequence quality, chosen mode and biological context affect what is predicted;
gene calling is not experimental confirmation of expression or function. Translations then
become inputs to marker or protein-comparison workflows.

**In Sapote–Mamey.** Prodigal can be a dependency of a selected genome workflow, rather than a
mandatory component of core antiSMASH-result extraction. An antiSMASH archive already contains
annotated region records that Mamey reads. Python bindings such as pyrodigal are related
implementation choices, not interchangeable proof that a particular command-line stage ran.
Specialized viral models should not be treated as a generic bacterial annotation improvement.

**Keep/check.** Retain assembly identity, calling mode/version, coordinate files and protein
FASTA headers. Gene identifiers must remain bound to the genome and downstream region mappings.
If two annotation sets differ, resolve the crosswalk before combining their evidence. See
[PREREQUISITES](PREREQUISITES.md) and [GTOTREE_WORKFLOW](GTOTREE_WORKFLOW.md).

### MAFFT — aligns sequences or adds queries to an alignment

**Standalone.** MAFFT constructs multiple-sequence alignments so related sequence positions can
be compared. Different modes serve different input sizes and alignment problems. An alignment
is a hypothesis about positional correspondence; producing aligned letters does not prove
that every column is homologous or useful for inference. Inspect long gaps, unusual lengths
and divergent sequences before accepting the result.

**In Sapote–Mamey.** The placement workflow uses alignment operations to put query sequences
into the reference alignment's coordinate system. That coordinate relationship is crucial:
a placement engine expects a matching alignment, tree and model. Other configured phylogeny
routes may use MAFFT, but its presence does not mean every workflow selects it instead of
MUSCLE or another aligner.

**Keep/check.** Preserve input FASTA identifiers, algorithm/options, reference alignment and
resulting alignment. Adding a query should not silently replace the reference definition.
If trimming follows, keep both pre- and post-trimming alignments. See the
[placement workflow](PHYLO_AUTOPILOT_WORKFLOW.md) for the complete data relationship; no
alignment or placement was run as part of the offline extraction walkthroughs.

### MUSCLE — another multiple-sequence alignment tool

**Standalone.** MUSCLE aligns nucleotide or protein sequences for comparison and downstream
inference. It is an alternative aligner with its own versions and command syntax, not a
synonym for any multiple alignment. Choice of inputs, parameters and version can affect the
alignment, especially where sequences are divergent, incomplete or contain large insertions.
A successful process exit does not establish biological suitability of every column.

**In Sapote–Mamey.** Some configured genome-marker workflows use MUSCLE as part of the
alignment-to-tree chain. Confirm the external version expected by the actual runner. A
historical guide showing one version's options should not be pasted into another version
without checking its help. The ordinary Mamey antiSMASH extraction does not need MUSCLE to
build the inventory.

**Keep/check.** Save original sequences, IDs, software/version, command and alignment. Preserve
any subsequent trimming and partition information as separate artifacts. If another aligner
is substituted, record that change rather than silently treating the output as an exact
reproduction. Follow [GTOTREE_WORKFLOW](GTOTREE_WORKFLOW.md) for the selected companion chain.

### trimAl — selects alignment columns for downstream analysis

**Standalone.** trimAl removes or retains columns according to a selected alignment-filtering
method. The aim is to manage gappy or unreliable alignment regions, but trimming is a
methodological choice rather than an automatic guarantee of accuracy. Different settings can
retain different information, especially with fragmented genomes or unequal sequence lengths.
Keep enough evidence to see what was removed.

**In Sapote–Mamey.** A configured phylogenomic workflow may trim marker alignments before
concatenation or tree inference. The Python binding pytrimal is a separate interface to
related operations; it does not establish that a particular external trimAl command ran.
Trimming should remain traceable to the aligned markers and their eventual partitions.
Core antiSMASH extraction does not require this stage.

**Keep/check.** Retain the original alignment, trimmed alignment, settings, retained-site
information where available, and sequence roster. Check whether any sequence or marker has
become effectively uninformative. Do not compare trees while concealing changes in the sites
used to build them. See [GTOTREE_WORKFLOW](GTOTREE_WORKFLOW.md) and the selected runner's receipts.

### IQ-TREE — maximum-likelihood tree inference

**Standalone.** IQ-TREE infers trees from aligned sequence data under selected evolutionary
models and can calculate different forms of branch support. The model, partition scheme,
search settings and support method are part of the analysis. A support value does not turn
an incorrect alignment, poor reference selection or taxonomic mislabel into correct data.
Different support procedures should not be reported as interchangeable probabilities.

**In Sapote–Mamey.** The genome-tree route can use IQ-TREE after marker preparation and
alignment. The README names an expected tool generation, while historical machine notes
mention another installed version; use the binary and syntax supported by the selected
runner rather than assuming those are interchangeable. Later figure tools consume the tree
and explicit strain/annotation mappings.

**Keep/check.** Retain alignment, partitions, model selection, seed, command, support method,
logs and final tree. The tree shows relationships under that analysis, not an automatic
species or functional assignment. See [GTOTREE_WORKFLOW](GTOTREE_WORKFLOW.md) and
[phylogeny guidance](PHYLO_AUTOPILOT_WORKFLOW.md) for source and reference requirements.

### FastTree — approximate maximum-likelihood tree inference

**Standalone.** FastTree builds an approximate maximum-likelihood tree from an alignment,
using methods intended to make larger analyses practical. It can be useful for exploratory
relationships or a workflow that specifically selects it. Speed is not a substitute for
checking alignment quality, model assumptions and the kind of support values reported.
Do not describe its outputs as the same inference procedure as another tree program.

**In Sapote–Mamey.** FastTree may be selected by a companion phylogeny or family-analysis
workflow. Check the actual generated command and files: installing FastTree does not mean
a Mamey extraction called it, and the presence of a network diagram does not prove that a
family tree was inferred. Optional companion steps have separate readiness and completion
states.

**Keep/check.** Save the exact alignment, selected options, output tree, logs and taxon/region
mapping. If using it as an exploratory tree before a different analysis, keep both methods
explicit. Family trees concern the selected sequences and families, not necessarily whole-genome
relationships. Consult [GTOTREE_WORKFLOW](GTOTREE_WORKFLOW.md) and [GCF workflow](BIGSCAPE_GCF_WORKFLOW.md).

### RAxML-NG — reference-tree inference

**Standalone.** RAxML-NG performs maximum-likelihood phylogenetic inference on aligned data
under a chosen model and analysis setup. Its output is meaningful together with the alignment,
model, search configuration and support analysis. Reference selection and outgroup choices
remain researcher decisions; the program does not resolve inadequate sampling simply by
finding an optimized tree.

**In Sapote–Mamey.** The placement-related toolchain can use RAxML-NG to establish a reference
backbone before placing new queries. The backbone's tree, alignment and model must remain
compatible with the placement stage. Rebuilding the backbone is a different operation from
adding one query to a fixed reference and may change the context of previous placements.

**Keep/check.** Preserve the reference roster, source sequences, alignment, model, seed,
commands and support records. Distinguish an inferred backbone from a rendered picture of it.
If references or filtering change, record a new analysis identity rather than silently
reusing old placement labels. See the [placement workflow](PHYLO_AUTOPILOT_WORKFLOW.md) for
how the reference components feed the next stage.

### EPA-ng — places queries onto a fixed reference tree

**Standalone.** EPA-ng evaluates where query sequences fit on branches of a supplied reference
tree using a compatible alignment and evolutionary model. It does not build a new genome tree
from arbitrary unaligned FASTA files. Placement can distribute support across multiple
locations; that uncertainty should be retained rather than reduced to an unjustified single
species name.

**In Sapote–Mamey.** The placement workflow prepares query/reference alignment relationships
and uses an existing backbone before producing placement results. MAFFT and downstream
processing tools can be part of that sequence. For 16S, the biological interpretation is
limited by the marker's resolution and reference sampling, even when the computation itself
is successful.

**Keep/check.** Retain the exact reference tree, reference alignment, model, aligned query IDs
and jplace output. Check whether identifiers remained intact and whether placements are
ambiguous. A placement result is relatedness evidence, not compound identity, activity or an
automatic species assignment. See [PHYLO_AUTOPILOT_WORKFLOW](PHYLO_AUTOPILOT_WORKFLOW.md).

### gappa — processes phylogenetic placements

**Standalone.** gappa provides operations for working with placement data, including handling
jplace records and preparing derived summaries or tree-related outputs. It sits downstream of
a placement calculation and should not be confused with the algorithm that produced the
placements. A transformed view should preserve enough provenance to trace back to the
original query and placement record.

**In Sapote–Mamey.** The placement toolchain can use gappa to process EPA-ng results before
later display or reporting. The exact operation depends on the configured workflow. A
successfully generated tree-like file or figure does not prove that query uncertainty,
reference composition and mapping have all been reviewed. Rendering and inference are
separate completion checks.

**Keep/check.** Retain original jplace files, command/options, query roster and derived outputs.
When aggregating placements, report the aggregation choice rather than implying that all
queries had an identical best location. Join metadata through explicit identifiers. Consult
the [placement workflow](PHYLO_AUTOPILOT_WORKFLOW.md) and the relevant renderer's expected schema
before handing a derived tree to a figure tool.

### FastANI — whole-genome nucleotide similarity

**Standalone.** FastANI estimates average nucleotide identity between suitable genome
assemblies using its comparison method. The estimate should be considered with aligned
fraction or comparable coverage information, genome quality and the comparison's direction.
A reported value without sufficient shared sequence can be misleading. Common taxonomic
thresholds are useful context, not an automatic replacement for taxonomic evidence and reference quality.

**In Sapote–Mamey.** ANI can provide genome-level context for selected comparisons or tree
annotations. It is different from BGC similarity, a protein hit or an AB/AF score. A genome
FASTA and a justified reference set are needed; an antiSMASH annotation table alone does not
establish an ANI experiment. Use the actual selected companion/backend and retain its identity.

**Keep/check.** Record query/reference accessions and versions, assembly hashes, method/version,
identity and coverage outputs. Treat no reported comparison as a state to diagnose, not
immediate evidence of unrelatedness. See [offline comparison](../sapote_addons/README_OFFLINE_ANALYSIS.md)
and the genome workflow for the applicable integration.

### skani / pyskani — another genome-similarity route

**Standalone.** skani estimates genome similarity using its own computational approach;
pyskani provides a Python interface. These are distinct from FastANI, so method names and
versions must remain attached to results. Fragmented assemblies and differing coverage can
complicate interpretation even when a tool is designed to handle such inputs efficiently.
The software cannot repair contamination or mistaken reference identities.

**In Sapote–Mamey.** Optional comparison paths may use pyskani for genome-level similarity.
Confirm the backend actually selected and executed; an importable library or a historical
installation table is not a fresh result. Protein alignment and nucleotide similarity are
separate parts of a comparison, and one can fail or be unavailable while the other succeeds.

**Keep/check.** Save genome inputs, hashes, method/version, coverage-related outputs and
fallback/error receipts. Do not merge ANI-like values from different methods without stating
the distinction. Species interpretation needs appropriate references and biological context,
not just a threshold check. See [offline comparison](../sapote_addons/README_OFFLINE_ANALYSIS.md)
for the selected package's actual route and limitations.

### R — the optional statistical and plotting environment

**Standalone.** R runs analysis and plotting scripts using installed packages and data tables.
It is an environment, not one figure-producing algorithm. A script's variables, grouping,
missing-value handling and transformations determine what a plot means. Package installation
should be separated from analysis execution so that a reader can identify which versions
produced the result.

**In Sapote–Mamey.** Several optional figure scripts use R, while core extraction figures use
Python. The Figure Factory and bioassay workflow can prepare or consume specific table/config
contracts for R renderers. Installing R does not automatically validate those contracts or
turn a raw assay export into an analysis-ready table. The selected material, target, replicate
structure and exclusions must be explicit.

**Keep/check.** Retain the script, input tables, configuration, R/package versions and output
files. Check numerical values, legends and joins independently of whether R exited normally.
Use [R_FIGURE_WORKFLOWS](R_FIGURE_WORKFLOWS.md) to select a supported renderer and
[BIOASSAY_FIGURE_FACTORY](BIOASSAY_FIGURE_FACTORY.md) for assay-input requirements.

### ggplot2 — constructs R figures from data and mappings

**Standalone.** ggplot2 turns a data table and aesthetic mappings into a layered plot. The
researcher chooses which variables define position, grouping, color and statistical summaries.
The library does not know whether two rows are comparable biological observations or whether
a mean combines different materials. A polished plot can therefore still encode a bad analysis.

**In Sapote–Mamey.** The optional R plotting scripts use ggplot2 for selected scientific
figures. The input should be the workflow's admitted, traceable table rather than an arbitrary
spreadsheet copied into a plotting command. Some renderers also rely on shared theme functions
and other R packages; verify the specific script's dependencies.

**Keep/check.** Save the underlying data, transformations, selected grouping and the script or
config that generated the plot. Compare displayed values against the source table and inspect
labels, legends, exclusions and missing values. Figure generation does not establish assay
validity or BGC-level activity. See [R_FIGURE_WORKFLOWS](R_FIGURE_WORKFLOWS.md) and the relevant
Figure Factory contract for the exact supported route.

### ggtree — displays trees with matched annotations

**Standalone.** ggtree extends the R plotting approach to phylogenetic trees and associated
annotations. It displays a supplied tree; it does not infer that tree from raw sequences.
Annotations can be useful only when tips are matched correctly to the accompanying data.
An attractive heatmap beside a tree is not evidence that its rows were joined correctly.

**In Sapote–Mamey.** The R tree-rendering scripts can combine a completed tree with approved
strain-level tracks or metadata. The workflow requires explicit tip mappings and source-bound
annotation data. Placement results, genome-tree results and assay summaries have different
provenance and should not be mixed simply because their labels look similar.

**Keep/check.** Retain tree, tip roster, crosswalk, annotation table, methods and output files.
Inspect tip order, missing taxa, label clipping, legend scales and the meaning of each track.
Keep uncertainty and unmeasured values visible. See [R_FIGURE_WORKFLOWS](R_FIGURE_WORKFLOWS.md)
and [BIOASSAY_FIGURE_FACTORY](BIOASSAY_FIGURE_FACTORY.md) for supported tree/assay joins; the
Type Strain extraction walkthrough does not imply that a tree was built.

### patchwork — arranges multiple R plot panels

**Standalone.** patchwork combines plots into a larger composition with chosen rows, columns,
relative sizes and guides. It is a layout tool. It does not make different panels scientifically
comparable or verify that their legends use the same scale. Separate panels may represent
different cohorts, normalizations or experiments that need explicit labeling.

**In Sapote–Mamey.** Some optional R output paths use composite layouts to place related
figures together. The selected renderer determines whether patchwork is needed; it is not a
core extraction dependency. A successful single-panel plot does not guarantee that the
assembled figure preserves readable labels, matching scales and adequate space for every panel.

**Keep/check.** Retain the panel sources, arrangement script, dimensions and final export.
Review the complete composition at the intended reading size rather than checking only
individual panels. Captions should explain differences in sample sets or scales. Refer to
[R_FIGURE_WORKFLOWS](R_FIGURE_WORKFLOWS.md) for the actual script and output contract, and treat
layout review as distinct from numerical or biological validation.

### svglite — writes SVG graphics from R

**Standalone.** svglite provides an SVG graphics device for R output. SVG can preserve vector
lines and text for resizing or further layout work, but portability still depends on fonts,
text handling and how another application renders the file. Choosing SVG does not repair
clipped labels or prove that the original chart was correctly constructed.

**In Sapote–Mamey.** Optional R renderers that export SVG may use svglite. It belongs to the
rendering stage after data preparation and plot construction. The presence of an SVG file
means an export was written; it does not establish that every companion PNG/PDF was generated
or that the files look the same in another viewer.

**Keep/check.** Save the original SVG, source data, plot script/configuration and any later
edited version separately. Inspect text, symbols, line widths and clipping in the intended
viewing/export application. If an editor changes labels or data presentation, retain that
change in the figure provenance. See [R_FIGURE_WORKFLOWS](R_FIGURE_WORKFLOWS.md) for which
renderers use this device and which sidecars belong with their exports.

## Reference databases are a separate choice

**Pfam** supplies protein-family profiles; HMMER/pyhmmer and relevant companions search those
profiles. **MIBiG** supplies curated reference-cluster records that inform comparisons; membership
or similarity is not a product assignment to a new strain. **UniProt/Swiss-Prot**, **nr**,
**ClusteredNR** and **RefSeq** are different protein-reference choices with different scope and
provenance. A local **16S reference set** must be bound to an actual release and taxon roster.

Do not infer a database installation from a Python package installation. Preserve resource/version,
retrieval date, hashes, query mappings and required attribution. Use the README's resource table
and the selected workflow's input requirements. The recovered historical tool guide's machine
availability table is not a current inventory of your other laptop.

## Before using a companion

Ask: Which question requires it? Which files will it read? Does the selected command actually
call it, or only prepare/import results? Which database and version are selected? Will data leave
the workspace? What files and sizes are expected? What result will demonstrate that the stage
completed? Record those answers with its receipt. A tool's availability is not authorization to
run every downstream stage.

## Hand a selected question to a companion tool

A useful handoff carries a biological question, exact sequence identities, input files and hashes, tool/database version, output destination and interpretation limit. The examples below describe handoff content, not results.

**Protein similarity:** export the selected protein FASTA with a mapping back to strain, full contig, region and locus tag. Specify whether the task uses local BLAST+/DIAMOND or an online service and which database. Retain raw alignments and query/subject coverage as well as scores. Bring results back through the documented importer for that channel; do not paste an unbound top-hit name into a BGC conclusion.

**Domain evidence:** supply the protein sequences and explicitly selected HMM library to HMMER or the supported pyhmmer route. Record model release, thresholds and scan status. Preserve negative results only with the tested scope. A missing database is not a zero-hit scan, and one domain match is not proof of a complete pathway.

**Cluster comparison:** select the exact region GenBanks and map every exported label to its source package. BiG-SCAPE grouping and clinker graphics address related but different questions: family grouping versus comparative gene arrangement. Retain run settings, input membership and identifiers. A visually similar arrangement is not a validated product assignment.

**Genome/tree context:** use a defined genome or sequence panel, selected reference set and outgroup, with recorded exclusions. ANI and species-marker trees describe genome relationships; a biosynthetic-domain tree addresses the history of those sequences. Do not exchange their conclusions. Preserve alignments, trimming/model settings, tree files and support values with the figure.

**Rendering:** supply the intended evidence table, units, missing-value meanings and identity mapping. Retain that table and rendering configuration alongside PNG/PDF/SVG output. Inspect the finished figure for clipped labels and misleading scales before sharing it.
