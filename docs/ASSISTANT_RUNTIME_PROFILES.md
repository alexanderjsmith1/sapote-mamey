# Separate assistant guidance from runtime limits

Early Sapote–Mamey workflows were developed in hosted chat interfaces before migration to local
coding agents. Repeated handoffs, capped runs and explicit completion menus come from that
context and should be evaluated in it. A constraint that helped
one environment is not automatically suitable as a universal rule for every later environment.

This is operational guidance, not a new configuration feature. No profile-switching command or
automatic hardware tuner is introduced by this document.

## Three independent decisions

| Decision | Evidence to use | Do not infer from |
|---|---|---|
| What the assistant should do | Current user request, selected output/profile and evidence standards | The presence of data or a historical system prompt |
| What execution is permitted | Workspace roots, network/disclosure scope, resource authorization | Model name, an old approval phrase or a handoff command |
| What execution is feasible | Python/dependencies, input size, RAM, process budget, measured timings | Subscription tier, model capability or the word “full” |

A model can differ in how well it follows instructions, handles long context or writes code.
The Python process still uses the code's parser limits and its actual host environment. A different
model does not change a hardcoded JSON byte cap. More CPU cores do not by themselves remove an
in-memory parser's RAM demand or make a sequential operation parallel.

## Choose settings from observed conditions

| Observed environment condition | Suitable adaptation | Keep explicit |
|---|---|---|
| Short process/session lifetime | Bounded work units, checkpoints, resumable logs | What evidence/output the shortened run omits |
| Ephemeral filesystem | Export recoverable artifacts before the environment expires | Where the handoff is saved and how inputs are rebound |
| Persistent local workspace | Reuse verified environment and prior receipts | User scope, path permissions and stale-source checks |
| Constrained RAM | Streaming/bounded parsing or a smaller selected task | Record/byte caps, truncation and unknown channel completeness |
| User-approved larger local budget | A separately reviewed cap/resource adjustment | Measured cost, test cases and unchanged versus altered scientific behavior |
| Useful next-step coaching requested | Offer grounded options suited to the user | User preference rather than a universal menu quota |

Do not assume a browser-hosted session is always ephemeral, or that a local session has unlimited
resources. Inspect the actual environment. Defaults should describe their applicability, side
effects and escape conditions; explicit user choices remain authoritative within host constraints.

## What to record with a benchmark or walkthrough

Record software commit and uncommitted patch identity, interpreter and dependencies, input hash
and uncompressed JSON size, parser mode, cap values, elapsed time, measured peak memory when
available, exit status, evidence-visibility receipt and unresolved warnings. CPU/thread settings
matter only for components that use them; do not claim a core-count speedup without a measurement.

Do not compare a held parse with an admitted parse as though they did the same amount of work.
One successful strain is a useful acceptance example, not a universal performance guarantee.
When raising a cap, preserve the earlier held/truncated attempt and test the size boundary too.

## Assistant-session accounting

Use `tools/session_cost_audit.py` for recorded Claude Code transcript usage, separately from benchmark timings. Select the intended transcript directory explicitly with `--proj`; the default is derived from `CLAUDE_PROJECT_DIR` or the current working directory. Supply `--since` for a common accounting window and retain the full input-log identities and hashes. The tool sums recorded input, cache-write, cache-read and output token fields; it does not compute currency charges, native CPU/RAM usage or elapsed job time.

Check the selection scope before comparing sessions. Only top-level `*.jsonl` files in that directory are considered, ordered by file modification time. The tool then audits at most the newest 25 files, or 200 after a `--session`/`--color` filter, before ranking by token total. `--session` is a filename substring match; `--color` is a heuristic based on directory names associated with `STATE.md` references. Neither supplies an authoritative session roster. No matching file exits 1; invalid `--since` exits 2. Successful exit means the selected logs were processed, not that every session or record was admitted. Invalid JSON lines are silently skipped; with a time window, records with absent/unparseable timestamps are omitted. The tool does not report those omission counts or deduplicate repeated record identities.

Interpret the output units precisely. `turns` counts assistant records with nonempty `message.usage`, and absent usage fields contribute zero; it is not the full conversational-turn count. `sub` counts recorded `Agent`/`Task` tool-use blocks, while `files` counts distinct path strings in `Write`/`Edit`/`NotebookEdit` calls; neither establishes completed work or delivered artifacts. Tool-result sizes count characters in strings or serialized JSON, despite the internal `result_bytes` name. A result whose tool-use record lies before the selected window can be assigned to `?`. The displayed `age_d` spans parseable timestamps across the whole log, even when token totals use `--since`; it is not the selected window's duration or active runtime.

Select a new TSV destination outside the transcript evidence. The writer directly replaces an existing output and does not reject input/output aliases, so a TSV path can overwrite a selected log after reading it. Preserve original logs and partial outputs; retry to a fresh path. Keep the console window statement, command, selection roster and source hashes with any `--tsv` output. The TSV contains token/count summaries but omits the window, log span, skipped-record coverage and separate fresh-input token column, and its session field is only the first eight filename characters. Distinct full session identifiers can therefore have the same exported prefix. `tok_per_turn` is integer-truncated in TSV; the console rounds its display. Compare bound full identifiers and explicitly stated denominators, and do not treat path-count ratios as cost per verified deliverable (`tools/session_cost_audit.py:26–27, 30–132, 142–232`).

## Migration priorities

Keep truthful evidence receipts, immutable inputs, scoped identities, resumability and resource
preflights. Retire unconditional model identities, repeated installs, rigid response rituals and
instructions that suppress legitimate audit findings. Where an old behavior is still helpful,
make it an explicit task or environment choice rather than deleting the capability.
