# Reference clade display derivatives

A display tree is a reproducible drawing input derived from an unchanged analysis tree. A group of near-identical reference sequences is a display choice, not a species assignment, ecological grouping, or scientific acceptance. The analysis Newick, alignment, and original metadata remain unchanged.

## Prepare explicit inputs

Provide one aligned nucleotide FASTA, one Newick, and one TSV with exactly matching tip identities. Duplicate tips, duplicate headers, malformed rows, unequal sequence lengths, empty sequences, and invalid nucleotide symbols are refused. Every non-root branch must have a finite, nonnegative length. The root may omit its length.

Metadata requires `tip`, `label`, and `role`. Roles are exactly `query`, `reference`, or `outgroup`. Supply `taxon` from the bound source record for references eligible to collapse; missing taxa remain uncollapsed. Names or an accession parser do not establish a taxon. Existing panels using `kind` require an explicit producer/schema adaptation to this contract; column position or a generic source category is not a role declaration. Query-like machine keys that conflict with a reference role are refused. Ordinary outgroup display labels remain ordinary organism labels; the outgroup role belongs in metadata and Methods.

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

## Validation boundary

Generic tests exercise retained distances, role protection, exclusive clades, complete-linkage limits, alignment and metadata failures, source-version conflicts, mutation refusal, deterministic replay, relocation, and real R rendering when the graphics stack is available. Focused test success is not a full-suite, integration, release, publication, or scientific validation result.
