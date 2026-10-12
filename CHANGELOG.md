# v9.7.450 — unsealed cut candidate · build 20261011v97450a

Build 20261011v97450a; engine 1.9.175.

- Accretion-justified: mamey/json_evidence_state.py — one shared projection and package reader for bounded JSON channel visibility across validation, workbook, explanation and reports; preserves unknown, held and truncated states without asserting upstream search or biological completeness.
- Accretion-justified: mamey/gold_bgc_identity.py — shared same-package identity admission for Gold figure data and receipts; keeps missing or conflicting physical locus evidence on hold.
- Accretion-justified: mamey/release_policy.py — shared local release decisions and read-only cohort privacy admission; identifier spelling does not establish distribution authority.
- Accretion-justified: mamey/report_release_policy.py — reconcile independently attributable release decisions across report inputs; incomplete, conflicting or unbound authority keeps combined exports private and on hold.
- Accretion-justified: mamey/rrefinder_status.py — preserve receipt-backed extraction states and raw-versus-retained RRE row counts without treating incomplete evidence as biological absence.
- Accretion-justified: mamey/native_workspace.py — shared bounded native cwd, byte-copy and owned cleanup contract for DIAMOND clustering and MLSA BLAST adapters; no scientific algorithm or threshold changes.
- Accretion-justified: mamey/figure_stamp.py — one shared writer for the renderer stamp in saved PNG, PDF and SVG figures, used by matplotlib renderers, the R theme and the caption band; the stamp names the code that saved a file and makes no data or design claim.

- **Full-genome annotation copies resolved at the reader.** `mamey/parsers.py` prefers full antiSMASH output records over archived `input/` copies only when contig identity, positive length and normalized sequence agree exactly; input-only and mismatched records stay available with bounded warnings. Engine 1.9.175.
- **Partner-check diagnostics say what was checked.** `mamey/ref_completion.py` reports a check as not needed when no outside-core find applies. Thresholds and scoring are unchanged.
- **Rejected rescue neighbours stay grey.** Gap-rescue maps keep PARALOG_FAMILY and HOUSEKEEPING_CONTEXT neighbours grey, with no identity ribbon, even when another gene supports the contig.
- **Renderer stamps and a figure provenance check.** Bundle renderers write their name into saved figures; `tools/check_figure_provenance.py` reads it back (PASS, PASS_DERIVED, PLAIN_MPL, UNKNOWN). A ratchet test lists renderers that do not stamp yet.
- **BLASTp runner keeps live searches through an NCBI outage.** A reply with no `Status=` line raises instead of reading as UNKNOWN, so the search stays in flight.
- **Lab Quest removed.** The optional local interface, its docs, tests, installer option and command are gone. Project catalog receipts now go to `project_outputs/`; an existing `lab_quest_outputs/` is still read.
- **Native workspaces and resource gates.** Shared bounded working folders for DIAMOND clustering and MLSA BLAST; GToTree runtime admission, version and worker-budget gates; EPA-ng resource binding.
- **Report scope and privacy.** Per-input release decisions, cached RRE evidence reconciled with extraction receipts, and fact-only key findings in reports.
- **Figures first.** The primary handoff is selected figures with plotted data, captions and Methods facts. Mode B cards and white papers are optional products.
- **Shorter CHANGELOG.** Entries before v9.7.440 are in earlier GitHub releases.
- **Tests use synthetic strain IDs only.** Public tiers check that every strain ID in tests is on `tools/test_synthetic_ids.txt`; 21 real IDs in 14 test files were replaced with unused numbers.
- **Run lock closes cleanly.** The package lock is held by a holder that closes its file when the run ends, and RG-GMCI intake no longer records a ResourceWarning from unrelated objects as a source diagnostic.

# v9.7.449 — unsealed cut candidate · build 20261009v97449a

Build 20261009v97449a; engine 1.9.174.

- **Partner headings preserve contig placement.** partner headings never move contigs.
- **Structures follow the map reference.** region structure follows map reference.
- **Optional post-run gap-rescue command.** gap rescue post run step.
- **Reference-centred pair maps.** rggmci pair map uses locus comparison.
- **Gene tables paired with maps.** gap rescue gene table with map.
- **Isolate labels clear ribbons.** gap rescue isolate label off ribbons.
- **Bounded distant-match display.** gap rescue map far match reach.
- **Split-piece labels.** gap rescue split piece labels.
- **Reconciled map and table captions.** gap rescue map redraw fixes.
- **PCoA collection denominators and provenance.** protein pcoa collection compare.
- **Offline PCoA three-axis view.** pcoa explorer 3d view.
- **Shared runner pacing.** blastp runner fleet pacing.
- **Full contig identifiers.** contig names lose coverage zeros.
- **Opt-in partner context.** gap rescue partner contig context.
- **Locus reading pages.** locus reading pages.
- **User documentation.** Rebased user guidance, current human entry guides, command routes and generator-owned inventories.

- **Visible logger messages.** Three added tools use the existing logger for seven progress, warning and refusal messages; the terminal-output ceiling is unchanged.

# v9.7.448 (2026-10-05), build 20261005v97448b — unsealed cut candidate

- **The sealed-tree notebook guard test runs on Linux (build b).** On GitHub CI, build a reported one failure: the test resolved its path under pytest's temporary folder, which is `/tmp/…` on Linux, where the guard deliberately allows working copies. The test now resolves against the filesystem root; the guard is unchanged. Build b changes only that test file; the engine (1.9.173), tools, outputs and scientific rules are the same as build a.
- **Strain-slide evidence and labels.** Reference-structure gallery and region structures; exact contig, locus-tag and normalized-protein binding for gene-label fallback; class-domain fallback and typed class steps; clearer strip labels and PCoA label placement.
- **Locus comparison slides.** Partner contigs are placed under the reference genes they match, not pushed past the right edge. Each partner track is named by the antiSMASH region that holds its matched genes, from the rescue table; when they lie in more than one place the identity is held. Contig-end and missing-stop markers are drawn for short contigs and genes cut by a contig end.
- **Multi-reference comparisons.** Per-strain comparison slides: best MIBiG or reference-genome matches, one row per compound across name variants, two-line headings, and a ribbon slide against the top match.
- **Neighbour panels.** Local 16S genome-hit and TYGS-table panel builders, plain-text and HTML-tagged TYGS handling, explicit unresolved/duplicate issue records and an independent top-row coverage check.
- **Cut preflight and portability.** Refuse release-root review artifacts; purge bytecode in the selected working copy before identity propagation; distinguish read-only touch/truncate reference operands from write targets; portable module and user-guide wording.
- **Shipped text names no person or working lane.** Rulings and history use role nouns; a new guard test fails the cut if a name, lane label, session id or task number comes back. Licences, citations and the two signed governance records are unchanged.
- **New tools meet the existing guards.** CSV-safe writers, the DPI clamp, import-safe entry points and the GenBank shim fallback. The terminal-emission ceiling moves from 1249 to 1255 for six new sites in modules that other tools import.

Accretion-justified: mamey/figures/locus_comparison.py — reusable source-bound report/slide renderer shared by the comparison adapters.

# v9.7.447 (2026-10-03), build 20261003v97447a — released

- **Completed companion cards.** Optional GECCO cross-check, class/domain metabolomics bridge, named non-KS second-proof policy, fresh-clone add-ons, scanner HMM builder, optional R admission, portable registry tests, RID expiry accounting, protein PCoA source bindings, external post-seal readers, sealed-source BiG-SCAPE staging and compiled PDF rendering.
- **Tools audit completion.** Explicit one-to-one distance contract; corrected extraction coordinates and safe output sets; consistent screen-evidence adjudication; versioned reference admission; homology labels preserving source annotation; cooperating cohort-bank transactions and recovery; owned archive/tarball publication and truthful committed holds; complete query-tip and requested-stage gates; strict RID response admission and paired checkpoint generations.
- **Integration controls.** Fault, concurrency, input-permutation, ownership, malformed-evidence and source-binding regressions exercise the combined implementation. Terminal report consolidation preserves channels and chronology with lower repository health ceilings and no new waiver.

- **Hook decisions and packaging evidence.** Scoped shell/cwd/heredoc/redirection handling, visible advisory channels, canonical candidate-source selection and source-bound suite receipts; recognized mutations can invalidate a packaging decision.
- **Expanded-locus source checks.** Offline assembly and package CDS binding; bounded supported-anchor context; separate core and selected-gene matrix rosters; required expanded work orders; actual verifier metadata admission; code-fence and input-alias refusals.
- **Registry-backed deliverable menu.** Native current50 and bounded expanded-locus recipes; GECCO, class-level MS review export and opt-in non-KS routes; legacy IDs/name aliases retained and availability kept separate from admission.
- **Mode B profiles and evidence routing.** Accepted current50_v2 contract, native template/profile header, supplied rescue reader, rank-1 ingest routing and independent identity/coverage checks; structural validation remains separate from scientific readiness.
- **Reference selection and user documentation.** Ambiguity refusals and bound reference staging; current profile routes, GECCO guidance, strain slides and antiSMASH submission instructions; neutral GToTree compatibility notes.
- **Intake and workbook preservation.** Nonblocking child-output monitoring, exact engine-version admission, conservative archive staging and receipt-bound resume; workbook row, alias, mapping, raw-value and generated-UID safeguards.
- **Incomplete computational stages.** Mandatory tree QC gates refuse when unavailable; requested ANI failures cannot report DONE; incomplete discovery service interactions cannot become ordinary completed empty evidence.

Accretion-justified: modeb_locus_scope.py — shared offline assembly/CDS binding, bounded context selection and expanded-card verification.
Accretion-justified: bank_transaction.py — shared cooperating bank locking, journaled generations and validated recovery.
Accretion-justified: companion_evidence.py — one owner for companion locus and source admission.
Accretion-justified: gecco_crosscheck.py — optional source-bound GECCO class evidence.
Accretion-justified: metabolomics_bridge.py — class and domain export with operator-owned metadata templates.
Accretion-justified: modeb_current50_v2.py — accepted named current50 contract emission and verification.
Accretion-justified: modeb_gap_rescue.py — supplied context reader without scientific adoption.
Accretion-justified: modeb_markdown.py — shared active Markdown interpretation for authored-card checks.
Accretion-justified: nonks_second_proof.py — explicit opt-in second-proof policy while retaining default rules.
Accretion-justified: optional_r.py — shared optional package admission distinguishing absence from unverified probes.
Accretion-justified: output_transaction.py — shared fresh output staging, ownership and ordinary-fault cleanup.
Accretion-justified: pdf_dependencies.py — shared visible PDF dependency causes.
Accretion-justified: postseal_output.py — shared immutable-source and external-reader output ownership.

This entry describes prepared source. The authorized cut owns version/build propagation and regenerated module, release, tier and checksum manifests. The default scientific rules remain unchanged; new distance and second-proof policies require explicit named selection. No compound or activity claim is adopted by this entry.

# v9.7.446 (2026-10-01) — build 20261001v97446a

- **PCoA-to-BGC explorer.** `tools/pcoa_bgc_explorer.py` builds an offline page from protein-class PCoA kits: click a point to open its whole BGC, with per-gene MIBiG and BLASTp evidence and ranked outliers. BGC numbers come only from a package crosswalk whose rows name the strain and list exactly the same region files and coordinates; BLASTp binds by strain, locus tag and protein length, a locus tag naming two proteins is held, and an exact-sequence row reaches every gene with that protein.
- **Protein-class PCoA renderer.** `tools/protein_pcoa_render.py` (with `protein_pcoa_render.R`) draws the PCoA figures with the strain-label rule, grouping labels on the span of the whole kit; R uses cairo, then Quartz, then base pdf.
- **Protein-class PCoA ordination.** `tools/protein_pcoa_ordinate.py` builds PCoA kits from region files (extract, Pfam, CARD, ordinate, nearest).
- **Library progress lines through the engine logger.** 52 library progress lines in 20 modules move from print/emit to the engine logger, byte-identical at the default level; the logger follows a swapped stdout. Command results (JSON, typed refusals, markdown reports, lookups) stay on emit, and WARNING/ERROR lines log at those levels. print_calls ceiling 1,280 → 1,272 (measured).
- **A ZIP without its whole-genome GenBank no longer fails RG-GMCI.** With a MIBiG protein database found, reference-guided completion raised on region-only ZIPs (such as single-region downloads) and the strain run failed. Such a ZIP now gets the tier `NO_WHOLE_GENOME_GENBANK` on every pair and table row, and its pairs are kept as scored.
- **Standalone rggmci 1.0.0rc2.** Version bump, an rc2 CHANGELOG entry, and README and output-guide sections for reference-guided completion, `build-mibig-db`, read depth and residue tiling.
- **print_calls waiver retired.** The signed strict-health waiver no longer covered anything; strict health passes with no waiver.

Engine 1.9.172 unchanged: no score, confidence or threshold changes. The new completion tier appears only on region-only ZIPs, which failed before; ZIPs with a whole-genome GenBank, including every AS cohort ZIP, take the same path as in .445.

# v9.7.445 (2026-09-30) — build 20260930v97445a

- **Registry test discovery.** Owner-table tests discover the nearest governed table independently of bundle depth.
- **Packed lane wrapper.** Packed BLASTp lanes invoke their internal runner with bash.
- **Standalone package wording.** Standalone RG-GMCI descriptions and version output retain source provenance with independent package wording.
- **Rare genera outgroup snapshot.** The bundled rare-genera snapshot records the ruled Bifidobacterium accession; the external owner table remains authoritative.
- **Placement reference home.** Default reference packages stay beside explicit outputs or in the configured tree home.
- **RG GMCI depth and residue evidence.** Pairs expose contig-depth fields; optional DIAMOND residue evidence remains advisory and leaves scores and confidence unchanged.
- **Pipefail checks.** CHANGELOG and denylist gates avoid early-exit grep pipelines.
- **Asset registry discovery.** Copies of the asset tool outside the bundle can discover the registry marker.
- **Resolver authority and case.** Reader homes match case-insensitively and omit archives; an optional owner table admits clean packages and refuses mismatches. Authority population remains with the owner.
- **Product label comparisons.** Product comparisons normalize separators while preserving raw labels and the reconciliation enum.
- **Dominated diagnostic report.** A separate same-CDS warning channel proposes bitscore <=30 and an E-value gap >=20 orders; calibration required, with no score or tier change.

- **User docs and wiki mirrors.** Documents the built changes, repairs stale guidance and keeps eight wiki mirrors bound to their maintained sources.

- **Portable tree home and fixture environment.** Configurable tree outputs remove a private locator, and the pipefail test preserves the required child environment flag.

- **RG-GMCI reference-guided completion.** Each edge region's best MIBiG reference is searched across the whole genome by default when a MIBiG protein database and DIAMOND or BLAST+ are found: missing and split genes and tested partner contigs (`_4E_*` tables), and `completion_tier`, `ref_completion_partner` and `split_gene_links` on every pair. Otherwise the tier says what was missing. It runs in capped sessions too. With pyhmmer, the registered Pfam-A.hmm sets aside lone finds beside housekeeping genes. Report-only: no score or confidence changes. The gap-rescue tool and the standalone package run the same code.

- **Gap rescue split-gene check.** Adds synthetic-tested split-gene, partner/reference, locus-map and all-regions advisory outputs.
- **TIGRFAM competitor print-count fixture.** Updates the existing output-count fixture to include the report-only competitor reader.
- **Gap rescue standing-gate repairs.** Guard optional Bio imports, scope test monkeypatches, and log optional-output fallbacks and progress without increasing print-call ratchets.
- **Silent-swallow handlers logged; ceiling zero.** Debug records preserve fallback behavior while reducing the measured silent-swallow ceiling to zero.

Accretion-justified: mamey/residue_tiling.py — optional DIAMOND residue tiling for RG-GMCI pairs, report-only, shared byte-for-byte with the standalone rggmci package.
Accretion-justified: mamey/ref_completion.py — reference-guided completion for RG-GMCI and the gene table and split-gene check it shares with tools/gap_directed_rescue.py, report-only, shared byte-for-byte with the standalone rggmci package.

Engine 1.9.172 covers the unreleased cut: emitted depth/evidence, product-family handling, gap-rescue and reference-completion fields. The new completion card emits _4E tables and pair completion fields; the gap-rescue card adds advisory tool outputs. No extra engine increment within this one unreleased cut. RG-GMCI and gap rescue remain advisory; homology is not product identity.

# v9.7.444 · 2026-09-29 · build 20260929v97444a · engine 1.9.171 · CODE

Accretion-justified: mamey/rescue_groups.py — RG-GMCI candidate groups and group GenBank files, shared with the standalone rggmci package.

- **RG-GMCI pairs only contig-edge regions on different contigs.** Interior regions and two regions on one contig are never rescues. Their HIGH or MODERATE shared-reference signals go to a related-loci table with the reason; LOW signals are omitted. antiSMASH edge flags take priority, with engine edge status as fallback. Triage ignores these related pairs.
- **RG-GMCI shows why a pair was demoted, and the result no longer depends on the hash seed.** The ranked-pairs table carries its gate columns; adjacency ties break by locus count, then prefix.
- **Rescues become analysis units.** HIGH pairs that share a region form candidate groups. A group GenBank file is written only when every member file and complete identity is bound, for the completeness, compare and relate tools; glycosylated pathways split across contigs can now be called.
- **Three advisory tools read a split cluster against a reference.** KS placement on a reference's module order, a gene-by-gene synteny map, and a gap-directed search for missing reference genes anywhere in the genome, with contig-track figures drawing reciprocal best matches only. None changes a pair's score or confidence.
- **Product classes are counted from products, not category words.** antiSMASH category words are no longer product classes; figure and report groupings read antiSMASH families; GCF tags stop calling every unmatched type I PKS a polyene, and NAPAA stays out of NRPS in three tools.
- **The GenBank fallback reader keeps LOCUS name and DEFINITION.** This closes the reproduced replicon-order and BGC-alias mismatch when Biopython is absent; it does not establish universal parser equivalence. Region-only CDS and domains use contig coordinates.
- **RG-GMCI ships as a standalone package built from the bundle's source.** It is checked against the repository docs, with public fixtures.
- **An operator can run a handoff gate on supplied packets, deliverables and reply links before sending them.** It checks queue and hash drift, orphan cards, replay, links, four-part BGC identities and figure text.
- **Releases cut the CODE tier only.** The clean, cohort, merged and public tiers and the four-tier driver stay in the bundle but refuse to run unless SAPOTE_ENABLE_DISABLED_TIERS=1 (CUT_PROTOCOL.md).
- **Lab Quest is an optional add-on.** It moves to sapote_addons/lab_quest (package sapote_lab_quest) with unchanged behaviour; `lab-quest` appears only when installed, and the launcher's missing `mamey[labquest]` extra is gone.
- **One GToTree version list for planner, gate and doc.** 1.8.19 and 2.0.x are accepted and 1.8.16 is refused everywhere; `--threads-per-tree` (default 1) keeps the four-core ceiling.
- **Genome-tree panels can add named type strains past the related cap.** Type anchors need the type-material flag, are capped per query and listed in the receipt.
- **Phylogeny option and rendering fixes.** phylo-run forwards IQ-TREE threads, seed and tree spec; the genome-tree runner honours its ModelFinder restriction; EPA-ng reference branch lengths are restored from ref.tree, and default query pendants are re-estimated when RAxML-NG, alignments and model are available; placement figures wait until branch lengths are verified, and the report says what is missing; rect02 strip cells stay on their tips.
- **Test runs no longer rewrite a checksummed file in tools/.** Inspect-command paths and candidate-census links are safe (Codex audits).
- Standalone examples and placement fixes: the standalone package example states the engine's own counts; placement figures wait for verified branch lengths.
- Compose fixes: the handoff gate is registered; ten new test fixtures join the determinism inventory; no .444 addition names an AS strain or contig; the command catalog lists the Lab Quest add-on whether or not it is installed.
- Integration review fixes (9): reciprocal-only partner support, one protein one rival, placement bound to its reference, fail-closed hash and replay checks in the handoff gate, every diff in a card accounted for, coverage labels match their identity cut, group export refuses incomplete identities, and a core prefix must name one region.

Engine 1.9.171: RG-GMCI output changes (which pairs are rescues, the related-loci table, gate columns, rescue groups) and product-class counting changes. Boards from 1.9.170 are not directly poolable for RG-GMCI calls or class counts.

Scientific hold: gap-rescue deployment thresholds have not been accepted (public calibration: STRONG partner precision 2/7 on a sparse truth set); the tool ships as advisory only.

# v9.7.443 · 2026-09-26 · build 20260926v97443a · engine 1.9.170 · CODE

Accretion-justified: no new mamey runtime module. New operator surfaces: tools/check_no_bundle_write_defaults.py, tools/make_verified_code_tarball.sh, tools/blastp_crawl/.

- **Adjacent-cluster pairs report MODULAR_CONTINUATION.** The rescue read adds assembly-line and release-gene columns beside functional_rescue_class, never replacing it. Scoring and extraction files are byte-identical to v9.7.442.
- **Deliverable PDFs embed their fonts.** The shared ReportLab renderer registers a TrueType family and refuses when none is found, so md_to_pdf.sh falls back to pandoc+xelatex; it never writes unembedded base-14 fonts.
- **Release tarball verification is receipt-bound.** Identity v3 plus membership, mode, streaming, member-count, path and ZIP-snapshot guards; CODE tarballs go through make_verified_code_tarball.sh.
- **Figure text is checked where it is drawn.** Figure QC binds its review manifest to the images, guards SVG text, and fails closed on OCR errors and invalid UTF-8 captions; a test-time page-text ratchet can only shrink its exemptions.
- **Writes stay out of the code bundle.** A new check_no_bundle_write_defaults gate (registered WIRED); BLASTp output, deliverable builders, the outgroup cache and crawl plots refuse bundle-internal output.
- **Bioassay inputs and contig rosters fail closed.** Rulings and source-column inventory with reasons, row-width guards, immutable input snapshots, plan hash binding; one removed-contig reader and strict bin values.
- **Runner and provenance bind what they run.** Bytecode cache marker bound to source content; run failures name the refusal; provenance logs session identity; intake and queue-resume fail closed.
- **Mode B reports true reasons and numeric identities.** BiG-SCAPE holds give the actual reason; template sources reach every route; percent identity must be a finite 0-100 value.
- **BLASTp crawl ships in tools, and says when its heartbeat is off.** RID runner, crawl handoff, health table and plots; runner failures are reported instead of swallowed. The crawl folder is exempt from print_calls only.
- Documentation: 24 operator-doc corrections, the W380 residual, plot-example wording at 300 dpi, owner-doc delta UD005; v9.7.441 release notes move to docs/history.
- Cut fixes: the new gate is registered; two test harnesses repaired; two clean figure sites leave the known-sites list; the phylo_place known-sites addendum was dropped.

Engine 1.9.170: emitted-output bump only (new pair columns). Scoring is unchanged and boards stay poolable with 1.9.169.

Not included: product/category separation (deferred by owner decision to a family-count card), held privacy-policy cards, the preliminary card census, superseded seal-binding v2 and AppleDouble guard.

# v9.7.442 · 2026-09-24 · build 20260924v97442a · engine 1.9.169 · CODE

- Accretion-justified: mamey/figure_policy.py — one shared check for text drawn on figures, used by the figure save path.

- **Figures carry no claim text on the canvas.** The shared save path stops drawing the claim footer and refuses banned wording; claim guards stay in the figure receipt and caption. Adds a caption band tool, a render QC that reads the text drawn on figures, an R publication-layout helper and a one-page figure house-rules document. The KCB novelty title drops its claim wording; the house-rules page now says which saves the check covers, and a test keeps the list of remaining draw sites from growing.
- **BiG-SCAPE inputs fail closed.** Staging can drop decontaminated contigs and refuses a drop list that matches nothing; a decontamination guard refuses missing region roots and manifests; product parking matches hybrid tokens.
- **Region counts refuse mixed antiSMASH strictness.** A one-setting region table validates identity, duplicates, headers and corrupt ZIPs; the profile checker marks ambiguous or blank profiles unknown; cohort figures refuse mixed strictness.
- **Mode B template binds full locus identity.** Cross-source prefill and identity-bearing filenames; a BiG-SCAPE lookup now requires strain, contig and region.
- **Session hook binds an explicitly located code root.** It no longer calls the highest versioned folder current, and no longer tells chats to write the retired shared colour marker.
- **BLASTp concurrency hook resolves wrapped launchers.** Interpreter, env, nohup, caffeinate and chained launches are recognized.
- **Output containment is one shared helper.** MIBiG neighborhood output adopts it and refuses path-bearing labels.
- **Release tarball excludes AppleDouble members, with a verifier.** The R installer honors dependency order and refuses online fallback for an offline route.
- **Silent failures now leave breadcrumbs.** An unreadable antiSMASH input ZIP no longer silently disables the gene-count cross-check; an unreadable intake file no longer drops the antiSMASH profile unrecorded; silent swallows fall from 14 to 13. Five new operator front doors join the terminal-output exemption; two tools with importable helpers stay counted.
- Adds a deposited 16S similarity check tool.
- The decontamination guard and one-setting region table no longer carry strain IDs or per-strain BGC detail in their docstrings.
- Operator TSV outputs from the four new count and QC tools go through the shared safe writers; three new operator gates are registered.
- NOTICE now credits the bundled ijson fallback (BSD 3-Clause) and the three build wheels.

Engine remains 1.9.169: extraction, scoring, evidence admission and scientific thresholds are unchanged. This is a locally validated candidate; public disclosure and publication approval remain separate.

Not included: the runner bytecode-cache guards (they refused every run after an ordinary import; moved to a later cut), the public-tier contig-name scan (privacy policy pending), the installed workspace session hook, privacy tiers, and the output-containment adoption for the outgroup registry.

# v9.7.441 · 2026-09-24 · build 20260924v97441b · engine 1.9.169 · CODE

Build b removes `bundle_support/vendor/ggrepel-master.zip` (5.8 MB), which build a shipped: ggrepel is GPL-3 and this CODE tier is MIT, and no bundle code needs it at runtime. The R installer's offline route now takes an operator-supplied `--from <dir>`. No other change from build a.

Accretion-justified: no new mamey runtime module. New standalone track adapter and R display helpers bridge the existing admitted Figure Factory contract.

- **Bundle-pinned execution and identity refusal.** Launch child commands through the bundled runner; detect stale engine or bundle-version bytecode; report mismatched child engine receipts before trusting intake output.
- **Portable placement assets and output containment.** Resolve workspace assets through explicit roots or verified marker parents, diagnose missing companion binaries, accept documented flat placement layouts, normalize merged FASTA deflines, and refuse reference-package output inside the bundle, including symlink routes.
- **Admitted assay tracks on existing trees.** Join exact tip crosswalks to hash-bound Figure Factory selections. Preserve zero, negative and unmeasured values; support configurable display thresholds and explicit reference labels. Ship generic fixtures and single/grouped R renderers, with no project-specific pooling or taxonomy inference.
- **Re-authored clinker and cohort controls.** Bound long-label layout, deterministic row order, visible hidden-track counts, valid query regexes, full deposited labels and centered PDFs. Add opt-in product parking and explicit query-only CDS-count staging filters with provenance receipts; preserve reference inputs and join keys.
- **Companion setup and documentation.** Prepend the active interpreter bin for BiG-SCAPE subprocesses; document optional R dependencies, provide installer readiness checks and an operator-supplied `--from <dir>` offline route (no third-party package source is vendored); regenerate inventories and observed health metrics.

Engine remains 1.9.169. No scoring threshold, scientific acceptance, publication authority or owner seal is changed. A local engineering cut candidate requires its own source and extracted-archive validation; consult RELEASE_MANIFEST.md for the measured status.

# v9.7.440 · 2026-09-22 · build 20260922v97440c · engine 1.9.169 · CODE

- **Receipt-hash spacing correction.** Whole SHA-256 receipt identifiers no longer trigger prose spacing holds; generic regression tests retain hash tamper detection.
- **BLASTp empty-discovery diagnostics and retry safety.** Package-trove scans that discover no supported source now explain the scanned layout and channel filenames, and leave no new overlay, ledger or immutable receipt. Sources that contain no admitted rows retain their normal evidence receipts; admission and quarantine rules are unchanged.
- **Complete rollup hit preservation.** Reservoir imports retain distinct hit-rank and subject-accession keys, rescan previously seen source paths to recover missing ranks, and preserve existing rows and provenance across idempotent retries.
- **Intake taxonomy and failure reporting.** Normalize placeholder GBK organism values to explicit unresolved taxonomy, reject placeholder entries in taxonomy maps before execution, and surface a bounded engine failure reason without changing the checkpoint CSV schema.
- **Portable tree-source export.** Import the success-output dependency and quote every value interpolated into the generated rerender helper; retain executable regression coverage for ordinary and shell-sensitive filenames.
- **Manifest and documentation accuracy.** Derive the observed terminal-emission metric from current source, distinguish the three BLASTp ingest destinations, and escape domain pipes in the Mode B substrate table.

Engine remains 1.9.169: extraction, scoring, evidence admission and scientific thresholds are unchanged. This is a locally validated candidate; public disclosure and publication approval remain separate.

Not included: new assembly-size heuristics, optional reference-genome acquisition, historical vocabulary redesign, workspace database mutation, or relaxation of strict source-disclosure policy. Historical figure-median and matrix-test-discovery findings are already resolved in the baseline.


# Earlier versions

Entries for v9.7.439 and earlier are in the CHANGELOG.md of every earlier release on GitHub, for example https://github.com/alexanderjsmith1/sapote-mamey/releases/tag/v9.7.448b. They were removed here to keep the bundle small.
