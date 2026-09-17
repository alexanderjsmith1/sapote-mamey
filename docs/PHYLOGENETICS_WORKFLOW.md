# Phylogenetics workflow

## Start here: choose the sequence route

Sapote-Mamey supports three related routes. **16S placement** uses EPA-ng to place a query 16S sequence onto a prepared reference backbone. **Five-locus MLSA** uses the protein-coding genes `atpD`, `gyrB`, `recA`, `rpoB`, and `trpB` as a quicker screen for selecting related genomes. **Core-genome inference** uses GToTree marker alignments and IQ-TREE for the selected genome panel. These analyses answer different questions; an MLSA screen can guide the genome panel but does not replace the 16S or core-genome tree.

**You can start from an antiSMASH ZIP.** Many antiSMASH result ZIPs contain the full assembly FASTA, but some contain only region-level records. Check which is present. If a full assembly is available, the optional `phylo-mlsa` route can plan, stage, and run a five-locus screen from that ZIP and a separately chosen set of local reference genomes. You may also supply genome FASTA files directly to the established MLSA and GToTree workflows. Reference genomes can be retrieved from online sources when access is permitted, but the bundled MLSA tool does not select or download them automatically. Retain their accession, source, retrieval date, and sequence hash.

For 16S, supply an existing 16S FASTA or extract candidate 16S spans from an assembled genome. The bundled `tools/phylo_16s_from_genome.py` uses BLASTn against a specified 16S reference database, groups nearby matches, and writes candidate spans with an extraction receipt. These are **candidates**, not validated rRNA gene boundaries. Check orientation, length, and identity before alignment and EPA-ng placement. A curated NCBI or other 16S reference set can support this route when its sequence and metadata provenance are recorded.

In our larger genome panels, a productive sequence has been: gather a broad reference set, run the comparatively fast five-locus MLSA screen, select a smaller informative panel, then run GToTree and IQ-TREE. The latter steps can consume substantial CPU time; an agent can prepare other work while an approved job runs. Record the actual companion-tool versions and resources used. IQ-TREE performs tree inference after alignment, while R/ggtree renders the resulting figure; these are separate steps.

Start with the sequences, trees, and metadata you already have. A tree can be reviewed without rebuilding it, but a PDF alone does not establish which sequences were inferred, which tips were removed for display, or whether its labels are correct. Record those links before calling a figure complete.

Prepare tip metadata early. GenBank or NCBI records may lack isolation source or geographic location, so check the exact accession against the original publication, abstract, BacDive, or a culture collection where necessary. An agent with access to those sources can help gather evidence, but every display category must remain traceable to its raw source. Bioassay and Sapote-Mamey heatmap tracks can be joined to EPA-ng or GToTree displays through an explicit tip-to-strain mapping. BGC and genome tracks generally need the corresponding antiSMASH and assembly evidence.

Where the input metadata and renderer support them, make companion views: a concise publication view and a more detailed view that shows isolation source or internal experiment/sample identifiers. These can reveal sampling patterns for review; a visual pattern alone does not establish host or geographic specificity. Keep the editable R script, tree and metadata beside the rendered PDF/PNG so you can adjust labels and layout in R/ggtree without reinferring the tree.

The three routes at a glance:

| Question | Input and method | What the tree can support |
|---|---|---|
| Where does a query 16S sequence fall relative to a reference backbone? | Aligned 16S references, a reference tree, query 16S sequences, and EPA-ng placement | A 16S clade or neighborhood, with placement support where available. It does not establish a species identity. |
| Which genomes should we compare more deeply? | Full assembly FASTAs, a declared reference set, and a five-locus MLSA screen | A fast comparator topology and a reasoned candidate panel for the later core-genome run. It is not species delimitation. |
| How do assembled genomes relate? | A declared set of genomes, a single-copy-marker alignment, and GToTree/IQ-TREE inference | A core-genome topology for the genomes actually included. Species delimitation needs separate genome comparisons such as ANI. |

Do not compare tip counts across these methods as if they were successive versions of one tree. Do not put a 16S query onto a protein-marker GToTree backbone. An MLSA screen is an optional way to choose genome comparators; it is not a prerequisite for reviewing an existing EPA-ng or GToTree result.

## Review an existing tree before rebuilding it

Make one record per **tree version**, including superseded versions. Keep its exact paths and SHA-256 values. A review record should answer:

1. **Analysis:** Which alignment or sequence roster produced the analysis Newick? What marker set, inference tool and version, model, support calculation, and outgroup were used? If the alignment or log is absent, mark that part *unbound* rather than reconstructing it from a PDF.
2. **Tips:** Parse the Newick tips and join them by exact tip ID to metadata. Record unmatched, duplicate, and metadata-only IDs. Keep accession versions; a similar name or accession stem is not an identity match.
3. **Provenance:** For every reference, retain its accession, sequence hash when available, organism name as deposited, type-status evidence, source/geography evidence, and the source record or URL. Query strain and biological-sample identities must come from the project's own governed table.
4. **Display:** Identify the actual Newick used for the PDF. Compare its tips with the full analysis tree and record each excluded tip and reason. A display omission is not an absent placement. A folder called “final” or “validated” is a review lead, not a substitute for these checks.
5. **Figure:** Check that every visible label and metadata strip has a matching row; the caption or Methods block **at the bottom of the figure** must name the method, inputs, reference policy, outgroup, support, displayed tip count, exclusions, and metadata source. Include the complete tree and display ledger beside the figure.

Use status terms that describe the evidence: `ANALYSIS_BOUND`, `SEQUENCE_UNBOUND`, `METADATA_HOLD`, `DISPLAY_SUBSET`, `SUPERSEDED`, and `READY_FOR_OWNER_REVIEW`. A mechanically complete record is not scientific or publication acceptance.

### Full tree and display tree

EPA-ng reports may contain a full grafted placement tree and a smaller `tree_display.newick` used by a colour-strip PDF. List **both** query rosters. A focused display must say which queries it omits. The strict prepared-series contract in [Tree Catalog](TREE_CATALOG.md) requires preservation of all declared queries; an older pruned figure that omits queries does not become a complete all-query series merely because its PDF renders. Rebuild the display with the queries retained, or prepare an explicitly scoped spotlight analysis and keep its full-context companion.

For GToTree, an inferred `.treefile`, a `.contree`, an aligned single-copy-gene FASTA, and a PDF may represent different stages. Check exact sequence/tree tip agreement where the alignment is available. A renderer may prune a duplicate reference accession while retaining the source analysis tree; record the exclusion and use the **displayed** count in the figure caption. Do not delete or relabel the source tree to make the count agree.

### Resolve missing metadata

Search by the exact versioned accession in an authoritative sequence or assembly record. Save the raw field, source URL or accession, retrieval date, and any transformation to a display category. `Not recorded` in a source is missing evidence, not a negative habitat or geographic observation. Do not fill a gap from a species-level generalization or a near-matching strain. If a reference cannot be resolved, keep the hold or exclude that reference upstream with a ledger; do not remove an owner query merely to make a figure pass. The prepared display series refuses missing source/geography categories for visible tips; see [Tree Catalog](TREE_CATALOG.md).

## Build a new tree when the existing evidence cannot answer the question

**16S route.** Inventory files with `python tools/phylo_autopilot.py plan INPUT_DIR`. Route sequences with `python tools/phylo_autopilot.py route --query QUERIES.fasta --db DB_PREFIX --out ROUTING.tsv`, then review genus conflicts. `run-16s --dry-run` prepares a reference/query plan without inference. A real run requires its `--approved-by` argument. The [autopilot guide](PHYLO_AUTOPILOT_WORKFLOW.md) and [16S data contract](PHYLO_16S_DATA_CONTRACT.md) describe sequence admission, reference evidence, and the EPA-ng outputs. `phylo_place.py report` can write a grafted tree without the required colour-strip figure if owner or reference metadata is missing; inspect `COLOR_STRIPS_NOT_RENDERED.txt` rather than treating the absence as success.

If you have a genome assembly but no 16S FASTA, first inspect candidate spans:

```bash
python tools/phylo_16s_from_genome.py genome.fna \
  --blastdb /path/to/curated_16s_db --out candidate_16s.fasta
```

This uses local BLASTn and the specified database. Review its receipt and sequence before treating a span as a 16S query.

**Optional MLSA screen.** A full-assembly antiSMASH ZIP can be checked without starting inference:

```bash
python mamey_run.py phylo-mlsa --input-zip antismash_results.zip \
  --query-label QUERY_A --mode plan
```

To run the five-locus screen, provide a curated directory of local `.fna` reference genomes, including one filename marked `_OUTGROUP`, and a new output directory. Use `--mode prepare` to stage and review the inputs or `--mode run` to invoke `build_mlsa.py`. The latter needs Prodigal, BLAST+, MUSCLE, and IQ-TREE. A ZIP containing only clipped region records is refused. See the [Quick Guide](GUIDE/02_Quick_Guide.md#trees-and-heatmap-overlays) and [GToTree workflow](GTOTREE_WORKFLOW.md) for panel selection after the screen.

**Genome route.** Start with an explicit genome list, comparator rationale, outgroup, and space-free work directory. `python mamey_run.py phylo-run --help` shows the current executable interface; `--approved` records authorization for the CPU run. GToTree, IQ-TREE, and optional fastANI are external companions, not included databases. The [GToTree execution guide](GTOTREE_WORKFLOW.md) and [preflight](GTOTREE_IQTREE_PREFLIGHT.md) describe the more detailed controlled route. Record the actual installed GToTree marker set and IQ-TREE settings for each tree; versions or marker sets must not be silently relabelled to match another figure.

Use a declared outgroup appropriate to the taxonomic scope and check the resulting root. `tools/signoff_check.py` is **advisory**; its process exit does not certify a tree. Keep preflight, branch/sanity checks, alignment completeness, support, ANI if run, and human review as separate receipts. A tree alone does not establish a new species, genus, compound, or bioactivity.

## Deliver one reviewable figure packet

For each selected figure, retain the source analysis tree; alignment or a typed absence statement; exact tip/sequence and tip/metadata joins; reference-accession provenance; display Newick and exclusions; figure PDF/PNG; Methods caption; tool versions; and hashes. Prefer a review index that can point to multiple versions while identifying superseded ones. Do not overwrite an earlier figure to hide why the roster or metadata changed.

The [tree display receipts](TREE_DISPLAY_RECEIPTS.md) explain reproducible pruning. The [Tree Catalog](TREE_CATALOG.md) gives the stricter prepared-series contract. [Species and BGC tree comparison](SPECIES_VS_BGC_TREE_COMPARISON.md) explains why a BGC overlay is an annotation track rather than an organismal phylogeny.
