# Read your Sapote–Mamey results

Start with your question: which region should I inspect, what evidence supports it, or what is missing?
Then open the run's **`*Complete_Package.zip`** (the filename includes strain, bundle, engine and
antiSMASH detection profile). antiSMASH is the separate program that finds biosynthetic gene
clusters (BGCs) in a genome and reports each as a region. Preserve the ZIP, extract a reading copy and open
`OPEN_ME_FIRST.html`. Use its links to reach the workbook and tables; keep the folder together.
You can read the HTML, workbook and tables without Python. A fresh software check needs the
configured environment; see [Saved summaries and current validation](#saved-summaries-and-current-validation).

Older packages may have an entry page that names one particular assistant, or a simpler
completion badge. That wording does not require a particular assistant. The current results
page separates the recorded statuses; older [sealed](GLOSSARY.md#evidence-identity-portability-and-authority-vocabulary) packages stay as they were. Use the files
below as the evidence.

## Open these in order

| File | What it is for | What to check |
|---|---|---|
| `OPEN_ME_FIRST.html` | Entry page and links | Correct strain and run; read the status details, not just the badge color |
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

Use the status field that answers your question:

| Recorded value | What it tells you | Next action |
|---|---|---|
| `MAMEY_COMPLETE_WITH_ISSUES` | Extraction reached completion with recorded issues | Read `issue_log.md` for the issue affecting your question |
| Validator `MAMEY_COMPLETE` | The package met the validator's encoded checks | Read evidence coverage and workbook diagnostics separately |
| `JUDGMENT_PENDING` | The saved interpretation state from the gold run (the default analysis mode) is pending | Look for separately authored work and its review record before writing a conclusion |

These values can coexist in one package: execution, checks and interpretation answer different questions.

| Evidence label | Read it as | Do not read it as |
|---|---|---|
| `MAIN_JSON_PARSE_HELD` | The main walker recorded JSON errors or skipped members; inspect their reasons and affected sources | No BGCs or no useful other evidence |
| `MAIN_JSON_WALKER_TRUNCATED` | The bounded walker stopped at a limit | Exhaustive JSON extraction |
| `UNKNOWN` | Completion was not established | No hits or successful full coverage |
| `NOT_SUPPLIED` / unavailable | Required input/channel was absent or unavailable | A negative biological result |
| Observed hit or match | Evidence under the recorded method and conditions | Confirmed compound identity or production |

## Practice reading a recorded row

The example below reports a bounded-mode package for *Nocardia brevicatena* NBRC 12119 with
55 region records. Use it to understand the fields, not as an expected result for your package.
The values here are a transcription of the guide's recorded example, not a newly measured run.
Its reported highest-ranked triage row is:

**NB_NBRC12119 / NZ_BAFU01000048.1 / region001 / BGC018**

The row records `Products = betalactone; other; terpene`, `Boundary = Edge`, `Arch = C`,
`Class_Conf = LOW`, `AB_auto = 54.0`, `AF_auto = 30.0`, and `Novelty_auto = 34.0`.
`AB` and `AF` mean antibacterial and antifungal; `Arch` is the
[architecture confidence grade](GLOSSARY.md#5-architecture-confidence-ae-and-the-three-confidence-axes).
Those numbers are pipeline scores. They are not percentages, probabilities, measured
antimicrobial activity, or proof of a new compound. The [Edge](GLOSSARY.md#4-edge-status) flag and low class confidence are
reasons to look at the underlying region before investing in a detailed interpretation. "other"
is an annotation category, not a reason to discard the record.

A good first question: what evidence supports this row, what might be missing at the contig
edge, and which interpretation would change if that evidence were available? A poor question:
asking the software to name the compound from the score.

## Counts, boundaries and assembly are different things

The same package reports 20 interior, 23 edge and 12 full-contig regions. The weighted count is
20 + 0.5 × 23 + 0.25 × 12 = **34.5**. That is the pipeline's boundary-weighted heuristic, not a
measurement of 34.5 pathways or compounds. The weights do not measure the fraction of a pathway
recovered: an Edge region is not necessarily half a cluster, and the statistic is not a proven
lower bound on distinct pathways. Raw regions can contain multiple protoclusters, and fragmented
pathways can span records. Report the raw count, boundary distribution, weighted statistic and
settings together; compare strains only with comparable input processing.

The assembly manifest separately reports **248 contigs** and **[N50](GLOSSARY.md#key-metrics) 102,039 bp**, with a
FRAGMENTED contiguity classification. The boundary-derived [POOR](GLOSSARY.md#bgc-inventory-and-fragmentation-tiers) label uses different evidence.
Do not call the whole assembly "poor" from the region-boundary label alone without looking at
contiguity.

## Decide what to investigate next

- For a figure handoff, inspect existing `gold_figures/` and `locus_maps/` where present, choose the figure roster with [Make and review figures](FIGURES_START_HERE.md), then use [Evidence to report](EVIDENCE_TO_REPORT.md) for captions, short findings and Methods facts. A [Mode B](GLOSSARY.md#14-mode-b) card is an optional selected format.
- Review a selected region's genes, domain support and reference matches, keeping the full identity.
- For an edge or full-contig region, inspect candidate links and competing fragment explanations.
- Treat assay observations as strain/extract context; do not assign them to a locus without evidence.
- Author a Mode B interpretation only after you have chosen the question, the available evidence and the named profile.

Online searches and BLASTp (protein similarity) searches are optional follow-up. These walkthroughs do not need them. Leave a
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

Choose a region in your existing package. Use [the nine recorded Type Strain cases](TYPE_STRAIN_WALKTHROUGHS.md)
as reading examples. Copy **strain / full node-or-contig / region / BGC alias** from one bound
record in your run, join its triage row to exactly one inventory row, and confirm the source
region GenBank exists. BGC aliases and ranks can change between runs; a remembered alias alone
is not enough.

Read the fields in this order:

| Question | Evidence to inspect | What stays uncertain |
|---|---|---|
| Which sequence was analyzed? | Input hash, full contig/region locator, inventory coordinates | A display name alone cannot establish identity |
| How well is the region recovered? | Boundary label, contig length, gene/domain architecture | Interior does not prove every pathway component is present |
| Why was it prioritized? | AB/AF/novelty scores, lead tier and recorded triggers | Scores are not calibrated probabilities or assay measurements |
| What does it resemble? | [KCB](GLOSSARY.md#2-kcb--knownclusterblast) (KnownClusterBlast)/reference identifiers, coverage and architecture | A top retained hit does not prove product identity or an exhaustive search |
| Which evidence is missing? | Per-channel status, truncation and issue records | Missing data must not become a biological negative |
| What claim can be written? | Source-bound observations, alternatives and claim limits | Production and activity need appropriately linked experiments |

Example: a retained high-priority region with an edge boundary and a named KCB hit can justify
investigating a related biosynthetic capacity. It does not justify "this strain produces that
named compound", however large the number beside the hit. Write down the sequence observation,
why it matters, the competing explanation, and the evidence that would separate them.

### Read a zero in its recorded scope

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

Save this as a review note. If you want an authored Mode B card, follow
[Write and review one Mode B card](MODE_B_USER_WALKTHROUGH.md) to choose the profile, prepare
the evidence, emit and author its template, then verify the saved card. Keep missing evidence
explicit; a required section does not justify invented detail.

For damaged or confusing results, see [Troubleshooting](COMMON_MISTAKES.md). To keep and
transfer the evidence, see [Files, storage and handoff](FILES_STORAGE_AND_HANDOFF.md).

## Saved summaries and current validation

Use `explain` for a quick reading of saved summaries, then return to the source files for your
question. It does not rerun extraction or validation. Its lead labels are bound to the
same-package native triage board; missing or conflicting identity produces `IDENTITY_HOLD`.
Resolve that hold in the source records before citing a lead.

`explain` shows at most five warnings, each shortened to 100 characters. For coverage questions,
read the full `issue_log.md` and `manifest.json`: `manifest_short.json` omits assembly-sanity,
record-cap and metric input-universe details. A missing issue log does not establish a clean run.
The generated brief also shows selected warnings rather than the full issue list. When reporting
counts, carry forward `ASSEMBLY_SANITY_PROBE_FAILED`, `RECORD_LIMIT_PROBE_FAILED` or
`RECORD_LIMIT_TRUNCATION` where recorded, and say whether the input was FASTA, whole-record or
region-only.

If you need a fresh mechanical check, validate a review copy and retain the printed findings,
`WORKBOOK_CONTENT` diagnostics and exit status. Workbook content is advisory unless
`--workbook-strict` is supplied. The normal validator refreshes `package_status.json`; preserve
the original package/hash and capture new output separately. See
[validation write scope](POSTSEAL_READERS.md#validation-can-update-a-mutable-status-receipt)
and [storage and handoff](FILES_STORAGE_AND_HANDOFF.md). Checklist COMPLETE cells and a readable
brief do not replace these checks or establish authored interpretation.

## Analysis-forward completion hints

`ANALYSIS_FORWARD` is a generated review/worklist snapshot. Its current COMPLETE/PENDING hint tests two manifest fields for nonempty values; it does not verify current-profile cards, the authored register or the expected region roster. Its JSON sidecar still records `mode_b_complete=0`. Preserve both observed values and resolve them against actual card/register/gate evidence. Empty manifest judgment fields do not prove later authored work is absent.

The terse board and `mode=full` legacy eight-section scaffold do not implement a finished current Full Mode B card. Generated trigger phrases express possible requests; follow the actual user's authorized scope before acting. See [analysis-forward and entry-page contracts](reference/06_CURRENT_SOURCE_SCOPE.md#plumbing-part-6-analysis-forward-and-package-entry-snapshots).

<a id="quick-list-selection-and-full-inventory"></a>

## Use the CLI to browse the triage board

For this optional CLI view, activate the configured environment and work from the program
folder containing `mamey_run.py`; see [Install](INSTALL.md) if you need setup. Replace the path
below with your extracted reading-copy directory, then choose a view:

```bash
PACKAGE='/absolute/path/to/extracted/package'
# First five retained rows, sorted by AB score:
python mamey_run.py list-bgcs "$PACKAGE" --axis ab --top 5
# All board rows, including recorded exclusions, as JSON:
python mamey_run.py list-bgcs "$PACKAGE" --json --include-dropped
```

The first command helps choose what to inspect; the second helps reconcile the shortlist with
the native board and source inventory. By default, `list-bgcs` hides rows with nonempty
`Primary_metab_flag` or `Standing_rule`, so its displayed count is not a raw-region census.
`rank` keeps board order; `ab` and `af` sort their respective numeric scores before `--top`.
Scores describe priority, not measured activity or product identity.

Use a positive integer for `--top`, or omit it for no limit. Zero or a negative number is
refused with exit code 2. Any nonempty flag text counts as true, including
hand-edited `NO` or `False`. Preserve the native board and resolve malformed flags rather than
silently recoding them. Identities are checked before selection, so an invalid hidden row can
block the command. JSON rows retain the complete locus identity but are a reading projection,
not an independent evidence review or checksum check.
