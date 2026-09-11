# DECISION MEMO — DAPR documented-but-unscored classes

**From:** Patch Chat · **Date:** 2026-06-20 · **For:** the Developer or User (scoring decision)
**Status:** analysis only — **no scoring code touched.** Wiring any of these is a scoring boundary.

---

## The situation

`docs/DAPR_CLASS_FRAMEWORK.md` is human-facing reference vocabulary. The engine's actual scoring is keyed on **class tokens** in `mamey/scoring.py` (`AB_KEYWORDS` 18, `AF_KEYWORDS` 17, `NOVELTY_KEYWORDS` 11). Six classes are documented in the framework but have **no token in the scoring dicts**, so a BGC whose only activity evidence is one of these gets **zero AB/AF keyword credit** from that axis:

| Class | Framework markers | Axis it would inform |
|---|---|---|
| Phenylpyrroles | pyrrolnitrin; prnABCD, halogenated tryptophan | AF |
| Glycolipopeptides | occidiofungin, burkholdine; β-amino acid/sugar | AF |
| Polyether ionophores | nigericin, monensin, lasalocid, salinomycin | AB (cytotoxic caution) |
| Macrolides | erythromycin, tylosin, pikromycin | AB |
| Orthosomycins | evernimicin, avilamycin | AB |
| Aminocoumarins | novobiocin, clorobiocin; gyrase target | AB |

**One caveat to verify before acting:** polyether ionophores may already be partially scored via the *compound-class annotation* path (`compound_class.py` routes ionophore → AB), which is separate from the keyword dicts. So the keyword gap overstates the *net* gap for ionophores. The other five have no path I can find.

---

## Why this is your call, not a hygiene fix

Adding tokens to `AB_KEYWORDS`/`AF_KEYWORDS` **changes scores** on any cohort BGC carrying that class — which:
1. **Creates a scoring boundary.** Scores before/after are not comparable; the cohort needs re-scoring under the new engine before any cross-strain AB/AF claim. (You already have boundaries stacked 1.9.84→1.9.96; this adds another.)
2. **Interacts with the standing claim-safety rules.** Macrolides especially are broad and would fire on many primary-metabolism-adjacent loci — the primary-metabolism DROP guard and mis-anchor suppression would need checking so it doesn't inflate false AB leads.
3. **Has real biological stakes for the bee program.** Aminocoumarins / orthosomycins are legitimate antibacterial chemistries that your cohort's actinomycetes could plausibly carry; *not* scoring them may be undercounting genuine AB capacity. That's a discovery-sensitivity question, not a typo.

---

## Options (pick by number)

1. **Leave as-is, relabel the framework.** Add a header to `DAPR_CLASS_FRAMEWORK.md` stating it's reference vocabulary and which classes are annotation-only vs scored. Zero scoring change, zero boundary. Honest and cheap.
2. **Wire the two highest-confidence AB classes** (aminocoumarins, orthosomycins) with gene-marker-gated tokens, full guard-interaction review + tests, accept the boundary, re-score the cohort. Targeted sensitivity gain.
3. **Wire all six**, same rigor, one larger boundary. Maximal sensitivity, maximal re-scoring cost.
4. **Investigate first:** I trace each class through the guard stack and `compound_class.py` and report exactly what *would* change (which cohort BGCs, which scores move, which guards fire) — a dry-run impact report — before you decide. No code change.

My honest read: **4 then 1-or-2.** The dry run tells you whether the missing classes actually touch your cohort before you pay a boundary; if they barely appear, relabeling (1) is the right answer and you avoid a re-score. If aminocoumarins/orthosomycins show up in real strains, (2) is worth the boundary.
