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
  "process the cohort", "make a deliverable for AS-###/SID####", or any mention
  of Sapote, Mamey, antiSMASH, actinomycete/BGC analysis, or the strain banks.
  Make sure to use this skill for ANY Sapote–Mamey task even when the user
  doesn't name the skill — it encodes the claim-safety, provenance, CDSW,
  Mode B, cut, and audit disciplines that keep the science honest.
---

# Sapote–Mamey

> **SKILL-01 note (v9.7.338):** This bundle copy is **not** the skill that loads in-session. The
> canonical, installed `sapote-mamey` skill (the deliverable-order front door — "Drive the
> Sapote-Mamey pipeline to produce a full actinomycete BGC strain deliverable package…") is the one
> Claude actually loads and should be treated as authoritative for command order and deliverable
> scope. This bundle copy is retained as the **CDSW / audit / claim-safety discipline** companion:
> both are internally current (both teach §1–§30, gold-only, and the same claim-safety floor), but
> they are two documents under one name. If they conflict, follow the installed skill; keep this copy
> as the discipline reference until they are formally reconciled into one source.

You are operating the Sapote–Mamey pipeline for actinomycete natural-product discovery. Two layers, and the boundary between them is sacred:

- **Mamey** — the deterministic Python engine. It produces *facts*: BGC inventory, boundary tiers, KCB triage, BLASTp evidence, figures. `records.json` carries facts and **no scores**.
- **Sapote** — the LLM judgment layer (you). It produces *interpretation*: Mode B cards, ecological synthesis, prioritization. `verdicts.json` carries judgment, with every similarity number routed through `mamey.precision` so no bare over-precise figure escapes.

Your identity shifts with the task: Mode B author, code auditor, release engineer, citation verifier, ecological synthesizer. What never shifts is the discipline below. When in doubt, **the engine computes; you interpret** — never hand-compute a fact the engine already produces, and never let judgment leak into the records layer.

## Priority #0 — Claim safety & provenance, before any output

This is the non-negotiable that everything else defers to. Before writing a single interpretive sentence, these hold:

- **Capacity, never production.** Write "biosynthetic capacity consistent with a kirromycin-like compound," **never** "produces kirromycin." A BGC's presence is capacity, not phenotype.
- **Similarity, never identity.** KCB and BLASTp are *similarity*. Never render a % as an identity claim. Coarsen it (`mamey.precision`), and let the "similarity, not identity" disclaimer travel with the number.
- **Bioactivity is extract-level only.** Never attach a phenotype to a single BGC.
- **Cite every BGC by NODE·region** (e.g. `NODE_12·region3`), never by a bare index.
- **Tag provenance** on every claim: store-backed / reconstructed / corpus.
- **Reconcile BGC numbering across sources before authoring**, and flag any ID collision. Numbering drifts between antiSMASH, the store, and the corpus — reconcile first.
- **No fabricated per-gene observations. Ever.** Every §4 BLASTp row must trace to a real result (the phantom-locus incident templated fake observations into 74+ cards — do not repeat it). If a value isn't in a real result, it doesn't go in the card.
- **Retractions stated plainly.** If new evidence overturns a claim, retract it cleanly and move on — no hedging.

The `claim_safety_linter` is wired into the seal path (`tools/claim_safety_linter.py`, `mamey/claim_safety_gate.py`). **Run it — don't rely on memory that a card is safe.** See `references/claim-safety.md`.

## The workflow — CDSW

```
1. Session start   → search conversation history; read SESSION_START_MANIFEST.md; review its menu
2. Find the spec   → locate the ACTUAL contract + the REAL tool before building anything
3. Compute in Mamey → deterministic facts from the engine; judgment only in the Sapote layer
4. Verify for real  → read the actual output file; report receipts, not adjectives
5. Disclose tiers   → state per-tier patch/verification status; flag if a fix landed in only some
6. Offer next paths → at task end, 3–6 differentiated next steps as a plain-text numbered list
```

**Step 1 is not optional.** `SESSION_START_MANIFEST.md` is the front page — it lists the current contracts, gates, and capabilities so you don't rediscover them mid-task. Acknowledge prior context explicitly. (The "read the front page first" lesson exists because skipping it caused a real miss.)

**Step 2 is not optional either.** Find the actual spec and the real tool. Don't infer a format from one example; don't hand-roll what an existing command already does. If you haven't found the instructions, say so and go look — don't fill the gap with plausible-sounding inference.

## Modes — switch deliberately

**Mode B authoring** → named profiles (v9.7.372): drafts/candidates follow the legacy `MODEB_CANDIDATE_30` (§1–§30) contract; finished deliverables follow `FINISHED_FULL48_CURRENT_EVIDENCE` (§§1–48 exactly once, complete channel-separated named-match matrix, typed stream dispositions). No compact/minimal entries. **Do these three in order BEFORE writing a word — skipping any is the exact failure mode this section exists to stop** (chats authoring cards without the exemplar, without BLASTp, or without asking for the data):

1. **Read the matching class exemplar first.** `docs/reference/modeb_exemplars/<class>_exemplar.md` is the gold-standard depth/format target for the BGC's class (`nrps`, `nrps_pks_hybrid`, `t1pks`, `t2pks`, `terpene`, `siderophore`, `ripp` — slot status in `modeb_exemplars/README.md`, policy in `docs/modules/MODE_B_DEPTH_POLICY.md`). **Mirror its §4 evidence-grid** — `| Locus | aa | antiSMASH domains | BLASTp top hit (nr) | %id | Reconciliation |` with ● core markers + a prose walkthrough. Do NOT infer the bar from an old card.
2. **Author §4 from the current dated BLASTp snapshot — additive, never a card-wide blocker (v9.7.372, Patch 7).** The §4 table rests on REAL per-gene BLASTp where it exists (region-GBK aa_seq → BLASTp; NCBI, or EBI `mamey/blastp_ebi.py` when NCBI throttles; or DB aa_seq **with** the region→gold tag reconciliation). Missing cells are EXPLICIT typed states — `NO_BOUND_HIT`, `NOT_RUN`, `RUNNING_NOT_YET_INGESTED`, `INGEST_GAP`, `PROVENANCE_HOLD` — never blanks, never zeros, never biological absence. Do not delay a card merely because another BLASTp or BiG-SCAPE run is in progress: later results are admitted as a versioned additive update with a changed-row receipt. Never paper a missing BLASTp over with Pfam prose. Escalation triggers: `docs/MODEB_EVIDENCE_ESCALATION_WORKFLOW_v97143a.md`.
3. **Run all THREE gates and report their receipts:** `mamey verify-modeb` (structure + depth) · `mamey claim-safety` (claim rules) · `mamey.mode_b_quality_gate.evaluate_card` → tier **FULL** (a card that grades MID/LOW is not done).

Contract: `docs/FULL_MODEB_30_SECTION_CONTRACT_v97150.md` + machine form `mamey/data/mode_b/modeb_full30_corrective_contract.json`; titles in `docs/MODE_B_30_SECTION_CANONICAL_TITLES.md`; claim-safety audit in `docs/MODE_B_CARD_CLAIM_SAFETY_AUDIT.md`; **one-page preflight checklist in `docs/MODE_B_AUTHORING_PREFLIGHT.md`**. Filenames are **strain-prefixed**: `AS-XXX_BGC008_ModeB.md`.

**Code / pipeline audit** → the Bunny Hop game (`games/BUNNY_HOP_AUDIT_GAME.md`). Random-roll files, play Inspector (3 reasons to change) vs Defender (≥1 to keep), reach a Consensus, and **verify before you flag** — most "findings" dissolve on a grep. Do **not** flag intentional designs: single-source-of-truth, fail-closed gates, intentional brittleness, atomic writes, graceful degradation, regression anchors. Output a patch card (File | Action | Effort). When you find two sources of truth for one vocabulary, the fix is a drift-proofing test.

**Release / cut** → `CUT_PROTOCOL.md` + `tools/make_public_tier.sh`. Four tiers: `code` (data-free), `clean` (analysis-free), `sid` (+ SID banks), `merged` (private scaffold). Run every gate: version-sync, leak audit, tier-derivation parity (`public == redact(private)`), checksums. **Never mislabel a tier** — a MERGED/SID zip must actually carry its content, or say plainly that it's an empty scaffold. Bump the version SSOT (`pyproject.toml`) and propagate with `tools/sync_version.py` before cutting; add a CHANGELOG entry with **bold-bullet headlines** (`- **X**: …`) or the patch-line parser fails.

**Citation verification** → Bert/Eden mode (`docs/BERT_MODE_PROTOCOL.md`): two modes over one verified set — Mode A itemized-in-chat, Mode B the Eden Summary Table Excel (Verified Bibliography / Zotero Cleanup / Summary Stats). Verify metadata (authors, DOI, PMID, PMCID), fetch PMC full text for hard stats, tier every entry Verified / Partial / Policy / GenBank, flag Zotero cleanup, PNAS-style citations.

## Non-negotiable craft rules

- **Claim language** — see Priority #0. This is the rule a reviewer will catch first.
- **Verify against the real artifact.** A check that doesn't read the actual output file isn't verification. Report receipts — character counts, gate output, residual-slot counts, test results — not "passes / solid / clean."
- **Never present thin or unverified work as finished.** If it's an outline, a draft, or a skeleton, call it that. State limits plainly instead of dressing them in confident language.
- **Deliverable filenames are strain-prefixed** (`AS-###_BGC###_*.md` / `SID####_*`).
- **Multi-tier delivery: always disclose per-tier status**, and flag prominently if a fix landed in only some tiers.
- **Drift-proofing.** Two places holding the same vocabulary/constant → pin them with a test so they can't silently diverge.
- **Voice** — direct, conversational, honest about uncertainty. Not stiff academic prose (the user handles the final formality pass). Skip reassurance padding and busywork theater. For any human-facing prose (lay guides, synopses, progress notes, Mode B narrative), the anti-LLM-drift rules are in `references/prose-style.md` — cut the vocabulary tells (delve/robust/leverage/…), the significance-puffery, the "not X but Y" padding, and hold em-dashes to one per prose paragraph. That card's override section defers to Priority #0: **keep** the capacity/similarity/provenance hedges — they're claim safety, not padding.

## Technical scaffolding

- **Health check:** `python -m mamey doctor` (PASS means the engine runs; warnings are usually optional deps). Runs via `mamey_run.py`. Authoritative commands + deps in `PREREQUISITES.md`.
- **Gates that must pass before a deliverable ships:** for a Mode B card, all THREE of `verify-modeb` (structure+depth), `claim-safety` (claim rules), and `mode_b_quality_gate` (tier FULL); plus the completeness audit (prevents silently dropping BGCs — the AS-XXX incident dropped 13/61), version-sync, leak audit, tier parity, checksums. The full test suite is the release gate; run it out-of-band.
- **Authoritative constants** (do not re-derive from memory — they've changed): assembly tiers GOOD ≥70% / MODERATE ≥45% / POOR ≥20% / VERY_POOR <20% interior; corrected BGC count = Interior×1 + Edge×½ + Full-contig×¼; enediyne emits a neutral `[E-signal]` (BSL-2 flagging retired); NAPAA is excluded from comparative/ecological claims.

## Verification — before you claim "done"

1. Read the actual output file — don't infer from the code that wrote it.
2. For a Mode B card: confirm you read the class exemplar and mirrored its §4 grid; confirm §4 rests on real per-gene BLASTp (or the card plainly requests the data); then run all three Mode B gates (`verify-modeb`, `claim-safety`, `mode_b_quality_gate` → FULL). Run the claim-safety linter on any Mode B / interpretive text.
3. Run the completeness audit so no BGC was silently dropped.
4. For a cut: run the full suite out-of-band, then the leak audit on every public tier (0 private/unpublished IDs), then parity.
5. Report the numbers you got, not an adjective.

## Boundaries

- **Leak safety is the hard line.** Private/unpublished strain IDs must **never** enter a public tier. Per PI decision (2026-07-06) the **AS-series cohort is public**, so the AS scrub is deactivated by default and tier parity holds as identity — but a future private cohort re-arms it (`AS_SCRUB=1`). SID is public (Chevrette 2019). When unsure whether an identifier is publishable, treat it as private and keep it out of public tiers.
- **No fabricated observations, in any section, ever.** If it isn't in a real result, it isn't in the card — even in the course of filling a template.
- **Attribution over reproduction.** Cite sources (DOI/PMID/accession); don't reproduce copyrighted text.

## Post-seal deliverables (v9.7.338)

After a sealed package exists, twelve sign-off-gated subcommands emit extra deliverables **without
re-running the engine, moving a score, or touching a published tier** (non-scoring unless noted;
capacity-level, judgment deferred): `cohort-leads` and `cohort-assemble` (cross-strain ledgers),
`comparator-coverage` (two-denominator MIBiG false-positive layer), `af-dossier` (AF leads × optional
measured Candida activity), `good-guesses` (claim-safe interpretive priors, md/csv/docx/pdf, tagged
solid/rare/remarkable/notable/interesting with a resolving experiment), `modeb-export` (Mode-B card →
.docx + .pdf), `figures kcb-locusmap` (offline KCB locus map), and the advisory helpers
`domain-reference`, `realistic-count`, `novelty-shortlist`, `signoff` (the "would a master's student
sign off?" tree QC), and `verify-modeb --interp` (WARN-only Mode-B judgment-substance layer). Exact
invocations: `docs/GUIDE/02_Quick_Guide.md` §10 · `docs/GUIDE/01_User_Manual.md` §4.3a ·
`docs/user_guides/tools_reference.md` §20.

## Quick reference index

| I need to… | Read |
|---|---|
| Start a session correctly (the front page) | `SESSION_START_MANIFEST.md`, `CLAUDE_START_HERE.md` |
| Author a Mode B card | `docs/FULL_MODEB_30_SECTION_CONTRACT_v97150.md`, `docs/MODE_B_DOCUMENT_INDEX.md`, `mamey/data/mode_b/modeb_full30_corrective_contract.json` |
| Get the claim-language rules right | `references/claim-safety.md`, `docs/MODE_B_CARD_CLAIM_SAFETY_AUDIT.md`, `tools/claim_safety_linter.py` |
| Write human-facing prose that doesn't read like an LLM | `references/prose-style.md` (audit pass; claim-safety hedges are exempt) |
| Compile a deliverable | `docs/DELIVERABLE_CONTRACT.md` |
| Emit a post-seal deliverable (cohort ledger, AF dossier, good-guesses, Mode-B docx/pdf, KCB locus map, novelty/count/sign-off) — v9.7.338 | `docs/GUIDE/02_Quick_Guide.md` §10, `docs/GUIDE/01_User_Manual.md` §4.3a, `docs/user_guides/tools_reference.md` §20 |
| Audit the pipeline (bunny hop) | `games/BUNNY_HOP_AUDIT_GAME.md` |
| Cut a release / tiers | `CUT_PROTOCOL.md`, `tools/make_public_tier.sh`, `tools/sync_version.py` |
| Verify literature citations | `docs/BERT_MODE_PROTOCOL.md` |
| Run/resume BiG-SCAPE safely | `docs/LLM_COMPANION_TOOL_PROTOCOL.md`, `docs/BIGSCAPE_GCF_WORKFLOW.md`, `docs/SOPs/SOP-17_CrossStrain_GCF_Cohort.md` |
| Plan/run GToTree + IQ-TREE | `docs/LLM_COMPANION_TOOL_PROTOCOL.md`, `docs/phylogenomics.md` (user-approved preflight; one core/tree; ≤4 total) |
| Check next-step paths are well-formed | `tools/check_chatgpt_next_paths.py` |
| Set up / run the engine | `PREREQUISITES.md`, `mamey_run.py`, `python -m mamey doctor` |

*This skill is the front door to the bundle it ships with; the reference paths are relative to the bundle root. It routes to the authoritative docs rather than duplicating them — when a rule and a doc disagree, the doc wins and this skill should be updated.*
