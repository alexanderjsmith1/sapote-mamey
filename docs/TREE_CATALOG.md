# Tree Catalog

The Tree Catalog turns one validated placement analysis into a declared set of
publication display variants. It is intended for recurring cohort views such as
bee isolates, moss isolates, attine-ant isolates, combined cohorts, genus-only
panels, and rare-actinomycete panels.

Each catalog entry states:

- the cohort and taxonomic scope;
- the completed placement run it consumes;
- whether its reference panel contains type strains only or type strains plus
  explicitly selected non-type strains;
- one, two, or three nearest reference tips per query;
- concise-source publication, detailed-source publication, no-geography, and
  internal specimen-review views; and
- optional spotlight-query intent.

The tool does not infer that a type strain is representative, merge cohorts,
choose an outgroup, or admit a non-type reference. Those decisions belong to the
upstream placement run and its receipts. A spotlight entry must point to a
placement run prepared with that declared query subset; the renderer refuses to
silently prune a full-cohort analysis into a rarity claim.

The `publication` view reduces long deposited isolation phrases to one readable
source term while retaining the raw phrase in the metadata sidecar. The
`publication-detailed` view keeps the deposited source wording for audit and
specialist use. Both consume the same Newick tree and differ only in display.

The `internal` view may append a bound specimen key such as `Exp 35 #12` to query
labels and uses `_internal` in its output name. Use it to review whether several
isolates came from the same biological sample. Treat the combined experiment and
sample identifiers as the sampling-unit key; neither field is sufficient alone.
An identical or near-identical marker sequence is not permission to merge
isolates. Record a proposed collapse separately and require source-registry
confirmation. Publication views omit these internal identifiers.

## Catalog format

```json
{
  "schema": "sapote.tree-catalog.v1",
  "defaults": {
    "views": ["publication", "publication-detailed", "publication-noloc"],
    "reference_ratios": [1, 2, 3]
  },
  "trees": [
    {
      "id": "bee_streptomyces",
      "run_dir": "/path/to/completed/placement-run",
      "group": "Streptomyces",
      "cohort_scope": ["bee"],
      "taxonomic_scope": "Streptomyces",
      "reference_panel": "type_only",
      "host_table": "/path/to/query_metadata.tsv",
      "ref_source_db": "/path/to/reference_metadata.sqlite",
      "required_reference_table": "/path/to/query_required_reference_species.tsv",
      "genus_roster": "/path/to/query_genus_roster.tsv"
    }
  ]
}
```

Relative paths resolve from the catalog file. The shipped example uses generic
paths because project datasets and private strain registries are not bundled.
The optional required-reference table has `strain` and `reference_species`
columns. A declared species must already be admitted to the placement backbone.
It counts first within that query's 1:1, 1:2, or 1:3 quota; missing species
refuse the display instead of being replaced silently by another neighbor.

## Plan before rendering

```bash
python3 tools/tree_catalog.py plan TREE_CATALOG.json --out tree_catalog_plan.json
```

The plan expands every entry across its ratios and views. A three-ratio catalog
with concise, detailed, and no-geography views therefore creates nine displays
from one placement analysis. Review the job count,
scope, reference policy, and paths before starting R.

```bash
python3 tools/tree_catalog.py render TREE_CATALOG.json --outdir rendered_tree_catalog
```

`placement_display.py` writes a display-specific Newick and annotation TSV, then
passes both to the maintained `tools/ggtree_rect_heatmap.R` source script. The R
script lays out the existing tree and draws labels, metadata strips, scale bar,
PNG, and PDF; it does not infer a new topology.
See [R figure workflows](R_FIGURE_WORKFLOWS.md) for the complete maintained R
source inventory and the input generated for each renderer.

Rendering is additive and refuses an existing output directory. Each child
directory contains the tree, metadata, reference-selection ledger, methods,
PNG/PDF, and receipts produced by `placement_display.py`. The catalog-level
receipt records each command and stops after the first failed job.

## Recommended project matrix

Maintain separate entries for bee, moss, and attine cohorts; combined cohort
questions; *Streptomyces*; and non-*Streptomyces* actinomycetes. For each
scientifically admitted analysis, render 1:1, 1:2, and 1:3 query-to-reference
views with and without geography. Treat the full 1:1 cohort tree as a compact
overview and use declared spotlight analyses for one or a few unusual isolates.
Keep a full-context companion tree and the complete reference-selection ledger
beside every spotlight figure.

For bee, moss, and attine datasets, add an internal companion view when the
source registry contains experiment and sample identifiers. This view supports
redundancy review, sample-level method counts, and interpretation of repeated
isolations; it is not the default manuscript figure.

The reference library can be a compact local 16S database, but file size is not
its quality criterion. Every record needs a stable accession, sequence hash,
taxon, type-status evidence, source class, admission state, and provenance.
Type and selected non-type panels remain separate so a convenient non-type
sequence cannot silently become a type-strain comparator.
