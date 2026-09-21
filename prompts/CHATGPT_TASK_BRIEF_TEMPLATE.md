> **Scope and precedence:** Apply this workflow only to the user's selected operation and named
> profile. `AGENTS.md` and `docs/ASSISTANT_GOVERNANCE.md` govern permissions, task scope,
> inspection-only work and conversational output. Package presence is not execution authority.
> Historical section counts, role assignments and examples below cannot replace a current profile.
> When instructions disagree, preserve evidence, identify the conflict, and do not expand authority.

# Sapote-Mamey / Mamey Task Brief Template — v9.7.435

Fill this template before handing a batch to ChatGPT or another Mamey-tier runner.  
Remove all square-bracket placeholders before submitting.

---

## Context

- **Date:** [YYYY-MM-DD]
- **Batch number:** [e.g., Batch 3 of 6]
- **Bundle/repo version:** [e.g., sapote-mamey-v9.4]
- **Active monolith:** SAPOTE_MAMEY_BUNDLE_MONOLITH
- **Master workbook state:** [filename + last-modified date + row count]
- **Checkpoint file:** [filename or NONE — if present, attach it]

---

## Input files supplied

| File | Type | Strain(s) | Notes |
|---|---|---|---|
| [filename.zip] | antiSMASH ZIP | [StrainID] | [any caveats] |
| [filename.zip] | antiSMASH ZIP | [StrainID] | |
| [master_workbook.xlsx] | master workbook | all | attach current version |
| [checkpoint.csv] | session checkpoint | all | attach if continuing |

---

## Requested run mode

> **v9.7.374 correction:** `smoke` was removed at v9.7.161 (`mamey run --mode` now accepts only
> `standard`/`gold`, and `standard` is a deprecated alias of `gold`) — it is not a selectable option
> today. `gold` is the only analysis mode.

- [ ] `gold` — all ten scans, sealed package, workbook merge (the only analysis mode)
- [ ] `project_merge` — merge existing sealed packages into workbook; no new extraction

---

## Work-unit commitment

- **Uploaded ZIPs this batch:** [N]
- **Committed for gold runs this session:** [N] — list strain IDs
- **Deferred (need follow-up session):** [N] — list with reasons
- **Continue from checkpoint strain:** [StrainID or NONE]

---

## Required outputs — every committed strain

Per-strain (gold mode):
- Sealed package ZIP with ten scan files, manifest, and SHA-256 checksums
- Updated scan_states JSON
- Checkpoint CSV row (appended)
- Workbook delta CSV (rows ready for merge)

End-of-batch:
- Updated master workbook (with merge log)
- Final handoff ZIP containing all per-strain packages + updated workbook + checkpoint

---

## Required validation

Before declaring batch complete:
- [ ] Every committed strain has package_status = MAMEY_COMPLETE or MAMEY_FAILED with reason
- [ ] scan_states JSON present for every strain
- [ ] No workbook rows fabricated from accession metadata
- [ ] Package statuses use approved vocabulary only (see §8 of Mamey execution prompt)
- [ ] All failures have exact recovery inputs listed
- [ ] Checksums validated for every sealed package

---

## Known issues or caveats this batch

[List any assembly problems, missing input files, or prior RECOVERY_NEEDED strains being retried]

---

## What to do if a scan fails

1. Record the failure with the exact failure code and reason.
2. Do not substitute prose or estimates.
3. Continue with remaining scans for the same strain.
4. Seal the package as `MAMEY_FAILED` with the failed scan listed.
5. List exact recovery inputs so the next session can retry.
6. Continue to the next committed strain.

---

## Required closer — Next-Paths Protocol

Report completed work, evidence, unresolved holds and the next bounded action when useful. Do not expand the task to populate a menu.

---

*Sapote-Mamey Bundle v9.7.428 | Active controller: docs/SAPOTE_MAMEY_BUNDLE_MONOLITH.md*
