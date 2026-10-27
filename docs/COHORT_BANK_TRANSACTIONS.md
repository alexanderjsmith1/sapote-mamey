# Cohort-bank publication and recovery

This command merges one package into a cohort bank:

```bash
python tools/ingest_package.py --package <package> --banked-dir <separate-bank> --merge
```

It admits the package's exact workflow version. One writer lock covers the whole update: reading, validating, staging and publishing the bank stores.

Always pass `--banked-dir`. Without it, the tool uses `/data/mamey-local`.

Direct Python `merge()` calls must carry `entry['workflow_version']` or an exactly matching package manifest. A missing or malformed schema declaration is refused, even with `--force-schema`. An explicit override for a different version is recorded in the commit receipt. The override does not normalize data or change scientific metrics.

## What the writer protects

The protected set is:
- `SCHEMA_VERSION`;
- seven JSON stores: `bgc_data`, `gene_data`, `rggmci_full`, `tigrfam`, `tfbs_coupling`, `resistance_coupling` and `strains`;
- `modeb_verdicts.csv`.

`deep_data.json` is also kept and recorded when it is present. The writer validates every current store and every incoming shape before it writes any canonical store. It creates `strains.json` for a new bank. It refuses a package folder that holds `manifest.json` as a destination. Use a separate cohort bank.

## Repeat banks and duplicates

- Banking a strain ID that is already in the bank replaces that strain's rows in every store the merge writes. It is an update, not a second copy.
- A different strain ID whose BGC fingerprint matches a banked strain is refused as a likely mislabeled or duplicate upload. The fingerprint is the BGC count plus each BGC's products, length and edge status. `--allow-dup` banks it anyway and prints the match.
- An entry that lists the same BGC ID twice is refused with `BANK_INCOMING_DUPLICATE_BGC`.
- A package whose workflow version differs from the bank's `SCHEMA_VERSION` is refused unless you pass `--force-schema`.

## How an update is published

1. The writer stages full before and after images of the stores in `.ingest_transactions/<id>/`.
2. It flushes and fsyncs that content to disk.
3. It publishes a durable journal, `.ingest_pending.json`.
4. It replaces the stores one at a time.
5. It writes `.ingest_state.json`, which records the exact hash of every published store.
6. It removes the pending journal last.

This is a journaled transaction. It is **not an atomic multi-file rename**. The versioned before image stays available after later transactions. The compatibility `.bak` sibling files do not.

## How readers use the bank

The bundled bank reader commands take a shared read lock before they load data. They hold it through the whole multi-file operation. They refuse a bank with a pending journal or with a mismatch against the committed hashes.

Code that calls several reader functions should wrap them in `with mamey.bank_transaction.reader(bank): ...`. Reader scopes on main functions release their locks on return or on an exception. `tools/build_master.py` keeps its lock until the process exits. Code that holds locks explicitly can release them with `release_reader_locks()`.

The comparative bank loader checks the transaction state before it falls back to an empty legacy bank. Package readers that find no bank transaction marker keep their read-only behavior.

## Recover an interrupted bank

An interrupted bank is closed to readers on purpose. It stays closed until the maintainer picks one recovery action:

- `python tools/ingest_package.py --banked-dir <bank> --recover rollback` restores every original store from the validated before image. It also restores files that were missing before, and the prior commit receipt.
- `python tools/ingest_package.py --banked-dir <bank> --recover finish` republishes every validated after-image store and commits its receipt.

Recovery validates all paths and image hashes before it restores any store. A bank with no pending journal refuses recovery with `BANK_NO_PENDING_RECOVERY`. `finish` does not validate or reseal a bank in general.

If a recovery is itself interrupted, the pending marker stays. Run the same action again. Never remove the marker by hand. Never copy single `.bak` files into a bank and call it complete. Old recovery folders are kept. Removing them is a separate owner decision.

## Reader and diagnostic limits

A reader can create the `.ingest.lock` file in an older bank that has none. This file is lock metadata, not a change to a protected store. It is still a write to disk.

An older bank without `.ingest_state.json` returns `LEGACY_UNRECEIPTED`. Reading it does not show that the stores match committed hashes. Keep the original files unchanged, and record the actual bank state before you use a result.

`tools/ingest_package.py --validate <strain> --package <package> --banked-dir <bank>` prints comparisons between the package entry and the bank. It can print DIFF and still exit with zero. Read every comparison; an exit of zero does not mean the bank matches. Python code that calls this check holds a reader lock. Release it through the code that took it when you are done.

Building an entry without `--merge` does not publish canonical stores. `--out` still writes an entry file when you give it. A transaction refused before the pending journal is published can still leave private staging images or `.bak` files. So a failed attempt may still have written files. Keep the diagnostics and check the pending and commit state.

`tools/build_deep_data.py`, `tools/build_finer_from_gbk.py` and the empty-bank setup in `tools/mamey_intake.py` use the same journaled writer. Intake releases its read locks before it starts a child banking process. Other derived reader outputs stay separate from the protected core stores.

## Platform and trust limits

Locks use POSIX `flock` or Windows `msvcrt` byte locking. A host with neither refuses unlocked access.

On POSIX, publication flushes both files and folders. On Windows it flushes file handles only, because folder fsync is not available. So no matching guarantee is made for sudden power loss on Windows.

The protocol needs all of these:
- tools that follow the protocol;
- stable source packages;
- a local filesystem that supports these locks;
- no outside writer that skips the protocol.

These receipts show that publication was coherent. They are not scientific validation or schema normalization. Nothing here seals a package or makes a release.
