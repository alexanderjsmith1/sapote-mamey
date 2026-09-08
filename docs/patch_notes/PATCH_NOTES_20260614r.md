# PATCH NOTES — build -r (2026-06-14)

**Bundle:** Sapote–Mamey v9.7.22 · **Engine:** Mamey 1.9.30 · **Build:** 20260614r
**Theme:** Standing-rule policy change (NAPAA / hglE) + registry-as-SSOT refactor. Stable checkpoint.

## Policy change — NAPAA neutral, hglE-KS-PREV-001 noted
- **NAPAA -> NEUTRAL.** No longer downgraded or excluded from comparative/ecological claims. NAPAA is
  common and frequently adjacent to genuine BGCs; the Nosema hypothesis stays retired, but that does not
  justify excluding NAPAA itself. (rules_registry.json: status=neutral, action=none, lead_blocking=false.)
- **hglE-KS-PREV-001 -> NOTED.** Habitat-non-specificity (8 strains / 7 genera / 3 habitats) is recorded as
  an informational property, not a downgrade. hglE-KS ranks as a normal lead. (status=noted, action=flag,
  lead_blocking=false.)
- The section 4.3 enediyne-artifact guard (scoring.py), the enediyne-KCB BSL-2 gate, and the
  saccharide / primary-metabolism / BRYO-HGT-001 registry rules are UNCHANGED.
- Output labels neutralized: NAPAA_EXCLUDED -> NAPAA (cli + workbook); source-scan routing note and the
  antiSMASH-evidence NAPAA marker comment reworded to neutral (boolean weighting unchanged).

## Architecture — registry is now the single source of truth (B1)
- scoring.py::standing_rule_for now reads the lead-blocking downgrade rules FROM the registry
  (mamey/rules.py::load_registry, cached once at module level - off the per-BGC hot path). The hardcoded
  STANDING_RULE_PATTERNS duplicate is RETIRED. Toggling a standing rule is now a registry edit, not code.

## Verification (per tier, not assumed)
- Full suite green in every tier: CODE 526 | CODE-analysis-free 524 | SID-public 526 | MERGED 525.
- Zero behavioral drift: the registry-driven saccharide matcher fires on the identical row set as the
  retired hardcoded one (0 disagreements across the 59-strain cohort); NAPAA/hglE fire on 0 ranking rows
  (the committed-class guard always protected them - the real enforcement was the lint/claims layer).
- Public tiers AS-### clean (mibig corpus exempt); MERGED retains AS refs (PRIVATE).
- DO-FIRST kit registry flipped to match; kit test_rules_registry 8/8.

## Not in this checkpoint (parked on the consolidated patch list)
B2 (boundary_audit / source_scans SSOT dedup), C1-C3 (carried -p audit items), and the E runtime-hardening
items (WWKJ large-run stall, F1 guard, streaming, progress checkpoints) from the ChatGPT runtime audit.
