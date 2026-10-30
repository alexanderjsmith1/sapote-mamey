# Find a missing input

Use this page when a task asks for a genome, reference file or optional software.
Start with the antiSMASH ZIP and package you already have; the needed file may be
inside them. [Install](INSTALL.md) covers Python setup, and the
[tool guide](COMPANION_TOOL_GUIDE.md) lists optional programs and downloads.

## What is supplied

The CODE ZIP includes the program, tools, documentation, profiles and add-on
installer. Its bundled wheels support packaging only; they are listed in
[wheels/WHEELS_MANIFEST.md](../wheels/WHEELS_MANIFEST.md). It does not contain a
complete offline environment, scanner HMM databases or normalized NP Atlas data.

## Inputs for the selected task

- **Extract evidence:** one antiSMASH result ZIP; use [Your first run](reader/01_FIRST_RUN.md).
- **Compare genes:** two result ZIPs with CDS translations; use [pairwise comparison](../sapote_addons/README_OFFLINE_ANALYSIS.md).
- **Whole-genome ANI:** both genome FASTAs and a working ANI backend. Check the
  original ZIPs for the submitted genomes before looking for another copy.
- **Reference comparison:** the reference archive, GenBank records or proteins
  required by that command. An index may only locate the data.
- **Workbook updates:** the workbook you intend to update, preferably a working copy.
- **16S comparison:** the query sequence and selected [reference database](LOCAL_16S_DATABASE.md).

## Recover a genome from an antiSMASH ZIP

From the program folder, replace the example ZIP path and choose a new output folder:

```bash
python tools/antismash_input_genome.py   --zip ~/Downloads/EXAMPLE.zip --out ../EXAMPLE-genome
```

The helper needs exactly one supported FASTA or GenBank file directly inside
an `input/` folder in the ZIP. It writes a FASTA and `MANIFEST.tsv` listing the
source member, counts, output hash and any problem.

Read every manifest note. Missing or multiple candidates require finding the
original input; size, parsing or empty-sequence errors need inspection of that
member. `exists; not overwritten` preserves the existing FASTA without verifying
it again. If the command fails before the manifest is finished, check for partial
files before retrying.

Keep the source ZIP hash and accession/version with the recovered sequence.
It is the sequence submitted to antiSMASH; compare its identity with the assembly
you intend to analyze.

## Comparison backends and fallback limits

Pairwise comparison tries DIAMOND, then an available smoke-tested `pyswrd`, then
Biopython. DIAMOND can come from `diamond4py` or an executable on `PATH`.
A DIAMOND execution failure or a later `pyswrd` alignment failure can fall back to
Biopython. Read the backend column and log to see what produced each row.

## Installation and companion-tool boundaries

Use [Install](INSTALL.md) for core dependencies. The `addons` extra adds comparative
and scanner dependencies; `all` does not include addons or tests.

For compatible add-on wheels in a local folder:

```bash
bash bundle_support/install_sapote_addons.sh ../wheels
```

Activate your virtual environment first. The script uses `PYTHON` when set,
otherwise `python3`. It searches neighboring wheel folders too, so review the
selected files if you need a restricted wheel set. Its normal route is offline;
`--online` permits index fallback for missing distributions.

The installer requires its core group, attempts optional figure dependencies,
and checks selected imports. External binaries and reference datasets need their
own installation. See [external assets](EXTERNAL_ASSETS_GUIDE.md).
