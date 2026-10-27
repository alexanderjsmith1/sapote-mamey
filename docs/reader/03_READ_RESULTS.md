# Read one saved package

Already have a `*Complete_Package.zip` or its extracted folder? Start here.
The outcome is a short review note grounded in the saved evidence; a new extraction
is not the default next step.

## 1. Find the package and preserve its identity

Use an existing reading copy, or extract the saved ZIP into a review folder.
Find the directory containing `manifest.json`; keep its linked files together.
Preserve the original ZIP and record its path and SHA-256. Separately record the
input checksum and program versions declared in the manifest: the input checksum
and the result ZIP checksum identify different objects.

Open `OPEN_ME_FIRST.html` if present. If local links are blocked, open the files
through your file browser. You can read the HTML, CSVs and workbook without Python.
Keep sorting, annotations and any later commands away from the original evidence;
see [files and handoff](../FILES_STORAGE_AND_HANDOFF.md).

## 2. Read the saved status before the rankings

| Open | Use it to answer |
|---|---|
| `manifest.json` and `issue_log.md` | Which input, settings and concerns belong to this run? |
| `gate_validation.json`, when present | What did the saved run/[seal](../GLOSSARY.md#evidence-identity-portability-and-authority-vocabulary) check report, including interpretation and evidence visibility? |
| `package_status.json`, when present | What mutable package-status receipt is currently stored? |
| `OPEN_ME_FIRST.html` | Where are the linked outputs, and which recorded states does this entry page display? |

The HTML is a snapshot, not a fresh check. A completed extraction, passing
mechanical checks, available evidence and reviewed interpretation are separate
questions. For example, `JUDGMENT_PENDING` does not mean extraction failed, and a
passing package check does not establish finished interpretation.

A missing issue log does not mean a clean run.

## 3. Follow one row back to its source

Open `[strain]_5_workbook.xlsx` for browsing, or the CSVs directly:

- `[strain]_4_triage_board.csv` helps choose a region to inspect.
- `[strain]_2_inventory.csv` supplies its recorded boundary, coordinates and annotations.

Replace `[strain]` with the actual label. Match the selected triage row to one
inventory row, then retain **strain / full node-or-contig / region / BGC alias**
(BGC: biosynthetic gene cluster) from the same package. Locate the source region record and retain its
path or archive-member locator and SHA-256. If identities conflict or the source
cannot be found, record that hold before attributing evidence to the region.

Scores order attention; they are not activity measurements or probabilities.
A reference match suggests similarity, not an identified product. An [Interior](../GLOSSARY.md#4-edge-status)
boundary does not prove a complete pathway, and a strain-level assay result does
not by itself identify the responsible locus.

## 4. Separate a gap from a negative finding

Read each channel's recorded status and scope, including parser limits and errors.

| What the record establishes | What to retain |
|---|---|
| Input absent or unavailable | The missing input/channel; no biological negative |
| Operation unrequested or not run | No computed finding for that operation |
| Failure, hold, truncation or unresolved binding | The reason and affected scope; any retained partial evidence |
| Completed scoped check with zero results | The performed check, database/input scope and zero; no claim of universal absence |

Blank cells alone do not distinguish these cases. Use the channel receipts and
full issue log; a short summary can omit warnings. Consult
[the detailed result-reading guide](../READING_YOUR_RESULTS.md#saved-summaries-and-current-validation)
before proposing a rerun.

**Example review note (made up; copy your own states and paths):**

~~~text
Package: <existing review-directory path>
Result ZIP SHA-256: <actual checksum to record>
Saved validation: receipt available; no fresh check made in this review
Selected channel: NOT_MEASURED
Locus: not selected
Decision: retain the evidence gap; inspect existing inputs before requesting new work
~~~

## 5. Save the review, or request a fresh check

Save the question, package/input bindings, selected row identity, observations,
receipt dates, unresolved evidence and one useful next action. Keep the original
records alongside it. Files authored after the ZIP was created may sit separately;
check the handoff inventory before concluding they are missing.

If fresh mechanical validation is part of the requested review, use a compatible,
configured bundle and an identified writable review copy. From the bundle root:

~~~bash
PACKAGE='/absolute/path/to/review/package'
python mamey_run.py validate "$PACKAGE" --workbook-strict
~~~

This command can refresh the copy's `package_status.json`; it does not automatically
replace the saved `gate_validation.json`. Capture stdout, stderr and the exit code
outside the package, and inspect both the package result and `WORKBOOK_CONTENT`.
The strict option makes a missing or nonpassing workbook check affect the exit;
ordinary workbook findings are advisory. A successful exit remains a scoped
software result, not scientific acceptance.

See [validation write scope](../POSTSEAL_READERS.md#validation-can-update-a-mutable-status-receipt)
before running it. For a failure or an interrupted attempt, preserve the evidence
and follow [Recovery and limits](04_RECOVERY_AND_LIMITS.md); do not repair a receipt or
overwrite the original package to make its status look complete.
