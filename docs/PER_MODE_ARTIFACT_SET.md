# Per-mode artifact set (historical: smoke / standard / gold)

*v9.7.319 — documents 9.7.88-deep: which artifacts each run mode produced at that point in the
engine's history, so an absent file was recognized as intended mode-gating rather than a
regression.*

> **v9.7.374 correction — this contract is now moot, not just outdated.** `--mode smoke` was
> **removed at v9.7.161**, and `--mode standard` has been a **deprecated alias of `gold`** since
> v9.7.92 (`cli.py:3042-3045` rewrites `args.mode` from `"standard"` to `"gold"` before the run
> context is built, so both mode values reach the gold analysis path; identical bytes still depend on inputs, options and provenance).
> `mamey run --mode` now accepts only `{standard, gold}` (`cli.py:4243-4244`) and both select
> gold depth; optional outputs and failed enrichment phases can differ — there is no longer any way to get a leaner package by choosing a
> different `--mode` value. **Gold is the only analysis mode.** The three-way table below is kept
> for historical/provenance reference only (it was accurate as of v9.7.88-9.7.91, before the .92
> and .161 retirements) — do not use it to predict what a current package will or won't contain.

## Expected output inventory (inspect actual phase results)
- `manifest.json`, `manifest_short.json`
- `<strain>_1_intake.json`, `<strain>_2_inventory.csv`, `<strain>_4_triage_board.csv`
- `<strain>_4A_RGGMCI_ranked_pairs.csv`, `<strain>_RGGMCI_evidence.csv`
- `gate_validation.json`, `gold_mode_receipt.json`, `checksums_sha256.txt`
- `run_phase_receipts.jsonl`, `<strain>_timing_breakdown.{json,csv,md}`
- `bgc_data.json` (single-strain bank)
- **`<strain>_gene_context.jsonl` + `<strain>_cds_table.csv`** (v9.7.88 — the normalized gene
  context; produced on every run because the CDS/domain objects are in hand at run time)
- `<strain>_gene_by_gene_top_leads.csv` (real CDS rows from the gene context)
- **`deep_data.json` + `gene_data.json`** — the gene-level deep-dive scaffold and per-gene data for
  `build_modeb_deepdive`. Historically gold-only; now produced on every run because gold is the
  only mode (`cli.py:661` still gates this on `mode == "gold"` internally, but that condition is
  now always true — see the correction note above).
- in-run brief figures (`--brief standard`) — supplementary, opt-in via `--brief`, independent of
  `--mode`
- the Complete Package ZIP

## Historical per-mode table (v9.7.88-era engine; retired v9.7.92/v9.7.161 — reference only)
| Artifact | smoke | standard | gold | Notes |
|---|:---:|:---:|:---:|---|
| `deep_data.json` | — | — | ✓ | was gene-level deep-dive scaffold; **gold only** at the time |
| `gene_data.json` | — | — | ✓ | was per-gene data for `build_modeb_deepdive`; **gold only** at the time |
| in-run brief figures (`--brief standard`) | opt-in | ✓ | ✓ | post-seal in v9.7.88 (Finding L); supplementary |
| Mode B cards (`mamey mode-b`) | on demand | on demand | on demand | gene table from gene_context (v9.7.88) |

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

The list above is an inventory of expected/possible outputs, not a universal presence guarantee. `deep_data.json`/`gene_data.json` emission is enrichment and catches errors without failing the package (`mamey/cli.py:870–897`). Gene-context writing records `ERROR` on exception (`:1598–1609`); the BGC bank records a failed phase (`:712–783`). A valid package or normal exit therefore does not certify every named enrichment file. Check actual artifact presence/bytes and each consumer's required input before downstream use.

For the deep-data pair, inspect the selected snapshot/evidence inputs as well as the output files. Missing or unreadable input JSON can become empty arrays without raising the enrichment warning, and the CLI does not retain the builder's returned counts. A file's presence, an empty array or a quiet issue log therefore does not establish a complete extraction. Compare the `bgc_profile` identities with the bound BGC inventory and retain unavailable coverage explicitly. The two files are replaced individually, in sequence; a failure between replacements can leave different generations. Confirm that both belong to the same extraction before downstream use (`mamey/deep_data.py:123–166`; `mamey/cli.py:888–897`).

`--brief`, `--locus-maps`, JSON evidence, workbook requirements and optional reference completion change outputs independently of gold mode. Capped mode forces brief none, JSON evidence off, workbook required and automatic locus maps off (`mamey/cli.py:4240–4248`); explicit optional work and environment capabilities still matter. In-run brief/render failures can be nonblocking (`:471–555`); generated prose scaffolds are not finished reports or cards.

Preserve `manifest.json`, phase receipts, issue log, validator results, checksum scope and actual file inventory together. A validator's `MAMEY_COMPLETE` means extraction-complete/judgment-pending after scoped gates, and `PASS` does not establish scientific acceptance (`mamey/validate.py:1003–1045`). Default validation can rewrite the mutable status receipt (`:1085–1106`). See [the deliverable contract](DELIVERABLE_CONTRACT.md) and [standalone output/status review](standalone/MAMEY_STANDALONE_CHATGPT_README.md).

Historical tables/line references above remain provenance, not an executable current output schema. Cohort GCF rows require their database/reference/identity bindings and are separate from a per-strain extraction. Retain actual extraction and renderer receipts for the selected run.

For named deliverable discovery versus actual artifact presence, see [artifact maps and menu limits](ARTIFACT_MAP_LIMITS.md). The generated menu is a catalog, not this package's file inventory.
