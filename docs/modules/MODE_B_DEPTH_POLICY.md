# Older character-floor check and where Mode B evidence lives

Finished cards follow a Mode B profile (`full48`, or `current50_v2`). See the [profile matrix](../MODEB_PROFILE_MATRIX.md) and the [walkthrough](../MODE_B_USER_WALKTHROUGH.md). A character count does not measure evidence. This page covers two smaller things: the older length check in `mamey/mode_b_quality_gate.py`, and where to find the data a card cites. For terms such as Mode B and card, see the [glossary](../GLOSSARY.md).

The JSON file named `modeb_full30_corrective_contract.json` holds the 48-section default profile. Its name is historical. Do not read a section count from it.

## The older check

The check counts text, not analysis. It cannot tell whether an analysis was run. Selected implemented text gates are:

- A character floor by triage rank: 12,000 for ranks 1 to 10, 11,000 for ranks 11 to 25, 10,000 for the rest. Fragment relief requires a recognized boundary state and a supplied CDS count at most 22; missing boundary/count information does not qualify. A qualifying fragment can use a 2,500 floor. Under 2,000 characters is a `STUB`.
- FULL also requires at least four matched section markers, explicit sections 9 and 10, and at least 2,000 characters from the first matched section 11–20 marker to the end. These are lexical gates, not verification that those sections contain valid evidence.
- A term-density check. It counts locus tags and domain terms, repeats included, with a minimum of 12. The threshold is `int(character_count / 1000 * 1.0)`.

None of these gates counts verified BLASTp alignments, distinct genes or finished analyses. Do not repeat tokens to clear a floor. If a card is thin, go back to the bound domain, gene and homology evidence and deepen the interpretation. If a required channel is unavailable, say so and state what that limits.

## Where the evidence lives

| Evidence | Source | How |
|---|---|---|
| Domain rows | antiSMASH source ZIP or package gene context | `python mamey_run.py domain-level --package runs/EXAMPLE/package --source-antismash path/to/antismash_result.zip --top-n 10 --out reviews/EXAMPLE-domain-new`. Use a new `--out` folder each run; an occupied one is refused. It picks the top BGCs by AB + AF auto score, not by the displayed rank. The archive is used only when its SHA-256 matches the package manifest. Otherwise the run can fall back to the package's limited gene context, or write a skipped receipt, and some skips exit 0. Read `domain_level_receipt.json`. See [domain-level Mode B](DOMAIN_LEVEL_MODE_B.md). |
| Per-gene BLASTp | Result files and their query receipts | Reuse existing results first. `blastp-round` writes a local plan by default: full proteins for the top 3 clusters (`--full-top`), representatives for the rest. A plan is not a search. See the [BLASTp protocol](../ONLINE_BLASTP_PROTOCOL.md). |
| Domain roles, burden, claim ceiling | `domain-level` output | Role category, per-cluster burden and a safe/unsafe claim pair. |
| Gene table | `<strain>_gene_by_gene_all_bgcs.csv` | The `sec_met_domains` column can split a domain name differently from antiSMASH (for example `micKC` and `Pkinase`). Treat a missing domain there as weakly supported, never as "lacks the domain". |
| KCB and MIBiG similarity | `knownclusterblast` files and the triage `KCB_top` column | Similarity, not identity. |
| Deep domain hits and active sites | `deep_data.json` in the package root | Gold-mode deep-data emission is attempted but may be skipped, held or fail. Inspect the actual file, full identity and issue records; empty arrays do not show absence. |

Match every profile row to the full identity, **strain / full node-or-contig / region / BGC alias**. Domain-hit rows carry the contig in `region_key` and omit the alias and region, so they are not a complete regional identity. Missing scores stay `null`.

Tag each fact in a card as from the package store, reconstructed, or from outside literature. Keep the language at class level ("consistent with", never "produces"). BLASTp and KCB are similarity. Bioactivity is extract-level.

## Format references

Read the [exemplar guide](../reference/modeb_exemplars/README.md) before you reuse a card. It holds one `full48` format reference and seven older class sketches. Copy structure and register only. Do not copy sections, genes or conclusions from them.

## Clusters that capture more than one class

When a region holds a second class next to the intended one, the card must say so. `modeb_class_checklist` maps words in the product label to concepts and raises a `CONTENT_GAP` warning when a concept is missing from the card. Explain each co-captured system from the region's evidence and separate it from the intended cluster. A keyword match does not prove a cluster is over-merged.
