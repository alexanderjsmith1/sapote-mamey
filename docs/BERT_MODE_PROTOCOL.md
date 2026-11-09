# Literature citation verification (Bert Mode)

This is the bundled citation-review protocol. It is a writing and verification workflow, not an
executable literature-validation engine. It can be followed without an external assistant skill.
User-selected output formats and project requirements take precedence over presentation defaults.

## Verify the source and the claim separately

Resolve the title, authors, publication venue, year and stable identifiers against a primary
record. Read the passage or table supporting each summarized claim. Record the source locator,
review date, reviewed passage location, applicability and unresolved fields. A DOI match helps
identify the record. It does not confirm the separately written title, authors, year or venue,
so check each field against the record you selected. It also does not show that the paper
supports a particular statement.

Do not invent identifiers, missing bibliographic fields or quantitative results. If full text is
unavailable, limit the summary to what was actually reviewed and identify the gap. Retained source
receipts can support reproducibility; a resolved local path alone does not promote an old row's status.

## Citation digest vocabulary

| Tier | Meaning |
|---|---|
| **Verified** | Bibliographic identity and the summarized claims or numbers were checked against the source's full text during the recorded review. |
| **Partial** | A record or passage is available but a required field or claim remains unconfirmed; name the gap. |
| **Policy** | A guideline, standard or agency source; record the version and review date. |
| **GenBank** | A sequence or assembly record; retain its accession and version. |

These are digest labels. They do not substitute for a citation store's `SOURCE_VERIFIED`,
`OWNER_ACCEPTED`, `UNBOUND` or hold states. Transcription verification does not confer scientific
acceptance. Preserve the store's own status and provenance alongside any digest label.

## Local resolver boundary

`mamey/citations/resolver.py` is a separate work-order/ledger writer. It normalizes supplied status
strings and extracts identifiers; it does not resolve DOI records or read primary full text.
Its `PASS_VERIFIED_PRIMARY` is computed from accepted row flags, and can include only method/database
or user-supplied reference rows. Therefore that gate is not equivalent to this protocol’s Verified
full-text/claim review. Retain source/passage receipts independently, and do not translate one status
vocabulary into another merely because the names sound similar. Its writer uses fixed filenames
and can overwrite an existing output directory; preserve original evidence and use an owned output.

## Output

A short digest can use one item per finding: supported summary, citation, evidence type,
applicability and review status. Save a durable file when the project requires one.

For a bibliography workbook, retain the established three-sheet layout:

1. **Verified Bibliography**: identifier, formatted citation, DOI, PMID/PMCID when available,
   summary, evidence type, relevance, status and topic. Add source receipt and passage locators
   where the evidence workflow supplies them.
2. **Zotero Cleanup**: citation, issue, corrected value and proposed action. Record that the
   library was not checked if it was outside scope; do not imply a clean audit from an empty sheet.
3. **Summary Stats**: source counts by status, evidence type and topic, plus unresolved fields.

An external workbook-formatting skill may help, but is not required by this portable protocol.
Avoid duplicate independently edited source lists: render multiple formats from the same reviewed
records. Formatting is separate from evidence verification.

## Applying references to genome-mining results

Distinguish a reference organism's experimentally reported phenotype from a hypothesis about the
query strain. Sequence similarity, a domain label or a comparator name alone does not establish
product identity, production or function. Display an individual locus as
`strain / full node-or-contig / region / BGC alias` using one bound record.

Preserve contradictory sources and explain applicability rather than selecting the most convenient
citation. For quantitative claims record the exact measure, units and conditions. A family-level
reference does not automatically support a strain-specific statement.

## Completion record

Report what was reviewed, source counts and outstanding gaps. A bibliography is complete only for
its declared scope; unresolved citations remain explicit. The older format example
[`examples/citation_library_exemplar.md`](../examples/citation_library_exemplar.md) keeps a
retired three-bucket vocabulary. Use the labels in the table above instead.

Maintainer note: this page is the bundled source of the digest vocabulary.
`tests/test_bert_taxonomy_drift.py` reads it, so update that test when the labels change.
