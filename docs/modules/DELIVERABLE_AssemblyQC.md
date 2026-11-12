# DELIVERABLE/GATE — Assembly QC (deterministic, pre-lead_board)

## 0. Who runs it and when
You run `tools/assembly_qc_check.py` by hand on a cohort, after intake and before lead ranking. The engine does
not launch it. Its size/count thresholds flag records for review before A/B promotion. A flag does not establish mixed culture or co-assembly. Lead classes and the corrected count it protects are in
[evidence axes and lead classes](KNOWLEDGE_Evidence_Axes_and_Lead_Class_Logic.md). The current user task and
[assistant governance](../ASSISTANT_GOVERNANCE.md) govern actions.

## 1. When to run it (recommended manual step)
Run it **early — right after intake/counts, before `lead_board.py` / `build_priority_leads.py`** — on each cohort,
especially a fresh or type-strain set. The bank fallback evaluates strains that have BGC rows. A `strains.json`
member with no BGC rows gets status `NOT_CHECKED` and is listed in `not_checked`; it is not a pass. Compare
the output roster with the cohort you meant to check. Incomplete delivery = banking leads from an unchecked cohort. The module recommends this ordering; the tool is operator-invoked (`tools/gate_registry.tsv`: OPERATOR_ONLY), not automatically launched by the engine. Bind the actual emitted receipt before using its hold list.

## 2. Inputs required
| File / field | Feeds | Required for |
|---|---|---|
| `Project_Memory_Snapshot.json` → `assembly.genome_bp`, `.contigs`, `.n50` | the size discriminator | the co-assembly FLAG |
| `…bgc_counts.raw`, `.interior_pct` | corroborating inflation | WARN / corroboration |
| `taxonomy`/genus (+ optional genus table) | genus-aware ceiling | optional sharper FLAG |
| (fallback) `bgc_data.json` | derive BGC-row counts, distinct recorded contig values and interior fraction; not the whole-assembly contig census | when no snapshot — genome_bp stays unknown |

**Default size-anchored mode:** absent `genome_bp` cannot produce an oversized-genome FLAG. Raw-count trips and the joint contig/interior condition produce WARN. `--literal-or` can FLAG those conditions even without genome size; do not confuse its logic with the default.

`--snapshot` takes a cohort snapshot or one package's own record. A cohort snapshot is a mapping of strain IDs to records, or a list of records with `strain` or `strain_id`. One package record is a flat record with an `assembly` or `bgc_counts` root, read as one strain under its `strain_id`. Each record carries `assembly`, `bgc_counts` and optional `taxonomy`/`genus`. Some malformed top-level shapes and non-record entries are refused with `ASSEMBLY_QC_SNAPSHOT_SHAPE`, but this reader does not establish identity, roster or measurement completeness. A dict containing only dict values can be interpreted as a cohort even when its keys were intended as fields; incomplete rows can reach `PASS`. Verify the exact IDs, schema and required measurements independently, and hold missing measurements as unchecked even if a row says PASS.

## 3. Pipeline
```bash
python tools/assembly_qc_check.py --snapshot Project_Memory_Snapshot.json --out cohort/assembly_qc.json
# fallback: BGC-row-scoped counts, no genome size flag by default; literal-or can flag count conditions
python tools/assembly_qc_check.py --banked-dir cohort --out cohort/assembly_qc.json
# spec-exact OR-logic (only on a cohort where genome_bp isolates the offenders):
python tools/assembly_qc_check.py --snapshot snap.json --literal-or --out cohort/assembly_qc.json
```

`--out` must be a new path. An existing file is refused unless `--replace` is given, and then only a regular
file is replaced. `--out` is never allowed to be an input (the snapshot, `bgc_data.json`, `strains.json` or the
genus table), even with `--replace`. A strain listed twice in the snapshot or in `strains.json` is refused.
Refusals print `REFUSED` and exit 2 before any file is written.

## 4. Outputs & behavioural contract
- `assembly_qc.json` (this writer does not create an `Assembly_QC` workbook sheet): `strain, genome_bp, contigs, n50, raw_bgcs, interior_pct,
  status (PASS/WARN/FLAG/NOT_CHECKED), reasons[]`, plus `held_qc[]`, `warn[]` and `not_checked[]` lists.
  A `NOT_CHECKED` row keeps its measurements blank (`null`), never 0. `held_qc` holds FLAG strains only.
- **Implemented consumer:** `tools/build_lead_tiers.py` reads `assembly_qc.json` under its
  `--banked-dir` and emits HOLD-QC rows for held strains. A missing receipt does not force a hold;
  an existing unreadable receipt fails closed. `lead_board.py` and `build_priority_leads.py` do not
  consume this receipt, so their runs do not inherit the hold automatically. WARN propagation and
  automatic exclusion from count comparisons described in earlier versions are workflow proposals,
  not implemented guarantees. QC thresholds are flags for review, not proof of culture composition.

## 5. Gate logic — size is the discriminator (refinement vs the bare spec)
An oversized assembly is a review signal with alternative explanations, not proof of culture composition. Raw BGC and contig counts can also be high in fragmented assemblies; these thresholds alone do not distinguish those explanations. Default (`size-anchored`):
- `genome_bp > 14 Mb` (or `> 1.5x` genus max) → **HARD FLAG**.
- raw-count trips or (`contigs > 3000` **and** `interior_pct < 10`) **without** an oversized genome → **WARN** ("verify purity"), not FLAG.
- `genome_bp > 12 Mb` or `raw_bgcs > 45` (no hard flag) → **WARN**.

`--literal-or` applies the spec's exact `ANY of → FLAG`. Size-anchored is the default because raw-count and
contig trips also fire on a fragmented single genome, so under `--literal-or` a cohort of draft assemblies can be
flagged on fragmentation alone. **Use `--literal-or` only when genome_bp is present and isolates the offenders.**

## 6. Sapote-side companion rule
When a strain is QC-FLAGGED, do not issue CONFIRM verdicts for its BGCs; record anchors in the round
synthesis under "leads HELD pending assembly QC" and recommend a per-contig taxonomy / CheckM screen.

## 7. Follow-up
1. Bind measured `assembly.genome_bp` in the snapshot for the default size-anchored flag; banks-only input cannot trigger that size flag, while `--literal-or` can flag its count conditions.
2. Add a genus typical-max table to enable the genus-aware 1.5x ceiling.
3. Investigate flags with source-bound assembly, taxonomy and contamination evidence as appropriate. These checks inform review; they do not alone confirm co-assembly or authorize discarding a strain.
4. If the owner authorizes a revised assembly or re-binning, retain both source bindings, rerun intake/QC and inspect the fresh receipt before considering a hold cleared.
5. Document comparison sensitivity and any exclusion decision; a FLAG alone does not prove counts inflated. Preserve the included/excluded roster and denominators.
