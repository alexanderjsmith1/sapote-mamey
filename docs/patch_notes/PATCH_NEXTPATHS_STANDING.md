# PATCH — CDSW Next-Paths: Standing Continuation Path
**Patch ID:** NEXTPATHS_STANDING_20260624  
**Applies to:** Sapote (Claude / LLM tier) — CDSW protocol, `prompts/CLAUDE_SYSTEM_PROMPT.md §12`  
**Bundle version:** v9.7.121+  
**Status:** ACTIVE  
**Authority:** aligns the Claude-tier CDSW rule with the ChatGPT-tier rule already in
`prompts/MAMEY_CHATGPT_EXECUTION_PROMPT.md:229`.

---

## Problem this patch fixes

A session produced a 59-page PDF for a strain and then offered five "next paths" — none
of which was "continue working on this strain." The five paths pointed elsewhere (other
strains, other analyses) while the strain in hand still had most of its Mode B cards and
contract deliverables unwritten. The most obvious next action — keep going on the strain
that is right here, half-finished — was omitted entirely.

**Root cause (verified in the tree):** the ChatGPT-tier execution prompt already carries
the fix —

> *"Standing paths, listed first when applicable: if any BGC in the strain lacks full
> §1–§8 Mode B, path #1 is 'Continue deeper Mode B: run the next batch (BGC[list]) to
> full §1–§8' (the most-missed path — never drop it while BGCs remain)."*
> — `MAMEY_CHATGPT_EXECUTION_PROMPT.md:229`

— but the Claude-tier system prompt (`CLAUDE_SYSTEM_PROMPT.md §12`) does **not**. The
Claude rule says "genuinely different directions" and "strategically differentiated,"
which actively pushes AWAY from listing the continuation, because continuing looks like
"more of the same" rather than a "different direction." The differentiation instruction,
without the standing-path carve-out, is what dropped the obvious path.

---

## Core rule (added to Claude-tier CDSW §12)

**While the strain in hand has unfinished contract work, the continuation is path #1 —
always — and it does not count against the "genuinely different directions" requirement.**

Specifically, prepend these standing paths, in this order, before the differentiated
paths:

1. **If any scorable BGC lacks full §1–§8 Mode B:** path #1 is
   *"Continue Mode B on [StrainID]: card the next batch ([specific BGC IDs]) to full
   §1–§8"* — naming the actual remaining BGCs. This is the most-missed path. Never drop
   it while BGCs remain uncarded.
2. **If Mode B is complete but contract items remain 🔲:** path #1 is
   *"Continue [StrainID]: produce [next missing contract deliverable]"* — naming the
   specific deliverable (Ecology Synthesis, Bench Guide, DAPR, etc.) from the Control
   Panel's remaining list.
3. **Only once the strain's 13-item contract is fully satisfied** do the next-paths
   become purely differentiated directions (other strains, cross-strain work, cohort
   synthesis, engine work).

The standing continuation path is **exempt from the differentiation rule** — it is
allowed to be "more of the same strain" precisely because finishing the strain in hand
is the correct default, not a failure of imagination.

---

## Why differentiation alone caused the failure

The Claude §12 rule optimizes for breadth ("genuinely different directions"). That is
the right instinct when a deliverable is actually finished — it surfaces options the
user might not have considered. But applied to a HALF-finished strain, it produces the
exact pathology seen: it treats "keep going on this strain" as insufficiently novel and
omits it, sending the user toward five new directions while the current work sits
abandoned at 50%. The fix is not to weaken differentiation — it is to make the
continuation a standing path that sits ABOVE the differentiated set, so breadth is
offered without abandoning the strain in hand.

---

## Consistency with the Control Panel

The Control Panel already computes what's unfinished (the 🔲 / ⚠️ contract rows and the
Mode B `[W of X]` count). The standing continuation path reads directly from that:

- Control Panel shows Mode B `6 ⚠️ 10 of 48` → path #1 names the next batch of the 38
  uncarded BGCs.
- Control Panel shows all Mode B ✅ but Ecology Synthesis 🔲 → path #1 is "produce the
  Ecology Synthesis."

The Control Panel's CRITICAL PATH line and next-paths path #1 should agree — if they
disagree, the Control Panel's critical-path computation is the source of truth.

---

## Exact edit to CLAUDE_SYSTEM_PROMPT.md §12

Append to the existing §12 paragraph:

> **Standing continuation path (listed first when applicable, exempt from the
> differentiation requirement):** While the current strain has unfinished contract work,
> path #1 is the continuation — if any scorable BGC lacks full §1–§8 Mode B, path #1 is
> "Continue Mode B on [StrainID]: card [next BGC IDs] to full §1–§8" (the most-missed
> path — never drop it while BGCs remain); if Mode B is complete but contract items
> remain, path #1 names the next missing deliverable. Only once the strain's 13-item
> contract is satisfied do all paths become purely differentiated directions. The
> continuation path may be "more of the same strain" — that is correct, not a failure of
> differentiation.

---

## Implementation checklist

- [ ] Append the standing-continuation paragraph to `CLAUDE_SYSTEM_PROMPT.md §12`
- [ ] Verify the Claude rule now matches the ChatGPT rule at execution-prompt:229
- [ ] Cross-check: path #1 always agrees with the Control Panel CRITICAL PATH line
- [ ] Add to the CDSW skill (`mamey` skills package) so it is enforced session-to-session

---

*Next-Paths Standing Continuation Patch v1.0 · Sapote–Mamey v9.7.121 · 2026-06-24*
