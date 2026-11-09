# Mode B support-card contract

## Purpose

A support card is a short evidence write-up for one biosynthetic gene cluster (BGC). It is a reviewable evidence bridge into later Mode B writing. It recovers useful interpretation while preserving source identity, database provenance, denominators, alternatives, and claim ceilings. It is not a chemical identification and does not replace the authored Mode B judgment.

Terms are in the [glossary](GLOSSARY.md). Statuses such as `OBSERVED_UNBOUND` and `QUARANTINED` are defined in the [status vocabulary](MODEB_STATUS_VOCABULARY_RATIFIED_v9_7_373.md). The live BLASTP channel is described in the [online BLASTP protocol](ONLINE_BLASTP_PROTOCOL.md).

## One-card workflow

Write a support card after `run` and `validate` have produced a validated package for the strain (see the [first-run recipe](reader/01_FIRST_RUN.md)). The package is the folder under `runs/<ID>/package`. A card covers one BGC and starts from a plain Markdown file you create. The [Mode B walkthrough](MODE_B_USER_WALKTHROUGH.md) covers the full card that follows.

A ledger is optional. It is a CSV with one row per card, which keeps a batch of cards consistent. If you use one, the checker reads the columns `priority_rank`, `markdown_path`, `value_tier`, `qc_status`, `expected_genes`, `direct_hit_union` and `no_significant_hit`. Without a ledger, skip steps 1 and 13.

1. Find the card's ledger row and confirm `(priority_rank, strain, bgc_id, markdown_path)`.
2. Read any earlier Markdown for the same BGC, and keep unresolved evidence from it as `OBSERVED_UNBOUND` or `QUARANTINED` rows (see the status vocabulary above).
3. Read the package's crosswalk, inventory, manifest and locus map.
4. Read the exact antiSMASH region and comparison files.
5. Establish the complete current protein denominator.
6. Match every BLASTP query sequence to its current raw translation.
7. Audit each database channel separately.
8. Reconcile domains, modules, comparisons, cohort context, linkage hypotheses and phylogeny.
9. Determine the value tier before writing extensive prose.
10. Write the card as one Markdown file.
11. Fill the metadata lines the checker reads (next section).
12. Run the checks (see [Checks before you finish](#checks-before-you-finish)). Some are commands and some are manual.
13. If you use a ledger, update its row for this card only.

## Metadata lines the checker requires

Write each as a bullet with a bold label that ends in a colon inside the bold, for example `- **Expected proteins:** 12`. The match ignores case. The checker takes the first run of digits as the integer for a count.

| Label | Required | Value |
|---|---|---|
| `Priority rank` | yes | an integer |
| `Value tier` | yes | one of `THESIS_READY`, `USEFUL_WITH_LIMITATIONS`, `CONTEXT_ONLY`, `HOLD` |
| `QA status` | yes | any text except `PENDING_FINAL_VALIDATION`, which fails |
| `Expected proteins` | yes | integer, the E below |
| `Direct-hit union` | yes | integer, the D below |
| `No-significant-hit proteins` | yes | integer, the N below |
| `Unresolved/unavailable direct-query proteins` | no | integer, the U below; a missing line counts as 0 |
| `Claim ceiling` | yes | any text |

Without these lines the checker reports `METADATA_MISSING` (or `CLAIM_CEILING_MISSING`). The card must also mention each of these names somewhere in its text: `NCBI nr`, `EBI`, `Local Swiss-Prot`, `General ClusterBlast`, `KnownClusterBlast`, `SubClusterBlast`, `BiG-SCAPE` and `RG-GMCI`. A missing name reports `CHANNEL_MISSING` or `COMPARISON_MISSING`.

## Required card sections

The checker needs real Markdown `##` headings. The first two are unnumbered (`## Recovery disposition`, `## Executive verdict`). The other ten are numbered 1 to 10 (for example `## 1. Source lock and locus identity`). A plain numbered list does not count.

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
5. Preserve rows that fail positive admission as `OBSERVED_UNBOUND` or `QUARANTINED` with a reason (see the status vocabulary above);
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

Report candidate partners and confidence, but retain `NOT_LINKED_ACROSS_CONTIGS` unless independently bound evidence establishes physical linkage. Sequence similarity, compatible architecture and reference-relative synteny support a candidate relationship; they do not by themselves demonstrate continuity between separate assembly contigs.

### Strain-level capture

Treat as secondary aggregation. Use assembly burden, KCB denominator profiles, and routing facts; do not treat the layer as independent experimental confirmation.

### Taxonomy and phylogeny

Use only independently auditable sources. Taxonomy can weight comparators but cannot transfer products. Do not copy unsupported bootstrap claims.

### Ecology and activity

Keep collection source and host context separate from ecological function. Keep strain/extract activity separate from a BGC unless governed, independently reviewed evidence establishes the locus link. Fractionation alone does not establish chemical identity or BGC causation; preserve material identity, measured assay scope and genetic/linkage evidence separately.

## Source-path rules

- Cite exact current paths.
- Cite ZIP members as `archive.zip::member`.
- Verify every cited absolute path.
- Label legacy paths and namespaces.
- Never silently repair a source path in prose without recording the correction.
- Do not cite a legacy workspace path. The checker flags one literal placeholder path.

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

- strain, BGC and ledger-row identity;
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
- the checks run, with their exit codes.

## Checks before you finish

Step 12 has five checks. The first two are commands. The rest are manual.

| Check | How |
|---|---|
| Card structure, metadata, D+N+U arithmetic, channel names, linkage and locus claim patterns, visible URL, cited `/Users` and `/home` paths | `python tools/audit_modeb_support_card.py <support-card.md> --json` |
| Ledger row, when the card has one | `python tools/audit_modeb_support_card.py <support-card.md> --ledger <ledger.csv> --json`. Without `--ledger` no ledger check runs. |
| Claim safety (for example "produces X" without a capacity ceiling) | `python tools/claim_safety_linter.py <support-card.md>` (exit 0 clean, 1 overclaim) |
| Query sequence equals the current raw translation by SHA-256, and duplicate-protein neighborhoods | manual; no single command checks it. Compare hashes of the submitted query and the package protein by hand, as the direct-query rules above require |
| Result-job receipts, and that every cited ZIP member exists | manual; open the receipt and the archive |
| Every accession URL resolves to the cited record | manual |

Save the output of both commands with the card. Neither writes a receipt.

### The support-card checker

`tools/audit_modeb_support_card.py` is a pattern screen. It does not check every requirement above.

```bash
python tools/audit_modeb_support_card.py <support-card.md> --ledger <ledger.csv> --rank-min <N> --rank-max <N> --json
```

`--ledger`, `--rank-min`, `--rank-max`, `--skip-source-existence` and `--json` are optional. Without `--json` it prints `modeb-support-card — PASS` or `FAIL` and the findings. It exits 0 on PASS and 1 on FAIL. Keep `--skip-source-existence` explicit when you use it, because it weakens the source-path check.

What it reads:

- The metadata lines above.
- Unique backticked `ctg<digits>_<digits>` tags, as the gene list. Their count must equal `Expected proteins`. Other locus-tag styles need a separate reviewed mapping. Do not rename real genes to match this pattern.
- The D+N+U arithmetic, the channel and comparison names, and selected claim patterns.
- With `--ledger`, the ledger row whose `priority_rank` equals the card's priority rank. It compares six fields: `markdown_path`, `value_tier`, `qc_status`, `expected_genes`, `direct_hit_union` and `no_significant_hit`. More than one row with that rank fails with `LEDGER_DUPLICATE_RANK`. The row is found by rank only: the checker does not compare the ledger's strain or locus with the card. Check that the row names the same `strain / full node-or-contig / region / BGC alias` yourself.
- Backticked `/Users` or `/home` paths, to confirm the file exists. For `archive.zip::member`, it checks only the archive.

What it does not check:

- ZIP-member existence, hash or sequence equality, or duplicate-neighborhood identity;
- job receipts, canonical gene membership, or all accession URLs;
- independent QA status. A declared tier such as `THESIS_READY` is accepted as syntax and is not approval.

A PASS here does not give a card a completed full48 or current50 judgment state.
