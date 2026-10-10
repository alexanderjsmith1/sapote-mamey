# Mode B batches: progress, verification, and completion

Use small, source-bound batches to author and review the selected exact-locus roster. Batch size is a scheduling choice, not an evidence denominator or a current-profile requirement. Preserve complete strain / full node-or-contig / region / BGC alias for each work unit; triage rank is a routing prior rather than biological truth.

## Current sequence

1. Bind the package/version, exact locus roster, source hashes and selected `full48` or `current50_v2` work-order contract. Use the [profile matrix](../MODEB_PROFILE_MATRIX.md); older §1–§10/20/30 descriptions are history.
2. Author each saved card from the bound evidence, retaining missingness and contradictory channels. Accessible evidence, scientific interpretation and independent review have their own authority.
3. If persisting through `record_mode_b`, inspect returned quality/locator/claim findings and `persistence_warnings`. The passive register does not refuse an incomplete draft. See [write behavior](MODE_B_WRITE.md).
4. Run the actual selected-profile verifier on each final saved card with the bound package and alias. Preserve its warning/error census, roster/coverage flags, invocation and card/source hashes. Update a per-card review ledger separately from legacy register progress.
5. Resume from that ledger and inspect actual file bytes. `batch_status` reports cached legacy quality state; it does not validate a saved card or infer current source freshness.
6. Before compiling a full-strain delivery, reconcile the complete expected roster, all card verification receipts and unresolved holds. Apply the separate artifact/layout and owner review gates. A partial source-bound draft may be retained, with its actual coverage stated.

## What the helper states mean

`record_mode_b` marks register status COMPLETE while separately storing `quality_tier`; SHALLOW/UNKNOWN cards can therefore increase `completion_pct`. `record_batch_complete` can mark aliases without card content. `batch_status` requires status COMPLETE plus cached `quality_tier=FULL` for its FULL count, and appends any registered aliases outside a caller's supplied order. Its denominator is the resulting alias list, not a freshly validated complete inventory.

`compile_ready(package_dir, ranked_bgc_ids)` returns `(ok, reason)`, not a boolean. Test `ok`, because even `(False, reason)` is a truthy Python tuple. Its legacy gate uses cached FULL tiers and blocks an unrecovered corrupt register; it does not run a current-profile verifier, check card hashes, or grant scientific acceptance. A regenerated source or edited card invalidates old cached verdicts until rechecked.

## Legacy quality policy

The passive evaluator's current character floors are HIGH 12,000 (rank 1–10), MID 11,000 (11–25), LOW 10,000 (otherwise). It also checks structural/gene-density conditions and a 2,000-character enrichment floor. A boundary Edge/Full-contig locus with supplied CDS count no greater than 22 can use a 2,500-character floor; missing boundary/CDS values do not grant this reduction. Text below 2,000 characters is STUB. These are legacy engineering thresholds, not licenses to pad text or bypass the selected finished profile.

## Failure and safe continuation

Preserve current and prior card files, register/last-good backup and review receipts. File writes are individually atomic but card/note/register publication is not one transaction. Repeating a write can duplicate optional reader notes; reconcile those files deliberately. Do not fix a corrupt roster by guessing its denominator or resetting history. Resume only from source-bound identities and a reconciled expected roster, then independently verify the current saved cards.

Source owners: `mamey/judgment_store.py:346–484,489–512,679–820`; `mamey/mode_b_quality_gate.py:60–99,264–291`; `mamey/authored_verify.py:68–109,591–680,804–891`.
