# Finding J — synthetic-ID allowlist contains real cohort strains (FORK — needs your call)

**Found:** Speed-Round 3 (hostile audit), 2026-06-30. **Status:** surfaced, NOT auto-fixed.

## What

`tools/test_synthetic_ids.txt` is the allowlist of identifiers permitted in `tests/` (the
tests/-leak-audit in `make_public_tier.sh` fails a public cut on any `AS-/AJS-/PENDING-` ID in
`tests/` that is not on this list). Its own RULE, line 9:

> "every entry here MUST be a synthetic id confirmed absent from the real cohort
> (Master_Strain_List_v3). Never add a real strain to silence the audit — scrub the test instead."

Two entries violate that rule:

- **`AS-XXX`** (allowlist line 43) — a **real cohort strain** (*Streptomyces* / bumblebee / Ontario,
  with completed Mode B work per project history), not a synthetic. The allowlist comment also claims
  it "appears only in test_directed_pks_study_scaffold.py" — it actually appears in **7** test files
  (`test_bunny_hop_fixes`, `test_directed_pks_study_scaffold`, `test_redact_public_tier`,
  `test_macosx_appledouble_intake_v9_7_152`, `test_next_ten_patch_stack`, `test_verify_tier_derivation`,
  `test_modeb_workflow_v97143a`). Both the "synthetic" label and the file-count claim are inaccurate.
- **`AS-XXX`** (allowlist line 47) — also a real cohort strain, labelled "synthetic strain label."

(`AS-XXX`, `AS-XXX`, `AS-9xx` are genuinely synthetic / structurally-impossible and are fine.
`AS-XXX` is 3-digit and in cohort range — worth a Master_Strain_List_v3 check, but not confirmed
real here.)

## Why I did NOT auto-fix it (unlike Finding I)

- **Finding I** (`AS-XXX`, `AS-XXX`) were NOT on the allowlist, so the audit **blocked** a public cut —
  a live mechanical failure with a policy-mandated fix (scrub the test). I fixed it this round.
- **Finding J** entries ARE on the allowlist, so the audit **passes** — no mechanical blocker today.
  The issue is integrity: the allowlist contains real strains mislabelled as synthetic, defeating the
  invariant it exists to enforce.

Resolving J properly means scrubbing `AS-XXX`/`AS-XXX` out of 7+ test files to synthetics and removing
them from the allowlist — a larger, cross-file change. And it intersects your statement that "AS
strains are now on GenBank with host metadata; disclosures are meaningless for short-term cuts." That
statement makes the *disclosure* risk nil, which raises a genuine policy question I should not answer
for you:

## The fork

1. **Keep the synthetic-only invariant; clean up J.** Scrub `AS-XXX`→synthetic and `AS-XXX`→synthetic
   across the 7+ test files, remove them from the allowlist, fix the inaccurate comments. Preserves the
   audit's original guarantee. ~Most work.
2. **Relax the invariant (strains are public now).** If AS IDs are no longer private, the tests/-leak-
   audit's purpose is largely moot for AS strains. Option: convert the audit from "fail on non-allowlisted
   AS ID" to "warn," or retire the AS portion entirely, and correct the allowlist comments to say "real
   but publicly-disclosed, retained intentionally." Least work, but changes a safety mechanism — a
   deliberate policy decision, not a silent one.
3. **Minimal: fix only the inaccurate comments.** Leave the entries, but correct the false "synthetic"
   labels and the wrong file-count to "real cohort strain, publicly disclosed (GenBank), retained by
   decision <date>." Documents reality without touching tests or the audit. Fastest honest option.

My recommendation: **(3) now** (it removes the false documentation immediately and is reversible),
then **(1) or (2)** as a deliberate follow-up once you decide whether the synthetic-only invariant
still earns its keep post-GenBank. I did not pick, per the standing surface-the-fork-on-a-hard-guard
rule.

## Note on Finding I (already fixed this round)

`AS-XXX` and `AS-XXX` were real strains used as test fixtures and NOT allowlisted, so they would have
hard-blocked any gated public cut. Per the allowlist's own mandated approach ("scrub the test, never
allowlist a real strain"), I scrubbed them: `AS-XXX`→`AS-XXX`, `AS-XXX`→`AS-XXX` (both allowlisted
synthetics) in `test_as188_ingest_patches_v9_7_152.py` and `test_verify_checksums_judgment_register_v97152.py`.
Both files still pass (8 tests); the tests/-leak-audit now reports the cut unblocked. This was
unambiguous (mechanical blocker + policy-mandated fix) so it was applied, not forked.
