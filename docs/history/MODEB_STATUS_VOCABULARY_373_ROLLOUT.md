> **Historical page.** Replaced by [the status vocabulary page](../MODEB_STATUS_VOCABULARY_RATIFIED_v9_7_373.md). It records how the mapping was rolled out in the .373 and .374 cuts; it is not a statement about the current bundle.

# Mode B status vocabulary: .373 rollout

## What .373 implemented and deferred
- **Implemented in .373 (engine 1.9.126):** the legacy token is honoured as an alias-trigger by the
  finished-profile check wired in `mamey/authored_verify.py` (B1) — a card carrying either
  `FINISHED_FULL48_CURRENT_EVIDENCE` or the legacy `FINISHED_CURRENT_EVIDENCE` activates the
  publication gate. The mechanical ceiling `EVIDENCE_MATRIX_VALIDATED` is unchanged.
- **Deferred to .374 (engine-bump):** the full Full48 named-profiles implementation
  (schema/emitter/gates emitting `document_state` + `evidence_state` as first-class fields) — it
  changes emitted output and warrants its own bump. Tracked with the sequence-first coded
  receipt-binding enforcement, which waits on the BLASTp-lane store schema migration
  (`hits` lacks `query_hash`/`result_job_receipt` columns).
