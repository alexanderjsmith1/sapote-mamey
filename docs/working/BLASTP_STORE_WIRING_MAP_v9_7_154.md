# BLASTP evidence-store wiring map — PATCH-005 parts 2 & 3

**Status:** investigation + scoped plan. **Not implemented in v9.7.154.** This documents what
already exists, what is missing, and the exact insertion points, so the feature can be cut
deliberately with the path/schema forks surfaced rather than picked silently.

**Author:** Patch Chat (Claude), hostile-auditor pass on v9.7.153 → v9.7.154.

---

## TL;DR

`mamey/blastp_evidence_store.py` is **already written, complete, and unit-tested** (4 tests in
`tests/test_blastp_evidence_store_v97142.py`). It does the durable per-strain, per-round,
per-gene storage PATCH-005 asks for. What's missing is **two thin seams**: (1) a CLI subcommand
so a user can call it, and (2) a read in `modeb_template_emitter` so emitted §8 carries the
BLASTP evidence automatically. The "build a new ingest step from scratch" framing in the patch
list overstates the work — the engine is done; this is wiring.

---

## What exists today (observed, in the v9.7.153 artifact)

`mamey/blastp_evidence_store.py` (296 lines). Public surface:

- `ingest_blastp_round(store_dir, *, strain, round_id, hit_table_csv, xml2=None, fasta=None,
  purpose=..., operator_note=..., allow_update=False) -> dict`
  - Copies raw NCBI files with SHA256 checksums into `raw_ncbi_downloads/<round_id>/`.
  - Parses via `blastp_followup.parse_hit_table_csv` + `merge_hit_xml(parse_xml2(...))`
    — **so it inherits the PATCH-001 fix automatically** once both ship in the same cut.
  - Writes per-round tables to `parsed_rounds/<round_id>/`:
    `BLASTP_all_hits_top10.csv`, `BLASTP_top_hits_by_query.csv`, `BLASTP_BGC_summary.csv`.
  - Appends a `BLASTP_round_manifest.jsonl` row; rebuilds `cumulative/` tables across all rounds.
  - **Idempotent / additive by round_id**: re-ingesting a known round raises unless
    `allow_update=True`; multiple distinct rounds for the same BGC accumulate rather than
    overwrite — exactly the "core + 2 flank batches merge" behaviour PATCH-005 wants.
- `rebuild_cumulative_tables(store_dir)` — re-derives cumulative tables from `parsed_rounds/`.
- `evidence_tier(record)` / `next_action(record)` — per-hit A/B/C/D tiering + recommended action.
- `summarize_bgc_rows(top_rows)` — BGC-level rollup (claim level, tier counts, best identity).

Output schema already keys per-gene:

```
HIT_FIELDS = [round_id, strain, bgc_id, query_gene, node, region, query_id,
              subject_id, subject_accession, subject_title, subject_sciname, subject_taxid,
              pct_identity, pct_positive, align_len, query_len, query_coverage,
              evalue, bitscore, evidence_tier, next_action, claim_safety]
```

`query_gene` + `bgc_id` + `node` are present on every row → a per-`locus_tag` join key already
exists. **No schema invention is required to key BLASTP evidence to genes.**

## What is missing (computed — grep across the bundle)

1. **No CLI subcommand.** `grep ingest_blastp_round / blastp_evidence_store mamey/cli.py` → no
   hits. The module is import-only; a user cannot invoke it. `mamey blastp-followup` exists and
   wraps the *side-artifact* path (`blastp_followup.command`), but nothing wraps the *durable
   store*.
2. **No template consumer.** `modeb_template_emitter._bgc_facts()` reads `manifest_short.json`,
   `manifest.json`, and the triage board. It does **not** read any BLASTP store. So §8
   (`_section_body(8, ...)`) seeds only `kcb_top`/`kcb_score` from the triage row — never the
   BLASTP-confirmed nearest match. Every BGC's BLASTP evidence is therefore hand-reassembled into
   the card, which is the exact loop PATCH-005 is trying to close.

---

## The two seams to add

### Seam A — CLI subcommand `mamey ingest-blastp`

Thin wrapper, mirrors the existing `blastp-followup` registration in `mamey/cli.py` (~line 3158).

```
mamey ingest-blastp --package <pkg> --bgc <BGC_ID> --round <round_id>
                    --hit-table <csv> [--xml2 <xml>] [--fasta <faa>]
                    [--store-dir <dir>] [--allow-update] [--note "<text>"]
```

Implementation: resolve `strain` from the package (`manifest_short.json:strain_id` — already how
`modeb_template_emitter` does it), default `--store-dir` to `<pkg>/blastp_evidence_store/`, then
call `ingest_blastp_round(...)`. ~25 lines + an `add_parser` block. **No new engine code.**

**Fork A1 — store location.** `<pkg>/blastp_evidence_store/` (travels with the sealed package,
visible to the template reader in Seam B) vs. a strain-level store outside the package (survives
re-seals, but the template reader must then be told where to look). Recommend in-package for the
template-read path; surface as a choice.

**Fork A2 — `--bgc`/`--round` provenance.** `ingest_blastp_round` keys by `round_id` and derives
`bgc_id` per row from the query header (now PATCH-001-correct). A `--bgc` flag is therefore
optional metadata, not a key. Decide whether to (a) require it and assert every parsed row's
`bgc_id` matches (a useful guard against pasting the wrong hit table), or (b) leave it free-form.
Recommend (a) — it's a cheap hallucination-trap consistent with the evidence-conservation rules.

### Seam B — `modeb_template_emitter` reads the store for §8 (and §4/§28)

Add a `_blastp_facts(pkg, bgc_id)` reader alongside `_bgc_facts`, then thread its output into
`_section_body` for §8. Minimal, additive, never-raises (same contract as `_bgc_facts`):

```python
def _blastp_facts(pkg: Path, bgc_id: str) -> dict:
    """Per-gene nearest-BLASTP-match rollup for one BGC, from the in-package
    evidence store. Returns {} if no store / no rows for this BGC."""
    store = pkg / "blastp_evidence_store" / "cumulative" / "BLASTP_top_hits_by_query_all_rounds.csv"
    if not store.exists():
        return {}
    rows = [r for r in _read_csv(store) if (r.get("bgc_id") or "").strip() == bgc_id]
    # group by query_gene -> nearest hit (title, accession, identity raw/pct, coverage)
    ...
```

Then in `_section_body(8, ...)`: when `facts.get("blastp_rows")` is present, append a
"BLASTP-confirmed nearest matches" table (one row per `locus_tag`:
`nearest match | accession | identity N/L (P%) | positives N/L (P%) | coverage`), seeded from the
store. Keep the existing KCB block above it; BLASTP is a **second, independent** evidence line,
not a KCB replacement — preserve the claim-safe framing ("similarity, not identity").

**Fork B1 — §8 vs §4 vs §28 placement.** PATCH-005 names §4/§8/§28. §8 (comparator/KCB) is the
natural home for "nearest BLASTP match". §28 (evidence provenance ledger) should get one ledger
row per BLASTP round (observed: round_id, file SHA256, query_count) so the provenance is auditable.
§4 placement depends on what §4 is in the current contract — **needs the contract doc check before
wiring** (don't assume §4 = gene table without confirming).

**Fork B2 — raw counts source.** PATCH-005 part 1 (raw `top_identical_count`/`top_positive_count`)
shipped in v9.7.154 in `blastp_followup.summarize_results`. The **store's** `HIT_FIELDS` does not
yet carry those columns — `_hit_to_row` would need the same two derived fields added for the
template table to show raw counts directly from the store rather than recomputing. One-line-each
addition to `_hit_to_row` + `HIT_FIELDS`; flagged so it lands with the rest, not after.

---

## Test plan (when cut)

1. `test_ingest_blastp_cli_writes_store` — run the subcommand against a fixture package + a real
   multi-query space-delimited hit table; assert store dirs/manifest/cumulative tables exist and
   `bgc_id`/`query_gene` populated for every row (regression-couples to PATCH-001).
2. `test_ingest_blastp_round_id_idempotent_additive` — two distinct rounds for one BGC accumulate;
   re-ingesting a round without `--allow-update` errors.
3. `test_modeb_template_pulls_blastp_section8` — after ingest, `emit_card_template` §8 contains the
   nearest-match table with raw counts; with no store, §8 is unchanged (KCB-only) and does not raise.
4. `test_bgc_mismatch_guard` (if Fork A2(a) chosen) — hit table whose rows' `bgc_id` ≠ `--bgc` is
   rejected.

## Effort estimate

- Seam A: ~30 lines (`cli.py` wrapper + `add_parser`). No engine change.
- Seam B: ~40 lines (`_blastp_facts` reader + §8 table block + 2 store-schema fields).
- Tests: 4 new.
- **Total: a small, self-contained feature cut (v9.7.155-class), gated on Forks A1/A2/B1/B2.**

The patch list's "one-time pipeline change that pays for itself by BGC #2" is accurate; the cost
is lower than stated because the durable engine already exists.
