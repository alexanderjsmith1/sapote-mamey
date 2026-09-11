# Mamey Engine Lineage

## Engine 1.9.163 — first bundle: v9.7.428

Post-seal phylogeny tooling now exports a complete standalone collaborator package for every
accepted tree display, applies explicit reviewed query-identity exclusions at panel admission,
distinguishes accession-shaped laboratory strain codes from conflicting deposited accessions,
supports reproducible closest-type-strain neighborhood catalogs, and avoids MAFFT's restricted
`/dev/stderr` wrapper path. Figure metadata and palettes are refined, and the bioassay plate-map
utility adds a validated plate-geometry layer. Core antiSMASH extraction, source scans, scoring,
triage thresholds, and sealed-package schemas are unchanged.

## Engine 1.9.162 — first bundle: v9.7.427

Post-seal phylogeny display changes add a declared Tree Catalog, exact placed-query role binding,
reference-definition screening, specimen-level internal labels, concise publication metadata, and
explicit horizontal layout controls. Distinct isolates remain distinct even when their submitted
16S sequences are identical. Core antiSMASH extraction, source scans, scoring, triage thresholds,
and sealed-package schemas are unchanged.

## Engine 1.9.161 — first bundle: v9.7.426

Post-seal Figure Factory behavior changes for fixed bioassay inputs: a canonical observation schema
retains material lineage, dose, time point, replication, controls, exclusions, and material amount;
the planning kind inventories raw, precomputed, MIC, and in-vivo datasets; and an explicit endpoint
or named fraction-set maximum can become a typed tree annotation. The 16S autopilot now screens
queries, selects MAFFT fragment alignment for partial reads, and holds near-tied cross-genus routing.
Reference admission and metadata display are shared across phylogenetic producers. Core antiSMASH
extraction, source scans, scoring, triage thresholds, and sealed-package schemas are unchanged.

## Engine 1.9.160 — first bundle: v9.7.425

Post-seal widgets, Mode B scaffolds, Lab Quest inventories, reports, guides and lead figures now preserve complete locus identity and typed missingness for fixed package inputs. Ambiguous, malformed and unsafe roster/evidence inputs return explicit refusals, and external guide output no longer rewrites the source package. Core extraction and scoring thresholds are unchanged. Generated scaffolds, references and test success do not establish scientific interpretation, production, activity or owner acceptance.

## Engine 1.9.159 — first bundle: v9.7.424

Reference-panel filtering, advisory terminal assessment and portable placement display integration change workflow outcomes. Exact accession and metadata refusals are preserved. Display conventions change labels only; full accession identities remain in source records.

## Engine 1.9.158 — first bundle: v9.7.423

BLASTp discovery excludes account-level automatic roots and the CLI reports typed discovery refusals. Identity-claim hedges are scoped to their clause in plain and structured lint results. Placement annotation can bind binary bioassay summaries with explicit missingness and duplicate/value refusals. These changes affect workflow and validation outcomes for fixed inputs; mechanical verification does not establish scientific acceptance.

## Engine 1.9.157 — first bundle: v9.7.421

Failure-state propagation changes verification, report, inspection, and evidence-admission outcomes for fixed inputs. Caught BLASTp file-set failures restore prior output or expose a recovery hold. Reference discovery, metadata projection, and exact outgroup-token handling change post-seal tooling. Scientific interpretation, product identity, and production claims remain deferred; mechanical validation does not confer acceptance.

## Engine 1.9.156 — first bundle: v9.7.420

Failure handling changes verification, report and evidence-admission outcomes for fixed inputs. Missing linkage no longer becomes a zero rescue measurement. Reference-label refusal diagnostics and narrowly scoped collection-prefix handling change post-seal display behavior. Core extraction algorithms and scoring thresholds are unchanged. Mechanical tests do not establish scientific acceptance.

## Engine 1.9.155 — first bundle: v9.7.419

Reference-label disambiguation and mixed-store admission change post-seal display and refusal behavior for fixed inputs. Refpkg filtering and supplemental citation checks are tightened. Core extraction, scans, scoring and sealed-package schemas remain unchanged. Test success does not establish scientific identity, rooting or acceptance.

## Engine 1.9.154 — first bundle: v9.7.418

Display labels change for fixed inputs and reference metadata gains explicit source states and provenance. Outgroup lookup refuses reference-only bundled authority and contradictory locked rows. These post-seal presentation and refusal changes warrant an engine identifier; core extraction, scans, scoring and sealed-package schemas are unchanged. Render or test success does not establish scientific rooting, identity or acceptance.

## Engine 1.9.153 — first bundle: v9.7.416

Post-seal deliverable commands now return a nonzero status on canonical-write refusal or execution failure, preserving actionable diagnostics and successful zero exits. The cut integrates portable phylogenetic workflow tools and stricter provenance/refusal behavior described in the changelog. Core extraction, scan and scoring algorithms are unchanged. A mechanically validated tree workflow does not establish scientific rooting, taxonomic identity or biological conclusions. Release test results are recorded separately in the release manifest.

## Engine 1.9.152 — first bundle: v9.7.414

Also shipped in v9.7.415: folder organization, post-seal inspector identity, test portability, companion-command failure handling, optional hooks, and documentation. No extraction/scoring or sealed-package schema change.

The post-render summary retains its relative package anchor and now copies subject identity and available engine/workflow fields from the package manifest. This changes a shipped artifact for a fixed input and warrants an engine bump. The cut also adds display-only title/host parsers to the existing label owner, Git-checkout audit exclusions scoped inside the audited root, portable link checking, test-skip repair, and signed-waiver ceiling enforcement. Scoring and biological scan outputs are unchanged. Display parsing is not taxonomy or host-association verification. Full-suite results are recorded in the release manifest.

## Engine 1.9.151 — first bundle: v9.7.413

The JSON parser receipt now preserves the original requested mode through timeout fallback and records structured-path request flags and budget outcomes. Validation exposes advisory JSON visibility fields. This changes emitted evidence receipts for a fixed input and warrants an engine bump. Missing historical fields stay unknown; the new visibility field does not change overall package acceptance. No new biological scans or scientific interpretations are introduced by this visibility change. The cut also includes source-bound post-seal evidence adapters and rendering/gate repairs described in the changelog. Existing source and cohort holds remain explicit.

## Engine 1.9.150 — first bundle: v9.7.412

**Reason for bump:** the emitted `manifest.json` changes for a fixed input. `mamey/packaging.py` (BC412_08) adds `gold_figures/figure_receipts.jsonl` to `MUTABLE_RECEIPT_NAMES`, so it is no longer hash-pinned in the manifest/checksums. This corrects a false `mamey validate` FAIL: `figure_save.py` appends that file into the package after the seal, so a pinned hash always went stale on a MAMEY_COMPLETE package.

**Scoring / parser semantics:** UNCHANGED. No scoring, source-scan, or parser module changed. Only the packaging pin-set and validate's reciprocal scan differ.

**Comparability:** a 1.9.149 package re-run under 1.9.150 produces identical score-bearing output. The manifest differs by exactly one entry: `figure_receipts.jsonl` is present-and-pinned under 1.9.149 (and makes validate FAIL) and present-but-unpinned under 1.9.150 (validate PASS). Consumers that enumerated pinned manifest entries see 100 vs 101.

**Tests at bump:** ACCEPT-union .412 slice 308 passed / 21 skipped; graft-integrity 25; parity gold-run on `examples/test_data/smoke_antismash_small.zip` (validate rc=0 vs .411 rc=1). Full suite is the seal gate (owner-run).

## Engine 1.9.149 — first bundle: v9.7.409

**Also shipped on 1.9.149 (engine unchanged, bundle-only bump):** v9.7.410 — reconciled two-stream fold (Codex chain + rebased Claude lanes + hostile-audit rounds + ported round-7 lanes); scoring-neutral, no scoring module changed, cross-strain comparability with .409 preserved.

**Why the engine bumps here:** one parser-level guard changes what can reach the evidence tables.
`parsers.QUALIFIER_MAX_CHARS = 4000` caps a single GenBank qualifier value at parse time. A region
GBK carrying a 300 KB `/note` on one CDS (reproduced from a hostile fixture) previously flowed
uncapped into `_2_inventory.csv` and the figure label path; the CSV reader then failed its field-size
limit and the renderer was killed. Annotation text beyond the cap is truncated with an explicit marker.
No scoring prior, scan pattern, class route or RG-GMCI band changes in this cut; the remainder of
v9.7.409 is gate, refusal, export-safety and documentation work.

**Comparability:** a 1.9.148 package re-run under 1.9.149 is identical unless a qualifier exceeded
4,000 characters, in which case only that annotation text differs. Use `tools/determinism_fingerprint.py`
to show a score-bearing re-run reproduces.

## Engine 1.9.148 — first bundle: v9.7.408

**Why the engine bumps here:** three fixes change what the evidence tables and the triage board say.
(1) `antismash_evidence._tigrfam_from_rec` keyed every TIGRFAM hit to `_c1` regardless of its true
region; on any contig carrying more than one region the lead board's TIGRFAM panel and
`_3_antismash_hmm.csv` attributed hits to the wrong BGC. Reference and type strains are the worst case;
this cohort's fragmented assemblies (mostly one region per contig) masked it. (2) Four cassette
patterns (`polyene`, `phosphonate`, `nucleoside`, `aminoglycoside_aminocyclitol`) gained the
false-positive guards their CCTT siblings already carried — owner ruling 2026-09-04 that the matches
they were making (arylpolyene pigments, phosphonate transporters, nucleoside diphosphate kinase,
aminoglycoside-modifying resistance enzymes) are false positives. Each had been raising a HIGH-tier
flag with a wet-lab route. (3) `scoring.py` rescue-bonus / mobile-element flag interaction.

**Comparability:** a 1.9.147 package re-run under 1.9.148 can differ in the TIGRFAM panel, the
`Cassette_Registry` sheet, and — where a cassette flag fed a lead tier — in lead ranking. AB/AF/novelty
priors themselves are unchanged. Packages produced under 1.9.147 whose genomes have one region per
contig will show no TIGRFAM change. Use `tools/determinism_fingerprint.py` to show a score-bearing
re-run reproduces where it should.

**Not a reason for the bump, recorded so it is not misread as one:** the `sid` → `cohort` tier rename is
packaging, not engine; and the emission merge is byte-identical output.

## Engine 1.9.147 — first bundle: v9.7.407

**Why the engine bumps here:** the shape of the `manifest.json` handoff changes, so a consumer written
against 1.9.146 cannot be assumed to read 1.9.147 output. The manifest contract map (CODEX-407 D01–D05,
F01) (1) nests owner keys that were previously flat, (2) removes a phantom depth-floor key that
`gate_validation.json` advertised but no producer ever wrote — a consumer guarding on its presence was
guarding on nothing, (3) adds the resistance-tier join so the tier is readable without re-deriving it
from the scan bundle, (4) adds a documented root provenance block, and (5) documents the whole shape in
`schemas/manifest_contract.json`, validated by `mamey.manifest_schema.check_package_contract` through
`validate --manifest-contract` (advisory; never blocking in this cut). Also on the run path: the in-run
V8 locus map now receives `region=` (P013) and falls back to the normalised `*_cds_table.csv` when the
rich gene table does not yet exist at that pipeline stage (P009) — before this, that renderer failed for
every in-run invocation; and the phylogeny package/tree join is validated rather than merely
key-present (P003, P014).

**Not a reason for the bump, recorded so it is not misread as one:** `mamey/console.py` and the two
`_console.py` siblings route 1,608 call sites through a pass-through emitter. It forwards
`*args, **kwargs` to `builtins.print` unchanged, so every converted site is byte-identical on stdout and
stderr. No output moved, no emission site was removed. The seam exists so a future `--quiet`, logger, or
capture change is one function rather than 1,608 edits; that migration is deliberately deferred.

**Comparability:** runs from 1.9.146 and 1.9.147 differ in manifest key layout and in the presence of the
contract schema, not in AB/AF/novelty priors — no scorer, standing rule, or guard threshold changed in
this engine. A 1.9.146 package remains readable; consumers pinned to the flat manifest keys need the
one-time key-path update the contract map documents. The calibration panel and the new
`tools/determinism_fingerprint.py` (with the shipped `.406` fingerprint data) are the intended way to
show that a re-run under 1.9.147 reproduces 1.9.146 score-bearing output.

## Engine 1.9.146 — first bundle: v9.7.406

**Why the engine bumps here:** output-changing changes in the run path and the models. (1) `--project-registry`
(BR6, rebased): `RunContext` gains `project_privacy_tier`, `project_privacy_tier_source`, `publication_status`,
`genome_state`, `project_registry_sha256`, `assay_summary`; the manifest gains a `project_privacy` block with
`drives_release: false`; a package without a registry writes `project_registry_status.json`
(`NOT_PROVIDED_PRIVACY_HOLD`). The registry is **recorded, not authoritative**: release and
`BGCRecord.privacy_tier` remain owned by the landed `--privacy-profile` mechanism, and supplying both flags is a
typed refusal (`PRIVACY_AUTHORITY_CONFLICT`); precedence between the two is deferred to a later engine.
(2) D2: `BGCRecord.kcb_evidence_state` (`OBSERVED` / `UNAVAILABLE_INPUT` / `PARSE_REFUSED` / `UNKNOWN_KCB`) is
carried to the inventory and named in the rationale when recorded and not `OBSERVED`; an absent KCB input never
moves novelty in either direction. (3) Scans and guards E1–E7: RG-GMCI terminus low-complexity guard
(`LONG_READ_ONLY`), edge-adjacent FabH/KSIII partner guard (`AMBIGUOUS_PARTNER`), chromosome-first replicon
ordering at intake, `--hmm-scan` on the run path with a named degradation, over-merge structural flag
(`OVERMERGE_SUSPECT`, ids untouched), saccharide standing-rule reason (`HOUSEKEEPING_GLYCOSYL` vs
`TAILORING_GLYCOSYL`), fragment-surfacing invariant in `lead_propagation`. (4) E8: one claim-ceiling string on
every architecture-first early return ("class-level capacity hypothesis; not product identity").

**Comparability:** runs from 1.9.145 and 1.9.146 differ in inventory/rationale columns and in flags, not in
AB/AF/novelty priors except where a new guard fires; the calibration panel (`tools/calibration_run.py`, H1–H3)
is the measurement for that drift from this engine forward. Claim-safety unchanged: class-level hypotheses,
judgment deferred.

## Engine 1.9.145 — first bundle: v9.7.403

**Why the engine bumps here:** a governed-data *source-selection* change. Until now an explicit
`MAMEY_OFFICIAL_DATA` override was only the FIRST candidate in a probe list that still appended
`MAMEY_DATA_ROOT` and the whole `__file__` parent walk behind it, and the caller loop simply
continued past a missing or unparsable file. A tree living under a workspace holding its own
`OFFICIAL_DATA/` could therefore consume **that** pack's exclusions and denominators while the
operator believed they had bound a different cohort — with no failure signal. From 1.9.145 an
explicit override is **exclusive**: nothing is consulted behind it, and a missing or malformed
file under it falls back to the documented empty default, never to another pack.

**Comparability decision, recorded explicitly (an independent QA pass asked for this):** runs
made *without* any env override are unaffected — the parent walk is unchanged, so a bundled
`OFFICIAL_DATA/` still resolves exactly as in 1.9.144 and cross-run comparability with `.402`
holds. Runs made *with* `MAMEY_OFFICIAL_DATA` set are **not** directly comparable across the
boundary, because before 1.9.145 such a run could silently have consumed a different pack. That
is the whole point of the repair, and it is why this is an engine bump rather than a bundle-only
patch: a consumer must be able to tell, from the engine stamp alone, whether an override-bound
run is trustworthy. Any pre-1.9.145 governed result produced under an override should be
re-derived before it is compared with a post-1.9.145 one.

**Scoring/parser/extraction semantics changed: no.** No scan, scorer, triage floor, guard, or
parser is touched. `scoring.py`, `source_scans.py`, `rggmci.py`, `parsers.py` and
`antismash_evidence.py` are untouched by this engine generation. What changes is *which governed
data file a run reads* when an operator binds one explicitly — a provenance contract, not a
judgment change. Claim-safety is unchanged: class-level hypotheses, judgment deferred.

**Also in this generation (no scoring surface):** the Mode B gene-first evidence-store bridge and
Layer A/B/C readiness receipts (V4 successor steps 3 and 4, closing the combined-receipt gap so a
layer can be READY while a later layer is HELD, and making a prefix such as `AS-*` a membership
*hold* rather than membership); a tree-ordered BGC-class heatmap panel joining the Figure Factory
to the GToTree phylogenomics lane; Codex's F13 provenance/source-artwork contract (independently
bound by a second lane before composition) and its phylo tick-label/data-rectangle clearance
renderer; a portable manifest-recovery locator; a BLASTp channel-triage contract; and a
DPI-independent repair to the gold-figure empty-state placeholder gate.

## Engine 1.9.144 — first bundle: v9.7.402

**Why the engine bumps here:** composed under an Alex ASAP-cut ruling. Two new module families
land for the first time — Mode B gene-first v2 (`mamey/mode_b/gene_first_stage_v2.py`,
`gene_first_interpret_v2.py`, `gene_first_figure_overlay.py`, the first fixed/versioned/static
gene-first staging workflow) and the Figure Factory publication/onboarding/continuity family
(policy-and-cohort schema, publication-artwork gate, phylogeny receipt adapter + renderer,
onboarding/package-continuity/portable-project widgets). Consumers distinguishing pre/post-these
generations need an unambiguous engine stamp.

**Scoring/parser/extraction semantics changed: mostly no, with one deliberate, flagged exception.**
Gene-first v2 composed in the Alex-ratified blocking-gate order: (1) sealed Codex candidate; (2)
GF3-2 — identity validator converges on the shipped `gene_first_explore.py`'s semantics (region/
BGC-alias normalization, NODE anti-shortening; 9-fixture differential gate, 9/9 concordant, was
6/9 divergent); (3) GF3-1 — coordinate/strand/membership added to the roster digest, schema bumped
to `modeb_gene_first_stage_v2.1`. The Figure Factory family (PF402-01 through 08 plus
FF402-LAYOUT-01) adds cohort/role-typed figure policy, a publication-artwork gate, and a
phylogeny-overlay renderer+adapter pair (PF402-03/04: a designed two-layer split, not a
duplication — the adapter routes `figure_kind` to the renderer, one-way dependency, both ride in
board order). Also folded: `mamey/cohort_resolver.py`'s AS-regex tightened to exact-anchor
matching, removing a shape-based false-positive on a non-AS prefix, plus a new `membership_authority`
field distinguishing a generic routing bucket from confirmed scientific cohort membership (no
scientific membership is ever inferred from an identifier prefix); estate index OSError→realpath
fallback; nine jq-dependent hooks ported to python3-stdlib; a currency-stamp sync-and-lock rule
pair; capabilities-search module-stem indexing; a tool-inventory provenance correction.

**The one deliberate, flagged scoring-visible exception**: the missing-KCB-evidence novelty credit
(`kcb_cumulative is None: novelty += 5`) is removed — missing evidence must not inflate a novelty
prior. This interacts with the tier-1 diagnostic floor's corroboration guard (PC-12/#28): an
uncorroborated diagnostic on a class-incompatible locus (the nucleoside-on-NRPS/T1PKS fixture) no
longer reaches Medium via a phantom credit that was masking the guard's own "uncorroborated"
finding. The stricter, honest behavior is shipped; a class-compatible companion case still floors
to Medium end-to-end (verified). **Open policy question for Alex, not resolved by this cut**:
should an uncorroborated diagnostic still floor tier at all? A future NUC~NRPS class-compatibility
ruling would flip today's shipped answer. Cross-strain comparability with `.401` preserved outside
this one flagged, deliberate exception.

**Previous engine:** 1.9.143

## Engine 1.9.143 — first bundle: v9.7.401

**Why the engine bumps here (after three bundle-only cuts on 1.9.142):** the `.400` fold changed
the manifest shape (R1: `source_scans` channels alias to standalone package files) and `.401`
changes the B2 product-class canon (23 → 37 columns, Alex n≥10 ruling, 2026-09-02). Consumers
distinguishing pre/post-R1 manifests and pre/post-promotion workbooks need an unambiguous engine
stamp; three manifest/schema generations under one engine number would be a provenance ambiguity.

**Scoring/parser/extraction semantics changed: NO** — with one guard-scope note: the resolved-KCB
class-mismatch guard now receives the resolved combined KCB/MIBiG anchor instead of only `kcb_top`
(closing a bypass when the top line is a genome self-hit); this is a guard-input correctness fix,
not a scoring recompute. `.401` also adds the `capabilities` discovery subcommand, safe_walk 4-gate
consolidation, ten gate/hook coverage hardenings, cohort-ID guards, figure_check render wiring
(OPERATOR_ONLY → WIRED), the in-bundle wiki page set, the intake→package→archive containment chain
(non-regular ZIP-member admission, package-internal symlink rejection, no-clobber final archives),
Mode-B receipt identity parity, mandatory figure-review digests, bootstrap core-fallback install,
the exact-locus prompt contract, data-root wiring, thread tunables, two architecture-gate
lock-tests, and the B2 column promotion (label vocabulary only — readers take columns from the
sheet; pre-.401 workbooks keep folding promoted classes into 'other'). Cross-strain comparability
with .400 preserved; triage priors, scans, and parsing untouched.

**Previous engine:** 1.9.142

## Engine 1.9.142 — first bundle: v9.7.397

**Also shipped on 1.9.142 (engine unchanged, bundle-only bump):** v9.7.398 — 14-patch hygiene/robustness/QC fold; scoring-neutral, cross-strain comparability with .397 preserved.

**Also shipped on 1.9.142 (engine unchanged, bundle-only bump):** v9.7.399 — 20-patch case-insensitivity/resolver/phylo-tooling fold; scoring-neutral (no scoring module changed; master_workbook class-label correctness only), cross-strain comparability with .398 preserved.

**Also shipped on 1.9.142 (engine unchanged, bundle-only bump):** v9.7.400 — 24-patch package-slimming/class-label/hook-redesign/phylo/figure-gate/release-tooling fold; scoring-neutral (no scoring module changed; class-matrix label correctness + additive domain-tree sections only), cross-strain comparability with .399 preserved.

**Previous engine:** 1.9.141

**Scoring/parser/extraction semantics changed: NO.** `.397` adds a portable Figure Review Queue,
strengthens the Figure Caption Contract, and corrects EFLS reporting so total candidate-pair count is
not confused with the capped listed-pair count. The EFLS change affects emitted report semantics only;
it does not change the adapter's source records, scientific evidence, scoring, parsing, or extraction.
`scoring.py`, `parsers.py`, `rules.py`, and `domain_level.py` are unchanged.

**Comparability:** `.396`- and `.397`-scored boards are poolable with no re-score when their external
inputs are otherwise identical. The engine bump records post-seal review workflow, caption-policy, and
reporting-truthfulness behavior, not a change to scored biological evidence.

## Engine 1.9.141 — first bundle: v9.7.392

**Previous engine:** 1.9.140

**Scoring/parser/extraction semantics changed: NO.** `.392` is a deliberately small stabilization cut
on sealed `.391a`. It adds portable, logical-locator reroot postflight receipts with application-error
rollback and exact default redaction, and makes `--locus-maps off` suppress the compiled-report locus-map
renderer. `scoring.py`, `parsers.py`, `rules.py`, and `domain_level.py` are unchanged.

**Comparability:** `.391`- and `.392`-scored boards are poolable with no re-score when their external
inputs are otherwise identical. The engine bump records post-seal tool and figure-policy behavior, not a
change to scored biological evidence.

## Engine 1.9.140 — first bundle: v9.7.391

**Previous engine:** 1.9.139

**Scoring/parser/extraction semantics changed: NO.** `.391` is a deliberately small testing cut on
sealed `.390b`. It adopts immutable Matplotlib colormap configuration, removes macOS Finder metadata
from temporary public-tier staging before audit, and makes the Mode B triage locator fail closed on
missing or conflicting manifest identity and ambiguous triage-board selection. `scoring.py`,
`parsers.py`, `rules.py`, and `domain_level.py` are unchanged.

**Comparability:** `.390`- and `.391`-scored boards are poolable with no re-score when their external
inputs are otherwise identical. The engine bump records stricter operational preflight and figure
compatibility behavior, not a change to scored biological evidence.

## Engine 1.9.139 — first bundle: v9.7.390

**Previous engine:** 1.9.138

**Scoring/parser/extraction semantics changed: NO.** `.390` adds a portable, user-defined strain
privacy profile and evidence-availability registry, including CLI validation and generic examples;
hardens workbook write paths and portfolio validation; and adds release-governance and documentation
controls. The new registry records declared availability and privacy state only. It does not infer
scientific findings, change BGC scoring, or alter extraction records. `scoring.py`, `parsers.py`,
`rules.py`, and `domain_level.py` are unchanged.

**Comparability:** `.389`- and `.390`-scored boards are poolable with no re-score when their external
inputs are otherwise identical. Registry and privacy metadata may add governed intake context but do
not change existing scored-board values.

## Engine 1.9.138 — first bundle: v9.7.386

**Previous engine:** 1.9.137

**Scoring/parser/extraction semantics changed: NO.** `.386` folds three verified peer cards onto sealed
`.385`. The Mode B publication + structure §4 gene-column resolver now disambiguates multiple
"gene"/"locus" headers by digit-bearing cell shape (a gate-classification fix — it was raising a false
`PUBLICATION_GENE_TABLE_DUPLICATE` and, worse, silently missing a real one); `cli.py`'s `_write_package`
two-pathway early pass now records a propagated parse failure instead of swallowing it with no receipt;
and Amber's phylogenomics render/preflight tools gain accession-junk stripping, governed-host tip
cleaning, an off-target non-actinomycete guard, and multi-outgroup rooting. No file under `scoring.py` /
`parsers.py` / `rules.py` / `domain_level.py` changed behavior — `.385`/`.386` boards remain poolable with
no re-score. The engine bumped because Mode B gate classification and the run's failure-receipt behavior
changed (not scoring).

## Engine 1.9.137 — first bundle: v9.7.384

**Previous engine:** 1.9.136

**Scoring/parser/extraction semantics changed: NO.** `.384` is a reader/gate/provenance + onboarding cut
on sealed `.383`. It closes two holes in `.383`'s own new code (the node·region citation gate was
case-sensitive on `BGC\d+`; the CLINKER dark-protein linker read a non-existent `_aa` key), surfaces the
ClusteredNR channel in `roster_v2.build_gene_roster` (reader-only), repairs a Mode B publication-gate
§4 column regression, and adds `input_zip_sha256` to the manifest (provenance, additive — no
repro-fingerprint change). No file under `scoring.py` / `rules.py` / `domain_level.py` changed behavior;
`parsers.py` is untouched.

**Comparability:** `.383`- and `.384`-scored boards are poolable with no re-score, under the same
external cohort pack condition `.382`/`.383` document.

## Engine 1.9.136 — first bundle: v9.7.383

**Previous engine:** 1.9.135

**Scoring/parser/extraction semantics changed: NO.** `.383` is a reproducibility + doc-truth cut on
sealed `.382`. It ships the external tool & database inventory the bundle previously lacked, adds a
JSON-less-intake warning, makes the multi-tier privacy framework user-extensible, and refreshes stale
docs. `parsers.parse_bgcs_from_zip` gained a preflight *warning* when a `bounded`/`full` run meets a
ZIP with no record JSON, but the returned `BGCRecord` list is byte-identical — the warning is a side
channel, not an extraction change. No file under `scoring.py` / `rules.py` / `domain_level.py` changed
behavior.

**Comparability:** `.382`- and `.383`-scored boards are poolable with no re-score, under the same
external cohort pack condition `.382` documents.

## Engine 1.9.135 — first bundle: v9.7.382

**Previous engine:** 1.9.134

**Scoring/parser/extraction semantics changed: NO.** `.382` is the GitHub due-diligence remediation of
sealed `.381` (Codex audit): a whole-tree portability scrub (chat codenames + private workspace locators
→ generic names), a fail-closed `public_release_audit`, online-BLASTp submission safety, literature-corpus
prose removal, doc-truth reconciliation, and assorted robustness/release-safety fixes. No file under
`scoring.py` / `parsers.py` / `rules.py` / `domain_level.py` changed behavior, so every `.381` package
stays directly comparable.

**Comparability:** `.381`- and `.382`-scored boards are poolable with no re-score, under the same external
cohort pack condition that `.381` already documents (the governed set is still read from the external
`OFFICIAL_DATA/exclusions.json`; the bare public tree has no roster by design).

**First bundle carrying 1.9.135:** v9.7.382
**Last bundle on 1.9.134:** v9.7.381

## Engine 1.9.134 — first bundle: v9.7.381

**Previous engine:** 1.9.133

**Scoring/parser/extraction semantics changed: YES (conditionally) — FINGERPRINT class, EXTERNAL-PACK-GATED.**
`.381` is the public-facing generic-source + whole-tree identity-scrub derivation of sealed `.380`. It
folds the Tier-B + generic-source layer (P1–P7): the cohort roster is removed from the code tree and
`mamey/exclusions._DEFAULT` is emptied, with the governed roster/denominator now read from an EXTERNAL
`OFFICIAL_DATA/exclusions.json` pack (or `$MAMEY_DATA_ROOT`) at runtime; plus the 13 AUDIT_378
correctness fixes, a whole-tree personal-identity scrub, and public front-door files.

**Why FINGERPRINT and why external-pack-gated:** run STANDALONE (no external pack), the emptied
`_DEFAULT` makes `governed_denominator()` return `{}` and `governed_excluded()` return `[]` (verified),
so whitelisted board outputs that depend on the governed set differ from `.380`. Run WITH the maintainer's
`OFFICIAL_DATA/exclusions.json` supplied, the governed set restores EXACTLY to `{strains: 44, regions:
1753}` / `{AS-XXX, AS-XXX}` (verified lossless this cut). So:

- **Boards are comparable ONLY when the SAME external cohort pack is supplied.** With the private
  `.380`-equivalent pack present, `.380`- and `.381`-scored boards are expected to match on the governed
  cohort; the bare public tree is NOT board-comparable to `.380` (it has no roster by design).
- A `scoring.is_lead_excluded()` schema fix (recognizes the real `_4_triage_board.csv` TitleCase headers
  `Standing_rule`/`Primary_metab_flag`/`Mobile_element_flag`, which the lowercase-only variants silently
  missed) is included, but `triage_bgcs()` (the whitelisted-board writer) does NOT call it — it feeds
  figures/report pages/`domain_level` enrichment only, so it moves emitted deliverables, not the 8 boards.

**Identity scrub (whole tree, verified 0 files):** a prior maintainer username, a co-author/PI name and
affiliation, an old contact email, absolute home/workspace paths, and internal workspace names are all
absent (verified against the maintainer's private ban-list). The published AUTHOR name and GitHub handle
are PRESERVED by design. `public_release_audit.py` banned-list EXTERNALIZED to a gitignored `.identity_banlist`
(not shipped) with graceful structural-only fallback when absent.

**Comparability summary:** treat `.381` as a fingerprint boundary vs `.380` for standalone runs;
board-poolable with `.380` ONLY under an identical supplied cohort pack. The `.377`↔`.378` cohort
re-score remains separately owed.

**First bundle carrying 1.9.134:** v9.7.381
**Last bundle on 1.9.133:** v9.7.380-CODE

## Engine 1.9.133 — first bundle: v9.7.380

**Previous engine:** 1.9.132

**Scoring/parser/extraction semantics changed: NO — GATE-SEMANTICS class.** `.380` is the bounded
Tier-A cut (Codex triage's fold-first set): three cards addressing demonstrated Mode-B authoring/gate
failures, folded on sealed `.379`. Every scored and extracted artifact is byte-identical to `.379`:
`scoring.py`, `rggmci.py`, `parsers.py`, `rules.py`, `pks_ks_scan.py`, `exclusions.py`,
`clusterblast_genes.py`, `rescue_two_proof.py`, `split_detector.py` and `domain_level.py` are all
unchanged; the DETERMINISM_WHITELIST count stays 8 and the governed denominator is unchanged
(44/1,753). The change is confined to Mode-B emitter output, a verify gate, and a CLI tool:

- **`modeb_structure_gate.py` — anti-padding §4 guard.** The anti-padding detector no longer treats
  the complete §4 gene matrix (and §28/§29 bodies) as padding — a `verify-modeb` acceptance change
  that stops a legitimately-complete card being flagged; moves no scored artifact.
- **`modeb_template_emitter.py` (+ `docs/MODEB_GATE_CLEAN_AUTHORING.md` new, §-requirements doc,
  routing regression test) — emitter/publication-gate lifecycle routing.** Implements the "no branch"
  ruling: a fully-authored saved candidate keeps the publication gate; a fresh scaffold is not
  required to pass it. Adds the missing §4 `#### Complete named-match, channel-separated table`
  heading and corrects stale §1–§30 → §1–§48 wording. `mamey/modeb_publication_gate.py` unchanged.
- **`tools/claim_safety_linter.py` — CLI execution-order fix** (a defect in the linter's `main`;
  tooling only, process not scoring).

**Comparability:** re-lint Mode-B cards at 1.9.133 (a card previously mis-flagged as padding, or a
saved candidate previously mis-routed through the fresh-scaffold gate, now passes); no re-extraction
and no re-score — `.379`- and `.380`-scored boards are POOLABLE. The `.377`↔`.378` cohort re-score
remains owed from the `.378` fingerprint bump; `.380` adds no new re-score obligation.

**First bundle carrying 1.9.133:** v9.7.380
**Last bundle on 1.9.132:** v9.7.379-CODE

## Engine 1.9.132 — first bundle: v9.7.379

**Previous engine:** 1.9.131

**Scoring/parser/extraction semantics changed: NO — EMITTED-OUTPUT class.** `.379` is the SAFE candidate
on sealed `.378b`: only independently-verified-NEW cards were folded (the `AQUARIUS_379_REBASED_DIFFS`
audit lane backlog was deliberately NOT folded — it is largely already-landed in `.378b` and
forward-folding it reverts working fixes; it needs per-card new-vs-landed curation first). Every scored
and extracted artifact is byte-identical to `.378b`: `scoring.py`, `rggmci.py`, `parsers.py`,
`rules.py`, `pks_ks_scan.py`, `exclusions.py`, `clusterblast_genes.py`, `rescue_two_proof.py` and
`split_detector.py` are unchanged; the DETERMINISM_WHITELIST count stays 8 and the governed
denominator is unchanged (44/1,753). The four changed modules are all off the scoring/whitelist path:

- **`domain_level.py` — mobile-element lead-exclusion gap** (`_top_bgcs_from_package` now mirrors
  `scoring.is_lead_excluded`, reading `mobile_element_flag` from the manifest bgcs since the triage CSV
  lacks the column). `domain_level` is a POST-SEAL enrichment module — it reads the triage board but
  writes domain-level cards/receipts, none of the 8 whitelisted artifacts — so this changes an
  enrichment deliverable, not a scored board. (+ regression test.)
- **`antimicrobial_recall.py` / `concordance.py` — degradation guards** (graceful keyword-baseline /
  NO_REFERENCE when the reference maps are absent; fixes a latent crash on a missing data file).
- **`tab_reconcile.py` — generic antiSMASH-at-root marker** (replaces a hardcoded cohort filename
  sentinel with a generic `*.json`-at-root check).

Plus a `docs/Sapote-Mamey.bib` bibliography append (+21 entries) and a `cairosvg` importorskip
broadened to `OSError` for test robustness.

**Comparability:** `.378b`- and `.379`-scored boards are POOLABLE — no re-score owed at this boundary
(scoring path byte-identical). The `.377`↔`.378` cohort re-score remains owed from the `.378` fingerprint
bump; `.379` adds no new re-score obligation.

**First bundle carrying 1.9.132:** v9.7.379
**Last bundle on 1.9.131:** v9.7.378-CODE (build …378b)

## Engine 1.9.131 — first bundle: v9.7.378 (build …378b, EXPANSION_v2)

**Previous engine:** 1.9.130

**Scoring/parser/extraction semantics changed: YES — FINGERPRINT class.** `.378` (EXPANSION_v2)
folds the dropped `.376` Mode-B §4 observed-no-hit gate restoration together with four accepted
claim-safety / scoring correctness cards and a corrected claim-safety-gate fold. Two of those cards
touch detection logic that feeds whitelisted score-comparable artifacts, so the CONTENT of
`_4A_RGGMCI_ranked_pairs.csv`, `_4_triage_board.csv` and the `_4c` AB/AF lead boards can move for
affected BGCs:

- **`rggmci.py` — `_label_class_tokens` substring-collision fix.** A naive substring match let a
  qualified class collide with its own unqualified substring (`NI-siderophore` ⊃ `siderophore`,
  `NRP-metallophore` ⊃ `metallophore`), which antiSMASH treats as biosynthetically distinct types.
  Correcting the token match changes which RG-GMCI pairs are labelled which class/confidence →
  `_4A` ranked pairs (and the tiers they float) move for BGCs carrying those classes.
- **`clusterblast_genes.py` — asn_synthase promiscuous-core false-rescue.** Adds the missing core
  tokens so a promiscuous asparagine-synthase core no longer grants a false rescue; rescue
  eligibility (and thus scored tier) changes for affected pairs.

The remaining changes are **claim-safety / gate text only, no scored artifact moves**: `scoring.py`
(the `rg_note` rationale no longer claims an RG-GMCI rescue when the score gate refuted the pair —
the score-affecting `rescue_bonus` block at 620-635 is byte-identical to `.377`),
`rescue_two_proof.py` (mixed-subject-signal false-rescue guard — contradicted overlap evidence no
longer satisfies the disjoint-reference fallback), `claim_safety_gate.py` (filler-word overclaim
continuation PLUS the v9.7.378b direct typed-object construction — "produces the antibiotic
streptomycin" and kin now flagged, generic capacity phrasing preserved), and
`modeb_structure_gate.py` (the restored observed-no-hit §4 recognition + count-first `n/N` qcov — a
verify-gate change). `parsers.py`, `rules.py`, `pks_ks_scan.py`, `exclusions.py` and
`split_detector.py` are byte-identical to `.377`; the DETERMINISM_WHITELIST count stays 8 and the
governed denominator is unchanged (44/1,753).

**EXPANSION_v2 correction note (build …378b).** This bundle supersedes the earlier `…378a`
EXPANSION seal, which a Codex post-cut audit found shipped two defects: (1) the NRPS split-detector
fold widened fragment acceptance but left the body-alignment loop PKS-only, admitting a random
NRPS fragment as a HIGH split candidate — a false-positive scientific route; and (2) the
claim-safety fold missed direct typed-object overclaims and shipped without its regression test.
EXPANSION_v2 **omits the NRPS split-detector fold entirely** (`split_detector.py` reverts to `.377`;
the real fix — NRPS-vs-NRPS body homology with identity + coverage, refuse-when-no-homolog, and a
negative random-sequence test — is deferred to a dedicated lane card) and **corrects the
claim-safety fold** (direct typed-object forms now covered; regression test
`tests/test_claim_safety_gate_filler_word_overclaim.py` folded).

**Comparability: a cohort re-score is owed on `.378`+.** `.377`-scored and `.378`-scored boards are
NOT poolable for BGCs affected by the two detection-logic cards above — re-run scoring before
comparing tiers or lead ranks across the `.377`↔`.378` boundary. This is the first fingerprint bump
since `.375`; the intervening `.376`/`.377` bumps were emitted-output and their boards remain
poolable with each other.

**First bundle carrying 1.9.131:** v9.7.378 (build …378b)
**Last bundle on 1.9.130:** v9.7.377-CODE

## Engine 1.9.130 — first bundle: v9.7.377

**Previous engine:** 1.9.129

**Scoring/parser/extraction semantics changed: NO — EMITTED-OUTPUT class.** `.377` folds three
Codex-"retain" correctness cards that change Mamey OUTPUT/gate behaviour but leave every scored and
extracted artifact byte-identical: `scoring.py`, `parsers.py`, `rules.py`, `domain_level.py`,
`pks_ks_scan.py`, `rescue_two_proof.py`, `source_scans.py`, `packaging.py` and `exclusions.py` are
all byte-identical to sealed `.376`, the DETERMINISM_WHITELIST count stays 8, and the governed
denominator is unchanged (44/1,753). The output-affecting drivers:

- **`mamey/compile_report.py` — corrected-rank exclusion in Key Findings.** An engine-excluded BGC
  (standing-rule / primary-metabolism / mobile-element withhold, `corrected_rank is None`) could
  previously re-enter the compiled report's Key Findings via its raw `Rank`; it can no longer.
  The compiled-report Key Findings surface changes for any strain that has an excluded-but-
  high-raw-rank BGC. (New test `tests/test_compile_report_corrected_rank_exclusion_v9_7_377.py`.)
- **`mamey/antismash_tables.py` — `double_record_pass_fix`.** The second antiSMASH record pass is
  eliminated, correcting the record-pass count (fixes the previously-red
  `tests/test_record_pass_count.py`); the emitted antiSMASH table no longer double-counts.
- **`mamey/bgc_l0_program.py` — atomic `_write_rows`.** The 8 L0 tables now write via tmp +
  `os.replace` (crash-safety; byte-content of a completed write is unchanged). (New test
  `tests/test_bgc_l0_write_rows_atomic.py`.)

**Comparability:** re-emit/re-lint affected compiled reports and antiSMASH tables at 1.9.130; scores,
triage, lead boards and every package artifact need NO re-derivation — `.376`- and `.377`-scored
boards are poolable.

**First bundle carrying 1.9.130:** v9.7.377
**Last bundle on 1.9.129:** v9.7.376-CODE

## Engine 1.9.129 — first bundle: v9.7.376

**Previous engine:** 1.9.128

**Scoring/parser/extraction semantics changed: NO — EMITTED-OUTPUT class.** `.376` changes Mamey OUTPUT
text/structure but NOT scored/extracted artifacts: `triage_bgcs` and all of `scoring.py`'s scoring paths are
byte-identical (the new `is_lead_excluded()` is a standalone predicate consumed only by figure/report builders,
never by `triage_bgcs`), so `_4_triage_board.csv` and the `_4c` boards are unchanged. **No re-score owed; `.375`
and `.376` boards ARE poolable.** The output-affecting drivers (deliverable surfaces only):

- **Workbook (`master_workbook.py`) — A4_Completeness_Audit** now reports computed verdicts (INCOMPLETE_EXTRACTION /
  NOT_LOADED) instead of hardcoded PASS.
- **Figures (`figures_extra.py` / `figures_sapote.py`)** delegate to `scoring.is_lead_excluded()`; the Sapote
  priority figures now also exclude mobile-element-demoted BGCs (a closed gap), changing which BGCs appear.
- **Report (`compile_report.py`)** surfaces the manifest `issues` list; **roster (`roster_v2.py`)** completes the EBI channel.

DETERMINISM_WHITELIST unchanged (8); governed-exclusion denominator unchanged (44/1,753); `scoring.py` scoring
logic, `parsers.py`, and `rules.py` are byte-identical to 1.9.128.

## Engine 1.9.128 — first bundle: v9.7.375

**Previous engine:** 1.9.127

**Scoring/parser/extraction semantics changed: YES.** `.375` folds correctness cards that change real
Mamey **output**, so the engine bumps under the standing rule (bump when Mamey OUTPUT changes because the
engine changed). The output-affecting drivers:

- **Scoring (`scoring.py`) — RG-GMCI rescue-class guard.** The auto-floor rescue bonus now consults
  `functional_rescue_class` and withholds credit from ACCESSORY_ONLY-only pairs; AB/AF/novelty routing
  priors change for BGCs that previously took an unguarded homology-only bonus.
- **Scoring (`scoring.py`) — inventory ambiguous-token tiering.** `is_housekeeping_only()` now honours the
  `ambiguous_review_tokens` policy, so BGCs previously auto-filed at Inventory tier on an ambiguous token
  can route to review.
- **Scan (`source_scans.py`) — domain over-count + bare-abbrev class triggers.** `aSModule`/`CDS_motif`
  features are no longer counted as domains, and bare domain-name substrings no longer trigger unrelated
  class patterns; domain counts and class calls change for affected BGCs.
- **Model (`models.py`) — manifest downgrade fields.** Standing-rule/exclusion explaining fields are now
  emitted on the manifest, changing the manifest handoff surface downstream sessions consume.

**BUMP CLASS: FINGERPRINT (amended v9.7.376).** The DETERMINISM_WHITELIST *count* stays 8, but the
`scoring.py` changes above move the CONTENT of whitelisted score-comparable artifacts —
`_4_triage_board.csv` and the `_4c` AB/AF lead boards — for affected BGCs. This is the first
fingerprint-class bump since `.366`. **A cohort re-score on `.375b`+ is owed; `.374`-scored and
`.375`-scored boards are NOT poolable** — do not compare pre/post-boundary tiers or lead ranks
without re-derivation. The governed-exclusion denominator is unchanged (44/1,753); `parsers.py` and
`rules.py` are byte-identical to 1.9.127. (The sealed `.375` stanza under-stated this as
"whitelist unchanged" without the fingerprint tag; corrected here per the `.375b` outstanding-items
ledger ACT-01.)

## Engine 1.9.127 — first bundle: v9.7.374

**Previous engine:** 1.9.126

**Scoring/parser/extraction semantics changed: YES (partial).** Unlike 1.9.126 (a Mode-B
gate-semantics-only bump), `.374` includes fixes that change real Mamey **output**, so the engine
bumps under the standing rule (bump when Mamey OUTPUT changes because the engine changed). The
output-affecting drivers:

- **Scan routing (`source_scans.py`) — arylpolyene wet-lab misclassification.** An unbounded substring
  match routed an arylpolyene pigment locus toward antifungal-priority wet-lab guidance it doesn't
  merit; corrected, so the wet-lab routing column changes for affected loci.
- **Adjudication (`rescue_two_proof.py` / two-proof logic) — complementarity inversion.** `_logic_proof`
  accepted paralogy (`BOTH_CORE`) as a genuine split and never checked the real `COMPLEMENTARY`
  signature — inverting the two-proof verdict for the exact false-positive case it screens. Corrected,
  so two-proof adjudication verdicts change for those pairs.
- **Boundary verdicts (`boundary_audit`) — mobile-element flag.** `mobile_element_flag` never reached
  `verdicts.json` and wasn't checked where written; a mobile/ICE-flagged verdict could carry a live
  `corrected_rank`. Now serialized and enforced, changing `verdicts.json` and rank for flagged regions.
- **Cross-strain workbook (`master_workbook.py`) — dead columns revived.** `CGAD_chitin`/`TFBS_DasR`
  read wrong dict keys and were silently zero in every workbook; corrected to the real scan keys, so the
  cross-strain sheet now carries real values (a prospective-only change — no shipped figure consumed the
  false zeros, per the blast-radius trace).
- **Governed exclusion + identity guards (`exclusion_gate` / strain-ID).** Case/prefix guards that were
  case-sensitive where strain IDs are not; corrected, changing which strains pass the governance gate.

**Gate-semantics / integrity-only changes (no package re-derivation):** the fabrication and fail-open
gate re-wirings (`mode_b_receipt` ingest door, `seal_package` locator, G2/deliverable-suite/guide/
v-status gates, KCB-recycling surfacing), the STRAIN-INTERNAL contamination guards
(`extract_module_core_domains` + `ks_phylogeny`), the claim-safety bioactivity-phenotype wiring (WARN,
non-blocking), the BLASTp/comparator channel-integrity fixes, and the atomic-write/crash fixes. These
change what the engine **detects, refuses, or writes atomically**, not the scored extraction of a clean
input.

**Public/private redaction layer:** held out of this cut per the 2026-08-22 PI decision (re-added during
analysis, not the default workflow) — so no release-tier/redaction semantics changed here.

Built by the patch lane from audit lane's audit cards; the Developer or User seals.

## Engine 1.9.126 — first bundle: v9.7.373

**Previous engine:** 1.9.125

**Scoring/parser/extraction semantics changed:** **NO.** Extraction, triage, and every package
artifact are byte-unchanged. This is a **Mode-B gate-semantics bump** (same class as 1.9.122/1.9.123/
1.9.125): the finished-card verification path changes what `verify-modeb` reports on
`FINISHED_FULL48_CURRENT_EVIDENCE` / legacy `FINISHED_CURRENT_EVIDENCE` cards. Three drivers, all in
the Mode-B gate layer; no package re-derivation needed.

**What lands (the patch lane 2026-08-21; Codex §4-title decision relayed; the Developer or User seals):**

- **Driver 1 — the matrix-roster gate is now actually enforced (BREAK-1).** The `.372`
  `_section4_complete_blastp_matrix_findings` gate demanded `ctx["known_locus_tags"]`, but no
  production context builder ever set that key — `authored_verify._bgc_context_from_package` set
  `known_loci` / `locus_home` under different names, so every finished card verified via
  `verify-modeb --package --bgc` hit `BLASTP_MATRIX_ROSTER_UNBOUND` and the roster was never checked
  (fail-open; only a test injecting the key exercised the pass path). Fixed: `authored_verify` now
  derives the exact per-BGC roster from the parsed `locus_home` (gene_by_gene membership, which
  already includes declared boundary-context CDS (verified on a real per-BGC roster), exactly
  the card's displayed roster) and sets `ctx["known_locus_tags"]`. Announced change: finished cards
  can now newly ERROR (real roster mismatch) or PASS (roster bound) where `.372` could only ever emit
  `ROSTER_UNBOUND`. Test: `tests/test_roster_key_wiring_v9_7_373.py`.

- **Driver 2 — one shared §4 matrix-table locator across both gates (BREAK-3).** The matrix gate and
  the publication gate previously located the §4 table by different rules (a strict heading regex vs a
  content regex), so they disagreed on real cards. Both now call
  `mamey.modeb_structure_gate.find_s4_matrix_block`, which accepts the canonical named-match heading,
  its measured `…gene table` variant, and the legacy `Complete channel-separated BLASTp matrix` form,
  scoped to §4 (an unrelated §4 table is not mistaken for the matrix). Codex ratified the canonical
  title (`Complete named-match, channel-separated table`) and the single-locator/both-headings
  contract 2026-08-21; the emitter converges new cards to canonical (emitter-side follow-up).
  Announced change: the matrix gate now FINDS the table on the 22 native cards where `.372` returned
  `BLASTP_MATRIX_MISSING`. Test: `tests/test_s4_matrix_locator_v9_7_373.py`.

- **Driver 3 — the finished-card profile auto-triggers the publication gate (B1).**
  `authored_verify` now activates `check_publication_quality` (and passes the canonical roster) when a
  card carries `FINISHED_FULL48_CURRENT_EVIDENCE` or the legacy `FINISHED_CURRENT_EVIDENCE` alias
  (per the ratified status vocabulary). Announced change: exactly the two finished shelf cards
  (AS-XXX/BGC045, AS-XXX/BGC067) now run the full §§1–48 publication battery under `verify-modeb`;
  draft/gap-aware cards are unchanged. Full-suite blast radius measured: **0 failures** (5030 tests;
  one env-gated test flipped passed↔skipped between independent runs, not a regression in the changed
  path).

**Comparability:** `verify-modeb` verdicts on finished-profile cards change per the three drivers
above; extraction/triage/scoring/packaging outputs are byte-identical to 1.9.125. Draft-profile
verdicts are unchanged.

## Engine 1.9.125 — first bundle: v9.7.372

**Previous engine:** 1.9.124

**Scoring/parser/extraction semantics changed:** **NO.** Extraction, triage, and every package
artifact are unchanged. This is a **Mode-B gate-semantics bump** (same class as 1.9.122/1.9.123):
the finished-card profile gains a hard gate. A card declaring `FINISHED_CURRENT_EVIDENCE` (or a
caller passing `require_complete_blastp_matrix`) must carry the complete channel-separated per-gene
BLASTp matrix — one row per canonical roster gene, nr/ClusteredNR/Swiss-Prot rank-1 kept distinct,
%id/%positives/qcov per bound cell, typed missing-states — enforced by five new `BLASTP_MATRIX_*`
ERROR states in `mamey/modeb_structure_gate.py`. Draft/gap-aware cards keep the warning-first path.

**What lands (CODEX_372_modeb_complete_blastp_matrix; the patch lane admission review 2026-08-20):**
the gate + contract doc section + 29-test battery; real-card control: the corrected AS-XXX v2
finished card passes 41/41 matrix rows, and the v1 card that motivated the gate now fails it.

**Comparability:** verify-modeb verdicts on FINISHED_CURRENT_EVIDENCE cards can newly ERROR where
the matrix is absent/incomplete — that is the gate working; draft-profile verdicts are unchanged.
No package re-derivation needed. 1.9.125 additionally carries: the no-pending amendment
(`BLASTP_MATRIX_PENDING_TERMINAL` — `pending` is not a terminal finished-matrix state), the
exact-locus four-field filename gate in `tools/check_bgc_naming.py`, and the VGP
`--antismash-profile auto` default — `manifest.json`/`_1_intake.json` now record the strictness
READ FROM the archive instead of the operator's unverified word (explicit values honoured, loud
`PROFILE_MISMATCH` on disagreement). Packages produced at 1.9.125 can therefore carry a different
(correct) `antismash_profile` than a 1.9.124 run of the same archive that defaulted to `unknown`.
The strain-identity guard is the same rider class: a single-strain run supplying an accession as
`--strain` can now refuse (exit 2, naming the correct id) where 1.9.124 proceeded, and batch runs
auto-upgrade accession ids to archive-resolved organism names — package names/manifest `strain_id`
for accession-named inputs change accordingly.
Also in v9.7.372 (doc/data only, no engine semantics): AS-strain BGC-content anonymization per the
2026-08-19 disclosure audit, and the public type-strain Full48 reference exemplar.

**Second gate-semantics change at this engine (added after the first draft of this stanza — the
publication-quality lane):** `mamey/modeb_publication_gate.py` is new and wired into
`modeb_structure_gate.lint_card` behind `check_publication_quality`. When that check is requested,
a publication-candidate card is validated fail-closed against an externally supplied canonical
roster: contiguous homology tables (blank-separated tables no longer read as one table), §§1–48
all required with a reasoned `NOT_APPLICABLE` disposition instead of omission, deep §§5–7
scientific scaffolds, a 48-row section-accountability matrix, typed dispositions for all 14
supporting streams, and a mandatory emitted `strain / full node-or-contig / region / BGC alias`
identity. Mechanical readiness is capped at `EVIDENCE_MATRIX_VALIDATED`.

**Emitted-output change (not only verdicts):** `mamey/modeb_template_emitter.py` was rewritten in
the same card — the §7 emitter and the card header/prompt text changed. A card scaffold emitted at
1.9.125 therefore differs in prose from one emitted at 1.9.124 even before any gate runs. Two
legacy Part-C contract elements dropped by that rewrite (the "grounded, from cohort precompute"
provenance marker and the never-a-phenotype discipline line) were restored by semantic merge
inside the new structure; both contracts' tests pass.

**Comparability (publication lane):** cards authored against the 1.9.124 emitter can newly fail
the publication gate on structure alone; this affects Mode-B authoring/verdicts only. Extraction,
triage, scoring, and every package artifact remain unchanged, and `DETERMINISM_WHITELIST` is
unchanged at 8 entries — no package re-derivation is needed for this change either.

**First bundle carrying 1.9.125:** v9.7.372
**Last bundle on 1.9.124:** v9.7.371-CODE

---

## Engine 1.9.124 — first bundle: v9.7.371

**Previous engine:** 1.9.123

**Scoring/parser/extraction semantics changed:** **NO.** AB/AF/novelty priors, standing rules,
RG-GMCI, and every extraction artifact are unchanged. This is an **emitted-output and
workflow-gate bump** (the Developer or User's standing rule, restated 2026-08-19: bump when Mamey output changes
because the engine changed). Three output surfaces move:

1. **Mode-B template text** (`mamey/modeb_template_emitter.py`): §4's pre-filled BLASTp command
   now names the real BGC (`--bgc BGC023`); every card emitted before 1.9.124 carried the literal
   `--bgc BGC` because the emitter read a facts key (`bgc`) that production never populated
   (real key: `bgc_id`).
2. **Sapote workflow gate results** (`mamey/sapote_workflow.py::s4_modeb`): the W4 gate now reads
   the judgment register's real `bgcs` key. Before, `complete` was permanently 0 while overall
   `judgment_status` was IN_PROGRESS (the whole authoring period) and constantly 1 when COMPLETE —
   so PASS/PENDING flips for strains with real completed Mode-B work.
3. **Workbook README tab guide** (`mamey/workbook.py`): the `_5_workbook.xlsx` cover sheet grows
   22→42 sheet descriptions (every emitted tab now documented; 7 generic entries reviewer-checked
   against `models.py` field comments).

Plus the wider audit lane wave-1 hygiene surface (atomic writes, case-sensitivity, wrong keys,
swallow fixes) — defect repairs whose intended outputs are unchanged; the three surfaces above are
the bump drivers. See the v9.7.371 CHANGELOG entry and the `.371` queue's per-card receipts.

**Comparability:** extraction/triage outputs need no re-derivation. Mode-B cards generated before
1.9.124 carry the literal `--bgc BGC` in §4 — cosmetic, no re-generation required; the identity of
the evidence is unaffected. Workflow-driver runs mid-flight at 1.9.123 should re-run `s4_modeb`
once at 1.9.124 (a falsely-PENDING gate will clear; a falsely-PASS one cannot have occurred with
COMPLETE status absent).

**First bundle carrying 1.9.124:** v9.7.371
**Last bundle on 1.9.123:** v9.7.370-CODE

---

## Engine 1.9.123 — first bundle: v9.7.370

**Previous engine:** 1.9.122

**Scoring/parser/extraction semantics changed:** **NO.** No `DETERMINISM_WHITELIST` artifact moves;
AB/AF/novelty priors, standing rules, RG-GMCI, and every extraction output are byte-unchanged. This is
a **Mode-B gate-semantics bump** (same class as 1.9.122): the `verify-modeb` door's evaluable-input set
changes. W7 two-door unification replaces the verify door's hand-kept whitelist merge of triage-context
keys with a full merge (authored package-derived values keep precedence), so both lint doors evaluate
identical conditionals **by construction** for every current and future context key. A card missing a
conditional section whose predicate the verify door previously could not see can newly ERROR — the
divergence class the W4 closing report measured (disagreement in both directions) is closed.

**What lands (AQUARIUS_370_w7_two_door_unification; the Developer or User include call 2026-08-18):** one hunk in
`mamey/authored_verify.py` (whitelist tuple → full tctx merge) + 5 door-parity tests including an
every-key-visible pin that fails the suite on any future whitelist regression.

**Comparability:** re-run `verify-modeb` at 1.9.123 — verify verdicts are now identical to
ingest/record verdicts for the same card+context; historical verify-door passes on under-authored
cards may not reproduce (correct). Extraction/triage outputs need no re-derivation. Measured
blast radius on 140 canonical cohort cards: zero verdict changes.

**First bundle carrying 1.9.123:** v9.7.370
**Last bundle on 1.9.122:** v9.7.369-CODE

---

## Engine 1.9.122 — first bundle: v9.7.369

**Previous engine:** 1.9.121

**Scoring/parser/extraction semantics changed:** **NO.** No `DETERMINISM_WHITELIST` artifact moves — `_2`/`_3`/`_4_triage_board`/`_4c`/`_4A`/`_4B` are byte-for-byte unchanged, AB/AF/novelty priors and every standing rule are untouched, and the fold does not read or write any scoring path (`grep` of the three changed files against `scoring.py` = 0). This is a **Mode-B gate-semantics bump**, not a fingerprint-artifact bump: the integer moves because a *deterministic gate* changes acceptance behavior, and per the engine-versioning rule "deterministic gate/checkpoint rules tie to the engine version." `verify-modeb` verdicts change for under-authored §31–§48 cards — a card that skips a now-`conditional` section (e.g. §43 with an above-bar RG-GMCI pair) errors where it previously passed. That is the intended effect.

**What lands (CERULEAN_369_full48_gate_binding; INDIGO2 generator-owner sign-off; the Developer or User green-lit the early fold + bump 2026-08-17):** three halves, all required —
- `mamey/mode_b_receipt.py::_bgc_context_from_triage` binds four package-derived keys into the Mode-B context (`module_count` = aSModule features only; `protocluster_count`; `n_4a_rows` = above-bar RG-GMCI pairs only; `n_4d_rows`), read-only/deterministic; a read failure leaves the key absent → predicate fail-safe False.
- `mamey/data/mode_b/modeb_full30_corrective_contract.json` flips seven §31–§48 sections `optional→conditional`, bound to predicates the engine already computes (§32/§33/§34→`has_assembly_line`, §35→`multi_protocluster`, §36→`boundary_or_overmerge_flag`, §38→`has_resistance_signal`, §43→`has_4a_rows`).
- `mamey/authored_verify.py` extends the selective tctx→ctx merge with the four predicate-input keys, so `verify-modeb` and ingest/record evaluate the same conditionals (closes the two-door divergence; full W7 unification is a separate `.369` card).

**Comparability:** re-lint Mode-B cards at 1.9.122 — under-authored §31–§48 cards that passed under 1.9.121 will now correctly error; extraction/triage outputs need no re-derivation (unchanged). Announced-change blast radius on the 82 first-generation W4 cards, re-measured after INDIGO2's honest §32–§34 re-authoring: **ZERO.** Claim ceiling: card-structure enforcement only; a bound section asserts an evidence STATE is positive, never biology; NOT-RUN ≠ biological zero.

**First bundle carrying 1.9.122:** v9.7.369
**Last bundle on 1.9.121:** v9.7.368-CODE

---

## Engine 1.9.121 — first bundle: v9.7.366

**Previous engine:** 1.9.120

**Scoring/parser semantics changed:** **NO for triage — the change is confined to the `_4B` advisory
channel.** The bump exists because `_4B_pks_ks_fragment_scan.csv` is in the determinism-fingerprint
whitelist and its content changes: the KS single-linkage clade pass is now partitioned by the antiSMASH
`/domain_subtypes` qualifier (a trans-AT KS can no longer join a cis-AT clade by transitivity). AB/AF/novelty
priors, every standing rule, all gates, and the RG-GMCI `_4A` output are **byte-for-byte unchanged** — `_4B`
feeds no scoring path (`grep _4B mamey/scoring.py` = 0), so **no triage value moves**. The integer is bumped
(not held) purely because a whitelisted deterministic output changes — the SSOT rule for a fingerprint-bearing
artifact.

**What lands (AMBER_366_C12, Amber `_4B`-owner sign-off 2026-08-12):**
- `mamey/pks_ks_scan.py`: `ks_domains_from_gbk()` parses `/domain_subtypes` (already in the region GBKs —
  no antiSMASH re-run); the containment/single-linkage pass unions two KS **only when they share the same
  named subtype** (Hybrid-KS with Hybrid-KS only); UNCLASSIFIED KS are kept out of the union-find and surfaced **pairwise** (each qualifying cross-contig unclassified pair is its own 2-member candidate, never transitively merged). New `ks_subtype` +
  `ks_subtype_partition_version` columns on `{strain}_4B_pks_ks_fragment_scan.csv`.

**Comparability:** re-derive `_4B` (and any `_4D` join that consumes it) at 1.9.121; do **not** re-score
triage priors — they are unchanged. Measured impact: 2/288 same-locus candidates drop under the partition;
nothing promotes/demotes to a confirmed split. `_4B`/`_4D` remain advisory CANDIDATES, never triage inputs.

**First bundle carrying 1.9.121:** v9.7.366
**Last bundle on 1.9.120:** v9.7.365-CODE

---

## Engine 1.9.120 — first bundle: v9.7.359

**Previous engine:** 1.9.119

**Scoring/parser semantics changed:** **NO — purely additive.** This bump adds a new deterministic
source-derived scan and two new package artifacts; it changes **no** existing triage value. AB/AF/novelty
priors, all standing rules, every gate that existed at 1.9.119, and the full RG-GMCI `_4A` output are
**byte-for-byte unchanged**. Prior packages remain fully score-comparable across 1.9.119↔1.9.120; they
simply lack the two new files. The engine integer is bumped (not held) only because new deterministic
outputs enter the package + the repro fingerprint — the SSOT rule for "new deterministic scan/checkpoint."

**What lands (phylogenomics-lane P358 `_4B/_4D`, converges BB_15 + the review lane C06 + contributor lanes KS-phylogeny RFCs):**
- `mamey/pks_ks_scan.py` → `{strain}_4B_pks_ks_fragment_scan.csv`: an offline, stdlib-only, cross-contig
  PKS-KS clade scan (5-mer containment + single-linkage) — reference-FREE homology that complements
  RG-GMCI's reference-based tiling. Wrapped to never fail the core run; joins the determinism fingerprint.
- `mamey/rescue_two_proof.py` → `{strain}_4D_two_proof_rescue.csv`: joins `_4A` (reference-based) × `_4B`
  (reference-free) under the review lane's C06 two-proof gate → `TWO_PROOF_RESCUE` / `KS_CLADE_ONLY` /
  `RGGMCI_ONLY` / `WEAK`. **Advisory only:** every verdict is a CANDIDATE for adjudication, never a merge,
  never a triage-score input. `validate.py` records a NON-BLOCKING `PKS_KS_SCAN_MISSING` note when absent.

**Comparability:** nothing to re-score. `_4B`/`_4D` are new advisory artifacts, not re-scored priors — do
not attempt to pool them backward before .359 (they simply don't exist earlier). Everything else pools freely.

**First bundle carrying 1.9.120:** v9.7.359
**Last bundle on 1.9.119:** v9.7.358 (parked candidate; sealed line topped out at v9.7.357-CODE)

---

## Engine 1.9.119 — first bundle: v9.7.338

> **WITHIN-1.9.119 NON-NEUTRAL UPDATES (comparability notes; the engine integer was held at the enforced
> SSOT across these — re-score only the named loci, not the whole cohort):**
> - **v9.7.350 — AQUARIUS_01 Inventory-tier reform (LABEL-only, forward-only):** the bottom tier became
>   class-gated (housekeeping→`Inventory`, specialized→new `Low`). **No AB/AF/novelty value changed** — a
>   pure re-label; all scores comparable .349↔.350. Only the `Lead_tier_auto` *string* differs for
>   specialized below-Medium loci.
> - **v9.7.351 — CLAUDE_AUG3_07 over-merge de-inflation (SCORE change, forward-only):** composite regions
>   (`protocluster_count≥2`, non-`chemical_hybrid`, ≥2 distinct products) now score MAX-over-protocluster
>   instead of the UNION. **106 BGCs change AB/AF/novelty (all decreases); 34 tier moves (33 Medium→Low,
>   1 High→Low: AS-XXX BGC002 AF 76→30); 0 increases; 0 hybrids moved** (38 AS zips / 1,507 BGCs on the
>   sealed-.350 base). **DO NOT pool these 106 composite BGCs across .350↔.351 — re-score them.** Every
>   single-protocluster and chemical-hybrid BGC is byte-identical; everything else remains comparable.
>   Forward-only: existing sealed boards keep their labels.
> - **v9.7.352 — H4 nucleoside-AF clamp scope narrowed (SCORE change, forward-only):** numeric
>   priors otherwise unchanged. The polyene mis-anchor clamp `min(base_af, 20)` no longer caps a
>   locus carrying its own corroborated non-polyene AF diagnostic (T43-NUC nucleoside / T43-PTM);
>   it still fires when the polyene KCB anchor is the SOLE AF evidence. Moves `af_score` (and can
>   move `Lead_tier_auto`) only on the rare polyene-anchor + corroborated-nucleoside co-fire path.
>   Do NOT pool af_score/Lead_tier_auto across this boundary for those loci. PI ruling the Developer or User 2026-08-05.
>   Also v9.7.352: AS-XXX ratified into GOVERNED (denominator 44/1,749 -> 45/1,787) via mamey/exclusions.py SSOT; raw assembly still void-quarantined for raw-reading layers; hard-exclude stays AS-XXX.

**Previous engine:** 1.9.118

**Scoring/parser semantics changed:** **YES — one item, narrow and upward-only (RG-01/NAPAA), plus a seal-integrity fix that is not a scoring change.**

RG-01 lifts the NAPAA-exclusion standing rule. NAPAA (non-alpha-poly-amino-acid) loci were held at a standing-rule floor regardless of their computed prior; they now surface at that prior. The audit chat's 11-strain cohort re-seal (identical BGC counts .337↔.338) showed exactly three `Lead_tier_auto` promotions — AS-XXX BGC029 and AS-XXX BGC034 Inventory→Exceptional, AS-XXX BGC012 Inventory→Medium — with `AB_auto`/`AF_auto`/`Novelty_auto` and every misanchor flag **unchanged**, plus four tier-neutral NAPAA-exclusion removals. Every move is upward and is the removal of a cap, not a re-scored prior. **NAPAA loci are not comparable across the 1.9.118/1.9.119 boundary — re-score; everything else is comparable.**

**Seal integrity (SEAL-02b) — found and fixed in this bundle, not in the incoming handoff.** The handoff's SEAL-02 made `_phase_package_seal` rewrite `gate_validation.json` from the final post-seal re-validation, which is correct. But `write_manifest()` hashes `gate_validation.json` (mid-build content) into `checksums_sha256.txt` first, and the filename was not in the writer's mutable-receipt exclusion set — so a **fresh** gold seal produced a file whose bytes no longer matched its recorded hash and failed its own `checksum_integrity` gate, sealing as VALIDATION_FAIL. Reproduced on a fresh seal of the bundled micromonospora fixture. Root cause was set-duplication: the "rewritten after checksum capture" name set existed in five hand-copied places across `packaging.py` and `validate.py` and had already drifted (two validator copies lacked `repro_fingerprint.json`). Fixed by defining `packaging.MUTABLE_RECEIPT_NAMES` once — with `gate_validation.json` added — and referencing it from every writer and validator site. This is bookkeeping, not scoring: it changes which files are hash-pinned, never any triage value. **Every package in a fresh cohort run on the raw handoff would have sealed VALIDATION_FAIL without it**; the handoff's re-seal report missed it because it validated via `package_status.json` rather than re-checking `checksums_sha256.txt`.

The five verdict-changing gate items (GATE-11, GATE-12, SEAL-02, SEAL-03, WB-02) land here after being held from v9.7.337. They were held then because, as measured in the .337 trial, `GATE-11 rggmci_gate` FAILed the ordinary `NULL_NO_RGGMCI_PAIRS`-with-no-parsed-references state and `SEAL-03 checksum_integrity` FAILed on post-manifest files — both of which reddened real packages. The handoff resolves the `rggmci_gate` state (verified: PASS on a fresh seal), and SEAL-02b resolves the checksum path. With both closed, the cohort re-seal shows 0 red-flips across 11 strains, so they land.

**Not in this bundle:** CAT-01 (design change, see 1.9.117 entry); the D1 comparator-coverage scoring wire (ships UNWIRED, sign-off pending, ~1.5% tier move per the handoff's impact note). MB-01/04 card-gate behaviour is present but was not exercised by the extraction-only re-seal.

**First bundle carrying 1.9.119:** v9.7.338
**Last bundle on 1.9.118:** v9.7.337

---

## Engine 1.9.118 — first bundle: v9.7.337

**Previous engine:** 1.9.117

**Scoring/parser semantics changed:** **YES — deliberately, narrowly, and in the conservative direction.** This engine exists for one fix. `scoring.py` gated both the aminoglycoside and the polyene mis-anchor clamps behind a single global `not tier1_diag`, so **any** Tier-1 CCTT diagnostic lifted **both** clamps regardless of class. Reproduced first-hand on the project's own `tests/test_misanchor_guards.py::_bgc` fixture: a `RiPP-like` locus with a `natamycin` polyene anchor and **zero** PKS KS domains scored **AF 20.0 / Inventory** with the flag `polyene_anchor_<4_PKS_KS(ks=0)`; adding the unrelated `T43-NUC_nucleoside` trigger produced **AF 45.0 / Medium with the flag erased**.

The clamps are now **unconditional**. That is stricter than the class-keyed rescue first considered, and simpler — the guards are themselves the machinery test. `source_scans` emits `aminoglycoside_misanchor` only when a committed DOIS gene is absent, and `polyene_misanchor` only when the locus carries fewer than four PKS KS domains. If the class-specific machinery existed, the flag would never have been emitted, so no diagnostic — related or not — should be able to lift it. A trigger-keyed variant was implemented and discarded: `T43-PYE` has its own separate `_pye_corrob` path and did not lift the clamp anyway, making the keyed version strictly more code for identical behaviour.

Unrelated Tier-1 evidence is **not** suppressed: `DIAGNOSTIC_BONUS` is untouched, and a lead tier can still rise on a genuine diagnostic while the mis-anchored axis stays floored and the warning survives for a human reader. This completes a direction the code was already moving — the enediyne (§4.3) and class-mismatch (v9.7.63) guards in the same block already fired independently of `tier1_diag`; the aminoglycoside/polyene pair was the last one still exempted. `tier1_diag` retains its four other uses (primary-metabolism flag, mobile flag, tier floor), so nothing is orphaned.

**Comparability.** Only loci carrying an emitted aminoglycoside or polyene mis-anchor flag **and** an unrelated Tier-1 trigger change. For those loci, `AB_auto`/`AF_auto` are now floored where they previously escaped and `Lead_tier_auto` can fall. **Do not pool such loci across the 1.9.117/1.9.118 boundary — re-score.** Everything else (BGC counting, KCB/AB/AF priors elsewhere, product classes, workbook columns) is unchanged from 1.9.117.

**Not in this bundle, with receipts.** The five verdict-changing items (GATE-11, GATE-12, SEAL-02, SEAL-03, WB-02) were applied to this tree, tested and reverted. Together they produced **7 failures and 6 errors** in the full suite, and validating a real sealed package produced by this pipeline returned **FAIL** on two independent dimensions: `rggmci_gate` FAILs the ordinary `NULL_NO_RGGMCI_PAIRS`-with-no-parsed-references state, and `checksum_integrity` FAILs on files the sealer itself writes after computing the checksum manifest (`repro_fingerprint.json`, `PACKAGE_MAP.json`, `<strain>_compiled_report.md`, `smoke_figures/*`) — a package failing its own integrity gate. Both are directionally correct and both need the seal write-ordering fixed before they can land. **CAT-01** also remains out; see the 1.9.117 entry for its first-hand two-BGC measurement and for why it must be decided before a large cohort run rather than after.

**First bundle carrying 1.9.118:** v9.7.337
**Last bundle on 1.9.117:** v9.7.336

---

## Engine 1.9.117 — first bundle: v9.7.336

**Previous engine:** 1.9.116

**Scoring/parser semantics changed:** **PARTIALLY — named, not glossed.** BGC counting, KCB/AB/AF triage priors and workbook scoring columns are otherwise unchanged, but **two folded items change runtime behaviour** and both are in the "freeze-safe" set of the items-31–55 handoff despite that label:

1. **`scoring.py` — RiPP-fragment span.** `_span_kb` now reads `abs(end - start)` whenever `end` is set, instead of requiring both `end` **and** `start` to be truthy. A BGC whose `start` is coordinate **0** is falsy in Python, so it previously fell through to whole-contig length; a RiPP at position 0 on an `Edge`/`Full-contig` locus could therefore take the fragment floor on the wrong span. This is a correctness fix, and it **can move `lead_tier_auto`** for exactly that case. Narrow, but not nothing.
2. **`rggmci.py` — ranked-pair retention.** `ranked_pairs` now keeps every `HIGH_RG_GMCI_RESCUE` pair past `RGGMCI_MAX_RANKED_PAIRS`, so a genuine split-pathway rescue is no longer dropped by display truncation. Additive rows; can surface an RG-GMCI rescue banner in a Mode-B card that was previously truncated away.

Everything else in the bump is fail-closed gate behaviour and reader-side rendering: the **CS-01** claim-safety inversion (the identity check returned clean for any compound absent from the supplied board — in two independent implementations), the **per-gene MIBiG convergence** section reaching the Mode-B card with a `convergence_layer_present()` guard so a package lacking the layer never has a novelty prior asserted for it, **PROV-01** (`engine_version` on every `B1_BGC_Master` row), and **SEAL-01** (`check_release_manifest` verifies TIER_MANIFEST membership, not just its stamp).

**Comparability.** Packages sealed on 1.9.116 and 1.9.117 are comparable for BGC counts, KCB/AB/AF scores and product classes. The two exceptions above are the only paths by which a `lead_tier_auto` or an RG-GMCI row can differ, and both are narrow and directional (a wrong-span RiPP floor lifting; a truncated HIGH rescue reappearing). This entry deliberately avoids the "existing scoring unchanged / no re-run needed" phrasing that proved wrong for v9.7.332 and .333.

**NOT in this cut, and it matters for anyone about to run a large cohort:** **CAT-01** — `parsers.py::_feature_products` ingests the antiSMASH `/category` qualifier as if it were another product class. Reproduced first-hand on the real `micromonospora_humida_JAFEUC01` fixture by removing that one key and re-running the same input: **BGC001** `Products` lost the injected `PKS`/`other`, `Arch_Capacity` moved from *"complex multi-class hybrid (arylpolyene/pks/…)"* to **"aromatic type II PKS (aromatic polyketide)"**, and `Class_Conf` rose **MODERATE → HIGH** — i.e. the injected class was making a clean T2PKS look unresolvable. **BGC002** moved the other way, `Arch_Capacity` *"complex multi-class hybrid (nrps/pks/t1pks)"* → **"unresolved"** and `Class_Conf` **MODERATE → LOW**, because `/category` is currently the only generic-class signal `classify_architecture` receives. `AB_auto`/`AF_auto`/`Novelty_auto` were byte-identical on both, and neither crossed a lead-tier boundary on this two-BGC fixture; the handoff's separate measurement of **8 of 140 BGCs crossing a tier boundary** across AS-XXX/AS-XXX/AS-XXX is not reproducible here for want of those inputs. The naive deletion also breaks `test_class_architecture.py::test_end_to_end_micromonospora_humida_hybrids` (expects ≥2 hybrids, gets 1) — confirmed. **So CAT-01 is a design change, not a one-liner:** `/category` must become a separate `antismash_category` field fed explicitly to the classifier and kept out of `score_keywords`/`WEAK_OVERCALL_CLASSES`/`_REAL_CLASSES`/`cctt_trigger_corroborated`. **Because it moves `Arch_Capacity`, `Class_Conf` and lead tiers, folding it after a large cohort run means re-running that cohort.** Decide it before, not after.

**First bundle carrying 1.9.117:** v9.7.336
**Last bundle on 1.9.116:** v9.7.335

---

## Engine 1.9.116 — first bundle: v9.7.335

**Previous engine:** 1.9.115

**Scoring/parser semantics changed:** **PARTIALLY — stated plainly, not as "unchanged".** BGC counting, KCB/AB/AF triage-score priors, standing rules, and workbook scoring columns are untouched, and AS-XXX re-run on the patched tree showed **0 field diffs** in `*_4_triage_board.csv` across `Arch_Capacity` / `Class_Conf` / `Lead_tier_auto` / `AB_auto` / `AF_auto`. **Two changes can nevertheless move a capacity line on other strains.** (1) `class_architecture.TAILORS` matched by bare substring, so `halogenat` matched **de**halogenase and `glycos` matched any glycoside hydrolase; six real BGCs (AS-XXX BGC011/017/040/043, AS-XXX BGC002/009) currently assert "+ halogenase" in the user-facing Mode-B §2 line on an annotation naming the opposite enzyme. The fix is `(?<!de)halogenase` plus a real transferase requirement, and the consumer changed too — patterns were `re.escape`'d, so a regex would have been searched literally and silently disabled halogenase detection altogether, strictly worse than the bug. Those six capacity strings will change. (2) `source_scans.module_count` tested `feature_type == "module"` while `parsers.py` passes GenBank's raw `f.type`, i.e. `aSModule` — so every BGC in every manifest reported **0 modules** (AS-XXX has 55). `module_count` becomes non-zero everywhere, and `manifest.json` is the authoritative handoff the judgment kernel reads. **AS-XXX and AS-XXX boards were NOT re-run and diffed on this tree** — do that before treating their capacity strings as stable. This entry deliberately avoids the "existing scoring unchanged / cross-strain comparability preserved / no re-run needed" phrasing, which proved **wrong** for 1.9.114 (see that entry) and was repeated uncorrected in the v9.7.333 cut report.

**The rest of the bump is fail-closed gate behaviour, not new metrics.** `validate.py`: an unparseable `manifest.json` no longer falls through to `PASS` (it was swallowed, so `mode` stayed `None`, the gold/depth block never ran, the reporting-v2 gate degraded to `LEGACY_NOT_APPLICABLE`, and a corrupt package scored strictly better than a good one — `manifest.json` is excluded from the checksum set, so nothing else caught it); and `gold_completeness` now matches authored card filenames against `locked_ids` instead of testing for the substring `mode_b` in a filename, which one **zero-byte** file satisfied. `mode_b_receipt`: a crashed structure gate is no longer recorded as a clean card — `ingest_one_card` emits an `ERROR / GATE_UNAVAILABLE` sentinel, and `ingest_receipt` + `auto_detect_ingest` (the batch front door and the session-start recovery sweep, which the incoming patch missed) route the card to the existing structure-invalid skip instead of `n_errors = 0  # gate fail-open`. `modeb_structure_gate`: the §4 evidence gate is capable of failing for the first time — the bare-verdict branch matched `CONFIRM/REFINE/OVERTURN` inside the emitter's own unauthored skeleton text, so `EVIDENCE_GAP` was dead on every card from the supported workflow, and the coverage check's `%id` clause was satisfied by the digits inside the locus tag itself (verified across all 2438 real locus tags in three sealed packages: zero rows where the clause was not already satisfied by the tag alone). `blastp_online`: `product_novelty` was hard-wired to **NOVEL** because `function_and_novelty` reads `kcb_top`/`kcb_coverage_genes` off `args` and neither argparse destination exists on the `blastp-online` parser — it now returns `UNDETERMINED`, saying the test was absent rather than negative; `blastp-round` no longer plans zero proteins on a valid package (it read `translation`/`seq`, which `gene_context.jsonl` does not carry, and exited 0); orphan genes are no longer dropped from their own denominator. `blastp_evidence_store`: tiering no longer reads our own panel defline, whose `reason=` field is built from the query's antiSMASH annotation using verbatim `CLASS_DEFINING_TERMS` members — antiSMASH's own call was being laundered back as BLASTp support. `render_brief`: rank truncation is no longer labelled saccharide filtering (AS-XXX printed 36 pure-saccharide against a true count of 0), and `_release_status` reads `manifest["release"]` instead of hardcoding `PRIVATE` for `AS-` strains, which had the same package labelling itself PUBLIC in `manifest_short.json` and PRIVATE in the brief PDF. `master_workbook` + `workbook_dedup`: the Sapote write-back helpers no longer clear the strain from 18 sheets and restore only their own. `bgc_blastp_panel` / `blastp_followup`: loop-exit fixes (`return`→`break`, `break`→`continue` on the residue budget).

**Verification.** Full `pytest` on the assembled tree, Linux / CPython 3.12, add-ons installed. New known-bad-input regression tests: `tests/test_v9_7_335_tier1_gates_known_bad_input.py` (13) and `tests/test_v9_7_335_ext_receipt_gate_failopen.py` (4), each asserting the gate now **refuses** the artifact that used to pass, each paired with a good-input control; verified in both directions against the unpatched .334 tree. MODULE_MANIFEST net +0 (198). `repo_health --strict` PASS, silent_swallow 110→109.

**First bundle carrying 1.9.116:** v9.7.335
**Last bundle on 1.9.115:** v9.7.334

---

## Engine 1.9.115 — first bundle: v9.7.333

**Previous engine:** 1.9.114

**Scoring/parser semantics changed:** **No — BGC counting, KCB/AB/AF triage priors, standing rules, and workbook scoring columns are identical to 1.9.114; cross-strain comparability is preserved and no re-scoring is required.** The bump is for **new read-only modules/subcommands + one additive reporting table + one fail-safe correctness fix**, none of which touch `run_one_strain` scoring or a gate: (1) `discover.py` + `discover` subcommand — workspace orientation (packages, completeness grid, ranked next actions); (2) `genus_appendix.py` + `genus-appendix` subcommand — antifungal/antibacterial **candidate** appendices grouped by genus, report-only keyword flags (comparator/class markers, explicitly NOT activity claims); (3) a first-class **PFAM/TIGRFAM HMM table** in `antismash_tables.py` (`build_hmm_table` → `3_antismash_hmm.csv` + `antiSMASH_HMM` sheet), sourced from `extract_gbk_pfam_hits`/`extract_tigrfam_hits` — previously these HMM hits were not surfaced as a standalone table; (4) **CORE-P02 fail-open fix** in `recovery_status.py` — `infer_package_status` now asserts `MAMEY_COMPLETE` only on an affirmative completion signal (or an empty packaging-time status); a non-empty unrecognized status (e.g. `GATE_FAILED`, `INCOMPLETE`) fails **safe** to `PARTIAL_FAILED` instead of rendering a package "complete" it never earned. Also additive/non-behavioral: the BLASTp support-card + deeper-dive + Mode-B-integration **templates** (`templates/`, `tools/audit_modeb_support_card.py`), the **tool-citation manifest** (`mamey/data/tool_citations.json`), removal of the "judgment deferred" motto from Mode-B card text (the substantive claim-safety ceiling is retained), and the silent_swallow sweep (110). MODULE_MANIFEST +2 (`discover.py`, `genus_appendix.py`). Tests: `test_discover`, `test_genus_appendix`, `test_antismash_hmm_table`, `test_recovery_status_schema` (+fail-safe), `test_doc_templates`, `test_audit_modeb_support_card` + full suite. Real-strain confirmation: AS-XXX → 419 HMM rows, 2 AF + 1 AB candidate rows, `discover` enumerated the package.

**First bundle carrying 1.9.115:** v9.7.333
**Last bundle on 1.9.114:** v9.7.332

---

## Engine 1.9.114 — first bundle: v9.7.332

**Previous engine:** 1.9.113

**Scoring/parser semantics changed:** **PARTIALLY — corrected 2026-07-27.** BGC counting, KCB/AB/AF triage-score priors, standing rules, and workbook scoring columns are unchanged. **However, an earlier version of this entry wrongly claimed "cross-strain comparability preserved / no re-run needed."** P_MPG also changed `parsers.py::extract_domain_features` to exclude region GBKs when whole-record GBKs are present (`exclude_regions=True`, de-duplicating domains / fixing region-local coordinate mis-assignment). That function feeds `architecture_first` (the architecture classifier), so **`Arch_Capacity` — and the `Class_Conf` + `Lead_tier_auto` that cascade from it — can shift for BGCs near a class boundary.** Confirmed on AS-XXX (BGC006 demoted High→Medium; BGC012/BGC015 reclassified; AS-XXX/AS-XXX unchanged). The new classification is plausibly *more correct*, but it is **not comparable** with pre-1.9.114 packages: **a cohort re-run on ≥1.9.114 is recommended before any cross-strain triage/lead-tier comparison.** See `Red/AS-XXX_scoring_regression_investigation.md`. The bump is otherwise for **new deterministic parser outputs**: the **P_MPG (MIBiG-per-gene) + P_LWC (length-weighted clusterblast)** patch (Codex). The parser now (1) retains the best hit for **every `(query gene, MIBiG accession)` pair** instead of one best reference per query gene — preserving the repeated-same-reference convergence signal; (2) emits a new `MIBiG_Convergence` report (grouped by BGC × MIBiG accession) and a `MIBiG_Profile` as package JSON + CSV + workbook sheet, with preliminary deterministic evidence tiers **H1_HIGH_DENSITY … H5_SINGLE_OR_WEAK + CAUTION_CLASS_MISMATCH**; (3) adds `mamey/antismash_tables.py` (structured module/RiPP/motif tables) and an `include_structured` path in `parse_antismash_evidence`; (4) adds a length-weighted clusterblast descriptor (`length_weighted.py`). **No AB/AF score bonus is added** — the tiers are reporting strata only; any future scoring use must keep mis-anchor/primary-metabolism guards at hard precedence, no positive bonus on class discordance, and no double-counting with the KCB channel. Packages gain new evidence files; every existing file is byte-identical in schema. MODULE_MANIFEST 193→196 (+3: `antismash_tables.py`, `length_weighted.py`, `mibig_per_gene.py`). Trial: 38 AS ZIPs, 1,507 BGCs, 45,767 retained rows, 0 parse errors. Tests: `tests/test_patch_p_mpg_lwc.py` + full suite.

**First bundle carrying 1.9.114:** v9.7.332
**Last bundle on 1.9.113:** v9.7.331

---

## Engine 1.9.113 — first bundle: v9.7.330

**Previous engine:** 1.9.112

**Scoring/parser semantics changed:** **No — BGC counting, KCB scoring, triage priors, and workbook columns are unchanged; cross-strain comparability with 1.9.112 is preserved.** The bump is for **new modules + post-seal subcommands** (the "new Mode-B workflow"), all of which consume an already-sealed package and never touch `run_one_strain` or a gate: (1) `class_believability.py` + `class-believability` (committed-step believability engine, LOCAL + POOLED passes); (2) `strain_modeb.py` + `emit-strain-modeb` (strain-level Mode B S1–S8 + strain-structure gate); (3) `cohort_context.py` (cohort-aware S5 from the BiG-SCAPE DB); (4) `modeb_cards.py` + `series_common.py` + `emit-modeb-cards` (Blue's compact per-BGC data cards). Also additive: `npatlas_resolver.class_frequency()` (NP Atlas class-frequency grounding, no genus/bioactivity claims) and Mode-B contract sub-questions on §5/§9/§13 (no section-count change). MODULE_MANIFEST 187→192.

**First bundle carrying 1.9.113:** v9.7.330
**Last bundle on 1.9.112:** v9.7.329

**Tests at bump:** full suite 3017 passed / 0 failed on the assembled cut source (+27 new regression tests across the six items).

---

## Engine 1.9.112 — first bundle: v9.7.329

**Previous engine:** 1.9.111

**Scoring/parser semantics changed:** **No — BGC counting, KCB scoring, triage priors, and workbook columns are unchanged, so cross-strain comparability with 1.9.111 is preserved.** The bump is for two *behavioral* (non-scoring) changes plus resource-lifecycle fixes: (1) **`bgc_decomp.run_bgc_decomp` return contract (SCHEMA-P01)** — the result dict gains a `gene_table_status` field (`OK`/`MISSING`/`NOT_FOUND`/`EMPTY`) and `status` may now be `"INCOMPLETE"` when no per-CDS gene table was available; previously a missing/absent gene table silently yielded `status="PASS"` with every BGC `ONE_MODEL_CONSISTENT` (a false "0 TWO_MODEL_STRONG" negative). Each such row's `null_reason` now names the true cause, and `cli.py` raises a `[WARN]`. The happy-path `PASS` contract (a real gene table) is unchanged. (2) **`workbook_schema_check.validate` (SCHEMA-P03/P04)** — no longer crashes with `TypeError` on read-only workbooks that omit the stored `<dimension>` (forces `calculate_dimension`), and closes the read-only handle via `try/finally`. (3) **comparator resource hygiene (COMP-P07/P09)** — extracted comparator ZIPs are cleaned from the package tree; `gcf_context` closes its sqlite connection on the error path.

**First bundle carrying 1.9.112:** v9.7.329
**Last bundle on 1.9.111:** v9.7.328

**Tests at bump:** full suite 2990 passed / 0 failed on the assembled cut source pre-version-bump (+8 new Red regression tests); the version-restatement gates re-green after the bump/sync/manifest sequence.

---

## Engine 1.9.111 — first bundle: v9.7.196
Parser + prediction recovery. `parsers.extract_domain_features` now includes `aSModule` in the wanted
feature set (was `"module"` — antiSMASH's type is `aSModule`, so modules were dropped) and surfaces
A-domain `substrate consensus` on `DomainFeature`. New `nrps_predictions` module recovers antiSMASH
NRPS/PKS predictions from the run JSON (per-A-domain Stachelhaus substrate, PKS-AT extender units,
assembled polymer/SMILES, over-merge flag) independent of `--json-evidence` mode. blastp-online:
crosswalk-grounded `--bgc` scoping + transient-UNKNOWN-as-pending polling robustness. Additive; no
change to BGC counting or assembly-tier semantics.


*Authoritative record of engine version changes. Every engine bump requires an entry here.*  
*If `mamey.__engine__` changes between release baselines without an entry here, `sync_version.py --check` will warn.*

---

## Engine 1.9.108 — first bundle: v9.7.191

**Previous engine:** 1.9.107

**Scoring/parser semantics changed:** **No — additive command/module changes; BGC counts, KCB scoring, and workbook columns unchanged.** (1) **BLASTp async submit** — new `run_batches_online` + `_submit_batch` in `blastp_online.py` submit all batches then poll RIDs together (NCBI URL API is asynchronous); ~Nx faster than the prior serial loop. `run_batch_online` unchanged; fail-closed/offline-safe/scoping guards intact; output identical to serial. (2) **`gemini.py` → `compare.py` module rename** — the two-strain comparison module is renamed (`compare_command` canonical, `gemini_compare_command` back-compat alias); `gemini.py` becomes a re-export shim forwarding the full namespace (private helpers included) so every existing importer keeps working. New tracked module → MODULE_MANIFEST 171→172. (3) **guide-gate AS-XXX hardening** — seal-time `write_gene_count_crosscheck` walks region GBKs from the input zip (independent code path from the CSV) → `gene_count_crosscheck.json`; `guide_quality_gate(package=...)` errors only on interior-gene omission, warns on edge/FC, degrades when the sidecar is absent. Engine bumped for the new module + seal-time writer, though scoring semantics are unchanged.

**First bundle carrying 1.9.108:** v9.7.191
**Last bundle on 1.9.107:** v9.7.190

**Tests at bump:** full suite 2596 passed / 0 failed pre-bump; new partitions for async submit, guide-gate crosscheck (design note's 6-case plan), and the compare rename (incl. shim private-name forwarding). Guide-gate verified end-to-end on real AS-XXX data (Interior omission → ERROR; Edge/FC → warn; correct count → clean).

---

## Engine 1.9.108 — first bundle: v9.7.191

**Previous engine:** 1.9.107

**Scoring/parser semantics changed:** **No — additive only; BGC counts, KCB scoring, and workbook columns unchanged.** Engine bumped because a new seal-time artifact is emitted and the online-BLASTp submission path changed shape. (1) **Guide-gate AS-XXX hardening** — seal now writes `gene_count_crosscheck.json` (an independent per-BGC CDS recount from the region GBKs, via a different code path than the gene-by-gene CSV); `guide_quality_gate` cross-checks against it, erroring only on interior-gene omission and degrading when the sidecar is absent. New seal output; no score change. (2) **BLASTp async submit** — `blastp-online`/`blastp-round` now submit all batches then poll together (`run_batches_online`), ~Nx faster; `run_batch_online` preserved, fail-closed semantics identical. (3) **`gemini.py` → `compare.py`** module rename (shim preserves all importers). Adds `mamey/compare.py`; `mamey/gemini.py` becomes a re-export shim.

**First bundle carrying 1.9.108:** v9.7.191
**Last bundle on 1.9.107:** v9.7.190

**Tests at bump:** full suite 2596 passed / 0 failed; async-property + guide-gate-crosscheck (6-case design-note plan) partitions added.

---

## Engine 1.9.107 — first bundle: v9.7.186

**Previous engine:** 1.9.106

**Scoring/parser semantics changed:** **No — additive deliverables only; BGC counts, KCB scoring, and existing workbook columns unchanged.** Two new, purely-additive capabilities: (1) **NP Atlas compound-reference resolver** — a new `B6_Compound_Reference` workbook sheet enriches each BGC's KCB-named compound with molecule-level chemistry (npclassifier class, formula, exact mass, [M+H]/[M+Na], InChIKey, primary DOI/PMID). It writes ONLY to B6 (B1 verified byte-identical); INVENTORY_ONLY; makes no genus-restriction or product-identity claim. NP Atlas references ship as an add-on (discovered via `SM_NPATLAS_DIR` / side-by-side layouts / bundle-local fallback; graceful empty if absent). (2) **`mamey guide`** — a layered per-gene BGC Guide deliverable (sibling of `mode-b`), rendering banked gene/domain data + the BLASTp evidence store's existing tiering; each per-gene claim is capped at its BLASTp `evidence_tier`. Adds `mamey/npatlas_resolver.py` and `mamey/bgc_guide.py`. Engine bumped because the workbook schema gains a sheet (B6), even though scoring semantics are unchanged.

**First bundle carrying 1.9.107:** v9.7.186
**Last bundle on 1.9.106:** v9.7.185

**Tests at bump:** full suite green pre-bump; NP Atlas (B1-immutability, INVENTORY_ONLY, add-on degrade) and guide (skeleton determinism, dropped-gene gate, readout variants, docx degrade) partitions added.

---

## Engine 1.9.106 — first bundle: v9.7.185

**Previous engine:** 1.9.105

**Scoring/parser semantics changed:** **Yes (schema + intake contents).** Round-2 reference-strain-audit fixes: (1) **P3** — `A2_Strain_Registry` gains a `scope` column (IN_SCOPE / OUT_OF_SCOPE / REVIEW from organism genus via cohort_resolver), so an off-target non-actinomycete (e.g. a Firmicute) is stamped rather than silently pooled into the cohort comparison. **A2 schema changes (new column).** (2) **P8** — antiSMASH version intake upgrades a bare `8.dev` label to the full `8.dev-<hash>(changed)` from the GBK structured comment; provenance field contents change. (3) **P13** — `gene_data.json` gains `other_domain_breakdown` (top-25) and `misfiled_core_tokens` (a self-check that stays empty while P11 holds). (4) **P7** — `blastp-online --bgc/--region` now scopes extraction to the named region + refuses oversized unscoped NCBI submissions (behavior change on an advertised command). (5) **P12** — the per-BGC catalytic heatmap drops three structurally-always-zero rows (transporters/regulators/oxidoreductases are genes, not aSDomains, and have dedicated figures); figure composition changes. (6) **P10/P6** — marker-file wording + OPEN_ME_FIRST next-steps (docs). BGC counts and KCB scoring unaffected.

**First bundle carrying 1.9.106:** v9.7.185
**Last bundle on 1.9.105:** v9.7.184

**Tests at bump:** full suite 2566 passed / 0 failed pre-bump; round-2 regression tests added (P3 scope classification, P7 guard, P13 self-check).

---

## Engine 1.9.105 — first bundle: v9.7.184

**Previous engine:** 1.9.104

**Scoring/parser semantics changed:** **Yes (classifier + figure data + input handling).** Three reference-strain-audit fixes change deterministic engine outputs: (1) **P11** — `DOMAIN_CLASS_PATTERNS` for the PKS reductive-loop domains (PKS_KS/AT/DH/ER/KR/ACP) now match the literal underscore-joined token; previously `\bDH\b` never matched inside `PKS_DH` (underscore is a word char), so real dehydratase/enoylreductase hits were misfiled as `Other_domain` and the F01 `PKS_DH` heatmap row read a false zero. **Any strain's domain-class heatmap (F01) and the F03 macrolide-type proxy may change**; a reducing modular PKS previously mislabelled non-reducing is corrected. (2) **P4** — the assembly-tier figure now reads the `Boundary` status column before `Assembly_Locator` (a locus string), so `fig_assembly_tier` no longer dumps every BGC into `Other`. Figure data CSVs change. (3) **P1** — `read_genbank_records` now accepts a single `.gbk/.gb/.gbff` file directly (previously `BadZipFile` on the advertised `blastp-online --package <gbk>` path). New input path; no change to existing ZIP/dir handling. Cohort figure re-run recommended for any strain previously processed under engine ≤1.9.104 if F01/F03 domain-class figures are used downstream. KCB scoring and BGC counts are unaffected.

**First bundle carrying 1.9.105:** v9.7.184
**Last bundle on 1.9.104:** v9.7.183

**Tests at bump:** full suite 2566 passed / 0 failed; P4/P11/P1 regression tests added; registry parity (`test_b2_registry_parity`) and marker-catalog staleness (`test_marker_catalog`, hash cf76161ce160) green after the 4-file coordinated P11 change.

---

## Engine 1.9.104 — first bundle: v9.7.158

**Previous engine:** 1.9.103
**Bump reason:** KCB source-precedence and rank-vs-score fix in `mamey/antismash_evidence.py`
**Scoring/parser semantics changed:** **Yes.** Two bugs fixed: (1) `apply_evidence_to_bgcs` now restricts KCB score aggregation to `knownclusterblast` records when present, instead of pooling `knownclusterblast/clusterblast/subclusterblast` under the same region key and taking max across all three; (2) `_parse_txt_evidence` now takes the file's rank-1 hit (first block) as `best`, instead of `max(block_records, key=score)` which could select a lower-ranked hit with a higher raw score. **Every strain's triage-board KCB_score and kcb_top fields may change under this engine.** Cohort re-run required for any strain previously processed under engine ≤1.9.103 if KCB-derived scoring (novelty, lead-tier, DAPR rank) is used in downstream decisions.
**Tests:** Existing suite (2,432 passed / 132 skipped / 0 failures). Verified on AS-XXX BGC058 (37,992 corrected from 73,038), BGC002 (2,949 corrected from 10,981), BGC001 (2,264 spot-checked). No new test file in this cut (engine fix is upstream of all existing KCB-consuming tests).
**First bundle carrying 1.9.104:** v9.7.158
**Last bundle on 1.9.103:** v9.7.157

---

## Engine 1.9.103 — first bundle: v9.7.157

**Previous engine:** 1.9.102
**Bump reason:** Mandatory-deliverable gate in `run_command` (touches `mamey/cli.py`)
**Scoring/parser semantics changed:** **No.** Post-seal, non-blocking auto-emit of the compiled report; no scores, counts, or figure content change. No cohort re-run required.
**Tests:** `test_mandatory_deliverable_gate_v9_7_157` (2). End-to-end verified on AS-XXX smoke.
**First bundle carrying 1.9.103:** v9.7.157
**Last bundle on 1.9.102:** v9.7.156

---

## Engine 1.9.102 — first bundle: v9.7.156

**Previous engine:** 1.9.101
**Bump reason:** Two compile-path root-cause bugfixes (touch `mamey/render_all_figures.py` and `mamey/compile_report.py`)
**Scoring/parser semantics changed:** **No.** AB/AF scoring, KCB, boundary, and corrected-count are untouched. Both fixes are in the reporting/figure-summary path only: (1) `_run_locus_maps` now returns an int figure count instead of leaking a list into the summary JSON; (2) `_read_manifests` falls back to `manifest.json["assembly"]` for n50/contigs on vintage packages. **No BGC counts or scores change; no cohort re-run required.**

**Also in v9.7.156 (non-engine):** AS-series privacy-guard retirement (tooling/docs; leak audit demoted FAIL→WARN behind `AS_GUARD_RETIRED`). Redaction machinery retained but inactive.

**Tests:** `test_render_all_locus_maps_count_v9_7_156` (3), `test_compile_report_n50_contigs_fallback_v9_7_156` (3), AS-guard suite 24 pass unchanged.
**First bundle carrying 1.9.102:** v9.7.156
**Last bundle on 1.9.101:** v9.7.155

---

## Engine 1.9.101 — first bundle: v9.7.152

**Previous engine:** 1.9.100  
**Bump reason:** Intake parsing change (macOS AppleDouble/`__MACOSX` cruft filter) + ingest/validate correctness fixes  
**Scoring/parser semantics changed:** **No.** AB/AF scoring, KCB matching, boundary computation, and the corrected-BGC-count formula are unchanged. The parser change only *removes* macOS resource-fork shadow files (`._*`, `__MACOSX/`, `.DS_Store`) from `namelist()` consumers before counting/parsing. **BGC counts are unchanged** (verified on AS-XXX: 64 raw / 24.0 corrected before and after), so **cross-strain comparability is preserved and no cohort re-run is required.**

**What entered the tree at v9.7.152 that prompted the bump:**
- `mamey/parsers.py` — `is_macos_cruft()` helper; applied at every `namelist()` sweep (JSON version probe, FASTA, GBK records, CDS/contig pass). Eliminates AppleDouble double-counting and the spurious "N/2N GBK file(s) yielded no records" warning on macOS-zipped antiSMASH inputs.
- `mamey/package_inspector.py` — cruft filter applied before all `inspect`/`classify_antismash_zip` counts (region GBK, KCB TXT, batch estimate).
- `mamey/mode_b_receipt.py` — `auto_detect_ingest` near-miss filename warning (AS-XXX Bug 1); new `lint_card_in_package()` context-aware lint wrapper (AS-XXX Bug 2).
- `mamey/validate.py` — `verify_checksums()` exempts the per-strain `*_judgment_register.json` (rewritten post-seal by `ingest-receipts`; Part-2 Finding 1).
- `mamey/modeb_structure_gate.py` — `_HEADING_RE` tightened so bare numbered lists are not mis-detected as section headings (W9 Bug 2.1).
- `mamey/locus_map.py` — `render_for_compile_report(..., fmt=...)`; `fmt="png"` for PDF pipelines without an SVG rasterizer (AS-XXX Bug 3).
- `mamey/cli.py` — `--chatgpt-safe`→`--capped-session` rename (deprecated alias retained); CLI/UX only, no engine semantics.

**Tests run at bump:** partitioned pytest (P0 bootstrap/version, P1 release-hygiene, P2 CLI, P3 workbook, P4 scoring, P5 figures) + consolidated patched-area sweep; all green. New regression tests added for each fix.  
**First bundle carrying 1.9.101:** v9.7.152  
**Last bundle on 1.9.100:** v9.7.151c

---

**Previous engine:** 1.9.99  
**Bump reason:** Evidence-handling and runtime-interface expansion  
**Scoring/parser semantics changed:** No intentional AB/AF scoring overhaul; evidence ingestion and output interfaces expanded  

**What entered the tree at v9.7.142 that prompted the bump:**
- `mamey/bgc_blastp_panel.py` — BLASTP panel export for large modular PKS/NRPS proteins
- `mamey/blastp_followup.py` — BLASTP follow-up result parsing and ingestion
- `mamey/blastp_evidence_store.py` — durable per-BGC BLASTP evidence store
- `mamey/citation_compact.py` — citation compact output mode
- `mamey/validators/modeb_full20.py` — first Mode B §1–§20 validator (144a schema)
- Claim-safety gate infrastructure
- LLM handoff utilities
- Release QA tooling
- Figure, comparator, and workbook infrastructure expansions

**Tests run at bump:** focused pytest suite (82 tests passed at v9.7.142 baseline)  
**First bundle carrying 1.9.100:** v9.7.142  
**Last bundle on 1.9.99:** v9.7.141 (or earlier — exact boundary not confirmed in lineage audit)

---

## Engine 1.9.99 — baseline (pre-v9.7.142)

**What this engine covered:** core BGC extraction, scoring (AB/AF), KCB/MIBiG matching,  
architecture grading (A–E), RGGMCI split-cluster reconstruction, FLBR/LMPKS rescue,  
UMED/CGAD/EFLS/CCTT triggers, evidence conservation, four-tier release infrastructure.

**Lineage note:** Engine 1.9.99 was the version at the v9.7.128 baseline (last Claude-cut  
before ChatGPT independent patch series v9.7.129–v9.7.141). The exact version at which  
1.9.99 was introduced is not confirmed; this record covers the confirmed delta.

---

## Release gate

`sync_version.py` checks for an ENGINE_LINEAGE entry when `mamey.__engine__` differs  
from the previous release baseline. If no entry exists, `--check` exits non-zero with:

```
ERROR: engine changed X → Y but docs/ENGINE_LINEAGE.md has no entry for Y.
Add an entry before cutting a release.
```

Future engine bumps must include:
- Old engine version
- New engine version  
- First bundle carrying new engine
- Reason for bump
- Whether scoring/parser semantics changed
- Tests run at bump

---

*Last updated: v9.7.145 · 2026-06-29 · Lineage audit finding from v9.7.145 testing chat*
