# Offline pairwise protein comparison

Sapote-Mamey’s `compare` command performs a directional protein comparison between two antiSMASH result ZIPs. It aligns CDS translations extracted from strain A against translations extracted from strain B and writes one best-hit row for each strain-A CDS.

This is a sequence-similarity aid. It does not identify a compound, prove biosynthetic production, establish gene function, or demonstrate that a gene is biologically absent.

## Inputs

The two required inputs are valid antiSMASH ZIPs containing GenBank records with translated CDS features:

- `--strain-a`: query ZIP. Every translated CDS from this input becomes a query.
- `--strain-b`: reference ZIP. Its translated CDS features form the comparison set.

A sealed Mamey package directory is not accepted by this command because it does not retain the required GenBank records and translations. The command is directional: reversing A and B creates a different query set and can produce a different result.

Two optional whole-genome nucleotide FASTAs enable an ANI calculation:

- `--genome-a`: strain-A assembly FASTA.
- `--genome-b`: strain-B assembly FASTA.

Supply both genome FASTAs or ANI is not attempted. When ANI succeeds, the summary records ANI, aligned fraction, backend, and a claim-safe species-boundary interpretation. ANI from 94% to 96% is reported as boundary/indeterminate.

## Check and install dependencies

From the extracted bundle root, inspect the current environment first:

```bash
python mamey_run.py doctor
python mamey_run.py compare --help
```

The lean CODE bundle contains the installer but not the wheel collection. Attach a complete set of platform-compatible add-on wheels, activate the Python environment that should receive them, and pass the wheel location explicitly:

```bash
bash bundle_support/install_sapote_addons.sh /path/to/addon-wheels
```

The installer uses `pip --no-index`; it does not download packages. It pools `.whl` files from the supplied path and several nearby search locations, then requires its complete core dependency set to resolve. A missing or incompatible core wheel stops the install. Figure and analysis wheels are attempted separately and are best-effort.

The script invokes `pip` for installation and `python3` for its import check. Confirm that both commands refer to the intended environment before running it. The installer does not install DIAMOND; see `sapote_addons/DIAMOND_STATUS.md` for the optional DIAMOND path.

## Run a comparison

Minimal protein comparison:

```bash
python mamey_run.py compare \
  --strain-a inputs/query-antismash.zip \
  --strain-b inputs/reference-antismash.zip \
  --out comparison_results
```

Add ANI when both whole-genome assemblies are available:

```bash
python mamey_run.py compare \
  --strain-a inputs/query-antismash.zip \
  --strain-b inputs/reference-antismash.zip \
  --genome-a inputs/query-genome.fasta \
  --genome-b inputs/reference-genome.fasta \
  --alignment-threads 2 \
  --out comparison_results
```

`--alignment-threads` must be a positive integer. It is passed to DIAMOND or each pyswrd query batch; the Biopython fallback remains serial. The requested value is recorded in the JSON summary and is not a measurement of actual native thread use.

## Outputs

The current command writes exactly two files:

- `S5_gene_level_similarity.csv`: one row per strain-A CDS, with `query_gene`, `best_match_B`, percent identity, query coverage, call, backend, and note.
- `gemini_summary.json`: counts, the selected alignment backend, requested thread count, fixed classification guardrails, the S5 filename, and ANI only when ANI succeeds. The filename is retained for compatibility.

The gene calls currently use fixed code-level thresholds:

- `present`: identity at least 70% and query coverage at least 60%.
- `divergent_candidate`: a hit exists but it does not clear both thresholds.
- `no_hit`: no best hit was returned.

`divergent_candidate` and `no_hit` are not evidence of biological absence. Input completeness, antiSMASH CDS coverage, assembly fragmentation, sequence-length guards, and backend behavior can all affect the result.

## Current limitations

- The command compares CDS translations exposed by the two antiSMASH ZIPs; it is not a general whole-genome orthology workflow.
- It does not currently emit per-BGC summaries, ClusterBlast/SubClusterBlast/KnownClusterBlast recovery tables, a fragmentation or scaffold map, or a 16S comparison.
- `--min-identity` and `--min-coverage` appear in the CLI but are not currently applied by `compare_command`; do not use them to claim a changed decision threshold.
- Backend selection is automatic. There is no CLI option to force DIAMOND, pyswrd, or Biopython.
- A successful command is mechanical comparison evidence only. Interpret the rows with package identity, BGC boundaries, evidence provenance, and claim ceilings supplied separately.

For CPU and memory notes, see `docs/COMPARE_RESOURCE_CONTROL.md`.
