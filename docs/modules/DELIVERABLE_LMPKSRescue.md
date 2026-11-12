# DELIVERABLE: Large Modular PKS Rescue (LMPKS)

**What this is.** A method for judging large modular type I polyketide synthase (PKS) pathways that antiSMASH labels, or KCB (KnownClusterBlast) scores, as weak or splits across contigs. The engine extracts the domain evidence. You grade it by hand. No tool applies the grades or the report.

**Purpose.** Record evidence-strength categories and separate structural hypotheses for reviewed loci, with the basis and open holds, to inform follow-up choices.

The current task and [assistant governance](../ASSISTANT_GOVERNANCE.md) decide what you may do. Source code owns the extracted fields. Do not change saved scores from this page. The [wet-lab matrix](DELIVERABLE_WetLabMatrix.md) tool does not apply any LMPKS adjustment. It records `LMPKS: not run`. Terms are in the [glossary](../GLOSSARY.md).

## When to run it

Run it next to the KCB review. Report a scoped no-trigger result only after the required criteria were assessed, listing each outcome. Missing, failed or unassessed evidence stays unavailable; it is not a null result. Include the section when the selected task calls for this review.

## The engine's own flag

The engine already sets a fragment flag, `LMPKS_FRAGMENT_SET`, with a different rule from the trigger table. It sets the flag when it counts 4 or more modular, hybrid or trans-AT KS-like text patterns in the CDS annotations and at least one edge or full-contig region has a PKS, NRPS or trans-AT product (`mamey/source_scans.py`, `scan_flbr`). With a weaker signal it writes `MEGASYNTHASE_FRAGMENT_SUSPECT`. With none it writes `NULL`. Read the `FLBR` row of `<strain>_3_scan_states.json` for the result. The count covers only the CDS records the scan was given. The scan stores it as `genome_wide_ks_like_count` for compatibility, but the code treats it as genome-wide only for whole-record GenBank input, and `run` passes detected GenBank record scope when available. Inspect the emitted `count_scope`; `NOT_BOUND` is the fallback when scope is not supplied, not the universal run state. Read it as a count over the parsed records, not the whole genome.

Your count from `<strain>_domains.csv` can differ from the engine's flag. Report both, and say which is which. Do not change the engine's flag.

## Triggers

| Trigger | Condition | Action |
|---|---|---|
| 1. Weak KCB hit | Interior T1PKS region with a KCB cumulative score below 1,500, including 0 (see the note below the table) | Reconstruct the modules |
| 2. Truncated fragment | Contig-edge T1PKS with at least one modular, hybrid or trans-AT KS domain of 300 bits or more | Fragment rescue |
| 3. Region KS count | 4 or more `PKS_KS` rows in `<strain>_domains.csv` (genes inside antiSMASH regions only) | Report the count as region-scoped; raise sequencing priority |
| 4. Possible trans-AT | KS, KR, DH and ER present, no in-cis AT domain | Trans-AT check |
| 5. Possible polyene | 3 or more DH domains, especially with few ER | Polyene check |
| 6. Chemistry mismatch | Published PKS chemistry for the genus, no clean antiSMASH BGC | Map chemistry to domains |

The 1,500-bit and 300-bit cutoffs and the count of 4 are manual conventions for this review. No code applies them.

A KCB score of 0 can mean no hit, but it can also mean the engine did not read KCB (`UNKNOWN_KCB`), or that the KCB text file was recognized as a no-hit report (`KNOWNCLUSTERBLAST_NO_HITS_UNVALIDATED`: "no hits" text or empty "Significant hits:" and "Details:" sections, not checked against the JSON). A missing or unreadable KCB file is neither of these reports; it is not a no-hit. Check which before you treat a 0 as weak. A zero with unavailable or unresolved KCB evidence is not a measured weak hit; hold that trigger assessment until the source state is resolved.

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
3. Describe the provisional architecture and broad class hypothesis. An inferred module count is not a proven chain length.
4. Group fragments from different contigs by KS subtype, AT pattern and docking. Cite the RG-GMCI pairs.
5. Report evidence-strength categories separately from supported structural hypotheses, with overlaps and the basis as described below.

Use this sentence for any split model:

> Split-pathway rescue hypothesis based on modular PKS domain architecture across contigs. Physical linkage and module order remain unresolved until independently tested with a method suited to the case.

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

Proposed review convention: report A–D as evidence-strength categories and T/P/L as separately described structural hypotheses when supported; they are not one ordered scale. Record overlaps and their evidence instead of choosing an undefined highest grade. Use X only after relevant rescue criteria were assessed and not met; mark incomplete evidence unavailable. This is documentation guidance for owner review, not an implemented engine rule or an adopted biological classification. No category changes a saved score.

## Outputs

You write these by hand: a rescue report (or the one-page null), the KS inventory table, the per-BGC module strings with grades, and the split-pathway model if there is one.

## Checklist

- [ ] Every interior T1PKS with a KCB cumulative score below 1,500 was evaluated. So was every contig-edge T1PKS with a KS of 300 bits or more.
- [ ] The region KS count from `<strain>_domains.csv` is reported next to the engine's `FLBR` result. Sequence outside the regions is listed as not assessed.
- [ ] Docking and TE or thioesterase searches are reported.
- [ ] AT calls are summarized where JSON evidence exists. Otherwise `unscanned`.
- [ ] Trans-AT and polyene criteria are checked.
- [ ] Evidence-strength categories, supported structural hypotheses and overlaps are reported separately; nulls are assessed and scoped, with missing evidence held.
- [ ] Long-read advice is updated where fragments or split evidence exist.
- [ ] Every locus is written as `strain / full contig / region / BGC alias`. No compound is named without chemistry.
- [ ] Open holds are listed.

For a standalone rescue prompt, see `prompts/reuse/SAPOTE_FRAGMENT_RESCUE_REUSE_PROMPT.md`.
