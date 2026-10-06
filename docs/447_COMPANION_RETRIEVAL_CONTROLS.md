# Companion provisioning and retrieval controls in the unsealed .447 candidate

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

Use `--preset 35` for the smaller selector list, or `--accessions /path/to/selectors.txt` for an explicit list. Selectors must match exactly, including versions. A source missing the pinned versions is refused. The builder requires fresh output/index/receipt paths, preserves each fetched model unchanged, verifies all four pressed indices, and records source, selector and output hashes. Set `SM_HMM_DB` to the output after reviewing the build receipt. This builds a source-bound artifact; it does not reconstruct or certify historical HMM bytes.

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
