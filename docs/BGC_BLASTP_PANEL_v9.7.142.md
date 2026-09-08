# Iterative BGC BLASTP Panel Exporter — v9.7.142 starter

Purpose: emit NCBI-web-safe protein FASTA panels from Mamey/antiSMASH evidence so users can investigate all BGCs efficiently without BLASTing every protein or whole contigs at once.

## Default workflow

Sapote/Mamey should guide the user through iterative BLASTP troubleshooting:

1. Start with a curated FASTA of approximately 30 high-value proteins.
2. Use NCBI BLASTP with **Max target sequences = 10**.
3. Download **Hit Table CSV** first.
4. Download **Single-file XML2** only when positives, similarity, alignment coverage, or proof-grade evidence is needed.
5. Upload/paste the RID/results back into Sapote/Mamey.
6. Sapote/Mamey reprioritizes remaining proteins: redundant high-confidence proteins can be downgraded; weak, unexpected, rare, resistance-like, transporter, or class-defining hits can be upgraded.
7. Generate the next FASTA batch from the updated priority list.
8. Continue until BGCs of interest have enough evidence for a claim-safe report.

If NCBI reports a CPU usage limit, timeout, or very large output file, reduce the batch size to 10 proteins and isolate giant multidomain NRPS/PKS proteins into their own follow-up batches or domain-focused FASTAs.

## Standalone command

```bash
python -m mamey bgc-blastp-panel \
  --input-zip AS-XXX.zip \
  --strain AS-XXX \
  --outdir AS-XXX_bgc_blastp_panel \
  --genes-per-bgc 2 \
  --first-pass-size 30 \
  --proteins-per-file 20 \
  --max-residues 90000
```

`--max-residues` is the load-bearing NCBI web-safety cap. NCBI web BLASTP rejects queries by amino-acid residues, not by Markdown/file characters. The hard limit is treated as 100,000 residues; the default safety cap is 90,000 residues.

## Output scopes

```text
<strain>_BLASTP_FIRST_PASS_top030_round001_for_BLASTP.faa
<strain>_one_best_protein_per_BGC_NCBI_safe_round001_for_BLASTP.faa
<strain>_curated_2_per_BGC_NCBI_safe_round001_for_BLASTP.faa
<strain>_curated_2_per_BGC_NCBI_safe_round002_for_BLASTP.faa
...
<strain>_BGC_BLASTP_PANEL_selection_manifest.csv
<strain>_NCBI_safe_batch_summary.csv
<strain>_BGC_BLASTP_PANEL_summary.json
<strain>_BGC_BLASTP_PANEL_USER_GUIDE.md
```

The one-best file gives a broad overview across BGCs. The curated two-per-BGC files preserve BGC boundaries when possible and stay below the residue cap. The first-pass file is the recommended starting point for ChatGPT/NCBI troubleshooting.

## In-run package output

Mamey writes a `bgc_blastp_panel/` folder during normal package generation when translated CDS features are available. This folder is non-blocking: extraction still succeeds if the panel cannot be emitted, but the skip/warning is printed.

## Claim-safety rule

The FASTA panel is an evidence-gathering artifact only. BLASTP hits are sequence-similarity evidence, not proof of compound identity, pathway completeness, expression, or bioactivity.


## Result ingest and follow-up

After running NCBI BLASTP, use `python -m mamey blastp-followup` to parse the Hit Table CSV and optional XML2 file. The importer writes normalized hit tables, per-query decisions, and—when given the previous panel manifest plus FASTA folder—a next NCBI-safe follow-up FASTA. See `docs/BLASTP_FOLLOWUP_v9.7.142.md`.
