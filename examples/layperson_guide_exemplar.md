# Plain-language genome and experiment guide — current format exemplar

This template explains a completed analysis to a reader who does not work with genome-mining
software. It is a format example, not a scientific result.

## What was analyzed

| Item | Plain-language description |
|---|---|
| Genome evidence | `[What sequence and antiSMASH results were available, and their quality.]` |
| Protein searches | `[Which protein sequences were searched, against which distinct databases, and what remained unsearched.]` |
| Fragment rescue | `[Which split signals were connected across contigs and which remain uncertain.]` |
| BGC families | `[Whether BiG-SCAPE or another family analysis was run and on what roster.]` |
| Phylogeny | `[GToTree genome tree, EPA-ng 16S placement, or neither; include the reviewed receipt.]` |
| Bioassay evidence | `[Which materials, targets, time points, replicates, and controls were admitted.]` |
| Chemical context | `[Any reference structures shown and why they are relevant.]` |

## Main findings

Use short statements tied to a source. Separate these levels:

- the genome contains genes consistent with a biosynthetic capacity;
- protein and comparator searches show sequence similarity;
- a tested crude extract or fraction had a recorded assay result;
- a known molecule is shown as a class-member or comparator reference;
- a strain falls within a tree neighborhood under the stated phylogenetic method.

Do not combine those statements into a claim that a locus produced an active compound unless a
separate admitted experiment connects the locus, detected molecule, and assay result.

## Priority locus table

Every locus uses the complete identity `strain / full node-or-contig / region / BGC alias`.

| Complete locus identity | Predicted class | Evidence in plain language | Boundary/assembly limit | Next useful step |
|---|---|---|---|---|
| `STRAIN-ID / FULL_CONTIG_ID / regionNNN / BGCNNN` | `[class]` | `[one sourced sentence]` | `[limit or none recorded]` | `[one concrete action]` |

## Bioassay view

| Material | What it is | Target label/state | Time point | Replication | Control state | Result |
|---|---|---|---:|---|---|---:|
| `[material ID]` | `[crude/flash/HPLC/purified]` | `[as recorded; verified or ambiguous]` | `[hours]` | `[singleton/technical/biological]` | `[valid/hold]` | `[% inhibition or missing state]` |

Explain whether the figure shows individual experiments or an exact-group average. A blank screen,
an untested organism, and a measured zero are different observations. If the positive control was
missing or its position is unresolved, say that the row was held rather than presenting a corrected
result.

## Phylogenetic and ecological context

State the data type first. A GToTree/IQ-TREE result uses genome marker genes. An EPA-ng result places
a partial or full 16S sequence onto a fixed reference backbone. A strain without a genome may still
appear in the 16S view and bioassay overlay. Preserve the raw isolation source and location beside
any simplified display category, and describe proximity as a neighborhood rather than a tested
ecological association.

## Chemical structures

Label every molecule drawing as one of: `reference class member`, `KnownClusterBlast comparator`, or
`identified assayed material`. The first two help a reader understand known chemistry; they do not
show what the current strain made. Include the database record or literature source and license in
the figure sidecar or reference table.

## What remains uncertain

- `[missing genome, partial sequence, fragmented locus, unrun search, ambiguous target, held control,
  unresolved fraction lineage, or missing chemical confirmation]`
- `[next experiment or data source that can resolve it]`

## Sources and reproducibility

Link the sealed package, tree/placement receipt, bioassay Figure Factory receipt, exact selected
tree track, structure record, and reviewed citations. The visible guide should stay readable; the
full hashes, mappings, and decisions travel in those sidecars.
