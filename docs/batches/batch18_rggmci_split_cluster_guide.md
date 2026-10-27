# Review an RG-GMCI split-cluster candidate

Start with the package's ranked-pair row and its source evidence. RG-GMCI nominates pairs for review from shared references and geometry. Use the row to explain why the pair was nominated and what would still be needed to assess physical linkage.

## Read and report a pair

1. **Identify both arms.** Copy each as **strain / full node-or-contig / region / BGC alias** from bound records. Keep both identities in every individual-pair statement; an alias cannot substitute for either endpoint.
2. **Read the evidence behind the label.** Retain the engine confidence token, original and effective subject verdicts, full override note, subject/geometry counts, guards and source version. Read a rollup label alongside its input row: the rollup can promote a verdict using a terminus note.
3. **Explain the supported interpretation.** Shared comparator evidence and complementary coverage can support a split candidate. State which alternatives the pair-specific evidence actually tests. KCB and ClusterBlast are related computational channels; HIGH and CONFIRMABLE are software labels, not proof of a physical join, one complete pathway, product identity, expression or activity.
4. **Carry the interpretation into the selected report.** Use the [current profile matrix](../MODEB_PROFILE_MATRIX.md) for a Mode B card. Keep missing or contradictory evidence explicit. The [ranker guide](../DEFINITIVE_BGC_RANKER.md) distinguishes a review bonus from measured linkage. Preserve the pre-rescue count descriptor; candidate pairs do not authorize subtracting from a biological cluster count.

## Read a cohort board with its inputs

The cohort helper reads package ranked-pair CSVs and writes a Markdown board plus an evidence CSV. Before using its totals, freeze the selected input inventory and hashes and bind a separate full-locus pair index: its exports lack explicit region columns. Read the complete input rows as well as the exported subset, because excluded, mixed and insufficient rows are not all exported as row-level evidence. An empty board is not by itself evidence that the cohort lacks candidates.

<details>
<summary>Implementation details for interpreting or planning a cohort rollup</summary>

## Engine evidence versus historical shorthand

The .149a guide's “both KCB = HIGH / both CB = MODERATE / one match = LOW” table was shorthand, not the current rule. Current `mamey/rggmci.py` uses scored signals, thresholds 14/9, geometry adjustments, hub demotion and additional terminus/overlap guards (`mamey/rggmci.py`). Engine values are `HIGH_RG_GMCI_RESCUE`, `MODERATE_RG_GMCI_CANDIDATE` and `LOW_SHARED_REFERENCE_SIGNAL`. Preserve the effective verdict, evidence base, subject/geometry counts, guards and source version rather than translating those tokens into biological confidence.

Subject verdicts include `COMPLEMENTARY_SPLIT`, `TERMINUS_TRUNCATION_SPLIT`, `OVERLAPPING_PARALOG`, `MIXED_SUBJECT_SIGNAL`, and `INSUFFICIENT_SUBJECT_DATA`; the old bare “AMBIGUOUS” menu is incomplete. Complementary coverage can be consistent with a split candidate, but it does not rule out co-capture or paralogy in general. An “alternative tested and rejected” statement requires actual pair-specific evidence, not a copied template. KCB and ClusterBlast are related computational channels, not independent experimental replication. Engine routing adjustments and downstream standalone ranker bonuses differ; no universal historical “+8” should be copied into a current report.

The weighted count `Interior + 0.5*Edge + 0.25*Full-contig` is an engineering descriptor. It is not a mathematical lower bound on true cluster number, and a homology-guided pair does not authorize subtracting an arbitrary post-rescue count. Preserve the pre-rescue descriptor and separately describe candidate pairs without changing the scientific denominator.

## Current cohort rollup interface

The actual CLI uses `--packages` and `--out-prefix`, **not** the old `--banked-dir`, `--workbook`, or `--outdir` arguments. It reads package ranked-pair CSVs and emits `<prefix>_board.md` and `<prefix>_evidence.csv`; it does not update a workbook or reconstruct sequence (`tools/rggmci_cohort_rollup.py:223–300`). Resolve unused external destinations before any separately authorized invocation.

Discovery is recursive but skips specifically named backup/scratch path segments. It keeps one file per filename-derived strain, preferring the shallowest and then lexicographically first equal-depth path. It does not verify which candidate is current, parse package sealing/receipts, or bind source hashes; caught I/O/CSV errors are ignored, but rows appended before a late error remain pooled (`tools/rggmci_cohort_rollup.py`). This is not whole-file rejection or a complete-ingestion receipt. Freeze the selected source inventory and exact hashes before treating totals as a complete cohort denominator. The evidence CSV has strain/aliases/contigs but no explicit region columns; the board likewise does not ensure the complete four-part identity. Maintain a separately bound full-locus pair index before report adoption.

The rollup uppercases/strips confidence and admits any `HIGH_RG_GMCI` prefix or legacy exact `HIGH`, rather than validating an exact enum. Its effective-verdict function promotes any non-genuine verdict, including an original `OVERLAPPING_PARALOG`, when the note contains `severed_arm` or `CORROBORATED_terminus_truncation`; it does not independently recheck the engine geometry. Preserve the original verdict, full note and effective verdict so this interpretation is visible (`tools/rggmci_cohort_rollup.py`).

Rollup review labels `CONFIRMABLE`, `LIKELY`, `NEEDS-REVIEW` depend on disjoint/shared counts, core fraction and distance guards. Missing/unparseable numeric fields default to zero, integer fields accept float conversion, and these helpers do not enforce finite values, valid ranges or a row schema. Treat input integrity and completeness as separate checks; multiple reference matches are not independent biological trials (`tools/rggmci_cohort_rollup.py`). The board and evidence CSV export only the software-defined genuine subset; excluded, mixed, insufficient and unrecognized rows are not exported as row-level evidence. Retain the complete bound input rows and their dispositions separately (`tools/rggmci_cohort_rollup.py`). Zero pooled rows returns1; pooled rows but no genuine pairs can still produce a successful empty review board. Output Markdown/CSV are separately atomic helper writes, not a pair transaction; no source/code/output hash receipt is emitted. Preserve partial outputs and use a new prefix after failure.

</details>

## Where the older instructions went

This page replaces the June 2026 .149a reading route. Its shorthand confidence table, joint-module template and post-rescue subtraction recipe remain in the immutable source history. Use the selected current profile for authoring; the older §3/§10 template does not define current50 validation. Physical linkage and scientific adoption require their own evidence and review.
