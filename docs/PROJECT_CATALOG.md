# Portable project catalog and private handoff

Request **Sapote-Mamey project catalog** for hash-bound package locations, or **private project handoff** for the separate multi-package archive. Both are operated by `tools/project_catalog.py` with the selected source environment. They are distinct from the per-package `mamey_run.py handoff` builder and the pointer-first [project data home](PROJECT_DATA_HOME.md).

## Register and verify package locations

```bash
python tools/project_catalog.py register \
  --project-root /absolute/project \
  --package /absolute/project/runs/strain/package
python tools/project_catalog.py verify --project-root /absolute/project
```

The package must be below the chosen root and contain a JSON-object `manifest.json` with a strain identifier. Register creates or updates `<project-root>/lab_quest_outputs/project_catalog.json`, rebinding a matching logical package path to its current manifest hash. Keep a prior catalog when its earlier binding is required.

Even `verify` initializes the catalog: a nonexistent project root can be created, and a missing catalog becomes an empty one. A successful empty report means zero registered entries; it does not prove the workspace contains no packages or that every run was inventoried. Verify an explicitly known root/catalog and compare its entry count to the requested inventory.

Verification checks package locators and recorded manifest hashes. It does not validate every package file, recompute engine gates or accept biological interpretation. Changing a CSV while leaving the manifest unchanged can escape this catalog check. Run the source-compatible package validator on a preserved review copy when package integrity is required.

## Export a private archive

```bash
python tools/project_catalog.py export-private \
  --project-root /absolute/project \
  --out /absolute/private_handoffs/new_project_handoff.zip
```

The export carries all regular files discovered below each catalogued package, and the catalog, plus an optional current portfolio binding and its named config/registry. Package traversal has no extension, hidden-file, cache or manifest-file-inventory filter. Review the actual package contents before transfer: extra files inside those directories travel too. Files outside those package directories are omitted unless they are the catalog or the named portfolio files; a portfolio registry's referenced evidence files are not automatically followed into the archive. This archive is not a complete project backup. It refuses symbolic links inside package file traversal, stale manifest/portfolio hashes and absolute-locator-shaped strings in package manifests. Preserve sealed evidence and use a governed relocation record when such a locator is refused; do not silently rewrite the original manifest.

Output must be outside the project root. The exporter creates its parent, opens the destination directly in write mode and can truncate/replace an existing file; it does not use the public archive transaction's no-clobber commit. Use a fresh destination and preserve earlier archives. An interrupted or failed write can leave a partial ZIP. Export hashes source files into a manifest but does not reopen its completed archive for an independent byte check. Keep the catalog, package files and optional portfolio files unchanged throughout export: the hash pass and archive-byte read are separate, with no snapshot lock or final source recheck. A successful export exit can therefore still produce an archive that a subsequent import refuses if files changed during writing. Preserve the candidate archive, record its SHA-256 separately, and confirm transfer into a fresh empty review root before treating it as a usable handoff. Record the sender and expected archive SHA-256 through a trusted separate channel; the archive's own CRC and internal hashes do not authenticate its origin.

This archive is explicitly `PRIVATE_PROJECT_HANDOFF_ONLY`. No public export or redaction option exists here. A package's recorded PUBLIC field does not authorize disclosing the whole private archive.

## Import into an empty root

```bash
python tools/project_catalog.py import-private \
  --project-root /absolute/new_project \
  --input /absolute/private_handoffs/new_project_handoff.zip
```

The importer requires an empty destination; it can create the root before archive checks. It checks CRC, supported handoff schema/class, declared member paths, bytes and hashes in a temporary sibling stage, then copies staged files into the root. Final catalog and optional portfolio verification happen after copying. A later failure or interrupted copy can therefore leave an occupied or partial destination that a retry refuses. Preserve the failed-root evidence and use a fresh empty root for recovery.

Capture stdout, stderr and exit status. The standalone front door lets library exceptions propagate, so refusal can be a traceback rather than a neat FAIL receipt. Inspect actual root/archive state before assuming a failure produced no writes. Successful import checks the extracted declared bytes and catalog provenance, not scientific acceptance. In this implementation, the member comparison uses sets and the declared inventory is converted to a dictionary keyed by path; duplicate ZIP member names or duplicate inventory paths are not explicitly rejected. Require a handoff from a known producer with a separately confirmed archive SHA-256, and retain the original archive. Import success does not certify that every original ZIP entry was uniquely inventoried and verified.

## Portfolio bindings have a separate schema

`tools/validate_portfolio_config.py --project-root ROOT --config RELATIVE_CONFIG` reads a `sapote_project_portfolio_v1` JSON file whose `project_registry` points to one contained registry. The default check does not write a binding. Adding `--write-binding` creates or replaces `lab_quest_outputs/portfolio_binding.json` with config/registry hashes and availability metadata; preserve an earlier receipt and avoid concurrent writers to that fixed path.

This project-registry portfolio is distinct from the extraction `sapote_privacy_profile_v1` policy and its separate evidence TSV. A valid portfolio does not override extraction release assignment. See [Lab Quest](LAB_QUEST.md) for the current authority boundary and [portable privacy and evidence](PORTABLE_STRAIN_PRIVACY_AND_EVIDENCE.md) for that intake schema.

## Binding inputs, writes and recovery

Run the read-only binding check first, from the selected bundle environment:

```bash
python tools/validate_portfolio_config.py \
  --project-root /absolute/project \
  --config config/portfolio.json
```

The existing config must declare `schema_version: sapote_project_portfolio_v1` and a `project_registry` relative logical path to an existing regular JSON file below that project root. Input containment is checked after resolving symlinks; outside-root targets and `..` registry paths are refused. Use a nonblank relative file path, not `.`. An absolute config path inside the root is accepted by this implementation, although its help advertises a root-relative path (`mamey/portfolio_config.py:47–68,120–149`). The default invocation produces stdout JSON without writing a receipt.

Adding `--write-binding` writes the fixed `lab_quest_outputs/portfolio_binding.json`, replacing an existing receipt through a fixed `.tmp` sibling. Preserve prior receipts and avoid concurrent writers. The writer revalidates the root directory but does not check final output containment or sealed-package state: a symlinked `lab_quest_outputs` directory can redirect writes outside the selected root. Use an explicitly authorized unsealed project root with an ordinary output directory; do not assume the input-containment check protects output writes. On failure inspect both receipt and `.tmp` before retrying (`mamey/portfolio_config.py:152–160`).

Keep config and registry bytes unchanged throughout validation. The binding hashes are computed after separate parse/load reads; there is no immutable snapshot or final consistency check. A concurrent edit can pair earlier availability metadata with a later registry hash. Preserve the input bytes used for review, record their hashes, compare the receipt to those exact files and rerun against unchanged inputs if uncertain. A binding receipt reports declared inventory and workflow states; it does not verify every referenced evidence file or scientific claim. See [project-registry validation limits](PORTABLE_STRAIN_PRIVACY_AND_EVIDENCE.md#project-registry-validation-and-receipt-limits).
