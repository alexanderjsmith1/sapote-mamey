# Control Panel Readout Contract
**Historical patch ID:** PROGRESS_REPORTING_20260624 / CONTROL_PANEL  
**Applies to:** Sapote (Claude / LLM judgment tier)  
**Bundle version:** v9.7.121+  
**Status:** ACTIVE — front-facing, mandatory  
**Authority:** extends `PATCH_PROGRESS_REPORTING_20260624`; the deliverable contract is
`FULL_RUN_PROFILE §A` (13 items) + Tier-2 packaging, as enforced by
`tools/check_deliverable_suite.py` against `docs/DELIVERABLE_MANIFEST_TEMPLATE.md`.

---

## What this is, and what it is NOT

The Control Panel is the front-facing readout a user sees after every deliverable
hand-off. **Its core is the deliverable contract** — the actual 13 scientific
deliverables a full run owes, each with live status. The gauges (run performance, BGC
census) are *supporting readouts arranged around the contract*, not a replacement for
it.

**The failure this closes:** AS-XXX was reported "finished" while the contract sat at
~15% — most of the 13 deliverables did not exist. The user only found out by asking.
The problem was never missing telemetry; it was **the scientific deliverables the user
actually wants not being produced, and that absence being hidden.** The Control Panel
exists to put the un-produced deliverables in front of the user's face on every
hand-off, so "we have 3 of 13" can never again read as "done."

The deliverable checklist is the heart of the panel. Gauges never push it below the
fold.

---

## THE CONTROL PANEL — canonical template

```
═══════════════════════════════════════════════════════════════
 CONTROL PANEL — [StrainID]
 [genus sp.] · [host] · [region] · [date] · [session label]
═══════════════════════════════════════════════════════════════
 DELIVERABLE CONTRACT: [N] of 13 · Mode B [W]/[X] cards
 [raw] raw → [corr] corrected BGCs · Engine Mamey [ver]
═══════════════════════════════════════════════════════════════

 FULL-RUN DELIVERABLE CONTRACT (FULL_RUN_PROFILE §A)
───────────────────────────────────────────────────────────────
  1 [✅/⚠️/🔲/🔒]  Assembly declaration + BGC inventory
  2 [✅/⚠️/🔲/🔒]  Architecture confidence grades
  3 [✅/⚠️/🔲/🔒]  WL scoring + Triage First Board
  4 [✅/⚠️/🔲/🔒]  Hallucination-trap audit (all BGCs)
  5 [✅/⚠️/🔲/🔒]  CCTT routing / §57 sub-grades / bldA-TTA /
                    resistance tiers / UMED / EFLS
  6 [✅/⚠️/🔲/🔒]  Full Mode B for EVERY BGC          [W of X]
  7 [✅/⚠️/🔲/🔒]  DAPR — dual AB/AF priority tracks
  8 [✅/⚠️/🔲/🔒]  Mechanistic Ecology Synthesis      [host]
  9 [✅/⚠️/🔲/🔒]  Fermentation / Induction / Extraction Plan
 10 [✅/⚠️/🔲/🔒]  Layperson-Ranked BGC Guide
 11 [✅/⚠️/🔲/🔒]  Compound Detection & Isolation Bench Guide
 12 [✅/⚠️/🔲/🔒]  Missingness register
 13 [✅/⚠️/🔲/🔒]  Full-run output gate check (Section H)

 PACKAGING (Tier-2 contract)
───────────────────────────────────────────────────────────────
    [✅/⚠️/🔲/🔒]  Master workbook surfaced (xlsx)
    [✅/⚠️/🔲/🔒]  Sapote sheets S1–S5 appended
    [✅/⚠️/🔲/🔒]  manifest.json + SHA-256 checksums
    [✅/⚠️/🔲/🔒]  Final ZIP bundled

 FIGURES
───────────────────────────────────────────────────────────────
    [✅/⚠️/🔲]  Locus maps               [N of X]  [missing leads]
    [✅/⚠️/🔲]  Maps co-located w/ Mode B (A2.5)

═══════════════════════════════════════════════════════════════
 GAUGES
───────────────────────────────────────────────────────────────
 BGC CENSUS   Interior [n] / Edge [n] / FC [n]   ·   KCB-dark [n]/[X]
              Top AB: [BGCxxx] [score]   Top AF: [BGCxxx] [score]
              Flags: [n] misanchor · [n] mobile · [n] UMED · [n] mismatch
 RUN HEALTH   Parse-conf [H/M/L]  ·  Extraction: [which artifacts emitted/failed]
              Concordance: [n] CONCORDANT / [n] DISCORDANT / [n] NO_REF
 RELEASE      [PRIVATE / PUBLIC]  ·  leak-audit [PASS/FAIL/—]
 ASSEMBLY     [tier]  ·  [interior]%  ·  [n] long-read-gated leads
 SCORE-DELTA  [n] discrepancies vs prior worker_diff / COMPLETE
 SESSION      +[n] cards · +[n] figures · +[n] corrections this session
═══════════════════════════════════════════════════════════════
 THIS SESSION PRODUCED: [specific files/sections added today]
 REMAINING: [count] of 13 contract items + [n] Mode B cards + Tier-2
 ▶ CRITICAL PATH: [single most important next step + why]
═══════════════════════════════════════════════════════════════
```

---

## The deliverable contract is mandatory and authoritative

The 13-item list above is **`FULL_RUN_PROFILE §A`**, the same list
`tools/check_deliverable_suite.py` validates against `docs/DELIVERABLE_MANIFEST_TEMPLATE.md`.
It is the contract. Rules:

- **All 13 rows always present.** A 🔲 not-started row is the information the user needs.
  Never drop a row because it is empty — the empty rows ARE the readout.
- **Status vocabulary mirrors the manifest:** ✅ = COMPLETE (give the artifact path),
  ⚠️ = partial (Notes say what exists / what's missing), 🔲 = not started,
  🔒 = blocked (name the blocker). These map to the manifest's COMPLETE / SKIPPED / N/A
  with a partial state added for live mid-run reporting.
- **Item 6 (Full Mode B for EVERY BGC) carries `[W of X]` against the full scorable
  count**, never the carded count. FULL ANALYSIS MODE means every BGC owes a card, so a
  strain with 3 HIGH cards and 45 uncarded BGCs reads `6 ⚠️ 3 of 48`, never `6 ✅`.
- **The headline line reads `[N] of 13`.** That number is the one whose absence caused
  the AS-XXX incident. It is non-negotiable and sits at the top, above the gauges.

---

## GAUGES — supporting readouts (the eight approved)

These sit BELOW the deliverable contract. They never displace it. Each reads from a
real engine field.

| # | Gauge | Reads from | Shows |
|---|---|---|---|
| 3 | **Edge-status breakdown** | `edge_status` | Interior / Edge / Full-contig counts — assembly truncation at a glance |
| 4 | **KCB-dark fraction** | `kcb_cumulative` null/below-threshold | the novelty frontier — count of anchor-less BGCs |
| 5 | **Top AB / Top AF leaders** | `ab_score`, `af_score` | the named strongest antibacterial and antifungal leads |
| 7 | **Flag census** | `misanchor_flag`, `mobile_element_flag`, `umed_gap_flag`, class-mismatch | all engine caution flags on one line |
| 8 | **Parse-confidence + manual-check** | `parse_confidence`, `needs_manual_kcb_check` | how trustworthy the KCB assignments are |
| 10 | **Extraction completeness** | which package artifacts emitted | names what failed (e.g. the AS-XXX workbook write that failed at source-locator) |
| 11 | **Concordance** | `concordance_verdict` | CONCORDANT / DISCORDANT / NO_REFERENCE — anchors corroborated vs. similarity-only |
| 13 | **Session-delta** | diff vs. session-start state | +cards / +figures / +corrections produced today |

Plus the five mandatory gauges promoted earlier (score-correction, claim-safety,
release, assembly, engine-version), which are folded into the GAUGES block and the
headline line above.

---

## When the panel fires

Same triggers as the parent patch's progress block: after a batch of Mode B cards,
a triage pass, a Mamey run, a `_COMPLETE_vN.md` assembly, session start with partial
prior work, or any "how far are we? / what's left? / what's done?" question. NOT after
every individual card. Order at end of a substantive turn: **Control Panel first**
(backward-looking), **CDSW next-paths second** (forward-looking).

---

## Condensed form (space-tight turns)

The deliverable contract line and critical path are never dropped, even condensed:

```
**Control Panel — [StrainID]:** [N] of 13 contract · Mode B [W]/[X]
✅ This session: [list]
⚠️ Partial: [list with what's missing]
🔲 Not started: [contract items not begun]
🔒 Blocked: [blocker]
▶ Critical path: [next step]
```

---

## Banned words still apply

"done / complete / finished / full" are not status claims. "Complete" survives only as
a filename component (`AS-XXX_COMPLETE_v1.md`) or a quoted contract deliverable name.
A panel showing `3 of 13` is the honest replacement for "the strain is finished."

---

**Filed by:** Sapote (Claude / LLM tier) · 2026-06-24  
**Review required:** No — behavior/reporting patch, applies immediately. The 13-item
contract is sourced from FULL_RUN_PROFILE §A / docs/DELIVERABLE_MANIFEST_TEMPLATE.md; if that
contract changes, this panel's deliverable list changes with it.
