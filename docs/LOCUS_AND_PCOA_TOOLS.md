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
