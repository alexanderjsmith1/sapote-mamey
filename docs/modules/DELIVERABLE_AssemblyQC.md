# DELIVERABLE/GATE — Assembly QC (deterministic, pre-lead_board)

## 0. Header block
> **Filing.** `docs/modules/DELIVERABLE_AssemblyQC.md`.
> **Extends / references:** `DELIVERABLE_CONTRACT.md` (registers as a **gate**, not just a report),
> `KNOWLEDGE_Evidence_Axes_and_Lead_Class_Logic.md` (corrected-count + lead classes it protects).
> **Precedence.** `DELIVERABLE_CONTRACT.md` wins; the active monolith wins over everything.
> **Status:** `CODE_BACKED` — `tools/assembly_qc_check.py`.
> **One-line purpose.** Flag mixed-culture / co-assembly strains and **hold their leads** before they reach the
> Lead_Board, so inflated counts and spurious couplings never enter A/B promotion.

## 1. When it is offered (gate, not optional)
Runs **early — right after intake/counts, before `lead_board.py` / `build_priority_leads.py`** — on every cohort,
especially a fresh or type-strain set. Incomplete delivery = banking leads from an unchecked cohort. The user
never has to ask: the gate runs and its `assembly_qc.json` is consumed automatically.

## 2. Inputs required
| File / field | Feeds | Required for |
|---|---|---|
| `Project_Memory_Snapshot.json` → `assembly.genome_bp`, `.contigs`, `.n50` | the size discriminator | the co-assembly FLAG |
| `…bgc_counts.raw`, `.interior_pct` | corroborating inflation | WARN / corroboration |
| `taxonomy`/genus (+ optional genus table) | genus-aware ceiling | optional sharper FLAG |
| (fallback) `bgc_data.json` | derive raw_bgcs, contigs, interior_pct | when no snapshot — genome_bp stays unknown |

**Skip-not-fake:** if `genome_bp` is absent the co-assembly FLAG **cannot** fire; raw/contig trips are reported as
WARN, never silently FLAGged (see §5).

## 3. Pipeline
```bash
python tools/assembly_qc_check.py --snapshot Project_Memory_Snapshot.json --out cohort/assembly_qc.json
# fallback (no snapshot): derives raw/contigs from banks; genome_bp unknown → WARN-only
python tools/assembly_qc_check.py --banked-dir cohort --out cohort/assembly_qc.json
# spec-exact OR-logic (only on a cohort where genome_bp isolates the offenders):
python tools/assembly_qc_check.py --snapshot snap.json --literal-or --out cohort/assembly_qc.json
```

## 4. Outputs & behavioural contract
- `assembly_qc.json` (+ `Assembly_QC` workbook sheet): `strain, genome_bp, contigs, n50, raw_bgcs, interior_pct,
  status (PASS/WARN/FLAG), reasons[]`, plus `held_qc[]` and `warn[]` lists.
- **Contract:** `build_lead_tiers.py` (and `lead_board.py` / `build_priority_leads.py`) read `held_qc` and set
  `confidence = HOLD-QC` for those strains' BGCs — never A/B — routing them to a `Held_QC` list. WARN strains
  proceed but carry `qc_note = "oversized assembly — verify purity"`. FLAG strains' raw class counts are excluded
  from cross-set / cross-strictness count comparisons. *(Wired in `build_lead_tiers.py` this cycle.)*

## 5. Gate logic — size is the discriminator (refinement vs the bare spec)
The co-assembly tell is an **oversized genome**. A fragmented single genome (POOR assembly) inflates raw BGC and
contig counts identically, so `raw_bgcs>60` / `contigs>3000` **alone cannot separate co-assembly from
fragmentation**. Default (`size-anchored`):
- `genome_bp > 14 Mb` (or `> 1.5x` genus max) → **HARD FLAG**.
- raw/contig trips **without** an oversized genome → **WARN** ("verify purity"), not FLAG.
- `genome_bp > 12 Mb` or `raw_bgcs > 45` (no hard flag) → **WARN**.

`--literal-or` applies the spec's exact `ANY of → FLAG`. **Validation:** on the SID reference cohort the
literal-OR mode FLAGs **36/59 strains (incl. the Class-A leads)** purely on fragmentation — a false-positive
cascade — while size-anchored FLAGs **0** (correct: no SID strain is a co-assembly). On a snapshot with the three
co-assembly AS strains, size-anchored FLAGs **exactly AS-XXX / AS-XXX / AS-XXX** and passes a clean 8.5 Mb strain
— meeting the spec's acceptance criterion. **Use `--literal-or` only when genome_bp is present and isolates the
offenders; otherwise the default is safer.**

## 6. Sapote-side companion rule
When a strain is QC-FLAGGED, Sapote MUST NOT issue CONFIRM verdicts for its BGCs; record anchors in the round
synthesis under "leads HELD pending assembly QC" and recommend a per-contig taxonomy / CheckM screen.

## 7. Next-paths closer
```
1. Provide a Project_Memory_Snapshot.json with assembly.genome_bp so the FLAG can fire (banks-only = WARN-only).
2. Add a genus typical-max table to enable the genus-aware 1.5x ceiling.
3. After flagging, run per-contig taxonomy / CheckM on FLAG strains to confirm co-assembly before discarding.
4. Re-bin a FLAG strain and re-run intake; the gate clears it automatically once genome_bp normalizes.
5. Exclude FLAG strains from the next cross-set count figure (their raw counts are inflated).
```
