# Mode B Card Claim-Safety Audit (reusable QA check)
**Added 2026-06-10.** Verified clean on 331 cards across 6 strains (philanthi, venezuelae, gossypii, amethystogenes, odorifer, spectabilis).

## Purpose
Mechanically verify per-BGC Mode B cards carry no claim-safety violations. Gold Mode B cards are template-locked and minimal, so the risk surface is small and checkable.

## The four checks (all must pass)
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
