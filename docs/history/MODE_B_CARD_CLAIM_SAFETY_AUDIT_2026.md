> **Historical page.** Replaced by [the Mode B card claim-safety audit](../MODE_B_CARD_CLAIM_SAFETY_AUDIT.md). It records a 2026 audit of template-locked extraction cards; it is not a current check for authored cards.

# Mode B extraction-card claim-safety audit (2026)

## Historical extraction-card audit: 10 June 2026

The retained record reports 331 cards across six strains as clean under its limited extraction-card
checks. That count and result are historical, not a current receipt for authored cards. These older
cards were template-locked; the checks do not establish absence of all claim-safety violations or cover
Layer A/B/C narrative and Technical Report prose. The whole-line safe-word exclusion can also miss an
assertion elsewhere on the same line.

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

The recipe and observed disclaimer variants above are retained for their original extraction-card scope.
Neither a clean heuristic output nor disclaimer presence establishes complete profile content,
experimental linkage or scientific acceptance.
