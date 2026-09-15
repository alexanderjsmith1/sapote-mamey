# Troubleshooting a Sapote–Mamey run

Start with the symptom below. Keep the failed attempt, exact command and error message. Change one thing at a time and use a new output folder for a replacement run. An error is useful evidence; repeatedly rerunning over the same folder makes it harder to diagnose.

## Collect a useful problem report

Record the source version (`python mamey_run.py start`), operating system, selected Python (`python --version`), exact input ZIP name and SHA-256, command, output path, exit code and final error. Include `manifest.json`, `issue_log.md` and the relevant validation or phase receipt if they exist. These may contain sample identifiers and paths; review them before sharing. A crash before intake may produce no package, so do not search forever for a missing manifest.

Run `python mamey_run.py doctor` from the program folder to inspect capabilities. It does not prove every optional workflow works or that your biological input is valid. Start with [the walkthrough](MASTER_WALKTHROUGH.md) if the program has never run successfully.

## The input is rejected or no regions are found

A code ZIP, raw genome FASTA and antiSMASH result ZIP are different inputs. Inspect the actual ZIP with `python mamey_run.py inspect '/path/to/input.zip'`. Check whether it contains region GenBank files and the associated antiSMASH output. No detected regions can also be a real upstream result; do not diagnose every empty inventory as the wrong ZIP. Retain the antiSMASH log and settings. Running antiSMASH is an upstream task, not a hidden step that Mamey performs.

**Recovery:** obtain the intended full antiSMASH results from the existing source, or arrange an upstream analysis separately. Success means the inspector recognizes the expected records, followed by a reviewed run; a ZIP filename alone is not proof.

## Organism is a dot, blank or an unverified placeholder

Some public Type Strain archives have `ORGANISM  .` even when the full GenBank DEFINITION identifies the organism. Round 3 encountered ten such inputs. Older candidate code normalized the dot to `sp.`; that prevented a literal dot from spreading but did not resolve taxonomy.

**Recovery:** inspect the full-genome DEFINITION and available accession metadata, record the binding source, and supply that taxonomy explicitly. Do not invent a genus from an unrelated folder or use the GenBank SOURCE field as isolation habitat. If taxonomy cannot be resolved, use the explicit `not verified` state and describe the limitation.

The Round 4 candidate refuses punctuation-only or bare `sp.` taxonomy at run admission with `TAXONOMY_PLACEHOLDER`, before creating a run directory. This checks an obvious placeholder, not taxonomic correctness. Existing packages are not retroactively repaired. A corrected run belongs in a new destination.

## Missing KCB, RiQ or JSON evidence

Blank values can reflect unavailable upstream analyses, absent files, parser limits, a failed scan or no retained match. They do not uniquely diagnose an old antiSMASH version. Read the issue log and evidence status before choosing a remedy.

**Recovery:** preserve the original full ZIP. Compare its available TXT/JSON evidence with the selected `--json-evidence` mode. `off` deliberately omits JSON parsing; `bounded` limits work and can report truncation; `full` attempts full parsing within its separate guard. The candidate full-JSON cap is **80,000,000 uncompressed bytes per guarded JSON member**, not an 80 MB upload or whole-ZIP limit. Bounded mode has its own limits. Increasing the full cap does not remove them. See [input consumption](ANTISMASH_INPUTS_CONSUMED.md).

If `ijson` is missing, install compatible dependencies in the selected project environment using [INSTALL](INSTALL.md); do not assume a compatible wheel is bundled. Success means a new receipt documents the intended channel and scope. A nonempty score alone is insufficient.

## Missing Python package or wrong Python

`No module named ...` may mean the intended environment is inactive. Confirm the interpreter and program folder before installing anything. Use `python -m pip` in that environment so installation targets the Python running the program. Follow [INSTALL](INSTALL.md) for core requirements and optional extras. No network installation was tested in these offline walkthroughs.

**Recovery:** activate the correct environment, check capabilities again, then rerun only the relevant step. A missing optional tree binary does not prevent every extraction. Do not copy a virtual environment from a different laptop as an installation method.

## Command options are rejected

Check `python mamey_run.py COMMAND --help`, replacing COMMAND with the actual command. Historical docs may show flags from another version. Keep the exact error and compare the loaded source version. A path containing spaces must be quoted. Do not replace working settings with a speculative command from an old release note.

## Run appears stalled or was interrupted

The terminal can be quiet during expensive stages. Check the process and the latest phase receipt before starting another copy. Runtime depends on evidence size, rendering settings, storage and the computer. Round 3's single-run times are observations, not a deadline.

**Recovery:** if a process is still running, inspect it before taking action. If it has stopped, retain its logs and partial directory. Start a new attempt in a distinct output location after diagnosing the cause; do not assume general extraction resumes automatically from every interrupted phase. A lock is not proof a process is dead. Do not delete locks or kill processes solely because progress is quiet.

## Validation passes but interpretation is unfinished

Execution, package structure, evidence coverage and authored interpretation answer different questions. Read [Reading your results](READING_YOUR_RESULTS.md). `MAMEY_COMPLETE_WITH_ISSUES` deserves issue review; `PASS_STRUCTURE` does not verify literature or product identity. A Mode B scaffold is not a finished interpretation.

**Recovery:** identify the exact missing evidence or interpretation task, its required files and scope. Ask for a review of a selected locus using its full identity. An upload of `manifest.json` alone does not transmit all the files it names. Do not trigger unrestricted online work simply to remove a pending status.

## Workbook missing, incompatible or changed after validation

Retain the workbook warning and check `openpyxl` in the selected environment. Existing master-workbook schemas can differ. Do not force a writer onto an incompatible workbook or edit a sealed workbook silently.

**Recovery:** keep the per-strain package independent, inspect the target schema and use its documented ingestion route. Work on a copy for manual annotation; keep that copy separate from the sealed evidence. Revalidate with the matching source version after a supported package update.

## PDF missing, clipped or confusing

A rendering timeout, missing library and successful-but-unreadable PDF are different failures. Inspect the render log and open the actual pages. The Round 4 candidate changes the text summary to wrap long content and continue onto additional pages; other appended figure renderers retain their own limitations.

**Recovery:** use the CSV/workbook and full identity while diagnosing the figure. Re-render into an explicit review destination; do not overwrite a sealed package casually. Never treat a successfully created PDF as publication-ready without visual review. A variable page count is expected.

## Package fails after transfer or files seem missing

Compare the transferred ZIP's SHA-256 with the source copy before extraction. Transfer the complete archive, not only the manifest, workbook or PDF. Extract to a fresh folder and validate that package with a compatible program environment. Browser restrictions can affect local HTML navigation without proving data corruption.

**Recovery:** preserve both copies, identify the specific checksum/path/schema failure, and recopy from the known source if transfer was incomplete. See [Files, storage and handoff](FILES_STORAGE_AND_HANDOFF.md). Do not reseal a damaged package merely to make checks pass.
