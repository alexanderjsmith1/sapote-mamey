# Owner-kept Figure Factory inputs

This page is for a **cohort** of sealed packages. It does not apply to a single strain.

`tools/build_owner_kept_figure_inputs.py` prepares source-bound data tables for nine earlier
cohort figure designs, kept so they can be rebuilt without redoing the extraction. The designs are
F03a, F03b, F03c (domain counts), F04f, F04g, F09a (product-class counts), F05a (cassette
families), F06d (resistance families) and F09e (BGC density). The tool does **not** render or
accept a figure. Run it once on the cohort, then review or plot from its tables.

## Steps

You need a `runs` folder with one run per strain, laid out as `runs/<STRAIN>/package/`, and
each strain's sealed package ZIP. Step 2 reads the ZIPs, not the folders. Each ZIP must contain
`Project_Memory_Snapshot.json`; a strain without a ZIP, or without that file, is recorded as
missing, not zero.

1. Build the cohort widget data:

   ```bash
   python mamey_run.py interactive-figures --runs-dir runs --out reviews/cohort/AS_All_Strains_Widget_Data.json
   ```

   The command writes the JSON file you name. Pass `--strains` to build from a chosen list. It
   records each strain's package ZIP name, taken from a `*.zip` in `runs/<STRAIN>/` or
   `runs/<STRAIN>/package/`. If the strains were run under different antiSMASH strictness, the
   figure steps refuse; add `--acknowledge-mixed-antismash-profile` here and name the mix in the
   caption. A strain whose strictness is recorded as `unknown` is refused even with that flag.

2. Build the source bundle from that file and the packages it names. `--package-dir` must be
   one flat folder that holds the package ZIPs, named as in the widget data. The ZIPs sit inside
   `runs/<STRAIN>/`, so `runs` itself is not such a folder. Copy the ZIPs into a new folder first;
   the originals are not changed:

   ```bash
   mkdir package_zips && cp -n runs/*/*.zip runs/*/package/*.zip package_zips/ 2>/dev/null
   ls package_zips | wc -l
   python mamey_run.py codex-figure-sources \
     --widget-data reviews/cohort/AS_All_Strains_Widget_Data.json \
     --package-dir package_zips --outdir reviews/cohort/FIGURE_SOURCE_BUNDLE
   ```

   `mkdir` fails if `package_zips` already exists, and the `&&` then skips the copy, so an old
   folder does not get new ZIPs mixed in. Pick a new folder name in that case. `cp -n` does
   not overwrite, so two ZIPs with the same name leave only the first; the `ls` count should
   equal the number of strains. A ZIP the folder lacks reads `MISSING_PACKAGE` for that strain,
   and one missing ZIP is enough to make the receipt status `FAIL`, which stops step 3. A
   failed run leaves its output folder, so use a new `--outdir` for the next try. The command
   name is historical; it is the only command that builds this bundle.

3. Build the owner-kept input tables. The output folder must not exist yet:

   ```bash
   python tools/build_owner_kept_figure_inputs.py \
     --widget-data reviews/cohort/AS_All_Strains_Widget_Data.json \
     --source-bundle reviews/cohort/FIGURE_SOURCE_BUNDLE \
     --outdir reviews/cohort/OWNER_KEPT_INPUTS
   ```

Source receipt hashes and the widget-data hash must match before any output is written. A
mismatch, or an unusable source bundle, stops the run with nothing written. The tool prints
`OUTPUT_REFUSED: ...` and exits 2.

## Output

The exit code is 0 when the tables are written, even if some designs are on hold. Open
`FIGURE_REBUILD_READINESS.tsv` before you plot.

| File | Content |
|---|---|
| `domain_counts.csv` | Strain by domain category |
| `class_by_strain.csv` | Strain by antiSMASH product-class membership count |
| `cassette_types.csv` | Strain by cassette-registry family |
| `resistance_families.csv` | Strain by resistance-scan family |
| `strain_context.csv` | Governance, host group, cohort role, denominator membership, genus, genome size, corrected-BGC count, assembly tier, snapshot state |
| `genus_selection.tsv` | An editable table for choosing comparison genera in a later plot. It does not infer taxonomic scope |
| `FIGURE_REBUILD_READINESS.tsv` | One row per design with `REBUILD_READY` or `HOLD` and the reasons |
| `FIGURE_INPUT_RECEIPT.json` | Source hashes, row counts, study denominator, benchmark selection and holds |
| `a8_boundary_inventory.csv`, `a8_architecture_features.csv`, `a8_manifest_scan_counts.csv`, `a8_resistance_routing.csv`, `a9_kcb_scores.csv` | Inputs for five provisional designs |
| `A8_PROVISIONAL_READINESS.tsv` | Readiness for those five. Every row is `PROVISIONAL_BINDING`, and one design always carries a scope hold named `SCOPE_1_VS_RENDER_CONTRADICTION` |

Read the readiness files this way:

- `REBUILD_READY` means the listed inputs were present. It does not mean every strain has every
  category, that an absent row is zero, or that a figure is accepted.
- The receipt's overall status comes from the nine main rows. It can read `PASS` while the
  provisional file holds a design. Check both files.
- Aggregate category files are not exact-locus records. For any individual BGC, keep the full
  identity: **strain / full contig / region / BGC alias**.

## Benchmarks and genus

A record typed `EXTERNAL_BENCHMARK` must declare `include_by_default=false`. It stays out of the
tables unless you name its exact identifier with `--external-benchmark`, repeated once per
benchmark. A selected benchmark can feed a comparison panel. It never enters the study
denominator or study percentages. An unknown identifier, or a benchmark that is on by default,
stops the run before any output exists.

Designs that compare groups need a genus for every study strain. The genus is the first word of
the `taxonomy` field in the strain's `Project_Memory_Snapshot.json`. If one is missing, the
affected designs are held with `MISSING_STUDY_GENUS`; fix the taxonomy in the package, not the
table. The tool does not infer genus from strain names or host labels. Other holds are
`MISSING_STUDY_DENSITY_INPUT` (BGC density needs genome size and corrected-BGC count) and
`NO_<KIND>_ROWS` (the design's source table is empty).

## Rebuild and edits

Rebuild into a new folder when the source packages or benchmark selection change. Editing
`genus_selection.tsv` does not change the tool's receipt. Save the edited file with its own hash
and name the plot that reads it.

## What the numbers mean

Domain, cassette, resistance-family and product-class values are annotation-based genomic
capacity. They do not show expression, production, activity, product identity or novelty.
Corrected BGCs per Mbp uses a boundary-weighted BGC count: interior regions count 1, edge regions 0.5 and full-contig regions 0.25 (`mamey/assembly.py:142-143`). That weighting is a heuristic, not a corrected biological count or a production rate. Keep the raw counts beside it.
Write captions and make comparisons as separate later steps.
