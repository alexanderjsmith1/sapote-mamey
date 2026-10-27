# antiSMASH intake requirements

Use [the intake SOP](../SOPs/SOP-01_Intake_RawAntiSMASH_vs_MameyPackage.md) to classify an upload. Use [installation](../INSTALL.md) to set up the bundle environment.

## What the run command consumes

`python mamey_run.py inspect <antiSMASH.zip>` previews an existing antiSMASH ZIP. `run --input-zip <antiSMASH.zip>` runs the extraction.

A nucleotide genome FASTA alone is not an antiSMASH ZIP and cannot replace it. Getting antiSMASH results is a separate workflow. `run --accession` is only a placeholder: it does not download or preprocess accessions. Without `--input-zip` it exits with `UNSUPPORTED_ACCESSION_MODE`.

A useful archive holds region GenBank records, the source sequence and metadata, and any JSON, KnownClusterBlast, ClusterBlast and report files that antiSMASH wrote. Missing comparator evidence stays unavailable. Do not infer it from a class label. A single-region accession ZIP is valid, but it covers only that one region's sequence.

## Optional evidence

Protein FASTA and separately generated HMMER or DIAMOND results can support later review. Having them does not fill every workbook evidence field automatically. See [protein input limits](PROTEIN_FASTA_WORKFLOW.md), [HMMER](HMMER_DATA_WORKFLOW.md) and [DIAMOND](DIAMOND_DATA_WORKFLOW.md) for what each one feeds today.

Keep the original input files unchanged and record their hashes. Write each run to a new output folder you are allowed to use. `inspect` is only a preview. A clean inspection is not a completed or validated analysis. After a run, validate the actual package path. Keep its warnings and unresolved fields.

## Record-limit warnings and coverage

Check [record-cap coverage](../ANTISMASH_INPUTS_CONSUMED.md#antismash-record-cap-coverage) before you treat the extracted inventory as a count of the whole input. `RECORD_LIMIT_TRUNCATION` records a log message that the parser recognized. If that issue is absent, it does not prove every eligible record was scanned.

Keep the upstream antiSMASH settings and logs with the package. Also keep the scope of records that were scanned and skipped. Compare the assembly-input scope with the region-input scope before you use a count or a warning.
