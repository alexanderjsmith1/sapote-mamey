# Encyclopedia currency record

> **Retired in v9.7.458.** This volume is kept as a historical record. Its settings and numbers may be out of date; the current guides are listed on the [Encyclopedia pointer page](../../../wiki/Encyclopedia.md).

This record explains the bounded corrections reviewed on **2026-09-09**. For a current task, start with [Read the large Sapote references](../../../docs/GUIDE/07_LARGE_REFERENCE_ENTRY.md), then compare the relevant symbol or function with your selected source version. The table below preserves that review’s settings; it does not update every volume’s grounding. Original volume stamps and historical worked-run numbers remain visible.

## Confirmed corrections

The engine dictionary has 18 CCTT families. Counting all T43-prefixed tokens also includes catalog-only names and gives the wrong denominator. The current scoring sets contain 8 AB and 3 AF triggers. Their sibling references were corrected in the affected volumes and the master index. The obsolete +5 novelty credit for missing KCB was also corrected in Volumes III, V, and VII; the current scorer grants no novelty credit for absent/unknown KCB evidence. The weak-class set contains 14 entries rather than the 12 previously listed in Volume VII. TOMM, LMPKS, and SILENT remain outside CCTT_PATTERNS.

## Engine observations checked

Collection-valued constants below report their number of entries; numeric constants report their value. These are executable settings and routing priors, not biological acceptance.

| Symbol | Recorded value | Source |
|---|---|---|
| `CCTT_PATTERNS` | `18` | `mamey/source_scans.py` |
| `CCTT_PROMISCUOUS` | `3` | `mamey/source_scans.py` |
| `_POLYENE_MIN_KS` | `4` | `mamey/source_scans.py` |
| `AB_DIAGNOSTIC_TRIGGERS` | `8` | `mamey/scoring.py` |
| `AF_DIAGNOSTIC_TRIGGERS` | `3` | `mamey/scoring.py` |
| `AB_KEYWORDS` | `18` | `mamey/scoring.py` |
| `AF_KEYWORDS` | `17` | `mamey/scoring.py` |
| `NOVELTY_KEYWORDS` | `11` | `mamey/scoring.py` |
| `DIAGNOSTIC_BONUS` | `25` | `mamey/scoring.py` |
| `RIPP_FRAGMENT_MAX_KB` | `8.0` | `mamey/scoring.py` |
| `TIER1_FLOOR_EXCLUDED_PREFIXES` | `('T43-HAL_', 'T43-XHAL_')` | `mamey/scoring.py` |
| `WEAK_OVERCALL_CLASSES` | `14` | `mamey/scoring.py` |
| `ADJ_MAX_LOCUS_GAP` | `30` | `mamey/rggmci.py` |
| `ADJ_MAX_SPAN` | `400` | `mamey/rggmci.py` |
| `RGGMCI_MAX_HUB_DEGREE` | `4` | `mamey/rggmci.py` |

For parameter comparisons, distinguish a function default from the value its caller supplies. The recorded weighted-count formula uses 1/0.5/0.25, and assembly tiers use 70/45/20 (`mamey/assembly.py`). `parsers._edge_status` defaults to a 5,000 bp flank. `source_scans.bgc_coupling` defaults to 10,000 bp, but `scan_cassettes` and `scan_umed` explicitly use 5,000 bp; the TFBS default is 300 bp. In `scoring.py`, 85/70/50 are initial lead-tier breakpoints, followed by further floor/exclusion rules. Rescue bonuses are 8/4 only under their eligibility and exclusion conditions. The 0.35/0.2 multipliers remain in the formulas, but `edge_penalty` returns zero, so those multipliers do not establish an active truncation penalty.

## Review limits

All 13 volume bodies were enumerated for numerical and roster references. That census is not validation of every sentence. The checked constants above cover the shared trigger/scoring roster and selected cross-referenced settings. Historical case-study counts, literature assertions, platform instructions, other detector rosters, and unbound numerical claims remain unverified against the current engine. Do not use old worked runs as current regression oracles without rerunning their exact inputs. Volumes retain their original grounding information; where no grounding stamp exists, current grounding is not established.

The source code and current command contracts govern executable behavior. For scientific use, bind the exact package/locus, source evidence, and review state independently. Similarity is not identity; capacity is not production; judgment is deferred.
