# What a gold run writes

Gold is the only analysis mode. `--mode standard` is an alias that becomes `gold` before the run starts; `--mode smoke` was removed. The list below is what a gold run can write. Check the package's phase receipts for what it actually wrote.

## Expected output inventory (inspect actual phase results)
- `manifest.json`, `manifest_short.json`
- `<strain>_1_intake.json`, `<strain>_2_inventory.csv`, `<strain>_4_triage_board.csv`
- `<strain>_4A_RGGMCI_ranked_pairs.csv`, `<strain>_RGGMCI_evidence.csv`
- `gate_validation.json`, `gold_mode_receipt.json`, `checksums_sha256.txt`
- `run_phase_receipts.jsonl`, `<strain>_timing_breakdown.{json,csv,md}`
- `bgc_data.json` (single-strain bank)
- **`<strain>_gene_context.jsonl` + `<strain>_cds_table.csv`** (the normalized gene
  context; produced on every run because the CDS/domain objects are in hand at run time)
- `<strain>_gene_by_gene_top_leads.csv` (real CDS rows from the gene context)
- **`deep_data.json` + `gene_data.json`** — gene-level scaffold/data inputs for
  `build_modeb_deepdive`. The CLI normalizes standard to gold, and `_emit_deep_data`
  attempts this gold enrichment; its exceptions remain nonblocking. Either file can be missing; neither is an authored card.
- in-run brief figures (`--brief standard`) — supplementary, opt-in via `--brief`, independent of
  `--mode`
- the Complete Package ZIP

The retired three-mode table is in [history](history/PER_MODE_ARTIFACT_TABLE_v9788.md).

## Cohort cross-strain layer (separate from run modes)
Cross-strain GCF analysis is a separate cohort layer run *after* several strains are banked, not
gated by run mode. Its artifacts come from the BiG-SCAPE tools rather than a Mamey run:
`cross_strain_GCFs.tsv` (family membership on `strain:node.region`), `known_vs_novel_GCFs.tsv`
(KNOWN/NOVEL vs MIBiG — only meaningful on a MIBiG-anchored DB), per-family domain TSVs +
relabelled Newick trees, and the §8 GCF-context injected into Mode B cards by
`tools/bigscape_ingest_to_mamey.py`. See `docs/SOPs/SOP-17_CrossStrain_GCF_Cohort.md`.

## Checking what a package should contain
A package's mode is recorded in `gold_mode_receipt.json` (`mode` field) and the manifest — on a
current engine this will always read `"gold"` (a literal `"standard"` value never reaches the
receipt; it is rewritten before the run context is built). If a listed artifact is absent, inspect phase receipts, selected options, issue log and validation findings. Missing optional outputs and failed mandatory outputs require different dispositions; neither should be silently represented as present.

## Current failure and option boundaries

The list above is an inventory of expected/possible outputs, not a universal presence guarantee. `deep_data.json`/`gene_data.json` emission is enrichment and catches errors without failing the package. Gene-context writing records ERROR on exception; the BGC bank records a failed phase. A valid package or normal exit therefore does not certify every named enrichment file. Check actual artifact presence/bytes and each consumer’s required input before downstream use.

For the deep-data pair, inspect snapshot/evidence inputs and the embedded `bgc_identity_contract`, not just file presence. Missing or unreadable JSON can become empty arrays without raising an enrichment exception. The builder returns counts and an identity receipt; the current CLI surfaces an identity HOLD but does not persist the returned count summary. Profiles may retain `HOLD_IDENTITY_CONTEXT_UNAVAILABLE` when the identity context cannot be admitted. A file, an empty array or a quiet issue log does not show that extraction was complete or tied to the exact locus. Compare profiles against the bound inventory and preserve unavailable/held coverage. The two final files are replaced individually in sequence, so a failure between replacements can leave different generations.

`--brief`, `--locus-maps`, JSON evidence, workbook requirements and optional reference completion change outputs independently of gold mode. Capped-session configuration forces brief none, JSON evidence off and workbook required; it changes locus maps from auto to off while preserving an explicit selection. This profile is not itself an enforced wall-clock deadline. Explicit optional work and environment capabilities still matter; generated scaffolds are not finished reports or cards.

Preserve `manifest.json`, phase receipts, issue log, validator results, checksum scope and actual file inventory together. A validator’s MAMEY_COMPLETE status separates extraction handoff from judgment; later integrity findings can still force FAIL, and a mechanical PASS is not scientific acceptance. Default validation attempts to rewrite its mutable status receipt; a caught write failure is recorded separately as `package_status_receipt_write.state=FAILED`, so inspect that result rather than assume the on-disk receipt was refreshed. See [the deliverable contract](DELIVERABLE_CONTRACT.md) and [standalone output/status review](standalone/MAMEY_STANDALONE_CHATGPT_README.md).

Cohort GCF rows require their database/reference/identity bindings and are separate from a per-strain extraction. Retain actual extraction and renderer receipts for the selected run.

For named deliverable discovery versus actual artifact presence, see [artifact maps and menu limits](ARTIFACT_MAP_LIMITS.md). The generated menu is a catalog, not this package's file inventory.
