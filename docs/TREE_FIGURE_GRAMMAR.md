# Tree figure display and provenance

Use labels derived from explicit, hash-bound panel metadata. Display style does not establish scientific acceptance.

## Labels

Query labels may show strain, deposited host or collection location, and accession. Reference labels may show the organism, deposited isolation source and country, and accession. Keep collection origin distinct from later handling location. Do not invent values or turn a missing database into biological absence.

Use brackets for accessions, including reference-tip accessions, following `FIGURE_HOUSE_RULES.md` rule 6. Put separately labeled deposited source text in parentheses or in the caption; do not confuse it with the accession. Extract accessions before interpreting organism text; culture collection codes are not accessions. Preserve complete accession strings outside the organism-text budget. Repeated copies of one accession are redundant; different accessions on one tip require reconciliation.

`tools/build_placement_ggtree_inputs.py` accepts explicit host, auxiliary and reference SQLite inputs. Its annotation and receipt distinguish unrequested metadata, unbound accessions, unmatched accessions, empty deposited fields and populated deposited metadata. The configurable `GG_REF_LABEL_CHARS` budget controls organism text; it does not validate label uniqueness or guarantee that every canvas is wide enough.

## Prepare matched tree and metadata inputs

Run from the selected bundle root with Biopython available. Create the destination parent beforehand and replace every quoted placeholder with the reviewed source or a fresh output prefix:

```bash
python tools/build_placement_ggtree_inputs.py \
  --graft "/absolute/source/placement.newick" \
  --host-table "/absolute/source/strain_metadata.tsv" \
  --group "reviewed panel name" --neighbors 3 \
  --family-level --outgroup-substr "reviewed exact outgroup substring" \
  --out-prefix "/absolute/new_view/panel" \
  --rect-meta-out "/absolute/new_view/panel_rect_metadata.tsv"
```

This example assumes a multi-genus panel with an independently selected outgroup. Inspect the actual matching tips; the substring is not an exact-tip identity validator. Query recognition is limited to names beginning with `AS` or `SID` followed by an optional hyphen/underscore and a digit. A differently named query can enter the reference branch; reconcile tree roles before using this helper. It retains each recognized query, selected outgroups and normally up to three references per query by patristic distance. A required reference species supplied with `--required-reference-table` consumes the same quota. `--keep-all-refs` retains all references; zero or negative `--neighbors` is effectively a minimum quota of one. No recognized queries means the nearest-reference pruning branch is skipped. Inspect counts and selection rows rather than assuming the filename represents the requested panel.

The producer writes `<prefix>_pruned.nwk`, `<prefix>_ggtree_annotation.tsv`, `<prefix>_reference_selection.tsv` and `<prefix>_metadata_receipt.json`, plus the explicitly requested rectangular metadata TSV. The placement annotation and rectangular metadata are different schemas. The receipt binds admitted input bytes and the output files other than itself; names are recorded as basenames, so preserve an external full-path/hash inventory and the receipt's own hash when basenames could collide. Annotation `validation=NEIGHBORHOOD` is an assigned label, not a separate scientific validation result.

Use a new prefix and a distinct rectangular metadata destination. Existing final files can be replaced. Output publication uses staged siblings, backups and a recovery receipt with rollback; individual replacements do not make the whole set one atomic transaction. If `<prefix>_publication_recovery.json`, its staging sibling or `.prepublish.bak` files remain, the next publication is refused. Preserve and inspect these files and the current final/staged hashes before resolving an interrupted attempt; do not delete recovery evidence merely to rerun.

## Bind an existing GToTree panel's display metadata

`tools/bind_panel_metadata.py` is a local TSV adapter for an existing panel's `figure_metadata.tsv`; it does not build, prune or render a tree or fetch NCBI records. Run it with the selected bundle's Python and bundled helpers. This metadata table differs from the placement/rectangular schemas above. Bind exact tip IDs, roles and identifiers to the intended tree before choosing a renderer.

```bash
python tools/bind_panel_metadata.py \
  --panel-dir "/absolute/source/reviewed_panel" \
  --out-dir "/absolute/new_view/bound_panel" \
  --assembly-records "/absolute/source/assembly_records.tsv"
```

`--assembly-records` needs `accession`, `organism`, `strain`, `fromtype`; identifiers join exactly, and duplicate accession rows keep the last row without conflict admission. When the deposited strain is empty, label construction can recover a `strain <token>` from the old concise label; inspect that inherited value separately from the new Assembly source. `--assay-table` is an optional strain-context table with `strain`, `anti_candida`, `anti_mrsa`. It affects only `role=QUERY` rows, preserves `+`, `-` (including Unicode minus), `n.t.` and blank, and refuses conflicting repeated strain states. Query strain recognition prefers an exact `AS-<digits>` identifier, then an `AS-<digits>` tip prefix, otherwise the identifier. A missing assay row retains previous cells and reports `NO_ASSAY_ROW`; a missing Assembly record retains previous labels and reports `NO_ASSEMBLY_RECORD`. Neither is a run failure or a measured negative.

For optional `--bc3`, panel selection uses the source directory's basename as a substring of each table row's `panels` field. The table must carry identifiers and reviewed isolation/geography/location fields; any panel tip absent from the selected table or source/geography text with no classification rule is refused. `--corrections` is processed only with `--bc3`: rows matching the exact panel or any `LOCAL-` panel are admitted, and repeated identifier/field corrections keep the last value. Curate the intended subset and retain its source hashes rather than relying on filename or substring selection as panel identity proof.

Combined-option order matters: source/geography corrections run first, assays second, Assembly labels third. A withdrawn assay cell cleared by a correction can be filled again from `--assay-table`, and an identity-held label can be replaced by an Assembly label, including a renewed `[Type]` tag. The current adapter does not reapply those owner holds at the end. Retain and reconcile the final cells/labels against the correction ledger before accepting the display; hold contradictory output for an owner source patch. `[Type]` is otherwise derived from `fromtype=assembly from type material`. The adapter uses parentheses for accession labels, so its output still needs review against this guide's bracket house rule before publication.

## Rendering and review

Choose the renderer and its matching metadata explicitly:

- `Rscript tools/ggtree_placement.R "/absolute/new_view/panel_pruned.nwk" "/absolute/new_view/panel_ggtree_annotation.tsv" "/absolute/new_render/placement" noloc` uses the placement annotation and writes `.pdf` then `.png`. It requires R packages `ape`, `ggtree`, `ggplot2` and `treeio`. The fourth argument selects `id`, `host`, `noloc`, `withloc`, `full` or a named annotation column; an unavailable style warns and falls back to `label_withloc`.
- `Rscript tools/ggtree_rect_heatmap.R "/absolute/new_view/panel_pruned.nwk" "/absolute/new_view/panel_rect_metadata.tsv" "/absolute/new_render/rectangular" "exact_query_tip1,exact_query_tip2"` uses `tip`/`label` metadata with unique IDs and an exact tree-tip set. It additionally requires `aplot`, `patchwork` and the bundled Python tree/annotation guards selected through `SAPOTE_PYTHON` or PATH `python3`. Its optional fourth argument supplies exact focal tip IDs. Without it, only a metadata `role=query` column supplies focal IDs; the producer's rectangular metadata does not include that column, so supply the focal roster explicitly when queries should be highlighted.

The placement renderer directly joins the annotation and does not perform the rectangular renderer's exact-tip-set/duplicate checks or Python tree gate. Reconcile counts and joins before accepting a placement image. The rectangular renderer writes `.annotation_audit.tsv`, `.methods.txt`, `.pdf`, `.png` and `.session.txt`; a hash-bound display-receipt route additionally invokes render binding. Read [display-receipt setup](TREE_DISPLAY_RECEIPTS.md) for that distinct route. Guard or binding failure is not visual acceptance, and graphics can already exist when final binding fails.

Both renderers write output files sequentially. Existing destinations can be replaced; the rectangular bound-display route has a narrower existing-output refusal, which is not a universal no-clobber promise. Use a fresh output prefix with an existing parent and inspect partial outputs after failure. Inspect the actual PDF or image for clipping, collisions and legibility after changing canvas size or label length. Identify the outgroup, analysis source, display transformations, and any missing metadata in the caption or accompanying provenance record. Set source-bound `GG_TITLE`, `GG_SUB` and `GG_METHODS` for the placement renderer: its defaults describe bacterial 16S/EPA-ng on a RAxML-NG GTR+G backbone with 10 bootstraps regardless of the actual input. Reusing it for another analysis without overriding those strings can mislabel the figure. `GG_METHODS` is optional in code; an unset value omits the placement methods caption, while the rectangular route records “Methods not supplied.” Neither supplies a verified analysis method automatically.

The analysis tree and any pruned or collapsed display derivative have separate roles. Preserve the analysis tree and the transformation ledger. A visible missingness marker can be omitted from a label only while its underlying hold and provenance remain available.

For a collaborator-facing editable copy of an existing rectangular display folder, use the [figure-source export contract](TREE_DISPLAY_RECEIPTS.md#export-an-editable-figure-source-copy). Confirm the exact source/receipt inventory, disjoint new output, supplement destination names and actual helper input filenames before copying. Editing an exported alias or refreshing file hashes does not establish a new valid display derivative or rendered result.

## Outgroups and claims

Use an explicitly selected, provenance-bound outgroup designation. Non-modal genera must not be accepted as outgroups merely from display heuristics.
The .447 `build_placement_ggtree_inputs.py` helper still treats non-modal genera as
outgroups unless `--family-level` is selected. For a multi-genus panel, use that
flag with an explicit `--outgroup-substr` bound to the reviewed roster and inspect
which tips matched; the flag alone does not verify a unique or appropriate outgroup. Missing or conflicting designation remains a hold. The bundled registry is a historical reference snapshot; use a governed external registry for project decisions. `tools/phylo_outgroup_gate.py` is the shipped outgroup gate; do not add a duplicate under a different name.

A passing mechanical check does not accept a rooting, species assignment, compound identity or biological activity. Report aligned length with identity measurements and distinguish sequence placement from scientific interpretation.

Deposited reference databases may include an optional `host` column. Host values remain explicitly labeled as host, even when isolation material is present. The full combined deposited text remains in annotations; the visible label uses its independent display budget. Databases containing only `acc_base`, `isolation_source` and `country` remain supported
by this compatibility helper. Its join normalizes accession bases; it does not prove
that metadata belongs to the exact accession version displayed. Conflicting source
values are refused, but identical metadata at multiple versions does not restore
version provenance. Use the exact-version source-label adapter in
[TREE_DISPLAY_RECEIPTS](TREE_DISPLAY_RECEIPTS.md#add-deposited-source-labels-before-collapsing)
when that version binding is required.

The helper skips specific legacy `AS_LOCAL_...` records, but a current 16S database
can contain `LOCAL:` keys. Those are not deposited accession records and can fail
this helper's accession admission. Prepare an explicit source-bound reference-only
view/export for this consumer; preserve the original mixed database and unresolved
local query metadata rather than deleting records to make rendering pass.

## Panel metadata outputs and recovery

Use a fresh output directory distinct from the source panel and every input. The binder creates/reuses its selected directory, copies the Assembly table by basename and an optional omit receipt as `omitted_tips.tsv`, then directly overwrites `figure_metadata.tsv`. It has no bundle/input collision guard, staged group publication, rollback or saved hash manifest. An input Assembly table named `figure_metadata.tsv` would collide with the output name; reject such destination collisions before running. A later failure can leave copied files, an empty directory or a partial table. Preserve those outputs and rerun corrected inputs into a fresh directory.

`--omitted-tips` accepts a receipt whose first columns are `tip`, `name`, `reason`, validates nonempty identities/names and supported reason grammar, and refuses receipted tips also present among the panel's identifier/tip cells. This binder does not establish that every prior-panel tip is retained or receipted; use the separate omission `check` route with its explicit prior/staged rosters for that narrower accounting. Neither route proves the asserted omission reason scientifically. TSV output uses spreadsheet formula escaping, so inspect and retain the original deposited text separately when exact byte preservation matters.

Success exits 0 and prints a human status summary on stdout, with no persisted receipt or input/output hashes. Missing assay/Assembly joins can still be reported in that success summary. Save the summary, exit status and external source/output hash inventory; inspect errors and partial artifacts before retrying. No binder status verifies the tree-tip set, unique labels, scientific identity, activity or a completed render.

## Resolve missing reference metadata explicitly

`tools/resolve_reference_metadata.py` can retrieve metadata for selected accessions
and optional linked BioSamples. It performs live network operations, so use it only
within the user-authorized retrieval scope and preserve the source evidence behind
the returned fields. It is not a read-only local inventory.

Inspect each output row's `verification_status`, `strain_match_basis` and
`unresolved_issue`. Refused identity or incomplete metadata can be represented as a
row without raising a transport exception, and `--continue-on-error` permits zero
exit even when ERROR rows occurred. Exit zero therefore does not mean every row is
resolved or scientifically accepted. `--out` overwrites its selected TSV destination;
use a fresh path and retain unresolved rows instead of silently filling values.
