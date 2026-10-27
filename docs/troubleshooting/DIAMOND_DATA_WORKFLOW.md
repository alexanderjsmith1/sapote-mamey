# DIAMOND evidence and integration limits

DIAMOND aligns protein sequences against a reference set you choose. The reference set sets the scope of the comparison, so record it with its hash, along with the query source, the settings and the raw output. Sequence similarity is not product identity or measured activity.

## What the program provides

`mamey/diamond_align.py` is an optional alignment helper. `align_fasta` takes a query protein FASTA and a reference protein FASTA. It uses the `diamond4py` Python binding when that works, or a `diamond` program on your PATH. When neither is available, or an input is bad, it returns the reason. It is an alignment helper, not a tool that loads a TSV into the workbook. Check the guide for the workflow that calls it before you choose one.

Each alignment it returns carries query and subject IDs, percent identity, aligned length, mismatches and gaps, coordinates, e-value, bitscore, and query and subject coverage. A hand-made seven-column TSV does not have the same fields.

## What the workbook does not do

`mamey/cell_provenance.py` always writes `NEEDS_DIAMOND_TSV` placeholders and empty per-locus homolog fields. Supplying a TSV does not fill them, and the main command line has no `--diamond-tsv` option. Keep outside results separately, and match their IDs in a review folder. Do not mark a field complete without a record of the step that filled it.

Older text described a "Release 1 / Release 2" plan and promised reference assets, a hosted service and automatic loading. The current workbook worklist writes `NEEDS_DIAMOND_TSV` placeholders. Verify any external reference set or service separately, recording its provenance and current availability. Check your local assets and the tool you chose. The package file `Troubleshooting/DIAMOND_Data_Workflow.md` is written from text inside the Python code, and older copies may describe an import path the program does not have.
