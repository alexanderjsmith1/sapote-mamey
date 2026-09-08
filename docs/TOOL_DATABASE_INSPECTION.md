# Read only tool database inspection

`tool-database-inspect` inspects one explicitly selected frozen tool-database manifest. It does not register a project, select evidence, ingest records, render a card, or grant scientific admission. Existing package catalog, BLASTP ingestion and exact-identity owners keep their roles.

Run from the portable bundle:

```sh
python mamey_run.py tool-database-inspect --root /work/evidence --manifest RELEASE_MANIFEST.json
python mamey_run.py tool-database-inspect --root /work/evidence --manifest RELEASE_MANIFEST.json --adapter gene-census-v1 --locus TEST-1 contig_complete_001 region001 cluster001 --limit 100 --offset 0
```

Use a native path for your operating system. The four-part example identity is `TEST-1 / contig_complete_001 / region001 / cluster001`. The root must already exist. Manifest locators are relative beneath it; database locators are relative to the manifest directory and must remain inside the root. Symlink inputs, absolute database locators and traversal are refused. No directories, evidence copies or output files are created by the inspection API.

## Manifest contract

The supported envelope is `tool_database_release_manifest/1`, with required `database`, lowercase `database_sha256`, and integer `bytes`. When `files` is present it must contain exactly one matching database entry with agreeing hash and size. Other files and dependency roots are not opened. Their closure is not verified.

`--manifest-sha256` optionally supplies an externally expected manifest hash. Without it, a self-consistent manifest is user-selected, not independently authenticated. Integrity checks cover database bytes, size, SQLite quick_check and pre/post file stability. These checks do not validate scientific claims or authenticate the producer.

## Supported adapters

- `manifest`: shared-envelope inspection only. Declared channel, version, status, profile/version metadata and coverage remain labeled declared, not recomputed. A locus request returns NOT_SUPPORTED, never fabricated empty evidence.
- `gene-census-v1`: the source-verified census v0.1.1 layout with no manifest channel field, explicit locus/gene tables and section_profile metadata. Returns bounded gene rows, including existing hold and membership fields.
- `keyword-gene-v1`: v0.1.0 regulator, chitinase, resistance-keyword and transporter-keyword channels. Returns gene state and groups_json, not decompressed annotation text or functional acceptance. Required table/column shapes are checked; recorded profile metadata is not a contract-completeness decision.

Domains, profile bridge, cassette coupling, resistance tiers, fragment context, saved-reference linkage, TFBS, codon counts, CCTT and UMED require their own result adapters. Their shared manifests can be inspected without implying result integration. No adapter is selected from a filename, alias, directory scan or heuristic.

### Explicit BLASTp result adapters

`blastp-nr-v1` and `blastp-clustered-nr-v1` support their separate v0.1.0 channel schemas. `blastp-swissprot-v2` supports local Swiss-Prot v0.2.0 and verifies its lossless grouped hit-pack hashes. Channel and database metadata must agree with the selected adapter. No source Python or arbitrary database views are executed.

The existing Python API also accepts `gene_order=None`, `view="genes"`, `search_id=None`, `hit_rank=None`. The corresponding CLI flags are `--gene-order`, `--view`, `--search-id`, `--hit-rank`. Choose one of four views:

- `genes`: complete locus identity required for rows; paginated binding, protein and availability records. Optional gene order selects one exact gene.
- `searches`: complete locus plus gene order required. Returns recorded observations, source hashes, query proof/receipt and source XML or dataset/batch provenance. Multiple searches and mixed outcomes are retained. Missing outcomes are not biological absence or proof no search ever ran.
- `hits`: additionally requires a gene-bound search ID. Returns source-retained hit evidence, descriptions and raw coverage, excluding HSP arrays, with retained HSP counts and an HSP view selector.
- `hsps`: additionally requires the source hit rank. Returns paginated raw HSP objects, preserving source fields, alignment denominators and metrics without recalculating scores or accepting function claims.

Swiss-Prot search selector `1` is scoped to the query's single outcome; it is not an original source search ID. All other searches must belong to that exact gene's sequence hash. Historical job labels and source paths are inert provenance, never alternate current identities or paths followed by the reader. The response envelope and gene object provide the full current locus identity for search/hit/HSP records.

Follow `next_offset` for the selected view. `total_records` and `omitted_records` refer only to source-retained data; they do not describe all possible matches in the reference database. Raw requested retention settings, when recorded, stay in search provenance. A locus may contain at most 10,000 genes per inspection; a compressed or uncompressed evidence unit is capped at 8 MiB, and provenance metadata/jobs at 256 rows per unit. The two-MiB total response ceiling still applies. Over-budget evidence is a typed hold, not a silent top-N result. These are inspection safety limits, not biological thresholds.

## Query and response

The Python entry point is `inspect_tool_database(root, manifest, *, adapter="manifest", identity=None, limit=100, offset=0, expected_manifest_sha256=None)` in `mamey.tool_database_reader`. Identity is a four-item tuple or list in strain/full-contig/region/alias order, validated through the existing exact-identity owner.

Responses separate `integrity_state`, `source_status`, `declared_coverage_not_recomputed`, `results.observed_counts`, and `scientific_admission=NOT_PERFORMED`. Concrete adapters return the full identity on every gene row. Missing loci, duplicate/conflicting identity, duplicate gene order, and loci without gene rows have typed missing/held states. Source row holds remain unchanged. An ordinary returned row is recorded evidence, not admitted evidence.

Use `limit` from 1 through 1000 and a nonnegative `offset`; follow `next_offset` until null. Total and returned record counts are explicit. Queries use bound parameters and fixed adapter SQL, with a ten-second SQL execution budget and a two-MiB serialized response ceiling. There is no arbitrary SQL or write mode. Errors raise `ToolDatabaseInspectionError` with a stable code; the CLI emits HELD JSON and exits 2. Result-adapter-not-selected and missing-locus states are inspectable responses, not scientific successes.

## Platform and concurrency limits

The implementation uses standard-library pathlib and SQLite URI read-only mode with query_only and a native read transaction, without fcntl or other POSIX-only locks. Only frozen rollback-journal-format databases without WAL, SHM or journal sidecars are supported. Stop writers before inspection. Busy/invalid databases, SQL-budget exhaustion and observed source drift are refused. Pre/post hashes do not defeat a hostile process that replaces and restores filesystem contents during the read.

The API has no write side effects. The broader CLI may initialize its existing dependency caches; this is distinct from evidence-database mutation. Windows and Linux behavior require platform CI before a cross-platform runtime PASS is claimed. Inspection output may contain private identities and source-declared metadata; it is a local review surface, not a public export or redaction workflow.
