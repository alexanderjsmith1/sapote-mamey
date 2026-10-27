# Companion files and optional capabilities

Missing a file for your next task? Check [what ships](#what-is-supplied), then
[the task inputs](#inputs-for-the-selected-task) below. Look in the permitted project
inventory before requesting another copy. If the missing item is a genome FASTA,
you may be able to [recover the submitted genome](#recover-a-genome-from-an-antismash-zip)
from the existing antiSMASH ZIP.

Installed software, supplied data and successful workflow results are separate
states; request only what the selected task is missing.

Use [installation](INSTALL.md) for environment setup,
[external assets](EXTERNAL_ASSETS_GUIDE.md) for reference discovery, and
[the Companion Tool Guide](COMPANION_TOOL_GUIDE.md) for tool roles.

## What is supplied

The CODE ZIP contains the engine, tools, documentation, add-on installer and
supporting profiles. Its only Python wheels are the packaging tools listed in
[wheels/WHEELS_MANIFEST.md](../wheels/WHEELS_MANIFEST.md):

- `wheels/packaging-26.3-py3-none-any.whl`
- `wheels/setuptools-82.0.1-py3-none-any.whl`
- `wheels/wheel-0.47.0-py3-none-any.whl`

These are packaging support, not a complete offline installation. The ZIP contains
no `.hmm` scanner database or normalized NP Atlas reference JSON files. Check any
separately supplied add-on by its actual inventory and compatible wheel tags;
a historical archive name or size does not establish its contents.

## Inputs for the selected task

| Task | Required input |
|---|---|
| Extract a strain's antiSMASH evidence | That strain's antiSMASH result ZIP; follow the [Quick Guide](GUIDE/02_Quick_Guide.md). |
| Compare genes between two strains | Both antiSMASH result ZIPs with CDS translations; follow [offline pairwise comparison](../sapote_addons/README_OFFLINE_ANALYSIS.md). |
| Whole-genome ANI | Both genome FASTAs and a working ANI backend. First check the strains' antiSMASH ZIPs: the submitted genome is usually inside ([recover it](#recover-a-genome-from-an-antismash-zip)). Ask for FASTA files only if neither ZIP is available. |
| Reference comparison | The selected reference archive, GBKs or proteins required by that command; a reference index alone is not every reference input. |
| Cross-strain workbook work | The actual workbook selected for reading or updating. |
| Independent 16S comparison | A bound 16S sequence plus the selected reference/search route; see [local 16S databases](LOCAL_16S_DATABASE.md). |

Missing inputs or unavailable backends remain uncomputed evidence, not biological
absence. Preserve complete locus identities when reporting individual comparisons.

## Recover a genome from an antiSMASH ZIP

When authorized, use a fresh output folder outside the bundle:

```bash
python tools/antismash_input_genome.py \
  --zip /path/to/result.zip --out /path/to/new-output
```

The extractor requires exactly one supported FASTA or GenBank file directly inside
an `input/` folder. Missing, ambiguous, size-refused, unreadable or sequence-empty
inputs are skipped/refused. It writes `<zip-stem>.fasta` and appends `MANIFEST.tsv`
with the source ZIP name, member, format, counts, output hash and note.

After the command, read every `MANIFEST.tsv` note and confirm which FASTAs were
written. If recovery did not complete:

- **No input genome or more than one:** locate the original submitted genome and
  establish which file belongs to this run; the helper does not choose among candidates.
- **Size-refused, unreadable or sequence-empty input:** retain the diagnostic and
  inspect the source member before arranging a replacement.
- **`exists; not overwritten`:** the existing FASTA was preserved and receives no
  new verified output hash. Compare it with its own provenance or choose a fresh destination.
- **Failure before the manifest is complete:** inspect residual files before retrying.
  FASTAs are written before the batch manifest append, so earlier outputs or a partial
  file can remain without a completed manifest.

Retain source ZIP hashes and accession/version bindings separately. The recovered
sequence is what antiSMASH received; extraction does not verify a deposited assembly's
version or completeness, or authorize submission to an external service.

## Comparison backends and fallback limits

`mamey/compare.py` selects DIAMOND first, then a smoke-tested `pyswrd`, then Biopython.
DIAMOND can be supplied through `diamond4py` or a `diamond` executable on `PATH`.
When the binding cannot load, the DIAMOND adapter can use the CLI.

A `pyswrd` selection probe failure falls through to Biopython; a later `pyswrd`
alignment exception also attempts Biopython. That fallback still needs a working
Biopython environment.

A DIAMOND execution failure also falls back to Biopython, so a failed search is
not written as zero hits. Check the backend column to see which aligner produced a row.

See [offline pairwise comparison](../sapote_addons/README_OFFLINE_ANALYSIS.md) and the actual backend diagnostics.
Sequence similarity does not establish compound identity.

## Installation and companion-tool boundaries

Install the core environment through [INSTALL](INSTALL.md). For the optional
comparative/scanner dependencies, the local package declares `.[addons]`.
The `.[all]` convenience extra excludes addons and tests.

For an authorized add-on installation with supplied compatible wheels:

```bash
bash bundle_support/install_sapote_addons.sh /path/to/wheels
```

The installer uses `${PYTHON:-python3}` and requires a virtual environment by default.
It pools wheels from the explicit directory and neighboring search roots, including
upload locations; the directory argument does not restrict discovery to that folder.
Review that scope when only a selected wheel set is intended.

The normal route is offline. `--online` permits pip-index fallback for missing
distributions, not every installation error. The script requires its core dependency
group, attempts figure/analysis dependencies on a best-effort basis, and checks
selected imports. It does not install external binaries, provision HMM/NP Atlas
datasets, or validate biological workflows. A Linux wheel is not evidence of
compatibility with macOS or another Python ABI.

For reader-side cohort tools, use
[the Multi-Cohort Comparison Toolkit guide](../deliverable_tools/README.md).
Individual tools have their own data and write behavior.
