# SOP-04 — Iterative NCBI BLASTP Batching for Sapote/Mamey BGC Evidence

## Purpose

This SOP describes the recommended BLASTP workflow for validating biosynthetic gene cluster class assignments and gene-level functions in Sapote/Mamey.

The goal is not to identify a final compound from sequence alone. The goal is to generate defensible evidence for BGC class calls, gene-function annotations, conserved-neighborhood hypotheses, and follow-up prioritization.

Live submission is a separate authorized action that sends query sequence and headers to an external service. A local PRIVATE/PUBLIC release tag does not by itself authorize disclosure. For current channel admission, provenance and mutation boundaries, read [the BLASTP protocol](../ONLINE_BLASTP_PROTOCOL.md).

## Principle

BLASTP should be run iteratively in small, evidence-driven batches.

Large all-protein BLASTP submissions produce oversized outputs, increase timeout risk, and slow down the operator. Small batches allow the user to keep NCBI BLASTP running while Sapote/Mamey parses previous rounds and prepares the next evidence table.

## Recommended batch size

The 30-protein mixes and top-10 setting below are for manual NCBI web searches. Tool defaults differ:

- `bgc-blastp-panel`: 20 proteins per file, a 30-protein first pass and 2 genes per BGC.
- `blastp-online`: 10 proteins per submission (hard cap 30), 3 hits per query; databases `nr`, `refseq_protein` or `swissprot`.
- `modeb-blastp`: 3 proteins per file.
- ClusteredNR has its own workflow.

Record the database, counts and hit settings you actually used.

Two manual modes are described below.

### Breadth mode

Use Breadth Mode when improving the all-BGC standing ledger.

Recommended composition:

- 12 priority BGCs × 2 proteins each
- 6 lower-confidence BGC probes × 1 protein each

Approximate total: 30 proteins.

### Depth mode

Use Depth Mode when preparing full Mode B cards for top antimicrobial or ecological leads.

Recommended composition:

- 6 lead BGCs × 5 proteins each

Approximate total: 30 proteins.

## NCBI BLASTP settings

Use NCBI web BLASTP with:

- Program: BLASTP
- Database: nr or clustered nr
- Max target sequences: 10

Download:

1. Hit Table CSV
2. Single-file XML2 only when needed for proof-grade details

## Failure recovery

If NCBI reports CPU limit, timeout, or very large output:

1. Reduce batch size to 10–15 proteins.
2. Isolate very large NRPS/PKS proteins into their own run.
3. Prefer domain-focused FASTAs for giant multidomain proteins.
4. Continue from the failed subset rather than restarting all BGCs.

## Expected Sapote/Mamey FASTA outputs

A BGC BLASTP panel export should provide:

- first-pass high-value FASTA,
- one-best-per-BGC FASTA,
- curated 2-per-BGC rounds,
- manifest CSV,
- round summary,
- user guide.

## Evidence roles

Class-defining evidence includes:

- PepM or FomB-like phosphonate enzymes,
- LanKC or other lanthipeptide maturation enzymes,
- YcaO or other RiPP maturation enzymes,
- lasso peptide maturation proteins,
- NRPS A/C/PCP domains,
- PKS KS/AT/ACP/module domains,
- terpene cyclases or squalene-hopene enzymes,
- siderophore biosynthesis enzymes.

Neighborhood-supporting evidence includes:

- transporters,
- regulators,
- immunity/resistance proteins,
- tailoring enzymes,
- precursor-processing proteins.

Generic function evidence includes:

- glycosyltransferases,
- peptidases,
- oxidoreductases,
- hydrolases,
- general ABC/MFS transporters.

Generic function evidence is valuable but should not be treated as equivalent to class-defining evidence.

## Public/private header safety

Private local evidence may retain raw strain labels with authorized custody. Sending those labels or their associated sequences to a remote service requires authorization for that disclosure; calling a run private does not keep remote submissions local.

Use the exact strain's approved disclosure scope and applicable private guards rather than inferring permission from an AS/SID prefix. Where authorized pseudonyms are required, retain a governed alias/query-hash map separately. The exporter's token cleaning does not anonymize strain labels, and a sanitized header does not authorize disclosure of its sequence. Do not label real query sequences as synthetic fixtures. Check public workbooks and reports for private identifiers or other disclosures outside the approved scope before release.

## Claim boundary

Do not claim compound identity from BLASTP alone.

## Bug-hunt checks

1. FASTA export should support ~30-protein batches.
2. FASTA export should support fallback 10–15 protein batches.
3. Giant NRPS/PKS proteins should be flagged.
4. BLASTP is optional evidence, not mandatory for every run.
5. Retain stable query/gene and complete strain, contig/node, region and BGC locators compatible with the selected parser. Current iterative-panel headers include strain, BGC, slot, role, gene, node, region, coordinates, amino-acid length and selection reason. Preserve product and KCB context in bound manifest/source records rather than assuming those fields are emitted in the header.
6. Headers must avoid breaking NCBI and Sapote/Mamey parser behavior.
