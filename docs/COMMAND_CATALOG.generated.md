# Command catalog (generated)

*Generated from the live argparse tree of `mamey.cli` by `tools/gen_command_catalog.py` — bundle v9.7.428 · engine 1.9.163. Do not edit by hand; `--check` fails the build when stale.*

Every command is invoked as `python mamey_run.py <command> …` from the extracted bundle root (the bundle-local launcher, so an older installed copy cannot shadow it). Most post-seal commands take `--package <sealed package dir>`; `run` is the only command that creates a package. Claim-safety: every output is a class-level hypothesis with judgment deferred.

## Recommended front doors

Most users can stay on this path: `start` for orientation, `inspect` then `run` for extraction, `validate` for the package gate, `discover` and `explore` for review, `render-all-figures` for the applicable figure suite, `phylo-autopilot` or `phylo-run` for tree workflows, `mode-b` for the interpretation scaffold, and `workflow` for status. The catalog below includes specialist commands so they remain discoverable; aliases are folded into their canonical command row.

## Run and seal a strain

_Deterministic extraction — the only step that creates a package._

| command | what it does |
|---|---|
| `run` | Run Mamey extraction on one or more antiSMASH ZIPs |
| `validate` | Validate an existing package directory |
| `seal-package` | Run all QC gates on a package and emit a seal receipt |
| `inspect` | Preview what Mamey sees in an antiSMASH ZIP before running |
| `start` | Primary CLI starting point: show the five-command workflow and run the environment check |
| `doctor` | Pre-flight environment check: Python, deps, write permissions, bundle integrity |
| `capabilities` | Search full docstrings for existing internal tools before writing a new one |
| `resume` | One-read session-resume briefing for a sealed package (strain context + judgment progress + what's next) |
| `fingerprint` | Determinism fingerprint of a sealed package (score-bearing outputs only) — same strain+bundle yields the same value in any chat |
| `handoff` | Pack a sealed package + region GBKs into one portable zip so another chat can do the full workflow (incl. online BLASTp) without the raw antiSMASH ZIP |
| `explain` | Human-readable summary of an existing result package |
| `release-qa` | Run release QA gates: Legacy Feature Matrix + Dual-LLM Handoff Receipt |
| `tab-reconcile` | Parse antiSMASH tabs for one BGC/region and emit Mode B evidence ledgers |

## Post-seal figures

_Start with `render-all-figures` for one sealed package. Use `figure-factory` for a receipt-bound custom configuration; the remaining commands are specialized builders._

| command | what it does |
|---|---|
| `render-figures` | Render one selected figure set from a sealed Mamey package |
| `figure-factory` | Render the receipt-bound Figure Factory evidence figure suite from a hash-bound JSON config (aggregate, phylogeny, or bioassay kind) |
| `figures` | Publication figures (diagram \| atlas \| ani \| gcf-network \| clinker) |
| `interactive-figures` | Build cohort widget data from a directory of sealed packages |
| `cohort-figures` | Emit the gold gene/domain figure suite (data-only PNG + sidecar CSV) for one or more gold packages |
| `overmerge-widgets` | Emit the over-merge inspector widget set (per OVER_MERGED region + ranked index) from the over-merge register + GBKs |
| `rggmci-widget` | Emit the within-strain RG-GMCI split-pathway linkage widget from each package's *_4A_RGGMCI_ranked_pairs.csv |
| `assembly-line-widget` | Emit the NRPS/PKS assembly-line / domain-architecture reader from a sealed package's antismash_modules.csv + gene_context.jsonl |
| `assembly-line-pdf` | print-ready PDF of a strain's NRPS/PKS assembly lines, 4 or 6 per page |
| `bgc-gene-map` | print-ready PDF gene map of EVERY region in a strain (all classes, not only NRPS/PKS) |
| `lead-pages` | Render lead-only §31-40 enrichment + related-genomes dossier pages from a sealed package |
| `render-all-figures` | Run every applicable figure module against a sealed package and record per-module outcomes without changing the sealed package |
| `render-widgets` | Render portable interactive widgets + publication handoff from a sealed package/ZIP |
| `attach-bgc-overlays` | Attach locator-first, hash-bound scientific-review overlays additively |

## Mode B judgment support

_Scaffolds and gates for LLM judgment; the triage table is NOT a finished card._

| command | what it does |
|---|---|
| `mode-b` | Emit a Mode B top-lead triage table and card scaffolds from a sealed package. NOT a finished 48-section Mode B card: finished cards are authored per wiki/Mode-B-Gene-First-and-48-Section-Manual.md and verified with `verify-modeb` (v9.7.405 wording). |
| `modeb-compile` | per-strain Mode B compilation (report+cards+majority-read overlay+figures) |
| `modeb-export` | Export an authored Mode B card .md (or a mode_b/ dir) to .docx + .pdf |
| `modeb-round` | Emit + scaffold-verify a round of N triage Mode B cards, write a stateful worklist (authoring is the Sapote step) |
| `verify-modeb` | Verify a FINISHED authored Mode B card via lint_card (structure + strict depth) |
| `write-narrative` | Write a pre-authored narrative section into the package judgment/ dir, with claim-safety linting before write |
| `compile-report` | Assemble the §13 compiled analysis report deterministically (disk-backed sections filled; narrative sections left as Sapote slots) |
| `report-card` | Render L0-L1 per-BGC report cards from a package (predicted molecule + badges) |
| `guide` | Layered per-gene BGC Guide (lay→technical; Structure/Function/BLASTp per gene) |
| `verify-guide` | Verify a FINISHED authored guide .md (no residual LAY slots; Parts authored; gene summaries present) |
| `verify-citations` | Fail-closed node·region citation gate: refuse a BGC deliverable that cites a strain+BGC with no contig node (WAC-01375 fatal-error class) |
| `dualpass` | Merge two engine CLAIMS_LEDGER.tsv into a divergence table (claims_vocab enum) |
| `surface-leads` | surface PROMISCUOUS_ONLY + coherent-LOW_ID review groups |
| `layperson` | Render a claim-safe plain-language guide from one sealed package (post-seal) |
| `emit-modeb-cards` | compact auto-filled per-BGC Mode-B data cards for a sealed package (composition, RG-GMCI banner, priors, architecture counts); non-blocking |
| `emit-modeb-template` | Emit a canonical §1–§48 Mode B card template for one BGC or a batch (W9, v9.7.150+) |
| `emit-strain-modeb` | emit the strain-level Mode B (Full Strain Sapote, S1–S8) deterministic skeleton from a sealed package; non-blocking, structure-gated |
| `modeb-availability` | Inventory and bind Mode B evidence streams before any card prose is authored |
| `modeb-blastp` | Emit per-BGC BLASTP FASTA batches from the panel manifest (Mode B §16 automation) |
| `modeb-gene-first` | Compose one exact-locus gene-first exploration without authoring a Mode B card |
| `build-bgc-drafts` | Build locator-first L0 BGC drafts from hash-bound external evidence roots |
| `claim-safety` | Run the post-hoc claim-safety linter on a Mode B card or compendium markdown |
| `class-believability` | committed-step class believability (HIGH/MEDIUM/LOW/SUSPECT) per BGC and pooled per strain; non-blocking, reads a sealed package |

## Evidence channels (BLASTp / MIBiG / BiG-SCAPE)

_Optional deeper evidence; every channel stays a separate lane._

| command | what it does |
|---|---|
| `tool-database-inspect` | Inspect one explicit manifest-bound tool database read-only; no scientific admission |
| `ingest-blastp` | Ingest an NCBI BLASTp HitTable CSV (+ optional Alignment XML) into a master workbook's B5_BLASTp_Hits sheet |
| `ingest-blastp-trove` | Ingest a pre-organized per-BGC BLASTp trove into the package overlay (no workbook). |
| `blastp-status` | Report per-BGC BLASTp overlay coverage (channels/genes) or flag ClusterBlast fallback. |
| `blastp-online` | Per-gene NCBI web BLASTp for a BGC (independent homology channel; fail-closed) |
| `blastp-ebi` | EBI fallback BLASTp transport (no nr; DB-tagged provenance; coverage-preserving XML path) |
| `blastp-round` | Plan/run a phased strain BLASTp round (full top-N + 1 per remaining BGC) |
| `auto-blastp` | Resumable priority BLASTp scheduler (1 query / 8 min, hourly ingest) |
| `blastp-availability` | Declare BLASTp availability (available-vs-ingested) per strain/channel |
| `bigscape` | RUN BiG-SCAPE 2.x on a package/cohort's region GBKs -> cohort DB (+ chained matrix/clinker widgets). Post-seal, non-blocking. |
| `hmm-adjudicate` | Ordered HMM domain readout for a BGC (intrinsic structure; complements BLASTp) |
| `domain-reference` | emit the Mode-B domain functional-context dictionary from sealed package(s) (DOMREF-01) |
| `domain-level` | Post-seal domain-level Mode B enrichment from a sealed package (role mapping, complexity, claim ceilings) |
| `reference-dark` | Write a non-ranking report of loci with limited admitted reference coverage |
| `kcb-frontpage` | Read antiSMASH KnownClusterBlast front-page hits, ranked + corroboration-tiered |
| `comparator-coverage` | FA2 two-denominator comparator coverage (report-only, non-scoring) |
| `bgc-blastp-panel` | Export up to two representative translated proteins per BGC as chunked FASTA files for manual BLASTP |
| `blastp-followup` | Parse NCBI BLASTP Hit Table/XML2 results and make the next iterative FASTA batch |
| `cohort-proteins` | Build/query an exact-locus within-project BGC-protein occurrence catalog |
| `resistance-dossier` | post-seal: per-BGC resistance-focused gene-by-gene dossiers (resistance loci via domain_reference + nr BLASTp + MIBiG). Non-blocking. |

## Cohort and cross-strain

_Aggregation across sealed packages._

| command | what it does |
|---|---|
| `cohort` | Cross-strain front-door: emit a cohort deliverable bundle (synthesis report + figures) with a mandatory-deliverable gate. |
| `cohort-leads` | Union every sealed package's triage board into ONE ranked cross-strain priority-leads CSV (Exceptional+High leads). Non-scoring, capacity-level re-projection. |
| `cohort-assemble` | Assemble many sealed packages into ONE cohort table (strain_summary + bgc_inventory + class_by_strain) as COHORT_MASTER.csv/xlsx, without the O(N^2) master rewrite. |
| `cohort-precompute` | Consolidate per-strain precompute sources into the 7 cohort tables (+ VERSION.json/MANIFEST.csv) |
| `majority-read` | whole-BGC MIBiG majority read (minority/promiscuous-anchor flags) |
| `novelty-shortlist` | composite multi-signal novelty shortlist (KCB-dark + low recognizability + RG-GMCI + cohort-unique domain); advisory |
| `realistic-count` | corrected-denominator BGC count (marginal-drop + HIGH RG-GMCI merge); advisory |
| `af-leadboard` | Emit the cohort ANTIFUNGAL (AF) capacity lead-board dashboard from the per-BGC master CSV + codex-judged cards |
| `af-dossier` | Antifungal (AF) Lead Dossier: AF lead board x measured Candida activity (report-only) |
| `genus-appendix` (alias: `af-ab-appendix`) | Antifungal/antibacterial candidate appendices, grouped by genus (report-only) |
| `good-guesses` | Good Guesses: single best claim-safe interpretive read per notable BGC (report-only) |
| `clade-deepdive` | Genus/clade deep-dive apparatus: six tracks (ANI, BiG-SCAPE matrix, conserved-dark, nt-core-BGC clock, decontam-if-flagged, clinker) -> <CLADE>_SYNTHESIS.md. Post-seal, non-blocking, degrades gracefully. |
| `split-overmerge-cards` | Run the deterministic per-protocluster SPLIT *_FULL.md card QC-fixer/generator over the split-card manifest (idempotent) |
| `compound-families` | Map a sealed package's anchored BGCs to compound families + related-known structures |
| `p450-tailoring` | Classify a sealed package's P450 genes (oxidative-tailoring vs crosslinker cassette) |
| `assembly-line` | Predicted PKS/NRPS assembly line per BGC from the native _domains.csv |
| `discover` (alias: `discovery`) | Orient in a workspace: list packages, coverage, and next actions |
| `explore` | question-driven genome exploration (divergence / co-capture / lead board) |
| `compare` | Compare two antiSMASH result sets gene by gene and retain ClusterBlast, SubClusterBlast, and KnownClusterBlast comparator evidence |
| `activity-leads` | Emit per-strain top-N antibacterial and antifungal routing boards from sealed triage packages (non-scoring; claim-safe). |
| `activity-lead-genes` | Bind per-package gene rows to an activity-leads CSV and select up to five genes that explain each source class label. |
| `cddr-pks` | Build a CDDR-PKS deep-dive report from an existing directed study, or run Directed PKS first from source/spec |
| `directed-pks-study` | Run Directed PKS Study Mode from source CDS CSV + study spec; emits Pre-Sapote Lite, EFLS, figures, LC-MS, citations, workbook, and CDDR-PKS report |
| `wise-fragmented-pks` | Split ranked fragmented PKS/NRPS FASTA into stable residue-safe BLASTP queue files |

## Phylogeny

_Use `phylo-autopilot` for 16S routing and EPA-ng placement; use `phylo-run` for an approved GToTree/IQ-TREE genome workflow._

| command | what it does |
|---|---|
| `phylo-run` | Run an approved GToTree and IQ-TREE genome workflow, with optional fastANI and tree sign-off |
| `phylo-autopilot` | Plan local 16S/genome inputs, route 16S references, or run an approved EPA-ng placement workflow |
| `signoff` | Analysis sign-off QC gate: objective checks on Newick trees (outgroup/contaminant/label-cruft/support/thin-tree). Advisory, exit 0. |

## Workflow, receipts, catalogs

_Non-destructive status and lookups._

| command | what it does |
|---|---|
| `workflow` | Sapote workflow ledger for a sealed package: per-step PASS/PENDING/BLOCKED with receipts (W0-W10). --strict fails closed. |
| `deliverables` | List, explain, preflight, or render the registry-backed deliverables menu |
| `deliverable-queue` | Resumable autonomous deliverable driver over a strain list (gate-gated) |
| `ingest-receipts` | Ingest Mode B judgment into the judgment store (+ optional --master E1 reconcile) |
| `validate-finished-review-request` | Validate a hash-bound Mode B finished-review request without promotion |
| `list-bgcs` | Quick BGC inventory from a sealed package (table or JSON) |
| `literature` | Full-abstract lookup / search over the in-bundle PubMed corpus |
| `lab-quest` | launch the optional local Lab Quest interface bound to one verified portable Mamey code tier |
| `triage-raw` | Guided PRE-EXTRACTION genome triage: KCB front page + scanner evidence + rare-motif scan + split-detector + bgc_walk on the priority regions, in one pass, directly on a raw antiSMASH ZIP/dir (see docs/Sapote_Mamey_ROADMAP.md). For sealed-package novelty/divergence correctness checks after extraction, see `mamey explore`. |
| `wheelhouse` | Manage the Wheelhouse lab-data store (strains, scanners, validations) |

## Compatibility and maintainer commands

_Retained for existing scripts and specialized maintenance. They are not additional onboarding paths._

| command | what it does |
|---|---|
| `chatgpt-init` | Legacy compatibility check for the shared assistant contract; new sessions use `start` |
| `codex-figure-catalog` | Legacy-named Figure Factory command: emit the governed figure registry and caption/method catalog |
| `codex-figure-sets` | Legacy-named Figure Factory command: render implemented strain/cohort sets from the governed registry |
| `codex-figure-sources` | Legacy-named Figure Factory command: build a provenance-rich source bundle from sealed package ZIPs |
| `codex-bigscape-figure-sets` | Legacy-named Figure Factory command: render the optional BiG-SCAPE figure extension |
| `codex-heatmaps` | Legacy-named Figure Factory command: convert matrix CSVs into SVG/HTML figure packs |

_113 canonical commands catalogued; 2 aliases folded into those rows._
