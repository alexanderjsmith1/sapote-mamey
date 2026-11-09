# Deliverable queue and availability checks

`python mamey_run.py deliverable-queue` runs the post-extraction steps for several strains in one
command. It runs deterministic steps only. It does not write or review any interpretation.

## Check what is available first

```bash
python mamey_run.py deliverables list --json
python mamey_run.py deliverables availability --package /absolute/path/to/package --json
```

The [menu](DELIVERABLE_MENU.md) names each output. `availability` reads local files and prints a
`state`, a `missing` list and `notes` for each output. With `--json` it prints a JSON array with one
object per output, holding `deliverable_id`, `state`, `missing` and `notes`. Without `--json`, an
input check without a ZIP prints:

```text
C01: INPUT_OR_LOCAL_DEPENDENCY_REQUIRED — antismash_zip
```

`READY` means the files and tools it looks for are present. The command exits 0 either way, so read
`state`. It only checks that a manifest file exists, not that the package is valid or sealed. Run
`validate` on the package yourself.

`deliverables render --out PATH` overwrites that Markdown file and does not create its folder. The
menu is generated from the registry. Do not edit it by hand.

## Run a queue

Before you start, each strain needs a validated package at `<runs-dir>/<strain>/package`. The `run` and
`validate` commands make it; see [first run](reader/01_FIRST_RUN.md). Work on copies of the packages,
because the queue writes into them. Use a new output folder.

```bash
python mamey_run.py deliverable-queue ABC-12 ABC-13 \
  --runs-dir /absolute/path/to/runs \
  --out-root /absolute/path/to/queue_run
```

List each strain once, as a plain folder name. An empty list exits 1. Optional inputs:

| Flag | What it adds |
|---|---|
| `--activity-table` | A measured-activity CSV for the activity dossier. |
| `--cohort-dir`, `--reference-dir` | Package roots that pre-fill the prevalence and genus sections. |
| `--strain-metadata` | A TSV of genus, host and exclusions, used as deposited. |
| `--bigscape-regions-dir` | Region GBKs for the BiG-SCAPE section. It binds only on an exact strain, full contig and region. |
| `--ledger`, `--no-resume` | Choose the ledger file, or ignore it and redo every strain. |

For each strain the queue works in `<out-root>/<strain>/sapote`. It ingests any stored BLASTp results,
checks the BLASTp gate, then makes the Mode B templates, lead pages, reference-dark page, Good Guesses
(a short class-level reading of each notable BGC), activity dossier and compiled report. Read [stored BLASTp evidence](ONLINE_BLASTP_PROTOCOL.md)
first. The queue never submits a live search.

The queue always emits `full48` Mode B templates. It does not take `--contract`. For `current50_v2`
cards, follow [the Mode B walkthrough](MODE_B_USER_WALKTHROUGH.md) instead. The gap-rescue flags (`--gap-rescue-dir`, `--rescue-verdicts-tsv`) do not switch it to `current50_v2`. Passing
`--rescue-locus-inventory` or `--rescue-gene-adjudication-tsv` needs `current50_v2` and can make the
card step fail.

## Read the result

Open `<out-root>/DELIVERABLE_QUEUE_LEDGER.json`. Every strain record has `strain`, `ts`,
`source_args_sha256` and `status`. The other fields depend on how far the strain got:

- `NO_PACKAGE`: nothing else. The queue found no `<runs-dir>/<strain>/package` folder.
- `BLASTP_BLOCKED`: also `ingested` and `missing` (the number of BLASTp inputs the gate still needs). There are no `steps`, `failed_steps` or `narratives`, because no step ran.
- `DETERMINISTIC_DONE` or `DETERMINISTIC_INCOMPLETE`: also `ingested`, `gate`, `steps`, `failed_steps` and `narratives`. A done record also has the resume hashes `package_sha256`, `outputs_sha256`, `context_sha256` and `sources_sha256`.

A field that is absent was not reached. It does not mean zero or empty.

- `status` is `DETERMINISTIC_DONE` when every step returned 0 and `DETERMINISTIC_INCOMPLETE` when any step failed. `DETERMINISTIC_DONE` does not mean every file is correct.
- `narratives` is always `PENDING_JUDGMENT`. A person still has to write the interpretation.
- The command exits 1 if any strain has a failed step, a blocked BLASTp gate or a missing package, if
  the request was empty, or if the done count differs from the number requested. Exit 0 means all
  requested strains are `DETERMINISTIC_DONE`. Exit 1 usually comes with `DETERMINISTIC_INCOMPLETE`.
- A step that fails does not undo earlier writes. Later steps still run.
- Each step times out after 1,800 seconds and then shows as `rc99`. In `steps`, a step that returned 0
  is stored as `ok`, with no output. A failed step is stored as `rc<code>:` plus the last line it
  printed, cut to 60 characters. For more detail, run the step's own command.
- The `report` step can fail with `compile-report: REFUSED - original package validation failed`
  even on a package that validated before the queue started. The queue's own Mode B template step
  adds files under `mode_b_templates/` that are not in `post_seal_checksums.txt`. A later `validate`
  then fails `checksum_integrity`, and `compile-report` refuses to run on that. The strain ends
  `DETERMINISTIC_INCOMPLETE` and no compiled report is written. The other outputs in
  `<out-root>/<strain>/sapote` are still there and usable. This is a defect in the queue, not in your
  package. This page has no verified way to get the compiled report from that package.
- The queue copies every `.md` already in `package/mode_b_templates`, even when the card step failed.
  Check that each copied template is current.

## Resume and recovery

The queue saves the ledger after each strain. Run the same command again to resume. A strain is
skipped only if it is `DETERMINISTIC_DONE` and its arguments, package files, output files, activity
table and Mode B source paths are unchanged. Otherwise it is processed again.

The source paths are the ones given with `--cohort-dir`, `--reference-dir`, `--strain-metadata`,
`--bigscape-regions-dir` and the gap-rescue flags. A source file is compared by its bytes. A source
folder is compared by each file's name, size and modification time, so an edit that keeps a file's
size and time stamp is not detected. If you replaced a source in a way that could keep them, start a
new queue with a fresh `--ledger` and `--out-root`. A record written by an earlier version has no
`sources_sha256`, so that strain is processed again once.

If the ledger is damaged, the queue stops with `DELIVERABLE_QUEUE_LEDGER_INVALID_JSON` or
`DELIVERABLE_QUEUE_LEDGER_INVALID_SHAPE`. Keep the damaged file. Start a new queue with a fresh
`--ledger` and `--out-root`, on fresh copies of the packages. Do not use `--no-resume` to hide a bad
ledger. It redoes every strain and can overwrite the old ledger and outputs.

Do not run two queues against the same ledger or output folder. A queue finishing is not acceptance of
the deliverables. The project lead still reviews and accepts them.
