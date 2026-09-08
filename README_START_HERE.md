# README — start here

> **One door: run `python mamey_run.py start`, then read `AGENTS.md`.** `start` prints this bundle's
> real version and the ordered happy path; `AGENTS.md` (= `CLAUDE.md`) is the canonical contract for
> every coding agent, and `CURRENT_DOCS_INDEX.md` is the sole authority on which docs are current.
> Read `CHATGPT_START_HERE.md` (ChatGPT) or `CLAUDE_START_HERE.md` (Claude) only for assistant-specific
> rules; for a timeout-safe first run add `--capped-session` to `run`
> (`python mamey_run.py run ... --mode gold --capped-session`). The rest of this page is the
> reviewer/operator banner and release status.

---

# Sapote–Mamey — START HERE

> **Build status.** This CODE tree is a controlled quality-recheck candidate, not a signed public release. [`pyproject.toml`](pyproject.toml) and the synced package identity define its canonical bundle version; [`RELEASE_MANIFEST.md`](RELEASE_MANIFEST.md) is the authority for its current release status and receiving-cut validation.
>
> **Reviewers/Claude:** read `SESSION_START_MANIFEST.md` first — it is the capability menu (tools, modes, deliverables) for the session.

## I want to… (pick one)

1. **Run a strain** → `docs/HOW_TO_USE.md` — operator guide: antiSMASH ZIP in, claim-safe report out.
2. **Audit a finished run** → `python -m mamey.boundary_audit <pkg>` (catches silent-omission / dropped-BGC) and `tools/evidence_conservation_audit.py`.
3. **Choose which ZIP to upload** → `docs/PACKAGE_PROFILES.md` — the four tiers and when to use each.
4. **Refresh the reference library** → `python tools/seed_reference_library.py --help`; read `resources/reference_seed_inputs/README.md` first (the JSON is authoritative; the seeder is guarded against downgrade).
5. **Make / verify deliverables** → `DELIVERABLE_MANIFEST_TEMPLATE.md` + `docs/DELIVERABLE_CONTRACT.md`.

## New in v9.7.368–v9.7.370 — read `docs/WHATS_NEW_368_370.md`

**Content-currency note (v9.7.371):** the sections below this line describe the v9.7.338-era menu and
are retained as history. The current user-facing surface added since — the `modeb-availability`
pre-authoring step, the Mode-B identity guard, the asset-discipline loop, BLASTp coverage waves,
strictness-aware BiG-SCAPE staging (BREAKING: `--strictness` is now required), and the portable
guardrail registry (`sapote_hooks/`) — is summarized in **`docs/WHATS_NEW_368_370.md`** with exact
commands. Engine gates moved too: §31–§48 depth is enforceable (1.9.122) and the verify door is
unified (1.9.123).

## New in v9.7.338 — post-seal deliverable menu additions

All of the following are **post-seal, non-scoring / advisory** add-ons: they read already-sealed package
outputs and never change AB/AF/novelty priors or the lead tier. Every read is a **class-level capacity
hypothesis** — judgment deferred, similarity not identity, no structure / product-identity / bioactivity claim.

- `good-guesses` — Good Guesses: the single best claim-safe interpretive read per notable BGC (capacity hypothesis + confidence + resolving experiment) → `GOOD_GUESSES.md/.csv/.docx/.pdf`.
- `modeb-export` — export an authored Mode B §1–§30 card (or a package `mode_b/` dir) to Word `.docx` + `.pdf` (real tables, per-page claim-safety footer).
- `figures kcb-locusmap` — offline clinker-style KnownClusterBlast comparative locus map (query over top-N MIBiG refs, homology ribbons shaded by %identity) → png/svg/csv.
- `af-dossier` — Antifungal Lead Dossier: joins each sealed package's AF lead board to measured Candida activity (capacity and measured activity kept in separate columns).
- `cohort-leads` — union every sealed triage board into one ranked cross-strain `COHORT_PRIORITY_LEADS.csv`.
- `cohort-assemble` — assemble many sealed packages into `COHORT_MASTER.csv` (+ siblings / optional xlsx): the figure-ready cohort substrate.
- `comparator-coverage` — two-denominator MIBiG comparator coverage (locus vs defining-core) flagging low-specificity accessory-only collisions.
- `domain-reference` — emit the Mode-B domain functional-context dictionary from sealed package(s).
- `realistic-count` — corrected-denominator ("honest") BGC count (marginal-drop + HIGH RG-GMCI merge); advisory.
- `novelty-shortlist` — composite multi-signal novelty shortlist (KCB-dark + low recognizability + RG-GMCI + cohort-unique domain); advisory prior.
- `signoff` — analysis sign-off QC gate ("would a master's student sign off?") on phylogenetic trees; advisory, exit 0.
- `verify-modeb --interp` — adds the Mode-B interpretation gate (judgment substance; advisory WARN, non-blocking) to the structure verify.

**Bundle:** `sapote-mamey-v9.7.414 (current tier zips; see CHANGELOG)`
**This is the current candidate build, not a signed release.** See `RELEASE_MANIFEST.md` before using it as a release artifact.
Naming convention: `sapote-mamey-v<bundle>-<YYYYMMDD>.zip` — alphabetical = chronological.

## What this bundle contains (cumulative as of 2026-06-10)
All changes applied in this order:

1. **evidence-conservation** — TIGRFAM, NRPS substrates, active-site, t2pks/terpene, RiPP cores all fixed
2. **gitignore** — internal-only files (NOTES_FOR_ALEX, ledger, triage, handoff) added to `.gitignore`
3. **synthetic-fixture** — `examples/test_data/test_master.xlsx` replaced with SYNTHETIC-1 (8 BGCs, no real strain data)
4. **disclosure-sweep** — §25, §26, §41.12, §51.12 FLBR appendix, §52.11 UMED table all anonymised; `MODE_B_RETROSPECTIVE_VALIDATION_REPORT.md` removed; `SHORT_ID_REGISTRY.md` SID table removed; `CHANGELOG.md` SID findings removed
5. **prompt-fix** — `MAMEY_CHATGPT_EXECUTION_PROMPT.md` §2 + §10: `--master` chaining made explicit and mandatory
6. **rggmci-key-fix** — `mamey/master_workbook.py`: `rggmci.get("high")` → `rggmci.get("high_pairs")` in B4 + C4 writers

## To run a strain diagnosis (normal use)
Give ChatGPT this bundle + an antiSMASH ZIP, use `prompts/RUN_DIAGNOSIS_PROMPT.md`.

## To merge a second (or later) strain into the master workbook
Pass the previous run's `Mamey_v1.9.31_Master_After_<Strain>_<date>.xlsx` as `--master`.
See `prompts/MAMEY_CHATGPT_EXECUTION_PROMPT.md` §10 for the exact command.

## Integrity
154 files · self-verifying: `sha256sum -c SOURCE_CHECKSUMS_SHA256.txt`


---

## Citation-Compact Provenance and Citation Status

Sapote-Mamey v9.7.140 uses citation-compact outputs to separate runtime evidence structure from literature verification.

- **antiSMASH 8.0** is recorded as method/database provenance for BGC detection and product/region calls: DOI `10.1093/nar/gkaf334`.
- **MIBiG 4.0** is recorded as reference-database provenance for curated BGC entries and KnownClusterBlast dereplication context: DOI `10.1093/nar/gkae1115`.
- **`PASS_STRUCTURE`** means the package structure, citation ledger, work-order files, compact reports, manifest tracking, and checksum tracking passed validation. It does **not** mean every literature claim has been manually verified.
- **`operator_supplied`** means the citation/provenance row came from runtime evidence or comparator fields already present in the package.
- **`citation_needed`** means literature support is missing and should be filled by a separate literature-search pass.
- **`Literature_Search_WorkOrder.md/json`** is a safe handoff for another ChatGPT/web-literature session. It is a search instruction, not a verified fact.

Current compact lead tables use `interpretation_scope` for reader-facing scope. The older reader-facing scope field should not appear in current citation-compact outputs.
