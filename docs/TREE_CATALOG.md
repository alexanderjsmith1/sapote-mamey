# Tree Catalog

## What this tool does

Use the Tree Catalog **after** you have a completed, validated 16S placement
run. It makes several *views of that same tree*: for example, one, two, or
three nearby reference tips per query, each with concise source labels or a
different metadata display. It keeps the tree, reference choices, methods, and
render receipts together for each view.

The catalog is **not an inventory of tree files on your computer**. It does
not search the Codex or Claude workspaces, infer a new tree, download reference
genomes, repair missing metadata, or decide which earlier figure is current.
Map and review existing assets separately before adding a completed placement
run to a catalog.

You need the completed placement run, the query metadata table, the reference
metadata database, and a verified roster binding the tree tips to their
sequences and source records. Choose the cohort, taxonomic scope, reference
panel, and desired views. Use `plan` to inspect the resulting jobs; use
`render` only after the full series requirements and reference manifest below
are present and pass validation.

For a tree already prepared outside this placement workflow, use the
[prepared display series](#prepared-display-series) route instead. It consumes
declared, hashed display inputs; it does not discover or infer trees either.

## Choose the output views

A typical genus run can produce a compact 1:1 query-to-reference view and
wider 1:2 and 1:3 views. The ratios are selection limits for nearby references,
not a change to the original placement analysis. A five-level series can also
include 1:4 and all references when the panel supports them. Select a concise
publication view, a detailed-source view, a view without a geography strip,
or an internal specimen-review view. The no-geography view still requires
resolved geography in the bound metadata; it only hides that strip in the
figure.

The tool is intended for recurring cohort views such as bee isolates, moss
isolates, attine-ant isolates, combined cohorts, genus-only panels, and
rare-actinomycete panels.

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

## Plan a catalog

The following JSON is a **planning sketch**, not a render-ready catalog. It
omits `series_requirements` and the hash-bound `reference_manifest`; the
renderer refuses it until those fields and their actual evidence are supplied.
The shipped example also uses placeholder paths, so replace them with files
from your own completed run before running `plan`.

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

```bash
python3 tools/tree_catalog.py plan TREE_CATALOG.json --out tree_catalog_plan.json
```

The plan expands every entry across its ratios and views. Three ratios times
three views create nine proposed displays. Inspect the job count, query scope,
reference policy, and paths. Planning does not prove that the underlying tree,
metadata, or references are scientifically accepted.

## Render after the inputs pass review

Add the exact `series_requirements` and `reference_manifest` described under
[Required series contract](#required-series-contract-and-verified-completion).
Resolve missing source/geography metadata in the source records, then run:

```bash
python3 tools/tree_catalog.py render TREE_CATALOG.json --outdir rendered_tree_catalog
```

The renderer refuses incomplete series declarations or missing bound inputs.
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


## Required series contract and verified completion

Rendering requires an explicit `series_requirements` object with nonempty lists
`taxonomic_scopes`, `reference_panels`, `reference_ratios`, and `views`. These
lists describe the requested Cartesian product. Missing, duplicated, or extra
variants refuse preflight. An older catalog without this object can still be
inspected with `plan`, but cannot be rendered as a completed series.

Use `[1, 2, 3, 4, "all"]` for the five-level density series. The `"all"` value
passes `--keep-all-references` to the maintained display producer. Numeric ratios
are per-query selection quotas before shared-reference deduplication; they are
not promises of that many unique references per query across the combined tree.

Every tree entry must supply `reference_manifest`: an object with `path` and
`sha256` for a TSV roster, and `tree` and `sequences` objects, each with a relative
`path` and `sha256`. The roster columns are `tip`, `role`, `type_status`,
`accession`, `sequence_sha256`, `evidence`, and `admission`. Roles are `query`,
`reference`, or `outgroup`; admitted records use `admission=admitted`. Sequence
hashes describe uppercase, ungapped sequence strings. The bound tree, FASTA and
roster must have exactly the same unique tip identities. The existing stem-aware
branch gate runs with the explicitly declared outgroup; it retains terminal and
other-branch checks and does not offer an unrestricted exemption.

Reference-panel distinctions are enforced:

- `type_only`: every ingroup reference has affirmative type status.
- `type_plus_selected_non_type`: both affirmative type and affirmative non-type
  records are present; unknown status cannot be converted into non-type status.
- `type_plus_selected_additional`: explicitly provisional broader context that
  can include `unverified` type status. Retain that uncertainty in the labels and
  methods; it is not a confirmed non-type panel.

The panel designation describes the input backbone. Compact display subsets may
contain only type references. Render receipts therefore record the actual type,
non-type, and unverified-reference counts for each delivered variant.

Subprocess success alone is insufficient. Completion requires nonempty Newick,
metadata, PDF and PNG outputs; exact tree/metadata tip joins; preservation of all
queries and outgroups; complete backbone retention for `"all"`; and agreement
with the declared parent tree after pruning and rerooting. Unrooted split-length
comparisons allow an explicitly reported 0.0001 substitutions/site tolerance for
legacy decimal serialization; this is not a biological uncertainty estimate.
Output hashes are recorded. None of these mechanical gates establishes source
metadata correctness, species identity, biological novelty or release authority.

`read_display_exclusions()` reads only the excluded `tip` and `accession` columns.
It must never interpret a `retained_accession` representative as another exclusion.

Existing projects must bind their actual reference evidence rather than inventing
manifest rows to make these checks pass. Additional reference selection and tree
inference remain separate upstream operations. Keep original failed attempts and
source authority holds linked to the final series receipt.

### Prepared display series

For externally inferred trees whose display inputs have already been prepared,
`tools/render_tree_reference_series.py --config series.json --outdir new_results`
provides an additive render path through the same series and delivery gates.
Its JSON contains the same `series_requirements` and `trees` contracts, plus
`display_jobs`. Each job has `job_id`, `tree_id`, `taxonomic_scope`,
`reference_panel`, `reference_ratio`, `view`, a relative `input_dir`, and
`input_hashes` for exactly `tree.newick`, `metadata.tsv`, `palette.tsv`,
`settings.tsv`, and `caption.txt`. An optional filesystem-safe `group` organizes
output directories. Job IDs must be unique and filesystem-safe.

Each prepared display job also declares an integer `series_index` and a
descriptive, filesystem-safe `output_stem`. Indices must be contiguous from 1
through the number of jobs, and output stems must be unique and cannot use
generic names such as `tree` or `figure`. Delivered filenames begin with the
zero-padded series index followed by the descriptive stem, so neighboring
trees remain identifiable after they are copied out of their job folders.

The prepared metadata retains `tip`, `label`, `role`, `accession`, `type_status`,
`raw_source`, `source_category`, and `geography`. The palette table has `field`,
`value`, and `color` columns, using `source` and `geography` as field names. The
settings table has `key` and `value`, including `view` and `title`.

Every displayed query, reference, and outgroup must have a nonempty label plus
resolved `source_category` and `geography` values. Missingness sentinels such as
`Not recorded`, `Unknown`, `Unresolved`, and `N/A` fail preflight for every role,
including when source and geography are both absent. Resolve that metadata or
remove the reference upstream and record it in the display-exclusion ledger.
An owner query cannot be removed to make a figure pass; hold the panel instead.
Missingness categories are also forbidden in the palette, so a gray unknown cell
cannot appear in an admitted figure or legend.

The renderer admits one shared palette contract across the entire series. A
source or geography category must keep the same color in every job, and two
categories in the same field cannot reuse an identical color. Any drift or
collision fails preflight before a figure is rendered.

Query tip text uses the series-wide red `#bb0000`. The preflight receipt records
this color together with the per-job complete-metadata counts.

The maintained direct rectangular renderer applies the same red query text and
the same fixed source-category colors. Its two-strip view requires complete
source and geography for every displayed tip. A source-only view may hide the
geography strip, but it cannot invent or display an unknown geography category.

Preflight verifies every input hash and refuses specific bee/wasp source labels
that contradict the raw source. Rendering copies inputs into a new output root,
freezes the R renderer and geometry helper, checks input/script hashes around
execution, audits the actual plotted cells, and binds delivered artifacts. It
never reuses an existing output directory as evidence of success. Every job gets
a receipt; the series is complete only when the full requested matrix succeeds.
This prepared-input consumer does not implement reference discovery or upstream
sequence admission and does not turn provisional metadata into confirmed facts.

This candidate depends on the separately reviewed annotation-gate patch, which
supplies `tools/tree_annotation_geometry.R`; apply that dependency first. The
complete extracted bundle supplies the normalizer, stem-aware gate and its
`mamey.csv_safety` dependency. A standalone export must retain those dependencies
rather than relying on an unrelated installed Mamey version.
