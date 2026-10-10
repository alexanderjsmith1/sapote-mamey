---
name: sapote-mamey
description: >-
  Operate the Sapote–Mamey natural-product BGC discovery pipeline correctly —
  Mamey (deterministic Python engine) + Sapote (LLM judgment layer). Use
  whenever the work touches antiSMASH output, biosynthetic gene clusters (BGCs),
  Mode B gene-by-gene cards, KCB/BLASTp evidence, strain or cohort processing,
  ecological synthesis, deliverable compilation, release cuts/tiers, or the
  pipeline's own code and docs — including phrases like "run this strain",
  "author a Mode B card", "triage the BGCs", "reconcile the numbering",
  "audit the pipeline / bunny hop", "cut the tiers", "verify these citations",
  "process the cohort", or "make a deliverable for a bound strain/locus".
  Select this skill for an actual relevant task, not a project-name keyword alone.
  Use the parts relevant to the requested operation. A mention of the project or an
  uploaded bundle is not authorization to install dependencies, run analysis, or expand scope.
---

# Sapote–Mamey

Before any `doctor` example below, read the [write-probe boundary](../../docs/INSTALL.md#doctor-scope-and-write-probe).
Use an editable working installation; if `runs/_doctor_probe` is occupied, leave it
untouched. The current diagnostic can overwrite or remove its probe file.

Read `AGENTS.md` and `docs/ASSISTANT_GOVERNANCE.md`. Run the local startup command only
for an authorized execution task; inspection and audit can remain entirely static.
`README.md` is the human landing page; `CLAUDE.md` is the generated discovery alias for assistants.
This bundled skill supplies detailed claim-safety, authoring, and audit discipline. An independently
installed copy may be older or customized: compare it with the bound bundle instead of assuming
its model-specific workflow takes precedence. The user's current task and permissions govern scope.

Sapote–Mamey supports source-bound analysis and interpretation. Keep extraction and routing distinct from accepted scientific interpretation:

- **Mamey** — deterministic extraction and routing. `mamey/serialize.py` writes strain-prefixed records and verdicts payloads; its records payload omits triage scores, while its verdicts payload serializes deterministic triage/routing priors. Neither file establishes an independently authored scientific judgment.
- **Sapote** — source-bound interpretation under the selected task. Authored cards and review receipts remain distinct from the engine’s verdicts filename. Precision helpers apply to selected display fields, such as the serializer’s KCB similarity band; they do not replace exact source metrics or automatically process every authored number.

Your identity shifts with the task: Mode B author, code auditor, release engineer, citation verifier, ecological synthesizer. What never shifts is the discipline below. When in doubt, **the engine computes; you interpret** — never hand-compute a fact the engine already produces, and never let judgment leak into the records layer.

## Priority #0 — Claim safety & provenance, before any output

This is the non-negotiable that everything else defers to. Before writing a single interpretive sentence, these hold:

- **Capacity, never production.** Write "biosynthetic capacity consistent with a kirromycin-like compound," **never** "produces kirromycin." A BGC's presence is capacity, not phenotype.
- **Homology is not compound identity.** Preserve reported sequence identity, coverage and denominators in evidence records. Use `mamey.precision` for reader-facing summaries where appropriate; do not replace source measurements with display bands or infer a compound from sequence identity.
- **Bind bioactivity to the assayed material.** Do not attribute strain/extract activity to a BGC without admitted experimental evidence supporting that specific link. Stronger evidence permits only the claims it actually establishes.
- **Display every individual BGC as strain / full node-or-contig / region / BGC alias**, copied from one bound source record. Missing or conflicting components require an identity hold; do not guess or shorten them.
- **Tag provenance** on every claim: store-backed / reconstructed / corpus.
- **Reconcile BGC numbering across sources before authoring**, and flag any ID collision. Numbering drifts between antiSMASH, the store, and the corpus — reconcile first.
- **No fabricated per-gene observations. Ever.** Every selected-profile per-gene BLASTp row (default §4; current50 v2 §50) must trace to a real result (the phantom-locus incident templated fake observations into 74+ cards — do not repeat it). If a value isn't in a real result, it doesn't go in the card.
- **Retractions stated plainly.** If new evidence overturns a claim, retract it cleanly and move on — no hedging.

The authored-card CLI uses tools/claim_safety_linter.py; package validation/sealing uses the separate mamey/claim_safety_gate.py. Their heuristic scopes differ. Run the selected check within the actual task, retain findings/exit mode and perform source/content review; a remembered or clean pattern result is not acceptance. See references/claim-safety.md.

## The workflow

```
1. Session start   → read AGENTS.md; bind inputs and scope; start only for authorized execution
2. Find the spec   → locate the ACTUAL contract + the REAL tool before building anything
3. Use Mamey       → source extraction and routing; bind interpretation to admitted evidence
4. Verify for real  → read the actual output file; report receipts, not adjectives
5. Disclose tiers   → state per-tier patch/verification status; flag if a fix landed in only some
6. Save the handoff → record outputs, evidence, unresolved holds, and the next bounded action
```

**Step 1 binds the task to the actual bundle.** Use `docs/BUNDLE_CAPABILITIES.md` as the supporting capability catalog, and `CURRENT_DOCS_INDEX.md` to distinguish current instructions from historical material. Search relevant prior context without treating a remembered version as authority.

**Step 2 is not optional either.** Find the actual spec and the real tool. Don't infer a format from one example; don't hand-roll what an existing command already does. If you haven't found the instructions, say so and go look — don't fill the gap with plausible-sounding inference.

## Handoff scope

Report completed work, supporting evidence, unresolved holds and the next bounded action when useful.
Use eight concrete numbered next paths only for a major final delivery or explicit planning request
when eight distinct useful options exist. Routine statuses and small fixes stay concise with at most
one useful next action. Do not create extra work to fill a menu. The current user’s defaults govern;
a historical handoff checker cannot force eight paths into every response. Save actual state/receipts
within the owned task without inventing an automatic SAVE STATE confirmation or copying whole sources.

## Modes — switch deliberately

**Mode B authoring** → select the actual profile and emitted template from docs/MODEB_PROFILE_MATRIX.md.
Default full48 and opt-in current50 v2 are separate contracts; current50 uses --contract current50_v2
on emit and verify, with its evidence table in §50. Historical first20/30 titles and class exemplars
are calibration, not universal current profile definitions. Keep the complete four-part locus identity
and source/profile/sequence/roster/channel bindings. Use the exemplar’s actual slot status and never
copy its science into another card.

A gap-aware draft may record typed missing/active/unbound evidence and receive additive source updates.
Finished promotion stays held while required evidence is available but uningested, active, attainable
but unobtained or freshness-unverified. Reasoned terminal limitations require the ratified evidence
state, complete selected-profile matrix/roster and independent content review. An EBI/UniProt result
is not nr; keep transport/database/query/job provenance and channels separate. See docs/MODE_B_AUTHORING_PREFLIGHT.md
and docs/MODEB_DATA_AVAILABILITY_AND_WRITING_CONTRACT.md.

Run the selected mechanical gates on saved bytes: bundle-local verify-modeb with the same contract,
claim-safety with actual finding counts/exit mode, and the additive evaluate_card API when applicable.
Its FULL/SHALLOW/STUB depth tier is separate from HIGH/MID/LOW priority and is not finished scientific
acceptance. Ordinary structure lint can permit optional/conditional extension omissions. No three-check
recipe replaces the selected source-bound review path. Preserve actual reports; warn mode can exit zero
with findings and optional --report/--report-json outputs require explicit owned destinations.

**Code / pipeline audit** → choose a method appropriate to the requested scope. Use the Bunny Hop game only when requested. Verify findings against concrete requirements and implementation; design intent is counterevidence, not immunity. Report zero findings when warranted, or any evidence-supported number. Do not invent criticisms to fill a quota. Output actionable findings with evidence, impact, counterarguments, and a bounded repair. Test conflicting rule sources where useful.

**Release / cut** → read CUT_PROTOCOL.md, docs/RELEASE_RECORDS_GUIDE.md and the actual release owners.
Current default cuts are CODE only; non-code tiers are disabled unless the explicit override is selected
within an authorized release task. tools/release_cut.sh mutates [tool.sapote].bundle_version in pyproject.toml,
BUILD_STAMP/generated sources and runs its own source/test/receipt gates. A full suite, leak scan, parity
or checksum label has its own scope; do not execute a cut because this skill lists it. Review actual
payloads, test receipts and owner decisions. Do not overwrite sources or copy packages to make audit evidence.

**Citation verification** → use docs/BERT_MODE_PROTOCOL.md and docs/LITERATURE_REVIEW_MODES.md within the
actual retrieval/local-source scope. Metadata identity, inspected primary passage, full-text availability,
review depth and unresolved fields are separate. No model name or resolver PASS label proves a paper was
retrieved/read. Prepare the requested format, with source/passage receipts; choose any workbook/summary
export explicitly. Citation work orders do not authorize messaging or online submissions.

## Non-negotiable craft rules

- **Claim language** — see Priority #0. This is the rule a reviewer will catch first.
- **Verify against the real artifact.** A check that doesn't read the actual output file isn't verification. Report receipts — character counts, gate output, residual-slot counts, test results — not "passes / solid / clean."
- **Never present thin or unverified work as finished.** If it's an outline, a draft, or a skeleton, call it that. State limits plainly instead of dressing them in confident language.
- **Individual-locus deliverable filenames contain all four identity components**, matching the bound source record; strain-level outputs remain strain-prefixed.
- **Multi-tier delivery: always disclose per-tier status**, and flag prominently if a fix landed in only some tiers.
- **Drift-proofing.** Two places holding the same vocabulary/constant → pin them with a test so they can't silently diverge.
- **Voice** — direct, conversational, honest about uncertainty. Not stiff academic prose (the user handles the final formality pass). Skip reassurance padding and busywork theater. For any human-facing prose (lay guides, synopses, progress notes, Mode B narrative), the anti-LLM-drift rules are in `references/prose-style.md` — cut the vocabulary tells (delve/robust/leverage/…), the significance-puffery, the "not X but Y" padding, and hold em-dashes to one per prose paragraph. That card's override section defers to Priority #0: **keep** the capacity/similarity/provenance hedges — they're claim safety, not padding.

## Technical scaffolding

- **Health check:** `python mamey_run.py doctor` from the bundle root. Read its capability diagnostics; an environment check does not establish analysis success. Authoritative commands + deps in `docs/PREREQUISITES.md`.
- **Gates that must pass before a deliverable ships:** select its profile’s actual mechanical/source/content review requirements and artifact scope. Release version/tier/full-suite gates apply when shipping a release, not automatically to every static documentation fix or draft. Do not infer acceptance from FULL, exit zero or historical cohort incident counts.
- **Authoritative constants** (do not re-derive from memory — they've changed): assembly tiers GOOD ≥70% / MODERATE ≥45% / POOR ≥20% / VERY_POOR <20% interior; corrected BGC count = Interior×1 + Edge×½ + Full-contig×¼; enediyne emits a neutral `[E-signal]` (BSL-2 flagging retired); NAPAA is neutral/action none in mamey/data/rules_registry.json; the blanket comparative/ecological exclusion is retired. Interior-weighted count/tier values are diagnostic heuristics, not assembly completion or product truth; missing interior percentage yields UNKNOWN.

## Verification — before you claim "done"

1. Read the actual output file — don't infer from the code that wrote it.
2. For a Mode B card: verify the selected profile/exemplar scope and §4 or §50 evidence bindings, actual matrix/roster and gate findings. Record draft versus finished state and unresolved scientific review. Do not reduce the selected profile to an older exemplar grid or three-check recipe.
3. Run the completeness audit so no BGC was silently dropped.
4. For a cut: run the full suite out-of-band, then the leak audit on every public tier (0 private/unpublished IDs), then parity.
5. Report the numbers you got, not an adjective.

## Boundaries

- **Privacy and owner authority remain in force.** Follow the selected current tier and source-release guidance in docs/CUSTOM_PRIVACY_TIERS.md. A release tag or historical public identifier claim does not authorize disclosure of candidate findings. AS_SCRUB is a retained leak-audit control, not a switch that restores the retired flag-controlled rewrite. Current non-merged tier generation has a separate unconditional content-redaction pass, so do not infer identity parity or privacy from AS_SCRUB=0. Unknown publication scope remains held; tier overrides do not grant owner approval.
- **No fabricated observations, in any section, ever.** If it isn't in a real result, it isn't in the card — even in the course of filling a template.
- **Attribution over reproduction.** Cite sources (DOI/PMID/accession); don't reproduce copyrighted text.

## Optional deliverables and helper commands

Use the current capability catalog, selected CLI parser and docs/user_guides/tools_reference.md for
helper availability, required inputs and output/write behavior. The historical twelve-item menu is
not a closed command inventory or proof that every helper is sign-off gated, requires a fully sealed
package, is read-only or leaves every score/file unchanged. Some helpers write fixed outputs/receipts
into a selected package or directory; some are advisory. Template emission, artifact validation,
independent scientific review, visual QA and release permission remain different lifecycle steps.
Reference existing source bytes in place; create only the requested owned output, never a new full
package/database copy merely to inspect a command.

## Quick reference index

| I need to… | Read |
|---|---|
| Start a session correctly (the front page) | `docs/BUNDLE_CAPABILITIES.md`, `AGENTS.md` |
| Author a Mode B card | `docs/MODEB_PROFILE_MATRIX.md`, `docs/MODE_B_AUTHORING_PREFLIGHT.md`, `docs/MODE_B_DOCUMENT_INDEX.md` |
| Get the claim-language rules right | `references/claim-safety.md`, `docs/MODE_B_CARD_CLAIM_SAFETY_AUDIT.md`, `tools/claim_safety_linter.py` |
| Write human-facing prose that doesn't read like an LLM | `references/prose-style.md` (audit pass; claim-safety hedges are exempt) |
| Compile a deliverable | `docs/DELIVERABLE_CONTRACT.md` |
| Emit a post-seal deliverable (cohort ledger, AF dossier, good-guesses, Mode-B docx/pdf, KCB locus map, novelty/count/sign-off) | `docs/GUIDE/02_Quick_Guide.md` §10, `docs/GUIDE/01_User_Manual.md` §4.3a, `docs/user_guides/tools_reference.md` §20 |
| Audit the pipeline (bunny hop) | `debugging_modules/BUNNY_HOP_AUDIT_GAME.md` |
| Cut a release / tiers | `CUT_PROTOCOL.md`, `tools/make_public_tier.sh`, `tools/sync_version.py` |
| Verify literature citations | `docs/BERT_MODE_PROTOCOL.md` |
| Run/resume BiG-SCAPE safely | `docs/LLM_COMPANION_TOOL_PROTOCOL.md`, `docs/BIGSCAPE_GCF_WORKFLOW.md`, `docs/SOPs/SOP-17_CrossStrain_GCF_Cohort.md` |
| Plan/run GToTree + IQ-TREE | `docs/LLM_COMPANION_TOOL_PROTOCOL.md`, `docs/phylogenomics.md` (user-approved preflight; one core/tree; ≤4 total) |
| Prepare a scoped handoff | Current user defaults, actual task state and `AGENTS.md`; use the historical eight-path checker only when that format is selected |
| Set up / run the engine | `docs/INSTALL.md`, `docs/PREREQUISITES.md`, `python mamey_run.py doctor` |

*The shared assistant entry point is `AGENTS.md`. Unless shown under `references/`, paths in this skill refer to the bundle root. Compare this companion discipline with the current contracts and update it when they diverge.*

The full48 contract names `FINISHED_FULL48_CURRENT_EVIDENCE` as its strict profile. Select and verify the requested profile explicitly; this name does not certify current50_v2 output, scientific acceptance or release readiness.
