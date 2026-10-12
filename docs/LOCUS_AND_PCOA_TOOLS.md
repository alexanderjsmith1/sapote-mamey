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

The primary mode admits a retained-point upper bound before clustering, then checks actual retained n before all-vs-all and dense allocation. An estimate over80% of the RSS budget refuses. Datasets that could fit after clustering may therefore refuse; no automatic subsampling or threshold change occurs. A cluster-first rescue mode is not provided.

All heavy Python work, including sequence loading and the eigensolver, and DIAMOND descendants run under one watched worker. POSIX process monitoring must be available; a failed monitor refuses rather than silently running unmonitored. Sampling can overshoot limits between observations and is not a kernel-enforced resource sandbox. Coordinator streaming memory is separate from the reported worker-tree RSS.

Ordinate requires a fresh `out_<SET>` directory. Use `--attempt-root NEW_OUTPUT_KIT` for another attempt without changing previous kits; this output kit need not contain extraction inputs. Inputs and ancestor paths must have no symlink aliases. Retained scratch/logs under `RESOURCE_ATTEMPT` belong to that one attempt; never treat failed scratch as a successful kit. Only the two expected scientific tables are promoted, with no overwrite; final RUN is written after successful monitor and hash checks. The terminal success receipt binds RUN, and RUN binds the frozen monitored resource receipt. Interrupted promotion is incomplete, not an atomic multi-file success.

New resource-contract kits require their matching successful receipt chain for replay. Legacy saved-coordinate kits remain usable with unknown historical producer metadata; replay receipts separately record saved-coordinate mode, supplied historical provenance and current rendering runtime. Installed package versions and loaded-module versions are distinguished; unrecorded R/font details remain unknown. These fields do not establish scientific accuracy or historical PNG byte equivalence. Original RUN metadata is never rewritten by replay. Resource receipts remain local/internal by default and may contain paths; public export requires its own projection review.
