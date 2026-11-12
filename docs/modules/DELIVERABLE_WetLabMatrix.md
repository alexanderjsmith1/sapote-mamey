# Wet-lab decision matrix

`tools/build_wetlab_matrix.py` scores each biosynthetic gene cluster (BGC) in a package and ranks it for wet-lab follow-up. It writes a CSV and attempts an XLSX when its dependency is available; inspect each output status. It reads only `manifest.json` from the package. The scores are a sorting aid. They do not say what a cluster makes.

For terms such as BGC, package and KCB, see the [glossary](../GLOSSARY.md). The class framework behind the Arch A to C grades is in the [class framework](../DAPR_CLASS_FRAMEWORK.md).

## Run it

You need a package that passed `validate`. See the [first-run recipe](../reader/01_FIRST_RUN.md). From the bundle root:

```bash
python tools/build_wetlab_matrix.py --package-dir runs/EXAMPLE/package --out-dir reviews/EXAMPLE-wetlab
```

The command makes the output folder if it is missing. It overwrites files of the same name, so use a fresh folder.

You should see three lines:

```text
EXAMPLE: 12 BGCs scored -> reviews/EXAMPLE-wetlab/EXAMPLE_WetLab_Decision_Matrix.csv
  categories: {'Strong follow-up': 2, ...}
  xlsx: reviews/EXAMPLE-wetlab/EXAMPLE_WetLab_Decision_Matrix.xlsx
```

The count and categories are your own. If the third line starts with `(xlsx skipped: openpyxl is not installed`, the CSV is still good; the XLSX needs `openpyxl`. If it starts with `(xlsx FAILED: <type>: <message>`, the XLSX build or write failed after the CSV was written. Any earlier `.xlsx` at that path was not replaced and may be stale; do not assume it matches the new CSV, and the tool exits 1. If the tool exits with `manifest.json not found in package dir`, check `--package-dir`.

The XLSX is a separate file with one sheet named `WetLab_Decision_Matrix`. The package workbook has a sheet with the same name. That sheet is a simpler view (primary axis, priority score, lead tier) and is not this matrix.

## What the tool reads

All inputs come from `manifest.json`:

| Field | Used for |
|---|---|
| `bgcs[].edge_status` | Interior bonus, truncation penalty, sequencing priority |
| `bgcs[].architecture_confidence` | Arch A, B or C terms |
| `bgcs[].kcb_similarity_pct`, `bgcs[].kcb_evidence_state` | KCB terms and the dereplication priority |
| `bgcs[].riq_score` | RiQ terms, when present |
| `bgcs[].length_kb` (or `start` and `end`) | Tiny-fragment penalty |
| `source_scans.blda_tta.per_bgc[].bldA_tier` | bldA gating term and activation priority |

The tool does not read `manifest.json → bgc_counts.assembly_tier`, the triage board or the RG-GMCI pair table. It also ignores strain bioactivity.

## How the score is built

KCB means KnownClusterBlast, the antiSMASH comparison to known MIBiG clusters. RiQ is a novelty score from the engine. bldA is a regulator whose rare TTA codons can gate gene expression.

| Term | Points |
|---|---:|
| Interior cluster | +3 |
| Architecture A / B / C | +3 / +2 / +1 |
| KCB similarity in the high band (70% or more) | +3 |
| No KCB anchor observed, with Arch A | +4 |
| No KCB anchor observed, with Arch B | +2 |
| RiQ below 0.50 | +3 |
| RiQ 0.50 to 0.85 | +2 |
| bldA tier T3 or T4 | +2 |
| Edge or full-contig truncation | -2 |
| Under 5 kb, not interior, no KCB anchor observed | -3 |

Each row of the CSV lists the terms that applied and the field each came from, in `score_breakdown`. The listed unavailable terms are named in `skip_notes`; check all required inputs and statuses independently: `RiQ: not computed`, `induction: not per-BGC`, `LMPKS: not run`. LMPKS is a rescue grading for fragmented polyketide clusters. The tool never applies it.

The KCB terms read antiSMASH's KnownClusterBlast percent similarity through the engine's bands in `mamey/precision.py` (high from `KCB_PCT_HIGH` = 70, moderate from `KCB_PCT_MODERATE` = 40). They do not read the cumulative BLAST score, which grows with cluster size.

The writer treats `UNKNOWN_KCB` as missing first. Otherwise it uses a valid percent; only when percent is unavailable does it fall back to the state `KNOWNCLUSTERBLAST_NO_HITS_UNVALIDATED` for a no-hit band. A valid zero percent gives the none band. These precedence rules can yield a percent band even alongside a conflicting no-hit label; inspect the original input, state and percent together. That state means the region's KnownClusterBlast text file was recognized as a no-hit report ("no hits" text, or empty "Significant hits:" and "Details:" sections) and no hit row was parsed; the text is not checked against the JSON. A missing or unreadable KCB file is not this state. That state is not evidence of novelty. With no applicable no-hit fallback, a blank, non-numeric or out-of-range percent is missing. `UNKNOWN_KCB` always takes that missing path. No KCB term then fires and `skip_notes` says `KCB percent: missing`. Conflicting or unavailable evidence remains a hold, not a novelty result.

## Decision categories

| Score | Category |
|---:|---|
| 10 or more | Immediate follow-up |
| 7 to 9 | Strong follow-up |
| 4 to 6 | Conditional follow-up |
| 1 to 3 | Inventory only |
| 0 or less | Deprioritized |

## Four action priorities

Each row also gets four priorities. They do not come from the single score, except isolation.
`LOW` means the input was read and did not meet the HIGH rule. When the input a rule needs is
missing, the label is `NOT_EVALUATED`, not `LOW`.

| Column | HIGH when | NOT_EVALUATED when |
|---|---|---|
| `seq_priority` | Edge or full-contig, or Arch C | `edge_status` is blank and the architecture is not C |
| `activation_priority` | bldA tier T3 or T4 (LOW for T1 or T2) | the bldA tier is missing or `NOT_APPLICABLE` |
| `isolation_priority` | Score 10 or more. MED at 7 to 9. Otherwise LOW | never |
| `dereplication_priority` | KCB similarity in the moderate band or higher (40% or more), or RiQ above 0.50 | neither a KCB percent band nor a readable RiQ is present |

A RiQ value that is not a number is recorded in `skip_notes` as `RiQ: unreadable value ...` and no RiQ term is applied.

A cluster can be sequencing HIGH and isolation LOW: a fragment worth fixing before it is worth isolating.

## Read the output

`locator` shows `BGC_ID (contig · regionN)` for each row. For the full strain / full node-or-contig / region / BGC alias identity, take the contig from the package inventory. The CSV is sorted by score, highest first.

Treat the result as a sort order for a person to review. The score combines the listed routing terms, including terms for an observed no-anchor state; inspect each term and missing input before interpreting it. It does not establish assembly quality, compound identity, activity or production.
