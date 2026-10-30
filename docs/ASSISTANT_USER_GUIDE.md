# Work with an assistant

Ask an assistant to run an antiSMASH ZIP, read an existing package, or write from
selected results. Supply the input, the question and where to save the work.
Start small; a large package does not require a full analysis.

For a first run, use the [walkthrough request](MASTER_WALKTHROUGH.md).
For other work, use [Choose a task](USER_TASK_ROUTER.md). The companion
[task-routing JSON](USER_TASK_ROUTER.json) gives an assistant the same routes.

## Ask for a result

An extraction request can be simple:

> Inspect my EXAMPLE antiSMASH ZIP, run extraction and validate the package.
> Return the region inventory, output paths and any errors. Keep the original
> ZIP unchanged and stop before online searches.

For existing results:

> Read runs/EXAMPLE/package and explain the main observations in two to four
> sentences. Link each claim to its source row, separate observations from
> interpretations, and list the missing evidence that could change the answer.
> Save the draft in reviews/EXAMPLE/ so I can review it.

For a document-only review, say that directly: “Read the guide and propose
changes; do not install or run the software.” Use the
[assistant governance guide](ASSISTANT_GOVERNANCE.md) for permission boundaries.

## Supply the right files

The **code bundle** contains the program. An **antiSMASH result ZIP** contains
its upstream annotations; Mamey reads these results rather than running antiSMASH.
A **Mamey package** contains the extracted inventory, workbook and other evidence.
Genome/16S FASTA files serve the separate genome and placement tools.

Keep the original filename, checksum, public accession and software revision
with the request. Copy taxonomy and source metadata from a real record; leave
unknown values unknown. For external search results, include the query mapping,
database, settings, timestamp and raw responses.

Follow [installation](INSTALL.md), then inspect and run using the first-run
page. Use the actual machine's limits; [runtime profiles](ASSISTANT_RUNTIME_PROFILES.md)
explain the alternatives. Capped mode suppresses JSON evidence, the brief and
automatic locus maps, so agree on that change before using it.

## Read what came back

Open the workbook, manifest and issue log. Use [Read one saved package](reader/03_READ_RESULTS.md)
for status labels and [Recovery](reader/04_RECOVERY_AND_LIMITS.md) for failed runs.
Ask for the actual output paths and check results, plus failed or unrun channels.

For one locus, use **strain / full node-or-contig / region / BGC alias** from the
source record. Follow [emit, author and verify](MODE_B_USER_WALKTHROUGH.md) for a
Mode B card. A template still needs interpretation, citations and review.
Keep sequence similarity, predicted chemistry and measured activity distinct
when writing the conclusion. The [external activity guide](AB_AF_EXTERNAL_ACTIVITY_CHANNEL.md)
covers supplied prediction documents.

For a report, ask for a short evidence brief, a claim-to-source table and review
questions. Each claim row should name the full locus, exact source record,
checksum, observation/inference and uncertainty. Record accepted, revised or
withheld wording after the review. The [evidence-to-report guide](EVIDENCE_TO_REPORT.md)
explains figures, captions and Methods facts.

If an LLM helps write the draft, keep its prompt, available model/version,
accessed sources and human edits. Leave unavailable details unknown. When a
source changes, check the affected claims again. Save the reviewed file separately
from its template, then use the card receipt workflow if persistence is requested.
Check any master-workbook update separately.

## Choose optional work

Before an online search, agree which proteins will be sent and to which service.
Use saved results when they answer the question. Before a large comparison or
tree run, select the inputs, tools, versions, thread/job count, disk budget and
estimated runtime. Recheck the plan when those inputs or limits change.

For figures, use [Make and review figures](FIGURES_START_HERE.md).
For a strain deck, use [Strain slides](STRAIN_SLIDES.md). Each route names its
inputs and the files to inspect afterward.

## Resume later

Keep failed outputs and logs. Fix the affected stage and choose a new output
folder for another attempt. Identify the run and master workbook by receipts
and hashes before updating them; keep a copy of the master.

Ask for one checkpoint listing the goal, agreed scope, source hashes, commands,
outputs, completed checks, errors and next action. The assistant's save-state
rules are in [AGENTS.md](../AGENTS.md#next-paths-automatic-save-state-and-transcripts).
Use the [public-strain walkthrough](ROUND2_PUBLIC_STRAIN_WALKTHROUGH.md) as an
example with its own inputs and recorded results.

<a id="start-with-the-result-you-need"></a>
<a id="know-which-files-you-have"></a>
<a id="account-for-the-execution-environment"></a>
<a id="prepare-a-first-run"></a>
<a id="understand-the-result"></a>
<a id="read-a-run-before-asking-for-interpretation"></a>
<a id="interpret-one-bgc-without-losing-its-identity"></a>
<a id="turn-evidence-into-a-report-you-can-review"></a>
<a id="decide-whether-external-work-is-worth-doing"></a>
<a id="recover-and-resume"></a>
<a id="use-examples-without-treating-them-as-guarantees"></a>
<a id="next-paths-automatic-save-state-and-transcripts"></a>
