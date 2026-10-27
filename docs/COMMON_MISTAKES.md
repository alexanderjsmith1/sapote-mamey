# Troubleshooting a Sapote–Mamey run

Find the symptom below and check its evidence before retrying. If this is your first run, use the [walkthrough](MASTER_WALKTHROUGH.md).

## Quick diagnosis

| What happened? | Start here |
| --- | --- |
| Input rejected, or no BGC regions found | [Check the input archive](#the-input-is-rejected-or-no-regions-are-found) |
| Import error or command not found | [Check the Python environment](#missing-python-package-or-wrong-python) |
| Missing genome FASTA or reference dataset | [Find the required input](#a-genome-or-reference-file-is-missing) |
| Blank KCB, RiQ or JSON fields | [Check evidence availability](#missing-kcb-riq-or-json-evidence) |
| Run is quiet or stopped midway | [Check the process and phase receipts](#run-appears-stalled-or-was-interrupted) |
| Retry or resume refuses a destination | [Check the existing output](#batch-resume-refuses-an-existing-package) |
| Validation returns zero, but something is missing | [Read the individual checks](#a-validation-or-seal-command-returns-zero) |
| `explain` finds no manifest | [Point it at the package folder](#explain-finds-no-manifest) |
| A `strain-master` command prints `REFUSED` | [Read the refusal code](#a-strain-master-command-is-refused) |
| Workbook, PDF or transferred package looks wrong | [Workbook](#workbook-missing-incompatible-or-changed-after-validation), [PDF](#pdf-missing-clipped-or-confusing) or [transfer](#package-fails-after-transfer-or-files-seem-missing) |

## Collect a useful problem report

Save the exact command, exit code and error text. Record the bundle version from `BUILD_STAMP.txt`, operating system, Python interpreter/version, input filename and SHA-256, and output path. Include the issue log, manifest and relevant phase/validation receipt when present; a failure before intake may produce none of them.

Check identifiers and local paths before sharing a report. Keep the failed attempt so a replacement does not erase the evidence needed to diagnose it.

## The input is rejected or no regions are found

**Check:** use `python mamey_run.py inspect '/path/to/input.zip'` on the intended archive. Mamey needs antiSMASH results; a raw assembly or the program's code ZIP is a different input. An empty upstream result is also possible, so keep the antiSMASH log and settings.

**Next step:** recover the complete existing antiSMASH export, or arrange the upstream analysis separately. See [which inputs are consumed](ANTISMASH_INPUTS_CONSUMED.md). A filename alone does not establish archive contents.

## Organism is a dot, blank or an unverified placeholder

**Check:** inspect the full-genome GenBank DEFINITION and accession metadata. A dot or `sp.` is unresolved taxonomy, not a genus or isolation habitat.

**Next step:** supply taxonomy supported by that source, keeping its provenance. `TAXONOMY_PLACEHOLDER` means the run rejected an obvious placeholder; passing that check does not verify the taxonomic assignment. A corrected run does not repair an older package.

## Missing KCB, RiQ or JSON evidence

**Check:** read channel statuses and the issue log. Blank fields can mean absent upstream analysis, missing files, parser limits, a failed scan or no retained match.

**Next step:** compare the original TXT/JSON evidence with the chosen `--json-evidence` mode. `off` skips the main evidence walker; other record/metadata paths can still read JSON. `bounded` and `full` have different limits. Use [input consumption](ANTISMASH_INPUTS_CONSUMED.md) for those limits instead of increasing a budget blindly. Keep unavailable, failed, unrun and evaluated-no-hit states distinct.

## Missing Python package or wrong Python

**Check:** confirm the active interpreter and program folder. An inactive environment can cause `No module named ...` even when another Python has the dependency.

**Next step:** follow [installation](INSTALL.md) for the selected environment and optional workflow. Use `python -m pip` so installation targets the same interpreter. A missing optional tree program does not block every extraction.

For a capability report, use `doctor` in a working installation. Read its [write-probe boundary](INSTALL.md#doctor-scope-and-write-probe) first. If `runs/_doctor_probe` already exists, doctor leaves it alone and reports a blocking write failure. Look inside it, move it out of `runs/` (keep it), then run doctor again. Capability detection does not verify the input or execute every optional tool.

## A genome or reference file is missing

**Check:** use [the task-input table](COMPANION_FILES.md#inputs-for-the-selected-task)
to identify the exact file the command needs. Look in the existing project inventory
and, if configured, [the Strain Master](DATA_HOME.md#looking-for-data-before-making-any).
A reference index is not a substitute for reference GBKs or proteins.

**Next step:** if a genome FASTA is missing, inspect the existing antiSMASH ZIP's
`input/` member and use [the recovery helper](COMPANION_FILES.md#recover-a-genome-from-an-antismash-zip)
when it has exactly one supported genome file. For a reference dataset, compare the
reported path with [the dataset's variable and probe](EXTERNAL_ASSETS_GUIDE.md#how-the-engine-finds-an-asset-once-it-is-present),
then read that consumer's requirements. Keep an unavailable input recorded as
uncomputed evidence while resolving it.

## Command options are rejected

Read `python mamey_run.py COMMAND --help` for the loaded version. Quote paths containing spaces. Compare the rejected option with the current guide; old release notes may use a different interface.

## Reusing a run destination

A direct run writes into `<outdir>/<strain>/package`. The active-package lock prevents simultaneous writers; it does not protect every file from a later run or remove stale outputs.

Keep the previous directory and use a fresh output root for a replacement. Check actual files after a refusal: early directories or receipts may already exist. Leave locks in place while establishing whether their process is still running.

## Run appears stalled or was interrupted

**Check:** inspect the process and latest phase receipt. A quiet terminal alone does not establish a hang; parsing and rendering time depend on the input and computer.

**Next step:** if the process stopped, retain logs and partial outputs before diagnosing a new attempt. General extraction does not resume from every interrupted phase. Do not start a competing writer or remove a lock based only on elapsed time.

## A validation or seal command returns zero

Read the named results, not just the exit code:

- `validate` reports package checks and `WORKBOOK_CONTENT` separately. Workbook findings block its exit only with `--workbook-strict`; manifest-contract checking is advisory. `NOT_EVALUABLE` means the evidence required for that check was unavailable.
- Default validation writes mutable `package_status.json`. A failed receipt write is reported separately and does not itself change the computed validation result. Use a working copy when the original must remain byte-identical.
- `seal-package` writes QC receipts to the package by default; an external `--out` keeps the review receipts separate. `--advisory` can return zero with blocking findings. Read each gate's status and blocking flag.

These are engineering checks. Review interpretation and release readiness separately.

## Batch resume refuses an existing package

`RESUME_BINDING_HOLD` means the harness found an earlier package or success for that input and could not match it to its exact run and output-tree bindings. It also appears when `--resume` was not given. `--resume` skips a matching completed attempt; it does not continue arbitrary partial extraction.

Later validation or enrichment can change mutable receipts and invalidate an earlier tree binding. Keep both records and establish what changed. Preserve the existing package, registry and receipt before selecting a replacement destination; a verified skip is not a new run or measurement.

## Explain finds no manifest

**Check:** `explain` reads one package folder. It exits 1 with `ERROR: no manifest.json or manifest_short.json found in <path>` when that folder holds neither file. A manifest that cannot be parsed first prints `[WARN] could not read ...`, then the same error. A path that is not a folder, such as the input ZIP, exits 1 with `ERROR: not a directory: <path>`.

**Next step:** give `explain` the package folder, `runs/<ID>/package`, not the run root `runs/<ID>` or the ZIP. `explain` never re-runs extraction, so it cannot replace a missing manifest. A package folder without one is incomplete; see [interrupted runs](#run-appears-stalled-or-was-interrupted).

## Validation passes but interpretation is unfinished

Check [Reading your results](READING_YOUR_RESULTS.md). Extraction, evidence coverage and authored interpretation have separate completion states. A Mode B scaffold is not a finished card; `PASS_STRUCTURE` does not verify literature or compound identity. If a card was not persisted, inspect [the ingestion route and branch-specific receipt](reference/06_CURRENT_SOURCE_SCOPE.md#card-ingestion-and-recovery-receipts).

Identify the missing evidence or writing task and its selected profile. Supply the full locus identity and required source files. A manifest names evidence files but does not contain all of them.

## Workbook missing, incompatible or changed after validation

Keep the workbook warning, check `openpyxl` in the selected environment and identify the target schema. Use its documented ingestion route rather than forcing a writer onto an incompatible master. When a run prints `cumulative_master_workbook: FAILED`, follow its `recovery:` line: submit the sealed package ZIP to the Strain Master with `strain-master submit`, then `verify` with a different `--chat` id, then `apply` ([the one way in](DATA_HOME.md#the-one-way-in); refusal codes under [A Strain Master command is refused](#a-strain-master-command-is-refused)).

Keep the per-strain package independent. Make manual annotations in a separate working copy, and use the matching source version to revalidate supported package updates.

## PDF missing, clipped or confusing

Inspect the render log and actual pages. Missing libraries, timeouts and successful-but-unreadable layouts need different remedies.

Use the CSV/workbook while diagnosing the presentation. Re-render into a review destination and inspect the result at its intended size. Brief text can flow onto additional pages; appended figure layouts have their own limits.

## A Strain Master command is refused

A refused `strain-master` request prints `REFUSED <CODE>: <reason>` and exits 2. A failing `check` exits 1 instead. Files enter a master through `submit`, then a second reviewer's `verify`, then `apply`. See [the one way in](DATA_HOME.md#the-one-way-in).

- `NO_MASTER` means no master folder was found. Give `--master <folder>` or set `SAPOTE_STRAIN_MASTER` to a folder that already exists. A path that does not exist counts as no master. `init` and `adopt` need `--master` itself; they do not read the variable.
- `SELF_VERIFY` means `verify` was given the submitter's own `--chat` id. Letter case does not make two ids different. A second reviewer runs `verify` with a different `--chat` id.
- `INBOX_REQUIRED` is the default answer to `strain-master store`. Use `submit`, `verify` and `apply` instead; the message calls the last step `import`, and the command is `apply`. `store` runs on its own only when the master's `strain_master.json` sets `"direct_store": true`. That setting is for a single-person master.

`where` does not refuse. Without a master it exits 0 and reports `NOT_CONFIGURED` or `MASTER_NOT_FOUND` as its status.

## Package fails after transfer or files seem missing

Compare the source and transferred ZIP SHA-256 values. Transfer the complete archive, extract into a fresh folder and validate with a compatible environment. Local browser restrictions can affect HTML navigation without indicating corruption.

Keep both copies, identify the failing checksum/path/schema, and recopy from the known source when the transfer is incomplete. See [Files, storage and handoff](FILES_STORAGE_AND_HANDOFF.md). Resealing is not a repair for unexplained byte changes.
