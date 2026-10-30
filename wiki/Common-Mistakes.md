<!-- Mirror of docs/COMMON_MISTAKES.md, made by tools/sync_wiki_mirrors.py. Edit the source, then run: python3 tools/sync_wiki_mirrors.py --apply -->
# Troubleshooting a Sapote-Mamey run

Find the symptom below before trying another run. You need the command, the last
error and the output folder. Keep the failed attempt so a retry does not erase
what you need to diagnose it.

## The input is rejected or no regions are found

Check the input ZIP:

```bash
python mamey_run.py inspect ~/Downloads/EXAMPLE.zip
```

Replace the path with yours. Use the full antiSMASH results archive, rather than
a genome FASTA or the Mamey code ZIP. Read the antiSMASH log if it found no regions.
[Input contents](../docs/ANTISMASH_INPUTS_CONSUMED.md) explains partial archives.

## Organism is a dot, blank or an unverified placeholder

Read the GenBank DEFINITION and accession metadata. Supply taxonomy from that
record; leave it unknown when you cannot confirm it. An organism name is not an
isolation habitat.

## Missing KCB, RiQ or JSON evidence

Read the channel status and issue log. JSON `off` skips the main walker, while
bounded parsing can reach its limits. TXT files can supply KCB comparisons;
RiQ scores need JSON evidence even if the inspector's hint groups them together.
Check the original archive before requesting another analysis.

## Missing Python package or wrong Python

Activate the environment used to install this bundle. Follow [Install](../docs/INSTALL.md)
for missing packages and its [doctor check](../docs/INSTALL.md#doctor-scope-and-write-probe).
A missing optional tree program does not block core extraction.

## A genome or reference file is missing

Use [Companion files](../docs/COMPANION_FILES.md#inputs-for-the-selected-task) to find the
required input. An existing antiSMASH ZIP may hold the submitted genome; that
guide describes the recovery helper. Reference indexes and reference sequences
are different files, so check the consuming tool's requirements.

## Command options are rejected

Use the loaded command's help and quote paths with spaces. For extraction:

```bash
python mamey_run.py run --help
```

## Reusing a run destination

Use a new output folder for a retry. The package lock works only where the
operating system and filesystem support it; check for an active writer before
starting another command on the same package.

## Run appears stalled or was interrupted

Check the process and `run_phase_receipts.jsonl`. `TIMEOUT`, `FAIL`, `ERROR` and
`SKIP` describe different outcomes; a lone `START` does not tell you whether the
process is still running. Keep partial outputs and use [Recovery](../docs/reader/04_RECOVERY_AND_LIMITS.md).

## A validation or seal command returns zero

Read the main result and `WORKBOOK_CONTENT` separately. `--workbook-strict` makes
a missing or invalid workbook fail validation. If `package_status_receipt_write`
reports `FAILED`, the saved status was not refreshed; keep the terminal result.

## Batch resume refuses an existing package

`RESUME_BINDING_HOLD` means the earlier package does not match the recorded run
and output files, or resume was not requested. Compare the existing records and
use the [batch guide](../docs/INTAKE_BATCH_AND_SMALL_N_DIRECTIVES.md). Resume skips a
matching finished attempt; it does not continue every partial extraction.

## Explain finds no manifest

Give `explain` the folder containing `manifest.json`, not the input ZIP or the
parent run folder:

```bash
python mamey_run.py explain runs/EXAMPLE/package
```

Use your actual strain name. If the package has no readable manifest, check the
failed run rather than creating one by hand.

## Validation passes but interpretation is unfinished

`JUDGMENT_PENDING` means extraction finished and writing remains. Choose the
[Mode B profile](../docs/MODEB_PROFILE_MATRIX.md) and follow the [authoring guide](../docs/MODE_B_USER_WALKTHROUGH.md).

## Workbook missing, incompatible or changed after validation

Read the workbook warning and check `openpyxl` in the active environment.
Keep annotations in a review copy. For a failed cumulative-master update, follow
the printed recovery line and the [data-home guide](../docs/DATA_HOME.md#the-one-way-in).

## PDF missing, clipped or confusing

Read the render log and compare the pages with the underlying tables. Use the
same documented renderer when repairing the layout, then inspect its output.

## A Strain Master command is refused

Read `REFUSED <CODE>: <reason>`. `NO_MASTER` needs the correct master folder;
`SELF_VERIFY` needs a different reviewer; `INBOX_REQUIRED` routes files through
submit, verify and apply. The [data-home guide](../docs/DATA_HOME.md#the-one-way-in) explains those steps.

## Package fails after transfer or files seem missing

Compare the original and transferred ZIP checksums, then extract into a fresh
folder. Keep the package files together so links resolve. If bytes changed,
recopy from the original rather than resealing the altered files.

## Collect a useful problem report

Send the command and error as text, plus Python and bundle versions, input
filename and checksum, and output location. Include the issue log when available.
