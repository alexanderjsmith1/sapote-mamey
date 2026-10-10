# Companion provisioning and retrieval controls in the unsealed .447 candidate

## Completion is scoped to the operation

A lane `run` exit 0 means its bounded loop ended normally, not that every query completed. Its final log may include failures and saved in-flight RIDs (`tools/blastp_crawl/nr_rid_runner.py:840–850`). Read ledger states and admission/generation receipts. `query_unbound`, `retrieval_unverified`, `unsure` and `submit_failed_parked` remain holds, not completed no-hit observations. Do not edit a hold merely to obtain a green count.

Rebuild processes only `fetched` rows and requires their admission binding before publishing (`:860–882`). It can return 0 with zero groups when none are fetched; success does not clear held or unsubmitted work. Admission checks database, raw/query hashes, exact header roster, result-file roster and generation hashes (`:536–559`). Run reclassifies unbound fetched rows as `query_unbound` (`:602–628`). The `fetched` label alone is insufficient.

Current local ingestion routes have distinct writes. `blastp-followup` writes review side artifacts. `ingest-blastp` requires `--master`, `--strain`, `--hit-table`, accepts optional `--xml` and `--package`, and can write workbook/package evidence. Its source defaults to NCBI web-BLASTp; EBI input needs explicit `--source` (`mamey/cli.py:6911–6929`). See [the follow-up reader guide](BLASTP_FOLLOWUP_v9.7.142.md) and [the current protocol](ONLINE_BLASTP_PROTOCOL.md).

This page documents proposed engineering controls. It supplies no biological or activity interpretation.

## Companion installation

Activate a virtual environment. The lean checkout has no guaranteed wheel pool. `pip install -e '.[addons]'` installs the Python comparison/science dependencies through the configured pip index. This is an online provisioning action; it does not install companion executables or external databases.

`bash bundle_support/install_sapote_addons.sh /path/to/wheels` remains offline. Add `--online` to explicitly permit an index fallback for missing wheel resolution, including a checkout without wheels. Other installation failures remain failures. The script verifies imports only; external data, HMMs and executable availability require separate checks.

`mamey doctor` distinguishes an available Rscript from an admitted R package. Optional R renderer integration tests use the same bounded `requireNamespace` probe and skip with an unverified reason when required packages cannot be admitted. A skipped renderer integration is not a successful render.

## Scanner subset provisioning

The bundled `bundle_support/scanner_pfam_35_accessions.txt` and `scanner_pfam_148_accessions.txt` contain exact versioned accessions verified against actual historical model headers and corresponding manifests. `scanner_accession_source_pins.json` records those source hashes. These selector files contain no model payloads.

An operator with HMMER (`hmmfetch`, `hmmpress`) and a local Pfam source can provision a new-source subset:

```sh
python tools/build_scanner_hmm.py --source /path/to/Pfam-A.hmm --preset 148 --out /path/to/scanner_pfam_150.hmm
```

Use `--preset 35` for the smaller selector list, or `--accessions /path/to/selectors.txt` for an explicit list; those switches are mutually exclusive. Selector files may have blank/comment lines, but the effective selectors must be nonempty, unique `PF` accessions. The syntax accepts an optional version; admission then requires each `hmmfetch` response to contain exactly one matching ACC string and one model terminator. Use the intended exact versioned selectors: a versionless request that returns a versioned ACC is refused rather than silently substituted.

Presets select the current bundled text file. The builder hashes the file it consumes but does not consult `scanner_accession_source_pins.json`, compare its hash/count to the historical preset pin or enforce that a modified preset still has 35/148 models. Check the selected list/hash/count against the intended source pin independently; the output filename `scanner_pfam_150.hmm` is a naming convention, not a validated 150-model census.

The builder requires fresh HMM, four index and receipt paths and copies fetched stdout unchanged into the subset. A zero-return `hmmpress` call plus existence of all four index files is its index admission check; it does not independently test nonempty/valid indices or run a scanner. The build receipt records source/list hashes, exact selectors and output HMM/index hashes. Set `SM_HMM_DB` only after reviewing the actual roster/receipt and separately required scanner compatibility. This builds a source-bound artifact, not historical HMM reconstruction, a completed scan or scientific acceptance.

### Scanner build publication and recovery

Use a fresh output basename outside source evidence and the code bundle. The builder creates its parent, stages in a temporary sibling directory, and publishes the HMM, four indices and `<out>.build_receipt.json` through separate no-replace hard links. An existing target, including a dangling symlink, is refused; a concurrent target claimant also makes that link fail. Ordinary caught publication failures unlink this invocation's already-published paths, but the set is not crash-atomic. A process interruption or cleanup failure can leave a partial target set or stage, which a retry refuses. Preserve the partial attempt/diagnostics and use a fresh basename after resolving the cause; do not delete source models or claim completion from a lone HMM/index file.

The CLI emits no success JSON on stdout; read the saved receipt and verify the full six-file roster. Receipt hashes cover the five HMM/index artifacts, not the receipt itself; it also lacks builder/binary hashes, HMMER versions and saved native logs. Capture the invocation/exit status and retain those additional bindings separately. Native commands have no timeout. Their failure output is captured internally but not saved in a diagnostic receipt/log; the CLI can show only the called-process summary after the temporary stage is removed. An error is a provisioning hold, not absent Pfam capacity. `COMPLETE_NEW_SOURCE_BUILD` records this build operation alone.

## Protein input admission

`protein_pcoa_ordinate.py extract` applies the same region/reference filename admission to ZIPs and extracted directories: `*.region*.gbk` or names beginning `BGC` and ending `.gbk`. Full-genome GBKs outside that policy appear in the rejected-file ledger. Directory symlinks are traversed once by resolved directory identity; loops and file aliases are recorded, and dangling aliases, repeated admitted ZIP member names and traversal errors fail closed. The extractor reports followed symlink folders and discovered file counts.

The extract receipt records admitted, rejected and duplicate source material. Metadata adds a source digest, source record, region, locus identity and assembly binding type. Without an explicit assembly table, the assembly field is a `SOURCE_RECORD_ID` namespace, not an inferred biological assembly. Exact copies with the same source class/record/region binding are deduplicated; differing bytes under that binding are refused. Independent loci remain distinct even if their protein sequences are identical.

Independent assemblies sharing otherwise identical identifiers and bytes require `--assembly-table /path/to/assemblies.tsv`, with `input` (the supplied ZIP or directory path) and `assembly` columns. Use distinct assembly values for independently sampled material; use the same value for alternative transports of the same source. Blank/repeated bindings are refused. The table digest is included in the receipt. Archive display labels retain their existing naming convention; the bound population identities and counts are transport independent.

## RID retrieval and checkpoints

The RID runner binds new submissions to the query file digest, exact header roster and requested database. A returned XML Search must have a complete supported structure and exactly the submitted roster; malformed, HTTP-error, partial, repeated-query or wrong-query responses cannot become completed empty evidence. Valid completed no-hit searches are admitted without resubmission. Raw attempts (including returned transport-error bodies), their digests, and per-query admission states are retained. Unverified retrievals retry the existing RID rather than creating another submission.

Unknown legacy bindings, database mismatches, missing queries, changed queries, and legacy completion without admission receipts are operator holds (`query_unbound`). They are not silently resubmitted or certified by coverage. Expiry still identifies the RID's own row and marks it `unsure`. The runner does not manufacture a missing historical query binding.

The transport requires a curl supporting `--fail-with-body`; an older curl fails visibly and leaves retrieval unverified.

A POSIX flock provides exclusive lane ownership before a run or rebuild; platforms without that facility refuse ownership. The PID remains advisory and is removed only by its owner. Ledger and raw checkpoints use unique staged atomic replacements. Each top10/top1 pair carries a generation receipt; a pending result transaction is recovered under lane ownership before subsequent writes. Ordinary interrupted publication restores the previous pair; recovery accepts a fully published receipt-bound generation or restores its preserved predecessor. Result files must be read with their generation receipt, since two ordinary filenames cannot provide a simultaneous multi-file filesystem replacement. External consumers that ignore the receipt are outside this consistency guarantee.

No lock is stolen automatically. Preserve a pending transaction and its journal after a recovery failure for operator diagnosis. Rebuild validates receipts and queries before publishing each result group. A query hash mismatch or unbound old completion requires explicit operator reconciliation, rather than an automatic migration. These controls concern local files and retrieval status; they do not assert scientific readiness.
