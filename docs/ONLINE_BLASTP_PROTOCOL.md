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
python mamey_run.py ingest-blastp-trove --help
python tools/ingest_blastp_rollups.py --help
python mamey_run.py blastp-online --help
python mamey_run.py blastp-round --help
```

## Ingesting existing results: choose the destination

| Command | Accepted input | Destination |
|---|---|---|
| `tools/ingest_blastp_rollups.py` | Dated per-strain rollup CSVs and supported single-protein ClusteredNR top-10 CSVs | An existing BLASTp SQLite evidence reservoir |
| `mamey_run.py ingest-blastp-trove` | Per-BGC directories containing the channel's supported per-gene CSV filenames | One selected package's channel-tagged BLASTp overlay |
| `mamey_run.py ingest-blastp` | NCBI HitTable CSV, with optional alignment XML | Master-workbook `B5_BLASTp_Hits` sheet |

For completed crawl rollups, inspect a dry run against explicit source and database paths:

```bash
python tools/ingest_blastp_rollups.py --root <source-root> --db <existing-hits.db>
python tools/ingest_blastp_rollups.py --root <source-root> --db <existing-hits.db> \
  --execute --source-workspace operator-import
```

Run the second command only when the displayed sources and destination are the intended ones and
the ingest is authorized. The tool rescans eligible source files and inserts new hit keys atomically;
the key includes strain, channel, gene, hit rank and subject accession, preserving multiple hits per
gene while keeping repeated imports idempotent. Previously stored rows are not overwritten. A source
path already present in the store does not prove that all its hit ranks were ingested. The tool
does not create a missing database. Use completed, stable CSVs. Later completed results require
another dry run; do not assume that a file still being written is a complete evidence source.
Reservoir insertion alone does not establish exact-sequence or complete-locus admission for a claim.

The package-overlay command accepts `<trove>/<STRAIN>/<BGC...>/` or a single-strain root with
`BGC...` directories. `--rekey-by-locus` resolves row aliases through the selected package's CDS
table; it does not make arbitrary gap-panel directory names discoverable. If no supported source
files are found, the command reports `NO_SOURCES_DISCOVERED`, the directories scanned, a bounded
sample of skipped names, and accepted filename patterns. It writes no new overlay, ledger,
quarantine, or receipt for that empty discovery. Correct the layout or command and retry without
deleting immutable receipts. A discovered source with zero admitted rows still retains its normal
receipt and quarantine evidence. No discovered source is not a verified no-hit result.

`ingest-blastp` accepts existing hit-table evidence; consult its help for the package and optional
alignment XML arguments. `blastp-round` supports phased planning; submission requires both `--run`
and `--confirm-public-sequence-upload` after reviewing the disclosed sequence count and digest.
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

## Optional per-strain BLASTp databases

When two antiSMASH assemblies of one strain carry different labels or contig numbering, compare their complete protein FASTAs before binding saved BLASTp evidence. The optional signature tool records raw FASTA hashes, an order-independent digest of `gene label + protein SHA-256`, and a separate sequence-only multiset digest:

Mamey already writes `<strain>_proteins.faa` and `<strain>_cds_table.csv` into each package. These are **BGC-member proteins**, not every protein in the genome. To make a portable, assembly-specific JSON index of the existing FASTA, including each gene's full contig, region, BGC alias, protein hash, and the antiSMASH input-ZIP hash, run:

```bash
python -m mamey.protein_signature --package <run>/<strain>/package \
  --out <analysis>/<strain>-bgc-protein-signature.json
```

This writes a new file outside the sealed package; it does not alter package contents. Keep the JSON beside BLASTp query and result receipts. A matching BGC-protein signature is not proof that the whole assemblies are identical.

```bash
python -m mamey.protein_signature <package-A-proteins.faa> <package-B-proteins.faa> \
  --out analysis/protein-signature-comparison.json
```

`EXACT_GENE_AND_SEQUENCE` means the normalized FASTA records agree despite row order. `SAME_SEQUENCE_MULTISET_RELABELED` means the proteins agree but gene labels differ. `LEFT_GENE_SEQUENCE_SUBSET` says every protein in the first FASTA occurs under the same gene label in the second, while the second has additional genes; it does not equate whole assemblies. `PARTIAL_OR_DIFFERENT` requires an assembly-level review before carrying results across. Repeated protein sequences remain counted; duplicate gene labels refuse the comparison. The output identifies a compatible **query source**, not whether a saved BLASTp hit came from that query. Full result admission still needs a query/RID receipt that binds each hit to its submitted protein sequence hash.

If you have a saved 22-column BLASTp hits SQLite store, you can export one database per strain. The source can be a cohort store or an existing per-strain database. The source is opened read-only. The selected Mamey package supplies the **current** gene, full contig, region, and BGC-alias roster; the source hit's possibly stale BGC alias remains visible as provenance but is never used to join coverage.

From the extracted bundle root:

```bash
python -m mamey.blastp_strain_db inspect --db <existing>/<strain>_blastp.db
python -m mamey.blastp_strain_db build --source-db <saved-hits.db> \
  --package <runs>/<strain>/package --out <output-root>
```

For a cohort, pass multiple package directories after `--package` (for example, a shell glob over one package per strain). The command makes **one transactionally consistent SQLite backup**, including committed WAL rows, and reuses that snapshot for every requested strain. It keeps the content-addressed `source_snapshot_<sha256>.sqlite` under the output root so the receipt remains verifiable later. This consumes approximately one extra source-database size of disk space; budget for that when exporting hundreds of strains. The command writes `<output-root>/<strain>_blastp.db`. It refuses duplicate strain packages and existing outputs; `--replace` atomically replaces a strain output only after the new database passes integrity checks. No source database or sealed package is changed.

The package's `manifest.json` strain must match the source hits' strain. If a reviewed package uses a different label, provide a two-column TSV with `package_strain` and `source_strain`, then pass `--strain-map <map.tsv>`. The original hit strain stays in the raw `hits` table and both labels are recorded in `source_receipt`. An unrecognized source strain refuses the whole batch **before any per-strain database is written**; an empty result requires explicit `--allow-empty`. Do not infer a mapping from a version suffix, filename, or changing BGC alias.

The new database retains every raw source row in `hits` and records the selected package's current full contig, region, and BGC alias in `locus_identity`. `hit_binding` gives every row a typed state: `LOCUS_BOUND`, `NONCURRENT_LOCUS`, `ZERO_OR_BLANK_AA_LENGTH`, `QUERY_CURRENT_AA_LENGTH_MISMATCH`, or `PROVENANCE_SUSPECT`. `held_hits` and `unbound_hits` keep rejected rows visible. Only `locus_bound_hits` contributes to separate nr/ClusteredNR/Swiss-Prot columns in `coverage` and to `clustered_gap`. `source_receipt` names and hashes the retained SQLite snapshot and package identity files. A gene with no locus-bound hit is a **missing or held evidence state**, not a tested negative. Length agreement is only a locus-binding check: the 22-column store lacks a query-protein sequence hash, so this export alone does **not** authorize a full Mode B BLASTp admission or a compound claim.

An existing per-strain database may be inspected without rebuilding. To rebind it to a newer package's physical loci, use it as `--source-db` and choose a different output root. Compare `raw_hits`, `locus_bound_hits`, `held_hit_rows`, the per-state hold counts, and the current-gene counts before using it in a report. Source BGC aliases can change across Mamey versions; the source alias is audit data, not the join key. The command does not submit BLASTp queries or infer compound identity.

## Related workflows

- [Channel-separated BLASTp workflow](BLASTP_NOVELTY_WORKFLOW.md): downstream comparison policy;
  distinguish workflow hypotheses from experimentally established results.
- [BLASTp batching SOP](SOPs/SOP-04_Iterative_NCBI_BLASTP_Batching.md).
- [Result upload and parsing SOP](SOPs/SOP-05_BLASTP_Result_Upload_Parse_Reprioritize.md).
- [Mode B authoring context](MODEB_LLM_AUTHORING_CONTEXT_HYGIENE.md).

Historical raw examples remain in their original release snapshot. Their absence from this operating
guide does not change the runtime scoring, inference thresholds or result vocabulary.
