# DELIVERABLE: Large Modular PKS Rescue (LMPKS)

**What this is.** A method for judging large modular type I polyketide synthase (PKS) pathways that antiSMASH labels, or KCB (KnownClusterBlast) scores, as weak or splits across contigs. The engine extracts the domain evidence. You grade it by hand. No tool applies the grades or the report.

**Purpose.** Give each triggered locus one rescue grade, so you can decide which loci deserve long-read sequencing.

The current task and [assistant governance](../ASSISTANT_GOVERNANCE.md) decide what you may do. Source code owns the extracted fields. Do not change saved scores from this page. The [wet-lab matrix](DELIVERABLE_WetLabMatrix.md) tool does not apply any LMPKS adjustment. It records `LMPKS: not run`. Terms are in the [glossary](../GLOSSARY.md).

## When to run it

Run it next to the KCB review. If no trigger fires, write a one-page null result that lists each criterion and its outcome. A report with no LMPKS section is incomplete, even when nothing needs rescue.

## The engine's own flag

The engine already sets a fragment flag, `LMPKS_FRAGMENT_SET`, with a different rule from the trigger table. It sets the flag when it counts 4 or more modular, hybrid or trans-AT KS-like text patterns in the CDS annotations and at least one edge or full-contig region has a PKS, NRPS or trans-AT product (`mamey/source_scans.py`, `scan_flbr`, lines 934-939). With a weaker signal it writes `MEGASYNTHASE_FRAGMENT_SUSPECT`. With none it writes `NULL`. Read the `FLBR` row of `<strain>_3_scan_states.json` for the result.

Your count from `<strain>_domains.csv` can differ from the engine's flag. Report both, and say which is which. Do not change the engine's flag.

## Triggers

| Trigger | Condition | Action |
|---|---|---|
| 1. Weak KCB hit | Interior T1PKS region with a KCB cumulative score below 1,500, including 0 (see the note below the table) | Reconstruct the modules |
| 2. Truncated fragment | Contig-edge T1PKS with at least one modular, hybrid or trans-AT KS domain of 300 bits or more | Fragment rescue |
| 3. Genome-wide KS count | 4 or more `PKS_KS` rows in `<strain>_domains.csv` | Report the count; raise sequencing priority |
| 4. Possible trans-AT | KS, KR, DH and ER present, no in-cis AT domain | Trans-AT check |
| 5. Possible polyene | 3 or more DH domains, especially with few ER | Polyene check |
| 6. Chemistry mismatch | Published PKS chemistry for the genus, no clean antiSMASH BGC | Map chemistry to domains |

The 1,500-bit and 300-bit cutoffs and the count of 4 are manual conventions for this review. No code applies them.

A KCB score of 0 can mean no hit, but it can also mean the engine did not read KCB (`UNKNOWN_KCB`), or that the KCB text file was recognized as a no-hit report (`KNOWNCLUSTERBLAST_NO_HITS_UNVALIDATED`: "no hits" text or empty "Significant hits:" and "Details:" sections, not checked against the JSON). A missing or unreadable KCB file is neither of these reports; it is not a no-hit. Check which before you treat a 0 as weak. Many interior T1PKS regions will trigger on a package with no KCB data.

"KCB cumulative score" is the summed BLAST score in the `KCB_score` column. It is not the percent similarity. See [Reading your results](../READING_YOUR_RESULTS.md).

## Inputs

| Field | Used for | If missing |
|---|---|---|
| `<strain>_domains.csv`: one row per domain on a BGC gene. Use columns `region`, `locus_tag`, `domain` (`PKS_KS`, `PKS_AT`, `PKS_KR`, `PKS_DH`, `PKS_ER`, `ACP` and so on), `bitscore` and `substrate`. It covers genes inside antiSMASH regions only. | Module string | Mark "not available". Never infer a domain is present. |
| AT substrate calls (malonyl, methylmalonyl, methoxymalonyl). Need `--json-evidence bounded` or `full` on `run`. | AT pattern | With `--json-evidence off`, mark the AT substrate `unscanned`. |
| Active-site pairings (AT specificity, KR configuration, TE serine) | Module completeness and stereochemistry | Mark "not available". |
| `*_4A_RGGMCI_ranked_pairs.csv` in the package | Grouping fragments across contigs | Linkage is a homology hypothesis, never a nucleotide join. |
| `manifest.json`, `bgcs[].edge_status` | `[missing start]` and `[missing terminus]` marks | None. |

`--json-evidence` takes `off`, `bounded` or `full`. `bounded` is the default for `run`. A capped session forces `off`.

## Steps

1. Take the KS inventory, reductive loops, AT substrates, docking and TE domains from `<strain>_domains.csv`. For KS clades shared across contigs, read `<strain>_4B_pks_ks_fragment_scan.csv`.
2. For each triggered BGC, write the module string in gene order.
3. Estimate the broad class only. Chain length from module count is a lower bound.
4. Group fragments from different contigs by KS subtype, AT pattern and docking. Cite the RG-GMCI pairs.
5. Assign exactly one grade.

Use this sentence for any split model:

> Split-pathway rescue hypothesis based on modular PKS domain architecture across contigs. Long-read sequencing is required to confirm physical linkage and module order.

## Rescue grades

| Grade | Definition |
|---|---|
| LMPKS-A | 3 or more complete modules, a TE, and a classifiable AT and reductive pattern |
| LMPKS-B | 2 or more modules plus docking or split evidence, incomplete ends |
| LMPKS-C | 4 or more KS domains in fragments, too few to order |
| LMPKS-D | One high-bitscore fragment, no evidence joining it to anything |
| LMPKS-T | Trans-AT confirmed or strongly supported |
| LMPKS-P | Polyene confirmed or strongly supported |
| LMPKS-L | Linear PKS of 3 or more modules, no TE recovered |
| LMPKS-X | A trigger fired and the evidence fails rescue (a null) |

Use the highest grade that applies. A grade is a triage label. It does not change any saved score.

## Outputs

You write these by hand: a rescue report (or the one-page null), the KS inventory table, the per-BGC module strings with grades, and the split-pathway model if there is one.

## Checklist

- [ ] Every interior T1PKS with a KCB cumulative score below 1,500 was evaluated. So was every contig-edge T1PKS with a KS of 300 bits or more.
- [ ] The KS count from `<strain>_domains.csv` is reported next to the engine's `FLBR` result.
- [ ] Docking and TE or thioesterase searches are reported.
- [ ] AT calls are summarized where JSON evidence exists. Otherwise `unscanned`.
- [ ] Trans-AT and polyene criteria are checked.
- [ ] One grade per triggered locus, or the null page.
- [ ] Long-read advice is updated where fragments or split evidence exist.
- [ ] Every locus is written as `strain / full contig / region / BGC alias`. No compound is named without chemistry.
- [ ] Open holds are listed.

For a standalone rescue prompt, see `prompts/reuse/SAPOTE_FRAGMENT_RESCUE_REUSE_PROMPT.md`.
