# Start a first run

Identify the file you have, then follow one route. The [first-analysis walkthrough](../MASTER_WALKTHROUGH.md)
contains the command sequence; this page helps you prepare for it.

| What you have | Your next action | What to expect |
|---|---|---|
| Code ZIP only | [Install the program](../INSTALL.md) | A program folder and Python environment; you still need an analysis input |
| antiSMASH result ZIP | Prepare below, then follow the walkthrough | A region inventory, evidence package and workbook to review |
| Complete_Package ZIP | [Read your results](../READING_YOUR_RESULTS.md) | Open saved results before deciding whether more work is needed |
| Genome FASTA only | Obtain antiSMASH results through a separate upstream workflow | An antiSMASH result ZIP for this extraction route |

## 1. Prepare your input and locations

Keep the original input unchanged. Identify the local strain label, taxonomy and isolation
metadata from source records; leave unknown values explicit. Choose a separate output location
and a fresh run destination if you change settings. Save the input identity/hash and command.

For execution, follow [Install](../INSTALL.md) with Python 3.12 or newer. The program folder
contains both `mamey_run.py` and `pyproject.toml`. Use a writable working installation.
The walkthrough explains which optional features its example needs; a first extraction does
not require every companion tool.

## 2. Choose assistant operation or Terminal

- **With an assistant:** fill in the paths and question in [Route A](../MASTER_WALKTHROUGH.md#route-a-ask-your-assistant-to-run-it).
  Agree on the input, output location and intended work. Decide separately about online sequence
  submissions and optional external analyses.
- **In Terminal:** follow [Route B](../MASTER_WALKTHROUGH.md#route-b-run-the-commands-yourself)
  from the program folder. Replace its example paths and metadata with your own.

During setup, inspect the diagnostics before proceeding. The walkthrough uses
`python -B mamey_run.py start --no-doctor` for orientation, then `doctor` separately.
Before `doctor`, read its [write-probe boundary](../INSTALL.md#doctor-scope-and-write-probe)
and leave an occupied `runs/_doctor_probe` untouched. Plain `start` also invokes that diagnostic.
A successful orientation exit does not prove the chosen analysis will work.

For preserved code or an inspection-only request, read files without executing them.
`-B` and `--no-doctor` do not establish that the whole program is read-only. The
[installation guide](../INSTALL.md#doctor-scope-and-write-probe) explains cache writes, bytecode
refusals and the limits of the synthetic launcher tests; cache removal is a separate mutation.
Leave `doctor --probe-transports` out of an offline setup because it makes network probes.

After `inspect`, check the reported antiSMASH version, region GBK count and available JSON/TXT
evidence. Use the walkthrough's extraction settings consistently: the short command printed
by `start` uses `--capped-session`, which forces main JSON evidence off. It does not preserve
the walkthrough's bounded JSON evidence. Use the [budget table](../GUIDE/02_Quick_Guide.md#2-choose-the-evidence-and-runtime-budget)
if you need to change that choice.

## 3. Check the package and open the result

Use the actual package path printed by the run. Follow the walkthrough's validate-and-read step
on the writable output: `validate` can refresh `package_status.json`. For preserved evidence,
read saved receipts first and arrange a separate verification workspace before invoking it.

The walkthrough requires a workbook and validates with `--workbook-strict`. Read both the main
package result and `WORKBOOK_CONTENT`, plus the exit status. Without that flag, a missing workbook
reports `SKIP`; with it, a missing workbook or non-PASS workbook-content result fails the command.
Validation checks encoded conditions; it does not finish interpretation or certify exhaustive evidence.

Next, open [Read your results](../READING_YOUR_RESULTS.md): inspect the entry page, issues,
workbook and source inventory. The CLI `list-bgcs` view can hide dropped rows, so use the source
inventory for the complete region roster. Keep the Complete_Package ZIP and separately produced
outputs needed for transfer. A new conversation alone is not a reason to rerun extraction.

## If the attempt fails

Keep the attempt and final error. Record the loaded version, interpreter, command, input,
output path and exit code. Use [Troubleshooting](../COMMON_MISTAKES.md) to fix one diagnosed
problem at a time, preserving the earlier attempt.
