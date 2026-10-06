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
