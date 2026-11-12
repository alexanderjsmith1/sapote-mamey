# Choose a Mode B example

For a new card, choose the [profile](../../MODEB_PROFILE_MATRIX.md), then follow the [authoring walkthrough](../../MODE_B_USER_WALKTHROUGH.md). The default profile is `full48`. Use `current50_v2` when your task selects it. A **profile** is the section layout a card must follow. Terms are in the [glossary](../../GLOSSARY.md).

There is no `current50_v2` example yet. The one full example below is a `full48` card.

## The full example

| Role | File | Status |
|---|---|---|
| Full48 format example, no independent BLASTp | `phosphonate_reference_full48_no_blastp_exemplar.md` | Collection role `CURRENT_TYPED_TERMINAL_FORMAT_EXEMPLAR`: an editorial label for this list, meaning the current example of the typed terminal format. It is not a document state and not a certification. The card's own `Document state` line reads `REFERENCE_AUTHORING_EXEMPLAR_WITH_TYPED_BLASTP_LIMITATION`, and its reader note says its historical pass labels were not rerun. |

It is a real reference-locus card with all 48 sections, a 23-gene roster as the card itself reports it (its source files were not re-checked for this collection), a disposition for every evidence stream, and a typed statement that no independent BLASTp was run. Use it to study section order, the displayed gene denominator and how to close unavailable evidence.

Do not copy its genes, pathway call, comparators, experiments, conclusions or action list into another locus. It is not positive calibration for §§20/39/40/42/48.

## Class sketches

Seven older cards show how to reason from genes to prose for one compound class. They cover only the first 30 sections, so they are not complete cards for either profile. Their measurements and "FULL" labels were recorded when they were written. They are not fresh validation, and they are not a template to finish a new locus.

| Class | File |
|---|---|
| NRPS | `nrps_exemplar.md` |
| Type I PKS | `t1pks_exemplar.md` |
| Type II PKS | `t2pks_exemplar.md` |
| Hybrid NRPS-PKS | `nrps_pks_hybrid_exemplar.md` |
| RiPP (lanthipeptide) | `ripp_exemplar.md` |
| Terpene | `terpene_exemplar.md` |
| Siderophore | `siderophore_exemplar.md` |

No example exists yet for type III PKS, saccharide or oligosaccharide, or other and mixed classes.

At least four sketches have unresolved differences between their own sections. The RiPP sketch's §15 disagrees with its §§4, 16 and 28 about the precursor and LanKC results. The siderophore introduction disagrees with its §§4, 16 and 28 about whether a BLASTp panel ran. The NRPS sketch treats the inventory as complete in §3 without a verified source basis, while §10 qualifies the boundary evidence, and presents a second system as possible in §9 but genuine in §11. The hybrid sketch states that a lasso system is present in §§1–2 but leaves its defining precursor and cyclase to be identified in §§15 and 21. Treat these as unresolved source states, not as no-hit results.

## How to reuse an example

- Reuse the writing structure and register. Do not transfer genes, scores, mechanisms, activity claims or proposed experiments.
- Trace every claim you reuse to its source and receipt before you rely on it.
- Write the complete identity, `strain / full node-or-contig / region / BGC alias`, in your own card.
- Check the gene denominator, channel binding, citations and interpretation yourself.
- Character counts are not an acceptance bar. Use the verifier for your profile (`verify-modeb`) and a person's review of the sources.
