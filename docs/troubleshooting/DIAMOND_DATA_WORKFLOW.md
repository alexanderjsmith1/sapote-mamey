# DIAMOND evidence and integration limits

DIAMOND aligns protein sequences against a reference set you choose. The reference set sets the scope of the comparison, so record it with its hash, along with the query source, the settings and the raw output. Sequence similarity is not product identity or measured activity.

## What the program provides

`mamey/diamond_align.py` is an optional alignment helper. `align_fasta` takes a query protein FASTA and a reference protein FASTA. It uses the `diamond4py` Python binding when that binding can be imported, and a `diamond` program on your PATH only when the import fails. Each call checks availability and tries importing the binding, otherwise selecting the CLI when available. If the binding imports but database construction or search fails, the helper returns that failure without retrying the CLI. Successful alignment results include `provenance.backend`; failure results may omit provenance, so retain the reason and external execution records. Unknown sensitivity settings can raise before the availability check. It is an alignment helper, not a tool that loads a TSV into the workbook. In this tree `align_fasta` is called by `mamey/compare.py`, `tools/gap_directed_rescue.py` and `tools/gene_synteny_map.py`. Read the help or guide for the one you use before you choose it.

Each alignment it returns carries query and subject IDs, percent identity, aligned length, mismatches and gaps, coordinates, e-value, bitscore, and query and subject coverage. A hand-made seven-column TSV does not have the same fields.

## What the workbook does not do

When a run reaches its cell-provenance step, `mamey/cell_provenance.py` writes `NEEDS_DIAMOND_TSV` placeholders and empty per-locus homolog fields. Supplying a TSV does not fill them, and the main command line has no `--diamond-tsv` option. Keep outside results separately, and match their IDs in a review folder. Do not mark a field complete without a record of the step that filled it.

Older text described a "Release 1 / Release 2" plan and promised reference assets, a hosted service and automatic loading. The current workbook worklist writes `NEEDS_DIAMOND_TSV` placeholders. Verify any external reference set or service separately, recording its provenance and current availability. Check your local assets and the tool you chose. The package file `Troubleshooting/DIAMOND_Data_Workflow.md` is written from text inside the Python code, and older copies may describe an import path the program does not have.
