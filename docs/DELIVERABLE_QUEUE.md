# Deliverable queue and availability checks

Request **Sapote-Mamey deliverable queue** to automate the requested deterministic post-extraction steps across explicit strain IDs. It is implemented by `mamey/deliverable_queue.py`; it does not author or review Sapote judgment. Use preserved working copies of the packages and a fresh output root because the queue can ingest evidence into packages before a gate blocks further work.

## Availability is discovery, not a run gate

```bash
python mamey_run.py deliverables list --json
python mamey_run.py deliverables availability --package /absolute/review/package --json
```

The [generated menu](DELIVERABLE_MENU.md) names registered outcomes. Availability checks read local presence and return typed `state`, `missing` and `notes`. The CLI returns zero even when required inputs are missing; inspect those fields rather than using exit status as a READY gate.

The `sealed_package` probe only checks for a manifest file, not valid JSON, checksum integrity or a seal. The locus probe counts three spaced separators and looks for a BGC token; it does not bind all four components to one inventory record. Figure-stack availability checks Matplotlib discovery, not every renderer dependency. Explicitly validate requested package, identity, inputs and tool requirements before execution.

`deliverables render --out PATH` overwrites that Markdown destination and does not create its parent. This rendering subcommand has different write behavior from read-only availability. Generated menu maintenance belongs to the registry and its renderer; do not independently edit generated menu content.

## Run an explicit queue

```bash
python mamey_run.py deliverable-queue isolate-001 isolate-002 \
  --runs-dir /absolute/review/runs \
  --out-root /absolute/deliverables/queue_run
```

The source expects `<runs-dir>/<strain>/package`. Supply a nonempty, unique list of single local strain-directory names; the current CLI returns 1 for an empty request rather than reporting successful completion. The queue joins these strings into source and output paths without validating basename containment, so independently verify each resolved package stays under the intended runs root and each output stays under the intended output root. Duplicate requests share one ledger key and can inflate requested/status counts. Preserve the intended roster rather than interpreting the summary total as unique strains. Keep paths and original sources in your checkpoint. Read [stored BLASTp evidence](ONLINE_BLASTP_PROTOCOL.md) before its automatic local-trove discovery and channel ingestion. This queue does not authorize live sequence submission.

For each strain it creates `<out-root>/<strain>/sapote`, attempts stored-channel ingestion, evaluates the BLASTp gate, then dispatches Mode B templates, lead pages, reference-dark, Good Guesses, AF dossier and compile-report through the bound runner. Templates are first emitted inside the package and then copied to the deliverable folder. The queue does not expose or forward `--contract`: the child emitter uses its `full48` default. Shared cross-source flags include current50-specific rescue inputs, but accepting their syntax does not select that profile. `--rescue-locus-inventory` or `--rescue-gene-adjudication-tsv` requires current50 and can cause the queued card step to fail; `--gap-rescue-dir` does not activate current50's rescue sections under full48. Use the explicitly selected [profile/emitter route](MODEB_PROFILE_MATRIX.md) when current50 output is required, and do not treat this queue as a current50 pipeline.

After dispatch, the queue copies every `.md` already in `package/mode_b_templates`, even when the current card subprocess failed. Existing stale templates can therefore appear beside an incomplete ledger record. Reconcile each copied file's producing contract/source/attempt with the requested run; its copied count is not proof of successful current emission. A failed step does not roll back earlier writes; later steps still run. Optional `--activity-table` changes dossier input, not locus-level activity authority.

Inspect every requested artifact and the per-strain `steps`, `failed_steps`, `ingested`, `missing`, `status` and `narratives` records. `DETERMINISTIC_DONE` means all recorded subprocess return codes were zero; it does not inspect every artifact or prove biological completeness. `PENDING_JUDGMENT` remains separate. The current CLI returns 1 when the summary has deterministic-incomplete steps, BLASTp-blocked strains, missing packages, an empty request, or a deterministic-done count different from the requested total. Exit 0 requires a nonempty requested total fully counted as deterministic-done; it still does not independently verify each artifact or child soft-success state. A subprocess can also return zero while its own requested output is skipped or held. Each child has a fixed 1,800-second timeout; a caught launch/timeout exception becomes synthetic `rc99`. The queue retains only the last line of stdout, or stderr when stdout is empty, and truncates failure text to 60 characters in `steps`. Earlier diagnostic lines and stderr accompanying nonempty stdout are not retained by the ledger. Preserve the terminal invocation/status and inspect the owning command's actual outputs and source receipts; a short step string is not a complete execution log. An exception during template copying or ledger publication can abort the queue before recording the current strain, after prior package/output mutations have occurred.

## Resume and recovery

The default ledger is `<out-root>/DELIVERABLE_QUEUE_LEDGER.json`. `--ledger` selects another path whose parent must exist. A fixed `.tmp` sibling is written and replaced after each processed strain; avoid concurrent queue writers sharing a ledger or output root. With resume enabled, malformed JSON raises `DELIVERABLE_QUEUE_LEDGER_INVALID_JSON`; a non-object ledger or any non-object strain record raises `DELIVERABLE_QUEUE_LEDGER_INVALID_SHAPE`. The current queue refuses these ledgers before strain processing instead of resetting them and rerunning prior work. The output root is created before ledger admission, so refusal is not a guarantee of zero filesystem changes. Preserve the damaged ledger and prior package/output state for owner-led recovery.

Resume requires a `DETERMINISTIC_DONE` record, matching `source_args_sha256`, and the current package/output/context binding introduced in .454. That binding hashes the package and delivered `sapote` tree paths/bytes (excluding `__pycache__`), absolute runs/output roots, and the activity-table path and bytes when it is a readable existing file. A changed binding, or an older DONE record lacking it, causes processing again; the queue does not simply skip on matching argument strings. Preserve working packages and use a fresh ledger/output root for a changed task because reprocessing can mutate them.

These are implemented resume comparisons, not independent artifact validation or an immutable source snapshot. The source-argument hash still binds argument strings rather than the bytes of every external file they name; tool/code/environment identity is not included. Tree hashing follows the files selected by `rglob`/`is_file` and supplies no separate containment or concurrent-writer lock. Hashes are captured after processing and compared later; a matching skip does not prove the earlier child outputs were scientifically valid or correctly bound throughout execution. Retain exact source/tool identities and child receipts separately (`mamey/deliverable_queue.py`).

There is no automatic empty-ledger repair on the current resume path. Inaccessible ledger bytes can raise, and a missing ledger parent can fail publication after strain/package work has already occurred. Preserve diagnostics and prior state; no complete rollback is supplied. `--no-resume` bypasses reading the old ledger, reprocesses records and can overwrite that ledger/output paths. Do not use it to conceal a corrupt-history hold. For a separately authorized replacement, select a fresh ledger/output root and preserved working packages with explicit supersession.

A queue checkpoint should record exact input/output hashes, requested strain count, all per-strain states, artifacts actually present, remaining judgment and the next bounded recovery action. A successful queue is neither owner acceptance nor release approval.
