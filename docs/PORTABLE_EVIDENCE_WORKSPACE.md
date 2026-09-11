# Portable evidence-workspace interface

Sapote-Mamey is a portable application. The extracted bundle contains the
engine, schemas, tests, documentation, and small shipped reference assets. A
user's antiSMASH archives, assemblies, BLASTP databases, literature library,
legacy reports, and generated results remain outside the bundle.

The boundary between those layers is a logical-root configuration plus a
hash-bound source manifest. Source discovery may propose files for the
manifest, but discovery never grants authority and newest-file-wins is never a
valid admission rule.

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

Relative roots are anchored to the configuration file. A portable project can
therefore move as one directory. Machine-specific absolute paths can instead
be supplied at runtime:

```bash
python mamey_run.py build-bgc-drafts \
  --evidence-root-config sapote-evidence-roots.json \
  --source-manifest source-manifest.json \
  --program-spec program-specs/five-strain-l0.json \
  --evidence-root blastp=/data/current-blastp
```

Runtime overrides are never written into public reports. Reports cite logical
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
  --out outputs/five-lead-stage2-overlay-v1
```

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
7. Outputs are written atomically to a new destination and carry a manifest;
   the builder refuses to overwrite a prior run.
8. Cache, rendered figures, environments, copied baselines, and raw analysis
   payloads are excluded from software patch packets.

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
