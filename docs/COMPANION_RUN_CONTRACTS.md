# Companion run contracts

This is a maintainer page. It lists what the phylogeny companion scripts read, write and return, so you can tell a finished run from an interrupted one. If you only want to pick a tool, start with the [companion tool guide](COMPANION_TOOL_GUIDE.md). For a first genome-tree run, use the [GToTree workflow](GTOTREE_WORKFLOW.md).

**Quick task: classify a folder of FASTA files (read-only).** From the bundle root:

```bash
python tools/phylo_autopilot.py plan <fasta_dir>
```

Success is a JSON object on the screen, such as `{"rrna": ["<fasta_dir>/a.fasta"]}`, and exit code 0. Each file ending `.fa`, `.fasta`, `.fna`, `.faa` or `.fas` is listed under the kind it was sorted into; any other file is listed under `not_classified_suffix`. A record with a header and no sequence makes its file `empty_record`. A missing folder exits 2. Nothing is written and no tree is built. The kinds come from length and alphabet, so check them against your files.

Run companion tools only when you are authorized to, with fresh output folders outside the code bundle. Keep inputs unchanged. External tools and databases are installed separately (see [companion files](COMPANION_FILES.md)).

## What each command does

A name such as `plan`, `dry-run` or `report` does not mean the command is read-only. Read the paths it prints. Companions do not share one folder layout.

| Command | Reads | Writes | Success signal |
|---|---|---|---|
| `tools/phylo_autopilot.py plan <dir>` | FASTA files | nothing | JSON of file kinds on screen |
| `tools/phylo_autopilot.py route --query ... --db ... --out ...` | nucleotide queries, a local BLAST database prefix | a routing TSV | every query has a routing state; check coverage and excluded rows |
| `tools/phylo_autopilot.py run-16s ... --dry-run` | the same database, a group, an output root | QC, routing, accession list, reference FASTAs | a reference roster with provenance; no placement yet |
| `tools/phylo_autopilot.py run-16s ... --approved-by ...` | the prepared scope | the preparation above, then placement files | jplace, placement tables and the files you asked for |
| `tools/build_mlsa.py <genomes_dir> <new_out>` | lowercase `*.fna` genomes, five protein seed files | `loci_report.tsv`, `run_status.json`, a log and a tree | exit 0 and the tree file; then check the loci report |
| `tools/plan_gtotree_iqtree.py plan ...` | a panel, an HMM set, tool paths | `RUN_MANIFEST.json`, `RUN_STATE.json`, `COMMAND.sh` | `RUN_STATE.json` reads `PLANNED_AWAITING_APPROVAL` (any `HOLD` state means fix the input) |
| `python mamey_run.py phylo-run ... --approved` | a genome list, an HMM set, an outgroup, a work folder | `run_status.json`, QC, alignment, tree, optional ANI | `run_status.json` plus tree and QC files |
| `tools/plan_gtotree_iqtree.py discover --run-dir ...` | a planner run folder | optional new receipt (`--receipt`) | one alignment candidate and the retained genome count |
| `tools/phylo_place.py report ...` | a jplace file, reference package, metadata | graft, tables, optional figures and caption | `<group>_REPORT_ATTEMPT.json`; exit 2 means a length or metadata hold |

The planner's state file and the runner's status file are separate. Compare them by hand.

## Resource settings and approval

`phylo-run` defaults to `--threads 4 --parallel 1`: four threads, one job at a time. For one core, add `--threads 1 --parallel 1 --iqtree-threads 1`. Use a larger budget only when your authorization allows it. For a 16S placement run, set `--threads` yourself.

The planner takes `--threads-per-tree` 1 to 4 and `--max-concurrent-cores` 1 to 4. It records the numbers. It does not start a scheduler or limit other processes.

`phylo-run` needs `--approved`. The planned route, `run_planned_tree.py --plan-dir`, also needs a `RUN_STATE.json` with `approved=true` and checks the saved input hashes, labels, tools and HMM against the plan. These checks confirm the records match. They do not identify a person. Placement uses `--approved-by` as your own statement of approval.

## MLSA inputs, completion and recovery

`build_mlsa.py` reads only immediate lowercase `*.fna` files, and five seed files must exist. It looks for programs in `--bin-dir`, then `MAMEY_PHYLO_BIN` (or `PHYLO_BIN` when the first is unset), then `PATH`. It rejects unknown options. Options: `--threads` (default 4), `--bin-dir`, `--seeds-dir`, `--native-work-root`, `--rss-limit-bytes`, `--min-free-disk-bytes`, `--timeout-seconds` and `--native-copy-limit-bytes`. Byte budgets and threads are positive integers; the other budgets are positive numbers.

The wrapper sets six native-thread variables to 1, records hashes of the inputs, seeds, tools and interpreter, and watches the worker's memory, free disk and elapsed time.

The output folder must be new or empty, its parent must exist, and it must not overlap the genome folder, seed folder or code tree. The same holds for the native work root.

Exit codes:

| Exit | Meaning |
|---|---|
| 0 | the worker finished inside its limits, outputs match, cleanup and promotion worked |
| 2 | bad usage |
| 4 | a preflight check refused the run |
| 6 | the worker, its completion check or promotion failed |

After a failure, look in `RESOURCE_ATTEMPT/<attempt-id>/` for `REQUEST.json`, `RESOURCE.json`, `WORKER_COMPLETION.json`, `SUCCEEDED.json` or `FAILED.json`, and `worker.log`. Some refusals happen before these exist. Keep the failed folder and use a new output folder for the next try.

Read the result before you trust it:

- Each locus uses the best-scoring BLAST hit for its seed. This is not an orthology test. Open `loci_report.tsv` and check the HIT and NO_HIT rows.
- A locus with no hit anywhere is left out. A genome with at least one locus stays in, with gaps. A genome with no locus drops out. Compare your intended genome list with the partitions and tips that remain before you call it a five-locus tree.
- `_OUTGROUP` in a file name is only part of the label. The command does not root the tree.
- The worker's final check needs a nonempty `tree.treefile` with at least one numeric internal support label, a nonempty `tree.contree`, and the IQ-TREE log line `Total wall-clock time`. The wrapper then checks that the worker exited 0 inside its limits, that `run_status.json` reads `COMPLETE`, that the completion record matches the frozen request, and that the output file list did not change during promotion. None of this checks tip names against your genome list or judges the support values. Exit 0 is mechanical completion, not a reviewed tree.

## Accepted GToTree versions

GToTree 1.8.19 and 2.0.x are accepted. Version 1 uses `-n`; version 2 does not, and the help probe uses `-s`. Recognizing a version is not the same as a run being admitted: unverified 2.0 profiles stay on hold, and the 2.0.0 route needs its own runtime and plan records. Keep the version, help text, generated command and receipt with the run.

## Checking outputs

A FASTA list is not a tree, and a tree file is not a reviewed figure, a taxonomy or an ANI result. `phylo_place.py report` returns 2 when branch lengths or a requested metadata strip are on hold. A failed optional figure or caption does not force a nonzero exit, so open `<group>_REPORT_ATTEMPT.json` and the files you asked for.

For `phylo-run`, a fastANI step (requested with `--ani-refs`) must write its output and pass its checks. A failure keeps the core tree files and returns nonzero. Keep the direction of each comparison, the matched and total fragments and the aligned fraction. A missing ANI row means not measured, not zero. An ANI threshold, or placement inside one reference set, does not give a species name by itself.

## Scanner HMM lookup

The HMM check in `doctor` and the scanner use the same lookup, in `mamey/wheelhouse.py`. The order is: an existing `SM_HMM_DB` path, then `MAMEY_HMM_DIR`, a shared-root `hmm/` folder, the bundle's own 148 set, an add-on 148 set, and last the bundle's 35 set. In a folder, `scanner_pfam_150.hmm` wins over `scanner_pfam.hmm`. The number in a file name is only a hint, so check the contents and record the file hash. Finding the file does not prove a scan ran.

The local PubMed helper reads PDF exports you already have; it does not fetch anything. See [external assets](EXTERNAL_ASSETS_GUIDE.md) and [external data](EXTERNAL_DATA.md).
