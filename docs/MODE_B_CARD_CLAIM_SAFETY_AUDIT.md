# Check claim language in an authored Mode B card

For a current full48/current50 card, screen the actual saved prose, then review its claims against the
sources and selected [profile](MODEB_PROFILE_MATRIX.md). From the selected bundle root:

```bash
python mamey_run.py claim-safety <card.md> --package <pkg> --mode warn --json
```

Retain the findings, compound-context messages and exit status. `--json` prints findings; it does not
save a receipt. Add `--report <existing-review-folder>/claim-safety.csv` if a persistent CSV is needed;
that report appends findings, so preserve which invocation produced each set of rows. Warn mode exits
zero even when findings exist. Review any compound-context fallback or unavailable-evidence message.

This front door uses `tools/claim_safety_linter.py`, rather than the historical four-check recipe linked at the end.
Current authored cards may contain source-bound citations; current50 v2 requires literature with
relevance in §48–§49. The old no-PMID/DOI check does not apply to those sections. Inspect primary-source
passage bindings: a citation pattern or disclaimer does not prove what the source says. Run the selected
profile verification and independent content review described in the [walkthrough](MODE_B_USER_WALKTHROUGH.md).

The 2026 extraction-card recipe is in [history](history/MODE_B_CARD_CLAIM_SAFETY_AUDIT_2026.md).
