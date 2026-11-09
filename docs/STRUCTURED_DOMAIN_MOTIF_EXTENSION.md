# Structured-domain/motif sidecar: source and receipt boundary

This page is the run guide. The [HTML overview](STRUCTURED_DOMAIN_MOTIF_EXTENSION.html) is a short summary; when the two differ, follow this page.

`mamey/structured_domain_motif_extension.py` builds a SQLite sidecar that indexes saved structured exports from Mamey packages. Use it when you already have a base database and those exports (see "Inputs you need first"). For a separately curated exact-reference panel, use [the reference-BGC validator](REFERENCE_BGC_STRUCTURAL_VALIDATOR.md) instead.

It indexes exports. It does not read original antiSMASH JSON or run a new analysis. Export hashes bind file bytes. Row hashes bind canonical JSON content, not whitespace or key order. A source, locus, gene or protein binding does not validate biochemical function, product, activity, novelty or scientific acceptance.

## Inputs you need first

- **Package exports.** Each package folder holds `manifest.json` and a file ending `_3_antismash_structured.json`. Next to them the tool also reads `<prefix>_gene_context.jsonl`, `<prefix>_proteins.faa` and `<prefix>_AntiSMASH_Evidence_Parse.json`, where `<prefix>` is the structured file's name before `_3_antismash_structured.json`.
- **Base database.** A SQLite file from a cohort evidence build done outside this bundle. No tool here builds it. The module reads the tables `source`, `locus`, `gene`, `feature`, `section_profile` and `section_relevance`. A file without them is refused with the code `no such table: source` (or the first missing table). If you do not have such a database, you cannot run this tool.
- **Inventory.** A JSON list with one row per package. Each row needs five keys: `package` (the name), `manifest` (relative path to `manifest.json`), `structured_path` (relative path to the structured export), and the hashes `manifest_sha256` and `structured_sha256`. Get each hash with `shasum -a 256 <file>` on macOS or `sha256sum <file>` on Linux. A wrong hash stops the run.
- **Pins.** The SHA-256 of the inventory file and of the base database, for `--inventory-pin` and `--base-pin`.

## Run it

The sidecar has no `mamey_run.py` subcommand. Run the module from the bundle root, because `python -m mamey...` finds the package only from there. Every flag in the first group is required.

```bash
python -m mamey.structured_domain_motif_extension \
  --inventory inventory.json --inventory-pin <sha256-of-inventory.json> \
  --source-root /abs/path/to/packages \
  --base base.sqlite --base-pin <sha256-of-base.sqlite> \
  --out /abs/path/to/allowed/sidecar.sqlite \
  --allowed-root /abs/path/to/allowed \
  --receipt /abs/path/to/allowed/sidecar_receipt.json
```

| Flag | Meaning |
|---|---|
| `--inventory` | JSON list of package rows with the five keys above. A `package` name uses letters, digits, `_`, `.` and `-` only. The two paths are under `--source-root`. |
| `--inventory-pin`, `--base-pin` | Exact SHA-256 of the inventory and base database. A mismatch stops the run. |
| `--source-root` | Folder that holds the packages. It must not be a symlink. |
| `--base` | The pinned base database. Its bytes are checked before and after the build. |
| `--out` | The sidecar database to create. It must sit inside `--allowed-root`. |
| `--allowed-root` | The folder that contains `--out` and `--receipt`. |
| `--receipt` | Where the JSON receipt is written. |
| `--resume` | Continue a partial build (see below). |
| `--selection`, `--archive-root`, `--archive-map` | Optional: choose a subset of packages, or map packages to verified source archives. `--archive-map` needs `--archive-root`. |

Success is exit 0, the database at `--out`, and the receipt. A refusal for a size, time, path, hash-pin or database reason prints a JSON line such as `{"status": "REFUSED_OR_CHECKPOINT_REQUIRED", "code": "..."}` and exits 2. Exit 2 does not say the output is empty. It means the run was refused or needs a checkpoint decision. One kind of bad input is not refused this way: an inventory row with a missing key ends in a Python `KeyError` traceback and exit 1.

## What the tool checks

It checks each export's hash, schema, table counts and consumed-file checksums. Missing input or a checksum conflict is a hold. A file that is not listed in a package's checksums can be hash-captured, which is weaker than a full checksum pass. Archive, manifest, geometry, roster and protein holds stay typed.

Unsupported motifs and predictions stay in the sidecar only. Do not treat them as compatible domain evidence because they are indexed.

## Limits

- 128 packages per inventory.
- 64 MiB per export or sidecar file.
- 100,000 observations per package.
- A 900-second timer, checked between packages. It is not a hard stop inside one package.

Each package commits on its own. A budget, parse or output failure can leave a partial database with the packages already committed. Keep the partial output and the original inventory.

## Resume

An existing output database needs `--resume`. Resume checks the base hash and the inventory content again, rechecks completed partitions and verified archives, and can return the state `RESUME_COMPLETE_OUTPUT_UNCHANGED` when nothing needed redoing. Resume with unchanged pins. Do not delete evidence to get past a hold.

## Receipt rules

The receipt path is checked before the database is built. It must be inside `--allowed-root`, must not be a symlink, and must not be the output database, its journal, WAL or SHM file, the base database, the inventory, the archive map, any inventory `manifest` or `structured_path` file, or any archive the map names. It must also not sit inside `--source-root` or `--archive-root`. Any of those is `RECEIPT_PATH_COLLISION`. The same source-tree rule applies to `--out`: a database path that is a consumed file or sits inside `--source-root` or `--archive-root` is `OUTPUT_PATH_COLLISION`. The other package files the tool reads (`_gene_context.jsonl`, `_proteins.faa`, `_AntiSMASH_Evidence_Parse.json`) sit in the package folder under `--source-root`, so the source-tree rule covers them. An existing receipt is refused unless you pass `--resume`.

The receipt is written to a temporary file and renamed. The database and receipt are not one transaction, so a receipt write failure after a good build leaves a database without a receipt. The receipt does not carry its own hash or a full code and parameter pin. Record the exit status, the database, receipt, inventory, code and parameter hashes yourself. "All saved packages" is not the same as a scientifically accepted cohort.

## Hold codes you may see

| Code or state | Meaning |
|---|---|
| `INVENTORY_PIN_HOLD` | The inventory's hash does not match `--inventory-pin`. |
| `PACKAGE_LOCATOR_HOLD` | A package name has characters outside the allowed set. |
| `PACKAGE_COUNT_LIMIT`, `PACKAGE_ROW_LIMIT` | The inventory or a package exceeds the limits above. |
| `SOURCE_EXPORT_SIZE_LIMIT`, `SIDECAR_STORAGE_LIMIT` | An export or the sidecar is over 64 MiB. |
| `RUNTIME_BUDGET_CHECKPOINT` | The 900-second timer ran out between packages. Resume. |
| `RECEIPT_PATH_COLLISION` | The receipt path equals a protected file. |
| `ARCHIVE_ROOT_REQUIRED` | `--archive-map` was given without `--archive-root`. |
| `EXPORTED_EMPTY_NOT_BIOLOGICAL_ABSENCE` | A table state: the export had no rows. It is not evidence the feature is absent. |
| `RESUME_COMPLETE_OUTPUT_UNCHANGED` | Resume found the build already complete. |

## For developers: reading the sidecar

There is no command-line reader. A callback takes two already-open, caller-pinned read-only SQLite connections (sidecar and base). It rechecks file hashes, the section count, the profile hash and requirement parity, and limits results to 1 to 500 rows. Raw rows also need an explicit package root and verified export and raw-row hashes. Integration with the shared reader is separate.

A gene-first evidence index needs a complete locus and compatible domain observations. `BOUND` means the package-locus geometry and gene-protein link were checked. It does not validate each domain or motif interval or its biological meaning. `EXACT_BASE_FEATURE_PROVENANCE_MATCH` also requires the feature type, coordinates, full qualifiers and gene set to agree with the pinned base. Keep `strain / full node-or-contig / region / BGC alias` for every locus. Paging is over source rows, not genes. `READ_ONLY_CANDIDATE_INSPECTION` records scientific admission as `NOT_PERFORMED`. Section parity does not validate an authored card. Record sidecar builds, callbacks, dataset changes and rendering as separate actions with their own receipts.
