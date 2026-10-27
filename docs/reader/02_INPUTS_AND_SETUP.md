# Inputs and setup

Use this checklist to identify your files and prepare the environment for the task you selected. For an existing result, you can read the HTML, workbook and tables without installing Python. The analysis input is a result ZIP from antiSMASH, a separate program that finds biosynthetic gene clusters in a genome.

## 1. Identify the ZIP you have

| File | Its role | Where to go |
|---|---|---|
| Code ZIP | The program, tools and documentation. It is not a strain result or an antiSMASH input. | Locate `pyproject.toml` and `mamey_run.py` together in a writable working installation. |
| antiSMASH result ZIP | The existing results [Mamey](../GLOSSARY.md#names) reads for extraction. It can contain GenBank, JSON, reference-hit text and logs. | Preserve the original ZIP; use [input contents and partial-input limits](../ANTISMASH_INPUTS_CONSUMED.md) to assess what is available. |
| `*Complete_Package.zip` | A saved Mamey result package. | Preserve the ZIP and use [Read one saved package](03_READ_RESULTS.md). Do not rerun extraction merely to open it. |

A genome FASTA alone is not an antiSMASH result ZIP. This guide does not acquire genomes or create antiSMASH results. Keep original filenames and record the actual input path, source version and SHA-256.

## 2. Separate program, input and output locations

Keep three locations explicit:

- **Program:** the directory containing `pyproject.toml` and `mamey_run.py`. An archive can contain an extra enclosing folder.
- **Input:** the preserved antiSMASH ZIP or saved result you intend to use.
- **Output:** a fresh run location under your permitted project folder, outside the program and source evidence. Use the selected workflow's output options.

An external output directory does not redirect every write. Doctor probes the program's own `runs/` directory; package commands have their own write boundaries. Post-seal commands work on a sealed package, one that already passed its extraction and integrity checks. Check [post-seal reader limits](../POSTSEAL_READERS.md) before using a saved package with an authoring command.

## 3. Use one compatible environment

The [package metadata](../../pyproject.toml) requires **Python 3.12 or newer**. Use the same interpreter for installation and the bundle-local launcher.

For a new macOS/Linux environment, first check the interpreter:

```bash
python3 --version
```

If it is older than 3.12, select a compatible installed interpreter before continuing; see [environment setup](../INSTALL.md#2-create-a-python-environment). From the program directory, the core online-installation example is:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
```

Run installation commands only when installation and their network access are authorized. For offline setup, create and activate the environment but skip that pip line: follow the complete [offline installation procedure](../INSTALL.md#offline-installation) with compatible build and dependency wheels. The code ZIP's packaging wheels are not a complete offline runtime. Windows activation is covered in [INSTALL](../INSTALL.md).

Choose extras for the requested task rather than installing every capability:

| Extra | Purpose |
|---|---|
| `bio` | Biopython-dependent parsing and tools |
| `json` | `ijson`, a streaming JSON reader (mamey/ also ships a vendored copy under `_vendor/`) |
| `figures` | Plotting dependencies; the first-analysis walkthrough uses figures and Biopython |
| `documents`, `slides` | The selected Word/document or PowerPoint workflow |
| `render` | CairoSVG conversion support, with its native-library prerequisites |
| `addons` | Optional comparison/scanner bindings; external executables and reference data remain separate |

Use the exact extra-selection syntax in [INSTALL](../INSTALL.md#3-add-the-features-you-need) and the requirements of the selected workflow. The `all` convenience extra excludes `addons` and `test`. See [prerequisites](../PREREQUISITES.md) and [external assets](../EXTERNAL_ASSETS_GUIDE.md) for the distinction between Python packages, system tools and datasets.

## 4. Read the environment diagnostics in scope

For orientation in the configured working installation, this command skips the doctor probe:

```bash
python -B mamey_run.py start --no-doctor
```

The `-B` flag suppresses bytecode writes; it does not make every imported handler read-only. Review the [write-probe and cache boundary](../INSTALL.md#doctor-scope-and-write-probe) before treating any invocation as read-only.

Doctor writes a test file at `runs/_doctor_probe/probe.txt` inside the program folder and removes it afterward. If `runs/_doctor_probe` already exists, doctor leaves it untouched and reports its write check as FAIL; the other checks still run. Move that folder out of `runs/` (keep it; do not delete it), then run doctor again.

```bash
python mamey_run.py doctor
```

Read the individual diagnostics and retain failures and warnings:

| Observation | What it establishes |
|---|---|
| A file or dataset is present | Something was found at the reported path; its version and suitability still need binding. |
| A dependency or executable is discovered | The selected probe found it; a complete workflow has not thereby been tested. |
| The write probe passes | The reserved bundle location was writable, not every future output destination. |
| A capability is missing or a probe fails | That selected prerequisite needs attention; this is not a measured biological negative. |

Doctor does not install missing tools or datasets, run a strain analysis, or certify valid scientific output. A successful overall return does not erase optional warnings.

## 5. Continue from the evidence you have

If setup is already recorded for this installation, activate that environment rather than reinstalling or repeating doctor just because you changed guides.

With the correct input and environment bound, follow [Your first extraction](01_FIRST_RUN.md). With a saved result, follow [Read one saved package](03_READ_RESULTS.md). For a missing task-specific input, use [Companion files](../COMPANION_FILES.md#inputs-for-the-selected-task).
