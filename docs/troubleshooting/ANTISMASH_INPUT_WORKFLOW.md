# antiSMASH intake requirements

Use [the intake SOP](../SOPs/SOP-01_Intake_RawAntiSMASH_vs_MameyPackage.md) to classify an upload and [installation](../INSTALL.md) for the selected bundle environment.

## What the run command consumes

`python mamey_run.py inspect <antiSMASH.zip>` previews an existing antiSMASH ZIP. `run --input-zip <antiSMASH.zip>` performs extraction. A nucleotide genome FASTA alone is not an antiSMASH ZIP and cannot replace it. Obtaining antiSMASH results is a separate workflow; this bundle's `run --accession` placeholder does not download or preprocess accessions.

A useful archive contains region GenBank records, source sequence/metadata and any available JSON, KnownClusterBlast, ClusterBlast and report files. Missing comparator evidence must remain unavailable rather than be inferred from a class label. A single-region accession ZIP is valid but supports only that limited sequence scope.

## Optional evidence

Protein FASTA and independently generated HMMER or DIAMOND results can support later review. Their presence does not make every workbook evidence field populate automatically. See [protein input limits](PROTEIN_FASTA_WORKFLOW.md), [HMMER](HMMER_DATA_WORKFLOW.md) and [DIAMOND](DIAMOND_DATA_WORKFLOW.md) for the current integration boundaries.

Keep original input bytes immutable, record their hashes, and write a new authorized run output. `inspect` is a preview; successful inspection is not a completed or validated analysis. After a run, validate the actual package path and retain warnings and unresolved fields.

## Record-limit warnings and coverage

Check [record-cap coverage](../ANTISMASH_INPUTS_CONSUMED.md#antismash-record-cap-coverage) before treating the extracted inventory as a whole-input census. `RECORD_LIMIT_TRUNCATION` records a recognized log message; no such issue does not prove every eligible record was scanned. Keep upstream settings/logs and scanned/skipped record scope with the package. Compare actual assembly-input scope with region-input scope before using a count or warning.
