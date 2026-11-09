# BGC-machinery domain-tree contract

Status: candidate interface contract. This document does not authorize or build a tree.

A domain tree is built only with explicit approval for the compute. For the size check and approval steps, see [the phylo autopilot workflow](PHYLO_AUTOPILOT_WORKFLOW.md).

## Scope separation

A domain tree asks about relatedness among homologous biosynthetic machinery domains. It is not an organismal tree, BGC tree, product-identification method, pathway-completeness test, or physical-linkage proof. The organismal phylogeny, built from 138 single-copy genes (SCGs, see [phylogenomics](phylogenomics.md)), remains a separate channel. PKS KS pools and RiPP enzyme/precursor pools remain family- and architecture-specific; they are not combined by default.

## Extractor interface

`mamey.ks_phylogeny.extract_module_core_domains` owns strain-internal raw domain extraction. Its required result fields are frozen here and in code:

<!-- DOMAIN_TREE_REQUIRED_TOP_LEVEL: strain,domains,class_counts,ks_per_node,claim_safety -->
<!-- DOMAIN_TREE_REQUIRED_DOMAIN_FIELDS: domain_class,locus_tag,domain_id,translation,node,region -->

| Layer | Required fields | Refusal boundary |
|---|---|---|
| extraction result | `strain`, `domains`, `class_counts`, `ks_per_node`, `claim_safety` | mixed or unrecognizable strain filenames refuse |
| each domain | `domain_class`, `locus_tag`, `domain_id`, `translation`, `node`, `region` | missing/invalid translation is not alignment-ready |
| alignment admission | complete `strain / full node-or-contig / region / BGC alias`, locus tag, domain ID, subtype/family, sequence SHA-256, source locator/hash | raw extractor rows lack the BGC alias and therefore require an exact inventory/module join before alignment |

The raw GBK extractor also shortens filename node names to `NODE_<digits>` and defaults a missing region token to `region001`. These fields are parsing outputs, not verified full locus identity; recover and verify the complete node/contig and region from bound source records before admitting a tip.

## What to run now

Write a spec file, then run the builder. The spec is JSON. Five keys are required and must be non-empty strings: `domain_class`, `gbk_dir`, `outdir`, `title` and `approved_by`. `gbk_dir` is a folder holding one strain's region `.gbk` files directly inside it, not in subfolders. An empty folder, a folder with only subfolders, or one that mixes strains stops with a `ValueError` traceback (exit 1), not a `REFUSED:` line. `outdir` is created if it does not exist. Optional keys are `min_tips` (default 4), `outgroup`, and `allow_no_outgroup` (default false). A spec that names no `outgroup` must set `allow_no_outgroup` to `true`; otherwise it is refused at load. With `allow_no_outgroup` true, the tree is a within-class panel with no outgroup. Module-core classes are `PKS_KS`, `PKS_AT`, `Condensation`, `AMP-binding`, `PKS_KR` and `PKS_DH`.

```bash
python tools/build_domain_tree.py DOMAIN_TREE_SPEC.json --inventory PACKAGE_inventory.csv --skip-inference
```

`--inventory` names the strain's package BGC inventory CSV, with `BGC_ID`, `Contig`, `antiSMASH_Region` and `Source_GBK` columns. Each extracted tip is joined to it through its source region GBK: the one file in `gbk_dir` whose name gives the tip's node and region. That file's name, or the name without the leading `<strain>_`, must equal `Source_GBK`. The row's `Contig` must be the tip's `NODE_<n>` or start with `NODE_<n>_`, and its region number must match. A joined tip gets its BGC alias and full contig. Any other tip is held and left out of the FASTA. Its `<class>_provenance.tsv` row reads `IDENTITY_HELD` with one of these reasons in `identity_hold`:

- `SOURCE_GBK_NOT_UNIQUE`: no file, or more than one, in `gbk_dir` gives that node and region;
- `NO_INVENTORY_ROW`: no `Source_GBK` row names the file;
- `DUPLICATE_INVENTORY_KEY`: two rows name the file with different alias, contig or region;
- `INCOMPLETE_INVENTORY_ROW`: the row lacks `BGC_ID`, `Contig` or `antiSMASH_Region`;
- `CONTIG_MISMATCH` or `REGION_MISMATCH`: the row disagrees with the file name.

The provenance table's `identity_state` column reads `VERIFIED`, `HELD` or `UNVERIFIED_NO_INVENTORY`. A missing inventory file prints `REFUSED: INVENTORY_MISSING` and exits 2.

Without `--inventory`, staging works as before, but every tip is `UNVERIFIED_NO_INVENTORY`, and the runner says so on stderr. After a gated tree, the summary is then written as `<class>_domain_tree_summary.UNVERIFIED.tsv`. Mode B reads only `*_domain_tree_summary.tsv`, so an unverified tree is never shown in a card. Pass `--inventory` for any tree whose tips will be displayed.

With `--skip-inference` the runner validates the spec, extracts domains and stages the FASTA, then stops. It exits 0 and prints a `[stage]` line with the staged, duplicate, short, long and identity-held counts. A bad spec or a staging refusal prints `REFUSED:` and exits 2. Drop the flag, and add `--threads N` (default 4), only after the compute is approved.

## Current retry and output boundaries

The required receipts below are acceptance requirements. The current
`tools/build_domain_tree.py` runner does not produce that complete receipt set.
A staging-only run writes files: `--skip-inference` stops after extraction and
staging and returns success without running inference. It is not a read-only
preview and does not establish a completed tree.

Use a distinct output directory for each attempt and retain prior outputs with
their input bindings. The current `mamey/domain_tree.py` writes fixed output
names directly. A staging refusal can replace the provenance table while leaving
an earlier FASTA, alignment, tree and summary in that directory. Inference opens
the alignment for replacement and requests IQ-TREE redo. This is not an atomic
output-set transaction or checkpoint resume. After a refusal or interruption,
existing files alone do not identify which outputs belong to that attempt.

A full runner success means the tree passed its sanity gate and a summary was
written. With `--inventory`, the summary holds the verified tips only, with
`bgc_id`, `full_contig`, `region` and `identity_state`. Without it, the summary
holds every extracted row and goes to the `.UNVERIFIED.tsv` name. In both cases
the summary includes rows the length and duplicate filters left out of the FASTA,
and it leaves tip, clade and reference measurements blank. It is not a completed
placement table. This runner
does not write the clade table or render a figure. Preserve the input roster,
staging decisions, native logs and hashes, and verify the current tree and exact
tip crosswalk before using downstream outputs.

The separate `tools/domain_phylo_rescue.py` exporter replaces its requested TSV
path directly. An empty result writes a header-only file; its JSON summary is
printed to the console rather than saved as a bound completion receipt. Retain
that invocation's input hashes, output hash, console summary and failure state.
A retained older TSV after an input or runtime failure is not a current result;
an empty successful export and a failed attempt must remain distinct.

## Required workflow receipts

These are acceptance requirements. The runner does not write all of them. Keep the missing ones yourself.

1. Extraction receipt: source GBK/module hashes, strain-internal check, retained/excluded counts, exact domain roster, and sequence hashes.
2. Pool-design receipt: one declared KS subtype or one homologous RiPP family, inclusion/exclusion reasons, duplicate-copy policy, reference provenance, and outgroup/rooting plan.
3. Alignment receipt: tool/version/command, input roster hash, alignment hash, retained columns, and invalid/short-sequence holds.
4. Inference receipt: tool/version/model/seed/thread count, alignment hash, tree hash, support method, and completion marker.
5. Figure/admission receipt: exact tip crosswalk, tree-sanity status, outgroup, omitted tips, caption/methods block, and output hashes.

## Guard composition

- Iterative-module guard: KS count is not module count or chain length; low KS count is not fragmentation evidence.
- Housekeeping convergence guard: FAS/FabB/FabF/FabH/hglE-like domains cannot anchor a rescue.
- Two-proof guard: domain co-clustering without RG-GMCI complementarity is `DOMAIN_ONLY_HINT`, never a rescue. RG-GMCI is defined in [the glossary](GLOSSARY.md).
- Tree-source separation: rendering consumes a completed, bound tree and never builds, re-roots, or relabels it.
- Exact-locus gate: any BGC-specific tip must display `strain / full node-or-contig / region / BGC alias`. `build_domain_tree.py --inventory` enforces it. Each tip is joined to the package inventory through its source region GBK, and a tip that cannot be joined is held with a reason (see [What to run now](#what-to-run-now)). Without `--inventory`, every tip is `UNVERIFIED_NO_INVENTORY`, and the summary is kept off the Mode B display path. `stage_domains` also stops with `STAGE_INCOMPLETE_IDENTITY` when `strain`, `node`, `region` or `locus_tag` is blank or a header holds a `?` placeholder. The FASTA header keeps the short `strain__node__region__locus_tag` form, so take the full contig and alias from the provenance table, not from the header.
- Duplicate gate: exact copies remain enumerated; no silent one-tip-per-strain collapse.


## Current preparation identity boundary

`tools/prepare_biosynthetic_tree_inputs.py` checks a strain-local BGC alias
against the supplied inventory and records source file/row, locus, sequence digest
and its generated tip token. Its inventory reader retains products by `bgc_id`;
the emitted sequence ledger and FASTA tip do **not** carry the full contig/node and
region components of `strain / full node-or-contig / region / BGC alias`.

A `MAPPED` row, alias membership or `READY_FOR_ALIGNMENT` count therefore does not
establish the complete locus identity. Before using an individual locus as an
alignment/figure tip, make an exact join to the bound current inventory/module
record and retain all four identity components plus locus/domain and source hashes.
Do not infer those missing fields from tip order or the alias. Unresolved or
conflicting joins remain identity holds. The preparer currently needs an owning
code change to emit and verify that complete crosswalk automatically.

## Claim ceiling

Domain topology can support domain-family relatedness and candidate evolutionary context. It does not establish product identity, pathway completeness, production, activity, novelty, physical linkage, species identity, ancestry direction, or horizontal transfer. Judgment deferred.
