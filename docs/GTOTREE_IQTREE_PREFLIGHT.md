# GToTree / IQ-TREE preflight contract

`tools/plan_gtotree_iqtree.py` is a planning and reconciliation tool. It never starts a phylogeny and
never downloads references. It writes one checksummed plan that a person approves before any CPU is used.

## Supported local interface

The planner was written against:

- GToTree 1.8.16 (`GToTree -v`, `GToTree -h`), where `-n` defaulted to 2 HMM-search CPUs, `-M`
  to 5 MUSCLE threads, and `-j` to one concurrent job. 1.8.16 is now refused: 1.8.19 is the production
  version and 2.0.x is admitted ([GTOTREE_WORKFLOW.md](GTOTREE_WORKFLOW.md)). Check `GToTree -h` for the
  installed version's defaults;
- IQ-TREE 3.1.2 for macOS ARM64, where `-T` controls cores/threads and defaults to one.

The planner checks the installed help for the exact options it will use. A missing option creates `HOLD_TOOL_INTERFACE_REVIEW`; it does not silently run a guessed command.
IQ-TREE is resolved from an explicit path first, otherwise `iqtree3`, `iqtree2`, then `iqtree`.
The planner and runner share `tools/_gtotree_versions.py`: v1 probes `-h` and emits `-n`; v2 probes
`-s` and omits `-n`. A v2 run also needs its reviewed runtime profile.
See [companion run contracts](COMPANION_RUN_CONTRACTS.md).

## Canonical tool chain

The tools run in this order:

1. `rank_clusterblast_phylo_candidates.py` creates an assembly-candidate ledger from the raw
   ClusterBlast channel. It neither downloads nor asserts organism identity.
2. A curator resolves eligible nucleotide accessions to versioned GCA/GCF assemblies and supplies
   any type-strain or outgroup status. Network retrieval remains a separately approved action.
3. `build_phylo_panel.py` selects and stages exactly 20, 40 (default), 60, or another explicit size
   through 60, retains selected distinct-content focal queries, enforces one outgroup, and admits up to three linked
   references plus up to two type anchors per query, with at most four comparators per query in all. It writes
   `panel_selected.tsv` plus `panel_receipt.json`. `select_panel` in `tools/build_phylo_panel.py` admits the
   anchors, and `read_prepared_panel` in `tools/plan_gtotree_iqtree.py` re-checks both caps.
4. `plan_gtotree_iqtree.py plan --prepared-panel ...` revalidates that staged panel, freezes the HMM
   set and tool/resource interface, and creates the immutable approval handoff.

The panel selector is authoritative for membership. The run planner does not independently re-rank
an already prepared panel. Manual `--panel-tsv` ingress remains available for recovery, but requires
the same single-outgroup and cap guards.

`prepare_biosynthetic_tree_inputs.py` is a separate PKS/RiPP evolutionary track. It must never be
fed into the organismal GToTree panel or treated as a substitute for a species tree.

## Hard safety and scale limits

- Default total panel cap: 40 unique normalized assemblies.
- User-selectable total cap: 3–60; 60 is a hard maximum for this workflow.
- Reference cap: user-selectable one, two, or three ranked references per focal query; default three.
- Default GToTree v1 plan: `-j 1 -n 1 -M 1 -N -k`.
- Default IQ-TREE plan: `-T 1` with a fixed recorded seed.
- `--threads-per-tree` can be 1–4, no larger than `--max-concurrent-cores`.
  The planner records concurrent trees as integer division of the core ceiling by
  threads per tree. This is planned resource accounting; it does not launch a dispatcher.
- Default and hard total core ceiling: four. Bind any non-default per-tree budget
  to the user's actual authorization.
- `-F`, IQ-TREE `--redo`, background fan-out, network downloads, and automatic accession fetching are
  absent from the generated command.

The planner stages local FASTA bytes source-preservingly as content-addressed objects. For an
antiSMASH ZIP it reads only the explicitly named whole-genome FASTA member, hashes both archive and
member, and never edits the archive. Region GBKs are not organismal-tree inputs.

## Assembly de-replication

Every assembly gets two hashes:

1. byte SHA-256 of the original FASTA or ZIP member;
2. normalized assembly SHA-256 over upper-cased nucleotide sequences sorted independently of FASTA
   headers and contig order.

The normalized hash is the de-replication key. The first admitted record owns the content object;
later aliases are written to `qa/DUPLICATES.tsv`. A duplicate reference is excluded but remains
traceable to the kept assembly. A duplicate focal query places the run on
`HOLD_DUPLICATE_QUERY_REVIEW` because sample mix-up or contamination must be reconciled rather than
silently collapsed. Identical 16S alone is not an assembly duplicate.

The panel builder already collapses equal-content queries before this step; see
[panel selection](GTOTREE_PANEL_SELECTION.md#exact-content-duplicate-guard).

## Immutable plan layout

```text
phylogenomics_workspace/
  CURRENT_RUN.txt
  runs/<run-id>/
    RUN_MANIFEST.json
    RUN_STATE.json
    COMMAND.sh
    EVENTS.jsonl
    HANDOFF.md
    input_objects/<normalized-sha256>.fna
    input_view/genomes.txt
    input_view/labels.tsv
    references/REFERENCE_SELECTION.tsv
    logs/
    outputs/
    qa/DUPLICATES.tsv
```

`RUN_MANIFEST.json` is created once with exclusive file creation. Reusing an existing run ID is an
error. `RUN_STATE.json` begins at `PLANNED_AWAITING_APPROVAL` or a specific HOLD. The current pointer is
created only when absent, so planning a second run cannot silently steal ownership from an active one.
The manifest records source hashes, assembly hashes and sizes, selected cap, reference rule, HMM hash
and profile count, resolved binaries, observed versions/help contract, and core ceiling.

## Approval boundary

Show the user the manifest summary and use matching existing approval, or obtain
explicit approval when the operation is not already authorized. The direct legacy
`COMMAND.sh` recipe only **comments** that `RUN_STATE` must record APPROVED; that recipe
does not read the state file. The governed 2.0.0 recipe instead delegates to
`run_planned_tree.py --plan-dir ...`, requires an explicit `--approved` argument and fresh
runtime probe directory, and checks `approved=true` plus the matching run ID and bound
inputs/mapping/tool/resource/HMM data. The planner has no approve subcommand. Preserve
the actual user approval in the handoff/state; a flag or script does not grant authority.
Reference downloads require a separate network approval. The direct recipe intentionally contains
`<DISCOVERED_ALIGNMENT_PATH>` for IQ-TREE: GToTree must exit zero and its real alignment must be
discovered and hashed before that command can be completed. The governed runner has its own
alignment discovery and completion checks; it does not use that manual placeholder.

After GToTree, use `discover`. It derives the retained taxon count from the unique
`Genomes_summary_info.tsv`, inventories all observed files, excludes individual-marker alignments from
final-alignment nomination, and returns PASS only for one root-level FASTA with the retained
denominator. This avoids depending on a version-specific filename.

## Claim ceiling

The result supports placement within the sampled panel. It does not establish species identity,
strain identity, formal taxonomy, contamination, biological activity, BGC product identity, or
production. Report proposed, admitted, duplicate-excluded, retained, and tree-tip denominators
separately. BGC content may annotate a tree but does not become an organismal-tree character unless a
separate analysis explicitly says so.
