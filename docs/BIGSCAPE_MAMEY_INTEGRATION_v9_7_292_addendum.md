# BiG-SCAPE↔Mamey integration — v9.7.319 addendum (join fix)

> **HISTORICAL ADDENDUM.** Retained for join-bug provenance. It is not an active LLM runbook.
> Current preparation, execution, exact-run selection, claims, mutation boundaries, and handoff are
> governed by `docs/LLM_COMPANION_TOOL_PROTOCOL.md` and `docs/BIGSCAPE_GCF_WORKFLOW.md`.


The v9.7.319 tool computed GCF context correctly from the DB but joined 0 cards on a real
package. The bridge (triage board → BGC# → node.region) was the failure, for three reasons:
wrong locator column (`Assembly_Locator` display form), no `strain` column on a single-strain
board, and lossy coverage formatting in `Contig`. v9.7.319 fixes all three in `load_triage()`
+ a new cov-free `canon_locator()`, and adds a `--from-tsv` path for the portable export.

## The join key, restated
Canonical join key is `strain:NODE_<n>_length_<L>.region<NN>` — **coverage-free**. A contig is
identified by node number + length; coverage is not identity and is formatted lossily by the
triage board, so it is stripped on both sides before comparison.

## Two source modes
- `--db anchored.db` — full context including cohort co-members (needs the SQLite DB).
- `--from-tsv AS_per_BGC_annotation.tsv --strain <ID>` — no DB; KNOWN/NOVEL + MIBiG anchors +
  nearest distance per BGC. Co-members are unavailable (no per-BGC `family_id` in the export);
  the injected block states this explicitly.
