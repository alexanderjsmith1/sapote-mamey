# Mode B Card Claim-Safety Audit (reusable QA check)
**Historical extraction-card audit, added 2026-06-10.** The original record reports 331 cards across six strains as clean under the checks below. This is not a current audit receipt or clearance for authored full48/current50 cards; the original cohort/denominator and limited scope remain historical.

## Purpose
These checks screen the older minimal/template extraction cards. They do not establish absence of all claim-safety violations, and current authored judgment cards are not universally template-locked. Use the current claim-safety command plus selected-profile source/content review for those cards.

## Historical four-check recipe (limited to its extraction-card template)
1. **No forbidden product-identity language.** Regex (case-insensitive): `\bproduces\b | \bsynthesizes\b | is an enediyne | confirmed enediyne | identical to (the )?compound | the strain makes` — EXCLUDING lines also containing claim-safe context (`candidate|predicted|putative|possible|does not|not a confirmed`). Expected: 0.
2. **Disclaimer present in EVERY card.** Match ANY of these wordings (do NOT hardcode one strain's phrasing — this was a real audit bug): `does not claim purified product identity | not a confirmed product call | source-bounded | source-derived extraction card | not...confirmed product | upgrade...only with`. Expected: cards_with_disclaimer == total_cards.
3. **No asserted PMID/DOI** (Bert mode): `PMID:?\s*[0-9]{6,} | doi.org/10. | 10.[0-9]{4,}/`. Expected: 0 (cards should not assert citations; that's the literature index's job, separately verified).
4. **No template deviation** hiding a claim: lines after `## Interpretation` (or `Interpretation limit`) beyond the standard disclaimer block. Inspect any card flagged.

## Note on disclaimer wording variants observed
- philanthi/citrea-era: "...does not claim purified product identity."
- venezuelae/gossypii/amethystogenes-era: "...not a confirmed product call and should be upgraded only with LC-MS/MS..."
Both satisfy check 2. The audit MUST accept either.

## Scope limit
This audits the CARDS only (template-locked, low risk). It does NOT cover Layer A/B/C narrative or Technical Report prose (free-form, higher overclaim risk) — those need a separate read.

## Current authored-card boundary

The no-PMID/DOI rule above belongs to that historical extraction-card template. Current authored cards
may contain source-bound literature citations; citation presence alone is not an overclaim or a failed
Bert review. Review the actual primary-source/passage bindings instead. The historical whole-line
safe-word exclusion is a coarse screen and can miss an assertion elsewhere on the same line.

The current `python mamey_run.py claim-safety <card.md> --package <pkg> --mode warn --json`
front door uses `tools/claim_safety_linter.py`, not this four-check text as an executable rule set.
Its findings/compound context and optional CSV output must be retained; warn exits zero with findings.
Neither a clean heuristic output nor disclaimer presence independently establishes source truth,
complete profile content, experimental linkage or scientific acceptance.
