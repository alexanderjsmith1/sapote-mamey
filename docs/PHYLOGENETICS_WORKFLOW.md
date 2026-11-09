# Phylogenetics workflow

Read this page before any tree task. It tells you which route to use and what to check before you call a tree finished. Terms are in the [glossary](GLOSSARY.md).

## Choose a route

| Question | Route | Input | What the tree supports |
|---|---|---|---|
| Where does a query 16S sequence fall among references? | **16S placement.** EPA-ng places the query onto a prepared reference tree. | Aligned 16S references, a reference tree, query 16S FASTA | A 16S clade or neighborhood. It does not establish a species. |
| Which genomes should we compare more deeply? | **Five-locus MLSA** (multilocus sequence analysis). A quick tree from `atpD`, `gyrB`, `recA`, `rpoB` and `trpB`. | Full assembly FASTAs and a declared reference set | A fast comparator topology and a candidate panel. It is not species delimitation. |
| How do whole genomes relate? | **Core-genome tree.** GToTree aligns single-copy marker genes. IQ-TREE infers the tree. | A declared set of genomes with an outgroup | A topology for the genomes included. Species delimitation needs a separate genome comparison such as ANI. |

Do not compare tip counts across routes as if they were versions of one tree. Do not place a 16S query on a protein-marker GToTree tree. The MLSA screen is optional. You do not need it to review an existing tree.

An outgroup is a distant genome that fixes the root. A tip is one leaf of the tree.

CPU-heavy steps (EPA-ng placement, IQ-TREE) need explicit approval. Heavy jobs run `nice -n 15`, one build at a time, at most 4 threads.

## Review an existing tree before rebuilding it

Start with the sequences, trees and metadata you already have. A PDF alone does not show which sequences were inferred, which tips were removed for display, or whether the labels are right.

Keep one record per tree version, including superseded versions, with exact paths and SHA-256 values. Each record answers five questions.

1. **Analysis.** Which alignment or sequence list produced the analysis Newick? Which markers, inference tool and version, model, support calculation and outgroup? If the alignment or log is missing, mark that part unbound. Do not reconstruct it from a PDF.
2. **Tips.** Join the Newick tips to metadata by exact tip ID. List unmatched, duplicate and metadata-only IDs. Keep accession versions. A similar name or accession stem is not a match.
3. **Provenance.** For each reference keep the accession, sequence hash if you have it, organism name as deposited, type-status evidence, source and geography evidence, and the source record. Query strain and sample identities come from your own governed table.
4. **Display.** Find the Newick that drew the PDF. Compare its tips with the full analysis tree and record each excluded tip and why. A display omission is not an absent placement. A folder called "final" is a lead, not proof.
5. **Figure.** Every visible label and metadata strip needs a matching row. The caption names the method, inputs, reference policy, outgroup, support, displayed tip count, exclusions and metadata source. Keep the complete tree and the display list beside the figure.

These record labels are yours; no tool emits them. A complete record is not scientific or publication acceptance.

### Full tree and display tree

EPA-ng reports can hold a full grafted placement tree and a smaller `tree_display.newick` used by a color-strip PDF. List both query lists. A display must say which queries it omits. The prepared-series rules in [Tree Catalog](TREE_CATALOG.md) require all declared queries to be kept. Rebuild the display with the queries retained, or prepare a clearly scoped spotlight and keep the full companion.

### A finished IQ-TREE build

An IQ-TREE build is complete only when all three hold:

- the `.contree` exists;
- the `.treefile` carries support labels;
- the log says "Total wall-clock time".

A `.treefile` without those is not a finished run. The launchers stop, with route-specific messages:

- `tools/build_tree.sh` prints `IQ-TREE run is INTERRUPTED (needs iqtree.contree + support labels + 'Total wall-clock time')` and exits 1;
- `tools/gtotree_execution_gate.py --check-completion PREFIX` logs a JSON status (`INTERRUPTED` or `MISSING`) with its reasons, and exits 1;
- `tools/build_mlsa.py` and the domain-tree builder stop with `IQTREE_INCOMPLETE` and the same reasons.

The reasons list what is missing, not why. Do not render or publish the tree. Keep the folder, find the cause, and re-run to completion.

A renderer may drop a duplicate reference accession from the display and keep the source tree. Record the exclusion and use the displayed count in the caption. Never delete or relabel the source tree to make the count agree.

### Resolve missing metadata

Search by the exact versioned accession in an authoritative sequence or assembly record. Save the raw field, the source URL or accession, the retrieval date, and any step that turned the raw text into a display category. "Not recorded" means missing evidence, not a negative observation. Do not fill a gap from a species-level generalization or a near-matching strain. If a reference cannot be resolved, keep the hold, or exclude it upstream and list it. Do not drop a query just to make a figure pass. The prepared display series refuses visible tips with no source or geography; see [Tree Catalog](TREE_CATALOG.md).

Make two views if the metadata allows it: a short publication view and a detailed view with isolation source and sample IDs. A visual pattern alone does not show host or geographic specificity. Keep the R script, tree and metadata beside the PDF so you can change labels without re-inferring the tree.

## Build a new tree

### 16S route

1. Inventory your inputs: `python tools/phylo_autopilot.py plan INPUT_DIR`. It classifies each file as rRNA, genome, protein or empty.
2. Route the queries to a genus group: `python tools/phylo_autopilot.py route --query QUERIES.fasta --db DB_PREFIX --out ROUTING.tsv`. Review any genus conflict by hand.
3. Prepare one group without running inference:

```bash
python tools/phylo_autopilot.py run-16s --query QUERIES.fasta --db DB_PREFIX \
  --group streptomyces --outdir NEW_OUTDIR --dry-run
```

`--group` is one of `nocardia`, `rare_genera` or `streptomyces`. `--db` defaults to the shared 16S database ([LOCAL_16S_DATABASE.md](LOCAL_16S_DATABASE.md)). The dry run writes into `NEW_OUTDIR`: `query_qc.tsv`, `routing_table.tsv`, `<group>_reference.fasta` and `<group>_query.fasta`. It prints `dry-run:` and exits 0. It exits 2 in two cases. If a query is refused, it says how many and tells you to read `query_qc.tsv`. If no query routes to your group, it names the groups that did get queries and tells you to read `routing_table.tsv`. It runs BLAST but no tree inference.

4. A real run needs `--approved-by NAME` instead of `--dry-run`. Without either flag it refuses. Details are in the [autopilot guide](PHYLO_AUTOPILOT_WORKFLOW.md); sequence admission is in the [16S data guide](PHYLO_16S_DATA_CONTRACT.md).

`phylo_place.py report` can write a grafted tree without the color-strip figure when the owner table or reference metadata is missing. It then writes `<group>_REPORT_ATTEMPT.json` in the report folder with state `HOLD` and a `metadata_strips` entry that gives the reason. It exits 2. Do not treat a missing strip figure as success.

If you have a genome but no 16S FASTA, extract candidates first:

```bash
python tools/phylo_16s_from_genome.py genome.fna \
  --blastdb /path/to/curated_16s_db --out candidate_16s.fasta
```

This runs local BLASTn and writes candidate spans with a receipt. They are candidates, not validated rRNA boundaries. Check orientation, length and identity before alignment and placement. To build the 16S database, see [LOCAL_16S_DATABASE.md](LOCAL_16S_DATABASE.md).

### How identity is measured

For nearest-reference selection and genus-conflict review, 16S identity is measured over alignment
columns where both sequences contain A, C, G, T or a gap. IUPAC ambiguity columns are excluded;
gaps remain differences. Raw BLAST `pident` is a separate measurement. The routing table retains
it as `pident_raw`; legacy imported hit tables without aligned sequences can only supply raw identity.
The genome-neighbor panel records the identity basis beside its selected value.

Local nearest-record searches set the subject limit to the database record count, or the exact
number of candidates in a locally constructed panel database. The requested number of output
references is applied after ranking. Genus routing ranks alignments at least 95 percent as long
as the original top BLAST alignment; the named reference picker and local marker selector compare
alignments at least 95 percent as long as the longest eligible alignment for that query. This keeps
short perfect fragments from displacing long 16S evidence. Some tools use an 85 percent raw-identity floor to limit output
and retry without it when a query has no eligible hit. That floor can still exclude an ambiguity-rich
record when another record passes; all-record subject capacity is not an exhaustive alignment guarantee.
A failed database-count probe uses a finite fallback where supported, so retain the actual count and
search settings in the run evidence. A partial database establishes proximity only within that subset.
See [How identity is measured in the local database guide](LOCAL_16S_DATABASE.md#how-identity-is-measured)
for the shared rule and reporting fields. These measurements support reference selection, not species
identification or scientific adoption.

### Optional MLSA screen

Check an antiSMASH ZIP without starting inference:

```bash
python mamey_run.py phylo-mlsa --input-zip antismash_results.zip \
  --query-label QUERY_A --mode plan
```

The ZIP must hold a full assembly. A ZIP with only clipped region records is refused. `--mode plan` reads the ZIP and reports what it found. To go on, give `--references-dir` (a folder of local `.fna` reference genomes, one filename containing `_OUTGROUP`) and `--outdir` (new or empty). `--mode prepare` stages and checks those inputs. `--mode run` runs `build_mlsa.py`, which needs Prodigal, BLAST+, MUSCLE and IQ-TREE. The tool does not choose or download references. Keep each reference's accession, source, retrieval date and sequence hash. See the [Quick Guide](GUIDE/02_Quick_Guide.md#trees-and-heatmap-overlays) and the [GToTree workflow](GTOTREE_WORKFLOW.md) for choosing a panel afterward.

### Genome route

Start with an explicit genome list, the reason for each comparator, an outgroup, and a work folder with no spaces in its path. `python mamey_run.py phylo-run --help` shows the interface. `--approved` records approval for the CPU run. GToTree, IQ-TREE and optional fastANI are external tools, not shipped. Use the [GToTree workflow](GTOTREE_WORKFLOW.md) and the [preflight](GTOTREE_IQTREE_PREFLIGHT.md) for the controlled route, and [companion run contracts](COMPANION_RUN_CONTRACTS.md) for the reviewed planner command. Record the marker set and IQ-TREE settings for each tree.

Use an outgroup that fits the taxonomic scope, and check the root. `tools/signoff_check.py` is advisory; its exit code does not certify a tree. Keep preflight, sanity checks, alignment completeness, support, ANI and human review as separate records. A tree alone does not establish a new species, genus, compound or bioactivity.

### Advisory tree sign-off check

Use explicit current artifact paths when requesting sign-off review:

```bash
python mamey_run.py signoff '<tree.treefile>'
```

The bundle CLI exposes files and `--minutes` only. Use the direct helper when
selection requires its additional options:

```bash
python tools/signoff_check.py --root '<review-root>' --outgroup '<declared-tip-token>' '<tree.treefile>'
```

The helper accepts repeated/comma-separated outgroup terms; recognizing a label
is not approval of outgroup choice. Without explicit files, it walks the selected
root for case-sensitive `.treefile` names modified in the last 90 minutes by
default. Hidden directories and its named environment/database/reference pruning
list are excluded; `SIGNOFF_PRUNE_DIRS` adds exclusions. This is a selected recent
file sweep, not the authoritative artifact roster or proof of current-run input
binding. Record the exact files, hashes, source/run identities, scan window and
exclusions separately. Use explicit paths for required older or pruned artifacts.

The report checks regex-extracted labels and support-like text rather than fully
validating Newick structure, every numeric measurement or provenance. It does not
read ANI data, validate comparator downloads or make biological sign-off decisions.
Those are independent review requirements. No structured receipt or report file
is saved by the helper; retain console diagnostics with the selected input hashes.

Valid advisory invocations return 0 for issues, read failures, an incomplete walk
and no selected files. `--quiet-if-clean` can suppress the no-selection message or
caution notes when no issues were found. Silence is not a completed clean review.
The direct helper parses its options with argparse. `--help` prints usage and
exits 0. An unknown option, a missing value or a non-numeric `--minutes` exits 2.
Do not use its exit alone for input admission or completion. The bundle CLI has
its own parser and does not offer these extra helper options.

## Deliver one reviewable figure packet

Keep, for each figure: the source analysis tree; the alignment (or a statement that none exists); the tip-to-sequence and tip-to-metadata joins; reference provenance; the display Newick and exclusions; the PDF and PNG; the caption; tool versions; and hashes. Do not overwrite an earlier figure to hide a change in the tip list or metadata.

See [tree display receipts](TREE_DISPLAY_RECEIPTS.md) for reproducible pruning, [Tree Catalog](TREE_CATALOG.md) for the prepared series, and [species and BGC tree comparison](SPECIES_VS_BGC_TREE_COMPARISON.md) for why a BGC overlay is an annotation, not an organismal tree.
