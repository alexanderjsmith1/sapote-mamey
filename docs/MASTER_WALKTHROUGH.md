# Your first Sapote–Mamey analysis

Use this guide to turn one **antiSMASH result ZIP** into a package you can inspect and discuss.
You do not need to become a programmer. You can ask an assistant to run the commands, or follow
the terminal route yourself. The scientific decisions remain yours: which strain, which question,
what evidence is sufficient, and which follow-up work is worthwhile.

Mamey extracts and organizes evidence. Sapote is the interpretation workflow. Neither a successful
run nor a high score establishes that the organism produces a compound or shows activity in an assay.

## Choose how you want to work

| You have… | Start here | Expected outcome |
|---|---|---|
| A code ZIP only | Installation below | A working program, not biological results |
| An antiSMASH result ZIP | Inspect and run below | A region inventory and evidence package |
| A Complete_Package.zip from a previous run | [Read your results](READING_YOUR_RESULTS.md) | Understand the existing output before deciding to rerun |
| A genome FASTA only | Arrange antiSMASH separately | Mamey does not create antiSMASH results |
| An error or warning | Recovery table below | A specific diagnosis and preserved attempt |

The code ZIP, antiSMASH ZIP and Complete_Package ZIP serve different purposes. Keep their original
names and record which is which. A ZIP is a compressed container; extract a copy before browsing
its files. Do not run the program against its own code ZIP.

## Route A: ask your assistant to operate the program

Supply the actual paths and replace the bracketed descriptions:

> Use the existing Sapote–Mamey candidate at [program folder]. Inspect the antiSMASH ZIP at
> [input path]. Keep all outputs under [existing project analysis folder] and tell me what you
> will create before writing. Confirm strain identity from the records. Use bounded JSON evidence,
> defer the brief and locus maps, and do not submit sequences to online services. Run and validate
> one strain, then show me the workbook, unresolved evidence and a short result explanation.
> Save state and the available transcript automatically, and give me the portable result ZIP.

If the environment needs installation, the assistant should tell you which environment and
packages it will use. A missing optional tree tool is not a reason to install every companion.
You can instead ask only to inspect the ZIP or explain an existing package.

## Route B: run the commands yourself

The commands below are for **macOS/Linux**. They run in Terminal, not inside Python or a chat box.
A quoted path can contain spaces. Lines beginning with `#` are comments. Replace sample paths
before running anything; do not paste the words “absolute/path” as a real location.
For Windows environment activation, use [INSTALL](INSTALL.md); this route was not tested on Windows.

### 1. Identify three locations

- **Program folder:** contains both `mamey_run.py` and `pyproject.toml`. A GitHub ZIP may add a
  folder inside the extracted folder. Look inside rather than guessing the name.
- **Input ZIP:** the original antiSMASH result; leave it unchanged.
- **Work folder:** your existing project location for this run. Use a distinct run subfolder for
  changed settings. Preserve your established top-level organization.

Set these variables in the same Terminal window. They are shortcuts for this shell session:

```bash
BUNDLE='/absolute/path/to/program-folder'
WORK='/absolute/path/to/project-analysis-folder'
INPUT='/absolute/path/to/antismash-result.zip'
cd "$BUNDLE"
```

`cd` changes Terminal's working folder. If it says “No such file or directory,” stop and correct
the path. These variables will need to be set again in a new Terminal window.

### 2. Prepare the environment once

An environment is a private installation of Python packages for this project. It is not a
biological input and should not be copied to another laptop as a portable installation.

Follow [INSTALL](INSTALL.md) to create/activate the environment and install the selected extras.
For the example below, core plus figures and Biopython are sufficient. Confirm:

```bash
python --version
python mamey_run.py start
python mamey_run.py doctor
```

The selected Python must be 3.12 or newer. If `ORGANISM` is a placeholder such as `.`, do not
pass it through as taxonomy: inspect the GBK DEFINITION and other source records, record the
binding source, or preserve taxonomy as unverified. `start` reports the loaded program; `doctor` reports
capabilities. Neither command analyzes your strain. Optional missing capabilities can remain
missing if the requested task does not use them. Save actual errors rather than repeatedly reinstalling.

### 3. Inspect before running

```bash
python mamey_run.py inspect "$INPUT"
```

Look for the antiSMASH version, region GBK count and available JSON/TXT evidence. A positive
inventory does not mean every evidence channel will be parsed completely. The inspector may
suggest a capped command; that is a resource option, not an instruction to override your choice.

Choose a local strain label, verified taxonomy, and an isolation source only if known. The
GenBank organism label named SOURCE is not necessarily the isolation habitat. Use `not supplied`
when that metadata is unavailable. The [public-strain walkthrough](ROUND2_PUBLIC_STRAIN_WALKTHROUGH.md)
gives actual input names, values and measured outcomes.

### 4. Run one strain with explicit settings

Replace `EXAMPLE` and `Genus sp.` with your chosen label and verified taxonomy:

```bash
python mamey_run.py run --strain EXAMPLE \
  --input-zip "$INPUT" --taxonomy 'Genus sp.' --source 'not supplied' \
  --mode gold --json-evidence bounded --brief none --locus-maps off \
  --release PRIVATE --outdir "$WORK/runs/first_bounded"
```

This creates many files, not just one report: tables, workbook, receipts and optional rendered
outputs, plus a portable package ZIP. In the Round 2 brevicatena example the package held 217
file/directory entries; this is an example, not a guaranteed count. Ask for an inventory and size
summary. The brief and locus maps are deliberately deferred here. Gold does not author a Mode B card.
PRIVATE is the selected output tag; it is not evidence that the source genome is unpublished.

Bounded mode can truncate JSON evidence. The 80 MB candidate full mode uses **uncompressed JSON
size**, not ZIP size, and can require several GB RAM. A bigger CPU does not bypass a file-size guard.
Use the [Quick Guide budget table](GUIDE/02_Quick_Guide.md#2-choose-the-evidence-and-runtime-budget)
before changing settings. Do not add `--capped-session` to preserve bounded evidence; it overrides
that selection to off for the main walker.

### Expand the offline outputs when you need them

For the deeper Type Strain walkthroughs we used `--brief standard --locus-maps on`, keeping
bounded JSON and a new output root. That renders a deterministic brief and region maps without
running BLASTp or online searches. It still does not author Mode B interpretation or guarantee
complete JSON evidence. Full-output packages can contain hundreds of files and exceed 100 MB
per strain before considering the portable ZIP. Record their sizes and review rendered pages.
Use the [Type Strain walkthrough results](TYPE_STRAIN_WALKTHROUGHS.md) for measured examples.

### 5. Validate and read what actually finished

Copy the actual package path printed by the run. With the example above:

```bash
PACKAGE="$WORK/runs/first_bounded/EXAMPLE/package"
python mamey_run.py validate "$PACKAGE"
python mamey_run.py explain "$PACKAGE"
python mamey_run.py list-bgcs "$PACKAGE"
```

A package validator checks encoded rules. It does not establish that every requested output exists,
that JSON evidence is exhaustive, or that biological interpretation is finished. Follow
[Read your results](READING_YOUR_RESULTS.md) to open the workbook and understand the status files.

## When something goes wrong

| What you see | What it usually means | What to do |
|---|---|---|
| File/path not found | Wrong folder or unquoted path | Correct the path; keep spaces inside quotes |
| Python below 3.12 | Wrong interpreter selected | Select a supported interpreter and recreate only the intended environment |
| No module named… | Selected environment lacks a dependency | Confirm activation; install the documented feature, not every available package |
| `MAIN_JSON_PARSE_HELD` | Full-mode file exceeds its guard | Retain this run; use bounded in a separate output root if partial evidence suits the task |
| `MAIN_JSON_WALKER_TRUNCATED` | Bounded evidence limit reached | Record the gap; inspect whether it affects the question before choosing further work |
| `UNKNOWN` completeness | Completion is not established | Preserve uncertainty; do not call the channel complete or absent |
| Validation failure | A required gate failed | Stop affected interpretation and diagnose the actual gate; do not edit status to PASS |
| Missing brief/locus maps | May have been explicitly deferred | Check the command and receipts before treating it as a failure |
| Interruption | Attempt may be partial | Retain logs and outputs; use a new run directory or a documented resume operation |

When asking for help, include the command, selected Python version, input filename/hash, last error,
and output directory. A screenshot alone may omit useful context; the text log is better evidence.

## Reopen or move a result

Use the existing Complete_Package ZIP; do not rerun merely because a new conversation starts.
On the other laptop, extract a copy and open `OPEN_ME_FIRST.html`. Keep the complete extracted
folder together because links use neighboring files. A workbook can be opened in Excel; software
re-execution requires its own compatible Python installation. Preserve checksum and run receipts.
No source ZIP, environment or working folder needs to be duplicated without a stated purpose.

For patching software, transfer the candidate patch kit and follow its numbered README. A patch
kit changes program files; a Complete_Package ZIP contains biological analysis results. They are
not interchangeable. Save state and transcript coverage using the [shared handoff policy](ASSISTANT_USER_GUIDE.md#next-paths-automatic-save-state-and-transcripts).

## Optional follow-up work

Choose one question after reviewing the first result. The following workflows are optional and
have additional input and environment requirements.

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

## Reopen, transfer and recover

You do not need to rerun extraction to read saved results. Follow [Files, storage and handoff](FILES_STORAGE_AND_HANDOFF.md) to reopen a package, retain original inputs, compare transfer hashes and account for later authored work. For recognizable error symptoms and recovery steps, use [Troubleshooting](COMMON_MISTAKES.md). The [documentation map](DOCUMENTATION_MAP.md) separates first-run guides from specialist and historical records.

## Continue into authored Mode B interpretation

Use [the Mode B user walkthrough](MODE_B_USER_WALKTHROUGH.md) for package inputs, exact identity, runnable preparation/verification examples, profile differences and the complete 50-section requirement map. The native scaffold is not a universal finished 50-section card.
