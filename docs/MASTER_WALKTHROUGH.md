# From installation to analysis deliverables

Start with an extracted Sapote-Mamey bundle and an antiSMASH result ZIP. This guide connects installation, extraction, protein evidence, comparative analysis and figures. It describes the workflow; it does not claim that a particular machine has all companion tools installed or that an example dataset has passed validation.

## 1. Choose the program and working directories

Keep the downloaded bundle ZIP and its published checksum. Extract it into a directory you choose, then locate `pyproject.toml` and `mamey_run.py`. The archive may contain files directly; do not assume extraction creates a version-named subdirectory.

Use a separate directory for environments, input data and analysis outputs. No particular laptop folder structure is required. In a macOS/Linux shell, substitute your absolute paths:

```bash
BUNDLE='/absolute/path/to/extracted-bundle'
WORK='/absolute/path/to/analysis-project'
mkdir -p "$WORK"
cd "$BUNDLE"
```

Do not put analysis outputs inside the program directory. Keep original antiSMASH ZIPs and genome assemblies unchanged.

## 2. Check Python and install the selected features

Python 3.12 or newer is required. Choose a working interpreter with TLS support. Check it before creating the environment:

```bash
python3 --version
python3 -c 'import ssl, platform; print(platform.machine()); print(ssl.OPENSSL_VERSION)'
python3 -m venv "$WORK/venv"
PY="$WORK/venv/bin/python"
"$PY" -m pip install -e '.[figures,documents,bio]'
"$PY" -m pip check
"$PY" mamey_run.py start
"$PY" mamey_run.py doctor
```

If the TLS import fails, repair or replace that Python installation before using online services. An offline wheelhouse can help install packages, but does not restore missing TLS support to an interpreter.

The extras install Python dependencies for figures, documents and Biopython support. They do not install antiSMASH, BiG-SCAPE, phylogenetic executables or their databases. See [installation](INSTALL.md), [prerequisites](PREREQUISITES.md), and the [tool download/license table](../README.md#tool-downloads-and-licenses). Windows activation instructions are in the installation guide.

For an offline machine, obtain a complete wheelhouse for its operating system, CPU architecture and Python version, including build dependencies. Use `--no-index --find-links` as documented in INSTALL. Linux x86_64 wheels do not become macOS arm64 wheels by renaming them. Do not copy a virtual environment from another machine as an installation method.

## 3. Inspect the input, then extract evidence

Mamey consumes the results of antiSMASH; it does not run antiSMASH itself. Choose a strain identifier and supply only taxonomy and isolation-source information supported by your records:

```bash
INPUT='/absolute/path/to/antismash-results.zip'
"$PY" mamey_run.py inspect "$INPUT"
"$PY" mamey_run.py run --strain EXAMPLE \
  --input-zip "$INPUT" --taxonomy 'Genus sp.' \
  --source 'recorded isolation source' --mode gold --outdir "$WORK/runs"
```

`EXAMPLE` and the metadata strings are placeholders. Read the actual output paths. If the package is emitted at the path below:

```bash
PACKAGE="$WORK/runs/EXAMPLE/package"
"$PY" mamey_run.py validate "$PACKAGE"
"$PY" mamey_run.py explain "$PACKAGE"
```

Resolve validation failures before interpretation. Do not turn a failed checksum or an engine mismatch into a pass by editing the manifest. Preserve the failing package and determine whether a clean rerun or an explicitly supported migration is required. A successfully launched command is not the same as a validated output.

Also read `gate_validation.json`, especially `json_evidence_visibility`, and the scan-state receipt. `MAIN_JSON_WALKER_TRUNCATED` means the bounded JSON path did not read all matching evidence. `UNKNOWN` completeness is unresolved, even when package integrity passes. Check the source-specific evidence tables before interpreting an empty result as absence.

For constrained runtimes, consult the [Quick Guide](GUIDE/02_Quick_Guide.md) before using `--capped-session`: it defers some evidence and outputs. Record what was deferred.

## 4. Review the package and deepen protein evidence

Read the inventory, gene context, comparator evidence, triage board and workbook. Select each region using its complete identity: **strain / full node-or-contig / region / BGC alias**. Copy all four components from a bound source record; do not infer a locus from an alias across package versions.

Use [the protein-search workflow](ONLINE_BLASTP_PROTOCOL.md) to choose manual web BLASTp, the online runner, or import of saved results. Preserve exported protein sequences and query headers, the query manifest, search database, settings, date, hit table and alignment XML. Keep nr, ClusteredNR and Swiss-Prot evidence separate. Import results using the documented command for their format and check that the intended queries were actually bound.

Search completeness matters: a representative protein panel samples the region; it does not establish that every gene was examined. A matching protein or reference cluster does not establish the identity or production of a compound in the focal strain.

## 5. Investigate fragmented regions and author a card

Review RG-GMCI and other fragment-linkage evidence alongside gene coverage, reference geometry and contig boundaries. Preserve competing explanations; nearby or complementary fragments are candidate links, not automatically one reconstructed pathway.

Before card or compiled-report generation, explicitly scope BLASTp discovery to the project that contains the evidence you intend to use:

```bash
export MAMEY_BLASTP_SCAN_ROOT="$WORK"
```

Use the actual evidence project root if results live elsewhere. Do not select an empty directory just to bypass ingestion checks. Automatic discovery uses project markers below the home-directory boundary. An explicit root is still preferable when evidence is outside the analysis project. A `BLASTP_DISCOVERY_HOLD` indicates discovery could not finish; correct the root or access problem and retry. A generated template remains a scaffold, not an authored card.

Use [Mode B authoring](MODEB_GATE_CLEAN_AUTHORING.md) and the selected package's active contract to emit, author and verify the card. Do not splice section numbers from different profiles. Citation availability does not equal passage review or scientific acceptance. Retain unresolved evidence states and check all generated exports against the authored source.

## 6. Compare strains and gene-cluster families

Run and validate each selected strain before building cross-strain summaries. Use explicit run roots and master-workbook paths, and preserve existing outputs before updates. Follow the [User Manual](GUIDE/01_User_Manual.md) for cohort commands.

For gene-cluster families, follow [the BiG-SCAPE workflow](BIGSCAPE_GCF_WORKFLOW.md). It needs compatible external tools and reference inputs in addition to the Python package. Record tool/database versions, settings and the resulting store. The presence of an installed executable or a network widget does not prove a clustering run succeeded.

## 7. Build trees and matched overlays

Follow [the phylogeny workflow](PHYLO_AUTOPILOT_WORKFLOW.md) for 16S placement or genome-based trees. Genome FASTAs and suitable reference metadata are separate inputs; an antiSMASH ZIP is not a substitute for a complete genome assembly.

Verify the chosen tree toolchain, reference panel, outgroup and label mapping. Join heatmap tracks through explicit strain/locus identifiers, then inspect labels, legends and plotted values. Use [the Figure Factory guide](figure_factory/README.md) for rendering and data sidecars. A staged tree job is not a completed tree, and a caption is not proof that the inputs it describes were used.

## 8. Check deliverables and save a reproducible handoff

Choose the outputs that answer the analysis question using the [deliverable menu](DELIVERABLE_MENU.md). Check the produced tables, cards, figures and exports, including missing or refused outputs. Keep derived work separate from sealed evidence unless the relevant command explicitly manages that operation.

Record the bundle checksum, Python and external-tool versions, database versions/hashes, input hashes, exact commands, package-validation result, output paths, and outstanding work. Distinguish installed, command-checked, executed and output-validated capabilities. A doctor summary checks the environment; it does not certify an analysis or every optional workflow.

Development history and historical benchmark results belong in [history](history/README.md) and the [changelog](../CHANGELOG.md), not as instructions to repeat on a new machine.
