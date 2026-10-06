# Companion tools — optional external analysis, detected not bundled

Sapote-Mamey's deterministic core remains offline-capable. BiG-SCAPE, GToTree, IQ-TREE, ANI tools,
reference downloaders, and their databases are optional downstream companions. A missing companion
must not fail a Mamey extraction or alter a sealed package.

**LLM operators:** read `docs/LLM_COMPANION_TOOL_PROTOCOL.md` before preparing or running these
tools. Installation, upgrades, downloads, and high-resource execution require the approvals named
there. Never guess that a folder named after a tool contains a usable installation: inventory the
binary, environment, version, database assets, and checksums.

## Detection

```bash
python mamey_run.py doctor --companions
bigscape --version
GToTree -v
iqtree3 --version || iqtree --version
fastANI --version
```

Keep every external environment separate from the Mamey core. Export the resolved environment and
record exact binary paths because a later Claude/Codex session may have a different `PATH`.

## BiG-SCAPE

- Purpose: run-specific family similarity among antiSMASH region GBKs.
- Input: antiSMASH `*.region*.gbk` members, staged with strain/BGC/locator provenance.
- Required assets: compatible BiG-SCAPE 2.x environment; `Pfam-A.hmm` and its pressed companions;
  HMMER; FastTree if tree outputs are requested.
- Optional assets: a user-approved, versioned MIBiG/reference panel.
- Active runbook: `docs/BIGSCAPE_GCF_WORKFLOW.md`.

Installation example (networked, user-approved):

```bash
conda create -n sapote-bigscape -c conda-forge -c bioconda bigscape
conda activate sapote-bigscape
bigscape --version
```

Do not put `--mibig`, auto-download references, or direct Mode B/triage mutation in a quick-start
command. A cohort-only run is scientifically useful but cannot support KNOWN/NOVEL language.

## GECCO

GECCO is an optional external caller, recorded in `mamey/data/companion_tools.json`
and detected by `python mamey_run.py doctor --companions` via `gecco --version`.
The registry is a capability inventory, not proof of a usable installation or a completed run.
There is no GECCO execution subcommand in the Mamey extraction route described here.

Preserve the actual input assembly, full sequence identifiers, tool/model version, input/output
hashes and run receipt. Keep outputs in a separate approved analysis directory.
`tools/strain_slides.py` consumes explicitly supplied `*.genes.tsv`, `*.features.tsv` and
`*.clusters.tsv` using `gecco_dir` in its sources file; see [strain slides](STRAIN_SLIDES.md).
The [current50 v2 contract](MODEB_CURRENT50_V2_CONTRACT.md) supplies §22 for GECCO
evidence and §50 for the complete gene table. Check sequence and coordinate bindings
before comparing predictions; agreement or disagreement is evidence to reconcile, not
a product, activity or novelty conclusion. Missing GECCO evidence remains explicit.

## GToTree and IQ-TREE

- Purpose: organismal phylogenomics from whole-genome assemblies; not BGC region phylogeny.
- Input: whole-genome FASTA recovered from antiSMASH ZIPs plus a recorded reference panel.
- Design: six-locus screen, then selected 138-SCG Actinobacteria tree; at most three references per
  focal genome; normally 40 and no more than 60 total genomes without a new preflight.
- Resource default: `GToTree -j 1 -n 1 -M 1 -N`; final IQ-TREE `-T 1`; maximum four concurrent
  one-core trees.
- Approval: show size, expected usage, references, network needs, and output root before GToTree.
- Active runbook: `docs/phylogenomics.md`.

The Bioconda package page is `https://anaconda.org/bioconda/gtotree`. Current channel state can
change; do not hard-code the channel's newest version. The production version is GToTree
1.8.19, with an Actinobacteria HMM of 138 profiles; 2.0.x is admitted and 1.8.16 is refused (`GTOTREE_WORKFLOW.md`). Re-check after installation or upgrade.

```bash
conda create -n sapote-phylo -c conda-forge -c bioconda gtotree iqtree fastani ncbi-datasets-cli
conda activate sapote-phylo
GToTree -v
GToTree -h
```

Reference downloads via NCBI Datasets need network approval. Preserve accessions, assembly hashes,
download receipts, and type-strain status rather than relying on filenames.

## Other optional companions

- antiSMASH: required upstream input generator; web/conda/Docker execution is outside Mamey.
- clinker/pyGenomeViz: BGC synteny figures.
- cblaster: targeted co-located homologue searches.
- GECCO: independent BGC caller.
- skani/fastANI: assembly similarity and de-replication.
- GTDB-Tk: heavy reference-database taxonomy; always preflight disk/network first.

Machine-readable detection remains in `mamey/data/companion_tools.json`. Update that registry and
its test whenever executable names or verified install hints change. Documentation is not proof that
an optional binary or database is present.
