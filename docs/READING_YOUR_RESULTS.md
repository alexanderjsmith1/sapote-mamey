# Read your Sapote–Mamey results

Start with the **`*Complete_Package.zip`** the run produced (the actual filename includes strain, bundle, engine and antiSMASH detection profile). Extract a copy and keep the extracted
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
| `gate_validation.json` | Saved run/seal validation receipt | `status`, `gold_completeness`, and `json_evidence_visibility`; this is not automatically replaced by a later validate command |
| `package_status.json` | Mutable package-status receipt | Current stored status and provenance; validation can refresh this file |
| `[strain]_5_workbook.xlsx` | Browse the analysis tables | Inventory and lead rows; source identities and missing values |
| `[strain]_2_inventory.csv` | One row per detected region | Boundary, coordinates, product annotations and evidence states |
| `[strain]_4_triage_board.csv` | Choose regions for closer review | Rankings, architecture, exclusions, evidence and fragmentation |
| `manifest.json` | Run identity and detailed provenance | Input hash, engine, settings, assembly fields and terminal issues |
| `manifest_short.json` | Compact triage summary | Boundary tier and counts; open the full issue log and source receipts for coverage warnings |

`[strain]` is your actual local label, not literal brackets. CSV is a plain-text table Excel can
open. JSON is a structured record; an assistant can explain selected fields without changing it.
Do sorting and annotation in a working copy, so an accidental spreadsheet save cannot alter the
sealed evidence.

## Four different questions about completion

1. **Did the command finish?** The exit code and execution log answer this.
2. **Did the package pass its checks?** A current captured validator result answers this. The saved seal receipt describes its earlier validation time.
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

## Saved summaries and current validation

`explain` summarizes `manifest_short.json` with fields from `manifest.json`; it does not rerun validation or synchronize saved summary status with a new result. Its top-lead lines can omit components of the required full locus display. Resolve the complete `strain / full node-or-contig / region / BGC alias` from the same bound inventory before citing one of those lines.

`manifest_short.json` does not carry the full issue list, assembly-sanity result, record-cap observations or metric input-record universe. `explain` reads warnings separately from `issue_log.md` and displays only the first five, truncating each to 100 characters, with a notice when more exist. Read the full log before interpreting a quiet summary as complete coverage. A missing log leaves that display without warnings; it does not establish that the probes passed.

The generated brief displays assembly metrics, contiguity and BGC-boundary labels, plus selected boundary/contiguity warnings. It points readers to the issue log but does not reproduce the full manifest issue list. A record-limit warning or failed probe can therefore be absent from the brief while present in the saved issues. Keep `ASSEMBLY_SANITY_PROBE_FAILED`, `RECORD_LIMIT_PROBE_FAILED` and `RECORD_LIMIT_TRUNCATION` attached to any downstream count or caption; retain the actual FASTA, whole-record or region-only input scope. Neither a readable brief nor a complete badge establishes whole-genome analysis.

Sources: `mamey/cli.py:2667–2696,3905–3921`, `mamey/package_inspector.py:276–301` and `mamey/render_brief.py:399–415`.

For a current mechanical check, validate a review copy and capture printed findings, workbook-content diagnostics and exit status. The workbook-content check is advisory unless `--workbook-strict` is supplied; a zero exit with a workbook warning does not mean every requested sheet is populated. See [storage and handoff](FILES_STORAGE_AND_HANDOFF.md) for exact writes and fingerprint limits.

For byte-preservation requirements, note that the normal validator refreshes the mutable package-status receipt. Keep the original source/hash record and capture validation output externally; [validation write scope](POSTSEAL_READERS.md#validation-can-update-a-mutable-status-receipt) explains the distinction. Checklist COMPLETE cells and archive existence do not replace this validation or prove authored interpretation.

## Analysis-forward completion hints

`ANALYSIS_FORWARD` is a generated review/worklist snapshot. Its current COMPLETE/PENDING hint tests two manifest fields for nonempty values; it does not verify current-profile cards, the authored register or the expected region roster. Its JSON sidecar still records `mode_b_complete=0`. Preserve both observed values and resolve them against actual card/register/gate evidence. Empty manifest judgment fields do not prove later authored work is absent.

The terse board and `mode=full` legacy eight-section scaffold do not implement a finished current Full Mode B card. Generated trigger phrases express possible requests; follow the actual user's authorized scope before acting. See [analysis-forward and entry-page contracts](reference/06_CURRENT_SOURCE_SCOPE.md#plumbing-part-6-analysis-forward-and-package-entry-snapshots).

## Quick-list selection and full inventory

`list-bgcs` reads the package's single native triage board. By default it excludes rows with a nonempty `Primary_metab_flag` or `Standing_rule`; its displayed count is a selected view, not a raw-region census. To include those rows, use:

```bash
python mamey_run.py list-bgcs "$PACKAGE" --json --include-dropped
```

Keep the full admitted board and manifest count alongside any shortlist. The reader validates all input row identities before applying selection, so a hidden invalid row can still block the command. Selected rows retain `strain / full node-or-contig / region / BGC alias`; the JSON is a projection of that board, not an independent evidence review or checksum validation.

Current `--axis` choices are `rank`, `ab` and `af`. `rank` keeps board order; `ab`/`af` sort their numeric score fields before `--top`. Use a positive integer for `--top N`, or omit it for no top limit. The current helper treats zero as no limit and negative values as Python tail-excluding slices rather than refusing them. It also treats any nonempty flag text as true, so a hand-edited `NO`/`False` flag can remove a row. Preserve the native board and reconcile malformed flags rather than silently recoding source evidence. Routing scores and selected order do not establish measured activity or product identity.

Sources: `mamey/package_inspector.py:344–348,388–438,441–477`, `mamey/cli.py:7136–7147`.
