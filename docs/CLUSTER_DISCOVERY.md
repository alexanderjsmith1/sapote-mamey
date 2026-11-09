# cluster_discovery — candidate assembly lookup from a marker

The tool maps marker-protein similarities to candidate assemblies. **It contacts NCBI live** (an online BLAST and IPG lookup), so run it only when a network request is approved. It is not a local lookup or a dry run. A homolog is candidate evidence; this lookup does not
establish cluster presence, physical linkage, compound identity or activity.

## Usage

    python tools/cluster_discovery.py \
        --marker marker.faa --entrez "Streptomyces[Organism]" \
        --min-identity 60 --max-strains 20 --outdir OUT

| Flag | Meaning | Default |
|---|---|---|
| `--marker` | Marker protein FASTA. Only the first record is used; extra records are not rejected. | required |
| `--entrez` | Entrez organism filter | `Streptomyces[Organism]` |
| `--evalue` | E-value cutoff | 1e-40 |
| `--min-identity` | Minimum percent identity to keep a hit (use 0 to 100; not checked) | 0 |
| `--max-strains` | Most candidate assemblies to keep (use a positive number; not checked) | 50 |
| `--outdir` | Output folder | `cluster_discovery_out` |

A completed run writes `candidate_strains.csv` and a generated download script, download_genomes.sh, in `--outdir`, and exits 0. The console prints how many strains were written. `candidate_strains.csv` has the columns `assembly`, `organism`, `strain`, `marker_identity_pct` and `marker_protein`, one row per candidate assembly. The download script calls the NCBI `datasets` command-line program, which you must install separately. A typed failure exits 2 and writes no completed table (see below): an unreadable marker file (`INPUT_FAILED`), a typed discovery failure, or a network or service error (`SERVICE_FAILED`). An output write error is `OUTPUT_FAILED`, also exit 2, and can leave partial files. Treat any nonzero exit, including an unexpected Python traceback (exit 1), as an incomplete run. Review the candidate identities before any separately authorized downstream download
or analysis. This tool has no `--verify` option.

## Incomplete interactions

A completed result requires an observed READY state. Exhausted polling raises TIMEOUT
without fetching results. Unparsed text without a recognized no-hit response raises
RESULT_PARSE_UNVERIFIED. Failed or malformed IPG resolution raises ASSEMBLY_UNRESOLVED,
or PARTIAL when some candidate rows were recovered. The CLI returns 2 for these states
and writes no completed candidate table. The importable DiscoveryFailure retains RID,
status and any partial rows. Existing files from an earlier run are not deleted;
consumers must check the current exit status.

A standalone starred `***** No hits found *****` response line can complete with an empty list;
prose merely containing that phrase and conflicting hit/no-hit markers are refused.
Parsed hits filtered out by the requested identity threshold can also yield an empty
candidate list; neither case establishes biological absence.

## Source selection, network and output receipt limits

Service submission and any download are separately authorized actions. Preserve the marker's exact record identity and complete file hash; retain the actual request/retrieval receipt separately from the example invocation.

IPG admission accepts only a complete versioned assembly accession (`GCF_` or `GCA_`, nine digits, `.` and a version); any other assembly value from the service is not admitted. It does not check curator authority. Ranking retains the best marker identity per assembly and may stop once three times the requested maximum candidates have accumulated; it is a bounded candidate list, not an exhaustive assembly census. A service READY state is not scientific reference admission.

The writer overwrites the candidate CSV and shell file directly, without source/output hashes, a RID-bearing completion receipt or a two-file transaction. The generated output at `out_dir / "download_genomes.sh"` (not a shipped tool) contains only GCF accessions (GCA candidates are omitted), each revalidated and shell-quoted, and is still written for an empty completed result. Service text is never placed in the script unchecked. Treat a script from an earlier version of the tool, which did not quote or fully validate accessions, as untrusted until you have read it. The console ends with a hint to run the download script. Do not run it as a validated download plan; inspect the actual candidate table and separately approve the exact accession roster. Retain the RID, parameters, observed response provenance and hashes separately. Zero exit can mean a completed empty list, whereas interrupted publication can leave partial or stale outputs. Use a fresh candidate destination and preserve earlier evidence in place.
