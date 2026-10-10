# Citation-compact report readers

These are optional output-layer supplements selected by `--token-budget citation-compact`. Read the package triage and source evidence before interpreting a report. The owner is `mamey/citation_compact.py`; CLI phase admission is in `mamey/cli.py:1011–1043`. This guide describes the .447 source contract; it does not request emission into an existing package.

## Inputs and identity

The owner picks the first lexically sorted `*_4_triage_board.csv` in the package root, reads all rows into memory and retains input order. No matching file yields no leads. The report's single summary row uses the first lead, which is not necessarily the highest priority. Resolve ambiguous boards before an independently authorized rebuild. Keep strain, full node/contig, region and BGC alias together in reader-facing interpretations: `stable_locus` selects the first available Assembly_Locator/Node_ID/Contig field and does not independently enforce the region. Row-derived BGC and lead IDs can be invented fallback labels; they do not prove an evidence binding.

## What is actually rendered

The technical, bench and layperson templates have a first-row substitution map plus the full appended lead table. Bench detection, assay, threshold and layperson value phrases are fixed generic substitutions; they are not specimen-specific recommendations, validated decision rules or recorded experimental results. Review them against supplied evidence before sharing a report. The lead-table template is copied without substitution and then followed by the populated table: remaining double-brace cells in that scaffold are expected current behavior, not filled results.

Method/database citation labels are seeded from an internal registry. The current ledger conversion retains citation ID, label, status and supports but drops DOI/PMID/URL/MIBiG/accession values supplied in a basis dictionary. Its scope uses whether the citation ID contains `KCB`, so method entries otherwise receive `compound_family`. Consult original evidence and the registry for citation details; a populated label or `verified` token alone is not verification of a lead's literature claim. Missing evidence is represented by a work order, which does not execute a search.

## Writes and recovery

Emission sequentially writes root Citation_Ledger CSV/JSON, work-order Markdown/JSON, four compact Markdown reports and QA JSON. Individual text writes use a fixed sibling `.tmp` plus replacement. The operation has no group rollback or immutable-package guard: later failure can leave earlier outputs replaced, and concurrent writers can collide on the temporary name. The CLI phase catches exceptions and records WARN/ERROR rather than guaranteeing a complete set. Use a separately authorized disposable working candidate for regeneration; preserve sealed evidence in place and reconcile every output against manifest/checksums before adopting it.

The QA file is serialized before its own path is appended to the returned outputs list; disk and return lists differ by that entry. Neither list proves a transaction, self-hash or complete package integrity.

## Acceptance limits

`PASS_STRUCTURE` means the producer found no priority-citation shape/status errors and no more than one exact global caveat. `citation_needed` is an accepted status; zero caveats also pass. The package validator accepts WARN, requires at least one compact Markdown report and checks ledger/work-order shape, selected QA entries, optional manifest tracking and checksum behavior. It does not prove all four reports are present, DOI correctness, source-to-lead mapping, complete locus identity, assay suitability or scientific acceptance. Keep structural status separate from reference review and user sign-off.

Sources: `mamey/citation_compact.py:125–175,233–391,424–526`; `mamey/validate.py:245–430`; `mamey/cli.py:1011–1043`. Check retained citation fields and required caveats independently before accepting a compact package.
