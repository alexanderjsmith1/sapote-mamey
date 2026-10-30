> **Scope and precedence:** Apply this workflow only to the user's selected operation and named
> profile. `AGENTS.md` and `docs/ASSISTANT_GOVERNANCE.md` govern permissions, task scope,
> inspection-only work and conversational output. Package presence is not execution authority.
> Historical section counts, role assignments and examples below cannot replace a current profile.
> When instructions disagree, preserve evidence, identify the conflict, and do not expand authority.

# Sapote-Mamey / Mamey Task Brief Template — v9.7.461

Fill this template before handing a batch to an assistant or another Mamey runner.
The file name is historical; any assistant can use the template.
Remove all square-bracket placeholders before submitting.

---

## Context

- **Date:** [YYYY-MM-DD]
- **Batch number:** [e.g., Batch 3 of 6]
- **Bundle/repo version and build:** [bundle, engine, exact source hash]. Read them from BUILD_STAMP.txt, mamey/__init__.py and pyproject.toml.
- **Reference and current profile:** [bundle-relative guide and profile paths]. `AGENTS.md` is the operating contract. The monolith is a design reference, not a command specification.
- **Master workbook state:** [filename, SHA-256, schema, source/run scope, row counts]. A last-modified date alone does not identify current evidence.
- **Checkpoint file:** [filename, SHA-256, producer/schema, or NONE]. A session tracking file is not an engine resume checkpoint.

---

## Input files supplied

| File | Type | Strain(s) | Notes |
|---|---|---|---|
| [filename.zip] | antiSMASH ZIP | [StrainID] | [any caveats] |
| [filename.zip] | antiSMASH ZIP | [StrainID] | |
| [master_workbook.xlsx] | master workbook | all | attach current version |
| [checkpoint.csv] | session checkpoint | all | attach if continuing |

---

## Requested operation and run settings

- [ ] New extraction: `mamey_run.py run --mode gold`; select exact ZIPs, strain labels, output root, evidence mode and optional outputs.
- [ ] Existing-package workbook work: `project_merge` is a handoff label, not a CLI subcommand or `run --mode` value. Before starting, name the compatible writer or bank-and-build route. Also name the source package hashes, the workbook schema and a writable destination.

`gold` is the analysis mode.
It selects evidence extraction and ranked outputs. It does not guarantee that every
scan or channel completed, an authored interpretation, or a successful master merge.
A live-run master update is requested with `--master`; retain its separate
workbook status. Existing sealed-package banking uses the selected
`tools/ingest_package.py --merge` route and a compatible workbook build; it is
separate from re-extracting ZIPs. Do not pass a session checkpoint CSV as an
engine resume state without a matching producer/schema.

**Selected settings:** [exact command, JSON-evidence mode, capped-session choice,
brief/figure choices, whether workbook production is required, and expected
omissions]. See [runtime guidance](../docs/ASSISTANT_RUNTIME_PROFILES.md),
[your first analysis](../docs/MASTER_WALKTHROUGH.md) and
[completion states](../docs/READING_YOUR_RESULTS.md#four-different-questions-about-completion).
---

## Work-unit commitment

- **Uploaded ZIPs this batch:** [N].
- **Committed for gold runs in this batch:** [N]. List strain IDs.
- **Deferred to a follow-up batch:** [N]. List them with reasons.
- **Continue from checkpoint strain:** [StrainID or NONE].

---

## Requested outputs and their producers

Record actual produced artifacts and their current-run hashes rather than
assuming the selected mode produced this entire list.

Engine-produced per-strain outputs, subject to actual run/validation state:
- The emitted package path/ZIP, manifest, integrity files and validation receipts.
- `[strain]_3_scan_states.json`; retain every reported state and channel limitation rather than treating file presence as ten successful scans.
- Per-strain workbook and optional master workbook statuses separately; a master update is not requested unless a compatible `--master` destination is supplied.

Additional work-order outputs, only when explicitly selected and assigned a producer:
- Session checkpoint CSV row and workbook delta CSV: [producer, schema, source/run bindings and destination]. These are not promised by `run_batch` merely because the brief requests them.
- Final batch handoff ZIP, merge log and reconciliation report: [assembly/reconciliation producer, admitted package roster, before/after workbook hashes, output path and completion checks]. The engine batch runner returns per-strain results and attempts selected cohort outputs; it does not assemble this custom final ZIP.

For omitted, blocked or failed outputs, record the actual state and owner instead
of creating an empty substitute or relabeling an earlier file as current.

---

## Required validation

Before declaring batch complete:
- [ ] Copy each emitted terminal status, validator status, package-status receipt and workbook state separately. Include issue-bearing completion or validation failure exactly as emitted.
- [ ] scan_states JSON present for every strain.
- [ ] No workbook rows fabricated from accession metadata.
- [ ] Retain the producer and meaning of each status. Historical prompt vocabularies do not override the current command or receipt schema.
- [ ] All failures have exact recovery inputs listed.
- [ ] Checksums validated for every sealed package.

---

## Known issues or caveats this batch

[List any assembly problems, missing input files, or prior RECOVERY_NEEDED strains being retried.]

---

## What to do if a scan fails

1. Record the failure with the exact failure code and reason.
2. Do not substitute prose or estimates.
3. Let the authorized runner control safe continuation; stop if the failure blocks extraction or integrity. Do not bypass gates to force remaining scans.
4. Preserve the engine-generated failure/recovery artifacts and actual status. Do not manually seal or label a failed package complete; diagnose from the emitted issue and record recovery inputs.
5. List exact recovery inputs so the next session can retry.
6. Continue to the next committed strain only when the authorized runner permits safe continuation; a blocking integrity, resource or source hold remains a stop.

---

## Required closer — Next-Paths Protocol

Close under the handoff policy in `AGENTS.md`. Report completed work, evidence and unresolved holds, then the numbered next paths and the SAVE STATE line that policy asks for. A user's explicit format instruction takes precedence. Do not expand the task to populate a menu.

---

*Select current commands and profiles from the bound bundle. `AGENTS.md` is the operating contract.*
