<!-- Mirror of docs/COMMON_MISTAKES.md, made by tools/sync_wiki_mirrors.py. Edit the source, then run: python3 tools/sync_wiki_mirrors.py --apply -->
# Troubleshooting a Sapote-Mamey run

Find the message you see below, then follow the fix. Keep the failed attempt. A
retry that overwrites it erases what you need to diagnose it.

To report a problem you need the command, the exit code, the last error line and
the output folder. The [recovery page](../docs/reader/04_RECOVERY_AND_LIMITS.md) explains
how to read `issue_log.md` and `run_phase_receipts.jsonl`, and lists every phase
status (`START`, `END`, `ERROR`, `FAIL`, `TIMEOUT`, `SKIP`, `WARN`). The
[first-run page](../docs/reader/01_FIRST_RUN.md) explains the exit codes. Terms such as
package, KCB and RG-GMCI are in the [glossary](Glossary.md).

## `run` exits 1 but a package exists

Open `issue_log.md` in the package folder. A line containing `[BLOCKING]`
is the cause. `run` exits 1 whenever the log holds one, whatever the status
string says. A `[WARN]` line does not change the exit code.

Fix the cause named on the line. Then run again into a new folder with `--outdir`.
Do not edit the package to clear the line.

## `ERROR: TAXONOMY_PLACEHOLDER: supply taxonomy bound to the source record...`

You passed `--taxonomy` with a value that is only punctuation, a bare `sp.` or
`spp.`, or the unfilled template text from `inspect` (for example
`'<Genus sp.>'`). `run` stops before it writes anything and exits 1.

Replace it with the genus and species from the GenBank record, such as
`--taxonomy 'Streptomyces sp.'`. If you cannot confirm it, pass
`--taxonomy 'not verified'`, or leave the flag out. `explain` then prints
"not verified". Do not guess a genus.

## `ERROR: SOURCE_PLACEHOLDER: replace the <isolation source> template text...`

You passed `--source '<isolation source>'` exactly as the template printed it.
`run` stops before it writes anything and exits 1.

Pass the isolation source as the record deposits it, or leave `--source` out.
`explain` then prints "not supplied". Do not paraphrase the text.

## A KCB column reads `KNOWNCLUSTERBLAST_NO_HITS_UNVALIDATED`

KCB is KnownClusterBlast, antiSMASH's comparison against known clusters. This
value means the KnownClusterBlast file was present and reported no hits for the
region. The read did not fail.

It is not a validated negative. The text was not checked against the JSON, and
no ClusterBlast hit is substituted for it. Do not read it as novelty or as proof
that no related cluster exists.

## Organism is a dot, blank or an unverified placeholder

The antiSMASH GenBank files often deposit the organism as `.`. Read the
DEFINITION line and the accession metadata, then pass `--taxonomy` and `--source`
to `run` as described above. An organism name is not an isolation habitat.

## KCB, RiQ or JSON evidence is missing

RiQ is the antiSMASH score for ribosomal peptide clusters. Read the channel
status and `issue_log.md`. `--json-evidence off` skips the main JSON walker, and
`bounded` parsing can reach its size limits.

KCB comparisons can come from the text files when there is no record JSON.
RiQ scores come only from the record JSON. When the JSON is absent, `inspect`
prints "NO — KCB comes from the TXT files; RiQ needs the JSON and will be
absent", and the RiQ cells stay blank. Check the original archive before you
request another analysis.

## Missing Python package or wrong Python

Activate the environment you installed into, then run `python mamey_run.py doctor`.
[Install](../docs/INSTALL.md) covers each missing package, and its
[doctor check](../docs/INSTALL.md#doctor-scope-and-write-probe) says what `doctor` tests.
A missing optional tree program does not block extraction.

## The input is rejected or no regions are found

```bash
python mamey_run.py inspect ~/Downloads/EXAMPLE.zip
```

Replace the path with yours. Use the full antiSMASH results archive, not a genome
FASTA or the Mamey code ZIP. If antiSMASH found no regions, read its log.
[Input contents](../docs/ANTISMASH_INPUTS_CONSUMED.md) explains partial archives.

## A genome or reference file is missing

Use [Companion files](../docs/COMPANION_FILES.md#inputs-for-the-selected-task) to find the
required input. An antiSMASH ZIP can hold the submitted genome, and that page
names the helper that extracts it. A reference index and a reference sequence
are different files, so check what the consuming tool needs.

## Command options are rejected

Quote paths that contain spaces. List the options the command accepts:

```bash
python mamey_run.py run --help
```

## `REFUSED: [lock] another mamey run is writing ...`

Another `run` holds the lock on `<outdir>/<strain>/.mamey.lock`. This run stops
with status `PACKAGE_LOCKED`, writes nothing and exits 1. Wait for the other run
to finish, or use a different `--outdir`.

The lock is advisory and covers `run` only. It is skipped on systems without
POSIX file locks (Windows) and when the folder is read-only. Where it is skipped,
nothing stops two commands writing to one package, so check that no other command
is still running on it.

## Other `REFUSED:` lines from `run`

A terminal line that starts `  REFUSED:` is a check made before any work. A
bracket names the reason: `[strain]` for an unsafe strain name, `[outdir]` for an
output folder inside the bundle itself. Nothing was written, and the
exit code is `2`. Fix the value the line names and run again. The `[lock]` line
above is different: it exits 1.

## Run appears stalled or was interrupted

Check for a live process, and read the last lines of `run_phase_receipts.jsonl`:

```bash
ps aux | grep mamey_run
tail -n 5 runs/EXAMPLE/package/run_phase_receipts.jsonl
```

A `START` line with nothing after it for that phase means the run stopped there
or is still going. The other statuses mean different things. The
[recovery page](../docs/reader/04_RECOVERY_AND_LIMITS.md#find-what-failed) has the table.
Keep the partial outputs.

## `validate` exits 0 but the workbook looks wrong

`validate` reports the main result and the workbook check
separately. Read the `WORKBOOK_CONTENT` line. Without `--workbook-strict`, a
missing or invalid workbook still exits 0. Add `--workbook-strict` to make it
fail.

If the output shows `package_status_receipt_write: FAILED`, the saved status was
not refreshed. Keep the terminal result.

## `RESUME_BINDING_HOLD`

This comes from the batch tool `tools/intake_harness.py --resume`. You will not
meet it on the single-run path. The existing package does not match the recorded
run, or you did not pass `--resume`. Use a fresh output folder and registry.
Resume skips a finished attempt that matches. It does not continue a partial
extraction. See the [batch guide](../docs/INTAKE_BATCH_AND_SMALL_N_DIRECTIVES.md).

## `explain` finds no manifest

Give `explain` the folder that holds `manifest.json`. Do not give it the input
ZIP or the parent run folder:

```bash
python mamey_run.py explain runs/EXAMPLE/package
```

Use your own strain name. If the package has no readable manifest, check the
failed run. Do not create one by hand.

## `validate` passes but `gold_completeness` says `JUDGMENT_PENDING`

You see this value as `gold_completeness` in the `validate` output. It means
extraction finished and the written interpretation does not exist yet. Choose a
[Mode B profile](../docs/MODEB_PROFILE_MATRIX.md) and follow the
[authoring guide](../docs/MODE_B_USER_WALKTHROUGH.md). [Reading your
results](../docs/READING_YOUR_RESULTS.md) explains the other fields.

## Workbook missing, incompatible or changed after validation

Read the workbook warning and check that `openpyxl` is installed in the active
environment. Keep your annotations in a review copy. If a cumulative-master update
fails, follow the recovery line it prints and the
[data-home guide](../docs/DATA_HOME.md#the-one-way-in).

## PDF missing, clipped or confusing

Read `issue_log.md` and the renderer's warning. Compare each PDF page with the
table it was built from, and look at every page before you send it. For figures,
see [figure help](../docs/FIGURES_START_HERE.md).

## `REFUSED <CODE>: ...` from `strain-master`

`strain-master` manages the strain data folder (the master). A refusal prints
`REFUSED <CODE>: <reason>` and exits 2. The [data-home guide](../docs/DATA_HOME.md#the-one-way-in)
explains the steps: `submit`, then `verify`, then `apply`.

| Code | Cause and fix |
|---|---|
| `NO_MASTER` | No master folder. Give `--master`, or set the environment variable the message names, to an existing folder. |
| `OCCUPIED` | `init` was pointed at a folder that exists and is not empty. Use an empty or new folder. To use an existing master, run `adopt`. |
| `BAD_ID` | The `--chat` value is not a short id. Use letters, digits, `.`, `_` and `-` only. |
| `INBOX_REQUIRED` | Files enter a master only through `submit`, then `verify`, then `apply`. |
| `BAD_STATE` | The submission is not in the `SUBMITTED` state, for example it was already verified. |
| `SELF_VERIFY` | `verify` used the same `--chat` id as `submit` (case ignored). Pass a different `--chat` id. |
| `NEED_CHECKS` | `verify` needs `--checks` saying what you ran. To accept, number every checklist item in it. The message lists the missing numbers. |
| `CANNOT_ACCEPT` | The tool's own checks failed, so the submission cannot be accepted. The message lists the problems, such as a staged file or its source that changed, or a target not in `LAYOUT.md`. Fix them, or return the submission. |

## Package fails after transfer or files seem missing

Compare the checksums of the original and the transferred ZIP. Extract into a
fresh folder. Keep the package files together so links resolve. If bytes changed,
copy the original again. Do not reseal altered files.

## Send a useful problem report

Send the command and the error as text. Add the Python and bundle versions, the
input file name and checksum, the output location and the issue log.
