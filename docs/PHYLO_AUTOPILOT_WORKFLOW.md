# Phylogenetic autopilot: 16S routing, placement and genome trees

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
Pass its absolute prefix through `--db`, or set it once for every tool as the
[local 16S database guide](LOCAL_16S_DATABASE.md) describes. A database in a developer workspace
is not a shipped product dependency. Reference titles and accessions must support the selected routing workflow.

Placement requires the external alignment/placement toolchain, including EPA-ng and its reference
preparation tools. Genome inference requires GToTree and IQ-TREE; optional ANI requires its own
binary and genome inputs. Check `doctor --companions` and the selected command's preflight before
running. Python package installation alone does not provision these databases or environments.

## Commands

### 1. `plan` — what did I upload?  (no ML, no network)
```
python tools/phylo_autopilot.py plan <uploads_dir>
```
Classifies discovered FASTA files as `rrna`, `genome`, `protein`, or `empty`. It first
checks protein-only symbols in the first five records, then assigns `genome` when the longest
record is at least 10,000 bases or total sequence length is at least 500,000. Otherwise, all
records at most 5,000 bases are routed as `rrna`; this is a heuristic, not marker identification.
A sufficiently large multi-FASTA of short 16S records can therefore be classified as `genome`.
Inspect the actual sequences and do not treat classification as assembly or 16S validation.

### 2. `route` — assign a genus and route every 16S  (BLAST, no ML)
```
python tools/phylo_autopilot.py route --query all_16S.fasta \
    --db /absolute/path/to/16S_database_prefix --out routing_table.tsv
```
Writes a routing table (`query, tophit_genus, pident, aln_len, routing_state, alternate_genera,
route_class, group, tophit_title, pident_raw`). `pident` is identity over unambiguous columns;
`pident_raw` is BLAST's own value. The search admits every database record as a subject, then ranks
hits at least 95% as long as the top BLAST alignment. A different-genus hit within 0.5 percentage points of the top identity and at least 95% of its aligned length is
recorded as `GENUS_CONFLICT` and is not automatically admitted to either reference group.
The command prints the per-class tally plus the reference genera each group will need. **Read this table
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
prepare local routing/QC tables, the selected reference accession list and reference/query
FASTAs, then stop before placement. The dry run still runs local `blastn` and `blastdbcmd`
and writes under `--outdir`.
Use a fresh, authorized output directory outside the code bundle. Reference selection is
by database title, definition screening and per-genus caps; it does not independently prove
that every selected record is type material. Bind supplied metadata before using `[Type]` labels.

## Whole-genome workflow

`phylo-run` is the released-v1 front door. It forwards selected tool/mapping and inference flags to the shared runner, but not the governed-v2 runtime/probe/plan controls. For the selected governed GToTree 2.0.0 route, retain the planner-generated `COMMAND.sh` and its exact manifest/state/runtime/resource bindings; that helper calls `run_planned_tree.py` with `--plan-dir`. Do not substitute the shorter front door for those bindings. See [companion run contracts](COMPANION_RUN_CONTRACTS.md).

Run `python mamey_run.py phylo-run --help` for the released-v1 genome list, work directory,
outgroup and compute settings. The `--approved` flag is required for execution. ANI is optional:
supply the corresponding reference/query genome lists if you need that comparison. The
`phylo-run` defaults are `--threads 4 --parallel 1`: 4 threads, one job at a time, which is the
house limit. Pass `--threads 1 --parallel 1 --iqtree-threads 1` only when you want a single-core
run. `phylo-run` always passes its `--parallel` value to the shared runner, so the runner's own
default does not apply. `phylo-run` writes `run_status.json` in its workdir
and does not automatically update the planner's `RUN_STATE.json`; reconcile both records
with the same bound inputs and actual output paths. A tree alone
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

## Requested-stage completion

The planned tree runner refuses absent or unloadable mandatory tree QC gates. An explicitly requested fastANI stage must complete successfully and create its current output before the overall run can report DONE. Missing executable, nonzero exit or missing output returns a typed FASTANI failure and exit 8, preserving core-tree artifacts and advertising no verified ANI table. A fresh attempt prevents an older table from masking failure; output existence and checksum do not independently validate ANI content or biological interpretation.

## Shell builder retention

`tools/build_tree.sh` binds the staged genome bytes, tip labels and TREE_SPEC.json
before GToTree. Extra arguments cannot replace its input list or output path.
The shared retention gate runs before IQ-TREE and again against the supported
final Newick tree; query loss, unexpected tips, missing gates and changed input
bytes return nonzero. `tree_input_binding.json`, `tree_retention_status.json` and
`DROPPED_BY_QC.tsv` retain the execution evidence. Only a literal
`"allow_reference_drop": true` in the bound TREE_SPEC permits recorded reference
drops; declared queries must remain. These checks establish execution identity
and roster retention, without adopting a scientific interpretation.
