# Sapote Mamey Quick Guide

**Version:** v9.7.433 / engine Mamey 1.9.167

Mamey extracts deterministic evidence from antiSMASH output. Sapote turns a validated evidence
package into governed interpretation. Start at the [README](../../README.md). If you work through a
coding assistant, it follows the shared [AGENTS contract](../../AGENTS.md); the workflow is the same
either way. Check the [release manifest](../../RELEASE_MANIFEST.md) for the status of the exact
bundle you have.

This page is the compact reference. For a first-time walkthrough with plain-language setup and
recovery steps, use [Your first analysis](../MASTER_WALKTHROUGH.md). If you already have a
package, use [Read your results](../READING_YOUR_RESULTS.md).

## Start with the question you need answered

There are two paths here: a first validated extraction, then optional follow-on analysis. You do
not need every optional tool to inspect the bundle or to run core extraction. For a
decision-oriented walkthrough, see [Working with an assistant](../ASSISTANT_USER_GUIDE.md).

Find your starting point in the table, then go to the matching section.

| Your situation | First useful action | What you should receive |
|---|---|---|
| Code ZIP or repository only | Review files; install only if execution is requested | Capability and setup assessment, not a strain result |
| One antiSMASH result ZIP | Inspect, bind metadata, then run and validate | Inventory, evidence package, workbook and explicit missing/deferred states |
| Existing validated package | Read manifest, issues and available evidence first | The requested summary/card/figure; no automatic rerun |
| Genome or 16S FASTA only | Select the appropriate sequence workflow | A scoped placement/genome plan; not an invented antiSMASH package |
| Several strains | Identify authoritative inputs and master workbook | A resumable batch with per-strain outcomes and preserved prior master |

Three things to know before you run anything:

- Read §2 (the evidence and runtime budget) before you run the command in §1. Bounded JSON is the
  documented default; capped mode trades evidence and rendered outputs for a shorter run.
- A code bundle alone contains software, not your biological results.
- Run the commands below yourself, in the foreground, one at a time.

## 0. Install

Use Python 3.12 or newer in an isolated environment. The archive name below matches the current
release manifest; if your download or unsealed candidate has a different name, substitute the real
archive and extracted directory. The bundle root is the directory that contains `mamey_run.py`.

```bash
unzip path/to/code-bundle.zip -d path/to/extracted-code
# Locate pyproject.toml and mamey_run.py together; GitHub ZIPs add a nested directory.
cd path/to/extracted-code/actual-bundle-root
python3 --version  # must be 3.12 or newer before creating the environment
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[figures,bio]'
python mamey_run.py start
python mamey_run.py doctor
python tools/sync_version.py --check # checks version consistency, not candidate release acceptance
```

This example installs the core plus the figure and Biopython extras. For core extraction only, use
`python -m pip install -e .`; rendering capabilities will then differ. Neither choice installs the
external companion databases or programs. Read doctor warnings by capability: a missing optional
tree tool does not stop core extraction.

Install only when you intend to run the software; reviewing the documentation does not need an
install. The pip commands may download packages. If network access is not authorized, use the
documented offline procedure. Keep the environment and all outputs inside your permitted root.

[INSTALL](../INSTALL.md) covers Windows activation, optional extras, offline wheel compatibility
and test setup. Do not override system Python protections or alter wheel compatibility tags.

## 1. Inspect and run one strain

Replace the paths and metadata below with the values bound to your real input. `EXAMPLE` is a
placeholder strain ID. Run `inspect` first and read its diagnostics and the invocation it suggests.

```bash
python mamey_run.py inspect path/to/antismash_result.zip
python mamey_run.py run --strain EXAMPLE \
  --input-zip path/to/antismash_result.zip \
  --taxonomy 'Genus sp.' --source 'recorded isolation source' \
  --mode gold --json-evidence bounded --brief none --locus-maps off \
  --release PRIVATE --outdir analysis/runs/
python mamey_run.py validate analysis/runs/EXAMPLE/package
python mamey_run.py explain analysis/runs/EXAMPLE/package
```

This first run deliberately skips the brief and the locus maps. `PRIVATE` labels your local
artifacts; it does not claim that a public source genome is private. Choose another release tag
only when it fits your output. If isolation metadata are missing, `--source 'not supplied'`
records that gap; the GenBank `SOURCE` organism label in the archive is not the isolation habitat.

Read the package path and status in the output. If validation fails, stop interpreting, record the
reported issue and resolve it. A passing structural gate is not scientific acceptance.

## 2. Choose the evidence and runtime budget

| Choice | Main JSON behavior | What to report |
|---|---|---|
| `--json-evidence bounded` | Streams with byte/leaf limits | Truncation, fallback and unresolved completeness |
| `--json-evidence full` | Cap: 80,000,000 bytes per file | Size hold if over cap; admitted files may still require several GB RAM |
| `--json-evidence off` | Disables the main walker; record-level paths are separate | Which evidence channels actually ran |
| `--capped-session` | Overrides the main walker to off and suppresses selected outputs | Deferred evidence and deliverables |

The shipped full-mode cap is 80 MB (`FULL_MAX_JSON_BYTES` in `mamey/antismash_evidence.py`); the earlier 20 MB cap was retired.
ZIP download size is not uncompressed JSON size, and more CPU threads cannot bypass this hard-coded
size check. Full mode is not a completeness certificate. See
[a public-strain walkthrough with examples on both sides of 80 MB](../ROUND2_PUBLIC_STRAIN_WALKTHROUGH.md).

Gold is the analysis mode. When a time limit applies, add `--capped-session` to the run command.
It forces JSON evidence off and `--brief none`, requires the workbook, and disables automatic
locus maps unless you enable them explicitly. Passing `--json-evidence bounded` alongside the
capped flag does not keep JSON evidence. For bounded JSON extraction, omit the capped flag and
allow enough runtime. The deprecated `--chatgpt-safe` alias behaves the same way.

A capped run can leave deliverables or evidence channels deferred. List those explicitly, and
render the applicable figures after validation.

## 3. Review and retain the package

Keep the input ZIP, its checksum, the run configuration, the package manifest and the issue log.
Check the inventory, triage board, workbook and validation result. Report any brief, figure, locus
map or evidence stream that is missing or deferred. Do not promise an artifact just because the
command supports it. Keep sealed inputs as they are and use the documented post-seal commands for
follow-on work.

### Know which kind of completion you have

| State | Meaning | Still not established |
|---|---|---|
| Doctor completed | Environment diagnostics were produced | Successful extraction or scientific correctness |
| Extraction and validation completed | Encoded package gates ran; inspect actual statuses and issues | Every optional evidence channel or requested narrative is finished |
| `MAMEY_COMPLETE_WITH_ISSUES` | Pipeline completed with recorded issues | That every warning is resolved |
| Validator says `MAMEY_COMPLETE` | Validator completed its encoded checks | That pipeline issues or judgment pending disappeared |
| A template was emitted | A writing scaffold exists | An authored or verified Mode B card |
| Structure/depth checks passed | The particular encoded checks passed | Factual source binding, literature verification or product identity |
| Requested deliverable reviewed | The selected files and their evidence were checked | Publication, new release or permission to distribute private material |

### Recover without losing provenance

| Symptom | Next check | Safe recovery |
|---|---|---|
| Wrong Python or import failure | Interpreter version and selected environment | Use Python 3.12+ and the documented extras; do not bypass system protections |
| `inspect` rejects a ZIP | Archive type and required antiSMASH contents | Obtain/fix the input; do not pass the code ZIP as biological data |
| Timeout/interruption | Last log event and partial output status | Preserve the attempt; resume through the documented intake workflow or start a separately named run |
| Validation failure | Actual failed gate and issue details | Hold affected interpretation; diagnose before declaring the package complete |
| Figure or homology result missing | Requested mode, dependencies and recorded channel status | Complete only the needed follow-on work; absence of a file is not negative biology |
| Ambiguous locus or master workbook | Source-bound identity, hashes and prior receipts | Hold the disputed join/update; continue independent review |

The example run writes under `analysis/runs/` inside the bundle working directory. Use a new output
directory when inputs or parameters change. Do not overwrite a previous run to make the latest
command succeed. Keep original inputs immutable and record which output supersedes which.

## 4. Process a cohort

Inventory the input ZIPs and run each strain before you choose cross-strain interpretation targets.
The intake and master-workbook workflows are in the [User Manual](01_User_Manual.md). The `run`
command accepts `--master /path/to/project_master.xlsx`; check the emitted workbook status and keep
a copy of an existing master before updating it. A folder name or modification time does not show
which master is authoritative.

## 5. Select a deliverable

Choose the output that answers the question: a triage board, lead summary, figures, a plain-language
guide, a Mode B card or a compiled report. The [deliverable contract](../DELIVERABLE_CONTRACT.md)
defines the required artifacts and quality checks. Record which outputs are complete and which are
pending.

## 6. Bind a complete locus identity

Every reference to an individual BGC must carry **strain / full node-or-contig / region / BGC alias**,
copied from one bound source record, and filenames must encode all four components safely. A bare
alias, a shortened node or a remembered label is not enough. If a component is missing or
conflicting, stop with an identity hold. Keep exact source paths and hashes.

## Deepen the evidence before writing

### Protein search and result import

Choose between a representative screen and a full region-level search. The representative panel
reads translated CDS sequences from the input ZIP and writes FASTA batches plus a manifest:

```bash
python mamey_run.py bgc-blastp-panel --input-zip path/to/antismash_result.zip \
  --strain EXAMPLE --outdir analysis/protein_panel --genes-per-bgc 2
```

For a manual search, submit the exported amino-acid FASTA batches to the BLASTp service you have
chosen. Keep the query headers and batch manifest. Save the hit-table CSV and alignment XML together
with the search database, date and settings. A representative panel samples the regions; it is not
a full per-gene examination of every region.

To submit every extracted protein from one selected region through the NCBI runner:

```bash
python mamey_run.py blastp-online --package path/to/selected_region.gbk \
  --database nr --outdir analysis/region_protein_search
```

This command makes network submissions. Here `--package` means the protein-bearing region GBK or
antiSMASH ZIP, not simply the sealed Mamey output directory. For a multi-region ZIP, bind the full
locus identity first and use the documented region/crosswalk selectors; do not submit an unscoped
whole-genome ZIP as if it were one region. The default batch size is 10 proteins.

For a strain-wide plan, `blastp-round` defaults to full coverage of the top three ranked regions
plus one representative protein from each remaining region. Planning does not submit searches:

```bash
python mamey_run.py blastp-round --package analysis/runs/EXAMPLE/package \
  --outdir analysis/blastp_plan
```

Inspect the plan before you add `--run`. For resumable scheduling, start with `auto-blastp --help`
and its `--dry-run` option. Confirm that the channel you chose is actually reachable; nr,
ClusteredNR and local Swiss-Prot are separate evidence channels.

To import saved NCBI hit tables into an existing project master and the matching package overlay:

```bash
python mamey_run.py ingest-blastp --master path/to/project_master.xlsx \
  --strain EXAMPLE --hit-table analysis/hits.csv --xml analysis/alignments.xml \
  --package analysis/runs/EXAMPLE/package
```

Keep a copy of the master before updating it. Review the import diagnostics and query mappings. If
you omit `--package`, the workbook is updated but downstream readers do not get the package overlay.
For non-NCBI results, use the channel-specific workflow and the correct source metadata; do not
label an EBI or local search as NCBI nr.

Use the results to look into disagreements. A short local match, a missing alignment segment or a
generic enzyme annotation can change meaning once full protein length, domains and gene context are
read together. A failed search is not a no-hit result. The
[BLASTp protocol](../ONLINE_BLASTP_PROTOCOL.md) covers scoping, batching, provenance and channels.

### Fragmented-pathway review

RG-GMCI runs during extraction. Review its pair-level evidence together with the inventory's
boundary status and the original reference matches. For each proposed link, inspect:

- shared reference support and hit geometry, including whether positions are coordinates or a locus-number proxy;
- complementary subject-gene coverage versus both fragments matching the same conserved machinery;
- contig-edge/terminus evidence, product-class compatibility, and reasons for a confidence downgrade;
- conflicting protein/domain evidence and any remaining missing sequence.

Keep both fragments' complete locus identities. A proposed link does not merge their source
records. Low-complexity termini can need long-read resolution rather than a computed junction.
BiG-SCAPE family context and BLASTp add evidence during interpretation; on their own they do not
promote a link or repair the assembly.

### BiG-SCAPE family analysis

The integrated runner accepts a package, a cohort run directory or an explicit directory of region
GBKs. Install the external BiG-SCAPE toolchain and provide the pressed Pfam database first:

```bash
python mamey_run.py doctor --companions
python mamey_run.py bigscape --runs-dir analysis/runs/ --out analysis/bigscape \
  --bigscape /absolute/path/to/bigscape --pfam /absolute/path/to/Pfam-A.hmm \
  --cpus 1 --dry-run
```

Review the staging plan, then remove `--dry-run` to execute it. The runner produces a cohort SQLite
database and, unless `--no-widgets` is set, tries to build the linked matrix and clinker widgets.
Check both the compute and the widget results; one successful stage does not prove every output
exists.

Use family membership to compare architectures across the sampled strains. Keep the run ID, cutoff,
region membership, input hashes, reference-panel composition and contig-edge flags. Family
identifiers are local to a run, and a singleton is not automatically a novel product. The
[GCF workflow](../BIGSCAPE_GCF_WORKFLOW.md) covers reference preparation and interpretation.

### Trees and heatmap overlays

Choose the sequence route that matches your question. A 16S FASTA can be
placed against a reference backbone. Whole-genome FASTA can support a core-genome
tree. If your antiSMASH ZIP contains the **full assembly** (not only clipped
region files), `phylo-mlsa` offers an optional five-protein-coding-gene MLSA
screen from that assembly. Selection of a non-region sequence member does not
certify that the assembly is complete; review the member and assembly metrics.
The screen helps select neighbors for a later core-genome
analysis; it does not establish species identity. Reference genome
acquisition remains a separate, reviewed step. Start by inspecting the uploads
or planning the MLSA input:

```bash
python mamey_run.py phylo-autopilot plan path/to/sequence_uploads
python mamey_run.py phylo-autopilot route --query path/to/16S.fasta \
  --db /absolute/path/to/16S_database_prefix --out analysis/routing.tsv
python mamey_run.py phylo-mlsa --input-zip path/to/antismash.zip \
  --query-label QUERY_A --mode plan
python mamey_run.py phylo-run --help
```

For MLSA, supply locally curated `.fna` reference genomes in
`--references-dir`, with exactly one filename containing `_OUTGROUP` for
`--mode run`. `--mode prepare --outdir new_directory` stages a source-bound
genome set; `--mode run` also calls the shipped `build_mlsa.py` driver, which
requires Prodigal, BLAST+, MUSCLE and IQ-TREE. A ZIP with region GBKs only is
refused. The database prefix and external tools for 16S placement must exist on
your machine. Review routing, references, outgroup and compute requirements
before building a tree. `run-16s` takes `--approved-by`; the core-genome runner
requires `--approved`. The [autopilot guide](../PHYLO_AUTOPILOT_WORKFLOW.md)
explains the 16S and core-genome routes; the [GToTree workflow](../GTOTREE_WORKFLOW.md)
explains MLSA screening and later genome-panel selection.

Building a tree and annotating it are separate steps. The tree overlay tool reads a
`sapote.tree-figure-factory.v1` configuration that names the tree, alignment, workflow/model/seed
receipts, outgroup and final-tip rosters, an explicit tip crosswalk and an annotation matrix:

```bash
python tools/tree_bgc_overlay.py --config path/to/tree_overlay.json
```

The config must bind the actual files and hashes; the command does not invent them. Supported
strain-level tracks are ANI, BGC, DOMAIN, MODE_B and ASSEMBLY. It renders SVG/PNG artwork with
reproducibility outputs. Placement renderers also support metadata-oriented tree views, with host
and location data taken from a supplied source. Keep missing values as missing, check label clipping
and track alignment, and keep the methods and caption sidecars with the final figure. The separate
`figure-factory` phylogeny adapters may return data or diagnostics rather than a finished tree
image, so check the output type. See the [figure entry point](../FIGURES_START_HERE.md).

For a repeatable series of 1:1, 1:2 and 1:3 query-to-reference displays, declare the completed
placement runs in a [Tree Catalog](../TREE_CATALOG.md). The catalog can emit paired geography and
no-geography views in one run. It records type-only versus type-plus-selected-non-type panels and
refuses to create a spotlight claim by silently pruning a full-cohort analysis.

### Bioassays, trees, and R figures

Do not feed a raw plate-reader export straight to a tree renderer. First map every 96- or 384-well
observation into the canonical schema, including material lineage, organism label state, time point,
replicate type, controls and exclusions. Then build the admitted summary:

```bash
python mamey_run.py figure-factory --config path/to/bioassay_figure.json
```

The bioassay factory can emit one explicitly selected quantitative `BIOASSAY` tree track. Its config
must name one target, target state, time point, material type, strain roster and material ID per
strain. A separate exact crosswalk binds those strains to a GToTree tree, or to reviewed EPA-ng tips
for strains that have 16S but no genome. See the [bioassay contract](../BIOASSAY_FIGURE_FACTORY.md)
and the [R renderer map](../R_FIGURE_WORKFLOWS.md).

## 7. Author Mode B from current evidence

Start from a validated package. `mode-b` emits a top-leads table; it does not write a finished card.
Before writing, read the [Mode B document index](../MODE_B_DOCUMENT_INDEX.md), the
[authoring preflight](../MODE_B_AUTHORING_PREFLIGHT.md) and the matching class exemplar.

Use `emit-modeb-template --help` for the template options. Choose the current named profile from its
machine-readable contract and emitted template; a historical section count is not authority. Keep
the exact titles and required evidence fields. When a command takes an alias in `--bgc`, bind it to
the complete four-component identity and the package first; the argument is only a machine selector.

Keep the nr, ClusteredNR and local Swiss-Prot channels separate. Missing hits, unrun searches and
provenance holds stay as explicit typed states. Never fill a template with invented observations.
Run the structure/depth, claim-safety and quality checks on the authored file itself and report
their receipts. A template pass or `PASS_STRUCTURE` does not make a card finished or scientifically
accepted.

## 8. Review figures and prose

Use the [figure entry point](../FIGURES_START_HERE.md) and the existing renderers before creating a
new plot. Read the rendered output, check labels and complete identities, and keep the data behind
it. Capacity is not production; similarity is not compound identity; strain or extract bioactivity
must not become an unsupported locus-level claim. Missing evidence is not biological absence.

## 9. Save a resumable handoff

Save the objective, the exact inputs and their hashes, the permitted output location, completed
work, unresolved holds and the next bounded step. Link the package and the authored deliverables.
Keep prior versions and state what supersedes them. A saved summary is not a verbatim transcript.
User review and release acceptance remain separate decisions.

### Citation-Compact Provenance and Citation Status

Method provenance: antiSMASH 8.0 DOI `10.1093/nar/gkaf334`; MIBiG 4.0 reference-database
provenance: DOI `10.1093/nar/gkae1115`. These identify methods and databases, not a confirmed product.
`PASS_STRUCTURE` reports structural checks, not verification of literature claims.
`operator_supplied` identifies runtime evidence provenance; `citation_needed` remains an unresolved
literature requirement. `Literature_Search_WorkOrder.md/json` is a search handoff, not a verified fact.
Current compact lead tables use `interpretation_scope` for reader-facing scope.

## 10. Post-seal deliverables

Use the validated package with the command you need. Begin with its `--help`, and keep the command,
input identity, diagnostics and resulting files. For the example package above:

```bash
python mamey_run.py list-bgcs analysis/runs/EXAMPLE/package
python mamey_run.py render-all-figures analysis/runs/EXAMPLE/package
python mamey_run.py emit-modeb-template --help
python mamey_run.py verify-modeb --help
```

`verify-modeb` takes the authored Markdown file as a positional argument. For a package-bound review,
also supply `--package` and the reconciled `--bgc` selector; `--interp` adds the interpretation check
and does not replace structural, claim-safety or quality review. A package path alone does not
identify an authored card.

The [tools reference](../user_guides/tools_reference.md) and
[command catalog](../COMMAND_CATALOG.generated.md) cover cohort ledgers, comparator coverage,
AF dossiers, Good Guesses, document export, locus maps and advisory helpers; check each one's
dependency, output and sign-off requirements. For release work, use the
[cut protocol](../../CUT_PROTOCOL.md); historical notes in the [changelog](../../CHANGELOG.md)
do not replace current operating instructions.
