# Gene-by-gene homology comparison

    python tools/cluster_gene_compare.py --gbk "ExampleA:region_a.gbk" \
      --gbk "ExampleB:region_b.gbk" --outdir OUT --pdf

Give each `--gbk` one cluster GenBank file, normally one antiSMASH region, as `LABEL:path`. Repeat the flag for each cluster you compare. The label becomes a column name. `--outdir` defaults to `cluster_compare_out`. Exit 0 and a console line giving the cluster, pair and group counts mean the files were written.

Labels must be unique safe basenames, including when compared ignoring case. The
complete output set must be fresh; an existing artifact or symlink is refused.
Inputs remain unchanged. `--min-id` (default 30 percent) and `--min-cov`
(default 0 percent, no additional coverage cutoff) admit cross-input global protein
alignments using BLOSUM62 and gap penalties -11/-1. Both thresholds must be finite
percentages in [0,100]; coverage uses the longer input protein as its denominator.
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

Global alignment uses canonical sequence orientation to preserve tie behavior when inputs are swapped. Group metadata records identity/coverage thresholds and the engine. The recorded engine is the one that ran: if `--engine pyswrd` is requested and pyswrd cannot be imported or cannot align on the machine, the command stops with `CLUSTER_GENE_COMPARE_ENGINE_UNAVAILABLE` (exit 2) before writing outputs, instead of falling back to the exhaustive comparison.

## Inventory, receipt and rendering boundaries

Inventory extraction includes translated CDS from **all** GenBank records, with zero-based half-open feature coordinates and record/gene indices. Labels identify comparison inputs; they are not validated four-part locus identities. Retain strain, full contig/node, region, BGC alias and each input path/hash separately. A multi-record comparison does not establish physical linkage.

Coverage is alignment columns containing residues in both sequences divided by the longer input protein length; it is not query-only coverage. Admission uses unrounded identity/coverage, while exported measured pairs round identity to one decimal and coverage to an integer. Near-threshold inspection must use the declared computation, not infer admission by re-thresholding the rounded CSV.

There is no comparison-contract JSON, source-hash manifest or output-hash receipt in the emitted roster. Qualifier metadata records grouping parameters but does not bind source bytes or scientific acceptance. Heatmap axis labels truncate at 34 characters, and no SVG is emitted. Full identity belongs in the canonical tables/receipt, not an abbreviated axis.

The fresh complete-set transaction rolls back owned publication links on ordinary failure; it is not crash-atomic. Cleanup failure can return an error after outputs were published. Inspect the actual roster and diagnostics before retrying, without overwriting prior outputs. Zero exit is software output production, not absence, orthology, visual clearance or scientific adoption. See the [cluster relationship guide](CLUSTER_RELATE.md) for the shared transaction limits.

Read the optional PDF's methods sentence with care. It says every cross-input CDS pair was aligned and it omits the coverage cutoff, even when `--engine pyswrd` restricted the candidates. The engine and both thresholds are in the run settings you passed, so record them yourself. Do not cite that sentence as the method until it matches the settings you used.
