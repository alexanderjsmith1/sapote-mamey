# BLASTP follow-up reader

`blastp-followup` reads the result files you download from NCBI web BLASTP and writes review tables. It suggests which proteins to search next. It reads local files and writes review files to the chosen output directory. It does not submit anything to NCBI. It does not protect package or workbook paths from being chosen as output: use a fresh review directory outside your packages and source data.

To submit searches and bring results into the workbook, use [the online BLASTP protocol](ONLINE_BLASTP_PROTOCOL.md). Search in small batches, not one query of every protein.

## Before you start

- A first-pass FASTA from `bgc-blastp-panel`.
- An NCBI BLASTP run on that FASTA with `Max target sequences = 10`.
- The run's **Hit Table (CSV)** download. This file is required. NCBI usually gives it with no header row, and the reader accepts that.
- Optional: the **Single-file XML2** download from the same run. It adds subject titles and query lengths.

Keep the CSV and XML2 from the same search. Match them to the strain, contig, region and BGC you submitted before you interpret anything.

## Run it

```bash
python mamey_run.py blastp-followup \
  --hit-table EXAMPLE-HitTable.csv \
  --xml2 EXAMPLE-Alignment.xml \
  --outdir EXAMPLE_blastp_followup
```

Leave out `--xml2` if you have no XML2 file. Use a new `--outdir` each time. A reused folder has its files replaced.

To also get a suggested next FASTA, add the earlier panel and its selection manifest. Give both or neither:

```bash
python mamey_run.py blastp-followup \
  --hit-table EXAMPLE-HitTable.csv \
  --xml2 EXAMPLE-Alignment.xml \
  --previous-selection EXAMPLE_BGC_BLASTP_PANEL_selection_manifest.csv \
  --panel-dir EXAMPLE_bgc_blastp_panel \
  --next-proteins 10 \
  --target-residues 20000 \
  --outdir EXAMPLE_blastp_followup
```

`--next-proteins` (default 10) and `--target-residues` (default 20000) work differently. Selection stops once the chosen count reaches `--next-proteins`. A protein that would push the residue total past `--target-residues` is skipped, and smaller ones after it can still be added. The first protein is always admitted before either check, even when `--next-proteins` is 0 or that protein alone exceeds the residue target. Check the counts the command prints.

## What you should see

The command prints a summary and exits 0 if at least one query had a parsed hit. It exits 1 if none did. The files are still written in that case, so check the counts in the JSON.

| File | Holds |
|---|---|
| `BLASTP_hit_table_normalized.csv` | Every parsed hit, with XML2 details added when supplied. |
| `BLASTP_query_summary.csv` | Top hit and follow-up decision for each query that had a hit. |
| `BLASTP_reprioritization.csv` | The same rows as a sortable table for planning the next batch. |
| `BLASTP_FOLLOWUP_next_batch_round001_for_BLASTP.faa` | The suggested next FASTA. Written only when both `--previous-selection` and `--panel-dir` are given. The name always says `round001`. |
| `BLASTP_followup_summary.json` | Counts and the path of the next FASTA. |
| `BLASTP_FOLLOWUP_USER_GUIDE.md` | Plain-language next steps. |

## Follow-up decisions

The top hit is chosen by bitscore, then identity, then alignment length.

- `DOWNGRADE_CONFIRMED_REDUNDANT`: strong, ordinary annotation. Usually skip it in the next batch.
- `RETAIN_CONTEXT_RELEVANT`: useful context, such as a transporter, regulator or tailoring enzyme.
- `RETAIN_PROOF_RELEVANT`: a hit relevant to the product class. Carry it into evidence tables.
- `UPGRADE_WEAK_OR_PARTIAL`: weak or partial hit. Search again if the BGC matters.
- `UPGRADE_UNINFORMATIVE_TOP_HIT`: the top hit is hypothetical or uninformative.
- `ISOLATE_GIANT_OR_DOMAIN_FOLLOWUP`: very large query. Split it into domain-sized queries if NCBI struggles.
- `REVIEW_AMBIGUOUS`: moderate or mixed evidence. Read it by hand.
- `UPGRADE_NO_HIT`: the classifier has this decision, but it never appears in the output. Queries with no parsed hit have no row.

BLASTP shows sequence similarity only. It does not show compound identity, pathway completeness, expression or bioactivity.

## Limits

- **No row means unknown.** A query with no row may have had no hit, or may never have been searched. The summary is not a list of submitted queries.
- **Headerless CSV.** The reader keeps the first row as data unless it clearly looks like a header. Query titles that contain commas, such as `complete_genome, Type: T1PKS`, are rejoined from the fixed trailing columns. Short rows are skipped.
- **Bad numbers.** A row whose identity or bitscore cannot be parsed, or is not finite, is skipped and does not appear in the output. Other integer fields (alignment length, mismatches, gap opens, start and end coordinates) fall back to 0 when unparseable, so a 0 there is not a measured zero. Positives that are blank stay blank. Reconcile the row count against the input Hit Table to see how many rows were skipped.
- **Coverage.** `query_coverage` is alignment length over query length for one hit row, capped at 1. It is `NA` when the query length is unknown. It is not a union of several alignments. The identical and positive counts are rebuilt from percentages, so use the raw alignments for exact counts.
- **XML2 failures are quiet.** A malformed or empty XML2 file gives no enrichment and no error. `xml_query_count=0` does not prove that XML was absent. XML2 is matched to a hit by exact query ID first, then by BGC alias and gene.
- **Next FASTA.**
  - It skips only headers that appear in the parsed-hit CSV, so a query that had no hit can be suggested again.
  - The panel folder is read for `*.faa` files directly inside it. Headers must be unique within it. Mixing strains in one manifest can drop rows.
  - Check each suggested sequence against its source before you submit it. A suggestion is not permission to submit.
- **Interrupted runs.** Files are written one at a time. A failure can leave new tables beside older summary files. Keep the failed folder and rerun into a new one.
- **Raw files.** Keep the original CSV and XML2. The reader keeps parsed hits only and records no file hashes.
