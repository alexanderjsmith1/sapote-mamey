# Phylogenetic workflow gate guide

This page covers the companion tools that build and check a multi-locus (MLSA) tree: `build_mlsa.py`, `phylo_preflight.py`, `phylo_postflight.py`, `ladder_test.py` and `tree_trust_audit.py`. They check mechanical properties of inputs and outputs. A pass does not establish biological association, strain identity, rooting, species boundaries or publication readiness. Read that once here; it applies to every tool below.

Before any tree compute, read the [companion tool protocol](LLM_COMPANION_TOOL_PROTOCOL.md). It requires the size and resource preflight and an explicit approval. `mamey_run.py phylo-run --approved`, `tools/run_planned_tree.py --approved` (with `approved=true` in `RUN_STATE.json`), `tools/phylo_place.py build-ref`/`all --approved-by` and `tools/phylo_autopilot.py run-16s --approved-by` take an approval option. `tools/build_mlsa.py` and `mamey_run.py phylo-mlsa` have none (`tools/_mlsa_resources.py:308-317`), so for those two the approval is your own step before you run them; the resource preflight still applies. Setup is in the [companion guide](COMPANION_TOOL_GUIDE.md). `ladder_test.py` also needs Biopython.

## Which entry point

- For one strain from an antiSMASH ZIP, use `python mamey_run.py phylo-mlsa --input-zip ZIP --query-label LABEL --mode plan|prepare|run`. Start with `plan`.
- For a folder of genomes you already hold, use `tools/build_mlsa.py`, described next.

## Build an MLSA tree

```bash
python tools/build_mlsa.py GENOMES OUTPUT [--bin-dir BINARIES] [--seeds-dir SEEDS]
```

Run it from the bundle root.

- `GENOMES` is a folder of genome `.fna` files.
- `--bin-dir BINARIES` is optional. It names a folder holding the Prodigal, makeblastdb, BLASTP, MUSCLE and IQ-TREE executables. Without it the tool uses `$MAMEY_PHYLO_BIN`, then your `PATH`.
- `--seeds-dir SEEDS` is optional. It names a folder of seed protein files for the loci to search. Without it the tool uses the seeds shipped in `mamey/data/phylo_seeds/` (atpD, gyrB, recA, rpoB, trpB).
- `OUTPUT` must be new or empty. A prior partial run is refused. Keep it as evidence and pick a fresh folder.

Any of the five external tools exiting nonzero stops the build, and the run log keeps its diagnostics. A zero exit with missing, empty or inconsistent output also fails. Taxon names with spaces or Newick punctuation are percent-escaped, and `taxon_map.tsv` keeps each exact input filename.

Read `run_status.json` before you use any output. `FAILED` and `IN_PROGRESS` outputs may be partial. `COMPLETE` alone is not enough for the governed route: also keep `RESOURCE_ATTEMPT/<attempt>/SUCCEEDED.json` and the promoted output hashes. This route does not resume or reuse a cached build.

`loci_report.tsv` has a `status` column. `HIT` is an accepted BLAST subject with a matching CDS. `NO_HIT` means the search returned nothing, which is not proof of absence. These are the only two values (`tools/build_mlsa.py:358,375`). A failed external tool is not a row: it stops the build, writes `TOOL_FAILURE: <program> exit <code>` to `mlsa.log` and to `run_status.json` (state `FAILED`), and the worker exits 6, so the loci table may not be written (`tools/build_mlsa.py:282-290`). If every search has no usable hit, the build exits nonzero with `NO_USABLE_DATA`. A failed later stage can leave a loci report, so the run status decides whether it is usable.

Resource defaults: 4 threads, 3,800,000,000 bytes of memory, 2,000,000,000 bytes of free disk and 900 seconds. Use `--threads 1` on a single-core policy. Exit 4 means an early refusal. Exit 6 means a caught worker failure. Keep failed attempts and their diagnostics under `RESOURCE_ATTEMPT`; do not treat an older status as current.

## Preflight and postflight check codes

Preflight checks the inputs before compute. Postflight checks the finished tree. Both are read-only and exit 1 on any FAIL. Warnings exit 0.

### What preflight needs

Run `python tools/phylo_preflight.py GENOMES` from the bundle root. It prints one line per check and ends with `DO NOT BUILD` if any check failed. To pass, set up four things first:

- **`TREE_SPEC.json`** in the folder that contains `GENOMES` (beside it, not inside it). It declares what the tree is. Its keys include `scope` (a family or order), `taxon`, `cohort`, `outgroup`, `min_comparators_per_genus` and `title`. Without the file, check S1 fails and the cohort check (H1) warns. You can pass `--cohort` instead of a `cohort` key.
- **The tools on `PATH`**: GToTree, muscle, prodigal, hmmsearch and iqtree. Run `source tools/gtotree_env.sh` first. Check E1 lists any that are missing.
- **`GToTree_HMM_dir`** set to a folder that holds `Actinobacteria.hmm`. The same script sets it. Check E1b fails otherwise.
- **An outgroup genome** in `GENOMES` whose file name contains `OUTGROUP`. Use `--outgroup TEXT` to match a different piece of the file name. Check O1 fails if nothing matches.

Each ingroup genome's file name must start with its genus, capitalized, such as `Streptomyces_EXAMPLE.fna`; the genus is read from the text before the first `_`, space or `.`. Otherwise check T1 fails. The genomes themselves must be non-empty, non-duplicate FASTA files of genome size (checks G1 to G3). The table below lists only some of the checks. Read every line of the output, not just the failures. A GToTree older than 1.8.19 gives a warning on check E2, not a failure.

| Code | Tool | What it checks |
|---|---|---|
| E1, E2 | preflight | Required tools are on PATH; GToTree version is at least 1.8.19. |
| O2, O3 | preflight | The outgroup genus is not also in the ingroup; the outgroup is a plausible sister group. |
| R1 | preflight | Registry accessions and binomials match supplied evidence records. |
| P3 | postflight | Support values are present and weak nodes are reported. |
| P6 | postflight | Tip count matches the input genome count. |

Preflight selects only top-level lowercase `.fna` and `.fasta` files. With several outgroups matched by filename, O2 and O3 are skipped. Save the JSON receipt (`--json`) in a fresh file outside your evidence folder, and read each check. For environment names, input limits and recovery, see the [preflight source contract](reference/06_CURRENT_SOURCE_SCOPE.md#phylogeny-preflight-local-probes-and-conditional-checks).

### R1 exact accession evidence

```bash
python tools/phylo_preflight.py GENOMES --r1-registry registry.tsv --r1-evidence evidence.json --json preflight.json
```

All other preflight checks still run. The registry needs the columns `assembly_accession` and `outgroup_species_strain`. R1 needs a complete versioned accession with its GCF or GCA prefix. It never strips versions, equates GCF and GCA, or reads organisms from filenames. It makes no network calls and writes no registry.

The evidence manifest lists JSON records and their SHA-256 digests. Relative paths resolve against the manifest:

```json
{"records": [{"path": "record.json", "sha256": "<64 lowercase hexadecimal characters>"}]}
```

Each record looks like this (the accession and organism are illustrative):

```json
{"assembly_accession": "GCF_000000001.1", "organism_name": "Examplegenus example"}
```

Every registry row gets a result. Exact evidence with a matching binomial gives `VERIFIED_BINOMIAL`. Conflicting records or a binomial mismatch give an R1 `FAIL`. Missing evidence, invalid accessions, hash drift and empty registries stay `UNVERIFIED` with a warning, and the exit is still 0. Read the per-row state, not just the exit code. Hashing proves the bytes match, not that the record is true.

### Postflight

```bash
python tools/phylo_postflight.py TREEFILE --outgroup SUBSTR --genomes-dir GENOMES --json postflight.json
```

Postflight uses lexical tip, support and root-depth checks and substring outgroup matching. P3 PASS on a placement graft is an exemption, not a measured confidence. P6 can PASS on an empty `.fna` roster, and it compares counts rather than identities. Weak-support details appear only in the JSON. Before you accept a tree, also check exact tips, support and rooting, and the rendered page. See the [postflight source contract](reference/06_CURRENT_SOURCE_SCOPE.md#phylogeny-postflight-lexical-checks-and-unmeasured-evidence).

## Descriptive density ladder

```bash
python tools/ladder_test.py FOLDER PANEL_STEM PATTERN
```

`FOLDER` holds at least two directories named `PANEL_STEM_<integer>x`, for example `panel_1x` and `panel_2x`. Each must hold exactly one `.nwk` or `.treefile`. `PATTERN` is a case-insensitive piece of a tip name; every tip whose name contains it is marked. At least two tips must be marked and at least one must be unmarked, and the marked tips must be the same in every rung.

Each tree needs unique, nonempty tip names and finite, nonnegative branch lengths. Missing or invalid data exit 2. For each marked tip, the tool takes the fraction of its nearest neighbors that are marked, then averages over marked tips. Ties use relative tolerance `1e-9` and absolute tolerance `1e-12`. The reference value is `(marked - 1) / (total - 1)`, and the ratio is observed divided by that reference. This is descriptive. It is not a significance test and has no interpretation thresholds.

The JSON on stdout records the tie fraction, marked identities, conditional monophyly and whether the smallest containing clade spans every tip. Save that output yourself, along with the rung paths and hashes. If every other tip is tied as a nearest neighbor for every marked tip, the rung is `UNINFORMATIVE` and the exit is 2. Other valid ladders exit 0 with an `UNDETERMINED` biological interpretation. The input root is not validated.

## Tree artifact audit

```bash
python tools/tree_trust_audit.py --manifest trees.json --output audit.json --gate tools/tree_sanity_check.py
```

The output file must not exist yet. Omit `--gate` only when you accept an unverified gate result. The gate is a Python script run on the tree path alone; exit 0 means it passed, exit 2 means failure, and any other exit or a timeout stays unverified. Declared outgroups are checked separately and are not passed to the gate.

The manifest binds each tree to its companion files. Relative paths resolve against the manifest. Nothing is found by scanning folders or guessing names.

```json
{"trees": [{"tree": "tree.nwk", "metadata": "meta.tsv", "render": "tree.png", "render_receipt": "render.json", "outgroups": ["Reference"]}]}
```

Metadata needs `tip` and `label` columns (change them with `--tip-column` and `--label-column`). Joins use the complete exact tip string. Duplicate identities, missing joins and blank labels fail.

The render receipt must hold `tree_sha256`, `metadata_sha256` and `render_sha256`, each computed from that file's bytes. A timestamp cannot replace it. Matching hashes show which files go together; the audit does not look at the render.

Each row reports `MECHANICAL_PASS`, `UNVERIFIED` or `FAIL`. The command exits 0 only when every row is `MECHANICAL_PASS`, 1 when the audit finished with holds or failures, and 2 when it refused an input or output. The audit writes its output without a temporary file, so a write failure can leave a partial file. Keep and review it before you retry, and record the gate command you ran.

## Limits

- Placement uses a single-genus outgroup rule with a root fallback. It does not validate the root. Do not cite it as proof of rooting.
- Minority reference genera are not independent evidence of an outgroup.
- Resource estimates are allowances, and sampled monitoring can overshoot between samples. They are not scientific approval.
