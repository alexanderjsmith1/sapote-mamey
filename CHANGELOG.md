# v9.7.460 — unsealed cut candidate · build 20261027v97460a

Build 20261027v97460a; engine 1.9.177.

Builds on the sealed v9.7.459 (CODE zip, build 20261027v97459a). The engine stays 1.9.177: no card changes RG-GMCI scores, ranks, thresholds or KCB values.

- **Metadata as deposited.** The 16S admission gate no longer refuses a whole roster when one row has no deposited isolation source. Isolation source now follows the geography rule: each tip carries its source exactly as deposited, and a tip with none is admitted and listed for omission from figures, with reason `NO_DEPOSITED_SOURCE`. A tip missing both is listed under both reasons. Accession and the evidence fields are still required.
- **Mode B ingest.** `ingest-receipts --card` no longer prints "structure: PASS" for a card the gate never checked, such as a card for a BGC already COMPLETE or one the register does not know. It prints "NOT EVALUATED" with the reason, and the result carries `structure_evaluated`.
- **No hidden package scans.** `tools/build_bgc_markers.py` and `tools/build_deep_data.py` read only the folders named in `MAMEY_PACKAGES`. Before, they also scanned shared `/tmp` folders and an old hosted-sandbox upload path, so packages from another run could enter a bank. The add-on installer no longer searches that upload path for wheels.
- **doctor** checks PyYAML, a declared core dependency, the same way it checks ijson.
- **Figures.**
  - The cohort figures no longer draw "novelty-leaning" on the plot; captions are unchanged.
  - The thesis method diagram drops "not saturated".
  - Reference labels from `tools/max4_tree_figure.py` put the accession in brackets, as the house rules and `bind_panel_metadata.py` do.
  - `tools/scan_prevalence.py` writes the `AUDIT_RECEIPT.json` its widget footer points to.
- **Tests.**
  - 22 exact duplicate tests are removed, including one whole file that another file already contained.
  - The docs line-reference ceiling drops to 72, measured.
- **Generated surfaces** are regenerated once, by the last card: the file atlas and the maintenance inventory.

Known limits, for later:
- The Mode B register still marks shallow cards COMPLETE. The fix, which also extends the seal checks to DRAFT cards, is held for its test updates.
- v2-only literature checks are not yet run at ingest.
- `test_release_cut_partition_mode` needs a real filesystem, not a sandbox.

# v9.7.459 — unsealed cut candidate · build 20261027v97459a

Build 20261027v97459a; engine 1.9.177.

Builds on the sealed v9.7.458 (CODE zip, build 20261026v97458a). The engine stays 1.9.177: no card changes RG-GMCI scores, ranks, thresholds or KCB values.

- **Metadata as deposited.**
  - The 16S admission gate no longer refuses a geography that is not one of ten regions. It keeps the deposited text on each tip of its receipt and adds a separate display field, `geography_region`, filled only from an exact list value or the bundle's country table. The receipt says in one line that the deposited text is the record and the region is display-only. A tip with no deposited geography is admitted, left blank and listed for omission from figures by full name.
  - Placement tip labels show the deposited country, not a continent.
  - `tools/bind_panel_metadata.py` writes the accession in brackets.
- **Defaults and help.**
  - `phylo-run` defaults to one GToTree job of four threads (`--parallel 1`). Before, it ran two jobs of four threads at once.
  - `doctor` no longer calls a missing core dependency optional, and its no-ZIP warning names flags that exist.
  - The `INBOX_REQUIRED` refusal names the `strain-master apply` step. Before, it said `import`, which is not an action.
  - `--genus-color` is the listed flag on the two figure tools that took only `--genus-colour`; the old spelling still works. Help and captions use American spelling.
  - `tools/export_figure_ready.py --help` and `tools/plot_examples.py --help` print usage instead of a traceback.
- **Figures.**
  - Locus map v8 writes its PNG at 300 DPI.
  - KCB and GCF figures use neutral wording on the plot.
  - The pangenome summary drops a "not saturated" sentence the data did not support.
  - The domain-prevalence widget's footer reports channel coverage from its input.
  - Strain decks give no region slide to a region whose only call is hydrogen cyanide.
  - The figure review queue: decision import matches a figure ID written with the spreadsheet formula guard, so IDs that start with `=`, `+`, `-` or `@` rejoin on rebuild. An ID that really starts with an apostrophe keeps it.
- **Smaller fixes.**
  - Enzyme neighborhoods: the receipt's scope text follows its counts.
  - Evidence disagreements: the audit file is created exclusively, so an earlier audit is never overwritten.
  - Normalization ranking: a non-finite correlation reads "not measurable", not "mild".
  - The reference panel ledger has no workspace default path, and exits non-zero when it finds no rows.
  - A comment in `mamey/antismash_evidence.py` now matches the JSON-mode code.
  - The Mode B registry CSV is generated from the JSON, so the two cannot disagree. The exporter writes through the bundle's formula-guarded CSV writer.
  - The document factory checks a card against the named contract in its header.
- **CI.** The two six-inch K01 layout tests carry the `needs_arial` marker, so they skip where Arial is absent, as on Linux CI. They failed there on v9.7.458. The print-call ceiling is 1250, measured.
- **Generated surfaces** are regenerated once, by the last card: the tool inventory, capabilities block, maintenance inventory and file atlas.

Known limits, for later:
- The register still marks SHALLOW and STUB Mode B cards COMPLETE. The fix, which also extends the seal checks to DRAFT cards, is held for its test updates.
- v2-only literature checks at ingest are not yet run.
- A missing isolation source still refuses a whole 16S roster. This waits on an owner ruling.
- `test_release_cut_partition_mode` needs a real filesystem, not a sandbox.

# v9.7.458 — unsealed cut candidate · build 20261026v97458a

Build 20261026v97458a; engine 1.9.177.

Builds on the sealed v9.7.457 (CODE zip, build 20261023v97457a). The engine stays 1.9.177: no card changes RG-GMCI scores, ranks, thresholds or KCB values. One engine output changes by owner ruling. A single-region public accession input now keeps its accession as the strain ID; before, it could get a derived or filename-based ID.

- **User docs, rewritten for a reader opening the bundle cold.** Measured on reader pages against sealed .457:
  - source line references: 539 → 73;
  - sentences over 40 words: 2,446 → 1,113;
  - hedge phrases: 966 → 845;
  - words: 892k → 646k.

  The work came in five parts:
  - all 16 docs-review batches, applied page by page;
  - six reader-path audits (front door, analysis, companion tools, cohort and data, figures, troubleshooting), each command and flag checked against the parser;
  - first-use definitions on the reader path;
  - over 100 retired or superseded pages moved to `docs/history/`, with banners and pointer pages;
  - the bundle monolith's design history split into `docs/history/MONOLITH_DESIGN_HISTORY.md`.

  A new test stops line references and long sentences from growing back.
- **Mode B ingest.**
  - `ingest-receipts` now checks each card against the contract named in its header, or against `--contract`. Cards written to the current50_v2 profile can be recorded; before, they were refused with title mismatches.
  - `ingest-receipts` refreshes the post-seal checksums, so a later `validate` no longer flags recorded cards as injected.
- **Strain Master.**
  - After a failed master-workbook update, the run prints the inbox route that works: submit, then verify, then apply. Before, it printed an `ingest_package.py --master` command that does not exist.
  - The README written by `strain-master init` names that route.
- **Identity and metadata.**
  - Single-region accession inputs keep the accession as the strain ID (see above).
  - `tools/strain_level_bgc_logic.py` counts strains and loci from its input instead of printing fixed numbers.
- **Figures.**
  - Render QC measures the smallest text at print width; `--min-text-pt` defaults to 8.
  - Placement activity legend per ruling 314: "strong (≥80%)" and "tested, below 80%". An opt-in three-state view is added.
  - Locus maps fit a landscape page.
  - TriMap pages: the corner-tick collision is fixed.
  - Bioassay figures:
    - pale last columns are no longer clipped;
    - species names in titles are italic;
    - family names are always roman;
    - the bee and attine A06 panels show all groups.
- **Codex hardening cards R458_36 to R458_60.**
  - Seeded BiG-SCAPE runs refuse randomized hashing, and the final receipt is written atomically.
  - A producer map without a declared source is refused.
  - Outgroup and panel admission are stricter.
  - Standalone receipts and round-trip checks are exact.
  - Checkpoint and freshness bounds are enforced.
  - Markdown appendices are preserved.
- **Help text and smaller fixes.** These help texts no longer mislead: `figures gcf-network --run` (no "largest is authoritative"), `guide --bgc` (gene-table order), `render-figures --outdir` (one default folder per figure set), and `emit-modeb-template` (American spelling).
- **CI.**
  - The print-call ceiling is 1251, measured.
  - The companion-instruction policy follows the current page wording.
  - The retired-mode scan treats `docs/history/` as archival.
- **Generated surfaces** are regenerated once, by the last card in the stack: the tool inventory, capabilities block, maintenance inventory, file atlas, command catalog, wiki mirrors and deliverable menu.

- **Correction to the minimum-text check entry in v9.7.457.** That entry overstated the evidence for tree-figure text being read as 1 pt. The retained baseline record did not reproduce the fault: all eight synthetic cases passed without the proposed adapter, and no code change was admitted. Reproducing the original environment and the affected PDF is still needed before choosing a fix. The page-fit floor is a separate change.

Known limits, for later (prepared for v9.7.459 or held for the owner):
- KCB band cut points are on the wrong scale for raw bitscores, and the KCB score and its reference can come from different records. Both are being carded for .459, each with a list of the loci that change.
- The register marks SHALLOW and STUB Mode B cards COMPLETE.
- `phylo-run` defaults to two parallel jobs of four threads.
- Placement tip labels bin countries into continents by default.
- The six known defects listed under decisions row 71 are carded for .459. Their pages warn about each one.
- A missing isolation source refuses a whole 16S roster. This waits on an owner ruling.
- 17 Arial-metric tests skip on CI. `test_release_cut_partition_mode` needs a real filesystem, not a sandbox.

# v9.7.457 — unsealed cut candidate · build 20261023v97457a

Build 20261023v97457a; engine 1.9.177.

Builds on the sealed v9.7.456 (CODE zip f2e315d1…ab92). The engine stays 1.9.177: no card changes RG-GMCI scores, ranks, thresholds or engine outputs.

- **Locus and protein-space pages.**
  - Locus figure pages and locus protein-space pages are new routes. Protein-space pages take `--cohort-point-scale`; figures are unchanged without it.
  - Comparison maps get page output.
  - The locus map takes a height option.
  - Region-protein figures share one comparator row.
  - HTML entities in locus-map labels are decoded.
  - The PCoA legend no longer lists MIBiG.
- **Trees and bioassay figures.**
  - Tree and dDDH figures gain layout options.
  - New HPLC and novel-active figure routes.
  - `tools/render_max4_tree.R` works from a script path that contains spaces.
- **GECCO.**
  - New cohort report, with `--summary` and `--per-mb` outputs.
  - Multi-reference comparison maps draw GECCO strips. Reading them needs optional Biopython and says so when it is missing.
- **Rarity and presence.**
  - Rarity by assembly is now the default view.
  - New family rarity by window and a region presence survey.
- **Manuscript revision kit.** New tools for tracking manuscript revisions.
- **Receipt verifiers.** The external receipt verifier gains a final-summary lane, a format-refusal lane and a record-admission lane. Input genome sequences are preserved byte for byte.
- **BiG-SCAPE and R.** BiG-SCAPE runs can be seeded for reproducible output. Rscript calls work from paths with spaces. `readxl` joins the R figure packages.
- **Min-text check.** The PDF minimum-text checker reads a text matrix correctly. Before, some tree-figure text was read as 1 pt. The page-fit floor is a half point.
- **Nine opt-in tools promoted.** Bioassay paper set, BiG-SLiCE overview, core amino acids by class, palette edge options, placement tree pages, region identity dot plot, family network page, in-vivo paired dose and September routes. All are opt-in. Their figure output has not had a visual parity review.
- **CI and tests.** The stem-aware gate finds bundle tools. Arial-metric tests carry a `needs_arial` marker. The print-call ceiling is 1242, recorded in the release manifest.
- **Generated surfaces** (tool inventory, capabilities block, maintenance inventory, file atlas, command catalog, wiki mirrors, deliverable menu) are regenerated once, at the end of the stack.

Known limits, for later:
- PCoA label inputs are read before they are bound.
- Grid pages do not record their R execution evidence.
- Manuscript QA can accept a coauthor's reference for a citation.
- A locus page shows unassignable GECCO evidence as "no recorded cluster".
- A Strain Master import that crashes partway can leave a partial install; a retry completes it.
- One `nonstrep_counts` fixture test is skipped.
- 17 Arial-metric tests skip on CI.
- Three `test_452_required_identity_tokens` errors appear only when the whole suite runs in one order; they also occur on the sealed .456.
- The multi-reference GECCO ledger (held card) is not in this cut: it runs on every region call and withholds figures when no evidence file is given.
# v9.7.456 — unsealed cut candidate · build 20261021v97456a

Build 20261021v97456a; engine 1.9.177.

Builds on the sealed v9.7.455 (CODE zip 42d06b36…1096). The engine stays 1.9.177: no card changes RG-GMCI scores, ranks, thresholds or engine outputs.

- **Strain Master parity.** The bundle's user Strain Master gains the working master's tools:
  - `import-tree` copies a folder with its subfolders, with `--tree-dest`, `--exclude`, `--link` (hard links) and `--replace` (older files move to `Superseded/`);
  - `record-replace` replaces a whole record table, refused if the table changed since submission;
  - subfolder READMEs are listed in the parent README;
  - the self-check confirms that copies match their sources.

  Imports check the whole write plan before any write. They refuse symlinked path components and any path that resolves outside the master, and a refused import can be retried. Backups are created exclusively and never overwrite an existing file. The user-facing name is "Strain Master"; `strain_master.json`, the module and the `strain-master` command are unchanged, so existing masters keep working.
- **Protein-space pages.** One rebased card brings in four things:
  - explicit point labels (`--label-ids`);
  - labels by region alias (`--label-regions`);
  - low-identity labels;
  - multi-set grids zoomed to the isolates.

  In grid mode, coordinates go through the same one-to-one admission as single pages, so a repeated ID is refused. Grid captions count proteins with unknown identity separately and describe axis values by what is known about them. The native R PNG is kept; a Quick Look preview, when made, is a separate review-only file. `--ref-point-scale` is a new opt-in option, and figures are unchanged without it.
- **Gap-rescue maps and tables.**
  - The gene table records gene positions, and every piece of a split gene is checked against its own saved contig.
  - The map can draw a GECCO track. GECCO calls join by exact contig name, or by a contig-length alias only when that alias is unique on both sides; anything else is left unjoined and counted.
  - Locus pages match GECCO by contig.
  - Maps title GenBank references by name.
- **Figure layout.**
  - The collection map can place pies on their sites.
  - BLASTp group labels are bold and below the panels.
  - Nearest-type maps get row height and a four-host palette.
  - Panel keys fit the page width.
  - Placement pages get height control and landscape pages.
  - A new genome-tree renderer, `tools/render_max4_tree.R`, works at 8 pt and stamps its output. It needs `phangorn`, which joins the `trees` R group.
  - Multi-reference comparison maps get an aligned layout and italic binomials. A comparison row shows the record's accession, not a strain token that looks like one.
  - Moss figures draw *Pseudonocardia* orange.
- **Bioassay figures.**
  - Groups are passed to the renderers in alphabetical order, so a group keeps one shape across figures; the owner ruled on this change of default.
  - A07 reads its label seed and an x-axis limit from the environment.
  - A04 reads its seed and a padding multiplier, and gains a label limit, a compact legend and an "either" label mode.

  Unset options leave every figure as before.
- **Size profiles.** `tools/build_size_profile.py` takes a unit label and a supplied table, and draws at print size.
- **Manuscript QA.** The new tool `tools/manuscript_qa.py` checks a manuscript's citations against its reference list.
- **CI and tests.**
  - The CI test job runs Python 3.13. A step proves that R can start that Python with pypdf and Biopython.
  - CI installs Arial-metric fonts, and a step checks which font R matches.
  - Page-width checks allow half a point.
  - One R test keeps R's library path.
  - Two release-workflow probe deadlines are longer (5 s → 60 s, 30 s → 300 s); a refusal is still a refusal.
  - The watched PCoA worker's disk floor leaves 1 GiB for other programs' writes; the hard floor is unchanged.
- **Housekeeping.**
  - The retired `tools/build_master_figure_atlas.py` stub is removed.
  - The headers of `tools/build_master.py` and `tools/mamey_package_qa_v2.py` now say they are still in use.
  - The release manifest records 1241 print calls, which is also the ceiling.

Known limits, for .457:
- PCoA label inputs are read before they are bound. An explicitly empty label list falls back to automatic labels, and conflicting label keys take the last row. Single panels can ignore region aliases. Grid captions do not state a non-default quantile.
- Grid pages do not record their R execution evidence.
- Manuscript QA can accept a coauthor's reference for a citation.
- A locus page shows unassignable GECCO evidence as "no recorded cluster".
- A Strain Master import that crashes partway can leave a partial install; a retry completes it.

Held for later: the BLASTp known-compound tier fix (needs an old-versus-new comparison on real packages first) and the DAPR board locator hold (awaiting a ruling).
# v9.7.455 — unsealed cut candidate · build 20261019v97455a

Build 20261019v97455a; engine 1.9.177.

Builds on the sealed v9.7.454 (CODE zip 873e0755…1614). The engine moves to 1.9.177 because the split-cluster second proof changes its default and three engine outputs gain fields. RG-GMCI scores, ranks and thresholds are unchanged.

- **The split-cluster second proof is routed by class, by default.** A pair with a KS domain keeps the KS-clade route. Other classes use core completion: the two pieces together complete a class core that neither completes alone. A duplicated single-copy marker or a far-apart complete relative vetoes the pair, and a matching position alone never promotes it. The readings come from the run's own antiSMASH archive through the new `mamey/split_evidence_layers.py`, a port of the RG-GMCI benchmark scorecard. `_4D` gains a `core_completion` column, and `two-proof-rescue` accepts `--input-zip`. `ks_clade_v2` and `nonks_position_v1` stay selectable. The 50-gene and 70% values were set on the lineage benchmark and are not validated on held-out data.
- **A two-proof rescue needs a HIGH pair on both routes.** Before, the KS route accepted a MODERATE pair as TWO_PROOF_RESCUE while the class-routed route needed HIGH. A MODERATE pair with both proofs now stays RGGMCI_ONLY and keeps its KS clade ID. This can only lower a verdict.
- **R figure packages come in groups; only the core group is required.** `core` serves every R figure. `trees` (ape, ggtree, treeio, aplot), `bioassay` (tidyr, png) and `extras` (ragg, ggchicklet) each add one figure family; a missing one is reported, not fatal, and `--require <group>` or `--require all` makes it required. GitHub CI uses `--require all`, so every R test still runs. `doctor` prints one line per group with the missing packages and the fix. ggchicklet now comes from a source archive pinned to one commit, with no GitHub API call; the .454 CI run failed on that call (HTTP 401) before pytest started. Without it, the class-group chart draws plain bars instead of rounded ones. The TYGS script no longer needs readr (its figures are byte-identical). `docs/PREREQUISITES.md` lists the groups in one table.
- **Missing is not zero in cross-strain figures.** A blank, NA or unbound count no longer becomes 0 in the fragmentation-loss, HIGH/MODERATE, by-strain and assembly-tier charts. Missing values are left undrawn, and observed zeros are still drawn.
- **The assembly check has a ceiling.** `assembly_sanity_check` flags an assembly above 12 Mb as INFLATED_ASSEMBLY_SUSPECT, with its own warning, matching the operator QC tool.
- **NP Atlas readiness reads the right files.** `doctor` and the external-data status add consumer-readiness fields read from the two `*_npatlas_ref.json` files the resolver loads. `provisioned` keeps its meaning.
- **The BLASTp runner stops re-downloading an unreadable result.** A READY request whose result cannot be read is counted on disk. After three failures it is held as `unsure`, the raw responses are kept, and the count survives a restart. Transport errors do not count.
- **The genome inside an antiSMASH ZIP can be written out.** The new `tools/antismash_input_genome.py` writes the `input/` genome as FASTA. `docs/COMPANION_FILES.md` no longer tells assistants to ask for genome files the ZIP already holds.
- **t-SNE beside PCoA.** `tools/protein_pcoa_ordinate.py tsne` fits the t-SNE layout inside the bundle (perplexity 40, seed 20261019 by default) and writes the table and sidecar the renderer credits. scikit-learn joins the figures extra.
- **Docs say what the code does.** Sixteen docs no longer claim `doctor` can overwrite its probe file; it refuses an occupied one. The Encyclopedia Volume XII worked example states capacity only. One intake directive links `prompts/FULL_RUN_PROFILE.md`. A wiki page no longer credits an assistant by name.
- **Figure routes.** The b03 comparator figure gains a label option. Bioassay A01 uses a linear axis for small rows, and the bioassay columns and A04 panel are sized for print. The BLASTp by-genome figure puts the genus key under panel A, and the by-class full grid gets a row gap. Locus maps draw longer ribbons and use set page widths.
- **PCoA scratch stays in the attempt folder.** Clustering scratch goes under the attempt's resource folder unless `--cluster-work-root` is given.
- **Tree display options v3.** It replaces v2 and replays its three v2 settings. The page title stays opt-in, as in .454.
- **Two new tools.** `tools/locus_rarity_by_genus.py` counts locus rarity within each genus, keeping public genomes and SID apart. `tools/pks_piece_map.py` maps PKS pieces across contigs.
- **The strain data home has a written contract.** `mamey/strain_master.py` reads and writes the user's strain master through the bundle's safe CSV writers.
- **Comments say what the code does.** Eight comments and help texts were corrected, among them subject tiling (it can lower confidence), the strong-support count, the class-routed help, and the gap-rescue tool versus the engine.
- **Tests.** The runner's build line and shadow-package warning have tests. A figure-text known site that now renders clean is removed from the list, and the ratchet keeps it out.
- Accretion-justified: mamey/split_evidence_layers.py — the RG-GMCI benchmark scorecard (single-copy-marker conflict and intact-relative position) moved into the bundle so the class-routed second proof reads the run's own archive; report-only layers, no scores changed.

Held for later: the BLASTp known-compound tier fix (needs an old-versus-new comparison on real packages first) and the DAPR board locator hold (awaiting a ruling).

# v9.7.454 — unsealed cut candidate · build 20261019v97454a

Build 20261019v97454a; engine 1.9.176 (unchanged).

Builds on the v9.7.453 cut (CODE zip 0a5c8079…3149), which was pushed to GitHub but not sealed. The engine stays 1.9.176: scores, thresholds and routing rules are unchanged. The engine edits change only:
- whether a report rewrites a sealed package's status file;
- when the deliverable queue may skip a finished strain;
- how the paper bioassay figures are drawn;
- where duplicate terminal-output calls live.

- **The README names everything the code depends on.** It adds rows for 22 tools, among them nine R packages including ggrepel, RiPPER, DeepBGC, CheckM2, Poppler, headless Chrome and the companion-registry tools. It also adds a table of Python libraries by extra, and an Online services table that says which services receive uploaded sequences. A new guard test fails the cut when code imports a library, runs a program, loads an R package or contacts a web host the README does not name, or when a tool in the companion registry is missing from the README.
- **The R installer covers every package the figures load.** `ragg` is added from CRAN and `ggchicklet` from its author's GitHub. GitHub CI installs `libwebp-dev` for ragg. The installer's completeness test now also reads R code embedded in Python tools.
- **GitHub CI runs pytest without writing bytecode.** The default and public test steps use `python -B -m pytest -p no:cacheprovider` with `PYTHONDONTWRITEBYTECODE=1`, as the cut does, so the bundle runner no longer refuses tests with BYTECODE_WRITES_DISABLED.
- **compile-report reads a sealed package read-only.** Validation of a sealed original no longer rewrites its `package_status.json`. A new test checks this with the real validator, on success, on refusal and on a repeated run. A pre-seal working package keeps its construction-time status write.
- **The deliverable queue resumes only when nothing changed.** A DONE strain is skipped only while its package bytes, delivered outputs and run context (including the activity table's bytes) match the DONE record. Ledger records from earlier versions are rerun rather than trusted.
- **The paper bioassay figures are drawn by the bundle.** Five renderer cards, signed off by the owner on 19 Oct:
  - material labels on every axis and a host-group legend for the bee profile;
  - HPLC fractions as their own material, never pooled with flash fractions;
  - every panel saved at the 7.2 in double-column width and centered;
  - no panel for an unnamed *Candida* screen in the moss and attine profiles;
  - A07, which draws every fraction, and A03 point labels by genus.
  Re-rendering all 25 panels of the three papers from this source, with the papers' own inputs, gives the same SVG and PNG files as the panels placed in the drafts. The one exception is two labels 0.01 px apart in one panel, drawn from an earlier version of the input table.
- **Bioassay tests follow those renderer cards.** The A04 page-width test expects 7.2 in. The A04 pooled-pixel fixture uses the new label settings, so labels clear their points. The A01 moss-target test no longer expects the unnamed-*Candida* panel.
- **Gene tables keep contig names exactly.** `tools/gap_rescue_gene_table.py` read contig names through Biopython's record id. That id drops a 0 that follows the decimal point of a SPAdes coverage, so `cov_28.095673` became `cov_28.95673`. The table now uses the engine's contig name.
- **More of the papers' figure tools ship in the bundle.**
  - The region-protein-by-genus plot without role jitter (f3b).
  - The paper flow diagrams.
  - Overflow pages and data-led axis breaks for the public genome families plot (B04).
  - A plural fix in the PCoA page caption.
  - Source-style colour options for the PCoA renderer. These are renderer options; figures are unchanged by default.
  - A new chitin genome census tool, whose table the chitin isolate-versus-references panel reads.
- **Fewer direct terminal-output calls.** 29 duplicate emission sites were folded into per-file helpers, with byte-identical output. The strict-health ceiling goes from 1,268 to 1,239, then to 1,240 for the census tool's one output site.
- **A strain roster with an evidence map.** The new `tools/paper_cohort_registry.py` builds, from a workspace spec, the union of the tables that list a study's strains. For each strain it shows which table lists it and where its 16S, genome, antiSMASH, package, TYGS, ANI, bioassay, BLASTp, tree and card data are stored. It finds the zips and packages through the bundle's own resolver. Every disagreement between sources is listed, and none is resolved. The tool has no terminal-output site.

Not in this cut:
- **Deferred to .455, with the reason:**
  - the PCoA multi-set grid (it collides with this version's page provenance binding, and no placed figure uses it);
  - PCoA admission after clustering (the admission code was redesigned);
  - the BLASTp identity figures card (the tool's data model changed);
  - T06 label nudges (its hygiene test flags two leak-scanner tools);
  - 18 cards that are partly present.
- **Dropped:**
  - placement group suffixes (tip labels carry names only, the owner's 14 Oct rule);
  - the attine bioassay profile card (it would change the placed Attine panels).

Linux CI: GitHub CI on the v9.7.453 push (main f64f656) failed 106 tests. These cards address about 48 of them (bytecode refusals and missing R packages). About 28 remain open, from Linux text fitting and from imports in child processes, and need a Linux run to diagnose.
# v9.7.453 — unsealed cut candidate · build 20261018v97453a

Build 20261018v97453a; engine 1.9.176 (unchanged).

This cut carries the October 17 improvement campaign on top of sealed v9.7.452 (CODE zip 8c57b2e3…fcd), plus four cut fixes. The later Source166/nf-core integration batch and the BGC machinery-tree prototype are not included. The engine stays 1.9.176: scores, thresholds and routing rules are unchanged. The scoring and rules files change only in comments and a policy ID that no code reads. The other engine changes refuse bad inputs that were admitted before; they do not change results for good inputs.

- **Analysis inputs are read from one bound snapshot.** A new opt-in captured-intake route records the exact bytes of an antiSMASH ZIP once and reads every member from that recorded copy, so a ZIP that changes mid-run cannot mix two versions. Readers moved to the source-binding path include the parsers, antiSMASH evidence, NRPS predictions, the KS scan and RG-GMCI. A FASTA whose contig ID names two different sequences is refused. The captured route covers intake only; gold analysis, Mode B, RG-GMCI, resume and batch use the existing route.
- **Neutral public names replace internal code names.** Package homes default to `mamey_packages` and `Package Outputs*`; `MAMEY_PACKAGE_HOMES` still adds more. Historical rule labels in shipped data become neutral IDs (the inventory bottom-tier policy is now `inventory-bottom-tier-v1`); its routing is unchanged. See `docs/CODE_NAME_MIGRATION.md`.
- **Test identifiers have one role table and an optional registry guard.** `tools/identifier_source_roles.py` validates one source-site role table for tests and staged artifacts. `tools/synthetic_id_registry_guard.py` and `tools/verify_export_registry.py` can check declared test identities against an explicitly supplied local registry before export. Ordinary CODE cuts do not need that registry, and a pass is not release clearance.
- **RiPPER is an optional, experimental adapter.** Eleven `tools/ripper_*` files and nine docs plan, bind and inspect RiPPER runs. Nothing runs upstream code by default; execution needs an explicit opt-in. RiPPER results are not imported into packages, scores or reports.
- **Completed render packets are checked from one admitted generation.** Packet QA reads only regular files inside the selected artifact root, re-validates the receipt and output roster just before writing reports, and never overwrites an existing `RENDER_QC.md` or `RENDER_QC.tsv`. See `docs/COMPLETED_RENDER_PACKET_QA.md`.
- **Release and report tooling is tighter.** Release partitions prepare the font cache explicitly (`tools/_release_font_cache.py`). Report paths get an advisory claim-safety scope check (`hooks/claim_safety_scope.py`). Saved protein-space coordinates without native-chain admission carry a conservative disclosure (`tools/protein_pcoa_annotations.py`). Evidence, BLASTp, Mode B gene-first, output-transaction and privacy-profile modules also change in this campaign. About 380 test files are new or updated.
- **Stabilize the MLSA workflow test fixture.** The functional-tool-stub fixture's disk observation is deterministic, so host free-space variation no longer looks like a workflow failure. The production disk guard and its refusal test are unchanged.
- **Keep cohort tests importable in isolated partitions.** Fixture and precompute-helper imports are package-qualified; test assertions are unchanged.
- **Preserve holds when recutting CODE exports.** A recut from an extracted CODE zip accepts the exact prior-omission receipt only after checking current policy bindings, safe namespaces, and that the held content and its locators are absent. The original held-file removal route and the independent tier derivation are kept.
- **Import smoke runs on Python 3.13 and beside fontconfig.** The font-cache mkdir proof accepts Python 3.13's `pathlib._local` as well as 3.12's `pathlib`; the bundle supports Python 3.12 and later. The font bootstrap gives `XDG_CACHE_HOME` its own folder, so fontconfig no longer writes into the single-file Matplotlib cache. Both checks stay as strict as before. The partitioned-cut tests give each fixture cut 900 s instead of 180 s, because each one now also runs import smoke.
- **Prepare an engineering CODE build.** Identity and generated release metadata are refreshed by the documented cut workflow. Source and extracted-archive results are recorded with the cut, not in this entry.

- Accretion-justified: mamey/source_context.py — per-run source binding for readers moved to the bound-snapshot path (parsers, antiSMASH evidence, NRPS predictions, KS scan, RG-GMCI); no global patching of open().
- Accretion-justified: mamey/archive_snapshot.py — bounded, immutable in-memory ZIP snapshot whose reads come from the recorded bytes; shared by antiSMASH input, strain identity and the intake session; no disk staging, discovery or network.
- Accretion-justified: mamey/intake_session.py — opt-in captured intake session; source binding is recorded separately from scientific certainty; intake only.
- Accretion-justified: mamey/captured_run.py — opt-in single-run transaction for the captured route; no unbound source and no early master publication.
- Accretion-justified: mamey/captured_batch.py — explicit all-or-nothing batch of captured runs, run in sequence with one cumulative private master.
- Accretion-justified: mamey/captured_harness.py — opt-in direct-archive intake harness used by tools/intake_harness.py and the captured batch.
- Accretion-justified: mamey/captured_intake_cli.py — CLI slice for captured intake; publishes intake JSON, never a full package.
- Accretion-justified: mamey/capture_completion.py — exact local completion bindings for captured runs; receipts are evidence, not snapshot capabilities.
- Accretion-justified: mamey/capture_governance.py — bounded per-invocation exclusions for captured runs; JSON receipts store digests only.

This is an engineering build candidate. Sealing, publication and hosted Linux validation are not established by this entry.

# v9.7.452 — unsealed cut candidate · build 20261016v97452a

Build 20261016v97452a; engine 1.9.176 (unchanged).

- **Evidence admission preserves identity and prior outputs.** Tightens explicit physical-identity and receipt binding, channel separation, query snapshots, source/output alias checks and quarantine preservation across the selected existing workflows.
- **Completion reports reflect observed work.** Queue and cohort checks refuse incomplete requests and corrupt history; timing records retain observed outcome and attempt uncertainty.
- **Archives and release checks bind their inputs.** Hardens required content and identity checks, checksum portability, archive preservation and exact-identity seal-plan generation. Generated plans do not authorize release execution.
- **Discovery and generated documentation remain accountable.** Tightens discovery publication and provenance, requires the tools/capabilities pair, applies 13 source-only documentation corrections, removes a duplicated stale introductory identity and regenerates the affected wiki and maintenance outputs through the normal owners.
- **Portability and resource controls are clearer.** Includes reviewed R system-dependency installation configuration, workspace temporary directories, portable checksum commands and nonfinite resource-limit refusal. Actual Linux installation and runtime remain unverified.

- Accretion-justified: mamey/blastp_physical_binding.py — shared admission of explicit physical-identity assertions and retained output receipts for existing ingest and gate callers; reuses exact_identity adapters, preserves raw evidence and holds contradictory or unbound generations. It performs no sequence analysis, cross-version identity inference or real-data re-key.

Qualification disclosure: 32 engineering cards passed an exact sealed-base combined replay with 1,868 distinct passes and 1 known skip. The first 12 documentation cards completed exact composition and 12 normal-owner steps. D05 then applied exactly on that proposal and passed four additional catalog/maintenance owner checks. All 13 remain source-only documentation corrections, not additional runtime-verified cards. These counts do not certify the final versioned source, the archive, a configured full suite or release acceptance. Optional utility modules, optional software inventory expansion, figure proposals and real-data re-key remain excluded.

# v9.7.451 — unsealed cut candidate · build 20261015v97451a

Build 20261012v97451a; engine 1.9.176.

- **Two-proof rescue holds an unreadable overlap count.** A blank or malformed overlapping-reference count no longer passes as zero: the pair becomes LOGIC_EVIDENCE_HOLD (or MULTI_CHANNEL_HOLD with a shared KS clade), and the logic version is 3. A legacy `_4A` without the column keeps its verdict and says so in `claim_note`.
- **The hybrid gate counts each antiSMASH category once.** NRPS + NRP-metallophore is one class, so `architecture_rationale` and the reproducibility fingerprint change for affected regions.
- **RG-GMCI and the KS scan read what is there.** Contig ends containing N are AMBIGUOUS_TERMINUS; `/contig_edge` is read from the region feature itself; a KS domain block ends at the next feature; thresholds are validated before work.
- **Package runs say when record-limit coverage is unverified.** RECORD_LIMIT_COVERAGE_UNVERIFIED is reported when the antiSMASH log is missing or unrecognised; only NOT_DETECTED counts as no cap.
- **Without biopython, a corrupt GBK is an error, not a package.** The GenBank shim refuses a record with no sequence and no numeric LOCUS length, as biopython does.
- **Tree tip labels carry names only.** The grouped-reference suffix is gone from labels; the caption names each drawn strain and the strains merged into it. Every unambiguous INSDC country has a display region, and INSDC missing-value terms are not places.
- **Evidence and outputs are admitted, not assumed.** Fixes across rescue, boundary, BiG-SCAPE, BLASTp, DIAMOND, handoff, portfolio and workbook paths refuse missing, malformed or aliased inputs and outputs, propagate child failures, and keep requested scope and identifiers.
- **GitHub CI installs R and runs the R figure tests.** CI sets up R and the bundle's R installer, which now lists every package the shipped R scripts load; without R, the newer R tests skip with a reason instead of failing.
- **BLASTp evidence binds to the protein that was searched.** Manual ingest saves the master workbook atomically and refuses a query that names another strain (QUERY_STRAIN_CONFLICT); native nr output records its channel; `deliverable_tools/roster_v2.py` shows an nr hit only where tag and length match; the new read-only `tools/blastp_tag_position_audit.py` keys rows whose tag is a position inside a region.
- **Gap rescue checks adjacent finds for housekeeping context.** Every partner find that is not a paralog gets the neighbour check, support must come from a non-housekeeping find, and the marker list adds the MEP, ClpC-Lsr2, pantothenate and NAD operon families. Verdicts change when gap rescue runs again.
- **Reference exports and handoffs fail closed.** A reference with an empty translation is refused; the database receipt binds the WAL actually read; handoff archives are never overwritten; assembly-line outputs, post-seal snapshots, crosswalk identity fields and partial MIBiG fetches are checked.
- **Protein PCoA admits reference and MIBiG sets cluster-first by default.** Those sequences are clustered in every run, so the dense solver is admitted at the clustered count; a cohort-only set keeps the upper-bound admission, `--no-cluster-first` restores the old order, and the receipt records which applied.
- **Errors say what happened.** The last silent `except: pass` in tools/ is gone (the ratchet measures 0); a local error in the NCBI fetch is no longer reported as an outage; the showdomycin row drops an unsupported zwitterion claim.

- Accretion-justified: tools/gene_local_names.py — bounded local protein-name evidence adapter with source bindings; similarity labels do not establish function.

- Candidate addition: tools/placement_root_variants.py binds unchanged source trees, strict gate results, and display-rooted split/diagnostic-only variants with hash receipts.
- Candidate additions: tools/bgc_class_summary.py, tools/region_edge_totals.py, tools/region_protein_totals.py, tools/region_protein_references.py, tools/palette_distance_report.py, and tools/gap_rescue_panel_figure.py provide source-bound descriptive tables, palette checks, and rescue-panel rendering; no release or scientific adoption claim.

- Accretion-justified: bioassay_paper.py — shared validated four-state bioassay table and renderer entry points.
- Accretion-justified: extra_csv_manifest.py — explicit additional-table manifest parsing and validation.
- Accretion-justified: protein_binding.py — sequence-bound protein query and annotation identity helpers.

- **The suite runs on Linux CI.** On GitHub CI, v9.7.450 reported 5 failures and 60 errors, all from macOS assumptions in tests and one tool. The CORASON adapter tests use `/tmp` with its physical path resolved, which works on both hosts. The five partitioned-cut tests skip, with a stated reason, on hosts without the macOS `sandbox-exec` import backend; the import gate itself is unchanged. `tools/build_mlsa.py` puts the bundle root on its import path, so it runs from any folder when the package is installed. Two placement tools (`build_placement_panel_inputs.py`, `placement_display.py`) bind the bundle root the same way. A new guard test fails if a test or tool names the macOS temporary root or calls `sandbox-exec` without a platform check.
- **No pytest cache in the CODE zip.** The tier's private-ID audit runs pytest without its cache, and the stage is cleared of `.pytest_cache`, `__pycache__` and `.DS_Store` just before zipping. The v9.7.450 zip carried 7 unlisted `.pytest_cache` entries (no data). A new test checks the archive members.
- **Gap-rescue partner checks count sibling MIBiG entries of the same compound.** The rescue tools now pass compound names into the partner checks, and `same_family()` reads string or list names alike. Before, a gene whose best match was a sibling entry of the reference compound (for example bottromycin D against bottromycin A2) was set aside as a paralog. Family stems now match only when equal or when one is the other plus a known prefix (neo, iso, deoxy and similar), so a name inside another name (istamycin, distamycin) no longer counts. Engine 1.9.176. Existing rescue outputs are not rewritten; a rerun list ships with the change record.
- **Locus maps name the grey genes.** Gap-rescue locus maps read one or more gene-name tables (BLASTp and local Swiss-Prot/MIBiG searches; the first table wins) and label genes as "name (db N%)", "(reference ref N%)" or "unnamed protein (db N%)". Sibling runs on the same core region can be drawn as extra references. Pale class fills replace flat grey. Names are similarity, not function.
- **BLASTp identity figures and one genus palette.** `tools/blastp_identity_figures.py` draws the per-genome identity figure and the core-genes-by-class figure in the bee paper's layouts. It reads per-gene BLASTp results and a genome table instead of fixed paths, takes the top hit or the mean of the top 10 hits, and keeps nr and ClusteredNR separate or takes the better per gene. Genus colours now come from one file, `mamey/data/genus_palette.json`, and saved figures carry the renderer stamp.

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
