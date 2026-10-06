# Cohort-bank publication and recovery

`tools/ingest_package.py --package <package> --banked-dir <separate-bank> --merge` admits the exact package workflow version under the same writer lock that reads, validates, stages and publishes its bank stores. Direct Python `merge()` calls must carry `entry['workflow_version']` or an exact matching package manifest. Missing or malformed schema declarations are refused even with `--force-schema`. An explicit divergent-version override is recorded in the commit receipt; it does not normalize data or change scientific metrics.

The protected set comprises `SCHEMA_VERSION`, seven JSON stores (`bgc_data`, `gene_data`, `rggmci_full`, `tigrfam`, `tfbs_coupling`, `resistance_coupling`, `strains`) and `modeb_verdicts.csv`; `deep_data.json` is retained and bound when present. All current stores and incoming shapes are validated before canonical store writes. `strains.json` is created for fresh banks. A package directory containing `manifest.json` is refused as a writer destination; use a separate cohort bank.

Each update stages complete before/after images in `.ingest_transactions/<id>/`. File content is flushed and fsynced before a durable `.ingest_pending.json` journal is published. Stores are replaced individually. This is a journaled transaction, **not an atomic multi-file rename**. After all stores are published, `.ingest_state.json` binds their exact hashes; the pending marker is removed last. The versioned before image remains available even after later transactions, unlike the compatibility `.bak` siblings.

Bundled bank reader CLIs take a cooperating read lock before loading data and hold it through their multi-file operation. They refuse a pending journal or a committed hash mismatch. Embeddings that call multiple functions should use `with mamey.bank_transaction.reader(bank): ...`; Main-function reader scopes release their locks on return or exception. The historical top-level `build_master.py` retains its lock through process exit; explicit embedding holds can be released with `release_reader_locks()`. The comparative bank loader checks transactional state before its legacy empty-shell fallback. Package readers without a bank transaction marker preserve their read-only behavior.

An interrupted bank is deliberately unavailable to readers until the owner selects one bounded recovery action:

- `python tools/ingest_package.py --banked-dir <bank> --recover rollback` restores every original store, original missing-file state and prior commit receipt from the validated before image.
- `python tools/ingest_package.py --banked-dir <bank> --recover finish` republishes every validated after-image store and commits its receipt.

Recovery validates all paths and image hashes before restoring any store. A recovery interrupted midway leaves the pending marker; the same explicit action can be retried. Never remove the marker manually or copy individual `.bak` files into a bank and call it complete. Historical recovery folders are retained; cleanup requires a separate owner decision.

`build_deep_data.py`, `build_finer_from_gbk.py` and intake's empty initialization also use the journaled writer boundary. Intake releases read locks before launching a child banker. Other derived reader outputs remain separate from protected core stores.

Locks use POSIX `flock` or Windows `msvcrt` byte locking; a host without either refuses unlocked access. POSIX publication flushes files and directories. Windows flushes file handles; directory fsync is unavailable, so no equivalent sudden-power-loss durability claim is made. Cooperating tools, stable source packages, a local filesystem supporting these locks, and no external writer bypassing the protocol are required. These receipts attest publication coherence, not scientific validation or schema normalization. No package seal or release is performed.
