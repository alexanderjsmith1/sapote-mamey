# Frozen database session candidate

`mamey.tool_database_session.FrozenDatabaseSession` extends the existing reader
owner for repeated local queries. It does not create a registry, copy a database,
admit scientific evidence or select a population. Apply after the tool database
reader and BLAST reader follow-on prerequisites listed in the patch receipt.

```python
from mamey.tool_database_session import FrozenDatabaseSession

with FrozenDatabaseSession(
    selected_root, "RELEASE_MANIFEST.json",
    expected_manifest_sha256=selected_manifest_hash,
    adapter="blastp-nr-v1",
) as source:
    page = source.inspect(full_four_part_identity, gene_order=1, view="searches")
    hits, total = source.hit_evidence(full_four_part_identity, 1, search_id,
                                      limit=25, offset=0)
```

`inspect` returns the existing reader's results object, without its outer report
wrapper. `receipt` contains source pins and verification scope. `rows` accepts
adapter-authored SELECT SQL and positional parameters; browser text must only be
passed as parameter values. It allows at most 1000 rows. The current nominal 8 MiB result budget counts byte strings by length, text by character count and other scalar values as 16 units; it is not an 8 MiB UTF-8 or Python-memory ceiling. A separate 2 MiB serialized-JSON limit applies to `inspect` and raw hit results.
`iter_rows` requires the text `ORDER BY` in the SQL, uses 500-row partitions and a caller
total ceiling at most 100000. The caller must supply a real deterministic ordering with a unique tie-breaker: the lexical check does not verify SQL semantics or uniqueness. Supply SQL without its own LIMIT/OFFSET, because the iterator appends them. Consumers needing larger indexes must use explicit
keyset partitions with their own total ceiling; never silently truncate.
`decode_retained_json` exposes the owner's bounded compressed JSON decoder.

Admission requires an independently supplied manifest hash, supported manifest
schema, contained relative database locator, hash, size, rollback-journal header,
quick-check and foreign-key check. Optional `dependencies` entries each require
`root`, relative `path` and `sha256`. Their content is hash checked on entry and
exit. A consumer must explicitly name its dependencies; source provenance fields
are not automatically reopened. Unsupported adapters are refused.

Each exposed query path arms a ten-second SQLite progress budget. A held or interrupted query
raises; it is never converted to zero records. The read-only transaction stays
open for the session. Stamps and live sidecars are checked for each query, with
full hashes checked at admission and close. Entry failures close the connection. A query exception caught inside a session does not itself close it; leave the context manager or explicitly close it. A close-time drift check may itself raise.
Ordinary input drift is detected; hostile replacement-and-restoration is outside
this guard. Sessions are single-threaded. Enter the context manager before using the API; merely constructing the object does not admit/open a database. `close()` closes an already entered session.

This candidate adds no evidence-index records or section-complete assertions.
Source profile metadata still requires comparison with the selected current
contract. Search provenance remains recorded evidence, not original-job locus
admission or accepted query function. Mixed hit/no-hit histories remain separate.

## Caller contract and recovery

The example uses placeholders: supply the exact selected root, manifest-relative path, independently obtained expected manifest hash, full strain / node-or-contig / region / BGC alias tuple, gene order and search identifier. Use [the reader contract](TOOL_DATABASE_INSPECTION.md) for supported manifests/adapters. The implementation accepts only its two declared manifest schemas and the reader's supported adapter names; it does not infer an adapter from a filename. Keep original-job evidence and selected-profile acceptance separate from a database inspection receipt.

`rows` accepts one adapter-authored statement beginning with `SELECT `, without a semicolon; caller/user values belong in parameters. It is not a general SQL editor. `iter_rows` yields earlier pages before discovering a later query or total-budget hold. Consumers must stage their own derived output and publish only after iteration and context-manager close succeed; a yielded prefix is incomplete evidence if a later check raises. No source database copy is required for these read-only inspections.

The SQLite progress callback runs periodically during SQL execution. It is not a wall-clock timeout for hashing, Python serialization, filesystem reads or an entire multi-page operation. Admission and close rehash pins; ordinary per-query checks use file stamps and sidecars. Freeze external writers during a session. A read-only transaction and pinned hashes detect the stated ordinary drift; they do not enforce scientific evidence admission or protect against hostile replacement-and-restoration.

If admission/query/close refuses, retain the error and source pins, hold the derived result and investigate the exact dependency/schema/drift or budget condition. Do not convert the refusal into an empty-hit result or bypass it by silently truncating. For raw protein hits, retain channel/search binding and pagination totals; a search identifier and recorded provenance still require separate original-job and locus acceptance.
