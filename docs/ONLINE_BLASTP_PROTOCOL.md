# Use BLASTp evidence

BLASTp compares each protein of a gene cluster with a public protein database.
This page covers how to search online, how to load saved results, and how to
check the result. Run every command from the bundle root. Setup is in the
[first-run recipe](reader/01_FIRST_RUN.md). Terms are in the [glossary](GLOSSARY.md).

## Pick a route

| You have | Run |
|---|---|
| A strain package and want to search NCBI | `blastp-online` (one cluster) or `auto-blastp` (many, slowly) |
| NCBI is unreachable | `blastp-ebi`, then `ingest-blastp` |
| An NCBI Hit Table CSV | `ingest-blastp` |
| A folder of per-gene result files | `ingest-blastp-trove` |
| Runner summary files | `tools/ingest_blastp_rollups.py` |
| A question: what is already loaded? | `blastp-status` |

## Databases and channels

- **nr** is NCBI's non-redundant protein database.
- **ClusteredNR** (`nr_cluster_seq`) holds one representative per cluster of nr.
- **Swiss-Prot** is a small, expert-reviewed protein database.

Keep nr, ClusteredNR and Swiss-Prot in separate **channels**. Never merge or
relabel hits from one into another. Record every locus as
**strain / full node-or-contig / region / BGC alias**. Keep query identifiers,
protein hashes and the original query and job receipts with the results.

## Before you load results

The routes below write into a workbook and a package. Work on a copy, so the
original stays untouched. Keep the copy in a folder outside the bundle: several
tools refuse to write inside it (`OUTPUT_INSIDE_BUNDLE`). The
[Mode B walkthrough](MODE_B_USER_WALKTHROUGH.md) uses the same folder, so hits
you ingest here reach your Mode B cards. If you already made the copy there,
skip this step.

```bash
mkdir -p $HOME/mamey-work/EXAMPLE
cp -R runs/EXAMPLE/package $HOME/mamey-work/EXAMPLE/package
cp runs/EXAMPLE/package/EXAMPLE_5_workbook.xlsx $HOME/mamey-work/EXAMPLE/EXAMPLE-master.xlsx
```

`EXAMPLE-master.xlsx` is the workbook that `--master` appends to. Use your own
master workbook for the strain if you keep one. `ingest-blastp` exits 2 if the
file is missing. Later sections use these two copies.

## Search NCBI for one cluster: blastp-online

Get the cluster's `BGC_ID` from `$HOME/mamey-work/EXAMPLE/package/EXAMPLE_2_inventory.csv`.
Then plan the search:

```bash
python mamey_run.py blastp-online --package inputs/EXAMPLE.zip \
  --bgc BGC_ID_FROM_INVENTORY --crosswalk $HOME/mamey-work/EXAMPLE/package
```

`--package` is the antiSMASH ZIP (or one region GBK). `--crosswalk` is the
matching package folder. The command resolves the cluster to its contig and
coordinates and refuses to widen an unresolved cluster to the whole genome.

The default run only plans. It prints the protein and residue counts, the
batches, the database, the endpoint and a sequence digest, and ends with:

```text
[blastp-online] PLAN ONLY — nothing was sent. Re-run with --submit --confirm-public-sequence-upload ...
```

Exit code 0 with `PLAN ONLY` means nothing left your machine. Check the locus
and the protein list before you approve an upload.

Options:

- `--database` takes `nr` (default), `refseq_protein` or `swissprot`.
- `--batch-size` sets proteins per submission. The default is 10 and the
  maximum is 30. Proteins over 2,500 residues go in batches of their own.
- `--evalue` sets the E-value cutoff.

**To submit,** add both `--submit` and `--confirm-public-sequence-upload`, and
choose an `--outdir` outside the bundle. The second flag states that the
sequences may be sent to NCBI. Do not send unpublished or restricted sequence.
Without it, `--submit` exits 1 and sends nothing.

```bash
python mamey_run.py blastp-online --package inputs/EXAMPLE.zip \
  --bgc BGC_ID_FROM_INVENTORY --crosswalk $HOME/mamey-work/EXAMPLE/package \
  --submit --confirm-public-sequence-upload --outdir $HOME/mamey-work/EXAMPLE/blastp_online_run
```

The default `--outdir` is the current folder, which is the bundle root. A run
without `--submit` is plan-only: it sends nothing, writes nothing and exits 0, so
it needs no `--outdir`. A run that submits or writes refuses an `--outdir` inside the
bundle; for that route always pass one outside the bundle.

The command waits for all batches, which can take many minutes. Its console shows
`batch N: RID <id>, <n> hits` for each batch. A RID is NCBI's job ID for one submitted search. It then writes
`<BGC>_online_blastp.csv` and `<BGC>_cluster_reads.json` to `--outdir`. Exit 0
means the files were written. Exit 1 means the locus did not resolve or a guard refused; the `REFUSING` text gives the reason. Exit 2 (`ONLINE CHANNEL UNAVAILABLE`) means no
batch returned results, and nothing was invented. One batch can fail while
another succeeds, so reconcile every batch against the submitted protein list.
Keep the RIDs, raw responses and the submitted roster.

**ClusteredNR.** `blastp-online` has no ClusteredNR option. Use
`auto-blastp --channel clustered_nr`, described next. To load ClusteredNR
results you already have, use `ingest-blastp-trove --channel clustered_nr`.
`refseq_protein` results have no matching `--channel` value for
`ingest-blastp-trove`, so that route cannot load them. Keep them as the
`blastp-online` CSV.

## Search many clusters, slowly: auto-blastp

`auto-blastp` works through every cluster that still needs BLASTp. It submits
one query about every 8 minutes and loads results about once an hour. A full
run takes hours and holds the terminal. Plan first:

```bash
python mamey_run.py auto-blastp --package $HOME/mamey-work/EXAMPLE/package \
  --strain EXAMPLE --channel clustered_nr --dry-run
```

`--channel` is `nr` (default), `clustered_nr` or `swissprot`. The dry run
contacts no network. It prints `DRY RUN`, the number of clusters and proteins to
search, the schedule and the first 20 queue entries. To run for real, replace
`--dry-run` with `--submit --confirm-public-sequence-upload`. Add
`--max-submits N` to stop after N submissions. State is saved in
`<package>/blastp_online/_autoharness_state.json`, so a rerun resumes. It
refuses to resume under a different strain or channel.

## EBI fallback: blastp-ebi

Use EMBL-EBI when NCBI is unreachable. EBI searches UniProt databases, not nr
(`uniprotkb_bacteria` is the default). EBI requires a real contact `--email`.
First make a multi-FASTA of the proteins. `bgc-blastp-panel` reads the antiSMASH
ZIP and writes FASTA round files and a manifest to `--outdir`. It picks 2
representative proteins per cluster by default. `--genes-per-bgc` raises that limit,
but the tool still keeps only proteins it rates as useful, so the count can stay low.
The last line names what it chose, for example
`curated 2 proteins from 1 BGCs`. Each round file is a multi-FASTA you can pass to
`--fasta`:

```bash
python mamey_run.py bgc-blastp-panel --input-zip inputs/EXAMPLE.zip \
  --strain EXAMPLE --genes-per-bgc 10 --outdir $HOME/mamey-work/EXAMPLE/panel
```

The curated proteins are in
`EXAMPLE_curated_10_per_BGC_NCBI_safe_round001_for_BLASTP.faa` (more rounds add
`round002` and so on). The folder also holds a one-protein-per-cluster file and a
first-pass file. `EXAMPLE_BGC_BLASTP_PANEL_selection_manifest.csv` says why each
protein was chosen. Then submit one round file with a state file path:

```bash
python mamey_run.py blastp-ebi --fasta $HOME/mamey-work/EXAMPLE/panel/EXAMPLE_curated_10_per_BGC_NCBI_safe_round001_for_BLASTP.faa \
  --state $HOME/mamey-work/EXAMPLE/ebi_state.json --email you@example.org \
  --submit --confirm-public-sequence-upload
python mamey_run.py blastp-ebi --fasta $HOME/mamey-work/EXAMPLE/panel/EXAMPLE_curated_10_per_BGC_NCBI_safe_round001_for_BLASTP.faa \
  --state $HOME/mamey-work/EXAMPLE/ebi_state.json --harvest
python mamey_run.py blastp-ebi --fasta $HOME/mamey-work/EXAMPLE/panel/EXAMPLE_curated_10_per_BGC_NCBI_safe_round001_for_BLASTP.faa \
  --state $HOME/mamey-work/EXAMPLE/ebi_state.json --to-outfmt10 $HOME/mamey-work/EXAMPLE/ebi_hits.csv
```

`--to-outfmt10` also writes `<csv>.provenance.json` with the query lengths. Each step prints a count, such as `3/3 jobs submitted` or `harvest: 3/3 XML
retrieved ... COMPLETE`. If harvest is not complete, run `--harvest` again. Then
load the CSV into the workbook with the stamp that marks it as EBI:

```bash
python mamey_run.py ingest-blastp --master $HOME/mamey-work/EXAMPLE/EXAMPLE-master.xlsx \
  --strain EXAMPLE --hit-table $HOME/mamey-work/EXAMPLE/ebi_hits.csv \
  --source "EBI (uniprotkb_bacteria)"
```

Replace `$HOME/mamey-work/EXAMPLE/ebi_hits.csv` with the file you wrote in the last step, and
the source label with the database you used. Without `--source`, EBI rows are
mislabeled as NCBI. Do not add `--package` for EBI results: the package overlay that
`ingest-blastp --package` writes (`blastp_online/`) is the NCBI nr channel, and the command
refuses any `--source` that is not NCBI nr with `BLASTP_CHANNEL_UNSUPPORTED_FOR_PACKAGE_OVERLAY`
before it writes anything. The workbook rows keep the EBI source label.

## Load an NCBI Hit Table: ingest-blastp

Use the original **headerless** CSV with 12 or 13 columns. In NCBI web BLAST,
download "Hit Table (CSV)". A file with a header row is rejected. There is no dry run, so
use the working copies from "Before you load results":

```bash
python mamey_run.py ingest-blastp --master $HOME/mamey-work/EXAMPLE/EXAMPLE-master.xlsx \
  --strain EXAMPLE --hit-table inputs/EXAMPLE-hits.csv --package $HOME/mamey-work/EXAMPLE/package
```

Use the strain name the package carries. On success it prints two lines:

```text
[ingest-blastp] N hit rows across Q query genes / B BGC(s) appended to B5_BLASTp_Hits ... binding guard: A admitted, R quarantined
[ingest-blastp] nr overlay: G gene(s) across B BGC(s) -> <package>/blastp_online ...
```

Without `--package`, the second line is a `NOTE: no --package given` instead.
A `WARNING` on stderr means rows parsed but none bound to a cluster.

Read the admitted and quarantined counts before you retry a zero-row result.
Exit 0 means the workbook and overlay were updated. Exit 2 means a named file
or folder was not found. Another failure exits with a message that starts
`ingest-blastp:`; the workbook and package are left unchanged.

`--source` defaults to `NCBI web-BLASTp`. Set an accurate label for any other
origin. `--xml` adds the matching alignment XML. The reader pairs XML records
with queries by submission order, so confirm that pairing before you rely on an
exact-gene hit.

## Load per-gene result files: ingest-blastp-trove

Arrange files as `EXAMPLE/BGC.../<file>`, where each `BGC...` folder holds one
cluster's file, or point `--trove` at one strain's folder of `BGC...`
folders. Then:

```bash
python mamey_run.py ingest-blastp-trove --trove inputs/EXAMPLE-results \
  --package $HOME/mamey-work/EXAMPLE/package --channel nr
```

Choose the real channel. The accepted file names depend on it:

| `--channel` | File name patterns, in order |
|---|---|
| `nr` | `<BGC>_top_hit_per_gene.csv`, `*_top_hit_per_gene.csv` |
| `clustered_nr` | `<BGC>_blastp_top10_clustered.csv`, `*_top10_clustered.csv`, then the `nr` patterns |
| `swissprot` | `<BGC>_blastp_top10_local.csv`, `*_top10_local.csv`, then the `nr` patterns |
| `ebi` | `<BGC>_ebi_top_hit_per_gene.csv`, `*_ebi*.csv`, then the `nr` patterns |

You should see `[ingest-blastp-trove] channel=nr N BGCs, M genes ...`, plus a
quarantine line if rows were held. If it prints `NO_SOURCES_DISCOVERED`, no
file matched: it lists the layouts it accepts and writes nothing, and the exit code is still 0. If your files
are runner summaries, use the SQLite route below.

`--rekey-by-locus` matches each query gene to its current cluster through the
package's CDS table. Use it when the results came from an older package and rows
were held as `FOREIGN_BGC` or `NONCURRENT_LOCUS`. Rows that cannot be matched stay
held. For gene-keyed rows with no query length, add `--query-root` with the
lane folder that holds the query FASTA. A source strain that conflicts with the
package stops the run with `QUERY_STRAIN_CONFLICT`.

## Load runner summaries into SQLite

Point `--root` at a folder that holds files in these layouts (`*` and `**` are
wildcards):

```text
strain_data/*/blastp_nr_*/*_nr_top10_*.csv
strain_data/*/blastp_clustered_nr_*/*_clustered_nr_top10_*.csv
Blastp RESULTS/_STRAINGAP_SINGLE_CLNR_*/results/**/*_blastp_top10_clustered.csv
Blastp RESULTS/_STRAINGAP_SINGLE_NR_*/results/**/*_blastp_top10.csv
```

`Blastp RESULTS` is a literal folder name with a space. The database must be an
existing BLASTp store (this route only adds to one; it does not create it); the tool refuses one whose `hits` table does not match
the expected columns. First run it as a read-only check:

```bash
python tools/ingest_blastp_rollups.py --root inputs/EXAMPLE-rollups \
  --db $HOME/mamey-work/EXAMPLE/EXAMPLE-hits.db
```

Check the file and row inventory, the numeric values and the resolved paths.
Unreadable files, empty files, excluded strains and duplicate keys can all give
zero new rows. Then repeat with `--execute --source-workspace operator-import`.
The label is a provenance name of 1 to 64 letters, digits, dots, underscores or
hyphens, starting with a letter or digit. It is not a path. Inserts are atomic.
A repeated key (strain, channel, gene, rank, subject accession) is skipped, so a
changed measurement under an old key does not correct the earlier row.

## Check what is loaded: blastp-status

```bash
python mamey_run.py blastp-status --package $HOME/mamey-work/EXAMPLE/package
```

It prints one line per cluster, such as `BGC001  channels=nr  genes=12`. The
command reads only the package's `blastp_online/` folder. A line ending
`DISARMED -> ClusterBlast fallback`, or the message `(no blastp_online overlays present ...)`,
means no overlay rows were found there. It does not check that ClusterBlast evidence
exists or that any later step used it; read "fallback" as "no BLASTp overlay found".
Both cases exit 0. A `--package` path that is not a package folder with `manifest.json`
is refused with `BLASTP_STATUS_PACKAGE_NOT_FOUND` and a nonzero exit; it is never
reported as an empty overlay.

## Check protein bindings

Index the proteins of the package's clusters:

```bash
python -m mamey.protein_signature --package $HOME/mamey-work/EXAMPLE/package \
  --out $HOME/mamey-work/EXAMPLE/EXAMPLE-bgc-protein-signature.json
```

Run it from the bundle root so that `-m mamey` resolves to this bundle's code.
The file records gene identities, protein hashes and the source ZIP hash. It
does not admit BLASTp hits. A hit needs a saved query or job receipt that ties
each submitted query hash to its result. Matching length alone does not supply
the missing query hash.

To audit whether each result row's gene tag names the protein that was searched, you
need a CSV of result rows with a `gene` column (the query tag) and an `aa_length` column
(the query length). The tool refuses a file without both. The `blastp-online` CSV names
the tag `locus_tag`, so it does not fit as written. This audit is for older result sets
whose tags may be region positions such as `ctg16_18`:

```bash
python tools/blastp_tag_position_audit.py --antismash-zip inputs/EXAMPLE.zip \
  --rows $HOME/mamey-work/EXAMPLE/EXAMPLE-results.csv --out $HOME/mamey-work/EXAMPLE/EXAMPLE-tag-audit.tsv
```

`--out` must not exist and must be outside the bundle. A path inside the bundle fails with `OUTPUT_INSIDE_BUNDLE`. The tool never edits its inputs.

## Read the result

For each hit keep the accession, organism, identity, coverage, E-value, bitscore
and the database and query provenance. A missing translation, a failed search and
a completed search with no hit are three different states. Do not collapse them.

`blastp-followup` parses a Hit Table and writes follow-up files:

```bash
python mamey_run.py blastp-followup --hit-table inputs/EXAMPLE-hits.csv \
  --outdir $HOME/mamey-work/EXAMPLE/followup
```

It writes parsed BLASTp evidence and follow-up files (and the next FASTA batch
when you give `--panel-dir`) into `--outdir`. Compare its query IDs with the submitted roster to find queries with no result.

Treat a named homolog as a hypothesis. Check it against domain and reference
evidence. For stored RID retrieval, see the
[retrieval controls](447_COMPANION_RETRIEVAL_CONTROLS.md) and check the ledger
states even when the runner returns zero.

Continue with the [channel-separated comparison](BLASTP_NOVELTY_WORKFLOW.md) or
[result parsing](SOPs/SOP-05_BLASTP_Result_Upload_Parse_Reprioritize.md).
