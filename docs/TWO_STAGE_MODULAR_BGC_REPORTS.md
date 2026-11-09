# Two-stage modular BGC reports

This is an advanced, cohort-scale route for assembling many BGC reports from earlier reports and
other saved evidence. For one quick overview of one cluster, use [`report-card`](PER_BGC_REPORT_CARD_SPEC.md).
For one authored card, use the [Mode B walkthrough](MODE_B_USER_WALKTHROUGH.md).

Sapote-Mamey can reuse a large prior-report corpus without pretending that old
locators, rankings, BLASTP snapshots, or interpretations are current. The
report is assembled in two stages. Stage 1 builds **L0** drafts: the first,
locator-first layer of a report, made from existing evidence. Stage 2 checks and
promotes them one module at a time.

## Stage 1 — preliminary assembly

Stage 1 produces a useful internal report quickly. Its primary user locator is
the exact node or contig plus antiSMASH region. A historical `BGCnnn` value is
retained only as a source-scoped alias.

The stage can include:

- exact assembly, node, region, profile and sequence identity when available;
- exact gene, protein and domain inventory;
- exact profile-call records;
- channel-separated observed BLASTP rows with explicit receipt state;
- a hash-bound literature-atlas section carried over from an earlier report (see the
  [literature atlas refresh](LITERATURE_ATLAS_CURRENT_EVIDENCE_REFRESH.md)); and
- a hash-bound preliminary Mode B section.

### Run stage 1

```bash
python mamey_run.py build-bgc-drafts \
  --evidence-root-config sapote-evidence-roots.json \
  --source-manifest source-manifest.json \
  --program-spec program-specs/report-program.json
```

All three JSON files are required. The command does not create them. See the [portable evidence workspace](PORTABLE_EVIDENCE_WORKSPACE.md) for their formats. The output folder is named by the spec, and the command refuses to run if it already exists.

On success the command prints one JSON object with `"status": "DRAFT_BUILT_NOT_ACCEPTED_NOT_INTEGRATED"` and counts of reports and module states. The output folder holds:

- `REPORT_INDEX.tsv`: one row per locus, with its identity state and draft state;
- `REPORT_MODULE_STATUS.tsv`: each module's state, promotion gate and next required input;
- `COMPARATOR_EVIDENCE_LEDGER.tsv`: the comparator rows, one channel per row.

Prior prose is marked `PRELIMINARY_SOURCE_BOUND_NOT_VERIFIED`. Observed BLASTP
rows remain navigation evidence until submitted query bytes and database/run
receipts are bound. Missing channels are missingness, not biological absence.

## Stage 2 — verification and promotion

Stage 2 operates module by module. It does not require the entire report to be
rewritten whenever one database, assembly, or interpretation changes.

The promotion sequence has six steps. Only some have a command:

1. Bind MIBiG and KnownClusterBlast comparator rows. No separate command. Declare them as `comparator_sources` in the program spec and stage 1 writes them (see the [portable evidence workspace](PORTABLE_EVIDENCE_WORKSPACE.md)).
2. Bind ClusterBlast subjects and ordered locus topology. Same route as step 1.
3. Generate an exact editable locus and domain map. No stage 2 command does this. The [command catalog](COMMAND_CATALOG.generated.md) lists the map commands, such as `bgc-gene-map`.
4. Compare strict, relaxed and loose profiles across the same assembly and version. No command in this route. Do it by hand.
5. Mark each inherited paragraph retain, update, supersede, remap or hold. `attach-bgc-overlays` records the dispositions you supply. It does not decide them.
6. Run current Mode B verification on the authored card: `verify-modeb` (below).

A locus-tag match to the exact-region inventory is recorded as
`LOCUS_TAG_IN_EXACT_REGION_QUERY_BYTES_UNBOUND`. It is not proof that the exact submitted query was used.
The builder keeps each comparator channel in its own child table and in
`COMPARATOR_EVIDENCE_LEDGER.tsv`. It never merges them. Source coverage above 100% stays in the raw column and is
kept out of the usable-coverage column.

`REPORT_MODULE_STATUS.tsv` and the per-locus `report_module_status.tsv` table give each
module's state, promotion gate and next required tool or input. They have no source-hash
column. Source hashes are in separate ledgers, and only for modules that have a source:
`EVIDENCE_MODULE_LEDGER.tsv` (`source_sha256`, `module_sha256` and `bridge_source_sha256` for
attached prior modules), `COMPARATOR_EVIDENCE_LEDGER.tsv` (`source_sha256` per comparator row),
and the per-locus `exact_gene_domain_inventory.tsv` and `exact_region_profile_calls.tsv`
(protein, archive and assembly hashes). A module in state `QUEUED_NOT_YET_ASSEMBLED` or a hold
state has no source and no hash; treat it as unbound.

### Run the stage 2 overlay

`attach-bgc-overlays` adds reviewed paragraphs beside a stage 1 folder; it writes nothing into it.
`--out` must be a new folder outside `--base-report-root` and `--review-root`, and not under any
input file path; a nested `--out` is refused before anything is written. The command builds in a
staging folder `.<out-name>.staging-<process-id>` next to `--out`. If that staging path already
exists, the command stops and leaves it in place for you to inspect. On a failure it removes only the
staging folder it created in that run. It takes 17
options and all are required. Most are paths or expected SHA-256 hashes. Five of them can repeat: `--analysis`, `--paragraph-disposition`, `--required-disposition-module`, `--allowed-review-role` and `--required-collection-type`. For what each flag expects, see [Attach a review tranche](PORTABLE_EVIDENCE_WORKSPACE.md#attach-a-review-tranche). Run
`python mamey_run.py attach-bgc-overlays --help` for the full list. In outline:

```bash
python mamey_run.py attach-bgc-overlays --base-report-root <stage-1-folder> \
  --target-ledger <ledger.tsv> --expected-target-sha256 <hash> \
  --review-root <review-folder> --source-manifest <manifest.json> --expected-manifest-sha256 <hash> \
  --analysis <rows.tsv> --paragraph-disposition <dispositions.tsv> \
  --expected-reviewed-loci <N> --required-disposition-module <module> --allowed-review-role <role> \
  --source-discovery-catalog <catalog.tsv> --expected-source-discovery-catalog-sha256 <hash> \
  --source-discovery-decisions <decisions.tsv> --expected-source-discovery-decisions-sha256 <hash> \
  --required-collection-type <type> --out <new-folder>
```

On success it prints one JSON object with `"status": "PASS_PROPOSAL_ONLY_NOT_ACCEPTED_NOT_INTEGRATED"`.

The command consumes a frozen target ledger, a
hash-and-byte-verified review manifest, locator-first scientific-analysis rows,
and paragraph dispositions. It requires the reviewed assembly and exact region
key to match the immutable base `REPORT_INDEX.tsv`, verifies every indexed base
report, and rechecks the base, target, and review snapshots immediately before
atomic publication. Source-reported comparator coverage above 100 percent is
admissible only as an explicitly quarantined, non-usable provenance value. Its
output is deliberately small and additive: one reconciliation Markdown module
per reviewed locus, a locator-first `INDEX.md`, machine-readable
`REVIEW_INDEX.tsv`, `SCIENTIFIC_OVERLAY_LEDGER.tsv`,
`PARAGRAPH_DISPOSITION.tsv`, and `MODULE_STATE_DELTA.tsv`. A proposed state
delta never edits the base report or confers acceptance, integration,
biological validation, or release authority.

## Independent states

The following states must remain independent:

- source discovered;
- exact identity bound;
- evidence observed;
- query and run receipt admitted;
- module assembled;
- module verified current;
- interpretation reviewed;
- public export approved.

Passing one state never manufactures another. Similarity is not identity, and
biosynthetic capacity is not production, activity, novelty, or physical
linkage.

## Portable software boundary

The report builder ships inside the standalone Sapote-Mamey bundle. User data
does not. External evidence is resolved through logical root configuration and
a hash-bound source manifest. Reports contain logical evidence identifiers, not
hard-coded personal workspace paths.

## Status words and checks

Stage 1 ends with `DRAFT_BUILT_NOT_ACCEPTED_NOT_INTEGRATED`. Read the module-state counts and the ledgers, not only the report count.
The overlay ends with `PASS_PROPOSAL_ONLY_NOT_ACCEPTED_NOT_INTEGRATED`. It proposes state changes. It does not run Mode B verification or prove a reviewed paragraph is correct.

Both commands refuse an output folder that already exists. Use a new folder for changed inputs, and keep the base report with each overlay.

`verify-modeb` checks the 48-section profile by default. For a 50-section card, pass `--contract current50_v2`. `--require-expanded-locus` works only with that contract. A `--rescue-tsv` file does not make a gene outside a region part of a BGC. Verification is a separate step with its own receipt.
