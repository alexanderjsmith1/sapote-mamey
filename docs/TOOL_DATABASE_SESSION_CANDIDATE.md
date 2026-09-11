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
passed as parameter values. It allows at most 1000 rows and 8 MiB of source values.
`iter_rows` requires deterministic ORDER BY, uses 500-row partitions and a caller
total ceiling at most 100000. Consumers needing larger indexes must use explicit
keyset partitions with their own total ceiling; never silently truncate.
`decode_retained_json` exposes the owner's bounded compressed JSON decoder.

Admission requires an independently supplied manifest hash, supported manifest
schema, contained relative database locator, hash, size, rollback-journal header,
quick-check and foreign-key check. Optional `dependencies` entries each require
`root`, relative `path` and `sha256`. Their content is hash checked on entry and
exit. A consumer must explicitly name its dependencies; source provenance fields
are not automatically reopened. Unsupported adapters are refused.

Each query has a ten-second SQLite progress budget. A held or interrupted query
raises; it is never converted to zero records. The read-only transaction stays
open for the session. Stamps and live sidecars are checked for each query, with
full hashes checked at admission and close. Exceptions close the connection.
Ordinary input drift is detected; hostile replacement-and-restoration is outside
this guard. Sessions are single-threaded. Use a context manager or call close.

This candidate adds no evidence-index records or section-complete assertions.
Source profile metadata still requires comparison with the selected current
contract. Search provenance remains recorded evidence, not original-job locus
admission or accepted query function. Mixed hit/no-hit histories remain separate.
