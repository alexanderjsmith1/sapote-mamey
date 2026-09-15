# Read your Sapote–Mamey results

Start with the **Complete_Package.zip** the run produced. Extract a copy and keep the extracted
folder together. Open `OPEN_ME_FIRST.html` in your browser, or open the per-strain workbook in
Excel. You can read these files without Python. You only need the environment to re-run or
validate the software.

Older packages may have an entry page that names one particular assistant, or a simpler
completion badge. That wording does not require a particular assistant. The current results
page separates the recorded statuses; older sealed packages stay as they were. Use the files
below as the evidence.

## Open these in order

| File | What it is for | What to check |
|---|---|---|
| `OPEN_ME_FIRST.html` | Entry page and links | Correct strain and run; read the status details, not just the badge colour |
| `issue_log.md` | Recorded concerns | Which issues affect your question; a warning is not automatically a failed run |
| `gate_validation.json` | Validation and evidence receipt | `status`, `gold_completeness`, and `json_evidence_visibility` |
| `[strain]_5_workbook.xlsx` | Browse the analysis tables | Inventory and lead rows; source identities and missing values |
| `[strain]_2_inventory.csv` | One row per detected region | Boundary, coordinates, product annotations and evidence states |
| `[strain]_4_triage_board.csv` | Choose regions for closer review | Rankings, architecture, exclusions, evidence and fragmentation |
| `manifest.json` | Run identity and detailed provenance | Input hash, engine, settings, assembly fields and terminal issues |

`[strain]` is your actual local label, not literal brackets. CSV is a plain-text table Excel can
open. JSON is a structured record; an assistant can explain selected fields without changing it.
Do sorting and annotation in a working copy, so an accidental spreadsheet save cannot alter the
sealed evidence.

## Four different questions about completion

1. **Did the command finish?** The exit code and execution log answer this.
2. **Did the package pass its checks?** The validator's result answers this.
3. **Which evidence actually ran?** Check evidence visibility and the channel-specific receipts.
4. **Was interpretation authored and reviewed?** A table, template or depth assignment does not mean yes.

`MAMEY_COMPLETE_WITH_ISSUES`, validator `MAMEY_COMPLETE`, and `JUDGMENT_PENDING` can all appear
in one legitimate package. Do not erase one status because another says complete.

| Evidence label | Read it as | Do not read it as |
|---|---|---|
| `MAIN_JSON_PARSE_HELD` | The full-mode main JSON parse was withheld by its guard | No BGCs or no useful other evidence |
| `MAIN_JSON_WALKER_TRUNCATED` | The bounded walker stopped at a limit | Exhaustive JSON extraction |
| `UNKNOWN` | Completion was not established | No hits or successful full coverage |
| `NOT_SUPPLIED` / unavailable | Required input/channel was absent or unavailable | A negative biological result |
| Observed hit or match | Evidence under the recorded method and conditions | Confirmed compound identity or production |

## Read a real row

An example bounded-mode package for Nocardia brevicatena NBRC 12119 has 55 region records. Its highest-ranked row
in the triage table is:

**NB_NBRC12119 / NZ_BAFU01000048.1 / region001 / BGC018**

The row records `Products = betalactone; other; terpene`, `Boundary = Edge`, `Arch = C`,
`Class_Conf = LOW`, `AB_auto = 54.0`, `AF_auto = 30.0`, and `Novelty_auto = 34.0`.
Those numbers are pipeline scores. They are not percentages, probabilities, measured
antimicrobial activity, or proof of a new compound. The Edge flag and low class confidence are
reasons to look at the underlying region before investing in a detailed interpretation. "other"
is an annotation category, not a reason to discard the record.

A good first question: what evidence supports this row, what might be missing at the contig
edge, and which interpretation would change if that evidence were available? A poor question:
asking the software to name the compound from the score.

## Counts, boundaries and assembly are different things

The same package reports 20 interior, 23 edge and 12 full-contig regions. The weighted count is
20 + 0.5 × 23 + 0.25 × 12 = **34.5**. That is the pipeline's boundary-weighted heuristic, not a
measurement of 34.5 pathways or compounds. Raw regions can contain multiple protoclusters, and
fragmented pathways can span records; do not force a one-to-one reading.

The assembly manifest separately reports **248 contigs** and **N50 102,039 bp**, with a
FRAGMENTED contiguity classification. The boundary-derived POOR label uses different evidence.
Do not call the whole assembly "poor" from the region-boundary label alone without looking at
contiguity.

## Decide what to investigate next

- Review a selected region's genes, domain support and reference matches, keeping the full identity.
- For an edge or full-contig region, inspect candidate links and competing fragment explanations.
- Treat assay observations as strain/extract context; do not assign them to a locus without evidence.
- Author a Mode B interpretation only after you have chosen the question, the available evidence and the named profile.

Online searches and BLASTp are optional follow-up. These walkthroughs do not need them. Leave a
missing external search as an explicit gap; do not fill it with remembered or invented hits.

## Keep and transfer the result

Keep the complete package, the original input identity/hash, the command and validation
records, the reviewed figures and any authored interpretation. A generated brief summarizes
extraction; it is not an authored biological conclusion. Open its pages and check labels and
content before you share it. A package can validate while its PDF has overflowing or
overlapping text. Treat such a PDF as needing layout repair and use the underlying tables for
exact identifiers. Brief profiles do not guarantee a fixed page count, because figure pages may
be appended.

The Complete_Package ZIP is the portable result unit. Some post-seal outputs can sit beside it;
check the run's final file inventory and transfer those separately if you need them. A later
brief is not in an earlier ZIP. On another laptop, extract a copy and keep the links intact.
The [shared handoff policy](ASSISTANT_USER_GUIDE.md#next-paths-automatic-save-state-and-transcripts)
covers automatic state saving, transcript coverage and file accounting.

## Work through one biological question

Start from a locus in [the nine Type Strain cases](TYPE_STRAIN_WALKTHROUGHS.md), not from a
familiar compound name. Copy its **strain + full contig + region + BGC ID** from the same run.
Join the triage row to exactly one inventory row and confirm the source region GenBank exists.
BGC IDs and ranks can change between runs; a remembered `BGC018` on its own is not enough.

Read the fields in this order:

| Question | Evidence to inspect | What stays uncertain |
|---|---|---|
| Which sequence was analyzed? | Input hash, full contig/region locator, inventory coordinates | A display name alone cannot establish identity |
| How well is the region recovered? | Boundary label, contig length, gene/domain architecture | Interior does not prove every pathway component is present |
| Why was it prioritized? | AB/AF/novelty scores, lead tier and recorded triggers | Scores are not calibrated probabilities or assay measurements |
| What does it resemble? | KCB/reference identifiers, coverage and architecture | A top retained hit does not prove product identity or an exhaustive search |
| Which evidence is missing? | Per-channel status, truncation and issue records | Missing data must not become a biological negative |
| What claim can be written? | Source-bound observations, alternatives and claim limits | Production and activity need appropriately linked experiments |

Example: a retained high-priority region with an edge boundary and a named KCB hit can justify
investigating a related biosynthetic capacity. It does not justify "this strain produces that
named compound", however large the number beside the hit. Write down the sequence observation,
why it matters, the competing explanation, and the evidence that would separate them.

### Counts and zeros

The corrected BGC count is the program's boundary-weighted statistic:
Interior + 0.5 × Edge + 0.25 × Full-contig. The weights do **not** measure the fraction of a
pathway recovered. An Edge region is not necessarily half a cluster, and the statistic is not a
proven lower bound on the true number of distinct pathways. Report the raw region count and the
weighted statistic separately, with the boundary distribution and settings. Comparisons between
strains still need comparable input processing.

A measured zero means a particular operation ran within a defined scope and returned zero.
`NOT_MEASURED`, `UNBOUND`, invalid data and truncated evidence are different states. A scan with
zero fragment pairs can complete correctly. No matches in one supplied database does not mean no
related pathway exists anywhere.

### A short interpretation template

- **Identity:** exact strain/contig/region/BGC and source run.
- **Observed:** file, row/field and value; say whether it is upstream annotation or new computation.
- **Interpretation:** a bounded capacity hypothesis and why the evidence supports it.
- **Alternative:** another explanation consistent with incomplete or conflicting evidence.
- **Missing:** specific channels, gaps, truncation or unresolved identities.
- **Next evidence:** one action that would separate the alternatives, with online scope stated separately.

This is a review note, not a substitute for the selected Mode B contract. Do not fill required
scientific sections with invented detail to satisfy a template.

For damaged or confusing results, see [Troubleshooting](COMMON_MISTAKES.md). To keep and
transfer the evidence, see [Files, storage and handoff](FILES_STORAGE_AND_HANDOFF.md).
