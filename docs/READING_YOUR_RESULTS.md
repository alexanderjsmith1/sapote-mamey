# Read your Sapote–Mamey results

Start with the **Complete_Package.zip** produced by the run. Extract a copy and keep the extracted
folder together. Open `OPEN_ME_FIRST.html` in your browser, or open the per-strain workbook in
Excel. You can read those files without learning Python. Re-running or validating the software
requires the appropriate environment; simply reading the files does not.

Older packages may have an entry page that mentions only Claude or a simpler completion badge.
That wording does not require a particular assistant. The candidate results page separates the
recorded statuses, but older sealed packages remain unchanged. Use the files below as evidence.

## Open these in order

| File | What you use it for | What to check |
|---|---|---|
| `OPEN_ME_FIRST.html` | Entry page and links | Correct strain and run; status details, not just badge color |
| `issue_log.md` | Recorded concerns | Which issues affect your question; a warning is not automatically a failed run |
| `gate_validation.json` | Validation and evidence receipt | `status`, `gold_completeness`, and `json_evidence_visibility` |
| `[strain]_5_workbook.xlsx` | Browse the analysis tables | Inventory and lead rows; source identities and missing values |
| `[strain]_2_inventory.csv` | One row per detected region | Boundary, coordinates, product annotations and evidence states |
| `[strain]_4_triage_board.csv` | Choose regions for closer review | Rankings, architecture, exclusions, evidence and fragmentation |
| `manifest.json` | Run identity and detailed provenance | Input hash, engine, settings, assembly fields and terminal issues |

`[strain]` means your actual local label, not literal bracketed text. CSV is a plain-text table
that Excel can open. JSON is a structured record; your assistant can explain selected fields
without changing it. Preserve the original tables; do sorting or annotation in a working copy
so an accidental spreadsheet save does not alter the sealed evidence.

## Four different questions about completion

1. **Did the command finish?** Its exit code and execution log answer this.
2. **Did the package pass its checks?** Read the validator's result.
3. **Which evidence actually ran?** Inspect evidence visibility and channel-specific receipts.
4. **Was interpretation authored and reviewed?** A table, template or depth assignment does not answer yes.

`MAMEY_COMPLETE_WITH_ISSUES`, validator `MAMEY_COMPLETE`, and `JUDGMENT_PENDING` can all appear in
one legitimate package. Do not erase one status because another says complete.

| Evidence label | Read it as | Do not read it as |
|---|---|---|
| `MAIN_JSON_PARSE_HELD` | The full-mode main JSON parse was withheld by its guard | No BGCs or no useful other evidence |
| `MAIN_JSON_WALKER_TRUNCATED` | The bounded walker stopped at a limit | Exhaustive JSON extraction |
| `UNKNOWN` | Completion was not established | No hits or successful full coverage |
| `NOT_SUPPLIED` / unavailable | Required input/channel was absent or unavailable | A negative biological result |
| Observed hit or match | Evidence under the recorded method and conditions | Confirmed compound identity or production |

## Read a real row

The Round 2 bounded Nocardia brevicatena package has 55 region records. Its highest-ranked row
in the inspected triage table is:

**NB_NBRC12119 / NZ_BAFU01000048.1 / region001 / BGC018**

The row records `Products = betalactone; other; terpene`, `Boundary = Edge`, `Arch = C`,
`Class_Conf = LOW`, `AB_auto = 54.0`, `AF_auto = 30.0`, and `Novelty_auto = 34.0`.
Those numbers are pipeline scores, not percentages, probabilities, measured antimicrobial activity,
or proof of a new compound. The Edge flag and low class confidence are reasons to inspect the
underlying region before investing in a detailed interpretation. “other” is an annotation category,
not permission to discard the record.

A useful first question is: “What evidence supports this row, what might be missing at the contig
edge, and which interpretation would change if the missing evidence were available?” A poor
question is to ask the software to name the compound from the score alone.

## Counts, boundaries and assembly are different

The same package reports 20 interior, 23 edge and 12 full-contig regions. The weighted count is
20 + 0.5 × 23 + 0.25 × 12 = **34.5**. This is the pipeline's boundary-weighted heuristic, not a
measurement of 34.5 pathways or compounds. Raw regions can contain multiple protoclusters and
fragmented pathways can span records; do not force a one-to-one interpretation.

The assembly manifest separately reports **248 contigs** and **N50 102,039 bp**, with a FRAGMENTED
contiguity classification. The boundary-derived POOR label uses different evidence. Do not call
the entire assembly “poor” solely from that region-boundary label without examining contiguity.

## Decide what to investigate next

- Review a selected region's genes, domain support and reference matches, preserving the full identity.
- For an edge/full-contig region, inspect candidate links and competing fragment explanations.
- Use assay observations as supplied strain/extract context; do not assign them to a locus without evidence.
- Author a Mode B interpretation only after selecting the question, available evidence and named profile.

Online searches and BLASTp are optional follow-up work. These walkthroughs do not require them.
Missing external searches should remain explicit gaps; do not fill them with remembered or invented hits.

## Keep and transfer the result

Keep the complete package, original input identity/hash, command and validation records, reviewed
figures and any authored interpretation. A generated brief summarizes extraction; it is not an
authored biological conclusion. Open its pages to check labels and content before sharing it. The Round 3 Nocardia example
exposed first-page overflow and overlapping text despite successful package validation. Treat
that PDF as needing layout repair; use the underlying tables for exact identifiers. Brief profiles
do not guarantee a fixed page count because figure pages may be appended.

The Complete_Package ZIP is the portable result unit. Some post-seal outputs can live beside it;
check the run's final file inventory and transfer those separately if they are needed. Do not assume
that a later brief is in an earlier ZIP. On another laptop, extract a copy and keep links intact.
Use the [shared handoff policy](ASSISTANT_USER_GUIDE.md#next-paths-automatic-save-state-and-transcripts)
for automatic state saving, transcript coverage and file accounting.

## Work through one biological question

Start with a locus from [the nine Type Strain cases](TYPE_STRAIN_WALKTHROUGHS.md), not a familiar compound name. Copy its **strain + full contig + region + BGC ID** from the same run. Join the triage row to exactly one inventory row and confirm the source region GenBank exists. BGC IDs and ranks can change between runs; a remembered `BGC018` alone is insufficient.

Read the fields in this order:

| Question | Evidence to inspect | What remains uncertain |
|---|---|---|
| Which sequence was analyzed? | Input hash, full contig/region locator, inventory coordinates | A display name alone cannot establish identity |
| How well is the region recovered? | Boundary label, contig length, gene/domain architecture | Interior does not prove every pathway component is present |
| Why was it prioritized? | AB/AF/novelty scores, lead tier and recorded triggers | Scores are not calibrated probabilities or assay measurements |
| What does it resemble? | KCB/reference identifiers, coverage and architecture | A top retained hit does not prove product identity or exhaustive search |
| Which evidence is missing? | Per-channel status, truncation and issue records | Missing data must not become a biological negative |
| What claim can be written? | Source-bound observations, alternatives and claim limits | Production and activity need appropriately linked experiments |

For example, a retained high-priority region with an edge boundary and a named KCB hit can justify investigating a related biosynthetic capacity. It does not justify “this strain produces that named compound,” even if the number beside the hit is large. Write the sequence observation, why it matters, the competing explanation, and the evidence needed to distinguish them.

### Counts and zeros deserve special care

The corrected BGC count is the program's boundary-weighted statistic: Interior + 0.5 × Edge + 0.25 × Full-contig. The weights do **not** measure the fraction of a pathway recovered. An Edge region is not necessarily half a cluster, and this statistic is not a proven lower bound on the true number of distinct pathways. Report raw region count and the weighted statistic separately, with boundary distribution and settings. Comparable input processing is still required for comparisons.

A measured zero means a particular operation ran within a defined scope and returned zero. `NOT_MEASURED`, `UNBOUND`, invalid data and truncated evidence describe other states. A scan with zero fragment pairs can complete correctly. No matches within one supplied database does not mean no related pathway exists anywhere.

### A short interpretation template

- **Identity:** exact strain/contig/region/BGC and source run.
- **Observed:** file, row/field and value; distinguish upstream annotation from new computation.
- **Interpretation:** a bounded capacity hypothesis and why the evidence supports it.
- **Alternative:** another explanation consistent with incomplete or conflicting evidence.
- **Missing:** specific channels, gaps, truncation or unresolved identities.
- **Next evidence:** one action that would distinguish the alternatives, with online scope stated separately.

This is a review note, not a replacement for the selected Mode B contract. Do not fill required scientific sections with invented detail just to satisfy a template.

For damaged or confusing results, use [Troubleshooting](COMMON_MISTAKES.md). To retain and transfer the evidence, use [Files, storage and handoff](FILES_STORAGE_AND_HANDOFF.md).
