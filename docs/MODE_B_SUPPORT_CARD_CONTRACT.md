# Mode B support-card contract

## Purpose

A support card is a reviewable evidence bridge into later Mode B writing. It recovers useful interpretation while preserving source identity, database provenance, denominators, alternatives, and claim ceilings. It is not a chemical identification and does not replace the authored Mode B judgment.

## One-card workflow

1. Resolve one assignment row and confirm `(priority_rank, strain, bgc_id, markdown_path)`.
2. Confirm ownership before any write.
3. Read the quarantined artifact and existing Markdown.
4. Read the current sealed package, exact crosswalk, inventory, manifest, and locus map.
5. Read the exact antiSMASH region and comparison files.
6. Establish the complete current protein denominator.
7. Match every BLASTP query sequence to its current raw translation.
8. Audit each database channel separately.
9. Reconcile domains, modules, comparisons, cohort context, linkage hypotheses, and phylogeny.
10. Determine value tier before writing extensive prose.
11. Author one Markdown outcome.
12. Run BLASTP, claim-safety, source-path, denominator, URL, and ledger checks.
13. Append only the task-specific ledger.

## Required card sections

1. Recovery disposition
2. Executive verdict
3. Source lock and locus identity
4. Complete gene-by-gene verdict
5. Homology channels
6. Captured architecture and alternatives
7. Cluster-comparison evidence
8. Cohort and cross-contig context
9. Taxonomy, ecology, and activity boundaries
10. Value tier and safe use
11. Missing evidence and next decision
12. QA receipt

## Denominator rules

Let:

- `E` = expected captured proteins from the current locus;
- `D` = proteins with at least one direct current-query hit;
- `N` = completed queries with no significant hit;
- `U` = unresolved or unavailable direct-query coverage.

The card must make `E = D + N + U` auditable. Database-specific coverage remains separate and may overlap. `D` is the union across channels, not the sum of channel hit counts.

## Direct-query acceptance

Protein identity is sequence-first and fail-closed:

1. Normalize the current translation and submitted query sequence identically, then compare their
   SHA-256 values. An exact hash match is the positive gene identity key.
2. Use amino-acid length only to reject impossible joins. Equal length is never positive identity.
3. If the protein hash is duplicated in the admitted comparison corpus, expand an ordered signature
   of adjacent protein hashes until the physical locus is unique. Record the smallest sufficient
   neighbor radius, corpus scope, and corpus receipt.
4. Bind the sequence identity to the exact assembly, full node/contig, region interval, CDS roster,
   channel/database, and result-job receipt.
5. Preserve rows that fail positive admission as `OBSERVED_UNBOUND` or `QUARANTINED` with a reason;
   do not quote their percentages as exact-current evidence.

A direct homology row can support a current exact-gene verdict only when:

- the strain, BGC, and gene resolve to the current locus;
- the query sequence exactly matches the current raw translation by SHA-256;
- any duplicate protein hash is disambiguated by the minimal ordered-neighborhood signature;
- query, channel/database, and result-job receipts are present and mutually consistent;
- the row is not an HTML/QBlast stub;
- accession and numeric evidence are present;
- database provenance remains explicit.

Matching a locus label, BGC alias, gene label, or amino-acid length alone is insufficient. If the query
FASTA or result-job receipt is unavailable, the row is visible context but is not admitted direct-query
evidence.

## Evidence-channel rules

### NCBI nr

Report current-query status, accession, description, organism, identity, aligned length, query coverage, E-value, and bit score when present. An absent artifact is `UNAVAILABLE`; a verified completed query with no row is `NO_SIGNIFICANT_HIT`.

### EBI

Report separately even when it resolves to `EBI_UNAVAILABLE`. Never reuse an NCBI or local row as an EBI result.

### Local Swiss-Prot

Report separately and label the database local/curated. Subject names may support broad role or family context but do not transfer substrate or product.

### Domain/HMM evidence

Distinguish coordinate-resolved domains, rule-level hits, PFAM/TIGRFAM hits, motifs, and antiSMASH predictions. A motif prediction does not prove biochemical activity.

### General ClusterBlast

Use for local homology and neighborhood comparison only. Reuse of a short query against several subject proteins does not establish whole-cluster equivalence.

### KnownClusterBlast/MIBiG

Preserve accession, rank, query-gene denominator, subject-gene geometry, and coverage. Named compounds remain comparator labels. Rank-uncapped per-gene rows can improve denominator visibility but remain package-native similarity evidence.

### SubClusterBlast

Report independently. A no-hit can constrain a subcluster claim but does not prove novelty.

### BiG-SCAPE

Record exact run, cutoff, class, family ID, and member count. Never merge family namespaces across runs. Family recurrence is not chemistry; a singleton is not novelty.

### RG-GMCI

Report candidate partners and confidence, but set linkage to `NOT_LINKED_ACROSS_CONTIGS` unless current sequence mapping plus compatible architecture/synteny demonstrates continuity.

### Strain-level capture

Treat as secondary aggregation. Use assembly burden, KCB denominator profiles, and routing facts; do not treat the layer as independent experimental confirmation.

### Taxonomy and phylogeny

Use only independently auditable sources. Taxonomy can weight comparators but cannot transfer products. Do not copy unsupported bootstrap claims.

### Ecology and activity

Keep collection source and host context separate from ecological function. Keep strain/extract activity separate from a BGC unless fractionation or genetic evidence links the phenotype.

## Source-path rules

- Cite exact current paths.
- Cite ZIP members as `archive.zip::member`.
- Verify every cited absolute path.
- Label legacy paths and namespaces.
- Never silently repair a source path in prose without recording the correction.
- Never cite or access the forbidden legacy workspace.

## Writing rules

- Lead with the defensible verdict.
- State the maximum claim before comparator detail.
- Name alternatives.
- Prefer concise `HOLD` or `CONTEXT_ONLY` cards over invented completion.
- Use visible public accession URLs for cited direct hits.
- Keep value and confidence conceptually separate.
- Finish with exact missing evidence and the decision it would unlock.

## QA receipt

Record:

- assignment tuple and ownership check;
- exact region and gene denominator;
- current-query sequence reconciliation;
- protein SHA-256 match count and duplicate-protein count;
- neighbor radius and comparison-corpus receipt for every duplicated protein hash;
- observed versus admitted coverage for every channel;
- result-job receipt and quarantine state for every observed result;
- channel-specific coverage and union coverage;
- no-hit and unresolved counts;
- comparison and linkage ceilings;
- source-path audit;
- visible URL count;
- claim-safety result;
- card/ledger reconciliation;
- confirmation that no DOCX or out-of-range card was changed.
