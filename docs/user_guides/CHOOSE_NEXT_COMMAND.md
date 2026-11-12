# Choose the next command

This page helps you pick one command and shows how to call it. It is not the full command list; see the [command catalog](../COMMAND_CATALOG.generated.md) for that.

Run every command from the program folder, the one that holds `mamey_run.py`. Replace `EXAMPLE` and each path with your own. For command options, open the selected command's help, for example `python mamey_run.py explain --help`.

A *package* is the folder of tables, workbook and issue log that `run` builds for one strain. A *ledger* is a table of claims, one per row.

## Start with the question

If you already have a package, read it first. The answer may be in the files, and you may not need another command. See [Read one saved package](../reader/03_READ_RESULTS.md).

| Your question | Command | What you see | Success |
|---|---|---|---|
| What did I receive? | `python mamey_run.py explain runs/EXAMPLE/package` | A package summary based on available manifests and supporting files; inspect missing/unreadable inputs. It does not run extraction or `validate`. | Exit 0 and a summary. Exit 1 means no manifest was found. |
| Which regions are in it? | `python mamey_run.py list-bgcs runs/EXAMPLE/package --top 10` | A table of regions in triage order. Add `--json` for JSON or `--axis af` to sort by antifungal score. Dropped regions are left out unless you add `--include-dropped`. | Exit 0 and a table. Note the filters with any count you report. |
| Is my input usable? | `python mamey_run.py inspect ~/Downloads/EXAMPLE.zip` | A preview of the ZIP and a suggested `run` command. It does not extract anything. | Exit 0 and a suggested `run` command. For a `Complete_Package.zip` it prints an extract note instead. A missing or non-ZIP file exits 1. |
| Is my setup ready? | `python mamey_run.py doctor` | A last line that says whether to go on. | `DOCTOR: ALL CLEAR`, or `PASS with N warning(s) — optional items only`. `PASS ... missing core dependency` means install the named package and run `doctor` again. `DOCTOR: N blocking issue(s)` exits 1; stop. The [doctor table](../reader/01_FIRST_RUN.md#1-check-the-install) covers each line. |
| Did the package checks pass? | `python mamey_run.py validate runs/EXAMPLE/package --workbook-strict` | Package and workbook results. Run it on a writable copy, because it can rewrite `package_status.json`. | Exit 0. |
| Where is the larger workflow up to? | `python mamey_run.py workflow runs/EXAMPLE/package` | Each stage as `PASS`, `PENDING`, `BLOCKED` or `N/A`, and a ledger file inside the package (use `--ledger-out FILE` to write it elsewhere). | See below. |

`workflow --strict` exits 1 only when a mandatory stage is `PENDING` or `BLOCKED`. A stage marked `N/A` counts as complete. A bad package path exits 2. A ledger-write OSError can be warned about while the command still exits 0. Check stderr and confirm that the expected ledger exists and is readable; exit 0 guarantees neither the write nor every stage passing. The default ledger is inside the package and can replace the previous default. Choose a fresh explicit `--ledger-out` outside source folders when preservation is required. [The workflow contract](../SAPOTE_WORKFLOW_CONTRACT.md) lists each stage.

A passing check, a written report and an accepted interpretation are three different things. Each needs its own evidence.

## Make a figure from saved data

These commands draw or reorganize evidence you already have. They do not search or run clustering. Write to a new folder outside the package. Look at every output before you use it.

**A numeric matrix: `codex-heatmaps`.** The input is a Figure Factory `*_data.csv` file: a row-label column, then numeric columns. Row and column labels must be unique. Output goes to `<outdir>/<file name without _data>/`.

```bash
python mamey_run.py codex-heatmaps \
  --input matrix_data.csv \
  --outdir heatmap_out \
  --top-rows 0
```

By default only the 40 rows with the highest totals are drawn. `--top-rows 0` keeps every row. The default `log1p` setting changes the color scale only; labels show raw values. You get SVG panels, an HTML explorer, caption and method text, and receipts.

**A list of possible figures: `codex-figure-catalog`.** It writes a registry with a readiness label for each figure set. A catalog entry is not a drawn figure.

```bash
python mamey_run.py codex-figure-catalog --outdir catalog_out
```

**Implemented figure sets: `codex-figure-sets`.** It needs a widget JSON file, which `interactive-figures` makes. Run these two in order:

```bash
python mamey_run.py interactive-figures --runs-dir runs --out widget.json
python mamey_run.py codex-figure-sets --widget-data widget.json --outdir sets_out
```

`--runs-dir` is a folder that holds `<STRAIN>/package/` for each strain. `--tranche` picks the group of figure sets; the default is 1. Tranches 2 to 6 and `all` also need `--source-bundle`: make it first with `python mamey_run.py codex-figure-sources --widget-data widget.json --package-dir package_zips --outdir sources_out`. `package_zips` must be a flat folder holding the ZIPs named in the widget; the nested `runs` folder is not that folder. See [owner-kept figure inputs](../OWNER_KEPT_FIGURE_INPUTS.md) for preparation and checks. Tranche 6 also needs `--lead-ledger`, a table of leads this guide does not cover; see the [deliverable menu](../DELIVERABLE_MENU.md). Check the list of figure sets the command reports against what you expected.

**A saved BiG-SCAPE result: `codex-bigscape-figure-sets`.** BiG-SCAPE groups similar regions into families. This command reads a finished result and does not run it. Name the exact run and cutoffs; it never picks the latest.

```bash
python mamey_run.py codex-bigscape-figure-sets \
  --bigscape-tsv result.tsv \
  --run-manifest run_manifest.json \
  --bigscape-run RUN_LABEL \
  --bigscape-cutoffs 0.30 \
  --outdir bigscape_figs
```

Use `--bigscape-db` in place of `--bigscape-tsv` when you have a database. A portable TSV also needs `--run-manifest`.

**A cohort summary: `interactive-figures`.** The command above also writes the widget JSON. Add `--emit-figures` to render publication figures as well. Compare the strains you asked for with those in the JSON, because a package that cannot be read is skipped. Read the figure status separately: the JSON can be written while figures are skipped.

## Print per-strain pages

`assembly-line-pdf` prints the saved domain layout of the NRPS and PKS regions in each strain. `bgc-gene-map` prints the saved gene positions of every region, whatever its class. Both take the same options.

```bash
python mamey_run.py assembly-line-pdf --strain EXAMPLE --runs-root runs --out pdf_out
python mamey_run.py bgc-gene-map --strain EXAMPLE --runs-root runs --out pdf_out
```

Use `--strains A B` for several strains, or `--all` for every strain that has an `antismash_modules.csv`. Point `--runs-root` at a folder with one package per strain. Keep the count of strains built against the count requested, and note each strain that was skipped. A missing coordinate leaves a gap in a gene map. A gap is not a finding.

The text in these PDFs is smaller than the 8 pt minimum the figure house rules set for print. Use them for review on screen, and do not use them as print figures.

## Specialist reports

Each of these writes a report. None of them is a finding on its own.

**`resistance-dossier`** lists regions that carry resistance-marker domains.

```bash
python mamey_run.py resistance-dossier runs/EXAMPLE/package --domain-reference domain_reference.tsv
```

The default output is a sibling named `<package>_resistance_dossiers`, which need not be new; existing matching files can be replaced through fixed temporary paths. Prefer an explicit fresh authorized external `--out`, inspect the destination and preserve earlier reports. Pass `--domain-reference` when you have one, because the built-in fallback misses some curated calls. A marker is a hypothesis about resistance. It is not a measured phenotype.

**`af-leadboard`** builds an HTML view of the antifungal-capacity score from a per-region master table. The table is `SAPOTE_PER_BGC_MASTER_all_AS.csv`, with one row per region (strain, region, products, tier, antifungal and antibacterial scores, MIBiG anchor, guard flags). It is a cohort file kept in the project's `strain_data` folder, not something `run` writes. Without `--master-csv` the command looks for it there. If the file is missing it exits 1 with "per-BGC master CSV not found".

```bash
python mamey_run.py af-leadboard --master-csv SAPOTE_PER_BGC_MASTER_all_AS.csv --out leadboard_out
```

A capacity score is not measured antifungal activity.

**`surface-leads`** lists two review groups from a cohort table: regions whose reference match rests only on common PKS or NRPS scaffold genes, and regions that match one known family at low identity. Both are class-level capacity, not identity. It reads `whole_bgc_majority_read_cohort.csv`, which `python mamey_run.py majority-read --cohort` writes. If that file is missing, it prints `surface-leads: skipped (FileNotFoundError ...)` and exits 1. The canonical guard refuses replacing existing files in recognized dated folders unless forced; it does not protect every custom output or first write. Set `--out` to a fresh authorized folder and inspect its contents; use `--force` only with replacement authority.

```bash
python mamey_run.py surface-leads --out leads_out
```

**`triage-raw`** ranks regions in a raw antiSMASH ZIP or folder before extraction. `explore` reads a finished package instead.

```bash
python mamey_run.py triage-raw --input-zip EXAMPLE.zip --top-n 5 --out triage.md
python mamey_run.py explore runs/EXAMPLE/package --top 5
```

`--no-walk` skips the selected walker, not every HMM-related evidence path; the command still imports Biopython. The `--out` report and optional `--json` companion use direct writes and can replace files. Choose fresh names outside source evidence and inspect both outputs. A ranking of the top regions is not a full inventory.

## Compare and review

**`dualpass`** compares two ledgers of claims from two independent passes, called the first and second ledger. It does not say which claim is true. Each ledger is a tab-separated file with the columns `task`, `strain`, `bgc_id`, `locus_tag`, `assertion_type` and `value`.

```bash
python mamey_run.py dualpass first_ledger.tsv second_ledger.tsv --out dualpass_out
```

It writes `DIVERGENCE.tsv` and normalized copies of both ledgers into `--out`, named for the ledger they came from: files from the first ledger start with `claude_` and files from the second start with `codex_`. Before the first write it checks every output path. It refuses, with exit 1, an output that is or resolves to an input, and an existing `DIVERGENCE.tsv` or normalized copy. So it will not write over an input or an earlier output; use a new `--out` folder each time. `--no-normalize` compares the raw values, so wording differences then show up as disagreement.

**`validate-finished-review-request`** checks a review packet.

```bash
python mamey_run.py validate-finished-review-request runs/EXAMPLE/package \
  --request request.json --artifact-root review_files
```

This is a maintainer command. Its `request.json` format is not documented for users, so skip this command unless a maintainer gives you a request file. A missing or wrong key comes back as a named finding. The command exits 0 with `READY_FOR_OWNER_REVIEW` when the packet is consistent, and exits 3 with `HOLD_FINISHED_REVIEW_REQUEST` when it is not. `READY_FOR_OWNER_REVIEW` means the request passed the named internal-consistency checks and can go to owner review. It does not show that the packet or its evidence is complete, current, authentic or scientifically valid, and it is not card acceptance.

**`directed-pks-study` and `cddr-pks`** build a study of polyketide synthase (PKS) regions and a report on it.

```bash
python mamey_run.py directed-pks-study \
  --source-csv genes.csv --study-spec study.json --out pks_study
python mamey_run.py cddr-pks --directed-study-dir pks_study --out pks_report
```

Use fresh user-controlled output directories for both study and report commands; `mkdir(exist_ok=True)` does not protect a prior `pks_study` from replacement. `study.json` is a JSON object. Only `groups` is needed to do anything useful:

```json
{
  "study_id": "example_study",
  "groups": {"SetA": ["NODE_1", "NODE_2"], "SetB": ["NODE_3"]},
  "excluded_bgcs": {"BGC011": "reason for leaving it out"},
  "figure_quality_gate": 9.0
}
```

- `study_id`: the study name. It names the output files. The default is `directed_pks_study`.
- `groups`: each group name maps to a list of full contig names. Each group gets its own locus map.
- `excluded_bgcs`: optional. Each BGC ID maps to the reason it is left out. Those regions are listed in `excluded_bgc_table.csv`.
- `figure_quality_gate`: optional, default 9.0. The command reports `READY` only when it has at least one figure and every figure's self-rating meets this number. Otherwise it reports `NEEDS_REVIEW` and exits 2. The existence/self-rating gate is not human visual inspection or scientific validation.
- `comparator_gene_table`: optional path to a comparator gene table. `--comparator-gene-table` on the command line overrides it.

`examples/directed_pks/bee_strain_directed_pks_study_spec.json` is a full example. `genes.csv` needs the columns listed in `directed-pks-study --help`.

`cddr-pks` exits 0 only when the study status is `READY`. A status of `UNKNOWN` means no readable study receipt was found. It exits 2 and still writes the report so you can read the gaps. Read the status, the warning count and the source-table counts before you use the report.

**`wise-fragmented-pks`** splits a ranked protein FASTA into batch files sized for the NCBI web BLASTp limit. It does not run a search.

```bash
python mamey_run.py wise-fragmented-pks --input-fasta ranked.fasta --outdir blast_queue
```

The FASTA headers carry a rank as `rank=N`. A queued file is not a finished search.

## If a command does not answer your question

Save the command, the input file names, the output folder, the exit code and the receipt it wrote. Add one sentence on what you expected and one on what you saw. Then fix the stage that failed. Do not rerun the whole pipeline. [Recover a run](../reader/04_RECOVERY_AND_LIMITS.md) shows how.
