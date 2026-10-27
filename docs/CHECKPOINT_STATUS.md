# Checkpoint status

`tools/checkpoint_status.py` writes a readable status page from a pinned list of source files. It sits beside `session_checklist.py`, `workflow_status.py`, `cohort_next_evidence_actions.py` and the Strain Master route. The earlier TB04 adapter owns Inbox snapshots. It checks an explicit pinned source roster, presents a fresh Inbox snapshot only when its source ledger still matches, and keeps a persistent goal separate from completed milestone receipts. It never manages the goal itself.

Input schema sapote.checkpoint.v1 contains sources with id, kind, path and sha256. Kinds are goal, inbox, allocation, deliverable, patch, receipt, ledger and memory. Goal, Inbox and allocation are singleton kinds. The goal input is a supplied policy or API snapshot, not live API access. Missing, unpinned, changed, malformed or over-budget sources are held. No file scan, source copy or automatic discovery is performed.

Run `python tools/checkpoint_status.py <manifest.json> --out <fresh-output-directory> [--now <offset-aware-ISO-time>]`. Output parent must exist, output must be fresh and outside the tool source tree. JSON and Markdown are written; existing output is refused. The resource snapshot uses actual free disk and logical CPUs; the latter never becomes allocated budget. Below the 15 GB floor the CLI prints observations and writes no outputs.

Inbox observations require the original receipt source path and checksum, observed_at with timezone and a caller-declared age bound (default 45 minutes). Changed or old ledgers retain reported counts but current counts become null. Native Inbox FAIL remains visible; this is not a full Strain Master audit. Pending entries request independent verification, not apply.

An optional allocation receipt needs schema sapote.scheduler-allocation.v1, host_id matching the current host, positive allocated_cores (not boolean), observed_at and optional queue text. Default maximum age is 15 minutes. It is a bound recorded allocation assertion, not live scheduler authority or validation. Missing, stale, future, wrong-host or invalid allocations leave the budget unknown; no queue capacity, task duration or dispatch is invented.

Generic QC receipts are displayed only as bound reported statuses, with their producer scope warning. Deliverable and patch byte pins prove only bytes, never readiness, acceptance or release. Use a capability card and existing producer checks for exact target/scope interpretation. Ledger and memory updates remain separate authorized routes. Nothing is accepted, applied, submitted, sent or scheduled by a checkpoint.

The human summary gives readable disk, allocation, Inbox, deliverable, patch and QC sections rather than raw JSON dumps. Optional source.surface is explicitly a manifest declaration, not adoption. Exact capability-card check states remain reported at their scope. A card target is marked TARGET_BYTES_RECHECKED only when the same artifact path and exact digest are independently present as a pinned deliverable in this invocation. An omitted or changed target does not inherit a pass. A stale Inbox count remains historical while the current count is unknown. Table cell values are escaped for Markdown display.

Next Steps can use the explicit pending actions and verified facts. It must not infer missing search outcomes, biological absence, a live runner, full visual acceptance or completion of an indefinite improvement goal from a completed batch.

Declared Inbox/allocation age limits must be finite nonnegative numbers, excluding booleans. Invalid policies raise an input error; zero minutes remains valid for an exact matching observation timestamp.

A current Inbox count additionally requires a nonnegative integer reported count, excluding booleans. Missing or invalid counts retain the raw report but keep the current count unknown and request refresh. Byte binding does not independently recount the ledger.
