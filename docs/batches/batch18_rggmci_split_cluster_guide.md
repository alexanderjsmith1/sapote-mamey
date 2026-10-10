# RG-GMCI split-cluster candidates: software and reporting limits

RG-GMCI nominates pairs for review from shared reference signals and geometry. Shared comparator evidence, complementary annotations, an engine HIGH token or a rollup “CONFIRMABLE” label does not prove a physical contig join, one complete pathway, product identity, expression or activity. Preserve both separate loci as strain / full node-or-contig / region / BGC alias in every individual-pair statement. Never replace either with a shortened BGC alias.

## Engine evidence versus historical shorthand

The .149a guide's “both KCB = HIGH / both CB = MODERATE / one match = LOW” table was shorthand, not the current rule. Current `mamey/rggmci.py` uses scored signals, thresholds14/9, geometry adjustments, hub demotion and additional terminus/overlap guards (`:27–28,528–536,950–1019,1187–1207,1331–1351`). Engine values are `HIGH_RG_GMCI_RESCUE`, `MODERATE_RG_GMCI_CANDIDATE` and `LOW_SHARED_REFERENCE_SIGNAL`. Preserve the effective verdict, evidence base, subject/geometry counts, guards and source version rather than translating those tokens into biological confidence.

Subject verdicts include `COMPLEMENTARY_SPLIT`, `TERMINUS_TRUNCATION_SPLIT`, `OVERLAPPING_PARALOG`, `MIXED_SUBJECT_SIGNAL`, and `INSUFFICIENT_SUBJECT_DATA`; the old bare “AMBIGUOUS” menu is incomplete. Complementary coverage can be consistent with a split candidate, but it does not rule out co-capture or paralogy in general. An “alternative tested and rejected” statement requires actual pair-specific evidence, not a copied template. KCB and ClusterBlast are related computational channels, not independent experimental replication. Engine routing adjustments and downstream standalone ranker bonuses differ; no universal historical “+8” should be copied into a current report.

The weighted count `Interior + 0.5*Edge + 0.25*Full-contig` is an engineering descriptor. It is not a mathematical lower bound on true cluster number, and a homology-guided pair does not authorize subtracting an arbitrary post-rescue count. Preserve the pre-rescue descriptor and separately describe candidate pairs without changing the scientific denominator.

## Current cohort rollup interface

The actual CLI uses `--packages` and `--out-prefix`, **not** the old `--banked-dir`, `--workbook`, or `--outdir` arguments. It reads package ranked-pair CSVs and emits `<prefix>_board.md` and `<prefix>_evidence.csv`; it does not update a workbook or reconstruct sequence (`tools/rggmci_cohort_rollup.py:223–300`). Resolve unused external destinations before any separately authorized invocation.

Discovery is recursive but skips specifically named backup/scratch path segments. It keeps one file per filename-derived strain, preferring the shallowest and then lexicographically first equal-depth path. It does not verify which candidate is current, parse package sealing/receipts, or bind source hashes; unreadable/CSV-error files are skipped (`:147–178`). Freeze the selected source inventory and exact hashes before treating totals as a complete cohort denominator. The evidence CSV has strain/aliases/contigs but no explicit region columns; the board likewise does not ensure the complete four-part identity. Maintain a separately bound full-locus pair index before report adoption.

The rollup admits engine HIGH-prefix or legacy exact HIGH rows, then applies its effective-verdict/terminus-note interpretation. Rollup review labels `CONFIRMABLE`, `LIKELY`, `NEEDS-REVIEW` depend on disjoint/shared counts, core fraction and distance guards; multiple reference matches are not independent biological trials (`:80–144,181–209`). Zero pooled rows returns1; pooled rows but no genuine pairs can still produce a successful empty review board. Output Markdown/CSV are separately atomic helper writes, not a pair transaction; no source/code/output hash receipt is emitted. Preserve partial outputs and use a new prefix after failure.

## Historical source record and current card scope

This replaces .149a guidance dated2026-06-29. The original explanatory prose, partial-identity examples, joint-module template and post-rescue subtraction recipe remain preserved in the immutable baseline for provenance, not as a scientific answer key. No individual-pair evidence was validated here, and no reconstruction or biological computation was run. Physical-linkage evidence and owner scientific adoption remain held independently of documentation readiness.

The old §3/§10 template is not a current50 validation contract. Use [the current profile](../MODEB_CURRENT50_V2_CONTRACT.md), retain exact identity and source evidence for both arms, and describe missing or contradictory steps. The [current ranker guide](../DEFINITIVE_BGC_RANKER.md) distinguishes review bonus from measured linkage and standalone evidence scores.
