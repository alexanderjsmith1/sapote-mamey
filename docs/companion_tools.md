# Choose optional companion tools

Use another caller, compare genomes, or build a tree after extraction. You need
the inputs and reference data for that task. Core extraction uses the
[core install](INSTALL.md); missing companions affect their own workflows.

## Check what is installed

Run this in the terminal environment you intend to use:

```bash
python mamey_run.py doctor --companions
```

The table reports executable/version probes, expected-version comparisons and
REVIEW_REQUIRED flags. A detected tool still needs the selected workflow's
inputs and databases. Record its binary path and environment so later runs use
the same installation.

The registry uses the invoking Python for import probes. Native probes try their
declared executable names; a selected failing executable is not replaced silently.
GToTree tries `GToTree`, then `gtotree`. The registry IQ-TREE probe names only
`iqtree3`, while ordinary doctor also accepts `iqtree2` or `iqtree`; this can
explain different reports. Web/manual entries are NOT_PROBED.

Use separate external-tool environments. The companion protocol,
`docs/LLM_COMPANION_TOOL_PROTOCOL.md` ([open it](LLM_COMPANION_TOOL_PROTOCOL.md)),
and [run contracts](COMPANION_RUN_CONTRACTS.md) describe installation, download
and resource choices. Check those before starting optional work.

## BiG-SCAPE

Compare antiSMASH region GBKs as run-specific gene-cluster families. You need a
compatible BiG-SCAPE 2.x environment, full Pfam-A with its pressed indexes and
HMMER; tree outputs also need FastTree. Add a selected, versioned MIBiG panel
only when the task calls for reference anchoring. Follow the
[BiG-SCAPE runbook](BIGSCAPE_GCF_WORKFLOW.md) for installation and commands.
Keep cohort-only family assignments separate from reference identity claims.

## GECCO

The optional `gecco-crosscheck` command runs a second caller on the original
archive. It needs GECCO 0.11.x and writes outside the package. Follow
[companion class evidence](COMPANION_CLASS_EVIDENCE.md#gecco) for the command,
source binding and outputs. Run it after extraction.

Keep sequence identifiers, model/tool version, input/output hashes and the run
receipt. [Strain slides](STRAIN_SLIDES.md) can read the supplied gene, feature and
cluster tables through `gecco_dir`. [Current50 v2](MODEB_CURRENT50_V2_CONTRACT.md)
uses §22 for GECCO and §50 for the gene table; check coordinates before joining them.

## GToTree and IQ-TREE

These use whole-genome assemblies, not isolated BGC regions. The workflow gives
priority to released GToTree **1.8.19**; native v2 work remains deferred.
Interface checks can admit 2.0.x, but that does not select its runtime or model.
Version 1.8.16 is refused. Check the chosen installation and model after an upgrade.
The Bioconda package page is `https://anaconda.org/bioconda/gtotree`.

The workflow begins with a five-protein-locus MLSA screen and separate 16S
context, then a selected 138-SCG Actinobacteria tree. Analysis panels normally
contain 40 genomes, no more than 60 without another preflight, and at most three
references per focal genome. Publication trees use at most four references.
Use [GToTree workflow](GTOTREE_WORKFLOW.md) and [phylogenomics](phylogenomics.md)
for the actual setup and run recipes.

Record the selected genomes, references, model, output root, disk/runtime estimate
and thread budget first. For serial GToTree 1.8.19, the control fragment is
`GToTree -j 1 -n 1 -M 1 -N`, with final IQ-TREE `-T 1`; use the workflow for
its input arguments. Shared policy omits `-n` for 2.0.x. Native v2 requests two
HMM workers per genome job: its phase bound is
`max(2 * jobs, jobs * muscle_threads)`, so even one job needs at least two CPUs.
The legacy `phylo-run` wrapper does not expose the native-v2 runtime/budget
options. Separately selected v2 work uses `tools/run_planned_tree.py` with its
runtime bindings and `--gtotree-cpu-budget`. See the
[run contracts](COMPANION_RUN_CONTRACTS.md) before any separately selected v2 work.
Keep reference accessions, hashes and deposited type-material status with downloads.

## Other tools

Clinker/pyGenomeViz draw synteny; cblaster searches for co-located homologs;
skani/fastANI compare assemblies. GTDB-Tk needs a large reference database, so
check space and the selected task before acquiring it. antiSMASH is the upstream
input generator and runs separately from Mamey.

The [CORASON adapter](CORASON_WORKFLOW.md) has a plan/run/read route, but its
external runtime remains unassessed and manual in the registry. It preserves
pre-filter neighborhoods and distinguishes multilocus inference from query-only
or BLAST-order fallbacks. Derived outputs remain PRIVATE. Follow that workflow
before running it; the antiSMASH-only figure route is separate.

Executable detection is defined in `mamey/data/companion_tools.json`. Changes to
its executable names or installation hints need the matching registry tests.

<a id="detection"></a>
<a id="other-optional-companions"></a>
<a id="corason-optional-runtime-not-admitted"></a>
