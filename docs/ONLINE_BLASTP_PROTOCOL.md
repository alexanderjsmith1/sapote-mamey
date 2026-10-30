# Use BLASTp evidence

Use an installed bundle to import saved results or plan an online search.
Run the commands from its folder. Planning needs the query source; workbook
imports need the master workbook; collection imports need the package; SQLite
imports need an existing hits store. Keep query identifiers, protein hashes
and original query/job receipts with the results.

Keep nr, ClusteredNR and Swiss-Prot in separate channels. Record every locus as
**strain / full node-or-contig / region / BGC alias**.

## Plan a search

Select one BGC through its matching package crosswalk:

```bash
python mamey_run.py blastp-online --package inputs/EXAMPLE.zip \
  --bgc BGC001 --crosswalk runs/EXAMPLE/package
```

The default prints protein and residue counts, batches, database, endpoint and
sequence digest. `PLAN ONLY` means nothing was sent. Check the full locus and
query set before approving an upload. A region GBK can also supply the proteins.

Defaults are nr and ten proteins per batch, with residue limits and separate
batches for proteins over 2,500 residues. Choose `--database` for
`refseq_protein` or `swissprot`; ClusteredNR uses its separate workflow.

Approved submission requires both `--submit` and
`--confirm-public-sequence-upload`. Choose `--outdir` when submitting and keep
the RIDs, raw responses, diagnostics and submitted roster. Reconcile every batch;
one can fail while another returns results.

## Import an NCBI HitTable into a workbook

Use the original **headerless outfmt 10 CSV with 12 or 13 columns**.
Headered per-gene and runner summaries use the collection or SQLite routes below.
Choose working copies of the master workbook and package:

```bash
python mamey_run.py ingest-blastp --master reviews/EXAMPLE-master.xlsx \
  --strain EXAMPLE --hit-table inputs/EXAMPLE-hits.csv --package reviews/EXAMPLE/package
```

This updates the workbook and package overlay; there is no dry run. Read the
admitted/quarantined and bound/unbound counts before retrying a zero-row append.
`--source` defaults to `NCBI web-BLASTp`; choose accurate provenance for another source.

Add `--xml` for matching alignment XML. The XML reader assigns records by
submission order; verify independent query/result bindings before using an exact-gene hit.

## Import a per-gene collection

Use supported filenames under `EXAMPLE/BGC.../`, or a single-strain root
containing `BGC...` directories. Preserve the original package:

```bash
python mamey_run.py ingest-blastp-trove --trove inputs/EXAMPLE-results \
  --package reviews/EXAMPLE/package --channel nr
```

Choose the actual channel. `--rekey-by-locus` resolves historical aliases through
the current CDS table; a conflicting source strain stops with `QUERY_STRAIN_CONFLICT`.

`NO_SOURCES_DISCOVERED` lists accepted layouts. It creates no ingest overlay or
receipt, although the CLI can refresh package integrity files. A discovered
source with zero admitted rows has different receipt/quarantine evidence.

## Import runner rollups into SQLite

Point `--root` at a directory containing these supported layouts:

```text
strain_data/EXAMPLE/blastp_nr_*/*_nr_top10_*.csv
strain_data/EXAMPLE/blastp_clustered_nr_*/*_clustered_nr_top10_*.csv
Blastp RESULTS/_STRAINGAP_SINGLE_CLNR_*/results/EXAMPLE/**/*_blastp_top10_clustered.csv
```

The existing database needs the canonical 22-column `hits` schema. Start read-only:

```bash
python tools/ingest_blastp_rollups.py --root inputs/EXAMPLE-rollups \
  --db reviews/EXAMPLE-hits.db
```

Check the found file/row inventory, numeric values and resolved source paths.
Read errors, empty files, excluded strains and duplicate keys can give zero new rows.

After that review, repeat the command with
`--execute --source-workspace EXAMPLE-results`. The required portable label records
where the imported rows came from; replace it with your logical source name.
Inserts are atomic and repeated keys are skipped. The key uses strain, channel,
gene, rank and subject accession; changed measurements under that key do not
correct an earlier row.

## Check protein bindings

Make a fresh index of the package's BGC-member proteins:

```bash
python -m mamey.protein_signature --package runs/EXAMPLE/package \
  --out reviews/EXAMPLE-bgc-protein-signature.json
```

It records gene identities, protein hashes and the source ZIP hash. Keep the
saved query/job receipt to bind a search result. For per-strain exports from a
22-column store, `mamey.blastp_strain_db` keeps separate held/unbound rows and
one consistent source snapshot; budget one extra database size and fresh outputs.
Length agreement alone cannot supply the store's missing query-protein hash.

## Read the result

Keep accession, organism, identity, coverage, E-value, bitscore and database/query
provenance for each hit. Missing translation, failed search and completed no-hit
results are separate states. Compare `blastp-followup` query IDs with the submitted
roster to find missing queries.

Treat a named homolog as a hypothesis to check with domain and reference evidence. Use
`blastp_tag_position_audit.py` for historical locator checks. For stored RID
retrieval, read [retrieval controls](447_COMPANION_RETRIEVAL_CONTROLS.md) and check
ledger states even when the runner returns zero.

Continue with [channel-separated comparison](BLASTP_NOVELTY_WORKFLOW.md) or
[result parsing](SOPs/SOP-05_BLASTP_Result_Upload_Parse_Reprioritize.md).

<a id="start-with-identity-and-evidence-availability"></a>
<a id="inspect-the-current-commands"></a>
<a id="ingesting-existing-results-choose-the-destination"></a>
<a id="batching-and-execution"></a>
<a id="outputs-and-interpretation"></a>
<a id="optional-per-strain-blastp-databases"></a>
<a id="related-workflows"></a>
<a id="rid-runner-completion-and-stored-result-admission"></a>
