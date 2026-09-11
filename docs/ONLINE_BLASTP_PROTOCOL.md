# BLASTp evidence: ingest existing results or submit a scoped query

Use existing, source-bound BLASTp results when available. `blastp-online` is an optional live
submission command, not a staging-only tool. This guide replaces the earlier experimental recipe
and proposed command description. Command behavior is grounded in `mamey/blastp_online.py` and the
local CLI; historical timing observations are not service guarantees.

## Start with identity and evidence availability

Bind the full locus identity: `strain / full node-or-contig / region / BGC alias`. Use its region
GenBank or a full antiSMASH ZIP with a matching crosswalk. Keep original sequences and results
immutable. A basename, alias or result order alone is insufficient evidence of a protein join.
Retain query identifiers and normalized sequence hashes with source receipts where available.

Keep nr, ClusteredNR, local Swiss-Prot and antiSMASH comparator evidence in separate channels.
Record the actual database and search parameters. A result from one channel cannot fill a missing
result in another by relabelling it.

## Inspect the current commands

```bash
python mamey_run.py ingest-blastp --help
python mamey_run.py blastp-online --help
python mamey_run.py blastp-round --help
```

`ingest-blastp` accepts existing hit-table evidence; consult its help for the package and optional
alignment XML arguments. `blastp-round` supports phased planning; `--run` enables submission.
The following live command contacts NCBI when executed, so use it only within the user's authorized
external-search scope:

```bash
python mamey_run.py blastp-online   --package inputs/query.region001.gbk   --database nr --batch-size 10 --outdir analysis/blastp
```

For a full ZIP, select `--bgc` with the matching `--crosswalk` (a crosswalk CSV or sealed package
directory), or use the explicit `--region` locator. Confirm the resolved locus before submission.
The supported database choices for this command are `nr`, `refseq_protein` and `swissprot`;
ClusteredNR belongs to its separate workflow and ledger.

## Batching and execution

The command defaults to ten proteins per batch and caps the requested count at thirty. Its batcher
also applies a residue budget and isolates proteins longer than 2,500 residues. Do not treat the
old ten-protein experiment as a universal service limit or fixed turnaround promise.

Use the bundled runner's pacing and recorded states rather than copying the retired ad hoc URL-API
snippets. Retain RIDs, terminal diagnostics, raw responses and the precise submitted sequence set.
Do not turn an unavailable, incomplete or failed search into a tested-negative observation.

## Outputs and interpretation

The command writes a scoped `*_online_blastp.csv` panel and `*_cluster_reads.json` under `--outdir`
(or the working directory if omitted). The prefix follows the requested locus selector; retain
complete identity in the associated record. Inspect the actual panel and cluster-read fields.
A file's existence or an exit status alone does not verify its scientific interpretation.

For each cited hit preserve accession, organism, percent identity, query coverage, E-value,
bitscore, query identity and source/database provenance. Retain missing translations and queries
without admitted results as distinct states. Map results using identifiers and sequence evidence,
not submission index alone.

Compare hits with domains and comparator evidence when authoring a card. A named homolog is a
functional hypothesis; numerical similarity thresholds alone do not prove a specific function.
No hit does not establish novel chemistry, and a shared reference family does not prove compound
identity. Use the selected Mode B profile's current section map rather than historical section
numbers embedded in an old recipe.

For RiPP analyses, retain the actual precursor sequence and evidence for leader/core boundaries.
Short or low-complexity sequences require explicit uncertainty; do not calculate a confident
mature-product mass from an unbound core assignment.

## Related workflows

- [Channel-separated BLASTp workflow](BLASTP_NOVELTY_WORKFLOW.md): downstream comparison policy;
  distinguish workflow hypotheses from experimentally established results.
- [BLASTp batching SOP](SOPs/SOP-04_Iterative_NCBI_BLASTP_Batching.md).
- [Result upload and parsing SOP](SOPs/SOP-05_BLASTP_Result_Upload_Parse_Reprioritize.md).
- [Mode B authoring context](MODEB_LLM_AUTHORING_CONTEXT_HYGIENE.md).

Historical raw examples remain in their original release snapshot. Their absence from this operating
guide does not change the runtime scoring, inference thresholds or result vocabulary.
