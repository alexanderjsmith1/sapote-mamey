# SOP-00 — Start Here / Choosing the Right Sapote/Mamey Path

Run the commands below from the bundle root, the folder that holds `mamey_run.py`.


## Purpose

Find out what kind of file you have, then pick the first command for it. Starting with the wrong command wastes time and can give a misleading result.

## First question

Before you run an analysis, decide what kind of file you have.

## Input classes

For an existing package, read its saved receipts first. `validate` rewrites
`package_status.json`, so validate an extracted copy if the original must stay unchanged. See [validation write scope](../POSTSEAL_READERS.md#validation-can-update-a-mutable-status-receipt).

| Input shape | Meaning | First action |
|---|---|---|
| Raw antiSMASH ZIP with many regions | Multi-region antiSMASH output; verify assembly and record scope separately | `python mamey_run.py inspect path/to/EXAMPLE.zip` |
| Raw antiSMASH ZIP with one region | One region file. This is an input shape, not a sign that the file is a reference or a test. Check the source assembly first | `python mamey_run.py inspect path/to/EXAMPLE.zip`; see [SOP-07](SOP-07_Single_Region_Public_Accession_Inputs.md) |
| Sealed Mamey package | Previous run output | `python mamey_run.py validate reviews/EXAMPLE-saved/package` |
| BLASTP Hit Table CSV | Follow-up evidence from NCBI | `python mamey_run.py blastp-followup --hit-table path/to/HitTable.csv --outdir reviews/new-blastp-review` |
| BLASTP XML2 file | Supplemental alignment detail (coverage, titles); not proof of source, query or locus binding | Pair with hit table when possible; check parsing and missing fields |
| FASTA only | Candidate for BLASTP or intake support | Do not run Mamey directly unless command supports it |
| Spreadsheet/workbook | Prior run table or manual ledger | Inspect sheet names before interpreting |
| Patch packet ZIP | Development patch | Read README / manifest / diffs before applying |

Replace example paths with your bound inputs and fresh output paths; quote paths containing spaces. Inspect saved receipts before validating a working copy.

## Standard decision tree

1. If it is an antiSMASH ZIP, run `inspect` first.
2. If `inspect` passes and the input/source binding and task authorize analysis, run gold directly. Gold (`--mode gold`) is the only analysis mode of `run`. Under a tool time limit, add `--capped-session`, the reduced-output profile in [SOP-02](SOP-02_ChatGPT_Safe_Smoke_Run.md).
3. If it is a Mamey package, validate it instead of re-running.
4. If it is BLASTP output, parse and reprioritize, do not rerun Mamey.
5. If it is a patch packet, audit contents before applying.
6. If file type is unclear, list archive contents and classify.

## Write down what the file is first

Before you run a command, note what the file appears to be: raw antiSMASH output, a sealed Mamey package, BLASTP result output or a patch packet.

## Failure modes

| Failure | What to do |
|---|---|
| No region GBKs | `inspect` admits whole records that have exactly one numbered region feature and holds the others. With none admitted, it says the ZIP does not look like antiSMASH output and exits 1 |
| No KnownClusterBlast TXT | Other inputs may still be parseable; inspect the independent JSON record-pass status before concluding that KCB similarity is unavailable |
| Single region only | One region file does not establish whether the source was a full genome. Check the source assembly, supplied records and intended reference/test role |
| One ZIP with a huge region count | Use one capped gold run (`--capped-session`) |
| Many ZIPs | Follow the [batch guide](../INTAKE_BATCH_AND_SMALL_N_DIRECTIVES.md) to choose the required input, output, registry and metrics paths; use `--resume` only for a retry |
| Mac dotfiles present | The inspector filters recognized macOS cruft; check admitted real records and their warnings rather than treating a filtered shadow as evidence |
| Filename differs from internal accession | Use the actual ZIP path for `--input-zip`; review the proposed strain label against the current strain-ID rule, retaining any deliberate accession-label override |

## Bug-hunt checks

1. Classify the uploaded file before choosing a command. `inspect` accepts an antiSMASH ZIP; it is not a universal detector for workbooks, FASTA, BLASTP CSVs or package directories.
2. Single-region antiSMASH ZIPs must not trigger misleading full-genome failure language.
3. Never read antiSMASH JSON by hand when `inspect` and `run` can read it.
4. The command recommendation must match input type.
