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

A five-candidate, one-no-call pilot must pass before the full projection. Default limits are 100 loaded loci, 1,800 seconds per invocation, 2,500 input gene/context rows and 10,000 feature rows per locus, and 32 MiB serialized view data. Override the cohort/runtime caps explicitly in the config if necessary. Run the same command to resume verified completed partitions. Changed source, code, template, selection, partition or completed output bytes cause a hold; use a new output directory for a revised build. A crash between a partition write and its receipt leaves an explicit hold rather than accepting partial bytes. No prior source or completed output is deleted.

## Meaning and limits

The four-part identity is validated before any join: strain / full contig / region / alias. Genes join on recorded locus tag, coordinates, strand and normalized protein hash within the source-bound locus. Domain links require the existing parent binding to agree on those fields. Names alone cannot establish a link. All exact-region census rows must match both owner projections; conflicts fail closed. Raw annotations and parser projections remain available in the evidence drawer.

Coordinates are one-based inclusive. A gap is current start minus previous displayed end minus one; a negative gap is overlap. The first displayed gap is unknown. Maps use separate coordinate scales. Exact genes and sparse boundary/flank context are visually distinct. The flank source contains only owner-term matches, so gap values do not establish adjacency there. Unlinked features remain in locus evidence; a missing link is not domain absence.

Recurrence counts three coordinate-ordered exact-region genes around a source-owner CDPS CDS term match, encoding recorded term groups and strands. It counts each locus once per pattern, preserves orientation and declares the eligible-locus denominator. It does not infer orthology, nucleotide conservation, conserved pathways or shared products. No-call controls are illustrative records outside this recurrence denominator, never evidence of biological absence.

The source-pinned current50 table reports applicability to verbatim requirements and explicitly leaves completion unassessed. Older source profile metadata remains distinct. Per-locus cohort evidence-index sidecars are validated by `gene_first_explore.load_evidence_index`. BOUND describes the source-bound observation only. Unsupported channels and scientific claims are not manufactured.

Missing inputs, parse failures, source tampering, mixed census bindings and roster conflicts cannot become empty successful results. Domain states distinguish observed linked features, tested no linked feature, unavailable sparse-flank coverage, and unbound/ambiguous source features. This tool is a private candidate view. Integration, scientific review, release and publication remain separate decisions.

## Exact pilot/resume and status caveats

Source-entry relative paths resolve against the config directory. `allowed_output_root` and `pilot_receipt` are used directly as paths; use absolute paths for them, since relative values resolve against the process working directory. Pinning rejects existing SQLite WAL/SHM/journal companions. The allowed output root must already exist. External reader Python is executed after hashing; hash equality is not a sandbox or proof that its code is trustworthy (`mamey/cohort_enzyme_neighborhoods.py:27–47,166–198`).

The selector enforces five distinct candidate records for a pilot, but does **not** require that any no-call control exists. Full selection uses up to the first five no-call records; the receipt's fixed scope text (“one”/“five” real no-call controls) can therefore overstate the actual control count. Verify selected identities and denominators, not that prose. `source_no_call_loci` is calculated as all source loci minus candidates, which is only a tested-no-call count if the source roster contains no other states. A full build checks the pilot receipt hash, PASS and source dictionary, but does not compare that pilot's builder/template hashes or selected controls against the current builder; require a separately verified pilot binding before adopting that prerequisite (`199–219,280–315`).

Within a build, source/builder/template/selection pins and per-partition seals guard resume. They do not authenticate the final manifest independently: SOURCE_MANIFEST.json holds output hashes but is excluded from its own hash map. Preserve its hash in an external receipt. Do not treat a modified manifest that drops an output entry as independently validated completeness. After partial writes, keep completed partitions in place and follow the explicit content hold rather than deleting or rebuilding source evidence (`219–267,314–315`).

`BUILD_AUDIT.json` PASS and console `EXTRACTION_QC_PASS_CANDIDATE` mean projection/join checks, not current50 completion, owner acceptance or scientific validation. Missing source/parse/hold failures exit 2; unexpected dependency/schema exceptions can still terminate outside those typed catches. Inspect exit status, current receipt and full output roster. Inspect the generated view and preserve its actual build/visual-review status (`319–331`).
