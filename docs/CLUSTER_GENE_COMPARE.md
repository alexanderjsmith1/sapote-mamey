# Gene-by-gene homology comparison

    python tools/cluster_gene_compare.py --gbk "FixtureA:fixture_a.gbk" \
      --gbk "FixtureB:fixture_b.gbk" --outdir OUT --pdf

Labels must be unique safe basenames, including when compared ignoring case. The
complete output set must be fresh; an existing artifact or symlink is refused.
Inputs remain unchanged. `--min-id` (default 30 percent) and `--min-cov` admit
cross-input global protein alignments using BLOSUM62 and gap penalties -11/-1.
`--engine pyswrd` optionally restricts candidates and can omit matches; the
exhaustive Bio.Align route is the default.

Threshold-admitted edges form single-link **homology groups**. A transitive
connection is not a measured direct pair, and a group can include multiple copies
from one input. This method does not establish orthology or biological function.

| Output | Meaning |
|---|---|
| `gene_pairs.csv` | Admitted measured pairs, identity, coverage and display labels |
| `homology_matrix.csv` | Every member tag in each input/group as a JSON list |
| `homology_members.csv` | All copies, record/gene indices, coordinates and source labels |
| `ortholog_matrix.csv` | Identical compatibility alias of the homology matrix; filename does not imply orthology |
| `annotated_gbks/*.gbk` | Copies retaining original qualifiers; separate inferred labels and provenance |
| `comparison_heatmap.png` | One deterministic representative per input/group, with unmeasured anchor pairs explicit |
| `comparison.pdf` | Optional figure, methods and descriptive interpretation |

Existing `/gene`, `/product`, `/sec_met_domain` and other qualifiers are retained.
The display label is stored in `/mamey_homology_label`; `/mamey_homology_meta`
records its single-link origin, source label set and absence of orthology proof.
Conflicting labels produce an explicit `CONFLICT` display label, not a first-row
choice. Clinker continues to use original `/gene` or `/locus_tag`; these inferred
labels are not promoted into gene annotations. Singleton tags remain source tags.

The figure is a representative identity view, not a copy-count or absence assay.
All copies remain in the two canonical CSVs. No compound, activity, evolutionary
outgroup or functional assignment follows from this comparison. Truncated inputs
and approximate gene boundaries limit the supplied inventory.

Global alignment uses canonical sequence orientation to preserve tie behavior when inputs are swapped. Group metadata records identity/coverage thresholds and the requested engine.
