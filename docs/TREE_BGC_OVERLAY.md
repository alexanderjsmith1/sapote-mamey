# Tree annotation Figure Factory consumer

`tools/tree_bgc_overlay.py` is the publication-gated renderer for existing MLSA and
GToTree/IQ-TREE outputs. It is not a third phylogeny engine and does not run alignment, tree
inference, relabeling, ANI, BGC, domain, or Mode B analysis.

The accepted tree channels are deliberately separate:

- `MLSA_PROTEIN5` — the five protein-coding loci built by `build_mlsa.py`;
- `MLSA_16S_SEPARATE` — the separately extracted 16S evidence channel; and
- `CORE_GENOME_GTOTTREE_IQTREE` — the GToTree core-gene alignment followed by recorded IQ-TREE
  inference.

The renderer never forces agreement between these topologies. Visual proximity does not establish
product identity, activity, horizontal transfer, ancestry direction, or topology equivalence.

## Hash-bound interface

A `sapote.tree-figure-factory.v1` configuration binds exactly one file for every role below:

| Role | Required content |
|---|---|
| `tree` | final canonical Newick tree |
| `alignment` | the exact alignment used for that tree |
| `tree_workflow_receipt` | JSON carrying matching `tree_channel` and `tool` |
| `model_receipt` | JSON carrying the selected `model` |
| `seed_receipt` | JSON carrying the exact `seed` |
| `outgroup_roster` | TSV with exactly one included `newick_label` |
| `final_tip_roster` | TSV: `newick_label`, `state`, `reason`; state is `INCLUDED` or `OMITTED` |
| `tip_crosswalk` | TSV: `newick_label`, `strain`, `display_label`, `role`, `genus` |
| `annotation_matrix` | adapter-owned TSV: `strain`, `channel`, `feature`, `value`, `state` |

Every locator is relative to a configured data root and every input carries an exact lowercase
SHA-256. Crosswalk labels and strains are each one-to-one; duplicates refuse. Crosswalk rows cover
the complete final roster, while tree tips must equal the `INCLUDED` roster exactly. There is no
prefix inference and no silent tip dropping. `OMITTED` rows travel in a typed omission receipt.

The annotation adapter may provide only strain-aggregate channels: `ANI`, `BGC`, `DOMAIN`, `MODE_B`,
and `ASSEMBLY`. It owns all domain semantics and exact-locus validation; the renderer does not
reconstruct inventories or judgments. A locus-specific future adapter must carry the complete
`strain / full node-or-contig / region / BGC alias` identity and fail if any part is unavailable.

## Output contract

The renderer transactionally writes:

- live-text, vector-geometry SVG and native 300-DPI PNG at both single- and double-column widths;
- deterministic recorded topology, branch lengths, support labels, and explicit display labels;
- accessible, channel-distinct annotation cells without cross-channel normalization or pooling;
- exact plot-data and omitted-tip TSV receipts;
- a dynamic caption/method JSON binding tree, alignment, tool, model, seed, outgroup, roster,
  crosswalk, and annotation hashes;
- separate owner-notes metadata that is not printed as a scientific caption; and
- a complete output/hash receipt.

At each declared publication width, every visible annotation-track x-axis tick label is measured
after the final layout pass and must be disjoint from the annotation axes data rectangle. A label
that touches or enters the data region is a hard refusal even when no two labels collide.

Canonical IQ-TREE Newick with quoted labels is accepted. Comments or extended annotation syntax are
refused so unsupported Newick cannot be misrendered. Any later PDF compilation must preserve the SVG
as vector artwork or pass the native-pixel fallback gate, then verify physical-width text legibility.

This renderer is candidate engineering only. A green render does not sign off the tree, reconcile
MLSA with core-genome topology, accept annotations scientifically, select a product, or authorize a
release.
