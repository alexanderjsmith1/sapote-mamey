# Make BiG-SCAPE family tables and figures

This page clusters antiSMASH regions from a hand-staged cohort and exports family tables and figures. For the bundle's first run, see [the first-run recipe](reader/01_FIRST_RUN.md). BiG-SCAPE setup is separate: see [the installation check and settings](BIGSCAPE_GCF_WORKFLOW.md) and the Pfam entry in the [external assets guide](EXTERNAL_ASSETS_GUIDE.md). The launcher on this page reads two settings: `BIGSCAPE_ENV_BIN` (the environment's `bin` folder that holds `bigscape` and `fasttree`) and `PFAM_HMM` (the path to the pressed `Pfam-A.hmm`).

## Which route

- This page: you stage the region GBKs yourself and run BiG-SCAPE with `tools/bigscape_launch.sh`. Use it for a cohort, or when you need to pick the inputs.
- `python mamey_run.py bigscape`: takes one sealed package (`--package`), a folder of packages (`--runs-dir`) or a folder of region GBKs (`--input-gbk-dir`). It stages into a space-free folder, runs BiG-SCAPE and then builds the cohort widgets. Defaults: `--cpus 4`, `--cutoffs 0.3,0.5,0.7`, `--record-type region`, `--classify category`. On a laptop you are also working on, pass `--cpus 1`. Add `--dry-run` to print the plan without running. Use it for one package or a plain cohort run.

The launcher on this page defaults to 4 cores too. The example below passes `--cores 1`.

## What you need

- The selected antiSMASH ZIPs.
- The `*_2_inventory.csv` file in each strain's `runs/<ID>/package/` folder. It binds each region to its contig and BGC alias.
- A working BiG-SCAPE 2 environment, and a pressed `Pfam-A.hmm` (the Pfam protein-domain database). The launcher checks that `Pfam-A.hmm` and all four `hmmpress` files (`.h3f`, `.h3i`, `.h3m`, `.h3p`) exist, and exits 2 if one is missing. It does not check that they were pressed from this `Pfam-A.hmm`.
- `fasttree` on the environment's `PATH`. The launcher exits 2 without it.
- The `sqlite3` command-line tool, for the run-ID query below.

Use fresh staging, output and figure folders. Keep the input hashes and the database run ID. Settings are in the [cohort workflow](BIGSCAPE_GCF_WORKFLOW.md). Terms are in the [glossary](GLOSSARY.md).

## Stage the regions

Strictness is the antiSMASH detection profile. It is read from the antiSMASH JSON inside each ZIP. This example uses `relaxed`:

```bash
python tools/bigscape_prep.py --inputs inputs/EXAMPLE-cohort \
  --strictness relaxed --out reviews/EXAMPLE-bigscape/gbk_input
```

What staging does:

- It stages only antiSMASH region GBKs, files whose names end in `regionNNN.gbk`. Whole-contig and whole-strain GBKs are never staged.
- It skips inputs recorded under another strictness profile.
- It skips strains on the hard-exclusion list. The list is read from `OFFICIAL_DATA/exclusions.json` when present, with a built-in fallback, and may be empty. Pass `--allow-excluded` to stage them anyway.
- It writes `STRICTNESS_MANIFEST.tsv` in the output folder. One row per input shows the state: `STAGED`, `SKIP_HARD_EXCLUDED`, `SKIP_WRONG_FLAVOR(!=relaxed)`, `SKIP_UNDETECTABLE`, `SKIP_UNSUPPORTED_INPUT`, `EMPTY_NO_REGION_GBKS` (the input was read but held no region GBK), `EMPTY_ALL_REGIONS_FILTERED` (`--drop-contigs` or `--min-query-genes` removed every region), or an `ERROR:` state such as `ERROR:MISSING_INPUT`, `ERROR:UNREADABLE_ZIP` or `ERROR:CONFLICTING_STRICTNESS`.

Read the exit code, not just the printed line. The `staged N region GBKs` line prints on exit 2 too.

- Exit 0: at least one region was staged and no input errored. Exit 0 still allows `SKIP_` and `EMPTY_` rows. Confirm in `STRICTNESS_MANIFEST.tsv` that every strain you expected is `STAGED` with a nonzero `n_regions`. An `EMPTY_` row is a staging result, not a biological absence. The tool also lists `EMPTY_` inputs on stderr.
- Exit 1: nothing was staged. A ZIP with no antiSMASH JSON inside gets `SKIP_UNDETECTABLE`, because its strictness cannot be read. If you know its strictness, add `--assume-strictness relaxed` (or the profile you know). The manifest records it as assumed.
- Exit 2: an input could not be read (an `ERROR:` row), the staged set mixed strictness profiles, or a `--drop-contigs` check failed. A named file that is neither a ZIP nor a folder gets `SKIP_UNSUPPORTED_INPUT` and does not change the exit code, so read the manifest on exit 0 too. Fix the cause and stage again into a fresh folder.

## Cluster the regions

With `bigscape` on PATH, set the environment folder and the Pfam path:

```bash
export BIGSCAPE_ENV_BIN="$(dirname "$(command -v bigscape)")"
export PFAM_HMM=../reference-data/Pfam-A.hmm
set -o pipefail
nice -n 15 bash tools/bigscape_launch.sh \
  reviews/EXAMPLE-bigscape/gbk_input reviews/EXAMPLE-bigscape/out \
  --label EXAMPLE --cores 1 --include-singletons \
  2>&1 | tee reviews/EXAMPLE-bigscape/launch.log
```

`--label` names the database (`out/EXAMPLE.db`). `--cores 1` limits CPU use. `--include-singletons` keeps isolated regions in the run. Default cutoffs are 0.3, 0.5 and 0.7.

BiG-SCAPE 2.0.3 scans Pfam in-process. Warnings about external `hmmsearch` or `diamond` alone need not stop the run.

Success: the launcher prints `BIGSCAPE_EXIT=0`, then a block of loaded counts (lines such as `Loading N query GBKs`) and up to five error lines. There should be no error lines, and the query count should match your staged count. The full BiG-SCAPE output is in `out/run.log`. Find the run ID, then use one that has an end time:

```bash
sqlite3 reviews/EXAMPLE-bigscape/out/EXAMPLE.db 'select id, end_time from run;'
```

A run with no end time is unfinished in the database. That does not tell you whether its process has stopped: it may still be running. Before you call it interrupted or retry, check that the launcher or BiG-SCAPE process for that output folder has exited (for example with `ps`) and read the end of `out/run.log`. If you cannot tell, record the run as unresolved and do not reuse its output folder. The launcher's exit codes are its own: 2 setup, 3 MIBiG folder too small, 4 MIBiG count not proven, 5 BiG-SCAPE itself exited nonzero (its code is the `BIGSCAPE_EXIT=` line). Each refusal line on stderr starts with `LAUNCHER_STAGE=`. Retries are in [troubleshooting](troubleshooting/BIGSCAPE_TROUBLESHOOTING.md). The optional MIBiG branch (`--mibig-dir`, `--mibig-name`) needs at least 2,000 GBKs and is explained there.

## Export families

The example uses run ID 1:

```bash
python tools/bigscape_family_verdicts.py reviews/EXAMPLE-bigscape/out/EXAMPLE.db \
  reviews/EXAMPLE-bigscape/FAMILY_VERDICTS.tsv --run-id 1 --query-regex '^([^_]+)_'
```

A query region is a staged file whose name matches the query regex. The default regex, `^([A-Za-z]+-\d+)_`, wants letters, a hyphen, digits and an underscore, such as `ABC-12_`. A name like `EXAMPLE_...` does not match it. This example passes `--query-regex '^([^_]+)_'`, which takes the name up to its first underscore, so name the ZIPs without an underscore.

Pass the same regex to every command that takes it: the verdicts command above, the figures command below, and the clinker command if you run it. `tools/bigscape_cohort_report.py` does not use a regex. It matches names against a host table; see the [network guide](BIGSCAPE_COHORT_NETWORK_GUIDE.md).

The table path and its `<table>.placement.tsv` companion must both be new files and must not be the database. The tool refuses them otherwise, with exit 2 before it reads the database. Use a new table name for each run and cutoff, for example `FAMILY_VERDICTS_run1_c0.3.tsv`.

If the table is empty, compare the query count with your staged roster before reading anything into it.

The default cutoff is 0.3. Family IDs belong to one database, run and cutoff. The `cross_strain` column separates families with several strains from families with several regions of one strain. Without loaded references, the table shows sharing within the cohort only.

## Singletons

A singleton is a region with no partner at the chosen cutoff. The verdicts tool writes a placement file next to the table. For each cutoff it lists `region_records`, `records_with_family_row` and `singleton_records`. The tool computes `singleton_records` as regions minus regions that have a row in `bgc_record_family`. So it counts regions without a family row. It does not count single-member families.

To count single-member families, count the members of each family in the database. The [troubleshooting page](troubleshooting/BIGSCAPE_TROUBLESHOOTING.md) gives the denominator rule.

## Draw selected families

Pass the same run ID. The figure tool reads one run. It refuses an interrupted run. It refuses a database with several finished runs unless `--run-id` names one.

```bash
python tools/bigscape_family_figures.py --db reviews/EXAMPLE-bigscape/out/EXAMPLE.db \
  --run-id 1 \
  --gbk-dir reviews/EXAMPLE-bigscape/gbk_input \
  --identity-glob 'runs/EXAMPLE/package/*_2_inventory.csv' \
  --out reviews/EXAMPLE-bigscape/figures \
  --private-tsv reviews/EXAMPLE-bigscape/FAMILY_VERDICTS.tsv --focus EXAMPLE \
  --query-regex '^([^_]+)_'
```

`--focus` takes the staged query name that the regex captures (here `EXAMPLE`). The default display limit is 40 tips. The full membership stays in the verdicts table.

Then check the results:

1. Open `reviews/EXAMPLE-bigscape/figures`. The `--focus` job writes `strain_focus/<strain>/`. It holds `family_trees_c<cutoff>/` with the figures, `FAMILY_FIGURES_INDEX.tsv` (one row per family, with `identity_holds` and `status`) and `BGC_TO_FAMILY_FIGURE.tsv` (one row per region, with its figure). The `--private-tsv` job writes `private_families/INDEX.tsv`, with the same `identity_holds` and `status` columns. The tool exits 1 if any family failed. Look at every figure.
2. Look for identity holds in the labels. A query label must read strain / full contig / region / BGC alias. A hold means the alias could not be bound; see troubleshooting.
3. Keep the closed database, the source records, the settings and the output hashes.

## Optional: clinker pages

`tools/bigscape_clinker_html.py` draws within-family gene alignments as HTML, and as PDF when you give `--chrome <binary>`:

```bash
python tools/bigscape_clinker_html.py --db reviews/EXAMPLE-bigscape/out/EXAMPLE.db \
  --out reviews/EXAMPLE-bigscape/clinker --run-id 1 --focus EXAMPLE \
  --query-regex '^([^_]+)_'
```

For several runs in one database, use the [explicit-run report](BIGSCAPE_COHORT_NETWORK_GUIDE.md).
