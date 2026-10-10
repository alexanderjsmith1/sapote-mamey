# Phylogenetic workflow gate guide

These companion tools validate bounded mechanical properties of their inputs and outputs. Their results do not establish biological association, strain identity, appropriate rooting, species boundaries, scientific acceptance or publication readiness. External phylogenetic tools and Biopython remain optional dependencies.

## MLSA build outputs

Run `python tools/build_mlsa.py GENOMES OUTPUT --bin-dir BINARIES --seeds-dir SEEDS` from the bundle root. The input directory contains genome `.fna` files. The output must be new or empty. Reusing a prior partial run is refused; retain that run as evidence and choose a fresh output directory.

Prodigal, makeblastdb, BLASTP, MUSCLE and IQ-TREE stop the build immediately on a nonzero exit. The run log retains tool diagnostics. A zero exit with missing, empty or inconsistent required output also fails. BLAST uses safe relative database, proteome and seed filenames inside an explicit working directory, allowing input and output paths to contain spaces. Taxon names with spaces or Newick punctuation are reversibly percent-escaped. `taxon_map.tsv` preserves each exact input filename; ordinary taxon names are unchanged.

Read `run_status.json` before using any generated files. Only `COMPLETE` identifies a mechanically completed build. `FAILED` and `IN_PROGRESS` outputs may be partial and must not be treated as completed data. This change intentionally does not support cached or resumed builds.

`loci_report.tsv` adds a `status` column. `HIT` records an accepted BLAST subject with a matching CDS. `NO_HIT` means BLAST successfully returned no hit for that search; it does not establish biological absence. If all searches have no usable hits, the build exits nonzero with `NO_USABLE_DATA`. Tool failures carry `TOOL_FAILURE` in the status and log instead of creating biological absence rows. A failed later stage may leave a loci report; the run-level status still controls its usability.

## Preflight roster, probes and receipt scope

Preflight runs local environment/version probes and reads/hashes selected files before expensive analysis. It selects only top-level lowercase `.fna`/`.fasta` files and can exit0 with warnings or omitted conditional checks. Multiple filename-matched outgroups skip O2/O3; a JSON check list is not a source/tool hash manifest. Use a fresh JSON receipt outside evidence with an existing parent, retain source paths/hashes and inspect each check. See [the selected preflight source contract](reference/06_CURRENT_SOURCE_SCOPE.md#phylogeny-preflight-local-probes-and-conditional-checks) for exact environment names, input/map/schema limits, conditional checks and recovery.

## Exact accession evidence for R1

Run `python tools/phylo_preflight.py GENOMES --r1-registry registry.tsv --r1-evidence evidence.json --json preflight.json`. All existing preflight checks still run. The environment check, including E2, is preserved.

The registry requires `assembly_accession` and `outgroup_species_strain` columns. R1 requires a complete versioned accession, including its GCF or GCA prefix. It never strips versions, matches only numeric bodies, equates GCF and GCA, or derives organisms from filenames. Paired assembly accessions and taxonomic synonym adjudication are outside this bounded checker.

The evidence manifest explicitly identifies JSON records and their SHA-256 digests. Relative record paths resolve against the manifest. For example, an illustrative manifest has the following shape; replace the digest with the SHA-256 of the actual record bytes.

```json
{"records": [{"path": "record.json", "sha256": "<64 lowercase hexadecimal characters>"}]}
```

Each bound record has this schema. The example accession and organism are illustrative, not an asserted database observation.

```json
{"assembly_accession": "GCF_000000001.1", "organism_name": "Examplegenus example"}
```

Supply records through a governed acquisition process and retain their source provenance. Hash checking verifies byte identity; it does not independently authenticate the biological contents of an operator-supplied record. R1 compares exact accessions and complete binomials only. Culture collection identifiers, strain equivalence, synonyms and biological outgroup suitability remain unverified.

Every registry row receives a result. Exact evidence and binomial agreement produce `VERIFIED_BINOMIAL`. Conflicting records or a binomial disagreement cause an R1 `FAIL`. Missing evidence, invalid accessions, incomplete labels, unreadable files, hash drift and empty registries remain `UNVERIFIED` and produce a warning. Warnings preserve the existing preflight exit convention and do not grant verified status. No cache, inventory or registry is written, and R1 performs no network calls.

## Finished-tree postflight scope

`phylo_postflight.py` uses lexical tip/support/root-depth checks, substring outgroup matching and conditional count/taxonomy checks. Placement P3 PASS is an exemption without measured placement confidence; P6 can PASS on an empty matching `.fna` roster and compares counts rather than exact identities. Warning-only results can exit0, and weak-support PASS details require the JSON rather than stdout. See [the current postflight source contract](reference/06_CURRENT_SOURCE_SCOPE.md#phylogeny-postflight-lexical-checks-and-unmeasured-evidence) for input/mode/receipt limits and recovery. Require separate exact-tip, support/rooting and rendered-page evidence before acceptance.

## Descriptive density ladder

Run `python tools/ladder_test.py FOLDER PANEL_STEM PATTERN`. A ladder requires at least two directories named `PANEL_STEM_<integer>x`; every matched directory must contain exactly one `.nwk` or `.treefile`. Selection is explicit and deterministic. The marked tip identities must agree across rungs.

Each tree requires unique nonempty tip names, finite nonnegative branch lengths on every non-root edge, at least two marked tips and at least one unmarked tip. Missing or invalid data cause exit 2. Biopython reads the trees; the tool does not change the process import path to a machine-specific installation.

For each marked tip, the observed fraction is the number of marked nearest neighbors divided by the size of the nearest-neighbor set. The tool averages these fractions across marked tips. Ties use relative tolerance `1e-9` and absolute tolerance `1e-12`, reported in the JSON. The descriptive reference is `(marked - 1) / (total - 1)`; the ratio is observed divided by this reference. It is not a significance test and has no biological interpretation thresholds.

The output records the tie fraction, marked identities, conditional monophyly and whether the smallest containing clade spans all tips. A root-spanning intruder count is flagged as vacuous context. If every other tip is tied as a nearest neighbor for every marked tip, the rung is `UNINFORMATIVE`: measurements are emitted, but the CLI returns exit 2. Other valid ladders return zero with an explicit `UNDETERMINED` biological interpretation. The input root is not independently validated.

## Explicit tree artifact audit

Run `python tools/tree_trust_audit.py --manifest trees.json --output audit.json --gate tools/tree_sanity_check.py`. The output must not already exist. Omit `--gate` only when an unverified gate result is intended. The selected gate is a Python script run with the current interpreter; exit 0 means that configured gate passed, exit 2 means failure, and other exits or timeouts remain unverified.

The manifest binds each tree to exact companion artifacts and exact declared outgroup tip identities. Relative paths resolve against the manifest; no newest bundle, dated root, directory scan or metadata-name guess is used.

```json
{"trees": [{"tree": "tree.nwk", "metadata": "meta.tsv", "render": "tree.png", "render_receipt": "render.json", "outgroups": ["Reference"]}]}
```

Metadata needs `tip` and `label` columns, configurable with `--tip-column` and `--label-column`. Joins use complete exact tip strings, including quoted Newick names. Duplicate identities, missing joins and blank or unnamed display labels fail.

The render receipt must contain `tree_sha256`, `metadata_sha256` and `render_sha256`, each computed from the corresponding file bytes. A fresh timestamp cannot substitute for this receipt. Receipt agreement proves the stated byte association only; the audit does not visually inspect the render or establish how it was produced.

The audit reports `MECHANICAL_PASS`, `UNVERIFIED` or `FAIL`. The overall CLI returns zero only when every row is `MECHANICAL_PASS`, 1 for completed audits with holds or failures, and 2 for refused input or output operations. Outgroup membership checks only that explicitly declared tips form a proper subset of the tree. It does not determine biological suitability or validate rooting.

## Placement proposal boundary

Minority reference genera are not independent evidence of an outgroup. The proposed broad exemption for every non-modal genus is not included. The existing placement implementation is preserved in this patch, including its legacy single-genus heuristic. That heuristic and its root fallback remain a separate authority hold; preserving it does not validate the inferred root. A future repair needs explicit outgroup tip evidence and a supported topology contract before broadening exemptions.

## Receipt, resource and refusal details

MLSA's `run_status.json` contains status, detail and mechanical scope, not a source/seed/tool/output hash manifest. Pin every genome, seed, executable/version and produced file separately. The standalone builder defaults `--threads` to4, unlike single-core companion recipes; the thread token is parsed directly rather than validated as a positive integer. Document a reviewed explicit resource setting before any authorized run; status COMPLETE is not evidence of a measured CPU/memory cap. Missing dependencies/seeds return3, fresh-directory/no-genome refusals return4, and caught pipeline failures return6. Early refusals can precede any status file (`tools/build_mlsa.py:202–276`). Retain a partial run rather than using an older status as current evidence.

R1 UNVERIFIED warnings can accompany preflight exit0, because only FAIL rows cause exit1. Read per-row verification state, not just exit status (`tools/phylo_preflight.py:607–664,843–846`). The density ladder writes its JSON to stdout rather than a named receipt and does not include tree-source hashes; preserve the exact rung paths/hashes and captured output if using it as evidence (`tools/ladder_test.py:100–119`).

The tree artifact audit executes the configured Python gate with the tree path only. Declared outgroup tips in the artifact manifest are checked separately and are not forwarded as `--outgroup` to that script. Do not infer an outgroup-aware gate from manifest membership. The audit hashes the gate/tree/metadata/render/receipt but does not authenticate biological claims or source acquisition. It creates output exclusively, with no parent-directory creation or atomic temp-file commit; a serialization/write failure can leave a partial output that must be preserved and reviewed before retry (`tools/tree_trust_audit.py:101–140,144–170`). Record the executed gate command and result separately from the manifest checks.
