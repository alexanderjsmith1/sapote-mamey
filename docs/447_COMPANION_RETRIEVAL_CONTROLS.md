# Companion setup, scanner HMMs, protein input and BLASTp checkpoints

This page covers four setup and retrieval tasks that sit beside the main pipeline:

1. installing the optional Python companions;
2. building the scanner Pfam HMM subset;
3. what the protein-space extractor accepts;
4. how the BLASTp RID runner tracks, retries and saves searches.

None of these steps interprets biology.

<a id="companion-installation"></a>
## 1. Install the optional companions

Activate a virtual environment before these installation commands.

```bash
python -m pip install -e '.[addons]'                         # online, through your pip index
bash bundle_support/install_sapote_addons.sh /path/to/wheels  # offline, from local wheels
bash bundle_support/install_sapote_addons.sh --online         # offline first, index for missing wheels
```

The `addons` extra installs Python comparison and scanner dependencies. It installs no external programs and no
databases. The add-on script stays offline unless you pass `--online`, which allows the pip index for
wheels it cannot find locally. Invalid core installation failures still fail. Its separate figure/analysis group is best-effort and can remain unavailable while core verification succeeds. The script checks selected core imports, not every installed dependency; data files, HMMs and external programs need their own checks.

Before `doctor`, read its [write-probe boundary](INSTALL.md#doctor-scope-and-write-probe) and use an editable working install. An occupied `runs/_doctor_probe` is refused; leave it intact.

`python mamey_run.py doctor` reports whether `Rscript` is present and, separately, whether each R
package loads. A package that loads is not a figure that rendered. In the test suite, the shared
`require_r_packages` fixture skips a test when a package is `UNAVAILABLE` and fails it when the probe
is `UNVERIFIED`.

<a id="scanner-subset-provisioning"></a>
## 2. Build the scanner Pfam HMM subset

The bundle ships accession lists, not models:

- `bundle_support/scanner_pfam_35_accessions.txt` and `scanner_pfam_148_accessions.txt` list exact,
  versioned Pfam selectors.
- `bundle_support/scanner_accession_source_pins.json` records the hashes of those historical sources.

With HMMER (`hmmfetch`, `hmmpress`) and a local `Pfam-A.hmm`, build a subset:

```bash
python tools/build_scanner_hmm.py --source /path/to/Pfam-A.hmm --preset 148 --out /path/to/scanner_pfam_150.hmm
```

- Choose one of `--preset 35`, `--preset 148` or `--accessions /path/to/list.txt`.
- An accession list may contain blank and `#` lines. The rest must be unique `PF` accessions, with or
  without a version. Each `hmmfetch` result must hold exactly one matching `ACC` line and one model.
  Asking for an unversioned accession and getting a versioned one is refused, not substituted.
- A preset reads the bundled list as it is now. The builder hashes that list but does not compare it
  with the source pins or check the model count. Check the list, hash and count yourself. The name
  `scanner_pfam_150.hmm` is a naming convention, not a 150-model count.
- After the build, set `SM_HMM_DB` to the new file.

**Outputs.** The builder writes six files: the HMM, its four `hmmpress` indexes (`.h3f`, `.h3i`,
`.h3m`, `.h3p`) and `<out>.build_receipt.json` with status `COMPLETE_NEW_SOURCE_BUILD`. It prints no
success message, so read the receipt. The receipt hashes the source, the list, the selectors and the
five HMM/index artifacts. A successful `hmmpress` exit and the four files' existence are its index check; it does not prove nonempty, valid indexes or a successful scanner run. The receipt does not hash itself and does not record HMMER versions or native logs; record
those yourself.

<a id="scanner-build-publication-and-recovery"></a>
**Failures.** Use a new output name, outside the bundle and away from source files. The builder
refuses any existing target, including a broken symlink. It stages files in a temporary folder and
publishes them one by one. If publishing fails normally it removes what it published, but a crash can
leave a partial set, and a retry then refuses. Keep the partial attempt, fix the cause and rerun with
a new name. `hmmfetch` and `hmmpress` have no timeout, and their error output is not saved. A failed
build is a setup problem, not evidence that a Pfam family is absent.

<a id="protein-input-admission"></a>
## 3. Protein input for `protein_pcoa_ordinate.py extract`

```bash
python tools/protein_pcoa_ordinate.py extract --kit /path/to/new_kit \
  --input isolate=/path/to/strainA.zip --input reference=/path/to/region_gbk_folder \
  [--assembly-table /path/to/assemblies.tsv]
```

`--input` can be repeated and requires `SOURCE=PATH`, with `SOURCE` one of `isolate`, `reference`, `SID` or `MIBiG`; the path is a ZIP or folder. Reference and SID inputs retain their `reference_held`/`SID_held` source classes. For an assembly table, the `input` column is the path alone, without the `SOURCE=` prefix.

- **Accepted files.** In ZIPs and folders alike: `*.region*.gbk`, and names that start with `BGC` and
  end with `.gbk`. Whole-genome GenBank files go to the rejected-file list.
- **Symlinks.** Each linked folder is read once. Loops and file aliases are recorded. Broken links,
  repeated ZIP member names and read errors stop the run.
- **Receipt.** `EXTRACT_RECEIPT.json` lists admitted, rejected and duplicate files. Metadata records the
  source digest, record, region, locus identity and how the assembly was identified.
- **Duplicates.** Identical bytes under the same source class, assembly binding, record ID and region filename are kept once. Different
  bytes under the same identity are refused. Identical proteins at different loci stay separate.
- **Assemblies.** Without `--assembly-table`, the assembly field is just the source record ID. Two
  independent genomes with identical names and bytes need the table. Its columns are `input` (the ZIP
  or folder path) and `assembly`. Give independent samples different values and alternate copies of
  the same source the same value. Blank or repeated rows are refused. The table hash goes in the
  receipt.
- **Use a new kit folder.** FASTA names are checked before writing, but the metadata tables and
  `EXTRACT_RECEIPT.json` are not. A failed run can leave partial files; keep them and start fresh.

<a id="completion-is-scoped-to-the-operation"></a>
<a id="rid-retrieval-and-checkpoints"></a>
## 4. BLASTp RID runner (`tools/blastp_crawl/nr_rid_runner.py`)

The runner submits query batches to NCBI BLAST, polls them by request ID (RID) and saves results. Its
subcommands are `run`, `status`, `rebuild` and `coverage`. It needs a `curl` that supports
`--fail-with-body`; an older `curl` fails visibly.

**Row states.** A query row is only a completed result when it is fetched and admitted. These states
are holds, not "no hit" results: `query_unbound`, `retrieval_unverified`, `unsure`,
`submit_failed_parked`. Do not edit a hold to make a count look complete.

- `run` exits 0 when its loop ends, not when every query finished. Its last log lines can list failures
  and RIDs still in flight. Read the ledger states.
- Each new submission is tied to the query file hash, the exact FASTA header list and the database.
- A returned XML result must be complete and match the submitted header list. Malformed, HTTP-error,
  partial, repeated-query or wrong-query results never count as an empty search. A valid search with
  no hits is accepted without resubmitting.
- An unreadable result retries the same RID. After three saved downloads that cannot be read, the row
  becomes `unsure` and leaves the in-flight set. The count survives a restart. Network errors are not
  counted. Raw responses are kept.
- A row older than `--max-wait` (default 129,600 s, 36 h) becomes `unsure`. `unsure` rows are not
  resubmitted automatically. A service `UNKNOWN` reply instead marks the row `expired`, which a later
  run will resubmit. Check the old RID before restarting.
- Unknown legacy bindings, database mismatches, missing or changed queries and old completions without
  receipts become `query_unbound`. They are never resubmitted automatically.
- `rebuild` publishes only `fetched` rows that pass the admission check (database, raw and query
  hashes, header list, result-file list and generation hashes). It can exit 0 with nothing rebuilt.
  `run` reclassifies a fetched row without that binding as `query_unbound`.

**Packet coverage.** Each `_result_generation.json` records `genes_done`, `genes_expected` and `complete`. Completion is true only for a nonempty expected gene roster whose members are all done, including completed no-hit genes. A partial packet can grow as another query batch returns. Treat `complete` as necessary coverage of the recorded roster, alongside current query bindings and admission/generation hashes; it is not scientific acceptance.

**Saving and locking.** A POSIX `flock` gives one process ownership of a lane; systems without `flock`
refuse. The PID file is advisory. Ledgers and raw checkpoints are written atomically. Each top-10 and
top-1 result pair carries a generation receipt; read the two files together with that receipt. An
interrupted publication is recovered under lane ownership: it accepts an already fully published, hash-matching generation or restores the preserved predecessor. Two filenames do not give readers a simultaneous multi-file replacement; consumers must use the generation receipt. Locks are never taken over automatically. If recovery
fails, keep the pending transaction and its journal for diagnosis.

**Importing results.** `blastp-followup` writes review files beside your outputs. `ingest-blastp`
writes into the workbook and, with `--package`, the package:

```bash
python mamey_run.py ingest-blastp --master <workbook.xlsx> --strain <ID> --hit-table <hits.csv> \
  [--xml <alignment.xml>] [--package <package>] [--source "EBI (uniprotkb_bacteria)"]
```

`--source` defaults to NCBI web-BLASTp; pass it for EBI results. See
[BLASTp follow-up](BLASTP_FOLLOWUP_v9.7.142.md) and the [BLASTp protocol](ONLINE_BLASTP_PROTOCOL.md).
