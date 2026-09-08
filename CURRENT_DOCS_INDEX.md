# Current Docs Index — v9.7.414 · engine 1.9.152 · build 20260907v97414a

Use this file to avoid treating historical root notes as current operating instructions.

## Current start files

1. `000_READ_ME_FIRST_CHATGPT_CLAUDE.md` — cross-assistant bootstrap and read-proof.
2. `CHATGPT_START_HERE.md` / `CLAUDE_START_HERE.md` — model-specific execution entry points.
3. `README_START_HERE.md` — human reading order.
4. `SESSION_START_MANIFEST.md` — current command summary and package workflow.
5. `PLAYBOOK.md` — current operator playbook.
6. `docs/WHATS_NEW_368_370.md` — what changed in cuts .368–.370 (breaking changes first: required
   `bigscape_prep.py --strictness`, the `sapote_hooks/` registry, availability pre-authoring,
   asset-discipline loop). Read this before following any pre-.368 instructions elsewhere.

## Current user docs

- `docs/GUIDE/01_User_Manual.md`
- `docs/GUIDE/02_Quick_Guide.md`
- `docs/GUIDE/03_Technical_Manual_Encyclopedia.html`
- `docs/GUIDE/04_Glossary.md`
- `docs/GUIDE/00_README.md`, `05_RunObservations_TEMPLATE.md`, `06_Concepts_QandA.md`,
  `07_Newsletter_June_2026.html` — also shipped in `docs/GUIDE/`.
- `TIER_DIFFERENCES.md` — current four-tier identity and label-only payload explanation;
  `PUBLIC-RELEASE` remains a separately governed promotion state.
- `TIER_SET_EXPLAINER.md` — historical v9.7.319 five-cut snapshot retained for provenance;
  its counts, sizes, and checksums are not current operating instructions.

## Historical / superseded operator surface

- `docs/QUICK_GUIDE.md` is a shipped historical reference, not a current operator guide. Use
  `docs/GUIDE/02_Quick_Guide.md` for the canonical current quick guide.

*(v9.7.335: the stamp was frozen at v9.7.136 and three of the four filenames above did not exist — `02_Quickstart.md`, `03_Technical_Manual_Encyclopedia.md`, `04_Workbook_Glossary.md`. Corrected against the real tree. v9.7.366-era note: the stamp then froze AGAIN at v9.7.337 for 29 cuts — caught 2026-08-15. The header is now owned by `tools/sync_version.py` so a third freeze fails `--check` instead of persisting.)*

*(v9.7.371 correction: the sentence above was aspirational — the sync_version ratchet (CANDIDATE_251) was never
implemented, and this index froze a THIRD time at v9.7.367 (caught 2026-08-19 inside the sealed .370 bundle).
The .371 cut re-stamps it AND lands the ratchet for real: `sync_version.py` writes this header and
`--check` fails on drift, with `tests/test_docs_version_drift.py` extended to cover it.)*

## v9.7.413 — cohort prevalence review surfaces (post-seal, read-only)

- `docs/PREVALENCE_WORKFLOW.md` — where the prevalence tools sit in a cohort analysis chain
  (post-seal, read-only; they consume the frozen tool databases and never alter a sealed package).
- `wiki/Domain-and-Scan-Prevalence.md` — how to run `tools/domain_prevalence.py` (Pfam/aSDomain/
  aSModule domain families across a cohort, with `--widget`) and `tools/scan_prevalence.py` (keyword
  scan datasets: resistance/regulator/transporter/chitinase). Both rank rare + evidenced +
  host-specific families as review candidates, not results.

## v9.7.339 → v9.7.370 — what landed after this index last moved

One line per cut, taken from the `CHANGELOG.md` entry headlines (the changelog remains the authority;
this table is navigation, not narrative). Engine bumps in this span: 1.9.119 (at .338) → 1.9.120
(.359, new deterministic scan + package artifacts) → 1.9.121 (.366, `_4B` KS-clade subtype partition).

| Cut | Date | Engine | Headline |
|---|---|---|---|
| v9.7.370 | 2026-08-18 | 1.9.123 (BUMPED) | W7 two-door lint unification + availability governance + asset discipline + hooks-travel + strictness-aware BiG-SCAPE staging (eleven cards) |
| v9.7.369 | 2026-08-17 | 1.9.122 (BUMPED) | full48 gate binding — §31–§48 Mode-B depth enforceable; W13 measured-architecture predicate |
| v9.7.368 | 2026-08-17 | 1.9.121 | MULTI_CHANNEL_HOLD wave (engine-neutral; non-whitelisted `_4D`) |
| v9.7.367 | 2026-08-16 | 1.9.121 | hygiene wave (incl. this index's previous re-stamp — see freeze note below) |
| v9.7.366 | 2026-08-13 | 1.9.121 (BUMPED) | `_4B` KS-clade subtype partition re-scores the fingerprint |
| v9.7.365 | 2026-08-12 | 1.9.120 | governed-source resolution closure + delegated decisions |
| v9.7.364 | 2026-08-12 | 1.9.120 | §31–§48 contract extension + governance/portability |
| v9.7.363 | 2026-08-11 | 1.9.120 | public-release readiness |
| v9.7.362 | 2026-08-11 | 1.9.120 | de-bundle third-party data |
| v9.7.361 | 2026-08-11 | 1.9.120 | sealer-authored governance/portability fixes |
| v9.7.360 | 2026-08-11 | 1.9.120 | engine-neutral additive |
| v9.7.359 | 2026-08-10 | 1.9.120 (BUMPED) | new deterministic scan + package artifacts |
| v9.7.358 | 2026-08-10 | 1.9.119 | carry-forward |
| v9.7.357 | 2026-08-09 | 1.9.119 | carry-forward |
| v9.7.356 | 2026-08-07 | 1.9.119 | workflow tools + full guardrail hooks in-bundle |
| v9.7.355 | 2026-08-07 | 1.9.119 | governance/coordination tooling + generic phylogenetics |
| v9.7.354 | 2026-08-06 | 1.9.119 | Mode B evidence governance + seal integrity + hygiene |
| v9.7.353 | 2026-08-05 | 1.9.119 | audit-driven correctness/claim-safety + post-seal tooling |
| v9.7.352 | 2026-08-05 | 1.9.119 | forward-only AF-scope change [H4]; AS-XXX ratified into GOVERNED 45/1,787 |
| v9.7.351 | 2026-08-04 | 1.9.119 | NON-NEUTRAL forward-only: over-merge de-inflation + post-seal integrity |
| v9.7.350 | 2026-08-04 | 1.9.119 | NON-NEUTRAL forward-only: Inventory-tier reform (class-gated `Low`) |
| v9.7.349 | 2026-08-03 | 1.9.119 | report-layer: phylo companions + compound-family curation + strain-data-home |
| v9.7.348 | 2026-08-02 | 1.9.119 | flagship: external-activity interface + resistance dossier + BiG-SCAPE figure factory |
| v9.7.347 | 2026-08-02 | 1.9.119 | correctness/governance cut |
| v9.7.346 | 2026-07-31 | 1.9.119 | Codex 200-set figure atlas |
| v9.7.345 | 2026-07-31 | 1.9.119 | BLASTp automation + literature corpus + heatmap pack |
| v9.7.344 | 2026-07-31 | 1.9.119 | BLASTp subsystem hardening + card enrichment + widget deliverables |
| v9.7.343 | 2026-07-30 | 1.9.119 | verdict surfacing + reference-dark wiring |
| v9.7.342 | 2026-07-30 | 1.9.119 | Wave B lead-pages layer |
| v9.7.341 | 2026-07-30 | 1.9.119 | Wave A report/tooling layers |
| v9.7.340 | 2026-07-29 | 1.9.119 | provenance caveats + trove ingest |
| v9.7.339 | 2026-07-28 | 1.9.119 | §4 judgment-forward template stubs |

## v9.7.413 — measured bioassay activity channel (strain-level, score-neutral)

- `wiki/Bioassay-Activity-Channel.md` — `tools/bioassay_to_activity_channel.py` turns MEASURED fraction-
  screen data into typed `bioactivity_metadata_v1` objects (`--bioactivity-json`) and, with `--af-dossier-csv`,
  the `af-dossier --activity-table` shape. Strain-level, extract-level, no BGC attribution; preliminary
  single-replicate screen (artifacts expected); judgment deferred.
- `docs/BIOASSAY_ACTIVITY_CHANNEL_WORKFLOW.md` — where it sits in the analysis chain.

## v9.7.338 new subcommands & deliverables

Twelve new post-seal, sign-off-gated capabilities landed in .338. All are **non-scoring** unless
noted (they read an already-sealed package and never touch AB/AF/tiers, scans, gates, or any
published tier — capacity-level, judgment deferred). Documented in `docs/GUIDE/02_Quick_Guide.md`
(command reference), `docs/GUIDE/01_User_Manual.md` §4.3a, and `docs/user_guides/tools_reference.md`
Section 20.

- **`cohort-leads`** — union every sealed package's triage board into ONE ranked cross-strain
  priority-leads CSV (Exceptional+High leads). *Non-scoring re-projection.*
  `python mamey_run.py cohort-leads --runs-dir <runs_dir> [--out COHORT_PRIORITY_LEADS.csv]`
- **`cohort-assemble`** — assemble many sealed packages into a cross-cohort master table
  (+ siblings, optional xlsx). *Non-scoring.*
  `python mamey_run.py cohort-assemble --runs-dir <runs_dir> [--out COHORT_MASTER.csv] [--xlsx]`
- **`comparator-coverage`** — two-denominator MIBiG comparator-coverage evidence layer
  (the false-positive killer: named-family leads that survive only one denominator). *Report-only, non-scoring.*
  `python mamey_run.py comparator-coverage <package> [--cohort-runs-dir <runs_dir>]`
- **`af-dossier`** — Antifungal Lead Dossier: the AF lead board × optional measured Candida

- **`docs/BIOACTIVITY_METADATA_CONTRACT.md`** — typed optional metadata contract; replaces named assay defaults.
  activity (capacity and measured columns never mix; runs with no wet-lab input). *Report-only, non-scoring.*
  `python mamey_run.py af-dossier <root> [--out DIR] [--activity-table CSV] [--depth N]`
- **`good-guesses`** — claim-safe interpretive-priors deliverable (md/csv/docx/pdf): the single best
  claim-safe read per notable BGC, tagged solid / rare / remarkable / notable / interesting, each with
  a confidence and a resolving experiment. *Report-only, non-scoring.*
  `python mamey_run.py good-guesses <root> [--out DIR] [--pdf] [--docx] [--depth N]`
- **`modeb-export`** — export an authored Mode B card (`.md`, or a package `mode_b/` dir for batch)
  to Word `.docx` + `.pdf` (reportlab). *Non-scoring.*
  `python mamey_run.py modeb-export <card.md|mode_b/> [--outdir DIR] [--format docx|pdf|both]`
- **`figures kcb-locusmap`** — offline KnownClusterBlast comparative gene-cluster locus map
  (PNG + SVG + `data.csv`). Degrades gracefully with no matplotlib. *Non-scoring figure.*
  `python -m mamey.kcb_locusmap --zip <zip> --contig <NODE> --out-dir <dir> --strain-id <ID> --bgc-id BGC### [--products "..."] [--top-n 6]`
- **`domain-reference`** — emit the bundled Mode-B domain functional-context reference dictionary from
  sealed package(s). *Advisory.*
  `python mamey_run.py domain-reference --package <pkg> [--out FILE]`
- **`realistic-count`** — honest corrected-denominator BGC count (marginal-drop + HIGH RG-GMCI merge). *Advisory.*
  `python mamey_run.py realistic-count --package <pkg> [--out FILE]`
- **`novelty-shortlist`** — composite multi-signal novelty shortlist (KCB-dark + low recognizability
  + RG-GMCI + cohort-unique domain). *Advisory.*
  `python mamey_run.py novelty-shortlist --package <pkg> [--top 30] [--out FILE]`
- **`signoff`** — the "would a master's student sign off?" analysis QC gate: objective checks on Newick
  trees (outgroup / contaminant / label-cruft / support / thin-tree). *Advisory, always exit 0.*
  `python mamey_run.py signoff [tree.treefile ...] [--minutes N]`
- **`verify-modeb --interp`** — adds the Mode-B interpretation (judgment-substance) layer to
  `verify-modeb`: **WARN-only** `INTERP_*` findings (missing §4 synthesis / tier / ref-dark read); the
  structure gate's PASS/FAIL and exit code are unchanged.
  `python mamey_run.py verify-modeb --package <pkg> --bgc BGC### --interp [--interp-strict]`

**Non-feature .338 changes that affect the docs:**
- **§4 Mode-B evidence gate now bites (MB-01)** — the §4 evidence-grid check is now enforcing, not advisory.
- **NAPAA standing rule now follows the registry (RG-01)** — the NAPAA exclusion is driven by
  `rules_registry.json`, not a hardcoded pattern; behaviour is unchanged, provenance is now single-source.
- **Redaction wording corrected (E2E-03)** — AS-series strains are **PUBLIC by default** as of the
  v9.7.236 PI decision (2026-07-06); the fail-safe PRIVATE guard applies only to AJS- / PENDING- /
  unrecognized shapes. Corrected in `docs/reference/03_Plumbing_Reference.md`. *(Note superseded
  2026-08-15: the top-level project `CLAUDE.md` has since been updated and now carries the correct
  AS-PUBLIC wording — the "should be updated by hand" action is done.)*

## v9.7.332 reporting-v2 (per-gene MIBiG convergence)

- `docs/reporting_v2_mibig_convergence.md` — **read before citing** the new `MIBiG_Convergence` /
  `MIBiG_Profile` / structured-antiSMASH outputs or the `H1_HIGH_DENSITY … H5` + `CAUTION_CLASS_MISMATCH`
  tier vocabulary. Tiers are reporting strata, not judgments; no AB/AF scoring; comparator ≠ product.
  (The P_MPG outputs are unchanged since .332; as of .336 they render into the Mode-B card via
  `emit-modeb-cards` — see below.)

## v9.7.336 convergence card layer + reliability fixes

- **`emit-modeb-cards` convergence card layer** — the per-gene MIBiG convergence layer that has shipped
  in every sealed package since .332 now surfaces in the Mode-B card via a
  `## Per-gene MIBiG convergence — primary family evidence` section (top-5 references, tier/gene-share/
  median %id-cov/class-concordance/dominance, a one-line convergence read, and the package's own
  `claim_safety` string verbatim). Three-state layer-presence guard (`convergence_layer_present()`):
  rows → table; layer ran with no family → evidence-backed reference-dark note; layer absent → an explicit
  "no family-convergence statement can be made". Reader-side only. See `CHANGELOG.md:18`.
- **CS-01** — `mamey claim-safety --package` identity-overclaim check de-inverted; production verbs
  (produces/synthesizes/yields) now fall through to the shape heuristic instead of silently passing
  hallucinated compound names. See `CHANGELOG.md:16`.
- **PROV-01** — every `B1_BGC_Master` row now carries `engine_version`, so a master accumulated across an
  engine bump is no longer silently mixed. See `CHANGELOG.md:20`.
- **SEAL-01** — `check_release_manifest` now verifies TIER_MANIFEST **membership** (omitted/phantom files),
  not just its stamp. See `CHANGELOG.md:22`.

## v9.7.337 (single-item scoring cut)

- **MISANCHOR-01** — the aminoglycoside and polyene mis-anchor clamps in `scoring.py` are now
  **unconditional** (no longer gated behind a single global `not tier1_diag`), so an unrelated Tier-1
  diagnostic can no longer erase a class-specific mis-anchor clamp. See `CHANGELOG.md:3,5`.

## Historical / provenance docs

Files named `BUNDLE_PATCH_NOTES_*`, `PATCH_*`, `VERIFICATION_REPORT_*`, and old `RELEASE_NOTES_*` are retained for provenance. Do not use them as current instructions unless a current start file explicitly points to them.

- `Sapote_Mamey_ROADMAP.md` — **HISTORICAL as a whole-document narrative** (2026-07-02 pre-phase-shift
  PI account; its "current status" is engine 1.9.104 / bundle 9.7.172). Two sections remain live and are
  NOT historical by association: **"Standing rules (unchanged)"** (claim-safety conventions still
  governing) and **"Mode B authoring order (v9.7.180)"** (verified live in
  `mamey/modeb_template_emitter.py` — CONFIRM/REFINE/OVERTURN, `hmm-adjudicate`, `kcb-frontpage`
  corroboration). Those two belong re-homed to a standalone current doc; a v2 roadmap is the PI's to
  write.

## v9.7.142 SOP / Bug Hunt / BLASTP Evidence Docs

- `docs/SOPs/SOP_MASTER_INDEX.md` — SOP library overview and current status.
- `docs/SOPs/SOP-04_Iterative_NCBI_BLASTP_Batching.md` — iterative NCBI BLASTP batching SOP.
- `docs/SOPs/SOP-05_BLASTP_Result_Upload_Parse_Reprioritize.md` — BLASTP result parsing and reprioritization SOP.
- `docs/SOPs/SOP-07_Single_Region_Public_Accession_Inputs.md` — single-region public accession intake SOP.
- `docs/release_planning/V97142_NEXT_CUT_PLAN.md` — v9.7.142 next-cut checklist.
- `docs/release_planning/SOP_DERIVED_BUGHUNT_MATRIX.csv` — SOP-derived bug-hunt matrix.


## v9.7.144 Mode B / Wise PKS patch documents

> **Canonical Mode B contract (current):** the finished deliverable is **§1–§48**
> (`FINISHED_FULL48_CURRENT_EVIDENCE`), gate-enforced since **v9.7.369**
> (`modeb_structure_gate.py`, `authored_verify.py`). **§1–§30** (`MODEB_CANDIDATE_30`) is the
> **legacy candidate/calibration** profile, and **§1–§20** is the always-required core subset, never
> a finished card. The v9.7.144 documents listed below are kept for provenance; where they call §30
> or §20 "the current canonical contract," read that as superseded by the §48 gate. Current authoring
> spec: `wiki/Mode-B.md` and `wiki/Mode-B-Gene-First-and-48-Section-Manual.md`.

- `docs/MODE_B_30_SECTION_CANONICAL_TITLES.md` — §1–§30 section titles (now the **legacy candidate/calibration** profile, not the finished contract).
- `mamey/data/mode_b/modeb_full30_corrective_contract.json` — machine-readable §1–§30 corrective-protocol contract (legacy candidate profile).
- `docs/FULL_MODEB_20_SECTION_CONTRACT_v97144.md` — DEPRECATED (§20-only); redirect pointers only.
- `docs/MODE_B_20_SECTION_CANONICAL_TITLES.md` — DEPRECATED (§20-only); redirect pointers only.
- `docs/MODE_B_FULL20_CONTRACT_RECONCILIATION.md` — explains the §1–§8 / §1–§10 / §1–§20 reconciliation.
- `docs/WISE_WORKFLOW_DOCTRINE.md` — fragmented PKS residue-aware workflow doctrine.
- `docs/PDF_OUTPUT_CONTRACT_v97144.md` — printable Mode B output packet rules.

## New in v9.7.405 (composition of the Codex punch card)

- `docs/COMMAND_CATALOG.generated.md` — task-grouped catalog of every CLI subcommand (generated; `tools/gen_command_catalog.py --check`).
- `docs/decisions/PROJECT_MEMORY_SNAPSHOT_FORK.md` — the June-25 keep/retire fork, resolved-by-alias at v9.7.400.
- `docs/KCB_SCORE_PROVENANCE.md` — point 4 corrected: a clusterblast-only region ends MEDIUM + manual-check, never HIGH.
- `docs/ACTIVITY_LEAD_REPORTS.md` — `tools/render_activity_lead_reports.py`, the Day-5-shaped per-strain lead report.
- `docs/CHITIN_REFERENCE_EVALUATION.md` — whole-genome, BGC-uncoupled chitin capacity evaluation.
- `docs/OWNER_KEPT_FIGURE_INPUTS.md`, `docs/FIGURE_OWNER_REVIEW_WORKFLOW.md`, `docs/OPTIONAL_FIGURE_FACTORY_TOOLS.md`, `docs/SAPOTE_REPORT_THEME.md` — Figure Factory owner-input, review-compiler, gallery and theme surfaces.
- `wiki/Audience-Start-Paths.md`, `wiki/Researcher-Recipes.md`, `wiki/Mode-B-Gene-First-and-48-Section-Manual.md`, `wiki/Figure-Factory-Preflight-and-Methods-Manual.md` — Codex Wiki Revision 03 pages, currency-stamped.
- Operator front doors (stdout = receipt): `tools/lead_propagation_gate.py`, `tools/bgc_alias_history.py`, `tools/reference_bgc_structural_validator.py`, `tools/generated_surface_ownership.py`, `tools/compile_figure_owner_review.py`, `tools/build_owner_kept_figure_inputs.py`, `tools/chitin_reference_eval.py`.

## Figure Factory — integrated deliverable (current)

Figure Factory is a first-class, expected deliverable: invoked as `python mamey_run.py figure-factory
--config <json>` and auto-emitted in the run/cohort flow. `python tools/figure_factory_next.py
--config <json>` is the advanced/manual path (same `build()`, identical artifacts). Every figure ships
its exact plotted-data sidecar (Figure Factory Next writes `figure_factory_next_data.tsv`; the wider
figure set carries a tidy `_data.csv`), restyleable in R via `tools/ggtree_placement.R` and the
`sapote_ggplot2.R` / `sapote_ggtree.R` template set. The legacy Diner Menu (`docs/DELIVERABLE_MENU.md`)
is retired; the CLI subcommand surface is the authoritative deliverable set.

- `docs/FIGURE_FACTORY_NEXT.md` — the deliverable-facing portable contract, integrated invocation, artifacts, and R companion.
- `wiki/Figure-Factory-Preflight-and-Methods-Manual.md` — preflight, typed refusals, caption/methods contracts, and claim ceiling.
- `docs/OPTIONAL_FIGURE_FACTORY_TOOLS.md` — the optional theme/component preview galleries (distinct from the integrated deliverable; deliberate manual tools only).
- `docs/figure_factory/` — Figure Factory repair specs, binding-status ledgers, and the reusable progress-dashboard pattern; see its `README.md`.
