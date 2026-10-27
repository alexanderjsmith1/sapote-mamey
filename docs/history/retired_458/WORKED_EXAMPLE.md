<!-- SAPOTE_DOC_STATE: HISTORICAL_REFERENCE -->
# Choose a worked example

Retired in v9.7.458 and kept as a record. Settings and commands may be out of date. Current guide: [Type Strain walkthroughs](../../TYPE_STRAIN_WALKTHROUGHS.md).

For a new run, follow [the Master Walkthrough](../../MASTER_WALKTHROUGH.md). To see how existing
results were read, open [the nine recorded Type Strain cases](../../TYPE_STRAIN_WALKTHROUGHS.md).
If you already have a package, start with [Read your results](../../READING_YOUR_RESULTS.md).

The previous text is in [the historical worked example](../WORKED_EXAMPLE.md).

The Type Strain cases describe candidate runs with retained input identities and reported
measurements. Their page explains the settings, coverage and reproduction evidence needed;
the code bundle alone does not contain every biological output package. Read their observations
as recorded results, not expected counts or speed guarantees for a new run.

## What the earlier public-genome example recorded

Earlier versions of this page walked through *Streptomyces olivochromogenes*, RefSeq
**GCF_001514115.1**, using **Sapote–Mamey v9.7.363 / engine 1.9.120** and public antiSMASH-DB
results. The accession identifies that historical example; it is not a replacement for the
exact input ZIP hash and antiSMASH version when comparing runs.

The historical page reported these values:

| Recorded item | Historical value |
|---|---|
| Input | About 21 MB zipped / 107 MB extracted; 43 region GenBanks and 29 records |
| Region count | 43 |
| Triage counts | High 2; Medium 6; Low 25; Inventory 10 |
| Assembly-boundary tier | `GOOD` |
| Package | 90 files; about 5.2 MB sealed |
| Pfam extraction | 27 tier-1 diagnostic hits |
| Fragment-pair summary | 31 pairs; good-geometry 28; complementary-split 3; overlapping-paralog 7 |

These are transcribed historical reports, not measurements from the current bundle. The old
input and run receipts were not rechecked for this page. Use them to recognize the kinds of
outputs a run records; use your own package's evidence to answer a biological question.
Differences warrant checking inputs, versions and settings before attributing them to a fault.

The historical source was the antiSMASH-DB output entry for `GCF_001514115.1`, with a download
named `GCF_001514115.1.zip`. Current availability and bytes must be checked during an authorized
intake. Keep the downloaded archive outside the code tree with its source and hash. For the
current inspect, extract and validation steps, use the Master Walkthrough rather than the
old installed `mamey` command recipe.

## Read the example in the same order as your package

1. **Confirm the input.** Compare accession, ZIP hash, antiSMASH version and settings in the
   manifest and retained input record. An accession or display name alone is insufficient.
2. **Check coverage.** Read the issue log, saved validation receipt and evidence-channel states.
   Missing reference data means the comparison was unavailable; a no-hit result requires a
   completed operation with known inputs and limits.
3. **Choose one row.** Copy `strain / full node-or-contig / region / BGC alias` from the same
   bound inventory, then read its boundary, architecture and reference support. Historical
   lead aliases without their region binding are insufficient for reuse.
4. **Write one bounded observation.** Say what the row shows, what it might mean, and what
   evidence would distinguish an alternative. AB/AF scores help choose review priority;
   they are not assay measurements or probabilities. An Interior boundary does not prove
   every pathway component is present.

Use [the reading guide's question table](../../READING_YOUR_RESULTS.md#work-through-one-biological-question)
to turn the selected row into a short note. Similarity can support a capacity hypothesis;
production and activity require appropriately linked experimental evidence.

## If the question needs more evidence

Optional datasets and companion analyses have their own inputs and execution requirements.
Use [the companion-tool guide](../../COMPANION_TOOL_GUIDE.md) to select a route for your question and
[external data](../../EXTERNAL_DATA.md) to identify required supplied resources. A single-genome
example does not establish cohort prevalence or family sharing. A tree requires an appropriate
panel and outgroup for its question; use [the current phylogeny workflow](../../PHYLO_AUTOPILOT_WORKFLOW.md)
rather than the earlier example's fixed tip-count warning.

Cite the deposited record, antiSMASH results/version and any reference datasets actually used.
A provenance label describes the source of metadata; it does not verify a functional claim.
For example, `accession` denotes metadata traced to a deposited record, while `asserted`
denotes a person's statement without an on-disk trace. See the
[Master Walkthrough](../../MASTER_WALKTHROUGH.md) for current intake guidance.
