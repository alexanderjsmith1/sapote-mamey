# Persisting Mode B drafts and reviewed cards

`mamey.judgment_store.record_mode_b` persists authored Markdown and optional reader notes in a package's judgment area. It records legacy quality findings and progress; it does not run the full current-profile verifier or establish scientific acceptance. Use the work-order profile described in the [profile matrix](../MODEB_PROFILE_MATRIX.md) and preserve the complete strain / full node-or-contig / region / BGC alias binding.

## Current API

```python
record_mode_b(
    package_dir=bound_package,
    bgc_id=package_scoped_alias,
    mode_b_md=authored_markdown,
    session_id=review_session,
    rank=bound_triage_rank,
    edge_status=bound_boundary_state,
    cds_count=bound_region_cds_count,
)
```

Inputs shown are caller-supplied variables from the selected evidence snapshot. Optional `layperson_paragraph` and `fermentation_note` default to empty strings. The API does not infer verified experiments or authorize a scientific procedure from those text fields. Preserve measured material-level observations separately from individual locus interpretation.

The passive quality evaluator receives the Markdown, rank, boundary and CDS count. It stamps `FULL`, `SHALLOW`, `STUB`, or `UNKNOWN` on failure; claim-safety and locator findings are surfaced but do not block persistence. Treat legacy `FULL` as a quality-tier observation, not a current50/full48 verification receipt. Character floors are not evidence sufficiency or scientific depth by themselves.

## Files and repeated writes

The selected package contains `judgment/<strain>_<alias>_mode_b.md`, optional accumulated `judgment/<strain>_laypersons_section.md` and `judgment/<strain>_fermentation_section.md`, and `<strain>_judgment_register.json` (with a `.last-good` backup for trustworthy register writes). The `<alias>` remains a package-scoped lookup, not a globally unique locus.

The function writes/replaces the per-BGC Markdown, appends each nonempty optional reader-note section, and then updates the register. Individual text writes use atomic replacement, but these separate files are not one transaction. Repeating the call replaces the card while appending duplicate reader-note sections unless the caller has deliberately handled them. Preserve old content and review note accumulation before a retry; inspect returned `persistence_warnings` and actual files. Do not rely on a printed success alone.

The register row becomes `status=COMPLETE` even when its quality tier is SHALLOW, STUB or UNKNOWN. `completion_pct` counts that status, not profile verification. `record_batch_complete` can mark known register aliases COMPLETE without per-BGC content. Neither this shortcut nor `judgment_status=COMPLETE` is sufficient to compile or accept the finished strain. [Batch guidance](MODE_B_BATCH_RUN.md) separates these checks.

## Required verification handoff

Keep persistence, current-profile verification, source/evidence admission, visual review and owner acceptance as separate recorded states. Verify the exact saved card with the intended contract and package context, inspect warnings and roster/coverage flags, and bind the card/source hashes in a separate run record. A register row stores a filename and cached quality fields rather than a card hash, so changing a persisted file makes the cached verdict stale. Recheck the actual bytes before each handoff.

`compile_ready` reads cached legacy FULL counts and the supplied/registered roster; it does not re-open the cards or run current Mode B verification. Record the full expected exact-locus roster independently. Unknown alias writes can add rows to the register without validating the inventory denominator. Source or profile changes require explicit reconciliation rather than reuse of old completion percentages. Corrupt-register recovery is a separate hold; preserve original and last-good files before investigating.

Workbook write-back functions consume the stored judgment state; they are separate mutations and do not supply missing verification or experimental evidence. Use the appropriate governed workflow and actual schema, preserving source identity and a backup/versioned destination. Old ten-section examples and illustrative biological narratives are not current completion definitions.

Source owners: `mamey/judgment_store.py:318–484,489–512,679–704,727–820`; `mamey/mode_b_quality_gate.py:60–99,264–291`; `mamey/authored_verify.py:591–680,804–891`.
