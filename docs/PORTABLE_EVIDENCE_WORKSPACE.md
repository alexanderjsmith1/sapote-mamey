# Portable evidence-workspace interface

> Advanced. This page is for linking a larger project to the bundle. You need to hand-write three JSON files: a root configuration, a source manifest and a program spec. For a single run, use the [first-run guide](reader/01_FIRST_RUN.md) instead.

The bundle holds the engine, schemas, tests, docs and small reference assets. Your antiSMASH archives, assemblies, BLASTP databases, literature and results stay outside it.

Two files draw the boundary between the bundle and your data:

- A **root configuration** names each logical root (such as `antismash` or `outputs`) and where it lives on disk.
- A **source manifest** lists every input file by logical ID, root, relative path and SHA-256.

Source discovery lists the folders that could hold evidence. It never admits them, and "newest file wins" is never a valid rule. The command is in [Find and dispose of sources](#find-and-dispose-of-sources).

## Refreshable report selection and recovery

For the refreshable exact-identity report, see [selection and publication](reference/06_CURRENT_SOURCE_SCOPE.md#refreshable-exact-identity-report-selection-and-publication-routes) and [evidence admission](reference/06_CURRENT_SOURCE_SCOPE.md#refreshable-report-evidence-admission-profiles-channels-and-mode-b). An omitted locus selector can select every region for the strain.

## Recommended project layout

```text
sapote-project/
  sapote-evidence-roots.json
  source-manifest.json
  program-specs/
  receipts/
  outputs/
  imports/        # optional controlled copies
  cache/          # disposable derivatives
```

Existing data does not have to move into this folder. Each logical root can point to a separate stable location.

```json
{
  "schema_version": "sapote_evidence_root_config_v1",
  "roots": {
    "antismash": {"path": "../evidence/antismash"},
    "blastp": {"path": "../evidence/blastp"},
    "literature": {"path": "../evidence/literature"},
    "legacy_reports": {"path": "../evidence/legacy-reports"},
    "outputs": {"path": "outputs"}
  }
}
```

A root path resolves in this order:

1. The `--evidence-root ROOT_ID=/ABSOLUTE/PATH` flag.
2. The environment variable `SAPOTE_EVIDENCE_ROOT_<ROOT_ID_UPPERCASE>`.
3. The configured path.

An override must be absolute and must name a root already declared in the configuration. Relative configured roots are anchored to the configuration file. In the example, `../evidence` is a sibling of the project, so moving the project folder alone does not move the evidence.

## Build the draft reports

```bash
python mamey_run.py build-bgc-drafts \
  --evidence-root-config sapote-evidence-roots.json \
  --source-manifest source-manifest.json \
  --program-spec program-specs/report-program.json \
  --evidence-root blastp=/data/current-blastp
```

The command reads the three JSON files. It does not create them. It writes the report folder named by the spec's `output`, and it refuses to run if that folder exists. On success it prints a manifest with `"status": "DRAFT_BUILT_NOT_ACCEPTED_NOT_INTEGRATED"`. That status means drafts exist, not that anyone accepted them.

### Find and dispose of sources

The spec's `source_discovery_preflight` needs two files: a catalog of collections and a decision table. Make the catalog with `scan`, then write the decisions by hand.

1. Write a collection registry. It tells `scan` which folders count as which kind of collection:

```json
{
  "schema_version": "sapote-source-collection-registry-v1",
  "default_strain_regex": "EXAMPLE",
  "rules": [
    {"collection_type": "ANTISMASH_INVENTORY",
     "directory_regex": "^antismash(/|$)",
     "material_file_regex": "inventory\\.csv$"}
  ]
}
```

Each rule needs `collection_type`, `directory_regex` and `material_file_regex`. The regexes match paths relative to the scanned folder. `strain_regex` and `root_segment_regex` are optional. A rule's `strain_regex` finds strain names in paths. Without one, the registry's `default_strain_regex` is used.

2. Scan. Run this from the bundle root. Write the catalog outside the scanned folder, and use absolute paths:

```bash
python -m mamey.workspace_source_discovery scan /ABS/sapote-project/evidence \
  --root-id evidence \
  --collection-registry /ABS/sapote-project/collection-registry.json \
  --expected-collection-registry-sha256 "$(shasum -a 256 /ABS/sapote-project/collection-registry.json | cut -d' ' -f1)" \
  --out-json /ABS/sapote-project/receipts/source-catalog.json \
  --out-tsv /ABS/sapote-project/receipts/source-catalog.tsv
```

`scan` stops at depth 6, 100,000 files, 20,000,000,000 bytes or 60 seconds unless you pass `--max-depth`, `--max-files`, `--max-apparent-bytes` or `--max-seconds`. The byte limit counts the sizes the filesystem reports for the files it lists (apparent size); the scan does not read those bytes. A stopped scan writes a catalog whose `status` is not `PASS_COMPLETE`, and the build refuses it. The catalog lists one row per collection with a `collection_id`.

A folder that matches no rule becomes an `UNCLASSIFIED_MATERIAL` collection when it holds a file with a material suffix (`.csv`, `.tsv`, `.json`, `.md`, `.docx`, `.pdf`, `.xlsx`, `.html`, `.svg`, `.gbk`, `.sqlite`) and sits no deeper than the registry's `unclassified_max_depth` (default 2). These collections need a decision too. Files that enter no collection are not dropped silently:
- A material-suffix file deeper than that limit sets `status` to `INCOMPLETE_UNCATALOGED_MATERIAL`, which the gate and the build refuse. Its folder is listed in `uncataloged_material_directories`. Add a rule for it, or raise `unclassified_max_depth`, and scan again.
- Other files outside every collection are counted in `scan_counts` and listed in `uncataloged_other_directories`. They do not change `status`; read the list.

`PASS_COMPLETE` means every material-suffix file the scan saw, within its limits, entered a collection. It is not an independently reconciled inventory of your evidence.

3. Write the decision table, tab-separated, one row per `collection_id` in the catalog:

```text
collection_id	decision	reason	evidence_receipt
COLL_df3fa19b79f4529f1f75	CONSUME		
COLL_54186ebcd55c60554725	REJECT_WITH_REASON	top-level database files, not a report source	
```

A row with a blank strain list applies to every strain, so it needs a decision as well. `reason` is required for every decision except `CONSUME`. `evidence_receipt` is required for `SUPERSEDED_WITH_RECEIPT`.

4. Check the pair before building. `gate-report` exits 0 on a pass and 3 on a failure:

```bash
python -m mamey.workspace_source_discovery gate-report \
  --catalog /ABS/sapote-project/receipts/source-catalog.json \
  --expected-catalog-sha256 "$(shasum -a 256 /ABS/sapote-project/receipts/source-catalog.json | cut -d' ' -f1)" \
  --decisions /ABS/sapote-project/receipts/source-decisions.tsv \
  --expected-decisions-sha256 "$(shasum -a 256 /ABS/sapote-project/receipts/source-decisions.tsv | cut -d' ' -f1)" \
  --strain EXAMPLE --require ANTISMASH_INVENTORY
```

A pass prints `PASS_SOURCE_DISCOVERY_AND_DECISIONS_BOUND`. A failure prints a `reason_code`, for example `MATERIAL_COLLECTION_DECISION_MISSING` with the ids to decide, or `REQUIRED_COLLECTION_TYPE_NOT_CONSUMED`. Two collections of one required type need exactly one `CONSUME` and the other marked `SUPERSEDED_WITH_RECEIPT`; otherwise the result is `PARALLEL_GENERATION_UNRESOLVED`. Hash the catalog and decision files again after every edit. The manifest must carry the new hashes.

### A minimal working set

This set builds one draft for a strain called `EXAMPLE`. Put the evidence files and the receipts under the project folder, then write the config, manifest and spec.

Root configuration, `sapote-evidence-roots.json`:

```json
{
  "schema_version": "sapote_evidence_root_config_v1",
  "roots": {
    "evidence": {"path": "evidence"},
    "receipts": {"path": "receipts"},
    "outputs": {"path": "outputs"}
  }
}
```

Source manifest, `source-manifest.json`. Take each `sha256` from `shasum -a 256 <file>`:

```json
{
  "schema_version": "sapote_portable_source_manifest_v1",
  "sources": [
    {"logical_source_id": "inventory_example", "root_id": "evidence",
     "relative_path": "antismash/EXAMPLE/inventory.csv", "sha256": "<hash>"},
    {"logical_source_id": "identity_db", "root_id": "evidence",
     "relative_path": "identity.sqlite", "sha256": "<hash>"},
    {"logical_source_id": "blastp_db", "root_id": "evidence",
     "relative_path": "blastp.sqlite", "sha256": "<hash>"},
    {"logical_source_id": "source_catalog", "root_id": "receipts",
     "relative_path": "source-catalog.json", "sha256": "<hash>"},
    {"logical_source_id": "source_decisions", "root_id": "receipts",
     "relative_path": "source-decisions.tsv", "sha256": "<hash>"}
  ]
}
```

Program spec, `program-specs/report-program.json`:

```json
{
  "schema_version": "sapote_l0_report_program_spec_v2",
  "release": "INTERNAL",
  "captured_at_utc": "2026-01-01T00:00:00Z",
  "identity_db_source_id": "identity_db",
  "blastp_db_source_id": "blastp_db",
  "inventories": [
    {"strain": "EXAMPLE", "source_id": "inventory_example", "profile": "relaxed", "allocation": 1}
  ],
  "source_discovery_preflight": {
    "catalog_source_id": "source_catalog",
    "decisions_source_id": "source_decisions",
    "required_collection_types": ["ANTISMASH_INVENTORY"]
  },
  "output": {"root_id": "outputs", "relative_path": "drafts-1"}
}
```

`allocation` is how many BGCs from that strain the roster takes. The build also needs three kinds of input file. Their formats follow.

**Inventory CSV** (comma-separated, one row per BGC):

```text
BGC_ID,Contig,Node_ID,antiSMASH_Region,Products,Length_kb,Boundary,Start,End
BGC001,NODE_7_length_90000_cov_40.0,NODE_7_length_90000_cov_40.0,region001,NRPS,45.0,Interior,1,45000
```

`BGC_ID`, `antiSMASH_Region`, `Products`, `Length_kb` and `Boundary` are required. The node comes from `Node_ID`, or from `Contig` when `Node_ID` is empty. `Start` and `End` are optional.

**Report roster** (tab-separated). Use it instead of `inventories`: set `roster_source_id` to its logical ID and give `strain_profiles` as a map of strain to profile, for example `{"EXAMPLE": "relaxed"}`. The set of strains in the roster must equal the set in `strain_profiles`. Required columns are `strain`, `strain_queue_rank`, `primary_user_locator`, `source_scoped_bgc_alias`, `products`, `length_kb`, `boundary`, `selection_lane`, `activity_route` and `prior_activity_routing_score`. Leave `prior_activity_routing_score` empty if you have none. The locator is `NODE / region`, with spaces around the slash. Each strain and rank pair must be unique.

```text
strain	strain_queue_rank	primary_user_locator	source_scoped_bgc_alias	products	length_kb	boundary	selection_lane	activity_route	prior_activity_routing_score
EXAMPLE	1	NODE_7_length_90000_cov_40.0 / region001	BGC001	NRPS	45.0	Interior	SIZE_COMPLETION	NOT_ROUTED	
```

**Identity database** (SQLite, opened read-only). The build reads these tables and columns. It joins on strain, node, region id and profile, and refuses an ambiguous match:

```sql
CREATE TABLE regions(region_key TEXT PRIMARY KEY, strain TEXT, assembly_sha256 TEXT, node_id TEXT);
CREATE TABLE sources(source_id TEXT PRIMARY KEY, archive_sha256 TEXT, antismash_version TEXT, embedded_assembly_sha256 TEXT);
CREATE TABLE region_calls(call_key TEXT, region_key TEXT, source_id TEXT, profile TEXT, region_id TEXT,
                          products_json TEXT, contig_edge TEXT, region_gbk_sha256 TEXT);
CREATE TABLE genes(gene_key TEXT PRIMARY KEY, locus_tag TEXT, strand INTEGER, protein_sha256 TEXT, aa_length INTEGER,
                   nucleotide_sha256 TEXT, nucleotide_length INTEGER, product TEXT, gene_kind TEXT, gene_functions TEXT);
CREATE TABLE gene_region_membership(region_key TEXT, gene_key TEXT,
                                    start_region_record_relative INTEGER, end_region_record_relative INTEGER);
CREATE TABLE domains(region_key TEXT, domain_key TEXT, gene_key TEXT, label TEXT);
```

**BLASTP database** (SQLite, opened read-only). One table. `channel` holds the stored code `local_swissprot`, `ncbi_nr`, `ncbi_clustered_nr`, `ebi_uniprot` or `merged_multi`; `bgc_id` is the inventory's `BGC_ID`:

```sql
CREATE TABLE hits(strain TEXT, bgc_id TEXT, gene TEXT, aa_length INTEGER, role TEXT, domains TEXT,
                  hit_rank INTEGER, subject_acc TEXT, subject_organism TEXT, subject_def TEXT,
                  pct_identity REAL, query_coverage REAL, evalue REAL, bitscore REAL,
                  provenance_suspect INTEGER, channel TEXT);
```

Both databases must integrity-check clean. The bundle ships no sample of either database and no command that builds the identity database. Create both from your own antiSMASH and BLASTP results.

### Source manifest

Schema `sapote_portable_source_manifest_v1`, with a `sources` list. Each source has:

| Field | Meaning |
|---|---|
| `logical_source_id` | Unique ID that workflows use. Required. |
| `root_id` | A root declared in the configuration. Required. |
| `relative_path` | Safe path under that root. Required. |
| `sha256` | Exact hash of the file. Required. |
| `bytes` | Size in bytes. Optional; checked when present. |
| `required` | `true` unless you set it to `false`. A required source that is missing, or has the wrong hash or size, fails the build. |
| `release_class` | `PUBLIC` to allow use in a `PUBLIC` build. |

A missing optional source gets the state `CHANNEL_NOT_CONSUMED`. That state is not evidence that the biology is absent.

A hash match shows the file equals what the manifest says. It does not show who wrote the file. The `PUBLIC` label is a policy check, not permission to publish private metadata.

### Program spec

Schema `sapote_l0_report_program_spec_v2`. The build checks these fields:

| Field | Meaning |
|---|---|
| `schema_version` | Must be `sapote_l0_report_program_spec_v2`. |
| `release` | `INTERNAL` (default) or `PUBLIC`. A `PUBLIC` build cannot use `evidence_modules` or `comparator_sources`. |
| `captured_at_utc` | Timestamp with a time zone, for example `2026-01-01T00:00:00Z`. |
| `identity_db_source_id`, `blastp_db_source_id` | Logical IDs of the identity and BLASTP databases in the manifest. |
| `inventories` or `roster_source_id` | Give exactly one. `inventories` is a list of `{strain, source_id, profile, allocation}`. `profile` is `strict`, `relaxed`, `loose` or `unknown`; `allocation` is a positive integer. A roster also needs a non-empty `strain_profiles` map of strain to profile. |
| `source_discovery_preflight` | `{catalog_source_id, decisions_source_id, required_collection_types}`. The two IDs name the discovery catalog and decision table in the manifest. |
| `output` | `{root_id, relative_path}`. The destination must not exist. |
| `deepening_per_strain` | Optional integer, zero or more. |

If admission fails, fix the catalog or decision finding and run again.

Reader reports cite logical source IDs, hashes, byte counts, assembly hashes and exact node/contig-plus-region locators. Diagnostics and arbitrary source metadata rows are not all redacted automatically. Review the output policy before a public export.

### Comparator tables

A spec can bind per-gene comparator tables:

```json
{
  "comparator_sources": [
    {"strain": "EXAMPLE", "source_id": "example_mibig_per_gene", "format": "MIBIG_PER_GENE_CSV"},
    {"strain": "EXAMPLE", "source_id": "example_clusterblast_per_gene", "format": "CLUSTERBLAST_PER_GENE_CSV"}
  ]
}
```

Each `source_id` must resolve through the manifest. The two CSV formats need these columns:

- `MIBIG_PER_GENE_CSV`: `bgc_id`, `query_gene`, `subject_gene`, `mibig_accession`, `mibig_compound`, `pct_identity`, `pct_coverage`.
- `CLUSTERBLAST_PER_GENE_CSV`: `bgc_id`, `query_gene`, `subject_gene`, `pct_identity`, `pct_coverage`.

These are preliminary evidence. A `PUBLIC` build rejects them.

## Attach a review tranche

A finished scientific review is attached on top of a base report. The base report is not copied or rewritten.

```bash
python mamey_run.py attach-bgc-overlays --help
```

Every flag in that help is required. Take the values from your review package, not from folder names:

- `--base-report-root` and `--out`: the base report folder and a new overlay folder.
- `--review-root`, `--source-manifest`, `--analysis`, `--paragraph-disposition`: the review files. Repeat `--analysis` and `--paragraph-disposition` once per file. The review team defines these tables; there is no bundled template.
- `--target-ledger`, `--expected-target-sha256`, `--expected-manifest-sha256`: the frozen target ledger, the review manifest, and their hashes.
- `--source-discovery-catalog` and `--source-discovery-decisions`, each with its `--expected-...-sha256`.
- `--expected-reviewed-loci`, `--required-disposition-module`, `--allowed-review-role`, `--required-collection-type`: the acceptance scope. Repeat the last three once per value.

The command checks that strain, assembly, node, region and region key agree with the base report index. It re-hashes the review package and every indexed base-report file. It writes only an overlay and a module-state delta. Target tables with source-reported coverage above 100 percent fail unless that value is quarantined. Keep the review manifest unchanged during the build; a change is refused before publication.

Success is a new overlay folder with `INDEX.md` and `REVIEW_INDEX.tsv`. They link each exact node/contig-plus-region locator to its base draft and its proposal reconciliation. The source-scoped BGC alias stays secondary. The command does not turn reviewer synthesis into accepted biology.

## Stable organization rules

1. The bundle is replaceable and holds no user evidence.
2. A source file may stay in any declared root. Its logical source ID is the handle.
3. A file name, folder name, BGC ordinal or timestamp is never an authority key.
4. The primary BGC locator is assembly identity plus exact node/contig and antiSMASH region. A BGC ordinal is only a source-scoped alias.
5. Mirrors and backups may exist. The manifest records which bytes a run used. Duplicate bytes do not count as separate observations.
6. Discovery writes a proposal catalog. Admission needs an explicit decision and a hash check.
7. The draft and overlay builders publish to a new destination with a manifest. Other commands differ; direct extraction and some export tools have their own overwrite and recovery behavior.
8. Cache, figures, environments, copied baselines and raw analysis payloads stay out of software patch packets.

## Reorganizing an existing workspace

Inventory first, move later. Make a read-only catalog with current path, collection type, hash, size, embedded provenance, proposed root and disposition. Then pick one action per collection:

- `REFERENCE_IN_PLACE`: leave the source where it is and bind its root.
- `COPY_TO_CONTROLLED_IMPORT`: make a receipted copy; keep the original and its hash.
- `QUARANTINE_OR_SUPERSEDE`: keep it as history and exclude it from automatic report use.

These labels describe where files live. They do not admit evidence. The source-discovery gate uses a separate decision table with columns `collection_id`, `decision`, `reason` and `evidence_receipt`. The `decision` value is `CONSUME`, `REJECT_WITH_REASON` or `SUPERSEDED_WITH_RECEIPT`. Resolve every missing decision the gate reports before building.

Do not reorganize by recency. Do not merge same-named folders silently. Do not move a large collection before a pre- and post-move hash receipt exists.

## Claim and channel boundary

BLASTP, Swiss-Prot, MIBiG, KnownClusterBlast, ClusterBlast, antiSMASH profile calls, domain annotations, literature and phenotype context are separate channels. Missing or unbound data is a channel state, never biological absence. Similarity is not identity. Biosynthetic capacity is not production or activity.
