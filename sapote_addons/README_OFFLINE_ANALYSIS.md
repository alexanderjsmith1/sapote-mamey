# Offline pairwise protein comparison

Before any `doctor` example below, read the [write-probe boundary](../docs/INSTALL.md#doctor-scope-and-write-probe).
Use an editable working installation; if `runs/_doctor_probe` is occupied, leave it
untouched. The current diagnostic can overwrite or remove its probe file.

Sapote-Mamey’s `compare` command performs a directional protein comparison between two antiSMASH result ZIPs. It aligns CDS translations extracted from strain A against translations extracted from strain B and writes one best-hit row for each strain-A CDS.

This is a sequence-similarity aid. It does not identify a compound, prove biosynthetic production, establish gene function, or demonstrate that a gene is biologically absent.

## Inputs

The two required inputs are valid antiSMASH ZIPs containing GenBank records with translated CDS features:

- `--strain-a`: query ZIP. The parser's retained translated CDS features become queries; this is not proof of a complete assembly-wide proteome.
- `--strain-b`: reference ZIP. Its retained translated CDS features form the comparison set.

A sealed Mamey package directory is not accepted by this command because it does not retain the required GenBank records and translations. The command is directional: reversing A and B creates a different query set and can produce a different result.

Two optional whole-genome nucleotide FASTAs enable an ANI calculation:

- `--genome-a`: strain-A assembly FASTA.
- `--genome-b`: strain-B assembly FASTA.

Supply both genome FASTAs or ANI is not attempted. When ANI succeeds, the summary records ANI, aligned fraction, backend, and a claim-safe species-boundary interpretation. The current code labels ANI strictly between 94% and 96% as boundary/indeterminate; exactly 94% is labelled distinct and exactly 96% same species. These are code-level routing labels, not taxonomic acceptance. ANI is rounded before the call. An omitted ANI field can mean it was not requested, a dependency was absent, there were no matches, or parsing/execution failed; preserve warnings and record that disposition separately.

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

The installer defaults to offline resolution with `--no-index`. It pools wheels from the supplied path **and nearby roots**, to depth four; an explicit path does not restrict discovery to that path. Same-named wheel copies use first-found precedence without checksum verification. Bind the selected wheel metadata/hashes and intended environment before installation; this documentation review did not install anything.

`PYTHON` selects the interpreter (default `python3`), and both installation and verification use that interpreter via `"$PY" -m pip` and `"$PY"`. Outside a virtual environment the script refuses with status 2 unless the operator deliberately sets `SAPOTE_ALLOW_SYSTEM_PIP=1`; that override changes system-Python protection and is not part of the normal setup recipe.

Core packages are required; figure packages are a separate best-effort group. Explicit `--online` permits a pip-index fallback only when wheels are absent or resolution reports a missing matching distribution. It changes the network/write scope and is not an automatic repair for any install failure. Partial prior package changes are not rolled back. The script's six required import checks and optional figure checks establish importability only, not complete backend execution, model/database availability or scientific validation. Temporary pooled wheels and error logs are removed when it exits; retain terminal diagnostics in the approved workspace if recovery needs them.

DIAMOND and external data/binaries are not provisioned by this script. Optional Lab Quest source installation requires `SAPOTE_INSTALL_LAB_QUEST=1`; failure there can leave the core install successful. See [DIAMOND status](DIAMOND_STATUS.md), [installation](../docs/INSTALL.md) and [bundle-support roles](../bundle_support/README.md). Source: `bundle_support/install_sapote_addons.sh:32–69,76–122,126–175`.

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

On its normal completed path the command writes these two named files; an existing output directory can retain unrelated or stale files:

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

## Identity, overwrites and recovery

The output directory is created before ZIP parsing or backend checks. The two normal files are individually replaced via a temporary sibling; they are not committed as a pair, and old completion outputs are not invalidated first. A failed attempt may leave an empty directory, a new CSV with an old summary, or both prior files unchanged. A surviving filename is not proof that the latest attempt succeeded. Use a dedicated destination, record invocation/input hashes and terminal status, and preserve an accepted prior result before a governed refresh.

Query keys use the locus tag (or an enumerated `cds_N` fallback) without contig/region identity. Repeated locus tags can collide in best-hit dictionaries and make multiple rows share a result. Bind ZIP identities and retained CDS counts, check locus-tag uniqueness, and retain full contig/region/BGC identity separately before locus-level interpretation. No source/ZIP hashes or full locus identifiers are emitted in the two normal files.

Invalid thread count returns 2 before output creation. Missing/non-ZIP inputs, no translated CDS or no backend return 1; completed comparison returns 0 even when ANI is absent or every protein row is `no_hit`. Other filesystem/parser/backend failures may propagate. Zero-hit output can also conceal a failed DIAMOND route, as detailed in [DIAMOND status](DIAMOND_STATUS.md). Inspect warnings and per-row backend instead of treating status 0 as successful evidence for every requested layer.

Source: `mamey/compare.py:111–123,209–227,343–404,407–525`; retained CDS extraction `mamey/parsers.py:872–923`. No comparison/ANI or installer was executed for this documentation audit. For CPU and memory notes, see [comparison resource control](../docs/COMPARE_RESOURCE_CONTROL.md).
