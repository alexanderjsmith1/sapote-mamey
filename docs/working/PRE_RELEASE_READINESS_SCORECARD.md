# PRE-RELEASE READINESS SCORECARD — Sapote–Mamey v9.7.96

**From:** Patch Chat · **Date:** 2026-06-20 · **Purpose:** the "are we actually ready to ship/publish" view, per area, with ranked open risks. Honest grades, not reassurance.

---

## Per-area grades

| Area | Grade | Basis | Open risk |
|---|---|---|---|
| **Extraction core (Mamey)** | A | Deterministic (byte-identical output, held by tests); `doctor` PASS; cassette imports clean | none material |
| **Scoring (Sapote axes)** | B | Tested; guard stack intact; claim-safe by construction | **scoring boundaries stacked 1.9.84→1.9.96 — cohort not re-scored** (blocks cross-strain AB/AF claims) |
| **Release machinery** | B+ | Was the weak spot; now: sync-gate wired (pytest + cut), `BUNDLE_VERSION` guarded, parity gate wired, leak audit fail-closed | `check_tier_parity` still manual; `log_release` not yet in build-prep |
| **Test suite** | B | ~1,400 tests, green | coverage was *broad but holey* — orphaned gates passed unnoticed; F6 QA tools un-triaged |
| **Gates** | A− | leak audit hardened (underscore, tests/, `.pytest_cache` ordering all fixed); version + tier-derivation now wired & fail-closed | one manual gate remains (`check_tier_parity`) |
| **Reference data** | B− | JSON all valid; AS-48 corruption fixed + carve-out + test | **ISID-XXX MIBiG organism name corrupted, original lost — needs online restoration** |
| **Docs** | B | current-claims re-grounded to 9.7.96; protocols/glossary/manual/prereqs fixed; dual-glossary resolved | encyclopedia **per-volume re-grounding** is honest-but-stale (editorial debt, file self-tracks it) |
| **Figures/prompts** | A− | `_INDEX` recount + 3 uncatalogued figures added; data-only PNG + companion CSV convention | none material |
| **Methods paper** | C | architecture is stable and documentable now | **not updated in a while** — see the methods draft deliverable |

---

## The honest headline

**Tooling/hygiene is genuinely close to release-ready.** The version-sync defect class that dominated this arc is now structurally closed (gates wired, literals guarded, parity enforced). What's left in hygiene is small and bounded.

**The real blockers to *publication* are scientific, not hygiene:**
1. the **cohort re-scoring** gate (no valid cross-strain comparison until every strain is re-scored under 1.9.96), and
2. the **methods paper** being out of date.

We've spent this arc making the bundle correct. The remaining high-value work is upstream of the paper, not more polish.

---

## Ranked open risks (highest first)

1. **Cohort re-scoring blocker** *(science).* Stacked scoring boundaries invalidate cross-strain AB/AF comparison. Gates any comparative claim in the paper. Needs the strain packages re-run under 1.9.96. **Highest leverage.**
2. **ISID-XXX public-data corruption** *(integrity).* A wrong public organism name ships in the MIBiG reference. Cheap to fix *with network* (taxId 2601673); I can't offline.
3. **Methods paper staleness** *(publication).* Out of date; draft provided to restart it.
4. **Encyclopedia per-volume re-grounding** *(docs debt).* Honest-but-stale; needs genuine per-volume re-verification, not a version bump.
5. **DAPR scoring decision** *(science/scope).* Six unscored classes; may undercount AB capacity. Decision memo provided.
6. **`check_tier_parity` manual + F6 QA tools un-triaged** *(hygiene tail).* Low severity; close for completeness.

---

## Recommended sequence to "publication-ready"
1. Restore ISID-XXX (you, online) — closes the last integrity item.
2. Re-score the cohort under 1.9.96 (unblocks comparative claims).
3. Methods paper pass (draft is ready to build on).
4. Decide DAPR (memo) + close the hygiene tail (`check_tier_parity`, F6, `log_release` wiring).
5. Encyclopedia per-volume re-grounding (lowest urgency; self-tracked).
