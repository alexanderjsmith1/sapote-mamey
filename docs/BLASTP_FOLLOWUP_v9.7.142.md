# BLASTP Follow-up Ingest — v9.7.142 starter

Sapote/Mamey BLASTP support is designed for iterative NCBI web BLASTP, not one giant all-protein query.

## Recommended loop

1. Generate a small first-pass FASTA with `bgc-blastp-panel`.
2. Run NCBI BLASTP with `Max target sequences = 10`.
3. Download the **Hit Table CSV** first.
4. Download **Single-file XML2** only when query coverage, positives/similarity, or proof-grade hit titles are needed.
5. Ingest results:

```bash
python -m mamey blastp-followup \
  --hit-table 40WGV6PM016-Alignment-HitTable.csv \
  --xml2 40WGV6PM016-Alignment.xml \
  --outdir AS-XXX_blastp_followup_round001
```

6. If a previous panel directory is available, emit the next safe FASTA:

```bash
python -m mamey blastp-followup \
  --hit-table 40WGV6PM016-Alignment-HitTable.csv \
  --xml2 40WGV6PM016-Alignment.xml \
  --previous-selection AS-XXX_BGC_BLASTP_PANEL_selection_manifest.csv \
  --panel-dir AS-XXX_bgc_blastp_panel \
  --next-proteins 10 \
  --target-residues 20000 \
  --outdir AS-XXX_blastp_followup_round001
```

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

`Max target sequences = 10` should be treated as a user-facing target, not a parser assumption. BLASTP result files can contain more than 10 hit rows for a query, and Sapote/Mamey keeps every row.
