# Round trip checkpoint

This read-only adapter supplements strain-master status and inbox bookkeeping. It exposes submitted-item age and pending unique IDs, preserves duplicate live-row and unledgered-directory holds, and optionally calls the existing native bookkeeping checker. Timestamps without an offset are interpreted in America/Los_Angeles; the observation records that assumption. A matching hash or a REVIEWED assertion does not accept science or authorize apply.

Run `python tools/round_trip_checkpoint.py inbox --master <master> --bundle-root <bundle> --out <new-receipt-outside-master.json>`. Optional `--now` pins an ISO timestamp for replay. The source ledger is never changed. APPLIED, RETURNED and WITHDRAWN remain distinct from SUBMITTED and ACCEPTED. A historical WITHDRAWN row with one live row is not counted as a live duplicate. Missing ledger means unknown backlog, never zero.

For a return, use `reconcile --sent-manifest <tsv> --returned <tsv> --root <returned-files-root> --out <new-external-receipt.json>`. The sent TSV has member and sha256. Return columns are item_id, sent_sha256, returned_path, returned_sha256 and decision (PENDING, REVIEWED, HOLD or SUPERSEDED). Each return is bound to its outgoing baseline and its actual current file bytes; ambiguous IDs, stale baselines, changed bytes and escaping paths hold. Not-returned items are listed; an empty return is NO_RETURNS_PENDING. No content is merged.

Resource facts include available disk bytes and logical CPUs. Allocated core budget and queue remain unavailable without a bound scheduler receipt; logical CPUs are never treated as allocation. Below the 15 GB floor the CLI refuses new receipt writes. No runner, scheduler, ledger, master content or memory is modified. Large raw inputs remain in their source homes.

Ledger and memory updates go through their owner's route; a checkpoint does not make them.

Existing strain-master verify/apply, its independent-verifier rule, and handoff_gate retain authority. The native check here is only inbox bookkeeping, not the full strain-master check. Before any import or handover, use the native route and required complete master check. It does not replace those checks.

Table bindings describe the exact single byte capture parsed for each ledger or manifest. Sources may change afterward; rebind path and hash before use. This does not promise a simultaneous filesystem snapshot.

Hexadecimal SHA-256 letter case is ignored for byte-binding comparisons. Original recorded spelling is retained; matching a digest still does not establish acceptance.

Receipt publication rejects symlink paths and uses exclusive creation, including collisions after the early existence check. Existing evidence is preserved; crash-safe publication is not claimed.
