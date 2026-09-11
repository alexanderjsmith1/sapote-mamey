# Prevalence workflow — where it sits

Post-seal, cohort-wide, read-only. It consumes the frozen tool databases (`antismash_gene_census`,
`antismash_gbk_domains`, optional `blastp_*` and `mamey_*_keywords`) and produces review surfaces, never
altering a sealed package. Run order in a cohort analysis chain:

1. seal the engine cut (owner) → 2. build/refresh the tool databases (source-verified, hash-bound) →
3. `tools/domain_prevalence.py` (+ `--widget`) → 4. `tools/scan_prevalence.py` per keyword dataset →
5. review the widgets; a rare + evidenced + host-specific family is a review candidate, not a result.

Wiring notes for the composer: these are new `tools/` scripts + one `tests/` file; re-run
`tools/gen_tools_inventory.py` after they land so the tool inventory covers them. No `mamey run` change —
they are downstream analysis, not part of the deterministic extraction pipeline, so cross-strain
comparability is unaffected. The host TSV and per-strain owner rulings (`--exclude`, `--host-override`)
are arguments, never hardcoded, so the cohort scope is auditable.
