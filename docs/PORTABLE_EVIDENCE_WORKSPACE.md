# Portable evidence-workspace interface

Sapote-Mamey is a portable application. The extracted bundle contains the
engine, schemas, tests, documentation, and small shipped reference assets. A
user's antiSMASH archives, assemblies, BLASTP databases, literature library,
legacy reports, and generated results remain outside the bundle.

The boundary between those layers is a logical-root configuration plus a
hash-bound source manifest. Source discovery may propose files for the
manifest, but discovery never grants authority and newest-file-wins is never a
valid admission rule.

## Refreshable report selection and recovery

For the current refreshable exact-identity report, read [selection/publication contracts](reference/06_CURRENT_SOURCE_SCOPE.md#refreshable-exact-identity-report-selection-and-publication-routes). The portable and native module entries use different configuration and publication-recovery contracts. An omitted locus selector can select every region for the strain; a bound draft, logical-source resolution or source snapshot PASS is not scientific completion. Keep partial-build and completed-publication recovery states separate. Read [profile/channel/Mode B admission](reference/06_CURRENT_SOURCE_SCOPE.md#refreshable-report-evidence-admission-profiles-channels-and-mode-b) before reusing currentness labels or an empty missing-evidence queue.

## Recommended user project

```text
sapote-project/
  sapote-evidence-roots.json
  source-manifest.json
  program-specs/
  receipts/
  outputs/
  imports/        # optional controlled copies; not required
  cache/          # reproducible, disposable derivatives
```

Existing data stores do not have to be moved into this directory. The root
configuration may point to several stable external locations. For example,
`antismash`, `blastp`, `literature`, `legacy_reports`, and `outputs` can each be
separate logical roots.

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

Root precedence is explicit CLI override, then `SAPOTE_EVIDENCE_ROOT_<ROOT_ID_UPPERCASE>`, then the configured path. Runtime overrides must be absolute and name a root already declared in the configuration; they cannot silently add an undeclared collection. Relative configured roots are anchored to the configuration file. A portable project can
therefore move as one directory. Machine-specific absolute paths can instead
be supplied at runtime:

```bash
python mamey_run.py build-bgc-drafts \
  --evidence-root-config sapote-evidence-roots.json \
  --source-manifest source-manifest.json \
  --program-spec program-specs/five-strain-l0.json \
  --evidence-root blastp=/data/current-blastp
```

The draft workflow uses logical locators in reader reports; do not infer that every diagnostic/log or arbitrary source metadata row is automatically redacted. Review output policy before a public export. Reports cite logical
source identifiers, hashes, byte counts, assembly hashes, and exact
node/contig-plus-region locators.

A completed scientific-review tranche is attached additively rather than by
copying and rewriting the base report cohort:

```bash
python mamey_run.py attach-bgc-overlays \
  --base-report-root outputs/five-lead-v6 \
  --target-ledger review/STAGE2_OVERLAY_LEDGER.tsv \
  --expected-target-sha256 <sha256> \
  --review-root review \
  --source-manifest review/ARTIFACT_MANIFEST.tsv \
  --expected-manifest-sha256 <sha256> \
  --analysis review/FIRST_FIVE_LOCUS_ANALYSIS.tsv \
  --analysis review/REMAINING_TEN_LOCUS_ANALYSIS.tsv \
  --paragraph-disposition review/FIRST_FIVE_PARAGRAPH_DISPOSITION.tsv \
  --paragraph-disposition review/REMAINING_TEN_PARAGRAPH_DISPOSITION.tsv \
  --expected-reviewed-loci <exact-reviewed-locus-count> \
  --required-disposition-module <module-id> \
  --allowed-review-role <review-role> \
  --required-collection-type <collection-type> \
  --source-discovery-catalog review/SOURCE_DISCOVERY_CATALOG.json \
  --expected-source-discovery-catalog-sha256 <sha256> \
  --source-discovery-decisions review/SOURCE_DISCOVERY_DECISIONS.json \
  --expected-source-discovery-decisions-sha256 <sha256> \
  --out outputs/five-lead-stage2-overlay-v1
```

The expected reviewed-locus count, required disposition modules, allowed review roles and required collection types are mandatory acceptance-scope inputs. Replace each placeholder from the actual review contract and repeat the module/role/collection flags for every required value. Do not infer these values from directory names.

The source-discovery catalog and decisions are mandatory bound inputs, not optional recovery notes. Use the existing discovery/decision workflow and their actual file hashes; placeholder names above do not create those artifacts. The draft program specification similarly needs its source-discovery binding accepted before report writing.

The command rehashes the review package, requires exact strain/assembly/node/
region/region-key agreement with the base report index, verifies every indexed
base-report byte, and emits only an overlay plus a module-state delta. Target
tables containing source-reported coverage above 100 percent hard-fail unless
the numeric value is explicitly quarantined and excluded from the usable
coverage field. Immediately before atomic publication, the builder rehashes
the base controls, all indexed base reports, the frozen target ledger, every
target artifact, and the review manifest again.

The overlay includes `INDEX.md` and `REVIEW_INDEX.tsv`. They link each exact
node/contig-plus-region locator to both its immutable base draft and its
proposal reconciliation, while keeping the source-scoped BGC alias secondary.
The command does not mutate or duplicate the base 100-report tree and does not
convert reviewer synthesis into accepted biology.

Internal report specifications may bind preliminary comparator tables without
copying them into the application bundle:

```json
{
  "comparator_sources": [
    {"strain": "STRAIN-1", "source_id": "strain1_mibig_per_gene", "format": "MIBIG_PER_GENE_CSV"},
    {"strain": "STRAIN-1", "source_id": "strain1_clusterblast_per_gene", "format": "CLUSTERBLAST_PER_GENE_CSV"}
  ]
}
```

Each `source_id` must resolve through the hash-bound source manifest. These
formats are preliminary internal evidence and are rejected from a `PUBLIC`
build until a separate admitted-evidence export exists.

Keeping outputs outside the application bundle requires review of each workflow's output path and writes. A passing bundle-write-default static check is limited by its selected source scope and matching rules; it does not establish that every write has a guard or that the guard runs before the write. See [maintenance check scope](CATALOG_MAINTENANCE.md#bundle-write-default-static-check) before using that result as portability evidence.

## Stable organization rules

1. The application bundle is replaceable and contains no user evidence.
2. A source file may stay in any declared root; its logical source ID is the
   stable handle used by workflows.
3. A filename, folder name, BGC ordinal, or filesystem timestamp is never an
   authority key by itself.
4. The primary BGC locator is assembly identity plus exact node/contig and
   antiSMASH region. A BGC ordinal is retained only as a source-scoped alias.
5. Mirrors and backups may exist, but the manifest records which exact bytes a
   run consumed. Duplicate bytes do not multiply biological observations.
6. Discovery writes a proposal catalog. Admission requires an explicit source
   decision and hash verification.
7. The governed draft/overlay builders publish their outputs to a new destination with a manifest. This is their specific contract, not a guarantee that every bundle command is atomic or refuses overwrite; direct extraction and some export tools have separate mutation/recovery behavior.
8. Cache, rendered figures, environments, copied baselines, and raw analysis
   payloads are excluded from software patch packets.

## Source-manifest states

The source manifest uses `sapote_portable_source_manifest_v1` with a sources list. Every source needs a unique logical_source_id, declared root_id, safe relative_path and exact sha256; optional bytes are checked when supplied. A required source defaults to required when the flag is omitted. Missing required roots/files or hash/size disagreement fail resolution. Missing optional roots/files receive CHANNEL_NOT_CONSUMED and do not prove biological absence.

PUBLIC resolution requires each consumed source to declare PUBLIC release_class. That label is a consumption-policy check, not authority to publish private metadata or scientific acceptance. Hash verification establishes selected-byte agreement with the supplied manifest; it does not independently authenticate the source author.

## Reorganizing an existing workspace

Inventory first and move later. Create a read-only catalog containing current
path, logical collection type, hash, size, embedded provenance, proposed root,
and disposition. Then choose one of three actions per collection:

- `REFERENCE_IN_PLACE`: leave the source where it is and bind its root.
- `COPY_TO_CONTROLLED_IMPORT`: make a receipted copy while preserving the
  original source and hash.
- `QUARANTINE_OR_SUPERSEDE`: retain it as historical evidence but exclude it
  from automatic report consumption.

Do not reorganize by recency alone, do not silently merge same-named folders,
and do not move large collections before a pre/post hash receipt exists.

## Claim and channel boundary

BLASTP, Swiss-Prot, MIBiG, KnownClusterBlast, ClusterBlast, antiSMASH profile
calls, domain annotations, literature, and phenotype context remain separate
channels. Missing or unbound data is reported as a channel state, never as
biological absence. Similarity is not identity; biosynthetic capacity is not
production or activity.
