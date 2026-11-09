# Panel preparation contract (historical filename)

## What it does

- Reads an antiSMASH result and writes local protein FASTA files in rounds, plus a selection manifest, a batch summary and a JSON summary.
- Defaults: 2 genes per BGC, a first-pass scope of 30, 20 records per file, an 85,000-residue cap per round, and a 2,500-aa threshold for very large proteins. `--help` shows the same defaults.

## What it does not do

- It does not submit anything. A prepared panel is not a submitted query and not an accepted result.
- It does not split a protein to fit a round. A protein above the residue cap stops that scope; earlier scopes may already be written.
- The first-pass scope is capped, so some BGCs can get no representative. It is not a complete BGC census.
- It does not record input, FASTA or protein SHA-256 values, and it has no fresh-folder guard. Use a new output folder and record hashes yourself.
- FASTA headers are sanitized. Keep the full identity `strain / full node-or-contig / region / BGC alias` from the manifest.

Check current server limits before any authorized submission. The software cap is a separate limit. Maintainer details with code references are at the end of this page.

Keep similarity, expression, activity and product-identity claims separate. Follow [current online protocol](ONLINE_BLASTP_PROTOCOL.md) for disclosure gates and [source-backed retrieval controls](447_COMPANION_RETRIEVAL_CONTROLS.md) for downstream evidence handling. Keep preparation, submitted queries and accepted results as separate recorded states.

---

# Iterative BGC BLASTP panel exporter

Run the examples below with `python mamey_run.py` from the folder that holds `pyproject.toml`. An installed `mamey` command may point at a different bundle.


Purpose: prepare local candidate protein FASTA panels from Mamey/antiSMASH evidence. Selection and packing are software heuristics; inspect coverage, batch statuses and identity/source bindings before any later use.

## Default workflow

The older iterative sequence is below. Exporting does not upload anything. Use existing results when you have them, keep the query and provider records, and check the [online protocol](ONLINE_BLASTP_PROTOCOL.md) before a new submission:

1. Start with a curated FASTA of approximately 30 high-value proteins.
2. Use NCBI BLASTP with **Max target sequences = 10**.
3. Download **Hit Table CSV** first.
4. Retain **Single-file XML2** when its alignment metadata is needed. XML enrichment alone does not admit exact query identity or make evidence proof-grade; reconcile query rosters, protein/source hashes and result/job bindings separately.
5. Upload/paste the RID/results back into Sapote/Mamey.
6. Review the importer's per-query heuristic decisions and unresolved identities/coverage. These labels do not establish biological redundancy or a validated function.
7. Review a candidate next FASTA separately: the current follow-up helper uses the previous selection manifest's ordering and exact parsed-hit-header exclusion, rather than automatically applying those classifier decisions to a newly ranked list.
8. Continue until BGCs of interest have enough evidence for a claim-safe report.

If NCBI reports a CPU usage limit, timeout, or very large output file, reduce the batch size to 10 proteins and isolate giant multidomain NRPS/PKS proteins into their own follow-up batches or domain-focused FASTAs.

## Standalone command

```bash
python mamey_run.py bgc-blastp-panel \
  --input-zip <input.zip> \
  --strain <strain> \
  --outdir <strain>_bgc_blastp_panel \
  --genes-per-bgc 2 \
  --first-pass-size 30 \
  --proteins-per-file 20 \
  --max-residues 85000
```

`--max-residues` sets the enforced per-round residue cap, rather than a Markdown/file-character target; its default is 85,000 residues. An intact protein above that requested cap refuses scope preparation. The separate 100,000-residue status constant is not a freshly verified service limit: a user-selected cap above it can still permit a batch labeled `EXCEEDS_NCBI_WEB_LIMIT`.

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

The one-best scope provides one selected representative per selectable BGC across one or more rounds. Proteins are assigned to a BGC by contig name and coordinate overlap among the parsed records. Each manifest row's `selection_binding_state` says how unique that join was: `UNIQUE_IN_PARSED_RECORDS_NOT_SEQUENCE_VERIFIED`, or a hold (`HOLD_AMBIGUOUS_LOCUS_TAG`, `HOLD_AMBIGUOUS_CONTIG_COORDINATES`) when the locus tag or contig and coordinates repeat. The summary JSON lists `bgcs_without_selection` and counts `selection_binding_holds`. A filled identity column is a declared mapping, not proof that the selection is bound to the source locus; resolve every hold before you claim per-locus coverage. Curated rounds preserve BGC boundaries when possible, but groups that exceed the round cap split. An individual protein above the requested residue cap is refused rather than emitted over that cap. The first-pass scope is capped and is not a complete BGC census. Inspect the manifest, unique-protein counts and every batch status.

## In-run package output

During package generation Mamey attempts `bgc_blastp_panel/` with two genes per BGC, 20 proteins per file, first-pass size 30 and an explicit **90,000-residue** cap, differing from the standalone 85,000 default. Empty selection can yield no FASTA. Caught panel failures print a warning without blocking extraction; inspect actual artifacts and summary.

## Claim-safety rule

The FASTA panel is an evidence-gathering artifact only. BLASTP hits are sequence-similarity evidence, not proof of compound identity, pathway completeness, expression, or bioactivity.


## Result ingest and follow-up

After running NCBI BLASTP, use `python mamey_run.py blastp-followup --hit-table <hits.csv> --outdir <new-review-dir>` to parse the Hit Table CSV and optional XML2 file. The importer writes normalized hit tables, per-query decisions, and—when given the previous panel manifest plus FASTA folder—a candidate follow-up FASTA requiring independent roster, sequence and batch-limit review. See `docs/BLASTP_FOLLOWUP_v9.7.142.md`.

## Maintainer notes (code references)

These notes cite `mamey/bgc_blastp_panel.py` line ranges as of this page's last check. They are for maintainers; the sections above are the user contract.

This builder prepares local FASTA; successful preparation does not mean any query was submitted or any similarity result accepted.

- Defaults: 2 selected genes per BGC, first-pass target 30, 20 records per file, 85,000 residue packing target and a 2,500-aa giant threshold (`mamey/bgc_blastp_panel.py:264–328,339–415,466–491`). First pass is capped: if more BGCs compete than available slots, some receive no representative. Giant-core exemptions improve ordering but do not guarantee coverage of every BGC.
- One-best is a scope containing potentially several FASTA rounds, honoring the per-file record/residue targets; it is not necessarily one file (`502–513`). Unique protein totals within scopes differ from manifest rows repeated across scopes. Empty selection can produce summary/manifests with no FASTA rounds; counts must be inspected.
- Current round assignment requires positive record/residue caps and refuses an intact protein above the requested residue cap before writing that scope (`mamey/bgc_blastp_panel.py`). It does not split that protein to force a fit. Earlier scopes can already have been written before a later scope refuses. The retained `EXCEEDS_NCBI_WEB_LIMIT` status can still be emitted when an explicitly larger requested cap permits a batch above the source's 100,000 constant; that constant is an implementation assumption, not fresh provider verification. Review requested limits, actual counts and statuses before any separately authorized use.
- FASTA headers sanitize tokens; preserve the unsanitized full identity `strain / full node-or-contig / region / BGC alias` and protein mapping in the selection manifest. Sequence normalization removes nonletter characters/stop symbols and uppercases translations (`127–128,191–257`). The manifest and summary do not record input, FASTA or protein SHA-256 (`522–567`); add governed source/export hash evidence outside the source package. Do not equate a sanitized header or alias-only internal grouping with a globally unique locus.
- Outputs use atomic replacement per individual file, but the whole panel has no directory-level transaction or fresh-directory guard (`84–95,483–484,495–567`). Reusing an output folder can replace named files and retain stale rounds from an earlier larger panel. Reconcile the current summary/manifest against inventory, quarantine incomplete candidate output, and use one governed candidate directory for recovery. Do not delete or overwrite source evidence.
