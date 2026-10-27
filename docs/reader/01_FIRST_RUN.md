# Your first extraction from an antiSMASH ZIP

Use this route when you have one antiSMASH result ZIP and want an evidence package
and workbook. antiSMASH is a separate program that finds biosynthetic gene clusters in a genome.

## 1. Identify the three locations and finish setup

| Item | Its role |
|---|---|
| Program folder | The working code installation containing `mamey_run.py` and `pyproject.toml` |
| antiSMASH result ZIP | The supplied analysis input; preserve its original bytes and checksum |
| Fresh run folder | A new output destination, separate from the input and earlier attempts |

A code ZIP is software, not an analysis input. If you have a Complete_Package ZIP
instead, go directly to [Read one saved package](03_READ_RESULTS.md).

If setup is not done yet, follow [Inputs and setup](02_INPUTS_AND_SETUP.md) first.
Reuse a working environment if you already have one. To have an assistant run it, use the
[walkthrough request](../MASTER_WALKTHROUGH.md#route-a-ask-your-assistant-to-run-it).

The examples below use a macOS/Linux shell. Replace every example path and
`EXAMPLE` with your actual locations and local strain label. Windows users should
follow the [installation guide's activation instructions](../INSTALL.md#2-create-a-python-environment)
and adapt shell syntax.

```bash
BUNDLE='/absolute/path/to/working-program'
INPUT='/absolute/path/to/supplied-antismash-result.zip'
OUT='/absolute/path/to/project/runs/EXAMPLE_first_run'
cd "$BUNDLE"
```

Keep the input filename, SHA-256 and producing antiSMASH settings with the run.
Use a fresh `OUT` if settings or inputs change.

## 2. Inspect the supplied ZIP

```bash
python mamey_run.py inspect "$INPUT"
```

Read the archive classification, available GenBank/JSON/TXT members and warnings.
This is a filename/marker preview, not proof that every record will parse or that
the assembly is complete. If its count looks wrong, compare the actual members
before requesting new upstream results. See [SOP-01 intake and preview limits](../SOPs/SOP-01_Intake_RawAntiSMASH_vs_MameyPackage.md#inspector-and-validator-scope).

Confirm the strain label and taxonomy from source records. Add
`--taxonomy 'Genus species'` only when a source record supports it. If you leave it
out, the run records `not verified`. Record the isolation source as deposited;
GenBank's organism/SOURCE line is not necessarily the habitat. Keep
`--source 'not supplied'` when no source is recorded.

## 3. Extract with bounded JSON evidence

Run this only after inspection and setup are satisfactory:

```bash
python mamey_run.py run --strain EXAMPLE \
  --input-zip "$INPUT" --source 'not supplied' \
  --mode gold --json-evidence bounded --brief none --locus-maps off \
  --reference-completion off --require-workbook \
  --release PRIVATE --outdir "$OUT"
```

This selects gold extraction (the default analysis mode), bounded JSON evidence and a required workbook. It
defers the brief and locus maps and turns optional reference completion off.
`PRIVATE` is a local output tag, not a claim about the source genome's publication
status or permission to distribute it.

Bounded evidence can truncate or fall back; read the effective mode and channel
receipts. Do not add `--capped-session` to this recipe: it forces main JSON evidence
off. If a session cannot support this bounded route, choose the tradeoff in the
[budget table](../GUIDE/02_Quick_Guide.md#2-choose-the-evidence-and-runtime-budget)
before starting a separate attempt.

## 4. Check the package and workbook separately

Use the actual package path printed by the run. With the example label and output
root above, it should be `$OUT/EXAMPLE/package`. Validate this newly produced working
output; the command can refresh `package_status.json`. For an older preserved
package, follow the [validation write scope](../POSTSEAL_READERS.md#validation-can-update-a-mutable-status-receipt)
and use a separate review copy.

```bash
PACKAGE="$OUT/EXAMPLE/package"
python mamey_run.py validate "$PACKAGE" --workbook-strict
```

Save the printed main result, `WORKBOOK_CONTENT` result and exit status. Also confirm
the expected `EXAMPLE_5_workbook.xlsx` belongs to this run.

| Check | Required disposition for this journey |
|---|---|
| Workbook production | `--require-workbook` makes a production failure fail the run |
| Missing matching workbook at validation | `--workbook-strict` reports `FAIL_WORKBOOK_MISSING` and exits nonzero |
| Present workbook with non-PASS content result | Strict validation exits nonzero |
| Main package check | Inspect its own result and issues; a workbook result cannot replace it |

Without strict mode, a missing workbook can report `SKIP` without failing that
branch. With several matching workbooks, only the first in sorted order is checked,
so verify the intended file yourself. A passing check does not certify every cell
or exhaustive evidence. [SOP-01](../SOPs/SOP-01_Intake_RawAntiSMASH_vs_MameyPackage.md#inspector-and-validator-scope)
describes the check's scope.

If extraction or validation fails, retain the attempt, command, logs and final
error. Diagnose the failed stage using [Recovery and limits](04_RECOVERY_AND_LIMITS.md);
do not overwrite the attempt or edit a status to PASS.

## 5. Open and retain what finished

Expect a package containing the inventory, triage board (the ranked region list), workbook, manifest, issue
log and reading entry page, plus a portable `*Complete_Package.zip` at the location
printed by the run. Confirm the actual files and sizes rather than assuming all
optional outputs were generated.

Open `OPEN_ME_FIRST.html`, then follow [Read one saved package](03_READ_RESULTS.md)
to inspect the workbook, issues and source tables. Keep the original input, run
settings, validation output and portable ZIP; retain later authored outputs
separately when needed.

This completes an extraction-and-review handoff, not authored [Mode B](../GLOSSARY.md#14-mode-b) interpretation.
Missing, failed, unrun and observed no-hit channels remain different states.
Scores and reference similarity do not establish compound production or activity.
If you later choose a card or another output, use [Choose a task](../USER_TASK_ROUTER.md)
to select its inputs and completion evidence.
