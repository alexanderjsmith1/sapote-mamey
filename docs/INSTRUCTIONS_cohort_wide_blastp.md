# INSTRUCTIONS — cohort-wide BLASTp for the AS Hymenoptera cohort

**For:** the multi-strain cohort chat · **From:** patch chat · **Bundle:** v9.7.319 / engine 1.9.111
**Date:** 2026-07-09

Read all of §1 before you start. The short version: **do not run EBI across the whole cohort.** The
numbers below are measured, not estimated from memory, and they say EBI is both the slow transport *and*
the one that cannot answer the question we actually care about.

---

## 1 · The feasibility answer, with receipts

### Scale (measured from the real packages, not guessed)

| Quantity | Value | Source |
|---|---:|---|
| Strains in the AS cohort | 21 | `COHORT_BGC_FULL_TALLY.csv` |
| BGCs | 819 | same |
| Mean CDS per BGC | **19.3** | `<strain>_cds_table.csv`, 5 strains / 165 BGCs (10.3–34.9 range; max single BGC = 96) |
| **Proteins in all BGCs, all strains** | **≈ 15,800** | 819 × 19.3 |

### Transport comparison — this is the decision

| | EBI (`blastp-ebi`) | NCBI (`blastp-online`) |
|---|---|---|
| Jobs for 15.8k proteins | **1 job per protein → 15,809 jobs** | **10 proteins per batch → 1,581 submissions** |
| Submit-side wall clock | 26.3 h at the code's 6 s fair-use gap (8.8 h at the 2 s I used) | ~4.4 h at a courteous 10 s/submit |
| Plus polling | 1.5–3× the submit time in practice | RID polling, overlappable |
| **Databases** | uniprotkb_bacteria, uniprotkb_trembl, uniref90 — **no `nr`** | **`nr`**, refseq_protein, swissprot |
| Accepts a prepared `.faa` panel | yes (`--fasta`) | no — builds queries from the package/ZIP |

**Conclusion.** Cohort-wide EBI is ~16× more requests, 1.5–3 days of continuous throttled traffic, and it
**cannot produce nr numbers**. The `conservation_median_id` → `NOVELTY_CONTRADICTION` guard is documented
as *nr-preferred*; the whole reason BGC014 and BGC043 are still flagged "unconfirmed" is that their
novelty rests on ClusterBlast rather than nr. Running 15.8k UniProt jobs would not close a single one of
those. **Use NCBI `nr` via `blastp-online`, and scope it.**

EBI keeps exactly one job: it is the only transport that takes a **prepared FASTA panel**, so it is right
for a curated per-BGC panel when you already have the `.faa` (that is what was run for the two worked-example regions below).

### Should you do all proteins in all BGCs at all?

No — and not because of the compute. Most of those 15.8k are context genes (transporters, regulators,
housekeeping) whose 95 %+ hits tell you nothing. What the guard consumes is a **per-BGC median over the
genes in the panel**, and what a card needs is the **closest match per gene in §4**. Both are satisfied by
a curated panel (core + informative context, ~20–25 queries/BGC), which is what the panel builder emits.

**Recommended scope, in priority order:**

1. **Tier 1 — the leads.** Every BGC that carries a novelty or "strain-specific" claim in a draft card, plus
   every `lead_tier ∈ {Exceptional, Strong}` BGC. These are where a wrong novelty call does real damage.
   Rough size: ~10 % of 819 ≈ 80 BGCs × ~22 queries ≈ **1,800 proteins ≈ 180 NCBI submissions**.
2. **Tier 2 — the modular set.** The 726 modular BGCs, core genes only (~8–10/BGC) ≈ 6,500 proteins ≈
   650 submissions. Do this once the Tier-1 loop is proven.
3. **Tier 3 — exhaustive.** All 15.8k. Only with a justification, and never as the first pass.

---

## 2 · The pipeline (v9.7.239 — the overlay write path is new and load-bearing)

Until v9.7.239, **nothing wrote the file the guard reads.** `authored_verify:99` and
`genome_explore:72` both read `<package>/blastp_online/<BGC>_online_blastp.csv`; `blastp-online` wrote to
`bgc_blastp_panel/` and `ingest-blastp` wrote only the workbook's B5 sheet, which no code reads back. So
`conservation_median_id` silently fell back to ClusterBlast for every card ever verified. `ingest-blastp
--package` now mirrors the hits into the overlay. **If you skip `--package`, the guard stays disarmed.**

### Per-strain loop (NCBI / nr)

```bash
# 0. one strain, one sealed package, one BGC scope at a time
PKG=runs/<STRAIN>/package

# 1. BLASTp against nr. Batches of 10; --bgc scopes via the crosswalk.
python3 -m mamey.cli blastp-online \
    --package <antismash_zip_or_region_gbk> \
    --bgc BGC018 \
    --crosswalk "$PKG" \
    --database nr \
    --evalue 1e-5 \
    --batch-size 10 \
    --outdir "$PKG/bgc_blastp_panel"

# 2. Mirror the hits into the overlay the readers expect. --package is NOT optional.
python3 -m mamey.cli ingest-blastp \
    --master <master_workbook.xlsx> \
    --strain <STRAIN> \
    --hit-table "$PKG/bgc_blastp_panel/BGC018_online_blastp.csv" \
    --xml       "$PKG/bgc_blastp_panel/BGC018.xml" \
    --package   "$PKG"

# 3. Confirm the guard is armed (this is the check that matters)
ls "$PKG/blastp_online/BGC018_online_blastp.csv"
```

Step 2 prints `nr overlay: N gene(s) across M BGC(s) -> …/blastp_online (arms conservation_median_id /
NOVELTY_CONTRADICTION)`. **If you do not see that line, the run did nothing for the guard.**

### If you must use EBI (prepared panel, no nr)

```bash
python3 -m mamey.cli blastp-ebi --fasta <panel>.faa --state <BGC>.state.json --submit  --hits 10 --submit-gap 6
python3 -m mamey.cli blastp-ebi --fasta <panel>.faa --state <BGC>.state.json --harvest --poll-budget 600
python3 -m mamey.cli blastp-ebi --fasta <panel>.faa --state <BGC>.state.json --to-outfmt10 <BGC>_hits.csv
```

The `--state` file is genuinely resumable — it persists `jobs` **and** `results`, and `--harvest` counts
only `OK`. Re-run either phase after an interruption; it picks up where it stopped. Verified on a real
44-job run (22 + 22), both COMPLETE.

---

## 3 · Traps I hit, so you don't

1. **`setsid` loses the working directory.** A detached harvest died with `ModuleNotFoundError: No module
   named 'mamey'`. Always `setsid bash -c 'cd <bundle> && python3 -m mamey.cli …'`. This was environment,
   not data — but it silently cost a run.
2. **`--to-outfmt10` gives you no subject titles.** outfmt10 is the standard 12-column format: it carries
   the subject *accession* (`A0A7X0TWU3`) and nothing else. In my AS-XXX overlays `locus_tag`, `aa_length`,
   `pct_identity`, `query_coverage`, `evalue` were 22/22 populated, but **`blastp_top_def` and
   `blastp_organism` were 0/22**. `conservation_median_id` only needs identity + coverage, so the medians
   were sound — but a §4 gene table built from that overlay has no hit descriptions. **Pass `--xml` to
   `ingest-blastp`** (the harvested XML carries the titles). I did not do this; treat it as a known gap.
3. **Don't report EBI numbers as nr.** They are UniProt-derived. Say which database, every time.
4. **Long runs need the detached-poll pattern**: `setsid bash -c '… > /tmp/log 2>&1; echo EXIT=$? >> /tmp/log' &`
   then poll `/tmp/log`. Anything over ~4 minutes exceeds a single tool call.
5. **Check `bgc_blastp_panel/` vs `blastp_online/`.** They are different directories with different
   meanings. The first is BLASTp output; the second is the overlay the guard reads.

---

## 4 · What to do with the numbers (the science discipline)

- Identity is **similarity, not identity of function**. Always report coverage alongside it — a 59 % hit at
  53 % coverage is much weaker evidence than a 39 % hit at 72 % coverage.
- Never turn a BLASTp hit name into a product identity. KCB and BLASTp are comparators.
- Bioactivity stays **extract-level**. Nothing in a BLASTp table licenses a per-BGC phenotype claim.
- Cite every BGC by **NODE·region** (`assembly_locator`). `BGC###` is run-local and collides across
  strains — 173 unique `bgc_id` across 952 BGCs in the type-strain cohort alone.
- A high median (≥ 90 %) **contradicts** a novelty claim; the gate will now say so. A low median does not
  *prove* novelty — it licenses "divergent, worth testing," nothing stronger.

### Worked example (real, from the v9.7.239 run)

Two class-I lanthipeptide regions from one cohort strain, 22 curated queries each,
`uniprotkb_bacteria` (v9.7.372: strain/BGC ids and contig locators withheld from the public code
tier; the numbers are the real run's):

| Region | Locator | median %id | min | genes < 60 % | Guard |
|---|---|---:|---:|---:|---|
| Region A | *(withheld)* | **95.8** | 92.4 | 0 | **NOVELTY_CONTRADICTION fires** |
| Region B | *(withheld)* | **73.1** | 30.4 | 3 | allows |

BGC005 is genus-conserved; a novelty claim there is contradicted by the data. BGC018 carries three
sub-60 % genes (`ctg2_435` 30.4 % @ 81.5 % cov; `ctg2_449` 39.0 % @ 71.9 %; `ctg2_437` 59.3 % @ 53.0 %) on
an otherwise conserved backbone — that reads as a tailoring/maturation difference worth testing, **not** a
novel scaffold. Both still need an nr pass before novelty language enters a card.

---

## 5 · Record-keeping (required)

Per `docs/audit_recordkeeping/SAPOTE_AUDIT_RECORDKEEPING_PROTOCOL.md`, every BLASTp round writes a run
ledger row: which instruction governed it, the command, the input file, the output file, and what passed /
failed / stayed ambiguous. `tools/round_ledger.py` appends the per-card row. Do not report a strain as
"BLASTp done" without the overlay file existing on disk — that is the artifact, not the log line.

**Definition of done for one BGC:** `<package>/blastp_online/<BGC>_online_blastp.csv` exists, has one row
per panel gene, `pct_identity` + `query_coverage` populated, and the database is named in the run record.

---

## 6 · Summary of what I'd actually run

1. Build the Tier-1 lead list from `COHORT_BGC_FULL_TALLY.csv` (`lead_tier` ∈ Exceptional/Strong, plus any
   BGC whose draft card claims novelty). Expect ~80 BGCs.
2. For each: `blastp-online --database nr --batch-size 10` → `ingest-blastp --package --xml` → confirm the
   overlay file exists.
3. Re-run `verify-modeb --strict` on the affected cards. Any `NOVELTY_CONTRADICTION` that now fires is a
   card that was making an unsupported claim against ClusterBlast data.
4. **Two named leads on the private lead board are waiting on exactly this.** Do them first.
5. Only then consider Tier 2. Skip Tier 3 unless something specific demands it.
