# BLASTP Follow-up Ingest — v9.7.142 starter

## Current reader contract (.447)

This filename retains a historical version suffix. `blastp-followup` remains a local side-artifact reader; it does not ingest the workbook or package overlay. For ingestion routes and submission controls read [ONLINE_BLASTP_PROTOCOL.md](ONLINE_BLASTP_PROTOCOL.md). Record searches and accepted evidence in their own run receipts.

Use a fresh output directory: fixed filenames are replaced on reuse. The second recipe below is an alternative to the first; choose a different directory if preserving both reviews. XML2 is optional: omit `--xml2` if no matching XML exists. Bind every download to the same submitted query roster, strain, full contig, region and BGC identity before interpretation. XML enrichment first looks up the exact CSV query ID. Its fallback uses the first parsed BGC-alias/gene match, without requiring strain, full contig, region or unique matching XML query; subject accession matching also removes accession versions. These conveniences do not admit cross-strain, ambiguous or different-version evidence. Use a bound single-source query roster and verify each enrichment against original CSV/XML; leave unbound title/coverage/context as held rather than accepting a merged value.

The query table includes only IDs with parsed hits; it is not a census of submitted queries. `UPGRADE_NO_HIT` exists in the classifier but the summary loop does not visit absent queries. Missing rows are not completed no-hit searches. `REVIEW_AMBIGUOUS` is another possible decision. Top-hit choice follows bitscore, identity and alignment length, not highest identity alone.

Exit 0 means at least one query had a parsed hit; exit 1 means none did, after files were written. Inspect JSON counts. The optional next-batch FASTA can be empty even with exit 0; its literal `round001` filename does not record the actual operator round. The reprioritization table repeats query summary rows, not BGC aggregates. Retain original CSV/XML: preservation applies to successfully parsed hits, not a raw-row conservation guarantee.

Source: `mamey/blastp_followup.py:417–497,611–699`. Bind actual runtime results to the selected source and inputs.

Operational examples below use the bundle-local launcher. Run them with the selected compatible interpreter from the directory containing `pyproject.toml` and `mamey_run.py`; follow the current task/profile and input bindings in `AGENTS.md`. An installed console/module entry point is supported, but does not by itself select this bundle.


Sapote/Mamey BLASTP support is designed for iterative NCBI web BLASTP, not one giant all-protein query.

## Local writes and interruption recovery

Outputs are written sequentially with fixed sibling `.tmp` names and per-file replacement; there is no complete-set rollback. The output parent/root is created before parsing. A later panel/batch/summary failure can leave new normalized CSVs beside older summary/guide files. Reusing a directory without requesting the batch does not delete an earlier next-batch FASTA. Follow the current summary's `next_fasta` field and bind the invocation/output roster; filename existence alone does not make that file current. Preserve the failed directory and original sources, capture diagnostics, and use a fresh output for a corrected retry. Avoid concurrent writers to the same directory. Summary JSON records paths/counts but no source/output hashes; retain CSV/XML, panel/manifest, owner, arguments and artifact hashes separately.

## Recommended loop

1. Generate a small first-pass FASTA with `bgc-blastp-panel`.
2. Run NCBI BLASTP with `Max target sequences = 10`.
3. Download the **Hit Table CSV** first.
4. Download **Single-file XML2** only when query coverage, positives/similarity, or proof-grade hit titles are needed.
5. Ingest results:

```bash
python mamey_run.py blastp-followup \
  --hit-table 40WGV6PM016-Alignment-HitTable.csv \
  --xml2 40WGV6PM016-Alignment.xml \
  --outdir AS-XXX_blastp_followup_round001
```

6. If a previous panel directory is available, inspect the optional next-batch FASTA:

```bash
python mamey_run.py blastp-followup \
  --hit-table 40WGV6PM016-Alignment-HitTable.csv \
  --xml2 40WGV6PM016-Alignment.xml \
  --previous-selection AS-XXX_BGC_BLASTP_PANEL_selection_manifest.csv \
  --panel-dir AS-XXX_bgc_blastp_panel \
  --next-proteins 10 \
  --target-residues 20000 \
  --outdir AS-XXX_blastp_followup_round001
```

## Review the optional next batch before any submission

Supply both `--previous-selection` and `--panel-dir` to request the next FASTA; supplying only one silently omits this step. Panel discovery reads only immediate lowercase `*.faa` files. It keys sequences by the complete stripped header, silently replacing duplicate headers and normalizing sequence text by dropping nonletters and uppercasing. The helper does not check original sequence hashes, amino-acid alphabet, recorded `aa_len` against emitted length, or a full-locus source register. Keep one governed strain/panel scope with unique headers and reconcile each emitted sequence/header with its original binding. Manifest-row deduplication uses BGC alias, locus tag, protein ID and slot, without strain; mixing strain manifests can silently omit otherwise independent rows.

Selection prefers curated rows, then one-best rows, no-warning rows, higher numeric selection score and shorter recorded length. Missing/unmatched/empty panel sequences are skipped. It excludes only exact headers in the parsed-hit CSV roster, not the complete submitted-query roster or XML no-hit query roster. A previously completed no-hit query or a CSV-truncated header can therefore be suggested again. Reconcile the candidate with the original submission/admission ledger before accepting it; an optional next-batch artifact does not authorize a new remote submission.

`--next-proteins` and `--target-residues` are selection controls, not hard admission ceilings in this implementation: the first eligible protein is accepted before those checks. It can exceed the residue target, and zero/negative limits are not rejected as invalid arguments. Use positive intended limits and inspect the emitted count/residue total plus individual sequence lengths before adopting the candidate. The follow-up classifier's decisions do not directly determine this batch; selection uses the previous manifest ordering criteria and exact searched-header exclusion.

## Outputs

- `BLASTP_hit_table_normalized.csv` — every parsed hit from the CSV, enriched by XML2 when supplied.
- `BLASTP_query_summary.csv` — top hit and follow-up decision per query.
- `BLASTP_reprioritization.csv` — sortable decision table for next batch planning.
- `BLASTP_FOLLOWUP_next_batch_round001_for_BLASTP.faa` — emitted only when previous manifest + panel FASTA files are provided.
- `BLASTP_followup_summary.json` — machine-readable counts.
- `BLASTP_FOLLOWUP_USER_GUIDE.md` — plain-language next steps.

## Follow-up decisions

- `DOWNGRADE_CONFIRMED_REDUNDANT` — strong, ordinary annotation; usually do not spend the next BLASTP batch here.
- `RETAIN_CONTEXT_RELEVANT` — useful context, such as transporter/regulator/tailoring support.
- `RETAIN_PROOF_RELEVANT` — product/class-relevant hit worth carrying into proof tables.
- `UPGRADE_WEAK_OR_PARTIAL` — weak or partial hit; prioritize if the BGC matters.
- `UPGRADE_UNINFORMATIVE_TOP_HIT` — top hit is hypothetical/uninformative.
- `ISOLATE_GIANT_OR_DOMAIN_FOLLOWUP` — giant NRPS/PKS-like query should be split into domain-focused follow-up if NCBI struggles.

## Claim safety

BLASTP evidence is sequence similarity only. It does not prove compound identity, pathway completeness, expression, or bioactivity.

## Hit Table CSV edge cases

NCBI web BLASTP Hit Table CSV is usually headerless. Sapote/Mamey preserves the first row as data unless it clearly looks like a header. Some query titles also contain commas, especially KCB labels such as `complete_genome, Type: T1PKS`; NCBI may not quote those fields. The parser therefore recovers rows by treating the final BLASTP metric columns as stable and joining extra leading fields back into the query title. This prevents false zero-identity or weak-hit calls for comma-bearing query IDs.

`Max target sequences = 10` should be treated as a user-facing target, not a parser assumption. BLASTP result files can contain more than 10 hit rows for a query, and Sapote/Mamey keeps every successfully parsed hit.
