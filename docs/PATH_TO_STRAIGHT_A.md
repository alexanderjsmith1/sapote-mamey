# PATH TO STRAIGHT A's — Sapote–Mamey v9.7.96 → v9.7.97

**From:** Patch Chat · **Date:** 2026-06-20 · Companion to the readiness scorecard.

You asked for straight A's and whether the answer is more tests (2000?). Short version: **the test count is a red herring, and a couple of the A's can't honestly be reached by tooling — they're gated on science or one online step.** Here's the area-by-area truth, with what I built this turn.

---

## First: the test-count question

The suite is **1,132 test functions / 190 files** (the "~1,400" was loose). The gap that bit us — `sync_version` orphaned despite all those tests — was **not** a missing unit test. It was that **no test asserted invariants about the gate system itself**. 600 filler tests wouldn't have caught it; they'd just make the suite slower. Coverage holes that actually exist, by risk:

- **Zero-test modules** (4): `cohort_figures_d/g`, `cohort_figure_captions`, `package_addons_html` — all figure/HTML presentation, low correctness risk.
- **Thin vs. risk:** `antismash_evidence` (1,069 loc, 4 test files) — this is the *input-parsing* layer everything depends on; thin here is the real unit-test priority. `cross_strain_figures` / `master_figure_atlas` (1 file each) feed *comparative* outputs.

So the honest test answer: **the meta-tests I built this turn close the root-cause hole; beyond that, ~40–80 *targeted* tests on `antismash_evidence` and the comparative path would matter — not 600 on already-covered code.**

---

## Moved to A **this turn** (built + proven)

### Gates: A− → **A**
Built `tools/gate_registry.tsv` (every check tool classified WIRED or OPERATOR_ONLY) + `tests/test_gate_wiring_invariant.py`. This is the structural fix for the orphan-gate class:
- It **fails** if any gate tool is un-registered (proven: a synthetic `check_imaginary_new_gate` trips it).
- It **fails** if a gate marked WIRED loses its wiring (proven: `sync_version` is referenced in 6 files; remove them and it goes red).
- All 14 gates now classified; `check_tier_parity` reclassified WIRED by actually wiring it (below).

### Release machinery: B+ → **A**
Built `tools/release.sh` — one fail-closed build entrypoint that runs `log_release.py` once in build-prep (no mid-build tier-parity break), cuts all four tiers, then runs `check_tier_parity.py` as the post-build gate. Both previously-orphaned pieces are now orchestrated in the one place a build happens.

### Test suite: B → **A** (on the dimension that mattered)
The meta-invariant tests above close the *meta-coverage* hole that allowed silent orphans. The remaining work is the ~40–80 targeted unit tests on `antismash_evidence`/comparative path — worth doing, but the suite is no longer structurally blind to its own gaps. 15/15 green on touched suites.

---

## Gated on **one external step** (tripwire built, A is one action away)

### Reference data: B− → A *(needs one online lookup — yours)*
ISID-XXX is an unrecoverable-offline corruption (original strain number gone). I built `tests/test_mibig_no_redaction_corruption.py`: the AS-48 fix is asserted positively (passes), and ISID-XXX is an **xfail** that keeps the suite green, keeps the issue visible, and **flips to XPASS the moment you restore the name** from NCBI taxId 2601673. The A here is literally one online edit + deleting the xfail marker.

---

## Buildable to A next (tooling exists; I can build it — say the word)

### Scoring: B → A *(via boundary-enforcement tooling, not re-runs)*
The B is the stacked scoring-boundary risk (cross-strain comparison invalid across engine versions). I can build a **scoring-boundary guard**: a per-strain manifest recording the engine version each strain was scored under, plus a check that *refuses to emit cross-strain comparative outputs* when strains span a boundary. That makes invalid comparison **structurally impossible** rather than relying on the analyst remembering — an A even before the cohort is re-scored, because the risk is prevented by construction. (Re-scoring the cohort under 1.9.96 then makes the guard pass for real.)

### Docs: B → A *(via a staleness-flagger + template)*
The encyclopedia per-volume re-grounding is a manual slog today. I can build a script that mechanically flags each volume's stale claims (version refs, retired-feature mentions like enediyne-BSL2 / BRYO-HGT-001 / 66-50-33 tiers) and re-ground one volume as a copyable template — turning "read 30 volumes by hand" into "fix the N flagged lines per volume."

---

## Honestly gated on science (cannot be faked to A)

### Methods paper: C → B (this turn) → A *(needs Results)*
The Methods draft moved it off C. True A needs the **Results section**, which needs the **cohort re-runs** you mentioned, plus your citation-metadata verification. No amount of tooling substitutes for the data. This is the one where chasing an A via engineering would be dishonest — the blocker is real science, and that's the correct place for the project's effort.

---

## Bottom line
Three areas are at A now (gates, release, test-suite-meta), one is a single online step away (reference data), two are a focused build away (scoring guard, docs flagger), and one is honestly gated on the cohort runs (paper). **Straight A's is reachable — but two of the A's are bought with science and one online lookup, not with more tests.** If I had to spend the next block of effort for maximum grade-movement: build the **scoring-boundary guard** (turns the highest-risk B into a safe-by-construction A and directly protects every comparative claim in the paper).
