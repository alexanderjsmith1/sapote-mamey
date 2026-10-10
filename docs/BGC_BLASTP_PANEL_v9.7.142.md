# Current panel preparation contract (v9.7.447)

This builder prepares local FASTA; successful preparation does not mean any query was submitted or any similarity result accepted. The versioned guide below is retained with its sample residue cap corrected to the installed **85,000** default. Verify current server limits before an authorized submission; the software default is a separate limit.

- Defaults: 2 selected genes per BGC, first-pass target 30, 20 records per file, 85,000 residue packing target and a 2,500-aa giant threshold (`mamey/bgc_blastp_panel.py:264–328,339–415,466–491`). First pass is capped: if more BGCs compete than available slots, some receive no representative. Giant-core exemptions improve ordering but do not guarantee coverage of every BGC.
- One-best is a scope containing potentially several FASTA rounds, honoring the per-file record/residue targets; it is not necessarily one file (`502–513`). Unique protein totals within scopes differ from manifest rows repeated across scopes. Empty selection can produce summary/manifests with no FASTA rounds; counts must be inspected.
- Residue targets are **packing rules, not hard refusal gates**. A single oversized protein remains unsplit; FASTA is written first, then the batch is labelled `WARN_ABOVE_SAFETY_CAP` or `EXCEEDS_NCBI_WEB_LIMIT` (`403–415,418–463`). Review every batch status before any separately authorized use. The 100,000 constant is an implementation assumption, not fresh provider verification.
- FASTA headers sanitize tokens; preserve the unsanitized full identity `strain / full node-or-contig / region / BGC alias` and protein mapping in the selection manifest. Sequence normalization removes nonletter characters/stop symbols and uppercases translations (`127–128,191–257`). The manifest and summary do not record input, FASTA or protein SHA-256 (`522–567`); add governed source/export hash evidence outside the source package. Do not equate a sanitized header or alias-only internal grouping with a globally unique locus.
- Outputs use atomic replacement per individual file, but the whole panel has no directory-level transaction or fresh-directory guard (`84–95,483–484,495–567`). Reusing an output folder can replace named files and retain stale rounds from an earlier larger panel. Reconcile the current summary/manifest against inventory, quarantine incomplete candidate output, and use one governed candidate directory for recovery. Do not delete or overwrite source evidence.

Keep similarity, expression, activity and product-identity claims separate. Follow [current online protocol](ONLINE_BLASTP_PROTOCOL.md) for disclosure gates and [source-backed retrieval controls](447_COMPANION_RETRIEVAL_CONTROLS.md) for downstream evidence handling. Keep preparation, submitted queries and accepted results as separate recorded states.

---

# Iterative BGC BLASTP Panel Exporter — v9.7.142 starter

Operational examples below use the bundle-local launcher. Run them with the selected compatible interpreter from the directory containing `pyproject.toml` and `mamey_run.py`; follow the current task/profile and input bindings in `AGENTS.md`. An installed console/module entry point is supported, but does not by itself select this bundle.


Purpose: prepare local candidate protein FASTA panels from Mamey/antiSMASH evidence. Selection and packing are software heuristics; inspect coverage, batch statuses and identity/source bindings before any later use.

## Default workflow

For a separately authorized evidence-gathering session, the historical iterative sequence is below. Local export does not authorize a public upload. Prefer existing governed results when available; preserve query and provider provenance, and follow the current disclosure gate before a new submission:

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
python mamey_run.py bgc-blastp-panel \
  --input-zip AS-XXX.zip \
  --strain AS-XXX \
  --outdir AS-XXX_bgc_blastp_panel \
  --genes-per-bgc 2 \
  --first-pass-size 30 \
  --proteins-per-file 20 \
  --max-residues 85000
```

`--max-residues` sets a residue-based packing target, rather than a Markdown/file-character target. The installed default is 85,000 residues. The source labels batches above its 100,000-residue constant as `EXCEEDS_NCBI_WEB_LIMIT`; it still writes them. Neither threshold is a runtime refusal or a freshly verified service limit.

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

The one-best scope provides one selected representative per selectable BGC across one or more rounds. Curated rounds preserve BGC boundaries when possible, but oversized groups split and an oversized individual protein can exceed the target. The first-pass scope is capped and is not a complete BGC census. Inspect the manifest, unique-protein counts and every batch status.

## In-run package output

Mamey writes a `bgc_blastp_panel/` folder during normal package generation when translated CDS features are available. This folder is non-blocking: extraction still succeeds if the panel cannot be emitted, but the skip/warning is printed.

## Claim-safety rule

The FASTA panel is an evidence-gathering artifact only. BLASTP hits are sequence-similarity evidence, not proof of compound identity, pathway completeness, expression, or bioactivity.


## Result ingest and follow-up

After running NCBI BLASTP, use `python mamey_run.py blastp-followup --hit-table <hits.csv> --outdir <new-review-dir>` to parse the Hit Table CSV and optional XML2 file. The importer writes normalized hit tables, per-query decisions, and—when given the previous panel manifest plus FASTA folder—a next NCBI-safe follow-up FASTA. See `docs/BLASTP_FOLLOWUP_v9.7.142.md`.
