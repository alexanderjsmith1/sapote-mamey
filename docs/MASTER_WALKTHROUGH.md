# Your first Sapote–Mamey analysis

This guide takes one **antiSMASH result ZIP** and turns it into a package you can open, read
and discuss. You do not need to be a programmer. Either ask an assistant to run the commands
(Route A) or run them yourself in Terminal (Route B). The scientific decisions stay with you:
which strain, which question, what evidence is enough, and what follow-up is worth doing.

Mamey extracts and organizes evidence. Sapote is the interpretation workflow. A finished run or
a high score does not show that the organism makes a compound or has activity in an assay.

## Pick your starting point

| You have… | Start here | You get |
|---|---|---|
| A code ZIP only | [Install](INSTALL.md), then come back | A working program, not biological results |
| An antiSMASH result ZIP | Route A or Route B below | A region inventory and evidence package |
| A Complete_Package.zip from a previous run | [Read your results](READING_YOUR_RESULTS.md) | Understand what you already have before rerunning |
| A genome FASTA only | Run antiSMASH separately first | Mamey does not create antiSMASH results |
| An error or warning | [When something goes wrong](#when-something-goes-wrong) | A specific diagnosis; the attempt is kept |

Three different ZIPs are involved: the code ZIP, the antiSMASH ZIP and the Complete_Package ZIP.
Keep their original names and note which is which. Extract a copy before browsing a ZIP's files.
Do not run the program against its own code ZIP.

## Route A: ask your assistant to run it

Fill in the real paths and paste this:

> Use the Sapote–Mamey program at [program folder]. Inspect the antiSMASH ZIP at
> [input path]. Keep all outputs under [existing project analysis folder] and tell me what you
> will create before writing. Confirm strain identity from the records. Use bounded JSON evidence,
> defer the brief and locus maps, and do not submit sequences to online services. Run and validate
> one strain, then show me the workbook, unresolved evidence and a short result explanation.
> Save state and the available transcript automatically, and give me the portable result ZIP.

If installation is needed, the assistant should tell you which environment and packages it will
use. A missing optional tree tool is not a reason to install every companion. You can also ask
for less: just inspect the ZIP, or just explain an existing package.

## Route B: run the commands yourself

These commands are for **macOS/Linux** and run in Terminal, not inside Python or a chat box.
For Windows environment activation see [INSTALL](INSTALL.md); this route was not tested on
Windows. A quoted path can contain spaces. Lines starting with `#` are comments. Replace the
sample paths before running anything; do not paste the words "absolute/path" as a real location.

### 1. Find your three locations

- **Program folder:** contains both `mamey_run.py` and `pyproject.toml`. A GitHub ZIP may put an
  extra folder inside the extracted folder, so look inside rather than guessing the name.
- **Input ZIP:** the original antiSMASH result. Leave it unchanged.
- **Work folder:** your existing project location for this run. Use a distinct run subfolder
  when you change settings. Keep your established top-level organization.

Set these in the Terminal window you will use. They are shortcuts for this shell session only;
a new Terminal window needs them set again.

```bash
BUNDLE='/absolute/path/to/program-folder'
WORK='/absolute/path/to/project-analysis-folder'
INPUT='/absolute/path/to/antismash-result.zip'
cd "$BUNDLE"
```

`cd` moves Terminal into the program folder. If it says "No such file or directory", stop and
fix the path.

### 2. Set up the environment once

An environment is a private set of Python packages for this project. It is not a biological
input, and it should not be copied to another laptop as a portable installation.

Follow [INSTALL](INSTALL.md) to create and activate the environment and install the extras you
want. For this example, core plus figures and Biopython is enough. Then confirm:

```bash
python --version
python mamey_run.py start
python mamey_run.py doctor
```

Python must be 3.12 or newer. `start` reports which program is loaded; `doctor` reports its
capabilities. Neither one analyzes your strain. Optional capabilities can stay missing if your
task does not use them. If something fails, save the actual error instead of reinstalling
repeatedly.

### 3. Inspect the ZIP

```bash
python mamey_run.py inspect "$INPUT"
```

Look for the antiSMASH version, the region GBK count and the JSON/TXT evidence available. A
positive inventory does not mean every evidence channel will parse completely. The inspector may
suggest a capped command; that is a resource option, not an instruction.

Now pick a local strain label, a verified taxonomy, and an isolation source if you know it.
If `ORGANISM` is a placeholder such as `.`, do not pass it through as taxonomy: check the GBK
DEFINITION and other source records, record where the value came from, or mark taxonomy as
unverified. The GenBank SOURCE label is not necessarily the isolation habitat. Use
`not supplied` when that metadata is unavailable. The
[public-strain walkthrough](ROUND2_PUBLIC_STRAIN_WALKTHROUGH.md) shows real input names, values
and measured outcomes.

### 4. Run one strain

Replace `EXAMPLE` and `Genus sp.` with your label and verified taxonomy:

```bash
python mamey_run.py run --strain EXAMPLE \
  --input-zip "$INPUT" --taxonomy 'Genus sp.' --source 'not supplied' \
  --mode gold --json-evidence bounded --brief none --locus-maps off \
  --release PRIVATE --outdir "$WORK/runs/first_bounded"
```

What this produces: many files, not one report. Tables, workbook, receipts, optional rendered
outputs, and a portable package ZIP. The file count varies with the input and settings; a
package can hold a few hundred entries. Ask for an inventory and size summary. The brief and locus maps are deliberately deferred in this command. Gold does
not author a Mode B card. `PRIVATE` is just the output tag; it says nothing about whether the
source genome is published.

Settings to know before you change them:

- Bounded mode can truncate JSON evidence. The 80 MB full-mode guard uses
  **uncompressed JSON size**, not ZIP size, and full mode can need several GB of RAM. A bigger
  CPU does not bypass a file-size guard. Use the
  [Quick Guide budget table](GUIDE/02_Quick_Guide.md#2-choose-the-evidence-and-runtime-budget)
  before changing settings.
- Do not add `--capped-session` if you want bounded evidence; it forces JSON evidence off for
  the main walker.
- To get the deterministic brief and region maps as well, use `--brief standard --locus-maps on`
  with bounded JSON and a new output root. That is what the Type Strain walkthroughs used. It runs
  no BLASTp or online searches, does not author Mode B interpretation, and does not guarantee
  complete JSON evidence. Full-output packages can contain hundreds of files and exceed 100 MB
  per strain before the portable ZIP. Record their sizes and look at the rendered pages. The
  [Type Strain walkthrough results](TYPE_STRAIN_WALKTHROUGHS.md) give measured examples.

### 5. Validate and read what finished

Copy the package path the run printed. With the example above:

```bash
PACKAGE="$WORK/runs/first_bounded/EXAMPLE/package"
python mamey_run.py validate "$PACKAGE"
python mamey_run.py explain "$PACKAGE"
python mamey_run.py list-bgcs "$PACKAGE"
```

The validator checks encoded rules. It does not confirm that every requested output exists,
that JSON evidence is exhaustive, or that interpretation is finished. Now go to
[Read your results](READING_YOUR_RESULTS.md) to open the workbook and the status files.

## When something goes wrong

| What you see | What it usually means | What to do |
|---|---|---|
| File/path not found | Wrong folder or unquoted path | Fix the path; keep spaces inside quotes |
| Python below 3.12 | Wrong interpreter selected | Pick a supported interpreter and recreate only the intended environment |
| No module named… | The active environment lacks a dependency | Confirm activation; install the documented feature, not every available package |
| `MAIN_JSON_PARSE_HELD` | Full-mode file exceeds its guard | Keep this run; use bounded in a separate output root if partial evidence suits the task |
| `MAIN_JSON_WALKER_TRUNCATED` | Bounded evidence limit reached | Record the gap; check whether it affects your question before doing more |
| `UNKNOWN` completeness | Completion was not established | Keep the uncertainty; do not call the channel complete or absent |
| Validation failure | A required gate failed | Stop the affected interpretation and diagnose the actual gate; never edit status to PASS |
| Missing brief/locus maps | Probably deferred on purpose | Check the command and receipts before calling it a failure |
| Interruption | The attempt may be partial | Keep logs and outputs; use a new run directory or a documented resume |

When you ask for help, include the command, the Python version, the input filename/hash, the
last error, and the output directory. Send the text log; a screenshot alone often misses the
useful part.

## Reopen or move a result

Use the existing Complete_Package ZIP. Do not rerun just because you started a new conversation.
On another laptop, extract a copy and open `OPEN_ME_FIRST.html`. Keep the whole extracted folder
together; the links point at neighbouring files. The workbook opens in Excel. Re-running the
software needs its own compatible Python installation. Keep the checksum and run receipts.
There is no need to copy the source ZIP, environment or working folder without a reason.

To patch the software, transfer the candidate patch kit and follow its numbered README. A patch
kit changes program files; a Complete_Package ZIP holds analysis results. They are not
interchangeable. Save state and transcript coverage as described in the
[shared handoff policy](ASSISTANT_USER_GUIDE.md#next-paths-automatic-save-state-and-transcripts).

## Optional follow-up work

Look at the first result, then pick one question. Each workflow below has its own extra inputs
and environment requirements.

### Review the package and deepen protein evidence

Read the inventory, gene context, comparator evidence, triage board and workbook. Name each
region by its complete identity: **strain / full node-or-contig / region / BGC alias**. Copy
all four parts from one bound source record; do not infer a locus from an alias across package
versions.

Use [the protein-search workflow](ONLINE_BLASTP_PROTOCOL.md) to choose manual web BLASTp, the
online runner, or import of saved results. Keep the exported protein sequences and query
headers, the query manifest, search database, settings, date, hit table and alignment XML. Keep
nr, ClusteredNR and Swiss-Prot evidence separate. Import results with the documented command for
their format and check that the intended queries were actually bound.

A representative protein panel samples the region; it does not show that every gene was
examined. A matching protein or reference cluster does not establish the identity or production
of a compound in your strain.

### Investigate fragmented regions and author a card

Read the RG-GMCI and other fragment-linkage evidence alongside gene coverage, reference geometry
and contig boundaries. Keep competing explanations; nearby or complementary fragments are
candidate links, not automatically one reconstructed pathway.

Before you generate a card or compiled report, point BLASTp discovery at the project that holds
the evidence you intend to use:

```bash
export MAMEY_BLASTP_SCAN_ROOT="$WORK"
```

Use the real evidence project root if results live elsewhere. Do not point it at an empty
directory just to get past ingestion checks. Automatic discovery uses project markers below the
home-directory boundary, but an explicit root is better when evidence is outside the analysis
project. A `BLASTP_DISCOVERY_HOLD` means discovery could not finish; fix the root or access
problem and retry.

Then use [Mode B authoring](MODEB_GATE_CLEAN_AUTHORING.md) and the package's active contract to
emit, author and verify the card. A generated template is a scaffold, not an authored card. Do
not splice section numbers from different profiles. Having a citation does not mean the passage
was reviewed or the science accepted. Keep unresolved evidence states, and check every generated
export against the authored source.

### Compare strains and gene-cluster families

Run and validate each strain before you build cross-strain summaries. Use explicit run roots
and master-workbook paths, and keep existing outputs before updating. The
[User Manual](GUIDE/01_User_Manual.md) has the cohort commands.

For gene-cluster families, follow [the BiG-SCAPE workflow](BIGSCAPE_GCF_WORKFLOW.md). It needs
compatible external tools and reference inputs beyond the Python package. Record tool/database
versions, settings and the resulting store. An installed executable or a network widget does not
prove a clustering run succeeded.

### Build trees and matched overlays

Follow [the phylogeny workflow](PHYLO_AUTOPILOT_WORKFLOW.md) for 16S placement or genome-based
trees. Genome FASTAs and reference metadata are separate inputs; an antiSMASH ZIP is not a
genome assembly.

Check the tree toolchain, reference panel, outgroup and label mapping. Join heatmap tracks
through explicit strain/locus identifiers, then look at the labels, legends and plotted values.
Use [the Figure Factory guide](figure_factory/README.md) for rendering and data sidecars. A
staged tree job is not a completed tree, and a caption is not proof that the inputs it describes
were used.

### Check deliverables and save a reproducible handoff

Pick the outputs that answer your question from the [deliverable menu](DELIVERABLE_MENU.md).
Check the tables, cards, figures and exports you produced, including anything missing or refused.
Keep derived work separate from sealed evidence unless the relevant command manages that
operation itself.

Record the bundle checksum, Python and external-tool versions, database versions/hashes, input
hashes, exact commands, package-validation result, output paths, and outstanding work. Say which
capabilities were installed, command-checked, executed and output-validated; a doctor summary
checks the environment, not the analysis.

Development history and historical benchmark results live in [history](history/README.md) and
the [changelog](../CHANGELOG.md). They are records, not instructions to repeat on a new machine.

### Reopen, transfer and recover

You do not need to rerun extraction to read saved results. [Files, storage and handoff](FILES_STORAGE_AND_HANDOFF.md)
covers reopening a package, keeping original inputs, comparing transfer hashes and accounting
for later authored work. [Troubleshooting](COMMON_MISTAKES.md) lists recognizable error symptoms
and recovery steps. The [documentation map](DOCUMENTATION_MAP.md) separates first-run guides from
specialist and historical records.

### Continue into authored Mode B interpretation

[The Mode B user walkthrough](MODE_B_USER_WALKTHROUGH.md) covers package inputs, exact identity,
runnable preparation/verification examples, profile differences and the complete 50-section
requirement map. The native scaffold is not a finished 50-section card.
