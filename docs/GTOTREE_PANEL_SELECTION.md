# Bounded GToTree panel selection

GToTree builds a tree from single-copy genes found in a set of genomes. This tool picks and stages that
set of genomes, called a panel, before you run GToTree. It does not run GToTree or IQ-TREE, and it cannot
change a Mamey core run. Terms are in the [glossary](GLOSSARY.md).

## Steps

1. Choose the panel size.
2. Fill the candidate manifest, one row per genome.
3. Run `tools/build_phylo_panel.py`.
4. Review the staged files, as described under [Check the output](#check-the-output).
5. Continue in the [GToTree workflow](GTOTREE_WORKFLOW.md).

## Choose the panel size

```bash
python tools/build_phylo_panel.py --show-options
```

The presets are **20**, **40** (default) and **60** total tips. You can give any integer from 3 through 60.
A value above 60 is an error. The number counts every tip: queries, references and exactly one outgroup.
It is not a per-query number. Use 20 for a focused figure. Sixty is the ceiling, not a target.

```bash
python tools/build_phylo_panel.py candidates.tsv staged_panel/ --panel-size 40
```

Success is exit code 0 and the files listed under [Check the output](#check-the-output). The output folder must
not exist yet, and an empty existing folder counts as existing.

## Fill the candidate manifest

Start from `examples/phylo_panel_candidates.template.tsv`. It has 13 columns and five example rows: two queries, a
reference, a type-strain reference and an outgroup. Replace the paths and names. A relative `source_path` is read from the manifest's own folder, not from where you run the command; use absolute paths if the manifest is elsewhere. The required columns are
`candidate_id`, `role` and `source_path`. A role is `QUERY`, `REFERENCE` or `OUTGROUP`.

The other columns are `source_member`, `priority`, `cohort`, `taxonomy`, `display_label`, `tree_label`,
`selection_basis`, `related_query_ids`, `reference_status` and `assembly_fromtype`.

Rules:

- Query IDs are the candidate IDs you write. They are not guessed from a prefix. Queries with different content are all kept before references. If the queries plus one outgroup are more than the panel size, the tool stops.
- Each `REFERENCE` needs a `selection_basis` and explicit `related_query_ids`, both written by you. The tool never works out which genome is nearest, a type strain or a reference.
- At most three references can link to one query (`--max-related-per-query`, 0 to 3, default 3).
- A **type anchor** is a named type-strain genome added past that cap, so a figure can anchor names. It is a `REFERENCE` row with `selection_basis` = `nearest_type_strain_<method>` (your method, such as `tygs`, `ani` or `mlsa`) and `assembly_fromtype` = `assembly from type material`, copied from NCBI Assembly. Any other `assembly_fromtype` value stops the tool.
- Anchors are chosen after the ordinary references, so they never change which ordinary references are picked. `--max-type-anchors-per-query` sets their limit (0 to 2, default 2). They count toward the panel size. A query never gets more than four references and anchors together.
- Exactly one outgroup is staged. "Outgroup" is your assertion. The tool does not check that the lineage suits your question.
- `priority` is the selection order, ascending: 1 is taken before 50. Within each role the tool walks the rows in `priority` order, then by `candidate_id`. The first outgroup in that order is the one staged. References are taken in that order until a per-query cap or the panel size is reached, and the rest are excluded (`EXCLUDED_RELATED_CAP`, `EXCLUDED_PANEL_FULL`). Type anchors follow the same order after the ordinary references. Among exact duplicates, a query is kept over an outgroup, an outgroup over a reference, an ordinary reference over a type anchor, and then the lower `priority` wins. So `priority` can decide which genomes are in the panel. It is not a biological rank. Read `decision` and `reason` for every row in `panel_candidates.tsv`, selected and excluded, before you build.

`panel_selected.tsv` marks anchors with `type_anchor` = `yes`, and `panel_receipt.json` lists them under
`type_anchors`. `plan_gtotree_iqtree.py` re-checks both fields and both limits.

## Sources

`source_path` can be a FASTA or GenBank file, or an antiSMASH results ZIP. For a ZIP, set `source_member` to the
exact assembly FASTA or whole-assembly GenBank inside it. A ZIP usually holds many region GenBank files, and
those are not whole assemblies. The tool will auto-pick a member only when exactly one assembly-like member is
left after it drops region and cluster members. It rejects unsafe or missing member paths.

This is a parser check, not an assembly check. FASTA headers and whitespace are dropped. The accepted symbols
are `ACGTUNRYKMSWBDHVX.-`, and dots and hyphens are removed. GenBank input is read from `ORIGIN` blocks only. The tool turns
U into T, as the planner does, so both compute the same content hash. Check the source accession and version,
the assembly scope and the type status yourself. The type-anchor check reads the string you supplied, not an NCBI record.

## Duplicates

Genomes are hashed from their uppercase nucleotide sequence, ignoring headers and contig order. A genome with
identical content to another is kept once, and each dropped copy points to the one kept. This applies to queries
too. A reverse-complement copy is not treated as a duplicate. Genomes that are only highly similar (high ANI) are
not merged.

Role priority is QUERY, then OUTGROUP, then REFERENCE. An outgroup that duplicates a query can disappear before
outgroup checks run.

After staging, open `panel_candidates.tsv` and check every `EXCLUDED_DUPLICATE` row before you accept the
panel. Keep every original query name. Unique assemblies are not necessarily independent isolates.
The planner for prepared panels reads only the selected rows, so it does not restore dropped duplicate queries on its own.
Direct planner input does check them, with the hold `HOLD_DUPLICATE_QUERY_REVIEW`.

## Check the output

The new folder holds:

| File | Purpose |
|---|---|
| `panel_candidates.tsv` | Every candidate, why it was selected or excluded, its source and hashes |
| `panel_selected.tsv` | The staged panel and the stated basis for each comparator |
| `label_crosswalk.tsv` | Five columns with a header: `candidate_id`, `tree_label`, `display_label`, `role`, `taxonomy`. For human review only. |
| `labels.tsv` | The GToTree `-m` label map: exactly two columns, no header |
| `panel_receipt.json` | Panel size, default and maximum, counts, duplicates, claim ceiling and the manifest hash |
| `genomes/*.fna` | The normalized assemblies |
| `genomes.txt` | Absolute paths for a later GToTree command |

Read `panel_selected.tsv` and `label_crosswalk.tsv` before you run GToTree. The status `PANEL_STAGED_NOT_RUN`
means staged, not run and not accepted.

## Run GToTree with the labels

The tool does not limit CPU use. The planner or runner you choose does. See
[runtime admission](GTOTREE_RUNTIME_ADMISSION.md) and [run contracts](COMPANION_RUN_CONTRACTS.md). For the
default GToTree 1.8.19 route, pass the headerless map:

```bash
GToTree ... -m staged_panel/labels.tsv ...
```

Column 1 is the staged FASTA file name (for example `Streptomyces_sp_QUERY_001.fna`). Column 2 is its unique,
machine-safe label. Do not pass `label_crosswalk.tsv` to `-m`.

The optional v2 planner writes a different map, keyed by the absolute paths in its `genomes_absolute.txt`. Do not
give it this tool's `labels.tsv` unchanged. Use the map the planner generates.

## If a run stops partway

Files are written one at a time, so an error can leave a partial folder that the tool then refuses to reuse. Keep
it, fix the input, and run again into a new output folder. The tool also refuses to return a smaller panel than you
asked for when too few genomes qualify.

The receipt hashes the manifest. Each row keeps a hash of the whole source and of the normalized content. The
receipt does not hash each raw ZIP member, each staged FASTA, each output TSV or the tool's own source. Keep those
bindings yourself if a later step needs them.

## What panel membership means

A panel is a choice of comparators. It does not establish taxonomic identity, nearest-neighbor status, strain
independence, novelty, biosynthetic production or biological activity. A core-gene tree strengthens topology. ANI
and provenance checks are separate. A duplicate is a warning about identity. It does not show what caused a mix-up
or a contamination.
