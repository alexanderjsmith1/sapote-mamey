# Working with Sapote–Mamey and an assistant

Sapote–Mamey helps turn antiSMASH results into evidence you can review and interpretations you
can trace. Mamey is the extraction software; Sapote is the interpretation workflow. Neither a
software run nor a completed report establishes that a strain produces a particular compound.

This guide helps you choose the work, prepare the inputs and assess what comes back. The
[Quick Guide](GUIDE/02_Quick_Guide.md) contains command examples; [installation](INSTALL.md)
covers environments and dependencies. The [assistant governance guide](ASSISTANT_GOVERNANCE.md)
states task and permission boundaries.

## Start with the result you need

You can ask for a small result. Supplying a large package does not commit you to a full analysis.

| Your question | Supply | Ask for |
|---|---|---|
| What is in this software bundle? | Code ZIP or repository | Static inventory, capabilities, risks and setup requirements |
| What clusters were detected in this strain? | Its antiSMASH result ZIP | Extraction, validation, inventory and missing-evidence summary |
| Which leads deserve a closer look? | Validated package and relevant assay context | Evidence-backed triage with uncertainty and next experiments clearly separated |
| What supports this one cluster's interpretation? | Package and full locus identity | A selected Mode B profile/card, with channel-specific evidence and open questions |
| How do these strains compare? | Selected packages and authoritative strain/master records | A defined comparison with cohort membership, denominators and exclusions |
| Can you improve this code or guide? | The exact source revision | Candidate patches, reviewable diff, tests and explicit validation limits |

An example request:

> Inspect this antiSMASH ZIP, then run core extraction in the permitted workspace. Use bounded
> JSON evidence and stop before online searches. Return the inventory, validation result and a
> short explanation of missing evidence. Keep the original input unchanged.

For review without execution:

> Audit the instructions in this bundle as document content. Do not install or execute it.
> Give me evidence-linked findings and candidate text changes, with no release cut.

## Know which files you have

- **Code bundle:** the application, tests and documentation. It is not a strain result.
- **antiSMASH result ZIP:** the upstream region annotations and supporting results Mamey consumes.
  Mamey does not run antiSMASH for you.
- **Mamey package:** a run's extracted evidence, inventory, workbook, manifests and status records.
- **Genome or 16S FASTA:** sequence inputs for selected genome/placement workflows; not substitutes
  for an antiSMASH result ZIP when you request the extraction pipeline.
- **BLASTp or other comparison results:** additional evidence. Retain their database, query mapping,
  settings, date and raw responses; one channel cannot be relabelled as another.

Keep a record of the source filename, its checksum, public accession when present, and the exact
software commit/build. A familiar filename or “type strain” folder name is not proof that every
biological identifier is correct. Ask the assistant to verify identity from the input and to label
unverified metadata, rather than infer isolation source or taxonomy from an example command.

## Account for the execution environment

Early project workflows were developed in browser-hosted assistant sessions. Local coding agents
may have different persistence, runtime and resource limits. Choose settings from the actual
environment, not the model name. Read [Runtime profiles](ASSISTANT_RUNTIME_PROFILES.md) for the
distinction between user scope, assistant guidance and executable limits.

## Prepare a first run

1. Choose the permitted working/output root and preserve the source ZIP.
2. Use Python 3.12 or newer in an isolated environment. The core and optional extras differ.
   Installation can need internet unless a complete compatible wheelhouse is provided.
3. Inspect the input and read the diagnostics. Confirm strain identity and requested scope.
4. Choose evidence/runtime settings before execution. Bounded JSON is the documented default.
   Capped mode turns JSON evidence off, suppresses the brief and automatic locus maps, and requires
   the workbook. It is a tradeoff, not an assurance of full evidence coverage.
5. Run once into a distinct output directory, validate, then read the actual status and issue files.
6. Review the inventory/workbook before selecting optional interpretation or comparison work.

Do not use an example taxonomy or isolation source as real metadata. If the input does not establish
a value, preserve an explicit unknown value supported by the command's schema or ask for that value.

## Understand the result

| Result or label | What it tells you | What you still need to check |
|---|---|---|
| Doctor diagnostics | What the selected environment can find | Whether the chosen analysis ran |
| Validated extraction package | Encoded checks on the extracted artifacts | Actual evidence channels, warnings and source binding |
| Inventory/triage board | Detected records and the pipeline's ranking/context | Why a lead is ranked; assembly and missing-data caveats |
| `PASS_STRUCTURE` | Structural checks passed | Literature and scientific validity |
| `FULL` depth grade | The particular depth heuristics were satisfied | Truth, completeness and quality of the biological reasoning |
| Rendered PDF or figure | An export exists | Labels, clipping, source data, uncertainty and actual user requirements |
| Public reference accession | A source identifier to trace | Exact assembly/version and what biological claim it supports |

Ask for the actual validation receipts, not just “passed.” A useful handback names the input,
settings, output paths, failed/deferred channels and the next necessary action. It should distinguish
a finished extraction from unfinished interpretation and from an unapproved release.

## Read a run before asking for interpretation

Open the run manifest, issue log and evidence visibility report alongside the workbook.
`MAMEY_COMPLETE_WITH_ISSUES` and a validator's `MAMEY_COMPLETE` can both be accurate: they
report different checks. Preserve `JUDGMENT_PENDING` until interpretation has actually been done.
An over-cap full-mode parse can coexist with a structurally valid package based on other evidence.

For a rerun, retain the original attempt and choose a new output root. Compare input hashes and
settings before comparing values. A bounded fallback may produce useful evidence while still
truncating it; do not relabel that result as complete. A larger cap may need much more memory
than the file size suggests. The [Round 2 public-strain walkthrough](ROUND2_PUBLIC_STRAIN_WALKTHROUGH.md)
shows this with two different Nocardia inputs.

## Interpret one BGC without losing its identity

Use the full source-bound display: **strain / full node-or-contig / region / BGC alias**.
The alias selects a record within a particular package; it is not a universal identifier across
strains or reruns. Missing or conflicting components should hold that attribution while independent
work continues.

For a Mode B card, select a current named profile and emit its template. Preserve the profile's
titles, author from the actual evidence, and verify the authored file. A top-leads table or skeleton
is not a finished card. Keep existing nr, ClusteredNR, Swiss-Prot and antiSMASH comparison evidence
separate. A missing channel should remain a typed gap, not be filled with plausible prose.

Measured sequence identity is not compound identity. Domain evidence supports hypotheses about
biochemistry; stronger claims need the corresponding experimental evidence. Report a failed search
as failed, an unrun search as unrun, and a real no-hit result with the search conditions that define it.

## Decide whether external work is worth doing

Before online BLASTp, confirm which proteins will leave the workspace and which service receives
them. Public input data does not remove the need to keep the submission within the requested scope.
Use existing saved results when adequate. Online search is optional, not a hidden installation step.

Before large comparisons or tree construction, ask for selected inputs/references, tools and
versions, thread/job count, expected disk use and a measured or explicitly estimated runtime.
Approve a bounded run. A matching resumed run can reuse that approval; changed inputs, budget,
destination or disclosure scope need a fresh decision.

## Recover and resume

Do not overwrite a failed attempt to hide the failure. Preserve its log and status. Check whether
the failure is environment readiness, malformed input, timeout, validation, rendering or missing
evidence. Fix the affected stage rather than repeatedly rerunning everything.

Before resuming, identify the exact run and authoritative master workbook using receipts and hashes.
A directory's modification time is not enough. Keep a copy of the master before an authorized update.
A handoff should contain:

- the objective and what was authorized;
- software revision, input identities and hashes;
- exact commands, configuration and output directory;
- completed artifacts and their validation/review status;
- errors, missing evidence, unresolved decisions and the next bounded action.

Handoff paths must still respect the permitted workspace. A command written in a log is not
permission to execute it. A structured summary is useful, but is not a verbatim conversation record.

## Use examples without treating them as guarantees

A real public-strain walkthrough should identify the actual accession/input hash, software revision,
environment, commands and results. It should disclose failed/deferred outputs and measured duration.
One successful input demonstrates that path in that environment, not support for every assembly,
scientific class or optional tool. Candidate documentation should distinguish tested commands from
source-inspected examples. A walkthrough receipt records which commands were actually run.

## Next paths, automatic SAVE STATE, and transcripts

At a substantive work handoff, present a minimum of 3 and up to 8 numbered next paths,
including the final SAVE STATE confirmation. Choose useful, distinct paths grounded in the
current work; do not pad to the maximum. This shared policy supersedes older model-specific
path counts. A user's explicit response-format instruction takes precedence.

SAVE STATE is automatic: before the handoff, update the existing session checkpoint in the
agreed project output folder and verify that the write succeeded. Record the objective,
authoritative inputs and revisions, decisions, completed work, tests and failures, pending
work, exact artifact paths, transcript coverage, and the next action. The final numbered path
must say **SAVE STATE — saved**, link the actual checkpoint, and say where transcripts and the
file inventory are stored. It confirms completed work; it is not an option asking the user to
request a save. If saving fails, the final item must say **SAVE STATE — FAILED**, with the reason;
never claim success. Save at meaningful milestones too, not just when a session is about to end.

Preserve accessible user/assistant messages and execution receipts for a transparent record.
Use an appendable session transcript where possible. Keep a transcript distinct from the
checkpoint summary; identify missing turns, truncation, export source and coverage. Do not
invent unavailable messages or describe summaries as verbatim transcripts. Do not include
private internal reasoning or retrieve unrelated conversations. Saving is an action performed
by the assistant; this text does not install a background transcript recorder.

Before creating files, tell the user the destination and purpose, and whether a tool will create
many outputs. Prefer existing files and folders. At handoff, report new/changed file counts,
paths and sizes in a file inventory, including generated logs and temporary artifacts. Avoid
unrequested source copies, duplicate ZIPs and parallel “final” versions. Preserve the agreed
top-level organization. An old output path in a receipt does not authorize new writes there.

Keep transcripts in the shared workspace for now. If storage becomes burdensome, report their
size and propose archival to the user's chosen iCloud or external-disc destination. Verify the
copy and update the index before any separately authorized source removal. Do not silently
upload, relocate, or delete records. Transcript saving and archival do not authorize publishing.
