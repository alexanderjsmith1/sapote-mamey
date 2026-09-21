# Sapote-Mamey

Sapote-Mamey is a python-based analysis pipeline for actinomycete genomes created with assistance of LLM (artificial intelligence). The program was developed with actinomycete genomes across most common genera (Streptomyces, Micromonospora, Actinomadura, etc). 

Sapote-Mamey is under continuous development and can help users run research tools and interpret their outputs. Its development has involved providing antiSMASH results (downloaded ZIP files) to LLMs and using those results to refine the analysis and reporting workflows.

The analysis pipeline primarily works to interpret antiSMASH results into a user-friendly narrative and allows integration of other bioinformatics tools and other data streams provided by the user. The LLM environment gives the user flexibility to explore the antiSMASH output and other data however they choose. This dynamic interaction allows the potential to take the analysis in any direction. 

Common applications include helping the user understand which biosynthetic gene clusters (BGCs) a genome carries, what their genes resemble, and which regions deserve a closer look. It is built around actinomycete genomes and a user's genome can be compared with reference genomes. The options to do this include downloading related reference genomes and running antiSMASH on them, and a user can ask the LLM for assistance. The user or LLM can find related genomes based on phylogeny (16S blast results), related genomes obtained by clusterblast and knownclusterblast matches, or searching the genus name in NCBI Nucleotide database and ranking by size to find the appropriately sized assemblies (approximately 5 to 11 mb depending on the genus). A score is a reason to inspect a region, not a measurement of antimicrobial activity.

Sapote Mamey has two main components. Mamey is the executable BGC-analysis module: extraction, evidence checks, tables
and analysis tools. Sapote is the interpretation and writing workflow: it takes those results into gene-by-gene
Mode B cards and reports. A generated table or template starts that review; it does not write
the interpretation for you.

From one antiSMASH result ZIP you can examine the genes and their reference matches, deepen
uncertain calls with BLASTp, and compare strains. Optional companion workflows add BiG-SCAPE
gene-cluster families and phylogenetic trees to the same evidence review and figure workflow.
You do not need every optional workflow to get a useful result. Mode B cards have optional sections designed to integrate these additional data streams.

For a one-page map of the program's parts, inputs, and outputs, see
[What Sapote-Mamey offers](docs/PRODUCT_MAP.md).

## Platform compatibility and equal AI contribution credit

Sapote-Mamey is designed to work across Anthropic and OpenAI platforms. Browser access through
Claude.ai and ChatGPT works well for inspecting inputs, interpreting existing evidence, and drafting
bounded reports, subject to each service's upload, runtime, network, and session limits. The desktop
applications generally provide a stronger file-centered experience. For the fullest experience, the
project recommends Claude Code or Codex in a local project environment; those agent interfaces offer
the best compatibility with bundle tools, local data, databases, long-running commands, rendered
artifacts, and validation receipts.

**Equal AI contribution credit (50/50).** The Sapote-Mamey project credits
[Anthropic](https://www.anthropic.com/) and [OpenAI](https://openai.com/) as equal contributors—50%
each—to the AI-assisted development, testing, refinement, and documentation of this bundle.
Anthropic's contribution was made through Claude and Claude Code; OpenAI's contribution was made
through ChatGPT and Codex. This credit records the project's development history. It does not imply
sponsorship, endorsement, approval, ownership, or responsibility for scientific conclusions by
either company.

## Start in ChatGPT or Claude.ai

Many Sapote-Mamey review and reporting workflows can begin in a browser without a local
installation. Paste the repository link
[github.com/alexanderjsmith1/sapote-mamey](https://github.com/alexanderjsmith1/sapote-mamey)
into a new ChatGPT or Claude.ai conversation, state the analysis you want, and attach one or more
antiSMASH result ZIPs. For phylogeny, attach the sequence input you actually have, such as 16S
FASTA, an assembled genome FASTA or GenBank file, and the matching sample metadata. Raw sequencing
reads first need an appropriate assembly and quality-control route.

Ask the assistant to read `AGENTS.md`, this `README.md`, and
`skills/sapote-mamey/SKILL.md` before it begins. Tell it whether you authorize inspection only or
execution of the attached data. For every individual BGC, require the complete identity in the
order **strain / full node-or-contig / region / BGC alias**, and require source-backed uncertainty
and claim ceilings. A useful opening prompt is:

> Read the Sapote-Mamey repository instructions and inspect my attached files. I authorize analysis
> of these inputs. Preserve complete BGC identities and provenance, report evidence gaps, and do not
> treat similarity as product identity or production. Use the available execution tools for supported
> workflows; if a required runtime or database is unavailable, identify the exact local step instead
> of inventing a result.

Browser interfaces differ in file-size limits, runtimes, network access, and session persistence.
They can inspect inputs, interpret existing evidence, and prepare reports when those capabilities are
available. The deterministic Mamey engine, external phylogeny programs, large databases, and long
runs may still require a local Claude Code or Codex session, or a terminal environment. Download
the generated reports and receipts; a chat response alone is not a validated or sealed Mamey package.

**Start with the file you have:**

- An **antiSMASH result ZIP** → [Your first Sapote–Mamey analysis](docs/MASTER_WALKTHROUGH.md). It has a route for working through an assistant and a terminal route.
- A **Complete_Package ZIP** from an earlier run → [Read your results](docs/READING_YOUR_RESULTS.md).
- A **code ZIP** → [Install](#install) below.

**Status.** The program and documentation are under active development. This build has known
gaps in metadata handling, evidence-completeness reporting and generated-PDF layout. A run that
finishes and validates does not close those gaps or certify a biological conclusion.

The program was occasionally tested with other bacterial orders, and several basidiomycetes and ascomycetous fungi. No extensive testing or development has occurred other than to establish some degree of functionality with these other microbial groups. The bacterial-specific tools will not work as-is, but many bioinformatics tools are expected to work and the primary Mamey engine will intake antiSMASH zips from these other organisms and produce a validated evidence package.  

## What you can do

| Your question | Workflow | What you get |
|---|---|---|
| What biosynthetic regions and genes are present? | Inspect and run an antiSMASH ZIP | Region inventory, assembly/boundary context, source scans, comparator evidence, triage board, workbook, and validated package |
| What do these proteins most closely resemble? | Export translated proteins for manual BLASTp, run an online search, or import saved results | Per-gene homology evidence to compare with antiSMASH annotations, domain architecture, and reference-cluster matches |
| Is a pathway split across contigs? | Review the extraction's RG-GMCI fragment-linkage evidence | Candidate links supported by reference geometry, complementary gene coverage, and contig-boundary evidence, with contradictory or insufficient evidence retained |
| Which clusters belong to related families? | Run the integrated BiG-SCAPE companion on region GBKs | Run-specific gene-cluster families in SQLite and, when available, matrix and gene-comparison widgets |
| How do biosynthetic features vary across a tree? | Route 16S sequences or build a genome tree, then supply matched annotation tracks | Trees with metadata or strain-level heatmap overlays, plus the data and methods needed to reproduce them |
| What does the combined evidence suggest? | Author and verify a Mode B card | A traceable gene-by-gene interpretation incorporating available protein, domain, cluster-family, and comparative evidence |

## Beyond extraction

**Protein evidence.** Mamey extracts translated CDS sequences from antiSMASH region GenBank
files. `bgc-blastp-panel` exports representative proteins as FASTA batches for a manual BLASTp
search. `blastp-online` submits a selected region's proteins to NCBI; `blastp-round` plans broader
coverage before submission; `auto-blastp` is a resumable scheduler. Import saved hit tables with
`ingest-blastp`. Before you revise a functional call, compare hit identity, alignment coverage,
protein length, domains and neighbouring genes. Keep each search database and its provenance
with the result. See the [protein-search walkthrough](docs/GUIDE/02_Quick_Guide.md#protein-search-and-result-import).

**Fragmented pathways.** Poor assemblies need more than an edge flag. The built-in RG-GMCI pass
compares fragments against shared ClusterBlast/KnownClusterBlast references, checks where their
hits fall, and tests whether they cover complementary parts of the reference pathway. Boundary and
terminus evidence add context; paralogous overlap and promiscuous links can weaken or reject a
proposed rescue. "Rescue" here means recovering an interpretable candidate pathway relationship.
It does not join contigs or reconstruct missing sequence. See
[fragment review](docs/GUIDE/02_Quick_Guide.md#fragmented-pathway-review).

**Cluster families.** `bigscape` stages region GBKs, runs an externally installed BiG-SCAPE 2.x,
and can chain the results into cohort widgets. The command is integrated; you supply the
BiG-SCAPE binary and the pressed Pfam database separately. Family membership belongs to that run
and cutoff; read it alongside assembly fragmentation and protein evidence. See
[the BiG-SCAPE walkthrough](docs/GUIDE/02_Quick_Guide.md#big-scape-family-analysis).

**Phylogeny and overlays.** `phylo-autopilot` inventories uploads and handles 16S routing and
placement. When an antiSMASH ZIP contains a non-region assembly sequence, `phylo-mlsa` can plan or stage an
optional five-locus MLSA screen from it. Review assembly completeness separately.
Local reference genomes and external companion tools are needed to run the screen. `phylo-run` launches an approved GToTree/IQ-TREE genome workflow,
with optional ANI inputs. The tree renderers join tree tips to metadata and to strain-level ANI, BGC, domain,
Mode B or assembly tracks. Each track needs an explicit tip-to-strain mapping and its own data;
nothing is inferred from the tree. See [trees and heatmaps](docs/GUIDE/02_Quick_Guide.md#trees-and-heatmap-overlays).

**Bioassay figures.** The bioassay Figure Factory takes a hash-bound long-form observation table
that keeps plate format, well, material lineage, target resolution, time point, replicate,
control and inclusion state. It emits an R/ggplot2 summary without averaging unlike materials or
treating a missing positive control as valid. Tree overlays need a separate, explicit selection
of material, target, time point and experiments. See the
[bioassay figure contract](docs/BIOASSAY_FIGURE_FACTORY.md).

## Install

> **Build status.** This CODE archive is a validated software artifact. The footer of this file carries the exact bundle and engine versions, sourced from [`pyproject.toml`](pyproject.toml). [`RELEASE_MANIFEST.md`](RELEASE_MANIFEST.md) is the authoritative status source.
>
> GitHub source users: start with `docs/PUBLIC_RELEASE_GUIDE.md` for what ships, the Pfam HMM you provision yourself, the tool's runtime network behavior, and air-gapped operation. Full step-by-step setup is in `docs/INSTALL.md`.

### Python and dependencies

You need **Python 3.12 or newer**. Run these from the extracted directory that contains
`pyproject.toml` and `mamey_run.py`:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python mamey_run.py start
python mamey_run.py doctor
```

These are macOS/Linux commands. On Windows, activate with `.venv\Scripts\Activate.ps1` in
PowerShell. The core dependencies are declared in [pyproject.toml](pyproject.toml): `openpyxl`,
`ijson`, `reportlab`, and `PyYAML`. Always use the local launcher (`python mamey_run.py`) so you
do not run some other installed version by mistake.

Optional features have named extras:

```bash
python -m pip install -e '.[figures,documents,bio]'
```

[INSTALL](docs/INSTALL.md) has the full setup, offline installation and platform-compatible
add-ons. [PREREQUISITES](docs/PREREQUISITES.md) covers companion tools and
[EXTERNAL ASSETS](docs/EXTERNAL_ASSETS_GUIDE.md) covers data provision. antiSMASH runs
separately; you give its result ZIP to Mamey. The core Python package does not install external
databases, system tools, or the curated Pfam HMM.

## Tool downloads and licenses

The [Companion Tool Guide](docs/COMPANION_TOOL_GUIDE.md) describes each tool, how to use it on
its own, and how it connects to Sapote–Mamey. The table below is the download and license
reference. It is not a requirement to install everything: install Python and the core package
first, then add only the companion tools your analysis needs.

The links go to the upstream project or installation page, where downloads and full license
texts are maintained. The listed license applies to the named upstream software; dependencies
and reference databases have their own terms. Check the license shipped with the version you
install. In practice: MIT, BSD, Apache, PSF and similar permissive licenses generally require you
to keep their copyright and license notices when redistributing the software. GPL and AGPL tools
carry source and license obligations when redistributed or modified; LGPL has its own linking and
redistribution conditions. The tools below are installed separately and are not copied into the
core Sapote-Mamey package. "Public domain" applies to the named software, not automatically to
records in a database it searches. Follow the linked upstream text for the exact version and
distribution you use.

| Tool / official download or installation page | Needed for | Upstream license |
|---|---|---|
| [Python](https://www.python.org/downloads/) | Required runtime, Python 3.12 or newer | [PSF License and bundled notices](https://docs.python.org/3/license.html) |
| [antiSMASH](https://github.com/antismash/antismash#installation) | Generate the input results; a supplied result ZIP avoids a local antiSMASH installation | AGPL-3.0-or-later |
| [NCBI BLAST+](https://www.ncbi.nlm.nih.gov/books/NBK279690/) | Local protein/nucleotide searches and 16S routing; not needed merely to export FASTA or use the web runner | [NCBI public-domain software notice](https://blast.ncbi.nlm.nih.gov/doc/blast-help/developerinfo.html) |
| [BiG-SCAPE 2](https://github.com/medema-group/BiG-SCAPE) | Optional gene-cluster family analysis | AGPL-3.0 |
| [HMMER](https://github.com/EddyRivasLab/hmmer) | Profile searches and pressed Pfam preparation for relevant companion workflows | [BSD-3-Clause](https://github.com/EddyRivasLab/hmmer/blob/master/LICENSE) |
| [clinker](https://github.com/gamcil/clinker#installation) | Optional gene-cluster comparison views | MIT |
| [DIAMOND](https://github.com/bbuchfink/diamond) | Optional accelerated local protein comparisons | GPL-3.0 |
| [GToTree](https://github.com/AstrobioMike/GToTree) | Optional genome-marker phylogeny workflow | MIT; dependencies retain their own licenses |
| [Prodigal](https://github.com/hyattpd/Prodigal) | Gene prediction where required by the selected genome workflow | GPL-3.0 |
| [MUSCLE](https://github.com/rcedgar/muscle) | Alignment in workflows configured for MUSCLE | [GPL-3.0 for the current upstream distribution](https://github.com/rcedgar/muscle/blob/main/LICENSE); verify the required CLI version |
| [MAFFT](https://mafft.cbrc.jp/alignment/software/index.html) | Alignment for the placement workflow | BSD for the core distribution; bundled extensions have separate terms |
| [trimAl](https://github.com/inab/trimal) | Alignment trimming in configured phylogenomic workflows | GPL-3.0 |
| [IQ-TREE 2](https://github.com/iqtree/iqtree2) | Maximum-likelihood genome-marker trees | GPL-2.0 |
| [FastTree](https://github.com/morgannprice/fasttree) | Tree inference when called by the selected companion | GPL-3.0 in the current upstream repository; check older distributions separately |
| [RAxML-NG](https://github.com/amkozlov/raxml-ng) | Reference backbone inference for placement | AGPL-3.0 |
| [EPA-ng](https://github.com/pierrebarbera/epa-ng) | Placement of query sequences on a reference tree | AGPL-3.0 |
| [gappa](https://github.com/lczech/gappa) | Phylogenetic placement processing | GPL-3.0 |
| [FastANI](https://github.com/ParBLiSS/FastANI) | Optional genome ANI comparisons | Apache-2.0 |
| [R](https://www.r-project.org/) | Optional R plotting scripts | [GPL-2 or GPL-3](https://www.r-project.org/Licenses/) |
| [ggplot2](https://ggplot2.tidyverse.org/) | R plotting | MIT |
| [ggtree](https://bioconductor.org/packages/release/bioc/html/ggtree.html) | R tree visualization | Artistic-2.0 |
| [patchwork](https://patchwork.data-imaginist.com/) | R composite layouts | MIT |
| [svglite](https://svglite.r-lib.org/) | SVG output for R renderers using ggplot2's SVG device | GPL-2.0-or-later |

Core Python dependencies install with `python -m pip install -e .`:
[openpyxl](https://pypi.org/project/openpyxl/) (MIT),
[ijson](https://pypi.org/project/ijson/) (BSD-3-Clause for current upstream; the vendored copy retains its own notice),
[ReportLab](https://pypi.org/project/reportlab/) (BSD), and
[PyYAML](https://pypi.org/project/PyYAML/) (MIT).
The optional Python figures and documents packages install through the extras above; their
license inventory is in [Third-Party Licenses](docs/THIRD_PARTY_LICENSES.md). This table covers
direct workflow tools, not every transitive library their package managers install.

### External reference datasets

The repository ships small, versioned lookup tables and positive-control extracts used by the
engine. It does not ship the full Pfam, MIBiG, UniProt/Swiss-Prot, nr, ClusteredNR, RefSeq, or
16S collections. Record the exact dataset release, download date and file hashes you used. A data
license governs reuse; a scientific citation documents which resource informed the work. Do both
when the resource asks for attribution.

| Resource | Used for | What the terms mean for this workflow |
|---|---|---|
| [Pfam](https://pfam-docs.readthedocs.io/en/latest/pfam.html) | Protein-domain HMMs; obtain the release and press it with HMMER | [CC0 1.0](https://www.ebi.ac.uk/interpro/about/license/): the downloadable Pfam data can be reused without a legal attribution requirement. Cite Pfam/InterPro as scientific practice and retain the release identity. |
| [MIBiG](https://mibig.secondarymetabolites.org/) | Experimentally supported reference biosynthetic clusters and their metadata | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/): attribution is required. Cite MIBiG, link the license when redistributing adapted content, and identify changes. |
| [UniProt / Swiss-Prot](https://www.uniprot.org/help/downloads) | Reviewed protein-reference evidence | [CC BY 4.0](https://www.uniprot.org/help/license/) applies to copyrightable database content: attribution is required. UniProt also notes that patents or other third-party rights may apply to some records. |
| [NCBI BLAST databases](https://www.ncbi.nlm.nih.gov/books/NBK62345/) | nr, ClusteredNR, RefSeq protein, and 16S reference searches | [BLAST software is public domain](https://blast.ncbi.nlm.nih.gov/doc/blast-help/developerinfo.html). Treat database content separately: retain the exact database name/date and record-level source identifiers, cite the contributing resources, and review the notices supplied with the selected database. |

Keep database versions and hashes with the analysis. Installing the Python package does not
download these databases or install the external binaries. Run
`python mamey_run.py doctor --companions` to check the analysis machine, and use the
[installation guide](docs/INSTALL.md) for the bundle setup.

## Quickstart

Replace the example paths and metadata with values you have verified from your input. Run from
the bundle root. The package path below assumes `--strain EXAMPLE` and `--outdir runs/`.

```bash
python mamey_run.py inspect path/to/antismash_result.zip
python mamey_run.py run --strain EXAMPLE \
  --input-zip path/to/antismash_result.zip \
  --taxonomy 'Genus sp.' --source 'recorded isolation source' \
  --mode gold --outdir runs/
python mamey_run.py validate runs/EXAMPLE/package
python mamey_run.py explain runs/EXAMPLE/package
```

Before you interpret anything, read the run status, the issue log and the output paths.
Validation checks package structure and the encoded evidence gates. It does not establish
biological identity, production, activity, or owner acceptance.

If your session has a time limit, add `--capped-session` to `run`. It forces `--brief none` and
`--json-evidence off`, requires the workbook, and turns off automatic locus maps unless you
enable them. If you want bounded JSON evidence instead, leave out `--capped-session`, use
`--json-evidence bounded`, and give it enough runtime. The old `--chatgpt-safe` spelling still
works only as a deprecated alias for `--capped-session`.

Once the package validates, render the deferred figures (needs the figure dependencies):

```bash
python mamey_run.py render-all-figures runs/EXAMPLE/package
```

The [Quick Guide](docs/GUIDE/02_Quick_Guide.md) covers package review, cohort work and the move
into Mode B. `python mamey_run.py --help` lists the commands. A Mode B template or lead table is
material for Sapote judgment; it is not a finished authored card.

## Repository layout

- `mamey/` — the deterministic engine (extraction, gating, figures; vendored `ijson` under `_vendor/`).
- `tools/` — release, audit, and authoring utilities.
- `bundle_support/` — add-on installer, registry inventories, and reusable templates.
- `debugging_modules/` — audit and debugging protocols.
- `docs/` — the operating contracts (Mode B, deliverables, claim-safety) and reference material; start at `docs/BUNDLE_CAPABILITIES.md`.
- `skills/sapote-mamey/` — the detailed operating discipline referenced by the shared assistant contract.
- `tests/` — the regression suite (`python -m pytest`).

## Using with an AI assistant

[AGENTS.md](AGENTS.md) is the portable operating contract for coding assistants. Have the
assistant run `python mamey_run.py start` from the extracted bundle to confirm the current
version and workflow. `CLAUDE.md` is a byte-identical copy of AGENTS.md for assistants that look
for that filename; it defines no separate startup path, and other assistants are not assumed to
find it. Point ChatGPT, Gemini, or any other assistant at `AGENTS.md`, or supply it through that
product's instruction mechanism. `skills/sapote-mamey/SKILL.md` holds the detailed Mode B and
audit disciplines.

## Citation-Compact Provenance and Citation Status

Sapote-Mamey uses citation-compact outputs to separate runtime evidence structure from literature verification.

- **antiSMASH 8.0** is recorded as method/database provenance for BGC detection and product/region calls: DOI `10.1093/nar/gkaf334`.
- **MIBiG 4.0** is recorded as reference-database provenance for curated BGC entries and KnownClusterBlast dereplication context: DOI `10.1093/nar/gkae1115`.
- **`PASS_STRUCTURE`** means the package structure, citation ledger, work-order files, compact reports, manifest tracking, and checksum tracking passed validation. It does **not** mean every literature claim has been manually verified.
- **`operator_supplied`** means the citation/provenance row came from runtime evidence or comparator fields already present in the package.
- **`citation_needed`** means literature support is missing and should be filled by a separate literature-search pass.
- **`Literature_Search_WorkOrder.md/json`** is a safe handoff for another literature session — a search instruction, not a verified fact.

Current compact lead tables use `interpretation_scope` for reader-facing scope.

## Data availability

Before you share data, check the exact tier's inventory, the release manifest and the disclosure
decisions. A CODE candidate's filename, a strain prefix, or a local test pass does not establish
public-release authority. Keep private or unpublished material out of public artifacts and
preserve source attribution.

## Scientific integrity

The interpretive layer is bound by claim-safety rules enforced in code (`tools/claim_safety_linter.py`, `mamey/claim_safety_gate.py`, and the Mode B structure gate): biosynthetic *capacity* is never reported as confirmed *production*; KCB/BLASTp similarity is never rendered as identity; bioactivity is extract-level, never per-BGC; and no observation is stated that isn't tied to a real result.

## Citation

If you use Sapote-Mamey, please cite it (see `CITATION.cff`) and antiSMASH 8.0 (Blin et al.). BGC detection depends on antiSMASH; interpretation depends on this pipeline.

## License

Code is released under the MIT License (`LICENSE`), © 2026 Alexander J. Smith. Documentation is covered by `LICENSE-DOCS.txt`. Bundled third-party code and its licenses are listed in `docs/THIRD_PARTY_LICENSES.md`.

## Practical help

- [Find the right document](docs/DOCUMENTATION_MAP.md)
- [Troubleshooting](docs/COMMON_MISTAKES.md)
- [Files, storage and handoff](docs/FILES_STORAGE_AND_HANDOFF.md)

---
*Current bundle: sapote-mamey-v9.7.437 / engine 1.9.167 · build 20260921v97437a · release profile: CODE (see RELEASE_MANIFEST.md)*
