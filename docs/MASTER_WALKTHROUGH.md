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
Keep their original names and note which is which. Browse archive members in place where possible; extract only the selected files needed for reading or an isolated working candidate, while preserving the original ZIP.
Do not run the program against its own code ZIP.

## Route A: ask your assistant to run it

Fill in the real paths and paste this:

> Use the Sapote–Mamey program at [program folder]. Inspect the antiSMASH ZIP at
> [input path]. Keep all outputs under [existing project analysis folder] and tell me what you
> will create before writing. Confirm strain identity from the records. Use bounded JSON evidence,
> defer the brief and locus maps, turn reference completion off, and do not submit sequences
> to online services. Require the workbook when running one strain, then validate with
> `--workbook-strict`. Show me the workbook, unresolved evidence and a short result explanation.
> Save state and the available transcript automatically, and give me the portable result ZIP.

If installation is needed, the assistant should tell you which environment and packages it will
use. A missing optional tree tool is not a reason to install every companion. You can also ask
for less: just inspect the ZIP, or just explain an existing package.

## Route B: run the commands yourself

These commands are for **macOS/Linux** and run in Terminal, not inside Python or a chat box.
Windows users should follow [INSTALL](INSTALL.md) for environment activation and adapt the
macOS/Linux shell syntax below to their shell. A quoted path can contain spaces. Lines starting with `#` are comments. Replace the
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

Complete [INSTALL steps 1–4](INSTALL.md) for this program installation and environment.
For this example, use Python 3.12 or newer with the core, figures and Biopython dependencies.
Read the [doctor write-probe and cache boundary](INSTALL.md#doctor-scope-and-write-probe)
before the setup diagnostics; they belong in a writable working installation. If
`runs/_doctor_probe` already exists, move it out of `runs/` (keep it; do not delete it)
before you run doctor.

If you already completed those steps for this installation and environment, activate that
existing environment in this Terminal and continue to step 3 below. Do not reinstall or repeat
the probe just because you moved between guides. Keep the setup diagnostics: missing optional
capabilities matter only for the work that uses them, and a successful check does not establish
valid analysis output. If setup failed, retain the actual error before trying a targeted fix.

### 3. Inspect the ZIP

```bash
python mamey_run.py inspect "$INPUT"
```

Look for the antiSMASH version, the region GBK count and the JSON/TXT evidence available. A
positive inventory does not mean every evidence channel will parse completely. The inspector may
suggest a capped command; that is a resource option, not an instruction.

Now pick a local strain label, a verified taxonomy, and an isolation source if you know it.
If `ORGANISM` is a placeholder such as `.`, do not pass it through as taxonomy: check the GBK
DEFINITION and other source records and record where the value came from. If taxonomy is
unverified, leave out `--taxonomy`; the run records `not verified`. The GenBank SOURCE label is
not necessarily the isolation habitat. Use `--source 'not supplied'` when no isolation source
is recorded. The
[public-strain walkthrough](ROUND2_PUBLIC_STRAIN_WALKTHROUGH.md) shows real input names, values
and measured outcomes.

### 4. Run one strain

Replace `EXAMPLE` and `Genus sp.` with your label and verified taxonomy:

```bash
python mamey_run.py run --strain EXAMPLE \
  --input-zip "$INPUT" --taxonomy 'Genus sp.' --source 'not supplied' \
  --mode gold --json-evidence bounded --brief none --locus-maps off \
  --reference-completion off --require-workbook \
  --release PRIVATE --outdir "$WORK/runs/first_bounded"
```

What this produces: many files, not one report. Tables, workbook, receipts, optional rendered
outputs, and a portable package ZIP. The file count varies with the input and settings; a
package can hold a few hundred entries. Ask for an inventory and size summary. The brief and locus maps are deliberately deferred, and reference-completion searches are off. This command requires workbook production; a failure is not a completed table handoff. Gold does
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

Copy the package path the run printed. Validate the writable output from this run:
`validate` can refresh `package_status.json`. For an existing preserved package, read
its saved receipts first and use a separate review copy for a new check; see
[validation write scope](POSTSEAL_READERS.md#validation-can-update-a-mutable-status-receipt).
Capture printed findings and the exit status beside the package. With the example above:

```bash
PACKAGE="$WORK/runs/first_bounded/EXAMPLE/package"
python mamey_run.py validate "$PACKAGE" --workbook-strict
python mamey_run.py explain "$PACKAGE"
python mamey_run.py list-bgcs "$PACKAGE"
```

The validator checks encoded rules. It does not confirm that every requested output exists,
that JSON evidence is exhaustive, or that interpretation is finished. Read the main result and
`WORKBOOK_CONTENT` separately. Without `--workbook-strict`, an absent workbook reports `SKIP`
and does not fail the workbook branch. With `--workbook-strict`, no matching
`*_5_workbook.xlsx` reports `FAIL_WORKBOOK_MISSING` and exits nonzero. When the workbook is a
required deliverable, add `--workbook-strict` to the validation command and confirm the expected
workbook path/current receipt independently; see the [inspector and validator scope](SOPs/SOP-01_Intake_RawAntiSMASH_vs_MameyPackage.md#inspector-and-validator-scope). Now go to
[Read your results](READING_YOUR_RESULTS.md) to open the workbook and the status files.

## When something goes wrong

| What you see | What it usually means | What to do |
|---|---|---|
| File/path not found | Wrong folder or unquoted path | Fix the path; keep spaces inside quotes |
| Python below 3.12 | Wrong interpreter selected | Pick a supported interpreter and recreate only the intended environment |
| No module named… | The active environment lacks a dependency | Confirm activation; install the documented feature, not every available package |
| `MAIN_JSON_PARSE_HELD` | Main-walker JSON errors or skipped members; the full-mode size guard is one possible cause | Keep the attempt; read the recorded error/skip reasons and affected members before choosing any separate rerun |
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
together; the links point at neighboring files. The workbook opens in Excel. Re-running the
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

Choose the card's contract with [the profile matrix](MODEB_PROFILE_MATRIX.md), then follow
[Mode B authoring](MODE_B_USER_WALKTHROUGH.md) to emit, author and verify it. Before native
`mode-b` authoring, read [post-seal write boundaries](POSTSEAL_READERS.md#commands-that-write-into-the-package):
an external output folder can still leave the supplied package's integrity records refreshed.
Use a bound working package copy for commands that author package data. Sealed-input
`compile-report` has a separate external-reader route described in that guide; check the
selected command rather than treating all follow-on work alike.

A generated template is a scaffold, not an authored card. Keep the same profile through
emission and verification; preserve unresolved evidence states and check each export against
the authored source. A citation alone does not establish source review or scientific acceptance.
For another selected output, use [Choose a task](USER_TASK_ROUTER.md).

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
trees. Supply a full genome assembly FASTA and the required reference metadata. An antiSMASH ZIP may contain that full assembly; if used, record its exact member path and hash. Clipped region GenBank files are not a substitute for the whole assembly.

Check the tree toolchain, reference panel, outgroup and label mapping. Join heatmap tracks
through explicit strain/locus identifiers, then look at the labels, legends and plotted values.
Start with [Make and review figures](FIGURES_START_HERE.md) to choose the rendering route
and retain its plotted data and captions. A
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

