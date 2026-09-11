# Sapote Mamey Quick Guide

**Version:** v9.7.428 / engine Mamey 1.9.163

Mamey extracts deterministic evidence from antiSMASH output. Sapote uses validated evidence
packages for governed interpretation. Start at the [README](../../README.md); coding assistants
use the shared [AGENTS contract](../../AGENTS.md). The same workflow applies across assistants.
Check the [release manifest](../../RELEASE_MANIFEST.md) for the exact bundle's status.

## 0. Install

Use Python 3.12 or newer in an isolated environment. The following archive name matches the
current release manifest; substitute the actual archive and extracted directory when working
with a renamed download or an unsealed candidate. The bundle root contains `mamey_run.py`.

```bash
mkdir -p sapote-mamey
unzip sapote-mamey-v9.7.428-CODE-20260911v97428a.zip -d sapote-mamey
cd sapote-mamey
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python mamey_run.py start
python mamey_run.py doctor
python3 tools/sync_version.py --check # → engine 1.9.163, bundle 9.7.428
```

See [INSTALL](../INSTALL.md) for Windows activation, optional extras, offline wheel compatibility,
and test setup. Do not override system Python protections or alter wheel compatibility tags.

## 1. Inspect and run one strain

Replace the paths and metadata below with values bound to the real input. `EXAMPLE` is a generic
strain placeholder. Inspect first and read its diagnostics and suggested invocation.

```bash
python mamey_run.py inspect path/to/antismash_result.zip
python mamey_run.py run --strain EXAMPLE \
  --input-zip path/to/antismash_result.zip \
  --taxonomy 'Genus sp.' --source 'recorded isolation source' \
  --mode gold --outdir ../analysis/runs/
python mamey_run.py validate ../analysis/runs/EXAMPLE/package
python mamey_run.py explain ../analysis/runs/EXAMPLE/package
```

Read the actual package path and status in the output. Stop interpretation on validation failure;
record and resolve the reported issue. A successful structural gate is not scientific acceptance.

## 2. Choose the evidence and runtime budget

Gold is the analysis mode. For time-limited execution, add `--capped-session` to the run command.
It forces JSON evidence off and `--brief none`, requires the workbook, and disables automatic
locus maps unless explicitly enabled. Passing `--json-evidence bounded` alongside that flag does
not retain JSON evidence. For bounded JSON extraction, omit the capped flag and allow enough runtime.

The deprecated `--chatgpt-safe` alias has the same behavior. This is a resource choice, not an
assistant-specific workflow. A capped run can leave deliverables or evidence channels deferred;
list those explicitly and render applicable figures after validation.

## 3. Review and retain the package

Keep the input ZIP, its checksum, the run configuration, the package manifest, and the issue log.
Check the inventory, triage board, workbook, and validation result. Report any missing or deferred
briefs, figures, locus maps, or evidence streams. Do not promise an artifact merely because the
command supports it. Preserve sealed inputs and use documented post-seal commands for follow-on work.

## 4. Process a cohort

Inventory input ZIPs and run each strain before selecting cross-strain interpretation targets.
Use existing intake and master-workbook workflows in the [User Manual](01_User_Manual.md).
The `run` command accepts `--master /path/to/project_master.xlsx`; check the emitted workbook status
and preserve an existing master before updating it. A folder name or modification time does not
establish which master is authoritative.

## 5. Select a deliverable

Choose the output that answers the user's question: a triage board, lead summary, figures, a
plain-language guide, a Mode B card, or a compiled report. The
[deliverable contract](../DELIVERABLE_CONTRACT.md) defines required artifacts and quality checks.
Record completed and pending outputs; there is no required menu size or model-specific reply ritual.

## 6. Bind a complete locus identity

Every individual BGC reference must carry **strain / full node-or-contig / region / BGC alias**,
copied from one bound source record. Filenames must encode all four components safely. A bare
alias, a shortened node, or a remembered chat label is insufficient. Stop with an identity hold
when components are missing or conflicting. Preserve exact source paths and hashes.

## Deepen the evidence before writing

### Protein search and result import

Choose between representative screening and a full region-level search. The representative panel
below reads translated CDS sequences from the input ZIP and writes FASTA batches plus a manifest:

```bash
python mamey_run.py bgc-blastp-panel --input-zip path/to/antismash_result.zip \
  --strain EXAMPLE --outdir analysis/protein_panel --genes-per-bgc 2
```

For a manual search, submit the exported amino-acid FASTA batches to the BLASTp service you have
chosen. Preserve the query headers and batch manifest. Save the hit-table CSV and alignment XML
alongside the search database, date, and settings. A representative panel samples the regions;
it is not a full per-gene examination of every region.

To submit all extracted proteins from one already selected region through the NCBI runner:

```bash
python mamey_run.py blastp-online --package path/to/selected_region.gbk \
  --database nr --outdir analysis/region_protein_search
```

This command makes network submissions. `--package` here means the protein-bearing region GBK
or antiSMASH ZIP, not simply the sealed Mamey output directory. For a multi-region ZIP, first bind
the full locus identity and use the documented region/crosswalk selectors; do not submit an
unscoped whole-genome ZIP as though it were one region. The default batch size is 10 proteins.

For a strain-wide plan, `blastp-round` defaults to full coverage of the top three ranked regions
and one representative protein from each remaining region. Planning does not submit searches:

```bash
python mamey_run.py blastp-round --package runs/EXAMPLE/package \
  --outdir analysis/blastp_plan
```

Inspect the plan before using `--run`. For resumable scheduling, start with
`auto-blastp --help` and its `--dry-run` option. Confirm the selected channel's actual transport
availability; nr, ClusteredNR, and local Swiss-Prot evidence are separate channels.

For saved NCBI hit tables, import into an existing project master and the matching package overlay:

```bash
python mamey_run.py ingest-blastp --master path/to/project_master.xlsx \
  --strain EXAMPLE --hit-table analysis/hits.csv --xml analysis/alignments.xml \
  --package runs/EXAMPLE/package
```

Retain a copy of the master before updating it. Review the import diagnostics and query mappings.
Omitting `--package` updates the workbook without providing the same package overlay to downstream
readers. For non-NCBI results, use the channel-specific workflow and correct source metadata;
do not label an EBI or local search as NCBI nr.

Use the results to investigate disagreements: a short local match, a missing alignment segment,
or a generic enzyme annotation can change meaning when full protein length, domains, and gene
context are considered together. A failed search is not a no-hit result. The
[BLASTp protocol](../ONLINE_BLASTP_PROTOCOL.md) covers scoping, batching, provenance, and channels.

### Fragmented-pathway review

RG-GMCI runs during extraction. Review its pair-level evidence with the inventory's boundary
status and the original reference matches. For each proposed link, inspect:

- shared reference support and hit geometry, including whether positions are coordinates or a locus-number proxy;
- complementary subject-gene coverage versus both fragments matching the same conserved machinery;
- contig-edge/terminus evidence, product-class compatibility, and reasons for a confidence downgrade;
- conflicting protein/domain evidence and any remaining missing sequence.

Keep both fragments' complete locus identities. A proposed linkage does not merge their source
records. Low-complexity termini can require long-read resolution rather than a computational
junction claim. Use BiG-SCAPE family context and BLASTp as additional evidence during interpretation;
their existence does not automatically promote a linkage or repair the assembly.

### BiG-SCAPE family analysis

The integrated runner accepts a package, cohort run directory, or explicit directory of region
GBKs. Install the external BiG-SCAPE toolchain and provide the pressed Pfam database first:

```bash
python mamey_run.py doctor --companions
python mamey_run.py bigscape --runs-dir runs/ --out analysis/bigscape \
  --bigscape /absolute/path/to/bigscape --pfam /absolute/path/to/Pfam-A.hmm \
  --cpus 1 --dry-run
```

Review the staging plan, then remove `--dry-run` to execute it. The runner produces a cohort
SQLite database and attempts the linked matrix/clinker widgets unless `--no-widgets` is set.
Check both the compute and widget results; one successful stage does not prove every output exists.

Use family membership to compare architectures across the sampled strains. Retain the run ID,
cutoff, region membership, input hashes, reference-panel composition, and contig-edge flags.
Family identifiers are local to a run; a singleton is not automatically a novel product.
See the [GCF workflow](../BIGSCAPE_GCF_WORKFLOW.md) for reference preparation and interpretation.

### Trees and heatmap overlays

Supply 16S FASTA for locus-based routing/placement or whole-genome FASTA for genome phylogeny.
An antiSMASH ZIP alone is not the input for a whole-genome tree. Start by inspecting uploads:

```bash
python mamey_run.py phylo-autopilot plan path/to/sequence_uploads
python mamey_run.py phylo-autopilot route --query path/to/16S.fasta \
  --db /absolute/path/to/16S_database_prefix --out analysis/routing.tsv
python mamey_run.py phylo-run --help
```

The database prefix and external tools must exist on your machine. Review routing, references,
outgroup, and compute requirements before executing a tree. `run-16s` uses its `--approved-by`
argument; the genome runner requires `--approved`. The
[autopilot guide](../PHYLO_AUTOPILOT_WORKFLOW.md) explains the sequence routes.

Tree construction and annotation are separate steps. The existing tree overlay tool consumes a
`sapote.tree-figure-factory.v1` configuration with the tree, alignment, workflow/model/seed receipts,
outgroup and final-tip rosters, an explicit tip crosswalk, and an annotation matrix:

```bash
python tools/tree_bgc_overlay.py --config path/to/tree_overlay.json
```

The config must bind the actual files and hashes; the command does not invent these inputs.
Supported strain-level tracks include ANI, BGC, DOMAIN, MODE_B, and ASSEMBLY. It renders SVG/PNG
artwork with reproducibility outputs. Placement renderers also support metadata-oriented tree
views; host/location data must come from a supplied source. Preserve missing values, inspect
label clipping and track alignment, and keep the methods/caption sidecars with the final figure.
The separate `figure-factory` phylogeny adapters may prepare data or diagnostics rather than a
finished tree image: check the returned output type. See the [figure entry point](../FIGURES_START_HERE.md).

For a repeatable series of 1:1, 1:2, and 1:3 query-to-reference displays, declare the completed
placement runs in a [Tree Catalog](../TREE_CATALOG.md). The catalog can emit paired geography and
no-geography views in one run. It records type-only versus type-plus-selected-non-type panels and
refuses to create a spotlight claim by silently pruning a full-cohort analysis.

### Bioassays, trees, and R figures

Do not feed a raw plate-reader export directly to a tree renderer. First map every 96- or 384-well
observation into the canonical schema, including material lineage, organism label state, time point,
replicate type, controls, and exclusions. Then build the admitted summary:

```bash
python mamey_run.py figure-factory --config path/to/bioassay_figure.json
```

The bioassay factory can emit one explicitly selected quantitative `BIOASSAY` tree track. Its config
must name one target, target state, time point, material type, strain roster, and material ID per
strain. A separate exact crosswalk binds those strains to a GToTree tree or to reviewed EPA-ng tips
for strains that have 16S but no genome. See the [bioassay contract](../BIOASSAY_FIGURE_FACTORY.md)
and [R renderer map](../R_FIGURE_WORKFLOWS.md).

## 7. Author Mode B from current evidence

Start from a validated package. `mode-b` emits a top-leads table; it does not author a finished
card. Read the [Mode B document index](../MODE_B_DOCUMENT_INDEX.md), the
[authoring preflight](../MODE_B_AUTHORING_PREFLIGHT.md), and the matching class exemplar before writing.

Use `emit-modeb-template --help` for template options. Choose the current named profile using
its machine-readable contract and emitted template; a historical section count is not authority.
Retain exact titles and required evidence fields. When a CLI requires an alias in `--bgc`, bind it
to the complete four-component identity and package first; that argument is only a machine selector.

Keep nr, ClusteredNR, and local Swiss-Prot channels separate. Missing hits, unrun searches, and
provenance holds remain explicit typed states. Never fill a template with invented observations.
Run structure/depth, claim-safety, and quality checks on the actual authored file and report their
receipts. A template pass or `PASS_STRUCTURE` does not establish a finished or scientifically accepted card.

## 8. Review figures and prose

Use the [figure entry point](../FIGURES_START_HERE.md) and existing renderers before creating a new
plot. Read the rendered output, check labels and complete identities, and retain the data behind
it. Capacity is not production; similarity is not compound identity; strain or extract bioactivity
must not become an unsupported locus-level claim. Missing evidence is not biological absence.

## 9. Save a resumable handoff

Save the objective, exact inputs and hashes, permitted output location, completed work, unresolved
holds, and next bounded step. Link the package and actual authored deliverables. Preserve prior
versions and state what supersedes them. A saved summary supplements the conversation; it is not
a verbatim transcript. User review and release acceptance remain separate decisions.

### Citation-Compact Provenance and Citation Status

Method provenance: antiSMASH 8.0 DOI `10.1093/nar/gkaf334`; MIBiG 4.0 reference-database
provenance: DOI `10.1093/nar/gkae1115`. These identify methods and databases, not a confirmed product.
`PASS_STRUCTURE` reports structural checks, not verification of literature claims.
`operator_supplied` identifies runtime evidence provenance; `citation_needed` remains an unresolved
literature requirement. `Literature_Search_WorkOrder.md/json` is a search handoff, not a verified fact.
Current compact lead tables use `interpretation_scope` for reader-facing scope.

## 10. Post-seal deliverables

Use the validated package with the command you need. Begin with its `--help` and preserve the
command, input identity, diagnostics, and resulting files. For the example package above:

```bash
python mamey_run.py list-bgcs runs/EXAMPLE/package
python mamey_run.py render-all-figures runs/EXAMPLE/package
python mamey_run.py emit-modeb-template --help
python mamey_run.py verify-modeb --help
```

`verify-modeb` requires the authored Markdown file as a positional argument. For a package-bound
review, also supply `--package` and its reconciled `--bgc` selector; `--interp` adds the interpretation
check and does not replace structural, claim-safety, or quality review. A package path alone does
not identify an authored card.

The [tools reference](../user_guides/tools_reference.md) and
[command catalog](../COMMAND_CATALOG.generated.md) cover cohort ledgers, comparator coverage,
AF dossiers, Good Guesses, document export, locus maps, and advisory helpers. Consult their
individual dependency, output, and sign-off requirements. For release work, use the
[cut protocol](../../CUT_PROTOCOL.md); historical notes in the [changelog](../../CHANGELOG.md)
do not replace current operating instructions.
