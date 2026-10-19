# Read locus maps, gene tables and protein PCoA comparisons

The optional `gap-rescue` command runs after validation and requires separately provisioned search inputs. It is a screen, not an adjudication. The main extraction command does not launch it. Use `python mamey_run.py gap-rescue --help` to check its inputs and output destination before authorizing a run.

`tools/gap_rescue_gene_table.py` pairs a reference-gene table with the locus map. Each reference gene has one row; a displayed split lists both pieces together in that row. The table includes saved local and reference protein lengths and a local/reference full-protein length ratio; split rows leave the ratio blank, and the ratio is not alignment coverage. Captions distinguish reference-gene counts from distinct local proteins. Homology does not establish physical linkage, product identity or production.

`tools/locus_reading_pages.py` builds Markdown reading pages from supplied packages, annotation ledgers and optional comparison evidence. Run its `--help` from the bundle root to bind the required arguments. Search inputs, when supplied, can trigger additional searches; omit them for an existing-evidence reading pass and retain the reported unsearched states. Each locus retains strain / full node-or-contig / region / BGC alias. Hand assessments remain separately authored material.

`tools/protein_pcoa_compare.py` consumes an existing protein PCoA kit and a cohort table. Its denominator uses cohort members represented in the kit's canonical per-set tables before set selection. It records denominator membership and hashes contributing tables, including unselected sets. Genome-level tests are primary; protein-level tests are secondary and pairwise p-values are raw, exploratory values. Similarity and position do not establish activity or resistance.

`tools/pcoa_bgc_explorer.py` adds an offline rotatable three-axis view of the same coordinates. Rotation changes the display, not the scores or point membership. Points without identity values retain a separate symbol. Supplied metadata and disagreements are recorded rather than silently inferred.

Use [figure house rules](FIGURE_HOUSE_RULES.md) and [figure style](FIGURE_STYLE.md) for exports. Inspect the actual rendered page and keep its caption, methods, source bindings and denominator together. Tools and command availability are listed by the generated [command catalog](COMMAND_CATALOG.generated.md) and [tools inventory](TOOLS_INVENTORY.generated.md).

## Saved coordinate replay

`tools/protein_pcoa_render.py` can redraw an existing kit without refitting an ordination. Bind its cohort table, drop-origin list, optional set-name table, selected PCoA/nearest tables and original `RUN_<SET>.json` metadata. A folder of delivered tables may need an adapter to the documented `out_<SET>/` layout.

Missing `pct_axes` now produces plain axis labels and `axis_metadata.state = NOT_PROVIDED` in each panel receipt. It never prints `nan%`. Use `--require-axis-metadata` to refuse missing axis percentages before any selected panel is drawn. Invalid supplied values are refused. The tool does not infer percentages from saved coordinates. This option checks axis metadata only; it does not certify a publication cohort or exclusion policy.

The final render receipt binds input paths and bytes, optional missing files, output hashes, renderer source and figure policy. If input or renderer files change during drawing, the attempt is refused and its partial artwork remains without a final success receipt. Preserve that attempt rather than presenting it as a completed figure. Receipts do not freeze external libraries or fonts, establish historical equivalence or replace rendered-page inspection.


## Watched protein ordination attempts

`protein_pcoa_ordinate.py ordinate` streams and binds metadata/FASTA before admitting heavy work. Its existing distance definition, clustering thresholds, cohort retention, solver branches and axis calculations remain unchanged. Conservative resource estimates include dense matrices/workspace, input overhead and quadratic all-vs-all text growth; they are estimates rather than guaranteed peak memory or disk bounds.

Use `ordinate --kit INPUT_KIT --set KS --preflight --resource-receipt-dir NEW_DIAGNOSTIC_DIR` for counts and estimates without tool discovery or computation. The explicit diagnostic destination must be fresh with an existing parent; no automatic sibling receipt is written. Preflight does not create an output kit.

Compute defaults are3,800,000,000bytes process-tree RSS,2,000,000,000bytes minimum free disk,900seconds and4DIAMOND threads. CLI `--rss-limit-bytes`, `--min-free-disk-bytes`, `--timeout-seconds` and positive `--threads` configure these limits. The M5 campaign's execution ceilings are separate from portable user configuration. Available CPU count is recorded as an observation, not an inferred scheduler allocation or a universal thread cap. Numerical libraries use one thread within the worker.

A set with reference or MIBiG sequences is admitted cluster-first by default, as described below: those sequences are clustered in every run, so the dense solver is admitted at the clustered count. A cohort-only set is never clustered; it is admitted on its retained-point upper bound before any work, then actual retained n is checked before all-vs-all and dense allocation. An estimate over80% of the RSS budget refuses. `--no-cluster-first` forces the upper-bound admission for any set, and `--cluster-first` forces cluster-first. The receipt records `admission_mode` and whether it came from the default or an explicit flag (`admission_mode_source`). No automatic subsampling or threshold change occurs.

All heavy Python work, including sequence loading and the eigensolver, and DIAMOND descendants run under one watched worker. POSIX process monitoring must be available; a failed monitor refuses rather than silently running unmonitored. Sampling can overshoot limits between observations and is not a kernel-enforced resource sandbox. Coordinator streaming memory is separate from the reported worker-tree RSS.

Ordinate requires a fresh `out_<SET>` directory. Use `--attempt-root NEW_OUTPUT_KIT` for another attempt without changing previous kits; this output kit need not contain extraction inputs. Inputs and ancestor paths must have no symlink aliases. Retained scratch/logs under `RESOURCE_ATTEMPT` belong to that one attempt; never treat failed scratch as a successful kit. Only the two expected scientific tables are promoted, with no overwrite; final RUN is written after successful monitor and hash checks. The terminal success receipt binds RUN, and RUN binds the frozen monitored resource receipt. Interrupted promotion is incomplete, not an atomic multi-file success.

New resource-contract kits require their matching successful receipt chain for replay. Legacy saved-coordinate kits remain usable with unknown historical producer metadata; replay receipts separately record saved-coordinate mode, supplied historical provenance and current rendering runtime. Installed package versions and loaded-module versions are distinguished; unrecorded R/font details remain unknown. These fields do not establish scientific accuracy or historical PNG byte equivalence. Original RUN metadata is never rewritten by replay. Resource receipts remain local/internal by default and may contain paths; public export requires its own projection review.

## Retaining the distance input

`ordinate --keep-allvsall` additionally promotes `allvsall.tsv.gz`. The RUN file's `retained_allvsall` record binds compressed and original TSV SHA-256, original byte length, and ID-order SHA-256. The order is the `id` column of the PCOA table. `tools.protein_pcoa_ordinate.distance_matrix(path, ids)` accepts the retained gzip or a plain hit table and uses the same float32 minimum bidirectional identity definition as ordinate. Callers must perform their own resource admission before its dense allocation. Without the flag, the hit table is removed as before. Retention is an input replay aid, not a new embedding method or a scientific accuracy claim.

The retained input is hashed before and after distance construction, and retention must match that consumed-input binding. The existing disk estimate reserves four times the quadratic hit-table term, covering the raw table, gzip temporary output and promoted gzip copy; compression streams in bounded blocks.

## Cluster-first admission (default for reference and MIBiG sets)

Cluster-first admission (the default when the set has reference or MIBiG sequences, or `--cluster-first`) admits bounded input materialization and reference/MIBiG clustering first, retaining the existing clustering settings and every cohort sequence. A linear cluster-stage engineering allowance replaces the initial dense upper-bound admission only in this mode. It does not guarantee that clustering fits. The same watched RSS ceiling, timeout and free-disk floor remain active; the RSS limit is never automatically raised. Large irreducible cohort membership still refuses early.

After clustering, actual retained n must pass the existing 80% RSS admission margin and a fresh scratch-disk check before all-vs-all, distance allocation or eigensolving. The run records its exact matrix admission estimate and receipt hash. The outer cluster-first watch keeps the free-disk floor throughout both phases; it does not reuse a small cluster-stage growth estimate as a dense-matrix quota.

Metadata-only `--preflight --cluster-first` reports `PREFLIGHT_CLUSTER_ADMITTED_ORDINATION_PENDING`; it does not execute clustering, know the final centroid count or claim that ordination is admitted. No subsampling, method substitution, cohort clustering or threshold change is performed. Native workspace safety and input/source binding refusals still apply.

## Native page artwork and raster QA

New protein pages preserve their PDF/SVG vector masters and the PNG drawn directly by R. A separate `_plot_only.png` is drawn natively at 300 DPI from the same checked geometry. No PDF screenshot replaces source artwork. Captions and Methods remain editable separate files; this clean-artwork packet does not establish a caption band or compiled-publication acceptance. The final completion receipt binds the packet, raster dimensions/declared width and direct QA/helper sources.

Page QA passes its declared print width to `figure_render_qc.py --print-width-in`; `--dpi` is a minimum. The checker distinguishes metadata DPI from pixels divided by declared embedded width. Without a supplied width, effective DPI is explicitly NOT_CHECKED. Pixel counts alone cannot detect an earlier upscale or establish native-render provenance; retain the bound direct-R source and rendering receipt.

## Completed packet transfer and current byte checks

A completed render receipt records an earlier successful operation. Post-completion figure QA rechecks every declared output hash and byte length, including captions, PNGs, metadata and runtime records. Editing a file while retaining the old COMPLETE marker is refused. The checker maps original absolute output locators lexically into the selected artifact folder, so a transferred packet can be checked without opening the old source paths. Duplicate JSON keys or output locators, escaping paths, symlink members and unbound selected PNG/SVG/caption files are refused.

Use a fresh QA child folder under the completed packet or a separate sibling folder; the packet root and an ancestor containing bound members refuse. A destination overlapping bound outputs is refused before OCR or report writes. For an admitted transfer, `figure_render_qc.py --render-receipt-sha256 <admitted_sha256>` also binds the receipt itself. Without that external hash, the checker establishes freshness against the supplied manifest; it cannot authenticate a manifest and artwork edited together. The receipt does not certify scientific correctness or historical fit execution. Unreceipted figures retain ordinary image/text QA without a completed-packet freshness claim.

Keep authored caption changes in a separately versioned document/artifact record with their new hashes, preserving the prior completion record. Changing wording does not require recomputing a figure whose data and geometry are unchanged. The compiled development prototype demonstrates separate caption binding without rewriting a source artwork packet.

## In-run page runtime and observed fonts

New page renders write an exact-stamp runtime sidecar from the R process that drew the final page. It records R/platform, the loaded namespace versions, the actual page labeler and the fact that the renderer executed no numeric ordination fit. Python binds that record and observes the font faces used by nonblank text in the final PDF. Per-page runtime/font records replace NOT_RECORDED in the final page receipt and travel in its output roster. Late changes to drawn artifacts during document/QC finalization refuse completion.

This bounded route records current page rendering, not upstream coordinate fitting, historical package equivalence or every font file's bytes. Single-panel R routes still have the separately recorded runtime gap until their producer is extended. A post-run installed-version probe is not substituted for the new in-run record.

### QA destination and refusal policy

QA reports are create-only: an existing `RENDER_QC.md` or `RENDER_QC.tsv` (including a symlink) refuses before receipt parsing or OCR. Use a fresh QA folder. A completed-packet admission error, including a bad external hash or malformed receipt, returns exit 2 with a diagnostic on stderr and writes no QA reports. A missing receipt is an admission error when an external receipt hash was requested; without that option ordinary pre-completion figure QA remains supported. Content QA findings can produce reports in a fresh destination.

For a completed packet, the destination must not contain any bound packet member. A fresh child folder under the packet or a separate sibling folder is allowed; the packet root or an ancestor containing its members is refused. Output members are resolved only inside the selected local artifact root. Report files are also created exclusively to guard against a file appearing after preflight. In that race a newly created empty report can remain for inspection; existing files are never truncated. Multi-page generation writes all companions first and runs folder QA once, so no page overwrites another page’s QA reports.

### PCoA axis definition and execution provenance

A finite `pct_axes` vector is an annotation format, not proof of variance explained or of a fit. For supplied/legacy metadata the caption identifies percentage annotations with unverified definition and fit execution. Values are preserved, including percentages above 100 or below zero.

The inspected native `classical_pcoa` function reports `100 * eigenvalue / signed trace` of the double-centred squared-distance matrix. It clips negative eigenvalues only for coordinates. For non-Euclidean input these signed ratios are not conventional variance explained and must not be clipped or renormalized for presentation. Full ratios remain in `axis_metadata`; the page shows the first two axes.

A native definition claim requires a validated successful resource terminal chain, matching consumed-coordinate output hash, matching selected native-source hash/byte count, and the known complete numerical-function fingerprint. The render receipt binds the RUN, coordinates and selected source. Unknown or unmatched source definitions stay supplied/unverified. This checks an upstream record association, not an independent rerun; no sidecar alone establishes fit execution, and this renderer only replays saved coordinates. The numerical producer and all fitted values are unchanged by this caption/provenance change.

## Renderer controls, supplied embeddings and explorer scope

`protein_pcoa_render.py --layout pcoa` replays the kit's PC1/PC2. `--layout trimap` or `--layout tsne` requires one `--embedding-table SET=TSV` per selected set, with the same exact point IDs and finite `TRIMAP1/TRIMAP2` or `TSNE1/TSNE2` columns. Duplicate/blank/padded headers, ragged rows, duplicate IDs, nonfinite coordinates and missing/extra identities refuse. These controls select saved coordinates; they do not run TriMap or t-SNE fitting.

An optional exact adjacent `.json` sidecar can supply `coordinates_sha256` and separate `trimap` or `tsne` objects containing a nonempty `version`, a nonnegative integer `seed` and optional `parameters`. Only matching coordinate hashes and complete per-layout fields enter the supplied-metadata caption. Missing, unbound, wrong-method and incomplete metadata remain explicitly unknown; even correctly bound supplied metadata is not proof that a fitter executed.

`--page pcoa,trimap` combines saved layouts with one shared legend and one cohort panel. Pages require the R route; an explicit unavailable R selection or page/matplotlib contradiction refuses. Page defaults supply an 8 pt floor and 70/85% identity tiers. `--label-names` may supply `short` for the canvas and `display` for the full caption key, keyed by `strain`; names and placement still require visual review. Optional `--require-axis-metadata` validates finite annotations, not their scientific definition or fit execution. Current page runtime and axis-definition records do not certify single-panel, comparison or explorer outputs automatically.

The offline `pcoa_bgc_explorer.py` interface selects PC1/2/3 axis pairs and rotates the existing
three-axis point cloud; `fitView` fits the display viewport, not an ordination. New per-set data
includes `axis_annotations`, and a visible note beside the plot identifies percentage labels as
supplied annotations with unverified definition and historical fit execution. The introduction
states saved-coordinate replay. Full finite values, including ratios above 100 or below zero,
are retained without clipping or renormalization. These consumers do not perform the page
reader's native terminal/source/coordinate admission; a purported native field in RUN alone
cannot establish a native definition or a fit.

`protein_pcoa_compare.py` writes the same disclosure per set in `AXIS_ANNOTATIONS.json` and
its separate `CAPTION.md`; percentage-bearing PCoA axis labels say “supplied”. Missing
annotations produce plain axis labels. Comparison statistics and cohort denominators are
unchanged and separate from axis provenance. Invalid supplied annotation vectors refuse
rather than displaying nonfinite percentages.

Comparison plots retain their SciPy/matplotlib route, palette, marker meanings and panel grids.
`--min-text-pt` defaults to 8 and refuses nonfinite values or values below 8 before output creation.
The floor applies at each PDF's native width (6.4 in for share-below, 7.2 in for other panels).
Smaller embedded widths require separate validation. Fixed axes and legends place no point
labels; no R/ggrepel substitution is made. Larger text uses layout-aware margins, wrapped
collection counts, and a minimum 2.6-in carriage height. Each figure is checked for text size,
collisions, canvas overflow and tick/data clearance before saving, then its PDF is read back
with the shared minimum-text checker. `<figure>_text_check.json` records the native width,
geometry result and PDF readback, source hash and image hashes. `SOURCES.tsv` binds those
records and the shared annotation source. A layout that cannot fit at the requested floor
refuses; it never shrinks text. These checks do not establish compiled-publication acceptance,
SVG live-text delivery or a new ordination fit. Prior delivered output directories remain
protected by the existing nonempty-output refusal.

For completed-packet read capabilities, platform refusals, consumed-generation binding and OCR prerequisites, see [completed render-packet QA](COMPLETED_RENDER_PACKET_QA.md).


### Page label quantiles and table compatibility

`--quantile` is the fraction of background nearest-neighbour distances used for label selection
(default 0.95, finite range 0–1). It does not refit coordinates. New page captions and receipt
`label_rule` describe the actual configured percentile, including when no label is drawn.
New page receipts declare `label_table_schema.version = 2`. Page label TSVs preserve existing
columns and append `threshold_distance` (the applied cutoff) and `label_quantile` (its fraction).
The historical `threshold_p95` column equals the applied cutoff only at the default 0.95; it
is blank for other quantiles so a legacy reader cannot mistake a nondefault cutoff for p95.
Readers of new tables should use the two canonical appended fields; a default-only reader can
continue to use `threshold_p95` at 0.95. Historical tables/COMPLETE packets are never rewritten.
For an old caption record with no quantile field, the historical 0.95 default is retained.
