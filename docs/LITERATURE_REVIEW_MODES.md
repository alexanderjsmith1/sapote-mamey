# Formal Literature Review Modes

These are normative review-depth labels, not executable modes or automatically enforced completion states. No local parser switches retrieval depth from FLR/VLR text. A label must be backed by the recorded reviewed sources, passages, scope, date and unresolved fields; it does not itself establish publication readiness.

## FLR -- Focused Literature Review

Default for strain-level and BGC-level interpretation.

**Purpose:** bounded contextual literature support, subject to scientific/editorial review, for a defined strain, genus, compound class, ecological source, or BGC interpretation.

**Typical scope:** 10--30 papers.

**Required fields:** key bibliographic verification, evidence type, key quantitative details when available, one-sentence relevance note, citation-ready reference, and explicit claim status.

**Use FLR for:** routine top-lead literature context, genus/source comparisons, compound-family searches, and quick support for Mode-B interpretations.

## VLR -- Verified Literature Review

Escalation mode for manuscript-grade or high-stakes claims.

**Purpose:** explicitly recorded citation/claim verification and deeper extraction within available source scope; the label is not an independent guarantee.

**Required fields:** DOI/PMID/PMCID/journal-page verification, full-text review when available, hard-number extraction, evidence typing, relevance notes, corrections/errata checks, and publication-style citations.

**Use VLR for:** manuscript, grant, supplement, final bibliography workbook, producer-genome precedent, MIC/mechanism claims, and high-confidence ecological/chemical assertions.

## Claim-status language

Every literature section should declare one of:

- `FLR_COMPLETED`
- `FLR_PRELIMINARY`
- `VLR_COMPLETED`
- `VLR_RECOMMENDED`
- `LITERATURE_NOT_RUN`

Reports must not imply VLR-grade verification when only an FLR/preliminary pass was performed.

The 10–30-paper range is a planning convention, not a numerical acceptance floor or proof of completeness. Keep these workflow labels separate from the Bert digest vocabulary and the exact status vocabulary of a citation store/resolver. A completed declared scope can still contain identified unavailable full text or unresolved claims; do not label those claims verified.
