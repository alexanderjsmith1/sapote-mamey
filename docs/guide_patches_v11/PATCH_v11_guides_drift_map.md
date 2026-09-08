# PATCH — v1.1 guide set → v9.7.23 drift map
## Targets: Quick Guide, User Guide, Technical Manual (all v1.1, 2026-06-03)

> These three guides are good and worth keeping — the audience-awareness, the reproducible
> worked example, and the three-workflow framing are strengths the newer docs lack. They are
> also stale: all three predate the two-layer Mamey/Sapote architecture and are versioned to
> **Sapote v8.9.9 / Mamey v0.1**, against the current **engine 1.9.31 / bundle v9.7.23**.
>
> This patch is a section-by-section drift map: what is stale, why, and the corrected fact.
> It does not rewrite the guides — it tells you exactly where to edit and what to. Companion
> patches supply drop-in replacement prose for the two highest-drift areas (the concepts
> front matter and the worked-example artifacts).
>
> Drift is graded: **[CONCEPT]** = the underlying model changed (highest priority);
> **[VERSION]** = a number/string moved; **[ADD]** = something true now that the guide
> predates; **[KEEP]** = flagged so a well-meaning edit doesn't remove a still-correct thing.

---

## The one conceptual change that drives most of the rest

**[CONCEPT] Mamey is no longer a prompt — it is a deterministic Python engine.**

Throughout the v1.1 set, Mamey is described as "Workflow 3," a *prompt you paste* into any
model to get triage output ("Paste the Mamey prompt as your first message"). That was true at
Mamey v0.1. It is now false. Mamey is the deterministic extraction engine; it reads antiSMASH
output and emits a sealed, checksummed evidence package. Sapote is the judgment layer that
interprets that package.

This is not a version bump — it inverts the relationship the guides describe. In v1.1, Sapote
is the heavy workflow and Mamey is the lightweight any-model fallback. In v9.7.23, **Mamey is
the deterministic foundation and Sapote is the judgment layer on top of it** — the two are
partners across one enforced boundary, not two alternative entry points at different access
tiers.

Every place the guides frame "Sapote vs Mamey" as a tier choice needs reframing as "Mamey
extracts, Sapote interprets." The three-*workflow* framing (paste-and-go / Projects / any-model)
is still useful as a description of *how a user runs the thing* — keep it — but it is no longer
the same axis as "Sapote vs Mamey," and the guides currently conflate the two.

---

## Quick Guide (v1.1) — drift

- **[VERSION]** Header reads "v8.9.9 & Mamey v0.1." → engine 1.9.31 / bundle v9.7.23.
- **[CONCEPT]** The whole "Which workflow?" table maps access tier → Sapote-or-Mamey. Reframe:
  the run *modes* (paste-and-go / Projects / any-model) are real; "Mamey" as the free-tier
  fallback is not — Mamey is the engine underneath all of them now. Simplest fix: rename the
  third row's payload from "Workflow 3: Mamey" to a genuinely model-light *Sapote triage* mode,
  and describe Mamey separately as the deterministic engine the package comes from.
- **[KEEP]** The trigger-phrase catalogue (full analysis / archive-quality / smoke-test /
  continuation / single-module scans / CCSM / literature) is still accurate in shape and worth
  preserving verbatim where the module still exists.
- **[ADD]** Single-module scan list is missing the current scans: add **RG-GMCI** (cross-contig
  adjudication), **EFLS** (edge-flank linkage), **UMED** (maturation-gap), **resistance tiers**.
  The list has CCTT, LMPKS, CGAD, KCB, ecological, resistance, fermentation, taxonomy — add the
  four newer ones or note they run inside the default pass.
- **[ADD]** No mention of the four release tiers or the public/unpublished guard. A one-line
  note belongs here for anyone cutting a shareable package: "AS strains never enter a public
  cut; any merged set with AS data is PRIVATE."

## User Guide (v1.1) — drift

- **[VERSION]** "Sapote workflow v8.9.9 · Mamey spec v0.1" throughout the front matter and
  worked-example header → current engine/bundle.
- **[CONCEPT]** §1 Introduction and §3 "Which workflow is right for you?" both present Mamey as
  the no-setup, any-model *alternative to* Sapote. Reframe per the conceptual change above. The
  claim-safety paragraph in §1 is **[KEEP]** — it is still exactly right and well-phrased.
- **[CONCEPT]** §6 "Workflow 3 — Mamey" describes pasting a prompt and getting a Markdown
  document back. Replace with: Mamey is run as a deterministic engine producing a sealed
  package (intake, inventory, triage board, RG-GMCI outputs, workbook, provenance, checksums,
  manifest). See the companion package-renderer patch for what that package contains and the
  honest note that the user-facing brief is the in-progress addition.
- **[VERSION]** §7.2 handshake example: "antiSMASH v8.0.4," "25 sheets," "depth floor (v8.9.9)"
  — re-point to current antiSMASH version run, current sheet count, current depth-floor logic.
  The *structure* of the annotated handshake is **[KEEP]** — it teaches well.
- **[KEEP]** §7.4 the BGC48 pulvomycin-override story is excellent and still valid — one vivid
  case of the hallucination-trap catching a wrong antiSMASH label. Keep it; it is the single
  best teaching moment in the guide. Optionally **[ADD]** a second modern case: the kcb_top
  genome-self-hit fix (a cluster whose displayed anchor was the whole chromosome until the fix
  surfaced the real MIBiG line) is the same lesson at cohort scale.
- **[VERSION]** §7.6 output package: "25 sheets," the file list — re-point to the current sealed
  package contents. **[ADD]** the honest gap: the sealed package today ships no reader-facing
  PDF/figure; the brief renderer (separate patch) closes that.
- **[ADD]** §9 deliverables: no architecture-capacity column, no DAPR dual-track table named as
  such, no RG-GMCI verdict. Add these to the deliverables inventory.

## Technical Manual (v1.1) — drift

- **[VERSION]** Titled "Sapote v8.9.9 — Technical Reference v1.1." → current.
- **[KEEP]** §2 the two-axis model (Lead Priority vs Claim Confidence, evidence tiers, safe-claim
  ladder, named hallucination traps) is the conceptual core and is still exactly right. Do not
  touch the model; only update counts and add the newer modules around it.
- **[CONCEPT]** §4 "The Nine First-Pass Scan Modules" → the scan set has grown and been split.
  Current detection is better described as **three detectors** (KCB anchors, T43 keyword markers,
  architecture-capacity) **plus the supporting scans** (FLBR, EFLS, UMED, CGAD, CCTT, resistance,
  bldA/TTA, TFBS) **plus RG-GMCI** cross-contig adjudication. The "nine first-pass scans" framing
  predates the architecture-capacity layer entirely — that layer is the single biggest addition
  and must be written in. See the concepts patch for the drop-in detector-stack description.
- **[ADD]** No architecture-capacity layer (`class_architecture.py`), no kcb_top correctness fix,
  no reference-panel validation ledger, no four-tier release with gates, no enforced
  deterministic/judgment boundary audit. These are the v9.x contributions and the technical
  manual is where they belong in depth — pull from the Operating Manual Parts II and V.
- **[VERSION]** §5 "25-sheet schema" → confirm current sheet count against the live workbook
  generator before printing; it has moved across versions (24/25 depending on the cut).
- **[KEEP]** §6 the Python scripts (`sapote_completeness_audit.py`, `sapote_excel_generator.py`,
  `sapote_pdf_styles.py`) and the LOCK/denominator/render audit invocations are still real and
  still the right reproducibility story — keep, and **[ADD]** the newer companion tools
  (`reference_panel_ledger.py`, `class_architecture.py`, `bank_architecture.py`).
- **[ADD]** §8 CCSM is still valid; add a note that cohort-local layers (product-class matrices,
  pan-genome families) must be recomputed after a merge, never concatenated — the merge-handling
  rule the v1.1 manual predates.
- **[KEEP]** §9 claim-language reference (avoid → use translations) is timeless — keep verbatim.

---

## Suggested patch order

1. Apply the **[CONCEPT]** Mamey-is-an-engine reframe everywhere first — it touches all three
   guides and everything else reads oddly until it is done.
2. Drop in the **concepts/front-matter patch** (companion file) for the corrected two-layer
   description, the detector stack, and the claim-safety conventions.
3. Update the **worked example** with the artifact patch (companion file) so the
   *S. amethystogenes* spine shows current handshake, package, and the architecture column.
4. Sweep the **[VERSION]** strings last — mechanical, do it in one pass against the live engine.
5. Leave every **[KEEP]** untouched; they are the parts that have aged well.
