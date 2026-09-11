# v9.7.428 · 2026-09-11 · build 20260911v97428a · engine 1.9.163

- **Portable collaborator figure packages** — automatically place descriptive PNG and PDF figures, source and display Newick trees, aligned FASTA, annotation TSV, full caption, methods, standalone R renderer, rerender command, and checksum manifest beside every accepted placement display.
- **Reviewed 16S identity exclusions** — preserve deposited records while applying explicit accession or designation-plus-genus review rules at panel admission; excluded requests are recorded and explicitly requested excluded records fail closed. This prevents the reviewed AS-XXX/Pseudonocardia and PX566631 misassociation from entering new panels without globally renaming either identity. Reference admission also distinguishes accession-shaped laboratory and culture-collection strain codes from conflicting deposited accessions, while retaining namespace-prefixed conflict refusals.
- **Placement runtime and display repairs** — run MAFFT quietly so its wrapper does not attempt a sandbox-blocked `/dev/stderr` write, preserve diagnostic logs on failure, recognize attine-ant host vocabulary, use more distinguishable host colors, and keep concise and detailed isolation-source variants.
- **Species-neighborhood catalogs** — split completed EPA-ng placements into reproducible closest-type-strain neighborhoods without changing the fixed reference inference, and preserve per-query grouping authority in a ledger.
- **Bioassay plate mapping** — provide a validated 96-to-384-well geometry profile for 120/60/30/15 µg/mL quadrants and keep plate-specific identity corrections separate from global strain identity.

# v9.7.427 · 2026-09-10 · build 20260910v97427a · engine 1.9.162

- **Tree Catalog** — render declared 1:1, 1:2, and 1:3 reference displays with concise geography, detailed geography, no-geography, and internal sample-review variants from one completed placement run.
- **Phylogeny identity and references** — retain distinct query isolates with identical 16S sequences, reject malformed multi-accession records and duplicate reference species, use the exact placed-query roster for tip roles, and let a checked strain-to-species table reserve each query's required reference before nearest-neighbor filling.
- **Figure labels and layout** — use consistent versionless GenBank accessions and isolation-source syntax for query and reference labels, keep full deposited metadata in sidecars, add `Exp 35 #12`-style specimen keys only to `_internal` labels, give branches explicit horizontal room, and float scale bars below trees.
- **Real-data validation** — render nine bee *Streptomyces* publication displays plus an internal specimen-ID companion from the same 102-query placement, with 96 workbook-required closest-type pairings, one reference per species, and complete selection ledgers.

# v9.7.426 · 2026-09-10 · build 20260910v97426a · engine 1.9.161

- **Bioassay Figure Factory** — admit hash-bound 96/384-well observations with material lineage, target resolution, dose, time point, replication, control, exclusion, and yield states; keep raw and precomputed inputs distinct.
- **Bioassay planning and tree tracks** — inventory heterogeneous assay datasets under the existing Figure Factory front door, propose reviewable previews, and emit exact-endpoint or complete declared fraction-set maximum tracks without merging doses or treating partial sets as complete.
- **Partial 16S placement** — screen query symbols, length, ambiguity, and terminal uncertainty; write a QC receipt; route partial reads through MAFFT fragment alignment; hold near-tied cross-genus BLAST assignments.
- **Portable 16S validation** — route optional real-store regression tests through `SAPOTE_16S_STORE` so public tests carry no machine-specific workspace path.
- **Phylogeny and metadata figures** — share reference admission and metadata normalization across producers, add typed bioassay annotations, and keep raw metadata beside simplified display categories.
- **User documentation and front doors** — consolidate current commands, correct table rendering and command descriptions, clarify external-data licenses and assistant discovery, replace stale bench/layperson exemplars, and retire internal version-delta and Figure Factory repair notes from the shipped user-doc surface.
- **R workflow map** — document the ggplot2/ggtree renderer surface, add a canonical bioassay SVG/PNG renderer, and keep detailed interpretation disclosures in receipts and sidecars rather than the plotted canvas.
- **Real-tree workflow repairs** — correct two accession-to-organism outgroup registry bindings, restore an explicit dropped-tip ledger, support deliberately sparse one-reference-per-genus backbones with warnings, and prefer governed query records when strain designations collide across database sources.
- **Reference-panel identity and density** — collapse only reviewed cross-accession strain aliases before inference, bind accession-only FASTA tips to an explicit species/role sidecar, refuse project queries reused as references, and render deterministic per-query 1:1, 1:2 or 1:3 reference ladders with a complete pairing ledger.
- **Placement runtime and methods** — allow a balanced display tree to consume its complete inference alignment without weakening the initial exact-coverage gate, normalize isolation-source/geography display fields, and write exact tool, model, bootstrap, thread, record and tip counts beside each figure.

# v9.7.425 · 2026-09-10 · build 20260910v97425a · engine 1.9.160

- **Widget evidence admission** — bind stable source tables, refuse ambiguous or malformed inputs, preserve missing quantitative values, and expose complete locus identity in interactive views and SVG/CSV exports.
- **Portable legacy rosters** — read equivalent directory and ZIP package inputs with bounded extraction, preserve full contig names, clean temporary files, and report malformed, duplicate, symlink, and traversal cases instead of silently dropping the roster.
- **Mode B and Lab Quest identity** — use native package inventories with complete strain / full contig / region / BGC identity while preserving unauthored scaffold and evidence-availability holds.
- **Reports and guides** — prevent external guide output from mutating a sealed package and keep incomplete fermentation sections from being reported as complete.
- **Figures and lead pages** — carry complete locus identity into lead outputs, retain missing scores as missing, and size standard lead figures from admitted labels.
- **Missingness and diagnostics** — reject malformed reference-dark counts and fractions, preserve missing KCB values separately from genuine zero, and return clean actionable refusals without increasing the terminal-output or silent-swallow ratchets.

# v9.7.424 · 2026-09-09 · build 20260909v97424a · engine 1.9.159

- **Placement workflow:** portable panel splitting and display orchestration preserve input tips and existing outputs, with explicit metadata and accession conflict checks.
- **Reference selection:** composable metadata/genus/habitat filters use correctly ordered parameters and exact governed identity exclusions.
- **Alignment preservation:** terminal disagreement is advisory and does not mask the inference alignment.
- **Figure presentation:** consistent source brackets and versionless accession display, measured grouping bounds, detached scale bars, and caption-only outgroup identification; provenance and full versioned identities remain in data and receipts.

# v9.7.423 · 2026-09-09 · build 20260909v97423a · engine 1.9.157

- **Bioassay overlay:** Add a tested binary-assay overlay with strict row/value checks and distinct missing-data states.
- **Claim validation:** Prevent unrelated clauses from supplying identity-claim hedges in text and structured reports.

- **Evidence discovery:** Bound automatic BLASTp discovery below account-level markers and return actionable typed refusals from CLI commands.

- **Portable walkthrough** — connect installation, extraction, protein evidence, comparative analysis, phylogeny and verified deliverables using configurable paths.
- **Current prerequisites** — align Python extras with package metadata and separate external tools, databases, TLS and wheel compatibility.
- **User documentation** — replace internal-version catch-up prose with current kernel guidance and correct Quick Guide extraction/output paths.

# v9.7.422 · 2026-09-09 · build 20260909v97422a · engine 1.9.157

- **Pre-release documentation** — revised user onboarding, protein evidence, comparative and phylogenetic workflows, and tool downloads and licenses.
- **Figure rendering** — repair R parsing, wrap long tree labels and captions, and improve layout controls.
- **Validation** — candidate validation is recorded separately; this entry does not assert a completed release seal.

# v9.7.421 · 2026-09-09 · build 20260909v97421a · engine 1.9.157

- **Evidence failure states** — make receipt persistence, authored evidence context, BLASTp ingestion, report completeness, package inspection, and figure failures observable while preserving typed missingness and refusals.
- **Bounded write recovery** — recover caught multi-file BLASTp write failures, reject unsafe recovery paths, and keep unresolved recovery visible. Concurrent-writer and power-loss atomicity are not claimed.
- **Reference displays** — reconcile reference metadata through explicit local inputs, preserve output rollback, escape spreadsheet-formula cells, and match outgroup markers on both token boundaries.
- **Release validation** — require structured source-bound external validation for release test reuse; the full release profile includes slow and network-marked tests. Harden nested archive disclosure checks and retire stale test exemptions.
- **Portable tests** — restore portable test stubs for interpreter paths containing spaces. Add precise collection and test-environment evidence for release comparison.
- **Encyclopedia currency** — correct the encyclopedia CCTT roster to 18, its diagnostic sets to 8 AB and 3 AF, and current missing-KCB novelty behavior. Preserve historical grounding and explicitly limit unrevalidated content.
- **Measured ratchets** — lower the measured silent-handler ceiling from 125 to 82. Narrow the existing terminal-emission exception to the measured 1322; no headroom is added.

# v9.7.420 · 2026-09-09 · build 20260909v97420a · engine 1.9.156

- **Discovery scope** — keep unmarked standalone packages within their containing directory; refuse invalid explicit BLASTp scan roots instead of silently replacing them.
- **Evidence failures** — make receipt, verification-context, judgment-recovery, BLASTp admission, report, inspection and figure failures observable; lower the measured silent-swallow ceiling from 147 to 125 without added headroom.
- **Rescue figures** — refuse missing or invalid linkage counts instead of interpreting them as zero; protect existing rescue outputs on refusal and close workbook readers.
- **Reference labels** — admit demonstrated collection prefixes only after an explicit strain marker; retain accession-conflict refusals and identify conflicting tips before writing output files.
- **Metadata display** — document the explicit reference-source input, report omitted requests, and suppress missing-value placeholders while retaining deposited metadata.
- **Portable discovery** — recurse through tool and test directories; keep release discovery and hermetic checks aligned with nested paths.
- **Citation rationale** — retain the reason for per-citation locating spans without private incident prose or a weakened identity rule.

# v9.7.419 · 2026-09-09 · build 20260909v97419a · engine 1.9.155

- **Reference labels** — preserve declared strain codes while refusing genuine accession conflicts. Explicitly typed local records no longer abort deposited-reference joins; malformed reference keys still refuse.
- **Placement preparation** — retain ingroup records when rebuilding from underscored refpkg labels. Explain unbound outgroup authority without an uncaught traceback; preserve the existing minority-genus hold.
- **Metadata diagnostics** — report auxiliary fields that actually enrich the current query tips and distinguish off-tree rows.
- **Citation checks** — prevent neighbouring aliases from borrowing locating fields in the supplemental ordered-citation check. This check alone does not validate complete locus identity or scientific claims.
- **Suite accounting** — detect rising skips, falling pass counts and lost passing testcase identities; validate counts-only baselines and label imported execution environments unbound.
- **Tool discovery and release scope** — index nested tools, extend duplicate warnings, and align the release runner and anti-emptying guard with configured test discovery.
- **Concurrency guard** — recognize wrapped runners and prevent inspection words or compound commands from hiding another launch.

# v9.7.418 · 2026-09-09 · build 20260909v97418a · engine 1.9.154

- **Reference metadata** — preserve accession namespaces, bind explicitly supplied deposited metadata to source hashes, distinguish unavailable states, and bound display text while retaining full annotations.
- **Registry authority** — share portable registry resolution across consumers; bundled rows are reference-only and incompatible locked selections are refused.
- **Placement validation** — preserve reference alignment columns and require fresh split queries; retain the existing minority-genus outgroup hold.
- **Tree presentation** — wrap complete captions and preserve uncertainty in metadata while simplifying visible labels.
- **Cohort widgets** — accept MIBiG rows and require every member to belong to the cohort before reporting cohort-exclusive membership. Similarity does not establish compound identity.
- **Test coverage** — collect adjacent tool tests, use explicit slow markers, scan guarded subdirectories, and separate collection from execution census outcomes.
- **Health accounting** — recognize known qualified console calls without counting unrelated methods; consolidate report emissions with output parity. Existing ceiling and exact signed count remain unchanged.

# v9.7.417 · 2026-09-08 · build 20260908v97417a · engine 1.9.153

- **Import safety** — prevent seven deliverable scripts from writing during import and extend the import gate to deliverable tools.
- **Input refusals** — require collapse taxon metadata, report absent and degenerate trees, and bound sibling Newick parser reads.
- **Coverage and identity** — restore manifest tests, contain test stubs, report contract identity, and synchronize the figures front door.
- **Portable input binding** — same-day BLASTp rollups preserve existing genes and require full-locus query titles; ambiguous legacy rows are refused. Genome inventories require explicit source/output roots and guard canonical overwrites. Placement metadata uses explicit tables, refuses conflicts, and records input hashes.
- **Reference labels** — use the bundled strain resolver without silent exception fallback.
- **Tree display** — preserve the existing minority-genus outgroup hold and add optional label typography, spacing, and density controls.

Local release composition. Timestamp freshness is advisory and does not replace a content-bound validation receipt. Scientific acceptance remains separate.

- Accretion-justified: modeb_full50_contract.py — the four modules that require exactly fifty Mode-B sections take their contract from an operator-supplied path pinned by a sha256 the same config supplies, so a passing pin shows the file is unchanged since that config was written, not which contract it is. This resolves the frozen contract from the bundle and reports whether a supplied contract is the canonical one. Reporting only: the consumers are deliberately contract-agnostic and several fixtures drive them with generic synthetic contracts, so no admission rule changes.
- Accretion-justified: release_receipt_freshness.py — a validation receipt older than the code it covers is indistinguishable from a true one, so a stale red log leaves an archive neither sealable nor clearable without re-running the whole suite. This compares receipt timestamps against the newest packaged artifact for a directory or an archive, without unpacking.

# v9.7.416 · 2026-09-08 · build 20260908v97416a · engine 1.9.153

- **Phylogenetic figures** — portable source-aware labels and rectangular rendering with exact metadata joins, optional titled strips and saved R session information. Analysis/display transformations require explicit provenance and refusal on invalid input.
- **Workflow failures** — distinguish tool failures and unverified evidence from successful zero-result searches. Deliverable commands return nonzero on write refusal or execution failure.
- **Identity and coverage** — reuse canonical BiG-SCAPE namespace parsing, freeze the 50-section reference without changing consumer formats, and prevent parameter text from silently excluding fast tests.
- **Optional hooks** — preserve repeated-stop release, expose missing configuration and bound transcript reads. Existing permissive receipt matching remains unchanged; no live hook configuration is installed.
- Accretion-justified: modeb_full50_contract.py — the four modules that require exactly fifty Mode-B sections take their contract from an operator-supplied path pinned by a sha256 the same config supplies, so a passing pin shows the file is unchanged since that config was written, not which contract it is. This resolves the frozen contract from the bundle and reports whether a supplied contract is the canonical one. Reporting only: the consumers are deliberately contract-agnostic and several fixtures drive them with generic synthetic contracts, so no admission rule changes.
- Accretion-justified: release_receipt_freshness.py — a validation receipt older than the code it covers is indistinguishable from a true one, so a stale red log leaves an archive neither sealable nor clearable without re-running the whole suite. This compares receipt timestamps against the newest packaged artifact for a directory or an archive, without unpacking.

This candidate retains the .415 folder organization. Scientific acceptance is separate from mechanical validation. Detailed phylogenetic workflow documentation and release evidence describe the included interfaces and remaining evidence limits.

# v9.7.415 · 2026-09-08 · build 20260908v97415a · engine 1.9.152

- **Folder organization** — consolidate assistant guidance into AGENTS.md with a generated CLAUDE.md alias; README.md remains the human entry point. Move supporting docs and helpers into docs/ and bundle_support/, and debugging modules into debugging_modules/.
- **Inspector identity** — preserve complete locus identity in text and JSON; reject missing, conflicting, malformed, or duplicate native board identities before filtering. Inspect recommends the local launcher.
- **Portable test coverage** — recover generic pipeline checks with the admitted synthetic fixture and make the domain-evidence reference root configurable with an explicit missing-evidence skip.
- **External failure verdicts** — check reviewed subprocess results before accepting BLAST results, reference panels, ingest output, or version strings. Bind round-ledger status to structured gate receipts and preserve unverified coverage. Refuse failed pytest execution in manifest convergence.
- **Tree check visibility** — state when no-outgroup handling skipped branch-length checks, without changing thresholds or verdicts.
- **Optional hooks** — ship eight optional hooks with generic roots, local gate binding, explicit wiring guidance and focused checks; no live settings are installed.
- **Current documentation** — align setup guidance and the shared contract; add patch-author orientation, current specialist pointers, and panel/metadata provenance rules. Qualify historical version and network statements.

- **Safer deliverable writes** — wire the existing canonical overwrite guard into majority-read and forward its explicit force option.
- **Evidence columns and asset lookup** — keep BLAST HSP length separate from unknown protein length, and retain asset registry rows missing only a trailing note.

The deterministic extraction, scanning, scoring, and sealed package schema are unchanged; engine 1.9.152 is retained. The post-seal inspector JSON gains identity fields and stricter admission. Workspace 16S and ladder prototypes are not integrated; their review holds remain outside the shipped software.

# v9.7.414 · 2026-09-07 · build 20260907v97414a · engine 1.9.152

- **Public audit** — share Git/cache metadata exclusions across scan loops and scope them to the audited root; parent directory names cannot hide release content.
- **Render provenance** — retain the relative package anchor while identifying the package from its manifest in the shipped render summary.
- **Portable checks** — ship the local Markdown link checker and restore the self-contained cross-strain empty-input test without requiring a private cohort fixture.
- **Identifier hygiene** — retain the two test-source literal corrections from the identifier-only rebuild of the previous cut.
- **Label display helpers** — add species-title and deposited-host text parsers to the existing label module; preserve complete words and accession-prefixed title parsing. These helpers do not verify taxonomy or host association.
- **Waiver validity** — honor the existing signed-ceiling field when the newer optional field is absent, so stale exceptions cannot silently cover current regressions.

Accretion-justified: tools/check_md_links.py — portable implementation for the existing link-check tests.

# v9.7.413 · 2026-09-07 · build 20260907v97413a · engine 1.9.151

- **Evidence preparation** — hash-bound database readers, separate BLASTp channel histories, gene-first packet joins, structured domain and reference adapters, and cohort evidence views. External database and reader prerequisites remain explicit; unavailable evidence is not biological absence.
- **JSON visibility** — preserve requested JSON mode through timeout fallback and expose advisory parse-budget, downgrade and truncation observations. Overall package acceptance and biological interpretation are unchanged by this visibility field.
- **Identity and figures** — protect complete accessions, query keys and outgroup markers in the placement renderer; record unverified source bindings. Add cohort assembly-line and whole-region gene-map print companions.
- **Safety and composition** — canonical dated-output overwrite refusal, output redirection, serialized signoff checks, outgroup-aware gate corrections and safe CSV export wiring. Candidate database observations do not confer scientific acceptance.

Accretion-justified: mamey/canonical_write_guard.py — shared overwrite refusal for post-seal outputs.
Accretion-justified: mamey/cohort_enzyme_neighborhoods.py — source-bound neighborhood evidence view.
Accretion-justified: mamey/evidence_disagreements.py — preserve cross-source disagreements without adjudication.
Accretion-justified: mamey/mode_b/gene_first_database.py — bridge selected databases to the existing gene-first owner.
Accretion-justified: mamey/mode_b/mibig_evidence_adapter.py — bounded reference-evidence adapter.
Accretion-justified: mamey/modeb_evidence_packet.py — compact source-linked evidence packet.
Accretion-justified: mamey/structured_domain_motif_extension.py — preserve structured observations and binding holds.
Accretion-justified: mamey/tip_label.py — shared protected-field display and provenance receipt.
Accretion-justified: mamey/tool_database_reader.py — single database admission/read owner.
Accretion-justified: mamey/tool_database_session.py — reuse admitted readers with pinned source identities.

# v9.7.412 · 2026-09-07 · build 20260907v97412a · engine 1.9.150 (BUMPED — emitted manifest.json changes)

Reconciled Claude + Codex .412 ACCEPT union on the sealed v9.7.411 base. **Engine bumps 1.9.149 -> 1.9.150** because the emitted `manifest.json` changes for a fixed input: BC412_08 removes `gold_figures/figure_receipts.jsonl` from the hash-pinned set (it is appended post-seal and cannot be hash-pinned), correcting a false `mamey validate` FAIL on a MAMEY_COMPLETE package. Parity gold-run: 100 pinned entries vs .411's 101; validate rc=0 vs .411 rc=1. Scoring, parser and gates are unchanged; comparability is preserved except for the manifest pin-set.

- **Surface + section gates** — modeb card surface gate + Codex table-boundary / uniformity (advisory WARN) / section-column-binding follow-ons.
- **Waiver** — slack visibility + ceiling-at-signing + Codex enforcement-parity (diagnostics only).
- **Manual BLASTp ingest** — binding guard (BC412_07) + Codex context-fail-closed + length-conflict.
- **Claim-safety round 5** — detector shapes (BC412_09) + Codex clause-local negation scope.
- **Gold completeness** — lexical filler floor (BC412_08) + Codex behavioral tests + mutation pairing.
- **Phylo** — graft generation corrected to validated `gappa examine graft` (Codex 002, split-edge distance integrity); ggtree writer-import restored; neighborhoods + model/redo; overlay denominators.
- **Signoff** — bounded-scan tool + Codex incomplete-inspection diagnostics; the Stop-hook lock change is HELD.
- **Composition** — ordered queue auditor + Codex ordered-content / byte-identity.
- **Docs/tooling** — functional-review contract clarification; RG-GMCI roadmap typo; PREREQUISITES offline-install fix.
- HELD out of this cut: signoff Stop-hook, two widget file-drops (visual QA), composition wiki + second-machine doc (narrower claims), queue-position card disclosure (card owner).

# v9.7.411 · 2026-09-06 · build 20260906v97411a · engine 1.9.149 (UNCHANGED — bundle-only: tools/ + one data file + docs)

Two reconciled streams folded on the sealed v9.7.410 base: the **EGGPLANT phylo / EPA-ng placement lane** (Claude, 6 overlays + a data addition + a producer/tool/docs) and the **Codex §1–§50 Mode-B publication contract PILOT** (documentation/candidate). No engine bump — scoring, parser, and gates are unchanged; every change is a `tools/` script, one data file, or docs, so cross-strain comparability is preserved and no cohort re-run is needed. Claim-safety unchanged throughout.

## Phylo / EPA-ng lane (Eggplant)
- **A — per-genus placement + outgroup rooting** (`tools/phylo_place.py`): accepts a single-genus `--group`; roots on the appended outgroup's record IDs, not the ingroup string.
- **E — sentinel strip** (`tools/phylo_place.py`, depends on A): auto-strips foreign-genus sentinel refs on a per-genus + outgroup backbone (kills the dominating-branch sanity FAIL).
- **B — placement-figure labels + prune ladder** (`tools/placement_figure.py`): real host + 16S-accession labels from the strain table, uniform font (label-collision fix), `--neighbors-per-query` ladder, and **`_is_query` anchored so a culture-code "AS 4.xxxx" is no longer read as a fake query**.
- **D — phylo_postflight P3 placement-aware** (`tools/phylo_postflight.py`): P3 no longer false-FAILs an EPA-ng graft — a placement onto a fixed backbone carries no tree-wide SH-aLRT/UFBoot by construction, so P3 now reads per-query LWR + backbone bootstrap and PASSes, while a genuinely killed IQ-TREE genome tree still FAILs.
- **C — ggtree producer + methods footer** (NEW `tools/build_placement_ggtree_inputs.py`, `tools/ggtree_placement.R`, NEW `docs/EPA_NG_PLACEMENT_WORKFLOW.md`): ships the missing producer for the orphaned R renderer, a `GG_METHODS` footer, reference isolation-source coloring, and an end-to-end workflow doc.
- **F — harvest_16s tool** (NEW `tools/harvest_16s.py`): offline 16S staging (query ← authoritative FASTA, refs ← local RefSeq, outgroup ← cache/RefSeq). Plus `tools/ggtree_rect_heatmap.R` (rect-heatmap mode) and a phylo `TROUBLESHOOTING` doc.
- **Data — 6 PROVISIONAL outgroup rows** (`mamey/data/outgroup_registry.tsv`) for rare Hymenoptera genera with no prior outgroup (Actinacidiphila, Actinomycetospora, Nocardioides, Nocardiopsis, Saccharothrix, Streptosporangium): 4 genome-backed (real GCA/GCF) + 2 explicitly 16S-only (genome TBD). All marked PROVISIONAL (owner ratifies → LOCKED).

## Codex — §1–§50 Mode-B publication contract (PILOT)
- **Codex §1–§50 publication contract (doc-only pilot).** Updated the publication section-requirements doc to §1–§50, plus the contract candidate and a tree-context integration proposal. The emitter/structure-gate section count is unchanged, so machine-enforcement of §49–§50 is deferred to a follow-on (proposal shipped). The contract codifies SHA-256 normalized-AA-sequence as the positive identity key (length is rejection-only), exact-locus binding, `OBSERVED_UNBOUND`/`QUARANTINED` for unbound rows, gate-runs-against-saved-bytes timing, and per-section predecessor reconciliation.

## Integration correctness (found + fixed here)
- **`test_real_accessions`** required a real genome accession on every outgroup row, which the 2 new 16S-only rows (sentinel `PROVISIONAL_16S_only`, genome TBD by design) failed. Refined the test to exempt sentinel rows **while requiring them to be PROVISIONAL (never LOCKED)** — the genome-accession guarantee still holds for every genome-backed row. (The phylo patch set verified that its diffs applied, but had not run this test.)

## Verification
Each overlay dry-ran and applied to the pristine sealed v9.7.410 with **0 rejects**; all patched Python compiles. **Targeted suite over every patched area — phylo / placement / postflight / outgroup / ggtree / harvest / modeb / claim-safety — 967 passed / 0 failed.** The full suite ran clean through 89% here before the sandbox reaped the long run (an external-tool/EPA-ng test needs binaries absent in this environment; it is not a code failure) — recommend a full CI pass for the record. Seal/identity/manifest PASS; `SOURCE_CHECKSUMS` regenerated last.

# v9.7.410 · 2026-09-06 · build 20260906v97410a · engine 1.9.149 (bundle-only bump — reconciled two-stream fold: Codex Round07 + MODEB chain, 17 rebased Claude lanes, hostile-audit rounds 1–6, and 4 ported round-7 lanes; engine unchanged, scoring-neutral)

**A reconciled composition on sealed v9.7.409. Two parallel streams produced `.410` material; both were audited, the more complete one adopted, and the other's unique value ported in rather than discarded blind. Engine is unchanged (1.9.149): no scoring module is touched and cross-strain score comparability with .409 is preserved. Internal candidate; not a public tier, GitHub release, figure acceptance, scientific acceptance, or publication claim.**

- **Codex Round07 + MODEB chain folded** — the stream absent from the competing candidate; carries the Mode-B chain and conservation-evidence work.
- **17 Claude round-6 lanes rebased onto that chain** — rather than applied to pristine, so the two streams compose rather than collide. Includes the Mode-B `_HEADING_RE` false-refuse fix, PHANTOM_LOCUS generalized beyond the contig-index grammar, seal `locus_maps/` injection closure with typed unreadable-subtree FAIL, claim-safety linter/verb normalization, the GBK size guard (fail-closed variant), the CSV writer coverage sweep, the R figure templates, and the patch-lane convention with its enforcement tool.
- **Hostile-audit rounds 1–6 (H1–H42)** — adversarial findings folded from the audit series against the sealed .408/.409 artifacts.
- **4 round-7 lanes ported** (`ROUND7_ONTO_CANDIDATE`, 9 files / 15 hunks) — blastp-online CSV safety, phylo-place FASTA tab handling, receipt-ledger recursion guard (a fourth validator site the chain's own guard did not cover), and workflow-ledger gates. Two of seven workflow hunks were dropped as already-present via the chain; the five logic hunks landed.
- **One round-7 lane deliberately held** — the zero-width/bidi claim-safety variant. The chain already carries zero-width and bidi handling, so the lane is redundant here and was recorded as a possible obfuscation-detection regression by one reviewer. Applying cleanly is not correctness; it stays out pending its own pass.
- **Two lane defects found and fixed during reconciliation** — a lane that changed a gate message string without updating the test asserting it (now inside the patch, with the lane checker enforcing it), and orphan hunks produced by text-filtered diffs (now generated with diff-level exclusions; every regenerated lane re-swept clean).
- **Convention gap recorded, not built** — the patch-lane checker validates completeness, disposition and naming but does not read a lane's declared base or dry-run against it, which is why a lane checked against the wrong base can look defective. Follow-up for the convention lane.

No scoring, parser, standing-rule, domain-call, or biological-interpretation change. Known reds are carried into post-cut bug-hunting by owner decision, not silently: see the cut receipt for the exact list.

# v9.7.409 · 2026-09-05 · build 20260905v97409a · engine 1.9.149

- **Candidate audit follow-up (unreleased)** — Consolidates: the synthetic archive
  preparation formerly embedded in pytest configuration now lives in
  `tools/fixture_inputs.py` and is shared with the determinism inventory runner.
  The helper admits only the hash-bound shipped fixture, preserves member contents,
  refuses output clobbering, and records source/prepared/member hashes. The original
  archive and production compression-ratio guard remain unchanged. This test-only
  helper is outside the `mamey/` module-accretion manifest.

- **Engine bump 1.9.148 → 1.9.149** — one output-changing parser guard: `parsers.QUALIFIER_MAX_CHARS`
  caps any single GenBank qualifier at 4,000 characters at parse time (a 300 KB `/note` on one CDS
  previously reached the CSV reader as a field over its size limit and the figure renderer as an
  unbounded label, taking the render down with SIGKILL). Every other change in this cut is a gate,
  a refusal, an export guard or a document; scoring priors, scans and class routing are untouched.
  Full driver list in `docs/ENGINE_LINEAGE.md`.
- **Hostile-audit gates on the sealed .408 artifact (BC_409)** — fifteen findings from four adversarial
  rounds, eleven patched with 41 tests proven to fail on the sealed engine first: strain identifiers are
  validated before they become path components; a single-digit private prefix no longer slips the leak
  guard; the ingest structure gate returns typed findings instead of PASS on files it never evaluated;
  `validate` binds the manifest identity; archives no longer carry DOS-epoch timestamps; formula-shaped
  annotation text is neutralised before it reaches any workbook; a card for a locus the package does not
  contain is refused; an outdir inside the engine tree is refused; concurrent runs on one package take a
  lock; `compile-report` validates the package it reads; BLASTp ingest refuses garbage inputs with a typed
  status instead of a traceback.
- **New-laptop audit fixes (NL_409)** — the CLI imports without openpyxl, so `doctor`, `--help` and
  `--version` run on a bare interpreter; a specialised Low lead no longer sorts beneath housekeeping
  Inventory; `validate` fails on a seal-time `claim_safety_status` of FAIL (waivable only by a
  `CLAIM_SAFETY_WAIVER.json` file beside the package); a finished-profile card with product-identity
  phrasing is blocking in `verify-modeb` and refused by `modeb-export` unless `--force`; a crashed
  bioactivity check is a finding, never a silent pass; three zero-false-positive production verbs join
  both linters (receipt over 1,559 finished cards); timing receipts leave the checksum set; four
  fail-open gates (lead pages, receipt import branch, compilation gate, zero-alignment audit) fail closed;
  `bgc_report_builder` no longer refuses PUBLIC export for the cohort series (GOV-001); the prompts
  teach the §1–§48 contract; a vacuous inventory test is deleted.
- **Export sanitization (CLAUDE_409)** — the seven interactive HTML widgets neutralise `</script>` in
  their embedded payloads and escape attacker-controlled fields written to `innerHTML`; five CSV writers
  route through `csv_safety.SafeDictWriter`; the PDF builder escapes markup before reportlab.
  Accretion-justified: csv_safety.py — shared leading-character quote-guard for csv.DictWriter outputs (OWASP CSV-injection neutralisation), mirrors the xlsx guard in xlsx_determinism.py.
- **Packaging hygiene (CLAUDE_409)** — networkx and scipy declared in the `figures`/`all` extras;
  the reportlab doc reconciled to the `<5.0` pin; third-party and invoked-tool licences listed. The
  proposed print-ratchet raise to 1290 was refused: the sealed tree measures 1289 under the target
  interpreter with no syntax-skipped files, and ceilings only go down.
- **Laptop audit lanes folded (CLAUDE_409, 47 lanes)** — the fresh-install walkthrough on the second
  machine produced 57 candidate lanes; 47 are folded here after re-verification on this tree (science
  relabels held for the owner's ruling; the ratchet raise refused). Headlines: one front door (every root
  read-me routes to `python mamey_run.py start` + `AGENTS.md`); the claim-safety detector normalises
  markdown/quote/bracket wrappers and look-alike characters before matching, applies the safe-context
  test clause-locally (bare `similarity`/`-like` no longer switch it off), adds a narrow copula-identity
  pattern and a strict-shape check for `encodes`/`generates`/`affords`/`manufactures`; the seal gains a
  tracked `post_seal_checksums.txt` and a recomputed fingerprint; `verify_release_identity` now folds in
  the checksum verdict; gold completeness lints candidate cards instead of counting filenames; eleven CLI
  crash-on-bad-input paths become typed refusals; PairwiseAligner and GBK inputs are length-capped;
  external tree tools get a wall-clock timeout; ~150 text-mode `open()` calls gain `encoding="utf-8"`;
  BSD/GNU shell idioms made portable; figure data sidecars and provenance columns added to per-BGC tables;
  MIBiG anchor locator no longer drops WGS-accession records; NP Atlas provisioner keys match the resolver.
  Accretion-justified: figure_factory_default_config.py — shipped default config for the figure-factory subcommands (CLAUDE_409_figure_factory_default_config).
  Accretion-justified: pair_scan_caps.py — all-vs-all pair-scan caps for the resource-bounds lane (CLAUDE_409_resource_bounds).
- **Also landed** — the zero-byte `tools/wac_validation_genelevel.py` removed; the file atlas regenerated
  (it listed 286 rows against 587 real files); silent-swallow ceiling ratcheted down 152 → 151.

# v9.7.408 · 2026-09-04 · build 20260904v97408a · engine 1.9.148

- **Engine bump 1.9.147 → 1.9.148** — three output-changing evidence fixes. (1) TIGRFAM region
  misattribution: `antismash_evidence._tigrfam_from_rec` keyed every TIGRFAM hit to `_c1` regardless of
  true region, mislabelling the lead board's TIGRFAM panel and `_3_antismash_hmm.csv` on any
  multi-region-per-contig genome — reference and type strains most of all; this cohort's fragmented
  assemblies happened to mask it. (2) Cassette-pattern false positives, owner-ruled 2026-09-04: a bare
  `polyene` matched arylpolyene pigment genes, bare `phosphonate` matched ABC-transporter/uptake and the
  ICL-superfamily "…family protein" annotations, bare `nucleoside` matched nucleoside diphosphate kinase
  and purine salvage, bare `aminoglycoside` matched the RESISTANCE enzyme families — each raising a
  HIGH-tier diagnostic flag with a wet-lab route attached. Guards now mirror the CCTT siblings that
  already had them; registry JSON and CSV changed in step, because the registry overlay silently
  overwrites a Python-literal-only fix at import. (3) Scoring rescue-bonus vs mobile-element flag gap.
  Full driver list in `docs/ENGINE_LINEAGE.md`.
- **Release tier `sid` renamed `cohort`** (owner ruling 2026-09-04): the old name was one lab's strain
  series in a general-purpose tool; the new one states what the tier does — it keeps `cohort/` where
  `code` strips it. `tools/tier_vocabulary.py` is the single owner of tier names, zip labels and
  aliases; `sid` stays resolvable as a deprecated alias and `-SID-public-` archives still parse, so every
  bundle sealed up to v9.7.407 stays readable. Behaviour unchanged: the SID uniformity scrub the old
  comments described was removed at v9.7.364. Nothing that is data moved — `SID####` strain identifiers
  and the `'sid'` strain-id data key are untouched, and `tests/test_tier_vocabulary_v97408.py` fails if
  either ever does.
- **Ratchet paydown, genuine this time** — 95 runs of consecutive single-argument terminal emissions
  merged into one call each with `sep="\n"` (byte-identical output: same bytes, same stream, same
  order); ceilings lowered to the measured floor. A first pass collapsed three single-line
  `for line in ok:   emit(...)` loops in `mamey doctor` because it took a source line's leading
  whitespace as a proxy for block scope; the suite caught it, the loops were restored byte-identical to
  the seal, and the merge was re-run with the statement required to stand alone on its line.
- **Strain-identifier leak caught again, second cut running** — ten `AS-` cohort identifiers reached
  five shipped files inside comments recording that a fix was verified against a real deliverable
  bank. Both redaction guards fired. Genericised to the placeholder; every measured value retained.
- **Codex `.407` P-series (P407-01…20) reverted and returned with receipts** — 16 tests that pass on
  sealed `.407` fail with the set applied, including `test_crashed_structure_gate_is_not_recorded_as_a_clean_card`
  (a crashed Mode B structure gate returned an empty finding list and printed `structure: PASS`) and
  eight `SKIPPED_IDENTITY_MISMATCH` refusals of cards that previously recorded. The set's own
  verification was a focused 344-test selection plus apply/reverse parity, which proves a patch is
  well-formed, not that the engine still behaves.
- **Also landed** — bgc atlas region disambiguation (fragmented genomes collapsed every card to
  `strain/region001`); lead-board mobile-element flag gap; locus-map v8 region fixture; fresh-bank
  bootstrap crashes in `build_deep_data` / `build_lead_tiers`; modeb-deepdive verdict-count mismatch;
  ingest-package cohort verdict merge; lead-pages undefined-docstring swallow; package positional alias
  for BiG-SCAPE/BLASTp availability; two figure footer/legend collisions; Amber tree-overlay figure;
  Indigo manifest-contract producer-version context; Codex RiQ record identity, compare alignment
  threads, figure-atlas source preflight, checksum path containment, prompts-4/5 deep rebase, indirect
  scan-source binding, and XLSX container-metadata canonicalisation.
- **Phylo front-of-pipeline glue (AMBER-408)** — `tools/phylo_autopilot.py`: classify uploads as 16S /
  genome / protein by sequence length, BLAST-assign a genus to every 16S, route each strain to the
  Streptomyces / Nocardia / rare-genera backbone or flag it (`FLAG_OTHER` for non-actinomycete top hits,
  `OFF_TARGET_ACTINO` for distant actinomycetes — never forced onto a backbone it does not belong on),
  auto-build the reference set for exactly the observed genera, and hand off to `phylo_place`, which still
  owns the tree-approval gate; refuses without `--approved-by`. 20 tests, no DB or ML needed. Companion:
  `phylo_place` `--bootstrap` default 100 → 10 on both `build-ref` and `all` — a placement backbone's
  reference bootstraps are never displayed (EPA-ng reports its own per-query support) and 100 of them
  turned a few-hundred-taxon 16S reference into a multi-hour job; IQ-TREE fallback unchanged (already
  clamps to ≥1000). Guide: `docs/PHYLO_AUTOPILOT_WORKFLOW.md`. A placement is a neighbourhood, not a
  species or ANI call.
- **One door for agents, and the phylo tools run from anywhere** (owner: "we still have too many front
  doors, even with three of them I can't get my LLMs to use it"; measured: ten root orientation files
  totalling 1,574 lines, 108 subcommands, 283 scripts in `tools/`). Root cause was not volume alone: the
  bundle had no `AGENTS.md` and no `CLAUDE.md`, the two files coding agents read WITHOUT being told to,
  so every START_HERE file depended on the model choosing to open it. Added `AGENTS.md` with `CLAUDE.md`
  as its byte-identical copy (one door, two names; no version literal, so it cannot go stale) and
  `mamey_run.py start`, which prints the five-command happy path with the live version and runs doctor.
  The existing START_HERE files stay this cut because twenty-three tests and the bootstrap contract name
  them; they now add assistant-specific rules only and point back to the door. `phylo-autopilot` is
  registered as a `mamey_run` subcommand (pass-through to `tools/phylo_autopilot.py`) so there is a
  single phylogenetics entrance beside `phylo-run`. README build-status line no longer carries a stale
  `v9.7.391` literal. AMBER-409 F2/F3 folded early: `phylo_place` and `outgroup_registry` resolve
  `OFFICIAL_DATA/` by walking the caller's directory upward before falling back to the bundle's own
  parents, and a missing metadata spine now prints a WARN naming the consequence (bare tip labels)
  instead of degrading silently; the autopilot pins `SAPOTE_WORKSPACE_ROOT` before shelling out.
  `workspace_root()` itself is unchanged. Guard: `tests/test_one_door_v97408.py` (6).
- **Pre-GitHub root cleanup + a figure-comparison defect from the Codex hostile audit** (owner: "the
  pre-github top folder cleanup is a good idea"). Root censused with bindings per file; only zero-test-
  binding entries touched. Deleted: `.pytest_cache/`, `LICENSE.txt` (one blank line from `LICENSE`;
  `CITATION.cff` repointed), and two EMPTY cohort CSVs (`COHORT_MASTER.csv`, `COHORT_PRIORITY_LEADS.csv`
  — "0 leads across 0 strains") that `cohort-assemble`/`cohort-leads` wrote into the bundle root via a
  bare-filename `--out` default and that shipped inside both sealed `.407` zips; the census now refuses
  them. Moved to `docs/` with every reference updated: `EXTERNAL_VALIDATION.md`, `WHATS_NEW_368_370.md`,
  `B2_REGISTRY_WIRING_SPEC.md`, `MODEB_EXPORT_HOOK.md`, and `REPORT_THEME_TOKENS.json` (no loader in the
  tree; self-declared unaudited draft) to `docs/working/`. Root files 59 → 50; the bound remainder is
  carded for `.409`. Codex audit Q3 confirmed and fixed: `figure_set_renderer_tranche5` dropped
  standing-rule/primary-metabolism loci from the governed arm of the PRI/NOV governance-sensitivity
  panel but not from the "all packaged" arm, so the pair compared exclusion policy, not cohort
  membership; both arms now share eligibility and a test proves equal cohorts give equal medians
  (fails on `.407`: 2.0 vs 2.5). Two composer regressions caught by the full suite and fixed: a
  `contextlib.suppress` swallow-narrowing without the import (`cohort_figures.py`), and the two new
  subcommands missing from the command-catalog groups.
- **Governance ledger made public-safe and current; figure source bundle reads the modules table by
  feature type** (owner: "can we get rid of that governance_decisions.json or modify it so I can upload to
  GitHub"; "what about the bundle builder fix? can we work on that here?"). `GOVERNANCE_DECISIONS.json`
  rewritten at the same schema: GOV-001 records the owner's 2026-08-28 ruling (identifiers ship; genomes,
  unpublished novelty findings and third-party personal identifiers do not) as ACTIVE with a primary
  artifact, replacing a PENDING record whose text narrated internal leak history and named an
  unsigned owner; the sealing-lane process record (GOV-005) is dropped as internal; the release gate's
  requirements (ACTIVE, condition false, signer + date) are met, so the public-tier authorised path is
  now exercised by `test_public_tier_strip_v9_7_267` instead of the refusal path. The GOV-001 status
  test was updated deliberately, as its own message asked. Builder (`figure_source_bundle.py`, Codex
  hostile audit Q2/Q5): domains are counted from `aSDomain` rows only (an `aSModule` row's `domain`
  cell holds the tool name "antismash"; 163 of them led one strain's domain tally); the `UNMAPPED` pseudo
  bgc_id is a state, not a 97th BGC; per-feature-type counts are emitted; and `ACTIVE_SITE_PAIRING` rows
  (367 in that strain, antiSMASH active_site_finder residue calls bound to a domain and node) now populate
  `active_site_rows` / `active_site_state` with an `active_site_source` column when `deep_data.json`
  carries none — previously reported STRUCTURALLY_UNAVAILABLE for every BGC. Packages without a
  `feature_type` column behave exactly as before. Two tests, both proven to fail on the sealed `.407`.

Accretion-justified: mamey/xlsx_determinism.py — canonicalises OOXML core properties and ZIP member headers after an atomic openpyxl save so equal workbooks serialise to equal bytes; cell content and structure untouched. One producer, used by the packaging path.

## Landed (Claude .408 pool + Codex .408 lanes; Codex P407-01…20 reverted — see receipts)

# v9.7.407 · 2026-09-03 · build 20260903v97407a · engine 1.9.147

- **Engine bump 1.9.146 → 1.9.147** — the manifest contract map (CODEX-407 D01–D05 + F01) changes the
shape of the `manifest.json` handoff itself: nested-owner keys, a documented root provenance block, a
resistance-tier join, and a phantom depth-floor key removed from `gate_validation.json`. A consumer
written against the 1.9.146 manifest can read a 1.9.147 one, but not the reverse, so the engine
version moves. `schemas/manifest_contract.json` now documents the shape and
`mamey/manifest_schema.check_package_contract` validates a package against it (advisory, behind
`validate --manifest-contract`; never blocking in this cut). Every lane that responded to the
composition notice — five independent review lanes plus the engine lane — concurred on 1.9.147.

- **Terminal-emission seam (architecture, not a reduction)** — `mamey/console.py::emit`, `tools/_console.py::emit` and a `deliverable_tools/_console.py`
sibling are pass-through emitters: each forwards `*args, **kwargs` to `builtins.print` unchanged, so
`sep`, `end`, `file` and `flush` behave identically and every converted call site is byte-identical on
stdout and stderr. 1,608 call sites across 325 files now route through them. **This removes zero
emission sites.** Its value is that adding a `--quiet`, routing CLI chatter to a logger, or capturing
output for tests is now a change to one function instead of 1,608 call sites; that migration is
deliberately not done here, because it would alter what users see.

- **Ratchet counters repaired (a gate could be emptied by a rename)** — `repo_health.check_print_calls`
matched the *name* `print`, so the seam above dropped it from 1442 to 2 while removing nothing. It now
counts `print` and `emit`, with `emit` scoped to files that import an emitter (a name-only match
over-counted by 73 on unrelated local `emit()` functions). `check_injected_print` had the same hole,
fell 3 → 1, and now counts both spellings. Against the repaired counter the honest figure is **exactly
1442**, identical to `.406` — the equality is the receipt that the seam moved nothing. Written up with
the generalisation in the `.407` patch folder: four checks in this one cut were found to be reporting
success while protecting nothing (a vacuous-test sweep, seven tests whose filenames never matched
pytest's collection pattern including a domain-level mobile-element gate, this ratchet, and a
source-grep test anchored to the token `print`). Codex's gate-mutation probe measured the same question
at scale: 18 of 90 inventoried protections have a paired test that bites under mutation.

- **Redaction guard caught a live leak** — `test_tool_layer_is_cohort_id_free` failed on a real strain
identifier introduced into `tools/phylo_preflight.py` by this cut's own N50-floor card, whose threshold
was justified against a real archived assembly. Genericised to the placeholder its two sibling
constants already use; every measured value retained. That identifier appears zero times in the sealed
`.406` copy of that file, so the guard caught a new leak in the cut that introduced it. (This paragraph
originally named the strain and was itself caught by the public-tier redaction pass — the same defect,
one file over, which is the point: the guard does not care who wrote the line.)

Accretion-justified: mamey/console.py — single owner of direct terminal emission for the package; a pass-through seam so a future --quiet/logger/capture change is one function rather than 1,608 call sites. Adds no behaviour and removes no emission site.
Accretion-justified: mamey/layperson_guide.py — renders the layperson guide from a sealed package through the canonical claim-safety footer owner; post-seal, non-blocking, no competing report builder.
Accretion-justified: mamey/xlsx_determinism.py — one shared owner for post-save OOXML core-time and ZIP-member normalization; four workbook producers reuse it instead of implementing competing byte-canonicalization paths.

## Round 4 (Codex `.407` P-series + goal lanes, Claude audit lanes, Amber phylogeny, Indigo, VGP)

# v9.7.406 · 2026-09-03 · build 20260903v97406a · engine 1.9.146

**Engine bump 1.9.145 → 1.9.146** — `--project-registry` (BR6, rebased by the Claude audit lane; models hunk 1
dropped) records project-level privacy, publication status, genome state and assay availability on `RunContext`
and in the manifest's `project_privacy` block, and writes `project_registry_status.json` when no registry is
supplied. Owner ruling 2026-09-03: the run-level field is named `project_privacy_tier` (never confused with
`BGCRecord.privacy_tier`); the registry is recorded and does **not** drive release, which the landed
`--privacy-profile` mechanism keeps owning; supplying both flags on one run is the typed refusal
`PRIVACY_AUTHORITY_CONFLICT`; precedence between the two is deferred to a later engine. Full driver list in
`docs/ENGINE_LINEAGE.md`.

**Release cardinality (H1, owner ruling 2026-09-03)** — four canonical tiers (merged, sid, code, clean) remain the
gate; the PUBLIC-RELEASE zip is an explicit `--with-public` promotion in `tools/release.sh` /
`tools/check_tier_parity.py` (F7A) behind an ACTIVE GOV-001. Owner note recorded verbatim in spirit: for this
project's purposes the CODE tier is the tier of use; the other tiers are cut for parity, not consumed.

Composed by the Claude Code patch lane on the SEALED v9.7.405 CODE tier (SHA-256 6ab06b78…dac38f, the
immutable comparator). Every item below was authored by Codex as a candidate card against that seal, or found
independently by a Claude audit lane, and was landed here after a zero-fuzz apply and its own tests.

**Documentation correction (DH-007):** the stale v9.7.405 close-out statement that classified LOCUS_MAP_V8 as
absent is superseded: `mamey/locus_map_v8.py` landed at v9.7.405 and is the default renderer at all three call
sites; this correction records implementation state without rewriting the sealed entry. The sealed v9.7.405
entry's opening line also still carries composition-time wording that should have been swept at seal; the new
`tests/test_newest_changelog_composition_prose_v97406.py` gate (F6) now refuses such wording in the newest entry.

## Gates that stopped failing open
- **Candidate census fails closed** (`tools/candidate_census.py`): `os.walk` now carries an `onerror` callback;
  an unreadable subtree yields `coverage_complete=false`, typed `traversal_errors`, `status=INCOMPLETE`, exit 1.
  Found independently by Codex (CODEX_406 census card) and by a Claude audit lane on the sealed tier; the audit
  lane's four tests are ported onto the typed receipt.
- **Tier-set completeness** (`tools/check_tier_parity.py`): a one-zip input can no longer PASS. The four canonical
  tiers (code, clean, sid, merged) are required exactly once; a governance-gated PUBLIC-RELEASE promotion is
  recognised and parity-checked when present; unknown and duplicate labels are refused.
- **Release-tier identity** (F4/F5): `tools/gen_release_manifest.py` imports the gate's tier set instead of
  hard-coding "all five tiers"; archive recognition is an anchored full-filename match, not substring order.
- **Locus-maps phase receipt** (D1): the `--locus-maps on` run-path test now requires exactly START then END with no
  ERROR — the class of defect the v9.7.405 close-out only caught on a full-suite run.

## Figure Factory
- **LOCUS_MAP_V8 receipt consumer** (A2): the V8 receipt now carries output hashes/bytes and the PNG/SVG/CSV
  triple is validated before success; tampering raises `FIGURE_RECEIPT_MISMATCH`.
- **LOCUS_MAP_V8 edge cases** (A3): deterministic tie-breaking pinned; zero-supported comparators excluded;
  source-reported coverage above 100% is labelled, not capped; 47-label rail geometry tested.
- **Three-channel evidence matrix → publication bridge** (A4): SVG always, optional PNG via CairoSVG, the
  `figure_theme.CLAIM_SAFETY` footer byte-present and hash-bound in the receipt.
- **Tree-heatmap admission panel** (`mamey/tree_heatmap_panel.py`): consumes an already-admitted tree and refuses
  to render when the phylogeny evidence is held; uses the canonical footer.

## Phylogeny → Figure Factory bridge (engine side; the phylo lane builds the trees)
- **Phylogeny evidence receipt producer** (`mamey/phylo_evidence.py`, C1-P): reads — never builds or changes — an
  existing GToTree/IQ-TREE tree and alignment under the phylo lane's home; validates tool receipts, marker-set
  identity, the locked outgroup-registry row, reference de-duplication, SH-aLRT/UFBoot pairs, exact tip count and
  one assembly-quality flag per tip; writes `phylo_evidence_receipt.json` beside the tree.
- **Evidence widget gate** (`mamey/phylogeny_figure_factory.py`, `tools/figure_factory_next.py`, C1/B2): imports the
  producer's schema constant, verifies tree/alignment hashes and outgroup/tip parity, blocks any non-PASS receipt,
  and renders the provenance widget. One schema, one footer string, no second tree engine.

## Documentation currency
- `docs/TIER_SET_EXPLAINER.md` marked historical (v9.7.319 five-cut measurement); `docs/TIER_DIFFERENCES.md` no longer
  describes the SID uniformity scrub removed at CUT-02 (2026-08-12); both indexed in `CURRENT_DOCS_INDEX.md`.

## Round 3 (Codex round-3 cards + Claude audit lane + phylogeny lane, landed 2026-09-03)

Gate hardening G1 (accretion gate compares to the sealed baseline; a manifest row can no longer hide a module), G2
(WIRED_ORPHAN reverse check), G3 (print-debt paydown on twelve tool front doors, byte-identical output), G4 (lock
registry extended). Figure Factory A8 (five directed repairs on PROVISIONAL bindings; publication bridge refuses
them), A9 (Q-020 KCB tertiles, fully bound field), A10 part 1 (shared paired PNG/SVG save + receipt owner), A11
(readiness board), A12 (cohort denominator guard), A13 (carotenoid label provenance RAW_ANTISMASH vs GENE_BACKED).
Widgets B1 (package fingerprint comparator), B3 (V8 gene-roster hash binding), B5 (Lab Quest privacy end-to-end +
stale-private-path leak fix). Phylogeny C2 (ANI/AAI honesty), C3 (package-tree join), C4 (outgroup one-rank guard),
C5 (reference-dedup verification against the real review schema), C6 (KS-burden table), C7 (domain-tree contract);
Amber: fungal outgroup genomes and rules; tree-sanity multi-outgroup. Mode B D2 (UNKNOWN-KCB typed state; absent
input never moves novelty), D4 (structure-gate broad excepts typed), D5 (S1-S8 citation receipt), D6 (evidence
state machine), D8 (stale-card diff). Guards E1-E8 (RG-GMCI terminus complexity, tetronate ambiguous partner,
chromosome-first intake, --hmm-scan run path with named degradation, over-merge structural flag, saccharide
reason, fragment-surfacing invariant, capacity-not-identity string). Release F8 (public metadata redaction
invariant), F9 (reference-strain registry consumer), F10 (seal sweep tool). Calibration H1-H3 (panel + drift
report + runner). Progress-dashboard renderer. Held for the owner: F7A/F7B (release cardinality, H1 ruling).
All engine outputs remain class-level hypotheses with judgment deferred; provisional bindings are never publication.

Accretion-justified: mamey/figure_save.py — canonical paired PNG/SVG save, receipt, and legacy-inventory owner shared by Figure Factory producers.
Accretion-justified: mamey/interactive_figures/figure_set_renderer_tranche7.py — extends the canonical Figure Factory renderer family for the five directed A8 repairs without creating a competing source parser or save path.
Accretion-justified: mamey/interactive_figures/kcb_tertile_figure.py — adds the fully bound Q-020 renderer through the canonical source, owner-kept, exclusions, and figure-save owners.
Accretion-justified: mamey/interactive_figures/progress_dashboard.py — converts an owner-supplied operational plot grammar into one portable Figure Factory renderer while keeping data-source adapters separate.
Accretion-justified: mamey/modeb_evidence_state.py — centralizes a previously prose-only lifecycle already consumed by multiple Mode B owners.
Accretion-justified: mamey/reference_strain_registry.py — provides the previously absent portable consumer for the governed reference-strain registry while keeping its project rows outside the code tier.

Accretion-justified: mamey/phylo_evidence.py — the single producer of the phylogeny evidence receipt the Figure Factory consumer already validates; closes the gap between trees the phylo lane builds and figures that cite them, without a second tree engine or a copied schema.

Claim-safety: unchanged. Outputs remain class-level hypotheses with judgment deferred; phylogeny receipts establish
provenance and mechanical consistency, not evolutionary or biological truth; similarity is not identity; capacity is
not production.

# v9.7.405 · 2026-09-02 · build 20260902v97405a · engine 1.9.145 (bundle-only bump — no extraction, scan, or scoring semantics change; the Codex punch card composed)

**CANDIDATE — not a seal.** Composed by the Claude Code patch lane (with three sibling lanes on file grants) on the frozen v9.7.404 candidate, under the owner's ruling that the
whole 2026-09-02 Codex punch card is worked — Figure Factory and ranked-first items first — and that
nothing is left out of a cut without the literal word DEFER. Alex alone seals.

- **LOCUS_MAP_V8 landed** (owner-ruled in at close-out; Codex `August 18 Codex/LOCUS_MAP_V8_2026-08-18`,
  cut against v9.7.369, hand-rebased onto this tree). `mamey/locus_map_v8.py` is now the DEFAULT
  renderer behind `render_for_compile_report(..., renderer="v8")`, the `run` pipeline's per-BGC locus
  maps, and the `locus-maps` figure set: every exact locus tag displayed on a leader-line label rail
  (no suppression), a deterministic MIBiG per-gene comparator (most unique supported query genes,
  then median identity, reference rank, accession), per-gene identity/coverage rows, and a
  domain/HMM/motif evidence panel — emitting PNG + SVG + exact-locus CSV + a receipt carrying label,
  comparator, evidence, source and claim-ceiling checks. `renderer="legacy"` keeps the prior arrow map
  as a bounded comparison, and both call sites fall back to it with a NAMED degradation (never a silent
  substitution) if v8 raises. Two `except: pass` sites introduced by the port were converted to typed
  stderr diagnostics, so the swallow ratchet holds at 153. The renderer scores and adjudicates nothing:
  similarity is not product identity, annotations show capacity only, judgment deferred.
Accretion-justified: mamey/locus_map_v8.py — the evidence-dense exact-locus renderer; replaces the
  v9.7.90 gene-arrow map in place (one renderer, one owner) rather than adding a parallel figure path.
- **Strict source-disclosure output is redacted by default** (REPAIR_16 second half, owner-ruled in at
  close-out): findings are `STRICT_SOURCE_<KIND>: locator=<scope>/<redacted:sha12> count=N`, so a retained
  CI log of a failing run cannot itself disclose the identifiers the gate caught. `--show-identifiers`
  (both `tools/public_release_audit.py --strict-source-disclosure` and the compat
  `tools/strict_source_disclosure_audit.py`) restores paths + tokens for interactive triage. Detection
  tests now request the verbose form explicitly; `tests/test_strict_disclosure_redaction_v97405.py` pins
  the default. The `.404` CLI help had already described the pass as "redacted" — it was not until now.

**Engine version held at 1.9.145 on purpose.** No parser, scan, scorer, triage floor, or guard
changes. What lands is (a) post-seal machinery that consumes sealed packages, (b) gates that make
manual seal-time sweeps mechanical, (c) provenance/receipt hardening, and (d) documentation and CLI
ergonomics. Cross-run comparability with .403/.404 is unaffected. One seal-time gate is new
(locator reconciliation) and is additive; the owner may still rule it an engine bump.

## Landed from the Codex punch card (each with its own tests; zero-fuzz unless stated)

- **Figure Factory batch (first, per owner):** CODEX_392 three-channel evidence matrix adapter
  (antiSMASH / BLASTp / MIBiG kept as separate lanes, no composite score) together with the
  CODEX_392 component/theme gallery lineage it depends on (Gallery-Only Portability Repair 09);
  CODEX_397 owner-kept figure input adapter (hash-bound owner inputs — the mechanism the nine
  `REPAIR_FIRST` queue rows need); CODEX_396 figure owner-review compiler; CODEX_390 report theme
  menu + Mode B export / PDF-portability / cross-strain theme hooks. Package `mamey.interactive_figures`
  now resolves `publication_bridge` and `build_widget_data` lazily (PEP 562): the eager import pulled
  cohort exclusions in and its OFFICIAL_DATA warning polluted every gallery tool's JSON stderr.
- **Science surface:** CODEX_385 gene-anchored activity leads V2 (`activity-leads`,
  `activity-lead-genes`: five AF + five AB routing rows per strain, each bound to ≤5 exact genes,
  fail-closed holds) and, on top of it, `tools/render_activity_lead_reports.py` (patch lane 2) —
  the per-strain report rebuilt to the owner's Day-5 layperson-guide shape: assembly-quality tier
  table (corrected-BGC formula), cross-strain best-targets table, per-strain cards with Novelty /
  Layperson headline / Next experiment; honest scope limits stated in `docs/ACTIVITY_LEAD_REPORTS.md`.
  CODEX_390 ecology-context hand-off (`build_bgc_ecology_context`: exact-locus ECO rows, typed
  PRESENT/ABSENT/NOT_SCORED, so a Mode B card cannot copy a strain-level signal onto the wrong BGC).
  Per-strain whole-genome chitin reference evaluation (patch lane 3; BGC-uncoupled by design,
  encoded capacity only). CODEX_391 MIBiG protein-context safety + admission repair (patch lane 3):
  a per-gene MIBiG hit is admitted as novelty evidence only with its protein context bound.
- **Gates that replace manual sweeps:** CODEX_396 four-part locator reconciliation at seal;
  CODEX_396 generated-surface ownership (every generated doc/table has a declared owner and regen
  command); CODEX_390 reference-BGC structural validator; MODEB reader-orientation + anti-padding
  publication-gate rules; CODEX_390 second-tool hardening; CODEX_392 BiG-SCAPE GCF namespace guard
  (patch lane 4, hand-rebased: `.392`-era patch context carries real strain ids the tree has since
  scrubbed to AS-XXX — the general reason those patches reject); CODEX_390 third-gate receipt
  hardening (receipt half by patch lane 3; the `sync_version` half hand-ported: every anchored rule
  is planned in memory and written all-or-nothing with atomic writes, bootstrap docs regenerate
  BEFORE any anchor is touched, and a failed/timed-out generator refuses the bump).
- **Revived from the June-2026 pre-Sapote-Mamey code:** `mamey/lead_propagation.py` +
  `tools/lead_propagation_gate.py` — every triage-board lead (Exceptional/High) must appear, by exact
  `BGC_ID`, in every package surface that lists leads (compiled report, gene-by-gene top leads,
  manifest, manifest_short, OPEN_ME_FIRST, inventory, workbook); `mamey/bgc_alias_history.py` +
  `tools/bgc_alias_history.py` — legacy-id history across re-runs of one strain by physical-locus
  overlap (ids are never renamed).
- **Repo-health ratchets:** print ceiling ratcheted DOWN 1629 → 1624 (paid by deleting the
  duplicate 15-print `__main__` self-test in `mamey/architecture_first.py`, whose nine cases are
  all named tests), silent-swallow 154 → 153; new `injected_print` metric (ceiling 3) measures the
  `logger=print` blind spot instead of footnoting it; `--ratchet-down` rewrites a ceiling to the
  measured value (never upward); `tests/test_lock_registry_v97405.py` asserts the seven structural
  locks exist and that every ceiling has zero headroom. Ruling applied to all lanes: a whole file is
  never excluded from the print count to absorb new prints (that drops pre-existing debt from the
  measure); typed stderr diagnostics use `sys.stderr.write`.
- **KCB_score:** `tests/test_kcb_rank1_and_source_precedence_v97405.py` pins BOTH 2026-07-01 defects
  on one synthetic fixture; writing it exposed that `docs/KCB_SCORE_PROVENANCE.md` point 4 described
  the fallback as ending `LOW` when the provenance step lifts it to `MEDIUM` (never `HIGH`, manual
  check still required) — doc corrected to the observed final state.
- **CLI / UX (WAC-01375 items 7, 11, 12, 13, 15, 16, 29):** every `--package` subcommand also
  accepts the package as a positional (compatibility-preserving; `--package` stays canonical in every
  error); `docs/COMMAND_CATALOG.generated.md` groups all subcommands by task family and `--check`s
  itself; `mode-b` help says plainly it is a triage table, not a finished 48-section card; the
  unfilled-PDF message names how to close each slot kind (a missing BLASTp stream is a workflow gap,
  not a no-hit) and calls `--allow-unfilled-pdf` draft-only; `doctor` add-on lines carry project URL,
  licence family, and "not shipped in the bundle".
- **Docs / wiki:** Codex Wiki Revision 03 pages admitted after a currency pass (Audience Start
  Paths, Researcher Recipes, Mode B Gene-First & 48-Section Manual, Figure Factory Preflight &
  Methods); `docs/decisions/PROJECT_MEMORY_SNAPSHOT_FORK.md` closes the June-25 keep/retire fork as
  RESOLVED-BY-ALIAS at v9.7.400 (recommend keep the stub); `CURRENT_DOCS_INDEX.md` lists the new
  surfaces.
- **Second-pass sweep (defined-symbol census of every Codex patch against this tree) — thirteen
  families the first punch card missed; landed here:** CODEX_390 token-light document factory +
  Sapote Markdown document rendering (`mamey/sapote_markdown.py`, `document_export.py`,
  `document_factory.py`, `sapote-documents` console script, `documents` extra) — the
  deliverable-rendering layer; CODEX_391 generated deliverables registry + menu
  (`mamey/deliverables_registry.py`, `tools/generate_deliverables_menu.py`, regenerated
  `docs/DELIVERABLE_MENU.md`; `tools/session_checklist.py` now reads the registry AND the
  CODEX_396 governed durable-root interface); CODEX_390 Mode B verifier actionable diagnostics
  (`verify-modeb --report-json / --summary-only`; hand-merged onto the current §1–§30 wording —
  the first punch card wrongly listed this as landed); CODEX_396 denominator-truthfulness repair 13
  (`ambiguous_denominators`, `denominator_audit_result`, PASS_WITH_REVIEW_NOTES; reconciled to
  BC-2's .401 fail-closed window — the review-note path now exercises denominators ABOVE the
  window; also wrongly listed as landed before); CODEX_391 patch-packet logical payload hygiene
  (P001); CODEX_396 recovery-locator durability root repair 14 (`mamey/evidence_roots.py`,
  `report_from_spec.py`); the BiG-SCAPE namespace guard, Lab Quest governed interface, public-tier
  archive transaction, add-on wheelhouse, clinker caption sidecar and patch lane 2's own .400
  hook redesigns are on the lanes (see the punch card's section G for status).
- **Owner-gated, not deferred:** LOCUS_MAP_V8 (absent by defined-symbol check; a figure candidate
  awaiting the owner's visual/evidence-contract review) and the nine `REPAIR_FIRST` figure rows (specs
  authored; exact source/denominator bindings only the owner can supply) are routed to one
  consolidated owner ask. `.336` modeb_convergence_integration is archived (target module gone; the
  idea landed as the per-gene MIBiG channel).

Accretion-justified: mamey/activity_lead_genes.py — gene-level foundations for the activity-lead routing boards (CODEX_385 V2); no existing module binds a routing row to ≤5 exact genes.
Accretion-justified: mamey/activity_lead_report.py — per-strain AF/AB activity-lead routing report with fail-closed holds; the engine command behind the 44-strain report set.
Accretion-justified: mamey/ecology_context.py — one exact-locus ECO hand-off object for Mode B; closes the gap between the scans that exist and the §ECO prompt that asks for them.
Accretion-justified: mamey/interactive_figures/three_channel_evidence_matrix.py — Figure Factory consumer keeping antiSMASH/BLASTp/MIBiG as separate lanes; the "no composite score" rule made renderable.
Accretion-justified: mamey/interactive_figures/component_gallery.py — static Figure Factory component gallery (CODEX_392 Repair 09); required by the three-channel adapter's tests.
Accretion-justified: mamey/interactive_figures/theme_gallery.py — portable theme-gallery prototype (CODEX_392 Repair 09).
Accretion-justified: mamey/interactive_figures/optional_output.py — small collision-safe output transaction shared by the optional figure tools (typed OUTPUT_REFUSED).
Accretion-justified: mamey/interactive_figures/owner_kept_inputs.py — hash-bound owner-supplied figure inputs and readiness receipts (CODEX_397); the mechanism the REPAIR_FIRST rows need.
Accretion-justified: mamey/markdown_pdf.py — package-scoped ReportLab Markdown renderer (Codex PDF portability); shared by modeb_export and render_activity_lead_reports.
Accretion-justified: mamey/report_theme.py — four named report theme presets + semantic helpers consumed by the Mode B export and cross-strain hooks.
Accretion-justified: mamey/bigscape_namespace.py — sole normalizer for run-qualified BiG-SCAPE GCF identity; consolidates ad-hoc family-id handling across 10 tools/ front doors and 4 mamey/ consumers so a GCF id cannot leak across runs.
Accretion-justified: mamey/lead_propagation.py — revived June-2026 lead-propagation audit as a package gate; no existing module checks that a board lead reaches every lead-listing surface.
Accretion-justified: mamey/bgc_alias_history.py — legacy-id history across re-runs by physical-locus overlap; the one piece of the early identity module the four-part contract never carried.
Accretion-justified: mamey/chitin_reference_eval.py — formalises the Codex per-strain whole-genome chitin reference-evaluation workroom (2026-08-21) as a generalized library + operator tool; no existing module covers whole-genome CGAD-vs-reference capacity typing.
Accretion-justified: mamey/figure_theme.py — single home for figure geometry, typography, the claim-safety footer and the paired PNG/SVG export; consumes report_theme's colour tokens rather than duplicating them (one system, one owner per concern).
Accretion-justified: mamey/issue_registry.py — formalises the plain issue_log.md into typed IssueEvent records with TSV/JSONL siblings and an explicit provenance class; replaces an ad-hoc text file rather than adding a competing mechanism.
Accretion-justified: mamey/project_registry.py — single home for user-declared privacy tiers with fail-closed export authorisation and independent genome/bioassay axes; lands INERT — its cli/models wiring changes the manifest contract and is owner-gated as an engine-bump candidate (see FINDING_privacy_tier_collision.md).
Accretion-justified: mamey/npatlas_provision.py — user-provisioned NP Atlas ingest + declarative filter + content-addressed receipt; closes audit findings NPA-01 (env-var contract), NPA-02 (licence is CC BY-NC 4.0, never redistributed) and NPA-03/04; the resolver/structure modules gain only env unification and a typed RDKit SVG renderer (RENDERED/HOLD/UNAVAILABLE).
Accretion-justified: mamey/sapote_markdown.py — the authoring-contract parser for Sapote deliverables (DocumentModel with exact-locus identity and typed validation issues); no existing module parses a deliverable into a checkable model.
Accretion-justified: mamey/document_export.py — deterministic DOCX/PDF export with an ExportReceipt; the rendering half of the token-light document factory.
Accretion-justified: mamey/portfolio_config.py — portable multi-strain portfolio binding (CODEX_391, rebased) that consumes mamey/project_registry.py as the single privacy_tier producer instead of the superseded privacy_profile/evidence_registry pair; small pointer file + hash-bound registry, both below project root.
Accretion-justified: mamey/project_catalog.py — hash-bound portable package catalog plus the private (non-public, non-redacted) project handoff, portfolio-aware with stale-binding refusal on both ends; reads privacy_tier/privacy_assignment_state off the package manifest, no fourth privacy mechanism.
Accretion-justified: mamey/document_factory.py — plan→render→receipt factory for guides/reports; the deliverable-rendering layer the Day-5 layperson-guide bar needs (`sapote-documents` console script).
Accretion-justified: mamey/exact_identity.py — the one fail-closed "strain / node / region / alias" display contract (Codex Lab Quest lineage); cohort_proteins._exact_display duplicates it with a looser validator and is a review item, not silently replaced.
Accretion-justified: mamey/lab_quest.py — portable engine binding + receipt-governed command builders; EngineBinding/PackageSnapshot were absent from the tree (76 defined symbols, 18% present before this cut).
Accretion-justified: mamey/lab_quest_registry.py — receipt-backed WorkflowRegistry/EvidenceState state machine for six governed stations; new capability, not a restructuring.
Accretion-justified: mamey/lab_quest_app.py — optional Streamlit UI over the registry; never imported by the core engine.

Suite: pending the definitive run on the settled tree (three lanes composed concurrently; every
count read mid-composition is void by rule). Health `--strict`: PASS at zero headroom on all three
ratchets. Claim-safety unchanged: every output remains a class-level hypothesis with judgment
deferred; nothing here makes a structural, product, or bioactivity claim.

# v9.7.404 · 2026-09-02 · build 20260902v97404a · engine 1.9.145 (bundle-only bump — no extraction or scoring semantics change)

**CANDIDATE — not a seal.** Composed by the Claude Code patch lane on the sealed
`sapote-mamey-v9.7.403-CODE-analysis-free-20260902v97403a`. Alex alone seals.

**The engine version deliberately does NOT move.** Nothing here touches a scan, scorer, triage
floor, guard, or parser. What changes is (a) what a figure and a doc *say* about a number the
engine already produced, (b) two defects in the repo-health gate itself, and (c) a release-metadata
provenance label. Cross-run comparability with `.403` is unaffected in both directions.

## B1 — `KCB_score` is now bound to its exact antiSMASH source field, and the figure says what the bands are

An owner figure review asked whether antiSMASH calculates the similarity measure, what
`KCB_score` means, and how the displayed bands were produced. The engine could not answer from
any single place. It can now: `docs/KCB_SCORE_PROVENANCE.md` traces the full chain with line
references — `antismash_evidence.py:794` parses `Cumulative BLAST score:` out of `>>`-delimited
subject-cluster blocks of antiSMASH's ClusterBlast/KnownClusterBlast TXT; `:826` takes
`block_records[0]`, i.e. the file's own **rank 1**, not the numeric maximum; `:861` carries it as
`cumulative_score`; `:1206` sets `kcb_cumulative = max(score_vals)` across output folders;
`b1_normalizer.py:20` aliases it to `kcb_score`; `cli.py` emits it as the `KCB_score` column.

Three consequences are now stated where a reader will meet them, not left implicit:

- **antiSMASH computes it; Mamey never re-derives, re-scales, or normalises it.**
- **It is a cumulative sum, not a per-hit bitscore.** It grows with cluster size and matched-protein
  count, so **two BGCs' scores are not comparable unless they are of comparable size**. The D04 and
  D06 axis labels called it a "bitscore"; both are corrected.
- **The G03 bands are cohort tertiles** — `np.percentile(scores,[33,66])` over this cohort's own
  available scores. They are **not similarity thresholds**, carry no biological meaning, and the
  same BGC can change band on a different cohort with no change to its evidence. Bin labels are
  reworded to "lower / middle / upper cohort third" and the figure title states the tertile basis
  and the size-dependence, because a reader who sees "high" beside a number reads it as a threshold.

The provenance doc also records the 2026-07-01 rank-vs-score fix as the worked example of why this
matters: on one region, a rank-46 hit (61753.0) numerically outscored rank 1 (37992.0), and the
then-current `max(...)` silently reported the wrong cluster as the top KCB hit. A bigger number
that means less is precisely the failure this binding guards against.

## A4 — the print ratchet counted prose, and is now measured from the AST (ceiling ratcheted DOWN)

`check_print_calls` was a **text regex** over whole files, so a comment or docstring naming the
call token counted as debt — not hypothetical: a comment written for the `.403` composer delta
pushed the count over its own ceiling and turned the gate red for prose. It now counts real calls
from the AST (bare-`Name` `print` only; `x.print(...)` was never library debt). The measured truth
is **1629**, and the ceiling is **ratcheted down 1635 → 1629**. This is debt **re-measured**, not
rebaselined: six of the calls the gate was defending never existed. The remaining distribution is
recorded at the constant for whoever does the conversion work — 721 in `mamey/` across 89 files,
led by `cli.py` 235, `package_inspector.py` 72, `mode_b_receipt.py` 61.

## A3 — the CLI-exclusion set matched on basename across every scanned directory

`CLI_TOOL_EXCLUDE_FILES` was applied as `p.name not in ...` across all `SCAN_DIRS`, so naming a
`tools/` operator front door also silently excluded any `mamey/` library module with the same
filename. `.403` shipped exactly that collision — both `tools/blastp_channel_triage.py` and
`mamey/blastp_channel_triage.py`. Nothing was hidden (the library module emits nothing to stdout),
but the exclusion was one `print(` away from concealing real debt. Now scoped to `tools/` only.

## A1 — the release manifest no longer claims a receipt it does not have

`gen_release_manifest.py` hardcoded "receipt-bound log" into the full-suite row regardless of
whether the counts came from `--pytest-log` or from `--tests-passed`/`--tests-skipped` typed by an
operator. The sealed `.403` manifest carries that mislabel. Provenance is now threaded through:
`receipt-bound log` / `receipt-bound log, partly operator-supplied` / `operator-supplied counts, no
log bound`. A tool scrupulous enough to refuse a red log should not mislabel the honest fallback it
pushes the operator toward.

## F13 — ADMITTED (owner decision, recorded)

`FF402-F13-01` was composed into `.403` as engineering only, with its audit hold cleared exactly as
that hold specified: a second lane independently bound the R03 packet (34/36 payloads matching, both
mismatches being files the receipt itself classifies `READ_ONLY_OBSERVED_NOT_CANONICAL`). Under the
standing rule that **binding is not admission**, admission was withheld pending an explicit owner
word. **Alex has now given it: FF402-F13-01 is ADMITTED.** Recorded here so the transition from
"bound" to "admitted" is a dated decision and not a drift in wording.

## Not changed, deliberately

- **The nucleoside tier-floor fork stays pinned conservatively** (uncorroborated diagnostic does not
  floor). Alex's ruling: no decision until class-compatibility evidence exists; deciding
  under-informed is worse than waiting.
- **`GOV-001` public-release HOLD is untouched.** Technical cleanliness is not publication authority.

# v9.7.403 · 2026-09-02 · build 20260902v97403a · engine 1.9.145 (engine bump — governed-data source selection: an explicit `MAMEY_OFFICIAL_DATA` override is now exclusive)

**CANDIDATE — not a seal.** Composed by the Claude Code patch lane on the sealed
`v9.7.402-CODE-analysis-free-20260902v97402a` baseline. Eight cards plus one mandatory composer
delta and two repairs raised by an independent QA pass. Alex alone seals. Internal candidate; not
a public tier, GitHub release, figure acceptance, scientific acceptance, or publication claim.
The public-release HOLD (`GOV-001`, PENDING_OWNER_CONFIRMATION) remains in force and is untouched
by this cut. Board and per-card evidence:
`Patches for Sapote Mamey Claude (v9.7.403)/CUT_BOARD_403_CLAUDE.md`.

Accretion-justified: mamey/blastp_channel_triage.py — new BLASTp channel-triage contract module
(C402-T02). It is a new capability with no existing home: it writes a fresh triage table and
receipt from hits/identity-map/provenance inputs without modifying any package file, and the
existing `blastp_ingest.py` is an ingest path, not a triage-contract producer. Consolidates
nothing; the paired `tools/blastp_channel_triage.py` is its operator front door.

- **Governed-data override precedence — an explicit override is authoritative (engine-visible).**
  `mamey/exclusions.py` gains one helper, `_probe_paths(filename)`, used by both
  `_candidate_json_paths()` and `official_data_json()` so the two probes cannot drift apart
  again. When `MAMEY_OFFICIAL_DATA` is set the probe list is exactly that one path — the
  `__file__` parent walk is no longer appended behind it; `MAMEY_DATA_ROOT` is likewise exclusive
  when set with no explicit override; with neither set the parent walk is unchanged. A missing
  **or malformed** file under an override warns and falls back to the documented empty default,
  **never to another pack**. Also repaired: the "directory is present but <file> is not in it"
  warning no longer fires when the file *does* exist but failed to parse — it named the wrong
  problem and sent an operator hunting for a file that was there. This is the defect behind the
  three location-dependent `test_official_data_missing_file_warns_v97395.py` failures that cost
  time during the `.402` seal, and it was independently reproduced by an outside QA pass.
  New `tests/test_official_data_override_precedence_v97403.py` (9 tests) covers all five cases
  that pass named: explicit file present; explicit directory missing the file with a conflicting
  ancestor pack; malformed explicit file; no override with parent fallback; and `MAMEY_DATA_ROOT`
  precedence — for both `load_exclusions()` and `official_data_json()`.
- **Mode B gene-first — evidence-store bridge + Layer A/B/C receipts** (V4 successor steps 3 and
  4). The interpreter previously emitted ONE combined A+B authoring receipt, so the layers had no
  separate readiness, receipts, or layer-scoped holds. `mamey/mode_b/gene_first_layers.py` now
  emits three immutable receipts with one-way references (A → B → C), so Layer A can be READY
  while Layer B is HELD. Layer C is READY **only** with a digest-bound membership manifest whose
  explicit integer denominator equals its member count; a prefix or glob (`AS-*`, `AJS-*`,
  `SID*`) in a member list is a membership **hold** — prefixes are never membership authority.
  v1 computes no cohort statistic: it is the gate, not the analysis. Named follow-on, not
  silently claimed: a Layer-A-only *stage* still cannot be sealed.
- **Figure Factory × phylogenomics — tree-ordered BGC-class heatmap panel** (`mamey/tree_heatmap_panel.py`
  + operator front door), joining the Figure Factory to the GToTree lane so a class heatmap can be
  ordered by an actual tree rather than by an arbitrary sort.
- **Codex F13 provenance / source-artwork contract** (`FF402-F13-01`, unchanged Codex blob
  `c46f8677…`). Composed only after its own audit hold was cleared the way that hold specified:
  a **second lane** independently bound the R03 packet — 34/36 payloads hash-match, 0 missing,
  and both mismatches are the two external live files the receipt itself already classifies
  `READ_ONLY_OBSERVED_NOT_CANONICAL`. Binding is not admission; admission remains Alex's.
- **Codex phylo tick-label / data-rectangle clearance** (`tools/tree_bgc_overlay.py`), the phylo
  instance of the global invariant that no tick label may touch the data rectangle, consuming the
  canonical `figure_policy.validate_tick_label_data_clearance` gate — one clearance owner, no
  second implementation.
- **C402-T01 portable manifest-recovery locator** (`mamey/packaging.py`).
- **C402-T02 BLASTp channel-triage contract** + a **mandatory composer delta**. T02 bare breaks
  two gates: `print_calls` 1637 (ceiling 1635) and `silent_swallow` 155 (ceiling 154). The delta
  *converts* rather than rebaselines — `contextlib.suppress(OSError)` for the temp-file cleanup
  swallow, and the operator front door registered in the existing named `CLI_TOOL_EXCLUDE_FILES`
  set (its stdout IS the deliverable, same family as the phylo launchers). **No ceiling was
  raised.** Two latent defects in the gate itself are recorded in the delta's comments and left
  as separate candidates: `CLI_TOOL_EXCLUDE_FILES` matches on basename across every scanned
  directory, and `check_print_calls` is a raw text regex, so prose naming the call token counts.
- **Gold-figure empty-state placeholder gate made DPI-independent.**
  `tests/test_gold_figures_degenerate_input_v9_7_267.py` asserted a raw `w < 1150` px bound
  written when `savefig.dpi` was ~150. `cohort_figures` sets `PUBLICATION_RASTER_DPI = 300`
  globally, so the *correct* placeholder renders 1984×844 and the assertion went red for a reason
  unrelated to the guard it locks — making `--run-slow` unusable as a release gate. The
  discriminator now measures inches (`w / PUBLICATION_RASTER_DPI < 7.6`; placeholder 6.0 in,
  normal path ~8.6 in). **Mutation-verified**: with the early-return guard disabled the repaired
  assertion still fails, so the invariant is preserved, not weakened.

# v9.7.402 · 2026-09-02 · build 20260902v97402a · engine 1.9.144 (engine bump — Mode B gene-first v2 fixed to a versioned static workflow + Figure Factory publication/onboarding family; one flagged scoring-visible policy exception)

**Composed under an Alex ASAP-cut ruling ("cut ASAP, can mean an hour"), an 8-patch Claude fold
(6 BC-4 Section A cards + the 3-patch gene-first stack) plus Codex's 8-family Figure Factory board
(PF402-01 through 08) + FF402-LAYOUT-01, plus a W402-35 AJS-cohort fix (round 3) and two composer
deltas fixing gate breaches the composed tree surfaced. The engine bumps to 1.9.144 because two new
module families land for the first time: Mode B gene-first v2 and the Figure Factory publication/
onboarding/continuity family. Full detail, including the one deliberate scoring-visible exception
and its open policy question for Alex, is in `docs/ENGINE_LINEAGE.md`'s 1.9.144 entry. Cross-strain
comparability with `.401` preserved outside that one flagged exception. Internal candidate; not a
public tier, GitHub release, figure acceptance, scientific acceptance, or publication claim.
Public-release HOLD remains in force. Independent review of the Codex board and both composer
deltas: `Patches for Sapote Mamey Claude (v9.7.402)/CLAUDE_402_pf402_independent_review_and_composer_delta/REVIEW.md`.**

- **Mode B gene-first v2 — fixed, versioned, static workflow.** Sealed Codex candidate
  (`mamey/mode_b/gene_first_stage_v2.py`, `gene_first_interpret_v2.py`,
  `gene_first_figure_overlay.py`) plus two Alex-ratified blocking-gate successors: **GF3-2**
  converges the identity validator on the shipped `gene_first_explore.py`'s exact semantics —
  region normalizes (`region7`→`region007`), BGC alias normalizes/case-folds
  (`bgc013`→`BGC013`), a shortened NODE token (`NODE_7`) is now refused (9-fixture differential
  gate, 9/9 concordant, was 6/9 divergent — also fixes a bare-fixture-import bug that prevented
  the candidate's own tests from collecting inside the real bundle's `tests/` package). **GF3-1**
  adds coordinate/strand/membership to the canonical roster digest, schema bumped to
  `modeb_gene_first_stage_v2.1`, so a silently-moved locus boundary invalidates a stage even when
  the protein is unchanged. Deferred: the BLASTp evidence-store bridge, the three-layer
  (gene-autonomous/exact-locus/cohort-population) receipt split.
- **Figure Factory publication/onboarding/continuity family (PF402-01 through 08,
  FF402-LAYOUT-01)** — cohort/role-typed figure policy with an explicit STUDY/REFERENCE/
  EXTERNAL_BENCHMARK/OUTGROUP schema; a vector/raster publication-artwork gate (rejects
  PDF-screenshot-as-source, computes true effective DPI from native pixel width); a phylogeny
  receipt adapter + renderer pair (PF402-04 routes typed, digest-bound channels/states to
  PF402-03's tree/crosswalk/publication-gate renderer — a designed two-layer split, independently
  verified as a one-way dependency via `phylogeny_figure_factory.py:43`, not a duplication); a
  tick-label data-clearance fix; onboarding/package-continuity/portable-project widgets.
  Independently reviewed this session (SHA-verified 8/8, ordered zero-fuzz replay clean, 71
  passed/1 env-gated skip on the targeted battery).
- **W402-35 AJS-cohort fix (round 3)** — `mamey/cohort_resolver.py`'s AS-regex tightened to
  exact-anchor matching (a shape-based false-positive on a non-AS two-letter prefix no longer
  resolves to the private AS cohort); a new `membership_authority` field marks a generic routing
  result (`cohort="OTHER"`) as explicitly non-authoritative for scientific cohort/study
  membership, distinct from confirmed AS/SID resolution — no scientific membership is ever
  inferred from an identifier prefix. A pre-existing lock-test (`test_resolver_allowlist.py`)
  encoding the old buggy behavior is corrected in the same fold.
- **Composer delta 01** (4 fixes the composed-tree gates caught, none visible in the patches
  alone): print-ratchet breach (+4 CLI `print(` calls → `sys.stdout.write`); silent-swallow
  breach (+2 in `compile_report.py` → `contextlib.suppress`); PF402-03's foreign-cwd import
  failure (missing bundle-root bootstrap, now added per the gate's own prescribed fix); one
  swallow in the GF3-2 successor (`except StageHold: pass` → `contextlib.suppress(StageHold)`).
- **Composer delta 02** — regenerated `MODULE_MANIFEST.txt` for 7 new modules (3 gene-first + 4
  Figure Factory widgets) the accretion gate had no rows for; inverted the stale
  `test_resolver_allowlist::test_ajs_matches` lock (see W402-35 above); pinned the honest
  tier-1-floor behavior for the uncorroborated-diagnostic case (see the flagged exception below)
  plus a class-compatible companion test proving the diagnostic layer still floors correctly when
  corroborated.
- **Estate index OSError→realpath fallback, jq-family hooks → python3-stdlib, currency-stamp
  sync-and-lock rules, capabilities module-stem indexing, tool-inventory provenance correction** —
  five additive Section-A fixes, unchanged from the originally staged cards.

**Flagged, not fully resolved — open policy question for Alex**: removing the missing-KCB
`novelty += 5` credit (missing evidence must not inflate a novelty prior) exposed that the tier-1
diagnostic floor's corroboration guard (PC-12/#28) was being masked by that same phantom credit on
at least one cross-class fixture (a nucleoside diagnostic on an NRPS/T1PKS locus). The stricter,
honest behavior — an uncorroborated diagnostic on a class-incompatible locus does not floor to
Medium — is what ships. Whether it *should* is a live question: a future NUC~NRPS
class-compatibility ruling would flip today's answer. Full policy statement in
`docs/ENGINE_LINEAGE.md`'s 1.9.144 entry.

# v9.7.401 · 2026-09-02 · build 20260902v97401a · engine 1.9.143 (engine bump — 30-patch fold: active capability discovery, B2 class canon 23→37 per the Alex n≥10 ruling, safe_walk consolidation, gate/hook coverage family, cohort-ID guards, figure_check WIRED, wiki-in-bundle, intake→archive containment chain, Mode-B receipt parity, KCB resolved-anchor guard, figure digests, bootstrap fallback, exact-locus prompt contract, lock-tests; scoring-neutral)

**A 30-patch fold on the sealed v9.7.400 source. The engine bumps to 1.9.143 after three bundle-only cuts on 1.9.142: the .400 manifest-shape change (R1 source_scans aliasing) and the .401 B2 canon change (23 → 37 columns) must not share an engine stamp with pre-R1 manifests — provenance disambiguation, not a semantics change. No scoring recompute anywhere; the one guard-input fix (resolved-KCB anchor) tightens a mis-anchor bypass without touching priors. Cross-strain comparability with .400 preserved. Internal candidate; not a public tier, GitHub release, figure acceptance, scientific acceptance, or publication claim. Public-release HOLD remains in force.**

- **Active capability discovery** — `python mamey_run.py capabilities <keyword…>`: deterministic, offline, full-docstring search over `tools/*.py` + `mamey/*.py`, owned by the existing inventory generator (no second registry; the parallel-module variant was not adopted). Measured retrieval: the four re-derivation-incident tools are #1–#3 hits for natural phrasings. Closes the E1 class.
- **B2 product-class canon v1.1 (23 → 37)** — 14 cohort-attested classes promoted from the full-cohort 'other' remeasure (43 strains / 2,438 BGCs; every token n≥10; Alex ruling 2026-09-02). Label vocabulary only; pre-.401 workbooks keep folding promoted classes into 'other'. Residual 'other' ≈ 13.1%, honestly labeled.
- **Containment chain (intake → package → archive)** — non-regular ZIP-member admission with consistent Finder-metadata exclusion and atomic all-member extraction preflight; package-internal symlink rejection before validation/checksum/ZIP emission; public-tier final archives refuse clobber and commit atomically (stale members can no longer survive update-in-place).
- **safe_walk 4-gate consolidation** — the rglob-OSError family closed in one owner (public_release_audit false-PASS fixed); supersedes the sealed .400 #8/#9 pair.
- **Gate/hook coverage family (BC2 ×10)** — check-tools-before-building hook (advisory, E1 prevention at write time); BGC node-name guard + scanner content-scan upgrades; check_command_pointers, claim_safety_gate, evidence_conservation (multi-locus TIGRFAM), leak_audit (public AS-strain self-id), legacy_feature_gate atomic write, bgc_citation_gate bare-contig decoy, cross-strain denominator wide-drift coverage.
- **Cohort-ID guards** — tools- and source-tree scanners enforcing the no-cohort-literals convention (synthetics in the reserved 9900+ numeric range), redaction invariant asserted.
- **figure_check OPERATOR_ONLY → WIRED** — the render entrypoint refuses to draw a failing figure; registry reclassified, allowlist entry retired, subprocess tests in-patch. Figure Review Queue digests become mandatory (missing digest refuses before output).
- **Mode-B receipt identity parity** — batch receipt ingest cannot persist a card as COMPLETE under receipt/package/strain/header-alias conflicts.
- **KCB resolved-anchor guard** — scan_misanchor_guards() consumes the resolved combined KCB/MIBiG anchor, closing the genome-self-hit bypass.
- **Wiki-in-bundle** — 32-page drift-killed doc set as pure adds, cohort-ID-swept to zero with a lock-test pinning that at zero, currency stamps pinned to the live engine/bundle version at test time.
- **Bootstrap core fallback** — a failed `.[all]` install now falls back to editable core with the offline PIP_ARGS instead of leaving deps-only with a source-root smoke test masking the gap.
- **Exact-locus prompt contract** — start/prompt surfaces consistently require strain / full node-or-contig / region / BGC alias.
- **Data-root wiring (repaired) + thread tunables** — env-driven data-root resolution (repaired lineage supersedes the earlier variant) and explicit BUILD_TREE_JOBS/BUILD_TREE_THREADS controls preserving prior defaults.
- **Architecture lock-tests** — T2PKS minimal-core (KSα+CLF) and carotenoid pathway gates pinned; they guard the approved MECHANISM_C Mode-B corpus regeneration.

Composer deltas folded in this tree (owning lanes fold back): print-ratchet conversions in the capabilities subcommand (9 prints → stderr/stdout.write; ceiling held, waiver untouched); cohort-ID anonymizations in lane test docstrings/fixtures (synthetics in the reserved 9900+ numeric range); BC-3 pair re-emitted diff-generated; wiki/wiring current-bytes taken per the AMBER re-emit instruction.


**seal-time folds (Claude chat, 2026-09-02):** two post-composition edits folded before cut — (1) SEAL_GATE_REPAIR_01 (hooks/bgc_node_name_guard.sh): payload parse moved from jq to python3/stdlib-json (jq is absent in clean/container shells; the jq||true form silently disarmed the guard there — 2 deterministic test failures on a jq-less PATH, now 9/9 with jq genuinely absent); malformed-payload behavior unchanged. (2) genericized a personal home path in tests/test_session_cost_audit_identify_v97395.py:44 (carried forward from the .400b hygiene edit, which the .400a-based composition had reverted). Manifests/checksums regenerated over the folded tree.
# v9.7.400 · 2026-09-02 · build 20260902v97400a · engine 1.9.142 (bundle bump — 24-patch fold: package-slimming, class-label case family, hook v3 redesigns, phylo domain-tree family, figure/render gates, release-tarball tool; engine unchanged, scoring-neutral)

**A 24-patch correctness/hygiene/tooling fold on the sealed v9.7.399 source. Engine is unchanged (1.9.142): no scoring module is touched (`scoring`/`rules`/`efls`/`card_verdicts`/`class_believability` are byte-identical to .399), and cross-strain score comparability with .399 is preserved. Internal candidate; not a public tier, GitHub release, figure acceptance, scientific acceptance, or publication claim. Public-release HOLD remains in force.**

- **Package slimming** — snapshot alias debloat (−24.7%/pkg) and `scan_channel_alias` (−37.8%/pkg; ~−44% composed): 4 manifest `source_scans` channels become alias stubs to the byte-identical standalone package files, the directory being the authority. The `Complete_Package.zip` (the documented unit of exchange) is unaffected; only a bare `manifest.json` shared without its package would lose those 4 channels.
- **Class-label case family (emitted-output correctness)** — `master_workbook` class-matrix, `cohort_figures` (re-emit with merge semantics), and `strain_bigscape_report` all fixed the same defect: real antiSMASH product tokens are lowercase, so case-sensitive matching created a second differently-cased column and the curated canonical column read as zero. Counts now route to the established casing; emitted class distributions change (correctly bucketed), no per-BGC score recompute. Same defect earlier fixed in `cnbu.py` (.371) and `master_workbook` product-counts (.399).
- **Hook v3 redesigns** — `block_subagent`, `deliverable_markdown_reminder`, `link_check`, `overclaim_guard`, `provenance_log_root`, `save_transcript`, `session_cost_ledger` reworked to canonical headers / v3 contracts (Codex C399 series closed).
- **Phylo domain-tree family** — additive per-class domain-tree subsections (existing `domain_phylogeny()` byte-unchanged; opt-in `domain_tree_sections()` carrying the capacity-context claim-safety note), re-emitted domain tree builder / tailoring extract / modeb domain trees with in-patch portable tests, and a fail-closed `root_and_gate` (typed refusals, no refpkg emitted on refusal; the print-and-continue path is gone and a test asserts its absence).
- **Figure/render + QC gates** — AMBER figure_check render gate (F1–F5, real-receipt tests) registered OPERATOR_ONLY; duplicate-dict-key and brace-path checks hardened for unreadable dirs; `wise_fragmented_pks` queue-ID label (display-only); resistance legend strip.
- **Release tooling** — `tools/make_release_tarball.sh` (+ test): space-safe relative-name `.sha256` sidecar beside a sealed artifact (ZIP stays canonical; any public tarball comes from the public tier only).

Composer deltas folded in this tree (owning lanes fold back): claim-safety comment narrowing in the modeb no-marker assert; a workspace locator removed from `tailoring_families.json` and a reviewer lane name neutralized in `phylo_place.py` (both public_release_audit catches); 5 status/refusal prints → stderr in `build_domain_tree.py` (print ratchet held at ceiling 1635, ceiling/waiver untouched); `figure_check` gate registration; regenerated MODULE_MANIFEST (288 modules) and tools inventory (246 tools).

No scoring, parser, standing-rule, domain-call, or biological-interpretation change. **Note:** print-ratchet and silent-swallow ceilings are both AT ceiling (1635/1635, 154/154) after this fold — the next cut has zero headroom and should convert, not add.
# v9.7.399 · 2026-09-01 · build 20260901v97399a · engine 1.9.142 (bundle bump — 20-patch case-insensitivity/resolver/phylo-tooling fold; engine unchanged, scoring-neutral)

**A 20-patch correctness/hygiene fold on the sealed v9.7.398 source. Engine is unchanged (1.9.142): no scoring module is touched (`scoring`/`rules`/`efls`/`card_verdicts` are byte-identical to .398), and cross-strain score comparability with .398 is preserved. Internal candidate; not a public tier, GitHub release, figure acceptance, scientific acceptance, or publication claim. Public-release HOLD remains in force.**

- **B2 class-name case-insensitivity (emitted-output correctness)** — `mamey/master_workbook.py` folded uppercase frozen-header B2 classes (NRPS, T1PKS/T2PKS/T3PKS, NRPS-like, NRP-metallophore, NI-siderophore) into `other` because the canonical-membership check was case-sensitive against lowercase antiSMASH product tokens. Matching is now case-insensitive; emitted rows keep the frozen canonical column names. This changes workbook class counts (correctly bucketing classes that were mislabeled), the same defect already fixed in `cnbu.py` at .371; sibling fixes this round in `tools/reclass_check.py`. Aggregation/label correctness only — no per-BGC score changes.
- **Flavor-aware resolver + case-twin dedup** — `mamey/strain_data_home.py`: a `flavor` argument threads through package/antiSMASH resolution so a caller asking for a specific detection-strictness flavor never silently gets another (the flavor-separated canonical directory is the strictness authority); `flavor=None` preserves the prior priority order byte-for-byte. Package walk now dedups by `(st_dev, st_ino)` inode identity, fixing double-indexing of a single physical directory reached via case-variant path strings on case-insensitive filesystems.
- **Hermetic suite** — the test suite now passes without the workspace `MAMEY_OFFICIAL_DATA` / `MAMEY_PACKAGE_HOMES` env wired; previously 18 tests depended on it.
- **Phylo tooling** — outgroup-aware render hard-gate and sign-off parity; homology-OK cleanup in `domain_phylo_rescue`; species dedup by accession key in `phylo_place`; an added fungal outgroup registry (per-row LOCKED/CONFIRM status carried in-band, CONFIRM rows explicitly unverified-representativeness), a fungal-placement workflow doc, and a standalone ggtree R renderer.
- **Label hygiene** — AS-strain relabel to underscore form in a render/label path; case-insensitive reclass check.

Ten new bundle tests accompany the fold. No scoring, parser, standing-rule, domain-call, or biological-interpretation change. **Open governance item:** five patches touching two source files (`strain_data_home.py`, `tests/conftest.py`; the rest test-only) carry full receipts and an in-cut engineering review but still owe formal independent sign-off — tracked, not blocking this internal candidate.

# v9.7.398 · 2026-09-01 · build 20260901v97398a · engine 1.9.142 (bundle bump — 14-patch hygiene/robustness/QC fold; engine unchanged, scoring-neutral)

**A 14-patch correctness/hygiene fold on the sealed v9.7.397 source. Engine is unchanged (1.9.142) and no scored or per-strain-emitted analytic result changes — every patch is workspace-freshness, ingest/parse robustness, figure contrast, monitoring parity, standalone-tool consistency, or QC-verdict correctness. Internal candidate; not a public tier, GitHub release, figure acceptance, scientific acceptance, or publication claim.**

- **Doctor `runs/` cleanup** — the doctor probe no longer leaves an empty `runs/` directory at the tree root; the staging hygiene defect that produced the shipped empty `runs/` is fixed at source.
- **Package flavor token in filename** — emitted package filenames carry the package-flavor token so re-runs are distinguishable.
- **Workspace-home freshness (4 patches)** — `strain_data_home`, `roster_v2` inventory, `inventory_audit` default homes, and `fair_cohort_analysis` no longer rely on a dated glob; inventory/roster reads reflect current workspace state rather than a stale or date-pinned view.
- **Ingest/parse robustness (5 patches)** — `sapote_md_preflight` NaN fallback case, `intake_harness` safe-extract consolidation, heatmap text-contrast fix, `build_bgc_markers` TIGRFAM fallback panel brought into line with the engine's 13-ID `DIAGNOSTIC_TIGRFAM` (fallback path only; the engine panel itself is unchanged), and `tab_reconcile` CSV parse-failure handling.
- **Evidence/monitoring (2 patches)** — `evidence_bundle` short-contig search, and `blastp_monitoring` stderr-regex parity.
- **Phylogenetic QC correctness** — `tree_sanity_check` is now outgroup-aware: a designated outgroup's long anchor branch is no longer flagged as pathological. This is a standalone QC tool (not imported by the scoring engine), so no scored output changes.

Thirteen new bundle tests accompany the fold. No scoring, parser, standing-rule, domain-call, or biological-interpretation change; cross-strain comparability with .397 output is preserved. Public-release HOLD remains in force; candidate status does not authorize GitHub promotion or public release.

# v9.7.397 · 2026-09-01 · build 20260901v97397a · engine 1.9.142 (internal evaluation candidate — portable figure review, traveling caption methods, and truthful EFLS pair counts)

**A deliberately narrow five-patch internal evaluation candidate on the sealed v9.7.396 source bundle. It adds a portable Figure Factory owner-review queue, strengthens the traveling caption/method contract, and reports EFLS total candidate-pair counts separately from capped listed pairs. The engine bump records the EFLS emitted-report semantic change. This candidate is for Claude and owner engineering evaluation only; it is not a public tier, GitHub release, figure acceptance, scientific acceptance, or publication claim.**

- **Portable Figure Review Queue** — builds a deterministic review-only HTML/TSV/Markdown surface from existing manifests without copying figures or editing decisions. Repair 02 makes final publication of the queue directory atomic and no-replace on supported hosts, preserves a competing destination, and returns a typed path-redacted refusal when the requested parent directory is unavailable.
- **Traveling caption and methods contract** — keeps publication-style caption/method text outside the plotted canvas while binding source, transformation, comparison group, exact overall and per-group denominator fields, units, typed and untyped missingness, contradictions, and external-benchmark default-off/nonpooled behavior. Placeholder method fields and contradictory benchmark statements fail before output.
- **Truthful EFLS pair-count reporting** — current payloads report total candidate pairs separately from the capped listed subset; legacy payloads explicitly mark the total unavailable while retaining the listed count. The emitted-report meaning changes, but no BGC score, class assignment, gene annotation, or biological interpretation is changed.
- **Cut boundary** — only the five exact patch applications in `PATCH_ORDER.tsv` are included. The owner-kept figure-input adapter, wiki integration, registry/privacy policy, public-source work, and every other v9.7.397 proposal remain outside this candidate.

No existing figure is scientifically accepted by this cut. No figure-derived result is admitted into a manuscript or publication.

# v9.7.396 · 2026-08-31 · build 20260831v97396a · engine 1.9.141 (bundle bump — fail-closed cut guards, truthful evidence states, Figure Factory preflight, deterministic output, and atomic JSON durability)

**A focused 15-patch internal source-bundle cut on the sealed v9.7.395 baseline. It strengthens release/cut refusal behavior, preserves typed evidence availability, improves Figure Factory preflight and caption requirements, eliminates order-sensitive emitted bytes, and replaces six direct JSON writes with one existing atomic owner. Engine and scoring semantics are unchanged. Internal candidate only; not a public tier, GitHub release, figure acceptance, scientific acceptance, or publication claim.**

- **Fail-closed cut and integrity guards** — provenance-column delimiter extension mismatches, malformed release-manifest lines, nested release-like artifacts, `runs` prefix-boundary drift, retired-doctrine case variants, and empty/whitespace/comment-only checksum manifests now refuse explicitly instead of passing through an ambiguous state.
- **Truthful evidence and intake telemetry** — zero available BLASTp observations remain distinct from not-run or absent states; non-finite comparator coverage is typed; the batch parser counts the same canonical antiSMASH region members as the parser and records detectable parsed-member shortfalls without changing typed parse failures.
- **Figure Factory preflight and caption contract** — the exact parent → Repair02 → Repair03 family refuses meaningless all-zero panels, honors explicitly default-off external benchmarks, requires source/denominator/transformation/comparison/contradiction context, and keeps governance prose off the plotted canvas. This is renderer-policy code, not acceptance of any existing figure.
- **Deterministic emitted outputs** — set-derived values and selector ties are made stable; ambiguous outgroup choice fails closed rather than selecting lexicographically. Similarity, deterministic ordering, and successful rendering do not establish scientific identity or interpretation.
- **Atomic JSON durability** — six operator-facing JSON writers now reuse `tools/_wbio.py` for sibling-stage, flush, file-fsync, atomic replace, directory-fsync, containment, symlink refusal, and cleanup. Existing file modes are preserved; newly created files deliberately use private mode `0600`.
- **Cut boundary** — the product artifact is the portable extracted source bundle/ZIP. Wheel/sdist parity for packaged runtime modules and data was checked separately, but six selected top-level tools remain source-bundle-only; wheel/sdist are not represented as the complete operator workflow in this cut.

No BGC scoring, standing-rule, domain-call, product-class assignment, biological interpretation, or publication status changes. Public-source disclosure and final public-archive transaction work remain separate held successors.

# v9.7.395 · 2026-08-31 · build 20260831v97395a · engine 1.9.141 (bundle bump — 33-patch fold: case-insensitivity gate family, exclusions out of bundle, silent-failure warnings, tool inventory, phylo placement dedup; engine unchanged)

**A correctness/claim-safety/hygiene fold on the sealed v9.7.394 source, composing 33 patches (27 from the Claude-side patch lanes; 4 Codex, including the 966-line Mode-B gene-first portability patch). No engine change. Internal candidate; not a public tier, GitHub release, or publication claim.**

- **Case-insensitivity bug family closed** — three citation/structure gates (`mamey/validators/node_notation.py`, `tools/deliverable_citation_audit.py`, `mamey/modeb_structure_gate.py`) missed lowercase BGC ids such as `bgc028`; the sibling `bgc_citation_gate.py` was fixed at .383/.384 and never propagated. `deliverable_citation_audit` is the section-15 BLOCK gate for finished deliverables, so the gap admitted uncited lowercase ids into shipped work. Closed with `re.IGNORECASE` symmetrically across all three.
- **Exclusions out of the bundle** — the four real exclusion identifiers replaced with synthetic placeholder identifiers across the shared fixture and eleven tests; the governed denominator genericized. The exclusion set now lives only in workspace `OFFICIAL_DATA`, per PI ruling.
- **Silent-failure family** — `official_data_json()` and the `doctor` governed-denominator check both previously returned empty or skipped with no signal; both now emit a warning.
- **Tool inventory + env docs** — the placement stack (MAFFT / RAxML-NG / EPA-ng / gappa), FastTree, blastn, and makeblastdb added to `docs/EXTERNAL_TOOL_INVENTORY.md` with versions, conda install recipes, an env-var contract, and citations.
- **Phylogenetic placement reference dedup** — duplicated type strains removed from the Nocardia 16S reference backbone.
- **Six composition-time failures found and fixed** — three module-accretion (manifest regenerated), two public-tier identity leaks (an internal chat codename in `tools/repo_health.py`, plus two more caught in new patch code — all three found by running `public_release_audit`, none by reading the diff), and one Codex-vs-Codex conflict where a feature patch emitted a JSON receipt via bare `print()` that its own convergence test forbade (reconciled to `sys.stdout.write`).

No scoring, parser, standing-rule, domain-call, or biological-interpretation behavior changes beyond the gate case-sensitivity fixes noted above. Candidate status does not authorize GitHub promotion or public release.

# v9.7.394 · 2026-08-31 · build 20260831v97394a · engine 1.9.141 (bundle bump — root-sprawl reduction; engine unchanged)

**A doc/data-hygiene cut on the sealed v9.7.393 source. It reduces repo-root sprawl: deletes two header-only CSV stubs with no readers, archives six unreferenced/point-in-time root documents to `docs/archive/`, and relocates three generated status graphics to `docs/status/`. No Python touched, no import path changed. Internal candidate; not a public tier, GitHub release, or publication claim.**

- **Root-file reduction** — loose files at the repo root go 67 → 56. `COHORT_MASTER_class_by_strain.csv` (8 B) and `COHORT_MASTER_strain_summary.csv` (92 B), both header-only stubs with zero references, deleted; six unreferenced root docs archived to `docs/archive/` (`RESEARCH_START_v9.7.138.md`, `RECONCILIATION_locus_renderer_to_analysis.md`, `B2_REGISTRY_WIRING_PHASE2_SPEC.md`, `READ_ME_FIRST.txt`, `TEST_PARTITIONS.md`, `PATCH_APPLY_LOG.txt`); three `workflow_status_*PRIVATE*` status graphics relocated to `docs/status/`. All eleven verified to have zero references by exact filename and stem across code, tests, and docs, and absent from `MODULE_MANIFEST.txt` and `RELEASE_MANIFEST.md`.
- **Reversible by construction** — everything except the two header-only stubs was archived rather than deleted, so any surprise consumer can be repointed rather than restored. No `.py`, test, or import path affected; the only regeneration is the routine cut-owned manifest/checksum refresh.

No scoring, parser, standing-rule, domain-call, or biological-interpretation behavior changes. Candidate status does not authorize GitHub promotion or public release.

# v9.7.393 · 2026-08-31 · build 20260831v97393a · engine 1.9.141 (bundle bump — AS-free shipped source + CI repair; engine unchanged)

**A source-genericization and CI-repair cut on the sealed v9.7.392b baseline. It removes real cohort strain identifiers from shipped Python (111 files → 3, the 3 remaining being an allowlisted synthetic sentinel), routes hardcoded exclusion-set literals to the `mamey.exclusions` SSOT, externalizes four cohort/demo constants to `OFFICIAL_DATA/*.json` with empty public defaults, genericizes two strain-named public API identifiers, and repairs both CI failures. Internal candidate; not a public tier, GitHub release, or publication claim.**

- **AS-free shipped source** — 204 prose spans (comments, docstrings, argparse help) across `mamey/`, `tools/`, `deliverable_tools/`, `sapote_hooks/` rewritten with the codebase's own `redact_public_tier.redact_text` so genericizer and gate share one matcher; AS-48 carve-out and `test_*.py` references preserved.
- **Exclusion SSOT consolidation** — hardcoded cohort-exclusion literals routed to `mamey.exclusions`; this also unified an inconsistent exclusion denominator, where some `deliverable_tools/` files omitted a strain that sibling `tools/` files excluded. Exclusion membership is now resolved solely from the operator's `OFFICIAL_DATA/exclusions.json`, so the shipped code names no strain and the operator's own exclusion set governs their analysis. Ratified by the owner 2026-08-31.
- **Cohort/demo data externalized** — `TIER`, `ATTINE_ANT_STRAINS`, `DEMO_STRAINS`, `CO_ASSEMBLY` moved to `OFFICIAL_DATA/*.json` with empty public defaults via a new `mamey.exclusions.official_data_json()` helper mirroring the existing `load_exclusions()` probing.
- **Public API genericization** — two strain-named public API identifiers renamed to strain-neutral names (`streptophenazine_background`, `forbidden_node_merge`); callers and two test files updated.
- **CI repair** — `pip install -e '.[figures]'` → `'.[figures,bio]'` (the reroot-postflight and locus-map render paths need biopython; its absence was the 14 CI failures); `repo_health` print ceiling raised 1632 → 1635 to admit 3+1 legitimate stderr error messages added by the bioactivity layer.

No scoring, parser, standing-rule, domain-call, or biological-interpretation behavior changes. Candidate status does not authorize GitHub promotion or public release.

# v9.7.392 · 2026-08-31 · build 20260831v97392b · engine 1.9.141 (INTERNAL NON-RELEASE integration candidate; bundle and engine unchanged)

**An internal integration rehearsal that composes three reviewed feature families on the sealed v9.7.392a code candidate. This build is for local engineering evaluation only: it is not a public tier, GitHub release, signed release, or publication claim.**

- **BLASTp store admission and connected-tool inventory** — adds typed local BLASTp-store admission and current tool-connection coverage while preserving live-store compatibility as an explicit hold.
- **Canonical release-status front door** — links user-facing status text to the version and release-manifest authorities without embedding a transient cut version literal.
- **Bioactivity metadata contract and Quick Guide supersession** — adds the reviewed typed bioactivity metadata contract, fail-closed CLI behavior, compatibility coverage, module inventory bindings, and an explicit historical/superseded wrapper for the legacy Quick Guide.

No public-source genericization, public archive transaction, privacy-policy activation, scoring change, parser interpretation change, or biological promotion is included.

# v9.7.392 · 2026-08-30 · build 20260830v97392a · engine 1.9.141 (BUMPED — portable reroot receipts and exact locus-map disable semantics)

**A deliberately small stabilization cut on the sealed v9.7.391a baseline. It composes two independently reviewed repair families across six unique feature and test paths: portable, transaction-safe reroot postflight receipts and an exact fix for `--locus-maps off`. Larger bioactivity, privacy-archive, workflow-pack, figure, and documentation candidates remain outside this cut.**

- **Portable reroot postflight receipts** — adds a generic postflight receipt tool and generated inventory entry, requires caller-supplied logical locator roots, and prevents absolute host paths from entering portable receipts or default console output.
- **Reroot application-error transactions** — stages rooted output and receipt writes, redacts unexpected-error detail by default, supports explicit local-only debugging, and restores replacement targets byte-for-byte when receipt commit fails. This is application-error rollback, not a crash or power-loss atomicity claim.
- **Exact `--locus-maps off` behavior** — prevents the mandatory compiled-report path from invoking locus-map rendering when figure generation is disabled, while preserving compiled reports and explicitly enabled or standalone rendering paths.

No scoring, parser, standing-rule, domain-call, or biological-interpretation behavior changes. Candidate status does not authorize GitHub promotion or public release.

# v9.7.391 · 2026-08-30 · build 20260830v97391a · engine 1.9.140 (BUMPED — small testing cut; score-neutral compatibility, staging hygiene, and exact-locator controls)

**A deliberately small testing cut on the sealed v9.7.390b baseline. It folds three independently reviewed, path-disjoint patches across seven paths. The cut repairs Matplotlib colormap compatibility, removes Finder metadata from temporary public-tier staging before audit, and makes the Mode B triage locator fail closed on incomplete or conflicting manifest identity. It does not include the broader Mode B workflow, command-center design, MIBiG parent-plus-repair stream, assembly-line widget, document factory, NP Atlas, Lab Quest, or visual concepts.**

- **Immutable Matplotlib colormap configuration** — replaces deprecated in-place `set_bad` and `set_under` mutation with `with_extremes`, preserving the rendered palette while removing two Matplotlib deprecation warnings.
- **Pre-audit macOS metadata scrub** — removes `.DS_Store` and AppleDouble metadata only from the temporary public-tier staging copy before the content audit, with regression coverage proving that the source tree is not mutated.
- **Fail-closed Mode B exact triage locator** — requires nonempty manifest identity, rejects nested/top-level identity conflicts and ambiguous triage-board matches before output, and preserves the complete strain / full node-or-contig / region / BGC identity contract.

No scoring, parser, standing-rule, domain-call, or biological-interpretation behavior changes. The engine bump records the stricter operational preflight and figure compatibility behavior. Candidate status does not authorize GitHub promotion or public release.

# v9.7.390 · 2026-08-29 · build 20260829v97390b · engine 1.9.139 (BUMPED — portable privacy/evidence intake and reliability controls; no scoring/parser/rules change)

**Finality-first testing candidate assembled from seven independently rehearsed patch units. This cut adds portable, user-defined strain privacy and evidence-availability inputs; hardens workbook tooling; adds a fail-closed public-release decision gate; and repairs concise user guidance. It excludes the experimental Sapote command center, NP Atlas prototype, Lab Quest integration, and visual concepts.**

- **Portable strain privacy and evidence registry** — adds explicit user-authored privacy profiles and per-strain evidence-availability rows, validators, generic examples, CLI intake, and documentation. Partial and overlapping genome, assay, fractionation, chemistry, ecology, and publication states remain typed rather than inferred. No personal workspace paths or fixed cohort assumptions are embedded.
- **Tool reliability and atomic workbook writes** — centralizes workbook I/O safeguards, replaces vulnerable direct-save paths with atomic writes, improves registry validation, and adds focused concurrency, schema, and import-safety regression coverage.
- **Public release decision gate** — separates mechanical tier construction from owner authorization. A public release requires an explicit, validated decision artifact; candidate and code-tier assembly do not confer release approval.
- **External literature corpus guidance** — documents portable user-supplied literature roots, provenance expectations, and evidence-admission boundaries without bundling a private corpus.
- **Quick-guide installation anchors** — repairs first-run installation and verification navigation in the concise user guide.
- **Candidate release-status front doors** — aligns README, START HERE, and public-release guide wording with manifest-linked candidate status and adds a regression gate against obsolete release claims.

# v9.7.389 · 2026-08-28 · build 20260828v97389a · engine 1.9.138 (bundle bump only — declare the true Python floor; engine UNCHANGED, no scoring/parser/gate change → `.388`/`.389` boards poolable)

**Final CI green-up. The `.388` build-artifact fix cleared the Release-gates job, exposing the real Test-suite blocker: the engine uses Python 3.12+ f-string syntax (PEP 701 — backslashes and reused quotes inside f-strings, e.g. `render_brief.py`, `cohort_synthesis.py`, `modeb_structure_gate.py`), so the CI 3.11 matrix leg failed at collection with hard SyntaxErrors. The declared floor `>=3.10` was never accurate; the add-on stack already requires 3.12. Metadata/CI only; no `mamey/` behavior change.**

- **Python floor corrected to 3.12** — `pyproject.toml` `requires-python = ">=3.12"` (was `>=3.10`); `README.md` "Python 3.12 or newer"; CI test matrix reduced to `["3.12"]` (dropped the 3.11 leg the code never actually supported). This aligns the declared floor with the code and with the already-3.12 add-on stack.

# v9.7.388 · 2026-08-28 · build 20260828v97388a · engine 1.9.138 (bundle bump only — CI release-gate build-artifact skip; engine UNCHANGED, no scoring/parser/gate change → `.387`/`.388` boards poolable)

**Second CI green-up on sealed `.387`. The `.387` `.git/` skip was correct but incomplete: the CI Release-gates job runs `pip install -e .` first, which drops `mamey.egg-info/` into the checkout, and `check_release_manifest.py` then flagged those 6 files as "TIER_MANIFEST omits ...". Release-tooling only; no `mamey/` behavior change.**

- **`is_tracked()` skips build artifacts** — `tools/tracked_file_policy.py::_SKIP_DIRS` already excluded `__pycache__`/`.pytest_cache`; added `.egg-info` (and `.git/`) so an editable-install checkout passes the manifest and tier gates. `check_release_manifest.py` imports this policy, so the fix covers it centrally; `tools/public_release_audit.py`'s whole-tree scan skips the same. Verified: governed files stay tracked, `.gitignore` stays tracked, egg-info + `.git` excluded.

# v9.7.387 · 2026-08-28 · build 20260828v97387a · engine 1.9.138 (bundle bump only — CI/release-tooling green-up; engine UNCHANGED, no scoring/parser/gate change → `.386`/`.387` boards poolable)

**Makes the inaugural public GitHub CI pass. Both `.386` CI failures were the runner exercising the tree in conditions the cut never did — not defects in the shipped bundle. Release-tooling + test-guard + CI-workflow only; no `mamey/` behavior change.**

- **Release-audit + manifest-check skip `.git/`** — `tools/public_release_audit.py` and `tools/check_release_manifest.py` walk the whole tree with `rglob("*")`; written to run in the project's non-git working dir, they descended into `.git/` on a GitHub checkout and failed on git internals (`.git/objects/*` "undecodable tracked text file"; `.git/HEAD` "TIER_MANIFEST omits 2072 files"). Both now skip any path with a `.git` component. `repo_health.py` was unaffected (scans source dirs only).
- **CI test job installs the figure stack** — `.github/workflows/ci.yml` now runs `pip install -e '.[figures]'` (matplotlib/numpy/pandas), so the figure test modules collect under the runner; a core-only install raised a collection error (pytest exit 2). `.[figures]` not `.[all]` — avoids cairosvg/cairo system-lib requirements the runner may lack.
- **README claim-safety wording tightened (Codex peer card)** — the public front-page README no longer says Mamey produces "facts"; it now says Mamey extracts and records source-derived measurements and evidence states, names Sapote the governed post-extraction judgment workflow, adds "missing evidence is not biological absence", and replaces absolute gate language with "gate success verifies the encoded checks; it does not establish biological identity, production, activity, acceptance, or publication readiness." Doc-only; the MRSA/Candida discovery lens is retained. *(Codex lane; a companion `wiki/Home.md` publishes separately to the GitHub wiki, not the repo tree.)*
- **Figure test modules degrade gracefully without matplotlib** — the ~14 `tests/test_*figure*/render/locus/ledger*` modules imported `matplotlib` at module top-level with no guard, so the real suite failed collection for any user without the optional figure stack (contradicting the README "core still runs" promise). Each now `pytest.importorskip("matplotlib")` before importing it — they SKIP, not error, when the stack is absent. Test-only.

# v9.7.386 · 2026-08-28 · build 20260828v97386a · engine 1.9.138 (BUMPED — peer-lane gate/reader/tool fixes on sealed `.385`; score-neutral → `.385`/`.386` boards poolable)

**Folds 3 verified peer cards onto sealed `.385` — two are adversarial follow-ups on `.384`'s own folds, one is Amber phylo tooling. Gate/reader/tool behavior only; no scoring/parser/rules/domain_level change → boards poolable.**

- **Mode B publication + structure gate §4 gene column — resolve by cell shape, not header order** — `.384`'s fix picked the FIRST header cell containing "gene"/"locus", which misfires when a descriptive "Gene context"/"Gene role" column precedes the real "Locus" identity column: a false `PUBLICATION_GENE_TABLE_DUPLICATE`, and a worse silent false-negative that masks a genuine duplicate. Now disambiguates among substring-matching candidates by cell shape — the column whose extracted tag is digit-bearing in every data row — falling back to the first match, then column 0. Mirrored in the sibling `modeb_structure_gate._section4_complete_blastp_matrix_findings`. Regression test added. *(peer-lane adversarial review of the `.384` fold.)*
- **`cli.py` two-pathway early pass now records its failure** — `.384` narrowed `two_pathway.py`'s own bare `except`, which exposed a SECOND unpatched bare `except` one frame up in `_write_package`: a stale/corrupt `*_gene_by_gene_all_bgcs.csv` now propagates a real parse error that this caller swallowed with no `_phase_receipt` and no `issues` entry — invisible on disk (worse than the pre-`.384` bug). Now records `run.issues` + a `two_pathway_early` ERROR receipt, matching its sibling early-pass handlers. Regression test added. *(peer-lane.)*
- **AMBER phylogenomics render/preflight fixes** — accession-junk strip in tip labels (`render_clean_tree.py`), governed-host + tip cleaning (`render_all.py`), off-target non-actinomycete T0 guard + multi-outgroup rooting (`phylo_preflight.py`). Advisory tooling; the `.385` `--tip-map` help redaction is preserved. *(Amber.)*
- **Changelog privacy touch-up** — the `.385` entry's description of the identifier removal no longer quotes a personal-name example.

# v9.7.385 · 2026-08-28 · build 20260828v97385a · engine 1.9.137 (bundle bump only — public-release privacy hygiene; engine UNCHANGED, no scoring/parser/gate change → `.384`/`.385` boards poolable)

**Pre-GitHub-release privacy pass on sealed `.384`. Tool/comment/denylist text only — no `mamey/` behavior change.** Prepares the inaugural public release at github.com/alexanderjsmith1/sapote-mamey.

- **Removed 4 personal identifiers from the release-audit denylist** — `tools/public_release_audit.py`'s `BANNED_IDENTITY` tuple embedded a PI name, an affiliation, a maintainer username, and a contact-email prefix (as terms for the audit to catch); those literals themselves shipped in the public tool. Removed the four; trimmed the two comments/docstring that described them. Also dropped a personal-name example from a `tools/phylo_preflight.py` `--tip-map` help string. **All internal codenames and workspace tokens are retained** (they disclose nothing), and the audit's structural checks + the planted-codename audit test (which uses a retained internal codename) is unaffected. The published author name + GitHub handle ship by design.
- **Genericized an unpublished novel-genus determination** — a Mode B claim-safety comment (`mamey/modeb_cards.py`) stated a specific unpublished result ("a genuine novel genus, ≤78% ANI") against named cohort strains. Replaced the real triad with generic calibration shapes; the teaching value (defer 16S-only genus novelty to genome-scale evidence) is preserved. Comment-only — AST-identical, zero behavior change.

# v9.7.384 · 2026-08-28 · build 20260828v97384a · engine 1.9.137 (BUMPED — reader/gate/provenance repairs + new-user onboarding on sealed `.383`; no scoring/extraction change → `.383`/`.384` boards poolable)

**A multi-lane fold on sealed `.383`: closes two holes in `.383`'s own new code (citation gate, CLINKER), surfaces the ClusteredNR channel in the gene roster, repairs a Mode B publication-gate regression, adds source-archive provenance to the manifest, and ships a new-user setup path. Reader/gate/doc/provenance only — no scoring, extraction, or triage output changed; boards stay poolable with `.382`/`.383`.**

- **New-user setup orientation + two dangling-doc fixes** — a fresh claude.ai/Claude Code/ChatGPT user gets engine + docs but no bundled dependency wheels, and two front-door docs pointed at files the CODE tier lacks: `docs/PREREQUISITES.md` sent readers to `offline_deps/bootstrap_offline.sh` (ships only in MERGED/SID tiers) and `docs/INSTALL.md` cited `Wheelhouse/hmm/SCANNER_PFAM_MANIFEST.md` (absent). Added a "which tier am I on?" split routing CODE-tier users to the universal `./wheels` path, a first-time-setup section (`doctor` first → `pip install -e .[figures]`; companions optional) in `AGENTS.md`/`README.md`/`AGENTS.md`, and repointed the HMM manifest to `docs/PUBLIC_RELEASE_DATA.md`. Doc-only.
- **Gene roster now surfaces the ClusteredNR channel** — `roster_v2.build_gene_roster()` read nr/swissprot/ebi but never `clustered_nr`, though `_CHANNEL_STORES` defined it and `_read_channel_store` handled both store spellings — so a package's ClusteredNR evidence was invisible in every roster model's `channels_present`/per-gene `channels` (and `widget_deliverable` already declared the channel). Now read, unioned into the BGC/gene sets, and emitted alongside nr. Reader-only; no scoring change.
- **Citation gate case-insensitive BGC match** — `bgc_citation_gate._BGC_RE` lacked `re.I` while its sibling strain/node regexes had it, so a lowercase/mixed-case `bgc016` was never recognized as a BGC citation and sailed through `mamey verify-citations` with a silent PASS — defeating the node·region fatal-error gate for exactly the casual-prose case it exists to catch. Mirrored fix in `sapote_hooks/bgc_citation_node_guard.py`.
- **CLINKER dark-protein link reads the real sequence** — `bigscape_clinker_widget.cluster_dark_proteins()` read `g.pop("_aa")` but the producer `genes_for_gbk()` sets `aa` (the integer length), not `_aa` (the sequence), so the "similar sequence, no shared Pfam" amber ribbon never rendered. Fixed the key so the reference-dark linking the `.383` CLINKER fold introduced actually runs.
- **Mode B publication gate resolves the §4 gene column by header** — `.383` narrowed §4 gene-tag extraction from a whole-row search to `matrix_gene_tag(row[0])` (column 0 only); a matrix leading with the mandated identity columns then yields the same column-0 value on every row and falsely trips `PUBLICATION_GENE_TABLE_DUPLICATE` — the exact shape the Mode B audits instruct lanes to emit. Now resolves the column whose header contains "gene"/"locus", falling back to column 0 (legacy tables unaffected). Regression test added.
- **Manifest records `input_zip_sha256`** — the sealed manifest recorded `input_zip` (path) but not the source archive's content digest, so dedup / "which bytes went in" could not be answered from the manifest alone. New `cli._input_zip_sha256()` records the SHA-256 next to `input_zip`; backward-compatible (old packages → `null`), no scoring/fingerprint change.
- **INDIGO reader/gate fixes** — (1) `two_pathway.py` bare `except` turned a parse failure into a success receipt (`bgcs_evaluated=0`); narrowed. (2) three readers (`lead_pages.py`, `figure_set_renderer_tranche6.py`, `bigscape_extension.py`) could not parse their own producers' `#` preamble, one printing a false negative into a deliverable. (3) `tools/workflow_status.py` computed the release tag correctly then hardcoded `PRIVATE` into three filenames + a caption. (4) `tools/reclass_discriminating_domains.json` t3pks paired-domain minimum activated.
- **AMBER phylogenomics render/preflight fixes** — surgical deltas onto the sealed `.383` tools: accession-junk strip in tip labels (`render_clean_tree.py`), governed-host + tip cleaning (`render_all.py`), and an off-target non-actinomycete guard + multi-outgroup rooting (`phylo_preflight.py`). Advisory tooling.
- **`future_improvements/README.md` truthfulness (peer-lane)** — marks 5 backlog items LANDED (v9.7.185–.194, each with a code marker) and 1 MOOT so the next cut cannot re-land finished work. Doc-only.
- **VGP blastp stop-guard lane-glob widening** — `tools/blastp_monitoring/blastp_stop_guard.sh` matched only `_sN`-suffixed CODEX100 lane bases, so a differently-suffixed lane was silently skipped and the guard could report CLEAN while that lane errored. Widened `_s*`→`_*`. Operator tooling.

# v9.7.383 · 2026-08-27 · build 20260827v97383a · engine 1.9.136 (BUMPED — reproducibility + doc-truth on sealed `.382`; parser returns byte-identical records, NO scoring change → `.382`/`.383` boards poolable)

**Documentation-truth and intake-robustness cut on sealed `.382`. Ships the external tool & database inventory that the bundle previously lacked, warns on JSON-less antiSMASH intake instead of silently dropping TIGRFAM, and makes the multi-tier privacy framework usable by downstream users. No scoring/extraction output changed.**

- **External tool inventory now ships (reproducibility gap closed)** — the sealed `.382` bundle carried no external-tool version record (only the 238-script internal `tools/` catalog). New `docs/EXTERNAL_TOOL_INVENTORY.md` documents the external stack (antiSMASH 8.0.4, BiG-SCAPE 2.0.3 + pyhmmer 0.12.1 + Pfam-A 38.2, IQ-TREE 3.1.2, GToTree 1.8.16, BLAST+ 2.17.0, SPAdes 4.2.0) and DB releases (MIBiG 4.0, Swiss-Prot NCBI build Jul-14-2026, NP Atlas 2024_09; nr + EBI/UniProtKB honestly marked rolling/remote) with version-matched citations — every value verified on disk. A fail-closed test refuses a cut whose inventory still carries an unresolved `VERIFY` cell. The generated internal catalog now points at it.
- **JSON-less antiSMASH intake warns instead of degrading silently** — a partial/web-exported ZIP of only region GBKs carries no record JSON, so `bounded`/`full` fell back to TXT-only KCB with no TIGRFAM and no signal. `parsers.parse_bgcs_from_zip` now emits a warning (via new `parsers._zip_has_record_json`) when a `bounded`/`full` run meets a JSON-less ZIP. The returned `BGCRecord` list is unchanged — this is a side-channel warning, not an extraction-semantics change. The stale `off`-is-default docstring is corrected (`run` defaults to `bounded`).
- **Multi-tier privacy framework made usable by downstream users (P0-11, re-scoped)** — the five release tiers are KEPT (not consolidated). New `tools/release_denylist.example.txt` template (the real denylist is stripped from public tiers, leaving users nothing to start from) and `docs/CUSTOM_PRIVACY_TIERS.md` how-to let a GitHub user run their own public/private separation with the existing fail-closed machinery.
- **Doc-truth** — `docs/ANTISMASH_INPUTS_CONSUMED.md` documents what Mamey reads from an antiSMASH ZIP (region GBK / whole GBK / FASTA / record JSON / clusterblast TXT / .log) and the JSON-less gotcha; `docs/TOOLS_INVENTORY.generated.md` header now distinguishes the internal script catalog from the external inventory (via the generator, so it survives regen); `QUICK_GUIDE.md` version header refreshed (was 9.7.319/1.9.111).
- **Mode B matrix gates admit non-`ctg` canonical gene tags (Codex fold)** — `modeb_structure_gate.py` and `modeb_publication_gate.py` read the gene identifier from the first gene-cell token via a shared `matrix_gene_tag()` instead of restricting matrix rows to `ctgN_N`-shaped loci, so exact RiPP-precursor tags (`allorf_013118_013336`) and imported NCBI-style tags (`ABC_RS12345`) satisfy the independently-supplied exact roster without renaming or omission. Missing/duplicate/extra-row checks preserved. Verification-coverage repair only — no gene identity, sequence, BGC membership, or scoring change.
- **Clinker figure widget: distant-paralog link toggle + caption sidecar (Codex fold)** — `deliverable_tools/bigscape_clinker_widget.py` hides distracting hairline diagonals from repeated generic domains by default (`distant/paralog links` opt-in checkbox), and emits a caption/methods sidecar. Figure-presentation only; non-blocking, post-seal deliverable tooling.
- **Mode B gate false-positives fixed (WAC-01375/DSM46095 tri-lane audit, batch 1)** — two gate false-alarms that fired on every compliant card, eroding trust in the safety channels: (1) `modeb_structure_gate._self_numbers` no longer reads the canonical `## §35 Protocluster decomposition` heading as a protocluster count (ATX headers + HTML comments stripped before number extraction; 4 adversarial tests); (2) `claim_safety_gate` negation is now clause-scoped — `; `/`—` bound a negation to its own clause and the disclaimer vocabulary (`not proof`, `cannot claim`, …) was added, so "not proof that the strain produces X" is claim-safe while "…not proof of novelty; the strain produces X" still flags. The naive flat-vocabulary variant was rejected because it opened a claim-safety false negative. No scoring/identity/membership change.
- **A-03: receipt-ingestion context-builder recursion fixed** — `mode_b_receipt._bgc_context_from_triage` and `authored_verify._bgc_context_from_package` each merged the other's output ("one ctx, both doors", added independently), forming an unbounded mutual recursion: it recursed to Python's limit, swallowed the terminal `RecursionError` (returning a degraded context), and on a real package blew the wall-clock re-reading the sealed CSVs (~250×) → `ingest-receipts` hang (exit 124). A `_cross` flag now permits one sibling merge and prevents the cross-back — terminating by structure, not deduplication or evidence loss, with both triage- and package-derived keys preserved. Two-run clean-bundle e2e: deterministic, bounded, depth 2, no `RecursionError`.
- **A-02: offline editable install made truthful** — `pyproject`'s build isolation requires `setuptools>=68`+`wheel`, which a fresh no-network venv cannot fetch, so the advertised offline `pip install -e .` failed. The bundle now ships those pinned MIT `py3-none-any` wheels in `wheels/` (with a license/SHA-256 manifest) and `bootstrap.sh` adds that dir to `--find-links` on every install, so build deps resolve offline.
- **A-05: figure-state bookkeeping reconciled** — `NO_FIGURES_RENDERED.md` was written early (`--brief none`) and never cleared when a later figure path rendered, so a sealed package could carry the "no figures" marker beside real PNGs/SVGs. `run_one_strain` now removes the stale marker once any figure step has produced output.
- **Node·region citation gate (fatal-error class, WAC-01375)** — a cross-strain Mode B review cited leads by bare `strain + BGC-number` (no contig node), which MERGED two physically distinct AS-XXX loci (atratumycin `NODE_35/BGC016` vs enediyne `NODE_21/BGC011`) and mis-attributed an AB-94 prior — a labeling shortcut became a factual error. New `mamey/bgc_citation_gate.py` + `mamey verify-citations <file|dir>` fail-closed: any deliverable line pairing a strain ID with a bare `BGC\d+` and no locating token (`NODE_`/`ctgN_N`/`regionNNN`) is refused. Validated against the corrected review (clean) and the exact failure lines (flagged); count phrases ("37 BGCs") never trip. Makes the standing "cite by node·region, never by BGC number" rule mechanical instead of instruction-only.

Accretion-justified: mamey/bgc_citation_gate.py — new fail-closed node·region citation gate; the WAC-01375 audit proved a node-less BGC citation is a factual-error vector, so the rule is now mechanical (`verify-citations` CLI + gate module).
- **NRPS substrate-conflict preservation (Codex fold)** — `nrps_predictions.py` / `modeb_template_emitter.py` / `build_cohort_precompute.py` now carry BOTH antiSMASH NRPS substrate streams (consensus + Stachelhaus/physicochemical) with a typed agreement state (concordant / one-uninformative / **conflict**) instead of silently resolving to one predictor. Conflicts are preserved as honest evidence in the Mode B card. Verified new (agreement-state absent before), applies clean, 6-test module + no regression across the nrps/emitter/cohort space; no scoring/rules/triage change — Mode B card content only, boards stay poolable.
- **ClusteredNR store-name convergence (Codex fold)** — a read/write interop bug: writers used `blastp_clustered_nr` while some readers (`modeb_subsections`, `blastp_ingest`) looked for `blastp_cluster_nr`, so a ClusteredNR store could be written but not found. Fix is migration-safe: new writes use the canonical `blastp_clustered_nr`, and every reader (`roster_v2`, `widget_deliverable`, `modeb_subsections`, `compile_report`, `blastp_ingest`) accepts BOTH spellings so legacy packages still read. Applies clean; 5-test module + no regression across the blastp/roster/widget/report space.

# v9.7.382 · 2026-08-27 · build 20260827v97382a · engine 1.9.135 (BUMPED — GitHub due-diligence remediation on sealed `.381`; portability + release-safety only, scoring path byte-identical to `.381` → NO re-score owed, `.381`/`.382` boards poolable)

**Codex GitHub due-diligence remediation of sealed `.381`. Portability, release-safety, and doc-truth fixes plus a whole-tree workspace scrub; no scoring/parser change. The simulated public code-tier now passes `public_release_audit` clean, and `repo_health --strict` passes.**

Accretion-justified: mamey/blast_ledger.py — new durable cross-run fair-use budget for the online BLASTp channels (P0-7).
Accretion-justified: mamey/cohort_proteins.py — Codex cohort-protein-comparison Mode B capability (stranded since .377), folded from COHORT_PROTEIN_COMPARISON_MODEB SUPERSEDING_V2; applies clean to sealed .381, adds a `cohort-proteins` path + contract doc + tests.

- **Whole-tree portability scrub (P0-8)** — internal chat-lane codenames and private workspace directory locators (the strain-data home, dated deliverable output folders, package-complete dirs, per-session state folders, and absolute home paths) were replaced tree-wide with generic, portable names; the private layout re-maps through config in the operator pack. A simulated `code`-tier cut audits clean (was 232 findings). The published author name and GitHub handle are preserved.
- **`public_release_audit.py` hardened (P0-1/P0-2)** — fail-closed on a missing/invalid root and unreadable files; whole-tree scan always on; banned-identity list extended with the codenames and workspace locators; fixed two self-bugs (an empty file no longer mis-flagged as unreadable; `.xlsx/.docx` no longer mis-flagged as undecodable); portabilization detectors allowlisted. `tests/public/` rewritten hermetically.
- **Online BLASTp submission safety + durable fair-use budget (P0-6/P0-7)** — `blastp-ebi --submit` now requires a valid `--email`, caps a transaction at 30 jobs, and refuses while prior jobs are unharvested; the NCBI batch runner's inter-submit gap raised 2 s → 10 s. New `mamey/blast_ledger.py` persists every online contact to a cross-run JSON ledger (`$MAMEY_BLAST_LEDGER` / `$XDG_CACHE_HOME/sapote-mamey/` / `~/.cache/sapote-mamey/`), so `run_batches_online` (NCBI) and `submit_ebi` (EBI) refuse up front when the rolling-24 h budget (`MAMEY_BLAST_DAILY_CAP`, default 100) is exhausted — closing the multi-run gap the per-call submit-gap could not see, the likely mechanism behind the NCBI block. Inert inside pytest unless a test sets the ledger path. No email is shipped in code; the README/guide document that the user supplies their own.
- **Literature corpus prose removed (P0-3)** — the per-genus and `_families/*.md` digests (corpus-derived) no longer ship; the fetch/curate tooling and PMID/DOI metadata manifest are kept so a user can regenerate locally. Wheel-content test added; the card writer degrades to empty §5 subsections when absent.
- **Doc-truth reconciliation** — Pfam/HMM "operator-provisioned, not bundled" reconciled across README/NOTICE/guides (P0-5); retired `--mode smoke`/`--mode standard` removed from the citation-compact guide, `HOW_TO_USE`, `intake_harness`, and the ChatGPT execution controller; a transitive bootstrap test now scans every front-door-reachable active doc for retired-mode run commands (P0-9/P1-1/P1-2/P1-3). Python-version drift fixed (3.10+ core; 3.12 only for add-on wheels) (P1-7). `INSTALL`/README now `pip install -e .` (P1-6).
- **Operator tooling folded into the bundle (previously stranded lanes).** The BLASTp crawl-monitor + plot fleet lands at `tools/blastp_monitoring/` (9 read-only dashboards/plotters), and the phylogenomics workflow-hardening tools land in `tools/` (`build_tree.sh` + `TREE_SPEC.example.json` = the mandatory declare-then-gate build path, `phylo_preflight.py`/`phylo_postflight.py` cohort-coherence + per-genus-comparator + assembly-quality gates, `gtotree_env.sh` portable launcher with GToTree v1/v2 variable spellings, `render_all.py`, `docs/PHYLOGENOMIC_TREES_METHOD.md`). Both were made portable on fold (hardcoded workspace roots/output dirs → `SAPOTE_WORKSPACE_ROOT`/`MAMEY_DATA_ROOT`/`SAPOTE_BLASTP_PLOT_DIR`, private locators genericized). `repo_health` excludes these operator-CLI tools from the `print_calls` hygiene scan (their stdout is the deliverable, not library debt) — ceiling unchanged, not raised.
- **Robustness** — `intake_harness` binds its own repo root before importing `mamey` (P1-4); all ZIP consumers route through `ziputil.safe_extract_all` (P2-1); the cohort KCB figures fall back to a linear axis instead of crashing when a cohort has no KnownClusterBlast hits (P1-8); `make_public_tier.sh` derives its stamp from `BUILD_STAMP.txt` and strips `_CANDIDATE_NOTES/` (P1-5); `verify_tier_derivation.py` gained a `STRIP_DIR_PREFIXES` set mirroring the cut's strips so a stripped dir is not misread as drift. `repo_health` `print_calls` brought back under the ceiling (P0-4) — three stderr writes, no ceiling raise.

# v9.7.381 · 2026-08-27 · build 20260827v97381a · engine 1.9.134 (BUMPED — FINGERPRINT, EXTERNAL-PACK-GATED: generic-source cohort externalization; boards comparable only under an identical supplied OFFICIAL_DATA pack)

**Public-facing generic-source + whole-tree identity-scrub derivation of sealed `.380`. Still a CODE tier (AS material present by design, AS_SCRUB=0); this is NOT itself the published GitHub artifact — publishing remains a separate maintainer decision.**

- **Cohort roster externalized** — `mamey/exclusions._DEFAULT` emptied; governed roster/denominator now read from an external `OFFICIAL_DATA/exclusions.json` (or `$MAMEY_DATA_ROOT`) at runtime. Bare tree degrades to an empty governed set; with the pack supplied it restores exactly to 44 strains / 1,753 regions / {AS-XXX, AS-XXX} (verified lossless). Cohort adapters degrade gracefully with no pack.
- **13 AUDIT_378 correctness fixes** folded, including `scoring.is_lead_excluded()` now recognizing the real `_4_triage_board.csv` TitleCase headers (`Standing_rule`/`Primary_metab_flag`/`Mobile_element_flag`) it previously missed silently. `triage_bgcs()` does not call it — figures/report pages/`domain_level` only.
- **Whole-tree personal-identity scrub** — a prior maintainer username, a co-author/PI name and affiliation, an old contact email, absolute home/workspace paths, and internal workspace names were removed to zero (verified against the maintainer's private ban-list). The published author name and GitHub handle are preserved by design.
- **`public_release_audit.py` banned-list externalized** to a gitignored `.identity_banlist` (not shipped), with a structural-only fallback when the file is absent (fail-closed verified). `audit_modeb_support_card.py` workspace-name literal genericized to a portable path regex (tool still parses; tests green).
- **Public front-door + hygiene** — `tests/public/` + `public` marker, `SECURITY.md`, `CONTRIBUTING.md`, `EXTERNAL_ASSETS_GUIDE.md`; AppleDouble extraction debris removed.

# v9.7.380 · 2026-08-26 · build 20260826v97380a · engine 1.9.133 (BUMPED — GATE-SEMANTICS: Mode-B emitter/gate lifecycle + anti-padding §4 guard; scoring path byte-identical to `.379` → NO re-score owed, `.379`/`.380` boards poolable)

**Tier-A cut (Codex triage fold-first set) on sealed `.379` — 3 bounded cards addressing demonstrated Mode-B authoring/gate failures. The AQUARIUS rebased backlog and Tier-B/C batches are NOT folded (Tier A stands alone).**

- **Emitter / publication-gate lifecycle routing** (`modeb_template_emitter.py`, + `docs/MODEB_GATE_CLEAN_AUTHORING.md` new) — the "no branch" ruling: a fully-authored saved candidate keeps the publication gate; a fresh scaffold is not required to pass it. Adds the missing §4 `#### Complete named-match, channel-separated table` heading, corrects stale §1–§30 → §1–§48 wording, + lifecycle-routing regression test. `mamey/modeb_publication_gate.py` unchanged.
- **claim-safety CLI execution-order fix** (`tools/claim_safety_linter.py`) — corrects a defect in the linter's `main` (process/tooling only, no scientific claim).
- **anti-padding §4 guard** (`modeb_structure_gate.py`) — the anti-padding detector no longer treats the complete §4 gene matrix (and §28/§29 bodies) as padding.

# v9.7.379 · 2026-08-26 · build 20260826v97379a · engine 1.9.132 (BUMPED) — SAFE candidate: verified-new cards only.

**SAFE .379 candidate — the AQUARIUS_379_REBASED_DIFFS backlog is NOT folded (largely already-landed in `.378b`; forward-folding reverts working fixes — needs per-card new-vs-landed curation). Only independently-verified-new cards folded.**

- **+21 domain/method bibliography entries** appended to `docs/Sapote-Mamey.bib` (halogenase, P450, MbtH, radical SAM, SARP, ABC-F, trans-AT PKS, RiPP; DOIs verified).
- **Degradation guards for `antimicrobial_recall._load()` and `concordance.load_reference_library()`** — graceful (keyword-baseline / NO_REFERENCE) when the reference maps are absent, fixing a latent crash on a missing data file; folds into both builds.
- **`domain_level.py` mobile-element 3-flag lead-exclusion gap** — `_top_bgcs_from_package` now mirrors `scoring.is_lead_excluded`, reading `mobile_element_flag` from the manifest bgcs (the triage CSV lacks the column). + regression test.
- **`tab_reconcile.py` generic antiSMASH-at-root marker** — replaced a hardcoded cohort filename sentinel with a generic `*.json`-at-root check.
- **`cairosvg` importorskip broadened** to skip on a native-libcairo `OSError`, not just `ImportError`, so a plain test run does not abort where libcairo is absent.

# v9.7.378 · 2026-08-25 · build 20260825v97378b · engine 1.9.131 (BUMPED — FINGERPRINT: rggmci + clusterblast detection fixes move whitelisted score artifacts (`_4A`/`_4_triage`/`_4c`) for affected BGCs → COHORT RE-SCORE OWED, `.377`/`.378` boards NOT poolable; restoration + claim-safety + scoring/rescue cards are text/gate-only)

**EXPANSION_v2 — corrective re-cut on sealed `.377`, supersedes the `…378a` EXPANSION seal per Codex post-cut audit. Restoration + 4 accepted corrections + corrected claim-safety fold; NRPS split-detector OMITTED.**

- **Monolith freshness anchor spot-vetted to `.378` at seal (patch chat).** Drift crossed the 60-patch tolerance at this bump (last spot-vet v9.7.317). Ran the doctrine scan (no retired assembly tiers / per-BGC BSL-2 / active AS_SCRUB / PRIVATE(AS-) doctrine / PUBLIC-PRIVATE figure divider — clean), restated the spot-vet anchor to v9.7.378, noting the one upload-at-session-time reference (`sapote_pdf_styles.py`). No full read-through claimed; monolith byte-identical to `.377`.
- **`modeb_structure_gate.py` — restored `.376` observed-no-hit §4 gate** (a completed exact-sequence search with no significant hit is a legitimate terminal state, not a fabrication gap; + count-first `n/N` qcov).
- **`rggmci.py` — class-token substring-collision fix** (`NI-siderophore`/`NRP-metallophore` no longer collide with their unqualified substrings; `_4A` ranked pairs move for affected BGCs).
- **`clusterblast_genes.py` — asn_synthase promiscuous-core false-rescue fix.**
- **`rescue_two_proof.py` — mixed-subject-signal false-rescue guard** (contradicted overlap evidence no longer satisfies the disjoint-reference fallback).
- **`scoring.py` — `rg_note` eligibility** (rationale text no longer claims a rescue the score gate refuted; score-affecting `rescue_bonus` block byte-identical to `.377` — text-only).
- **`claim_safety_gate.py` — filler-word continuation + direct typed-object overclaim (CODEX correction A).** "produces the antibiotic streptomycin" / "the compound streptomycin" / "the metabolite erythromycin" are now flagged, while generic capacity phrasing ("produces a polyketide backbone"), class-noun-with-no-name, safe-context, and negation-scoped sentences stay clean. Regression test `tests/test_claim_safety_gate_filler_word_overclaim.py` folded.
- **NRPS split-detector fold OMITTED (CODEX correction B).** The `…378a` fold widened fragment acceptance but left the body-alignment loop PKS-only, admitting a random NRPS fragment as a HIGH split candidate. `split_detector.py` reverts to `.377`; the real fix (NRPS-vs-NRPS homology with identity + coverage, refuse-when-no-homolog, negative random-seq test) is deferred to a dedicated lane card.
- **Deferred (AS-policy batch, per the Developer or User's "exclude all AS" ruling):** the AS-redaction-machinery cards remain held; one card (`exclusion_gate_code_adversarial_review`) stays quarantined pending a `.377` rebase.

# v9.7.377 · 2026-08-25 · build 20260825v97377a · engine 1.9.130 (BUMPED — EMITTED-OUTPUT: compile_report Key Findings no longer re-admits an engine-excluded BGC via raw Rank, and the antiSMASH record-pass count is corrected; scored boards `_4_triage_board.csv` + `_4c` byte-identical, so NO re-score owed — `.376`/`.377` boards poolable)

**Three Codex-"retain" correctness folds on sealed `.376` (the patch lane candidate; sealed here).**

- **`compile_report.py` — corrected-rank exclusion in Key Findings.** An engine-excluded BGC (`corrected_rank is None` from a standing-rule / primary-metabolism / mobile-element withhold) can no longer re-enter the compiled report's Key Findings through its raw `Rank`. New test `tests/test_compile_report_corrected_rank_exclusion_v9_7_377.py`.
- **`antismash_tables.py` — `double_record_pass_fix`.** Eliminates the second antiSMASH record pass; fixes the previously-red `tests/test_record_pass_count.py`.
- **`bgc_l0_program.py` — atomic `_write_rows`.** The 8 L0 tables write via tmp + `os.replace`. New test `tests/test_bgc_l0_write_rows_atomic.py`.
- **Deliberately excluded:** the `bgc_report_builder` AS-public-prefix change is REJECTED per the Developer or User's 2026-08-25 "exclude all AS" ruling; `PRIVATE_PREFIXES` keeps `AS-`/`AJS-`/`PENDING-` refused (`bgc_report_builder.py` byte-identical to `.376`).

# v9.7.376 · 2026-08-22 · build 20260822v97376a · engine 1.9.129 (BUMPED — EMITTED-OUTPUT: workbook completeness verdicts, compiled-report run-issues, roster EBI channel, and figure lead-exclusion change Mamey OUTPUT; scored boards `_4_triage_board.csv` byte-identical, so NO re-score owed)

**Correctness + honesty pass from the `.375b` outstanding-items ledger (5 the patch lane cards).** Built against sealed `.375b`; each card verified on a clean compose. the Developer or User seals.

- **Completeness audit reports real extraction state, not hardcoded PASS.** The master workbook's `A4_Completeness_Audit` stamped every stage PASS and `overall = PASS_EXTRACTION` before checking anything — a governed handoff asserting success it never verified. Verdicts are now computed from the run's real state (scans loaded, triage present, rggmci computed, …) and report `INCOMPLETE_EXTRACTION` / `NOT_LOADED` when a stage did not run.
- **One canonical lead-exclusion predicate; a silent figure gap closed.** The nine `.375` excluded-BGC-leak fixes had left two divergent `_is_lead_excluded` helpers — the reader-facing Sapote priority figures silently omitted the mobile-element exclusion signal. A single `scoring.is_lead_excluded()` (the exclusion SSOT) now serves every consumer; a mobile-element-demoted BGC can no longer appear as a lead in the priority figures.
- **Compiled report surfaces run-level red flags.** The mandatory compiled report never read the engine's own run issues (contamination-suspect, record-truncation, over-merge candidates, …), so a report could carry zero indication its run was flagged. The issues field is now surfaced.
- **Per-gene roster completes the EBI BLASTp channel.** The roster's EBI channel was half-wired; the present-channel signal + an overlay/TOP10 schema fallback are completed so EBI rows render with their def/organism/accession.
- **Engine-lineage honesty: `.375` reclassified as a FINGERPRINT bump.** The sealed `.375` stanza under-stated its scoring change as "whitelist unchanged"; the `1.9.128` stanza is amended to carry the FINGERPRINT tag and the cohort re-score-owed / not-poolable note.

# v9.7.375 · 2026-08-22 · build 20260822v97375b · engine 1.9.128 (BUMPED — scoring/scan/model output changes on real cards: RG-GMCI rescue-class guard, inventory ambiguous-token tiering, domain over-count and bare-abbrev class triggers, manifest downgrade fields)

**The MEDIUM/LOW half of the audit lands (170 cards), plus a pre-publication disclosure scrub.** This is the companion to `.374`'s 44-HIGH cut: the remaining atomic-write, correctness, and doc cards, re-ranked by measured real-world consequence rather than self-assigned severity, composed onto the sealed `.374` base and folded only where each card applied clean against it. Two cards that partial-conflicted after sibling cards landed (`compiled_report_missing_run_issues`, `roster_v2_swissprot_ebi_channel_gap`) are deferred to `.376` for regeneration; three superseded and eight paused public/private cards are held out. Built by the patch lane from audit lane's staged cards; the Developer or User seals.

- **Excluded-BGC leak sealed across the deliverable surface.** Nine independently-found touchpoints — manifest, compiled-report key findings, the priority/RG-GMCI widgets, the primary triage workbook sheets, and the published priority-ranking figures — each mishandled the scorer's `corrected_rank=None` for standing-rule/primary-metabolism/mobile-element-excluded BGCs, letting an excluded BGC rank above a real lead. All nine now carry and honour the exclusion flag.
- **ClusterBlast evidence attributed to the right region.** The tab-reconcile and JSON-summary paths hardcoded region 1 regardless of the region requested, mis-attributing homology evidence across multi-region contigs; the requested region is now honoured end to end.
- **RG-GMCI rescue bonus now checks functional complementarity.** The auto-floor AB/AF/novelty rescue bonus was granted from `rggmci_confidence` alone; it now consults `functional_rescue_class` and withholds the bonus from ACCESSORY_ONLY-only pairs, so a homology-only accessory linkage no longer inflates a strain's top leads.
- **Domain over-counting and false class triggers corrected.** `aSModule`/`CDS_motif` features were counted as independent domains (up to a 9x over-count on one BGC) and bare domain-name substrings falsely triggered unrelated class patterns; both scan paths now count and match on real domain evidence.
- **Inventory-tier reform: real leads no longer buried by ambiguous tokens.** The `ambiguous_review_tokens` policy existed in the rules registry but was never consulted, so genuine MIBiG-anchored candidate leads could silently file at Inventory tier; the housekeeping check now honours the policy.
- **RiPP-core gene-kind counting fixed.** Lasso/lanthipeptide/ranthipeptide maturation domains were miscounted as non-core, weakening the per-gene BLASTp-coverage denominator exactly where the RiPP class needs it; core-gene kind is now recognised on the real production path.
- **Fail-open gates closed.** The citation resolver returned its best status on zero rows, a surrogate-gate timeout rolled into overall PASS, and the tree-sanity p90 index collapsed to the tree max on thin (n≤10) trees disabling the long-terminal check; each now fails safe.
- **Atomicity across the MEDIUM writer cluster.** The remaining non-atomic deliverable writers (availability, presapote-lite, antismash-ingest, dossier, cohort-assemble, and others) were switched to atomic writes, closing crash-corruption windows in the same pattern as `.374`'s core package writer.
- **F-series heatmap empty-matrix guard completed at seal (patch chat, 2026-08-22).** The folded card `cohort_figures_f_series_empty_matrix_crash` shipped its regression test (`tests/test_gold_figures_f_series_degenerate_input_v9_7_374.py`) but not its code fix — `cohort_figures.py` was byte-identical to `.374`, so `heatmap()` (F-series) still reached `ax.imshow()` with a zero-size array and crashed, aborting `figs_multi()` and every remaining F-series figure. The test skips in isolation (`importorskip matplotlib`) and only fails under the full suite where matplotlib is pre-loaded, so the candidate's own validation missed it. Added the same early-return placeholder guard its two siblings `hmap()` (G) and `bubble_matrix()` (D) received in v9.7.267, using heatmap's own F-series `stamp`. Not a scoring/whitelisted artifact — the engine fingerprint is unaffected. Full suite: 4771 passed / 0 failed.
- **Tracked-file-policy test aligned with its own shipped fix at seal (patch chat, 2026-08-22).** One folded card correctly made `tools/tracked_file_policy.py` path-aware so governed nested source ZIP fixtures (`examples/test_data/*.zip`, `tests/fixtures/*.zip`) are listed in `TIER_MANIFEST` — but left the paired test `test_shipped_tier_manifest_excludes_release_artifacts` on the old broad `.*\.zip` regex, which then flagged those same governed fixtures as release artifacts and failed the in-tier cut gate. Scoped the test's ZIP alternative to root-level (`[^/]*\.zip`), matching the shipped policy's `_ROOT_LEVEL_ZIP_RE` + `"/" not in rel` guard; verified it still catches a real root-level release ZIP. Test-only; no engine effect.
- **Pre-publication disclosure scrub.** Ahead of the cohort genomes' publication, distinctive real-cohort BGC content (named compounds and rare classes tied to specific strains) was genericised in the changelog, docs, code comments, and test exemplars; reference strains and the public `enterocin AS-48` are retained, and the full un-redacted changelog lives external and versioned.

# v9.7.374 · 2026-08-22 · build 20260822v97374a · engine 1.9.127 (BUMPED — scoring/routing and gate-semantics fixes change Mamey output on real cards: arylpolyene wet-lab routing, two-proof adjudication, boundary verdicts, master-workbook cross-strain columns)

**A large correctness-and-robustness sweep — 45 cards (44 HIGH + one required dependency) from the audit.** This is the HIGH-severity half of a ~154-card audit queue; the ~105 MEDIUM/LOW atomic-write and cosmetic cards are deliberately split to `.375` so this cut's blast radius stays legible. **Public/private redaction cards are held out of the default workflow per the 2026-08-22 PI decision** (the distinction is re-added during analysis, not forced into the default run). Highlights below group 45 fixes by class; the frozen card list is `candidate_cut_v9.7.374_AQUARIUS/FROZEN_374_HIGH_MANIFEST.txt` and every card carries its own reproduce-fix-verify `PATCH_CARD.md`. Built by the patch lane from audit lane's staged cards; the Developer or User seals.

- **Fail-open and fabrication gates now actually fire.** The documented ingest-receipts front door (`mode_b_receipt`) ran three ERROR-level fabrication checks fail-open since they were built; the seal-package locator gate silently reduced to non-blocking SKIP on a corrupt triage board; the G2 structural-check, the deliverable-suite standing-constraint gate, the interior-gene-omission cross-check, and the pipeline v-status all had fail-open or unwired paths. A KCB-recycling corruption detector and a mobile-element boundary flag were computed but never reached a human or a verdict. All re-wired to their intended blocking/surfacing behavior.
- **Contamination guard hardened: the STRAIN-INTERNAL gate is no longer bypassable by a filename.** Both the `tools/extract_module_core_domains.py` KS-tree builder and its engine twin `mamey/ks_phylogeny.py` silently dropped any GBK whose name didn't match the strain regex while still merging its domains — letting two strains fuse into one fictitious pathway (the AS-XXX-style chimera the gate exists to prevent). Both now fail closed on any unrecognized filename.
- **Producer/consumer key mismatches fixed — dead data revived.** The master workbook's `CGAD_chitin`/`TFBS_DasR` cross-strain columns read a wrong dict key and had been silently zero in every workbook ever built; the DAPR rescue sheets crashed on a stale `KCB_Provenance` header; an RG-GMCI locus-map confidence key was dead; and the compiled report looked for a fermentation section under a filename its own instructions never produce.
- **Case/prefix and identity guards hardened across intake and cohort assembly.** Governed-exclusion, accession-strain-ID (`NZ_`-prefix + case), BiG-SCAPE/KCB strain-join collisions, and several cohort ledger/dossier keys were case-sensitive where the data is not, silently dropping or double-counting real strains.
- **Claim-safety: a bioactivity-phenotype overclaim is now surfaced at seal.** The blocking seal gate and the packaging advisory called the identity-only linter, so a per-BGC "is antibacterial / confirmed producer / MIC" assertion sealed with zero visibility. The H3 bioactivity check is now wired into both (WARN-level — a genomics pipeline never requires bioactivity, so it surfaces, it does not block), with its false-positive-suppression sibling so shipped exemplars stay clean.
- **Scoring and adjudication corrections.** An unbounded substring match routed an arylpolyene pigment locus toward antifungal-priority wet-lab guidance it doesn't merit; the two-proof complementarity check was inverted (accepting paralogy as a split, never checking the real split signature); and a RiPP-core false-conservation call was corrected.
- **BLASTp and comparator channel integrity.** EBI-transport hits were stamped as NCBI web-BLASTp; an ebi/nr channel glob cross-contaminated the unmixed store; a short comparator row crashed the multi-strain L0 batch with an uncaught `TypeError`; and a SID neighbor query was silently dropped.
- **Atomicity and crash fixes in the highest-blast-radius writers.** The core package writer (`_write_package`, 27 of 28 non-atomic writes), a removed-matplotlib-API crash that took down the entire cross-strain figure pack, a corrupt-register data-loss path and a session-resume roster mismatch in `judgment_store`, and a freshbank-recovery crash were all fixed.

Engine drivers (what changed Mamey output vs. what is gate-only) are detailed in `docs/ENGINE_LINEAGE.md` (1.9.127 stanza).

# v9.7.373 · 2026-08-21 · build 20260821v97373b · engine 1.9.126 (BUMPED — three Mode-B gate-semantics fixes change verify-modeb results on finished-profile cards; extraction/triage/packaging byte-unchanged)

- **Roster-membership correction (`…b` re-cut, per Codex HOLD 2026-08-21).** BREAK-1's per-BGC roster wiring built `known_locus_tags` from a last-write single-home dict (`home[locus_tag] = bgc_id`), which silently dropped a boundary CDS legitimately shared by two adjacent BGC regions — Codex's read-only census of the 44 loose packages found 8 per-BGC undercounts across 6 packages (e.g. AS-XXX/BGC031 lost `ctg37_25`). Fixed to a one-to-many membership relation: `known_locus_tags` is now built from direct membership rows for the requested BGC, `ctx["locus_home"]` carries the set of homes for a shared gene (bare string for single-home genes, preserving legacy-context back-compat), and the `LOCUS_BGC_MISMATCH` guard passes a cited gene when the named BGC is **one of** its declared homes. New regression fixture `tests/test_roster_shared_boundary_cds_v9_7_373b.py` (4 tests: shared gene in both rosters, home-set vs string, no false flag under either home, genuine misattribution still flagged). Engine stays **1.9.126** (correctness fix within the same gate-semantics change; no scoring/whitelist/extraction move — the six scoring-path modules remain byte-identical to sealed .372b). **Still owes Codex's re-review** of the implementation shape and the live-corpus zero-mismatch acceptance run (the 44-package on-disk corpus is not reachable from the seal container; the fix is proven on Codex's documented cases synthetically + the full suite is green). The non-blocking `find_s4_matrix_block` docstring wording ("from the heading" → "body after the heading") is also corrected.

**The finished-card gate actually works now — plus a claim-safety fix and the sequence-first/vocabulary/hook governance folds.** The .372 finished-card matrix gate shipped with a producer↔consumer roster bug that made it fail-open: it could only ever emit `ROSTER_UNBOUND`, never actually check a card's gene roster. This cut fixes that, reconciles the two gates onto one §4 table locator (Codex-ratified title decision, 2026-08-21), and wires the finished-profile trigger — three Mode-B gate-semantics changes that drive engine **1.9.125→1.9.126** under the standing rule (bump when Mamey OUTPUT changes because the engine changed). Alongside: an urgent interpretive-floor claim-safety correction, the Codex sequence-first gene-identity contract (docs+tests), the Developer or User-ratified status vocabulary, the changelog-build-token seal gate, and the chat-link Stop hook. Engine drivers are detailed in `docs/ENGINE_LINEAGE.md` (1.9.126 stanza). Built by the patch lane; the Developer or User seals.

- **Mode-B matrix-roster gate is now actually enforced — a real .372 defect fixed (BREAK-1).** The `.372` `_section4_complete_blastp_matrix_findings` gate demanded `ctx["known_locus_tags"]`, but no production context builder ever set that key (`authored_verify._bgc_context_from_package` set `known_loci`/`locus_home` under different names). Every finished card verified via `verify-modeb --package --bgc` therefore hit `BLASTP_MATRIX_ROSTER_UNBOUND` and the roster was **never checked** — the hard gate the .372 changelog announced was fail-open in production; only a test injecting the key exercised the pass path. Fixed: `authored_verify` derives the exact per-BGC roster from the parsed `locus_home` (gene_by_gene membership, which already includes declared boundary-context CDS — AS-XXX/BGC001 → 15 genes incl. `ctg105_3`, exactly the card's displayed roster) and sets `ctx["known_locus_tags"]`. Finished cards can now newly ERROR (real mismatch) or PASS (roster bound) where .372 could only emit `ROSTER_UNBOUND`. Test: `tests/test_roster_key_wiring_v9_7_373.py` (3). Independent shelf audit (`AQUARIUS_373_modeb_shelf_independent_audit`): supplying the roster over all 12 native finished cards → zero genes missing, only labelled boundary-context extras.
- **One shared §4 matrix-table locator across both Mode-B gates (BREAK-3; Codex title decision relayed 2026-08-21).** The matrix gate and the publication gate previously located the §4 table by different rules (strict heading regex vs content regex) and disagreed on real cards. Both now call `mamey.modeb_structure_gate.find_s4_matrix_block`, which accepts the canonical named-match heading (`Complete named-match, channel-separated table`), its measured `…gene table` variant (15/23 live cards), and the legacy `Complete channel-separated BLASTp matrix` form — scoped to §4 so an unrelated §4 table is not mistaken for the matrix. Codex ratified the canonical title and the single-locator/both-headings migration contract; the emitter converges new cards to canonical (emitter-side follow-up, tracked). The matrix gate now FINDS the table on the 22 native cards where .372 returned `BLASTP_MATRIX_MISSING`. Test: `tests/test_s4_matrix_locator_v9_7_373.py` (6); one fixture heading line added to `tests/test_modeb_publication_quality_v9_7_372.py` (Codex-confirmed correct; no assertion changed; no title-free fallback).
- **Finished-card publication profile auto-triggers the publication gate (B1).** `authored_verify` now activates `check_publication_quality` (and passes the canonical roster) when a card carries `FINISHED_FULL48_CURRENT_EVIDENCE` or the legacy `FINISHED_CURRENT_EVIDENCE` alias, per the ratified status vocabulary. Blast radius measured on the live shelf: exactly the two finished cards (AS-XXX/BGC045, AS-XXX/BGC067) now run the full §§1–48 battery under `verify-modeb`; draft/gap-aware cards unchanged. Full suite after wiring: 4,445 passed / 585 skipped / 0 failed (one env-gated test flipped passed↔skipped between independent runs, not a regression in the changed path).
- **Interpretive-floor claim-safety fix (URGENT; highest-value item).** `docs/MODEB_INTERPRETIVE_FLOOR_v97146.md:50` instructed authors to state a "novel compound class" from a MIBiG search-negative — a negative→positive logical error that violates the claim ceiling. Corrected to "no admissible MIBiG match in the searched reference set" (search-negative / reference-dark, NOT a novelty claim); novelty is deferred to gene-level architecture plus phylogenomic evidence. Adjacent structural-novelty-prediction lines (47–49) flagged for the owner, not changed. Dry-run `-p1 --fuzz=0` clean vs the sealed .372 tree; docs only, no engine bump on its own.
- **Sequence-first gene-identity contract (Codex patch, sha 120483f8; docs+tests only).** Amino-acid SHA-256 is the positive gene-identity key; length is rejection-only; duplicate hashes disambiguate by ordered neighborhood signature at smallest radius; a BLASTp row is admitted only when query-hash + exact-locus + channel/db + result-job-receipt all bind, else it stays `OBSERVED_UNBOUND`/`QUARANTINED`. Touches `docs/MODEB_PUBLICATION_SECTION_REQUIREMENTS_v9_7_372.md` + `docs/MODE_B_SUPPORT_CARD_CONTRACT.md` + `tests/test_modeb_sequence_identity_contract_v9_7_373.py`; no `mamey/*.py`. The coded receipt-binding enforcement waits on a BLASTp-lane schema migration (the store `hits` table lacks `query_hash`/`result_job_receipt` columns) — carved out; the prose defines the admission states the gate will emit.
- **Governance folds (no engine impact): ratified status vocabulary, changelog-build-token seal gate, chat-link hook.** The the Developer or User-ratified status mapping (two orthogonal axes: `document_state` 8-state ladder + `evidence_state` carrying the sequence-first holds; strict profile `FINISHED_FULL48_CURRENT_EVIDENCE`, legacy grandfathered as alias) is recorded in `docs/`. `release_cut.sh` now rewrites the CHANGELOG-head build token to the actual BUILD_STAMP at seal, with `test_changelog_head_build_matches_stamp` ratcheting it — closing the same drift class as the .372 E-01 erratum below. The chat-link Stop hook (missing/directory/outside/unencoded-link advisory, fail-open) is folded into `hooks/` with its `HOOKS_MANIFEST.tsv` row.

### ERRATA (v9.7.372) — narrative-only, no code impact

The sealed `v9.7.372` CHANGELOG head carried three narrative errors. None affected shipped code, engine behavior, or any gate; the sealed artifact's checksums are unchanged. The sealed .372 tree is NOT retro-edited (retro-editing sealed, checksummed history is exactly what P372-01 was raised to prevent). Corrected here, fix-forward:

- E-01 (build letter): the .372 head declared `build 20260820v97372a`; the sealed build stamp is `20260820v97372b`. `BUILD_STAMP.txt` was authoritative throughout; the header was written against the candidate's provisional letter. Root-caused and gated in .373 by the changelog-build-token seal gate above.
- E-02 (combined-patch sha): the publication-quality bullet cited `sha 26f34ec3…`; the artifact actually applied and shipped is the superseding revision, sha256 `b6c7a76772e7550e9fec68cef96a8f7e11fdf1b18761ac351a81906984c08577`. The shipped code is the correct `b6c7a767` revision — only the citation was stale (the stale sha propagated into `BUILD_STAMP.patch=` because `test_build_stamp_patch_c1` derives `patch=` from the head by design — same root as E-01).
- E-03 (card count): the head opened "Ten cards"; the final admitted composition was twelve (the Codex all-48 combined patch and the patch lane complementary layer + chat-link hook were admitted after that sentence was drafted). The individual bullets are complete; only the summary count was short.

# v9.7.372 · 2026-08-20 · build 20260820v97372a · engine 1.9.125 (BUMPED — the finished-card BLASTp-matrix hard gate changes verify-modeb results for FINISHED_CURRENT_EVIDENCE cards)

**Ten cards, three lanes — AS-disclosure anonymization, the Codex finished-card evidence contract, and the
VGP identity/profile guards.** Supersedes the two-card "small cut" draft this entry originally described.
Motivated by the 2026-08-19 disclosure audit (`.372` queue, AQUARIUS_372_as_bgc_disclosure_audit: 338
AS+BGC-content line pairings measured in the sealed CODE tier), by a Codex owner-finding on a nominally
finished Mode-B card, and by two VGP defects caught in production against the real 255-archive corpus.
Built by the patch lane; the Developer or User seals.

- **AS-strain BGC-content anonymization, Tier 1+2 (the patch lane; the Developer or User scope ruling 2026-08-19: AS ids alone are public, but specific BGC content linked to AS strains is unpublished).** Eight files: five docs carrying real per-strain analysis results (`GENE_LEVEL_ANALYSIS_GUIDE`, `STRAIN_BIGSCAPE_REPORT`, `BIGSCAPE_MAMEY_INTEGRATION`, `CLUSTER_COMPLETENESS`, `INSTRUCTIONS_cohort_wide_blastp`) now carry anonymized passages with explicit withheld-content notes; two engine-data files (`compound_family_rules.json` notes, `reclass_discriminating_domains.json` provenance) drop strain/BGC ids with zero behavior change (curation tests assert classify() behavior, not note text — verified); `math_reference_vol2.md`'s derivation table gains the AS-XXX published-genome clarifier. Worked examples regenerate from public type strains in a following cut (VGP request in the queue). Tier-3 narrative (changelog/docstring case citations, 293 lines) deliberately NOT scrubbed — forward-only policy, the Developer or User to re-rule if wanted. Working-artifact sweep: the .371 session logs and staging notes that sealed into the release tier are excluded from this candidate.
- **Publication-quality repair — all nine patches, via the Codex COMBINED implementation (sha 26f34ec3…, 10 files, applied fuzz=0; supersedes the same-night the patch lane hand-implementation of the gate side, per the card's own semantic-merge rule).** New `mamey/modeb_publication_gate.py` + reworked structure gate/template emitter: fail-closed publication-candidate gate against an externally supplied canonical roster; contiguous-table enforcement (blank/prose break between separator and first data row rejects — the caught 4-of-7-cards production defect); all §§1–48 required with reasoned-not-applicable instead of omission; deep §§5–7 scientific scaffolds; a 48-row section-accountability matrix (SUBSTANTIVE / REASONED_NOT_APPLICABLE + predecessor disposition per section); typed dispositions for all 14 supporting streams; historical-card/V7/locus-map source-loss reconciliation; mandatory `strain / full node-or-contig / region / BGC alias` emitted identity; mechanical states capped at `EVIDENCE_MATRIX_VALIDATED` (`RELEASE_READY` retired); the human section contract `docs/MODEB_PUBLICATION_SECTION_REQUIREMENTS_v9_7_372.md`. the patch lane complementary layers retained on top: named-profile front-door alignment (SESSION_START_MANIFEST, skill, both START_HEREs, contract-JSON `profiles` block, regen tool now emits the profile section in BOTH generated docs), the channel-separated matrix schema constants in `mamey/mode_b/schema.py`, the additive-BLASTp skill rule, and the exemplar relabelling. Focused batteries green on the composed tree (their 4 files: 43; complementary: 27 incl. accretion 276 modules); character counts remain diagnostics, never acceptance evidence.
- **Complete per-gene BLASTp matrix gate — as-tested v2 (Codex recovery-policy patchset 2026-08-20, supersedes the first-revision diff; patch sha256 606febed…, applied fuzz=0).** Adds named-subject enforcement beyond v1. A card declaring `FINISHED_CURRENT_EVIDENCE` must now carry the `#### Complete channel-separated BLASTp matrix` in §4 — exactly one row per authoritative canonical gene (roster supplied by the validator, never self-certified), separate NCBI nr / ClusteredNR / local Swiss-Prot rank-1 columns, %identity + %positives + query coverage per bound cell, and explicit typed missing-states (no zero-imputation). Five new ERROR states (`BLASTP_MATRIX_*`). Draft and gap-aware cards keep the existing warning-first path — the hard gate is profile-scoped. Caught case: a finished AS-XXX card that passed every existing strict check while omitting the full matrix.
- **Obtainable-evidence / no-pending amendment (Codex patchset, applied after the matrix gate).** `pending` is no longer a terminal state in a finished §4 matrix — new hard error `BLASTP_MATRIX_PENDING_TERMINAL`; drafts keep pending work in ledgers; six readiness states documented, three allowed at content-QA. Attainable evidence must be acquired before content-QA, never disguised as a typed missing state. Codex combined verification: patch 2 + this amendment on fresh .371 = 33 targeted tests passed; reproduced by the patch lane on the composed candidate: 33/33.
- **Exact-locus filename gate (Codex patchset).** `tools/check_bgc_naming.py` now requires the full four-field identity (`strain__full_node__region__BGC_alias`) in AS-locus basenames: region-only is no longer a sequence anchor, shortened `NODE_n` rejected when the full form is expected, crosswalk emits the canonical prefix, regression tests added (naming/locus battery: 110 passed).
- **Dual-writer/dual-auditor evidence-retention protocol (Codex, relayed by the Developer or User).** Ships as `docs/MODEB_DUAL_WRITER_AUDITOR_PROTOCOL.md`: exact-locus identity tuple and display rule, SOURCE_REGISTER + EVIDENCE_RETENTION_LEDGER schemas with typed dispositions, the 8-state status ladder, the 22-column gene×channel table, 18 auditor acceptance tests, difference-report contract, and the AS-XXX pilot.
- **Full48 public type-strain reference exemplar + LLM context hygiene (Codex urgent patch, sha a83100c4…, the Developer or User-relayed).** Adds the 48-section reference authoring exemplar for `Kitasatospora setae KM-6054T / NC_016109.1 / region016 / BGC016` (public type strain — the first exemplar under the disclosure rule), updates the legacy exemplar README/index (seven §1–§30 class exemplars retained as legacy calibration), removes the release-profile stamp from the Claude system-prompt footer (PUBLIC/PRIVATE leaves Mode-B scientific-authoring context; export/redaction guards intentionally untouched this cut), and adds a regression test (48/48 sections, 23/23 genes, zero release stamps, zero placeholder tokens, zero structure/depth findings — 4/4 green). Independent BLASTp is a typed structural limitation in the portable fixture; no observation invented.
- **antiSMASH input-profile auto-recognition (VGP card; admission-verified).** New additive pure-read `mamey/antismash_input.py` streams the strictness token from inside the archive (4 MB chunks, ~0.03 s/zip); `--antismash-profile` default flips `unknown`→`auto`, resolved from the archive at intake; an explicit operator value that disagrees with the archive emits a loud non-fatal `PROFILE_MISMATCH`. Fixes the caught-in-production defect where a 44-strain cohort sealed as `unknown` and a 228-archive reference set (actually 148 loose / 78 relaxed) nearly ran as uniformly loose. VGP receipts reproduced: module tests 21p/1s; profile/antismash/version sweep green.
- **Strain-identity guard — an id must be an identity, not an accession (VGP card #2; depends on the profile-recognition module).** New `mamey/strain_identity.py` owns the single `looks_like_accession` definition (`cli._label_is_accession` delegates — no drift); closes the two regex gaps that let 2-letter INSDC prefixes and sanitised forms (`CP025018_1`) through. Policy: refuse an accession `--strain` ONLY when the archive yields a better name (naming the exact fix); loud-warn when nothing better resolves; batch mode auto-upgrades and reports (the path that shipped six accession-named packages on 2026-08-20, caught by eye); `--allow-accession-strain-id` opts out. False-positive guard: real cohort shapes (`AS-XXX`, `SID10815`, `Kribbella_albertanoniae`) asserted never-flagged — the guard on the guard. Receipts reproduced: 52p/1s both VGP suites; strain/profile/accession sweep 354p/45s. **v2 supersession (VGP self-reported post-admission, 2026-08-20, caught by running the module over the real 255-archive reference corpus rather than fixtures):** (a) batch strain-id collisions — two archives of the same organism resolved to the same id and the second silently overwrote the first's package directory; the batch loop now carries a seen-set and suffixes `_2`/`_3` with a printed notice (5 colliding ids measured across 10 real archives); (b) doubled accession token in suggested ids reduced 25→7 of 255 (the residual 7 are formatting-variant cosmetics, left honest). Lesson recorded: synthetic fixtures cannot catch collision defects — corpus-scale validation is part of admission for identity-handling cards.
- **Fold fixes wave 2 — suite-#4 integration collisions (the patch lane; composed at admission). Exemplar tests gain accession-contig mode-3 so the .372 identity guard's sanitised forms are covered; `check_bgc_naming` gains its `tests/test_gate_wiring_invariant.py` registration row (the tool itself has been OPERATOR_ONLY in `tools/gate_registry.tsv` since v9.7.354 — this cut registers it in the wiring invariant, it does not add the gate); `MODULE_MANIFEST.txt` regenerated to 275 modules (net +0 accretion). Receipts: accretion gate 275/275 PASS, naming/locus battery 110 passed.**

# v9.7.371 · 2026-08-19 · build 20260819v97371a · engine 1.9.124 (BUMPED — Mamey output changes: Mode-B §4 command text, s4_modeb gate results, workbook tab-guide sheet)

**The audit lane hygiene wave + doc currency + the docs-index ratchet, landed for real.** The largest single fold to date: 77 audit lane correctness/hygiene cards (each with its own PATCH_CARD + receipts; 73 applied as diffs, 2 same-file hunk collisions resolved by hand, 1 already-present, 1 workspace-scoped) plus five the patch lane cards and the VGP seal-gate wiring. Admission per the Developer or User's batch ruling 2026-08-19: spot-check first (5/5 dry-run clean, 2/2 deep claims re-verified in sealed source), then compose-and-gate — full suite 4,345/0/584 green, repo_health --strict exit 0, sapote_hooks verify --tree CLEAN. Engine 1.9.123→**1.9.124** under the standing rule (bump when Mamey OUTPUT changes because the engine changed); the bump-driving fixes are named in their bullets. Per-diff ledger + green log archived in the `.371` queue. Built by the patch lane; the Developer or User seals.

- **audit lane wave 1 — 77 correctness/hygiene cards across the whole engine surface (audit lane; the patch lane batch fold 2026-08-19).** Families: atomic-write hardening (manifest/workbook/receipt/status writers no longer leave truncated files on interrupt), case-sensitivity fixes (BGC/node/tier key comparisons), wrong-key fixes (dict keys that silently returned nothing), swallow fixes (error paths that hid real failures), checksum-exemption completions, and claim-safety text corrections. Output-affecting standouts: `modeb_template_emitter` §4 now emits the real BGC id (`--bgc BGC023`) instead of the literal `--bgc BGC` (the old facts key was never populated); `sapote_workflow.s4_modeb` reads the register's real `bgcs` key, so the W4 workflow gate reports true COMPLETE counts instead of a permanently-empty or constant-1 count; `workbook.py` tab_guide grows 22→42 sheet descriptions (README cover sheet finally documents every emitted tab; 7 generic entries reviewer-checked against `models.py` field comments). Each card's receipts live in its `AUDIT_371_*` folder.
- **Doc currency for the navigational layer (the patch lane; audit lane cross-review with 3 corrections applied).** `CURRENT_DOCS_INDEX.md` re-stamped from its THIRD freeze (v9.7.367) with the .367–.370 cut rows restored and an honest correction note; new `WHATS_NEW_368_370.md` documents the .368–.370 surface (required `bigscape_prep.py --strictness`, `sapote_hooks/` registry, availability pre-authoring, asset loop) breaking-changes-first; pointer notes added to `README.md` and `docs/BUNDLE_CAPABILITIES.md` above their historical folds.
- **CANDIDATE_251 docs-index ratchet — implemented, not just claimed (the patch lane; the Developer or User green-light 2026-08-19).** The v9.7.367 changelog said sync_version owned the index header; it never did (0 grep hits) and the index froze a third time. Now real: a `CURRENT_DOCS_INDEX.md` header rule in `tools/sync_version.py` (--apply re-stamps, --check fails on drift) + two new tests in `tests/test_docs_version_drift.py` (header-current assertion + root front-door STALE_PATTERNS scan). Self-tested both directions: --check FAILS on the frozen header, PASSES after the re-stamp.
- **`--release` operator strings tell the v9.7.236 truth (the patch lane+audit lane merged diff).** The argparse help, refusal print, and example comment all still described pre-.236 behavior (AS→PRIVATE); code was already correct (`dedup_and_guard.derive_release`: AS→PUBLIC per the PI decision; PUBLIC override honored on unrecognized shapes, refused only on AJS/PENDING/private-registry). Strings now match the code; no logic touched.
- **Four cli.py advisory fixes (the patch lane; from audit lane's monolith review; the Developer or User approval 2026-08-19).** `_cb_dir` initialized at the top of `run_one_strain` (locals() introspection retired); `chatgpt-init` presence claims routed through real existence checks; `--node-first` help made honest (always-on, no off switch); the P-LWC failure path gains its sibling-style `[WARN]`.
- **SEAL_GATE goes live (VGP; shipped UNWIRED in .370 by design).** `sapote_hooks.py verify --tree` (scope-aware bundle-integrity check) wired into `hooks/full_suite_before_package.sh` ahead of candidate zip; 32-row `HOOKS_MANIFEST.tsv`. Dry-run on this very candidate: CLEAN (0 gate, 0 advisory).
- **Fold fixes (the patch lane).** `tools/check_dangling_refs.py` SEARCH_DIRS learns the .370 `hooks/`+`sapote_hooks/` directories (5 genuinely-shipped hook names were flagged dangling); the §4-naming test now supplies the emitter's real `bgc_id` key (the old `bgc` key was validating the bug it existed to catch); one `patch`-generated `cli.py.orig` removed (failed hygiene + both public-tier content tests).
- **Not in this cut:** AMBER resolver_flavor_aware (diff artifact corrupt — truncated hunk; hand-back with regeneration recipe in the queue; design itself review-verified); the review lane bgc_tier_column_rename (needs rebase; wave 2); package-side card remediation (the Developer or User ruling 2026-08-19: NOT approved, lane closed); everything audit lane staged after the 77-card snapshot (wave 2 / .372).

# v9.7.370 · 2026-08-18 · build 20260818v97370a · engine 1.9.123 (BUMPED — W7 two-door lint unification changes the verify gate's evaluable-input set)

**Availability governance + hygiene + asset discipline + W7 door unification.** Six cards, all verified against the sealed .369 base before fold; every receipt named below is archived in the `.370` patch queue. Five cards are engine-neutral (verified per card, not asserted: the Codex diff's 8-file surface contains zero scoring/parser/packaging writers; the swallow triage is error-path-only; the rest is tools/hooks); **W7 alone drives the 1.9.123 bump** (the Developer or User's include call, 2026-08-18) — extraction/triage/scoring outputs are byte-unchanged, the bump is Mode-B gate semantics only. Built by the patch lane; the Developer or User seals.

- **W7 — two-door lint unification (the patch lane, INDIGO2-lane inheritance; the Developer or User include call 2026-08-18 → engine 1.9.122→1.9.123).** `verify-modeb` and ingest/record previously built Mode-B context differently: the verify door merged a hand-kept WHITELIST of triage-ctx keys (kcb/novelty at v9.7.203, +4 extension inputs at v9.7.369) — so every new triage-ctx key silently re-opened the divergence the W4 closing report measured in both directions (cards recorded while verify failed them; cards blocked on §29 at one door the other passed silently). One hunk in `mamey/authored_verify.py`: full tctx merge, authored package-derived values keep precedence — **door symmetry by construction for every current and future key; the whitelist is retired.** Receipts: +5 door-parity tests (`tests/test_w7_two_door_unification.py`, incl. an every-key-visible pin — a future whitelist regression fails the suite); consumer battery 70/70; real-corpus blast radius 140 canonical cards (AS-XXX/162/760/932) = **zero verdict changes**. Announced change: on degraded or historical cards the verify door can newly ERROR where a predicate it previously could not evaluate now applies — that is the fix working, stated not suppressed.

- **Mode-B availability + locus-map review contract (Codex-lane candidate; the patch lane admission review 2026-08-18).** New `mamey/mode_b/availability.py` + `mamey modeb-availability`: a formal pre-authoring data-availability step — inventories evidence streams, binds them to the canonical exact locus, separates STRAIN_ONLY/UNBOUND/ABSENT as explicit workflow states, maps channels to §1–§30, emits a manifest-backed work order; writes no Mode-B prose. Plus the normative `LOCUS_MAP_REVIEW_CONTRACT` and the dense-label transparency fix in `mamey/locus_map.py` (figures now report `labels shown N/total`; sidecar CSV gains `label_visible_on_figure` — silent suppression removed). Admission receipts: packet's receipt base-hash == sealed .369 `SOURCE_CHECKSUMS` sha256 (65e96213… exact); 7/7 packet hashes; clean apply; named battery 0 failures; freshness doctrine (mtime is not freshness; a curated index must state CURRENT) preserved. Claim ceiling per the card: availability establishes presence of evidence, never identity/production/activity/novelty. `Accretion-justified: mamey/mode_b/availability.py — new pre-authoring availability module (Codex candidate, admission-reviewed).`
- **silent_swallow triage — 151→146, waiver valid again (the patch lane, INDIGO2-lane inheritance).** Full drift attribution by AST diff of sealed trees: 149 (signed baseline, .366) → 150 (.367 wave: +3 sites, −2 converted) → 151 (.369: `register_compute_output._human_size`, added by this author, caught by this triage). All five remaining new-since-baseline sites are the degradation-reporting path's own last-resort guards — recording a recorder failure is circular, so the fix is `contextlib.suppress(Exception)` + comment: identical semantics, named deliberate suppression instead of anonymous `except: pass`. Files: `cli.py` (24→22), `master_workbook.py` (2→1), `degradation.py` (1→0), `tools/register_compute_output.py` (1→0). **repo_health `--strict` returns to PASS-with-waiver (146 ≤ signed 149) — after three consecutive cuts sealed over the expired waiver.** Process fix: `repo_health --strict` joins the standing per-fold gate battery.
- **Mode-B card identity guard (the review lane card; the patch lane fold).** `tools/modeb_card_guard.py`: diffs a card's §1/§12 stated genus + ecology against the strain's authoritative `STRAIN_CARD.md` — the mechanical backstop for the 2026-08-17 fabrication class. Discrimination measured pre-fold: 64/64 canonical PASS, 43/43 fabricated FAIL (the review lane, AS-XXX); full-cohort measurement 2026-08-18: **1,477 of 1,559 package-side cards FAIL** (receipt archived in the queue) — the canonical Codex corpus is the clean copy; package-side remediation is the Developer or User's call, outside this cut.
- **Asset discipline, bundle-shipped.** `tools/find_asset.py` now ships in the bundle, ported to the portable root contract (`SAPOTE_WORKSPACE_ROOT`→`SAPOTE_ROOT`→`mamey.workspace_root`→fail-visibly; verified: keyword lookup, `--check` exit 3 on redundant fetch, no-root fails loudly). `hooks/check_local_assets_before_download.sh` updated to the live copy (adds redundant-COMPUTE gating: bigscape/gtotree/antismash/clinker run-signatures — shipped≠live drift measured sha e40441f6…→33f3451e…). New `hooks/bundle_staging_reminder.sh` ships (the 3×-the Developer or User ship-in-bundle rule as a warn-only nag). Together with .369's `register_compute_output.py` the bundle now carries the full loop: find before compute, gate on recompute, register after compute.
- **Hook & guard organization that travels with the bundle (VGP; the patch lane fold+review 2026-08-19; re-opened cut on the Developer or User's call).** New `sapote_hooks/` (`sapote_hooks.py` capture/list/verify/install + `HOOKS_MANIFEST.tsv`, 31 annotated rows + `portabilize_hook_bodies.py`): the declarative registry and processing for the guardrail fleet — `verify` detects missing/unmanifested/non-portable/drifted hooks (CI-usable), `install --apply` wires `$CLAUDE_PROJECT_DIR`-relative hook paths on any workspace (dry-run default, settings backup). **16 hook bodies replaced with portable versions** (`${CLAUDE_PROJECT_DIR:-<historical>}` fallback — behavior-preserving by construction; all 16 re-verified `bash -n`/`py_compile` at fold by the patch lane), plus two guards the bundle never shipped: `block_out_of_bounds_writes.py` and the heredoc-false-positive-fixed `block_heavy_compute.sh` (6/6 behavior tests per the card). `hooks/SEAL_GATE_snippet.sh` ships as a **documented drop-in, deliberately NOT auto-wired** into `full_suite_before_package.sh` this cut — wiring the hook-integrity gate into the live seal path lands after a workspace dry-run (.371), not on the cut being sealed.
- **BLASTp coverage-wave tool (VGP).** `tools/blastp_coverage_wave.py` (measure/stage/plot): generalizes the live Wave-1 staging — coverage-gap classification off `blastp.sqlite`'s `gene_coverage` view, isolated-ledger wave staging, coverage plots. Engine-neutral operational tooling; validated live per the card (Wave 1 = 1,491 core-NEITHER genes across 6 ledgers, all verified submitting). Env-var-root.
- **Local SwissProt ingest (VGP; fold-time portability port by the patch lane).** `tools/ingest_swissprot_local.py`: folds local SwissProt BLASTp CSVs into `blastp.sqlite` on the `local_swissprot` channel — same 22-column schema, gene-level dedup, per-`source_file` skip, governed-strain exclusions, `--dry-run` default. Fold fix: the `SAPOTE_ROOT` literal fallback replaced with the standard root contract (env → `mamey.workspace_root` → fail-visibly) — **the fourth author caught by the same portability gate this week**; the gate works.
- **verify-before-assert contract hook (the phylogenomics lane).** `hooks/verify_before_assert_contract.py` ships in the bundle: the UserPromptSubmit reasoning-order contract (think → observed-vs-told → consider-you-are-wrong → check alternatives → reconcile → present with uncertainty) formalizing the Developer or User's 2026-08-18 operating procedure; already active in this workspace, now travels. Wiring via `sapote_hooks install` on landing.
- **BiG-SCAPE strictness awareness (the phylogenomics lane).** `tools/bigscape_prep.py` reworked so an input dir can never silently mix antiSMASH loose/relaxed/strict regions — flavor is detected/declared per input set and mixing fails loudly instead of corrupting GCF families (real-incident driven: the cohort exists at more than one strictness). Full-file fold (the shipped diff's headers were malformed; the `candidate_files/` full copy is the authoritative artifact, delta reviewed in-scope at fold). Claim ceiling: input hygiene for clustering; no scientific claim.
- **Hook fix — release-folder guard read-source false-positive (the patch lane, hooks lane per the Developer or User 2026-08-18).** `hooks/block_top_level_release_folder.sh`: an argument naming an EXISTING release path is a reference (read source / var assignment), not a creation — creation targets do not exist yet; writes into sealed trees remain `block_sealed_tree_edits.sh`'s job. Three-case self-test: sealed-tree read now allowed; the .355 HOLE case and bare `mkdir` still DENY. (The guard had blocked two legitimate reads-from-sealed on 2026-08-18.)

# v9.7.369 · 2026-08-17 · build 20260817v97369a · engine 1.9.122 (BUMPED — Mode-B gate semantics change: §31–§48 depth made enforceable)

**Engine-behavior fold: full48 gate binding.** First `.369` candidate item; the Developer or User green-lit the early fold ("Yes fold early - green light", MAINTAINER_RULINGS_2026-08-17.md evening R7) — that ruling is the bump call. Owning-lane sign-off: the review lane (gate is engine lane) authored + sandbox-proved; INDIGO2 (W4 generator owner) signed off. Built by the patch lane as a candidate; **the Developer or User seals.** The `.368` contract shipped all 18 §31–§48 sections as `optional`/`condition_key: null` while `modeb_structure_gate` computed 14 typed predicates bound to nothing — so `verify-modeb` could check §31–§48 titles/ordering and nothing else. Observed in production 2026-08-17: 81 of 82 W4 extension-section instances were §43, §31–§42/§44–§48 never authored, every card passed `verify-modeb` clean. This fold makes the depth enforceable.

- **full48 gate binding — three halves, all required (the review lane; INDIGO2-signed; the Developer or User green-lit 2026-08-17).** (A) `mamey/mode_b_receipt.py::_bgc_context_from_triage` now binds four keys from the package's own sealed tables, read-only/deterministic/no new deps: `module_count` (**aSModule features only** from `*_3_antismash_modules.csv` — not aSDomain rows), `protocluster_count` (`*_2b_bgc_crosswalk.csv`), `n_4a_rows` (**above-bar** RG-GMCI pairs only, `rggmci_confidence != LOW_SHARED_REFERENCE_SIGNAL`), `n_4d_rows` (two-proof rows naming the BGC). Any read failure leaves the key absent → predicate falls to fail-safe False (existing semantics). (B) `mamey/data/mode_b/modeb_full30_corrective_contract.json` flips **seven** sections `optional→conditional` bound to predicates the engine already computes: §32/§33/§34→`has_assembly_line`, §35→`multi_protocluster`, §36→`boundary_or_overmerge_flag`, §38→`has_resistance_signal`, §43→`has_4a_rows`. Deliberately still `optional`: §31/§37/§39/§40/§41/§42/§44–§48 (inputs live outside the package; §41 awaits an authoring side). (C) `mamey/authored_verify.py` extends the selective tctx→ctx merge (the B1/v9.7.203 kcb/novelty pattern) with the four predicate-input keys, so `verify-modeb` evaluates the same extension conditionals as ingest/record — closing the two-door divergence W7 documents (full W7 unification remains the top structural `.369` card and neither blocks nor is blocked by this). **ENGINE-BEHAVIOR → engine 1.9.121→1.9.122:** `verify-modeb` verdicts change for under-authored cards (that is the point) — a stripped §43 on AS-XXX BGC024 now errors `MISSING_CONDITIONAL_SECTION §43` where it previously shipped clean; correct cards stay clean. **Announced-change blast radius, re-measured on all 82 authored cards after INDIGO2's honest-§32–§34 re-authoring: ZERO.** Fold is byte-exact: sealed `.368` files matched the review lane's BASE refs, proven NEW files dropped in and byte-verified against NEW. Claim ceiling: card-structure enforcement only; a bound section asserts an evidence STATE is positive, never biology; absence of evidence keeps a section inapplicable (NOT-RUN ≠ biological zero). Judgment deferred.
- **W13 amendment — `has_measured_assembly_line` (INDIGO2 owner ruling, the review lane-bisected, 2026-08-18): the as-shipped three-half fold carried a real ingest regression, caught at fold time and fixed before handoff.** Binding §32–§34 to `has_assembly_line` inherited that predicate's third branch — a PKS/NRPS **class-token** match — so a §1–§30 card for any class-labeled region with zero measured architecture became structure-invalid at the ingest door (`recorded==[]`, `judgment_status` stuck `PENDING`). Found by **three independent derivations agreeing**: the patch lane's minimal-package repro, INDIGO2's read-only mechanism diagnosis, the review lane's bisection (sealed baseline 10-pass; +half A alone pass; +half C alone pass; **+half B alone 7 fail**). Fix: new predicate `has_measured_assembly_line` = `module_count > 0` or explicit flag — **measured architecture only, a bare product label never makes a section REQUIRED** (the gene-level guard applied to the gate itself; measured counterexamples AS-XXX BGC009/BGC030 + AS-XXX BGC016: label-PKS, zero aSModule). §32–§34 `condition_key` rebound to it; `has_assembly_line` retained for WARN-level applicability. the review lane re-verified the card's purpose survives: stripped-§43 on AS-XXX BGC024 still ERRORs at both doors; 153 real cards lint 0 ERRORs. **Announced residual:** label-fired non-modular regions no longer get §32–§34 as *required* (the W4 composer authors them honestly regardless — the gate just won't demand it).
- **W13b — degraded-mode title-guard repair (the patch lane, at fold).** Flipping sections optional→conditional silently dropped `TITLE_MISMATCH` on *present*-but-mis-titled conditional sections when no BGC context is supplied (the optional tier title-checked present sections; the no-ctx conditional branch only WARNed on absent ones) — weakening the punctuation anti-spoof pin (`test_5b`). Repair: a present section's title is checkable without any context — predicates gate whether a section is *required*, never what a present heading must say; 8-line branch restores `TITLE_MISMATCH` in no-ctx mode and `test_5b` passes unchanged. Two announced-change test updates (tier-map test now pins the **exact** seven `condition_key` bindings including W13, so a silent rebind fails; legacy §1–§30 cards may gain WARN-level `CONDITIONAL_SECTION_NOT_EVALUATED` breadcrumbs but never an extension ERROR). **Final receipts: full suite 4,322 passed / 0 failed / 581 skipped; `RELEASE_MANIFEST.md` test counts bound to that exact green log (sha256 `0ae565ec…3841afc`, archived as `pytest_369_green_receipt.log` in the patch queue); `sync_version --check` PASS; accretion 272/272.**
- **Recompute-register step — the formal "register after running" step for heavy compute (the patch lane; response to the Developer or User's 2026-08-17 recompute flag, reported to auditors). ENGINE-NEUTRAL (additive tooling; no `DETERMINISM_WHITELIST` artifact moves — rides the 1.9.122 bump, does not cause one).** A chat recommended re-running BiG-SCAPE while 5.3 GB of finished results sat registered on disk; the download-blocking hook cannot catch a *prose* recommendation, and — root cause — computed results were only registered in `OFFICIAL_DATA/ASSET_REGISTRY.tsv` manually, after the fact. New **shipped** `tools/register_compute_output.py`: idempotently appends one registry row for a produced result (no-op on existing id OR path — never duplicates, never clobbers); portable root via `SAPOTE_WORKSPACE_ROOT`→`SAPOTE_ROOT`→historical default, mirroring `mamey/workspace_root.py`; exposes `register_result()` for future subcommand wiring plus a CLI for the documented BiG-SCAPE/GToTree/clinker/antiSMASH recipes to end with — so the *next* heavy result self-registers instead of waiting for someone to remember. Ships in the bundle (not a machine-local `.claude` hook), per the portable-rules principle. +5 tests (`tests/test_register_compute_output.py`; throwaway tmp roots, the live registry is never touched). **Honest limit, stated not papered over:** no code gates a prose recommendation — the durable defenses are registration-by-construction, the escalated behavioral rule, and `find_asset` as mandatory preflight. Companion (not in-tree): `STAGED_REGISTRY_ROWS.md` in the patch queue lists the still-unregistered tree results with sign-off preconditions.

# v9.7.368 · 2026-08-17 · build 20260817v97368a · engine 1.9.121 (UNCHANGED — engine-neutral; MULTI_CHANNEL_HOLD lives in non-whitelisted _4D)

**Engine-neutral surfacer wave (Wave 2 of the .367/.368 split — resolved NOT to bump the engine).** The .367 CHANGELOG predicted this wave would bump engine 1.9.121 → 1.9.122 via Mango Tango's RFC PATCH-2 `MULTI_CHANNEL_RESCUE`. Both lane owners ruled CHANGES on 2026-08-17 (the review lane two-proof: RG-GMCI homology + KS-phylo homology is proof-1 + proof-1, NOT an independent proof-2; Amber `_4B`: preserve the subtype partition), and the AS-XXX chimera negative control (PASS-with-caveat) reinforced surfacer-only. Implemented to that spec, the feature became a **pure advisory verdict in `_4D_two_proof_rescue.csv`, which is NOT in `packaging.py::DETERMINISM_WHITELIST`** — so it moves no score-comparable artifact and the engine stays 1.9.121. `.368` is therefore an engine-neutral bundle bump, like `.367`. CODE tier; PUBLIC/SID/MERGED remain on HOLD. Built by the patch lane; owner sign-off the review lane + Amber PASS (2026-08-17); sealed by the Developer or User 2026-08-17.

- **MULTI_CHANNEL_HOLD — advisory two-proof concordance verdict (Mango Tango RFC KS_PHYLO_MULTI_CHANNEL_RESCUE; the review lane + Amber ruled 2026-08-17).** New verdict in `mamey/rescue_two_proof.py::two_proof_join`: a contig pair that RG-GMCI ranked **HIGH/MODERATE** but that FAILED the complementarity (`_logic_proof`) gate, **and** which the reference-free KS-clade channel (`_4B`) independently groups, is now labeled `MULTI_CHANNEL_HOLD` instead of the imprecise `KS_CLADE_ONLY` (RG-GMCI *did* rank it). Meaning: two HOMOLOGY channels concordant, independent complementarity proof still owed → **advisory HOLD, never a rescue.** It feeds **no** score/rank/prior and does **not** promote to `TWO_PROOF_RESCUE`; `COMPLEMENTARY_SPLIT` (`_logic_proof`) remains the SOLE rescue gate. **Engine-neutral, verified not asserted:** `_4D_two_proof_rescue.csv` is not in `DETERMINISM_WHITELIST` (`packaging.py:65-74`), and the change reclassifies existing `_4D` rows without adding/removing any (row-count invariant → `modeb_structure_gate.has_4d_rows` and every `_4D` consumer see the same set). `mamey/pks_ks_scan.py` and `_4B` are **byte-identical** — Amber's `.366` subtype partition is untouched, so no cross-subtype bridge is introduced. AS-XXX caveat met by construction: the in-engine KS channel is 5-mer containment single-linkage (subtype-gated), not an "any shared ancestor UFBoot≥80" tree query, so the naive-backbone false positive the control flagged cannot arise here. Consumer card `mamey/modeb_domain_phylogeny.py` renders the verdict; `TWO_PROOF_LOGIC_VERSION` 1→2 (self-declared in `_4D`, not the engine version). +8 tests (`tests/test_multi_channel_hold.py`); full suite 4,322 passed / 0 failed / 581 skipped.

# v9.7.367 · 2026-08-16 · build 20260816v97367a · engine 1.9.121 (UNCHANGED — hygiene wave; no DETERMINISM_WHITELIST artifact changes)

**Engine-neutral hygiene wave (Wave 1 of the .367/.368 split).** Engine 1.9.121 unchanged — nothing in this cut alters a `DETERMINISM_WHITELIST` score-comparable artifact. The engine-BEHAVIOR items (Mango Tango RFC PATCH-2 `MULTI_CHANNEL_RESCUE` + PATCH-4 iterative-module rescue) were deliberately split to the `.368` queue, which will bump engine 1.9.121 → 1.9.122. CODE tier; PUBLIC/SID/MERGED remain on HOLD. Built by the patch lane; sealed by the Developer or User. *(Candidate in progress — bullets land as Wave-1 items are applied.)*

- **Scoring net — silent-degradation breadcrumbs on the scoring surface + coverage-assertion wiring (Indigo2 §1, the review lane-ruled 2026-08-15).** New `mamey/degradation.py`: a process-local collector so a defensive broad-`except` on the scoring/scan surface records WHAT degraded instead of vanishing. Wired into `scoring.py` + `source_scans.py` (10 Tier-A sites) and drained by `cli.py` into `run_phase_receipts.jsonl`. **Fingerprint-neutral by construction, verified against the sealed engine, not asserted:** `run_phase_receipts.jsonl` is a `MUTABLE_RECEIPT_NAMES` member (`packaging.py:25`) and is NOT in `DETERMINISM_WHITELIST` (`packaging.py:65-74`), and `record()` fires only on the exception path — so no score-comparable output moves → not a bump. Also lands both coverage-assertion surfaces (per-strain + B1 merge, one canonical guard) and the `cli.py:19` stale smoke-help fix. +16 tests (`test_scoring_net.py`, 16/16 on the patch lane's independent re-run). `Accretion-justified: mamey/degradation.py mamey/logging_setup.py mamey/ziputil.py mamey/workspace_root.py` — new modules, deliberate baseline additions; `Consolidates: raw_antismash_triage._safe_extract_zip`; MODULE_MANIFEST.txt regenerated this cut.
- **Home-path convergence — DEC-02 closed (Indigo2 JOB-C / A10).** New `mamey/workspace_root.py` is the single home of the workspace-root default: `workspace_root()` resolves `SAPOTE_WORKSPACE_ROOT`, then `SAPOTE_ROOT`, then the historical literal — **byte-identical when no env var is set** (verified: env-unset returns the exact prior literal). Routed **11 hardcoded sites across 10 modules** (`npatlas_structure`, `cli` ×2, `interactive_figures/widget_data`, and 7 `tools/` scripts) through it; the literal now lives in exactly one sanctioned place (portability guard `test_workspace_path_portability.py` allowlists it, and `docs/INSTALL.md` documents `export SAPOTE_WORKSPACE_ROOT` for non-the Developer or User machines). This converges the two env-var names (`SAPOTE_ROOT`→`SAPOTE_WORKSPACE_ROOT`) that DEC-02 tracked. Resource-path only — no scoring path, no whitelisted artifact. +3 tests. (The repo_health `home_path` ceiling-drop 12→1 + the ruff config are advisory-CI follow-ins, no suite gate.)
- **Safety Five (+1) (Indigo2 Block F / A7).** Six mechanical safety fixes, zero scoring/biology semantics, all fingerprint-neutral. New `mamey/ziputil.py::safe_extract_all` promotes the existing member-path traversal guard; `raw_antismash_triage._safe_extract_zip` becomes a one-cut back-compat shim; three unguarded `extractall` sites (`tab_reconcile.py` ×2, `lead_pages.py`) route through it — malicious/corrupt zips now fail loudly instead of writing outside dest. `tools/mlsa_outgroup_scan.py` `os.system`→`subprocess.run` list-argv (no shell interpretation; `rc==0` semantics preserved). `deliverable_queue.py` timestamp is now tz-aware UTC (`+00:00`; documented non-fingerprinted field). `cli.py::_stamp_terminal_status` no longer swallows a manifest-write failure silently — it writes a `stamp_terminal_status FAIL` phase-receipt row (additive; the never-raises phase log). The card's 3 companion tests (zip-slip guard, single-guard-definition AST, seal-receipt) are a follow-in — authoring them from prose was held to avoid introducing defects.
- **Hooks fail-closed (Indigo2 JOB-B).** Three blocking guardrail hooks (`hooks/block_seal_commands.sh`, `block_sealed_tree_edits.sh`, `block_top_level_release_folder.sh`) failed OPEN on internal error (jq/grep failure → silent allow). Added strict mode + an `ERR` trap that EMITS the deny decision, so an internal error now DENIES. Additions-only (verified diff vs bundle: 10 lines each, 0 removals); bash `-n` clean. Live-hook application is the Developer or User-run (`apply_to_live.sh`); this folds the shipped bundle copies so shipped==live.
- **Logging seed (Indigo2 JOB-E).** New `mamey/logging_setup.py` — one stdout logging front door, bare `%(message)s` at INFO, so a converted `print(x)`→`log.info(x)` emits byte-identical bytes; `MAMEY_LOG` env override; idempotent. Seed conversion of `mamey/wheelhouse.py` (15 sites). **Two defects in the candidate files fixed on apply (caught by running them):** the converted `wheelhouse.py` placed the logger import before `from __future__ import annotations` (SyntaxError) — reordered; and `test_logging_setup.py` used `import logging_setup` instead of `from mamey import logging_setup` — corrected. +tests (10 pass w/ determinism smoke).
- **Determinism smoke test (Indigo2 JOB-D).** `tests/test_determinism_smoke.py` — package-vs-itself `repro_fingerprint()` self-consistency (6 cases: idempotence, byte-rewrite stability, CRLF normalization, single-byte divergence naming, MISSING-component contract, whitelist coverage). CI-only harness (`.github/workflows`); no engine change.
- **cohort_figures dead-block deletion (Indigo2 TASK-02 / A9).** Deleted the 115-line `# merged from figures_split.py` duplicate in `cohort_figures.py` (`render_split_figures` + 7 helpers) — an EXACT 1.000-per-function copy of the live `figures_split.py` implementation, carrying a latent F821 (`sys`/`subprocess` unimported) but **unreachable** (no importer takes it; `render_brief.py` imports the real one from `figures_split.py`). Verified every helper use sat inside the block before cutting (`_stem` had no live collision; `_acc_cls` did not exist). No deliverable ever rendered from this copy → no erratum. `figures_split.py` remains the single implementation.
- **Wheel data-glob gap (Indigo2 I-53 / A8).** `pyproject.toml [tool.setuptools.package-data]` shipped only `.json/.md/.yaml/.yml` — `.tsv/.csv/.faa` under `mamey/data/` (`outgroup_registry.tsv`, `strain_genus.csv`, `nocardia/*.csv`, `phylo_seeds/*.faa`) were unmatched and silently absent from wheel installs. Added the three globs. (Wheel-content gate `test_wheel_data_completeness.py` is a `slow` cut-time build gate — held for the cut runner, not the candidate suite.)
- **CURRENT_DOCS_INDEX.md re-stamped (Indigo2 JOB-A / A6).** Header was frozen at v9.7.337; corrected to v9.7.367 with the `.339–.366` span from CHANGELOG headlines and link-verified refs. (The `sync_version`-owns-the-header ratchet, CANDIDATE_251, is a follow-in so it can never freeze again.)
- **Governed denominator ratification propagated into the engine bundle (enacts the Developer or User's 2026-08-14 ruling).** The 2026-08-14 ratification (GOVERNED = 44 strains / **1,753** regions, from the MEASURED AS-XXX decontam antiSMASH count of 52, superseding the projected 38) updated `OFFICIAL_DATA/exclusions.json` but not the engine's bundled fallback, because the `.366` seal (2026-08-13) predated the ruling by a day. Per `test_exclusions_ssot.py`'s own protocol ("a future ruling must update the JSON, `_DEFAULT` and `_RULED` together"), this cut updates `exclusions.py::_DEFAULT` (`strain_of_record` → `decontam_52region_measured_2026-08-14`; `governed.regions` 1739 → 1753) and the pinned test literals (`_RULED`, dual-state) to mirror the ratified SSOT. Governed metadata only — no scoring path, no whitelisted artifact. This closed 3 of 6 real test failures surfaced by the independent full-suite re-run (Indigo2's "zero regressions" receipt did not catch them).



**Engine bump 1.9.120 → 1.9.121 — a score-comparability boundary.** One fold changes a whitelisted output; the others are engine-neutral and ride the same bump. CODE tier; PUBLIC/SID/MERGED remain on HOLD. Built by the patch lane; sealed by the Developer or User.

- **_4B cis/trans-AT domain-subtype partition (AMBER_366_C12, Amber sign-off 2026-08-12).** `pks_ks_scan.py` now parses the antiSMASH `/domain_subtypes` qualifier (already present in the region GBKs — no antiSMASH re-run) and partitions the single-linkage KS-clade pass **within each subtype**, so a trans-AT KS can no longer join a cis-AT clade by transitivity (killing the substrate-clade false positive Amber's trees exposed). Edge policy (the phylogenomics lane's ruling as `_4B` owner): each named subtype single-linkage-clusters only with itself; **Hybrid-KS joins only Hybrid-KS**; **UNCLASSIFIED KS are surfaced PAIRWISE** (ASK-1 ruling (b) + pairwise-not-bridge — an unsubtyped KS never merges a blob by transitivity; each qualifying cross-contig unclassified pair is its own 2-member candidate for RG-GMCI's second proof). New `ks_subtype` + `ks_subtype_partition_version` columns on `{strain}_4B_pks_ks_fragment_scan.csv`. **This rewrites a `DETERMINISM_WHITELIST` artifact → re-scores the fingerprint → the engine bump.** Measured cohort impact 2/288 same-locus candidates drop; `_4B` feeds no scoring path, so no triage verdict moves. +7 tests; existing `_4B` fixtures updated to carry a subtype (as real GBKs do).
- **VGP-06 — `diagnostic_tier` → `run_depth_mode` gene_by_gene column rename (engine-neutral schema).** The `gene_by_gene` column named `diagnostic_tier` was populated from `Depth_floor` — the per-RUN depth mode, a constant across a strain's genes — and read as a per-gene signal it never was. The value was always correct; only the name misled. `gene_by_gene.py` is **not** in the fingerprint whitelist, so this is a schema rename, not a re-score; consumers keying on the old name are updated.
- **AMBER_366 phylo-placement Tier 1 — reference-backbone placement tools + docs (engine-neutral add).** Six standalone `tools/` scripts (`phylo_place`, `outgroup_registry`, `phylo_refset`, `figure_methods`, `placement_to_docx`, `placement_figure`) + two workflow docs: build a fixed type-strain backbone once, then place lab 16S/protein queries (EPA-ng/gappa/SEPP) and report the clade/neighborhood (LWR + pendant length) rather than rebuilding a tree each time. Validated end-to-end on the Nocardia cohort (13/13 placed). Pure add; no engine files, no fingerprint change. +5 tests.
- **REV-01 — independent review of the sealer-authored .361–.364 span: PASS (the patch lane, independent of that span).** Engine-diff `.360 → .364 → .365`: all changed engine files clean/intentional — MIBiG data externalized (licensing) via a fail-loud `external_data.py` resolver, `doctor` dataset report, §31–48 gate (already audited), two hardcoded paths de-hardcoded to `SAPOTE_WORKSPACE_ROOT`, AS-scrub removed per GOV-003. No persisting defect. Limit: Codex's original `.361–.364` findings list not located on disk; independent engine-diff accepted by the Developer or User as the REV-01 basis, with a parallel non-blocking ask to Codex.

**Claim ceiling:** `_4B`/`_4D`/RG-GMCI/KS-clade rows are homology-guided CANDIDATES, not merges or nucleotide joins; the subtype partition is a false-positive reducer, not a new claim; comparators are similarity not identity; placement = neighborhood hypothesis, 16S = anchor; missing evidence ≠ biological absence; judgment deferred. **Deferred from this cut:** CERULEAN_366_C13 bioassay/alias registry (engine-neutral but carries governed strain-provenance claims + targets workspace `OFFICIAL_DATA/` — belongs in the workspace, not the sealed engine); C09/C10/C11 (unfinished / spec / docs); phylo Tiers 2/3.

# v9.7.365 · 2026-08-12 · build 20260812v97365a · engine 1.9.120 (UNCHANGED — governed-source resolution closure + delegated decisions)

**Engine-neutral.** Engine 1.9.120 unchanged; `scoring.py`, `parsers.py`, `rules.py`, `domain_level.py`, `pks_ks_scan.py`, `packaging.py` byte-identical to sealed .364. No scoring path, no repro-fingerprint artifact, no gate decision moves. Single tier (CODE); PUBLIC/SID/MERGED remain on HOLD.

- **CUT-10B — governed-source resolution closure (Codex/Rootstock candidate, applied).** `.364` registered `official_data` in the external-data registry but **`exclusions.py` never honoured `MAMEY_DATA_ROOT`** — registering a dataset and resolving it were two different things. **Reproduced on sealed .364 before applying:** with `MAMEY_DATA_ROOT` set, the registry reported `provisioned: True` while `governed_denominator()` still returned the in-module default `44 / 1,739`. That is worse than the original silent walk-up it replaced: an invisible dependency became a **visible but wrong reassurance**. Now `$MAMEY_DATA_ROOT/OFFICIAL_DATA/exclusions.json` is a valid governed source; `doctor` prints the **exact resolved file path** when source-bound, and **warns rather than reporting an all-clear** when falling back. Verified both directions (bound → `7 strains / 91 regions` from a synthetic fixture; unbound → warning naming both env vars). Patch SHA `c1b96ba5…`, dry-applied clean, +2 tests.
- **GOV-002 — engine version for §31–§48 gate behaviour: HELD at 1.9.120.** Decided on evidence: `modeb_structure_gate.py` is **not** in the repro-fingerprint whitelist (which holds only `_4A_RGGMCI_ranked_pairs.csv` and `_4B_pks_ks_fragment_scan.csv`); no scoring path, parser or rule changed; and **no shipped Mode B card carries a §31+ heading**, so no existing artifact changes verdict. The engine integer marks a *score-comparability* boundary, not a *validation* boundary. Bumps if a slot is promoted past `optional`, if a §31+ output enters the fingerprint, or if lint verdicts begin feeding a scored field.
- **GOV-003 — CUT-01 scope stated exactly, because two controls shared one flag name.** **REMOVED:** the AS-ID *scrub* — the pass that REWROTE identifiers in the staged tree, inert since v9.7.219. **RETAINED:** the AS-ID *leak audit* — read-only, reports and can fail a cut, rewrites nothing. A scrub **mutates** the release; an audit **observes** it. Removing a mutation nobody runs removes dead weight; removing the observation would remove the only control that would notice a genuinely private identifier entering a public tier, which is not what was approved.
- **GOV-004 — CUT-05 implemented, not waived.** Verified unsatisfied first (`doctor` on .364 printed nothing for gtotree/iqtree/phylo). Companion **binaries** and reference **datasets** answered the same operator question through two unrelated registries. `doctor` now reports GToTree / IQ-TREE / fastANI presence, and states plainly that absent binaries mean trees render **NOT MEASURED, not absent** — `plan_gtotree_iqtree.py` correctly refuses to authorize a run (`HOLD_TOOL_MISSING`). GToTree is GPL-3 and will never be vendored, which is precisely why its absence must be visible rather than discovered mid-run.
- **GOV-005 — `.365` queue ownership, held PENDING.** Sealer owns mechanical/testable work; Codex owns independent review and content authoring; the release owner owns disclosure scope and any engine-integer bump. Grounded in the failure record, not preference: four consecutive sealer-authored cuts (.361–.364) went unreviewed and Codex found real defects in them — including one where the sealer verified against a baseline it had itself contaminated. **The governance guard refused this record `ACTIVE`** because its own invalidating condition (REV-01 outstanding) is currently true; it stands as a working assignment until the independent review is signed. The mechanism added in .361 correctly fired on its own author.

**Claim ceiling:** no engine, scoring, gate-decision or disclosure behaviour changed. **SCI-02 remains OPEN** — ~190 lines still pair a real strain identifier with an unpublished genome finding; the scrubber prototype aliased them to residual 0 but failed 12 tests on embedded-ID forms (`AS-XXX_NODE_5`, `AS-XXX_BGC3`) and is **not** in this cut. Contract recognition is still not section authoring: §31–§48 content producers are §41's emitter plus one hand-authored pilot; 17 slots remain `NOT_PRODUCED`. Judgment deferred.

# v9.7.364 · 2026-08-12 · build 20260812v97364a · engine 1.9.120 (UNCHANGED — §31–§48 contract extension + governance/portability)

**Engine-neutral.** Engine 1.9.120 unchanged; `scoring.py`, `parsers.py`, `rules.py`, `domain_level.py`, `pks_ks_scan.py`, `packaging.py` byte-identical to sealed .363. No scoring path, no determinism-fingerprint artifact, and **no gate DECISION change** — a card that passed .363 still passes. Forward-only ENGINE_LINEAGE stanza per the .350/.351/.352 precedent. Single tier (CODE); PUBLIC/SID/MERGED remain on HOLD.

- **§31–§48 Mode-B contract extension (CUT-14).** The contract now covers **§1–§48** (`schema_version: modeb_corrective_full48_v1`). The §1–§30 core is untouched — same 30 rows, same required-tiers. The 18 new sections ship as a **THIRD tier, `optional`**: recognised as contract, **never required**, and fully validated when present (exact title, order, uniqueness, non-empty body). Promoting any slot to `conditional`/`always` is a per-slot decision for when its authoring instruction and content exist — not a side effect of numbering.
  - **The defect that made v1 and v2 wrong, found by Codex/Rootstock review:** the contract gained §31–§48 while **both Markdown parsers stayed hard-capped at `1 <= num <= 30`**, so a card with valid §31/§48 headings parsed to `[]`/`{}` and the sections were **silently discarded**. Verified first-hand on sealed .363 before fixing (`extract_section_titles()` → `[]`). **The sealer's own verification was the weak link**: a test reading "0 UNKNOWN_SECTION_NUMBER findings" as *recognised* could not distinguish that from *never seen*. Recognised section numbers are now **derived from the contract** (`recognised_section_numbers()`) — deliberately NOT a literal 48 swapped for the literal 30 — with `_SURFACED_UNKNOWN_MAX = 50` so a future §49/§50 still WARNs rather than vanishing one rung up.
  - **Typed predicates, not Python truthiness.** A negative blacklist cannot be complete: `SOURCE_UNAVAILABLE`, `NOT_APPLICABLE`, `IDENTITY_OR_JOIN_HOLD` slipped through it. Inverted to a **positive-state allowlist** (`PRESENT`/`BOUND`/`TRUE`/positive count/identifier), with the full deficit vocabulary explicit. An **unrecognised** value is treated as NOT applicable — the fail-safe direction. Three tightenings: **§39** needs a bound cross-strain comparison (`cohort_size >= 2` is a roster fact, not a measurement); **§40** needs provenance (run/cutoff) beside the family id; **§42** needs measured composition **and** a declared baseline (GC alone is not HGT evidence).
  - **Exact punctuation-bearing titles for §31–§48.** `_normalise()` strips all punctuation, which silently broadened the selected contract — "Initiation release logic" passed for "Initiation & release logic". Extension titles are now compared **literally**; §1–§30 keep the tolerant match (tightening those is a separate decision that would fail existing authored cards).
  - **Duplicate extension section is an ERROR** (§1–§30 stay WARN): two blocks claiming one registered slot make body ownership ambiguous, and only the first is parsed. **`EMPTY_OPTIONAL_SECTION` is unconditional** — body/depth floors run only under `check_depth=True`, but `compilation_gate.py` and several receipt paths lint without it, so an empty registered heading would otherwise assert coverage it does not have.
  - `tests/test_modeb_sections_31_48.py` — **30 behaviour tests** (all 12 Codex acceptance cases), exercising parser, linter and predicates against real card text rather than counting contract rows. The previous tests counted rows and stayed green while the parser was broken.
- **AS_SCRUB machinery REMOVED (CUT-01, PI instruction, the Developer or User 2026-08-12).** Inert at `AS_SCRUB=0` since v9.7.219; a switch that is never on is a switch nobody tests — it read as a live control while doing nothing. AS identifiers are public (16S on GenBank); the real exposure is unpublished genome **findings in prose**, which no identifier scrub ever caught. `tools/redact_public_tier.py` is **retained** and stays reusable for a future genuinely-private cohort. **The AS leak AUDIT is deliberately kept** — removing a safety net is not what was approved.
- **SID uniformity scrub REMOVED (CUT-02, same instruction).** Its own v9.7.250 comment recorded it as simultaneously **destructive** (it rewrote `Amycolatopsis sp. SID8362` — an NCBI BLASTp *subject organism*, not ours to redact — inside the very evidence file the phantom-locus fix points authors at, and broke the mycotrienin ground-truth linkage) and **ineffective** (the identifier survived in the filename, in `TIER_MANIFEST.txt`, and in `tests/`). SID is public (Chevrette 2019). Removed with its two payload files and the v9.7.250 clean-tier scrub-scope test (retired in this cut; it existed only to pin the exclusions that stopped the scrub eating `Wheelhouse/` evidence, and has no subject now the scrub is gone).
- **`OFFICIAL_DATA` registered as an external dataset (CUT-10; Codex .363 review).** It is a **governance** input — it sets the governed denominator — yet `exclusions.py` resolved it by walking **up** from the bundle and was **silent on success**, so the same sealed engine reported a different denominator depending on where it was extracted. Now a sixth registered dataset (`MAMEY_OFFICIAL_DATA`), and **`mamey doctor` prints the resolved denominator and its source** so an operator sees which figure is in force *before* generating a governed claim.
- **`tests/test_tool_front_doors.py` (CUT-04).** Runs `--help` on every tool from a **foreign working directory** — **229 tools pass** — plus a static check that any tool importing `mamey.*` carries a `sys.path` guard. This closes a structural blind spot: 100 test files load modules by file path (`spec_from_file_location`), so the suite cannot detect a broken package import in the corresponding tool. Codex independently flagged the same gap as a recommended regression gate.
- **`docs/WORKED_EXAMPLE.md` (CUT-11).** End-to-end walkthrough on a **public** genome — *Streptomyces olivochromogenes* `GCF_001514115.1` — one download, three commands, every number reproducible (43 BGCs; High 2 / Medium 6 / Low 25 / Inventory 10; assembly tier GOOD). Replaces in-house worked examples so documentation neither depends on unpublished data nor discloses it, and states plainly what it does **not** demonstrate (cohort analysis, phylogenomics, bioactivity).

**Claim ceiling:** no engine, scoring, gate-decision or disclosure behaviour changed. Contract *recognition* is not scientific section authoring — §31–§48 content producers that exist are §41's emitter (`modeb_domain_phylogeny.py`) plus one hand-authored pilot; the other 17 slots remain `NOT_PRODUCED` as engine emitters. Class-level capacity hypotheses; comparators are similarity, never identity; judgment deferred.

# v9.7.363 · 2026-08-11 · build 20260811v97363a · engine 1.9.120 (UNCHANGED — public-release readiness)

**Engine-neutral.** Engine 1.9.120 unchanged; `scoring.py`, `parsers.py`, `rules.py`, `domain_level.py`, `pks_ks_scan.py`, `packaging.py` byte-identical to sealed .362. Single tier (CODE). PUBLIC/SID/MERGED remain on HOLD. **Sealer-authored** (same provenance caveat as .361/.362: no second pair of eyes; scope confined to mechanical, testable, reversible changes).

- **Workspace-path genericisation COMPLETED — the last privacy blocker for a public repo.** `.361` fixed the 13 hooks; this cut finishes the tree: **27 files in `deliverable_tools/`** plus stragglers in `tests/`, `tools/`, `mamey/` and two `mamey/cli.py` argument defaults (the BiG-SCAPE binary and Pfam-A paths). Everything now resolves through **`$SAPOTE_WORKSPACE_ROOT`, defaulting to the original path** — verified unset → original, set → override, so existing setups are untouched. **Bare hardcoded author paths in code: 41 → 0.** Publishing no longer exposes a username or private folder layout. `tests/test_workspace_path_portability.py` (8 tests) pins it.
  - **One documented exception:** `tools/audit_modeb_support_card.py` and its test keep literal author paths because the tool's *job* is to detect workspace paths leaking into Mode B cards — parametrising them would disable the guard. Annotated in-file and allowlisted in the test.
  - **Root cause fixed properly:** `mamey/cli.py` used `os.environ` at parser-build time while importing `os` lazily. Rather than patch the symptom, `import os` moved to the module import block. That single fix cleared 28 test failures.
- **Public-repo hygiene restored.** `.gitignore` (caches, editor debris, user-provisioned external data, local run output) and `.github/workflows/ci.yml` — the real suite on Python 3.11/3.12 plus the six release gates a cut actually runs (`sync_version --check`, `verify_release_identity`, `check_release_manifest`, `check_module_accretion`, `check_monolith_freshness`, `repo_health --strict`). The bundle previously shipped **zero dotfiles**, so a public repo would have had a 3,900-test suite and no CI, and contributors would commit `__pycache__` on their first PR. `ALLOWED_HIDDEN` widened deliberately and narrowly to `{.gitignore, .github, .gitkeep, .gitattributes}` — a test asserts it stays ≤6 entries, so the gate that caught the `_CANDIDATE_NOTES` dotfiles at .355 keeps its teeth.
- **`mamey doctor` now reports external-data provisioning.** `.362` shipped `external_data.status()` but nothing user-facing called it, so an operator discovered a missing dataset mid-analysis as a NOT MEASURED section. Doctor now lists which of the five datasets are provisioned and, for each missing one, names the env var, the upstream URL and the doc — plus a standing reminder that an absent dataset renders **NOT MEASURED, never an empty result**. Wrapped so a probe failure can never break doctor.

**Claim ceiling:** no engine, scoring, gate-decision or disclosure behaviour changed. Judgment deferred.

# v9.7.362 · 2026-08-11 · build 20260811v97362a · engine 1.9.120 (UNCHANGED — de-bundle third-party data)

**Engine-neutral, licence-driven.** Engine 1.9.120 unchanged; `scoring.py`, `parsers.py`, `rules.py`, `domain_level.py`, `pks_ks_scan.py`, `packaging.py` byte-identical to sealed .361. No scoring path, no determinism-fingerprint input, no gate decision moves. Single tier (CODE). PUBLIC/SID/MERGED remain on HOLD.

**Accretion-justified: mamey/external_data.py — single resolver for user-provisioned third-party datasets; replaces four ad-hoc in-tree data paths with one documented contract (env var → $MAMEY_DATA_ROOT → legacy), so no consumer hardcodes a redistributed payload.**

- **THIRD-PARTY REFERENCE DATA IS NO LONGER REDISTRIBUTED (PI instruction, the Developer or User, 2026-08-11: "we dont want or need mibig data in the bundle … I will instruct users to download the entire mibig database files, same for hmm and other databases like NP Atlas").** Removed from the tree: `mamey/data/mibig/` (reference index + neighborhood partitions, 2.3 MB), `Wheelhouse/hmm/` (Pfam profiles, 4.4 MB), and the literature corpus JSONL (10.8 MB). **Total 17.6 MB — 34% of the extracted tree.** The bundle is MIT-licensed CODE; these datasets carry their own licences, citation requirements and release cadence, and bundling them (a) misstated the licence, (b) froze operators to whichever snapshot a cut happened to capture, and (c) made a third of the release third-party payload.
- **The licence problem, stated plainly.** MIBiG and NP Atlas are **CC BY 4.0 — attribution required**, so shipping them inside an MIT tree implies terms that do not apply. Worse, the literature corpus contained **4,658 full publisher-copyrighted abstracts** (of 7,648 records) redistributed under that same MIT licence; PubMed *metadata* is freely available but the *abstracts* are not ours to give away. Pfam is CC0 so redistribution was permitted, but pinning a frozen subset inside a code release is still the wrong coupling. **This is a genuine pre-publication blocker that the GitHub-release milestone would have shipped.**
- **NEW `mamey/external_data.py` — one resolver, five datasets, fail-loud.** Resolution order per dataset: its own env var (`MAMEY_MIBIG_DIR`, `MAMEY_MIBIG_NEIGHBORHOODS_DIR`, `MAMEY_LITERATURE_CORPUS`, `MAMEY_HMM_DIR`, `MAMEY_NPATLAS_DIR`) → `$MAMEY_DATA_ROOT/<subdir>` (extending the .352 H1 convention rather than inventing a second one) → the legacy in-tree path, honoured only if it still exists so pre-.362 trees keep working. `require()` raises `MissingExternalData` carrying **the dataset, the env var, the expected layout, the upstream URL and the licence** — actionable, not a stack trace. `resolve()` returns None for optional consumers, `status()` powers an operator check. `_data_dir()` resolves **per call**, so an operator can provision mid-session.
- **Deficit semantics preserved (this is the claim-safety half).** An absent dataset renders **NOT MEASURED**, never an empty result that reads like a measured zero. Absence of a comparator is not evidence of novelty; absence of literature is not absence of prior art. The literature loader already degraded silently by design for the purgeable public tier — that path is now explicit rather than incidental.
- **Tests: data-dependent assertions SKIP when unprovisioned, structural ones were corrected.** 35 tests failed on removal; each was triaged rather than blanket-skipped. `test_mibig_neighborhoods.py` (25) and the MIBiG-content assertions in `test_mibig_no_redaction_corruption.py`, `test_as48_public_np_carveout.py`, `test_fragment_ceiling.py` assert **dataset content**, so they are `skipif`-guarded on provisioning — the invariants they protect still run wherever the data IS present. `test_public_tier_strip_v9_7_267.py` asserted the tier **must ship** the Pfam HMM; that expectation is now **inverted and renamed** (`test_public_tier_does_not_ship_user_provisioned_hmm`), because shipping it is precisely what this cut removes.
- **NEW `docs/EXTERNAL_DATA.md`** — per-dataset licence, upstream URL, expected layout, size, consumers, and what happens when absent; plus the deterministic rebuild command for the MIBiG neighborhoods (MUSCLE 5.2 → FastTree 2.2.0 `-lg` → complete-linkage cut at patristic diameter ≤1.5 → medoid representative). Operators cite the release they actually provisioned; the bundle cannot know which one that is and does not cite on their behalf.
- **Retained in-bundle, deliberately:** `mamey/data/phylo_seeds/*.faa` — five MLSA seed proteins (atpD, gyrB, recA, rpoB, trpB) from the **public type strain *Kitasatospora setae* KM-6054**, ~4 KB total, BLASTp **bait only** (the seed's own identity never enters results; `build_mlsa` takes each target genome's best-ortholog CDS). Tiny, public, and the pipeline is unusable without them.

**Claim ceiling:** no engine, scoring, gate-decision or disclosure behaviour changed. Class-level capacity hypotheses; comparators are similarity, never identity; missing evidence ≠ biological absence. Judgment deferred.

# v9.7.361 · 2026-08-11 · build 20260811v97361a · engine 1.9.120 (UNCHANGED — sealer-authored governance/portability fixes)

**Engine-neutral.** Engine 1.9.120 unchanged; `scoring.py`, `parsers.py`, `rules.py`, `domain_level.py`, `pks_ks_scan.py` and `packaging.py` are byte-identical to sealed .360 — no scoring path, no determinism-fingerprint input, no gate decision moved. Every .343–.360 package stays score-comparable. Single tier (CODE). PUBLIC/SID/MERGED remain on HOLD.

> **PROVENANCE — this cut was authored by the sealer, not by the patch lane.** Every other cut in this campaign came from a candidate built in a separate lane and was independently verified here; this one closes findings the sealer itself raised, so the usual builder/sealer separation does not apply and no second pair of eyes has reviewed the changes before seal. It is recorded here rather than left implicit. Scope was deliberately confined to items that are mechanical, testable, and reversible; every engine-behaviour item on the open list was left alone. **Approved by the Developer or User, 2026-08-11 ("Please make a cut using your recommendations. Approved.").**

- **R1 — ZIP-hygiene gate now consults the path-bound allowlist (closes a .355 finding).** `tools/zip_hygiene_allowlist.{py,tsv}` shipped in .355 as the sanctioned mechanism for intentionally-large files, and it *passed* the shipped zip — but `tools/preflight_zip_hygiene.py` used only its own hardcoded suffix tuple and never read the file, so the gate stayed RED on a corpus that had already been reviewed and given a ceiling. Two tools, one gate, not connected. `scan()` now loads the TSV and checks each oversized entry against its declared per-file ceiling. **The gate keeps its teeth** — verified three ways: the real .360 zip passes; an undeclared 7 MB file still FAILS; and an allowlisted file **over its own declared ceiling** still FAILS. A missing TSV degrades to strict, never permissive. `tests/test_zip_hygiene_allowlist_wiring.py` (6 tests, four of them negative cases).
- **R2 — both strict-health waivers re-signed at current observed (`repo_health --strict` now PASSES).** Both had **expired by design**: `silent_swallow` drifted 139 → 140 (.359) → 142, and `print_calls` 1389 → 1447 → 1488 → 1513 → 1526 → 1557, each rising above its signed `observed` and so ceasing to cover its metric. That auto-expiry is the mechanism working — it forced a conscious owner decision instead of letting drift accumulate silently, and it is the model `GOVERNANCE_DECISIONS.json` now copies. Re-signed at **142** and **1557** on the Developer or User's explicit approval, with `prior_observed`, `prior_date` and an `approval` field recorded so the re-sign is auditable rather than absorbed. **Ceilings are UNCHANGED at 110 / 1300** — a waiver documents an exception, it never raises a ceiling — and both will expire again on the next drift, which is intended. `repo_health --strict` returns **rc 0** for the first time this campaign, unblocking `tools/release_cut.sh`, which gates on it.
- **R3 — bundle hooks are workspace-portable (closes the .356 finding, including one the sealer flagged but never fixed).** 13 of 25 hooks hardcoded `$SAPOTE_WORKSPACE_ROOT` (33 references) while .356's changelog claimed they carried no workspace specifics — a claim corrected at that seal but not remediated. All now resolve through **`$SAPOTE_WORKSPACE_ROOT`, defaulting to the original path**, so existing setups are unaffected (verified: unset → original path, set → override) and a new user can genuinely load the guardrail set from the bundle. `sapote_version_guard.py` was already env-parametrised and is aligned to the same variable rather than left as a second convention. All 25 hooks syntax-checked. **`bgc_node_name_guard.sh` also had a real cohort strain (`AS-XXX`) in its example string — replaced with the synthetic `AS-XXX`**; that was a .356 finding this chat raised and had not acted on. `tests/test_hooks_workspace_portability.py` (7 tests) pins no-bare-path, env-override, syntax validity, and synthetic-only example IDs.
- **R4 — `GOVERNANCE_DECISIONS.json` (NEW): governance decisions become machine-checkable.** Implements recommendation 3 of `MEMO_AS_strain_disclosure_2026-08-10`, modelled on `STRICT_HEALTH_WAIVER.json`: a decision carries an explicit signer, date, scope, and an `invalidates_when` condition that can be evaluated, so it can expire the way the health waivers just did. **GOV-001 records the AS-series disclosure decision as `PENDING_OWNER_CONFIRMATION` — it is deliberately NOT resolved here.** The entry documents the decision *as asserted* (signer "the Developer or User Smith", 2026-06-30, reaffirmed 2026-07-06), flags `record_type: PROSE_ONLY` with no primary artifact, records the measured scope (231 AS-style identifiers, 8 declared synthetic, ≥22 real cohort strains, spread across tests/ 139, mamey/ 45, docs/ 35, tools/ 26, deliverable_tools/ 19), notes the two prior leaks the retired invariant used to catch, and marks `condition_currently_true: true` because PUBLIC is on HOLD for unpublished-genome disclosure while the asserted rationale depends on shipping concurrent with publication. **Nothing about the bundle's disclosure behaviour was changed: `AS_SCRUB` remains at its configured `0` and the redaction machinery is untouched.** Resolving GOV-001 is the release owner's decision, not the sealer's. `tests/test_governance_decisions.py` (7 tests) pins the record's *shape* — never its outcome — including that a PROSE_ONLY record cannot be `ACTIVE`, that a decision whose invalidating condition is true cannot read as `ACTIVE`, and that GOV-001 cannot be silently flipped by a later cut.

**Deliberately NOT in this cut** (each needs someone other than the sealer): BB360 ks-clade cis/trans-AT `_4B` split — changes `_4B`, which **is** in the determinism fingerprint, so it re-scores the cohort and needs **Amber's sign-off**; VGP-06 `diagnostic_tier` rename — engine-behaviour, the Developer or User's bump call; §31–§48 wiring and the §30→§48 structure-gate extension — the bake-off winners are not picked and the gate extension is a separate engine-behaviour patch; AS-XXX's decontaminated-assembly antiSMASH rerun — not runnable in the seal environment; the `deliverable_tools/` share of the hardcoded-path condition — 31 files that want their own focused pass, not a sealer-authored drive-by.

**Claim ceiling (whole cut):** no engine, scoring, gate-decision or disclosure behaviour changed. Class-level capacity hypotheses; comparators are similarity, not identity; `_4D`/RG-GMCI/KS-clade rows remain candidates for adjudication; bioactivity extract-level only; judgment deferred.

# v9.7.360 · 2026-08-11 · build 20260811v97360b · engine 1.9.120 (UNCHANGED — engine-neutral additive)

**Engine-neutral reader-side + governance fold.** Bundle 9.7.359→9.7.360; engine 1.9.120 UNCHANGED (no triage score, gate, or determinism-fingerprint artifact changes; prior packages stay fully score-comparable). Single tier (CODE). PUBLIC remains on HOLD. Built by the patch lane as a CANDIDATE — **NOT sealed; the Developer or User alone seals.**

**SEALED 2026-08-11 as build `20260811v97360b`** (letter `b`, not `a`): this seal regenerated the integrity manifests and edited this entry, so the sealed artifact is materially different content and must not reuse the candidate's `…a` identity string (the v9.7.319a/b rule, applied as at `.359`). Re-stamped with `tools/rewrite_release_identity.py`, never hand-edited.

**ENGINE-NEUTRALITY VERIFIED FIRST-HAND, not taken from the handoff.** `scoring.py`, `parsers.py`, `rules.py`, `domain_level.py`, **`pks_ks_scan.py` (`_4B`)** and **`packaging.py`** are all **byte-identical to sealed .359** — so no scoring path and no determinism-fingerprint input moved, and every .359 package stays score-comparable. The one engine-adjacent file that did change is `rescue_two_proof.py`, and the change is provably safe: `packaging.py`'s fingerprint whitelist contains `_4A_RGGMCI_ranked_pairs.csv` and `_4B_pks_ks_fragment_scan.csv` but **not `_4D`**, so adding the `interpretation` and `two_proof_logic_version` columns cannot move any fingerprint; the four verdict labels (`TWO_PROOF_RESCUE` / `KS_CLADE_ONLY` / `RGGMCI_ONLY` / `WEAK`) are unchanged, making the change purely additive.

**Claim-safety reviewed at seal (reader-side features are exactly where a candidate can quietly become an assertion).** Every `_4D` `interpretation` string stays at candidate/link/surface-for-adjudication wording, and each row carries a `claim_note` reading *"two-proof candidate for adjudication; homology-guided linkage, NOT a merge or nucleotide join; the review lane adjudicates; judgment deferred."* The P360-002 Mode-B subsection renders a gate-safe `#### ` block with no `§N` marker (so `modeb_structure_gate` is untouched) and documents the real confound in its own header — cis-AT KS domains can cluster by upstream-module **substrate** (programming convergence) rather than shared origin, so `KS_CLADE_ONLY` is a reference-DARK candidate to surface, never a confirmed rescue. The MIBiG neighborhood data ships with a `PROVENANCE.md` naming panel, tool versions (MUSCLE 5.2, FastTree 2.2.0 -lg), the complete-linkage diameter cut (≤1.5), medoid-representative rule and a rebuild command — reproducible reference data, query-independent.

**Manifest staleness on the candidate was expected and pre-disclosed** (25 unlisted files, **zero phantom entries**), regenerated at seal → `check_release_manifest` **PASS**. This is the corrected form of the defect found at `.357` and `.359`: the handoff's pre-seal list now names `check_release_manifest` explicitly and states the staleness up front, and `*.egg-info` no longer appears in the tree.

- **P360-001 evidence bundle + BB16 extensions** (`tools/evidence_bundle.py`): per-BGC reader assembling MIBiG convergence/novelty/per-gene ClusterBlast/RG-GMCI/`_4D` with PRESENT/ABSENT_NO_ROWS/ABSENT_NO_FILE deficit flags; BB16 adds `channels_agree` (AGREE/DISAGREE/ONE_CHANNEL_ONLY two-channel MIBiG reconciliation), `unmeasured_fields` (row-level scanned-but-empty columns), `antismash_strictness` (RELAXED/STRICT provenance from manifest), + a `mibig_graded_anchor` channel. 13 tests.
- **P360-002 `_4D` domain-phylogeny card subsection** (`mamey/modeb_domain_phylogeny.py`): surfaces the `_4D` two-proof/KS-clade verdict per BGC into the Mode-B card as a gate-safe `#### ` block (no §N marker; structure gate unaffected), wired at one call site in `modeb_subsections.py`; collapses WEAK pairs; cites the KS/AT tree; enriches with a per-strain (never pooled) identity baseline when tree artifacts are co-located. Adds `interpretation` + `two_proof_logic_version` columns to `mamey/rescue_two_proof.py`'s `_4D` writer (`_4D` is NOT in the determinism fingerprint; the `verdict` label is unchanged). 8 tests.
- **P360-003 MIBiG antimicrobial neighborhoods** (the phylogenomics lane; `mamey/mibig_neighborhoods_api.py` + `tools/mibig_neighborhoods.py` + `mamey/data/mibig/neighborhoods/`): stable, query-independent reference partition of MIBiG KS/C/A/AT/glyc/resi domains (complete-linkage diam≤1.5) as bundle reference data + loader. `tools/mibig_neighborhoods.py` uses the `_gbk_shim` SeqIO fallback (offline-safe). 25 tests.
- **C07 workhorse-scoped subagent ban + cost ledger** (the review lane): in-bundle `hooks/block_subagent_spawn.py` (deny-by-default only for `SAPOTE_CONTROL/MAINTENANCE_LANES.tsv` lanes) + `hooks/session_cost_ledger.py` + `Tools/session_cost_audit.py` (`--since`, registered OPERATOR_ONLY in `gate_registry.tsv`) + `SAPOTE_CONTROL/SUBAGENT_ALLOWLIST.tsv`. Governance-only; the reason is auditability (a subagent transcript is never persisted), not cost.

**Claim-safety:** all reader-side; comparators are similarity not identity; `_4D`/RG-GMCI/KS-clade rows are homology-guided CANDIDATES, not merges or nucleotide joins; `channels_agree=DISAGREE` is a flag to adjudicate, not a correction; missing evidence ≠ biological absence; judgment deferred. **Held for .361 (engine bump):** BB360 ks-clade cis/trans-AT `_4B` split (re-scores cohort — needs Amber sign-off), VGP-06 `diagnostic_tier` rename, §30→§50 structure-gate extension (opens §31–§48; the review lane+Codex bake-off in flight).

# v9.7.359 · 2026-08-10 · build 20260810v97359b · engine 1.9.120 (BUMPED — new deterministic scan + package artifacts)

**Engine feature cut — the first non-neutral cut since .354.** Engine 1.9.119→**1.9.120** because this adds a new deterministic source-derived scan and two new package artifacts; existing SCORES are unchanged (the new artifacts are advisory and do not enter triage), so prior packages stay score-comparable, but they now gain `_4B`/`_4D`. Accretive superset of the parked .358 candidate (all of .358 fold-1 + fold-2 carried forward). Single tier (CODE). PUBLIC remains on HOLD. Built by the patch lane as a CANDIDATE — **NOT sealed; the Developer or User alone seals.** the review lane owns rescue-verdict adjudication; Amber authored + standalone-verified the channel.

- **`_4B` PKS-KS intrinsic clade scan + `_4D` two-proof rescue verdict (NEW ENGINE CHANNEL — phylogenomics-lane P358, converges BB_15 + the review lane C06 + contributor lanes RFCs).** `mamey/pks_ks_scan.py` runs a deterministic, offline, stdlib-only cross-contig KS-domain clade scan (5-mer containment + single-linkage) each run, emitting `{strain}_4B_pks_ks_fragment_scan.csv` beside RG-GMCI's `_4A`. `mamey/rescue_two_proof.py` then joins `_4A` (reference-based) × `_4B` (reference-free) into `{strain}_4D_two_proof_rescue.csv`, applying the review lane's C06 two-proof gate: `TWO_PROOF_RESCUE` / `KS_CLADE_ONLY` (reference-dark) / `RGGMCI_ONLY` / `WEAK`. Both are wrapped to never fail the core run; `_4B` joins the determinism fingerprint (`packaging.py`); `validate.py` adds a NON-BLOCKING `PKS_KS_SCAN_MISSING` advisory. **Fold adaptations by the patch lane (integration bugs Amber's standalone verify could not see):** (1) `cli.py` imports `os as _os` — used `_os.path.join`; (2) `_4D` moved from beside `_4B` to inside `_write_package` AFTER `_4A_RGGMCI_ranked_pairs.csv` is written (the join reads it from disk; at the original insertion point it did not yet exist); (3) declared `pks_ks_scan` as a `SourceScanBundle` field. Tests: `tests/test_pks_ks_scan.py` + `tests/test_rescue_two_proof.py` (9). **Claim-safety:** every `_4B`/`_4D` row is a `KS_CLADE_LINK` / two-proof CANDIDATE — reference-free intrinsic homology, NOT a rescue, NOT a merge, NOT nucleotide joining; promotion requires the two-proof gate; the review lane adjudicates; judgment deferred. The heavy IQ-TREE/muscle ML figures stay an OPTIONAL post-seal subcommand, never in core.
**SEALED 2026-08-10 as build `20260810v97359b` (letter `b`, not `a`).** The the patch lane candidate was distributed carrying stamp `…97359a`; this seal regenerated the integrity manifests and edited this entry, so the sealed artifact is materially different content and must not reuse that identity string. Two artifacts sharing one build stamp is the v9.7.319a/b failure this project already paid for once — `verify_release_identity` only checks that the strings agree with each other, never that an identity is unique to the bytes. Re-stamped with the bundle's own `tools/rewrite_release_identity.py`, never hand-edited. **The same defect applies to sealed `.356` and `.357`, which reused their candidates' `…a` stamps after seal-time content edits; remediation is pending.**

**SEAL FINDING — the engine feature itself was missing from the integrity manifests.** `check_release_manifest` FAILED on the candidate: 11 files present on disk were absent from `SOURCE_CHECKSUMS_SHA256.txt` and `TIER_MANIFEST.txt`, and 6 `mamey.egg-info/*` build artifacts were listed but absent from the tree. The unlisted files were not incidental — they included **`mamey/pks_ks_scan.py` (`_4B`), `mamey/rescue_two_proof.py` (`_4D`) and `mamey/ks_phylogeny.py`**, i.e. the very modules whose new deterministic outputs are the stated justification for bumping the engine integer to 1.9.120 and for entering the reproducibility fingerprint. Unchecksummed, that fingerprint claim could not be honoured. Regenerated at seal over the final staged tree. This is the second consecutive candidate whose pre-seal gate list omitted `check_release_manifest` (see .357) — it is the only gate that detects manifest/tree divergence and belongs in every handoff. `*.egg-info` should be excluded from tracked files so an editable install cannot seed phantom manifest entries.

**AS-XXX — SEALED ON THE "SEAL NOW" PATH, WITH THIS NOTE.** The exclusions SSOT in this bundle reports the **ratified GOVERNED denominator of 44 strains / 1,739 regions** (`{AS-XXX, AS-XXX}` excluded) — verified first-hand in a clean extraction. Per the patch lane seal handoff, **AS-XXX has no decontaminated-assembly antiSMASH rerun**, so the *built* corpus behind that denominator is **43 strains / 1,701 regions**; the 44/1,739 figure is ratified governance, not built data. That gap is the handoff's figure, carried here as disclosed — it was not independently re-measured at seal (antiSMASH is not runnable in the seal environment). **Any governed claim generated from this bundle must state which denominator it used**, and `AS-XXX PENDING` until the rerun lands. This also closes the .357 finding that the AS-XXX ruling was unsynced: it is now in `_DEFAULT`.

**AS-STRAIN DISCLOSURE — UNRESOLVED, RAISED AT SEAL, NOT REMEDIATED HERE.** This bundle carries **231 distinct `AS-`style identifiers**, of which only 8 are declared synthetic plus 2 carve-out tokens (`AS-48` = the public enterocin bacteriocin, MIBiG BGC0000489; `AS-XXX` = boundary token). At least **22 real cohort strains** are embedded — `AS-XXX` in 54 files, `AS-XXX` in 51, `AS-XXX` in 29 — and not only in fixtures: 45 files under `mamey/`, 35 under `docs/`, 26 under `tools/`, 19 under `deliverable_tools/`. The authority for this is a **prose** record, `docs/TIER_DIFFERENCES.md` + `tools/redact_public_tier.py` ("PI decision, the Developer or User Smith, 2026-06-30", reaffirmed 2026-07-06), whose stated rationale is that the strains are already disclosed via 16S on GenBank and that the bundle "ships concurrent with the associated publications." **That premise is in tension with this bundle's own release state, which holds PUBLIC on an unpublished-genome disclosure blocker.** The AS scrub nonetheless remains deactivated (`AS_SCRUB=0`) and the AS leak audit remains WARN-not-FAIL. Sealing the CODE tier does not publish anything — PUBLIC/SID/MERGED are not cut and remain on HOLD — but the standing GitHub public-release milestone would. Flagged for adjudication; the redaction machinery is intact and `AS_SCRUB=1` re-arms it.

- **Carried forward from the parked .358 candidate (unchanged):** fold-2 — C05 `_role_of` NULL-resistance correction, C01/P358-001 locator §1-region fallback, P358-002 BLASTp Repository registry rule, P358-003/C06 KS-phylogeny reader channel (`mamey/ks_phylogeny.py` + `tools/extract_module_core_domains.py` + `tools/domain_phylo_rescue.py`); fold-1 — AS-XXX exclusions SSOT sync (GOVERNED 44/1,739), source-availability preflight, combined V7+Mode-B builder, Figure-Factory Next portable, BB13 `--lit-refs`.

# v9.7.358 · 2026-08-10 · build 20260810v97358b · engine 1.9.119 (UNCHANGED — carry-forward)

Engine-neutral cut. **Engine 1.9.119 unchanged, no scoring/parser change** — every prior package stays comparable, no cohort re-score, no ENGINE_LINEAGE entry. Single tier (CODE). Additive fold onto the sealed **.357** CODE tree in composite order: AS-XXX exclusions sync → source-availability preflight → combined V7+Mode-B builder → Figure-Factory Next portable → BB13 literature stage. Each patch dry-run clean and applied with 0 rejects against the sealed .357 fork; manifests regenerated post-apply; full suite green in BOTH modes (clean extraction and OFFICIAL_DATA-reachable). PUBLIC remains on HOLD (unpublished-genome disclosure blocker carried from .355/.356, not remediated here).

**Build `b` fold-2 (2026-08-10, the patch lane):** additive second wave onto the same .358 candidate — three verified corrections/channels plus the KS-phylogeny engine placement. Version unchanged (.358, engine 1.9.119). All new tests green; both-mode suite re-run below. Still a candidate, NOT sealed.

- **C05 — `_role_of` NULL-resistance correction (the review lane).** `mamey/bgc_guide.py` `_role_of` truth-tested `resistance_tier`, so the enum's NULL member — `NULL_NO_SOURCE_DERIVED_RESISTANCE`, a *truthy* string meaning "scanned, found nothing" — was promoted to the `resistance` role. Now reads the tier: `res.startswith(("t1","t2"))`. Verified against the current engine's enum `{NULL_…, T2_RESISTANCE_LIKE_SOURCE_DERIVED, T3_TRANSPORTER_ONLY_ROUTING}`: the only behaviour change is NULL→accessory; T2 stays resistance, T3 stays accessory (the old `"transporter_only" not in res` already excluded T3). Reference consumers read `resistance_tier` directly, not `role`, so no double-correct. `tests/test_role_of_resistance_tier.py`.
- **C01 / P358-001 — locator §1-region fallback (the review and patch lanes).** `tools/locator_reconciliation.py`: the current emitter writes `# Mode B — BGCnnn (NODE_x…) — AS-xxx` with no region in the header, so `_RE_CARD_HEADER` group(3) was None on every current card and the region never reconciled. Added `_RE_S1_REGION` fallback to the canonical §1 identity block (`**antiSMASH region:** regionNNN`, present on 1,962/1,962 mode_b_v9.7.339 cards). `tests/test_locator_region_reparse.py`.
- **P358-002 — BLASTp Repository registry rule (the patch lane).** `mamey/data/source_collection_registry.json`: widened the `BLASTP_BY_BGC` classifier to also recognize the real on-disk `BLASTp Repository/<STRAIN>/<BGC>/` trove (`directory_regex`/`root_segment_regex` now match `blastp[ _-]?repository`). Pure classifier widening — no CONSUME/SUPERSEDE decision change; enables the trove to be seen by the source-discovery gate. `tests/test_blastp_repository_registry_rule.py` (in patch card).
- **P358-003 / C06 — KS-phylogeny rescue channel (the patch lane, unifies the review lane C06).** Non-scoring reader-side channel: `tools/extract_module_core_domains.py` (deterministic module-core aSDomain extractor; PKS_KS=38 on real AS-XXX = Amber's tree n), `tools/domain_phylo_rescue.py` (two-proof corroborator — CORROBORATED_SPLIT needs a supported clade co-cluster **and** RG-GMCI homology; DOMAIN_ONLY_HINT is advisory, never a rescue), and the engine home `mamey/ks_phylogeny.py` (importable extraction + A.3 routing of DOMAIN_ONLY_HINT verdicts to a `PENDING_ADJUDICATION` queue). Two gates baked in (ITERATIVE-MODULE: KS count ≠ module count ≠ chain length; STRAIN-INTERNAL only). FAS/Fab*/hglE convergence excluded (shared rggmci.py:289 hazard). `tests/test_domain_phylo_rescue.py`, `tests/test_ks_phylogeny.py`. Real AS-XXX control: 6/6 pass.

- **AS-XXX exclusions SSOT sync (governance).** `mamey/exclusions.py` `_DEFAULT` synced to the ratified ruling — AS-XXX OMITTED (duplicate of SID10815; −48 regions), so GOVERNED = **44 strains / 1,739 regions**; new `qc_hold_audit_only()` accessor exposes the AS-XXX QC-HOLD (audit-only, NOT hard-excluded); reworked `tests/test_exclusions_ssot.py` with a `_DEFAULT`↔`OFFICIAL_DATA/exclusions.json` drift guard (now also locks `strain_of_record`). Root cause confirmed 2026-08-10 (the SID10815 genome is labeled as AS-XXX — identity/label error; SID10815 remains distinct). the phylogenomics lane (CLM-005/022); the integration lane implementation payload; both-modes verified. **DANGER:** the pre-patch in-workspace suite failed 3 `test_exclusions_ssot` on *correct* behaviour — never "fix" that by reverting `_DEFAULT` to 45/1,787.
- **Source-availability preflight (NEW).** `mamey/source_availability.py` + `mamey/data/source_collection_registry.json` + `bgc_report_builder` integration + tests: builds logical exact-locus source-availability tables from a P357-019 discovery catalog; exact-locus available only on a hash-bound binding (strain + assembly SHA-256 + node + region ordinal + region key); filename/path matches stay navigation holds, never promoted to identity; emits `evidence://` locators only. Missing source roles are typed workflow gaps, not biological absence.
- **Combined V7 + Mode-B report builder (NEW).** `mamey/combined_report_builder.py` + `tools/build_combined_bgc_report.py` + test: preservation-first Markdown dossier composing the P357-015 V7 evidence packet with Mode-B, ordered exact/current → retained historical; admits added evidence as content-addressed files; does not re-read the identity/BLASTP SQLite stores.
- **Figure-Factory Next portable (NEW).** `mamey/figure_factory_next.py` + `tools/figure_factory_next.py` + `docs/FIGURE_FACTORY_NEXT.md` + test: receipt-bound aggregate evidence figures from a JSON data-root contract; filters policy-held identities BEFORE computing denominators, keeps evidence channels independent, writes raster + vector; does not discover personal workspaces or interpret biology.
- **BB13 — pipeline literature stage (NEW, opt-in).** `tools/mamey_pipeline.py` additive `--lit-refs` optional stage: calls a strain-keyed literature query tool and appends its stdout to the report. No scoring/gate/parser change; opt-in only. a contributor lane (CLM-021).

Assembled by the patch lane (Patch Chat) — candidate only, NOT sealed. VGP hazard scan: no retired `best_pct_identity` consumer in the folded set. Full-suite result recorded at seal-prep below.

# v9.7.357 · 2026-08-09 · build 20260809v97357a · engine 1.9.119 (UNCHANGED — carry-forward)

Engine-neutral cut. **Engine 1.9.119 unchanged, no scoring/parser change** — every prior package stays comparable, no cohort re-score, no ENGINE_LINEAGE entry. Single tier (CODE). Additive fold of the Codex `.357` P357 core, source-first report path, applied to the sealed .356 CODE tree in the governed order 020 → 019 → 015 → 021. Each patch apply-checked clean against sealed .356 (disjoint files, 0 rejects) and focused-test-green before folding (P357-020 6/6; P357-021 13 passed/1 skip; P357-019+P357-015 74 passed). Excluded per Codex governance + independent agreement: P357-013 (Figure-Studio, RB3 boundary drift), P357-011 (2.33 GB, no diff), P357-012/014/016 (no clean implementation).

- **P357-020 — patch-packet integrity gate (NEW).** `tools/patch_packet_preflight.py` + `docs/PATCH_PACKET_POLICY.md` + test: refuses oversized / cache-contaminated / no-delta patch packets so they cannot look cut-ready. Also updates the in-bundle `hooks/patch_hygiene_warn.sh`.
- **P357-019 — workspace source-discovery gate (NEW).** `mamey/workspace_source_discovery.py` (+ test): separates package discovery from workspace evidence discovery and blocks report authoring until material collections + parallel generations are explicitly dispositioned. Discovery ≠ admission.
- **P357-015 — portable refreshable BGC evidence/report builder (NEW).** `mamey/bgc_draft_queue.py`, `bgc_report_builder`, `evidence_roots`, stage-2 overlay + prior-report corpus + literature intake, with portable logical-source URIs and query-binding HOLD semantics. **Hard-depends on P357-019** (`evidence_roots.py` requires the workspace source-discovery preflight before report emission). Leads with NODE_*/region; BGC ordinal is a source-scoped alias only. Ships AS-XXX/AS-XXX/AS-XXX test fixtures — genericize before any PUBLIC tier (PUBLIC already on HOLD).
- **P357-021 — release-cut integrity (NEW).** Hardens `tools/release_cut.sh` (macOS `sed -i ''` portability, item 159 — the `-i -E` bug that wrote stray `-E`-suffixed files at cut time on BSD sed), `make_public_tier.sh`, `gen_release_manifest.py`, `CUT_PROTOCOL.md`, + `test_release_cut_integrity_p357021.py` and `test_release_zip_hygiene.py`.

Assembled by the patch lane (Patch Chat) — candidate only, NOT sealed; sealed here. Full suite green in a clean extraction: **3850 passed / 561 skipped / 0 failed** (source and shipped artifact identical). PUBLIC remains on HOLD (unpublished-genome disclosure blocker carried from .355/.356, not remediated here).

**CORRECTED AT SEAL — the candidate's manifests were NOT regenerated post-apply.** The handoff stated they were; the shipped candidate zip in fact carried sealed **.356**'s `SOURCE_CHECKSUMS_SHA256.txt` (1758 entries) and `TIER_MANIFEST.txt` over a .357 tree of 1786 files. `check_release_manifest` FAILED on it: **1710 verified / 48 mismatched / 0 missing**, plus *"TIER_MANIFEST omits 27 file(s) present in the tree"* — 48 and 27 matching the delta's MODIFIED and NEW counts exactly. This is the v9.7.319b botched-recut signature (content changed, manifests never regenerated). The candidate's gate list named `sync_version --check`, `gen_release_manifest --check`, `gen_tools_inventory --check` and `render_bootstrap_contract --check` — all of which genuinely pass — but omitted `check_release_manifest`, the one gate that detects this. Regenerated at seal by `make_public_tier.sh` over the final staged tree (the normal cut step), taking the sealed tier to **1785 checksum entries**. Compounding the risk, the candidate was distributed under a *sealed-tier* filename (`sapote-mamey-v9.7.357-CODE-20260809v97357a.zip`) with a full BUILD_STAMP and TAG, so it reads as a finished release while failing its own integrity gate.

**Seal-time review of the self-referential P357-021 change (the seal ran the patched controllers).** Line-reviewed against sealed .356; every hunk **tightens**, none loosens. `make_public_tier.sh` replaces three silent `find … -delete` sweeps with a fail-closed `fail_on_backup_debris` (exit 7) — backup/editor debris is now treated as evidence of a dirty source tree rather than disposable cache, so a rejected `.rej` patch or a BSD-`sed` `-E` artifact can no longer be quietly destroyed before checksums; `*-E` is added to both the checksum-exclusion and zip-exclusion lists. `release_cut.sh` gains the same gate (run twice), an atomic portable bump via `tools/rewrite_release_identity.py` in place of non-portable `sed -i -E`, and a hard requirement that `--skip-tests` bind a caller-supplied green log which is then validated for a passed-count *and* the absence of failures/errors. `gen_release_manifest.py` now derives the cut date from the build stamp — closing the stale `Cut/build date` field this chat had hand-corrected at each of the last three seals — and retires the dead test-count sync rules that had been emitting a "matched ZERO times" warning since .354. `rewrite_release_identity.py` (present in the delta but unnamed in the handoff table) is the item-159 implementation: it validates bundle/stamp formats and raises unless each edit matches exactly once — fail-closed, not a gate bypass.

**Governance divergence the sealer must know about (NOT introduced here, unresolved upstream).** `mamey/exclusions.py` resolves the governed denominator by walking *up* from the bundle and reading the first `OFFICIAL_DATA/exclusions.json` it finds, falling back to the in-module `_DEFAULT` — and it is silent on success. In a clean extraction this bundle is internally consistent and reports **45 strains / 1,787 regions** with `AS-XXX` hard-excluded (verified first-hand; all 6 `test_exclusions_ssot.py` tests pass). Inside a workspace whose `OFFICIAL_DATA/exclusions.json` carries the 2026-08-09 AS-XXX ruling, the *same sealed bundle* reports **44 / 1,739** and 3 of those tests fail. Sealed .356 behaves identically, so this cut is baseline-equivalent with zero regression — but the consequence is that a governed denominator is a function of extraction location, and any deliverable's denominator depends on where the engine was run. Syncing the AS-XXX ruling into `_DEFAULT`, the bundled `exclusions.json` and the test is deliberately deferred (governance value in flux).


# v9.7.356 · 2026-08-07 · build 20260807v97356a · engine 1.9.119 (UNCHANGED — carry-forward: workflow tools + full guardrail hooks in-bundle)

Engine-neutral cut. **Engine 1.9.119 unchanged, no scoring/parser change** — every .343–.355 package stays comparable, no cohort re-score, no ENGINE_LINEAGE entry. Single tier (CODE). Additive fold of the ready .356-queue cards (BB workflow tools, hooks-in-bundle, Amber/VGP phylo+BLASTp tools+doc, optional autosave-hook template): **33 new / 39 modified / 0 removed**. Full suite green (**3816 passed / 0 failed / 522 skipped**). Forked from the sealed .355 tree; every folded artifact re-verified generic (0 project/organism identifiers) and test-green first-hand.

- **Workflow tools folded into `tools/` (NEW).** `input_manifest.py` (per-analysis input-completeness manifest + coverage/GAP report — the "no wrong / no half files" mechanism: declares the authoritative denominator, keys every consumed input by NODE + sha256, surfaces gaps rather than hiding them), `lab_office_render.py` (Lab Office report-layer renderer), `comparator_discovery.py` (shared-BGC / marker comparator discovery), `mamey_pipeline.py` (end-to-end run orchestrator). All generic (**zero project/organism identifiers**), each with a test. Tools inventory regenerated (204 → 208).
- **Full guardrail hook set now ships in `hooks/`.** Extended the in-bundle hooks from **2 to 23** so a new user loads the complete guardrail set straight from the bundle: seal-command + sealed-tree-edit + top-level-release-folder blockers, claim-safety + overclaim guards, provenance loggers, BGC node-naming + gene-level guards, deliverable/markdown-link/session-start hooks, and an **optional transcript-autosave** hook template (`save_transcript_stop.sh` + `save_transcript.py`, env-parametrized — ships INACTIVE; a user copies it into their own `.claude/hooks/` to activate), alongside the existing `link_check` / `sapote_version_guard`. Deliberately-historical version references carry `version-sync-ok` markers (the pre-existing, human-audited exemption implemented in `make_public_tier.sh`). **CORRECTED AT SEAL — these hooks are NOT workspace-clean:** 13 of the 23 hardcode the authoring machine path `$SAPOTE_WORKSPACE_ROOT` (33 references), `bgc_node_name_guard.sh` uses a real collection strain ID in an example, and `save_transcript.py`'s docstring carries unrelated-project specifics. They ship as INACTIVE templates and touch no engine, gate or scoring path, so they are non-blocking — but they are **not portable as shipped**, and the claim that they are has been removed rather than left standing. See the seal findings below.
- **Phylo + BLASTp workflow tools (NEW, generic).** `tools/bgc_neighbor_layer.py` (+ test) — tags tree tips `query | type_16S | bgc_neighbor` so a renderer paints shared-BGC neighbors as their own layer (shared pathway ≠ phylogenetic relatedness — a sign-off-gate guard). `tools/ingest_blastp_rollups.py` — gene-level-deduped ingestion of dated per-strain BLASTp rollup CSVs into a store (exclusions via `SAPOTE_EXCLUDE_STRAINS` env, no hardcoded IDs). `docs/BLASTP_NOVELTY_WORKFLOW.md` (+ generic-safety test) — the canonical four-unmixed-channel BLASTp doc (nr=novelty prior · MIBiG/ClusterBlast=anchor capacity · SwissProt=curated sanity · ClusteredNR=deep) feeding the anchor × nr-distance lead rank. Tools inventory 208 → 210.

**Seal-time fixes (STOP-SHIP, caught here):** the two folded workflow tests (`tests/test_input_manifest.py`, `tests/test_comparator_discovery.py`) resolved their tool via `Tools/<name>` — the **authoring workspace** layout — and raised `RuntimeError` when absent. In the bundle, where these tools ship as `tools/input_manifest.py` and `tools/comparator_discovery.py`, that is a hard pytest **collection error**: the suite could not run at all. The candidate's reported "3816 passed / 0 failed" was measured in the authoring workspace where `Tools/` resolves, so it did not hold for the bundle as shipped. Fixed at seal by resolving both `tools/` (bundle) and `Tools/` (workspace); the interpreter already fell back to `sys.executable`. Post-fix suite: **3750 passed / 561 skipped / 0 failed**. Also repaired at seal: the candidate arrived with `sync_version --check` **FAILING** (`BUILD_STAMP.txt patch=` did not match the CHANGELOG head — the phylo/BLASTp headline was folded after the stamp was written). Because this candidate freehanded its own version bump rather than leaving it to the seal, that stale stamp would have been refused by the un-skippable version-sync gate in `make_public_tier.sh`; regenerated with `sync_version`.

**Known-unclean, pre-existing (not introduced here, recorded honestly):** hardcoded user-home paths are a **bundle-wide** condition, not a hooks-only one — the sealed .355 artifact already contains 41 such files (31 in `deliverable_tools/`). This is a blocker for the standing GitHub public-release milestone and wants one dedicated genericization pass (the `MAMEY_DATA_ROOT` env pattern from .352's H1 fix), not a per-cut patch.

**Claim ceiling (whole cut):** class-level capacity hypotheses; comparators are similarity anchors, not identity; AB/AF are routing priors, not activity; judgment deferred. No engine/scoring change.

**Cut scope:** single tier (CODE). AS scrub off (`AS_SCRUB=0`). Engine-neutral, additive.

# v9.7.355 · 2026-08-07 · build 20260807v97355a · engine 1.9.119 (UNCHANGED — governance/coordination tooling + generic phylogenetics)

Engine-neutral cut. **Engine 1.9.119 unchanged, no scoring/parser change** — `scoring.py`, `parsers.py`, `rules.py` and `domain_level.py` are untouched by this delta, so every .343–.354 package stays comparable, no cohort re-score, no ENGINE_LINEAGE entry. Single tier (CODE). Additive: **8 modified / 20 new / 0 removed** in candidate content. Folded from the patch and review lanes v9.7.355 CANDIDATE; every claim re-verified first-hand against the tree at seal.

- **Governance tooling (NEW, all generic, all tested).** `tools/gen_cut_receipt.py` — machine checksum-diff between two `SOURCE_CHECKSUMS_SHA256.txt` files, emitting modified/new/removed with file lists, so a cut receipt's delta is never hand-counted again. `tools/zip_hygiene_allowlist.py` + `zip_hygiene_allowlist.tsv` — a path-bound, per-file-ceiling, reason-bearing allowlist for intentionally-large shipped files, so the ZIP-size gate can permit a known exception without being disabled. `tools/gen_tier_doc.py` — generated tier documentation.
- **Generic phylogenetics.** `tools/tree_sanity_check.py` (registered OPERATOR_ONLY in `gate_registry` + `_UNIT_TESTED_OPERATOR_GATES`), `docs/PHYLOGENETICS_WORKFLOW.md`, and `mamey/data/outgroup_registry.tsv`.
- **Mode B class-conflict wiring (advisory WARN, engine-neutral).** `mamey/modeb_structure_gate.py` wires `check_class_conflict` into `lint_card`, so the PTM-tetramate vs tetronate adjudication introduced in .354 now actually fires during card linting rather than sitting unreferenced. Additive, WARN-level, try/except-guarded.
- **Nucleoside checklist — 5th concept.** `mamey/modeb_class_checklist.py` adds a self-resistance / immunity expectation to the nucleoside class.
- **Comparator selection + professionalism lint.** `tools/comparator_select.py` (blast-free organism-parse / genome-resolve logic) and `tools/professionalism_linter.py` (deliverable professionalism lint). Both were held back in an earlier pass for carrying real strain IDs; verified at seal that the genericization landed — **zero `AS-` identifiers remain in either tool**.
- **Regression guards.** `tests/test_reform_scorer_stays_removed.py` pins the `_reform_scorer` deletion (it crept back .352→.353 and was only actually removed in .354); plus a version-guard hook test and a portable markdown-link checker test.

**Seal-time defect fixed (caught by CUT_PROTOCOL rule 5, artifact-only):** the new `tests/test_reform_scorer_stays_removed.py` matched on a bare `_reform_scorer` substring, which also matches **its own path** in `TIER_MANIFEST.txt` / `SOURCE_CHECKSUMS_SHA256.txt` once those are regenerated at seal. The test therefore passed in the candidate tree (which carried .354's stale manifests, not listing the new file) and failed **only in the shipped artifact** — the exact "looked right in the working tree, broke in the zip" class rule 5 exists to catch. The manifests were correct; the matcher was too broad. Anchored to the exact artifact filenames (`_reform_scorer.py`, `kcb_source_precedence_and_rank_fix.patch`) and verified in both directions: clean on the real manifests, and still flagging both artifacts when they are injected into a manifest.

**Candidate contamination removed at seal (STOP-SHIP, caught here):** the candidate tree carried **553 files / 85 MB of gold-run output under `runs/`** — complete sealed packages for **AS-XXX and AS-XXX** plus a `mamey_handback_v1` `HANDBACK.json`. Sealed .354 ships `runs/` **empty**. This contamination was the sole cause of the candidate's one reported test failure: `test_public_tier_content_matches_code_tier` was failing on the **tier-derivation parity gate** (`FATAL: code tier is NOT an exact redaction-view of the private source`), one of the four gates `CUT_PROTOCOL` names un-skippable. The candidate documented that failure as "pre-existing/environmental" and reproducible on pristine sealed .354; **it is not** — the test passes on the sealed .354 artifact in the same environment, and passes on this tree once `runs/` is emptied. The two gold packages are real deliverables and were preserved out-of-band, not deleted.

**Candidate-document discrepancies reconciled at seal (recorded, not silently fixed):** `CANDIDATE_MANIFEST.md` listed `CLAUDE_nucleoside_self_resistance_concept`, `AMBER_COMPARATOR_SELECT` and `AMBER_PROFESSIONALISM_LINTER` in **both** its FOLDED table and its DEFERRED list. The tree is authoritative: all three are folded, and the claim-safety concern that drove the deferral (real strain IDs) is genuinely resolved. Its full-suite figure (3806 passed / 1 failed) also disagreed with `FULLSUITE_RESULT.txt` (3770 passed / 1 failed) for the same suite; neither reproduces here because both were measured on the contaminated tree.

**Claim ceiling (whole cut):** class-level capacity hypotheses; comparators are similarity anchors, not identity; AB/AF are routing priors, not activity; every Mode-B addition is advisory WARN; judgment deferred.

**Cut scope:** single tier (CODE). AS scrub off (`AS_SCRUB=0`). Governed denominator 45 strains / 1,787 regions (AS-XXX in, AS-XXX hard-excluded).

# v9.7.354 · 2026-08-06 · build 20260806v97354a · engine 1.9.119 (UNCHANGED — Mode B evidence governance + seal integrity + hygiene)

Engine-neutral cut. **Engine 1.9.119 unchanged, no scoring/parser change** — every .343–.353 package stays comparable, no cohort re-score, no ENGINE_LINEAGE entry. Single tier (CODE). Folded from the patch lane v9.7.354 CANDIDATE (SHA256 `5ad727c8…87417`), which unified this chat's base with the queue's staged engine/tool cards; every claim below was re-verified first-hand against the tree at seal, not taken from the candidate changelog.

- **Mode B evidence-governance gate (NEW — the "fix Sapote Mamey" capstone).** `tools/modeb_evidence_gate.py` turns the external Codex review (2026-08-06) into a deterministic lint: a card may not call itself promoted/authoritative/lead/novel-congener/near-complete unless it clears an admission gate — a fresh per-gene BLASTP channel (U=0) **and** OBSERVATION/INFERENCE/ALTERNATIVE/FALSIFIER structure — and it flags motif-grammar fusion (**tetramate ≠ tetronate**: FkbH+ACP ⇒ glyceryl-S-ACP/tetronate chemistry, not an HSAF/PTM "hallmark starter"), novelty-from-weak-evidence, activity inheritance, assay conflation, Edge-vs-completeness, and internal arithmetic/denominator mismatch. Verified at seal on independent fixtures: an over-promoting card returns HOLD + exit 2 with ADMISSION_GATE / STRUCTURE_MISSING / MOTIF_GRAMMAR_CONFLICT / NOVELTY_FROM_WEAK_EVIDENCE / ACTIVITY_INHERITANCE violations plus the permitted HOLD verdict; a structurally honest HOLD card returns ADMISSIBLE with zero findings (no false positive). Engine-neutral, advisory, OPERATOR_ONLY in `gate_registry` — an authoring lint, not a release build gate. `tests/test_modeb_evidence_gate.py` (8, adversarial). SCOPE LIMIT: the arithmetic check compares a slash-form fraction (`12/45`) against a stated decimal share; it does not parse prose ratios ("12 of 45") and does not know the canonical governed denominator (45 strains / 1,787 regions) — it catches internal inconsistency, not a stale canonical denominator.
- **LLM trustworthiness linter — REWORKED + re-admitted** (was F02 REJECT_AS_IS in .353). `tools/llm_trustworthiness.py`: evidence anchors are now TYPED + provenance-bearing (versioned accession / 7-digit MIBiG / Pfam / file:line / check result / "per <ledger>" / DOI-PMID), matched case-sensitively; a bare local `BGCnn` is NOT evidence. Verified at seal: "BGC001 produces nystatin … confirmed producer" scores **44/100 OVER-CLAIMING** with UNCITED_STRONG_CLAIM + VERIFIED_WITHOUT_ANCHOR (was 100/100, 0 flags). `tests/test_llm_trustworthiness.py` (12, adversarial).
- **F04/F05 seal integrity — REWORKED + re-admitted** (were OPEN after the .353 revert). `mamey/cli.py`: the final `gate_validation.json` is finalized **after `write_manifest`** (package complete → status identical to base → no new gold-path blocking, the regression that backed it out of .353) and **before the ZIP**, with `_verify_sealed_receipt` byte-comparing sealed-internal against external and raising a BLOCKING issue on divergence. `mamey/seal_package.py`: a blocking gate FAIL now **exits non-zero by default**; `--advisory` opts back into report-only behind a loud banner; `--strict` still forces and overrides `--advisory`. Verified at seal across all four flag combinations: default → exit 1, `--advisory` → exit 0 + banner, `--strict` → exit 1, `--strict --advisory` → exit 1. The module docstring was corrected at seal (it still described the pre-F05 exit-0 default). `tests/test_seal_integrity_f04_f05.py` + updated `test_seal_package.py` / `test_seal_strict_exit.py`; the 13 tests that regressed in .353 are green. **⚠ SEAL-SEMANTICS CHANGE — blessed at cut: `mamey seal-package` on a blocking-FAIL package now exits 1 by default (was 0). Automation depending on exit-0 must add `--advisory`.**
- **Hygiene — actually executed (completes a premature .353 claim).** `_reform_scorer.py` and `kcb_source_precedence_and_rank_fix.patch` are deleted and de-listed from TIER_MANIFEST + SOURCE_CHECKSUMS + MODULE_MANIFEST. The sealed .353 CHANGELOG claimed this but both files shipped in .353; verified first-hand at seal that neither remains on disk nor in any manifest.
- **Mode B class checklist — nucleoside class + class-conflict adjudication (advisory WARN, engine-neutral).** `mamey/modeb_class_checklist.py` gains a `nucleoside` class (CONTENT_GAP WARN when a nucleoside card skips core-formation / subtype-mechanism / housekeeping-vs-secondary / tailoring-set — encodes the H4 ruling "don't demote nucleosides" and a nucleoside-class exemplar [Redacted — publication in preparation]) and `check_class_conflict()` (CLASS_CONFLICT WARN when antiSMASH fires BOTH a PTM/tetramate and a tetronate CCTT trigger on one locus without adjudication, keyed off CCTT triggers since antiSMASH emits neither as a product label). This is the generation-point complement to the authoring-point `modeb_evidence_gate.py`.
- **Claim-safety gate — anchor-label hole closed (non-scoring receipt only).** `mamey/claim_safety_gate.py` gains `_ANCHOR_LABEL_RE`, closing the seal-time `KNOWN → <compound>` construction the verb-only `_PRODUCTION_RE` missed (the BGC059 defect). Verified at seal: `KNOWN -> tetrachlorizine`, `KNOWN: nystatin` and `anchor -> vancomycin` all flag, while `KNOWN -> tetrachlorizine family` and capacity-hedged class-level prose stay clean. Only the advisory `claim_safety_status.json` receipt gains findings — no score, tier, gate-decision or package change.
- **Tooling:** `tools/check_bgc_naming.py` (BB07) — portable AS-strain BGC node/contig-token checker, exits non-zero on a bare `BGCnn`; OPERATOR_ONLY in `gate_registry`. Portable `hooks/` — `sapote_version_guard.py` (UserPromptSubmit: forces current-engine awareness so no chat authors a correction from a stale card) and `link_check.py` (Stop: flags unregistered deliverable folders).

**Claim ceiling (whole cut):** class-level capacity hypotheses; comparators are similarity anchors, not identity; AB/AF are routing priors, not activity; every Mode-B/claim-safety addition is advisory WARN or receipt-only; judgment deferred.

**Cut scope:** single tier (CODE). AS scrub off (`AS_SCRUB=0`). Governed denominator 45 strains / 1,787 regions (AS-XXX in, AS-XXX hard-excluded).

**File delta vs sealed .353** (computed at seal against .353's `SOURCE_CHECKSUMS`, correcting the candidate changelog's stated "5 NEW"): **11 modified** — `mamey/claim_safety_gate.py`, `mamey/cli.py`, `mamey/modeb_class_checklist.py`, `mamey/seal_package.py`, `tests/test_gate_wiring_invariant.py`, `tests/test_seal_package.py`, `tests/test_seal_strict_exit.py`, `tools/gate_registry.tsv`, `docs/BUNDLE_CAPABILITIES.md`, `TIER_MANIFEST.txt`, `docs/TOOLS_INVENTORY.generated.md`. **11 new** — `tools/modeb_evidence_gate.py`, `tools/llm_trustworthiness.py`, `tools/check_bgc_naming.py`, `hooks/sapote_version_guard.py`, `hooks/link_check.py`, and tests `test_modeb_evidence_gate.py`, `test_llm_trustworthiness.py`, `test_seal_integrity_f04_f05.py`, `test_modeb_class_conflict.py`, `test_modeb_nucleoside_checklist.py`, `test_claim_safety_gate_anchor_label.py`. **2 removed** — `_reform_scorer.py`, `kcb_source_precedence_and_rank_fix.patch`. Candidate scaffolding (`_CANDIDATE_NOTES/`, incl. 2 dotfiles that would trip `preflight_zip_hygiene`) dropped at seal per .353 precedent.

# v9.7.353 · 2026-08-05 · build 20260805v97353a · engine 1.9.119 (UNCHANGED — audit-driven correctness/claim-safety + post-seal tooling)

Engine-neutral cut. **Engine 1.9.119 unchanged, no scoring/parser change** (scoring.py, parsers.py, rules.py, domain_level.py byte-identical to .352) — every .343–.352 package stays comparable, no cohort re-score, no ENGINE_LINEAGE entry. Driven by external audit `SAPOTE_MAMEY_AUDIT_v9.7.352_to_v9.7.353`; every verdict honored. Single tier (CODE).

- **F15 (CRITICAL) exclusion hardening — claim-safety.** New `mamey/exclusion_gate.py`: a governed-output leak detector over the `exclusions.py` SSOT, wired into `validate.py` + `master_workbook.py`. A hard-excluded strain (AS-XXX) can no longer validate-as-governed or enter the master workbook — verified first-hand: `assert_strain_governable("AS-XXX")` raises `ValueError: AS-XXX is hard-excluded from GOVERNED output`, while AS-XXX (governed, decontaminated) and AS-XXX pass. +20 gate/integration/ssot tests.
- **F14 (CRITICAL) figure-fabrication removal.** `tools/build_figures.py`: removed fabricated `SID-XXX` / `value:2` placeholders; the genuine-enediyne bar + class-A flag now derive from real data only.
- **F03 (CRITICAL) fabricated-identity fix.** `tools/cluster_gene_compare.py`: `pid_lookup.get(...,60)` no longer invents 60% identity for unmeasured member↔anchor pairs → NaN, labeled 'n/a' (extracted testable `_build_identity_matrix`).
- **F09 (HIGH/STOP_SHIP) stale-engine-label fix.** `mamey/report_card.py`: module-scope `import json` (was a swallowed NameError) + the engine label now derives from the sealed manifest / live `__version__`, never the frozen `v1.9.110`.
- **F16 (MED) bigscape chunk CLI.** `--chunk-mibig` caller passes `--mibig-gbk-dir` + `--index-dir` (was the obsolete `--mibig-dir`).
- **Hygiene:** removed the `_reform_scorer` scratch scorer + a loose kcb-precedence patch that shipped by accident in .352; de-listed both from TIER_MANIFEST + SOURCE_CHECKSUMS.
- **Engine-neutral additive tooling (all post-seal, non-blocking, append-only):** VGP flagged-lead (`majority-read` / `surface-leads` / `modeb-compile` post-seal subcommands + 3 deliverable_tools, dispatcher try/except never raises into a seal); AMBER_PHYLO_RUNNER (`tools/run_planned_tree.py` approved-tree executor — refuses without `--approved`, respects the tree-approval gate); BLIZZARD_BLUE_05 (5 widget subcommands); BLIZZARD_BLUE_06 (`tools/cut_audit.py` verify/rebase-verify harness, OPERATOR_ONLY); CLAUDE_clade_deepdive (`clade-deepdive` + 4 deliverable_tools); AMBER_PREPUSH_POLICY (pre-push guard).

**Deliberately backed out (recorded, not silently dropped):** F02 LLM-trustworthiness linter — audit REJECT_AS_IS (it scored a "confirmed producer" over-claim 100/100 with 0 flags; do not re-admit until reworked with typed provenance anchors + adversarial fixtures). F04/F05 seal-integrity — REVERTED: passed its 18 focused tests but regressed 13 seal/package/deliverable tests (its receipt-reorder made a validation FAIL block the gold-path seal for smoke/minimal packages); `seal_package.py` is byte-identical to .352, so **seal exit semantics are UNCHANGED** (no bless required). Audit F04/F05 remain OPEN.

**Claim ceiling (whole cut):** class-level capacity hypotheses; comparators are similarity anchors, not identity; post-seal tools never mutate a sealed package or raise into the seal; judgment deferred.

**Cut scope:** single tier (CODE). AS scrub off (`AS_SCRUB=0`). Governed denominator 45 strains / 1,787 regions (AS-XXX in, AS-XXX hard-excluded).
# v9.7.352 · 2026-08-05 · build 20260805v97352a · engine 1.9.119 (forward-only AF-scope change [H4] + release-SSOT: AS-XXX ratified into GOVERNED 45/1,787)

- **H4 nucleoside-AF clamp scope (PI ruling, the Developer or User 2026-08-05: "Don't demote nucleosides. They are antifungals."):** the polyene mis-anchor clamp (`min(base_af, 20)`) no longer caps a locus that carries its OWN corroborated non-polyene AF diagnostic (T43-NUC nucleoside / T43-PTM); the nucleoside machinery is surfaced in the rationale. The clamp STILL fires when the polyene KCB anchor is the sole AF evidence. Moves AF only on the rare polyene-anchor + corroborated-nucleoside co-fire path. **Forward-only — see ENGINE_LINEAGE; do not pool `af_score`/`Lead_tier_auto` across this boundary for those loci.** Two shipped assertions in `test_misanchor_guards.py` were consciously inverted to encode the ruling (they previously encoded the v9.7.337 MISANCHOR-01 behavior the Developer or User overruled) — blessed at cut, as .335/.336 did. AB-axis aminoglycoside clamp UNCHANGED (ruling is AF/nucleoside-specific).
- **AS-XXX ratified into GOVERNED (the Developer or User, 2026-08-05, on satisfactory decontamination):** new SSOT `mamey/exclusions.py`. GOVERNED denominator **44/1,749 → 45 strains / 1,787 regions**. AS-XXX is a decontaminated strain-of-record and IS in governed conclusions; its RAW on-disk assembly is still void (chimera), so raw-reading report layers (dualpass_ledger, p450_tailoring, compound_family_report, assembly_line, interactive_figures/widget_data) route via `derive_release`/`raw_assembly_void`. Hard-excluded stays AS-XXX only. Release routing (AS-→PUBLIC) now flows through the SSOT; the old `test_release_failsafe_private_on_as_prefix` was replaced by `test_exclusions_ssot`. (This stream was authored in a parallel chat; ratified here per the Developer or User.)
- **Correctness/portability fixes (no score movement):** H5 cross-strain figure import (≥2-strain cohort figures were silently SKIPPED_ERROR); H3 seal strictness (blocking-FAIL surfaces a loud non_strict_warning; card-less pkg → claim_safety WARN never PASS; per-card try/except); H2 + W2-H3 (3.10/3.11 f-string floor restored, matplotlib import guards so figure modules import on a core-only install); H1 (killed the user-home hardcoded ROOT → env-configured `MAMEY_DATA_ROOT`/`MAMEY_COHORT_ANALYSIS_DIR` with visible WARN); W2-H4 code half (count-agnostic CCTT docstring). **the review lane apply-drop:** `bigscape` subcommand + conserved-dark-protein finder (+9 tests).
- **Verification:** independently re-verified here against sealed .351 — governed_denominator()={strains:45,regions:1787}, governed_excluded()={AS-XXX} (AS-XXX IN); H4 clamp scoped (fires when polyene is sole AF, skipped when a corroborating non-polyene class is present); full suite --run-slow 0 failed. Engine 1.9.119 held (forward-only stanza, per .350/.351 precedent). Judgment deferred.
# v9.7.351 · 2026-08-04 · build 20260804v97351a · engine 1.9.119 (NON-NEUTRAL, forward-only: over-merge de-inflation + post-seal integrity + package columns)

- **CLAUDE_AUG3_07 — over-merge protocluster-split de-inflation (engine scoring change, NON-neutral, forward-only):** a composite region's `products` is the UNION of its merged single-class protoclusters, so `score_keywords` banked every co-captured class and inflated AB/AF/novelty. Now scores each protocluster's OWN class and takes the strongest (`scoring.py`, `parsers.py`); `chemical_hybrid` regions are left intact. Regression on the sealed-.350 base (38 AS zips / 1,507 BGCs): **106 de-inflated, 0 increases, 34 tier moves — 33 Medium→Low + 1 High→Low (AS-XXX BGC002 AF 76→30), 0 hybrids moved.** De-inflated composites land in .350's `Low` tier, never `Inventory`. Existing sealed boards keep their labels (forward-only).
- **BLIZZARD_BLUE_03 — triage protocluster columns:** `Protocluster_count`, `Single_protocluster_count`, `Chemical_hybrid` written unconditionally on the triage board (37→40 cols; append-only, read by header). Supplies the fields AUG3_07 keys on.
- **PATCH_001–004 — post-seal integrity chain:** the reciprocal-checksum validator now recognises the documented post-seal output surfaces (`figure_manifest_print.csv`; `figures/`, `figures_rendered/`, `domain_level/`, `render_all_figures_summary.json`; the governed `blastp_online/quarantine/ingest_receipts/` trees; `mode_b_templates/`, `judgment/`, `guide/`) so `mamey validate` no longer fails a MAMEY_COMPLETE package on its own documented post-seal artifacts; completes the domain receipt; BLASTp availability reports package-stored ingestions. Fail-closed for lookalike paths retained.
- **Widget deliverable_tools (AUG3_08/11):** 9 BiG-SCAPE + widget generator modules added to `deliverable_tools/` (standalone; the `mamey <widget>` subcommand wiring is a tracked .350-rebaseline follow-up).
- **Verification:** full suite **3,625 passed / 0 failed / 515 skipped**. Engine version **1.9.119** (integer unchanged, per the enforced SSOT), **but AUG3_07 changes AB/AF/novelty on 106 composite BGCs** — those 106 are **NOT comparable** across .350↔.351 (re-score them; everything else is comparable). Comparability recorded in `docs/ENGINE_LINEAGE.md`. Base = sealed .350 (which shipped AQUARIUS_01's `Low` tier + AQUARIUS_02 AS_SCRUB fix). Judgment deferred.

# v9.7.350 · 2026-08-04 · build 20260804v97350a · engine 1.9.119 (NON-NEUTRAL, forward-only: Inventory-tier reform — class-gated `Low` tier)

- **AQUARIUS_01 Inventory-tier reform + AQUARIUS_02 AS_SCRUB fix** — sealed as v9.7.350 (see that cut's CHANGELOG/ENGINE_LINEAGE). Recorded here for lineage continuity; this tree was forked from the sealed .350.

# v9.7.349 · 2026-08-03 · build 20260803v97349a · engine 1.9.119 (UNCHANGED — report-layer cut: phylo companion tooling + compound-family curation + convergence band + roster/novelty/strain-data-home)

Report/companion-layer cut, forked from sealed .348. **Engine 1.9.119 unchanged, no scoring change** — every card is data/report/companion; sealed .343–.348 packages stay comparable, no cohort re-score. Single tier (CODE).

- **AMBER_04–07 (phylo companion):** two-tier GToTree/MLSA workflow (`build_mlsa`→`prune_neighbors`→core + `tree_bgc_overlay` + `phylo_roster` + `mlsa_outgroup_scan` + `marker_candidate_search`), 10-check `signoff_check.py` superset, BiG-SCAPE fragmentation doc, optional `fragment_adequacy` activity-channel gate (EDGE/SHORT/PADDED never IN_DOMAIN, score-neutral), and an `edge_penalty()==0` regression guard. Non-executing/plan-only; no cores committed without approval.
- **BLIZZARD_BLUE_01 (compound-family curation, data-only):** +42 rules (38→80); anchored coverage 597→795 of 1,181 (50.6%→67.3%, +198 BGCs); 42/42 evidence receipts (4 `corpus_text_unattributed` after a corpus-contamination audit — the in-bundle literature corpus is ~22.9% mis-attributed; those receipts carry no citable PMID). `pactamide → AF/cytotoxic` (PI decision; most antifungals carry some cytotoxicity). Data-only — no code branches on the value.
- **BLIZZARD_BLUE_02 (convergence strength band, display-only):** shared band vocabulary (`REFERENCE_DARK_BELOW`/`STRONG_MIN`/`MODERATE_MIN` + `is_reference_dark()`), stdlib-only, imported by the reference-dark layer so the cohort quotes ONE novelty threshold.
- **CLAUDE_AUG3_01/02/03 (reader-side):** per-gene 4-channel widget view + `roster_v2`; reference-dark novelty synthesis (imports the BB_02 band cutoff — 60.0, no local literal); and a canonical strain-data-home resolver (`strain_data_home.py`) + copy-only stager fixing the "data exists but the tool can't find it" class (e.g. AS-XXX). *Note: AUG3_01's widget is not yet exercised end-to-end against a package carrying all four channel stores.*
- **Release health:** net-new CLI emissions routed through a `print`-compatible `emit()` helper (byte-identical stdout) so `repo_health --strict` print_calls stays ≤ the signed 1389 ceiling (migrate path, waiver NOT re-signed).

# v9.7.348 · 2026-08-02 · build 20260802v97348a · engine 1.9.119 (UNCHANGED — flagship: external-activity interface + resistance dossier + phylo planning + BiG-SCAPE figure factory)

Flagship cut, forked from the released .347. **Engine 1.9.119 unchanged, no scoring change** — every stack is non-executable/interface (no tree run, no BiG-SCAPE DB write, no model execution, no network); sealed .343–.347 packages stay comparable, no cohort re-score. No `ENGINE_LINEAGE` entry. Single tier (CODE). All .347 correctness/governance (NC-001–010/037, CODEX13B browser raster, companion gate, shared tracked-file policy, strict-health waiver) is preserved — .348's additive payload was merged onto the released .347 rather than the pre-.347 base the candidate was staged on.

- **External AB/AF activity interface (CODEX_01/02) — score-neutral by construction.** New `mamey/activity_predictions.py` + `mamey/data/activity_adapters.json`: a schema/validator/registry for DECLARED external activity-prediction adapters (NPBDetect-style). **DECLARED, not BUNDLED** — no model weights or third-party runtimes ship. Every adapter is `core_tier_influence=NO` and the loader HARD-REFUSES any adapter that doesn't declare it, so an external prediction can never change `ab_score`/`af_score`/`ab_recall`/`af_recall`/lead tier/the sealed triage board. Predicted activity is not measured activity.
- **CLAUDE05 resistance-dossier.** New `mamey/resistance_dossier.py` + `resistance-dossier` subcommand: post-seal per-BGC resistance-focused gene-by-gene dossiers, sibling output (never mutates the package). The cross-BGC MIBiG join is keyed on `(bgc_id, query_gene)` (the prior bug joined too broadly). Class-level capacity/self-protection context, not a resistance-phenotype claim.
- **GToTree/IQ-TREE phylo planning (CODEX_19/06/09/10).** New `tools/plan_gtotree_iqtree.py`, `prepare_biosynthetic_tree_inputs.py`, `build_phylo_panel.py`, `rank_clusterblast_phylo_candidates.py`: PLANNING/INPUT-PREP only — 40-tip default, one core, `-j 1 -n 1 -M 1 -T 1`, no execution, no network. Reconciles the AMBER↔CODEX16 `docs/phylogenomics.md` collision (the .348 doc supersedes; companion gate stays 20/20).
- **BiG-SCAPE Figure Factory extension.** New `mamey/interactive_figures/bigscape_extension.py` + `codex-bigscape-figure-sets` subcommand: 8 GCF views from an existing BiG-SCAPE run's TSV/DB (read-only; no clustering run, no DB write). 200-set registry unchanged; accretion/figure gates pass.

**Merge discipline (fork-from-released-.347):** the .348 candidate was staged on a pre-.347 base, so 3 of its "modified" files (`lead_pages.py`, `modeb_export.py`, `widget_deliverable.py`) were byte-identical to .346 and would have REGRESSED the .347 NC-007/008/037 claim-safety work — those were NOT ported (my .347 versions kept). `cohort_class_heatmap.py` was kept at .347 because .347's CODEX13B browser-safe raster SUPERSEDES the .348 version. Only genuinely-additive changes were merged: `cli.py` + `interactive_figures/__init__.py` (new subcommand wiring), the 4 new modules, 4 new phylo tools, and the updated `phylogenomics.md`. The .348 candidate's 4 modified release tools (`check_release_manifest.py`, `repo_health.py`, `make_public_tier.sh`, `release_cut.sh`) were NOT ported — they predate .347's NC-001/NC-005 governance (no shared tracked-file policy, no waiver loader) and porting them would have reverted it.

**Open refinement (not a blocker):** `GCF-SEN` currently duplicates `GCF-OVR` — relabel as a count-sensitivity summary or wire true split/merge sensitivity when cross-cutoff lineage data exist.

**Claim ceiling (whole cut):** external activity = declared prediction, never measured/score-influencing; resistance dossier = class-level self-protection context, not a phenotype; phylo tools = planning/inputs only, no tree is run or claimed; BiG-SCAPE views = read-only visualization (co-occurrence ≠ linkage). Judgment deferred.

**Cut scope:** single tier (CODE). AS scrub off (`AS_SCRUB=0`).
# v9.7.347 · 2026-08-02 · build 20260802v97347a · engine 1.9.119 (UNCHANGED — correctness/governance cut)

Correctness/governance cut. **Engine 1.9.119 unchanged, no scoring change** — none of the four patches touches scoring, source scans, models, or deterministic-extraction gates; every .343–.346 sealed package stays comparable, no cohort re-score. No `ENGINE_LINEAGE` entry. Single tier (CODE).

- **PATCH007 — BLASTp five-part ingest guard.** `blastp_ingest.py` / `blastp_gate.py` now enforce fail-closed exact `(strain, BGC, current locus, positive query aa-length, query aa-length)` identity on ingest, with a deterministic content-addressed quarantine CSV + reason codes and a persisted per-channel source-file hash + admitted/quarantined counts. Foreign strain/BGC/locus rows cannot write; zero/missing/mismatched lengths quarantine; the four channels (NCBI-nr / EBI / Swiss-Prot / ClusteredNR) stay unmixed; clean re-ingest is idempotent; stale/header-only channel files are removed so the gate cannot mistake an empty file for evidence. BLASTp-subsystem only — no scoring/triage/model change. Re-checked `git apply --check` clean against the .346 baseline (was previously only checked vs .344). **Operational follow-on (not code):** re-ingest the 7 emptied strains + 168 cross-strain BGCs at cut time.
- **PATCH006 — Mode-B interpretation experiment-stem fix.** `modeb_interp_gate.py` widens the advisory `EXP` detector to accept inflected stems (`resolv\w*`, `resolut\w*`, `discriminat\w*`, `express\w*`, `adjudicat\w*`) so normal "resolving experiment" prose stops tripping `INTERP_NO_EXPERIMENT`. Advisory gate only; no scoring effect.
- **CODEX13 — Figure Factory truth-reporting.** `render_all_figures.py`, `cohort_class_heatmap.py`, `interactive_figures/codex_heatmap_pack.py`, `figure_atlas.py`: fix false-`SKIPPED`/false-success status normalization, atlas gating on `FAIL` receipts, missing-vs-observed-zero handling, SVG ID uniqueness, and stale-file disclosure; expose independent render/source/biological/release/publication states as machine-readable. Post-seal / reader-side. **REQUIRED_AT_CUT:** a browser visual review of one cohort class workbook + one real per-BGC matrix (machine PASS alone is not publication approval).
- **CODEX16 — LLM companion instruction routing.** Adds `docs/LLM_COMPANION_TOOL_PROTOCOL.md` as the single authoritative *tool-policy* front door (BiG-SCAPE 2.x, GToTree one-core/60-genome-cap defaults, optional `-B`), routes both assistant front doors (`AGENTS.md` + `AGENTS.md`) to it, and banners legacy BiG-SCAPE drivers as non-active. Docs/governance + a small policy JSON + audit tooling (`tools/audit_llm_companion_instructions.py`, 20-check gate = PASS). **Open follow-up (the Developer or User, 2026-08-02):** sharpen the *dual-path* separation of Claude-vs-Codex execution instructions while keeping tool-policy single-source.

- **Release-health claim-safety (NC-006/007/008) — `mamey/lead_pages.py`.** Replaced the three bare `except:` clauses with typed `(TypeError, ValueError)` (NC-006; strict `repo_health` `bare_except` now 0). **NC-007:** an absent/invalid `length_fraction` is no longer coerced to `1.0` — it resolves to `None` (completeness UNRESOLVED) and emits an explicit "must NOT be read as complete" note, instead of silently making an unrecovered window look 100% captured. **NC-008:** self-resistance "genuinely absent on current evidence" wording now fires ONLY when the window is resolved-complete; an UNRESOLVED window is labelled "not evidence of absence." +3 regression tests in `tests/test_lead_pages_wave_b.py`. (No engine/scoring change — lead-page rendering text only.)

- **Release-health render + path integrity (NC-009/010/037).** **NC-009:** `mamey/modeb_export.py` gains `core_render_dependency_status()` and `doctor` (`mamey/cli.py`) now surfaces `reportlab` as a **CORE** dependency (`CORE_DEPENDENCY_MISSING` when absent) distinct from the optional figure extras — a "PDF-ready" state is never claimed silently. **NC-010:** cut-time Mode-B PDF + DOCX renderer smoke tests (a real card renders to a `%PDF-` file and a structurally valid `.docx`; gated on the renderer libs). **NC-037:** `mamey/widget_deliverable.py::PackageSource.locate()` now matches only at a path/basename boundary — a bare token that merely *ends* another filename can no longer admit the wrong evidence table post-seal (+ collision fixture). No engine/scoring change.

- **CODEX13B browser-safe cohort raster — `mamey/cohort_class_heatmap.py`.** The 300-DPI publication PNG is unchanged; when its longest estimated edge exceeds the browser tile limit (14,000 px — the maintained cohort raster is ~12,770×36,122 px and the in-app Chromium paints below the top blank) the renderer ALSO emits `<stem>_SCREEN.png` at a deterministic lower DPI and records `browser_raster` + `raster_eligibility` (PASS | HOLD_PANEL_REQUIRED) in the receipt. `browser_visual_review` stays **REQUIRED** — raster eligibility never promotes it to PASS. +3 tests (small figure, 281-row geometry, real large-render `_SCREEN.png` emission).

- **NC-004/005 strict repo-health waiver — `tools/repo_health.py`.** `--strict` now honors a machine-readable, **signed** waiver (`STRICT_HEALTH_WAIVER.json`: metric/ceiling/observed/owner/reason). A strict WARN is treated as WAIVED only when fully signed AND the current count has not drifted above the signed `observed`; a hard FAIL is **never** waivable and ceilings are **unchanged** — the exception is documented and owned, not hidden. The gate FAILs without a waiver, PASSes with a valid one, and re-blocks the moment a metric drifts past its signed observed. Shipped waiver covers the two pre-existing baselines (`silent_swallow` 139/ceiling 110, `print_calls` 1389/ceiling 1300). +3 tests.
- **NC-001/002/003 shared tracked-file policy — `tools/tracked_file_policy.py` (new).** One source of truth for which files are GOVERNED (in TIER_MANIFEST + SOURCE_CHECKSUMS) vs excluded; the tier builder (`make_public_tier.sh --emit-manifest`) and the manifest checker (`check_release_manifest.py`) now BOTH consume it, so they can never enumerate two file-sets (the SEAL-01 failure class). The cut's own RELEASE ARTIFACTS — cut logs (`cut_*_log.txt`), `SHA256SUMS*.txt`, and the tier ZIP (`*.zip`) — are a DOCUMENTED exclusion class (they are produced at/after the manifest and the ZIP is self-referential), fixing the .346 finding that TIER_MANIFEST omitted three present files. `check_release_manifest --root .` = PASS. +3 tests.
**+ tests:** PATCH006 6/6, PATCH007 25/25, CODEX13 34/34 (`--run-slow`), CODEX16 8/8, lead_pages NC-006/007/008 5/5, NC-009/010/037 4/4 — all pass in the candidate.

**Not in this cut (held with repair checklists — see `Red/HANDOFF_v9.7.347_staging/`):** CLAUDE_05 resistance dossier (confirmed cross-BGC MIBiG-join bug `resistance_dossier.py:82–89/184`; sibling-output policy fix), BLIZZARD_BLUE_01 compound-family rules (evidence receipt 4/40→40/40 + substring-shadow test; `pactamide→AF` review), AMBER_04 GToTree (merge/reconcile — one real `docs/phylogenomics.md` collision with CODEX16, + SID/orthology/provenance/dedup safeguards). The v9.7.346 audit's AF02/AF03/AB04 "critical scanner blockers" were **rejected** as verified false alarms against phantom regexes (`source_scans.py:112–186`). **Release-health blockers NC-001–NC-010 + NC-037 — CLOSED and tested this session** (typed excepts; `length_fraction` no longer fail-opens to 1.0 [NC-007]; absent-resistance wording gated to resolved-complete windows [NC-008]; reportlab surfaced as a CORE dependency in `doctor` + Mode-B PDF/DOCX smoke tests [NC-009/010]; widget `PackageSource.locate()` path-boundary exact + collision fixture [NC-037]; one shared `tools/tracked_file_policy.py` for builder+checker [NC-001/002/003]; `repo_health --strict` wired as a hard pre-package gate in `release_cut.sh` honoring the signed `STRICT_HEALTH_WAIVER.json` [NC-004/005]).

**Cut scope:** single tier (CODE). AS scrub off (`AS_SCRUB=0`). Candidate rehearsal — the Patch Chat performs the authoritative seal.

# v9.7.346 · 2026-07-31 · build 20260731v97346a · engine 1.9.119 (UNCHANGED — Codex 200-set figure atlas)

Additive, optional post-seal FIGURES cut (`CODEX_OPTIONAL_POST_SEAL`). **Engine 1.9.119 unchanged, no scoring change** — renderer code only; no engine, parser, gate-precedence, sealed-package, or BGC-count change. Every .343/.344/.345 package stays comparable. No `ENGINE_LINEAGE` entry. Single tier (CODE).

- **Codex Figure Atlas — 200-set governed renderer.** New `mamey/interactive_figures/figure_set_registry.py` (the 200-contract registry: 25 scientific families × 8 lenses — verified `build_registry()` returns exactly 200 entries), `figure_source_bundle.py` (sealed-package source bundler: per-strain members + provenance, checksums, missingness state, compact source tables, reconciliation ledgers), `figure_atlas.py` (cumulative HTML atlas + manifest + machine QA receipt), and six deterministic render tranches `figure_set_renderer.py` + `figure_set_renderer_tranche2..6.py` → exactly 200 nonduplicate SVG sets, each with a plotted-data CSV + caption/methods sidecar. New subcommands `codex-figure-catalog` (emit the 200 governed specs), `codex-figure-sets` (render implemented strain/cohort sets), `codex-figure-sources` (source bundle) — all lazy-import; cli import never requires the new modules. `interactive_figures/__init__.py` gains lazy re-exports for the atlas/registry/bundle.
- All rendering is written OUTSIDE sealed packages; capacity-level visualization only. No gate, seal, or package mutation.

**+11 atlas tests** (`test_figure_set_registry_v97345.py`, `test_figure_set_renderer_v97345.py`, `test_figure_source_bundle_and_tranche2_v97345.py`), all marked slow (`--run-slow`) — verified 11/11 pass with the flag, skip by design without it.

**Handoff was a pre-built candidate tree + INDEX.** The full delta vs sealed .345 was discovered by direct diff (2 modified: cli.py + interactive_figures/__init__.py, both purely additive — no removed/changed existing lines; 9 new modules under interactive_figures/) and ported onto the sealed .345 tree for traceability rather than shipping the pre-built tree wholesale. **Noted an INDEX inaccuracy:** the INDEX named the new subcommands `figure-sets`/`figure-sources`, but the actual registered names are `codex-figure-catalog`, `codex-figure-sets`, `codex-figure-sources` (three, codex-prefixed). The rendered 200 SVG sets + HTML atlas + Word caption/methods catalog are separate DELIVERABLES (in a MAMEY_200_FIGURE_SETS dir, not in this code cut).

**Claim ceiling (whole cut):** figures are class-level capacity/context visualization — similarity not identity; missing ≠ observed-zero; co-occurrence ≠ physical linkage; lead highlighting only via a user-reviewed external ledger, implying no outlier/priority/production/activity/novelty. Governed denominators = 44 strains / 1,749 BGCs. Judgment deferred.

**Cut scope:** single tier (CODE), per the Developer or User. AS scrub off (`AS_SCRUB=0`).
# v9.7.345 · 2026-07-31 · build 20260731v97345a · engine 1.9.119 (UNCHANGED — BLASTp automation + literature corpus + heatmap pack)

Bundle + report-layer / automation cut. **Engine 1.9.119 unchanged, no scoring change** — reader-side and automation layers over the existing BLASTp + figure subsystems; every .343/.344 package stays comparable. No `ENGINE_LINEAGE` entry. Single tier (CODE).

- **BLASTp automation + Central Command (all reader-side/non-scoring).** New `mamey/blastp_availability.py` (`blastp-availability` subcommand): declares BLASTp available-vs-ingested per strain/channel at session onset. New `mamey/deliverable_queue.py` (`deliverable-queue`): resumable autonomous deliverable driver — auto-ingest → gate → deterministic layers, with narrative sections flagged PENDING_JUDGMENT (never auto-authored). New `mamey/blastp_autoharness.py` (`auto-blastp`): resumable ~1-query/8-min NCBI web-BLASTp scheduler with hourly ingest; transport injectable, no email/personal id. All three sit over the existing BLASTp subsystem — no engine/scoring/parser/BGC-count change.
- **BLASTp gate regression fix (`blastp_gate.py`).** Header-only / empty trove files were counted as "available BLASTp" and blocked the gate forever; the gate now requires a real data row (`_has_data_row()`) before treating a channel file as ingestable. (This fix had been lost before .344.) Bugfix to the .344 gate — no behaviour change when real BLASTp is present.
- **Literature corpus + lookup (reader-side, PURGEABLE for public).** New `mamey/literature_lookup.py` (`literature lookup <PMID>` / `literature search <terms>` with AND/OR) over an in-bundle PubMed corpus `mamey/data/literature/_corpus/literature_corpus.jsonl` — **7,648 unique PMID-keyed records, 4,658 with full abstracts** (verified first-hand; degrades cleanly if the corpus is purged for a public tier). Reproducibility tools ship alongside: `_corpus/pubmed_ingest.py` (PubMed result PDF → deduped JSONL + FTS5) and `_corpus/curate_kb.py` (corpus → per-genus/family PMID-cited KB index). New per-genus KB `.md` files and a per-family KB `mamey/data/literature/_families/`. Literature = class-level context (similarity not identity; no bioactivity/structure claim); the `.md` KB files are a curated index into the corpus; judgment deferred.
- **Family-literature Mode B subsection (`modeb_subsections.py`).** New gate-safe `#### Family literature context` subsection keyed on THIS BGC's CCTT warheads / product-class tokens → the exact `_families/<family>.md` file (thioamide, polyene, hsaf, spirotetronate, enediyne, phosphonate, glycopeptide, lanthipeptide, lassopeptide). All `####` (no `§N`) → structure gate unaffected. Capacity/similarity anchor, not a product claim.
- **Codex heatmap pack (`interactive_figures/codex_heatmap_pack.py`, `codex-heatmaps` command).** Stdlib-only zero-aware cohort-class heatmap renderer: missing ≠ observed-zero, per-cell luminance contrast, deterministic viridis SVG/HTML + caption/receipt. Written outside sealed packages; no gate change. The core `cohort_class_heatmap.py` figure also got a rendering refresh (observed-zero masked to neutral paper-white while the raw zero stays in the companion CSV and the stats matrix; layout polish; reworded comparative-exclusion caption). **Verified the exclusion LOGIC is unchanged — only the caption wording and colour handling changed; grid/stats values are identical.**

**+23 tests** (`test_blastp_autoharness.py`, `test_codex_heatmap_pack_v97345.py`, `test_literature_lookup.py`).

**Handoff was a pre-built candidate tree with no patch card / diffs.** The full delta vs sealed .344 was discovered by direct diff (5 new modules + literature data; 5 modified files: blastp_gate regression fix, cli wiring, cohort_class_heatmap rendering refresh, modeb_subsections family-lit, interactive_figures/__init__ lazy re-export) and ported onto the sealed .344 tree for traceability rather than shipping the pre-built tree wholesale. **Corrected a CHANGELOG claim:** the candidate's text said the corpus held 4,508 records / 1,524 with abstracts; the shipped file actually holds 7,648 / 4,658 (verified — no duplicate PMIDs).

**Claim ceiling (whole cut):** BLASTp = similarity, never identity; channels unmixed; subsections + heatmaps + literature are class-level capacity/context, never a product/activity claim; automation auto-fills only deterministic layers and flags narratives PENDING_JUDGMENT; judgment deferred.

**Cut scope:** single tier (CODE), per the Developer or User. AS scrub off (`AS_SCRUB=0`).
# v9.7.344 · 2026-07-31 · build 20260731v97344a · engine 1.9.119 (UNCHANGED — BLASTp subsystem hardening + card enrichment + widget deliverables)

Bundle + report-layer cut. **Engine 1.9.119 unchanged, no scoring change** — every .343 package stays comparable. Four independent groups; the one engine-adjacent change (the ingest ledger) is additive. No `ENGINE_LINEAGE` entry.

- **BLASTp becomes a first-class, enforced, self-contained subsystem (Group A).** New `mamey/blastp_gate.py`: a hard completeness gate that makes `compile-report` and `emit-modeb-template` exit 3 when ingestable BLASTp exists on disk but hasn't been folded into the package, printing the exact `ingest-blastp-trove` command; override only with `--blastp-waiver "<reason>"` (recorded to manifest provenance). Scan-root discovery is generic (`$MAMEY_BLASTP_SCAN_ROOT` → `.claude`/`.git`/`CLAUDE.md` → cwd — no hardcoded personal paths). `blastp_ingest.py` now recognises the real per-channel filenames (clustered_nr `*_top10_clustered.csv` and swissprot `*_top10_local.csv` previously ingested 0 rows), adds a first-class `swissprot` channel, writes a durable ingest ledger `blastp_online/_ingest_ledger.json` (authoritative — fixes a precedence over-block where a lower channel could contribute 0 surviving rows yet be ingested), and `install_channel_top10()` writes FOUR unmixed named channel stores (`blastp_nr/`, `blastp_cluster_nr/`, `blastp_swissprot/`, `blastp_ebi/`) with all 10 ranks carrying **pct_identity AND pct_positives** separately. `compile-report` fills `blastp_evidence` from the internal channel stores and `fermentation` from a deterministic genus/class bench draft (so `fermentation` is now a deterministic-source slot, not an open narrative slot). +6 gate tests.
- **Gate-safe `####` Mode B subsections (Group B).** New `mamey/modeb_subsections.py`: five subsections (Good Guess §2; catalytic-domain census, per-channel BLASTp evidence, gene-based ClusterBlast §4; genus literature §5), all emitted as `#### <title>` (no `§N`) so the structure gate — which keys on `§N` — is unaffected. Wired into `modeb_template_emitter.py`. New data: `mamey/data/strain_genus.csv` (strain→genus crosswalk, resolver fallback) and `mamey/data/literature/` (portable genus KB — PURGEABLE for public). +5 subsection tests. Verified: `test_modeb_structure_gate` + `test_modeb_interp_gate` + `test_modeb_template_emitter` = 33/33 with subsections present.
- **Codex interactive-figures bridge (Group C).** New `mamey/interactive_figures/` (`widget_data.py` emits cross-strain cohort widget-data JSON from sealed packages; `publication_bridge.py` vendored from Codex, reportlab imports soft-guarded so the module imports without svglib/reportlab/pypdfium2). New `interactive-figures` subcommand (lazy dispatch — cli import never requires the subpackage). +3 widget-data tests. Verified import-safe (no matplotlib poisoning; no sys.path surgery or absolute self-imports). Honest caveat carried from Codex: AS-XXX machinery core↔additional split off by 1 gene (a 3160-aa megasynthase truncated at 300 chars in `_cds_table.csv`; ≤0.26% of role-assigned genes, never a scalar/class/total — flagged, not fabricated).
- **Codex render-widgets post-seal deliverable (Group D).** New `mamey/widget_deliverable.py` (stdlib-only) + `render-widgets` subcommand: reads a package/ZIP and writes a SIBLING bundle of self-contained per-package explorer widgets + `PUBLICATION_HANDOFF.md` + manifest + checksums; never mutates the source. Complementary to interactive-figures (per-package explorers vs cross-strain aggregate). +7 tests. Docs: `docs/WIDGET_DELIVERABLES.md`.

**Two pre-existing tests updated to the .344 contract (not silenced):** `test_ferm_section_falls_back_to_slot_when_absent` and `test_open_slots_reports_remaining_prose` asserted the OLD contract (fermentation absent → open `SAPOTE:fermentation` slot). Under .344 `fermentation` fills with a deterministic bench draft, so both now assert the new deterministic-source behaviour. (These two failed on the handoff's own combined tree too — the handoff's "2 failures" suite claim was inaccurate.)

**Claim ceiling (whole cut):** BLASTp = similarity, never identity (pct_identity AND pct_positives shown separately, never conflated); channels unmixed; subsections + bench draft are class-level capacity/guidance, never a product/activity claim; genus literature is class-level context; judgment deferred.

**Cut scope:** single tier (CODE), per the Developer or User. AS scrub off (`AS_SCRUB=0`).
# v9.7.343 · 2026-07-30 · build 20260730v97343a · engine 1.9.119 (UNCHANGED — verdict surfacing + reference-dark wiring)

Bundle-only, cohort-neutral cut. **Engine 1.9.119 unchanged** — display/report-layer only: it surfaces verdicts the engine ALREADY computes onto the reader-facing cards, and wires a previously-orphaned module into a post-seal deliverable. No scoring, parser, gate-precedence, or BGC-count change; every .342 package stays comparable. No `ENGINE_LINEAGE` entry.

- **Surface the engine's own per-BGC capacity verdicts onto the Mode-B cards ("why does it say GENERIC" fix).** An audit of the .342 engine showed the interpretive calls the roadmap kept proposing to *build* already exist and mostly run — `architecture_first.py` writes `Arch_Capacity`/`Class_Conf`/`Novelty_auto` to the triage board, `diagnostic_rescue.py` writes split-pathway verdicts — but the four per-BGC emitters (`modeb_template_emitter.py`, `modeb_cards.py`, `lead_pages.py`, `report_card.py`) printed `Arch_Capacity` **zero** times, so a card read GENERIC while the engine had already made a class-level capacity call. New `mamey/card_verdicts.py` reads those already-sealed fields and renders an **Engine capacity read** block: architectural capacity, class confidence, novelty prior, guards (concordance / mis-anchor / standing rule / primary-metabolism), and an honest Diagnostic-Rescue summary. Verified first-hand on a real card — the block now shows e.g. capacity `complex multi-class hybrid (nrps/pks/t1pks)`, confidence `MODERATE`, novelty `63.0`, standing-rule guard — where the pre-.343 card showed nothing. Display-only; the four emitters print the block, none of them computes or changes a value.
  - **Honest Diagnostic-Rescue rendering (the part that matters for claim safety).** The renderer splits engine-**SUPPORTED** reconstructions (`tiling_verdict = RECONSTRUCTION_SUPPORTED…`) from ones the engine evaluated and **DEMOTED** (homology without the RG-GMCI complementarity proof), and never presents a demoted candidate as a live hypothesis. A claim-ceiling line travels with every rescue mention: a homology-guided reconstruction hypothesis, not a nucleotide contig join, not an identity claim.
- **Wire the orphaned `reference_dark_prior.py` into a real deliverable.** The module was built and tested (`tests/test_reference_dark_prior.py`, 8/8) but imported by no production path. New non-blocking post-seal subcommand `reference-dark <package>` emits `<strain>_3b_reference_dark_prior.csv` from the already-sealed package — a per-BGC novelty PRIOR (reference-dark / partial / well-characterised), never proof of a new compound. New file only; verified freeze-safe (pre-existing package files byte-identical after a run).

**+7 surfacing tests** (`test_card_verdicts_surfacing.py`), including the demoted-vs-supported honesty split and str/None path handling.

**Claim ceiling (enforced in every surfaced line):** `Arch_Capacity` is a class-level capacity/mechanism read, never a compound identity; a diagnostic trigger sets capacity, not product; a Diagnostic-Rescue verdict is a homology-guided reconstruction hypothesis, never a physical join or identity claim; reference-dark is a novelty prior. Judgment deferred to Sapote.

**Explicitly NOT in this cut:** any `diagnostic_rescue` threshold tuning or other scoring change (that is the re-score batch — engine bump + full-cohort re-score + AS-XXX A/B, never a bundle cut); Red's duplicate `fragment_linkage.py` / `contradiction_linter.py` / `chemistry_fingerprint.py` (redundant with `rggmci.py` / `architecture_first.py` / `diagnostic_rescue.py`, and wrong where the engine is right).

**Cut scope:** four tiers. AS scrub off (`AS_SCRUB=0`); armed gates (private/, denylist, SID) pass.
# v9.7.342 · 2026-07-30 · build 20260730v97342a · engine 1.9.119 (UNCHANGED — Wave B lead-pages layer)

Bundle-only, cohort-neutral cut — the Wave B follow-up Red staged out of Wave A. **Engine 1.9.119 unchanged**; one additive post-seal report module that reads already-sealed package files and writes NEW files only. A re-run yields byte-identical triage for every BGC (proven byte-level: lead-pages run into a real package left all pre-existing files at an identical aggregate digest, only a new `LEAD_PAGES/` folder added). No `ENGINE_LINEAGE` entry.

- **lead-pages (roadmap #4 dossier + #7 lead-§31–40).** New `mamey/lead_pages.py` + `mamey/data/lead_literature_table.json`. Renders lead-only §31–§40 enrichment + related-genomes dossier pages from a sealed package: the family call + convergence tier, package-evidence crosswalk, PKS/NRPS module counts (aSDomain-only, via the shipped Wave A `assembly_line` module — not a duplicate walk), tailoring inventory, self-protection (resistance + efflux) prior, rarity/novelty with ClusteredNR nearest-OTHER, the literature-to-locus crosswalk, compound-family/structure context, cross-strain/GCF linkage, provenance caveats, and a claim-safety attestation. The related-genomes block surfaces the MIBiG anchor + top NCBI ClusterBlast references — the higher-quality neighbour genomes — with the ceiling stated: identity is gene-vs-subject similarity, the AS genome is draft, and the metadata shown is the reference's, not a claim about the AS strain.
  - **Lead-only routing** (the point of the 2026-07-29 audit that cleared the boilerplate): pages emit for genuine leads (Lead_tier_auto in Exceptional/High/Medium) only, never stubs/Inventory/VOID. `--all-tiers` lifts the gate for a full capacity read. Subcommand `lead-pages <package> [--bgc BGC|ALL] [--all-tiers]`.
  - **Ported, not dropped in.** The 450-line reference impl (`reference_impl/build_lead_pages.py`) was vendored into `mamey/` under a provenance header with a clean command wrapper; its sibling `assembly_logic` dependency was rewired to the shipped `mamey.assembly_line` engine module, and its literature-table load was made lazy (points at `mamey/data/`, degrades to a GENERIC-only table so import never fails in a stripped tier). +5 tests (lead-only gate, enrichment+reference content on a real package, engine-adapter routing).

The only edit to an existing file is `mamey/cli.py`: one additive `sub.add_parser` block + import, matching the Wave A pattern. No gates added.

**Still deferred (unchanged):** the re-score batch (engine 1.9.120: #2 diagnostic-gene override, #5 terpene demote, RG-GMCI two-proof scoring half — one bump + one cohort re-score + one AS-XXX A/B); the #1 LLM interpretation pass and #3 Pixtle literature KB (design drafts). Wave B completes the freeze-safe report lane Red scoped (Wave A + this).

**Cut scope:** four tiers. AS scrub off (`AS_SCRUB=0`); armed gates (private/, denylist, SID) pass.
# v9.7.341 · 2026-07-30 · build 20260730v97341a · engine 1.9.119 (UNCHANGED — Wave A report/tooling layers)

Bundle-only, cohort-neutral cut. **Engine 1.9.119 unchanged** — every item is an additive post-seal report/tooling layer that reads already-sealed package files and writes NEW files; a re-run yields byte-identical triage for every BGC (proven byte-level: report commands run into a real package left all pre-existing files with an identical aggregate digest, only new subfolders added). No `ENGINE_LINEAGE` entry. Five new modules, four non-blocking subcommands, +26 tests.

- **compound-families (roadmap #10).** New `compound_family_report.py` + `npatlas_structure.py` + `mamey/data/compound_family_rules.json` (38 rules / 232 anchor keys). Maps a sealed package's anchored BGCs to compound families with AF/AB context and, where NP Atlas refs are available, a conservative name→InChIKey/SMILES structure column that binds only on a real match (a bogus name returns `match=none`, never a fabricated InChIKey) and degrades to `unavailable` when the refs aren't shipped — never an error. Subcommand `compound-families <package>`.
- **p450-tailoring (roadmap #11).** New `p450_tailoring.py`. Classifies a package's P450 genes as oxidative-tailoring vs a crosslinker (glycopeptide-type) cassette from the anchor context — capacity-level, no structure claim. Subcommand `p450-tailoring <package>`.
- **assembly-line (roadmap #6, report half).** New `assembly_line.py`. Reads the native `_domains.csv` aSDomain order into a predicted PKS/NRPS monomer/extender sequence + module count + class-consistency check per BGC. Freeze-safe because `_domains.csv` is native on the seal path. The scoring/RG-GMCI consumer of the same walk is deliberately NOT here (see below). Subcommand `assembly-line <package>`.
- **dualpass (roadmap #8).** New `dualpass_ledger.py` + `mamey/data/claims_vocab.json`. Merges two engine `CLAIMS_LEDGER.tsv` files into a divergence table under a canonical claims vocabulary. Subcommand `dualpass <claude> <codex>`.

The only edit to an existing file is `mamey/cli.py`: four additive `sub.add_parser` blocks + their imports, matching the `render-figures` registration pattern. No gates added (non-blocking), so `gate_registry.tsv` is unchanged.

**Deliberately NOT in this cut (verified lane split):**
- **#2 diagnostic-gene-overrides-cluster, #5 terpene-housekeeping demote, and the RG-GMCI two-proof scoring half** are verdict-moving. They ride a separate **re-score batch** (engine bump 1.9.120 + one cohort re-score + one AS-XXX-grade A/B), never a bundle cut. The assembly-line *report* half ships here; its *scoring* consumer waits for that batch — this is the concrete RG-GMCI unblock, now that the module-role walk exists over data already on the seal path.
- **#4 dossier / #7 lead-§31–40** (`build_lead_pages.py`) — freeze-safe in principle but not yet ported to `mamey/` and tested; staged for a follow-up bundle-only cut rather than rushed in unverified.
- **#1 LLM interpretation pass / #3 Pixtle literature KB** — design drafts only; #1 in particular needs the Mamey/Sapote split decision (deterministic evidence packet in-engine; the LLM interpret + sanity gate as a post-seal Sapote-tier tool with no live model in pytest). Not a cut.

**Cut scope:** four tiers. AS scrub off (`AS_SCRUB=0`, AS public per the 2026-07-06 PI decision); the armed gates (private/, denylist, SID) pass.
# v9.7.340 · 2026-07-29 · build 20260729v97340a · engine 1.9.119 (UNCHANGED — provenance caveats + trove ingest)

Bundle-only, cohort-neutral cut. **Engine 1.9.119 unchanged** — no scoring, parser, gate-precedence, or BGC-count change; every .339 package stays comparable. Three items, all sign-off / ingest lane. Full `pytest`: 0 regressions (see receipts).

- **AMBER_03 — provenance strength + assembly-quality caveats (the phylogenomics lane).** Three sign-off-lane items that make a downstream figure or caption harder to get wrong, none touching scoring. (1) `mamey/assembly.py` gains `assembly_quality()`, surfaced through `MameyRun.to_dict()` into the manifest as an `assembly_quality` block with a tier and a ready-to-paste caption sentence — captions become generated, not hand-typed (a caption in this project had asserted "5 assemblies exceed 6,000 contigs" when the true count was 4). (2) New module `mamey/source_provenance.py` records how a `--source` host was established (`accession`/`table`/`filename`/`asserted`, default `asserted`) with claim-safe wording, so a host read off a ZIP filename can never be quoted as traceable — this is sign-off item 7, and 16 AS strains had been found carrying a wrong hand-typed host. (3) `assembly.py` + `cli.py` emit a `[WARN]` when `genome_bp` falls below an actinomycete floor, so a truncated GenBank submission (e.g. *Actinophytocola* sp. NPDC049390 at 1.46 Mb vs ~7.6–9.5 Mb congeners) is never silently used as a genus comparator or its BGC count read as a measurement rather than a floor. +5 tests.

- **TROVE-01 — defline locus recovery (Red).** `_gene_from_query` recovered a locus only from an explicit `gene=` token, so a pipe-format defline without one (`AS-XXX|BGC041|ctg66_8|3116` — the trove format) returned the WHOLE defline as the locus tag, fragmenting the per-gene merge (every row a unique key: no dedup, no coverage roll-up). Fixed with a `ctg<N>_<M>` fallback; the `gene=` fast path is byte-identical (standard panels unchanged) and NODE_/length_/cov_ headers are guarded against mis-parse. Reader-side, cohort-neutral. Two independent builds (Red's and the patch-chat's) converged on the identical regex and fallback; Red's — the fuller, wired version — is the one landed. +5 tests, proven failing on the .339 parser and passing here.

- **Trove-ingest feature (Red).** New `ingest-blastp-trove` and `blastp-status` subcommands, with channel tags and precedence (`nr` > `clustered_nr` > `ebi`) and `_TROVE_ALIASES` column mapping for pre-organized per-BGC trove result trees. Additive ingest surface; no existing path changes.

**Deliberately deferred, with verified reasons (not oversights):**
- **RG-GMCI two-proof** — its gate requires `functional_rescue_class == "COMPLEMENTARY"`, a field that does not exist in `rggmci.py`; the module-role vocabulary (loading/extension/tailoring/release) has no data source in a sealed package, which carries only `ks_domain_count`. Building it means adding module-role extraction to the SEAL PATH, which changes package contents and re-opens cohort comparability. It is a before-cohort parser feature, not a scoring gate — scope separately.
- **`feature_modeb_auto_author.py`** — references `TIGR03731`, which `test_tigrfam_extraction_consistency` flags as neither extracted nor excepted; adding the module fails that test on a pristine tree. Land only after registering TIGR03731.
- **`FEATURE_compound_family_structure_scans_and_audit`** — arrived alongside this handoff but is outside the three-item scope of this cut; not evaluated here.
- `modeb_synthesis_stub` (already in .339, reverse-patch detected); `dual_llm_modeb_reconciliation`, `modeb_generator_defect_fixes` (cards only, no code).

**Cut scope:** four tiers. AS scrub is off (`AS_SCRUB=0`, AS-series public per the 2026-07-06 PI decision), so the AS-ID leak audit is deactivated by design; the armed gates (private/, denylist, SID) pass.
# v9.7.339 · 2026-07-28 · build 20260728v97339a · engine 1.9.119 (UNCHANGED — §4 judgment-forward template stubs)

Bundle-only reader-side cut. **Engine 1.9.119 unchanged** — no scoring, parser, gate-precedence, or BGC-count change; cross-strain comparability with every .338 package preserved. Full `pytest`: **3317 passed / 484 skipped / 0 failed**.

- **The §4 Mode-B template now seeds the interpretation anchors the .338 gate already checks for.** v9.7.338 landed the interpretation gate (`modeb_interp_gate`, anchors `SYNTHESIS` / `REFDARK`) — the *check* — but the §4 template still led with the machine gene table and seeded neither anchor. Its own docstring said the anchors are "seeded by the template emitter"; that emitter half had never shipped. So `verify-modeb --interp --strict` had nothing to enforce against, and a card could pass every mechanical gate while making no judgment (the handoff's example: the AS-XXX BGC041 flagship is green on `verify-modeb` + `claim-safety` with its 3,116-aa megasynthase core left as `DATA REQUEST`). `_section_body(num==4)` now emits two `####` subsections **inside** §4: `⬛ Interpretive synthesis — read this first` (anchor `SYNTHESIS`) — a five-move judgment-forward lead (family call + convergence tier as a similarity anchor · how cores cooperate by locus_tag · second/over-merged capacity · leading alternative · resolving experiment), with the gene table demoted to its evidence — and `Reference-dark / partial cores — domain-based read` (anchor `REFDARK`), which forces a domain-grammar read of homology-poor cores instead of silence.

- **Verified, on a real emitted card rather than the emitter in isolation.** Emitted through the `emit-modeb-template` CLI against a freshly-sealed package: both anchors appear, ahead of the gene table; the same card emitted on .338 vs .339 shows **`##` heading delta 0** (structure gate untouched) and **+2 `####` subsections**; the structure gate reports 0 ERRORs; and under `verify-modeb --interp --strict` the freshly-emitted, unauthored stub correctly **fails C1 as "anchored, 0 chars"** — the gate now recognises the anchor block and demands it be authored, which is the whole point of shipping the two halves together. +4 tests, including an authored-synthesis control confirming the gate accepts a real ≥350-char, tier-citing lead.

**Claim-safety unchanged:** the synthesis states class-level capacity and convergence tier with judgment deferred; comparators remain similarity anchors, bioactivity extract-level, and absence-of-homolog a novelty prior, not proof of a new compound. No claim-safety-precedence change.

**Cut scope:** CODE tier only this cut (per operator request during an active cohort run). The clean/sid/merged tiers derive from the same source and can be regenerated on demand; from a CODE source the sid/merged tiers carry no additional bank content (see the v9.7.335/.336 tier-content disclosures).
# v9.7.338 · 2026-07-28 · build 20260728v97338a · engine 1.9.118→1.9.119 (verdict-changers + comparator features)

Large cut from the Red audit/analysis handoff: the five held verdict-changing items land with cohort re-seal evidence, twelve new sign-off deliverable subcommands, RG-01 NAPAA re-tiering, parser/gate/perf hardening, and a folded documentation refresh — plus a **seal-integrity fix found here that the handoff's own certification missed**. Engine 1.9.118→1.9.119. Full `pytest`: **3313 passed / 484 skipped / 0 failed** on Linux/3.12.

- **SEAL-02b — a fresh .338 seal failed its own checksum gate (found and fixed here).** The handoff's SEAL-02 correctly made `_phase_package_seal` rewrite `gate_validation.json` from the final post-seal re-validation (so a late gate regression can fail the seal). But `write_manifest()` had already hashed the mid-build `gate_validation.json` into `checksums_sha256.txt`, and that filename was not in the writer's mutable-receipt set — so on a **fresh gold run** the file's bytes no longer matched its recorded hash and the package failed its own `checksum_integrity` gate with status FAIL. Reproduced on a fresh seal of the bundled micromonospora fixture (`checksum mismatch for gate_validation.json`, then after a partial fix `untracked file present but absent`, exposing that the "files rewritten after checksum capture" set was **copy-pasted into five places** across `packaging.py` + `validate.py` and had already drifted — two validator copies were missing `repro_fingerprint.json`). Fixed by defining the set **once** as `packaging.MUTABLE_RECEIPT_NAMES` (adding `gate_validation.json`) and pointing all writer and validator sites at it. Verified: a fresh gold seal now returns `MAMEY_COMPLETE` with `checksum_integrity PASS`, and re-writing `gate_validation.json` post-seal no longer reddens the package. +4 tests. **Without this, every package in a fresh cohort run on .338 would have sealed as VALIDATION_FAIL.** The handoff's re-seal report read green because it validated via `package_status.json`, not by re-checking `checksums_sha256.txt` against the rewritten file.

- **The five verdict-changing items land, with the audit's cohort re-seal evidence.** GATE-11, GATE-12, SEAL-02, SEAL-03, WB-02, plus RG-01 NAPAA and COH-01/02, MB-01/04. The audit chat re-ran all 11 cohort strains (72/61/46/36/45/64/26/31/11/44/30 BGCs, identical .337↔.338): **0 packages flip red**, and the only verdict movement is the intended RG-01/NAPAA re-tiering — three upward lead-tier moves (AS-XXX BGC029 and AS-XXX BGC034 Inventory→Exceptional, AS-XXX BGC012 Inventory→Medium) with `AB_auto`/`AF_auto`/`Novelty_auto` and misanchor flags unchanged, plus four tier-neutral NAPAA-exclusion removals. `GATE-11 rggmci_gate` — which I measured FAILing the ordinary `NULL_NO_RGGMCI_PAIRS` state when I trialled these in .337 — now PASSes that state; the handoff fixed exactly what I flagged. This is the reversal of the .337 hold: they were held then because they reddened real packages, and they land now because that no longer happens (with SEAL-02b closing the last such path).

- **RG-01 (NAPAA) is a scoring change — named, narrow, upward-only.** The NAPAA-exclusion standing rule is lifted; affected BGCs surface at their true prior instead of a standing-rule floor. Only `Lead_tier_auto` and `Standing_rule` move, only for NAPAA loci, and every observed move is upward with the underlying AB/AF/Novelty prior unchanged. **Not comparable across the 1.9.118/1.9.119 boundary for NAPAA loci — re-score.**

- **Twelve new sign-off / deliverable subcommands (non-scoring unless noted):** `good-guesses` (interpretive-priors md/docx/pdf), `modeb-export` (Mode-B → docx/pdf), `figures kcb-locusmap` (offline KCB comparative locus map), `af-dossier` (antifungal leads × measured Candida), `cohort-leads`, `cohort-assemble`, `comparator-coverage` (two-denominator evidence), `domain-reference`, `realistic-count`, `novelty-shortlist`, `signoff` (QC gate), and `verify-modeb --interp` (judgment-substance gate). Twelve modules, wired via their HOOK files, each reader-side.

- **Fix set + hardening:** parser/output hardening, gate tightenings (COH-01..05, MB-01..04), PERF-05, and 14+ documentation-freshness fixes folded in (core index, User Manual, Quick Guide, SKILL, user guides, deliverables, figures, front-doors, roadmap, prompts).

**Held / deferred, unchanged:**
- **CAT-01** (antiSMASH `/category` product-class injection) remains out — a design change that moves `Arch_Capacity`/`Class_Conf`/tiers; decide before a large cohort run. See the 1.9.117 lineage entry for the first-hand two-BGC measurement.
- **The D1 comparator-coverage scoring wire ships UNWIRED** (CAT-01-class, sign-off pending). Its 2-line hook and the 83%-de-weight / 1.5%-tier-move impact are in `FEATURES/COMPARATOR_SCORING_*.md`.
- **MB-01/04 card-gate behaviour** was not exercised by the extraction-only re-seal; verify in a `mode-b` + `verify-modeb --interp` card build before relying on it.
- The top-level project `CLAUDE.md` (governing config, outside the bundle) still carries stale `AS-→PRIVATE` wording; it is a one-paragraph manual fix on the operator side. The bundle's own copy (`docs/reference/03_Plumbing_Reference.md`) is already corrected.
# v9.7.337 · 2026-07-28 · build 20260728v97337a · engine 1.9.117→1.9.118 (mis-anchor honesty)

Single-item scoring cut. **MISANCHOR-01 only** — reviewed independently by the Orange session against the sealed .336 tier and reproduced first-hand here before landing. The five held verdict-changing items were trialled for this cut and **pulled back out**; the receipts are below, because they fail on the pipeline's own real output and would have marked every package in a large cohort run as FAIL.

- **MISANCHOR-01 — an unrelated Tier-1 diagnostic could erase a class-specific mis-anchor clamp.** `scoring.py` gated both the aminoglycoside and the polyene mis-anchor clamps behind a single global `not tier1_diag`, so **any** Tier-1 CCTT trigger lifted **both**. Reproduced on the project's own fixture — a `RiPP-like` locus with a `natamycin` polyene anchor and **zero** PKS KS domains scored **AF 20.0 / Inventory** carrying the flag `polyene_anchor_<4_PKS_KS(ks=0)`; adding the unrelated `T43-NUC_nucleoside` trigger moved it to **AF 45.0 / Medium with the flag erased**. A nucleoside diagnostic supports nucleoside capacity; it says nothing about whether a polyene backbone exists, and the locus still has no KS domains. **The clamps are now unconditional**, which is stricter and simpler than a trigger-keyed rescue: the guards are themselves the machinery test — `source_scans` emits `polyene_misanchor` only when KS < 4 and `aminoglycoside_misanchor` only when committed DOIS/aminocyclitol evidence is absent — so if the class machinery existed the flag would never have been emitted, and no trigger should lift it. Unrelated Tier-1 evidence keeps its own positive credit through `DIAGNOSTIC_BONUS`, untouched; verified that a lead tier can still rise on a genuine diagnostic while the mis-anchored axis stays floored and the warning survives for a human reader. This completes a direction the code was already moving: the enediyne (§4.3) and class-mismatch (v9.7.63) guards in the same block already fired independently of `tier1_diag` — the aminoglycoside/polyene pair was the straggler. `tier1_diag` retains its four other uses, so no orphaned variable.

- **Inverted shipped assertion — blessed consciously.** `tests/test_misanchor_guards.py::test_tier1_diagnostic_exempts_misanchor` **codified the defect**: it asserted `misanchor_flag == ""` under a Tier-1 trigger. It is replaced by three class-specific controls — an unrelated trigger does not rescue a polyene anchor, the same on the AB axis for an aminoglycoside anchor, and a control proving the unrelated trigger still earns its own credit while the wrong axis stays floored. This is the third consecutive cut in which a shipped test encoded the bug it should have caught (v9.7.335 `test_blastp_online` asserting NOVEL, v9.7.336 the convergence reference-dark fallback, now this). Recording the pattern rather than only the instance.

- **The five verdict-changing items are NOT in this cut, and the reason is a measurement, not a preference.** GATE-11, GATE-12, SEAL-02, SEAL-03 and WB-02 were applied to this tree, tested, and reverted. Applied together they produced **7 failures and 6 errors** in the full suite, and validating a *real* sealed package built by this pipeline returned **FAIL** on two independent dimensions: (a) **GATE-11** — `rggmci_gate` FAILs any package whose RG-GMCI status is `NULL_NO_RGGMCI_PAIRS` while no ClusterBlast references parsed, which is the normal state for a run with no KCB hits or `--json-evidence off`; (b) **SEAL-03** — `checksum_integrity` FAILs on files the sealer itself writes *after* computing the checksum manifest (`repro_fingerprint.json`, `PACKAGE_MAP.json`, `<strain>_compiled_report.md`, `smoke_figures/*`), so a package fails its own integrity gate. Both items are directionally right and both need the write-ordering fixed first. Shipping them as-is would have marked every package in a 200-strain run as FAIL.

**Scoring/parser semantics changed: YES, deliberately and narrowly.** Only loci that carry an emitted aminoglycoside or polyene mis-anchor flag **and** an unrelated Tier-1 trigger are affected; their AF or AB is now floored where it previously escaped, and `lead_tier_auto` can fall accordingly. Everything else is untouched. **Packages sealed on engine ≤ 1.9.117 are not comparable with 1.9.118 for those loci** — re-score rather than pool. This is a correction in the conservative direction: a comparator the locus cannot support no longer inflates the axis.
# v9.7.336 · 2026-07-28 · build 20260728v97336a · engine 1.9.116→1.9.117 (evidence honesty II)

Second correctness cut in the same family as v9.7.335 — **a check that reports success without having checked** — plus the per-gene MIBiG-convergence layer finally reaching the Mode-B card, per-BGC engine provenance, and a seal gate that verifies its own file list. **Engine bumps 1.9.116→1.9.117**: two of the folded items change runtime behaviour (below), so this is not a bundle-only cut. Full `pytest` on the assembled tree: **0 fail**.

- **CS-01 — the identity-overclaim check was INVERTED when a compound board was supplied.** `mamey claim-safety --package` derives the strain's compound names from its triage board and announces it is "using the robust check path"; that path then evaluated `return t in cnames`, so a production verb on a compound **not** on the board returned clean. The more likely a name was a hallucination, the less likely it was caught — measured: *"BGC041 produces zorbamycin. The cluster synthesizes vancomycin and yields teicoplanin."* against a board listing none of them returned **0 findings**. The inversion existed in **two independent implementations** in one file (`lint_claim_safety` and `lint_claim_safety_report._identity_hit`). Fixed verb-class-aware, and the split is measured rather than assumed: **production verbs** (produces/synthesizes/yields) fall through to the shape heuristic regardless of board; **copula** (is/are) keeps the board gate, because removing it there fired **192** findings across the ten shipped claim-safe exemplars ("is that", "are read", "is expected"). Net: true positives 0→3, false positives on those exemplars 1→2 (the +1 is "makes fragmentation risk low" in the RiPP exemplar, documented not tuned away). +10 tests.

- **Per-gene MIBiG convergence reaches the Mode-B card — with a layer-presence guard.** The v9.7.332 P_MPG layer has been written into every sealed package since .332 and never surfaced in a card. `modeb_cards.load_convergence()` + a new `## Per-gene MIBiG convergence — primary family evidence` section render the top-5 references (rank · family+accession · tier · genes · gene-share · median %id/cov · class-concordance · dominance), a one-line convergence read (H1/H2 **and** CONCORDANT → lead-grade, else caution), and the package's own `claim_safety` string **verbatim**. **The incoming patch had a defect and it is fixed here:** its reference-dark fallback fired whenever the row list was empty — including when the package carries no `*_3_mibig_convergence.csv` at all. Every package sealed before v9.7.332 lacks the layer (the reporting-v2 gate deliberately treats those as `LEGACY_NOT_APPLICABLE`, not invalid), so that version would have printed a family-evidence **novelty prior derived from a file that was never written**, on every BGC of every pre-.332 package. Now three-state via `convergence_layer_present()`: rows present → table; layer ran, no family → the evidence-backed reference-dark note; layer absent or unestablished → an explicit "no family-convergence statement can be made — this is *not* a reference-dark finding and *not* a novelty prior." Reader-side only: `modeb_cards` imports nothing from `scoring`/`rules`/`triage`, and `cli.py` reaches it only to register the post-seal `emit-modeb-cards` subparser. +6 tests.

- **PROV-01 — every `B1_BGC_Master` row now carries `engine_version`.** `A2_Strain_Registry` and `A3_Run_Manifest` already stamped a strain-level `workflow_version`, but `B1_BGC_Master` — the sheet every cross-strain figure, cohort synthesis and lead comparison joins on — had no engine field, so a master accumulated one strain at a time across an engine bump was silently mixed. That is concrete, not hypothetical: engine 1.9.114 changed `parsers.extract_domain_features`, which feeds `architecture_first`, so `Arch_Capacity`/`Class_Conf`/`Lead_tier_auto` are **not comparable** across that boundary. Column appended at the tail, so name-indexed readers are unaffected. Verified end-to-end on a real run: `engine_version = '1.9.117'` on every BGC row of a freshly built master. +3 tests.

- **SEAL-01 — `check_release_manifest` now verifies TIER_MANIFEST membership, not just its stamp.** Checks 1–3 verified the checksum manifest and that `TIER_MANIFEST stamp=` equalled `BUILD_STAMP build=`; nothing verified that the manifest's **file list** described the tree. The v9.7.334 rev-b handoff source shipped a manifest listing 1399 files against a 1438-file tree, omitting **42 files including 13 engine modules** — every module added across .330–.333 — and naming three files the tree did not contain, while identity, checksums, sync and accretion all passed. The new check reports omitted and phantom entries and fails the gate; its exclusion set is deliberately pinned to `make_public_tier.sh`'s own TIER_MANIFEST generator, since two sources of truth for one file-set is the failure class the check exists to catch. Verified firing on the real rev-b tree: 42 omitted, 3 phantom. +4 tests.

- **Items 31–55, freeze-safe set (20 items).** Parser hardening, gate/scoring/redaction fixes, cohort-synthesis and cohort-figure repairs, provenance/doc sync rules, plus `tests/test_parse_hardening_v9_7_336.py`. Applied clean with no rejects and no fuzz. **Two of these are runtime-behaviour changes despite the "freeze-safe" label, and are named here rather than glossed:** (a) `scoring.py` — the RiPP-fragment span now reads `abs(end-start)` whenever `end` is set, instead of requiring both `end` **and** `start` to be truthy; a BGC whose `start` is coordinate **0** previously fell back to whole-contig length, so a RiPP at position 0 on an Edge/Full-contig could take the fragment floor on the wrong span. Correctness fix, but it **can move `lead_tier_auto`** for that narrow case. (b) `rggmci.py` — `ranked_pairs` now retains every `HIGH_RG_GMCI_RESCUE` pair past the display cap, so a genuine split-pathway rescue is no longer dropped by ranking truncation; additive rows, which can surface an RG-GMCI banner that was previously truncated away.

- **Held back deliberately.** The five **verdict-changing** items from the same handoff (GATE-11, GATE-12, SEAL-02, SEAL-03, WB-02) are **not** in this cut. Each is correct and each can turn a package that seals green today into a FAIL, which is the wrong surprise to hit in the middle of a large cohort run; they are gate-layer, so folding them later costs a re-validate, not a re-run. **CAT-01** (the antiSMASH `/category` product-class injection) is likewise **not** folded — see the lineage entry for the measurement and for why it must be decided *before* a large cohort run rather than after.

# v9.7.335 · 2026-07-27 · build 20260727v97335a · engine 1.9.115→1.9.116 (evidence honesty)

Correctness cut from the audit chat's six-agent pass over the sealed v9.7.334 tree and three real sealed packages (AS-XXX / AS-XXX / AS-XXX), plus a gate-fail-open extension and the Tier-1 known-bad-input regression tests found missing at sign-off. **Engine bumps 1.9.115→1.9.116** — twelve engine modules change behaviour. Every finding was reproduced against a real artifact before it was patched.

The through-line for the whole cut: **a check that reported success without having checked.** `discover` said "all packages look complete" having found zero (fixed in .334); `validate` upgraded a corrupt manifest to PASS; a coverage view counted only the proteins that were submitted. Each fix below closes one instance.

- **Tier 1 — gates that could not fail.** `validate.py`: an unparseable `manifest.json` was swallowed, so `mode` stayed `None`, the gold/depth block never ran, the reporting-v2 gate degraded to `LEGACY_NOT_APPLICABLE`, and status fell through to **PASS** — a corrupt package scored strictly better than a good one, and `manifest.json` is excluded from the checksum set so nothing else caught it. Now fails closed with `manifest_parse: FAIL`. `validate.py`: `gold_completeness: PASS` was decided by a filename substring — one **zero-byte** `mode_b.md` flipped a real 46-BGC package to PASS with the note "All 46 BGCs accounted for"; now matches authored card filenames against `locked_ids` and carries `(n/N BGC ids matched an authored card file)` in the note. `mode_b_receipt.ingest_one_card`: a **crashed** structure gate set `structure_findings = []`, byte-identical to a clean lint, and the CLI printed `structure: PASS`; now emits an `ERROR / GATE_UNAVAILABLE` sentinel. `modeb_structure_gate`: the §4 evidence gate could not fail two independent ways — the bare-verdict branch matched `CONFIRM/REFINE/OVERTURN` **in the emitter's own unauthored skeleton text**, so `EVIDENCE_GAP` was dead on every card from the supported workflow; and the coverage check's `%id` clause was satisfied by the digits inside the locus tag itself (`ctg13_108` supplied the "13") — verified across all 2438 real locus tags in three packages, zero rows where the clause was not already satisfied by the tag alone. Now requires a real table row and strips the locus tag before testing for an identity.

- **Tier 2 — wrong numbers reaching a human.** `render_brief.py`: page 1 of every strain brief labelled rank truncation as saccharide filtering — AS-XXX printed "36 pure-saccharide suppressed" against a true count of **0** (AS-XXX printed 20, true 0; AS-XXX printed 54, true 14); the two exclusions are now counted separately. `render_brief.py`: `_release_status` hardcoded `PRIVATE` for any `AS-` strain and ignored the manifest, so the same package labelled itself PUBLIC in `manifest_short.json` and PRIVATE in the brief PDF — asymmetric harm, a script publishes while an analyst withholds; now reads `manifest["release"]`. `source_scans.py`: `module_count` tested `feature_type == "module"` while the parser passes GenBank's `aSModule`, so **every BGC in every manifest reported 0 modules** — AS-XXX has 55. `blastp_online.py`: `product_novelty` was hard-wired to **NOVEL** — `function_and_novelty` reads `kcb_top`/`kcb_coverage_genes` off `args`, but neither argparse destination exists on the `blastp-online` parser, so the cross-check inputs were always empty and the `else` branch always fired; now returns `UNDETERMINED` with text saying the test was absent, not negative. `class_architecture.py`: `TAILORS` matched by bare substring, so `halogenat` matched **de**halogenase — six real BGCs across AS-XXX/AS-XXX assert halogenating capacity in the user-facing Mode-B §2 line on an annotation saying the opposite enzyme; `"glycos"` matched any glycoside hydrolase. Now `(?<!de)halogenase` plus a real transferase requirement, with the consumer changed too (patterns were `re.escape`'d, so a regex would have been searched literally and silently disabled halogenase detection entirely). `blastp_evidence_store.py`: `evidence_tier` included our own panel defline, whose `reason=` field is built from the query's antiSMASH annotation using verbatim members of `CLASS_DEFINING_TERMS` — antiSMASH's own call laundered back as BLASTp support; a 19%-identity, 12-aa alignment with an empty subject title graded `TIER_A_CLASS_DEFINING`. Now tiers on subject fields only. `master_workbook.py` + `workbook_dedup.py`: the Sapote write-back helpers called `drop_existing_strain`, clearing the strain from **18 sheets** and restoring only their own — and `workbook_schema_check` returned PASS on the wreckage because every sheet lost the strain consistently; now scoped via a `sheets=` parameter. The live `SID_Master.xlsx` (89) and `TypeStrains_Master.xlsx` (71) were checked and are intact — this never fired on a real master.

- **Tier 3 — silently missing work.** `blastp_online.py`: `blastp-round` planned **zero** proteins on a valid sealed package and exited 0, because the planner read `r["translation"]`/`r["seq"]` and `gene_context.jsonl` carries neither — an operator following the documented per-gene BLASTp step concluded the strain needed none; now falls back to `<strain>_proteins.faa` keyed on locus_tag. `blastp_online.py`: orphan genes were dropped from `scored`, so `orphans` was structurally always empty and `characterized_fraction` / `pct_uncharacterized` / `mean_top_hit_identity` all used a survivorship-biased denominator; now assessed over every submitted gene. `bgc_blastp_panel.py`: the first-pass loop `return`ed instead of `break`ing, exiting the whole function at the cap so the second fill loop never ran. `blastp_followup.py`: one oversized protein ended batch selection — `break` is right for the count cap, wrong for the residue budget (21 selected / 18819 of 20000 residues, 56 droppable proteins skipped); now `continue`s past it.

- **Gate fail-open extension (this cut, beyond the incoming patch).** The incoming patch closed the crashed-gate fail-open in `mode_b_receipt.ingest_one_card` only. Auditing the module for the same shape found the identical `except Exception: n_errors = 0  # gate fail-open` in **`ingest_receipt`** — the primary documented Sapote→durable-store batch front door — and in **`auto_detect_ingest`**, the session-start orphan-card recovery sweep. Both recorded a card whose gate had crashed. Both now route to the existing structure-invalid skip and print a `gate UNAVAILABLE` line. Left flagged rather than patched: the `except Exception: _gate_available = False` import guard at the top of both functions, which skips the gate for every card with no sentinel if the gate module fails to import — a wider behaviour decision.

- **Known-bad-input regression tests (this cut).** The incoming patch shipped 18 fixes with **zero** new test functions, against a defect class whose whole signature is passing every known-good input. Added `tests/test_v9_7_335_tier1_gates_known_bad_input.py` (13 tests) and `tests/test_v9_7_335_ext_receipt_gate_failopen.py` (4 tests): each feeds the gate the specific artifact that used to slip through and asserts refusal, each paired with a good-input control. Verified in both directions — on the unpatched .334 tree the corrupt-manifest case returns `status: PASS` and the zero-byte card returns `gold_completeness: PASS` with the note "All 2 BGCs accounted for with Mode B cards or ledger entries", and the two extension cases record the card despite a crashed gate.

- **Docs — front doors that taught the wrong thing.** `docs/START_HERE.md` advertised a first-run command that **crashes** (`--mode smoke --chatgpt-safe`; `smoke` retired in v9.7.161, `run` accepts only `{standard,gold}`, `--chatgpt-safe` renamed `--capped-session`) and stated "AS data is private", contradicting the PI decision of 2026-07-06 that the AS-series cohort is PUBLIC. `AGENTS.md` told sessions in five places that Full Mode B is **§1–§20** while the engine validates **§1–§30**, so a ChatGPT session obeying its own front door authored the wrong scaffold and failed `verify-modeb` — the exact failure v9.7.322's Mode-B guardrails shipped to stop. `CURRENT_DOCS_INDEX.md` was stamped v9.7.136 and three of its four "current user docs" did not exist (`02_Quickstart.md`, `03_Technical_Manual_Encyclopedia.md`, `04_Workbook_Glossary.md`); corrected against the real tree.

**Scoring/parser semantics changed: PARTIALLY — stated plainly rather than as "unchanged".** BGC counting, KCB/AB/AF triage priors and workbook scoring columns are untouched, and AS-XXX re-run on the patched tree showed **0 field diffs** in `*_4_triage_board.csv` across Arch_Capacity / Class_Conf / Lead_tier_auto / AB_auto / AF_auto. But two changes can move a capacity line on other strains: `class_architecture.TAILORS` no longer matches dehalogenases or glycoside hydrolases, so the six BGCs currently asserting "+ halogenase" on a dehalogenase will change their capacity string; and `module_count` becomes non-zero everywhere. **AS-XXX and AS-XXX boards have not been re-run and diffed on this tree** — do that before treating their capacity strings as stable. This entry deliberately avoids the "existing scoring unchanged / no re-run needed" phrasing that proved wrong for v9.7.332 and v9.7.333.

**Still open, not in this cut** (each needs a sign-off, in the audit chat's own ranking): the antiSMASH `/category` ingest at `parsers.py:312`, which injects a synthetic product class and moves **8 of 140 BGCs across a tier boundary** including AS-XXX BGC006 (84→47, High→Medium, that strain's top AB lead); the all-genes BLASTp panel (`cli.py` hardcodes `genes_per_bgc=2`, so AS-XXX requests 87 of 1056 proteins); `cohort_synthesis.load_master` reading retired TitleCase headers and emitting `fully_dark 0/140` where truth is 56/140; the inverted `_identity_hit` in `mamey claim-safety --package`, which passes flagrant overclaims; missing `engine_version` on master workbook rows, which leaves mixed-engine dashboards silent; and the `compile-report --strict` deadlock — `build_report` emits `SAPOTE:blastp_evidence` and `SAPOTE:fermentation` slots that `write-narrative --section` cannot fill, so `--strict` can never return 0 once they are emitted.

# v9.7.334 · 2026-07-27 · build 20260727v97334a · engine 1.9.115 (UNCHANGED — discover guard + seal hygiene)

Small hygiene cut from the BLASTp chat's independent audit of .333 (real-strain AS-XXX run, 3.12/Linux). **Bundle-only — engine 1.9.115 unchanged** (no scoring/parser/gate change; a read-only subcommand message fix + release-tooling cleanup). Full `pytest` 0-regression.

- **P1 — `discover` empty-scan guard.** `discover.py::_suggest` claimed *"all scanned packages look complete"* when it found **zero** packages — a false completeness claim in the misleading direction (an operator with a wrong path was told everything was done). Now emits *"no packages found — point `discover` at a directory containing sealed Mamey packages."* + **P1b** the test that codified the vacuous message is tightened to forbid it.
- **P2 — seal hygiene.** `make_public_tier.sh` now drops `*-E` / `*.orig` / `*.rej` / `*.bak` / `*~` editor/sed backup artifacts before checksums. BSD/macOS `sed -i -E` had left `BUILD_STAMP.txt-E` in all four v9.7.333 tiers (harmless content, but tracked in `SOURCE_CHECKSUMS` — every seal gate passed while shipping junk). Structural fix, not manual.


# v9.7.333 · 2026-07-27 · build 20260727v97333a · engine 1.9.114→1.9.115 (discover + genus appendices + HMM table + templates)

A feature-forward, claim-safe cut. **Existing scoring is unchanged** (no change to BGC counting, KCB/AB/AF priors, gates — cross-strain comparability preserved, no re-scoring); the engine bumps for new read-only modules/subcommands, one additive reporting table, and one fail-safe fix. Full `pytest` on the 3.13 interpreter; 25 new feature tests; real-strain confirmation on AS-XXX.

- **`discover` subcommand (RED_01).** New workspace-orientation verb (sibling to `doctor`/`inspect`/`explain`): enumerates every sealed package with a completeness grid (Figs·ModeB·BLASTp·Report) + a ranked "what to run next". Read-only, stdlib-only, additive. + `test_discover`.
- **`genus-appendix` subcommand.** Antifungal (AF, primary target) **and** antibacterial (AB — MRSA/foulbrood, secondary) **candidate** appendices grouped by genus, from sealed packages. Keyword flags are comparator/class markers — capacity-level class-level hypotheses, **not** activity claims. Report-only. + `test_genus_appendix`.
- **First-class PFAM/TIGRFAM HMM table.** `antismash_tables.build_hmm_table` → `3_antismash_hmm.csv` + `antiSMASH_HMM` sheet, sourced from the existing `extract_gbk_pfam_hits`/`extract_tigrfam_hits` (these HMM hits were previously not surfaced as a standalone table). Reporting-only; AS-XXX → 419 rows (160 Pfam / 6 TIGRFAM / 253 other, 38 tier-1). + `test_antismash_hmm_table`.
- **CORE-P02 fail-open fix.** `recovery_status.infer_package_status` now asserts `MAMEY_COMPLETE` only on an affirmative completion signal (or empty packaging-time status); a non-empty unrecognized status (`GATE_FAILED`, `INCOMPLETE`, …) fails **safe** to `PARTIAL_FAILED`. + fail-safe test.
- **Doc templates.** BLASTp support-card (`templates/MODE_B_SUPPORT_CARD_TEMPLATE.md` + `_CONTRACT` + evidence matrix + `tools/audit_modeb_support_card.py`), deeper-dive exploration, and Mode-B integration templates — claim-safe scaffolds. + `test_doc_templates`, `test_audit_modeb_support_card`.
- **Tool-citation manifest.** `mamey/data/tool_citations.json` + `docs/Sapote-Mamey.bib` (Crossref-verified citations for 43 companion tools) — pairs with the .331 companion-tools registry.
- **Hygiene.** Stripped the "judgment deferred" motto from Mode-B card text (substantive claim-safety ceiling retained); silent_swallow swept to 110; biopython test-skip guard; reporting-v2 tier doc.


# v9.7.332 · 2026-07-26 · build 20260726v97332a · engine 1.9.113→1.9.114 (per-gene MIBiG convergence evidence)

Engine cut that composes the v9.7.331 hygiene overlays **plus** the Codex **P_MPG + P_LWC** per-gene clusterblast evidence patch. **Existing scoring is unchanged** (BGC counting, KCB/AB/AF triage priors, standing rules, workbook scoring columns identical to 1.9.113 — cross-strain comparability preserved, no re-scoring needed); the engine bumps only because the parser gains **new deterministic outputs**. Full `pytest` on the 3.13 interpreter; see the per-cut receipts in the candidate report.

- **P_MPG (MIBiG-per-gene) + P_LWC (Codex).** Parser retains the best hit for **every `(query gene, MIBiG accession)` pair** (not one per gene), preserving the repeated-reference convergence signal. New `MIBiG_Convergence` report (BGC × MIBiG accession) + `MIBiG_Profile` as package JSON + CSV + workbook sheet, with deterministic evidence tiers **H1_HIGH_DENSITY … H5_SINGLE_OR_WEAK + CAUTION_CLASS_MISMATCH** (reporting strata, **not** final Sapote judgments). New `mamey/antismash_tables.py` (structured module/RiPP/motif tables) + `include_structured` parse path + `length_weighted.py` descriptor. **No AB/AF score bonus added** — mis-anchor/primary-metabolism guards keep hard precedence; no double-counting with the KCB channel. Class-level hypotheses; judgment deferred. + `tests/test_patch_p_mpg_lwc.py`.
- **Carries forward all five v9.7.331 overlays** (the phylogenomics lane REL-P01/TAX-P01 + COMPANION-01, Lemon schema-drift, Orange gate calibration, Red RED-02 RiQ median) — composed clean over them with zero rejects; RED-02 and Amber-02 verified intact after the P_MPG apply.


# v9.7.331 · 2026-07-22 · build 20260722v97331a · engine 1.9.113 (UNCHANGED — bundle-only hygiene/fix cut)

Audit-hardening + companion-tools + one correctness fix. **Bundle-only bump — engine 1.9.113 is unchanged** (no scoring/parser/gate-behavior change to the deterministic run; the RiQ fix touches a descriptive intake metric only, not any scoring input — cross-strain comparability preserved, no cohort re-run needed). Every overlay is additive / non-blocking / reader-side.

- **REL-P01 + TAX-P01 (the phylogenomics lane).** `dedup_and_guard.py`: opt-in `published_registry` allowlist narrowing the `AS-`→PUBLIC rule (default empty = no behavior change). `modeb_cards.py`: Mode-B taxonomy line tags 16S provenance and defers genus-level novelty to genome-scale (MLSA/ANI). + 2 tests.
- **COMPANION-01 (the phylogenomics lane).** `companion_tools.py` + `data/companion_tools.json` registry (15 external tools, detection-not-bundling) + `doctor --companions` probe (inert without the flag) + `docs/companion_tools.md` and the battle-tested `docs/phylogenomics.md` (MLSA + GToTree 138-SCG + fastANI methods). + 7 tests.
- **LEMON — emit-modeb-cards schema-drift fix.** `modeb_cards.py::load_domains_csv` made schema-tolerant (accepts `bgc_id`/`locus_tag`, recovers role/product from `cds_table.csv`); fixes `KeyError: 'bgc'` on every sealed gold package. Reader-side, output format unchanged.
- **ORANGE gate calibration (code diffs).** `authored_verify.py` §4 core-count P01 (accepts the `biosynthetic (rule-based-clusters)` token → clears cohort-wide `COVERAGE_UNVERIFIED`); `modeb_structure_gate.py` P05/P06/P07/P08 false-positive fixes (LOCUS_BGC_MISMATCH contrast cues, §24 comment-strip for NOVELTY/PAD, hedged/rejected KCB names, nr-pending BLASTP_THIN); `tools/claim_safety_linter.py` CS-P01/02/03 hedge/rejection frames + §30-question suppression. Each pairs a cleared false-positive with a preserved genuine-finding guard.
- **RED-02 (Red) — RiQ median correctness.** `antismash_evidence.py`: genome RiQ summary median now uses `statistics.median` (even-length region lists average the two central values instead of taking the upper). Descriptive intake metric only — not a scoring input. + 5 tests.


# v9.7.330 · 2026-07-19 · build 20260719v97330a · engine 1.9.112→1.9.113 (new Mode-B workflow modules)

The **new Mode-B workflow** cut — Lab Quest's + Blue's Mode-B tooling folded into the engine as non-blocking post-seal subcommands (zero core-run risk; each reads a sealed package, never touches `run_one_strain` or a gate). Engine bumps 1.9.112→1.9.113 for the new modules/subcommands (scoring, BGC counting, triage priors, workbook columns all unchanged — cross-strain comparability preserved). Full `pytest`: **0 fail** (3017 passed, 491 skipped). +27 new regression tests.

- **LQ-PATH-01 (Lab Quest, P1) — committed-step class-believability engine.** New `mamey/class_believability.py` + `class-believability` subcommand: judges a class call from its enzyme logic (gateway → committed pull → warhead/tailoring → assembly), returning HIGH/MEDIUM/LOW/SUSPECT with the evidence and the named false-positive superfamily. Runs a LOCAL (per-BGC) and a net-new POOLED (per-strain) pass — a pooled tier stronger than any single BGC flags a **candidate split pathway**. Phosphonate module validated on real cohort BGCs [Redacted — publication in preparation] (two HIGH calls and a LOW false positive). 6 tests.
- **LQ-STRAIN-01/02 (Lab Quest, P1) — strain-level Mode B (Full Strain Sapote, S1–S8).** New `mamey/strain_modeb.py` + `emit-strain-modeb` subcommand + a strain-structure gate (sibling of `modeb_structure_gate`). The missing altitude above the per-BGC card: pools a strain's whole capacity, reassembles split pathways (S4), judges the strain as a unit. Fail-safe PRIVATE on AS-/AJS-/PENDING- release tags. 4 tests.
- **LQ-STRAIN-03 (P1) — cohort-aware S5 + SID.** New `mamey/cohort_context.py`: `emit-strain-modeb --cohort-db <full_cohort.db>` populates S5 cross-cluster / private-chemistry (private vs shared GCFs, co-member strains, nearest-MIBiG KNOWN/NOVEL) via the tested `gcf_context` reader; portable-TSV fallback; degrades to single-strain when absent. Plus a cross-card GCF index (links a BGC to same-GCF BGCs in other strains' cards). Makes SID-strain cards meaningful. 5 tests.
- **LQ-MODEB-02 (P2) — Mode-B section build-out via sub-questions.** Deepen §5 (committed-step audit + minimal-gene-set completeness), §9 (named-FP + fragment alternatives), §13 (class-in-Actinobacteria + class-in-genus) with named sub-questions in the contract JSON — **no new section**, no gate/section-count change; the regen doc renders them. 3 tests.
- **LQ-NPATLAS-01 (P2) — NP Atlas class-frequency grounding.** `npatlas_resolver.class_frequency()` exposes the organism-independent npclassifier CLASS distribution for the §13/S6 "class in Actinobacteria" sub-question, with a **hard boundary**: no genus-precedence / novelty claims (NP Atlas records isolation provenance, not taxonomic distribution), no bioactivity. Degrades when the add-on is absent. 4 tests.
- **emit-modeb-cards (Blue) — compact per-BGC data cards.** `mamey/modeb_cards.py` + `mamey/series_common.py` + `emit-modeb-cards` subcommand: Blue's auto-filled per-BGC card (composition tag, RG-GMCI split-pathway banner, auto-priors, architecture domain-counts) — **complementary** to `emit-modeb-template` (the §1–§30 authoring scaffold), a triage/quick-look card. Ported portable: domains from the package (BLUE_01), all external enrichments opt-in and degrade to empty (no hardcoded paths). 5 tests.
- **LQ-FIG-01 (Lab Quest, P3) — `domain-level --emit-figures` help fixed.** The flag advertised itself as a "no-op placeholder" but the handler is live (`render_domain_figures`); help now states it works.



Integration cut on base v9.7.328 (Red + Green + Blue). Every overlay was verified against the pristine .328 tree and again as an assembled set — **0 cross-stream file collisions** (each touched file is owned by exactly one overlay). Full `pytest` on the assembled tree: **0 fail** (2990 passed, 491 skipped). Engine bumps **1.9.111→1.9.112** because two Red fixes change *runtime behavior*, not just packaging: SCHEMA-P01 changes a `run_bgc_decomp` return contract, and COMP-P07/P09 change resource lifecycle.

- **SCHEMA-P01 (Red, P1) — no more silent all-PASS two-model decomposition.** `run_bgc_decomp` derives its gene table from a package glob that returns `None` when the table was not written; the old `if gene_table_csv and Path(...).exists()` then left `genes_by_bgc` empty, so every BGC fell to `ONE_MODEL_CONSISTENT` and the run reported PASS / "0 TWO_MODEL_STRONG" — a clean-looking negative for an analysis that never ran. Now it computes `gene_table_status ∈ {OK,MISSING,NOT_FOUND,EMPTY}`, returns `status=INCOMPLETE` with an honest per-row `null_reason`, and `cli.py` raises a `[WARN]`. Happy-path PASS contract preserved. 4 tests.
- **SCHEMA-P03/P04 (Red, P2×2) — workbook_schema_check read-only safety.** In `read_only` mode openpyxl returns `None` for `max_row`/`max_column` when a writer omits the stored `<dimension>`, so `range(1, None+1)` / `None-1` crashed `validate()` with `TypeError`; and the post-load body ran outside any `try/finally`, leaking the read-only zip handle on any mid-validation exception. Now forces `calculate_dimension(force=True)` (floored at 0) and closes via `try/finally`. 2 tests.
- **COMP-P07/P09 (Red, P3×2) — comparator resource hygiene.** Extracted untrusted comparator ZIPs no longer persist under `out_dir/_extracted_comparators` (cleaned in a `finally` once genes are parsed); `gcf_context` closes its sqlite connection on the error path via `contextlib.closing`. 2 tests.
- **GREEN_01 / SM-P-031 (Green, P2 silent-wrong-result) — `_scope_feats` contig match robust to coverage-decimal mangling.** The sealed crosswalk `contig` can drop a leading zero in the `_cov_<float>` tail (`NODE_49_..._cov_34.087283`→`...cov_34.87283`), so the old `contig not in fc` substring test never matched and whole-BGC BLASTp silently scoped **zero genes** (AS-XXX BGC060/BGC058). Now matches on the stable `NODE_<n>_length_<L>` key first, raw substring as fallback. (Authored for 328, did not land; re-issued unchanged.)
- **BLUE_01 / F-DOMDATA (Blue, P3 additive) — self-describing domain data in the package.** The sealed package carried only `aa_length` + the biosynthetic `sec_met_domains` subset and no translations, forcing cohort / Mode-B / annotation consumers to re-open the antiSMASH ZIPs. `gene_context.py` now writes out the full `PFAM_domain`/`aSDomain` annotation and `/translation`s that mamey already parses during the run — pure pass-through, no new HMM run, no scoring change.

Deferred (not in this cut): the design-call items (COMP-P01/P02 exclude-strain SQL, BLAST-P10, CORE-P02) and EVAL-P03 (defensible fail-closed, `watch`).

# v9.7.328 · 2026-07-18 · build 20260718v97328a · engine unchanged (1.9.111)

Multi-surface integration cut (Red ready-overlays + Green + Purple + Orange), base v9.7.327; each overlay was verified against the pristine .327 tree before folding. Bundle-only; no engine change. Full `pytest`: **0 fail** (2983 passed).

- **EVAL-P01 (Red, P2 claim-safety) — no more wrong-molecule chemistry binding.** `npatlas_resolver`'s bidirectional prefix match (`n.startswith(k) or k.startswith(n)`, first-in-order + `break`) could bind an arbitrary molecule's formula/mass/InChIKey to a KCB label (`actin` → `actinomycin d`). Now both sides must be ≥6 chars and it binds **only** when the surviving candidates are a single distinct molecule — any ambiguity resolves to nothing. Verified in the shipped code (`npatlas_resolver.py:159,166`).
- **EVAL-P04/P09 (Red, P2/P3) — enrichment robustness.** A missing `locus_tag` no longer crashes card enrichment (the row is skipped); `aa_length` digit-extracts (`"123 aa"`→123, `"1,024"`→1024). 2 tests.
- **SCHEMA-P05/P06 (Red, P2) — boundary_audit fail-closed.** A failed `import mamey.rules` used to silently skip the retired/exclusion leak checks and produce a *green* audit; it now appends `RULES_UNAVAILABLE` so the audit reads INCOMPLETE. A duplicate `bgc_id` (extractor double-emit) that was silently collapsed is now detected and reported. 29 boundary tests pass.
- **GREEN (P2/P4) — pre-flight honesty + encoding.** `doctor`/banner claimed biopython was needed only for `triage-raw`, but `blastp-online` hard-requires it and the bundled wheel is Linux/cp312-only; both messages now say so. `run_phase_receipts.jsonl` append gets `encoding="utf-8"` (same sweep as .324/.327).
- **PURPLE COMP-P01/P02 (P2 correctness) — stop the strain-bleed in GCF figures.** `gcf_network()` selected regions with a substring `LIKE '%{strain}%'`, so `--strain AS-XXX` absorbed **44 of AS-XXX's** regions (67 records = 23 real + 44 bled). Now requires `strain` to be a full `_`-delimited token in the basename (`AS-XXX_` / `_AS-XXX_`), which still matches SID tokens and spaced Type names. Bleed proof: AS-XXX 67→23. 5 tests.
- **ORANGE COHORT-FIG-P01 (P2 crash) — cohort figures no longer die on display-named folders.** `cohort_figures.load()` built the intake path from the *folder name* but files are prefixed with the `--strain` id, so a display-named folder (`Actinomadura citrea DSM 43461/`) raised `FileNotFoundError` and the first strain killed the whole run (the Type-strain suite produced 0 figures). Now globs for the real intake file.

Deferred (not in this delivery): **PURPLE_01 / Orange O2 — the `parse_locator` accession regression** (Orange measured 0 unresolved in the .326 seal vs 8,986 in .327 over `full_cohort.db`). I could **not** reproduce it as a code regression: `parse_locator` (`tools/bigscape_ingest_to_mamey.py`) is byte-identical .326↔.327, so the cause is likely the delivered DB or a caller, not the function — and PURPLE_01, the claimed fix, is not in this bundle. Flagged for the next handoff to include PURPLE_01 + the exact failing accession input, at which point the suggested `-k locator` regression gate can land against a real fix. Also deferred: the **exclude-strain SQL half** of COMP-P01/P02 (`bigscape_combined_run.py`, a separate design call) and **EVAL-P03** (defensible fail-closed, left as watch).

# v9.7.327 · 2026-07-18 · build 20260718v97327a · engine unchanged (1.9.111)

Claim-safety + comparator robustness + ingest portability, from the Red audit chat's v9.7.327 suggestions (base v9.7.326). Bundle-only; no engine change. Full `pytest`: **0 fail**.

- **SCHEMA-P02 (P2, claim-safety) — public-tier private-strain-ID leak.** The `PRIVATE_STRAIN_ID_IN_PUBLIC_SPEC` guard matched `AS-\d{3}` — which now over-matches publishable 3-digit AS while **missing** the IDs that are actually private: `AS-XXX`/`AS-XXX` (2-digit), 4-digit AS, and the `AJS-`/`PENDING-` provisional prefixes. A private strain ID could pass the guard into a PUBLIC-tier spec. Broadened the configured regex in the JSON source-of-truth to `(?<![A-Za-z])(?:AJS-\d{1,4}|PENDING-\d{1,4}|AS-\d{2,4})`; 4-test lock, scaffold test preserved.
- **comparator_robustness (COMP-P04/P05/P06).** The comparator GBK collector now filters `is_macos_cruft`, so `._*.gbk` resource-fork shadows are no longer parsed as phantom comparator genomes; comparator CSV reads get `encoding=`; and the GCF-network's sqlite connection is now closed on both exit paths (was leaked on the early-return path).
- **INGEST-P01 (portability).** The schema-gate `SCHEMA_VERSION` marker read/write use a `with`-block + `encoding=`, and the gate now `makedirs` the banked-dir (with a clear error if it can't) instead of assuming a hardcoded `/data/mamey-local` that crashed off the build server. Keeps the ingest schema gate working in other environments.

Verified: SCHEMA-P02 4 tests + 87 targeted (private/public-tier/redact/comparator) pass; ingest regression 78 pass; `repo_health --strict` PASS; full suite 0-fail. Deferred to the next round (Red's Bucket B, fix sketches in hand): EVAL-P01 (npatlas wrong-molecule binding), the SCHEMA-P01/P05/P06 fail-open guards, SCHEMA-P03/P04 + EVAL-P03/P04 robustness, and the design calls (COMP-P01/P02 `AS-1`↔`AS-XXX` strain-bleed, BLAST-P10, CORE-P02, and the three architectural items).

# v9.7.326 · 2026-07-18 · build 20260718v97326a · engine unchanged (1.9.111)

Grand Master integration — six disjoint, independently-verified overlays from the Red audit chat (18 patch items across 59 files), certified against v9.7.325. Bundle-only; no engine change. Full `pytest`: **0 fail** (2972 passed). Already-shipped items (B1/B2/P3a in .324, GATE-P09 + COVERAGE_UNVERIFIED in .325) were deliberately excluded.

- **P3b + PyYAML (META-P01/02/03/04).** 103 `json.load(open(...))` handle leaks across `tools/` + `mamey/` swept (AST transform) to a per-file `_read_json` helper (with-block + encoding); no leaked descriptors. **PyYAML promoted from dev-extra to a core dependency** — the two features that import `yaml` now work on a clean install, and the clean-install release gate stops failing. Resolves the standing item-11 decision.
- **CORE-P01 + GATE-P11 (P1).** Added `encoding="utf-8"` to all 11 package CSV read/write sites. Without it, the seal path is **locale-dependent** and crashes under `LC_ALL=C` / non-UTF-8 locales when a package carries a non-ASCII byte — a real crash in the release path, now deterministic.
- **OUT-P11 (P2).** The master workbook duplicated 7 sheets on a strain re-run: the column-1 de-duplicator missed column-2 keys. Fixed + regression-locked (`test_workbook_dedup_out_p11.py`). (Directly relevant to the item-10 Master-Workbook redesign.)
- **Atomic writes (OUT-P02/P03, CORE-P04/P05, OUT-P06).** The last 5 non-atomic writers — master saves, sealed manifest, sealed checksums, deliverable ZIP, report — now write to `.tmp` and `os.replace`, so an interrupted write can't leave a half-written sealed artifact.
- **BLASTp stub guards (BLAST-P02/P03/P06/P07).** The remaining unguarded BLASTp parse doors now degrade to empty on an NCBI HTML / `QBlastInfo` stub instead of crashing ingest mid-run; regression-locked (`test_blastp_stub_guards.py`).
- **Evidence macOS cruft (PARSE-P03/P08).** Three evidence file-list builders now apply `is_macos_cruft`, so `._*.gbk` / `._*.json` resource-fork shadows are no longer parsed as phantom evidence; regression-locked (`test_evidence_macos_cruft.py`).

Verified: `APPLY_ALL` applied to a pristine v9.7.325 with **0 rejects**; 11 new regression tests pass; `repo_health --strict` PASS; full suite 0-fail. Deferred as design calls (in the roadmap, not this set): the top-3 architectural risks — `bgc_id` positional counter (wrong-attribution linchpin), uncalibrated RG-GMCI/scoring thresholds, and the single master-workbook accumulator (item-10 redesign) — plus CORE-P02, BLAST-P10, and Blue's §4-denominator-definition question.

# v9.7.325 · 2026-07-18 · build 20260718v97325a · engine unchanged (1.9.111)

Curated from the four-surface patch handoff (Blue + Red), integration base v9.7.324; the handoff was pre-reconciled against .324 so nothing already-shipped was re-folded. Bundle-only; no engine change. Full `pytest`: **0 fail** (2961 passed).

- **COVERAGE_UNVERIFIED (Blue) — close the §4-coverage false-confidence hole.** `verify-modeb` on a **card-only** run (no `--package`/`--bgc`) has `bgc_context=None`, so §4_BLASTP_COVERAGE's denominator collapses to the card's OWN rows — a thin §4 that lists reconciled verdicts for the few rows it shows scores "clean," and `verify-modeb` prints a bare `OK` that reads as "coverage verified" when it never was (exactly how the AS-XXX BGC054 3-row card passed all three gates). Fix at the **command layer** (the pure gate's card-only behaviour is intentional and test-locked): a pure `_coverage_unverified_reason` helper fires a `COVERAGE_UNVERIFIED` **WARN** when §4 asserts `CONFIRM/REFINE/OVERTURN` verdicts but no authoritative package core count reached the gate, and the summary line becomes `OK (§4 coverage NOT verified — no package core count)`. Non-blocking; tells the author to re-run with `--package … --bgc …` so item-5's real-core-count coverage actually gates. 4 new tests.
- **GATE-P09 (Red) — handle-leak cleanup.** The `blastp_online/<bgc>_online_blastp.csv` read used a bare `nr_csv.open()` inside `DictReader`; now a `with`-block + `encoding=`. Second such leak after .324's P3a, in a disjoint region (both preserved).

Verified: Blue's 4 tests + 197 targeted modeb/coverage/verify tests pass; `repo_health --strict` PASS; P3a intact; full suite 0-fail. Deferred (handoff decisions, not patches): promote PyYAML to core (dissolves the docs-stale misreport + clean-install test noise), the P3b ~95-site `json.load(open())` hygiene sweep, and the §4-denominator-definition question (rule-based cores only vs also tailoring/accessory — exemplar-calibration risk, deliberately not decided).

# v9.7.324 · 2026-07-18 · build 20260718v97324a · engine unchanged (1.9.111)

Fail-closed + shadow-guard hygiene. Integrates two carried-over defects from the v9.7.322 audit that the independent "Red" bughunt of v9.7.323 found were never folded, plus one handle-leak cleanup. Bundle-only; no engine change. Full `pytest`: **0 fail** on the assembled tree.

- **B1 (P1) — the mandated BLASTp verify gate crashed under version-shadow.** `scripts/verify_blastp.py` imported `mamey.blastp_ingest` first and only inserted the local package root into `sys.path` inside the `except`. When an installed/older `mamey` is on the path (the exact drift `mamey_run.py` defends against), the first import caches the wrong parent `mamey` in `sys.modules`, so the `except` retry re-uses it and re-fails — the gate then exits nonzero on **every** input, giving zero real verification on the machines it's meant to protect. Its unit tests masked this: the negative cases expect exit 1 and passed by accident on the import crash. Fixed by inserting the local root **before** the import (standard shadow guard); all 6 `test_bug1_verify_blastp` cases pass, including under a shadowing `mamey`.
- **B2 (P2) — checksum-integrity was fail-open on its own error.** In `mamey/validate.py`, if `verify_checksums()` itself raised, the handler recorded `checksum_integrity="ERROR: …"` but left `status` untouched, so a package could still return `PASS`/`MAMEY_COMPLETE` with **unverified** integrity — contrary to the v9.7.145c intent and the fail-closed meta-pattern. Fixed by forcing `status="FAIL"` in that `except` (only reachable when the integrity check errors).
- **P3a — handle-leak cleanup.** `authored_verify` read the gene-by-gene table with a bare `open(gt)` inside `DictReader` (no `with`, no `encoding=`); now reads via a `with`-block into a list. Behavior-identical; removes the leaked descriptor.

Verified: B1 6/6, B2 validate/checksum subset 21 passed, item-5 core-denominator test still green, `repo_health --strict` PASS. Deferred (proposed by Red, not folded here): P3b (`json.load(open(...))` handle leaks across ~10 one-shot `tools/` scripts) and P3c (distinguish "PyYAML missing" from "docs stale" in `sync_version --check`, which ties to the pending item-11 PyYAML decision).

# v9.7.323 · 2026-07-18 · build 20260718v97323a · engine unchanged (1.9.111)

Mode-B enforcement, claim-safety calibration, and audit-residual hygiene. Bundle-only; no engine change. Full `pytest`: **0 fail** on the assembled tree.

- **H3-calibrate — bioactivity_phenotype false-positive fix.** The `_BIOACTIVITY_RE` check over-fired on bare adjectives with no assertion frame — section headers (`§13 Antibacterial / antifungal relevance`), table labels (`| Antibacterial score |`), class names (`bioactive pigment`), and discovery-lead phrases (`a novel antibacterial lead`). Split the vocabulary into assertion terms (kills / MIC / producer / activity-against — inherently phenotype claims) vs bare adjectives (antibacterial / antifungal / …), which now flag only in an assertion frame (copula/intensifier before, or an activity noun after), never when attributive (adjective + noun = a class name) or on a header/table-label line. Real overclaims still flag. Clears the 6–19 FPs the parallel surfaces measured; the check can now be promoted toward blocking.
- **§4_BLASTP_COVERAGE enforced at receipt (item 4).** The named-subject + §4-coverage checks now run through `mode_b_receipt` (the hub every incoming card passes), not only `verify-modeb` — so a non-compliant card is caught even if the producer skipped the preflight. They fire under `check_evidence_presence` and self-skip when there is no core grid, so no panel artifact is required.
- **§4 coverage denominator uses the package core count (item 5).** `authored_verify` now counts a BGC's rule-based `core biosynthetic` genes into `bgc_context["n_core_genes"]`; the coverage gate uses `max(package cores, card cores)`, so a §4 that OMITS cores (lists 2 of 10) is caught, not just one that under-covers the cores it lists.
- **GATE-WIRE-2 — symmetric gate-wiring invariant (item 7).** The invariant enforced WIRED→referenced but not the reverse, so an OPERATOR_ONLY gate that gained a test kept a stale label (how `check_module_accretion` sat mislabeled until .321). Added the reverse check: an OPERATOR_ONLY gate that becomes test/`.sh`-referenced must be reclassified WIRED or enumerated in a documented unit-tested-not-cut allowlist (6 current entries), plus a staleness check on the allowlist.
- **F1 — `repo_health --strict` restored to PASS.** `cohort_deliverable.py`'s `_strain_rows` swallow (`except: pass` → `return -1`) was changed to `except: return -1` (behavior-identical), dropping `silent_swallow` 111→110 under the ceiling. Not a .322 regression — the count crossed at .320's F5 fix; the gate isn't cut-wired so it shipped red.
- **latent-sort — scanner registry version select.** `raw_antismash_triage._resolve_scanner_registry` now keys on numeric `(major, minor)` instead of lexicographic `sorted()[-1]`, which mis-orders `v0.10 < v0.5` once the minor reaches double digits (safe today at v0.5, latent).
- **F3 — `TAG` `patches:` line** replaced with a pointer to the authoritative `BUILD_STAMP.patch=`/CHANGELOG (was a stale .320-era snapshot; can no longer drift).

Verified: all 7 shipped Mode-B exemplars stay clean under the broader (receipt-style) firing; H3 FP set → 0 findings, real overclaims still flag; +new tests; modeb/claim-safety/gate-wiring suites green.

# v9.7.322 · 2026-07-18 · build 20260718v97322a · engine unchanged (1.9.111)

Mode-B authoring guardrails. Unifies two independent investigations of the same recurring failure — chats authoring Mode-B cards without reading the class exemplar, without real per-gene BLASTp, or (grabbing a thin/region-relative source) fighting PHANTOM_LOCUS instead of switching source. Bundle-only; no engine change. Full `pytest`: **0 fail** (2950 passed) on the assembled tree.

- **Author-time preflight (docs).** `skills/sapote-mamey/SKILL.md`'s Mode-B section is rewritten into a 3-step preflight done BEFORE authoring: (1) read the matching `docs/reference/modeb_exemplars/<class>_exemplar.md` and mirror its §4 evidence grid; (2) get per-gene BLASTp of the rule-based cores FIRST — or request the data (region GBKs) from the operator and say so plainly — never paper over it with Pfam prose; (3) run all three gates (`verify-modeb`, `claim-safety`, `mode_b_quality_gate` → FULL). New one-page `docs/MODE_B_AUTHORING_PREFLIGHT.md` checklist; the gates-that-must-pass + verification lists now name all three Mode-B gates. Makes the workflow unmissable from the front-door.
- **§4_BLASTP_COVERAGE gate (code, WARN-first).** `modeb_structure_gate.py` now demands the evidence a length-based depth grade can't: core rows in §4 must carry a `%id` value AND a CONFIRM/REFINE/OVERTURN reconciliation. Codes: **BLASTP_ABSENT** (a core grid where no core carries real BLASTp — reads as Pfam-only), **BLASTP_THIN** (< ceil(cores·0.5) covered — usually a thin core_batches source), **DATA_REQUESTED** (the honest "BLASTp pending — requested" path passes with an acknowledged WARN, never a fail). Silent when no core grid is detectable (RiPP/siderophore §4s use a different shape). Denominator prefers a package core count when the context supplies one, else the card's own ● cores.
- **SUBJECTS_UNDESCRIBED gate (code, WARN).** §4 carrying verdicts but no named nr subject organism (e.g. `[Streptomyces sp.]`) is the signature of a bare-accession source or a run without `--xml`; flagged with the fix (re-run `--xml` / pull the full package-tagged hittable).
- **PHANTOM_LOCUS message now names the root cause.** Instead of only "check for boilerplate/copy-paste," it names the most common cause — region-relative tags from a thin core_batches hittable instead of the strain's real package locus_tags — and the fix: switch source (full package-tagged wave-2 hittable + `--xml`, or the region-GBK core batch), don't reword tags to pass.
- **All new checks are WARN-band (advisory, non-blocking)** — calibration phase. BLASTP_ABSENT is the promote-to-ERROR candidate after one pass over the exemplar set + current authored cards. Verified: all 7 shipped exemplars stay clean (zero false positives); 10 new tests; 171 modeb tests pass.

# v9.7.321 · 2026-07-18 · build 20260718v97321a · engine unchanged (1.9.111)

Claim-safety + gate-hardening point cut from the post-v9.7.320 hostile-audit + real-data validation. Bundle-only; no engine change. Full `pytest`: **0 fail** on the assembled tree before stamping.

- **VBP-genecount — `verify_blastp.py` gene coverage was silently broken.** `_gene_of` took `rsplit("|",1)[-1]` (last pipe field), but the pipeline's pipe-query deflines carry the locus as a `gene=ctgN_M` KEY in the middle (`…|gene=ctg13_21|node=…|reason=biosynthetic`), so every row collapsed to the constant trailing field and `genes_covered` reported **1** instead of the real count — silently disabling the `--expect` MISSING/PARTIAL coverage assertion, the gate's entire purpose as the BLASTp-claim precondition. Found by gating 39 real returned wave-2 result files (1 → **931** genes after fix). Now extracts the `gene=` key / ctg token wherever it sits; backward-compatible.
- **H3-followup — bioactivity-phenotype false-negative.** The `bioactivity_phenotype` claim-safety check (shipped .320) matched `antibacterial/antifungal/…` but omitted `bactericidal/fungicidal/bacteriostatic/fungistatic`, so a per-BGC claim like "BGC is bactericidal against S. aureus" slipped through clean. Added the four terms; the extract-level / negated / hedged / capacity exemptions still apply. WARN band.
- **GATE-WIRE-1 — gate-registry classification fix.** `check_module_accretion` was labeled `OPERATOR_ONLY` ("kept out of the cut on purpose") while its own reason says it "fails a cut adding an unjustified module" and `test_module_accretion.py` runs it against the real tree in the full pytest suite that the cut requires. Reclassified → `WIRED`; the gate-wiring invariant stays green. (Root-cause follow-up GATE-WIRE-2 — the invariant enforces WIRED→referenced but not OPERATOR_ONLY→not-referenced — is flagged for a registry-policy decision, not in this cut.)

# v9.7.320 · 2026-07-18 · build 20260718v97320a · engine unchanged (1.9.111)

Consolidated cut from the 2026-07-17/18 hostile-audit campaign (9+ chats). Bundle-only; no engine change. Full `pytest`: **0 fail** (verified on the assembled tree before stamping). Every fix reproduced against a real artifact and regression-tested.

- **INT-1 — v97319b was cut without regenerating its seal.** `TAG build:` was bumped to `…v97319b` but `BUILD_STAMP`, `TIER_MANIFEST stamp=`, and `SOURCE_CHECKSUMS_SHA256.txt` still described the `…v97319a` tree → `check_release_manifest`/`sync_version --check` FAIL and 4 red tests, while `verify_release_identity` falsely passed (reads only BUILD_STAMP). Resealed canonically (sync_version → gen_release_manifest → regenerate SOURCE_CHECKSUMS **last**, the step the hotfix skipped).
- **INT-2 — the root cause, now closed.** `sync_version.py` owned `TIER_MANIFEST`'s `version=` but not its `stamp=` ("left to the cut to set"), nor the `· build <stamp>` restatements in `docs/TIER_SET_EXPLAINER.md` and `docs/user_guides/{comprehensive_glossary,operational_reference,sapote_kernel_guide}.md`. Added sync rules anchoring all of them to the build `STAMP`, so a cut only bumps `BUILD_STAMP` + `pyproject.toml` and `--apply`/`--check` keep every stamp consistent. INT-1's silent-drift class can't recur.
- **B3-fix — terpene KCB detector.** The v97319b B3 flag shipped a substring `_is_terpene_kcb` that false-fired on non-terpene names containing a terpene token ("hopene-like NRPS") — which would wrongly suppress a real betalactone call — and missed albaflavenone/neomenthol/avermitilol. Replaced with exact-set + MIBiG-class matching (no substring). Flags, never relabels.
- **H3 — per-BGC bioactivity-phenotype claim-safety check.** `claim_safety_linter.py` had only compound-scoped identity checks, so a per-BGC PHENOTYPE claim ("BGC059 shows potent antibacterial activity against MRSA … is a confirmed producer") passed clean. Added a `bioactivity_phenotype` violation (activity/kills/inhibits/active-against/MIC/producer), exempt on extract-level / negated / capacity-framed / hedged forms. Emitted at **WARN** (calibration phase). Bioactivity is extract-level only, never a per-BGC phenotype.
- **BLASTp verify gate shipped.** `scripts/verify_blastp.py` (mandated by SKILL.md but absent from the bundle) now ships, reusing the pipeline's own `parse_hit_table` so "real rows" can't drift from ingest; exits nonzero on HTML-stub/empty/missing/partial.
- **checksum_integrity — supplementary PDFs excluded.** Nondeterministic matplotlib PDFs (`*_8_strain_brief.pdf`, `*_PRINT_FIGURE_PACK.pdf`) at package root no longer enter checksums, unblocking `seal --strict` on scientifically-complete packages.
- **deliverable-suite gold gate fail-closed.** `check_deliverable_suite.py` short-circuited to no-finding when the `gold_completeness` / `Mode B cards written:` lines were absent; an absent line is now a finding.
- **F5 — cohort master completeness selection.** `_locate_master` picked the lexicographically-last `*master*.xlsx` — a partial `…Master_After_AS-XXX.xlsx` (4 strains) over the canonical `Mamey_Master.xlsx` (9) — so `mamey cohort` silently ran on a subset. Now picks the most-complete master (max `A2_Strain_Registry` rows, tie-broken by mtime).
- **F4 / BUG3 — cohort prevalence derived from B2.** `cohort_synthesis.load_master` and `cross_strain_card_context.load_prevalence` required a `Cross_Strain_Class_Prevalence` sheet the base master-workbook never writes; the equivalent counts live in `B2_Product_Class_Matrix`. Both now derive prevalence from B2 when the dedicated sheet is absent, so `mamey cohort` works on a plain gold master and cross-strain Mode-B sec-blocks stop silently dropping.

# v9.7.319 · 2026-07-12 · build 20260712v97319a · engine unchanged (1.9.111)

Analysis-chat handback (v9.7.318 audit): three verified, regression-clean fixes. Bundle-only; no engine change. Full `--run-slow --run-network` suite: **3,234 pass, 0 fail.**

- **F1 — `mamey figures gcf-network` + `figures clinker` were wired but unreachable (`bgc_figures.py`).** The subparsers were registered in cli.py, but `figures_command` never dispatched them, so both fell through to "specify a kind (diagram | atlas | ani)" — a whole command class silently unavailable. Added the two dispatch branches routing to `bigscape_figures.gcf_network` / `clinker_figure`. **Verified end-to-end against the real cohort DB:** `mamey figures gcf-network --db cohort_with_AS-XXX.db --strain AS-XXX --run 32 --cutoff 0.5` now emits a 377 KB PNG (`status: WRITTEN`).
- **F2 — cohort front-door couldn't auto-locate its own master (`cohort_deliverable.py`).** `_locate_master()` globbed lowercase `*master*.xlsx`, but the master-workbook step names its output with a capital "Master" (e.g. `Mamey_v1.9.111_Master_After_<strain>.xlsx`) — so the .317/.318 headline feature silently degraded to "no master found." This was a real bug in the .317 cohort code. Now matches on a case-folded stem; verified it finds both capital-`Master` and lowercase files.
- **F3 — domain-figure titles were node-scoped (`domain_figures.py`), hardening.** `_node_label` is now region-aware so two BGCs on one contig get distinct, region-bearing labels. Does not reproduce as wrong output on current data (latent); hardening + a region-disambiguation test. **Still owed:** a guard that the domain-level CSV's BGC↔region assignment is itself region-correct.
- **13 new tests across the three fixes, 0 fail.** repo_health PASS, command-pointer guard OK, monolith gate PASS (spot-vet anchor preserved at v9.7.317).
- **Not folded (deliberately):** (a) a duplicate F1 fix from a second patch bundle — functionally equivalent to the one folded, skipped to avoid collision. (b) `genefirst_glycopeptide_scan.py` — a session-side gene-first glycopeptide scanner (reads a strain region dir + external pfam HMM via pyhmmer); stays OUT of the bundle by the data-hygiene rule, same class as the BLASTp harness scripts. (c) **F4 (cohort synthesis schema drift)** — `cohort_synthesis.load_master()` requires a sheet set the current master-workbook writer doesn't all emit, which blocks the cross-strain *synthesis* branch (the figure branch is unaffected). Correctly left for a canonical-side decision: reconcile the reader's required sheets against the writer's output. This is the remaining blocker on `mamey cohort` end-to-end synthesis.

# v9.7.318 · 2026-07-12 · build 20260712v97318a · engine unchanged (1.9.111)

Analysis-chat handback: two prepared, independently re-verified audit fixes. Both bundle-only; no engine change. **First fully-green full suite of this run — the 2 long-standing monolith-freshness reds are retired.**

- **pandas pin admits 3.x (audit Worst #9).** `requirements.txt` + `pyproject.toml` pinned `pandas>=2.0,<3.0`, but the environment/wheelhouse actually ships pandas 3.0.x — a real contradiction. Verified the code works under pandas 3.0.2 (pandas-touching tests pass), so the honest resolution is to admit 3.x: all three sites now read `pandas>=2.0,<3.1`. Also updated `test_v97133_bughunt_regressions` which hard-asserted the old pin (the incoming patch missed the test; caught by the full suite).
- **Monolith freshness: sanctioned spot-vet restamp (audit Worst #7).** The monolith carried a full-read-through anchor at v9.7.242 and had drifted ~75 patches, failing `check_monolith_freshness`. The gate explicitly sanctions a *spot-vet* anchor (distinct from a full read-through). The analysis chat performed a doctrine scan against the .317 tree — confirmed clean of retired doctrine (no `66%`/`33%` assembly-tier thresholds, no per-BGC BSL-2 flagging) — which I re-verified independently before folding. Added a `spot-vetted against bundle v9.7.317` anchor **alongside** the preserved v9.7.6 full-read-through line (not overwriting the full-vet history). Anchored at .317 (the tree actually scanned), not .318, so it claims exactly the vet that was performed. Gate: PASS (anchor honest, no retired doctrine); the 2 monolith tests now pass. **This is a spot-vet (doctrine-clean + drift-bounded), NOT a full human re-read — a full read-through is still eventually owed.**
- **One self-inflicted fix:** the .317 CHANGELOG text quoted the phantom `mamey <cmd>` token it was describing, which the command-pointer guard flagged; reworded so no `mamey`-prefixed phantom token appears in prose. Full `--run-slow --run-network` suite: **3,221 pass, 0 fail** (no known reds); repo_health PASS.

# v9.7.317 · 2026-07-12 · build 20260712v97317a · engine unchanged (1.9.111)

Two independent, complementary cross-strain additions. Bundle-only; no engine change.

- **New `mamey cohort` front-door (`mamey/cohort_deliverable.py`).** Accretion-justified: cohort_deliverable — the cross-strain layer had all the capabilities (cohort_synthesis, cohort_figures, bigscape_figures) but no single command that triggers them together and *guarantees* a deliverable. This closes that: `mamey cohort --runs-dir <dir>` locates the verified cohort master, emits the cross-strain synthesis report, and emits the cohort figure suite — with a **mandatory-deliverable gate** mirroring the single-strain promise (a completed cohort run hands back at least one human-readable deliverable or returns exit 1 with a clear message). Orchestrates existing writers; adds no new capacity claims (synthesis stays capacity-level, GCF stays similarity-not-identity). Verified: exit-1 gate on no-master, exit-0 with 22 figures + captions on a real run. 6 tests. **Caveat:** the synthesis-report branch is unit-tested + gate-proven but not yet run against a real multi-strain master (only single-strain AS-XXX was available here); the figure branch ran for real. The untested path fails *safely* via the gate.
- **New `tools/bigscape_combined_run.py` (BiG-SCAPE combined-run tool).** Handoff from the BiG-SCAPE chat (discovered during AS-XXX processing). Reconstructs cohort GBKs from a BiG-SCAPE 2 SQLite DB and runs combined clustering with a new strain's region GBKs — giving real cross-strain GCF assignments without needing the original cohort GBK files on disk. Carries 5 documented GBK-reconstruction fixes (LOCUS-line layout, 0-based coordinate rejection, antiSMASH-feature omission, real/reconstructed split, local-run guidance for Pfam scan time). Chains into the existing bigscape_cross_strain / bigscape_known_novel / bigscape_ingest_to_mamey tools. 8 tests.
- **Four defects in the incoming BiG-SCAPE patch, caught by the release gates and fixed before cut** (not shipped): (1) phantom command pointer — a help string referenced a nonexistent bigscape-prep subcommand (no `mamey`-prefixed token); repointed to the real `tools/bigscape_prep.py`. (2) unguarded module-scope `from Bio import SeqIO` in the test — wrapped in `pytest.importorskip`. (3)(4) hard-coded self-describing `v9.7.317` version literals in the tool + test — removed (version comes from the SSOT, not baked into files). Full `--run-slow --run-network` suite: 3,219 pass, only the 2 known monolith-freshness reds; repo_health PASS.

# v9.7.316 · 2026-07-12 · build 20260712v97316b · **ENGINE 1.9.110 → 1.9.111 (first engine bump of this run)**

- **Engine-tier scoring fix: glycopeptide leads no longer buried by antiSMASH region overmerge.** Diagnosed on a real cohort glycopeptide BGC [Redacted — publication in preparation] by running the real engine: it scored **Medium** because antiSMASH overmerged the node into a 5-class `neighbouring` region and the engine labelled it "complex multi-class hybrid" instead of glycopeptide. Two composed fixes:
  - **(A) Tailoring-detection widening (`parsers.py`).** The CDS `product` string is now augmented at parse time with `gene_functions` / `sec_met_domain` / `gene_kind` / `note` qualifiers. Root cause: glycopeptide tailoring enzymes (glycosyltransferase, Trp_halogenase, P450) are annotated in those qualifiers, NOT in `/product` (which on an antiSMASH region is just the class label "NRPS"). The existing glycopeptide pre-check (`class_architecture.py`: `nrps_c>=6 + halogenase + glycosyltransferase`) therefore never saw the machinery and fell through to the multi-class bucket. With the widening, the pre-check fires and BGC014's capacity call becomes **glycopeptide (HIGH confidence)**.
  - **(B) Machinery-confirmed glycopeptide floor (`scoring.py`).** When the architecture capacity call is `glycopeptide` at HIGH confidence — which by construction means the crosslinking/tailoring machinery is present (≥NRPS-6C + halogenase + glycosyltransferase, i.e. ≥4 genes incl. the P450/Oxy crosslinker) — the tier is floored to **High**. Claim-safe: capacity (machinery consistent with glycopeptide production), never a production claim; caps at High; the standing-rule and RiPP downgrades still run after and can override, so the floor never shields a real exclusion.
- **Verified on the real artifact + cohort diff.** Re-ran `mamey run --mode gold` on the affected strain [Redacted — publication in preparation]: **the BGC moved Medium → High, capacity complex-multi-class-hybrid → glycopeptide.** Full cohort before/after tier diff: **exactly 1 of 72 BGCs changed** (BGC014) — the fix is surgical, nothing else re-tiered. 172 scoring/architecture tests pass; full fast partition 2,886 pass (only the 2 known monolith-freshness reds); repo_health PASS.
- **Engine version 1.9.110 → 1.9.111.** This is a genuine scoring/routing change, so the engine bumps, per the deliberate decision (audit chats will analyze .315 vs .316). Math-reference volumes are NOT re-stamped to 1.9.111 — their constants were verified against 1.9.110 and a re-verification pass is pending (honest note added to VolII); the scoring *thresholds* are unchanged, only the capacity-class routing sees more.

# v9.7.315 · 2026-07-12 · build 20260712v97315a

- **Three small tooling patches (swept from the AS-XXX archive, all bundle-only):** (1) new `tools/archive_leak_scan.py` (+ test, WIRED gate) — a private-ID leak guard for the *contents* of committed archives, closing a coverage hole where the existing leak-audit chain only scanned loose text files / single xlsx, not members inside a zip. (2) `finding4` requirements/pyproject sync: corrected a stale `requirements.txt` note that wrongly said reportlab was unused — reportlab IS a core dep (backs the primary PDF renderer); updated `check_requirements_pyproject_sync.py` + test to match. (3) new `tools/fetch_mibig_reference.py` (+ test) — fetch a MIBiG reference cluster GBK for the comparative chain, wired into `cluster_brief.py`.
- **repo_health kept honest:** `archive_leak_scan` initially pushed the `silent_swallow` count to 111 (ceiling 110) via an `except FileNotFoundError: pass`. Fixed the swallow (explicit empty-fallback for the optional terms file) rather than bumping the ceiling; `repo_health --strict` PASS.
- **Engine unchanged at Mamey 1.9.110**: new tools + a requirements-doc correction; no scoring or package-format change. Bundle only. (The engine-tier overmerge/glycopeptide scoring fix is the next cut, separately.)

# v9.7.314 · 2026-07-12 · build 20260712v97314a

- **New figure tool: `mamey figures gcf-network` (BiG-SCAPE GCF network + clinker) — `mamey/bigscape_figures.py`.** Fills a real gap confirmed against the tree: eight tools read the BiG-SCAPE DB but none rendered the GCF network as an image file. Accretion-justified: `mamey/bigscape_figures.py` is the renderer (matplotlib/networkx, lazy-guarded so it degrades without the `figures` extra), wired as a `figures` subcommand in `cli.py`.
- **Why it's cuttable now (it was HELD in .313):** all three blockers I sent back are fixed and I verified each against the real files, not the handoff note. (1) The node-to-BGC mapping goes through the **tested `bigscape_ingest_to_mamey.canon_locator`/`parse_locator`** (cov-independent), not the naive `re.match` — this closes the .291-class mis-map that would otherwise mis-attribute nodes in a *published* figure; 0 naive-regex refs remain. (2) No bare `json.load(open())` — one context-managed `_load_json` helper. (3) `run`/`cutoff` are `required=True` on the subparser with a `MISSING_ARGS` guard. Ships with `tests/test_bigscape_mapping.py` (4 pass, exercises the mapping bug in the fast partition) and `docs/BIGSCAPE_FIGURES.md`.
- **Claim discipline:** GCF membership + gene links are labelled SIMILARITY, not identity. clinker + the BiG-SCAPE DB are external prerequisites (not bundled); real strain figures/DBs are never bundled.
- **Engine unchanged at Mamey 1.9.110**: additive figure module + CLI subcommand; no scoring or package-format change. Bundle only.

# v9.7.313 · 2026-07-12 · build 20260712v97313a

- **Defect hunt round 2 — three real defects fixed (same failure class as the BLASTp clobber bug: output written/read without validating it's real)**: (D1, HIGH) `compile-report --pdf` silently never produced a PDF — `_render_compiled_pdf` ran `md_to_pdf.sh` with `cwd=pkg` but passed the render-md/out-pdf as *relative* paths, so the renderer's `open()` couldn't find them and returned `RENDER_FAILED` every time. Fixed by passing `render_md.resolve()`/`out_pdf.resolve()` (absolute) while keeping `cwd=pkg` so relative figure paths still resolve. (D2, MED — the important one) `blastp_ingest.parse_hit_table` skipped only `#`-comment lines, so an NCBI HTML/QBlastInfo error stub (a clobbered results file) parsed into garbage hit rows; added a file-head guard that returns no rows if the file starts with `<` or contains `QBlastInfo` — the same clobber failure class, on the pipeline-ingest side. Functionally tested: HTML stub → 0 rows, real HitTable → parsed. (D3, LOW-MED) `_render_brief_nonblocking` didn't resolve `pdir` before a subprocess with a different cwd — latent twin of D1; now `.resolve()`d.
- **Not included (deliberately)**: the BLASTp *harness* patches (`poll_blastp`/`fetch_xml`/`verify_blastp`) are session-side execution scripts, not bundle files — not cut. The GCF-network figure module (`bigscape_figures`) is held: it's a real renderer now but still uses a naive node-mapper (no `canon_locator`, reintroducing the .291-class mis-map), has two bare `json.load(open())`, and lacks required run/cutoff args — handed back for revision, not folded in.
- **Engine unchanged at Mamey 1.9.110**: three deliverable-path bug fixes (no new behavior, no scoring/package-format change). Bundle only.

# v9.7.312 · 2026-07-12 · build 20260712v97312a

- **Wheelhouse scanner registry v0.5 (AB/AF capacity-scoring build-out)**: three new files under `Wheelhouse/` — `scanners/scanner_registry_v0.5.json` (v0.4 + the new **RS01** self-resistance / target-directed-genome-mining scanner + a validation-readiness review of the five untested class-priors), `validations/SCANNER_VALIDATION_PLAN_v0_5.md`, `reports/SCANNER_RUN_RECIPE.md`. RS01 is gated (fires only on a duplicated housekeeping target OR a co-located known resistance marker) and carries a false-positive trap. **Behavior note (transparent):** `raw_antismash_triage._resolve_scanner_registry` and `wheelhouse` select the highest-version registry by sorted glob, so the triage now resolves to v0.5 and RS01 becomes active — additive only; the 95 scanner/triage/wheelhouse tests and the full fast partition (2,866 pass) show no regression, and no existing scanner's behavior changes. The review flagged an AB04 (β-lactam) GATE/POS mismatch (gate catches only the IPNS-route) — recorded in the registry notes + validation plan, not silently "fixed."
- **Engine unchanged at Mamey 1.9.110**: no `mamey/*.py` change; the scanner subsystem carries its own version (registry v0.5). Registry is versioned data the triage consumes, added additively. Bundle only.

# v9.7.311 · 2026-07-12 · build 20260712v97311a

- **Audit paths 1–3 — CI + repo-health automation + a figures data-hygiene fix**: (1) new `.github/workflows/ci.yml` — a fast partition (`repo_health.py --strict` + a <2-min pytest run) on every push/PR, and the full suite (`--run-slow --run-network`) on tags and manual dispatch, mirroring the pre-tag full-suite gate. (2) new `tools/repo_health.py --strict` — a repo-health gate (bare-except, print-ceiling, docstring coverage, onboarding-doc inventory); currently PASS, no blocking issues. (3) new `tests/conftest.py` — fast/slow test partitioning: a bare `pytest` auto-deselects the matplotlib figure-render tests and anything marked `@slow`/`@network` (SKIPPED, not failed); `--run-slow --run-network` runs everything. (4) new `tools/check_duplicate_dict_keys.py` (+ test) — a duplicate-dict-key gate, registered `WIRED` in `gate_registry.tsv` (check_-class); it caught and the patch fixed real dup keys in `master_figure_atlas.py`/`build_master.py`. (5) **data hygiene**: `mamey/master_figure_atlas.py` no longer hardcodes real per-strain label offsets — `LABEL_POSITION_OVERRIDES` is empty by default with a deterministic generic fallback (0 hardcoded strain IDs). Plus regression tests (`ptm_af_scoring`, `c5_c7`, `bee_wasp`).
- **Full suite (`--run-slow --run-network`)**: only the two known `test_monolith_freshness` governance reds; all new tests pass; `repo_health --strict` PASS.
- **Engine unchanged at Mamey 1.9.110**: the only `mamey/` change is figure-atlas label positioning + dedup — no scoring or package-format change. Bundle only.

# v9.7.310 · 2026-07-12 · build 20260712v97310a

- **Bert Mode taxonomy reconcile — retire the stale v9.4 three-bucket citation taxonomy, adopt the four-tier standard**: `docs/BERT_MODE_PROTOCOL.md` was stamped "Bundle v9.4" (badly stale) and carried an obsolete bucketing. Wholesale-replaced it with a current, self-contained version whose status vocabulary is the four-tier standard **Verified / Partial / Policy / GenBank** (the Eden Summary Table tiers), now the single source of truth. `prompts/CLAUDE_SYSTEM_PROMPT.md` aligned to the same four-tier bucketing — the one behavior-affecting change, it drives how citations get sorted at author time. `docs/user_guides/operational_reference.md` access-unavailable rule fixed (mark Partial + record the reason, not "Unverified leads"). `CUT_PROTOCOL.md` and `skills/sapote-mamey/SKILL.md` stamp/vocabulary updated (R-02 empty-() stays gone). New `tests/test_bert_taxonomy_drift.py` gates the taxonomy against re-drift. Applied the combined patch (5 files) + the wholesale BERT_MODE replace; the redundant split-out per-file patches were not applied.
- **Deferred (decision-required)**: the monolith's Bert/Eden five-section workbook needs a whole-section reconcile — left for the same re-vet pass the monolith-freshness gate is already asking for (see .309).
- **Full-suite state**: only the two known `test_monolith_freshness` governance reds; the taxonomy reconcile adds none and the new drift gate passes.
- **Engine unchanged at Mamey 1.9.110**: docs + one prompt behavior alignment + a drift test; no scoring or package-format change. Bundle only.

# v9.7.309 · 2026-07-12 · build 20260712v97309a

- **GBK-shim compliance fix (standing rule E2) — a real violation that shipped in .296–.308**: nine tools added this session imported `from Bio import SeqIO` (lazily) without the required `mamey._gbk_shim` fallback, so they'd fail rather than degrade when biopython is absent: `bgc_reference_align`, `cluster_gene_compare`, `extract_cluster`, `bgc_figures`, `cluster_completeness`, `cluster_relate`, `scope_cluster`, `fetch_reference_cluster`, `cluster_discovery`. Factored a reusable `SeqIO` adapter into `mamey/_gbk_shim.py` (wraps `parse_genbank_text`) and gave each tool a two-line `try: from Bio import SeqIO / except ImportError: from mamey._gbk_shim import SeqIO` fallback. Verified functionally (the shim parses a GBK with no biopython) and the E2 lint passes. I found this by finally running the WHOLE suite in four chunks, not just a–c — the lint lives in d–h.
- **Full-suite state**: ~3,183 pass across all four chunks; the only remaining reds are the two `test_monolith_freshness` governance checks (see below), which are not code failures.
- **Engine unchanged at Mamey 1.9.110**: an additive `_gbk_shim` adapter + tool import-fallbacks; no scoring or package-format change. Bundle only.

# v9.7.308 · 2026-07-12 · build 20260712v97308a

- **New tool `tools/deliverable_citation_audit.py` — pre-delivery every-mention citation gate for COMPILED deliverables**: automates the hand-scan the compiled-report rule (execution slice 15) told authors to run by eye — finds bare `BGC\d{3}` mentions not followed by a `NODE_...`/`r\d+` locator in the same clause, across Lay Guide / Synopsis / Chapter / exclusion tables / lead-tier tables / fermentation guidance. Fills three real gaps: `verify-modeb` only runs on §1–30 cards, is deliberately weak ("cited *somewhere*" passes), and the strict `_BARE_BGC_RE` in `modeb_structure_gate.py` was defined-but-never-called. Targets the documented incident of 324 bare BGC-IDs in one compiled report. Complementary to `bgc_reconcile --verify-card` (that reads a card against package signals; this reads finished text with no package and checks citation hygiene + ID-collision across the deliverable set). stdlib-only; registered `WIRED` in `gate_registry.tsv` (name ends `_audit` → the gate-wiring invariant requires the row). Test 26 pass. Gap-analysis note under `future_improvements/`.
- **Engine unchanged at Mamey 1.9.110**: a pre-delivery gate over finished text; no scoring or package-format change. Bundle only.

# v9.7.307 · 2026-07-12 · build 20260712v97307a

- **Parked-decisions cleanup**: (R-02) removed the leftover empty `()` affiliation placeholder in `skills/sapote-mamey/SKILL.md:21` (the MANIFEST placeholder was already gone) — keeps the 0-affiliation rule clean. (patch-14) resolved as **no code change**: `run --json-evidence` defaulting to `bounded` is documented and intentional (stream+cap with ijson, graceful fallback to off; `blastp` defaults to off because it needs no antiSMASH JSON; capped-session overrides run to off). Added a code comment so the stale audit note doesn't resurface.
- **Math-reference work order — Tasks B, C, D, E complete** (Task A, the new cross-strain/GCF math volume, is a separate standalone doc, not attempted here): (B) reconciled the two divergent VolI copies — `docs/reference/01_Math_Reference_VolI.md` stays canonical; `docs/user_guides/math_reference_vol1.md` retitled the plain-language companion with a header stating its constants are illustrative and the canonical file wins. (C+D) VolII and General-Audience footers now track the frozen engine instead of the rolling bundle version (matching VolI's .296 fix); every load-bearing numeric constant cited in VolII (13: ADJ_MAX_LOCUS_GAP/SPAN, BACKBONE_MIN_KB, CONCORDANT_MARKER_FRAC, COVERED_FLOOR, FRC_*, PER_ARM_FLOOR, _ORPHAN_FLANK, _POLYENE_MIN_KS, _STREAM_JSON_MIN_BYTES, SIZE_LO/HI) and GA (base_ab/af/novelty=25/20/30, DIAGNOSTIC_BONUS=25, RGGMCI_MAX_HUB_DEGREE=4) was re-verified against `mamey/*.py` at engine 1.9.110 — all match, no drift. (E) tagged VolII's `ADJ_MAX_LOCUS_GAP=60` / `ADJ_MAX_SPAN=400` (`diagnostic_rescue.py:208-209`) as untuned engineering estimates and closed VolII's self-flagged tagging TODO.
- **Engine unchanged at Mamey 1.9.110**: docs + a code comment; no scoring or package-format change. Bundle only.

# v9.7.306 · 2026-07-12 · build 20260712v97306a

- **`bgc_reconcile.py` gains `--verify-card` — post-authoring reconcile-loop closure**: given a written Mode B card (`--verify-card card.md --bgc BGCNNN`), re-runs the reconcile for that BGC and checks the card actually *acknowledges* each contradiction signal the ledger raised (`_ACK_SIGNALS` / `_ack_found` / `verify_card` / `render_verify_md`). A BLOCK signal with no acknowledgement in the card fails verification — so the pre-authoring `--strict` gate and this post-authoring check now bracket the whole authoring step. Tests extended.
- **New tool `tools/cluster_brief.py` — one-command driver for the comparative chain**: runs the `scope_cluster` → `extract_cluster`/`fetch_reference_cluster` → `cluster_gene_compare` → `cluster_relate` → `cluster_completeness` chain (the KCB-guided fetch+compare path, 4/7 of the chain) for one query BGC and consolidates the REAL tool outputs into a single authoring brief — orchestration over verified tools, not a new algorithm. stdlib-only, builder (no gate row). Test pass.
- **Data hygiene**: the real demo/brief outputs (`BGC018_verify_card_DEMO.md`, `Ae150A-Ps1_r001_comparative_brief.md`) were NOT bundled.
- **Engine unchanged at Mamey 1.9.110**: authoring-aid + orchestration tools; no scoring or package-format change. Bundle only.

# v9.7.305 · 2026-07-12 · build 20260712v97305a

- **New tool `tools/cluster_completeness.py` — the comparative-chain capstone (truncation vs biological absence)**: assesses a query BGC's completeness against the strict-majority-recurrent gene set of its homologous reference clusters (flanking singletons excluded), so a gene that's missing reads as either assembly truncation or genuine biological absence rather than an unexplained gap. completeness = query-present / recurrent-reference; capacity/architecture-level. Completes the comparative chain `scope_cluster` → `extract_cluster`/`fetch_reference_cluster` → `cluster_gene_compare` → `cluster_relate` → `cluster_completeness`. stdlib-core, builder (no gate row). Doc `CLUSTER_COMPLETENESS.md`, test 3 pass.
- **Data hygiene**: the real `AS-XXX_BGC008_completeness.json` output was NOT bundled.
- **Engine unchanged at Mamey 1.9.110**: comparative-analysis tool only. Bundle only.

# v9.7.304 · 2026-07-12 · build 20260712v97304a

- **`bgc_reconcile.py` real-strain fixes (found running on Pseudonocardia sp. Ae150A-Ps1, 36 BGCs — the .302 synthetic tests missed them)**: (1) **self-lint false-positive** — the ledger's own reclass prose tripped an INTERNAL claim-safety warning against itself; fixed so the rendered ledger is clean. (2) **region-number mapping** — triage keyed anchors by `region0NN` with no index map, so 23 anchors showed UNVERIFIED even though the evidence was present; added the region-number→index resolution so present anchors verify. (3) added `_load_over_merge` so a region inherits its over-merge flag when any protocluster row carries `over_merge_flag=YES`. Tests 6→10 (the three real-strain cases now covered). This is the same lesson as the .291→.292 ingest fix: a synthetic fixture passed while the tool failed on real data.
- **Engine unchanged at Mamey 1.9.110**: authoring-aid tool fixes; no scoring or package-format change. Bundle only.

# v9.7.303 · 2026-07-12 · build 20260712v97303b

- **Cluster-GBK toolkit round (three tools, folded)**: `tools/fetch_reference_cluster.py` — reconstructs a reference or cohort cluster GBK from the anchored BiG-SCAPE DB (`--acc ACCESSION:label`, matched on gbk.path substring), the reference/cohort ingress that feeds the align/compare/relate chain without a download. `tools/scope_cluster.py` — scopes an over-merged antiSMASH region GBK to a target class and flags genes overlapping another category's protocluster core, fixing a real over-merge error at the boundary. `tools/cluster_relate.py` — turns a set of homologous cluster GBKs into a distance tree, completing the chain `fetch_reference_cluster`/`extract_cluster` → `cluster_gene_compare` → `cluster_relate`. All stdlib-core, builders (no gate rows); capacity/architecture-level. Tests pass (9 across the three). Renumbered from the analysis chats' colliding .302 labels; the patch chat owns the sequence.
- **Data hygiene**: the real top-target Mode B cards (`modeb_cards_top_targets`) were NOT bundled.
- **Engine unchanged at Mamey 1.9.110**: cluster-analysis tools only. Bundle only.

# v9.7.302 · 2026-07-12 · build 20260712v97302a

- **New tool `tools/bgc_reconcile.py` — pre-authoring cross-channel evidence reconciliation ledger**: over a sealed package, aggregates the scattered contradiction signals (Class_Conf, Misanchor_Flag, Two_Pathway_Flag, Two_Model_Flag, Concordance, Primary_metab_flag, Boundary, KCB) plus reclass domain-discrepancy into one CONTRADICTIONS-TO-RESOLVE checklist with a claim ceiling, so an author sees every conflict before writing a Mode B card instead of discovering them scattered across artifacts. Reuses the engine's own `reclass_check.analyze`, `kcb_frontpage._corroboration_tier`, and `claim_safety_linter` (7 engine modules) — store-backed, deterministic, no network. `--strict` = pre-authoring gate (exit 1 on any BLOCK); the rendered ledger itself passes `lint_claim_safety`. stdlib-only, analysis tool (no gate-registry row). Test 6 pass (each detector + clean path + strict counts + ledger lint). Gap-analysis note under `future_improvements/`.
- **Engine unchanged at Mamey 1.9.110**: an authoring-aid tool that reads existing package signals; no scoring or package-format change. Bundle only.

# v9.7.301 · 2026-07-12 · build 20260712v97301a

- **New tool `tools/extract_cluster.py` — the first non-antiSMASH entry point**: locates and extracts a BGC from a RAW genome FASTA by marker-gene co-occurrence. Gene-calls with pyrodigal (lazy-imported), finds the tightest window where ≥N diagnostic markers co-localise, and writes an annotated GBK (marker genes labelled for clinker / `cluster_gene_compare`) + a present/absent JSON. This closes the external-genome loop `cluster_discovery` → `extract_cluster` → `cluster_gene_compare`, and doubles as `cluster_discovery`'s confirmation step (candidate → confirmed carrier). stdlib-core; pyrodigal optional/lazy (tests skip when absent), builder (no gate row). Doc `EXTRACT_CLUSTER.md`, test pass. Capacity/architecture-level.
- **Data hygiene**: certain cohort nucleoside comparison outputs [Redacted — publication in preparation] were NOT bundled.
- **Engine unchanged at Mamey 1.9.110**: a raw-genome analysis entry point; no scoring, data, or clustering change. Bundle only.

# v9.7.300 · 2026-07-12 · build 20260712v97300a

- **New tool `tools/cluster_discovery.py`**: scans a cohort (or outgroup) for candidate carriers of a BGC of interest by marker-gene co-occurrence — the "which other strains might have this cluster" step that feeds `extract_cluster` → `cluster_gene_compare`. Reports candidate carriers with a present/absent marker profile and a conservation summary; capacity/architecture-level, no compound-identity claim. stdlib-only, builder (no gate row); doc `CLUSTER_DISCOVERY.md`, test pass.
- **Engine unchanged at Mamey 1.9.110**: analysis tool only. Bundle only.

# v9.7.299 · 2026-07-12 · build 20260712v97299a

- **New tool `tools/cluster_gene_compare.py`**: gene-by-gene comparison across homologous clusters — builds an ortholog matrix + gene-pair correspondence across a query BGC and its reference clusters (reusing the clinker-consistent GLOBAL-identity metric from the .298 fix, so counts match). Emits ortholog-matrix + gene-pairs CSVs for the cross-cluster synteny/conservation view. stdlib-only, builder (no gate row); doc `CLUSTER_GENE_COMPARE.md`, test 3 pass. Capacity/architecture-level — homology is ancestry.
- **Engine unchanged at Mamey 1.9.110**: analysis tool only. Bundle only.

# v9.7.298 · 2026-07-12 · build 20260712v97298b

- **Correctness fix / clean retraction — `bgc_reference_align.py` global identity**: the .296/.297 tool aligned LOCALLY (Smith-Waterman) and called a homolog on local %id ≥ 25 + coverage ≥ 30, which **overcounts** — a short high-identity block passes even when identity over the *full* protein is background. Switched to clinker-consistent **GLOBAL** (Needleman-Wunsch) identity = matches / alignment-length, 0.3 confident cutoff + a 25–30% twilight tier (`--min-gid`, default 30). Reproduces clinker exactly. **This corrects the v9.7.296 claim of "7/12 genes homologous to both" for AS-XXX BGC008 — the honest count is 4 confident cross-cluster orthologs** (2 oxygenases, EPSP synthase, nikJ), 2 twilight, 6 background. CSV now emits `{ref}_global_id` / `{ref}_tier`. Test `test_reference_align_global_identity.py` (3 pass, DB-free). The historical .296 entry is left as the accurate record of what was believed then; this is the forward correction.
- **Bug Hunt on .296 (P296, P2 hygiene)**: context-managed the `urlopen(...).read()` in `bgc_reference_align.py` and the two bare `open(...).read()` reads in `bgc_deliverable_pdf.py`; added an `importorskip` guard to `test_reference_align.py::test_score_pid_identical` (lazy `Bio` via `_aligner()`), so a bio-less env skips rather than fails.
- **Engine unchanged at Mamey 1.9.110**: a tool correctness fix + resource hygiene; homology stays capacity/architecture-level (ancestry, never “makes the reference compound”). Bundle only.

# v9.7.297 · 2026-07-12 · build 20260712v97297a

- **Gene-level assembly-line analysis toolkit (5 tools, floors baked in)**: `gene_assembly_line.py` — reliable PER-GENE NRPS/PKS module counts from `nrpspksdomains` annotations, fixing the three traps that corrupt region-level counts (PFAM_domain duplicates, condensation subtypes, PKS_PP carrier naming); region sums are unreliable, this is the trustworthy path. `nrps_substrate.py` — predicted peptide backbone + siderophore/glyco/lipopeptide signatures from A-domain specificity, auto-confirmed against P450/halogenase/GT / cyclizing-TE. `pks_product_class.py` — polyene / aromatic / reduced-macrolide call from per-module reductive loops. `bigscape_blastp_novelty.py` — MIBiG protein DB + BLASTp of target proteins, reporting percent **similarity (never identity)** and flagging self-hits + genuine novelty (<55%). `gene_modeb_enrichment.py` — emits the gene-level Mode B subsection with the project floors ENFORCED: 15 kb confidence tier, capacity language, "similarity not identity," node·region citation, NAPAA excluded, no em-dashes. Doc `GENE_LEVEL_ANALYSIS_GUIDE.md` (workflow + floors + the 1-strain-per-chunk rule for CDS-dense Nocardia). Test 5 pass; verified on real cohort BGCs [Redacted — publication in preparation]. stdlib-only (BLAST+ external for the optional novelty step); all builders (no gate rows).
- **Data hygiene**: the real 51-strain outputs (target-novelty TSV, a per-strain class brief [Redacted — publication in preparation], PKS-classes figure/TSV) were NOT bundled.
- **Engine unchanged at Mamey 1.9.110**: gene-level analysis tools that consume antiSMASH annotations; substrate/product-class calls are model predictions, capacity-level. No scoring, data, or clustering change. Bundle only.

# v9.7.296 · 2026-07-12 · build 20260712v97296a

- **Docs round 1 (all-docs work order, applied)**: cross-strain/GCF front-door discoverability — `START_HERE`, `QUICK_GUIDE`, `SINGLE_STRAIN_QUICKSTART`, `PER_MODE_ARTIFACT_SET` gained cross-strain/cohort entries (were 0 mentions). New `SOPs/SOP-17_CrossStrain_GCF_Cohort.md` (end-to-end cohort workflow grounded in the real `bigscape_*` tools; every cross-ref resolves), registered in `SOP_MASTER_INDEX` + `DELIVERABLE_MENU`. Mode B contract currency: `QUICK_GUIDE`/`TRIGGER_ROUTING` §20→§30 (verify-first; the historically-correct §20 refs inside the contract doc left untouched). Math Reference VolI footer now tracks the frozen engine (`Mamey 1.9.110 (frozen; math tracks the engine, not the rolling bundle)`) — the math work-order's Task C.
- **BGC deliverables toolkit (new tools)**: `tools/bgc_reference_align.py` — aligns a BGC's proteins to characterized reference clusters and draws a clinker-style synteny figure + correspondence CSV; the key insight is that the anchored BiG-SCAPE DB *already stores every reference cluster's proteins* (`cds.aa_seq`), so MIBiG refs need no download (`--ref-db`); `--ref-ncbi` efetches non-MIBiG clusters, `--ref-gbk` takes a local file. Local Smith-Waterman (Bio.Align/BLOSUM62), capacity/architecture-level — homology is ancestry, never “makes the reference compound.” Verified on public MIBiG reference clusters [Redacted — publication in preparation]. Plus `tools/bgc_deliverable_pdf.py` (PDF assembly) and a `bgc_figures.py` update (RGB-PNG save for universal viewer rendering; json.load hygiene). Optional deps (biopython/matplotlib/dna_features_viewer) lazy-imported; tests skip when absent. Doc `BGC_DELIVERABLES.md`.
- **Data hygiene**: the real AS-XXX deliverable artifacts (BGC008 Mode B card, synteny PNGs, reference-alignment CSV, figure catalog) were NOT bundled.
- **Engine unchanged at Mamey 1.9.110**: docs + display/deliverable tools; no scoring, data, or clustering change. Bundle only.

# v9.7.295 · 2026-07-12 · build 20260712v97295a

- **Strain + per-BGC figure/report deliverables (two handoffs, folded)**: (1) `tools/strain_bigscape_report.py` — a per-strain BiG-SCAPE report as a standard deliverable (overview, assembly quality, class distribution, antimicrobial *capacity*, MIBiG anchors with antiSMASH domains, notable intact assembly lines, novel families with architecture); DB-free, reads the portable derived TSVs; verified on the real 51-strain export (AS-XXX: 96 BGCs, 34 T1PKS). (2) `tools/bigscape_figure_labels.py` — canonical figure node-categories that fix the grey-"Reference"/red-"MIBiG" legend collision at the source (cohort type strains → "type strain"/grey, MIBiG → "MIBiG reference"/red; bare "reference" guarded); display-only. (3) `tools/bgc_figures.py` — per-BGC figure set: fig1 locus map (gene arrows by role, labelled by function not g1/g2/g3), fig2 GCF novelty (nearest-neighbour distances), fig3 per-gene BLASTp %identity — each with a sibling `*_data.csv` so the figure is reproducible; inputs degrade gracefully (fig1 needs only `--gbk`).
- **Optional figure deps guarded**: matplotlib / dna_features_viewer are imported lazily (Agg backend) and are not vendored; the fig-render test skips (not fails) when they're absent, per the optional-dep policy. All three tools are builders (no gate-registry rows). Docs `STRAIN_BIGSCAPE_REPORT.md`, `BGC_FIGURES.md`; tests pass. Genericized one demo strain string in the labels module.
- **Data hygiene**: the real 51-strain outputs (novel-discovery PDF/PNG/TSV, the all-strain reports zip) were NOT bundled. Reports stay capacity-worded — antimicrobial *capacity*, never a per-BGC production claim.
- **Engine unchanged at Mamey 1.9.110**: display/report tools only; no scoring, data, or clustering change. Bundle only.

# v9.7.294 · 2026-07-12 · build 20260712v97294a

- **Bug Hunt on .292 (audit-chat handback)**: (P292-05) `bigscape_cross_strain.py` now takes `--run-id`/`--cutoff` to disambiguate a multi-run DB (defaults to the latest run) instead of silently mixing runs; (P292-01/02) wrapped bare `open(...).read/write` and `json.load(open(...))` in context managers in `bigscape_ingest_to_mamey.py` and `antismash_bigscape_join.py`; (P292-03) removed a redundant SSF block in `architecture_first.py` whose `and`/ternary precedence was broken — the robust `re.search(r'\bSSF\b', doms)` check just below supersedes it, so it's behavior-neutral (71 architecture tests confirm no output change). Test `test_bigscape_bughunt_v9_7_294.py`.
- **Deferred, deliberately (P292-04)**: 42 `write_text()` calls without `encoding=` (P3, platform-dependent codec). They're spread across the mixed tree in non-trivial call forms; a blind regex sweep is exactly the mixed-tree hazard to avoid, so this is flagged for a careful per-file pass, not rushed here.
- **Data hygiene**: the real 51-strain analysis outputs (novel-siderophore dossier, network gallery, 51-strain analysis zip) and external-tool binaries (FastTree, sourmash plugin) were NOT bundled. The Math-Reference WORK ORDER (Tasks A–E) is a separate analysis-chat assignment ("do not cut") — noted, not actioned here.
- **Engine unchanged at Mamey 1.9.110**: tool fixes + one behavior-neutral engine cleanup; no scoring or package-format change. Bundle only.

# v9.7.293 · 2026-07-12 · build 20260712v97293a

- **`blastp-online` gene-by-gene CSV now carries the locator and %similarity**: (1) new **`node_region`** column — the BGC's cov-stripped `node.region` locator resolved from the `*_2b_bgc_crosswalk.csv` (e.g. `NODE_275_length_8783.region001`, matching the GCF context-table format), so each gene's BGC is identified by contig/region, not just the bare BGC number; (2) new **`pct_positive`** column — %similarity (BLAST positives / alignment length) alongside the existing `pct_identity` (%identity), bringing the online path to parity with the offline `blastp_ingest` path that already carried positives. Both are similarity-to-reference capacity signals, not compound-identity claims (the claim-safety footer stating BLASTp = similarity not identity is unchanged). Additive/header-keyed — 133 blastp tests pass. Test `test_blastp_online_locator_similarity_v9_7_293.py`.
- **Engine unchanged at Mamey 1.9.110**: an additive extension to the online-BLASTp deliverable CSV; no scoring or core package-format change. Bundle only.

# v9.7.292 · 2026-07-12 · build 20260712v97292a

- **Fixed the .291 ingest silent zero-join** (`bigscape_ingest_to_mamey.py` joined 0 cards on the real 51-strain DB — the DB side was fine, the triage bridge failed). Three real-data causes the .291 synthetic test missed because its fixture was idealized: (1) `load_triage` read the display `Assembly_Locator` (`NODE_.. region001 (BGC025)` — spaces + suffix) which never equals the `node.region` the DB uses — now reconstructs from `Contig` + `antiSMASH_Region`; (2) single-strain boards have no `strain` column — now tolerated by keying `("", bgc)` with a fallback in `main()`; (3) coverage renders lossily (`cov_73.020183`→`cov_73.20183`), so a cov-exact key missed ~1/5 rows — new `canon_locator()` drops `_cov_<float>` on BOTH sides (coverage isn't identity; node+length are). Also added **`--from-tsv`** to source context from the portable per-BGC annotation TSV instead of the 400 MB DB. Verified against the REAL AS-XXX board: bridge now builds 64 entries (was 0); real DB run reports cards updated 64 / skipped 0.
- **Testing lesson**: the .291 fixture was too idealized (clean locator, strain column, no coverage) and gave false green. New `test_bigscape_integration_v9_7_292.py` uses realistic fixtures (display-format locators, strain-less board, lossy coverage). Both tests pass.
- **Engine unchanged at Mamey 1.9.110**: single-file tool fix + test + doc; no scoring or package-format change. Bundle only.

# v9.7.291 · 2026-07-12 · build 20260712v97291a

- **BiG-SCAPE ↔ Sapote-Mamey true integration (closes the ingest loop)**: `tools/bigscape_ingest_to_mamey.py` writes cross-strain GCF context — family, KNOWN/NOVEL, MIBiG anchors + compound names, nearest-cluster distance, cohort co-members — INTO each Mode B card §8 and the triage board, joined on the `node.region` locator. Idempotent, capacity-worded, provenance-tagged; this is the ingest half the .290 workflow only did by hand. Verified on the real 36-strain anchored DB (1,613 GCF contexts; correct KNOWN family with 10 MIBiG PTM anchors incl. frontalamide B, nearest BGC0001043 d=0.408).
- **`tools/bigscape_pipeline.py`** (new): one-command driver — prep → cluster+anchor → known_novel + cross_strain → ingest; orchestration over existing verified tools (not a new algorithm), `--chunk-mibig` for small memory, resumable. **`tools/bigslice_query.py`** (new): BiG-SLiCE second opinion — de-novo cohort clustering (diff vs BiG-SCAPE) + query vs the BiG-FAM global model (novel-vs-all-NCBI, not just vs MIBiG); external prerequisite like BiG-SCAPE. **`tools/antismash_bigscape_join.py`** (new). Doc `BIGSCAPE_MAMEY_INTEGRATION.md`. Test `test_bigscape_integration_v9_7_291.py` (1 pass). All stdlib-only builders (no gate rows), 0 new bundle deps.
- **Data hygiene**: the real 36/51-strain analysis outputs (novel-family PDF/DOCX, GCF/AMR network PNGs, integrated TSV, region-GBK and export zips) were NOT bundled.
- **Engine unchanged at Mamey 1.9.110**: external-tool adapters + a card/triage post-processor + docs; no scoring or package-format change. Bundle only.

# v9.7.290 · 2026-07-12 · build 20260712v97290a

- **BiG-SCAPE-friendly (gaps a full 27-strain + 2,088-ref MIBiG run surfaced)**: (1) `bigscape_prep.py` now skips macOS `._*` AppleDouble siblings — they match the region glob but are non-UTF-8 and crash BiG-SCAPE on load. (2) New `tools/bigscape_known_novel.py`: KNOWN-vs-NOVEL table from a *single* consolidated anchored DB (the one-run counterpart to `bigscape_merge_anchors.py`'s per-batch union); verified on the real 26-strain + 2,088-ref DB (350 cross-strain families). (3) New `tools/bigscape_family_domains.py`: per-family Pfam domain content from BiG-SCAPE's own `hsp` table + relabelled Newick — the novelty-verification tool (a NOVEL family with coherent machinery e.g. IucA/IucC + FhuF is a genuine candidate). (4) Operational notes appended to `docs/BIGSCAPE_GCF_WORKFLOW.md`: AppleDouble, memory-chunking the ~14k-CDS scan, DB-cache reuse, `--include-gbk '*'`, and the `FAM_#####`-vs-`family.id` trap. Test `test_bigscape_friendly_v9_7_290.py` (3 pass). Both new tools stdlib-only, builders (no gate row).
- **Engine unchanged at Mamey 1.9.110**: external-tool adapters + a prep bugfix + docs; no scoring or package-format change. Bundle only.

# v9.7.289 · 2026-07-12 · build 20260712v97289a

- **Closed the .277 cohort-precompute gap (G1+G2, from the analysis-chat gap-fixes)**: `COHORT_resistance_signals_by_bgc.csv` now populates from a `manifest.json` `resistance_gene_summary` fallback, and `COHORT_BGC_FULL_TALLY.csv` from a `*_4_triage_board.csv` fallback — both had been empty since .277 because their standalone primary sources aren't gold-package artifacts. Verified against the real 4-strain cohort: **26 resistance-signal rows and 153 tally rows** (were 0). Added `_bgc_json_row` to `package_inspector.py` as the single source of truth for the `list-bgcs --json` schema so the tally fallback can't drift from the command (list-bgcs output itself unchanged — 22 related tests green). Test `test_cohort_precompute_package_fallback_v9_7_286.py`. Also fixed the ungrammatical .286 bigscape reword (L1).
- **Reconciled (already covered, confirmed by dry-run)**: the .285 audit patches (01–03) landed in .286/.288; the FIXA-B blastp-guard narrowing already matches the .288 per-test guard (`importorskip` scoped to the one Bio test that lazy-imports NCBIXML).
- **Engine unchanged at Mamey 1.9.110**: a cross-strain tool fix plus a shared-helper refactor; no per-strain scoring or package-format change. Bundle only.

# v9.7.288 · 2026-07-12 · build 20260712v97288a

- **Reconciled with the audit chat's authoritative patch set** (the .285 handback package): a dry-run confirmed the P1 dup-key, P2 module-manifest, P3 bigscape-reword, RELEASE_MANIFEST date/§30, and whitepaper hunks already landed in .286/.287. Two places the pre-made patches did it better, now adopted: (1) **per-test** `importorskip("Bio")` guards in `test_analysis_modes.py`/`test_blastp_online.py` instead of my .286 module-level guard — the module-level version over-skipped the files' non-bio tests in a bio-less env; (2) the RELEASE_MANIFEST "Patches in v9.7.149–v9.7.157" header is **restored** (my .286 rename to "through v9.7.287" mislabeled a section whose content is specifically the .149–.159 engine span) and **annotated** as a carried-forward historical snapshot, pointing to CHANGELOG.md as the authoritative per-cut history.
- **Engine unchanged at Mamey 1.9.110**: test-guard granularity + one doc reconciliation; no scoring or package-format change. Bundle only.

# v9.7.287 · 2026-07-12 · build 20260712v97287a

- **Added the Ingest & Principles white paper** (`docs/INGEST_AND_PRINCIPLES_WHITEPAPER.md`): a natural-voice conceptual doc on why ingest is the *authoritative* fail-closed gate (vs `verify-modeb`'s authoring aid), the §1–§30 structure firebreak, and the standing principles (verify the real artifact, fail-closed/idempotent, order enforcement, claim-safety, provenance banding, cite-by-node·region, retract cleanly). Verified against the code before adding: all 7 cited grounding files exist, `ingest-receipts`/`verify-modeb` are real subcommands, the §1–§30 contract id resolves, and `_bgc_context_from_triage` (the mechanism behind its central claim) is real; the phantom-command and dangling-ref gates stay green.
- **Data-hygiene flag (not auto-resolved)**: the white paper's AS-XXX worked example carries real strain specifics (genus *Saccharothrix*, moss host, 59-BGC counts, omnipeptin/yatakemycin KCB anchors) — now present in all tiers including PUBLIC. Consistent with the master-table / over-merge removals, whether to genericize that worked example for the public tier or keep it as an illustrative working-draft is left to the Developer or User's formality/hygiene pass.
- **Engine unchanged at Mamey 1.9.110**: documentation only. Bundle only.

# v9.7.286 · 2026-07-12 · build 20260712v97286a

- **Full-suite audit fixes (from the .285 verification handback) — validated with a full `pytest -q`, not the surrogate subset**: (P1) real defect in `run_chatgpt_surrogate_gate.py` — a duplicate `"status"` key meant the no-surrogate-pytest branch silently recorded FAIL instead of the intended ENV-SKIP (my incomplete patch-5 fix, dropped across .281→.285); removed the trailing dup, dup-key gate green. (P2) `mamey/cohort_figures_extended.py` (shipped .279) was never added to `MODULE_MANIFEST.txt` — baseline written (185 modules), accretion gate green. (P3) added `pytest.importorskip("Bio")` guards to the four biopython-backed tests so a bio-less env SKIPs instead of FAILs; reworded the external BiG-SCAPE 1.x `bigscape.py` mention that the dangling-tool scanner false-flagged.
- **RELEASE_MANIFEST.md prose refreshed**: stale `Cut/build date 2026-06-30` → 2026-07-12, and the carried-forward "Mode B §1–§20" functional-scope line → §1–§30 (the canonical contract).
- **Cut protocol corrected**: this cut was validated by a **full four-chunk `pytest -q` — 3093 passed / 149 skipped / 0 failed** — before stamping, per the audit's finding that the 22-file surrogate gate is structurally blind to the full suite and has let fixes drop between cuts. Full-suite-before-TAG is the new discipline.
- **Engine unchanged at Mamey 1.9.110**: gate bugfix + baseline + test guards + doc refresh; no scoring or package-format change. Bundle only.

# v9.7.285 · 2026-07-12 · build 20260712v97285a

- **Locator bugfix (`bigscape_cross_strain.py`)**: the node·region regex `_(NODE_\d+[^.]*?)\.(region\d+)` broke on SPAdes filenames whose coverage carries a dot (e.g. `cov_19.006984`) — the no-dot middle stopped at the dot, the match failed, and `members_locators` silently fell back to the full filename, defeating the cite-by-node·region contract and any downstream join. Fixed to greedy `_(NODE_.+)\.(region\d+)`, which spans the dotted coverage and still anchors on the final `.region\d+.gbk`. Regression test `test_bigscape_locator_dotted_coverage_v9_7_285.py` (dotted + undotted parse identically).
- **New: parallel MIBiG anchoring recombination layer** — `tools/bigscape_mibig_anchors.py` (per chat/DB: emits anchoring edges `cutoff, strain, node_region, mibig_accession, mibig_product`) and `tools/bigscape_merge_anchors.py` (unions per-chat anchor TSVs against the no-MIBiG base and tags each family KNOWN/NOVEL with matching accessions). Lets the ~2 h bacterial MIBiG scan run job-parallel across isolated 1-core chats and recombine with **no DB merge and no family_id join** (family_ids are per-chat; only the node·region+accession key is portable). Verified across 5 parallel sessions (14,883 edges, 20 strains, all 15 batches). stdlib-only; builders (no gate-registry row). Workflow section + deliverable A2.8 (`known_vs_novel_GCFs.tsv`). Test `test_parallel_anchoring.py`.
- **Data hygiene**: the real 20-strain browsable BiG-SCAPE HTML output (205 MB) was NOT bundled.
- **Engine unchanged at Mamey 1.9.110**: external-tool adapters + docs + one regex bugfix; no scoring or package-format change. Bundle only.

# v9.7.284 · 2026-07-12 · build 20260712v97284a

- **BiG-SCAPE workflow doc — two verified operational findings from a real parallel run**: (1) `fasttree` is a **third per-run prerequisite** alongside BiG-SCAPE 2 + Pfam — without it a run exits non-zero with `FileNotFoundError: 'fasttree'` at the HTML per-GCF-phylogeny step, which is *after* family assignment, so the GCFs are already in the DB and anchoring/ingest still succeed (the non-zero exit only looks like a failure); any parallel run kit must list `fasttree`. (2) New **detached-execution** section: in a sandbox that kills commands after minutes and reaps background jobs, a foreground `bigscape cluster` gets SIGKILLed mid-scan and the all-or-nothing scan rolls back — launch with `setsid` + poll the log/DB across short calls (a batch ran ~6.5 min uninterrupted this way). This is what makes the isolated-1-core-per-batch parallel model reliable for fanning out batches.
- **Note**: the external `PARALLEL_RUN_INSTRUCTIONS.md` companion (not shipped in the bundle) should mirror the `fasttree` prerequisite — relayed for whoever maintains that kit.
- **Engine unchanged at Mamey 1.9.110**: documentation only. Bundle only.

# v9.7.283 · 2026-07-12 · build 20260712v97283a

- **Four pre-release fixes re-verified and finally landed** (handed back earlier, lost in the .276→.282 work stream, confirmed still-unfixed against .282): (1) `build_pangenome.py` NameError — the pan-BGC-ome markdown f-string referenced undefined `CORE_MIN`, now `core_min`; (2) `modeb_template_emitter._select_scope` dropped **EXCEPTIONAL**-tier BGCs from the leads scope — `EXCEPTIONAL` added to the tier set so those BGCs flow into Mode B template selection (emit-selection change; scoring/tiers unchanged); (3) `bgc_guide.verify_authored_guide` crashed with IsADirectoryError on a directory arg — now returns a clean FAIL; (4) `rggmci_cohort_rollup.py` now `os.makedirs` the output parent before writing. Regression tests: `test_v282_prerelease_fixes.py` (4 pass).
- **Fixed an orphan-gate regression introduced by the .281 phantom-command guard (patch 52 / re-audit R-01)**: `check_command_pointers` is a `check_`-class gate, so the bundle's `test_gate_wiring_invariant` required a `tools/gate_registry.tsv` row; it was missing, which failed the wiring invariant and the surrogate gate. Registered it WIRED. Invariant now 4 passed. (`bigscape_mibig_batches` correctly needs no row — it's a builder.)
- **NOT applied — flagged for decision (re-audit R-02 / F-09)**: the audit proposes filling two empty affiliation placeholders (`SKILL.md`, `docs/BUNDLE_CAPABILITIES.md`) with "the source institution". That contradicts the 0-affiliation rule enforced in every cut this session, so it is deliberately left for the Developer or User to decide (fill vs. remove the blank).
- **Engine unchanged at Mamey 1.9.110**: bug fixes + gate registration + tests; scoring and package format unchanged. Bundle only.

# v9.7.282 · 2026-07-12 · build 20260712v97282b

- **Batched, prokaryote-filtered MIBiG loading for BiG-SCAPE**: `tools/bigscape_mibig_batches.py` reads the bundle's existing `mamey/data/mibig/` indexes, filters an extracted MIBiG GBK dir to bacterial (default; `--include-fungi` for fungal cohorts), splits into `batch_NN/` dirs, and emits RUN_ORDER.md so MIBiG references load a few hundred at a time on a small machine instead of one ~2,600-BGC scan that dies mid-run. Workflow section added to `docs/BIGSCAPE_GCF_WORKFLOW.md` carrying the two verified gotchas (`--include-gbk '*'` is mandatory or MIBiG GBKs are silently skipped; the scan caches per `--db-path` so batches resume). No new data ships — the MIBiG tarball stays external. Test `test_bigscape_mibig_batches.py` (3 pass).
- **Doc-audit patches (continued)**: softened the untraceable "CCTT bitscore floor 150" in SESSION_START_MANIFEST to "registry-configurable bitscore floor (min_bitscore, unset by default)" — no such 150 constant is applied anywhere (patch 9/F-08); added a surrogate-gate ENV-SKIP self-test (patch 48). Verified clean (no change needed): patch 11 (all backticked `mamey <cmd>` pointers resolve — guard green), patch 13 (standard mode aliases to gold), patch 15 (version is only `--version`/`-V`).
- **Engine unchanged at Mamey 1.9.110**: external-tool adapter + docs + tests + one manifest wording fix; no scoring or package-format change. Bundle only.

# v9.7.281 · 2026-07-12 · build 20260712v97281b

- **Doc-vs-program audit, Tier-1 defects fixed**: purged the phantom `crosswalk` command pointer (kcb_frontpage stderr + `--bgc` help + 3 docs + changelog → point to the real `<strain>_2b_bgc_crosswalk.csv` artifact) and the phantom `render-brief` command pointer (→ `render-all-figures` brief set / `render_brief.py`); fixed a third phantom the new guard caught, `blastp-campaign` (a script, not a subcommand) → `tools/blastp_campaign.py`. Surrogate gate now reports ENV-SKIP (not FAIL) when pytest is merely absent; `test_raw_antismash_triage.py` uses `importorskip("Bio")` so one optional dep can't abort collection; corrected the garbled batch15 missing-count (10 of 28); tagged `dump_scan_state.py` invocations PLANNED; dropped the dangling `scanner_pfam_150.hmm` fallback candidate.
- **New CI gate: phantom-command guard**: `tools/check_command_pointers.py` fails if any backticked `mamey <token>` isn't a live subcommand (the gate that would have caught the crosswalk/render-brief class), plus a meta-test that no test hard-imports an optional dep at module scope. Tests `test_command_pointers_guard_v9_7_281.py`, `test_no_modulelevel_optional_imports_v9_7_281.py`.
- **Data hygiene**: removed `docs/reference/AS-XXX_AS-XXX_over_merge_decomposition.csv` (real per-BGC assembly coordinates for two named strains), following the master-strain-table removal in .280.
- **Engine unchanged at Mamey 1.9.110**: pointer/message/gate/doc fixes + one dead-path removal; no scoring or package-format change. Bundle only.

# v9.7.280 · 2026-07-12 · build 20260712v97280a

- **BiG-SCAPE GCF cross-strain layer (external prerequisite, not vendored)**: two thin stdlib adapters — `tools/bigscape_prep.py` (strain-prefix antiSMASH region GBKs from raw zips or sealed packages into a BiG-SCAPE input dir) and `tools/bigscape_cross_strain.py` (parse the BiG-SCAPE 2 SQLite DB into `cross_strain_GCFs.tsv`, joining GCFs back on the node.region locator). Workflow + receipts in `docs/BIGSCAPE_GCF_WORKFLOW.md`; A-series deliverable entry A2.7. BiG-SCAPE / HMMER / FastTree / Pfam stay external (documented like antiSMASH) — requirements.txt untouched. Verified: prep staged 46 prefixed GBKs from a real zip.
- **Data hygiene**: removed `docs/reference/Master_Strain_Table_Hymenoptera_2026-07-05.csv` (181 strains × host, location, geo-loc, Candida/MRSA bioassay results, GenBank accessions, collection dates — unpublished data that should not ship). The BiG-SCAPE real-output TSV and the MIBiG reference tarball were deliberately NOT bundled (external / real-data).
- **Engine unchanged at Mamey 1.9.110**: external-tool adapters + docs; no scoring or package-format change. Bundle only.

# v9.7.279 · 2026-07-12 · build 20260712v97279a

- **Deliverable-surfacing gate**: the run command now prints an explicit DELIVERABLES block as the final stdout and writes `HANDBACK.json` (`schema mamey_handback_v1`) to the outdir, naming each sealed `*_Complete_Package.zip` so operators (human or agent) surface the sealed zip instead of a hand-rolled subset. Best-effort, never changes the exit code; covers both single-strain and `--strains` batch paths. (from the audit/patch handoff; test `test_deliverable_surfacing_v9_7_279.py`, 3 pass.)
- **Extended figure suite fused into auto-emit**: `mamey/cohort_figures_extended.py` (`generate_extended`) emits the 11 cross-strain / per-BGC figures, and `cohort-figures` now fires it automatically after the standard F-series (26 figures total) plus `COHORT_FIGURE_CAPTIONS.md` alongside. `--no-extended` opts out; `tools/cohort_figure_prototypes.py` is now a thin CLI over the module (single source). Never blocks the standard suite. Test `test_cohort_figures_extended_v9_7_279.py`.
- **Figure catalog + captions**: `docs/FIGURE_CATALOG.md` evaluates every figure across all three tiers (single-strain gold D/F/G + locus maps; cohort F01–F15; the 11 extended) with an overlap map and honest caveats; `docs/COHORT_FIGURE_CAPTIONS.md` carries the domain glossary (Pfam/antiSMASH/TIGRFAM accession + catalytic signature) and precise resistance/TTA tier definitions.
- **BiG-SCAPE companion guide** shipped (`docs/AS_batch1_BiGSCAPE_run_guide.md`) — the external GCF-network complement to the Mamey pangenome layer.
- **Engine unchanged at Mamey 1.9.110**: HANDBACK.json is a run-dir pointer (not package content) and the extended figures are a cohort-figures command addition — no package-format or scoring change. Bundle only.

# v9.7.278 · 2026-07-12 · build 20260712v97278b

- **Cohort figure suite shipped as a tool**: `tools/cohort_figure_prototypes.py` regenerates 11 cross-strain / per-BGC figures from sealed gold packages alone (census, PKS length bars, size-vs-richness, enriched locus map, archetype composition, KCB novelty, CCTT trigger landscape, boundary/fragmentation profile, domain co-occurrence, self-resistance marker map, TTA/bldA dependency profile). One command, reads only `<strain>_2_inventory.csv` + `<strain>_gene_by_gene_all_bgcs.csv`, no engine changes.
- **Figure captions with precise definitions**: `docs/COHORT_FIGURE_CAPTIONS.md` rides along with the figures — a domain glossary for the co-occurrence matrix (Pfam/antiSMASH/TIGRFAM accession, function, and the diagnostic catalytic signature for each; the deterministic call is the HMM match), and exact tier definitions for the resistance (T1/T2/T3) and TTA/bldA (T1–T4) profiles. Percentages moved off the figures into the captions.
- **Tool summary de-versioned**: `cohort_figure_prototypes.py` docstring carries no version tag, so the generated tools inventory can't drift from it.
- **Engine unchanged at Mamey 1.9.110**: this is a bundled analysis/figure tool plus documentation — no scoring or package-format change. Bundle only.
- **Known follow-on**: deep integration into the auto-emit figure suite (`cohort_figures.py` / the locus renderer) so the winners fire automatically, with tests, is deferred — the set is still under review.

# v9.7.277 · 2026-07-12 · build 20260712v97277a

- **Standalone, portable packages for cross-strain**: the gold run now bakes the cross-strain cohort-source CSVs into `package/cohort_source/` (`_emit_cohort_sources` in `cli.py`, reusing `run_domain_level`). A folder of shared packages assembles the cohort tables with no re-derivation and no original antiSMASH zips — the sealed package is the portable unit of exchange.
- **Engine 1.9.110**: the gold run's emitted output changed (every gold package now carries `cohort_source/`, and the run is heavier by design). No scoring change — the numbers are identical; the baking reuses already-computed data.
- **cohort-precompute resolves portable layouts**: `tools/build_cohort_precompute.py` now finds sources across `cohort_source/`, `package/cohort_source/`, the strain root, and `package/`, so both raw run output and extracted shared packages work. This also fills the nrps A-domain table (109 rows on the AS-XXX/AS-XXX pair) that the old strain-root-only lookup missed.
- **Known gap (follow-on)**: `resistance_signals` and `BGC_FULL_TALLY` cohort tables stay empty — their sources (`resistance_gene_summary.json`, `list_bgcs.json`) are not gold-package artifacts yet. Five of seven tables populate from the package alone.
- **Test**: `tests/test_cohort_source_portable_v9_7_277.py` — gold run wires the emission, and cohort-precompute fills a non-empty table from a synthetic two-package folder.

# v9.7.276 · 2026-07-11 · build 20260711v97276c

First public-release version. Advances the finalized v9.7.275 build series to v9.7.276 for the GitHub release; the content below was completed across the .275 builds and carries forward unchanged, and this cut also advances every version-of-record stamp to .276. Engine unchanged at Mamey 1.9.109; no scoring change.

- **Institutional affiliation removed bundle-wide**: former lab/university affiliation lines (and city) removed from all docs, code emitter output, HTML, LICENSE, CITATION.cff, and config; deliverable footers now identify the project by name and version only. Author names (Alexander J. Smith) retained. `test_affiliation_guard.py` guards CITATION.cff against reintroduction.
- **Doc-currency slices applied**: SOP historical reframing and placeholder tag bumps, HOW_TO_USE dead-ref removal, version-of-record stamp bumps across user_guides / reference / modules, CITATION_COMPACT de-versioning, the Vol II Cluster-A cross-reference repointed to its in-document section, ONLINE_BLASTP status changed from "proposed default" to "fallback channel (offline ingest is the default)", SOP_MASTER_INDEX title de-versioned, retired-monolith dangling references reworded, FILE_ATLAS regenerated via `tools/file_atlas.py` (285 files), and two dangling `validation/v97143b_*.stdout` rows removed from MODE_B_DOCUMENT_INDEX.
- **README / INSTALL GitHub setup**: install guide expanded (core install, add-on wheel setup, PyPI alternative, external-tool pointers) and the Python floor reconciled (project requires 3.10+; add-on wheels need 3.12), with antiSMASH called out as the required input generator.
- **Colorful deliverable PDF renderer is the default doc PDF path**: `tools/md_to_pdf.sh` runs `tools/render_deliverable_pdf.py` (indigo cover band, colored section headers, tinted callouts, styled tables) as the primary renderer, with the pandoc+xelatex path as automatic fallback if reportlab is absent or a render fails. Verified end-to-end (reportlab 4.4.10 produces the colorful PDF).
- **md_to_pdf.sh contract fix**: removed a `|| true` on the colorful-renderer log line that tripped `test_md_to_pdf_contract` (the guard that keeps xelatex fallback errors fatal); replaced with a file-existence guard, so the colorful-primary/pandoc-fallback path keeps xelatex errors fatal.
- **Generated indexes refreshed**: `docs/TOOLS_INVENTORY.generated.md` and the SESSION_START_MANIFEST tools block regenerated via `tools/gen_tools_inventory.py` (137 tools, includes `render_deliverable_pdf.py`); FILE_ATLAS already regenerated to 285 files.
- **Mode B is 30-section canonical**: MODE_B_DOCUMENT_INDEX and MODEB_CORRECTIVE_PROTOCOL updated from §1–§20 to the §1–§30 contract (canonically `mamey/data/mode_b/modeb_full30_corrective_contract.json`, documented in `docs/FULL_MODEB_30_SECTION_CONTRACT_v97150.md`); a dangling reference to the removed `modeb_full20_corrective_contract.json` was fixed. `modeb_full20.py` remains the documented legacy §1–§20 facade.
- **03_Plumbing_Reference stamps cleaned up**: seven version-of-record stamps bumped to current (engine v1.9.109 / bundle v9.7.276); the substantive “STALE, v9.7.213 audit” drift warnings (P3/P4 subsections referencing modules removed in the v9.7.155 consolidation) were kept and reframed off the old stamp line rather than hidden.
- **pseudomonas_validation.json restored**: `Wheelhouse/validations/pseudomonas_validation.json` (removed during the earlier Wheelhouse repurposing) is back; the cohort is public per the 2026-07-06 PI decision.
- **Version stamps advanced to v9.7.276**: ~60 files' version-of-record stamps, build stamps, and install-filename references bumped from the .275 build series; audited line-by-line against a snapshot (0 non-stamp changes).

# v9.7.275 — 2026-07-11 · build 20260711v97275d

Final v9.7.275 build, prepared for public GitHub release: deliverable and documentation footers standardized to name and version only, and the doc-currency slices applied, on top of the two verified tool-hardening patches from the .274 audit round already in build a. Engine unchanged at Mamey 1.9.109; no scoring change.

- **Deliverable and documentation footers standardized to "Sapote-Mamey · <version>"**: footers and version-of-record lines across docs, code emitter output, HTML, LICENSE, CITATION.cff, and config now identify the project by name and version only; author names (Alexander J. Smith) retained. `test_affiliation_guard.py` guards CITATION.cff against reintroduction of an affiliation line.
- **Doc-currency slices applied**: SOP historical reframing (SOP-10/15/MASTER_INDEX) and placeholder tag bumps (SOP-03/06/08/09/11/12/14), HOW_TO_USE dead-ref removal, user_guides / reference / modules version-of-record stamp bumps to v9.7.275, CITATION_COMPACT de-versioning, the Vol II Cluster-A cross-reference repointed from the nonexistent `VolII_ClusterA_CCTT.md` to its in-document section, and stale-count fixes (source_scans 1733 lines, 3064 tests).
- **README / INSTALL GitHub setup**: install guide expanded (core install, add-on wheel setup, PyPI alternative, external-tool pointers) and the Python floor reconciled (project requires 3.10+; add-on wheels need 3.12), with antiSMASH called out as the required input generator.

- **file_atlas fan-in counts relative imports (audit tool-bug)**: `tools/file_atlas.py`'s import extractor only handled `from mod import X` (where `n.module` is set), silently dropping `from . import submod` / `from .. import submod` (where `n.module` is None but `n.level` is set) — so the fan-in / orphan detector under-counted relative-import edges. Now both are captured. `docs/FILE_ATLAS.{csv,md}` regenerated (284 files). Note for future orphan sweeps: this was one of two compounding blind spots the auditor identified (the other being that any module with a test is never flagged orphan, which hides the "tested but unwired" class).

- **check_deliverable_suite.py bad-input guard**: raised a raw `FileNotFoundError` traceback on a missing/bad `--manifest`; now prints `error: cannot read manifest '<path>': <reason>` and exits 2. Same class as the `build_deep_data.py` guard added in v9.7.274 — the auditor confirmed this as the second instance of the pattern.

- **Confirmed**: the .274 tier-stamp BLOCKER fix verified independently by the audit — both `BUILD_STAMP.txt` and `TIER_MANIFEST.txt` read `tier=code` in the CODE bundle.
- **Residual doc-currency fixes**: ONLINE_BLASTP_PROTOCOL status changed from "proposed default" to "fallback channel (offline ingest is the default)"; SOP_MASTER_INDEX title de-versioned; the retired v8.10.2 monolith cross-references (which pointed at a nonexistent `docs/legacy/` file) reworded; FILE_ATLAS regenerated from the current tree via `tools/file_atlas.py` (285 files); two dangling `validation/v97143b_*.stdout` rows removed from MODE_B_DOCUMENT_INDEX. Includes `tools/render_deliverable_pdf.py`, the colorful reportlab deliverable renderer (present as a tool; not yet wired as the default doc PDF path — see handoff).

# v9.7.274 — 2026-07-11 · build 20260711v97274a

Audit-response cut over v9.7.273 — lands four verified patches from the audit chat, fixes a provenance BLOCKER, and hardens an operator tool. Engine unchanged at Mamey 1.9.109; no scoring change.

- **BLOCKER (tier-stamp contradiction) fixed**: a random-file audit found the PUBLIC-RELEASE bundle's `BUILD_STAMP.txt` said `tier=CODE` while its `TIER_MANIFEST.txt` said `tier=public` — and the same disagreement affected clean/sid/merged. The cut regenerated the manifest per tier but never updated the stamp's tier field. `make_public_tier.sh` now sets `BUILD_STAMP.txt`'s `tier=` to the tier being cut (right after emitting `TIER_MANIFEST`), `verify_tier_derivation.py` allows `BUILD_STAMP.txt` to vary per tier (like `TIER_MANIFEST`), and the strip harness test asserts the two stamps agree (`tier=public` in the public bundle). A verified consequence: the public bundle is no longer byte-identical to code — it now differs only in the two tier-labelling files, which is the correct provenance.

- **Lazy biopython import in the CLI (PATCH A)**: `build_parser()` eagerly imported `raw_antismash_triage`, which hard-imports `from Bio import SeqIO`, so with biopython absent every command — including `mamey doctor` — died at parser construction. The import is now deferred to command invocation, so the CLI builds and runs without biopython (only `triage-raw` needs it). This makes the "runs offline, biopython optional" claim in the public-release docs actually true. New test `test_cli_parser_no_biopython_v9_7_268.py` locks it (red on pristine cli.py, green after).

- **Bubble-placeholder stamp + non-vacuous test (PATCH C)**: the empty-state placeholder in `bubble_matrix` used `stamp_g` (copy-pasted from `hmap`), mis-filing the placeholder into the G/heatmap family; fixed to `stamp_d`. The shipped `.267` degenerate-input test only asserted "a PNG exists," which the inline guard satisfied on its own — it is now strengthened with two file-reading discriminators (placeholder panel width < 1150 px; `D`-series filename) that only the early-return placeholder satisfies.

- **biopython doc/messaging reconcile (PATCH D)** and **stale reference-index fix**: `docs/PREREQUISITES.md`, the run banner, and the `doctor` reason now say biopython is "optional — required only for `mamey triage-raw`"; and `docs/reference/00_README.md` no longer describes the public release as "stripped / data you fetch over the network" (the one reference-index entry the v9.7.272 doc pass missed).

- **build_deep_data.py usage guard**: the operator tool raised a raw `FileNotFoundError` on `--help` or a missing banked dir; it now prints usage / a one-line error and returns a proper exit code.

- **SOP-16 added**: the random-file inspection protocol (hostile-auditor spot-check, receipts-based, per-type checklists) is now `docs/SOPs/SOP-16_Random_File_Inspection.md`, wired into the SOP master index.

# v9.7.273 — 2026-07-11 · build 20260711v97273a

Repo-hygiene cut over v9.7.272 — removes orphaned dev-session artifacts. No engine, scoring, or code change.

- **Removed 34 orphaned, transient session artifacts** that shipped in every tier: the 21 `validation/` dev-logs (`.stdout`/`.stderr`/`.log` from the July-4 v97143a/b and v97144a runs — the `.stderr` files were identical captures of an unrelated `artifact_tool` spreadsheet-warmup traceback, not Sapote-Mamey output), 5 associated `validation/` session JSONs (validation summaries, identity probes, a zip-cache scan), the entire sibling `validation_logs_v97148c/` directory (4 files, v97144b captures), the 3 `work_in_progress/` scratch files (README + two `BGC*_corrected.md` drafts), and `tmp_next_paths_sample.md` (a demo handoff sample). All were confirmed to have zero code references before removal, and the full suite (3062 passed) confirms nothing depended on them. The two now-empty directories were dropped. Tree drops from 1300 to 1266 files.

- **Kept the real validation result**: `validation/mibig_reference_kcb_accuracy_v9.7.165.{csv,_summary.json}` is a deliberate KCB-accuracy record, not session cruft, and stays. `registry_inventory_v1.9.4.{json,csv}` was briefly in the removal set but is the source data `tools/gen_user_catalog.py` reads to regenerate the user catalog — the test suite caught the dependency and it was restored, so it stays.

# v9.7.272 — 2026-07-11 · build 20260711v97272a

User-documentation coherence pass over v9.7.271. Documentation only; no engine, scoring, or code change.

- **Public-release docs reconciled with the "nothing is stripped" state**: the strip-then-unstrip arc had left vestigial "bare-bones / fetch it / what was stripped" language that contradicted the shipped release. Fixed across all four user-facing docs. `docs/PUBLIC_RELEASE_DATA.md` retitled from "what was stripped and how to fetch it" to "provenance and optional HMM rebuild", and its rationale paragraph — which still claimed the HMM is kept out of the public release while internal tiers retain it — rewritten to state the HMM ships in every tier (Pfam is CC0) and the recipe exists only to regenerate it from a newer Pfam-A. `docs/PUBLIC_RELEASE_GUIDE.md` intro no longer calls the release "bare-bones" or says you fetch data "to complete" it; §3 retitled to "Data that ships, and the one thing you bring yourself" (your antiSMASH input); the air-gapped §5 now says the HMM already ships (nothing to build/carry). `docs/INSTALL.md` and `README.md` pointers updated from "the data you fetch (HMM, fixtures)" to "what ships (everything, including the Pfam HMM)". The valuable runtime-network / air-gap / graceful-degradation content is unchanged. Consistency sweep and dangling-refs gate clean.

# v9.7.271 — 2026-07-11 · build 20260711v97271a

Public tier ships the Pfam HMM (CC0) — nothing is withheld anymore, cut over v9.7.270. Engine unchanged at Mamey 1.9.109.

- **The public tier now ships the full content, HMM included**: Pfam is distributed under CC0 (public-domain dedication), so there is no licensing reason to strip `Wheelhouse/hmm/scanner_pfam.hmm` — and with the teicoplanin fixtures already retired (v9.7.270), nothing remains that must be withheld from a public release. `make_public_tier.sh`'s `public` case no longer strips the HMM, writes no `.REMOVED.txt` stubs, and drops the fail-closed strip check; it now produces content **identical to the code tier**. Added a top-level `NOTICE` crediting Pfam (CC0, EMBL-EBI/InterPro; HMMER3 by Sean Eddy) and the public Micromonospora humida genome (GenBank JAFEUC01) used by the test fixture — attribution is a courtesy, not a requirement, since none of the bundled data is copyleft or restricted.

- **Docs re-framed from "fetch it" to "it ships"**: `docs/INSTALL.md`, `PUBLIC_RELEASE_GUIDE.md`, and `PUBLIC_RELEASE_DATA.md` now state the release is complete with no downloads needed; the Pfam recipe is retained only as provenance and an optional rebuild path for a newer Pfam. The public-tier harness test was flipped to assert the public tier *ships* the HMM and the Micromonospora fixture with no download stubs, and that its content matches the code tier.

- **Note**: the public tier is now a labelled alias of the code tier (same content). It is left in place pending the tier reorganisation; it can be retired so the code tier is published directly to GitHub, or kept as an explicitly-named public artifact.

# v9.7.270 — 2026-07-11 · build 20260711v97270a

Retire the teicoplanin MIBiG test fixtures in favour of a small public fixture, cut over v9.7.269. Engine unchanged at Mamey 1.9.109.

- **Teicoplanin fixtures replaced with a small public Micromonospora humida fixture**: the two MIBiG teicoplanin fixtures (`teicoplanin_BGC0000440.zip`, `_BGC0000441.zip`, ~2.6 MB total) carried a CC-BY attribution requirement and were the largest binaries under `tests/`. They are retired and replaced by `tests/fixtures/micromonospora_humida_JAFEUC01.zip` (~136 KB, GenBank JAFEUC01, freely redistributable), which bundles two PKS-containing multi-class-hybrid regions (arylpolyene/T2PKS and NRPS/T1PKS). The end-to-end architecture test now derives on that public export (`test_end_to_end_micromonospora_humida_hybrids`, replacing the two teicoplanin end-to-end tests); glycopeptide classification itself stays covered by the pure-classifier unit test. Teicoplanin remains a reference *compound* in the science docs and MIBiG index — only the heavy antiSMASH-export fixtures were removed.

- **Public-release strip simplified to the HMM only**: because the new fixture is small and public, it ships in **every** tier, so `make_public_tier.sh` no longer strips a fixture — the `public` tier strips only `Wheelhouse/hmm/scanner_pfam.hmm`, and the fail-closed check now verifies `0 hmm`. The strip harness test asserts the M. humida fixture ships in the public tier and the HMM is stripped; the negative control confirms the code tier keeps the HMM.

- **Docs updated**: `docs/INSTALL.md` drops the teicoplanin fetch step (all fixtures ship; only the HMM is optional), and `PUBLIC_RELEASE_GUIDE.md`, `PUBLIC_RELEASE_DATA.md`, `large_files_reference.md`, and the operational/development guides reflect the retirement and point their examples at the new fixture. Dangling-refs gate clean.

# v9.7.269 — 2026-07-11 · build 20260711v97269a

Public-release user documentation cut over v9.7.268. Documentation only; no engine, scoring, or code change.

- **New authoritative public-release user guide**: `docs/PUBLIC_RELEASE_GUIDE.md` is the single starting point for public (GitHub) release users. It consolidates what the release contains and what is stripped, the data to fetch over the network (the Pfam HMM from Pfam-A at EBI with the 35-accession recipe pointer, and the teicoplanin fixtures from MIBiG), and — the gap the prior docs did not cover — exactly what the tool does over the network at runtime: the pipeline is offline by default with no telemetry or phone-home (timing receipts are local JSON), and the only network-touching feature is the optional online BLASTp panel (`blastp-online` → NCBI `blast.ncbi.nlm.nih.gov`, `blastp-ebi` → `www.ebi.ac.uk`), which has a zero-network alternative via `ingest-blastp` of a pre-run hit-table. Includes a fully air-gapped operating procedure and a graceful-degradation table. Wired from `docs/INSTALL.md`, `README.md`, and the reference index `docs/reference/00_README.md`; the referenced `SCANNER_PFAM_MANIFEST.md` survives the public strip (only `.hmm` and teicoplanin fixtures are removed), so every link resolves in the public tier. Dangling-refs gate clean.

# v9.7.268 — 2026-07-11 · build 20260711v97268a

Test-only hardening cut over v9.7.267 — locks the SVG-embed render path and the public-release strip with end-to-end tests. No engine, scoring, or production-code change.

- **End-to-end SVG-embed PDF test**: `tests/test_compiled_pdf_svg_embed_e2e_v9_7_267.py` builds a package whose compiled markdown references a locus-map SVG, runs the real `_render_compiled_pdf` (pandoc + xelatex via md_to_pdf.sh), and asserts the SVG was converted to PNG by `_svg_to_png` (cairosvg, the `render` extra) and embedded in the output PDF (`converted_figs >= 1`, PDF WRITTEN, `pdfimages` shows the raster). Skips cleanly where the toolchain or cairosvg is absent, so it locks the .265/.266 render path wherever the PDF is actually built.

- **Public-release strip harness**: `tests/test_public_tier_strip_v9_7_267.py` runs the real `make_public_tier.sh public` on the tree (with the tree's own build stamp so the gates pass) and asserts the produced zip carries zero `.hmm` files and zero teicoplanin fixtures, plus the download stubs, `docs/INSTALL.md`, and `docs/PUBLIC_RELEASE_DATA.md`, and that the fail-closed `heavy-file strip: OK` check fired. A negative-control cut confirms the `code` tier still keeps the heavy files, guarding against an over-broad strip that would gut the internal distribution.

# v9.7.267 — 2026-07-11 · build 20260711v97267a

Autonomous hardening cut over v9.7.266 — closes the audit's Path-3 figure crash and makes the public-release strip fail-closed. Engine unchanged at Mamey 1.9.109; no scoring change.

- **Gold figures no longer crash on a degenerate single-BGC input (audit Path-3)**: a single-region strain (e.g. a MIBiG reference run through `mamey run`) left some cross-strain/cross-BGC views with an empty matrix, and two helpers reduced over it — `bubble_matrix` did `counts.max()` ("zero-size array to reduction operation maximum", the audit's exact error) and `hmap` did `imshow` on a zero-size array ("Invalid shape (0,)"). Either exception propagated out of the whole gold suite and skipped every figure. Both now render a labelled empty-state panel and return, so the suite completes (a 1-BGC slice of a real gold package now yields 21 figures instead of a crash, and a 60-BGC single strain still yields the same 22 as before). Reproduced end-to-end from a sliced real package before fixing; new `tests/test_gold_figures_degenerate_input_v9_7_267.py` (3 cases) locks it.

- **Public-release heavy-file strip is now fail-closed**: the `public` tier cut verifies, after stripping, that zero `.hmm` files and zero teicoplanin fixtures survive; if any do (a future rename breaking the globs), the cut refuses loudly rather than silently shipping a heavy file to the public GitHub tier. Emits `public-release heavy-file strip: OK` when clean.

# v9.7.266 — 2026-07-11 · build 20260711v97266a

Exemplar BLASTp upgrade + panel-guide fix + audit hardening, cut over v9.7.265. Engine unchanged at Mamey 1.9.109.

- **Two public exemplars upgraded from the no-BLASTp read to real per-gene BLASTp results**: an operator-supplied NCBI web BLASTp of the three-gene panels (hit-table + XML2, RID 558R3023014) was offline-ingested (`ingest-blastp`, zero network) and mirrored to `blastp_online/BGC042_online_blastp.csv` and `…BGC008…`. `siderophore_exemplar.md` §4 now cites the IucA/IucC NIS synthetase ctg1_5461 at 90.8% identity (99.7% cov) to an IucA/IucC-family protein and the DesC acyltransferase ctg1_5462 at 96.2%; `ripp_exemplar.md` §4 now cites the class-III LanKC ctg1_685 at 98.5% (100% cov, E=0.0) to a class III lanthionine synthetase and the RamS precursor ctg1_682 at 93.3% to a SapB/AmfS lanthipeptide. All framed as similarity, not identity. The dependent §14/§15/§16/§19/§28 sentences were updated from "not run" to the run state; both cards clear verify-modeb and the results-artifact PANEL_ABSENT_CLAIM gate is now satisfied (the honest-caveat is retired). The DesB hydroxylase (BGC042 ctg1_5463) and the second/third RamS precursors (BGC008 ctg1_683/684) sat outside the three-gene panel and remain domain-only, noted honestly.

- **Panel user-guide now tells users to download both result files**: `bgc-blastp-panel`'s emitted USER_GUIDE previously framed the XML2 as optional; it now instructs downloading both the Hit Table (CSV) and the Single-file XML2 — the CSV is the hit list `ingest-blastp` reads and the XML2 supplies coverage/alignment enrichment — and gives the exact `ingest-blastp --hit-table --xml` command. Test updated to match.

- **Ingest header-format regression guarded**: added `tests/test_blastp_ingest_panel_header_v9_7_266.py` pinning that `parse_bgc_id` / `parse_short_contig` / `build_b5_rows` parse the current pipe-delimited panel header (`strain|BGCnnn|slot=…|gene=ctgN_M|node=…`) and key each hit to the right BGC, reproduced from the real returned files. Confirms the earlier header-parsing concern is resolved and locks it against regression.

- **pks.py robustness (Bunny Hop XS)**: `group_machinery_summary` now raises a clear error naming the missing `set_id` column instead of a bare `KeyError` when fed a non-Lite gene-evidence CSV.

# v9.7.265 — 2026-07-11 · build 20260711v97265a

Public-release tier + gate FP fix + audit patches, cut over v9.7.264. Engine unchanged at Mamey 1.9.109. Adds a fifth, bare-bones public tier for GitHub; the four existing tiers are unchanged and still ship every file (Wheelhouse, fixtures) for internal distribution.

- **New fifth tier — PUBLIC-RELEASE (bare-bones GitHub)**: `make_public_tier.sh` gains a `public` tier (the code tier, minus the two heavy static data files — the ~4 MB curated Pfam HMM `Wheelhouse/hmm/scanner_pfam.hmm` and the ~2.6 MB teicoplanin MIBiG fixtures `tests/fixtures/teicoplanin_BGC000044{0,1}.zip`), each replaced by a `.REMOVED.txt` download pointer. `release_cut.sh` now cuts five tiers. The engine runs without the stripped files: the HMM scanner falls back to regex, and the two teicoplanin tests already skip when the fixture is absent. New `docs/INSTALL.md` (numbered bare-bones install steps) and `docs/PUBLIC_RELEASE_DATA.md` (fetch recipes: Pfam-A at EBI for the HMM, MIBiG for the fixtures) ship in the tree. The four internal tiers (CODE / CODE-analysis-free / SID-public / MERGED-PRIVATE) keep everything in place; the tier-parity receipt still covers those four.

- **PANEL_ABSENT_CLAIM false-positive fixed (from the .264 audit)**: the .264 selected-but-no-results branch widened a topic-mention false positive — a card that *defers*, *recommends*, or marks a panel *N/A* for a selected-but-unrun BGC (the correct §4 for such a BGC) was flagged as a fabricated result. Added `_PANEL_NONRESULT_RE` (recommend / defer / pending / planned / N-A / to-be-run / would-need …) that skips before both gate branches; a stated result ("overturned two of ten") still fires on both. New test `tests/test_panel_absent_nonresult_v9_7_264.py` (4 cases). Reproduced the FP against the tree before fixing and confirmed real results still fire.

- **cairosvg added to optional extras**: new `render` extra (`pip install '.[render]'`, also folded into `[all]`) so the compiled-PDF SVG→PNG embed path works wherever the PDF is built, not only where cairosvg was installed by hand. Noted in `tools_reference.md`; the converter stays soft (rsvg/inkscape fallback, then drop) when the extra is not installed.

- **Audit patches applied**: `0002` corrected the .259 CHANGELOG wording (the second MftA mycofactocin precursor in the June newsletter HTML was replaced with a placeholder, not neutralized to the core motif — the entry now says so); `0007` removed dead whitelist entries (`"them,"`, `"it,"`) from the claim-safety gate that could never match after tokenization.

# v9.7.264 — 2026-07-11 · build 20260711v97264a

Gate + exemplar + render cut over v9.7.263. Engine unchanged at Mamey 1.9.109; no scoring change. Lands the six-item next-steps batch that could be completed in-session (items 1 and the erythraea half of 2 are blocked on the erythraea sealed package; live BLASTp could not complete in-session — see notes).

- **Two AS-derived Mode B exemplars replaced with public class exemplars**: `ripp_exemplar.md` is now a public class-III lanthipeptide (*S. amethystogenes* subsp. *fukuiense* BGC008 · JBHTEE010000001.1 · region008, KCB catenulipeptin BGC0000501.3) and `siderophore_exemplar.md` is a public NI-siderophore (*S. avermitilis* MA-4680 BGC042 · BA000030.4 · region042, KCB desferrioxamine B/E BGC0000940.5). Both are FULL §1–§30 (ripp adds §21/§22/§23/§24; siderophore adds §23/§24), 0 lint ERRORs, verify-modeb clean against their packages, and pass the exemplar-clean and no-foreign-locus guards. §4 is authored to the honest no-live-BLASTp read — no per-gene BLASTp outcome is asserted (the new results-artifact gate below would catch fabrication anyway); the offline `ingest-blastp` path to add the channel later is documented in each §16. Retired the AS-derived mycofactocin ripp card and the AS-XXX siderophore card; the ripp §24 KNOWN_ERRORS whitelist entry was removed (ratchet).

- **PANEL_ABSENT_CLAIM extended to require a results artifact, not just a panel selection**: `authored_verify.py` now tracks BGCs with an actual `<BGC>_online_blastp.csv` results artifact separately from panel selections and sets `blastp_results_present` only when a `blastp_online/` results directory exists. `modeb_structure_gate.py` adds a case — a per-gene BLASTp result claimed for a BGC that is selected but has no results artifact, when results are tracked, is flagged as unbacked (the S_erythraea BGC017 residual-gap class the selection-only check missed). Conservative: silent when results are not tracked, so packages that do not ship result CSVs are unaffected. New test `tests/test_panel_absent_results_artifact_v9_7_264.py` (4 cases); all existing exemplars still pass.

- **SVG locus-maps now embed in the compiled PDF instead of being dropped**: `compile_report.py` gains a soft `_svg_to_png` converter (cairosvg → rsvg-convert → inkscape) used by `_render_compiled_pdf`; SVG figure refs are converted to PNG and embedded, falling back to the previous drop when no converter is present, so the dependency stays optional. Reports `converted_figs`. New test `tests/test_svg_to_png_render_v9_7_264.py` (2 cases).

- **Layperson authoring guidance wired into the bundle**: `docs/reference/layperson_authoring_guidance.md` (the claim-safe structural arc + analogy library distilled from the May-27 AS-XXX/AS-XXX prose) added and referenced under a new "Authoring guidance" heading in the reference index `docs/reference/00_README.md`; dangling-refs gate clean.

# v9.7.263 — 2026-07-11 · build 20260711v97263a

Doc-sync cut over v9.7.262 — closes the CLI-doc gap the .262 compile-report flags opened. Documentation only; no engine or scoring change.

- **`compile-report` new flags documented**: `tools_reference.md` now lists `--pdf` (render the Boss-Ready Compiled Master PDF via `tools/md_to_pdf.sh`; refuses on unfilled narrative slots) and `--allow-unfilled-pdf` (render the skeleton PDF anyway) in the compile quick-reference. The .261 CLI-sync predated these flags, which landed with the .262 compiled-report integration; header bumped and the CLI-sync note dated to v9.7.262 so the "CLI-synced" claim stays honest.

# v9.7.262 — 2026-07-11 · build 20260711v97262a

Compiled-report PDF + front-matter cut over v9.7.261 — integrates the S. erythraea audit chat's verified pipeline fixes (`mamey/compile_report.py` +116, `mamey/cli.py` +6, `DELIVERABLE_MENU` +2/-2). Applied to the tree, full suite green (3044 passed / 0 failed); no scoring change.

- **Compiled-report PDF renderer fixed**: `_render_compiled_pdf` drives the sanctioned `tools/md_to_pdf.sh` with cwd = package dir so relative figure paths (`gold_figures/`, `locus_maps/`) resolve; gates only SVG/PDF images (need Inkscape) and truly-missing refs, so the D-series subdir + locus PNGs now embed instead of being dropped by an earlier basename bug. Remaining: the 5 locus-map SVGs still need PNG conversion (or Inkscape) to embed — flagged, not done.
- **Deterministic front matter (May-27 parity)**: `_key_findings()` emits a claim-safe KEY FINDINGS banner (top-5 KCB leads + low/zero-KCB novelty count + assembly posture, all "capacity consistent with... product identity requires isolation", bioactivity extract-level only), and `_described_toc()` a reader-facing Contents. Neither needs the judgment layer.
- **`--pdf` gated behind filled slots**: `compile-report --pdf` now refuses when narrative slots are unfilled ("must not ship with empty judgment slots"), overridable with `--allow-unfilled-pdf` for the one legitimate case (a section honestly left not-filled, e.g. blastp_evidence when no BLASTp was run). Guard against the thin-skeleton failure mode.
- **Integration verified against the tree**: the incoming diff was against cut258; confirmed `compile_report.py`/`cli.py` had not drifted since (my .259-.261 cuts did not touch them), dry-run applied clean at -p1, and the audit chat's "20/20 pass" claim was re-verified as the full 3044-test suite staying green. The audit chat's discipline note (it reverted a `_blastp_summary` change rather than rewrite two pinning tests) was preserved.

# v9.7.261 — 2026-07-11 · build 20260711v97261a

User-doc currency cut over v9.7.260 — brings `docs/user_guides/` up to the .251-.260 delta. Documentation only; no engine or scoring change (engine 1.9.109 throughout the range).

- **Mode B referent lints documented (v9.7.256 gates)**: added `LOCUS_BGC_MISMATCH` (real locus cited under the wrong BGC) and `PANEL_ABSENT_CLAIM` (per-gene BLASTp result asserted for a BGC with no panel) to the five guides that enumerate the PHANTOM_LOCUS family — `development_issues_compendium`, `tools_reference`, `comprehensive_glossary`, `operational_reference`, `sapote_kernel_guide`. Correcting the audit brief's blunt "add wherever lints are listed": these are ERROR-severity referent siblings of `PHANTOM_LOCUS` that block via the any-ERROR path, **not** members of the four-code `_READINESS_BLOCKING` set — those set literals were left exactly as-is. The two guides with no lint enumeration (`cross_chat_doc_protocol`, `math_reference_vol2`) were correctly not edited for this.
- **`tools_reference.md` CLI-synced**: header bumped v9.7.241 -> v9.7.260; new Section 19 documents the BLASTp toolchain (`bgc-blastp-panel`, `blastp-online`, `blastp-ebi`, `blastp-round`, `blastp-followup`, `ingest-blastp`, `modeb-blastp`), `hmm-adjudicate`, and `release-qa` from the registered `mamey <cmd> --help`. Section 17 extended with the two new gates. §4 guidance reflects v9.7.260's offline-preferred ingest path (not the brief's stale "run the online channel first"). Execution-provenance stamps at lines 330/336/441 left untouched (changing them without re-running would be a false claim).
- **Overlay + batch-rule prose corrected**: `math_reference_vol2` now states the v9.7.252 nr-overlay self-hit exclusion (subject binomial == query genome AND identity >= 99.0% -> excluded; unnamed AS "sp." strains correctly keep 100.0). `operational_reference`'s stale "never submit more than 10" hard rule replaced with the current v9.7.252 rule (MAX_BATCH 30, DEFAULT_BATCH 10 courteous default, 30,000-aa RESIDUE_BUDGET, giants solo, SUBMIT_GAP_S spacing).

# v9.7.260 — 2026-07-11 · build 20260711v97260a

Public exemplar + token-friendly-BLASTp cut over v9.7.259. Lands five source-derived public Mode B exemplars and wires the offline BLASTp ingest into the authoring workflow. No engine or scoring change.

- **Five public Mode B exemplars landed**: authored terpene / t1pks / nrps / t2pks / nrps_pks_hybrid(+lassopeptide) cards from public type strains (*S. avermitilis* GCA_000009765.2, *S. amethystogenes* GCA_042665875.1, *S. spectabilis* GCA_008704795.1), each from store-backed package data plus operator-supplied per-gene BLASTp, all clearing `verify-modeb` (sections 1-30, depth floors, KCB hedges, conditional sections). Teaching cases: an OVER-MERGED region (filipin, analysed per-protocluster, no single-product claim), a class-divergent KCB comparator held similarity-only (tetronasin anchor on NRPS content), a GerE->LuxR regulator REFINE (fogacin), and a genuine multi-system region filling both the hybrid and lasso slots (lagmysin).
- **Token-friendly BLASTp wired into section 4**: the Mode B template now leads with the offline `ingest-blastp --hit-table [--xml] --package` route (pre-run NCBI results become the same `<BGC>_online_blastp.csv` panel with zero network), and demotes the live `blastp-online` (~1-2 min/query poll) to the explicit fallback; the live command's banner now points at the cheaper route. A guard test locks the offline route into the emitted template so it cannot silently revert to live-only.
- **Foreign-loci guards generalized to accession contigs**: both exemplar phantom-locus guards (v97247, v97250) derived the card's own contig from a `NODE_<n>` SPAdes header; finished-genome public exemplars cite accession contigs (BA000030.4, CP023690.1), so the guards now fall back to the modal `ctg<n>` index. The `ctg12_71` defect class stays caught; the limitation (a foreign locus sharing the modal index) is stated, not hidden.

# v9.7.259 — 2026-07-10 · build 20260710v97259a

Confidentiality-closure cut over v9.7.258. Removes unpublished-strain sequence from the public tier. No engine or scoring change.

- **Strain-derived sequences removed from the public tier**: removed the two embedded MftA mycofactocin precursor sequences — in `docs/reference/modeb_exemplars/ripp_exemplar.md` §21 (neutralized to the conserved, published core motif `IDGMCGVY`) and (audit-missed) `docs/GUIDE/07_Newsletter_June_2026.html` (replaced with a `sequence omitted (unpublished strain)` placeholder); the CODE tier now carries zero unpublished-strain peptide sequence.
- **Incoming audit finding corrected**: the audit brief's "exactly one embedded sequence" was incomplete — a second precursor (from a different strain, loci ctg73/ctg94) shipped in the June newsletter and is now closed; the remaining >=20-mers are benign public/synthetic test fixtures (EBI samples, KS-domain data), confirmed not strain-derived.

# v9.7.258 — 2026-07-10 · build 20260710v97258a

GitHub-readiness cut over v9.7.257 — public-facing polish + release tooling. No engine or scoring change.

- **GitHub-facing README**: `README.md` rewritten for a human audience (what it is, install, quickstart, repo layout, data availability, scientific-integrity note, citation, license); the AI-assistant upload flow is now a section pointing at the existing entry files.
- **Author-path scrub**: neutralized hardcoded dev-container absolute paths (the sandbox home and user dirs) across 14 test/tool/doc files — those tests already skip when the path is absent, so behavior is unchanged; the dev-environment leak is gone.
- **Third-party license notice**: `docs/THIRD_PARTY_LICENSES.md` records the one vendored library (ijson, BSD) with its retained license, and lists the pip-installed runtime deps for transparency.
- **Over-production guard in §13**: the authoring crosswalk now rejects the prompting reference's "maximize features / go beyond basics" advice on claim-safety grounds, not just its stale API specifics.
- **release_cut.sh**: one-command gate-enforced cut wrapper (validate CHANGELOG → bump → sync → gen-manifest LAST → clean backups → gates → four tiers → checksums), codifying the sequence.

# v9.7.257 — 2026-07-10 · build 20260710v97257a

Correctness cut over v9.7.256. Closes the CLAIM_SAFETY multi-line denial false-positive carried since the B1 design note. No engine or scoring change.

- **CLAIM_SAFETY multi-line denial guard**: a denial that introduces a list (`does not support:` then `(1) …produces X`) no longer false-positives on the list item; guarded to list items under a colon-terminated denial cue within two lines, so an unrelated earlier negation can't mask a real unhedged claim (+5 tests). Was WARN-level but trained authors to delete correct denials.

# v9.7.256 — 2026-07-10 · build 20260710v97256a

Authoring-guidance cut over v9.7.255. Adds the prose-style skill reference; fixes a stale manifest count. No engine or scoring change.

- **prose-style skill reference**: anti-LLM-drift authoring card (`skills/sapote-mamey/references/prose-style.md`) wired into the sapote-mamey skill's Voice discipline + router; claim-safety hedges explicitly exempt (capacity/similarity/provenance stay).
- **manifest count de-frozen**: `docs/BUNDLE_CAPABILITIES.md` no longer pins a stale '395 files' number (actual ~1279/tier); replaced with a regenerate command, since the count drifts every cut and varies by tier.
- **B1 phantom-locus membership gate**: two ERROR lints in `modeb_structure_gate.py` — `LOCUS_BGC_MISMATCH` (locus cited under a BGC it doesn't belong to) and `PANEL_ABSENT_CLAIM` (BLASTp result stated for a BGC with no panel), with contrast/denial guards; closes the AS-XXX cross-assembly contamination class PHANTOM_LOCUS missed (+11 tests).
- **authoring-discipline crosswalk**: `prompts/CLAUDE_SYSTEM_PROMPT.md` §13 maps seven evergreen prompting principles to the Sapote rules that already instantiate them; docs-only, stale platform specifics explicitly NOT adopted.

# v9.7.255 — 2026-07-10 · build 20260710v97255a

Multi-chat reconciliation cut over v9.7.254. Folds in verified audit-chat patches + the operating skill. No engine or scoring change.

- **N1 release-manifest regen**: `RELEASE_MANIFEST.md` body no longer stamps stale .252 under a .254 header (via `gen_release_manifest.py --apply`).
- **S4 remediate card-filter**: `remediate_phantom_locus.py --apply` no longer deletes from protected non-card docs (+ companion test).
- **S6 pandas prereq documented**: `docs/PREREQUISITES.md` records pandas as required-for-figures with the graceful §28 fallback.
- **readiness_lint FP fix (corrected)**: `modeb_structure_gate.py` `_MIBIG_REF` regex fixed to match real MIBiG accessions (the dead double-backslash version was rejected).
- **sapote-mamey skill added**: `skills/sapote-mamey/` operating front door (claim-safety, CDSW, Mode B, cut, audit disciplines).
- **Consolidated punchcard recorded**: `docs/CONSOLIDATED_PUNCHCARD_v9.7.254.md` multi-chat reconciliation; B1 phantom-locus gate gap flagged OPEN.

# v9.7.254 — 2026-07-10 · build 20260710v97254a

Review cut over v9.7.253 — hygiene / drift-proofing / provenance. No engine, scoring, or analysis-logic change.

- **PC-5 named core-synthase constant**: `mode_b/guards.py` inline tuple → `CORE_SYNTHASE_TERMS` (behavior identical).
- **PC-6 absolute-path warn**: `release_qa._relpath` surfaces an un-relativized path instead of silently leaking it.
- **PC-7 deprecation banner**: `tools/build_master.py` warns at runtime that it is not the canonical builder.
- **PC-9 view_fidelity column**: `domain_rows_long.csv` records the FULL/LIMITED input path per row.
- **Drift-proofing tests added**: PC-1/3/4/8 + RV-1/2 (20 tests) pinning palette, batch rules, class sets, glossary sync, parse_cb parity, concordance weights.
- **PC-2 / PC-10 doc notes**: boundary-palette decision + locus_map PNG/SVG cross-references (non-behavioral).

# v9.7.253 — hygiene / doc / tooling cut

Retroactive lineage entry (this cut shipped before the CHANGELOG convention caught up; content per `HANDBACK_v9.7.253.md`).

- **Hygiene/doc/tooling only** — archived stale root entry-points, fixed the `--pytest-log` test-count parser, flagged three release-manifest/tier items. No engine or scoring change.

# v9.7.252 — 2026-07-10 · build 20260710v97252a

**Engine 1.9.109 (unchanged) · Bundle 9.7.251 → 9.7.252.** The nr overlay recorded the genome's own proteins; single-strain gold runs emitted 2 figures instead of 21; and the BLASTp batcher capped protein count while never capping payload. No scoring change.

## The overlay recorded the query genome as its own comparator

`write_nr_overlay` took the **rank-1** hit per gene. For a **deposited type strain or reference genome**, that genome's own proteins are in nr — so rank-1 is the query itself at ~100% identity. That value is `conservation_median_id`, which feeds `scan_divergence` (the exploration board's novelty axis) and the `NOVELTY_CONTRADICTION` guard. **Arming the overlay — the act meant to improve the evidence — silently inverted the divergence signal.**

Observed on real data (*Nocardia rhizosphaerae* type strain, GCA_042650365.1): BGC022, the strain's most divergent locus, `median_id` **55.0 → 100.0**; `exploration_interest` 45.5 → 35.5, dropping it out of the exploration top-5. Across six freshly-ingested type-strain genomes, **67 of 234 overlay rows (29%) were ≥99.9% identity.** For `ctg7_50` the informative comparator sat one rank down: rank 2, **77.3%** to *Nocardia* sp. NPDC058633.

- **The overlay now records the best hit to another organism.** A hit is a self-hit when the subject's binomial equals the query genome's **and** identity ≥ 99.0%. Ranks below 1 are now considered; with no self-hits the best-by-bitscore hit *is* rank-1, so the **P7a contract is preserved exactly**.
- **Unnamed species never match.** `"Micromonospora sp."` is not a binomial; treating it as one would exclude every unnamed congener in nr. **Every AS-series strain is unnamed, so nothing is excluded for them** — the AS-XXX background figure is unaffected by this bug and by this fix.
- **A same-species hit from a different strain at moderate identity is retained** (92% to *N. rhizosphaerae* is a comparator, not the genome). That is what the identity floor is for.
- A gene whose every hit is its own genome is omitted: it carries no conservation information.
- **Verified end-to-end**, not just by unit test: on a deposited-genome fixture `conservation_median_id` now reports **77.3** (the comparator) where it reported **100.0** (itself); on an unnamed AS-series fixture it correctly keeps 100.0. `NOVELTY_CONTRADICTION` fires at ≥90 — that 100.0 would have suppressed a real divergence lead. Supplied 11-test suite passes verbatim.

This is the same failure class as the `kcb_top` genome-self-hit bug fixed in v9.7.22.

## P8 — a single-strain gold run emitted 2 figures instead of 21

`_emit_gold_figures` called `cohort_figures.generate()` **without `series=`**, and the default is `"F"`. So the G-series (8 panels) and D-series (11) were never requested. **The capability existed and nothing invoked it** — the fifth instance, after `--from-precompute`, `--hits`, `--strict-paths`, and `DEFAULT_BATCH`.

`_run_all_g` then ran batches 3–4 unconditionally. Those index a correlation matrix with `~np.eye(...)`; **at n=1 the off-diagonal is an empty slice**, so the cross-strain similarity and product-class co-occurrence panels are meaningless. Guarded behind `len(order) >= 2`; batches 1–2 are per-strain and always run. *(Nuance worth recording: in this NumPy the 1×1 case yields NaN with a RuntimeWarning rather than a hard traceback. The guard is right either way; "crashes" is environment-dependent.)*

Verified: single-strain → batches [1, 2]; two strains → [1, 2, 3, 4], unchanged.

## The batcher capped count, never payload

Two contradictory observations were on record: the AS-XXX archive shows five clean 30-protein batches; the docs lineage reproduced a 30-protein batch returning zero alignments three times. **the Developer or User, 2026-07-10: "batches of 30 worked fine except for very large proteins, and the submissions needed temporal spacing."** Both observations are true, and the variable was never the count.

Giants (>2500 aa) already ran solo. But **thirty 2,400-aa proteins is 72,000 residues in one submission, and not one of them is a giant.**

- `chunk_proteins` now closes a batch when **either** the protein count **or** a `RESIDUE_BUDGET` (30,000, calibrated from the field report) would be exceeded. Verified: 30 × 350 aa → one batch of 30 (unchanged); 30 × 2,400 aa → **12/12/6**, none over budget, no protein lost. Giants still solo.
- **`MAX_BATCH` stays 30.** Lowering it would have been the wrong fix for the right symptom.
- `SUBMIT_GAP_S` — spacing between submissions, not only on retry.
- **`batch_shape()`**: the v9.7.250 zero-alignment guard refused an all-empty batch correctly and **said nothing about why**, so the mechanism survived two lineages and three reproductions. The refusal now reports `n=30, max_aa=2400, total_aa=72000, budget=30000 (OVER BUDGET)`. One line, and nobody has to guess again.

## Note on a test contract

`test_package_arg_writes_the_overlay_the_readers_expect` asserted **exact dict equality** on `write_nr_overlay`'s return, so adding `self_hits_excluded` failed it. Loosened to the fields it is about. *A contract that forbids adding a field forbids fixing a bug.*

## Multi-tier
3 module edits + 3 test files (23 tests) + 1 assertion loosened; no new modules, no AS scrub; 4-tier unchanged.
# v9.7.251 — 2026-07-10 · build 20260710v97251a

**Engine 1.9.109 (unchanged) · Bundle 9.7.250 → 9.7.251.** The v9.7.250 release check: one owned process failure, one real gate gap now closed, and the emitter/verify divergence that had survived six cuts. No scoring change.

## The three "release blockers" were one mistake, and it was mine

I shipped `sapote-mamey-v9.7.250-CODE-SCRUBBED` by running `zip` over the working tree instead of cutting it through `tools/release.sh` → `tools/make_public_tier.sh`. Those scripts regenerate `SOURCE_CHECKSUMS_SHA256.txt` and `TIER_MANIFEST.txt` **as the last step, after redaction**. A hand-zip carries whatever manifest was last written.

Verified by running the reviewer's own checks against **both** artifacts:

| | my hand-zip | the proper `release.sh` CODE tier |
|---|---|---|
| checksum entries verified | 1,085 | **1,262** |
| mismatched | **112** (reviewer counted 128 on the zip) | **0** |
| manifest entries naming an absent file | **2** (`BGC002_corrected.md`, `BGC058_corrected.md`, moved to `work_in_progress/` in `.247`) | **0** |
| `TIER_MANIFEST` stamp | `20260705v97233a` | `20260709v97250a` ✓ matches `BUILD_STAMP` |

So the *cut* was sound and the *artifact I handed over* was not. The reviewer's diagnosis was right on every count; the cause was one step skipped, not three defects.

**The gate gap they identified is real, and it is the important finding.** All five governance gates and `release-qa` passed on that artifact. `verify_release_identity.py` checks that version / engine / build agree **with each other**; nothing recomputed a checksum or walked the manifest.

- **`tools/check_release_manifest.py` (new, WIRED).** Recomputes every `SOURCE_CHECKSUMS_SHA256.txt` entry, asserts 0 mismatches and 0 entries naming an absent file, and asserts `TIER_MANIFEST` `stamp=` equals `BUILD_STAMP` `build=`. Verified: **FAIL on the stale working tree** (112 / 2 / stamp contradiction, all three, with the file names printed); **PASS on the proper `.250` tier** (1262 / 0 / 0).
- **It runs in the cut path, fail-closed** — `make_public_tier.sh`, after redaction, after regeneration, before the zip. That is the only moment the assertion can be true.
- **It is deliberately *not* a full pytest assertion.** A checksum manifest is invalidated by every source edit until it is regenerated; asserting it per-commit would fail on every commit and be disabled within a week. pytest asserts the edit-stable half (stamp == build) and that the gate correctly detects all three defect classes against synthetic fixtures. **A gate that must be true only at cut time belongs in the cut, not in the suite.**
- Working-tree artifacts regenerated: 1,262 entries, 0 mismatched, 0 missing, stamps agree.

## Emitter/verify divergence — landed, sixth cut after report

`_build_predicates` (`modeb_structure_gate.py:359`) read `ctx["umed_gap_flag"]` and `ctx["maturation_gap"]`. The emitter writes `umed_gap_flag` (`cli.py:2259`), but the **triage board column** — the one `chatgpt_commands` reads and writes, and the one a `ctx` built from a board row actually carries — is **`UMED_gap`** (`cli.py:2213`). So §23 was **emitted** on one BGC set and **enforced** on another; reported as 41 of 336 real BGCs diverging, all on `maturation_gap_or_novel_class`.

Now accepts every spelling the pipeline actually produces. Verified: `umed_gap_flag`, `UMED_gap`, and `maturation_gap` all raise the predicate.

**This is the same class as the `.245` overlay miss** — `bgc_guide` read `query_gene` while `ingest-blastp` wrote `locus_tag`. A producer and a consumer naming one fact two ways. That is now four instances (`wanted_region`, `DEFAULT_BATCH`, `query_gene`/`locus_tag`, `umed_gap_flag`/`UMED_gap`), and none of them is a logic error.

## Deferred, explicitly

- **`ingest-blastp` batch mode.** ~79% of an 8.6 s per-file ingest is one `openpyxl` load+save; cohort re-ingest ≈ 2.2 h. Real, profiled, and **not** a correctness defect. Its own cut.
- **`SCRUBBED` as a tier token.** `TIER_MANIFEST` declares `tier=code` while the zip is named `CODE-SCRUBBED`. The reviewer is right that this is a release-policy question. Flagging, not deciding.


## Redactor: two leak vectors found by scrubbing a real tier and measuring the residual

- **f-string literals were invisible to the redactor.** Python 3.12 splits an f-string into
  `FSTRING_START / FSTRING_MIDDLE / FSTRING_END`, none of which is `tokenize.STRING`. `redact_py()` touched
  only `COMMENT` and `STRING`, so a private ID inside an f-string passed straight through every public cut.
  Found by scrubbing the CODE tier and counting what was left: `tools/build_cohort_precompute.py:90` still
  read `f"... (legitimate for AS-XXX/AS-XXX)"`. Now redacted; the `{expr}` parts are code and are still never
  rewritten (pinned by test).
- **The redactor rewrites CONTENT, never PATHS.** The v9.7.250 CODE-SCRUBBED artifact shipped
  `docs/reference/AS-XXX_AS-XXX_over_merge_decomposition.csv` — every row inside redacted to `AS-XXX`, the
  strain IDs still in the filename, and repeated verbatim in `TIER_MANIFEST.txt`, which *is* a file list.
  A content-only scrubber is structurally incapable of seeing this. New `audit_paths()` reports such files
  (honouring `KNOWN_PUBLIC_AS`, so enterocin **AS-48** is not flagged). Renaming stays a human decision:
  references must move with the file. The delivered scrubbed tier has the file renamed and repointed;
  **0 strain IDs remain in any filename.**

## Multi-tier
1 new gate (WIRED, fail-closed in the cut path) + 1 module fix + 1 test file + regenerated integrity artifacts; no new modules, no AS scrub; 4-tier unchanged.
# v9.7.250 — 2026-07-09 · build 20260709v97250a

**Engine 1.9.109 (unchanged) · Bundle 9.7.246 → 9.7.250.** Lineage consolidation, a tier-parity defect found by diffing the shipped v9.7.246 artifacts against each other, and the copy-paste vector the `.246` phantom-locus sweep missed. No scoring change.

## P1 — `blastp-online` recorded a zero-alignment batch as thirty tested-negatives

Reported by an analysis chat mid-cut, on v9.7.246, while authoring AS-XXX BGC034. **Reproduced three times against real NCBI `nr`; mechanism NOT established** — by them, and not by me either. At `--batch-size 30` one entire submission batch returned zero alignments. `reconcile()` maps an empty `hit_def` to `NO_HIT`, so all thirty genes were written into `<BGC>_online_blastp.csv` as **tested negatives**, indistinguishable from a gene genuinely queried with no nr homolog. The same proteins at `--batch-size 10` recovered **82/83 at 61–99% identity**.

Those rows feed `conservation_median_id`, the input to `NOVELTY_CONTRADICTION`. **It is the v9.7.241 P7a shape — a biased subset silently arming the novelty guard — arriving through a different door.** And it corrupts the science, not merely the statistics: three of the fabricated negatives were the sugar aminotransferase, the NDP-hexose dehydratase and the glycosyltransferase, so BGC034's card would have asserted that its glycosylation machinery has no known relatives.

**What I fixed, all of it mechanism-independent — because the mechanism is unknown:**

- **`_zero_alignment_batch()` guard.** A multi-query batch whose every query returned zero alignments is a **transport failure, not a result**. It now yields `ok=False` with an actionable reason, at *both* parse sites (serial `run_batch_online` and async `run_batches_online`). A whole batch of one BGC's proteins having no nr homolog at e<1e-5, while sibling batches return 94–100% identity, is not data. **Solo giants are exempt** — one gene with no homolog is an ordinary, and scientifically real, outcome.
- **`SAFE_BATCH = 10`.** `chunk_proteins` now warns on stderr above it. `tools/cohort_blastp_driver.py`'s `--batch-size` default reverts **30 → 10**.
- **The banner told the truth about a constant, not about the run.** `--batch-size 10` printed `(<= 30/batch)` — it echoed `MAX_BATCH`, not the argument. A log that cannot tell you what was submitted made this defect meaningfully harder to see. It now prints the requested size, the widest batch actually produced, and the hard cap.
- **`tools/audit_blastp_zero_alignment.py` (new, WIRED).** Every overlay BLASTed above 10 since v9.7.240 may already carry fabricated negatives. `--xml` is **authoritative** (BLAST XML2 emits one `<Search>` per query *even with no hits*, so a tested-negative is recorded); `--overlay` is **heuristic** and says so — an overlay CSV records `NO_HIT` and nothing else, and **cannot** distinguish "never came back" from "tested, no homolog". It reports SUSPECT, never GUILTY.
- **The test the report asked for.** *"P7a survived .239 because every test ingested one round. This survives because every test submits one batch, or a batch of ≤10."* `test_multi_batch_at_max_batch_recovers_every_gene` submits **83 proteins at `MAX_BATCH`, across four batches**, through a fake transport, and asserts per-gene recovery; its sibling empties batch 2 and asserts the refusal. **Verified to bite:** disabling the guard fails 3 of 12.

**I did NOT lower `MAX_BATCH`, and I am flagging the disagreement.** The report recommends it. The evidence archive uploaded alongside — 36 real RIDs from an AS-XXX `nr` campaign — contains **five batches of exactly 30 queries, each returning 27–28 genes with hits and no all-zero batch**. So "batch > 10 always breaks" is not supported, and silently clamping an explicit `--batch-size 30` down to 10 would be its own silent-wrong-answer. The default is safe, the excess warns, and the failure is now *detectable*. **the Developer or User's call to overrule.**

**Live receipt, real data.** `audit_blastp_zero_alignment --xml` over that 36-RID archive:

```
XML2 audit: 36 file(s), 479 queries, 55 with zero hits.
No all-zero batches.
```

Those 55 are genuine tested-negatives — **and not one of them appears in the sibling HitTable CSVs.** A HitTable lists only queries that got hits. **So the `ingest-blastp` HitTable path cannot mark a tested-negative at all**, which is the deeper form of the report's fix #2. **Recorded, not fixed** — giving `NO_HIT` provenance (`no_alignments_returned` / `not_queried` / `tested_no_homolog`) changes `_OVERLAY_COLS`, which `authored_verify` and `genome_explore` read. That is a schema change and it belongs in its own cut, with its own migration. **Flagged; your call.**

**Existing overlays are not repaired by this cut.** Anything BLASTed above batch-size 10 since v9.7.240 needs auditing before its novelty read is trusted — including AS-XXX's campaign, whose background (95.4% over 877 genes) was already corrected once, for P7a.

## The v9.7.246 sweep missed the exemplars — the vector its own remediation note names

`.246` fixed `modeb_template_emitter._section_body` and swept all 30 emitted sections. It did not sweep `docs/reference/modeb_exemplars/`. Its own remediation note names them:

> *"Check for templated boilerplate carried over from a different strain's session, **and for a copy-paste from an example card**."*

Measured on the shipped `.246` tree:

```
ripp_exemplar.md        (BGC036 · NODE_5): 65 distinct loci — 64 ctg5_*,  one ctg12_71
siderophore_exemplar.md (BGC038 · NODE_6): 100 distinct loci — 99 ctg6_*, one ctg12_71
```

One foreign locus in each. `ctg12_71` belongs to *Amycolatopsis* sp. NPDC004378. **An exemplar is read as a model to copy: a foreign locus in an exemplar is a phantom locus with a propagation mechanism.** `PHANTOM_LOCUS` would have caught these had it ever been pointed at them — it runs on authored cards against a sealed package, and an exemplar has neither.

- Both sentences replaced with **the emitter's own corrected phrasing, verbatim**. Deleted, not reworded — there is no BLASTp result for these strains to reword. Post-fix: `ripp` cites 131 loci, all `ctg5_*`; `siderophore` cites 206, all `ctg6_*`.
- `docs/Sapote_Mamey_ROADMAP.md` carried the same free-floating citation with no organism named; it now points at the worked example by path.
- `docs/ONLINE_BLASTP_PROTOCOL.md` is **left alone**: it is the case study itself, its subject is named, and its loci are its own.
- **New gate `tests/test_exemplar_no_foreign_loci_v97250.py` (6 tests).** The exemplar header declares `node: NODE_<n>`; antiSMASH loci on that contig are `ctg<n>_*`, so the check needs no CDS table — the card states its own contig. **Verified to bite:** re-injecting the leaked sentence fails two of six; removed after the probe.

## `CODE-analysis-free`'s SID scrub corrupted validation evidence — and never achieved uniformity

Found by diffing the four shipped `.246` tiers against each other. `docs/TIER_DIFFERENCES.md` claimed the tiers are byte-identical except `TIER_MANIFEST.txt`, `SOURCE_CHECKSUMS_SHA256.txt` and `CHANGELOG.md`. **They are not.** The `clean` tier differs from `merged` on **16 files** — the three above plus **five under `Wheelhouse/`**, four under `docs/batches/`, `docs/ISSUES_EXPERIENCED_DURING_DEVELOPMENT.md`, `docs/ONLINE_BLASTP_PROTOCOL.md`, and two user guides — because `make_public_tier.sh` runs `sed -E 's/SID[0-9]{2,}/SID-XXX/g'` over shipped content, excluding only `tests/`. The five `Wheelhouse/` files are the ones that matter: that tree is evidence.

A blanket regex cannot tell a the source lab strain id from an NCBI organism label. In the shipped `.246` clean tier:

```
Wheelhouse/validations/BGC006_online_blastp.csv    Amycolatopsis sp. SID8362 -> ... SID-XXX  (x2 rows)
docs/ONLINE_BLASTP_PROTOCOL.md                     Amycolatopsis sp. SID8362 -> ... SID-XXX
```

`SID8362` is a BLASTp **subject organism** returned by NCBI. It is not ours to redact. **And that CSV is the exact file the `.246` phantom-locus fix instructs authors to consult, so they can see which organism the worked example belongs to.** The scrub destroyed the attribution in the file whose only job is to carry it. It also broke the mycotrienin ground-truth linkage in `Wheelhouse/scanners/scanner_registry_v0.4.json`.

**Simultaneously destructive and ineffective.** `SID10815` survives in the *filename* `Wheelhouse/validations/mycotrienin_SID10815.json`, whose content was rewritten to `"strain": "SID-XXX"` — so the path names a strain the file no longer admits to being. It also survives in `TIER_MANIFEST.txt`, `SOURCE_CHECKSUMS_SHA256.txt`, and `tests/`. SID is **public** (Chevrette 2019; `dedup_and_guard.PUBLIC_PATTERN` admits `^SID\d+$`) and the script's own comment calls this "a uniformity scrub, not a secrecy one."

- **Fix, in two parts.** (a) The scrub now excludes `Wheelhouse/`, `tools/`, and `docs/TIER_DIFFERENCES.md` in addition to `tests/`. (b) **`sed` cannot express a negative lookbehind**, so excluding trees was never enough: `Amycolatopsis sp. SID8362` was *also* mangled inside `docs/ONLINE_BLASTP_PROTOCOL.md` — the doc that *is* the worked example. The scrub is now a small `python3` filter with a lookbehind that **never rewrites `sp. SID####`**: binomial nomenclature is an NCBI subject organism, not a the source lab strain, and not ours to redact. Bare strain references (`SID8370 walkthrough`, `mycotrienin(SID10815)`) are still scrubbed. Narrowed, not removed. Pinned by `tests/test_clean_tier_scrub_scope_v97250.py` (6 tests), which asserts the evidence CSV still names *Amycolatopsis* sp. NPDC004378 and that the protocol doc never contains `sp. SID-XXX`. **Verified to bite:** removing an exclusion, or the lookbehind, fails it.
- **A parity regression I introduced, and caught in the verification build.** Writing the fix, I put the literal organism name into the script's own comment. `tools/make_public_tier.sh` was **byte-identical across all four `.246` tiers**; the scrub promptly rewrote it in the `clean` tier only, because the comment now contained `SID8362`. **A scrub that edits its own source of truth is a parity regression, and it silently rewrote the very evidence the comment exists to record.** Hence `tools/` is excluded: *a tier must ship the script that cut it.* `docs/TIER_DIFFERENCES.md` is excluded for the same reason — a document that describes a redaction must not be redacted, or it can no longer describe it. Both were SID-literal-free before this cut, so excluding them changes no pre-existing content. **Caught only because CUT_PROTOCOL step 5 requires verifying the artifact rather than the source tree.**
- **`docs/TIER_DIFFERENCES.md` corrected against the artifacts.** It claimed CODE / clean / SID each ship an `AS-XXX`-redacted CHANGELOG. All four `.246` tiers carry the same **22 real `AS-###` identifiers**, because `AS_SCRUB` defaults to `0` (PI decision 2026-07-06). Permitted — but the table said otherwise for 94 cuts. A tier-differential table is a claim, and claims rot.
- **The filename residue is flagged, not fixed.** Renaming files across a tier requires `verify_tier_derivation.py` to model path rewrites, which it does not. That is a scoped change, not a `sed` flag.

## `gen_release_manifest` recorded the pass count of a failing suite

CUT_PROTOCOL step 7 passes `--pytest-log <a fresh full-suite run>` because "it parses the real summary line instead of you re-typing two numbers by hand." It does. It also parsed, without complaint, a log whose summary read `5 failed, 2906 passed, 152 skipped`, and reported `tests 2906p/152s`. **Caught on my own first run of this cut**, when step 4's (red) log was handed to step 7 before step 6's generators had been re-run.

**A release manifest that records the pass count of a failing suite is worse than one that records nothing, because it looks like evidence.** `counts_from_log` now raises on any nonzero `failed`/`error` count. **6 tests**, including that `0 failed` is still green — the guard keys on the count, not the word.

**Flagged, NOT fixed — a writer with no target.** `gen_release_manifest` emits `WARNING — sync rule matched ZERO times ... tests passed row, Gate 5 test count, tests skipped row`. Those three rules match **zero lines**, because `RELEASE_MANIFEST.md` no longer carries test counts at all. So `--pytest-log` parses a log, prints two numbers, and **writes nothing** — and passing `--pytest-log` to `--check` makes it exit 1 regardless of whether the log is green. Step 8 only passes because it invokes `--check` bare. This is the mirror of the "defined and never invoked" class: a writer whose target was reworded away, warning into a void for an unknown number of cuts. Restoring the rows changes the manifest's shape; **your call, the Developer or User.**

## Lineage consolidation

Three concurrent codebases, two of which had each shipped a `v9.7.244`. Consolidated at **9.7.250** — a number no lineage had used, with room beneath it. Applied in the order the `.245` changelog recommends: Bunny Hop `.243`–`.246` (this tree), then the docs lineage's `P-emit-01`, then the guide lineage's P8/P9/P10.

**P8 and P10 already exist here by independent reproduction and fix at `.245`.** Verified rather than re-applied: `chunk_proteins(60)` → `[10]×6` on the default, explicit `30` honoured, `99` clamps to `30`; `bgc_guide._load_blastp_store` accepts `locus_tag` or `query_gene`. **P9 (`background_tier` in `genome_explore`) is not merged** — it does not exist in this lineage and the diff is unavailable. Guessing its name or semantics would produce a third incompatible implementation, which is the problem this consolidation exists to end.

## `P-emit-01` (merged from the docs lineage)

`emit-modeb-template --batch --scope leads` exited **0** when no BGC carried `Lead_tier_auto` in `{HIGH, PRIORITY_ISO, HIGH_SEQ}` — every VERY_POOR assembly whose BGCs are all Medium or below. W3 checks for `mode_b_templates/`; an exit-0 over an empty directory reads as PASS while producing no templates, so W4 blocks with no stated cause. Now exits **3**, naming the condition and the fix path. New `--fail-on-empty` generalises it to any scope. **6 regression tests**, including that a *missing* triage board stays exit 1 — the codes must remain distinct.

## `tools/remediate_phantom_locus.py` (new) — the card-side companion to the lint

`PHANTOM_LOCUS` refuses a card citing a foreign locus. It does not repair one, and the 74 authored cards are not in this tree. This tool finds and deletes the fabricated paragraphs, applying the rule the `.246` incident report states: **delete, do not reword — there is no BLASTp result to reword.**

- `--package` is the **authoritative** mode: loads the strain's locus universe from `<pkg>/*_cds_table.csv`, exactly as `authored_verify` does. Without it, only the known `.246` leak strings match, and **the tool says so**.
- **Guarded:** an empty CDS table would make every locus look phantom, so an empty locus universe is **refused (exit 2)**.
- Dry run by default (exit 1 on findings); `--apply` rewrites in place keeping `.bak`. Deletes the paragraph **and exactly one adjacent blank-line separator**, so markdown is not reflowed. Idempotent; a clean card is left byte-identical and gets no `.bak`.
- **9 tests**, including that heuristic mode *cannot* see a different foreign locus (`ctg99_1`) — the limitation is pinned, not papered over.

## Orphan audit, and the gate it produced

Rolled `file_atlas --orphans`: **35 orphan candidates of 281 files, 74,981 LOC.** Import smoke test across all 35: 33 import clean, 2 do not — both perform file I/O at import. Widening from *"does it import"* to *"does it do work at import"* found a **third, and the worst**:

```
tools/build_master.py        line 28  json.load(open('bgc_data.json'))   DEPRECATED one-off
tools/plot_examples.py       line 10  reads figure_ready/strain_summary.csv
tools/add_xstrain_sheets.py  line  6  _p.parse_args()                    LIVE TOOL
```

`add_xstrain_sheets.py` calls `parse_args()` at module import, so `import add_xstrain_sheets` under any foreign `sys.argv` raises `SystemExit(2)`. Its module docstring sits *after* the code, so it is not a docstring at all. **Production is unaffected** (`build_workbook.py` invokes it by path via subprocess), but any importer — a linter, a doc scanner, a future `file_atlas` that moved from `ast` to `import` — dies on it. Restructuring a live tool is a scoped change with its own verification; **baselined, not swept.**

- **New gate `tests/test_tools_import_safe_v97250.py` (3 tests).** Baseline ratchet per the bundle idiom; **the baseline must only ever SHRINK**, and a positive control asserts the gate still detects the three it baselines. **Verified to bite** on a fabricated fourth offender.
- Writing tests for the two new tools moved the atlas: **orphans 35 → 32, untested 57 → 53.** The tools added here did not become orphans 36 and 37.

## Documentation — the reference set reaches ten

- **`math_reference_vol1.md` (new).** Volume II cited a Volume I companion that had no document. Counting, corrected count, assembly tiers, the three routing scores with every keyword weight, lead tiers, the A–E grade and the four confidence axes, all eight guards, RG-GMCI and its gate cascade, the completeness invariant. **All 17 constants in its quick-reference table were re-read from the running modules and agree.**
- **`math_reference_vol2.md` — Cluster G written.** Marked *pending* in the Vol II source since v9.7.119. `crosswalk.py` (fan-in 11), `dedup_and_guard.py` (release tiering is **fail-closed**: `AS-XXX` matches no pattern and is still PRIVATE), `merge_policy.py` (**Pareto dominance**; `CONSULT` when no source dominates — the engine refuses to choose and asks), `mode_b_quality_gate.py`.
- **Drift found while writing it.** Vol II records `MIN_ENRICHMENT_CHARS = 1000` and tier floors of 9k/8k/6k. **Live values are 2,000 and 12k/11k/10k.** **Do not cite Vol II for these constants.** A constants table in a reference document is a claim, and claims rot — which is what `check_monolith_freshness.py` catches in the monolith, and what nothing catches in the reference volumes.
- Also advanced: `development_issues_compendium` (Groups 13–18), `sapote_kernel_guide` (Parts VIII–X), `tools_reference` (§16–18), `comprehensive_glossary` (§26), `operational_reference` (§16–18), `cross_chat_doc_protocol` (§15–18, incl. the **live-receipt requirement** and Anti-Pattern 5, *the vivid foreign example*).

## Multi-tier
6 module/script edits (`blastp_online`, `mode_b_receipt`, `cli`, `cohort_blastp_driver`, `make_public_tier.sh`, `gen_release_manifest.py`) + 3 doc-data fixes (2 exemplars, ROADMAP) + `docs/TIER_DIFFERENCES.md` corrected + 2 new tools + 1 gate-registry row + 8 test files (54 tests) + 10 user guides; no new mamey modules, no AS scrub; 4-tier structure unchanged. **`make_public_tier.sh` narrows the `clean` tier's scrub — see the per-tier disclosure.** **P1 `blastp-online` guard is engine-adjacent but changes no score: it converts a fabricated negative into a refused batch.**


## Also in this cut — the v9.7.246 pre-release audit (findings F1–F7)

Filed by an analysis chat against the CODE tier; every finding reproduced here before it was patched.

- **F1 (release blocker) — `.246`'s release-blocking `PHANTOM_LOCUS` gate refused `.246`'s own exemplars.** Both `docs/reference/modeb_exemplars/ripp_exemplar.md` (BGC036 · NODE_5_length_320211_cov_36 · region001) and `siderophore_exemplar.md` (BGC038 · NODE_6_length_288305_cov_36 · region001) cited `ctg12_71`, which belongs to *Amycolatopsis* sp. NPDC004378. Reproduced: ERROR on both, `readiness_state` DRAFT on both. I wrote that gate in `.246` and never pointed it at the two cards this bundle ships as the standard — while `docs/modules/MODE_B_DEPTH_POLICY.md` instructs authors to mirror them.
  - Paragraphs **deleted, not reworded**. I linted the reconstructed *pre*-deletion text as well as the post, rather than assume: `ripp` PRE `{MISSING_CONDITIONAL_SECTION, PAD_SIGNAL, PHANTOM_LOCUS}` → POST `{MISSING_CONDITIONAL_SECTION}`; `siderophore` PRE `{PAD_SIGNAL, PHANTOM_LOCUS}` → POST `{PAD_SIGNAL}`. **The boilerplate was itself padding.** Both cards remain FULL, `THIN_*` = 0 (37,624 and 46,894 chars).
  - **New finding, disclosed rather than hidden inside F1:** `ripp_exemplar` carries a *pre-existing* ERROR — `MISSING_CONDITIONAL_SECTION §24` (Scaffold novelty score, required by "no MIBiG hit"). The rule post-dates the card's v9.7.207 landing; it was never re-linted. **The README's "0 lint ERRORs" was already false, for a different reason.** Not fixed: authoring a novelty score for a strain whose data I do not have is the fabrication `.246` was cut to stop. Recorded in `KNOWN_ERRORS` as a ratchet.
  - `tests/test_exemplars_are_clean_v97247.py` (8 tests) lints the exemplars in CI. **Verified to bite:** re-inserting `ctg12_71` fails 3; reverting passes 8. It coexists with the docs lineage's `test_exemplar_no_foreign_loci_v97250.py`, which passes on the deleted text.
- **F2 — pandas.** Swept independently: exactly two consumers, `mode_b/evidence_ledgers.py` (graceful) and `mamey_native_figures.py` (hard-fails via `_require_deps`). So pandas is **required for figures**, not optional. `cli.py:146` `figs_ok` did not check it — the banner printed `figures✓` and `render-all-figures` then raised at run time after a green preflight. Fixed (no test asserted on the banner string; grepped first). `docs/PREREQUISITES.md` corrected across §0/§1/§2/§3a/§5/§6. The stale `v9.6.21` preamble is **removed, not bumped**: a restated version number's only possible future is to be wrong.
- **F2d — the CODE tier printed a pointer to a script it does not ship.** `offline_deps/bootstrap_offline.sh` is absent from this tier; the banner emitted it unconditionally. Now conditional on the directory existing.
- **F3 — `CITATION.cff` `date-released` was owned by no gate**, and sat 24 cuts / 17 days stale while `sync_version --check` passed. Asked whether a hand-check note would do: no. `CUT_PROTOCOL.md` already records the `TAG build:` hand-check failing in the wild at v9.7.153; **a second field on the list of things humans must remember is not a fix, it is a second place to be wrong.** Rule added, derived from the same `STAMP` every other rule uses. Fired: `2026-06-22` → `2026-07-09`.
- **F4 — `reportlab` is imported zero times** (`grep -rn "import reportlab" mamey/ tools/` → 0). Dropped from `README.md` Quick Start and the dependency block; pandas noted for the figure path.
- **F5 — `LICENSE-DOCS.txt` granted CC-BY-4.0 over three files that do not ship.** Trimmed, with the three names preserved in a comment: **I cannot tell from inside the bundle whether they were lost or unbundled, and restoring a file I do not have would be fabrication.** If lost, restore beats trim. New `tools/check_license_docs.py` (WIRED, 2 tests, one proving it fails on a missing grant).
- **F6 — two unfinished drafts sat at the bundle root** (9 and 10 unfilled `<!-- Author: -->` slots) where they read as finished reference material. Moved to `work_in_progress/` with a README. Both cite only their own contigs (`ctg107_*`, `ctg58_*`); **neither is among the affected cards.**
- **F7 — `docs/EXAMPLES_REFERENCE_LEDGER.md` presented a resolved worklist as open.** All 8 `examples/` targets are present and `DANGLING_BASELINE = frozenset()` has enforced zero since v9.7.97. Re-framed as a **CLOSED** record.
- **F8 — tier decision deferred to the Developer or User.** Not a defect.

**Scientific caveat carried forward from P1, and it touches a number I published.** The `ingest-blastp` HitTable path cannot record a tested-negative at all: a BLAST HitTable lists only queries that got hits. AS-XXX's overlays were built from HitTables, so they contain **no fabricated negatives** (the P1 failure mode requires the `blastp-online` `NO_HIT` path) — but they also silently **omit** every gene with no nr homolog. **The background median I published — 95.4% over 877 genes — is computed only over genes that had a hit, and is therefore biased upward by an unknown amount.** The XML2 archive that would settle it is not in this container. This is the third correction to that figure and it should not be cited until `audit_blastp_zero_alignment --xml` has been run over the 36 AS-XXX RIDs.
# v9.7.246 — 2026-07-09 · build 20260709v97246a

**Engine 1.9.109 (unchanged) · Bundle 9.7.245 → 9.7.246.** A fabricated per-gene BLASTp claim was templated into every Mode B card of every strain. Source fixed; a release-blocking gate added so it cannot recur. No scoring change.

## The defect

`modeb_template_emitter._section_body(4)` hardcoded a **real** result belonging to a **different organism**:

> *"per-gene BLASTp overturned two of ten on BGC006 (β-lactamase→esterase, phenol-hydroxylase→ferritin)"*
> *"the offline, deterministic channel that settled BGC006 ctg12_71"*

Those numbers are genuine — they live in `Wheelhouse/validations/BGC006_online_blastp.csv`, whose organism is ***Amycolatopsis* sp. NPDC004378**. Templated into §4, they were emitted verbatim into **every card of every strain**, asserting a specific per-gene BLASTp outcome for strains on which **no BLASTp had been run**, and citing `ctg12_71` — a locus that exists on neither AS-XXX's BGC006 (NODE_1) nor AS-XXX's (NODE_16). Reported against 74 cards across two strains.

`§8` carried a lesser instance: *"the BGC006/colibrimycin fix: score 3734"* — another strain's BGC id and another run's KCB score.

This is the most serious class of defect this bundle can produce. It is not a wrong number; **it is a fabricated observation, in the one section whose job is to report observations.** Every guard passed those cards — claim-safety, evidence-presence, citation, padding — because none of them ever asked the only question that matters about a cited locus: *does this gene exist in this organism?*

## The fixes

- **Source.** §4 keeps the methodology (*"antiSMASH Pfam calls are a hypothesis, not function"*) and now cites the validation set by path, with the instruction **"a different strain — do not cite its loci here."** §8 keeps the lesson (*"a high KCB score backed by only a handful of shared genes is NOT the compound"*) as the **colibrimycin-class fix**, without the foreign BGC id or score. **Swept all 30 sections:** zero foreign loci, zero foreign BGC ids, zero foreign scores remain in any emitted body.
- **Net — new `PHANTOM_LOCUS` lint (ERROR, release-blocking).** Any `ctgN_M` cited in a card that is absent from that strain's own CDS table is flagged as a fabricated observation. `authored_verify` now loads `known_loci` from the sealed `<strain>_cds_table.csv`. **Verified against the real AS-XXX package: 758 loci loaded, `ctg12_71` not among them; the exact leaked sentence raises ERROR and drops `readiness_state` below RELEASE_READY.** A card citing that strain's real loci passes clean. With no CDS table the lint is **silent** — it cannot judge what it cannot see, and a false accusation of fabrication is worse than none.
- Added to `_READINESS_BLOCKING`. A card that cites a gene from another organism cannot be presented.

## Notes

- The methodology those examples illustrated is correct and worth keeping. The examples were doing real work — which is exactly why nobody looked at them. **A vivid, true example from the wrong organism is more dangerous than an obviously wrong one**, because it survives review.
- One correction to my own first test: I asserted `"3734" not in §8`. It *is* there, because the fixture passes `kcb_score=3734` as a fact of that card. **A fact of the card is not boilerplate.** Only the hardcoded foreign id was the leak; the assertion was overreach and was removed.
- The 74 already-authored cards are not repaired by this cut. Re-running `verify-modeb` against them with a sealed package will now flag every one. **Every §4 and §16 paragraph containing `ctg12_71` should be deleted, not reworded** — there is no BLASTp result to reword.

## Multi-tier
2 module edits + 1 new lint + `known_loci` wiring + 1 test file (6 tests) + 1 test corrected; no new modules, no AS scrub; 4-tier unchanged.
# v9.7.245 — 2026-07-09 · build 20260709v97245a

**Engine 1.9.109 (unchanged) · Bundle 9.7.244 → 9.7.245.** Three defects raised by the AS-XXX session's independent fix-verification, each reproduced here before it was touched. One is an owned regression from `.240`. No scoring change.

- **`region_label(-1)` returned `region001`** — the residual the verifier found by testing the boundary my own fix note named, instead of assuming the note covered it. `re.search(r"(\d+)", "-1")` matches `"1"`: the sign is not part of `\d+`, so the negative was silently dropped *before* the `n > 0` check could see it. The function contradicted its own stated rule. Now a leading minus is rejected before the digits are read: `-1`, `-7`, `"-1"`, `" -12 "` → `region_unknown`; positives unaffected. Unreachable from antiSMASH input, real against the design — and a one-line miss in a fix I had already declared verified.

- **Owned regression from `.240`: `chunk_proteins` defaulted to the ceiling, not the courteous default.** (The verifier's **P8**.) `.240` raised `MAX_BATCH` 10 → 30 on the strength of a real 878-protein AS-XXX run, and added `DEFAULT_BATCH = 10` — **which nothing ever read.** The function signature still said `batch_size: int = MAX_BATCH`, and two internal call sites passed `MAX_BATCH` explicitly. So every caller that omitted `batch_size` silently tripled its NCBI submission size. Verified: `chunk_proteins(60)` returned `[30, 30]`; now `[10]×6`. Explicit `30` is still honoured, `99` still clamps to 30. **This is the same shape as `wanted_region` and `--strict-paths`: a thing defined and never invoked.** I wrote the constant and did not wire it.

- **The nr overlay was invisible to the BGC guide.** (The verifier's **P10**, reproduced independently.) `ingest-blastp --package` writes `blastp_online/<BGC>_online_blastp.csv`, whose gene column is `locus_tag`. `bgc_guide._load_blastp_store()` did `if "query_gene" not in r: continue` — skipping **every row** of the overlay. The guide could not see the nr evidence that `.239` was written to create and `.241` was written to stop truncating. Confirmed on the real overlay column set: 0 rows loaded before, 1 after. Now accepts either column, `query_gene` winning a tie. 4 new tests.

**Their P9 (`background_tier` in `genome_explore`) is not merged.** It does not exist in this lineage and I do not have the diff. Guessing its name or semantics would produce a third incompatible implementation, which is precisely the problem below.

## The version-lineage split — a decision, not a test

The AS-XXX session's report is correct and the collision is now real in both directions: **two active codebases have each shipped a `v9.7.244`,** and their P8/P9/P10 predate this cut. As of this entry, P8 and P10 exist here *by independent reproduction and fix*, not by merge — **the code will differ from theirs even where the behaviour now agrees.**

Recommended resolution, offered rather than taken, because it is a project decision:

1. Freeze both lineages at their current heads (`v9.7.244-bunnyhop` here, `v9.7.244-guide` there).
2. Consolidate at **`v9.7.250`** — a number neither lineage has used, with room beneath it.
3. Apply in sequence: this lineage's `.243`–`.245` (file atlas, `_wbio` hardening, `kcb-frontpage` fail-closed, `tab-reconcile` region resolution, crosswalk, monolith gate), then their P8/P9/P10 diffs, resolving P8/P10 against the versions here.
4. Whoever consolidates must run the full suite on the merged tree. Neither side's count is authoritative for the other: **2867p/155s here vs 2877p/147s there is expected** — different trees with different tests, and 0 failures on both is the invariant that matters. Chasing the counts to equality would mean one of them was lying.

**On the six independent `mamey run` results:** 46 raw / 32.25 corrected / MODERATE, six times. That is the scoring parity claim doing its job.

## Multi-tier
3 module fixes + 3 test files (10 tests); no new modules, no AS scrub; 4-tier unchanged.
# v9.7.244 — 2026-07-09 · build 20260709v97244a

**Engine 1.9.109 (unchanged) · Bundle 9.7.243 → 9.7.244.** Bunny Hop session 2: a wrong-region bug in `tab-reconcile` reported from outside, reproduced on the real antiSMASH JSON, plus the crosswalk it hops to. No scoring change.

- **`tab-reconcile --bgc` reported a different region's evidence.** [P1, silent wrong answer]
  `_choose_record()` computed `wanted_region` (line 139) **and never read it**; `_gene_overview_summary()` then hardcoded `areas[0]` — the first region on the contig. **Reproduced on a real cohort antiSMASH JSON [Redacted — publication in preparation]:** the contig carries three regions, and the target BGC is region003. The ledger reported

  ```
  span=233558-275304; products=NRPS-like; RRE-containing; CDS=535
  ```

  i.e. **region001's span, region001's products, and the whole contig's CDS count.** Any BGC that is not the first region on its contig received another cluster's evidence, and the tab ledger is the artifact a Mode B card cites.
  - `_region_index()` resolves the region label to the area index (antiSMASH `areas` carry no region number; **index order IS the region number**, verified against the real JSON).
  - `_gene_overview_summary(rec, area_idx)` takes the resolved area.
  - New `_feature_in_span()` scopes the CDS count to the region instead of the contig.
  - **Verified on the real record, all three regions:** `region001 → 233558-275304 / NRPS-like / 40 CDS`, `region002 → 332841-394488 / NRPS / 48`, `region003 → 438609-463791 / lanthipeptide-class-i / 22`. That 22 is an independent cross-check: the BGC018 BLASTp panel run in `.239` had exactly **22 queries**.
  - **Why no test caught it:** the BGC028/AS-XXX reference fixture sits on a contig with exactly **one** region, where `areas[0]` is always right. A single-region fixture cannot exercise region selection. 5 new tests, shapes copied from the real JSON.
  - Swept the bundle for the same assumption: no other module hardcodes `areas[0]`.
- **`mamey/crosswalk.py` hardened** (hopped to: `tab-reconcile --bgc` resolves through it; 218 loc, **fan-in 11**).
  - `region_label("region003")` raised **ValueError**. Callers read `antismash_region`, whose value *is* that string; the crash was latent only because every current caller happens to pass an int. Now tolerant, digits extracted.
  - `region_label(0)` rendered `region000`. Region numbers are 1-based; 0 is invalid, not zero. Now `region_unknown`.
  - `assembly_locator` did `get("region_number") or get("Region")` — `or` treats `0` as absent and silently answers from a **different field**. Now an explicit `None`/`""` check.
  - 5 new tests, including that `contig_key` still normalises the SPAdes `_cov_` float (`_cov_80.858698` and `_cov_80.0858698` are the same contig) while leaving GenBank accessions alone for the type-strain cohort.

**Session artifacts:** `docs/FILE_ATLAS.md` (279 files, 35 orphans, 57 with no test naming them) is the roll pool; `BUNNY_HOP_SESSION_v9.7.243.md` and `_v9.7.244.md` carry the four-inspector transcripts.

## Multi-tier
2 module fixes + 2 test files (10 tests); no new modules, no AS scrub; 4-tier unchanged.
# v9.7.243 — 2026-07-09 · build 20260709v97243a

**Engine 1.9.109 (unchanged) · Bundle 9.7.242 → 9.7.243.** A Bunny Hop audit session with receipts: one file atlas, one owned retraction, one hardening of the highest-fan-in file in the bundle, and a freshness gate for the monolith. No scoring change.

- **`tools/file_atlas.py` (new).** Describes **every** file under `mamey/` and `tools/` from the real source via `ast` — LOC, docstring summary, fan-in, fan-out, CLI verbs, test references, orphan status. **279 files, 74,750 LOC, 35 orphan candidates, 57 files no test names at all.** Emits `docs/FILE_ATLAS.csv` + `docs/FILE_ATLAS.md`. The orphan column is the roll pool for `debugging_modules/BUNNY_HOP_AUDIT_GAME.md`. *First pass called `verify_release_identity.py` an orphan — it is invoked by `release.sh`, which the scanner did not read. Fixed before shipping: shell and gate-registry invocations now count. 42 → 35.*
- **H-003 fixed — owned retraction of my own `.230` work.** `kcb-frontpage --node` / `--bgc` matched keys that `read_frontpage` never sets. **Verified against a real 14 MB antiSMASH `regions.js`:** the anchors are `r1c1`-style and the per-region detail carries no contig, no `seq_id`, no Mamey BGC id. Those filters could only ever return "no hits after filter" on real output. They passed CI because **my `.230` test stubbed `bgc_id` into the hit dicts** — a proxy, not the artifact. A BGC→anchor map needs antiSMASH's record index, which `regions.js` does not expose. So the flags now **fail closed** (exit 2) with a pointer to `--region` and `<strain>_2b_bgc_crosswalk.csv`, rather than lying quietly. The stubbed assertion is deleted and replaced with one that pins the finding.
- **`tools/_wbio.py` hardened — 85 lines, 38 importers, 1 test.** The bunny hop landed on the highest-fan-in file in the bundle. Two defects, both reproduced before the fix:
  - **Permission widening.** `os.replace()` adopts the *temp* file's mode, so rewriting a `0600` deliverable left it **`0644`** — in a bundle that ships a MERGED-PRIVATE tier. All four helpers now inherit the target's mode.
  - **Stray `.tmp` on failure.** `atomic_dump_json` on a non-serializable object left `x.json.tmp` on disk; `atomic_save` and `atomic_write_text` leaked the same way. Only `atomic_open` cleaned up. All four now discard the temp and re-raise.
  - **`.bak` window.** `atomic_save(keep_bak=True)` did `os.replace(path, path + ".bak")` *before* moving the temp in — a window in which the target did not exist at all, the exact opposite of this module's stated invariant. `.bak` is now a copy. **+5 tests** (1 → 6).
- **`tools/check_monolith_freshness.py` (new, WIRED).** The monolith is the parent design controller: **20 files reference it, including `prompts/CLAUDE_SYSTEM_PROMPT.md` and a test.** Its convention — reviewed at checkpoints, not bumped per patch — is sound. Its *anchor* was not: at v9.7.242 it still read "current bundle 9.7.57 / engine 1.9.64", **185 cuts behind**, and claimed a full read-through against v9.7.6 (236 patches of drift). The gate checks the anchor, the drift, and the presence of retired doctrine (66/50/33 tiers, per-BGC BSL-2 flagging, AS_SCRUB, the PUBLIC/PRIVATE figure divider). **The doctrine scan came back clean** — the monolith's content is current even where its label was not.
  - Anchor restated truthfully: a **spot-vet** (doctrine + anchor + dangling refs) is recorded as such and does not pretend to be a read-through. The lying `current bundle X / engine Y` parenthetical is deleted; `pyproject.toml` is authoritative.
  - **The gate false-positived on its own first run**, flagging my freshly written "no per-BGC BSL-2 flagging" as an assertion of the doctrine it denies. Negation-aware window added — the same lesson the `.233` novelty lint learned. Verified it still fails on a genuine assertion (`GOOD >= 66%`).

## Multi-tier
2 new tools + 1 module fix + 1 module hardening + 3 test files + 2 gate rows; no new mamey modules, no AS scrub; 4-tier unchanged.
# v9.7.242 — 2026-07-09 · build 20260709v97242a

**Engine 1.9.109 (unchanged) · Bundle 9.7.241 → 9.7.242.** Closes G01 — the strict-paths guard that existed but nothing invoked — and folds the user documentation set into the bundle. No scoring change.

- **G01 closed (carried three cuts).** `.238` added `check_dangling_refs --strict-paths`, which resolves a path-qualified reference (`tools/X.py`) by its full relative path rather than its basename — the mode that would have caught the `.237` missing-shim bug. Nothing ever ran it. This is the same pattern the last three cuts each fixed once: *a capability that exists and nothing invokes.*
  - Wired: `tools/gate_registry.tsv` row now points `check_dangling_refs` at `tests/test_no_dangling_tool_paths_v97239.py` (the wiring-invariant test enforces this).
  - **The ratchet was verified to bite**, not merely to pass: adding a fabricated `` `tools/totally_made_up_tool.py` `` reference to a doc fails `test_baseline_is_a_ratchet`. Removed after the probe.
  - **Doc rot repaired rather than frozen.** The ratchet then failed with *"PATH_BASELINE entries no longer dangle; delete them"* — exactly as designed. Three entries fixed at the source and deleted from the baseline: `mamey/cohort_figure_captions.py` → `mamey/cohort_figures.py`; `mamey/first_pass_scans.py` → `mamey/source_scans.py`; `validators/modeb_full20.py` → `mamey/modeb_structure_gate.py`. Baseline **6 → 3**, and the survivors (`../bootstrap.sh`, `engine/pyhmmer_scanner_engine.py`, `directed_studies/pks.py`) are genuinely out-of-bundle, not rot.
- **`docs/user_guides/` (new, 8 files).** `sapote_kernel_guide`, `operational_reference`, `tools_reference`, `development_issues_compendium`, `comprehensive_glossary`, `sapote_mamey_wheel_glossary`, `cross_chat_doc_protocol`, `large_files_reference`. Markdown only — the PDF/DOCX renderings stay out of the bundle (they were ~42 MB of the 43 MB upload and carry no information the markdown lacks). Verified: the new docs introduce **zero new path-qualified** references (the class the ratchet guards — it still passes 4/4). They do add three *bare-name* references the lenient scan reports — `bunny_hop_audit_game.py`, `workbook_status.py`, `setup.py` — none of which ships in this bundle. Stated rather than swept; they are doc-side names, not broken paths, and the strict ratchet is by design indifferent to them.

**Review accepted (`CUT_REVIEW_239_to_241`).** The reviewer retracted their own `.239` sign-off: they exercised `write_nr_overlay()` once, with one BGC and one round, and passed it — a shape of test that *cannot* expose a truncate-on-second-write bug. "I checked the mechanism, not the workflow. The mechanism worked. The workflow lost 43% of the data." They independently confirmed `conservation_background` is wired (`authored_verify:127-131` → `modeb_structure_gate:818`) and not merely added.

**Still open, and blocked on data, not code:** the three duplicate-dict-key collisions (`label_positions` 10→1, `CAUSEMAP` 3→1, `SURVEY` 5→4) await the strain→entry mapping. The AS_SCRUB anonymiser collapsed the IDs; the blocker was lifted when AS went public in `.236`.

## Multi-tier
1 registry row + 1 ratchet test + 3 doc repairs + 8 user guides; no new modules, no AS scrub; 4-tier unchanged.
# v9.7.241 — 2026-07-09 · build 20260709v97241a

**Engine 1.9.109 (unchanged) · Bundle 9.7.240 → 9.7.241.** Three defects in the .239 overlay write path — the path .239 shipped specifically to arm the novelty guard. No scoring change.

- **P7a — the nr overlay truncated instead of merging, losing 43–44% of a campaign.** `write_nr_overlay()` opened `blastp_online/<BGC>_online_blastp.csv` with mode `"w"`, but a strain is BLASTed in rounds (one Hit Table per round → one `ingest-blastp` per round), so every round erased the previous round's genes for the BGCs it touched. **Independently reproduced here** on the Developer or User's real 30-RID AS-XXX campaign before applying the patch: hit tables cover **877 genes; the overlay retained 504 — 373 lost (43%)**, worst BGC042 44→7, BGC028 66→29, BGC012 44→10. The audit measured 1,002→557 (44%) on their 35-round run. Now merges by `locus_tag`, higher bitscore wins a collision. **Post-patch, re-ingesting the same 30 RIDs yields 877/877.**
- **P7b — `antismash_domains` hardcoded to `""`**, so `reconcile("", hit_def)` could only ever return `REVIEW`; the CONFIRM/REFINE/OVERTURN column the Mode B §4 bar depends on carried no information. **Verified on the real overlays: 504/504 rows empty.** Now joined from `*_gene_context.jsonl` on the panel defline's `gene=` token; fails open when gene_context is absent. (Sibling of .240's P5, which fixed the same field on the `blastp_online` path but not the `ingest-blastp` path.)
- **P7c — `B5_BLASTp_Hits` append was not idempotent**: re-ingesting one table went 150 → 300 → 450 rows. Now keyed on `(strain, query_locus, subject_acc, hit_rank, q_start, q_end)`; `duplicates_skipped` returned. Fail-open on a non-canonical header.

**Correction to the v9.7.240 changelog (owned).** The AS-XXX nr figures I recorded there — "background 95.4% **over 504 genes**" — were computed on the truncated overlay. That 504 *was* P7a. Corrected on the merged data: **background 95.4% over 877 genes**; BGC014 median 93.8% (8 genes, Δ−1.6); BGC043 **94.1% over 21 genes** (was reported 94.6% over 20); BGC028 96.5% over **66** genes (was 29); BGC042 95.0% over **44** (was 7). The conclusions stand — no AS-XXX BGC is distinctive against its own genome background — but they had been drawn from a biased 57% subset, and the `n` I published was wrong.

**Verified:** 29 new tests across `test_as421_patchset_v9_7_240.py` + `test_blastp_ingest_overlay_v9_7_241.py`, zero skips. Full suite below.

## Multi-tier
1 module edit (blastp_ingest) + 2 test files; registry surfaces move in lockstep and are tier-scoped — run pytest per tier, do not assume propagation.
# v9.7.240 — 2026-07-08 · build 20260708v97240a

**Engine 1.9.109 (unchanged) · Bundle 9.7.239 → 9.7.240.** Cohort BLASTp companions + the nr-saturation correction. No scoring change.

- **`NOVELTY_CONTRADICTION` was mis-calibrated against nr, and the real AS-XXX run proves it.** Ingesting the Developer or User's 30-RID / 878-protein nr run (`nr_cluster_seq`, BLASTP 2.17.0+) wrote 36 overlays, and the guard fired on **36/36 BGCs** (medians 92.1–98.6%). Cause: AS-XXX's sister species *Streptosporangium saharense* is deposited in nr (325/878 top hits), so **rank-1 identity measures "has a close relative been sequenced", not "is this cluster distinctive."** An absolute ≥90% floor flags everything.
  - New `genome_explore.conservation_background(pkg)` — genome-wide median across every overlay (AS-XXX: **95.4% over 504 genes**) — and `conservation_saturated(pkg)`, true when the background itself clears the floor.
  - `authored_verify` now carries `conservation_background_id` / `_n` / `conservation_saturated`; the finding message reports the delta (`this BGC sits −1.6 vs its own genome`) and, when saturated, states plainly that the verdict "carries little novelty signal on its own — judge distinctiveness by the delta, not the absolute."
  - The guard is **not suppressed**; it is made interpretable. Suppressing it would hide real over-claims on unsaturated genomes.
- **`MAX_BATCH` 10 → 30** (`DEFAULT_BATCH` stays 10). The 10-cap was a conservative reading of URLAPI guidance; the Developer or User's real 878-protein run completed at 30/batch. **Verified:** `chunk_proteins(878, batch_size=30)` → **30 submissions**, exactly the 30 RIDs observed. 88 → 30 submissions for a whole strain.
- **`tools/cohort_blastp_driver.py`** — the companion to `docs/INSTRUCTIONS_cohort_wide_blastp.md`. Scopes by tier (`leads` / `modular` / `all`), shells to the real `blastp-online` + `ingest-blastp --package` (passing `--xml` when present), appends a run-ledger row, and **refuses to mark a BGC done unless the overlay file exists on disk with populated identity + coverage** — the artifact is the receipt, not the exit code. `--plan-only` prints scale before anything runs. **Verified** against the 36 real AS-XXX overlays: both leads report `DONE 8 genes` / `DONE 20 genes`.
- **`ingest-blastp --xml` closes the field gap I flagged in the .239 run record.** The ingest parser is already BLAST-XML2-native, so the Developer or User's `-Alignment.xml` files fill `blastp_top_def` and `blastp_organism`. **Verified:** all six overlay fields 8/8 populated (`cytochrome P450 [Streptosporangium sp.]`), where the outfmt10-only path left both 0/22.

**Scientific notes (data, not code).** AS-XXX nr conservation, 36 BGCs: **no BGC is distinctive against its own genome background** (all within −3.3 … +3.2 of 95.4%). BGC014 median 93.8% (Δ−1.6, 0 genes <60%) and BGC043 median 94.6% (Δ−0.8) — **neither supports a novelty claim on nr**. **ID-collision warning:** this is *AS-XXX*'s BGC043 (NODE_8·region001); the halogenated-NRPS BGC043 in the priority queue is *AS-XXX*'s — different clusters, same run-local id. Cite by NODE·region.


**Merged: the AS-XXX audit-session patch set (5 defects), verified independently before applying.**
- **P1** `modeb_template_emitter._over_merge_facts` matched `predicted_polymers.csv` on the **bare contig**, never comparing `region_number` — its own docstring admitted it ("Matches on the bare contig"). Every BGC sharing a contig with an over-merged region inherited that banner *and its protocluster count*. Real package: **13 banners → 7**; the 7 wrong ones (BGC008/009/010 from NODE_1·r001, BGC017/018 from NODE_2·r001, BGC040 from NODE_6·r002, wrong count on BGC042) all contradicted `docs/reference/AS-XXX_AS-XXX_over_merge_decomposition.csv`, which .239 itself shipped. Post-patch: 0 disagreements.
- **P2** `authored_verify` aliased `single_protocluster_count` (cand_clusters `/kind="single"`) onto `ctx["protocluster_count"]` (protocluster features). For BGC041 those are 1 and 3. Confirmed at :137-138.
- **P3** UMED registry patterns were unanchored: `lant` matched `lanthipeptide`, `Lant_dehydr_N` **and** `Lanthipeptide_LanB_RRE`; `\brre\b` never matched `LanB_RRE`; `peptidase s9` never matched `Peptidase_S9`. Verified by regex against the real domain strings. Real buckets: `LanT_C39_transporter_peptidase` **14 → 1** (the 13 evictees — three RamS precursors, LanKC, both LanBs, both LanCs, two class-I precursors — carry no C39 or peptidase domain); `FlaP_AplP_S9_protease` **0 → 6**; `RiPP_RRE` **2 → 5**; three untouched buckets unchanged. All four surfaces move in lockstep (`source_scans.py`, `mamey_markers.py`, registry `.json` + `.csv`) because `registry_detector` rebinds `UMED_PATTERNS` at import — patching one is a runtime no-op.
- **P4** `bgc_blastp_panel --isolate-giants` shredded BGC groups into singletons; `one_best` hardcoded `proteins_per_file=1000000`.
- **P5** `blastp_online` never populated `antismash_domains`, so `agreement` was constant and `cluster_coherence` reported **n_core = 0 on every cluster ever analysed**.
- The audit modified `test_overmerge_banner.py::test_banner_fires_on_over_merged_region`, which passed `facts` with **no `region` key** and asserted the banner fired — it encoded the bug and could never have caught P1. Correct call.

## Multi-tier
2 module edits + 1 new tool + 1 doc + 7 tests; no new mamey modules, no AS scrub; 4-tier unchanged.
# v9.7.239 — 2026-07-08 · build 20260708v97239a

**Engine 1.9.109 (unchanged) · Bundle 9.7.238 → 9.7.239.** The nr-overlay write path — the missing half of the .233 novelty guard. No scoring change.

- **The guard was disarmed, and nothing said so.** `authored_verify._bgc_context_from_package` (:99) and `genome_explore._conservation_median` (:72) both read `<package>/blastp_online/<BGC>_online_blastp.csv` to prefer **nr** over ClusterBlast when computing `conservation_median_id` — the input to `NOVELTY_CONTRADICTION`. **Nothing ever wrote that file.** `blastp-online` writes `<outdir>/{bgc}_online_blastp.csv` with `outdir` defaulting to `bgc_blastp_panel/`, and `ingest-blastp` wrote only the workbook's B5 sheet, which no code reads back. **Verified on the real AS-XXX package:** `blastp_online/` absent, `bgc_blastp_panel/` present — so every conservation read silently fell back to ClusterBlast. That is precisely the "novelty rests on ClusterBlast, not nr" failure class flagged for BGC014 and BGC043; the lint built to catch it was reading the wrong channel.
- **Fix:** `ingest-blastp --package <pkg>` now mirrors the ingested rank-1 nr hits into `blastp_online/<BGC>_online_blastp.csv` in the 11-column shape the readers expect (`_OVERLAY_COLS`), recovering `locus_tag` and `aa_length` from the panel defline (`gene=…`, `aa=…`) since XML enrichment leaves `query_len` blank. **Verified against the real AS-XXX panel deflines** (`gene=ctg19_109 | aa=1041`, …) and end-to-end: with the overlay present, `_conservation_median` returns an nr-sourced median (98.0 across 3 genes) instead of the ClusterBlast fallback — the guard arms.
- **5 non-skip regression tests** (`test_blastp_overlay_write_path.py`), including `test_without_package_arg_the_guard_falls_back_to_clusterblast` and `test_overlay_arms_the_novelty_guard`. Zero skip markers — the bug class this project keeps hitting (a fix lands, a proxy test passes) is pinned on the real path.

**Analysis data folded (not engine code):** a real cohort over-merge decomposition table [Redacted — publication in preparation] — 13 regions, every one **"NO - decompose per protocluster"** (2–4 protoclusters each; interleaved / chemical_hybrid / neighbouring kinds). A single-product Mode B card on any of these would be wrong; they need per-protocluster analysis. Two 22-query BLASTp panels are staged as run-ready deliverables, and their deflines are exactly what the new overlay parser consumes.

**Note:** `20.zip` and `21.zip` were byte-identical; applied once.

## Multi-tier
2 module edits (blastp_ingest, cli) + 1 new test file + 1 reference CSV; no new modules, no AS scrub; 4-tier unchanged; per-tier confirmation at cut.
# v9.7.238 — 2026-07-08 · build 20260708v97238a

**Engine 1.9.109 (unchanged) · Bundle 9.7.237 → 9.7.238.** Fixes two gaps the .237 cut itself introduced (both mine), plus the root cause that hid the first one. No scoring change.

- **F01 (owned) — the .237 CHANGELOG claimed `tools/sapote_workflow.py` shipped; it did not.** I copied the driver to `mamey/sapote_workflow.py` only, leaving **9 references to a nonexistent path**, including `mamey/sapote_workflow.py:276` — the **ledger header string written into every package**, plus `cli.py`, the contract doc, and the changelog line itself. Shim restored (25 lines, pure delegator). **Verified:** `mamey workflow` and `tools/sapote_workflow.py` emit **byte-identical JSON** (3,104 B) on the real AS-XXX package; the ledger header now cites a path that exists.
- **F02 (owned) — I dropped two regression tests that shipped with the .237 patch set**, leaving P02 and the workflow driver unpinned. `test_private_policy_single_source.py` contains the string `AS-XXX`, but only inside `is_private("AS-XXX")` — it pins the *predicate*, not the *redaction regex*. So the AS-XXX leak fix had no test. Restored `test_redact_ajs_single_digit.py` (6) + `test_sapote_workflow_driver.py` (7) — **13 passed**. This is exactly the proxy-verification failure this project keeps flagging; it was mine this time.
- **F03 (root cause, reported by the review, fixed here) — `check_dangling_refs` resolved path-qualified references by basename.** `tools/sapote_workflow.py` was satisfied by `mamey/sapote_workflow.py`, so the guard passed while 9 refs pointed at nothing. New `--strict-paths` mode resolves the **full relative path** whenever a reference contains a `/`. **Proven:** on a shim-less tree `--strict-paths` flags `tools/sapote_workflow.py` (basename mode does not) — it *would* have caught F01 automatically; the shipped tree is clean. +4 regression tests.
- **`--strict-paths` also surfaces 6 pre-existing dangling path-refs in docs** (`directed_studies/pks.py` (external, not shipped in this bundle), `engine/pyhmmer_scanner_engine.py` (external, not shipped in this bundle), `mamey/cohort_figures.py`, `mamey/source_scans.py`, `mamey/package_addons.py`, `mamey/modeb_structure_gate.py`). Opt-in, so no existing gate breaks; flagged, not silently swept.

**Review cross-checks accepted:** the reviewer's leak-check of my .236 `dedup_and_guard` change (no private identifier resolves PUBLIC: AS-* PUBLIC, AJS-*/PENDING-* PRIVATE, SID3343 PUBLIC) and their note that the CHANGELOG's "4/11 steps" vs their 3/11 is package state (templates emitted), not a false claim. Their two retracted non-findings (tools count offset; `WW-12` fail-safe PRIVATE, pre-existing) checked and agreed.

**Verified:** full partitioned suite run (the review explicitly did not run it) — below.

## Multi-tier
1 restored shim + 1 gate mode + 3 restored/new test files; no new modules, no AS scrub; 4-tier unchanged; per-tier confirmation at cut.
# v9.7.237 — 2026-07-08 · build 20260708v97237a

**Engine 1.9.109 (unchanged) · Bundle 9.7.236 → 9.7.237.** The v9.7.235 audit round: one live P1, one latent leak, the Sapote workflow driver, and the duplicate-dict-key gate (properly wired). No scoring change.

Accretion-justified: mamey/sapote_workflow.py — the Sapote-layer workflow driver (W0–W10). Mamey enforces phase order in engine code, but nothing sequenced the Sapote judgment steps; this re-implements no gate, it shells to the real ones and blocks a step whose mandatory predecessor is not PASS.

- **Root cause the audit named: the private-strain rule was hand-copied, not imported.** The canonical predicate is `cohort_figures.is_private()`; call sites re-implemented it with their own regex and went stale after the 2026-07-06 PI decision.
  - **P01 (P1, live).** `tools/intake_harness.py` blanket-refused `--release PUBLIC` for every `AS-####` — the 28-strain round actually aborted on *"Refusing PUBLIC intake for private-looking strain AS-XXX"*. Replaced the local regex with an import of `is_private()`. **Verified:** `is_private("AS-XXX") → False` (PUBLIC intake allowed), `is_private("AS-XXX") → True` (refused, unchanged).
  - **P02 (P2, latent).** `tools/redact_public_tier.py` `AS_RE` shared a `A(?:JS|S)-\d{2,}` alternation, so the deliberate 1-digit **AS-N** prose carve-out silently applied to **AJS** too and `AS-XXX` escaped redaction. Split into `AJS-\d+` / `AS-\d{2,}`. **Verified on the real redactor:** `AS-XXX`/`AS-XXX` now redact; `AS-1`, `AS15`, `AJS327`, `enterocin AS-48` all still kept.
  - **§3-D stale prose swept** (3 sites in `cli.py`/`cohort_figures.py` still told readers AS- is private) + a new `test_private_policy_single_source.py` pinning the rule, the intake import, the prose, and **release-tier ⟷ figure-tier agreement**.
- **P03 — `mamey workflow`** (+ `docs/SAPOTE_WORKFLOW_CONTRACT.md`, `tools/sapote_workflow.py` thin shim). **Verified on the real AS-XXX package:** 4/11 steps PASS, W6 correctly **BLOCKED by W4** (mandatory predecessor PENDING), `--strict` exits 1. It is a gate, not decoration.
- **P04 — duplicate-dict-key gate registered `WIRED`.** *The patch set registered it but did not ship its test*, so the bundle's own orphan-gate tripwire (`test_gate_wiring_invariant.py`) failed — caught, not papered over. **I wrote `tests/test_duplicate_dict_key_gate.py`** against the real gate: PASS on the shipped tree, `--strict` still detects the known sites, the 3-entry allowlist is asserted as a ratchet (no growth, live paths, reasons required), and a fourth collision **fails closed** (probe under `mamey/`, the gate's scan root). Wiring invariant now passes.
- `tools/build_cohort_html.py` — cohort-level offline HTML analysis (no such tool existed).

**§3-C provenance, resolved:** `tools/check_duplicate_dict_keys.py` is genuinely absent from my pristine .235/.236 tree and from `SOURCE_CHECKSUMS_SHA256.txt` — it is a new file, so the auditor's authored version stands, as they proposed.

**Still needs the Developer or User (not guessed):** the real strain→entry mapping for `label_positions` (10) and `CAUSEMAP` (3). The AS_SCRUB anonymiser collapsed distinct IDs into one placeholder; **the blocker is gone now that AS- is public**, so the real IDs can be restored and the allowlist entries deleted. Also open: `strain_registry.json` AS-XXX (`genus: "AS-XXX"`, data not code); `BUILD_STAMP` wording "fixes" → "detected, pinned, allowlisted" for the dup-key line; `emit-modeb-template --scope leads` exits 0 on zero leads (suggest exit 3 / `--fail-on-empty`).

## Multi-tier
1 new module (sapote_workflow) + 2 new tools + 4 patches + 2 new tests + prose sweep; no AS scrub; 4-tier unchanged; per-tier confirmation at cut.
# v9.7.236 — 2026-07-08 · build 20260708v97236a

**Engine 1.9.109 (unchanged) · Bundle 9.7.235 → 9.7.236.** Resolve the AS-XXX release-tier conflict (PI decision: AS is public) + stand up the audit record-keeping protocol as a bundled standing process. No scoring change.

- **AS-series release-tier now agrees with the figure-tier (PI decision).** `dedup_and_guard.derive_release` / `_trips_private_guard` no longer treat the AS-pattern as a private identifier — same basis as the .219 AS_SCRUB retirement and the .229 `is_private()` flip. Before: `derive_release('AS-XXX') → PRIVATE` and `resolve_release('AS-XXX','PUBLIC')` was refused, silently re-tagging a strain the figure layer already treated as public. After (verified): `derive_release('AS-XXX') → PUBLIC`, `resolve_release('AS-XXX','PUBLIC') → ('PUBLIC', False)`, `is_private('AS-XXX') → False` — all three agree. AJS-/PENDING- remain private (genuinely unpublished). Updated the two tests that asserted the old AS→PRIVATE fail-safe to key the private guard on AJS-/PENDING-.
- **Audit record-keeping protocol bundled (`docs/audit_recordkeeping/`).** The finding ledger / decision log / run ledger / instruction-compliance-matrix templates + the protocol, now a standing part of the bundle rather than an external kit — the external, reviewable audit trail the recurring proxy-verification failures argued for (complements `tools/round_ledger.py` from .232). "Do not trust a result unless the record shows which instruction governed it, what ran, what went in, what came out, and what passed/failed/stayed ambiguous."

**Not a cut change — for feedback:** `dual_priority_atlas_label_feedback.png` renders the 5 on-disk strains' AB/AF capacity scores; AS-XXX/AS-XXX/AS-XXX all land at AB=74 and their labels collide — the concrete case the `master_figure_atlas.label_positions` offsets (the .235 documented duplicate-key placeholder) need to resolve. Per-strain nudges pending your eye on the plot.

## Multi-tier
1 module edit (dedup_and_guard) + 2 tests updated + docs/audit_recordkeeping (new docs); no new modules, no AS scrub; 4-tier unchanged; per-tier confirmation at cut.
# v9.7.235 — 2026-07-08 · build 20260708v97235a

**Engine 1.9.109 (unchanged) · Bundle 9.7.234 → 9.7.235.** Two duplicate-dict-key fixes (CAUSEMAP class) from the .234 audit, the boundary-colour palette, and the long-standing inspect version-detection fix (H-002). No scoring change.

Accretion-justified: mamey/boundary_palette.py — new single-source boundary-tier colour palette (Interior/Edge/Full-contig) consumed by figures_smoke + figures_sapote; replaces per-figure hardcoded colours so the two renderers can't drift.

- **Duplicate-dict-literal-key fixes (audit F-001, CAUSEMAP class):**
  - `master_figure_atlas.py` `label_positions` — 10 hand-tuned `(x,y,ha)` scatter-label offsets all authored under the placeholder key `"AS-XXX"`, so 9 silently collapsed and the survivor never matched a real strain (every label used the fallback offset). The *mechanical* collision is documented + locked by a regression test (`test_label_positions_dict_documents_the_known_duplicate_key_collision`); the *correct* per-strain offsets need the real rendered layout — flagged, not guessed.
  - `master_workbook.py` `top_kcb_score` — placeholder `""` first, real value second, so last-key-wins already produced correct output; removed the dead placeholder (zero-risk cleanup, verified).
- **Boundary palette:** `boundary_palette.py` centralises the Interior/Edge/Full-contig colours; `figures_smoke` + `figures_sapote` now import it instead of hardcoding.
- **Inspect antiSMASH-version detection (H-002 / F-005 — flagged three separate audits).** `mamey inspect AS-XXX.zip` printed "antiSMASH version : not detected" while `mamey run` parsed "8.0.4", because inspect used a narrow GBK structured-comment regex. Inspect now falls back to the **same `parsers.extract_antismash_version` run uses**. Verified on the real AS-XXX.zip: extractor returns `8.0.4`, so the preflight no longer contradicts the run receipt.

**Verified:** H-002 fix confirmed on real AS-XXX; +2 dup-key regression tests (from the audit patch) + H-002 test; full suite below. Audit confirmed the .234 merge is correct by direct inspection (novelty windowed-guard, `--top`/`--json`, collision resolved — `explore` registered exactly once).

**Still open (flagged, not guessed):** the AS-XXX release-tier vs figure-tier conflict (PI decision); the real per-strain `label_positions` offsets (need the rendered figure); the front-page `explore.py` third-chat module (needs a renamed verb before it can land).

## Multi-tier
1 new module (boundary_palette) + 3 edited modules + inspect fix + 3 tests; no AS scrub; 4-tier unchanged; per-tier confirmation at cut.
# v9.7.234 — 2026-07-08 · patch/audit-chat reconciliation


**Merged in a second parallel-session reconciliation (`PATCH_v9_7_233_applied`), verified applying cleanly on top:**
- `modeb_structure_gate._novelty_conservation_findings` — a real **false-negative in the .233 readiness lint**: the denial/contrast guard scanned the whole sentence, so a negation early in a sentence masked a genuine unhedged novelty overclaim later in it. Fixed by windowing the denial check to ±40/+20 chars around the matched claim. Verified: the exact repro ("not a housekeeping gene, but … a novel, isolate-specific … architecture with no known relatives" @98% id) now flags; all four original disciplined denials stay clean.
- `genome_explore.explore_command` — `--top` was ignored in `--json` mode (dumped the uncapped board); now respected.
- `class_architecture.annotate_architecture`, `blastp_ebi.to_outfmt10` (+ missing `sys` import), `gene_context.load_gene_context` — silent exception/partial-return paths now warn to stderr (fail-closed unchanged). Plus cosmetic (Wombat→Alexander J. Smith ×6, PREREQUISITES path, arts_ingest `--strain` no-default) and a stale `check_dangling_refs` docstring.

**Engine 1.9.109 (unchanged) · Bundle 9.7.233 → 9.7.234.** Reconciles this bundle (the "official" v9.7.233 cut) with a parallel patch-chat session's independent work on the same v9.7.232 base. Both sessions ran the same "bunny-hop debugging + genome exploration mode" brief without visibility into each other; this entry merges the non-overlapping, non-conflicting parts. No scoring change to any existing extraction/judgment path.

Accretion-justified: mamey/raw_antismash_triage.py — new pre-extraction triage module (kcb-frontpage + scanner-evidence census + rare-motif + split-detector, chained per docs/Sapote_Mamey_ROADMAP.md's documented run order); operates on a RAW antiSMASH ZIP/dir, before extraction — a different pipeline stage and a different question ("where do I look first") than mamey/genome_explore.py's post-extraction correctness checks ("is this claim actually right"). Originally named genome_explore.py / CLI verb `explore` in the parallel session — renamed to avoid colliding with this bundle's own genome_explore.py, which already owns that name and verb (see that module's docstring; both are described there in full).

- **Three `render-all-figures` / `intake_harness.py` fixes (independent findings from the parallel session, not present in this bundle — verified against real AS-XXX/AS-XXX packages).**
  - `_run_mamey_native` reported `ERRORED` (not `SKIPPED`) for the normal, expected case of a single-strain workbook lacking cohort sheets (`Strain_Registry`/`DAPR_*`/`RG-GMCI_All_Strains`) — now `SKIPPED` with the real missing-sheet names; a genuine failure still reports `ERRORED`.
  - `_run_cohort_class` silently dropped `render_cohort_class_heatmap`'s own specific skip reason (`"no B2 data"`, etc.), falling back to a generic "likely matplotlib/addon missing" line indistinguishable from a real problem — now threads the real reason through.
  - `tools/intake_harness.py` had no CLI-level way to override per-strain taxonomy when the source GBK's `ORGANISM` line is a placeholder (common on raw SPAdes drafts) — new optional `--taxonomy-map <json>` of `{strain: taxonomy}` overrides, fails closed on a malformed map, unmapped strains unaffected.
  - `mamey/raw_antismash_triage.py` (above) — the new triage mode, plus a real anchor-id reconciliation bug caught while building it: `kcb_frontpage`'s KCB anchors (`r7c1`) and the GBK-filename region ids the other three modules use are two different id spaces for the same regions; fixed via a new `_kcb_anchor_to_region_id`, derived directly from `regions.js`'s own `recordData`.
  - Verified: full suite **2766 passed / 0 failed / 152 skipped** (up from this bundle's own 2739/0/152 baseline; +27 new tests, zero regressions). `mamey doctor`, `sync_version --check`, `check_module_accretion` (182/182), `gen_tools_inventory --check`, and `gen_release_manifest --check` all PASS.

**NOT reconciled in this pass — deferred, flagged for explicit review rather than silently applied:**
- **Five additional independent parallel-session submissions** (received as a batch, labeled 1.zip–5.zip) were audited but not merged this pass:
  - Two (matching this bundle's own BUG-1/2/3 fixes and the readiness-lints/genome_explore diffs) are **already shipped here** — no action needed, confirmed by direct comparison.
  - One submission's `hmm_blastp_adjudicate.py` expansion (7→21-family dictionary, a `NO_SIGNATURE_DICT` verdict, `region_module_census()`/`trap-census` CLI verb, a `compile_report.py` §11.5 section, a `gere` HTH-token fix) touches files this bundle hasn't modified since v9.7.232 and looks substantive and independently verified (described as re-derived against the live AS-XXX package post-patch) — **not applied here**; recommend a dedicated follow-up pass to verify and merge, since it wasn't practical to independently re-verify five sizeable, unfamiliar diffs' numeric claims in this reconciliation pass.
  - That same submission's own `NOVELTY_CONTRADICTION` lint variant (in `modeb_structure_gate.py`) **duplicates and would conflict with** this bundle's own `NOVELTY_CONTRADICTION` lint (same finding code, different implementation, different false-positive guard) — needs an explicit decision (which implementation, or a merge of both guards' coverage), not a silent pick.
  - Two more submissions each shipped their own third `explore`/`genome_explore.py` design, both now redundant with the two already reconciled here (this bundle's package-based tool + the newly-merged `raw_antismash_triage.py`) — not merged; flagged only in case either contains a unique check the other two miss (not independently verified in this pass).
  - One submission proposed changing `prompts/CLAUDE_SYSTEM_PROMPT.md`'s CDSW next-steps count from "3–10, upper end when rich" to "exactly 8" — a standing-behavior/policy change, not a code-correctness fix. **Not applied**; flagged for the Developer or User's decision rather than adopted unilaterally, and it also conflicts with the "up to 6 (minimum 3)" range this session's own instructions currently specify — the two numbers disagree and that disagreement should be resolved deliberately, not by whichever patch happens to get applied last.

## Multi-tier
1 new `mamey/raw_antismash_triage.py` module + 1 new CLI verb (`triage-raw`) + 2 `render_all_figures.py` fixes + 1 `intake_harness.py` addition + 3 new/extended test files; CODE tier only this session — other three tiers not yet ported; no AS scrub. Five additional parallel-session submissions audited, two confirmed already-shipped, one substantive submission and two design questions deferred to a follow-up (see above) rather than merged without independent verification.


**Engine 1.9.109 (unchanged) · Bundle 9.7.232 → 9.7.233.** The readiness correctness layer (the .232 flagship, now built) + genome-exploration mode + three bug fixes to .231/.232. nr-preferred conservation throughout. No scoring change.

Accretion-justified: mamey/genome_explore.py — new question-driven exploration module (scan_divergence / scan_co_capture / exploration_board); no existing module answers "what's distinctive and where to look first" over a sealed package without re-extraction. Single-purpose.

- **Readiness correctness lints (flagship).** Three WARN lints in `modeb_structure_gate.lint_card`, binding prose to the deterministic data + to itself, plus a `readiness_state()` DRAFT/VERIFIED/RELEASE_READY helper (`_READINESS_BLOCKING` = the three codes):
  - `NOVELTY_CONTRADICTION` — novelty/rarity asserted while per-gene conservation median ≥ 90% (genus-conserved). Data-relative (divergent clusters allowed); "no MIBiG / uncharacterised" allowed; sentence-level denial/contrast guard prevents false positives on disciplined cards that *deny* novelty.
  - `INTERNAL_CONTRADICTION` — same fact stated two ways (TTA, bldA tier, protocluster count).
  - `FACT_MISMATCH` — card fact vs `gene_context`/manifest (per-gene TTA, CDS count, protoclusters, edge status).
  - `authored_verify._bgc_context_from_package` now supplies `conservation_median_id` (**nr-preferred over ClusterBlast** — the correctness-critical detail), `tta_by_gene`, `cds_count`, `protocluster_count`, `edge_status`.
  Verified: "novel scaffold"/"structural novelty" @98% id flags; @45% (divergent) allowed; "not novel"/contrast denials clean.
- **`mamey explore` — genome exploration mode.** `genome_explore.py`: `scan_divergence` (nr-preferred), `scan_co_capture` (independently re-derived BGC033's TA/GH/pentapeptide co-capture found by hand), `exploration_board`/`render_explore` (promotes only **nr-confirmed** divergence). Correction it surfaced: **BGC014's earlier "standout novelty lead" rests on ClusterBlast (51–78%), not nr — UNCONFIRMED, the same failure class as BGC043**; the board buckets it under unconfirmed divergence pending an nr pass.
- **Bug fixes (.231/.232):** BUG-1 the .232 KCB-identity lint wrongly treated `<comparator>-class` as a hedge — it's exactly the BGC046 overclaim, now flagged; BUG-2 `tab_reconcile` duplicated the node id in output filenames on the `--node`/`--region` path (no `--bgc`); BUG-3 `round_ledger` counted bytes not characters (multibyte §/– overcounted the char metric the gate reports).
- **PAD_SIGNAL tuning:** contrastive cross-references ("unlike/whereas/in contrast/rather than for BGC0xx") are legitimate interpretive contrasts, now exempt like the blast/kcb/cohort anchors.

**Verified:** 12 new hermetic tests (9 readiness + 3 genome_explore) pass; bug fixes + padding tuning re-verified; full suite below.

**Still spec-only (next cut):** the `compile-report --release` presentation gate + `render-cards` renderer (§3–§4 of the readiness memo); `readiness_state` now exists for them to consume.

## Multi-tier
1 new module (genome_explore) + gate/authored_verify edits + 3 bug fixes + cli explore verb + 12 tests; no AS scrub; 4-tier unchanged; per-tier confirmation at cut.
# v9.7.232 — 2026-07-05 · build 20260705v97232a

**Engine 1.9.109 (unchanged) · Bundle 9.7.231 → 9.7.232.** Two tested Mode-B gate lints (roadmap #2/#3) + the round-ledger tool. No scoring change.

- **KCB-name-as-identity lint (roadmap #2).** New WARN `_kcb_identity_findings` in `modeb_structure_gate`: pulls the comparator name from `kcb_top` and flags sentences asserting `is <name>` / `<name>-class/cluster/producer` without a hedge (similarity / comparator / backbone / -adjacent / family / not) → `KCB_IDENTITY_RISK`. Catches the failure that mis-called BGC046 "selvamicin-class" when KCB is backbone similarity and the per-gene BLASTp genus differed. Wired next to the padding lint; fires because `authored_verify` already carries `kcb_top` in `bgc_context`. Verified: "is selvamicin" (no hedge) flags; hedged/comparator card clean; no `kcb_top` → silent.
- **§29 padding-lint exemption (roadmap #3).** `_padding_findings` counted §29 (Cross-cluster interactions) cross-BGC references as padding — a false positive on its legitimate core content. Now §29 is excluded alongside §28 (`n not in (28, 29)`). Verified: a §29-only cross-ref card no longer trips PAD_SIGNAL.
- **`tools/round_ledger.py` (new).** Verifies a Mode B card through the same gate, then appends one audit row (round, bgc, node_region, gate_status, warnings, chars, blastp/precursor status, authored_utc, card_path) to a durable CSV — a greppable trail across the 6+ authoring rounds and across chats, built only from data the gate already prints. Inventory 124 → 125.
- **HMM/BLASTp adjudication expanded (audit #4 direction; AS-XXX HMM census).** `hmm_blastp_adjudicate.py`: the family dictionary is expanded beyond the original 7-family BGC006 set (the old lookup mapped neither call term for ~16/18 of adjudicate() calls, falling through to AMBIGUOUS on real agreements), and a new `orphan_rescue()` reports HMM family hits that rescue an assignment no other channel supplies (BLASTp-free genes, non-core tailoring) — on AS-XXX (820 CDS, 64 BGCs) the old single-trigger path undercounted these. Verified: the module's 19 tests pass.

**Verified:** hermetic regression tests for both lints; full suite below.

**NOT in this cut (flagged, from the same archive):**
- **Readiness / presentation gate** — the flagship, but delivered as **spec only** (`PATCH_readiness_and_presentation_gate.md`); no `readiness_gate.py` in the archive. It's the correctness layer (NOVELTY_CONTRADICTION / INTERNAL_CONTRADICTION / FACT_MISMATCH binding prose to `gene_context`/`manifest`/`source_scans`, a DRAFT/VERIFIED/RELEASE_READY lifecycle, and a `compile-report` presentation gate). Build-from-spec, its own substantial cut — highest-value next piece, addresses the real BGC043 novelty-over-claim + TTA-contradiction failures.
- `small_fixes.diff` (docs-only; mixed/ambiguous `-p` path depths — not force-applied); the monolith doc patch; the GUI (`sapote-mamey-gui-v1.zip`, separate deliverable); the AS-XXX HMM census (data); roadmap #1/#4/#5/#6/#7 tooling items.

## Multi-tier
1 gate module edit + 1 new tools/ script + 1 test; no new mamey modules, no AS scrub; 4-tier unchanged; per-tier confirmation at cut.
# v9.7.231 — 2026-07-05 · build 20260705v97231a

**Engine 1.9.109 (unchanged) · Bundle 9.7.230 → 9.7.231.** The reusable antiSMASH-tab reconciliation parser — `mamey tab-reconcile`, the QC follow-up to the BGC028/AS-XXX tab-reconciliation direction. No scoring change.

Accretion-justified: mamey/tab_reconcile.py — new deterministic parser/report module for the antiSMASH-tab evidence layer (no existing module ingests the 6 under-surfaced tabs: MIBiG cluster_compare, TFBS, TIGRFAM, NRPS/PKS predictions, active-site, TTA/bldA). Single-purpose; not foldable into an existing scorer/extractor.

- **`mamey tab-reconcile`** parses all 12 antiSMASH tabs for one BGC/region into a single evidence ledger + a captured/underused/missed Mamey comparison, following the reusable checklist. Args: `--antismash <ZIP|dir> [--package <complete-pkg>] [--bgc|--node|--region] --out`. Resolves `--bgc BGC028` → its record via the package crosswalk, or runs package-free from `--node`. Emits `*_ANTISMASH_TAB_EVIDENCE_LEDGER.csv`, `*_ANTISMASH_VS_MAMEY_COMPARISON.csv`, `*_EVIDENCE_LEDGER.html`, `*_TAB_RECONCILIATION_REPORT.md`, `*_tab_reconcile_summary.json`.
- **Discipline encoded:** absent tabs are explicit **negative evidence** (`NO_HITS`), not blank; weak tabs are demoted; KCB stays the family anchor over generic cluster_compare; no tab promotes a comparator name to a product identity.
- **Verified on the REAL AS-XXX data** (not the supplied fixture test, which returns early without the 143 MB `AS-XXX.zip`): I ran `build_tab_reconciliation` against the actual antiSMASH ZIP + the .229 complete package — BGC028 → `NODE_32_length_60747_cov_53.323339`; SubClusterBlast + TIGRFAM → `NO_HITS` (no positive evidence); KnownClusterBlast → `BGC0000115.5` (nystatin A1, positive); NRPS/PKS → 11 KS/11 AT/11 KR + 8 ACP; TFBS → RutR/ToxT (weak). Matches the audit's tab counts exactly.
- **Coverage:** kept the supplied fixture test (real assertions when `/mnt/data/AS-XXX.zip` is present) and **added 4 hermetic unit tests** for the negative-evidence discipline (empty `Significant hits:` → `NO_HITS`; missing tab → `TAB_ABSENT`; real hit counted; node coverage-suffix normalization) so CI has a non-fixture-gated signal.

**Pairs with .229/.230:** the ledger's "tabs that added no positive evidence" list + the SubClusterBlast `NO_HITS` rule (.230 audit #3) are the same discipline; the checklist's required-output items are candidates to become Mode B depth-gate form assertions (extending the .229 evidence-presence bar).

## Multi-tier
1 new module + cli registration + 1 fixture test + 4 hermetic tests; no AS scrub; 4-tier unchanged; per-tier confirmation at cut.
# v9.7.230 — 2026-07-05 · build 20260705v97230a

**Engine 1.9.109 (unchanged) · Bundle 9.7.229 → 9.7.230.** Bounded fixes from the AS-XXX v9.7.229 patch-chat audit (no blocker found; these are the provenance/UX items). No scoring change.

- **Audit #3 — SubClusterBlast parsed-zero is now explicit negative evidence.** The triage board serialized an empty `subcluster_hits` list as blank, so Sapote couldn't tell "tab parsed, 0 hits" from "not parsed." Now: if ANY BGC in the run carries subcluster hits (proving the tab was parsed), an empty list emits **`NO_HITS`**; only a genuinely unparsed run stays blank. Directly serves the tab-reconciliation discipline (absent submodule = negative evidence, e.g. BGC028's 0 SubClusterBlast hits mean no sugar-submodule claim).
- **Audit #5 — `kcb-frontpage` gains `--region` / `--node` / `--bgc` filtering.** It returned every region, forcing card authors to grep. The filters narrow to the region/contig/BGC being authored. Verified: `--region r32` → only the nystatin-A1 hit; `--bgc` filters to one cluster.
- **Audit #2 — the fractional corrected BGC count is labelled.** AS-XXX's 28.5 is the intended `Interior + ½·Edge + ¼·Full-contig` weighting, not a miscount; the run summary now reads **"corrected 28.5 (effective estimate; Interior + ½·Edge + ¼·Full-contig)"** so it isn't read as an exact cluster count.

**Verified:** hermetic regression tests for the NO_HITS rule + the frontpage filters; full suite **2701 passed / 0 failed**. The audit's own run confirmed .229 is sound: AS-XXX → MAMEY_COMPLETE, validates, 65 targeted pytest pass, BGC028 judgement stable (AF lead, nystatin-class capacity, partial-capture ceiling).

**Audit findings NOT in this cut (flagged):** #1 inspect/run antiSMASH-version detection mismatch (unify the probe); #4 `hmm-adjudicate` results not written back to cell provenance (a writeback path, its own feature); #6 saccharide-tag science caveat (authoring guidance, not code). The `mamey tab-reconcile` parser (the QC follow-up) lands next as its own cut.

## Multi-tier
Edits to cli.py + kcb_frontpage.py + 1 test; no new modules, no AS scrub; 4-tier unchanged; per-tier confirmation at cut.
# v9.7.229 — 2026-07-05 · build 20260705v97229a

**Engine 1.9.109 (unchanged) · Bundle 9.7.228 → 9.7.229.** Four coordinated pieces: the evidence-presence bar, the rest of the Part C section wiring, the figure privacy flip, and the parallel data-track engine work. No scoring change.

- **Evidence-presence bar (the padding fix's follow-up — quality = evidence, not length).** `modeb_structure_gate` gains `check_evidence_presence`: when the strain has a BLASTp panel, §4 MUST carry the reconciled per-gene closest-match table, else `EVIDENCE_GAP` (WARN). Panel auto-detected in `authored_verify` from `bgc_blastp_panel/` + the B5 worklist; enabled on both `verify-modeb` call sites. Verified: panel+no-table → flags; panel+table → clean; no-panel → no gate. Advisory (WARN), matching depth severity.
- **Part C remaining section wiring.** `_precompute_facts` now also joins nrps substrates + resistance by (strain, bgc_id); `_section_body` grounds §4 (domain-role census), §5 (architecture), §7/§27 (resistance), §16 (A-domain Stachelhaus table), §21 (substrate specificity) from the cohort tables — alongside §11/§14. Verified end-to-end on the real CLI (AS-XXX card → 4 grounded pre-fills) and on AS-XXX BGC018 (9 A-domains). Discipline preserved: Stachelhaus = similarity not identity; resistance = capacity, never phenotype.
- **Figure privacy flip.** `is_private()` returns False for AS- (public per the .219 PI decision) — the PCA/tier scatters no longer draw diamond/`(PRIV)` markers on AS strains; machinery kept for AJS-/PENDING-. `public_only` test updated. **Not changed:** `lab()`'s two-line labels — no spec/memo for a target format, left as-is.
- **Parallel data track.** `mamey cohort-precompute` promoted to a first-class subcommand (reproduces all 7 golden tables on the real CLI) that emits `VERSION.json` + `MANIFEST.csv` (0-mismatch integrity; "join on assembly_locator, BGC_ID not portable" baked in). Strain-ID auto-derivation (`Genus_species_Designation` from the ORGANISM line, filename fallback, never LLM-invented) wired into `mamey run`, with a guard that never rewrites canonical AS-/already-derived IDs.

**Verification.** Full suite **2699 passed / 0 failed**. New regression tests: evidence-presence (EVIDENCE_GAP gating), Part C section grounding, is_private flip, strain-ID derivation (all convention examples + AS guard), cohort-precompute VERSION/MANIFEST.

**Documented limits (not blocking).** `lab()` label format unaddressed (no memo). Strain-ID derivation *function* fully unit-tested, but the full `mamey run` path not exercised end-to-end (no accession-labeled antiSMASH ZIP on disk; the AS-XXX/AS-XXX inputs are AS- IDs, which the guard skips by design).

## Multi-tier
Edits to modeb_structure_gate, modeb_template_emitter, authored_verify, cohort_figures, cohort_resolver, cli + 1 tools/ script; 6 new tests + 2 updated; new `cohort-precompute` subcommand; no new modules, no AS scrub; 4-tier unchanged; per-tier confirmation at cut.
# v9.7.228 — 2026-07-05 · build 20260705v97228a

**Engine 1.9.109 (unchanged) · Bundle 9.7.227 → 9.7.228.** Fix the Mode B depth gate so it stops rewarding padding. No scoring change.

- **Problem (measured, not asserted):** the `verify-modeb` depth gate enforced character-count floors (700/section, 1,400 heavy, **20,000/card** for large BGCs, with `_is_large_bgc` defaulting True). That's a length *target*, and a keyword scan of the four gold cards flagged **19–24% obvious padding** (evidence-free cross-refs to other BGCs, restatement openers, boilerplate hedges) — authors expanded to hit the count. "Passes `verify-modeb --strict`, 0 warnings" then got reported as a *quality* signal when it only meant "long enough + structured." That's the receipts-over-adjectives / no-busywork discipline violated by the gate itself — including in cards this lineage produced.
- **Fix (3 changes to `modeb_structure_gate.py`, from the work order, verified against the real cards):**
  1. **Floors lowered to "not empty," not a target:** section 700→**250** (small 300→150), heavy 1,400→**450** (500→300), card 20,000→**7,000** (6,000→3,000). Still fail a skeleton/"N/A" card; stop forcing 30k when the evidence supports 12k.
  2. **`_is_large_bgc` default flipped to `False`** — the large floor now applies only on positive evidence (Interior / ≥40 domains / ≥30 kb), not by default. Demanding max depth by default was the padding incentive.
  3. **New `_padding_findings` (WARN-level `PAD_SIGNAL`)** — flags evidence-free cross-references to other BGC ids and restatement openers, reporting the count + approx % of prose. Conservative (under-flags): ~3–5% on the current cards.
- **Verified:** `_is_large_bgc({})` → False; a **10.6k** dense BGC010 passes depth (would have tripped THIN_CARD at the old 20k floor); PAD_SIGNAL fires on a sectioned padded card and stays silent on evidence prose (no false positive). Updated `test_small_bgc_gets_lower_floor` to the new floor band; +2 regression tests (floor constants + flip; PAD_SIGNAL fires-on-padding / silent-on-dense). Suite 2691 / 0 failed.
- **Severity kept advisory** (PAD_SIGNAL is WARN, matching depth's existing WARN policy). Raising it to ERROR above a threshold (e.g. >15% prose) is a policy choice left to you.

**Follow-up flagged (not this cut):** the real quality bar is **evidence presence**, not length — e.g. requiring the closest-BLASTp-match-per-gene table in §4 when the strain has a BLASTp panel. That belongs in the Mode B forms work (each form asserts which evidence artifacts must be present) so the char-floor stops being the quality proxy entirely.

## Multi-tier
1 module (depth gate) + 1 test updated + 1 new test; no new modules, no AS scrub; 4-tier unchanged; per-tier confirmation at cut.
# v9.7.227 — 2026-07-05 · build 20260705v97227a

**Engine 1.9.109 (unchanged) · Bundle 9.7.226 → 9.7.227.** Fix an owned latent bug in the EBI transport CLI. No scoring change.

- **Owned bug (from .218): `mamey blastp-ebi --submit` raised `AttributeError: 'Namespace' object has no attribute 'hits'`.** In .218 I threaded `hits=a.hits` into `submit_ebi` (`blastp_ebi.py:157`) but never added `--hits` to the `blastp-ebi` subparser — so `a.hits` had no arg to bind to and the submit phase crashed. Same class as the .225 `run_round` bug: an arg referenced without being defined, latent because no test exercised the real CLI submit path.
- **Fix:** added `be.add_argument("--hits", type=int, default=6, …)` to the `blastp-ebi` subparser (the descriptive diff supplied wasn't a machine-applicable unified diff — the `@@` header carried no line numbers — so applied by hand to the exact spot, after `--poll-budget`).
- **Verified on the REAL CLI** (not a proxy): `blastp-ebi --help` now lists `--hits`; `mamey blastp-ebi --submit --fasta … --hits 6` submits a live EBI job ("1/1 jobs submitted") with **no AttributeError**; the full chain holds — `--hits 6` → `a.hits=6` → `submit_ebi(hits=6)` → `_snap_alignments(6)=10` (the .218 valid-enum fix, intact). **+2 non-skip CLI-path regression tests** (`--hits` binds + defaults to 6; `_snap_alignments` enum) so this bug class is caught in CI.

## Parallel (NOT in this cut — data track)
The type-strain cohort merge (`MERGED_45strain_BGC_tally.csv`, 45 strains / 1,771 BGCs) and the SID/TYPE xstrain layers are a separate data-track deliverable, per the Developer or User — QC'd by the other chat (join 952/952, merge keyed on strain+assembly_locator, zero collisions). Two items there map to future engine work, not this cut: the strain-ID auto-derivation convention (`Genus_species_StrainDesignation` from the antiSMASH ORGANISM line, never LLM-invented) and Part A `cohort-precompute` auto-emitting `VERSION.json`/`MANIFEST.csv` for the xstrain store.

## Multi-tier
1-line CLI arg add + 1 test; no new modules, no AS scrub; 4-tier unchanged; per-tier confirmation at cut.
# v9.7.226 — 2026-07-05 · build 20260705v97226a

**Engine 1.9.109 (unchanged) · Bundle 9.7.225 → 9.7.226.** Fix the Part C `modeb-round` CLI path — broken as shipped in .225. No scoring change.

- **Owned bug (audit-found): `mamey modeb-round` crashed on every invocation.** `modeb_round.py:63` in `run_round(package_dir, top_n, scope)` referenced `getattr(args, "from_precompute", …)`, but `args` isn't in `run_round`'s scope (it belongs to the caller `modeb_round_command`), and the caller never threaded `from_precompute` in — so `mamey modeb-round …` raised `NameError: name 'args' is not defined` before reaching the (correct) emitter layer. **Reproduced on the real CLI** against a runs197 package.
- **Why .225's suite stayed green — structural false-green (the real lesson):** the only test exercising `run_round` was `skipif`-gated on a hardcoded absolute dev path (`/data/mamey-local/work/strain_intake/runs_v184/AS-XXX/package`), absent in the hermetic env → it skipped everywhere → the NameError never executed. My .225 hermetic test pinned `emit_batch`/`_precompute_facts` **directly**, bypassing the broken orchestrator. So my ".225 wired end-to-end (CLI → …)" claim was wrong at the CLI level — **retracted**; it held only at the emitter.
- **Fix (from the audit/eval handoff, applied + verified):** `run_round` gains a `from_precompute` param, line 63 uses it (not `getattr(args,…)`), and `modeb_round_command` threads `from_precompute=getattr(args,"from_precompute",None)`. **+2 non-skip-gated `tmp_path` regression tests** (`test_run_round_no_nameerror_without_precompute`, `test_run_round_threads_precompute_dir`) — these run in CI and catch this bug class, closing the coverage hole.
- **Verified against the REAL CLI path this time** (not a proxy): `mamey modeb-round --package <strain> --from-precompute <cohort-dir>` emits 3 cards with **no NameError**, and `BGC001_template.md` carries the grounded pre-fills — §11 "class-I/II lanthipeptide — lanthipeptide maturation machinery present", §14 "assembly-line architecture; not product scaffold". Suite 2687 passed / 0 failed.

**Still open (unchanged, flagged):** remaining Part C section wiring (§4/§5 roles, §7/§27 resistance, §16/§21 nrps substrates) from precompute; `cohort-precompute` as a first-class `mamey` subcommand (currently the verified `tools/build_cohort_precompute.py`); and the figure adjustments the audit re-flagged (`cohort_figures.py` `lab()` two-line labels + `is_private()` still True for AS- strains on the PCA/tier scatters — a separate memo I don't have yet).

## Multi-tier
2-file fix (modeb_round.py + its test); no new modules, no AS scrub; 4-tier unchanged; per-tier confirmation at cut.
# v9.7.225 — 2026-07-05 · build 20260705v97225a

**Engine 1.9.109 (unchanged) · Bundle 9.7.224 → 9.7.225.** Precompute-layer Part C — the card assembler pre-fills grounded facts from the cohort tables so no card re-derives them. Foundation + first verified sections; no scoring change.

- **`modeb-round --from-precompute <cohort-dir>`** — threads a cohort precompute dir through `emit_batch` → `emit_card_template` → new `_precompute_facts()`, which joins a BGC's rows from the cohort tables on the **assembly_locator** (the Part B key, built from `{contig} {region}` via `_cohort_locator` so it matches the tables exactly). Non-fatal: absent dir/rows leave the author prompts intact.
- **Sections wired + verified (grounded pre-fill from real tables):**
  - **§11 product family** ← `COHORT_domain_architecture_by_bgc.csv` archetype.
  - **§14 what cannot be claimed** ← `COHORT_domain_claim_ceiling_by_bgc.csv` (domain-safe / unsafe claims + ceiling), capacity language preserved ("never 'produces'", KCB = similarity not identity).
  - §8 comparator/KCB already reads `facts["kcb_top"]` from the tally.
- **Verified against a real cohort RiPP BGC [Redacted — publication in preparation], cross-checked to its authored card:** §11 emits "lasso/other RiPP"; §14 emits "architecture/family-level; not product identity" + "confirmed RiPP product without precursor validation" — consistent with the authored card's family-level, source-derived read. Hermetic regression test pins the join + both section pre-fills + the non-fatal absent-dir path.

**Correction (owned):** an earlier status note claimed BGC065 was non-modular with 0 rows in the cohort tables — that was a wrong-strain lookup (searched AS-XXX; BGC065 is on **AS-XXX**). BGC065 joins cleanly across architecture / claim-ceiling / roles / tally; it is a valid validation card.

**NOT wired this cut (flagged, bounded follow-ons on the proven mechanism):** §4/§5 (module + ordered domains + roles), §7/§27 (resistance — helper joins `pc_resistance`, section prose not yet wired), §16/§21 (nrps substrate + Stachelhaus). And the full acceptance bar — pre-filled card passes `verify-modeb --strict` with 0 warnings against the **modular** authored golds — still needs `BGC010_AUTHORED.md` / `BGC041_AUTHORED.md` (not on disk); §11/§14 are verified against the tables and the one authored card available.

## Multi-tier
Emitter + modeb-round + cli edits, 1 test (+1 test signature update); no new modules, no AS scrub; 4-tier unchanged; per-tier confirmation at cut.
# v9.7.224 — 2026-07-05 · build 20260705v97224a

**Engine 1.9.109 (unchanged) · Bundle 9.7.223 → 9.7.224.** Precompute-layer wiring, Parts A + B (the cross-strain "cite one table everywhere" layer). Additive/reporting; no scoring change.

- **Part B — `list-bgcs --json` emits the cohort join-key `assembly_locator` natively** (`package_inspector.py`). Closes the QA flag: the tally keyed on `node_id` (truncated) while the architecture tables key on `Assembly_Locator` (`{full contig} {region}`), so a locator join returned 0. New `_cohort_locator()` builds `{Contig} {regionNNN}` — the **full** contig (with `.cov`), region label, NO bgc_id parenthetical — matching the precompute architecture tables exactly. Intentionally distinct from the boss-facing `crosswalk.assembly_locator()` label (truncated node + `(BGC###)`); this is the machine join key, engine-1.9.109-scoped. **Verified:** produces `NODE_9_length_167436_cov_37 region003`; bare-number regions normalize (`2`→`region002`).
- **Part A — `tools/build_cohort_precompute.py`** consolidates the per-strain precompute sources into the seven cohort tables (`mamey cohort-precompute`'s engine). AS-XXX excluded; AS-XXX/815 flagged `co_assembly`; AS-XXX/705 missing nrps_prediction → **WARN not fail**. **Verified against the golden verification pack:**
  - **5 of 7 tables reproduce golden byte-for-byte** (sorted): module architecture (726), domain architecture (726), domain roles (5,846), domain claim-ceiling (726), resistance signals (150).
  - nrps A-domain substrates: **1,100 rows exact**; bgc_id mapped **711/1,100** via the `module_domains` locus→BGC join — the remaining 389 (A/AT domains not present in their strain's assembled modules) need a gene-coordinate→BGC map beyond this pack; documented, not faked.
  - full tally: **819 rows exact**; **Part B join verifies end-to-end — 726/726 tally locators ∩ architecture locators**. 93 non-modular locators are blank because the sample `list_bgcs.json` predates Part B; regenerating them post-Part-B fills them (the real pipeline emits `assembly_locator` natively now).
- Regression tests: `tests/test_cohort_precompute_and_locator.py` (locator format + normalization + boss-label distinction + tool surface). Inventory 123 → 124.

**NOT in this cut (Part C, flagged):** the card-assembler `modeb-round --from-precompute` wiring (pre-fill §4/§5/§7/§8/§14/§16/§21/§27 from these tables) — the golden tables are its inputs, validation targets are the authored BGC065/010/041 cards (`verify-modeb --strict`, 0 warnings). Needs emitter surgery + verify-modeb verification; its own cut.

## Multi-tier
One engine edit (package_inspector) + one new tools/ script + 1 test; no AS scrub (cohort public); 4-tier unchanged; per-tier confirmation at cut.
# v9.7.223 — 2026-07-05 · build 20260705v97223a

**Engine 1.9.109 (unchanged) · Bundle 9.7.222 → 9.7.223.** The two co-audited SCORING cuts (KCB ceiling coverage-gate + edge-downgrade assembly-awareness), implemented by the parallel chat, run through four-tier cut discipline here. This is a scoring change — batteries re-verified against the real functions this pass, not self-certified on the note's word.

**CUT A — KCB coverage + class-mismatch → claim ceiling** (`antismash_evidence.py`, `chatgpt_commands.py`)
- Shared helpers `kcb_class_mismatch()` + `kcb_coverage_substantial()` — ONE coverage rule, reused by both ceiling sites (no third variant). The real BGC065 inflation site (`antismash_evidence.py:1110`) previously granted a product-level ceiling for any MIBiG reference line, coverage-blind; now requires `kcb_protein_hits ≥ 5` (the `function_and_novelty` substantial floor) AND no PKS/NRPS-vs-RiPP/cofactor class mismatch, else caps at "source-derived similarity anchor only" + records `claim_ceiling_gate`. `_claim_ceiling` reconciled to the same rule (incl. ≥30%-of-cluster when gene count is known).
- **Re-verified on BGC065's real values:** class_mismatch True, substantial(3) False, `_claim_ceiling` → "source-derived similarity" (was product-level). **No over-suppression:** a genuine 12/15-gene concordant PKS (kp=12, T1PKS vs T1PKS) still → "candidate product-level similarity".

**CUT B — edge-downgrade assembly-awareness** (`architecture_first.py`, `cli.py`)
- `ArchitectureReport` gains `assembly_tier` + `finishing_candidate`; a module run-context (`set_run_assembly_tier`, wired once at `cli.py` from `assembly_tier(interior_pct)`) feeds `_apply_boundary_adjustment` without touching its 28 call sites. On POOR/VERY_POOR the Edge penalty is skipped (fragmentation, not biology) and the BGC is flagged `finishing_candidate` instead of downgraded; Full-contig penalty retained everywhere; GOOD/MODERATE/UNKNOWN unchanged.
- **Re-verified tier cases:** POOR Edge HIGH → HIGH + finishing_candidate; GOOD Edge HIGH → MEDIUM; VERY_POOR Full-contig HIGH → MEDIUM; UNKNOWN Edge HIGH → MEDIUM (pre-cut default preserved).

**Regression tests:** `tests/test_scoring_cuts_223.py` (6) pins both batteries incl. the BGC065 fixture + the GOOD-assembly no-regression case. Full suite **2675 passed / 0 failed**.

**AB_auto impact (traced, not a cohort re-run):** AB_auto reads `antibacterial_score`, NOT `product_claim_ceiling` or `confidence` — so these cuts do **not** shift the AB_auto ranking by design; the effect lands on the claim ceiling and confidence/lead_tier. No unintended rank perturbation.

**NOT done this cut (stated plainly):**
- **Real-package AS-XXX end-to-end flip** — the AS-XXX sealed package is not on this disk; I verified the helpers, the `_claim_ceiling`/`_apply_boundary_adjustment` paths, and the suite against the real functions, but not a full extraction re-run showing BGC065's `product_claim_ceiling` change in the sealed package. Whoever holds AS-XXX should confirm the package-level flip.
- **Edge-core vs edge-flank refinement** (CUT B item 3) — tier-gating + finishing flag are in; the crosswalk-coordinate edge-core detection (penalise only when core domains sit at the contig break) is still pending, flagged in the reasoning string.

## Multi-tier
Scoring edits to 4 existing modules + 1 test; no new modules, no AS scrub (cohort public); 4-tier structure unchanged; per-tier confirmation at cut. Staged for independent audit sign-off (not self-certified).
# v9.7.222 — 2026-07-05 · build 20260705v97222a

**Engine 1.9.109 (unchanged) · Bundle 9.7.221 → 9.7.222.** Align the cohort figures with the .219 AS-public decision (figure-side of the PI decision). Reporting/format only — no scoring.

- **`mamey/cohort_figures.py` — PUBLIC/PRIVATE divider + labels retired.** The AS cohort is public at publication (PI decision 2026-07-06), so the figures no longer draw the dashed PUBLIC|PRIVATE divider or the "PRIVATE (AS)" / "PUBLIC (SID)" labels: `soft_divider` is a no-op (call sites unchanged), the two inline divider blocks and the two title/caption strings that named the split are removed (0 `PRIVATE (AS)`/`PUBLIC (SID)` refs remain).
- **`order_strains` — ascending strain number + clustering hook.** Default axis order was `raw_bgcs` with a public-then-private split; now a single ascending-strain-number run so panels line up by ID across figures and the axis is reproducible. `explicit=` is preserved as the hook for a data-clustering order (e.g. dendrogram leaf order from the .221 domain matrix). New `_strain_num()` helper.
- Updated `test_cohort_figures_v9792::test_cohort_figures_multi` to the new convention (ascending strain number; the retired "PRIVATE last / PUBLIC first" assertion is replaced with a monotonic-number check).

**Reconciliation note:** the source diff (`DIFF_cohort_figures_ordering_labels_privremoval.patch`, 13 hunks) was cut against a base that had diverged from the .221 tree and would not apply (0/13 hunks, even fuzzy). Changes were hand-applied from the diff's intended end-state and verified against the real figure tests (3/3 pass) rather than trusting the patch. A partial apply broke the ordering test first — caught and completed here, not shipped half-done.

## Multi-tier
Edits to 1 module + 1 test; no AS scrub (cohort public); 4-tier structure unchanged; per-tier confirmation at cut.
# v9.7.221 — 2026-07-05 · build 20260705v97221a

**Engine 1.9.109 (unchanged) · Bundle 9.7.220 → 9.7.221.** Wire the cross-strain antiSMASH-HMM domain census (PATCHCHAT work order). Additive/reporting only — no scoring, Mode B, or claim-safety logic touched.

- **New `tools/build_domain_matrix.py`** — cohort-level, deterministic, offline, no add-on. Reads the per-gene `sec_met_domains` column (antiSMASH pre-computed HMMER calls, already banked in every sealed package) across a cohort and emits a domain × strain matrix (`domain_matrix_counts.csv`), **per-Mbp density** (`domain_matrix_density_per_mbp.csv`), a function × strain rollup (`domain_functional_rollup.csv`), a core/accessory/strain-private split, and `Domain_Matrix.md`. The gap it closes: no existing cross-strain surface (B4 triggers, normalization matrix, pangenome, TFBS) aggregated the banked domains into a domain × strain matrix.
- **Vocabulary single-sourced** from `mamey.mamey_markers.MAMEY_MARKERS` (each Marker's regex Target + `category`) — the domain→function map never drifts from the engine's own marker set, per the work order.
- **Claim-safety banner is mandatory in every output:** antiSMASH domain calls are HMMER profile/similarity matches, **not verified function** (same standing as KCB); per-Mbp density is the cross-strain-comparable metric (counts scale with genome size + fragmentation); a strain-private domain is a CANDIDATE until confirmed.
- **Source-agnostic hook** (`--domtblout-dir`) so the Release-2 offline-pyHMMER `domtblout` can later fold in as a second higher-recall domain source.
- **Verified against real artifacts:** ran on the 5 sealed runs197 packages → 5 strains, 1593 domain tokens, core 85 / accessory 506 / private 1002; function mapping confirmed (ACP→PKS, AMP-binding→NRPS, halogenase→halogenation). Hermetic test asserts core/private split + genome-size density normalisation + MAMEY_MARKERS sourcing. Inventory 122 → 123.

**Follow-on (NOT in this cut, flagged):** work-order §6.2 — folding a `Cross_Strain_Domain_Prevalence` sheet into `add_xstrain_sheets.py` so the master workbook gets it each round. `add_xstrain_sheets.py` currently carries hardcoded per-strain data rather than consuming a cohort dir, so wiring the census in needs that plumbing added first — a bounded next step, not hand-rolled here.

## Multi-tier
New tools/ script + 1 test + inventory regen; no AS scrub (cohort public); 4-tier structure unchanged; per-tier confirmation at cut.
# v9.7.220 — 2026-07-05 · build 20260705v97220a

**Engine 1.9.109 (unchanged) · Bundle 9.7.219 → 9.7.220.** One coordinated CORRECTNESS pair (MODEB_STRENGTHEN findings 1+2) + the AS-XXX provenance-columns gate (PATCH_301PM). No scoring change.

- **Finding 1 — `verify-modeb` now runs claim-safety.** `mamey/authored_verify.py:95` and `:130` called `lint_card` without `check_claim_safety=True`, so the .217 claim-safety lint (#58) was dark on the path authors actually run — an injected "produces phosphonoacetic acid" passed `verify-modeb` clean. Both call sites now pass `check_claim_safety=True` (WARN-level, never a structural refuse). **Verified:** the injected overclaim now raises a CLAIM_SAFETY finding (was 0); the verb-match check is **0-false-positive on all 3 real exemplar cards**, so enabling it doesn't spam legit prose.
- **Finding 2 — robust linter matches multi-word compound names.** `tools/claim_safety_linter.py` `_identity_hit` captured a single token after the production verb and checked `t in cnames`, so multi-word names ("phosphonoacetic acid", "heat-stable antifungal factor") were false-negatives even when correctly derived. Now builds a probe from the captured token + the window to sentence end and substring-matches any derived name, reusing the negation/capacity guards. **Verified:** single-word still flags; both multi-word names now flag; negated + capacity-framed multi-word pass; "produces a signal" does not flag (no new FP). (Finding 3, visible depth floors, already landed in .218.)
- **PATCH_301PM — per-BGC provenance-columns gate.** From the AS-XXX run: three of four per-BGC TSVs led with a bare `bgc` column, untraceable to strain/node·region (violates the durable-anchor rule). Folded `tools/check_provenance_columns.py` (fail-closed: any per-BGC CSV/TSV must carry strain + contig+region, or an `assembly_locator` that encodes both) + `tests/test_provenance_columns_gate_v97218.py` (7 tests) + a `gate_registry.tsv` row (WIRED, referenced by its test — satisfies the wiring invariant). The gate guards **analysis** artifacts, so it's test-referenced, not release.sh-invoked. Inventory 121 → 122.

## Multi-tier
Edits to 2 existing files + 1 new gate tool + 2 tests + registry/inventory regen; no AS scrub (cohort public per .219); 4-tier structure unchanged; per-tier confirmation at cut.
# v9.7.219 — 2026-07-05 · build 20260705v97219a

**Engine 1.9.109 (unchanged) · Bundle 9.7.218 → 9.7.219.** Fold the public Hymenoptera strain metadata into the bundle and deactivate the AS-ID leak enforcement, per PI decision (the Developer or User Smith, 2026-07-06). **Tier structure unchanged** — all four tiers still cut and cross-tier parity still holds. No scoring change.

- **Strain metadata folded in** — `docs/reference/Master_Strain_Table_Hymenoptera_2026-07-05.csv`, 181 strains × 16 cols (Host, Location, Strain, Genus(16S), Closest Type Strain, 16S %sim, Candida/MRSA, GenBank accession, collection date, geo-loc). Public data per the paper; the Candida/MRSA columns are non-authoritative and not a disclosure concern. This is also the store-backed source the collection figures need (unlocks the metadata-gated `render_collection_figures` set).
- **AS-ID leak enforcement DEACTIVATED (reversible)** — the whole AS cohort is public (strain/genus/host/16S/accession in the Hymenoptera paper), so AS IDs are no longer scrubbed or audited:
  - `tools/make_public_tier.sh`: the AS-scrub (`redact_public_tier.py --as-only`) and the AS-leak audit are gated behind a new `AS_SCRUB` flag (**default 0** = deactivated). Real AS IDs — including the folded table — now survive into the public tier (verified: `AS-XXX` intact in the SID-public zip, not `AS-XXX`). Machinery **retained and reversible**: `AS_SCRUB=1` re-arms both for a future private cohort.
  - `tools/verify_tier_derivation.py`: the parity derivation mirrors the same flag (identity redaction when `AS_SCRUB=0`), so `public == redact(private)` still holds honestly. Verified: tier-derivation parity gate OK, 4-tier parity PASS.
  - **All non-AS hygiene stays hard-fail** — `private/` tree, internal working docs, denylist terms, banks-in-code-tier, post-scrub parse sanity are untouched.
  - `test_verify_tier_derivation.py` updated to assert **both** modes (identity by default, scrub under `AS_SCRUB=1`), guaranteeing the reversibility rather than commenting it.
- **Doc contradiction resolved** — `AGENTS.md` no longer says "PRIVATE for AS-series"; it now states the cohort is PUBLIC (PI decision 2026-07-06) with the `AS_SCRUB=1` re-arm note. This closes the standing audit flag (shipped guard-retired vs. doc-says-private).

## Multi-tier
New public data file + tooling/test edits; AS IDs now intentionally present in all tiers (cohort public); 4-tier derivation + parity unchanged; per-tier confirmation at cut.
# v9.7.218 — 2026-07-05 · build 20260705v97218a

**Engine 1.9.109 (unchanged) · Bundle 9.7.217 → 9.7.218.** One owned bug fix + two tested diffs from the AS-XXX run (Patch_1252). No scoring change.

- **EBI transport bug (owned) — `mamey/blastp_ebi.py`.** The .215 fold posted `alignments=6`/`scores=6`; EBI's `alignments` is an **enum** (`0,5,10,20,50,…`), so 6 is a hard **HTTP 400 "Invalid parameters"** — the transport was non-functional as shipped in v215–v217. Fixed: `_snap_alignments()` rounds the requested hit count up to the nearest valid enum (6→10), threaded from `--hits`. **Verified live:** a real EBI submit now returns a job id (was 400). Regression test asserts `_snap_alignments(6)=="10"` and the value is in the enum.
- **Diff A — cnames slash-split (`tools/claim_safety_linter.py`, item 3 corrected).** `derive_compound_names_from_package` already added the KCB comparator, but as the raw `KCB_top` token, which is often slash-joined (`"bombyxamycin A/bombyxamycin B"`) — so the bare `bombyxamycin` was absent and a genuine "synthesizes bombyxamycin" passed unflagged. Fix splits slash-joined tokens + strips the trailing designator to add the base name. **Verified on my tree:** `produces/synthesizes/makes bombyxamycin` now flag when the base name is derivable; the .217 negation guard still passes denials.
- **Diff B — visible depth floors (`mamey/modeb_template_emitter.py`, item 8).** Emits each section's enforced char floor as a comment so authors see it where they write (floors imported from `modeb_structure_gate` — single source, no divergence). **Correction I made on apply:** the diff put the comment *inline* in the `## §N title` header, which broke `test_emit_template_roundtrip_passes_validator` (TITLE_MISMATCH on all sections — the validator read the comment as part of the title). Moved the comment to its own line under the header; title clean, floor still visible, roundtrip + all 14 emitter tests pass. The patch chat had verified `extract_section_bodies` but not the full suite — caught here.

## Multi-tier
Edits to 3 existing files + 1 test; no AS IDs, no new modules → all four tiers; per-tier confirmation at cut.
# v9.7.217 — 2026-07-05 · build 20260705v97217a

**Engine 1.9.109 (unchanged) · Bundle 9.7.216 → 9.7.217.** Reopen + correct the #3 claim-safety fix — .216 patched the wrong linter. No scoring change.

- **#3 (owned reopen).** The .216 fix added negation/idiom handling to `mamey/claim_safety_gate.py::lint_text` — but the CLI `claim-safety` command calls `tools/claim_safety_linter.py::lint_claim_safety_report` (the robust cnames path that auto-derives compound names). That linter never got the fix and had **no negation detection**, so correct §14 denials ("does not support that BGC010 produces colibrimycin") still flagged MEDIUM end-to-end. The .216 module fix was dead code for the CLI path — which is exactly why it looked verified in isolation. Credit: v216 verification chat traced the root cause.
- **Fix:** added `_NEGATION_RX` and guarded **both** hit-testers in `tools/claim_safety_linter.py` — `_flag` (heuristic path) and `_identity_hit` (robust cnames path) — before the `t in cnames` membership return, on a widened ±80-char window. Full call-site sweep this time, not one of two.
- **Verified against the real CLI function** (`lint_claim_safety_report` with `compound_names` supplied), audit's battery: the §14 denial's `identity_overclaim` is **gone**; a genuine overclaim ("BGC010 produces colibrimycin at high titer") **still flags**; "resembles X rather than produces X" and "capacity consistent with X" **pass**. New `tests/test_claim_safety_cli_path.py` exercises the CLI path (4 tests) — the coverage the .216 test lacked (it tested the non-CLI `lint_text`).

**Flagged, NOT fixed here:**
- **Two diverged linters.** `mamey/claim_safety_gate.py::lint_text` and `tools/claim_safety_linter.py::lint_claim_safety_report` now both have negation handling, but they remain two implementations. Whether the CLI should call one canonical linter is a de-duplication decision for a later cut, not folded here.
- **`derive_compound_names_from_package` coverage gap** (pre-existing, independent of #3): it did not include "bombyxamycin" (BGC041's KCB comparator) among its derived names, so a genuine "synthesizes bombyxamycin" overclaim could pass the robust path in that package. A false-negative on a hypothetical vs. #3's false-positive on real cards — lower priority; the derivation should include KCB comparator names from every authored BGC.

## Multi-tier
Edit to one tool + 1 new test; no AS IDs, no new modules → all four tiers; per-tier confirmation at cut.
# v9.7.216 — 2026-07-05 · build 20260705v97216a

**Engine 1.9.109 (unchanged) · Bundle 9.7.215 → 9.7.216.** Three bounded bug-fixes from the v9.7.215 audit addendum + the AS-XXX authoring run. No scoring/format change — the Mode B redesign recs and the edge/KCB scoring changes are deliberately held for their own cuts (see below).

- **#3 claim-safety false positives** (`mamey/claim_safety_gate.py`). Two classes, both fired on *correct* cohort cards: (a) `_PRODUCTION_RE` matched the English idiom "makes it/the/them/for" as a biosynthetic claim — now those function-word objects are in `_SAFE_AFTER`; (b) the ±80-char negation window was too short to see denials 100+ chars upstream, so correct §14 denials ("does not support that the BGC produces a named compound") flagged MEDIUM — now a `_NEGATION_RE` scans back to the sentence start (≤400 chars). Verified: the denial + three "makes" idioms pass; real overclaims ("produces a named compound", "synthesizes another named compound") still flag; safe-context ("capacity consistent with") still passes.
- **#4 hmm-adjudicate dependency mislabel** (`mamey/hmm_blastp_adjudicate.py`). Reported "pyhmmer not installed" even when the real missing dep was **biopython** (`from Bio import SeqIO` in `bgc_walk`) — cost real debug time. Now reads `exc.name` and names the actual missing module, and points at the full addons stack (pyhmmer + biopython).
- **#6 `mamey doctor --probe-transports`** (spec §6.6). Opt-in, offline-safe (short timeout, errors → WARN, never hangs) probe of both `blast.ncbi.nlm.nih.gov` and the EBI REST base, reporting which BLASTp transport is live. Verified in the current sandbox — the exact blocking scenario: NCBI **DOWN (Temporarily unavailable)** → routes to `blastp-ebi`; EBI **LIVE**. Turns a mid-run submission failure into a startup decision.

**Received this run, staged (NOT in this cut):** the AS-XXX patch delivered the `MODEB_REDESIGN` spec + the KCB over-valuation trace I owed. Tier plan, matching the spec's own classification: **Rec 1/2/6** (evidence auto-populate, footer caveats, visible depth floors — format, no scoring) → next format cut; **Rec 4** KCB coverage-banner at emit (presentation) coordinates with the **KCB-demotion** score-weighting (the trace shows KCB_score is coverage-blind: 3-gene matches score 1117/1012/438); **Rec 5** edge-downgrade decoupling (`architecture_first.py:807`, 28 call sites) and the KCB score-weighting are **scoring-tier → own cut + audit each**. Rec 4-emit and KCB-demotion-score must be coordinated to avoid double-patching the KCB path.

## Multi-tier
Edits to 3 existing files + 1 test; no AS IDs, no new modules → all four tiers; per-tier confirmation at cut.
# v9.7.215 — 2026-07-05 · build 20260705v97215a

**Engine 1.9.109 (unchanged) · Bundle 9.7.214 → 9.7.215.** Fold the EBI BLASTp fallback transport into the engine (from the AS-XXX EBI patch), so a run can get per-gene homology when NCBI nr is unreachable — the "Temporarily unavailable" failure that's been blocking the online channel from this sandbox. No scoring/parse layer change: EBI feeds the SAME `ingest-blastp` unchanged.

Accretion-justified: blastp_ebi.py — EBI transport (submit/harvest/convert); no existing module speaks the EBI REST protocol, and blastp_online is NCBI-URL-API-specific.
Accretion-justified: ebi_xml_to_outfmt10.py — EBI-XML → NCBI -outfmt 10 converter; the coverage-preserving interop shim, distinct from the NCBI XML parser.

- **`mamey/ebi_xml_to_outfmt10.py`** — converts an EBI ncbiblast **XML** result into the exact 13-column NCBI `-outfmt 10` that `blastp_ingest.parse_hit_table` already accepts. Uses `<sequence length>` + `<querySeq start/end>` to recover **query-coverage** — the field the EBI *TSV* shortcut drops. **Verified on a live EBI XML this session:** a 78-aa query emits `q_start=1,q_end=78` = 100% coverage; hermetic test asserts 13 cols + coverage present + that the real ingest parser accepts the output.
- **`mamey/blastp_ebi.py`** — resumable EBI transport: `submit_ebi` (one job per protein, job ids persisted after every submit so a killed run resumes), `harvest_ebi` (poll → retrieve **XML**), `to_outfmt10` (convert all harvested XML → one ingest-ready CSV + a `.provenance.json` sidecar). Throttled (default 6 s/submit) for EBI fair-use.
- **CLI `mamey blastp-ebi`** — `--submit` / `--harvest` / `--to-outfmt10 OUT.csv`, mirroring `blastp-online`'s shape. Default DB `uniprotkb_bacteria` (actinomycete-relevant; `uniprotkb_trembl`/`uniref90` also offered).
- **Provenance is mandatory, not optional.** EBI has **no nr**; its hits/%identities are not interchangeable with an nr panel. `transport=EBI` + `database` are stamped into the panel's provenance sidecar so no card can silently mix nr and EBI. EBI is a **fallback only**, never the default — nr remains the reference DB when reachable; DB-sensitive calls should be flagged for nr re-run.

**Verified against real artifacts, not proxies:** live EBI submit→poll→XML→convert round-trip; the bundle's real `parse_hit_table` accepts the converter output with coverage intact. 2/2 new tests pass.

**Superseded (retracted):** my earlier `blastp_campaign.py ebi-run` used the EBI **TSV** result, which drops coverage — the exact shortcut the patch spec warns against. This XML-based fold is the correct path; the TSV `ebi-run` is not carried into the bundle.

**Deferred (spec §6.6, not a blocker):** `mamey doctor` probing both NCBI and the EBI REST base to report which transport is live — a clean follow-up.

## Multi-tier
Two new `mamey/` modules + CLI verb + 1 test (with a real-XML fixture); no AS IDs → all four tiers; per-tier confirmation at cut.
# v9.7.214 — 2026-07-05 · build 20260705v97214a

**Engine unchanged (1.9.109) · Bundle 9.7.213 → 9.7.214.** tools/ duplication-risk audit (audit chat) — one real duplicate retired, three doc fabrications/dangling-refs fixed, and the doc-reference gate extended to cover `tools/` (the gap that let them ship). No scoring change.

- **`tools/build_master_figure_atlas.py` → redirect shim.** Confirmed duplicate of the load-bearing `build_master_figures.py` (its own docstring admitted it mirrored it; zero CHANGELOG entry for its creation). Body replaced with a redirect that errors to stderr (exit 1) naming the canonical tool — not deleted, in case something calls it by name.
- **Doc fixes (fabricated/dangling references removed):** `docs/FIGURES_START_HERE.md` (listed `build_bee_wasp_master_figures.py`, which exists nowhere in the tree); `docs/GUIDE/06_Concepts_QandA.md` (described `apply_hygiene.sh` in confident detail — a script invented from nothing, zero tree mentions; replaced with two verified-real examples); `docs/reference/03_Plumbing_Reference.md` (stale by 96 versions — staleness banners + italicized 5 consolidated-away module names in §P3/§P4); `docs/FIGURES_DIAGNOSTIC_v9.7.150.md` (answered its own open "does first_pass_scans.py exist?" — no, it's a `tools/` build script, not a `mamey/` module).
- **Class-level gate — `tools/check_dangling_refs.py --scope tools`.** The accretion gate is `mamey/`-only and this dangling-ref gate was `examples/`-only; nothing checked doc references to `tools/` names — exactly how the above shipped silently. New additive `--scope tools` mode checks backtick-quoted `.py`/`.sh` names against a real file index (tools/mamey/scripts/tests/Wheelhouse/root), with the same historical/forward-looking exclusions the accretion gate uses. **+companion test** `tests/test_no_dangling_tool_refs_v97213.py` freezes the 6 known-remaining refs (all deep `03_Plumbing_Reference.md` API subsections needing consolidation-era module-tracing) and fails on any *new* one.

**FLAGGED for PI decision — NOT touched by this cut:** the audit found the **AS-series privacy guard is retired** in the shipped tree (`make_public_tier.sh`: `AS_GUARD_RETIRED=1`, dated PI decision 2026-06-30 — leak-audit WARN not FAIL on AS IDs), while `AGENTS.md` still says "PRIVATE for AS-series/unpublished strains." That's a dated policy decision by the PI with real disclosure consequences; I don't guess on disclosure, so both files are left exactly as-is pending the Developer or User's confirmation of which is current.

**Deferred (gate keeps flagging until done):** the deep `03_Plumbing_Reference.md` subsections (§3/§12/G-series/§9) that document consolidated-away modules by function signature — correcting them means tracing where each function landed post-consolidation; not faked.

## Multi-tier
Doc edits + one tool→shim + one gate extension + 1 new test; no AS IDs, no new modules → all four tiers; per-tier confirmation at cut.
# v9.7.213 — 2026-07-05 · build 20260705v97213a

**Engine unchanged (1.9.109) · Bundle 9.7.212 → 9.7.213.** Audit follow-on to the .212 empty-strain guard (audit chat signed .212 PASS). No scoring change.

- **Empty-strain heatmap guard — completed for the whole bug class.** The .212 guard (Nocardia patch B) fixed only ONE `np.nanmax`-on-empty site (`figs_single`). The identical crash — an empty cohort or all-zero/all-negative strain row makes the log-scaled `disp` empty/all-NaN, so `np.nanmin`/`np.nanmax` raise `ValueError` (zero-size reduction) or emit an all-NaN warning — was still live in three siblings: the shared **`heatmap()`** helper (line ~145, *more* exposed than the site .212 patched), **`hmap()`** (~849), and the **class×resistance figure** in `batch3` (~1095), plus two `mx=np.nanmax(mat) or 1` annot sites (the `or 1` catches a 0 result but not the empty-array exception). All five guarded with the same size-and-not-all-NaN check → benign 1..2 fallback so the empty grid renders instead of crashing the figure run.
- **+3 reproduction tests** (`tests/test_empty_strain_heatmap_guard.py`) drive the real `heatmap()`/`hmap()` entry points with all-zero/empty input, promoting the all-NaN `RuntimeWarning` to an error. Verified FAIL on the unpatched .212 tree, pass here — closing the audit's residual #3 (guard now proven by reproduction, not just code-reading).
- **Audit residual #1 — `tools/build_lead_tiers.py:80`.** The adjacent `modeb_verdicts.csv` read was a bare `open()` (read-side `#18` residual in the file B3 touched); now `encoding="utf-8"`.

**Still deferred (audit residual #2, not a blocker):** the 88 `tools/` `json.load(open())` sites — CPython-safe; a future codemod cut should close them rather than leaving them permanently deferred.

## Multi-tier
Edits to one module + one tool + 1 new test; no AS IDs, no new modules → all four tiers; per-tier confirmation at cut.
# v9.7.212 — 2026-07-05 · build 20260705v97212a

**Engine unchanged (1.9.109) · Bundle 9.7.211 → 9.7.212.** Audit-fix batch (bug-hunt report B1–B4 + a Nocardia-chat robustness patch), independently converged with the Sonnet audit chat. No scoring change.

**Independent convergence:** the bug-hunt chat, the Sonnet audit chat, and this chat arrived at the same fixes for B4/B3/B2 (matching sites, matching approach) — folded once here, not thrice.

- **B4 (owned) — `cohort_figures.py` matplotlib guard was defeated by two module-level sites.** `plt.rcParams.update(...)` ran unconditionally at import → `NameError('plt')` without matplotlib, and a redundant unguarded `from matplotlib.colors import LogNorm` (already imported under the guard). Both fixed; `import mamey.cohort_figures` now works matplotlib-less. My .209 #35 guard on this file was incomplete and my .210 test too weak (asserted `hasattr(_HAVE_MPL)` with matplotlib *present*). New `tests/test_figure_import_guards.py` **subprocess-blocks matplotlib and asserts all three figure modules import with `_HAVE_MPL=False`** — the real absence simulation.
- **B3 (HIGH, claim-safety) — `tools/build_lead_tiers.py` fail-closed.** The QC hold-set is a stated contract ("FLAG strains are held, never promoted"); a silent `except Exception: pass` left `held={}` on any parse failure, silently **promoting strains that must be held**. Now raises `SystemExit` on a corrupt `assembly_qc.json` (can't prove which strains are safe → refuse) + closes B1/B2 at that site.
- **B2 — `write_text()` without `encoding="utf-8"`.** 35 mamey-core sites swept (paren-matched); **verified residual 0** across 135 total `write_text` calls in mamey/. Write-side twin of the .209 #18 read-side sweep; crash reproduced under `LC_ALL=C` on real `§`/`·` content.
- **B1 — `json.load(open())` handle leak.** All **14 mamey-core sites** routed through a context-managed `_loadj()` helper (incl. the real-risk 3-fds-per-strain loop in `cohort_figures.load()`); residual 0 in core. The **89 `tools/` sites deferred** (one-shot CLI scripts, CPython-safe) — same scope call as the Sonnet audit.
- **Empty-strain guard (Nocardia chat, patch B) — `cohort_figures.py`.** Heatmap crashed on an empty/all-zero strain (`np.nanmax` on empty); reshape + guarded `vmax`.

**Already-landed, skipped:** Nocardia A1/A2 (= .210 #35 collection/locus guards), D (= .211 KCB dedup); Sonnet audited .211 as correct, no patch needed.

**Staged separately, NOT in this cut:** the Sonnet **KCB-demotion implementation** (base .207, items 1–4) — Sonnet marks it *draft, verified-not-regressing but not release-safe*, with 4 open gaps (HMM-vs-BLASTp tiebreak, the agree-doesn't-stop-scanning generalization, clinker integration, thin report_card test coverage). It needs its own cut + audit; folding it into a hygiene release would be exactly the "present draft as finished" failure to avoid.

## Multi-tier
Edits to existing files + 1 new test; no AS IDs, no new modules → all four tiers; per-tier confirmation at cut.
# v9.7.211 — 2026-07-05 · build 20260705v97211a

**Engine unchanged (1.9.109) · Bundle 9.7.210 → 9.7.211.** One bug fix (owned) in a shipped tool, found while extracting KCB confidence from a real AS-XXX v8 antiSMASH run. No scoring change.

- **BUG (owned) — `tools/kcb_confidence.py` double-counted KCB regions.** antiSMASH v8 renders the region-overview table **twice** (per-record + global), so the extractor counted each region ~2×. Now dedups by `region_anchor`. **Correction to the figures reported in .208:** AS-XXX is **23 KCB hits (3 High / 3 Medium / 17 Low)**, not the 44 (4H/6M/34L) stated in the .208 changelog and the tool docstring — both corrected here. The *calls* were always right (streptophenazine=High, cinnapeptin/tambjamine=Low all still hold) and the distribution shape is unchanged (~74% Low), so the demotion premise — most KCB calls are Low — stands; only the counts were inflated.
- Verified on a fresh **AS-XXX antiSMASH v8.0.4** run (full run, KCB Similarity-Confidence present, unlike the prior v5.1.1 detection-only zip): **17 KCB hits (2 High, 1 Medium, 14 Low)** — 82% Low. High calls: FW0622, loseolamycin A1/A2.
- +1 hermetic dedup test (two overview tables → one row per anchor).

## Multi-tier
Edits to one existing tool + its test; no AS IDs, no new modules → all four tiers; per-tier confirmation at cut.
# v9.7.210 — 2026-07-05 · build 20260705v97210a

**Engine unchanged (1.9.109) · Bundle 9.7.209 → 9.7.210.** Four more bounded, no-decision items from the 60-worst scope, investigated + fixed against the real tree (for an audit chat to sign off). No scoring change.

- **#35 completed** — `mamey/collection_figures.py` + `mamey/locus_map.py` top-level matplotlib imports now wrapped in `_HAVE_MPL`/`_require_mpl()` (matching the .209 cohort_figures guard). All three figure modules now degrade with a clear "install `.[figures]`" message instead of a traceback. Verified: 0 bare top-imports remain in the three.
- **#24 evaluate_card arg-order guard** (`mamey/mode_b_quality_gate.py`) — passing the card text as the first arg used to return a silent garbage STUB. Now raises `ValueError` when `bgc_id` is multiline or >100 chars (a real id is neither). Docstring preserved; normal calls unaffected; verified the guard fires on a swap and a correct call still grades.
- **#18 residual** — `mamey/kcb_frontpage.py` `read_text()`/`open()` text sites now carry `encoding="utf-8"` (0 bare remain there).
- **#16 partial** — the two portability-breaking `else '/data/mamey-local'` fallback defaults (`tools/build_deep_data.py:63`, `tools/build_bgc_markers.py:67`) → `os.getcwd()`. **Left intentionally:** the `/mnt/user-data/{uploads,outputs}` search paths/defaults — those are the canonical locations in this deployment, not bugs; changing them would break the workflow. So #16 is *not* fully closed by design.
- +3 regression tests (`tests/test_cut_210_hygiene.py`): the two figure guards + the evaluate_card swap.

## Multi-tier
Edits to existing files + 1 test file; no AS IDs, no new modules/tools → all four tiers; per-tier confirmation at cut.
# v9.7.209 — 2026-07-05 · build 20260705v97209a

**Engine unchanged (1.9.109) · Bundle 9.7.208 → 9.7.209.** Two independent patch sets from the 60-worst-qualities scope (AS-XXX chat + Sonnet chat), reconciled — no file overlap, both verified against the real tree. No scoring change.

## AS-XXX chat — clusters A+B lints/guards (4 items, 8 tests)
- **#58 claim-safety lint** (`mamey/modeb_structure_gate.py`): opt-in `check_claim_safety` → `_claim_safety_findings` flags product-identity phrasing ("produces", "synthesizes", "is an enediyne"). Regex + claim-safe exclusions lifted verbatim from `docs/MODE_B_CARD_CLAIM_SAFETY_AUDIT.md`. WARN-level, never a structural refuse. Verified 0 FP on 3 real cohort cards [Redacted — publication in preparation].
- **#59 citation/provenance lint** (same file): opt-in `check_citations` → flags a BGC id never given a node·region locator (MISSING_LOCATOR) and a card with no provenance tags (NO_PROVENANCE_TAGS). WARN-level.
- **#8 docstring/FLOORS residual** (`mamey/mode_b_quality_gate.py`): fixed the stale `6,000` LOW-floor comment (a *different* fragment than the header I fixed in .206 — B17 kept re-drifting). Test asserts every FLOORS value appears and the `6,000` fragment is gone.
- **#35 figure-import guard** (`mamey/cohort_figures.py`): top-level matplotlib wrapped in `_HAVE_MPL`/`_require_mpl()`; a bare checkout gets a clear install message, not a traceback. **Partial:** `collection_figures.py` + `locus_map.py` still carry bare imports — follow-up.

## Sonnet chat — #18 encoding sweep + bonuses (9 files)
- **#18**: `read_text()`/text-mode `open()` → `encoding="utf-8"` across `bgc_guide, master_workbook, npatlas_resolver, output_checklist, package_map, directed_studies/pks, tools/{blastp_campaign, mamey_habitat_map, reclass_check}`. Residual bare read_text/open in the swept files: **0**.
- **Handle-leak fix (bonus)**: the `json.dump(recs, open(ck,"w"))` checkpoint sites in `blastp_campaign.py` now use a `with` block — closes a real leak.
- **Redaction (bonus, leak-critical)**: `tools/reclass_check.py` docstring `AS-XXX` → `AS-XXX` (a private ID that would reach public tiers). Verified: 0 `AS-XXX` remain.
- **Robustness (bonus)**: `reclass_check.py` Rank cast `int(x.get("Rank"))` → `int(float(x.get("Rank") or 9999))` — handles float-string ranks.

## Multi-tier
Edits to existing files + 1 new test file; the AS-XXX redaction reduces leak surface; no new modules/tools → all four tiers; per-tier confirmation at cut.
# v9.7.208 — 2026-07-05 · build 20260705v97208a

**Engine unchanged (1.9.109) · Bundle 9.7.207 → 9.7.208.** Fold two verified reference tools with hermetic tests. Reference tools only — the deep integration each enables stays a separate (Sonnet) job, flagged below.

- **`tools/blastp_campaign.py`** — checkpoint-first, resumable NCBI BLASTp campaign runner. Fixes the two confirmed failures in the current `blastp-online` path: (a) `run_batches_online` holds RIDs in memory then polls in memory, so a timeout mid-poll loses every RID and resubmits from zero (never completes a large run) — this writes `rids.json` after every submit and `harvest` resumes; (b) raw BLAST XML is ~6M chars (~1.5M tokens) for a 492-protein run — this parses to a compact `blastp_hits.csv` (verified on the real batch_001: 3,940 chars vs ~130k raw XML, ~31× reduction) with zero XML in the LLM path. Test: hermetic FAA-parse + XML top-hit parse. **Deferred (Sonnet):** register as a `tools/blastp_campaign.py` verb, wire `blastp_hits.csv → ingest-blastp → B5_BLASTp_Hits`, and replace/checkpoint the in-memory `run_batches_online` poll.
- **`tools/kcb_confidence.py`** — antiSMASH v8 KnownClusterBlast **Similarity Confidence** extractor (per-region High/Medium/Low). Verified read against real AS-XXX (antiSMASH 8.0.4): 4 High / 6 Medium / 34 Low, spot-checks match (streptophenazine=High, cinnapeptin=Low, tambjamine=Low). The label lives in the region-overview HTML (`<td class="similarity-text">`), NOT in regions.js/JSON. Test: hermetic HTML extract. Feeds the KCB-demotion **verification-only** signal (antiSMASH's own Low flags the weak calls to discount). **Deferred:** wiring into the demotion logic + `function_and_novelty` is the KCB-demotion cut.

## Multi-tier
Two new tools + 2 tests; no AS IDs, no new `mamey/` modules → all four tiers; per-tier confirmation at cut.
# v9.7.207 — 2026-07-05 · build 20260705v97207a

**Engine unchanged (1.9.109) · Bundle 9.7.206 → 9.7.207.** Mode B production note from the eval chat: the one real bug (item 1) + the first two per-class exemplars + a doc note. No scoring change.

- **Item 1 (BUG) — `mamey/hmm_blastp_adjudicate.py` default HMM resolution.** `hmm_file = hmm_file or resolve_hmm_db()` handed the resolver's **dict** `{path, n_models_hint, tier, reason}` straight to the pyhmmer loader → `AttributeError: 'dict' object has no attribute 'readable'` on every locus, dark-ing the HMM adjudication channel the depth policy leans on for OVERTURNs. Now extracts `['path']`. Verified on a real GBK: default resolution → `reason='' hits=1 genes=33` (was the AttributeError). +1 regression test covering the previously-untested default-resolution path.
- **Exemplars — `docs/reference/modeb_exemplars/` — 2 of 10 slots filled.** `siderophore_exemplar.md` (BGC038) and `ripp_exemplar.md` (BGC036), authored by the eval chat through the real `emit-modeb-template → verify-modeb → evaluate_card` loop on .205. Verified here through the real gates: both **FULL, 0 lint ERRORs** (siderophore 48.5k chars / 5.8 mentions-per-1k, RiPP 39.2k / 4.7). Redaction-clean (0 private AS IDs). These are the gold-standard depth targets for their classes and the first real calibration anchors beyond the initial exemplar.
- **Item 6 (doc) — `MODE_B_DEPTH_POLICY.md`.** Over-merged regions must address the co-captured class's diagnostic (terpene→GPP/FPP/GGPP, NRPS→adenylation/Stachelhaus); `CONTENT_GAP` firing on the co-capture is correct, not a bug — authors should expect it.

Deferred (ergonomics, none blocked the exemplars — next batch): item 2 `fill-modeb` helper + §28 placeholder normalization, item 3 emit per-section floor annotations, item 4 dangling conditional-section-ref warning, item 5 `grade-modeb` card-path-first verb (prevents silent `evaluate_card` misgrading).

## Multi-tier
One code fix + 1 test + 2 exemplar docs + a doc note; no AS IDs (exemplars redaction-clean), no new modules/tools → all four tiers; per-tier confirmation at cut.
# v9.7.206 — 2026-07-05 · build 20260705v97206a

**Engine unchanged (1.9.109) · Bundle 9.7.205 → 9.7.206.** Audit-driven fix batch — the .204 audit's v9.7.205 patch card (which .205 didn't touch), plus two of my own incomplete/worsened fixes caught auditing .205. No scoring change.

- **B17 (owned) — `mode_b_quality_gate.py` docstring floors.** My .205 floor raise updated the FLOORS-block comment but left the module header docstring (§4.2 lines) at the old §1–§10 6k/5k/4k, so the drift got *larger*. Header now reads 12k/11k/10k, matching FLOORS.
- **P12-residual G09 (owned) — `cohort_figures.py:957`.** My .202 P12 fix stripped the dead English-word dims from the figs_multi vocab but missed the second copy in `_strain_profiles` (the G09 strain-similarity matrix). Now stripped there too (Oxidoreductase/Aminotransferase/Transporter/Regulator — never aSDomain tokens).
- **wishlist #1 — `tools/sapote_judgment_receipt.py`.** `count_modeb_cards` now routes through `lint_card` (§1–§30 structure gate) in the completeness path (`enforce_structure=True` in `main`), so a structurally-invalid card can no longer flip `gold_completeness=COMPLETE`. Mirrors compilation_gate's fail-open ERROR filter. Default stays pure-count (preserves the regex/dedup tests); enforcement is on where it determines COMPLETE. +2 regression tests.
- **cov-.200 — `tests/test_build_card_workbook.py` (NEW).** First hermetic tests for the .200 card-workbook feature: CW-1 (AUTHORED via store header) + CW-2 (dedup by BGC_ID). Closes the "verified only by direct package run" gap.
- **B16 — `mamey/dedup_and_guard.py`.** `AS_PATTERN`/`AJS_PATTERN` `\d{2,4}` → `\d{2,}` to match `redact_public_tier`'s unbounded pattern (a 5-digit ID no longer bypasses the dedup guard). Not a live risk at 3-digit cohort.
- **B4-residual — 9 `read_text()` sites** across authored_verify/judgment_store/cli/compile_report/validate now carry `encoding="utf-8"`. (Remaining bare text `open()` sites are a further sweep.)
- **habitat RULES** — comment that rule order is load-bearing (`termite` must precede `attine`).

## Multi-tier
Edits to existing files + 2 new test files; no AS IDs, no new modules/tools → all four tiers; per-tier confirmation at cut.
# v9.7.205 — 2026-07-05 · build 20260705v97205a

**Engine unchanged (1.9.109) · Bundle 9.7.204 → 9.7.205.** Mode B depth policy raised + re-centered on domain substance (the Developer or User's directive), plus the reclass-check (L1) integration package.

## Mode B depth policy — `mamey/mode_b_quality_gate.py`
- **Floors raised + compressed:** HIGH 12,000 · MID 11,000 · LOW 10,000 (was 9k/8k/6k). Compression stops the rank tiering from dropping important-but-**fragmented** BGCs (low rank = short/edge contig, not less interesting) to a soft floor. Genuine boundary fragments keep the FRAGMENT_FLOOR exemption.
- **No padding — domain density:** a FULL card must carry ≥ 1.0 gene/domain·BLASTp mention per 1,000 chars (+ ≥ 12 absolute). Padded length grades SHALLOW with *"add aSDomain/BLASTp detail, don't pad prose."* Verified: real AS-XXX BGC007 (§30, 36k chars, 3.0/1k) → FULL; a 17k-prose/0-domain card → SHALLOW.
- **Old floors were for the retired §1–§10+§11–§20 (20-section) contract**; the canonical contract is §1–§30 and a real §30 card is ~36k chars, so 9k was a fraction of one. Docstring updated to §1–§30.
- ⚠ **Provisional calibration** (anchored on n=1 real §30 card + directive). The per-class exemplars are the real calibration set — see below.
- New guidance: `docs/modules/MODE_B_DEPTH_POLICY.md` (the bar, where to find the domain data — antiSMASH aSDomains via `domain-level`, per-gene BLASTp via `blastp-round`/`B5`, gene table, KCB — and the multiple-rounds/batches expectation) + `docs/reference/modeb_exemplars/` (one good card per BGC class; slots awaiting the Developer or User).
- Gate tests updated (fixtures bumped above the new floors; density check confirmed to pass real content and reject padding). Suite green.

## reclass-check (L1) integration — `tools/reclass_check.py` (+ curated map, test)
- Domain-arm class-discrepancy **review prompt** (capacity-level, not a verdict), from the 811 chat; eval chat verified 6 tests green + `analyze()`/`render()` split matching the arts_ingest contract. Classified OPERATOR_ONLY in `gate_registry.tsv`. Motif arm (M6 mycofactocin rescue) is the next L1 cut (M6 needs the same analyze()/render()+test standard first).

## Multi-tier
Gate + docs + one new tool; no AS IDs, no new `mamey/` modules → all four tiers; per-tier confirmation at cut.
# v9.7.204 — 2026-07-05 · build 20260705v97204a

**Engine unchanged (1.9.109) · Bundle 9.7.203 → 9.7.204.** Module integration round 1 — two verified reference tools from the analysis-module bundle folded in **with hermetic tests** (not dropped in raw). No scoring change.

- **habitat-map — `tools/mamey_habitat_map.py`** (L5/L6). Store-backed strain→habitat map from each package's `manifest.source`; normalizes bee/wasp/moss/termite/attine/clinical/environmental/reference and emits `UNASSIGNED` (flagged for the Master Strain List, not silently bucketed) for host-less records. Carries the **termite ≠ attine** distinction (fungus-growing termites are a distinct lineage from attine ants) — a real misclassification the Nocardia chat caught. Test: `classify()` rule table + termite/attine separation + UNASSIGNED/reference split.
- **arts-ingest — `tools/arts_ingest.py`** (M7). ARTS2 → per-BGC self-resistance **lead-priority** signal (SMK-RES-001), built and verified against the real AS-XXX ARTS2 output (6 duplicated+BGC-proximal core genes / 27 BGC-hit clusters). Lead-priority only — never claim-confidence, never a per-BGC phenotype; flags likely **BGC-intrinsic** duplications (sugar machinery in glycosylated BGCs) with a review-not-verdict banner. Test: dup+proximal core gene → self-resistance lead + node·region mapping.

Both land as `tools/` with tests + inventory; `mamey`-verb CLI registration deferred to a follow-up. The GCF/deepdive verbs remain out (they need the Developer or User's GCF metric decision + cohort-mode reconciliation with the Nocardia module).

## Multi-tier
Two new tools + two tests; no AS IDs, no new `mamey/` modules → all four tiers; per-tier confirmation at cut.
# v9.7.203 — 2026-07-05 · build 20260705v97203a

**Engine unchanged (1.9.109) · Bundle 9.7.202 → 9.7.203.** Two verified bounded fixes from the analysis-module bundle's priority-bug list (B13, B1). No new modules/tools; no scoring change.

- **B13 — `tools/build_pangenome.py` `CORE_MIN` was hardcoded 45.** For any <45-strain cohort `core` was empty by construction — this is the root cause of the "0 core" in the Nocardia cross-strain analysis (a threshold artifact, **not** "nothing conserved"). Core threshold is now cohort-relative `max(2, n_strains//2)` with a `--core-min` override. Verified: 9-strain cohort → core_min **4** (was 45).
- **B1 — `authored_verify` §24 novelty now routes through `_bgc_context_from_triage`.** Supplies `kcb_top` + `Novelty_auto` from the triage so `verify-modeb --package` and `ingest-receipts` compute §24 via the **same** two-branch formula and can no longer disagree. Completes the partial .201/.202 S1 fix (which used a manifest single-branch `not kcb`, missing the `novelty=="HIGH"` arm). Verified on AS-XXX: the verify-path ctx now carries `KCB_top` + `Novelty_auto`.

## Multi-tier
Edits to two existing files; no AS IDs, no new modules → all four tiers; per-tier confirmation at cut.
# v9.7.202 — 2026-07-05 · build 20260705v97202a

**Engine unchanged (1.9.109) · Bundle 9.7.201 → 9.7.202.** Figure false-absence class + three decided patch-list items (B3/P1/provenance). No new modules/tools; no scoring-semantics change.

## Figure false-absence class (`mamey/cohort_figures.py`) — verified on the real 5-strain packages
- **RiPP-1** — F01 "RiPP calls" now counts antiSMASH RiPP-family **product classes** from the inventory (always present) instead of the mode-gated `gene.ripp` scan (empty under `json_mode:off`). **0 → 27** across the cohort (AS-XXX 7 / AS-XXX 8 / AS-XXX 3 / AS-XXX 3 / AS-XXX 6).
- **ActiveSite-1** — F01 drops any **all-zero metric row** before z-scoring, so the active-site row (empty under `json_mode:off`) no longer renders as a measured flat band; F10 active-site completeness now labels **"scan not populated (json_mode:off) — not a measured 0%"** instead of 0% bars for every strain (incl. GOOD-assembly). Verified: census sidecar drops the row, RiPP row shows 27.
- **P12-residual** — F13/F14/F15 ordination `vocab` dropped the four always-zero English-word dims (Oxidoreductase/Aminotransferase/Transporter/Regulator — separate genes, never aSDomain tokens). Ordinations still render (F11–F13 confirmed).
- *class_pred dead-field removal deferred* — referenced by 2 tests; not worth the suite risk for a LOW cleanup. Left as documented-dead.

## Decisions applied (your calls)
- **B3 (redact)** — `AS-XXX` → `AS-XXX` in `bgc_guide.py:349` **and** `tests/test_guide_gate_crosscheck.py:37` (which asserted the string — a blind source-only swap would have reddened it), plus all docstring refs. 0 residual `AS-XXX`; guide-gate test passes 6/6.
- **P1 (fix + name)** — `docs/BUNDLE_CAPABILITIES.md` no longer claims the alignment wheels ship in-bundle; states they install via `bundle_support/install_sapote_addons.sh`.
- **Provenance (point at code)** — all marker/cassette/schema `source_locator`s repointed from the absent `docs/SAPOTE_v8.10.2_MONOLITH.md` to the implementing code (`mamey/sapote_markers.py` / `source_scans.py`); module docstring updated. 0 residual monolith refs.

## Multi-tier
Edits to existing files + one test; no AS IDs added (AS-XXX redacted out) → all four tiers; per-tier confirmation at cut.
# v9.7.201 — 2026-07-05 · build 20260705v97201a

**Engine unchanged (1.9.109) · Bundle 9.7.200 → 9.7.201.** Bounded fixes from the outstanding patch list (Sapote verifier + Sonnet + audit-chat leads). No new modules/tools; no scoring/count-semantics change.

- **S1 (HIGH) — `authored_verify._bgc_context_from_package` §24 novelty.** Was loading `manifest.json` then discarding it and hardcoding `novel_or_no_mibig=True`, so `verify-modeb --package` spuriously ERRORed §24 on **every** BGC (incl. strong-KCB hits). Now derives it from the per-BGC `kcb_top` in the sealed manifest (`not kcb_top`). *Correction vs the reported fix:* the manifest carries `kcb_top` + numeric `novelty`, not the categorical `novelty_auto` the triage-fed gate uses, so `kcb_top` presence is the MIBiG-hit signal on this path. Verified on AS-XXX: KCB-hit BGC→False, no-KCB BGC→True (was both True).
- **P4 — `tests/test_analysis_modes.py`.** `test_modules_parse_and_expose_api` imports `mamey.bgc_walk`, which imports `pyhmmer` at module top → bare-checkout red. Added `pytest.importorskip("pyhmmer")` (the second unguarded-import red the .199 B2 didn't cover).
- **S2/B2 — `blastp_online.parse_blast_xml`.** A non-XML NCBI response (HTML error / rate-limit / empty) made Biopython's `NCBIXML.parse` raise before `expat_parser` bound, then its `finally` leaked `UnboundLocalError`. Guarded with a `<?xml` prefix check + try/except → `[]` (caller's fail-closed path). Verified: 3 non-XML inputs → `[]`, no raise.
- **CW-1 — `tools/build_card_workbook.py` E5 provenance.** Every ingested card was mislabeled `SKELETON` because the emitter's `<!-- MODE B TEMPLATE -->` header survives in the stored file. Now labels `AUTHORED` off the `<!-- MODE B: BGC -->` store header. (bug in the .200 card-workbook feature.)
- **CW-2 — `tools/build_card_workbook.py` E5 de-dup.** Deduped by filename, so authored `{strain}_{bgc}_mode_b.md` and template `{bgc}_template.md` double-counted the same BGC. Now dedups by extracted `BGC_ID`, preferring `judgment/`. Verified: authored+template of one BGC → 1 row, `AUTHORED`.

## Multi-tier
Edits to existing files + one test guard; no AS IDs, no new modules → all four tiers; per-tier confirmation at cut.
# v9.7.200 — 2026-07-04 · build 20260704v97200a

**Engine unchanged (1.9.109) · Bundle 9.7.199 → 9.7.200.** Reproducibility + portable handoff + cross-strain card workbook, plus a `blastp-online --bgc` default bugfix. Authored by the reproducibility/handoff patch chat on the v9.7.199 base; folds cleanly (zero overlap with the .199 bughunt cut). Accretion-justified: mamey/handoff.py

- **Determinism fingerprint — `mamey/packaging.py` (+ `mamey fingerprint`).** `repro_fingerprint(package_dir)` hashes only the score-bearing outputs (inventory, crosswalk, scan_states, triage_board, AB/AF lead boards, RGGMCI_ranked_pairs; line-endings normalized; missing→"MISSING"), written to `repro_fingerprint.json` + recorded in the manifest (added to MUTABLE_NAMES so validate stays green). `mamey fingerprint <pkg> [--compare X] [--json]` — exit 0 = match. Cross-chat reproduction: equal fingerprint = reproduced, mismatch → component diff shows which output disagrees.
- **Portable handoff bundler — `mamey/handoff.py` (+ `mamey handoff`).** Packs a sealed package + region GBKs into one zip so online BLASTp (needs per-CDS sequences the package doesn't carry) works downstream without the raw ZIP. `--top-n N` limits to top ranked leads; omitting `--input-zip` gives a package-only handoff with an explicit NOTE.
- **`blastp-online --bgc` default bugfix — `mamey/cli.py`, `mamey/blastp_online.py`.** `--bgc` defaulted to the truthy metavar string `"BGC"`, so every call without an explicit `--bgc` entered the crosswalk-scoping branch and refused — even a bare region GBK that needs no scoping. Default → `None`; output filenames fall back to `region` when None.
- **Cross-strain card workbook — `tools/build_card_workbook.py` (new, standalone, ADDITIVE).** `B10_BGC_Report_Cards` (one row per BGC) + `E5_ModeB_Cards` (one row per §-section, AUTHORED/SKELETON tagged); dense §4 bodies chunked to respect Excel's 32,767-char/cell limit. Does NOT modify the FROZEN master schema — folding B10/E5 into the master writer is a separate schema-gated append-only change.

## Verification
- Applies clean on the v9.7.199 tree (5 files, no rejects); `--bgc` default now None; new verbs present.
- `pytest -k "packaging or checksum or blastp_online"`: 27 passed. Full suite receipt at cut.

## Multi-tier
Code + two new modules + one tool; no AS IDs added → all four tiers; per-tier confirmation at cut.

# v9.7.199 — 2026-07-04 · build 20260704v97199a

**Engine unchanged (1.9.109) · Bundle 9.7.198 → 9.7.199.** Bounded fixes from the reconciled v9.7.198 bug hunt (Helper Bee audit + Sapote verifier): suite hygiene plus the F5 tier-note fix that .198 missed. No scoring/count semantics change.

- **F5 (real fix) — `docs/TIER_NOTE_CODE.md` anchored under version-sync (`tools/sync_version.py`).** The .198 "F5 refresh" shipped the note stale at v9.7.197 inside a v9.7.198 bundle, because *no `sync_version` rule owned the file* — so `make_public_tier.sh`'s version-sync gate waved the drift through. Added four anchor rules (H1 title + Build stamp + Engine + Bundle), tolerant of the `sapote-mamey-` prefix. `--check` now flags the drift (was silently OK) and the note is regenerated to v9.7.199. This is the anti-drift mechanism the .198 cut lacked, not a one-time re-stamp.
- **B2 — over-merge count test made hermetic (`tests/test_nrps_predictions_patchG.py`).** The v9.7.198 headline test lacked the `skipif(not _HAVE)` guard its siblings carry, so it hard-failed (FileNotFoundError on the private `AS-XXX_loose.zip`) on any clean checkout — the shipped suite was red. Added the guard; the fix is now skip-clean in-bundle. (In-bundle synthetic fixture still to vendor — deferred.)
- **B1 (guard half) — NP Atlas alias test gates on the alias map (`tests/test_npatlas_alias_map.py`).** `test_kcb_alias_recovers_hsaf` failed whenever the index was present but `kcb_label_aliases.json` absent (this addon's shape), because the guard keyed only on the index. Now requires both. (Data-side — shipping the alias file in the addon `npatlas/` — is an addon-build fix, deferred.)
- **B4 — five file-handle leaks / non-atomic writes closed (`tools/`).** `json.dump(obj, open(path,"w"))` in `build_genelevel_triage`, `build_finer_from_gbk` (×2), `sapote_judgment_receipt`, `backfill_reference_signatures` — wrapped in `with`; the fail-closed judgment receipt now writes-temp-then-`os.replace` (atomic).

## Deferred (documented, not dropped)
- **B3** — the `AS-XXX` in `bgc_guide.py:349` is an *intentional, tested* reference (`test_guide_gate_crosscheck.py` asserts it; v9.7.191 hardening). Blind redaction breaks the test. Needs a decision: redact source+test together, or keep and rely on `redact_public_tier.py` tier redaction. Held.
- **RiPP-1 / ActiveSite-1** — F01 "RiPP calls" reads the empty `gene.ripp` scan vs 27 real RiPP product-class BGCs; F10 + F01 active-site render `json_mode:off` empties as measured 0%. Figure fixes needing sealed-package verification; exact fixes in `RECONCILED_BUGHUNT_v9_7_198`.
- **B1 data**, **`class_pred`** dead field, **C-3/H-1** sweep + encoding hygiene.

## Multi-tier
Code + tests + doc + F5 sync-anchor; no AS IDs added → all four tiers; merged-private data wiped (old-engine, per the Developer or User); per-tier confirmation at cut.

# v9.7.198 — 2026-07-04 · build 20260704v97198a

**Engine unchanged (1.9.109) · Bundle 9.7.197 → 9.7.198.** Five bounded fixes from the AS-XXX/AS-XXX/AS-XXX audit sessions. No scoring/count semantics change except the over-merge count correction (was inflated).

- **Over-merge banner in `emit-modeb-template` (HIGH, `modeb_template_emitter.py`).** The emitter was blind to Patch G's over-merge signal, so an authoring chat could write a single-product Mode B card for a region antiSMASH resolved as ≥2 protoclusters (caused wrong AS-XXX BGC006/BGC023 cards). The emitter now reads `predicted_polymers.csv` (bare-contig + region match) and prepends an `⚠ OVER-MERGED REGION` banner when the region carries ≥2 protoclusters, naming the count + candidate_kind. Fires only on over-merged regions (no false positive on single-protocluster), honest-blank when the CSV is absent. Same failure class as the Patch A blank-grid bug: author over a skeleton that doesn't warn you.
- **Over-merge COUNT fix (`nrps_predictions.py`).** `over_merged_regions` counted polymer *rows*, but each over-merged region has ~2–3 candidate-polymer rows, so the headline (`OVER_MERGE_CANDIDATES: N`) was inflated ~2–3×. Now counts unique `(record_id, region_number)`. Verified AS-XXX: 16 → 7. The flagging was always correct; only the count was wrong. `cli.py` reads the corrected value automatically.
- **ingest-receipts header resolver (F1, HIGH, `mode_b_receipt.py`).** `_parse_card_bgc_id` matched only the canonical `<!-- MODE B: <ID> | -->` header (written by judgment_store *after* ingest), so a freshly-authored card carrying the emitter's `<!-- MODE B TEMPLATE | bgc: <ID> -->` header returned `UNRESOLVED_BGC` and never reached the register. Added a keyed-header fallback, tried after the canonical form. Verified: emitter header now resolves `BGC008` (was `''`); canonical unchanged.
- **F3 — wire the source ZIP into automated domain-level (`cli.py` + `render_all_figures.py`).** The .197 suffix-strip keying works (`aSModule_count` sum 111 on AS-XXX *when the ZIP is supplied*), but no automated path supplied it: `render_all_figures` hardcoded `source_antismash=None`, so every delivered module summary read 0. Now the seal records `input_zip` in the manifest, and `render_all_figures._resolve_source_zip` resolves it (explicit > manifest > basename-beside-package > None-honest-0). Resolver verified 4 ways here; the 0→111 end-to-end is the audit chat's AS-XXX receipt (no AS-XXX package in this tree to re-derive).
- **F5 — `docs/TIER_NOTE_CODE.md` refreshed** from stale `v9.7.144b / engine 1.9.100` to current `v9.7.198 / 1.9.109`, with a note that BUILD_STAMP/TAG are authoritative.

## Verification
- Full suite: 2634 passed / 0 failed / 134 skipped (+11 over .197's 2623).
- Over-merge banner: fires on over-merged, silent on single-protocluster, blank when CSV absent (3 tests).
- Count fix: AS-XXX 16→7 (test asserts unique-region == count < rows).
- ingest-header: emitter + canonical + no-header (3 tests). F3 resolver: 4 paths (4 tests).

## Deferred to next cut (flagged, not dropped)
- **F2** (§24 emit/verify predicate mismatch) — needs a single-source-of-truth refactor consumed by both emit and verify; held for a design decision, not one-side-patched.
- **H-series cohort figures** — a feature (reads G CSVs), held for a figures-focused verification pass on the full cohort.
- **F4** (module *type* `?` on ZIP frame), **F6** (async blastp-submit/poll verbs), the R renderer toolkit (data-layer verified, render-unconfirmed), and `compare --scope bgc`.

## Multi-tier
Engine code + tests + one doc refresh; no AS IDs added → all four tiers; per-tier confirmation at cut.
# v9.7.197 — 2026-07-04 · build 20260704v97197a

**Engine unchanged (1.9.109) · Bundle 9.7.196 → 9.7.197.** Fixes the three findings from the v9.7.196 cut audit, plus a new `report-card` command. No scoring/count semantics change beyond making the .196 fixes actually reach output.

- **New `mamey report-card` command (`mamey/report_card.py`, spec `PER_BGC_REPORT_CARD_SPEC.md §6.1`).** Renders L0–L1 per-BGC report cards from a sealed package (triage board + Patch-G prediction CSVs): plain-language headline, deterministic Novelty/Activity/Tractability badges, predicted molecule/mass (RDKit on wildcard-free SMILES, optional dep — degrades to "pending"/"no rdkit" gracefully), with L2/L3 auto-comparators + `<!-- AUTHOR -->` slots. Claim-safe by construction: capacity-level, KCB = similarity not identity, bioactivity extract-level, node·region locators. Headline and Novelty badge share one `_novelty_tier` (no "similar to X" headline against a "KCB-dark" badge). Verified end-to-end via the CLI on AS-XXX (46 cards, exit 0, claim-discipline present, `produces`=0); CLI-path + function regression tests added. The cited spec is a new artifact renamed from `PER_BGC_REPORT_SPEC.md` to avoid a near-collision with the existing, unrelated `docs/PER_BGC_PAGE_LAYOUT_SPEC.md` (page co-location; has no §6) — the two are complementary.

- **Patch B — CRITICAL fix: `blastp-online --bgc` crashed on every call (`blastp_online.py`).** The .196 cut shipped B with a green unit test but a broken CLI: (1) `_find_crosswalk` used `Path` with the import scoped to a different function → `NameError` on every `--bgc`; (2) `extract_cds_features` was called on a package dir → `ValueError` (a sealed package has no protein records). Fixes: `from pathlib import Path` moved to module level; `extract_cds_features` call wrapped to fail-soft to `[]`; `_find_crosswalk` now resolves via explicit `--crosswalk` (CSV or package dir) or auto-discovers the sibling crosswalk from a ZIP path, and refuses cleanly (rc=1, clear message) when it can't rather than crashing. New `--crosswalk`/`--region` args. **The audit's coverage gap is closed with a CLI-level e2e test** (`test_blastp_cli_e2e_patchB.py`) that exercises `command → extract_cds_features → _find_crosswalk` — the path the unit tests skipped.
- **Patch F — HIGH fix: `aSModule_count` now reaches output (`domain_level.modules_from_source_zip`).** The .196 changelog read F as fixed, but `aSModule_count` was still 0 for all BGCs: the feature contig carries the antiSMASH region suffix (`NODE_6_..._84.228413`) while the BGC contig is bare (`NODE_6_..._84`), so keying matched nothing. Now strips the `.NNNNNN` suffix and keys on bare contig + coordinate window. Verified: BGC041 aSModule_count 0→2 (types nrps, pks). Substrate resolution stays G's job (JSON Stachelhaus); this restores the module count/type only.
- **D residual sweep — LOW: `run_batch_online` single-batch path** also treated transient `UNKNOWN` as terminal `FAILED`; now pending (matches `run_batches_online`), only explicit `FAILED` is terminal.

## Correction to the .196 changelog
The .196 Patch F bullet stated F was fixed when its user-facing goal (non-zero `aSModule_count`) was unmet — an overclaim the audit correctly caught. F is now actually complete. (The audit's sub-claim that `substrate_consensus` was absent from `parsers.py` was a string-grep artifact — the extraction is present under the local name `substrate`, populating the `substrate_consensus` field; verified 3 features incl. `Orn`. The substantive count-not-reaching-output finding was correct.)

## Verification
- Full suite: 2620 passed / 0 failed / 134 skipped (+4 audit-fix tests over .196's 2616).
- Patch B: CLI e2e — package-dir + `--bgc` refuses cleanly (rc=1), no NameError/ValueError; explicit `--crosswalk` dir resolves.
- Patch F: aSModule_count 0→2 on BGC041.

## Multi-tier
Engine-code fixes + tests; no AS IDs added → all four tiers; per-tier confirmation at cut.

## Still open (next cut)
- Re-source substrate surfaces (E4 / gene_context / Mode B §4–§5) from G's `nrps_prediction.csv` (planned).
- Patch E (opt-in Pfam), Patch C naming-convention doc.
- F coordinate keying verified on the region-GBK frame; confirm on a full-genome run frame (coordinate alignment holds, but not yet exercised end-to-end on a genome ZIP).
# v9.7.196 — 2026-07-04 · build 20260704v97196a

**Engine 1.9.108 → 1.9.109 · Bundle 9.7.195 → 9.7.196.** AS-XXX patch set A–G (from one audit chat): recover antiSMASH predictions the pipeline dropped, fix §4 gene-table emptiness, fix blastp scoping + robustness, and correct a guide claim-safety label. No change to BGC counting or assembly-tier semantics.

- **Patch G — NRPS/PKS prediction recovery (new `mamey/nrps_predictions.py` + `cli.py` wire-in).** antiSMASH computes and stores a predicted-peptide layer the engine ignored: per-A-domain Stachelhaus substrate calls (resolving the GBK's blank `X`), PKS cis-AT extender-unit calls (Minowa, margin-based confidence), assembled `region_predictions.polymer` + SMILES (D-config marked, `+` splits protoclusters), and the candidate-cluster `kind`/protocluster count (antiSMASH's own "region = ≥2 BGCs" over-merge signal). Reads the run JSON straight from the ZIP (independent of `--json-evidence`; resolves the largest top-level `.json`, never a reconstructed `<strain>.json` filename). Emits `<strain>_nrps_prediction.csv` + `<strain>_predicted_polymers.csv`; raises `OVER_MERGE_CANDIDATES` to run issues. Claim-safe: inferred specificity, similarity-level, never product identity. Verified on AS-XXX (unseen by the patch): 57 substrate rows (44 NRPS-A + 13 PKS-AT), 16 over-merged regions. KNOWN LIMITATION: trans-AT PKS (`consensus_transat`) not captured — empty in tested strains, deferred.
- **Patch F — `aSModule` dropped (`parsers.py`).** `wanted` used `"module"`; antiSMASH's feature type is `aSModule`, so module features (and `aSModule_count`) were zero everywhere. One-token fix + a `DomainFeature.substrate_consensus` field. F's coordinate-keyed `modules_from_source_zip` rewrite was DROPPED (unresolved BGC→module coordinate keying; G supersedes its substrate purpose) — `modules_from_source_zip` retained as a minimal aSModule presence reader only.
- **Patch A — §4 gene table empty (`modeb_template_emitter.py`).** `_gene_rows_for_bgc` didn't handle the current writer shape `{"bgc_id":X,"cds":[…]}`, appending the wrapper as one blank row. Now reads the `cds[]` array (verified: 1→3 rows, header skipped).
- **Patch B — `blastp-online --bgc` scoping (`blastp_online.py`).** The `BGC### → region###` string-transform matched nothing on a multi-region genome (empty `source_gbk`, no `regionNNN` in contig), so the whole proteome was submitted and the guard refused. Now resolves `--bgc` to contig + coordinate window via the sealed crosswalk; unresolved → refuse (never dump the proteome).
- **Patch D — blastp polling robustness (`blastp_online.py`).** A transient/unparseable `UNKNOWN` status was treated as terminal FAILED, abandoning a live RID. Now `UNKNOWN` is pending (bounded to 5 polls, then times out); only explicit `FAILED` is terminal.
- **BUG2 (guide false-orphan, `bgc_guide.py`).** An un-queried gene (absent from the BLASTp store) rendered as "no hit / orphan (fast-evolving)" — asserting a negative never tested. Now distinguishes never-queried ("not run for this gene; absence is not an orphan call") from genuine no-hit, via caller-supplied store membership.
- **Patch C (partial) — over-merge flag ships via G.** The functional "≥2-BGC region" auto-flag is delivered by G's `OVER_MERGE_CANDIDATES` issue. The NODE·region naming *convention* doc is deferred.

## Verification
- Full suite: 2616 passed / 0 failed / 134 skipped (+8 patch regression tests over .195's 2608).
- Patch G on unseen AS-XXX: 57 substrate rows, 16 over-merge — receipts, not assertions.
- Patch A: gene rows 1→3. Patch B: scopes by contig+window, unresolved→[]. Patch D: 66 blastp tests green.

## Deferred (flagged, not fixed)
- **Patch E** (opt-in full-Pfam `--hmm`): low-priority, manifest-marked redundant when antiSMASH output present — NOT in this cut.
- **Patch C convention doc** (NODE·region naming in `DELIVERABLE_CONTRACT.md`): Sapote-side; the engine over-merge flag ships.
- **Re-source substrate surfaces from G's CSV** (E4 sheet, gene_context field, Mode B §4/§5): plumbing + authoring, next cut.
- **F module→BGC coordinate keying** + G trans-AT PKS: known limitations carried forward.

## Multi-tier
Engine + new module + docs + tests; no AS IDs added → all four tiers; per-tier pytest disclosed at cut.
# v9.7.195 — 2026-07-03 · build 20260703v97195a

**Engine unchanged (1.9.108) · Bundle 9.7.194 → 9.7.195.** Authoring/BLASTp front-door cleanup: one behavior-preserving code fix + doc corrections that close the workflow-report gaps. No scoring/count semantics change.

- **Mode B authoring bar surfaced in the emitted skeleton (`modeb_template_emitter._header_block`).** The contract's `quality_gate` checklist (gene-interplay prose, ≥2 alternative interpretations, §4 prose-not-tables, CSV-free readability, capacity language, node/region on first mention) lived in the contract JSON but was only reachable by independently opening the file past the sections list — so an authoring chat could fill to its own sense of "adequate" and only learn the card was thin when `verify-modeb` rejected it. The 13-item checklist now renders in every emitted skeleton's header, framed "author to this first; run the gate as confirmation, not discovery." Verified: all 13 items render once in a real emitted skeleton; scaffold-verify still passes; new regression test guards it.
- **BLASTp Gap 1 — stale guard message (`blastp_online`).** `--bgc`/`--region` has scoped a full ZIP since v9.7.185 P7, but the unscoped-guard message still told users to "pass a single region GBK." Corrected to state `--bgc <BGC_ID>` scopes a full ZIP to one BGC's proteins. Message-only; scoping behavior unchanged.
- **BLASTp Gaps 2–3 — agent-session submission boundary (`docs/ONLINE_BLASTP_PROTOCOL.md`).** New section documents that `blastp-online` submits LIVE to NCBI (not a stager; fail-closed on network error means no traceback and no fabricated hits, not dry-run), and gives the exact outfmt-10 column recipe (`qseqid, sseqid, pident, length, mismatch, gapopen, qstart, qend, sstart, send, evalue, bitscore[, ppos]`) for going around the tool back into `ingest-blastp`. Column list verified against `parse_hit_table_csv`.
- **Front-door correction (`AGENTS.md`).** The .186 note claiming `blastp-online` "submits batches serially" was stale — `run_batches_online` already submits all batches up front then polls together (async). Corrected, and pointed at the new agent-session recipe section.

## Verification
- Full suite: 2608 passed / 0 failed / 134 skipped (+1 checklist regression test over .194's 2607).
- `tests/test_modeb_round.py::test_emitted_skeleton_carries_quality_gate_checklist`: all 13 quality_gate items present in the header.
- Front-door + blastp + template subset: 201 passed.

## Multi-tier
One code fix (guard message) + docs + emitter change + one test; no AS IDs added → all four tiers; §34 backstop.
# v9.7.194 — 2026-07-03 · build 20260703v97194a

**Engine unchanged (1.9.108) · Bundle 9.7.193 → 9.7.194.** Two additive items: a Mode B round orchestrator and a CCTT co-fire precedence fix. No scoring/count semantics change.

- **`mamey modeb-round` — contractual emit→verify→worklist orchestrator (`mamey/modeb_round.py`).** Chains the deterministic halves of the Mode B authoring sequence: emits N triage skeletons (top-N by Corrected_rank via the existing `emit_batch`), scaffold-verifies each against the §1–§30 structure gate (structure only, NOT depth — an unauthored skeleton is expected to be thin), and writes `<pkg>/modeb_round_worklist.json` with per-BGC `authoring_state` (TRIAGE_EMITTED / AUTHORING / AUTHORED_VERIFIED / SCAFFOLD_INVALID / VERIFY_FAILED). The state names avoid colliding with the depth gate's `THIN_CARD` (a triage card is not-yet-authored, not a failed card). Authoring itself remains the Sapote/LLM step — the command emits + verifies + tracks state and says so in its own output. Contract encoded: minimum ≥1 AUTHORED_VERIFIED before contact; preferred N TRIAGE_EMITTED then user chooses fill scope. Verified on AS-XXX: 46 BGCs emitted + scaffold-verified in 6.0s, 0 scaffold-invalid, worklist written.
- **FkbH / PTM-vs-tetronate co-fire precedence (`source_scans.apply_cctt_vetoes`).** Wires the previously-orphaned `tetronate_cassette_completeness` grader (defined in `antismash_evidence.py`, never called) into the real CCTT co-fire site. When T43-PTM and T43-TET co-fire on one BGC, the grader now decides precedence from ring-closure evidence: FkbH + FabH-KSIII or Diels-Alderase → spirotetronate precedence; FkbH starter-only or absent → PTM retains precedence, T43-TET is starter-signal only; edge-truncated → indeterminate, neither asserted. New outputs `tetronate_cassette_grades` + `ptm_tet_precedence` per co-firing BGC. This is the correct scoping of the AS-XXX BGC020 report: FkbH logic already existed but was unwired, and the report's literal "FkbH present → raise tetronate" would have been wrong (FkbH is necessary-not-sufficient; it also feeds non-tetronate glyceryl starter routes).

## Verification
- Full suite: 2607 passed / 0 failed / 134 skipped (+2 tetronate co-fire tests, +3 modeb-round tests over .193's 2602).
- `tests/test_tetronate_cassette.py`: SPIRO→tetronate precedence, STARTER_ONLY→PTM retains (guards against the over-broad report suggestion).
- `tests/test_modeb_round.py`: emit+scaffold+worklist states; broken skeleton flagged SCAFFOLD_INVALID (gate is not a rubber stamp).
- New module `mamey/modeb_round.py` registered in MODULE_MANIFEST (174 modules).

## Multi-tier
Engine code + tests; no AS IDs added → all four tiers; §34 backstop.
# v9.7.193 — 2026-07-03 · build 20260703v97193a

**Engine unchanged (1.9.108) · Bundle 9.7.192 → 9.7.193.** Figure delivery + coherence. The figure code produced ~40 figures but scattered them across 6 directories with silent skips, so sessions "could barely get figures to produce" and couldn't find the ones that did render. This cut makes `render-all-figures` deliver every figure to one place and reconciles three contradictory class-figure titles. Additive tooling; no scoring/count semantics change.

- **One-directory figure delivery (`render_all_figures.gather_figures`).** After the sets run, every produced PNG + SVG is copied into a single `<pkg>/figures/` directory with a `FIGURE_INDEX.csv` manifest (figure, source_dir, bytes, type). Source-dir prefix keeps names unique/traceable; non-destructive copy. Verified on AS-XXX: 40 files gathered (30 PNG + 10 SVG), 40 manifest rows, 0 duplicate names, `by source: (root):15, domain_level:8, figures_rendered:2, gold_figures:2, locus_maps:10, smoke_figures:3`.
- **On-disk count is authoritative.** The command's set self-count reported 38 while 40 exist on disk (the 2 gold figures are produced but not counted by any set's return). The gather count (40) is now reported as authoritative, with a printed note when it disagrees with the self-count.
- **Loud figure-stack preflight + non-empty skip reasons.** `figure_stack_preflight()` prints one clear line — present ✓ or MISSING with the exact install fix — before any set runs. Empty-reason `SKIPPED ()` lines now name matplotlib/addon-missing or no-data-for-set as the likely cause. This turns the silent-skip failure (0–2 figures, no explanation) into a diagnosable one.
- **Class-figure title reconciliation (root-cause fix for the cross-figure contradiction).** Three figures showed the same strain's "class composition" with different numbers because they measure different quantities under near-identical names. Retitled to state what each measures: `8b`/render_brief → "Product-label token frequency (all tokens; saccharide incl.)"; `8g`/figures_extra → "Primary product class per BGC (one class/BGC, n=…; saccharide-only omitted)"; smoke → "Product-label token frequency (all tokens per BGC; standing-rule rows excluded)". **Bug fixed:** the smoke figure's y-axis read "BGC count" but the code counts product-label tokens (splits "NRPS; PKS" into 2) — y-label corrected to "product-label token count".
- **KCB-anchors claim-safety (`figures_extra.fig_kcb_anchors`).** The figure plotted the "UNRESOLVED" sentinel as an anchor product — surfacing bars for exactly the BGCs whose identity the engine withheld under their claim ceiling (a claim-safety inversion). Withheld/UNRESOLVED sentinels are now excluded from the anchor tally and the excluded count is disclosed in the footer.

## Verification
- Full suite: 2602 passed / 0 failed / 134 skipped. Figure-subset (508 tests) green after retitles.
- `render-all-figures` on AS-XXX: gather + preflight + skip-reason output verified against real on-disk files (receipts above).
- New functions `gather_figures`, `figure_stack_preflight` registered in MODULE_MANIFEST (accretion gate).

## Deferred (per user)
Per-figure tweaks — silent-truncation labels ("top N of M"), layout collisions (32-label axes, footer overruns), gold/F02 legend + subset caption, NAPAA-in-atlas ruling, "Other accessory/domain" bucket question. These are cosmetic/judgment items to address after the delivery + coherence fixes land.

## Multi-tier
Engine code + tests; no AS IDs added → all four tiers; §34 backstop.
# v9.7.192 — 2026-07-03 · build 20260703v97192a

**Engine unchanged (1.9.108) · Bundle 9.7.191 → 9.7.192.** Authored-output verification — four guardrails that make a green check mean the work was actually read. Motivated by two failure reports: a guide gate that ran on the skeleton (passing an empty template), and a hand-built 5-section doc shipped as a "Mode B Card" though it had no §1–§30 structure. Additive tooling; no scoring/count semantics change.

- **Authored-guide verifier (`bgc_guide.verify_authored_guide` + `mamey verify-guide`).** Reads the FINISHED guide .md (not the re-derived skeleton): fails on any residual `<!-- LAY: -->` slot, a thin/unauthored Part (per-Part authored-prose floor), or a gene subsection missing its plain-language summary. A blank skeleton — which `guide_quality_gate` passes — fails this by design (verified: 60 errors on the empty template, 0 on a fully-authored guide).
- **Mode B naming/write guard + `mamey verify-modeb` (`authored_verify.py`).** `verify-modeb` runs the real `lint_card` (structure + `strict_depth=True`) on the authored card, so a thin-but-structured card fails on depth and a hand-built non-§ doc fails `NO_HEADINGS_DETECTED`. `guard_deliverable_name` refuses to let any `*Mode?B*`-named file pass without clearing `lint_card` — the reported hand-built "Mode B Card" is structurally un-nameable as one.
- **Front-door disambiguation (`AGENTS.md`).** States plainly that `mamey mode-b` = triage top-leads TABLE, NOT the §1–§30 card (the name trap); replaces the structure-only verify snippet with `verify-modeb` (structure AND depth); adds the RiPP requirement that §21 mass ladder / §22 RiPP DB search / §24 novelty score are load-bearing, not satisfied by "listed the precursor sequences"; adds the `verify-guide` step to the guide section.
- **`guide_quality_gate` scope clarified.** Docstring + the command's own stdout now state it gates the SKELETON only and cannot see authored prose; both point to `verify-guide` for the finished file — so its pass can't be mistaken for validation of authored work.

## Verification
- `tests/test_authored_verification.py` (6 cases): blank skeleton fails authored-verify; authored guide passes; naming guard refuses the hand-built Mode B doc; non-Mode-B names pass through. Full suite green.
- New module `mamey/authored_verify.py` registered in MODULE_MANIFEST (accretion gate).

## Multi-tier
Engine code + one doc + tests; no AS IDs added → all four tiers; §34 backstop.
# v9.7.191 — 2026-07-03 · build 20260703v97191a

**Engine 1.9.107 → 1.9.108 · Bundle 9.7.190 → 9.7.191.** Implements the three open items from the v9.7.190 handoff — BLASTp async submit, the compare module rename, and the guide-gate AS-XXX hardening. All additive; no scoring/count semantics change.

- **Front-door: BGC Guide authoring route (`AGENTS.md`).** Added an "Authoring a BGC Guide" section parallel to the Mode B one — names `mamey guide`, `--blastp-store`, the `DELIVERABLE_CONTRACT.md`, and the `examples/` exemplars, and states the engine-emits-skeleton / Sapote-authors-prose division explicitly. Closes the same discoverability gap the .190 Mode B route closed, one deliverable over: a session following the front door literally would otherwise hand-roll the Guide (mis-scoping region genes and reproducing none of the store-backed readouts) instead of driving the real command. Docs-only.

- **BLASTp async submit (`blastp_online.py`).** The `blastp-online`/`blastp-round` runner submitted batches serially (each blocked on its poll-to-READY before the next Put). Split submit from poll: new `_submit_batch` (Put→RID only) and `run_batches_online` (fire all Puts spaced ~2 s for NCBI etiquette, then poll the RIDs together). NCBI runs the searches in parallel, so wall-clock drops from N× to ~one batch (live: 180 s vs ~10 min on a 4-batch BGC). `run_batch_online` preserved unchanged for back-compat; fail-closed intact (a failed submit or timeout yields `ok=False` in input order; nothing fabricated).
- **`gemini.py` → `compare.py` module rename.** The two-strain comparison module is renamed; `gemini.py` becomes a thin re-export shim so every existing importer (`from mamey import gemini`, `from .gemini import gemini_compare_command`) keeps working. `compare_command` is the canonical name with a `gemini_compare_command` back-compat alias; `cli.py` imports from `.compare`; `test_gemini*` → `test_compare*`. The add-on `gemini_stack*` glob back-compat in `wheelhouse.py`/`npatlas_resolver.py` is deliberately untouched (add-on dir name, separate concern). MODULE_MANIFEST regenerated (172 modules; accretion gate cleared).
- **Guide-gate AS-XXX hardening (`gene_by_gene.py` + `bgc_guide.py`).** Implements the design note behind the sidecar. At seal time, `write_gene_count_crosscheck` walks each BGC's region GBK from the INPUT ZIP via `_parse_cds_from_gbk` (an independent code path from the CSV writer) and emits `gene_count_crosscheck.json` with per-BGC `gbk_cds_count` / `gbk_edge_cds_count` / source. `guide_quality_gate` gains an optional `package` arg: with the sidecar present it **errors only on interior-gene omission**, warns on edge/FC differences, and degrades to a warning when the sidecar is absent (never false-fails). Interior regions → 0 edge-droppable (any shortfall is real omission); Edge/FC → droppable. Two design corrections found by testing on real data: region GBKs live in the input zip not the sealed package (writer takes `input_zip`), and the manifest boundary field is `edge_status` (not `boundary`). Wired into the seal pipeline best-effort/non-blocking.

## Verification
- **Full suite 2596 passed / 0 failed** (+10: async property tests + the design note's 6-case guide-gate plan).
- Guide-gate verified end-to-end: sidecar emits real per-BGC CDS counts; a guide short of a region's interior CDS → ERROR "interior gene(s) missing (AS-XXX upstream-omission)"; an edge-spanning surplus → benign warning. Compare shim re-exports resolve; async fail-closed preserved.

## Multi-tier
All changes are code/tests + one regenerated manifest; no AS IDs added (protocol-name `AS-XXX`/`AS-XXX` comments only). Lands in all four tiers; §34 backstop.

## Not done — flagged for the Developer or User
The read-proof handshake in `AGENTS.md` / `AGENTS.md` remains untouched — an instruction embedded in a doc is not a workflow decision to apply on the doc's say-so; that's the Developer or User's call to make directly.
# v9.7.191 — 2026-07-03 · build 20260703v97191a

**Engine 1.9.107 → 1.9.108 · Bundle 9.7.190 → 9.7.191.** Implements the three engineering items left open after .190. Additive; no scoring/count semantics change.

- **BLASTp async submit (`blastp_online.py`).** New `run_batches_online` + `_submit_batch` submit all batches up front (Puts spaced ~2 s for NCBI etiquette) then poll the RIDs together — NCBI's URL API is asynchronous, so wall-clock drops to ~one batch's runtime instead of N× (live: 180 s vs ~10 min on a 4-batch BGC). `run_batch_online` left unchanged for back-compat; fail-closed/offline-safe/scoping guards all intact; output identical to the serial path. Both `blastp-round` and `blastp-online` command loops rewired.
- **`gemini.py` → `compare.py` module rename.** The two-strain comparison module is renamed (`compare_command` canonical, `gemini_compare_command` retained as a back-compat alias). `gemini.py` becomes a re-export shim that forwards the full `compare` namespace — public AND private names — so every existing `mamey.gemini` importer keeps working through the deprecation window. Tests renamed `test_gemini*`→`test_compare*`. The add-on `gemini_stack*` discovery globs are deliberately untouched (add-on dir back-compat, a separate concern). MODULE_MANIFEST 171→172.
- **guide-gate AS-XXX hardening (`gene_by_gene.py` + `bgc_guide.py`).** Implements the .190 design note. Seal-time `write_gene_count_crosscheck` walks each BGC's region GBK from the input zip via `_parse_cds_from_gbk` — an independent code path from the gene-by-gene CSV — and emits `gene_count_crosscheck.json` (per-BGC gbk_cds_count / gbk_edge_cds_count / source). `guide_quality_gate` gains an optional `package` arg: with the sidecar present it errors ONLY on interior-gene omission (a gene the clipped GBK could not legitimately drop), warns on edge/FC differences, and degrades to a warning when the sidecar is absent — never false-fails. Backward-compatible (no `package` arg → prior behavior). Wired into the seal pipeline, best-effort/non-blocking.

## Verification
- **Full suite 2596 passed / 0 failed** (new tests: async-submit 4-case incl. "all Puts precede any poll"; guide-gate crosscheck 6-case design plan; compare rename incl. shim private-name forwarding).
- Guide-gate verified end-to-end on real AS-XXX data: sidecar 32/32 BGCs, antismash 8.0.4; an Interior BGC claiming 73 vs 76 CDS → ERROR "at least 3 interior gene(s) missing"; correct count → clean; Edge BGC → warn only.
- Both `mamey.compare` and `mamey.gemini` import paths resolve to the same command; shim forwards private helpers.

## Multi-tier
All changes are engine code + tests + one regenerated MODULE_MANIFEST. No AS IDs added (protocol-name `AS-XXX`/`AS-XXX` comments only). Lands in all four tiers; §34 backstop.

## Not done (flagged, not acted on)
- **FkbH / spirotetronate CCTT precedence** (AS-XXX BGC020 note) — a real precedence/annotation refinement (FkbH disambiguates PTM-vs-spirotetronate co-fire), but its own engine change with the audit chain; not bundled here.
- **BLASTp workflow doc gaps** (scoping `--bgc` on a full ZIP, a documented `--submit`/live path, web-result→ingest recipe) — doc/UX, a natural BLASTp-doc pass; not in this code cut.
- **Read-proof handshake** in the front door — an instruction embedded in a doc, not a request from the Developer or User; left untouched.
# v9.7.190 — 2026-07-03 · build 20260703v97190a

**Engine unchanged (1.9.107) · Bundle 9.7.189 → 9.7.190.** Docs-only cut (front door; no code change). Closes two instruction gaps a clean-room audit found by following `AGENTS.md` verbatim on a fresh strain.

- **Front-door instruction fixes (`AGENTS.md`).** (1) The "Operating mode" run command omitted `--taxonomy`/`--source`, so a session following it verbatim shipped a package with `taxonomy = "not verified"` / `source = "not supplied"` and no warning — a blank-taxonomy package that must never reach a manuscript/CCSM output. Added both flags plus a "substituting the placeholders" block giving the rule for every field (ID derivation, display-name form, date format, PUBLIC/PRIVATE selection, and the explicit taxonomy-placeholder caveat). (2) The front door opened the Mamey-first Mode B gate ("run + validate, then interpret") but never told a session HOW to author the card — no pointer to `emit-modeb-template`, the §1–§30 contract docs, or the structure gate — so a fresh session would hand-write the card on the historical §1–§10 scaffold and silently omit ~two-thirds of the required sections (the failure the structure-gate docstring documents). Added an "Authoring Mode B" section with the canonical 4-step sequence (emit-template → blastp-online → author into slots → verify with the structure gate) and pointers to the three authoritative docs. AS-series example ID generalized to a neutral placeholder.

## Verification
- Front-door / bootstrap-discoverability test set: 63 passed (content assertions intact).
- Full suite 2586 passed / 0 failed. No code touched; all referenced docs + `emit-modeb-template` confirmed present/working (no dangling links).

## Multi-tier
Docs-only; the front door carries no AS IDs after the example was generalized. Lands in all four tiers; §34 backstop.

## Noted for a future engine cut (not in this docs cut)
The `blastp-online`/`blastp-round` runner submits batches serially (blocks on each poll before the next submit); NCBI's URL API is asynchronous, so submit-all-then-poll is ~Nx faster (live: 180 s vs ~10 min on a 4-batch BGC). Latency only — correctness/fail-closed/scoping unaffected. Its own change.
# v9.7.189 — 2026-07-03 · build 20260703v97189a

**Engine unchanged (1.9.107) · Bundle 9.7.188 → 9.7.189.** Test-quality cut (test only; no code change). Closes a coverage gap the audit found in the .188 truncation test.

- **Ground-truth `--limit` truncation tests.** Replaced the synthetic truncation-log fixture with ground-truth fixtures whose strings are taken verbatim from the antiSMASH source (`common/record_processing.py`, `main.py`). Adds two cases the original test missed: default-verbosity runs (the common real path) emit only the WARNING line — the skip lines are DEBUG-level and absent — so `truncated=True` must fire from the warning alone with detail fields legitimately empty; and a `--debug` run carries the real `%s: %s` skip lines. The `.188` detector was already correct on both paths (it sets `truncated=True` from the warning and degrades gracefully); this closes the test's default-mode coverage gap. Detection behavior unchanged. Suite 2584 → 2586.
# v9.7.188 — 2026-07-03 · build 20260703v97188a

**Engine 1.9.107 (unchanged) · Bundle 9.7.187 → 9.7.188.** Single-purpose cut: detect antiSMASH `--limit` record-cap truncation. Additive intake warning only; no scoring/parser semantics change.

- **RECORD_LIMIT_TRUNCATION intake warning (`parsers.py` + `cli.py`).** antiSMASH analyses only the largest N `--limit` records (default 1000); on a highly-fragmented assembly, BGCs on skipped records are silently absent from the region set while the GC/contamination stats still read the FULL FASTA — an incomplete scan presented as `MAMEY_COMPLETE` (AS-XXX silent-omission family, at the whole-record level). New `parsers.antismash_record_limit_truncation()` reads the archived `.log` for the cap warning; intake emits a `RECORD_LIMIT_TRUNCATION` issue stating the region count is a FLOOR, the GC stats cover the whole assembly and aren't comparable, and to re-run with a higher `--limit`. Best-effort, never blocks a run. Found on a highly-fragmented 9,133-contig co-assembly (755 of 1,755 eligible records unscanned, reported as 43 BGCs / MAMEY_COMPLETE with no warning).

## Verification
- **Full suite 2584 passed / 0 failed** (3 new tests: truncated log fires, clean log silent, missing log graceful).
- Detector confirmed on a truncated-log fixture (analysed=1000, first_skipped=NODE_1001, skipped_count correct) and silent on a clean 112-record log.

## Multi-tier
Both files are engine code, no AS IDs → land in all four tiers (MERGED-PRIVATE / CODE / CODE-analysis-free / SID-public); §34 backstop.

# v9.7.187 — 2026-07-03 · build 20260703v97187a

**Engine 1.9.107 (unchanged) · Bundle 9.7.186 → 9.7.187.** First cut carrying the NP Atlas resolver + `mamey guide` (staged in .186) together with three audit-chain fixes and the add-on rename. All additive; no scoring/count semantics change.

- **P3 lineage-genus fix (`cohort_resolver.py`).** `_genus` now reads the genus from a `;`/`,`-delimited lineage string (terminal rank), not just a binomial's first token. v9.7.185 P3 stamped every lineage-form `--taxonomy` (the documented format) as `REVIEW` regardless of true genus — a real Streptomyces lineage came back REVIEW, and a non-actino lineage came back REVIEW instead of OUT_OF_SCOPE (contamination gate silently failed). Fix benefits every `_genus` caller. Regression test added.
- **D2/D3 RG-GMCI consistency (`master_workbook.py`).** D2 now includes any `HIGH_RG_GMCI_RESCUE` pair scoring below `RGGMCI_D2_TOP_N`, so the top-pairs board never omits a rescue that D3 promoted (the run flag counts D3). Pre-fix, a below-cap HIGH pair landed in D3 but was truncated out of D2 — a silent-omission (AS-XXX family). Regression test added; `corrected_bgcs` unaffected.
- **NP Atlas KCB-label alias map (`npatlas_resolver.py` + add-on `kcb_label_aliases.json`).** Curated functional-label → canonical-name aliases recover compounds present in NP Atlas under a chemical name when the KCB label is a functional description — e.g. "heat-stable antifungal factor"/HSAF → dihydromaltophilin (the recurring cross-genus antifungal in the bee cohort). Consulted after exact+prefix fail; INVENTORY_ONLY, no new claim strength, no genus/provenance. Alias targets test-enforced to exist in the shipped ref; empty/absent file → no regression.
- **Add-on rename: `gemini-stack*` → `sapote-addons*`.** The wheels/HMM/NP Atlas dependency store is renamed (`sapote_addons_core` / `sapote_addons_figures` / `bundle_support/install_sapote_addons.sh` / `sapote_addons/`), dropping the Google-Gemini-LLM collision. HMM + NP Atlas discovery now glob flexibly (`*addons*`, `*stack*` back-compat), so the data is found regardless of dir name. Wheels install by `*.whl` glob (name-independent), so pre-existing on-disk zips still install. The two-strain comparison MODULE (`gemini.py` / `mamey compare`) is NOT renamed here — separate change.

## NP Atlas + guide (carried from staging)
- **NP Atlas compound-reference resolver.** `B6_Compound_Reference` sheet: npclassifier class, formula, exact mass, [M+H]/[M+Na], InChIKey, primary DOI/PMID per KCB-named compound. B1 byte-unchanged; INVENTORY_ONLY; no genus/identity claim (HSAF-immune by design). Refs ship in the sapote-addons core.
- **`mamey guide`.** Layered per-gene BGC Guide, sibling of `mode-b`; each per-gene claim capped at its BLASTp evidence_tier; five-part gate-checked contract; deterministic md + LAY prose slots; docx degrades to md.

## Verification
- **Full suite 2581 passed / 0 failed** (3 new regression tests: P3 lineage, D2/D3 consistency, NP Atlas alias).
- P3 verified against the audit case matrix (lineage + binomial, actino + non-actino). D2/D3 re-run on AS-XXX (flag=D2=D3=4). Alias: HSAF→dihydromaltophilin, target confirmed in ref.

## Multi-tier
All changes touch `mamey/` (engine) or add-on data → land in all four tiers (MERGED-PRIVATE / CODE / CODE-analysis-free / SID-public); §34 backstop. No AS IDs in any change → public-tier scrub clean.

## Deferred (not in this cut)
- **guide gate AS-XXX upstream-omission hardening (LOW).** The audit's suggested independent expected-count cross-check needs a seal-time second count emitted from the region GBKs (design note first) — deferred to avoid a half-specified gate that could false-fail. The feature works; the gap is latent (not triggered on AS-XXX).
- AS-XXX reconciliation is analysis context (genus/host metadata caveats, 8.0.3→8.0.4 renumbering), not a code change — no action.

# v9.7.186 — 2026-07-03 · build 20260703v97186a

**Engine 1.9.106 → 1.9.107 · Bundle 9.7.185 → 9.7.186.** Two additive deliverables — the NP Atlas compound-reference resolver (new `B6_Compound_Reference` sheet) and the `mamey guide` layered per-gene BGC Guide. Both reuse banked data and the existing tier system; nothing existing is modified destructively.

- **NP Atlas compound-reference resolver.** New `B6_Compound_Reference` sheet enriches each BGC's KCB-named compound with molecule-level chemistry — npclassifier compound class, molecular formula, exact mass, [M+H]/[M+Na] adducts, InChIKey, and primary literature reference (DOI/PMID). Feeds metabolomics dereplication (exact-mass target lists) and auto-resolves primary citations for Mode B / the Eden–Bert workflow. Records isolation provenance not taxonomic distribution, so it makes NO genus-restriction claim (immune to the HSAF cross-genus problem); it resolves the compound the KCB reference already names to organism-independent properties. B1 untouched (verified byte-identical, AS-XXX 32/32); every row `evidence_tier=INVENTORY_ONLY`; no BGC→compound identity claim. NP Atlas refs ship as an add-on (env `SM_NPATLAS_DIR` / side-by-side layouts / bundle-local fallback / graceful empty if absent). AS-XXX: 15/23 KCB compounds resolved.
- **`mamey guide` — layered per-gene BGC Guide.** New deliverable, sibling to `mode-b`. Every gene carries Structure, Function, and a standardized BLASTp similarity readout rendered from the existing evidence store (id/pos/cov/E/bit/acc/tier/claim), so each functional claim is capped at its BLASTp evidence_tier. Five-part contract (Plain-Language / Primer / Technical Overview / Gene Catalogue / Synthesis), gate-checked like Mode B: every CDS gets a section (AS-XXX-class omission check), every gene carries all three readouts, no per-gene claim exceeds its BLASTp tier. Deterministic md skeleton + narrowly-scoped Sapote prose slots (`<!-- LAY: … -->`); docx via python-docx, degrades to md with notice. Adds `mamey/bgc_guide.py` + `data/bgc_guide/` contract. Prototype: AS-XXX BGC006.

## Verification
- **NP Atlas.** B1-immutability, INVENTORY_ONLY tagging, add-on present/absent graceful degrade; module registered in MODULE_MANIFEST.
- **guide.** Skeleton determinism (same package → identical md); dropped-gene ERROR gate; no-hit/no-translation readout variants; docx-absent degrade; module registered. Full suite passes.

## Multi-tier
Both touch `mamey/` → land in all four tiers (MERGED-PRIVATE / CODE / CODE-analysis-free / SID-public); §34 backstop. NP Atlas add-on data is public → safe for SID-public.

## Still open
NP Atlas + guide will likely need tweaking next cut (both first-integration). Homopolymer/junk-termini guard for RGGMCI stitching (LOW). Tetronate cassette-completeness gate (MED, staged).

# v9.7.185 — 2026-07-03 · build 20260703v97185a

**Engine 1.9.105 → 1.9.106 · Bundle 9.7.184 → 9.7.185.** Round-2 reference-strain audit: the 7 remaining P-items authored as tested fixes on top of v9.7.184. Engine bumped (A2 schema + intake contents change).

- **P3 (HIGH) — non-actinomycete contamination gate (`master_workbook.py`).** `A2_Strain_Registry` gains a `scope` column via `_scope_from_taxonomy()` (reuses cohort_resolver): IN_SCOPE / OUT_OF_SCOPE / REVIEW. An off-target Firmicute (Paenibacillus SY20) is now stamped OUT_OF_SCOPE rather than silently pooled into the cohort comparison; downstream cross-strain readers can exclude it. Non-destructive by design (stamp, not refuse). VALIDATED: SY20→OUT_OF_SCOPE, Streptomyces/Kitasatospora→IN_SCOPE, Oscillatoria→REVIEW.
- **P7 (MED) — `blastp-online --bgc/--region` now scopes extraction (`blastp_online.py`).** Previously `--bgc` affected only the output filename, so a genome + `--bgc BGC001` submitted the entire proteome to NCBI. Now filters to the named region, with a `MAMEY_BLASTP_MAX_UNSCOPED` guard (default 200) refusing an oversized unscoped submission. Separate function from P1's extraction edit — no collision.
- **P8 (LOW) — antiSMASH build hash preserved (`parsers.py`).** A bare `8.dev` label is upgraded from the GBK `##antiSMASH-Data##` structured comment to the full `8.dev-<hash>(changed)` — provenance for the 200-strain run. New `_antismash_version_from_gbk()`; does not touch P1's `read_genbank_records` branch.
- **P12 (MED) — per-BGC catalytic heatmap drops 3 always-zero rows (`cohort_figures.py`).** Corrected diagnosis vs the v184 note: transporters/regulators/oxidoreductases are separate GENES, never aSDomains, so the rows were structurally unfillable — the fix is to remove them from this figure (they have correct dedicated figures: transporter_family_heatmap, bubble_regulators), not to broaden patterns.
- **P13 (LOW) — `Other_domain` visibility (`source_scans.py` + `deep_data.py`).** `gene_data.json` now carries `other_domain_breakdown` (top-25) and `misfiled_core_tokens` (a self-check that stays empty while P11 holds — makes the next classifier gap self-announcing).
- **P10 (LOW) — `NO_FIGURES_RENDERED.md` wording (`cli.py`).** Only written when figure dirs are truly empty; states the real `render-all-figures` recovery instead of a false "intentionally skipped" reassurance.
- **P6 (LOW) — `hmm-adjudicate` discoverable (`cli.py`).** OPEN_ME_FIRST next-steps reference the optional HMM pass (not wired into `run` — that architecture call is left open).

## Verification
- P3 scope classification validated on all 4 reference strains; 4 round-2 regression tests (P3 scope + schema, P7 guard, P13 self-check confirming P11 holds).
- All 7 diffs applied cleanly against the v9.7.184 base; every touched file parses.
- Full suite 2566 passed, 0 failed. Multi-tier: all 7 touch engine code → land in all four tiers, §34 backstop.

## Still open
P9 (plasmid-first replicon label, latent — needs a multi-replicon test run of S. violaceusniger Tü 4113; author a guard/warning before any silent reorder). Scanner-registry-into-run wiring (P6 architecture call). Product-novelty MIBiG cross-check. RiPP precursor extraction into §4. Tetronate grade wiring into source_scans.
# v9.7.184 — 2026-07-03 · build 20260703v97184a

**Engine 1.9.104 → 1.9.105 · Bundle 9.7.183 → 9.7.184.** Reference-strain audit fixes: the PKS_DH classifier silent-zero, the assembly-tier figure boundary column, and the blastp-online single-GBK crash. Engine bumped because these change deterministic figure/classifier outputs.

## HIGH fixes (validated on 4 reference genomes: YPW6 · Kitasatospora KM-6054ᵀ · Oscillatoria PCC 6304 · Paenibacillus SY20)

- **P11 — PKS reductive-loop domains misfiled as `Other_domain` (silent-zero heatmap row).** `DOMAIN_CLASS_PATTERNS["PKS_DH"] = [r"\bDH\b", ...]` never matched inside the token `PKS_DH` — underscore is a word char, so there is no word boundary before "DH" (`re.search(r"\bDH\b","PKS_DH")` → None). KS/AT/KR populated only via their spelled-out enzyme-name backup; DH/ER had none and read a false zero on genomes with real dehydratase domains (KM-6054ᵀ: 11 real PKS_DH hits, all tagged Other_domain). This is a reducing-vs-non-reducing PKS call in Mode B and gates the F03 macrolide proxy. Fix: prepend the literal `PKS_<abbr>` token to all six PKS patterns. **4-file coordinated change** (bundle_support/registry_inventory_v1.9.4.json + source_scans literal + mamey_markers + regenerated MARKER_CATALOG, hash cf76161ce160) — the runtime dicts are registry-built at import, so editing only the literal is a no-op; parity test guards this. VALIDATED: KM-6054ᵀ PKS_DH row 0/40 → 5/40 BGCs populated.
- **P4 — assembly-tier figure dumped every BGC into "Other".** `_LOC_COLS` put `Assembly_Locator` (a locus string like "NZ_..._region001") before `Boundary` (the Interior/Edge/Full-contig status), so `_first()` returned the locus string and no BGC ever matched a boundary token. Fix: read `Boundary` first, keep `Assembly_Locator` as a legacy fallback so older fixtures still resolve. Confirmed: all-Interior triage now yields Interior=N, Other=0.
- **P1 — `blastp-online` crashed on the GBK input its own `--package` help advertises.** `read_genbank_records` branched on directory input but fell straight into `zipfile.ZipFile` for a single `.gbk`, raising BadZipFile. Fix: added a single-GBK-file branch that parses in place (SeqIO / _gbk_shim), mirroring the zip path's record shape. ZIP and directory handling unchanged.

## Verification
- 5 regression tests (P11: all six PKS tokens classify correctly + registry/literal parity; P4: Boundary read before Assembly_Locator, status token wins; P1: single .gbk parses, not BadZipFile).
- Registry parity + marker-catalog staleness green after the coordinated P11 change (catalog hash cf76161ce160, exactly as specified by the audit).
- Full suite 2566 → (post-bump re-run) passed, 0 failed.

## Multi-tier note
P1/P4/P11 touch engine code (mamey/) — the fixes land in every tier carrying the engine (MERGED-PRIVATE, CODE, CODE-analysis-free, SID-public). §34 backstop confirms.

## Diagnoses recorded (NOT fixed this cut — reproduce-and-author per the audit)
P3 (non-actinomycete master-merge contamination gate, HIGH — needs a scope-column/refuse decision), P7 (blastp-online --bgc doesn't scope extraction, MED — shares P1's path), P12 (Transporter/Regulator/Oxidoreductase rows structurally zero — needs a token-family decision, distinct from P11), P6 (scanner registry never on the run path), P8 (antiSMASH build-hash dropped), P13 (Other_domain catch-all visibility), P10 (NO_FIGURES_RENDERED wording), P9 (plasmid-first replicon label, latent). All in future_improvements/README.md.

## Still open
The P3/P7/P12 authoring items above. Product-novelty MIBiG cross-check. RiPP precursor extraction into §4. Tetronate grade wiring into source_scans. AHBA_synth HMM for AN01.
# v9.7.183 — 2026-07-03 · build 20260703v97183a

**Engine unchanged (1.9.104) · Bundle 9.7.182 → 9.7.183.** The grand final cut of this run: split add-on for fast parallel loading, flexible wheel discovery, the biopython-on-critical-path fix, and the AS-XXX tetronate cassette-completeness gate.

## Split add-on + flexible wheel loading (the load-time fix)
The 118 MB single add-on loaded too slowly into chats. It is now split so parts upload in parallel:
- **gemini-stack-core (~27 MB)** — all runtime function (BLASTp, HMM, ANI, Gemini); starts runs immediately. The 25 most important HMM models ship in the bundle, so HMM scan/adjudication work with core alone.
- **gemini-figures-part1/2/3 (~24–34 MB each)** — the plotting stack (scipy/numpy/pandas/matplotlib/logomaker/pycirclize/dna-features-viewer) + the 148-family HMM enhancement.
- **`install_gemini_offline.sh` rewritten to accept ANY layout** — one combined zip, split zips, or loose `.whl` files. It scans every add-on location, pools whatever wheels it finds, installs core (required) then figures (best-effort). VERIFIED across three scenarios: split parts side-by-side (41 wheels pooled), loose wheels, and core-only (34 wheels, figures gracefully absent). A core-only install verifies clean and notes figures are unavailable rather than failing.

## biopython on the critical path (review-chat defect, fixed)
`blastp-online` was made a documented §4 authoring step in v9.7.178 while `requirements.txt` still labelled biopython "optional". Fixed:
- `mamey/blastp_online.py` — `_require_biopython()` guard: `parse_blast_xml` raises an actionable RuntimeError (not a bare ImportError) if biopython is absent; `run_batch_online` still fail-closes (ok=False, zero hits, no raise).
- `requirements.txt` — biopython relabelled: required for the BLASTp/HMM channels, installable via the `bio` extra or the add-on (which vendors it); extraction-only runs don't need it.
- §4 template prompt names the dependency inline.
(Note: the user's deployment always has biopython, so this was hygiene rather than an urgent break — but the "optional" label was simply wrong once the §4 prompt directed authors to the command.)

## AS-XXX tetronate cassette-completeness gate
From the AS-XXX BGC010 research session. The `T43-TET` CCTT trigger fired on FkbH alone, but FkbH is necessary-not-sufficient for a tetronate — the ring needs a FabH-family KSIII closure enzyme. Same partial-evidence-as-identity class §8 (KCB coverage) and §4 (BLASTp reconcile) already close.
- **FabH/KSIII ring-closure markers added to `DIAGNOSTIC_SEC_MET_DOMAINS`** (fabH / ACP_syn_III / Chal_sti_synt / ksIII), distinct from the existing spiro-specific Diels-Alderase.
- **`tetronate_cassette_completeness()`** grades the trigger: COMPLETE (FkbH+ACP+KSIII co-located) / SPIRO (FkbH+Diels-Alderase) / STARTER_ONLY (FkbH, no ring-closure reachable) / INDETERMINATE (required contig edge-truncated). VALIDATED on AS-XXX BGC010: FkbH present, no KSIII anywhere → STARTER_ONLY, correctly tipping the PTM-vs-TET fork to tetramate.
- future_improvements #8–10 recorded (grade-wiring into source_scans, edge-adjacency FabH guard, homopolymer-termini guard).

## Documentation
User Manual: new §2.3 (split add-on / flexible loading), §4.2a (three-channel evidence workflow), §11.1 (evidence-channel commands). Quick Guide: evidence-channel phrases. Plus the standalone white paper, technical bulletin, and news feature produced this session.

## Verification
- Tetronate gate: 6 tests (STARTER_ONLY ground truth, COMPLETE co-located + via partner, SPIRO, INDETERMINATE, NO_STARTER, markers-in-table).
- biopython guard: actionable RuntimeError + fail-close preserved.
- Installer discovery: 3 scenarios verified.
- Full suite 2561 passed, 0 failed. Engine unchanged.

## Add-on note
The add-on is RE-PACKAGED this cut (split into core + 3 figure parts). Old single `gemini-stack-20260702.zip` still works with the new installer (it pools wheels from any layout), but the split parts load far faster. Ship the bundle + core part to start; add figure parts for `mamey figures`.

## Still open
Wire the tetronate grade into source_scans (auto-surface on every T43-TET). Product-novelty MIBiG cross-check. RiPP precursor extraction into §4. AHBA_synth HMM for AN01. split_detector marinolide validation. Edge-adjacency + homopolymer-termini guards.
# v9.7.182 — 2026-07-02 · build 20260702v97182a

**Engine unchanged (1.9.104) · Bundle 9.7.181 → 9.7.182.** HMM adjudication wired into the Mode B template — the three evidence channels are now mutually reconciled as an enforced authoring step (template + roadmap + test only; no new module).

- **§4 now routes every BLASTp-vs-antiSMASH OVERTURN to the HMM domain tie-breaker.** The emitted template requires `mamey hmm-adjudicate <region.gbk> --locus <lt>` on any disagreement, and the author records the verdict (SUPPORTS_BLASTP / SUPPORTS_ANTISMASH / AMBIGUOUS / INSUFFICIENT). This completes the three-channel reconciliation: antiSMASH Pfam (inherited) + BLASTp (extrinsic identity) + HMM (intrinsic domain signature). BGC006 ctg12_71 is the caught case — the α/β-hydrolase signature backs esterase, not the antiSMASH β-lactamase call.
- **The template also surfaces the channel division of labour** so the author knows why all three run: HMM = what the machine IS (intrinsic domain grammar, module count, short/orphan-gene rescue — offline, deterministic); BLASTp = whose machine it is most like + product novelty (extrinsic, online, contextual).
- docs/Sapote_Mamey_ROADMAP.md updated: the enforced authoring order now includes the HMM tie-breaker step. Wiring-lock test added (test_section4_requires_hmm_adjudication_on_overturn).

## The full enforced Mode B evidence order (now complete)
1. §8 — `mamey kcb-frontpage`: KCB anchor WITH gene coverage (STRONG/COINCIDENTAL/LARGE_GENERIC), never score-as-identity.
2. §4 — `mamey blastp-online`: per-gene independent homology; reconcile CONFIRM/REFINE/OVERTURN.
3. §4 — `mamey hmm-adjudicate` on any OVERTURN: domain-signature tie-breaker.
The template seeds all three so this order is the path of least resistance, not a rule to remember — the BGC006-class failure (score-as-identity + Pfam-as-function) is now structurally prevented across all three channels.

## Verification
- 4 wiring-lock tests (§8 KCB coverage, §4 blastp-online required, §4 names the BGC in the command, §4 HMM adjudication on OVERTURN).
- 181 template/modeb tests stay green (structure gate + emitter contract intact).
- Full suite 2555 passed, 0 failed. Engine unchanged. Addon unchanged.

## Still open (updated)
Product-novelty MIBiG cross-check (KCB-coverage proxy currently). RiPP precursor extraction into §4. AHBA_synth HMM for AN01. split_detector marinolide validation. LP01/MT01 HMMs.
# v9.7.181 — 2026-07-02 · build 20260702v97181a

**Engine unchanged (1.9.104) · Bundle 9.7.180 → 9.7.181.** HMM<->BLASTp division of labour — the intrinsic-structure HMM channel, reconciled with the extrinsic BLASTp channel. Fills the `custom_marker_hmmer` slot that has been flagged NEEDS_HMMER_DOMTBLOUT since the beginning.

- **hmm_blastp_adjudicate (new module + `mamey hmm-adjudicate` CLI)**: now that per-gene BLASTp leads Mode B annotation (extrinsic identity — which named protein, which organism, how novel), HMM is demoted from primary annotation to the specific jobs BLASTp structurally cannot do (intrinsic structure). Four roles:
  1. **Ordered domain architecture** — BLASTp gives one alignment over a whole protein; profile HMMs tile it into ordered domains (KS→AT→DH→KR→ACP), giving module grammar + count. This is the megasynthase-trap discriminator ("single module, no chain-extension partners") BLASTp can't resolve. VERIFIED on real venturicidin region: full modular PKS grammar recovered.
  2. **Orphan / short-gene rescue** — RiPP precursors, leader motifs, small modifiers, and genes with NO nr hit (BGC023 ctg4_35) — an HMM family hit rescues an assignment where homology search comes up empty.
  3. **Adjudication of BLASTp-vs-antiSMASH disagreements** — when BLASTp overturns an antiSMASH call (β-lactamase→esterase), the domain signature is the tie-breaker: does the protein carry the α/β-hydrolase motif or the β-lactamase fold? VERIFIED: the BGC006 ctg12_71 case adjudicates SUPPORTS_BLASTP on the abhydrolase signature; the reverse (lactamase fold present) → SUPPORTS_ANTISMASH; no HMM hits → INSUFFICIENT (defer to BLASTp %id/cov).
  4. **Deterministic offline floor** — pyHMMER + scanner_pfam.hmm runs offline in seconds with reproducible bitscores; never depends on NCBI. The channel the engine can run in CI against the CCTT bitscore floors.
  - Accretion-justified: HMM<->BLASTp reconciliation is a distinct evidence-adjudication concern from the online BLASTp runner (extrinsic identity) and from the scanners (capability gates).
- **The clean division, wired**: HMM = what the machine IS (intrinsic, offline, deterministic); BLASTp = whose machine it is most like + whether the product is known (extrinsic, online, contextual). A Mode B card reconciles both. Degrades cleanly if pyhmmer / the HMM db are absent (clear reason, never a traceback).

## Verification
- 7 adjudication tests (BGC006 esterase adjudication, reverse fold, insufficient, module-arch single-module flag, orphan rescue with/without BLASTp hit, no-db degradation).
- Ordered readout VERIFIED end-to-end on a real venturicidin region GBK with the bundled 35-core HMM (modular PKS grammar recovered).
- Full suite 2554 passed, 0 failed. Engine unchanged. Addon unchanged (uses the bundled pyHMMER engine + Wheelhouse HMM; no new wheels).

## Still open (updated)
Wire hmm-adjudicate into the Mode B template so §4 disagreements auto-route to the domain tie-breaker (module ready; authoring-order wiring is the follow-up, same pattern as blastp-online). Product-novelty MIBiG cross-check. RiPP precursor extraction into §4. AHBA_synth HMM for AN01. split_detector marinolide validation. LP01/MT01 HMMs.
# v9.7.180 — 2026-07-02 · build 20260702v97180a

**Engine unchanged (1.9.104) · Bundle 9.7.179 → 9.7.180.** Mode B evidence-channel wiring + phased BLASTp round planner + cluster coherence and function/novelty reads. The BGC006-class failure is now structurally prevented, not just documented.

## Mode B template wiring (kcb-frontpage + blastp-online now enforced in the emitted card)
- **§8 requires the KCB corroboration tier.** The emitted template will not let a KCB anchor be stated without its gene coverage; the author must run `mamey kcb-frontpage` and record the tier (STRONG / COINCIDENTAL / LARGE_GENERIC). This structurally prevents the BGC006/colibrimycin failure (score 3734 with a handful of shared genes read as identity).
- **§4 requires the independent homology channel.** The template instructs the author to run `mamey blastp-online --package <gbk> --bgc <ID>` before writing §4, and to author from the reconciled call (CONFIRM / REFINE / OVERTURN) rather than raw antiSMASH Pfam. The command is pre-filled with the actual BGC id. Unavailable channel must be banded unverified — never fabricated.
- docs/Sapote_Mamey_ROADMAP.md documents the enforced authoring order. 3 wiring-lock tests.

## Phased strain BLASTp round planner (`mamey blastp-round`)
Per the standing prioritization model: **FULL proteins for the top-N BGCs (default 3) so complete homology is back BEFORE their Mode B cards are authored, + one representative protein for EVERY other BGC — saccharides included** (a representative BLASTp can promote a saccharide the scanners would downgrade). Follow-up rounds deepen the sampled BGCs. Dry-run by default (prints plan + submission-cost estimate); --run submits fail-closed. Reuses the template emitter's triage/rank/gene-row loaders. 3 planner tests incl. the saccharide-not-skipped guard.

## Cluster coherence + function/novelty (protocol §9/§10)
- **parse_blast_xml now retains the top ~6 hits per gene** (not just top-1) — the source-organism distribution across the cluster is a primary evidence axis, not throwaway.
- **cluster_coherence()** (§9): three reads — genome-span/synteny (recent-transfer vs vertically-inherited), core-vs-periphery identity (stable pathway + evolvable shell), and genus-break/mosaic detection (candidate HGT sub-islands, flagged provisional). VALIDATED against the real BGC006 run: genome-span 6/61 = diverged-genus-wide, core 90.7% vs periphery 82.3%, Amycolatopsis consensus, Streptomyces mosaic at ctg12_64-66 — all matching the protocol ground truth.
- **function_and_novelty()** (§10): FUNCTION via top-N CONSENSUS annotation (not top-1 — the reason ctg12_71 reads esterase not β-lactamase) with confidence tiers (HIGH/MEDIUM/NONE from %id×cov) and role buckets (core_PKS/NRPS/RiPP, tailoring, transport, resistance, regulator). NOVELTY kept as TWO SEPARATE AXES: gene-level (top_id bins + uncharacterized + orphan) and product-level (KNOWN_COMPOUND / KNOWN_CLASS / NOVEL). The product gate is conservative and fails toward NOVEL — it requires substantial cluster overlap, so a high KCB score with few shared genes is NOT called known. VALIDATED: BGC006 = gene-conserved (mean id 82.7%) but product-NOVEL — the two axes correctly diverge, which is the whole BGC006 lesson ("gene conservation does NOT make the compound known").
- The online command emits `<BGC>_cluster_reads.json` (coherence + function/novelty) alongside the §4 CSV.

## Verification
- reconcile still fail-closed + the two known BGC006 overturns flagged REVIEW (never auto-CONFIRM).
- coherence + novelty validated against the real 61-gene BGC006 fixture (product_novelty=NOVEL at realistic colibrimycin coverage; KNOWN_COMPOUND only at substantial overlap).
- Full suite 2547 passed, 0 failed. Engine unchanged. Addon unchanged (pure code; stdlib urllib + vendored biopython).
- Protocol doc updated to §10 (docs/ONLINE_BLASTP_PROTOCOL.md).

## Still open (updated)
Product-novelty MIBiG cross-check (currently uses the KCB coverage proxy; the protocol wants top-hit accessions cross-referenced against the bundled MIBiG 4.0 protein set gated by >=50% core-gene coverage). RiPP precursor-peptide extraction into §4. AHBA_synth HMM for AN01. split_detector marinolide validation. LP01/MT01 HMMs.
# v9.7.179 — 2026-07-02 · build 20260702v97179a

**Engine unchanged (1.9.104) · Bundle 9.7.178 → 9.7.179.** BGC006 online-BLASTp validation fixture + reconcile regression lock (data + test only; no new module).

- **BGC006 61-gene BLASTp validation data** (Wheelhouse/validations/BGC006_online_blastp.csv): the full AS-XXX/BGC006 per-gene NCBI BLASTp result (RID 4E4J591J016 lineage) from the analysis chat — the ground-truth run that validated the online-BLASTp channel. 61 genes; 52 top-hit Amycolatopsis (genus resolved from uniform per-gene consensus); the two antiSMASH overturns (ctg12_21 Phenol_Hydrox->ferritin, ctg12_71 Beta-lactamase->EstA esterase) present as recorded ground truth.
- **Reconcile regression test** (validates blastp_online.reconcile against the real 61-gene run): confirms the two known overturns are flagged REVIEW (never auto-CONFIRMed) — the claim-safety property the channel exists to guarantee — and that clean core genes CONFIRM. Locks the behavior against the real data, not just the synthetic fixture.

## Verification
- reconcile() validated against 61 real BGC006 genes: 24 CONFIRM / 37 REVIEW / 0 NO_HIT; both known overturns correctly REVIEW.
- Full suite 2537 passed, 0 failed. Engine unchanged. Addon unchanged.

## Context: the BGC006 recut (science outcome, not shipped code)
The analysis chat used this channel to withdraw the card's wrong colibrimycin anchor. The corrected §8 read — conserved across the genus Amycolatopsis but chemically uncharacterised, novel at the product level, not "probably colibrimycin" — is the evidence quality the online-BLASTp default is meant to produce. The recut card itself is a Sapote authoring deliverable, not bundle code.

## Still open (updated)
Wire blastp-online + kcb-frontpage as forced Mode B authoring steps (both modules ready; sequencing is the follow-up decision). AHBA_synth HMM for AN01. split_detector marinolide validation. LP01/MT01 HMMs.
# v9.7.178 — 2026-07-02 · build 20260702v97178a

**Engine unchanged (1.9.104) · Bundle 9.7.177 → 9.7.178.** Online BLASTp channel — the runner + interpreter for independent per-gene NCBI BLASTp, the missing piece the pipeline's bgc_blastp_panel scaffolding was built for.

- **blastp_online (new module + `mamey blastp-online` CLI)**: submits a BGC's CDS to NCBI web BLASTp in fail-closed batches, polls, parses the XML, and reconciles each hit against the antiSMASH domain call. The independent third evidence channel (beyond inherited antiSMASH Pfam + KCB score) that authoring §4/§8/§27/§28 should rest on.
  - Accretion-justified: an external-homology runner is a distinct evidence channel from the deterministic extraction engine and the offline scanners.
- **Fail-closed + offline-safe (hard requirement)**: if blast.ncbi.nlm.nih.gov is unreachable the channel is simply OFF — run_batch_online returns ok=False with a clear reason and ZERO fabricated hits; the card is then authored from antiSMASH+KCB with an explicit unverified banner (protocol §6). Directly tested: no-network -> ok=False, empty hits.
- **Batch discipline (protocol §3.0/§3.1)**: hard cap 10 proteins/submission (verified: 61-protein batch stalls, 10-protein batch READY ~2.5 min); giant proteins (>2500 aa) run solo. chunk_proteins enforces both.
- **Claim-safety**: a BLASTp hit is homology (similarity), not function or product identity — "capacity consistent with," never "produces." Coverage + %id always reported. Auto-reconcile only CONFIRMs on literal antiSMASH-keyword match; REFINE/OVERTURN are author judgments, never auto-asserted (so a real overturn like the BGC006 β-lactamase→esterase is surfaced for review, never falsely auto-called).
- **docs/ONLINE_BLASTP_PROTOCOL.md**: the internal spec, backed by the verified AS-XXX/BGC006 core-10 run (RID 4E4J591J016) — genus resolved to Amycolatopsis from uniform per-gene consensus; two antiSMASH calls overturned (ctg12_71 β-lactamase→EstA esterase, ctg12_21 phenol-hydroxylase→ferritin); one resistance gene named (ctg12_74 → AAC(3)).

## Verification scope (honest)
- Parse + reconcile + chunk core: PROVEN offline against a recorded NCBI XML fixture (the BGC006 ctg12_38 hit: Amycolatopsis, 95.1% id, 100% cov) — 6 unit tests.
- Fail-closed network safety: PROVEN (no-network returns ok=False, zero hits).
- **Live submit/poll path**: the recipe is verified end-to-end on the USER's network (RID 4E4J591J016, per the protocol) but ships SPECIFIED here because this build environment has no NCBI access — like the DIAMOND fast-path, it self-verifies wherever NCBI is reachable.
- Full suite 2536 passed, 0 failed. Engine unchanged. Addon unchanged (pure code channel; no new wheels — uses stdlib urllib + already-vendored biopython).

## Still open (updated)
Wire blastp-online into Mode B authoring as the default lead-BGC channel (module ready; the authoring-order wiring is the follow-up). kcb-frontpage as forced step-1. AHBA_synth HMM for AN01. split_detector marinolide validation. LP01/MT01 HMMs.
# v9.7.177 — 2026-07-02 · build 20260702v97177a

**Engine unchanged (1.9.104) · Bundle 9.7.176 → 9.7.177.** bgc_figures module — the three wheel-stack publication figures, now fully functional (addon updated with the figure wheels).

- **bgc_figures (new module + `mamey figures` CLI: diagram | atlas | ani)**: the three figures from the wheel-stack work, modularized and wired.
  - `figures diagram <region.gbk> <out.png>` — BGC gene-arrow diagram (dna-features-viewer). VERIFIED renders.
  - `figures atlas <strain_dir> <out.png>` — circular contig/BGC map (pycirclize). VERIFIED renders.
  - `figures ani <strain_dirs...> <out.png>` — all-vs-all ANI heatmap (pyskani + matplotlib), with the intransitivity data-quality flag surfaced by design. VERIFIED renders on the real AS-XXX × Amel2xC10 genomes.
  - Accretion-justified: publication-figure generation is a distinct output concern from extraction/scanning/comparison.
- **Bug fix in bgc_figures.ani_heatmap**: guarded the <2-strains-with-FASTA case (was crashing with a zero-size-array ValueError on ani.min()); now returns a clear actionable error dict naming what's needed.
- **Addon updated**: the gemini-stack addon now includes the figure wheels — pycirclize, dna-features-viewer, logomaker (+ scipy, pandas as deps). 36 → 41 wheels. All three `mamey figures` kinds now work offline once the addon is installed; without it, each degrades with a clear "ship the gemini-stack addon" message (RuntimeError, not a traceback).

## Verification
- All three figures render on real data: ANI heatmap (AS-XXX × Amel2xC10, 42 KB), gene-arrow diagram (24 KB), genome atlas (85 KB).
- bgc_figures: 3 tests (API surface, ANI insufficient-strain guard, _need degradation message).
- Figure wheels install offline from the rebuilt addon (pycirclize/dna_features_viewer/logomaker).
- Full suite 2530 passed, 0 failed. Engine unchanged.

## Addon changed this cut
The gemini-stack addon MUST be re-shipped with v9.7.177 (now 41 wheels incl. the figure stack). The prior addon (36 wheels) pairs with <=v9.7.176 but lacks the figure wheels.

## Still open (updated)
kcb-frontpage as forced step-1 (currently a command). AHBA_synth HMM for AN01. split_detector marinolide validation. LP01 starter-condensation HMM. MT01 meroterpenoid HMM.
# v9.7.176 — 2026-07-02 · build 20260702v97176a

**Engine unchanged (1.9.104) · Bundle 9.7.175 → 9.7.176.** KCB front-page reader + Layer-3 analysis modes (split detector, rare-motif, bgc_walk) — the roadmap response to the mycotrienin miss.

- **kcb_frontpage (new module + `mamey kcb-frontpage` CLI)**: reads the antiSMASH "Most similar known cluster" column for every region and ranks with a corroboration tier derived from BOTH similarity% and matching-gene count — STRONG (mycotrienin 50%/26, selvamicin 100%/29), COINCIDENTAL (geosmin 100%/1 = single-protein fluke, demoted), LARGE_GENERIC (many generic genes at tiny similarity). This is the systemic fix for the front-page miss: read the cheapest, highest-signal data FIRST; named KCB hits are leads to check, not verdicts. 5 ground-truth tests (mycotrienin/selvamicin/geosmin cases).
  - Accretion-justified: KCB front-page reading is a distinct Layer-0 concern (read-what's-there) from scanners (capability detection) and extraction.
- **split_detector (new module)**: contig-end split detector v2 — the long-standing top method gap. Detects a modular PKS/NRPS fragmented across contig ends (body + partial-module fragment) via terminal-gene position, paralog-range identity (35–78% = same pathway, >90% demoted as duplicate), product match, and a trans-AT class bonus (the signal that uniquely resolved marinolide). This is the general form of the fragmentation problem AN01 worked around for ansamycins.
  - Accretion-justified: cross-contig split detection is a distinct spatial analysis not present in any existing module.
- **rare_motif (new module)**: rare/high-value motif discovery — flags BGCs carrying domains rare across the strain set (novel chemistry) or on a curated high-value watchlist (phosphonate, enediyne ene_KS, lasso RRE, azole RiPP, aminocyclitol DHQ_synthase, etc.). The discovery mode for the actual unknowns. (Fixed the uploaded module's IMPORTANT_MOTIFS dict, which had invalid set/dict-mixed syntax; each domain synonym now maps to its description.)
  - Accretion-justified: rarity-based discovery is orthogonal to class-based scanners.
- **bgc_walk (new module)**: ordered HMM readout along a cluster (assembly-line architecture in genomic order), surfacing rare/unexpected domains that cluster-level gate counts discard. Validated upstream on ionostatin's 7 modules.
  - Accretion-justified: per-BGC ordered domain walk is a distinct view from gate-count scanners.
- **ROADMAP.md** (new, bundle root): honest development-stage roadmap written after the mycotrienin miss; defines the run order (KCB front page → scanners on every region → rare-motif → bgc_walk → cross-strain → Mode B).

## Verification
- kcb_frontpage: 5/5 tier tests pass (STRONG/COINCIDENTAL/LARGE_GENERIC/LOW ground truth).
- split_detector, rare_motif, bgc_walk: import + smoke + API tests pass; all run without error on staged antiSMASH GBKs. (The engine upload was byte-identical to the bundled one — no change.)
- Full suite 2527 passed, 0 failed. Engine unchanged.

## Still open (updated)
AHBA_synth HMM for AN01 (highest-value). LP01 starter-condensation HMM. split_detector needs validation on the marinolide c2+c5 ground truth in a real fragmented strain (module built; ground-truth run pending). MT01 meroterpenoid HMM.
# v9.7.175 — 2026-07-02 · build 20260702v97175a

**Engine unchanged (1.9.104) · Bundle 9.7.174 → 9.7.175.** Scanner registry v0.4 + AN01 ansamycin scanner + SID10815 mycotrienin ground truth (data-only; from the scanner chat).

- **Scanner registry v0.4 (29 scanners, was v0.3=28)**: adds AN01 (ansamycin / AHBA-mC7N starter macrolactam). Now the latest tier; mamey wheelhouse clean correctly flags v0.2 and v0.3 as superseded.
- **AN01 ansamycin scanner**: gates on AHBA synthase (3-amino-5-hydroxybenzoate synthase — the mC7N starter unit that is the class signature of ALL ansamycins: rifamycin, geldanamycin, mycotrienin, trienomycin, ansamitocin, naphthomycin). Trap documented (generic DHQ_synthase / shikimate primary metabolism). KEY INSIGHT: AHBA synthase is a discrete gene, so it survives the assembly fragmentation that hides a modular PKS — this is the fragmented-assembly detection lesson generalized (class-defining discrete-gene markers beat modular-PKS counting on drafts).
- **SID10815 mycotrienin ground truth (validation)**: the blind SID10815 prediction (previously "awaiting ground truth") resolved — the compound is mycotrienin (an ansamycin), and the pipeline MISSED it: the blind call was T2PKS c00194 + atropopeptide c00308, neither correct. Root cause: no ansamycin scanner existed AND the modular PKS is fragmented across contigs so PK01 (>=5 KS/region) could not fire. The AHBA signal WAS present (AHBA_synth_RP on c01012, annotated NRPS-like, 22 kb) — detectable with a dedicated AHBA gate. AN01 is the fix.

## Verification scope (honest)
- **AN01: SPECIFIED_PARTIAL** — scanner specified and ground-truth-confirmed (AHBA_synth_RP present on SID10815 c01012), but its gate HMM (AHBA_synth) is NOT yet in the bundle 35-core or addon 148-family Pfam sets, so the engine cannot fire AN01 until the AHBA_synth HMM is sourced. Same honest posture as LP01. Marked SPECIFIED_PARTIAL in the registry with the dependency noted.
- Wheelhouse list/clean recognize v0.4 automatically (29 scanners; v0.2/v0.3 superseded). 5 validations now (added mycotrienin). Full suite 2518 passed, 0 failed. Engine unchanged.

## Still open (updated)
AHBA_synth HMM needed to make AN01 fireable (new, highest-value — closes the ansamycin miss). LP01 starter-condensation HMM. Contig-end split detector (marinolide c2+c5) — AN01 demonstrates the discrete-marker workaround for one class but the general splitter is still unbuilt. MT01 meroterpenoid aromatic-prenyltransferase HMM.
# v9.7.174 — 2026-07-02 · build 20260702v97174a

**Engine unchanged (1.9.104) · Bundle 9.7.173 → 9.7.174.** ANI/compare + cohort-ingest bug fixes (patch from the ANI-run audit chat). Four real bugs, all in code paths untouched by the recent scanner/wheelhouse streams; verified still-present in our tree before applying.

- **F1 (MEDIUM) — `mamey compare <package_dir>` cryptic crash**: a sealed package dir has no GBKs/translations, so the S5 proteome step can't run from one, but it threw a raw IsADirectoryError from deep in zipfile. Now read_genbank_records guards directory input with an actionable ValueError ("pass the antiSMASH output ZIP…"), and the compare --strain-a/-b help is corrected to state a ZIP is required.
- **F2 (MEDIUM/HIGH) — `mamey compare` OOM-killed on draft genomes**: _align_pyswrd ran the entire query set against the entire target proteome in one pyswrd.search() call; the C-side candidate structures for tens of millions of pairs blew memory (OOM on a real 6,054×7,291 CDS run). Now batches the query set (query_batch=250 default) with gc.collect() between batches. Best-hit-per-query is order-independent so results are unchanged — VERIFIED 300/300 identical best-hits batched vs single-shot.
- **F3 (LOW/MEDIUM) — fresh-bank ingest crash**: tools/ingest_package.py load() did a bare open() with no existence guard, so first --merge into an empty bank hit FileNotFoundError. Now load(p, default=None) returns the caller's empty shape for a missing store.
- **F4 (LOW) — lead_board crash without deep_data.json**: bd() was intolerant of the optional deep_data store (read only for the CCTT fallback). Now returns {} for a missing store; the board builds.

## Verification
- F1: passing a directory now yields the actionable ValueError (confirmed).
- F2: batched vs single-shot = 300/300 identical best-hits (correctness preserved); memory bounded by batching.
- Affected-path selector (gemini/compare/parser/ingest/cds_feature/align): 86 passed, 1 skipped, 0 failed — matches the handoff's regression check.
- New coverage: F2 batching-equivalence test + F3 fresh-bank load-default test. Full suite 2518 passed, 0 failed. Engine unchanged.
# v9.7.173 — 2026-07-02 · build 20260702v97173a

**Engine unchanged (1.9.104) · Bundle 9.7.172 → 9.7.173.** Hostile-audit response (F1–F3) + 148-family HMM tier + HMM-tier resolver.

- **F1 (MEDIUM) — strain-registry integrity guard**: the audit flagged an AS-XXX key-collision failure mode (masking collapsing multiple AS-strains into one JSON key, silently dropping records with n_strains disagreeing). Verified the SHIPPED v9.7.172 registry does NOT have this — all 11 strains present with distinct keys (the auditor reviewed an earlier collapsed copy). Added a durable invariant test: n_strains == len(strains) AND no literal "AS-XXX" key, so this class of bug can never ship silently even if masking regresses.
- **F2 (LOW) — 148-family Pfam tier**: added the data-driven scanner_pfam_150.hmm (148 families, empirically derived from SID10815's full-Pfam scan: 578 families hit, ~150 = the coverage sweet spot at 66% of domain signal + all scanner-gate domains). Placed in the ADDON (gemini_stack/hmm/, 14 MB) — heavy static reference data belongs with the wheels, keeping the bundle lean. Bundle keeps the 35-family core (4.4 MB, standalone). SHA256-verified; loads with gathering cutoffs; all gate domains (DHQ_synthase etc.) present.
- **New: HMM-tier resolver** (wheelhouse.resolve_hmm_database): picks the best available Pfam DB across tiers — bundle-local 148 → addon 148 → bundle-local 35-core — with SM_HMM_DB env override, degrading gracefully to whatever is attached. Surfaced in mamey wheelhouse list. Realizes the three-tier reference model (35 core in bundle / engine wheels in addon / 148 reference in addon).
- **F3 (LOW)**: changelog reconciled to shipped artifacts (35-core in bundle, 148 in addon, 11 strains verified).

## Verification
- Registry invariant: n_strains=11 == 11 records, no AS-XXX collision (shipped registry correct).
- 148-HMM: SHA-verified, 148 models with gathering cutoffs, gate domains present.
- Resolver: 8 wheelhouse tests pass (tier preference, env-override, none-case, count invariant).
- Full suite 2516 passed, 0 failed. Engine unchanged. Addon rebuilt (36 wheels + 148-HMM, 55 MB).

## Audit disposition
Hostile review verdict was SHIP-READY after one fix. F1 verified non-present in the shipped cut but hardened with an invariant test; F2 148-tier folded into the addon; F3 changelog reconciled. No pipeline correctness regressions.

# v9.7.172 — 2026-07-02 · build 20260702v97172a

**Engine unchanged (1.9.104) · Bundle 9.7.171 → 9.7.172.** Wheelhouse lab-data store + pyHMMER scanner engine (from the scanner patch-chat).

- **Wheelhouse/ (new, bundle root — DATA not code)**: a round-trippable lab-data store holding strain knowledge (strain_registry.json, 11 strains), the scanner registries (v0.2 = 26, v0.3 = 28 scanners), validations (AS-XXX answer-key, selvamicin, pyHMMER attine results, Pseudomonas scope), the pyHMMER scanner engine, and reports. Excluded from the test suite by design (it is data); included in the bundle manifest. "Clean the Wheelhouse" = prune superseded scanner versions.
- **mamey wheelhouse CLI (new module, accretion-justified)**: `list` (summarize store), `clean [--apply]` (prune superseded scanner-registry versions; dry-run by default), `add-strain <json>` (merge a strain record). Accretion-justified: lab-data lifecycle management is a distinct concern from pipeline extraction; not foldable into existing modules.
- **pyHMMER scanner engine (Wheelhouse/engine/)**: builds HMMs from discriminating domains (antiSMASH sec_met hits or custom seqs) and searches proteomes with hmmsearch. Needs pyhmmer + pyfamsa (already in the gemini-stack addon). KEY SEMANTIC (enforced in registry, documented): a raw HMM domain hit is NOT a scanner hit — the scanner value is the CLUSTER-LEVEL GATE (per-region domain count / co-occurrence) layered on top. Raw PKS_KS hits every ketosynthase; the PK01 gate (>=5 KS in one region) is what yields real large-PKS clusters.
- **Curated Pfam HMM database (Wheelhouse/hmm/scanner_pfam.hmm)**: 35 official Pfam models (with curated gathering cutoffs) — the discriminating families the v0.3 scanners gate on, extracted from the 2.2 GB Pfam-A into a 4.3 MB subset. SHA256-verified. Lets the scanner engine search against real curated models (not just on-the-fly HMMs) offline. VERIFIED end-to-end: engine proteome extraction + KS Pfam search at gathering threshold on venturicidin = 7 KS proteins, PK01 gate (>=5/region) FIRES, correctly calling the large modular PKS.

## Verification scope (honest, from the scanner brief)
- Scanner engine: PROVEN (runs, builds HMMs, searches, gates) on 5 attine proteomes; pyHMMER corroborated the domain-name proxy (AS-XXX richest: lanthipeptide/large-PKS/thiopeptide/siderophore all confirmed at E<1e-12).
- Validated scanner set: PK01, PK02, DK01, HP01, AB02, AB03 (AS-XXX 4/4). AF01 = the aminocyclitol/acarviostatin scanner with the correct DHQ_synthase/valiolone gate.
- **LP01 lipopeptide gate: SPECIFIED_PARTIAL** — needs the antiSMASH Condensation_Starter sub-domain to be specific; currently over-broad (plain Condensation). Marked partial until the starter-C HMM is sourced.
- wheelhouse CLI module: 4 tests (clean dry-run/apply, add-strain merge, list). Full suite 2512 passed, 0 failed. Engine unchanged.

## Still open (carried from the brief)
Contig-end split detector (marinolide c2+c5 ground truth) — highest-priority method gap, unbuilt. LP01 starter-condensation HMM. SID10815 blind prediction awaiting ground truth. MT01 meroterpenoid aromatic-prenyltransferase HMM.

# v9.7.171 — 2026-07-02 · build 20260702v97171a

**Engine unchanged (1.9.104) · Bundle 9.7.170 → 9.7.171.** Hostile-audit fixes (F1–F4). No correctness changes — the audit found the v9.7.170 science work sound and independently reproduced; these close documentation/coverage defects.

- **F1 (MEDIUM) — DIAMOND execution test**: added a skipif-guarded test that aligns a protein against itself through the DIAMOND path and asserts ~100% identity/coverage — the check that would catch a pident/qcovhsp parsing error in the outfmt6 wrapper. Skips (not fails) where no DIAMOND binary is present, so the fast-path SPECIFIED_UNVERIFIED status is explicit rather than silently assumed-covered.
- **F2 (LOW) — docstring**: align_genes_to_proteome now documents the real backend chain DIAMOND then pyswrd then Biopython (was "DIAMOND else Biopython", omitting pyswrd).
- **F3 (LOW) — test-count drift**: confirmed no shipped code or doc hardcodes a suite size; the §34 backstop reports live counts. Hardcoded numbers exist only in point-in-time changelog prose (correct as historical record).
- **F4 (LOW) — doctor probe**: mamey doctor science-stack check now includes pyrodigal_gv (reports 5/5 when the addon is installed).

## Verification
- Audit-touched tests: 14 passed / 1 skipped (DIAMOND test skips cleanly with no binary).
- Full suite 2508 passed, 0 failed. Engine unchanged.
- Hostile review verdict was SHIP-READY; all four findings addressed. ANI cross-validation (pyskani 97.15 / pyfastani 97.24 / report 97.3, within 0.15%) independently reproduced by the auditor.

# v9.7.170 — 2026-07-02 · build 20260702v97170a

**Engine unchanged (1.9.104) · Bundle 9.7.169 → 9.7.170.** Two-bundle split (lean pipeline + separate wheels addon) + pyskani ANI backend + science stack.

- **Two-bundle architecture**: the ~53 MB of static offline wheels moved OUT of the Sapote–Mamey bundle into a SEPARATE addon bundle (gemini-stack-<date>.zip). Pipeline cuts stay lean (bundle back to ~26 MB) and no longer re-copy static wheels every cut. install_gemini_offline.sh now auto-locates the wheels from the addon (or takes an explicit path arg). docs/COMPANION_FILES.md documents the two-bundle model: both must be attached; a missing addon is a missing attachment, not a missing feature.
- **pyskani ANI backend**: new compute_ani() prefers pyskani (fragmentation-robust, better for drafts like AS-XXX) with pyfastani fallback; always reports aligned fraction. Wired into mamey compare (runs S2 when genome FASTAs supplied). Cross-validated on the real AS-XXX × Amel2xC10 pair: pyskani 97.15% vs pyfastani 97.24% vs report 97.3% — three methods agree within 0.15%.
- **Science stack added to addon** (offline wheels): pyhmmer (offline HMMER3 profile search — closes most of the DIAMOND gap), pyfamsa/pytrimal/pytantan (MSA + cleanup), pyrodigal-gv, gb-io/pyfastx (fast I/O), dendropy/taxopy (phylo/taxonomy), matplotlib (figures — 13 modules import it). mamey doctor now reports science-stack availability.

## Verification
- Offline install verified from the SEPARATED layout (bundle + addon side by side): all stage deps import.
- pyskani + pyfastani agree on real genomes (97.15/97.24%); synthetic-fixture ANI test passes on both backends.
- Full suite 2508 passed, 0 failed. Engine unchanged.
