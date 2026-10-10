# cluster_discovery — candidate assembly lookup from a marker

The tool maps marker-protein similarities to candidate assemblies through an injectable
BLAST/IPG service interface. A homolog is candidate evidence; this lookup does not
establish cluster presence, physical linkage, compound identity or activity.

## Usage

    python tools/cluster_discovery.py \
        --marker marker.faa --entrez "Streptomyces[Organism]" \
        --min-identity 60 --max-strains 20 --outdir OUT

A completed interaction writes `candidate_strains.csv` and download_genomes.sh.
Review the candidate identities before any separately authorized downstream download
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

## Validation boundary

Tests use fake service replies only. No online search or live database is used in the
repair validation. The legacy text-parser format and service-version compatibility
remain bounded admission assumptions; unsupported responses fail rather than being
reported as completed empty evidence. Scientific marker specificity and downstream
confirmation are separate from service completion.

## Source selection, network and output receipt limits

The default CLI constructs the live `Net` service; it is an online BLAST/IPG interaction, not a local lookup or dry run. Service submission and any download are separately authorized actions. The marker parser takes only the first FASTA record and does not reject additional records. Preserve its exact record identity and complete file hash; retain the actual request/retrieval receipt separately from the example invocation.

IPG admission checks an assembly's GCF_/GCA_ prefix, not full versioned accession syntax or curator authority. Ranking retains the best marker identity per assembly and may stop once three times the requested maximum candidates have accumulated; it is a bounded candidate list, not an exhaustive assembly census. A service READY state is not scientific reference admission (`tools/cluster_discovery.py:83–169,189–205`).

The writer overwrites the candidate CSV and shell file directly, without source/output hashes, a RID-bearing completion receipt or a two-file transaction. The generated output at `out_dir / "download_genomes.sh"` (not a shipped tool) contains only GCF accessions (GCA candidates are omitted), clips their combined string at 4000 characters and is still written for an empty completed result. Do not execute that file as a complete validated download plan; inspect the actual candidate table and separately approve the exact accession roster. Retain the RID, parameters, observed response provenance and hashes separately. Zero exit can mean a completed empty list, whereas interrupted publication can leave partial or stale outputs (`172–211`). Use a fresh candidate destination and preserve earlier evidence in place.
