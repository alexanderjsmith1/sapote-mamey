# Enzyme neighborhood explorer

This optional local view compares source annotations around existing DKP/CDPS owner candidates. It reuses the supplied immutable DKP and architecture readers and the shared gene-census reader. It performs no new biological scan or sequence search and creates no database copy. Open the generated `explorer.html` directly in a browser; it uses no external assets or network requests.

## Build and resume

From a bundle containing the shared `tool_database_reader` prerequisite:

```sh
python tools/build_enzyme_neighborhoods.py --config /work/evidence/view-config.json --out /work/derived/pilot --pilot
python tools/build_enzyme_neighborhoods.py --config /work/evidence/view-config.json --out /work/derived/run001
```

Supply JSON with `allowed_output_root`, `population`, `pilot_receipt`, `pilot_receipt_sha256` (after the pilot finishes), and `sources`. Each source entry has a `path` and exact SHA-256 in `sha256`. Source-entry paths may be absolute or relative to the config file; use absolute output-root and pilot-receipt paths (see caveats below). Explicit source keys are `dkp_manifest`, `dkp_database`, `dkp_reader`, `architecture_manifest`, `architecture_database`, `architecture_reader`, `census_manifest`, `census_database`, `domain_manifest`, `domain_database`, and `current50_contract`. The external reader files are trusted executable dependencies selected and pinned by the operator. Freeze them and all databases before running. Never supply untrusted code.

The DKP reader API is `read(database, manifest_sha256, identity, kind, limit, offset, include_raw=True)`. Its kinds are `loci`, `genes`, `cds_context`, and `domains`. The architecture API is `read(database, identity, kind, limit, offset, include_qualifiers=False)`, for `genes` and `features`. The shared census API remains `inspect_tool_database` with `gene-census-v1`. These are explicit dependencies; the widget does not rediscover evidence or choose a newest file.

A pilot must select five distinct owner candidates before a full projection; it also selects one tested-no-call control when available. Full projection includes up to five available tested-no-call controls. Inspect actual selected identities and counts. The default cap is 100 selected loci, checked after the complete source locus roster is read; it is not a source-roster loading limit. Other limits are 1,800 seconds per invocation, 2,500 input gene/context rows and 10,000 feature rows per locus, and 32 MiB serialized embedded view data. Override only the cohort/runtime caps through the config. Repeat the same command to resume verified completed partitions. Within one build, pins cover selected source files, the builder file, template and selected identities; they do not cover every imported bundled helper. Changes to those bound inputs or completed partition/output bytes cause a hold. Use a new output directory for revised bindings. A crash between a partition write and its receipt leaves a hold. Existing source evidence and completed partitions are retained.

## Meaning and limits

The four-part locus identity is checked before projection: strain / full contig / region / alias. Genes join by recorded locus tag, coordinates, strand and normalized protein hash. Exact DKP and census duplicate keys are refused, and their key sets must match the exact-region architecture key set. Architecture rows are first collapsed into a dictionary by that key, so repeated architecture keys are not separately refused and the last row supplies its retained raw projection; this is key-set parity rather than full row/cardinality equality. Domain links require the recorded parent fields to agree; names alone cannot establish a link. The drawer retains the selected DKP, census and architecture projections.

Coordinates are one-based inclusive. A gap is current start minus previous displayed end minus one; a negative gap is overlap. The first displayed gap is unknown. Maps use separate coordinate scales. Exact genes and sparse boundary/flank context are visually distinct. The flank source contains only owner-term matches, so gap values do not establish adjacency there. Unlinked features remain in locus evidence; a missing link is not domain absence.

Recurrence counts three coordinate-ordered exact-region genes around a source-owner CDPS CDS term match, encoding recorded term groups and strands. It counts each locus once per pattern, preserves orientation and declares the eligible-locus denominator. It does not infer orthology, nucleotide conservation, conserved pathways or shared products. No-call controls are illustrative records outside this recurrence denominator, never evidence of biological absence.

The source-pinned current50 table reports applicability to verbatim requirements and explicitly leaves completion unassessed. Older source profile metadata remains distinct. Per-locus cohort evidence-index sidecars are validated by `gene_first_explore.load_evidence_index`. BOUND describes the source-bound observation only. Unsupported channels and scientific claims are not manufactured.

Missing inputs, parse failures, source tampering, mixed census bindings and roster conflicts cannot become empty successful results. Domain states distinguish observed linked features, tested no linked feature, unavailable sparse-flank coverage, and unbound/ambiguous source features. This tool is a private candidate view. Integration, scientific review, release and publication remain separate decisions.

## Exact pilot/resume and status caveats

- Use absolute paths for `allowed_output_root` and `pilot_receipt`. The output root must already exist. Source-entry relative paths resolve against the config directory.
- SQLite WAL/SHM/journal files beside a database are refused.
- Reader Python files are run after hashing. A matching hash is not a sandbox.
- A pilot needs five distinct candidates. No-call controls are optional, and the receipt's scope text says "one" or "five" whatever was selected, so check the selected identities and counts. `source_no_call_loci` is all source loci minus candidates.
- A full build checks the pilot receipt's hash and PASS, not the pilot's builder and template hashes or its controls.
- `SOURCE_MANIFEST.json` is not in its own hash map; record its hash separately. After partial writes, keep completed partitions in place.
- `BUILD_AUDIT.json` PASS means the joins worked, not that current50 is complete. Missing-source, parse and hold failures exit 2; other exceptions can end the run outside those checks.
