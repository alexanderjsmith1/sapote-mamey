# Add another view of a package

Compare predictions with GECCO, prepare genome-side files for metabolomics, or
review candidate fragment pairs. You need an extracted package and its original
antiSMASH ZIP. Run the examples from the program folder; replace `EXAMPLE` and the ZIP path.

Each command writes under the run's `post_seal/` folder, outside the package.
For another attempt, use `--out` with a new folder: existing destinations are
refused, even when empty. Keep the package and source files unchanged during a run.

## GECCO

Get a second set of cluster predictions from the same genome. Install **GECCO
0.11.x** separately and put its executable on PATH; this adapter checks that
version before starting. Then run:

```bash
python mamey_run.py gecco-crosscheck --package runs/EXAMPLE/package \
  --zip ~/Downloads/EXAMPLE.zip
```

The defaults are a probability threshold of 0.8 and one job. Change `--threshold`
or `--jobs` only for a deliberate analysis/resource choice. The adapter launches
GECCO on the whole-genome GenBank member of the package-bound ZIP. If the ZIP has
several eligible genome members, choose one with `--genome-member`.

Open the output's `*_7_gecco_vs_antismash.csv`,
`*_7_gecco_only_clusters.csv` and `*_7_gecco_gene_probabilities.csv`.
The folder also contains the selected genome, raw outputs, log, support file and
receipt. GECCO-only means no overlap with this package's selected region roster.

A version probe has a 15-second timeout; the analysis has no adapter timeout.
On failure, keep the terminal output: a failed native run can lose its staged
files before `gecco.log` is written. The receipt's recorded command contains
staging paths, so use your published paths when reading its outputs later.

<details>
<summary>Check GECCO joins and coordinates</summary>

The returned gene table must match the full source CDS roster, contigs and
coordinates.  Blank/NA probabilities stay unknown;
invalid present probabilities are errors. The gene CSV uses **1-based inclusive**
coordinates, while GECCO-only cluster intervals use **zero-based half-open**
coordinates. Convert explicitly when joining them.

For copied gap-gene tables, repeat `--gap-genes` with each input. TSV files use
tabs; other suffixes use commas. At least one of `locus_tag`, `query_gene` or
`protein_id` is required. When several are present, their nonblank values must
match exactly in each row. Supply complete start/end pairs for coordinate checks.

Read `gecco_join_state` and `gecco_binding_scope`. A tag-only match is labeled
`SOURCE_LOCUS_TAG_ONLY`; unknown tags stay unmatched. Original tables are unchanged.
The copied table adds GECCO columns, so inputs already containing those columns
are refused. Keep the support file, receipt and raw outputs together.

</details>

## Genome-side metabolomics files

Prepare region GenBank files and class hypotheses for an MS workflow:

```bash
python mamey_run.py export-metabolomics --package runs/EXAMPLE/package \
  --source-zip ~/Downloads/EXAMPLE.zip
```

`--source-zip` supplies the original archive: a recorded relative path may not
resolve from the package folder. Its hash must match the package manifest.
Add `--gecco-dir` only for a matching GECCO crosscheck output.

Open `*_metabolomics_targets.tsv`, `metabolomics_targets.json` and
`nplinker/antismash/`. The export also writes source pointers, strain mappings,
a PoDP record template, README and receipt. Compare the exported region count
with the package inventory; missing region members stop the export.

Fill the MS sample mapping and metadata from your actual experiment.
`OPERATOR_COMPLETION_REQUIRED`, null fields and an empty sample list identify
unfinished templates.  JSON lists inside TSV cells
remain serialized JSON.

## Candidate fragment pairs

Recompute the saved pair review using the original archive:

```bash
python mamey_run.py two-proof-rescue --package runs/EXAMPLE/package \
  --input-zip ~/Downloads/EXAMPLE.zip
```

The default `class_routed_v1` policy uses the KS-clade check for KS-bearing pairs.
For eligible non-KS pairs, it checks whether the members together complete their
class core when neither does alone. It also reads position evidence and marker
conflicts. Keep the policy with every reported result.

Open `*_4D_two_proof_rescue.csv` and `receipt.json`. Read the full `identity_a`
and `identity_b`, verdict, `second_proof_channel`, `independent_proof_state`,
`position_verdict` and `position_reference`. The package needs exactly one
`*_4A_RGGMCI_ranked_pairs.csv`; this reader uses stored domain/KS evidence.
A successful command can produce zero pairs or unresolved results.

The position reading shares ClusterBlast evidence with RG-GMCI. Its thresholds
were set on the lineage benchmark and have not been tested on held-out data.
Keep the candidate contigs separate while reviewing the proposed relationship.

### Use a supplied non-KS scorecard

Choose this route only when your task calls for the scorecard-based policy:

```bash
python mamey_run.py two-proof-rescue --package runs/EXAMPLE/package \
  --policy nonks_position_v1 --scorecard reviews/EXAMPLE/scorecard.tsv \
  --out reviews/EXAMPLE/nonks-review
```

`--policy` selects that alternative; `--out` keeps it separate from the default
review. The TSV needs `strain`, exact `identity_a` and `identity_b`,
`layers_verdict` and `relative`. Compare the requested and consumed pair counts:
rows for another strain are skipped, and an unknown verdict spelling leaves the
position check unresolved. A missing scorecard can also produce unresolved rows.

This policy requires complementary HIGH linkage, an observed eligible non-KS core
and a CONSISTENT scorecard reading naming a relative. APART_CLOSE or CONFLICT
vetoes an eligible pair; unavailable or weak position evidence leaves it unresolved.
KS-bearing candidates keep the KS rule. `--policy ks_clade_v2` selects the earlier
KS-only policy when needed for a comparison.

A disjoint-reference fallback can report independent proof PRESENT without
changing its earlier verdict. Read the original pair counters instead of treating
that one field as a completed two-proof result. Keep unresolved KS-only rows
without invented locus assignments. Pair, scorecard and source hashes belong with
the final CSV; the receipt does not hash every output file.

## If a command stops

Read the terminal error and keep the original package. Outputs inside the package
and package symlinks are refused. An interrupted attempt can leave a hidden
staging folder; inspect it with the log and retry at a new destination after
fixing the cause. These readers use `--package` followed by the extracted package
folder, rather than a package ZIP or run root.

<a id="genome-side-metabolomics-bridge"></a>
<a id="second-proof-policy-routed-by-class"></a>
<a id="package-argument-syntax"></a>
