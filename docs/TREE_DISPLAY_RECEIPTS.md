# Reference clade display derivatives

A display tree is a reproducible drawing input derived from an unchanged analysis tree. A group of near-identical reference sequences is a display choice, not a species assignment, ecological grouping, or scientific acceptance. The analysis Newick, alignment, and original metadata remain unchanged.

## Prepare explicit inputs

Provide one aligned nucleotide FASTA, one Newick, and one TSV with exactly matching tip identities. Duplicate tips, duplicate headers, malformed rows, unequal sequence lengths, empty sequences, and invalid nucleotide symbols are refused. Every non-root branch must have a finite, nonnegative length. The root may omit its length.

Metadata requires the four columns `tip`, `label`, `role`, and `taxon`. An absent `taxon` header is refused. Roles are exactly `query`, `reference`, or `outgroup`. Supply `taxon` from the bound source record for references eligible to collapse; blank taxon cells remain uncollapsed. Names or an accession parser do not establish a taxon. Existing panels using `kind` require an explicit producer/schema adaptation to this contract; column position or a generic source category is not a role declaration. Query-like machine keys that conflict with a reference role are refused. Ordinary outgroup display labels remain ordinary organism labels; the outgroup role belongs in metadata and Methods.

## Create an additive display

```bash
python tools/collapse_near_identical.py panel.aln.fasta panel.nwk panel_meta.tsv \
  --max-nt 2 --min-cols 500 --out-prefix figures/panel
```

Both numerical limits are required. Mismatches count only columns where both sequences contain A, C, G, or T; gaps and ambiguous bases provide no shared-column support. Every pair in a collapsed group must meet both limits, and the entire group must form an exclusive clade in the analysis tree with the same recorded taxon. The largest qualifying clades are selected first. Smaller clades are still considered when their parent fails. All query tips and outgroups are excluded from collapse; `--protect EXACT_TIP` adds further retained tips and can be repeated. An absent protected tip is a refusal.

Representatives maximize the number of unambiguous bases, with exact tip identity breaking ties. Branch lengths serialize with 17 significant digits. Retained-tip patristic distances are preserved within floating-point precision, including when branches are joined during pruning. The original analysis tree bytes are never rewritten.

The default retains outgroup tips. Explicit `--prune-outgroup` only permits removal when all declared outgroups form one exclusive root-sister clade. An explicitly protected outgroup cannot be pruned. The display must retain at least two tips. This option does not authorize rerooting, changing the analysis topology, or accepting the outgroup scientifically.

Outputs are `<prefix>_display.nwk`, `<prefix>_display_meta.tsv`, `<prefix>_collapse_ledger.tsv`, and `<prefix>_display_receipt.json`. Existing outputs are refused. Each ledger row retains the full original metadata as JSON, with the tip, representative, disposition, pairwise summary, and mismatch/shared-column counts. Every input tip appears exactly once, including representatives, retained queries, and explicitly pruned outgroups.

Collapsed labels identify the shared recorded taxon, member count, mismatch ceiling, and representative. Source, category, accession, and other member-specific columns are cleared on grouped display rows; `display_source_scope=member_records_in_ledger` records why. A representative's deposited source is never displayed as a shared habitat. All member-specific values remain in the ledger.

## Verify and render

Creation prints the receipt path and its SHA-256. Carry that expected digest in the invoking run manifest or command record. A receipt is an integrity binding, not a signature or scientific approval. Its relative locators can move with the input/output directory structure.

```bash
python tools/gate_stem_aware.py figures/panel_display.nwk \
  --metadata figures/panel_display_meta.tsv \
  --receipt figures/panel_display_receipt.json \
  --receipt-sha256 EXPECTED_SHA256 --parent panel.nwk
```

The verifier checks the externally supplied receipt digest, all input and output hashes and byte counts, the requested tree/metadata/parent paths, and the complete schema. It rebuilds the display from the bound inputs in memory and requires exact output bytes, including the membership ledger. Rehashing an arbitrary display does not make it a valid derivative. There is no sibling-filename receipt trust or newest-bundle selection. The checker is always the gate wrapper's sibling `tree_sanity_check.py`. Missing machinery returns exit 3 and blocks rendering; invalid bindings or gate failures return exit 2.

The wrapper retains the engine's branch checks. Its narrow structural exemption applies only to a dominating internal ingroup stem directly below a bifurcating root with an exclusive outgroup sister. Every other non-outgroup branch is checked against the same depth ceiling, and terminal failures remain fatal. No comparison against rounded diagnostic text establishes branch identity. The exemption is printed and remains a display gate result, not scientific acceptance.

```bash
GG_DISPLAY_RECEIPT=figures/panel_display_receipt.json \
GG_DISPLAY_RECEIPT_SHA256=EXPECTED_SHA256 \
GG_GATE_TREE=panel.nwk GG_FIGID='Figure reference panel' GG_STRIPS=0 \
Rscript tools/ggtree_rect_heatmap.R figures/panel_display.nwk \
  figures/panel_display_meta.tsv figures/reference_panel QUERY_A
```

`GG_GATE_TREE` is optional when the receipt selects the analysis parent; if supplied, it must match that parent. An ordinary render retains its existing sibling-checker path. A distinct parent without a verified receipt, `GG_SKIP_GUARD`, and `GG_GATE_EXEMPTION` remain refusals. The renderer preserves exact metadata joins, ordinary outgroup labels, plain query fonts by default, a scale bar, optional titled strips, and named figures. `GG_STRIPS` accepts 0, 1, or 2; `GG_STRIP1_TITLE` and `GG_STRIP2_TITLE` name the actual columns being shown.

The caption identifies the display tip count, pruned outgroup count, mismatch/shared-column limits, query retention, and membership ledger. After drawing, the receipt is verified again; a separate `.render_receipt.json` binds the PDF, PNG, session information, analysis tree, display receipt, renderer, checker, and gate wrapper. Existing bound render outputs are refused. If final binding fails, generated graphics remain unverified and no render receipt authorizes them.

## Add deposited source labels before collapsing

```bash
python tools/add_reference_source_labels.py panel_meta.tsv \
  --db frozen_reference.sqlite --out panel_with_sources.tsv
```

The database is explicit and read-only. It must be a frozen, checkpointed SQLite snapshot with a `record.acc_version` column; active journal/WAL sidecars are refused. Exact versioned accessions use the existing canonical parser. Versionless, conflicting, missing, and ambiguous lookups retain typed unresolved states. No shared numeric accession body or filename alias supplies identity.

Only reference labels can change. The field order is deposited `isolation_source`, then `host`, then `geo_loc_name`; a geographic fallback is labelled `location:`. Full original labels, type tokens, accession versions, source fields, and raw record values are retained. Existing bracketed sources remain unchanged with an explicit review state. Query and outgroup labels remain unchanged. Missing source fields are unavailable evidence, not a negative biological observation. A sidecar receipt binds the original metadata, frozen database, and additive output. Perform this step before collapse so source values are part of the display's original metadata and ledger.

## Export an editable figure-source copy

Request `tools/export_tree_figure_source_package.py` for a separately identified copy of one already-rendered rectangular display folder. It copies selected existing files and renderer/gate helpers; it does not infer a tree, verify a scientific interpretation or run a renderer. Inspect its input inventory and estimated copy size first. When an editable copy is unnecessary, reference the existing evidence in place by path and hash.

```bash
python tools/export_tree_figure_source_package.py inputs/rendered_panel \
  --out outputs/editable_panel_new
```

The source needs exactly one `*_display.nwk`, one matching-stem PNG/PDF `*_rect02` pair, exactly one `*_rect02.methods.txt`, fixed `display_input.tsv` and `display_input.fasta`, `METHODS.md`, and one stem-specific `*_display_receipt.json` excluding the generic placement summary. `--caption` can select another existing text file, but the unique default methods sidecar is still required by discovery. A separate `placement_display_receipt.json` is copied when present. The receipt's selected analysis tree and every input/output record must resolve to existing files directly in the source directory; valid displays whose original bound inputs reside elsewhere are not automatically adapted.

The exporter does not verify the display receipt schema, recorded hashes/bytes or replay, nor reconcile the selected display/clean figures/fixed input names against that receipt. Verify the original source and its actual display/render bindings before export; a newly hashed copy does not repair a stale or mismatched receipt. The original clean figure's `.render_receipt.json` is not automatically selected. Retain it in place with its hash, or deliberately include it as a reviewed supplement without assuming that relocation preserves its relative bindings.

Select a new output directory outside the source and all preserved evidence; existing output is refused. Review receipt locators as safe single basenames, with no absolute paths or `..` components, and confirm all generated destinations remain inside the selected output. The current source-parent check does not guard the destination built from the same locator: a path can resolve into the source directory for reading yet escape the export directory for writing. Check unique destination names across receipt records, generated helper/README/manifest names and supplements before running.

Copies include figure-specific tree/analysis-tree/metadata/alignment/caption/methods/clean-figure aliases, original receipt-bound names, the display receipt and local R/Python helper sources. Selected ledger/selection/pairing/custom TSVs and named provenance JSONs are copied automatically into `supplementary_ledgers/`; repeated `--supplement FILE` adds explicit files. Distinct supplements with the same basename are copied to the same target, and a later copy can silently replace an earlier one. Keep the original evidence and an explicit source-to-destination inventory; a single final filename is not proof that every selected source survived.

Export creates the output directory before all receipt-bound sources, helper files and explicit supplements are fully admitted, then copies/writes sequentially. A later refusal or I/O failure can leave a partial directory without `MANIFEST.json`; retrying to it is refused because it exists. Preserve partial output and diagnostics, correct the inputs and choose another fresh directory. Success prints the output path and writes a final file-hash/size manifest; it provides no frozen consumed-source snapshot or group transaction. Its `source_dir` is an absolute source locator, so review that metadata and the copied evidence before sharing.

## Editable aliases, replay and refreshed manifests

The generated `<stem>_rerender_captioned.sh` invokes `<stem>_render_figure.R` with the original tree and metadata paths named by the display receipt. The convenient `<stem>_tree.nwk`/`<stem>_metadata.tsv` aliases are not substituted automatically. Editing an alias can therefore have no effect on the helper's render. Inspect its actual arguments and keep all receipt-bound scientific inputs unchanged for a replay. A changed tree/alignment/scientific metadata needs a separately admitted derivative and new receipt, not just a refreshed package manifest.

The export includes both the figure-specific R entry and a canonical `ggtree_rect_heatmap.R` copy. The current render gate binds the canonical filename as renderer provenance even when the helper executes the figure-specific entry. If that entry is edited, retain its actual executed file hash separately; do not describe the canonical copy's hash as proof of the modified renderer used. Shell interpolation is quoted, and the exported helper retains receipt-bound display checking, but export itself does not execute that check. A bound rerender refuses existing output-prefix artifacts; retain prior results and select a fresh reviewed prefix before an authorized rerender.

The helper finishes by running its sibling `refresh_figure_source_manifest.py`, which directly replaces that exported folder's `MANIFEST.json` with hashes of current eligible files. It omits symlinks, caches/bytecode and files named `MANIFEST.json`; it is an inventory refresh, not display replay, complete source provenance, rendered-page inspection or scientific acceptance. Preserve the previous manifest as separate evidence before adopting an edited derivative. R packages and Python gate dependencies must be available on the destination machine; copying helper sources is not environment provisioning. Sources: `tools/export_tree_figure_source_package.py:13–149`, `tools/gate_stem_aware.py:49–87,165–180`, `tools/ggtree_rect_heatmap.R:4–65`, and `tools/refresh_figure_source_manifest.py:15–46`.

## Validation boundary

Generic tests exercise retained distances, role protection, exclusive clades, complete-linkage limits, alignment and metadata failures, source-version conflicts, mutation refusal, deterministic replay, relocation, and real R rendering when the graphics stack is available. Focused test success is not a full-suite, integration, release, publication, or scientific validation result.
