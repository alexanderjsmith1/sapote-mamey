# Manual BLASTp spot-check evidence

A manual BLASTp spot-check is optional. It gives independent homology evidence for one question you have chosen. A pending row on a worklist is not a search result, and it does not give permission to send anything out. Reuse results you already downloaded for the same queries. Any new online search follows [the BLASTp protocol](../ONLINE_BLASTP_PROTOCOL.md) and stays inside the user's request.

## What to keep for each query

- strain / full contig / region / BGC alias, and the exact locus tag;
- the submitted protein or query ID, and its sequence hash;
- the original result files, the database, the retrieval date, and the RID or other receipt;
- identity, positives and query coverage as separate numbers, with alignment length, e-value and anything missing.

A hit's title is an annotation to check. It does not show function, product identity or activity.

## Getting results into the package

Pick the reader that actually supports your files. [blastp-followup](../BLASTP_FOLLOWUP_v9.7.142.md) writes review files to the directory you select with `--outdir`. For workbook ingestion, `ingest-blastp` changes the workbook selected by `--master`; adding `--package` also enables package evidence updates. A loose TSV, or a cell edited by hand, does not update everything that reads the evidence. Work on copies before loading anything. Check the reported hit, query and BGC counts and the binding-guard status; retain an explicit hold when binding is not validated. For DIAMOND output, see [its data guide](DIAMOND_DATA_WORKFLOW.md).

## What a pending row means

`mamey/cell_provenance.py` writes a `MANUAL_BLASTP_OPTIONAL` placeholder for each BGC. It is not a live check of outside results. `blastp-followup` summarizes only the queries that have hits, so a query missing from a hit table is not a confirmed no-hit. Match the submitted list against the result receipts before claiming coverage or a negative. Keep anything unresolved as a hold; do not mark it complete.
