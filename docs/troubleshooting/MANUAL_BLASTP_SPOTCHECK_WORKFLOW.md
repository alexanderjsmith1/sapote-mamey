# Manual BLASTp spot-check evidence

A manual spot-check is optional independent homology evidence for a selected question. A pending worklist is not a search result and does not authorize outbound submission. Reuse already-downloaded, query-bound results where available; remote work follows [the current BLASTp protocol](../ONLINE_BLASTP_PROTOCOL.md) and the user's scope.

Preserve strain / full contig / region / BGC alias, exact locus tag, submitted protein/query identifier and sequence hash, original result files, database/channel, retrieval date and source/RID receipt. Carry identity, positives and query coverage separately with alignment length, e-value and missingness. A hit title is an annotation to assess, not demonstrated function, product identity or activity.

Choose the actual supported reader and destination. [blastp-followup](../BLASTP_FOLLOWUP_v9.7.142.md) writes review side artifacts; workbook/package ingestion has different required flags and writes. Neither an arbitrary local TSV nor a manually edited workbook cell automatically updates every evidence consumer. Preserve working copies before ingestion and inspect admission/quarantine/binding counts. For DIAMOND-shaped output see [its data guide](DIAMOND_DATA_WORKFLOW.md).

The extraction provenance writer emits `MANUAL_BLASTP_OPTIONAL` placeholders per BGC (`mamey/cell_provenance.py:149–154`); that label is not a live completeness check of external results. Absence from a hit-only table is not completed no-hit evidence. Reconcile the submitted roster and result receipts before claiming coverage or a negative. `blastp-followup` summarizes observed-hit queries only (`mamey/blastp_followup.py:459–497`).

This source review performed no searches. Retain unresolved evidence as a hold rather than manufacturing completed status.
