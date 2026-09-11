# Phylogenetic autopilot — upload 16S and/or genomes, get gated trees

`phylo-autopilot` inventories sequence uploads and provides 16S routing and placement commands.
Use `phylo-run` for the approved genome workflow. Tree inference, evidence review, and rendering
are distinct stages; inspect their outputs before treating a figure as finished.

Start with the [user walkthrough](GUIDE/02_Quick_Guide.md#trees-and-heatmap-overlays), which also
covers strain-level heatmap overlays. The executable tools are `tools/phylo_autopilot.py`,
`tools/run_planned_tree.py`, and the existing placement and Figure Factory renderers.

## Choose the sequence route

Use `plan` to inventory an upload directory. It classifies sequences for routing; it does not
execute a genome tree. Use `route` to search 16S queries against your local reference database,
then inspect the proposed genus/group and any flagged or off-target results. Resolve a questionable
assignment before putting that query on a reference backbone.

For whole-genome FASTA, use `phylo-run` with an explicit genome list, outgroup, and output directory.
It delegates to the GToTree/IQ-TREE workflow. A genome upload identified by `plan` is not an
already completed genome analysis.

## Install / prerequisites

Provide BLAST+ (`blastn`, `blastdbcmd`) and a suitable local 16S nucleotide database for routing.
Pass its absolute prefix through `--db`; a database in a developer workspace is not a shipped
product dependency. Reference titles and accessions must support the selected routing workflow.

Placement requires the external alignment/placement toolchain, including EPA-ng and its reference
preparation tools. Genome inference requires GToTree and IQ-TREE; optional ANI requires its own
binary and genome inputs. Check `doctor --companions` and the selected command's preflight before
running. Python package installation alone does not provision these databases or environments.

## Commands

### 1. `plan` — what did I upload?  (no ML, no network)
```
python tools/phylo_autopilot.py plan <uploads_dir>
```
Classifies every FASTA under the directory as `rrna`, `genome`, or `protein`. Classification is by
sequence **length**, so a single multi-FASTA of many 16S sequences (one per strain) is correctly
`rrna`, never mistaken for a genome.

### 2. `route` — assign a genus and route every 16S  (BLAST, no ML)
```
python tools/phylo_autopilot.py route --query all_16S.fasta \
    --db /absolute/path/to/16S_database_prefix --out routing_table.tsv
```
Writes a routing table (`query, tophit_genus, pident, aln_len, routing_state, alternate_genera,
route_class, group, tophit_title`). Up to five ranked hits are retained during routing. A different-
genus hit within 0.5 percentage points of the top identity and at least 95% of its aligned length is
recorded as `GENUS_CONFLICT` and is not automatically admitted to either reference group.
and prints the per-class tally plus the reference genera each group will need. **Read this table
before building anything** — it is where you catch a contaminant or a mis-sort.

### 3. `run-16s` — build the gated tree for one group  (auto-reference → phylo_place)
```
python tools/phylo_autopilot.py run-16s --query all_16S.fasta \
    --db .../16S_ribosomal_RNA --group rare_genera --outdir runs/rare_genera \
    --approved-by "<who authorized this tree>"
```
Routes, subsets the query to that group, auto-builds the reference (type strains for exactly the
observed genera, plus a few sentinels + a distant outgroup, pulled from the DB), then shells
`phylo_place all`. **`--approved-by` is required** — without it the command refuses and tells you to
use `--dry-run`. This is the standing **tree-approval gate**; the autopilot never bypasses it, and
the heavy ML still runs inside `phylo_place`, which enforces the gate itself. Use `--dry-run` to
produce the reference + query FASTAs and stop, so you can inspect them before committing compute.

## Whole-genome workflow

Run `python mamey_run.py phylo-run --help` to prepare the genome list, space-free work directory,
outgroup, and compute settings. The `--approved` flag is required for execution. ANI is optional:
supply the corresponding reference/query genome lists if you need that comparison. A tree alone
does not provide ANI or a species identification.

## Review and annotate the results

Retain the inferred tree, alignment, input/reference rosters, outgroup decision, tool versions,
and actual sanity/sign-off results. Review support and branch lengths before preparing a final
figure. Keep the full inference panel recorded even when the display uses a smaller roster.

For metadata views, supply the source of host, location, and accession fields and check their tip
mapping. A private project registry is not part of the portable program's bundled data.

For strain-level heatmaps beside an existing tree, use `tools/tree_bgc_overlay.py` with an explicit
config. Its ANI, BGC, domain, Mode B, and assembly tracks come from supplied annotation data and
an exact tip-to-strain crosswalk. See [trees and heatmap overlays](GUIDE/02_Quick_Guide.md#trees-and-heatmap-overlays).
Tree placement does not calculate those annotations, and an overlay does not change the topology.

Routing tables and prepared reference/query FASTAs are written to the selected output locations;
`run-16s` delegates placement beneath its output directory. Read the emitted paths and command
receipts, including partial or failed stages. Keep the tree, overlays, source data, and methods
sidecars together in your project.

## Source and subprocess checks

A failed external command is an execution failure, not zero hits, absent loci, or a clean assembly.
Preserve its exit code and diagnostic output. Some BLAST installations reject paths containing
spaces; successful path staging requires the database prefix and all referenced volume files,
as well as query and subject inputs. Do not infer success from an empty output file.

When an outgroup changes, reconcile its taxon, marker accession, genome accession, source path,
and selection receipt as one record. A 16S selection does not by itself select a genome outgroup.
Keep marker-specific rulings separate until the corresponding source and scope are verified.
For source lookup, preserve accession versions and use verified paired-accession records rather
than treating a shared numeric body or name similarity as proof of identity.
