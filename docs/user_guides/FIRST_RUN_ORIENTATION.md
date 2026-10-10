# Start a first run


Start by identifying the file you have. A code ZIP installs the program. An antiSMASH result ZIP is an analysis input. A Complete_Package ZIP contains results you can already read. A genome FASTA needs an upstream antiSMASH workflow before this extraction route.

## Choose how you want to work

You can ask an assistant to operate the program, or use a terminal yourself. In either case, agree on the input, question, output location and intended work. Decide separately whether you want any online sequence submissions or optional external analyses; a first extraction does not require every companion workflow.

If you already have results, use the results reader before rerunning. A new conversation is not by itself a reason to repeat an analysis.

## Prepare the program and input

Use [INSTALL.md](../INSTALL.md) for the environment setup, then [MASTER_WALKTHROUGH.md](../MASTER_WALKTHROUGH.md) for the complete first-run procedure. Work from the program folder containing `mamey_run.py` and `pyproject.toml`, with a separate output location. The installation guide requires Python 3.12 or newer and distinguishes core requirements from optional features.

These orientation commands are supported by the bundle parser:

```bash
python mamey_run.py start
python mamey_run.py doctor
python mamey_run.py inspect '/your/actual/antismash-result.zip'
```

Replace the example path before running it. `start` prints orientation; `doctor` checks the environment; `inspect` previews the input. They do not substitute for the extraction, validation and interpretation steps. The optional `doctor --probe-transports` flag makes network probes, so leave it out for an offline orientation.

Read the current walkthrough when choosing extraction settings. The short route printed by `start` includes `--capped-session`; that setting forces the main JSON evidence off. It is different from the walkthrough’s bounded-JSON route. Choose the evidence scope deliberately rather than combining settings from two examples.

## Know what a successful attempt should leave

Before extraction, identify the real strain label and the source of the supplied taxonomy and isolation metadata. Keep an unknown value explicit. Use a fresh run destination for a changed configuration. Save the command and input identity/hash.

After extraction, use the actual package path printed by the run. In this candidate, `validate` can refresh `package_status.json` inside that package. Use it on the writable run output you intend to check; for a preserved evidence package, read its saved receipts first and arrange a separate verification workspace before invoking it. The current CLI accepts the package as a positional argument for these checks:

```bash
python mamey_run.py validate '/your/actual/package'
python mamey_run.py explain '/your/actual/package'
python mamey_run.py list-bgcs '/your/actual/package'
```

A validator checks encoded conditions; it does not certify that every evidence channel is exhaustive or that a biological interpretation is finished. Open the actual result files and review the issues and evidence states. Keep the Complete_Package ZIP and any separately produced outputs you need to transfer.

## If the attempt fails

Keep the attempt and the final error. Record the loaded version, interpreter, command, input, output path and exit code. Fix one diagnosed problem at a time. Use [COMMON_MISTAKES.md](../COMMON_MISTAKES.md) for symptom-based recovery. Avoid overwriting an earlier attempt simply to make the visible status look complete.


