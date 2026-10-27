# Portable project catalog and private handoff

Request **Sapote-Mamey project catalog** for hash-bound package locations, or **private project handoff** for the separate multi-package archive. Both are operated by `tools/project_catalog.py` with the selected source environment. They are distinct from the per-package `mamey_run.py handoff` builder and the pointer-first [project data home](PROJECT_DATA_HOME.md).

## Register and verify package locations

```bash
python tools/project_catalog.py register \
  --project-root /absolute/project \
  --package /absolute/project/runs/strain/package
python tools/project_catalog.py verify --project-root /absolute/project
```

The package must be below the chosen root and contain a JSON-object `manifest.json` with a strain identifier. Register creates or updates `<project-root>/project_outputs/project_catalog.json` (older projects keep an existing `lab_quest_outputs/`), rebinding a matching logical package path to its current manifest hash. Keep a prior catalog when its earlier binding is required.

Even `verify` initializes the catalog: a nonexistent project root can be created, and a missing catalog becomes an empty one. A successful empty report means zero registered entries; it does not prove the workspace contains no packages or that every run was inventoried. Verify an explicitly known root/catalog and compare its entry count to the requested inventory.

Verification checks package locators and recorded manifest hashes. It does not validate every package file, recompute engine gates or accept biological interpretation. Changing a CSV while leaving the manifest unchanged can escape this catalog check. Run the source-compatible package validator on a preserved review copy when package integrity is required.

## Export a private archive

```bash
python tools/project_catalog.py export-private \
  --project-root /absolute/project \
  --out /absolute/private_handoffs/new_project_handoff.zip
```

The export carries all regular files discovered below each catalogued package, and the catalog, plus an optional current portfolio binding and its named config/registry. Package traversal has no extension, hidden-file, cache or manifest-file-inventory filter. Review the actual package contents before transfer: extra files inside those directories travel too. Files outside those package directories are omitted unless they are the catalog or the named portfolio files; a portfolio registry's referenced evidence files are not automatically followed into the archive. This archive is not a complete project backup. It refuses symbolic links inside package file traversal, stale manifest/portfolio hashes and absolute-locator-shaped strings in package manifests. Preserve sealed evidence and use a governed relocation record when such a locator is refused; do not silently rewrite the original manifest.

Output must be outside the project root. The exporter refuses an existing output path. It writes a hidden temporary file beside the output and links it into place only when complete, so a failed export leaves no partial archive. On a filesystem without hard links, export fails. Keep the catalog, package files and optional portfolio files unchanged during export; a file changed mid-export can make the archive fail import. Record the archive SHA-256 and send it separately; the archive's own hashes do not prove who made it. Test the archive by importing it into an empty root.

This archive is explicitly `PRIVATE_PROJECT_HANDOFF_ONLY`. No public export or redaction option exists here. A package's recorded PUBLIC field does not authorize disclosing the whole private archive.

## Import into an empty root

```bash
python tools/project_catalog.py import-private \
  --project-root /absolute/new_project \
  --input /absolute/private_handoffs/new_project_handoff.zip
```

The importer requires an empty destination; it can create the root before archive checks. It checks CRC, supported handoff schema/class, declared member paths, bytes and hashes in a temporary sibling stage, then copies staged files into the root. Final catalog and optional portfolio verification happen after copying. A later failure or interrupted copy can therefore leave an occupied or partial destination that a retry refuses. Preserve the failed-root evidence and use a fresh empty root for recovery.

Capture stdout, stderr and exit status. The standalone front door lets library exceptions propagate, so refusal can be a traceback rather than a neat FAIL receipt. Inspect actual root/archive state before assuming a failure produced no writes. Successful import checks the extracted declared bytes and catalog provenance, not scientific acceptance. Import refuses an archive that repeats a member name, or a manifest that lists a path twice. Accept handoffs from a known sender, with the archive SHA-256 confirmed separately, and keep the original archive.

## Portfolio bindings have a separate schema

`tools/validate_portfolio_config.py --project-root ROOT --config RELATIVE_CONFIG` reads a `sapote_project_portfolio_v1` JSON file whose `project_registry` points to one contained registry. The default check does not write a binding. Adding `--write-binding` creates or replaces `project_outputs/portfolio_binding.json` with config/registry hashes and availability metadata; preserve an earlier receipt and avoid concurrent writers to that fixed path.

This project-registry portfolio is distinct from the extraction `sapote_privacy_profile_v1` policy and its separate evidence TSV. A valid portfolio does not override extraction release assignment. See [portable privacy and evidence](PORTABLE_STRAIN_PRIVACY_AND_EVIDENCE.md) for that intake schema.

## Project-registry validation and receipt limits

The two portfolio validators accept different inputs. `tools/validate_portfolio_registry.py` takes the extraction privacy-profile JSON (`--privacy-profile`) and evidence TSV (`--evidence-registry`) described in [portable privacy and evidence](PORTABLE_STRAIN_PRIVACY_AND_EVIDENCE.md#heterogeneous-evidence-registry); selected policy/evidence validation errors print `FAIL` to stderr and exit 2. `tools/validate_portfolio_config.py` takes a project root and pointer-config JSON naming a `sapote_project_registry_v1` registry. Its successful stdout is the binding JSON; failures can propagate as tracebacks. Capture stdout, stderr and exit status for either route, and keep those input schemas separate.

The project registry rejects duplicate tier/strain/assay IDs, unknown declared tiers and assays referring to undeclared strains. It accepts an empty strain/assay collection if at least one tier exists. `audience_rank` and `replicate_count` must be whole numbers: an integer, a string of digits or a whole float such as `50.0`. Booleans and fractions are refused. `target_ids` must be a string or a list of strings; a mapping or a non-string item is refused.

In this project schema, source locators, source SHA-256 text and parent-material IDs are recorded declarations. The loader does not open/hash each cited source, validate SHA-256 syntax or resolve a cycle-free material graph. That differs from the separate evidence-TSV validator's limited parent-existence checks. Verify source bytes and lineage independently before relying on a recorded result.

`assay_data_state: AVAILABLE` means at least one assay record exists, including a record marked `NOT_TESTED`, `NOT_RETURNED` or `UNBOUND`. Read `result_state_counts` and exact material/condition/source fields alongside it. The counts are declared records and distinct declared target labels, not independent replicates, tested-target coverage, positive outcomes or genomic causal evidence.

A project-registry export decision compares declared audience ranks; it does not perform export or approve disclosure. Unknown strains are held, and absence of an explicit public-export tier maps to PRIVATE. `write_strain_registry_surfaces` writes `project_registry_snapshot.json` followed by `bioassay_scope.tsv` directly; it can replace prior files and a later failure can leave a partial pair. Preserve existing outputs and use a fresh authorized output directory. This helper itself is not a sealed-package transaction.

## Binding inputs, writes and recovery

Run the read-only binding check first, from the selected bundle environment:

```bash
python tools/validate_portfolio_config.py \
  --project-root /absolute/project \
  --config config/portfolio.json
```

The existing config must declare `schema_version: sapote_project_portfolio_v1` and a `project_registry` relative logical path to an existing regular JSON file below that project root. Input containment is checked after resolving symlinks; outside-root targets and `..` registry paths are refused. Use a nonblank relative file path, not `.`. An absolute config path inside the root is accepted by this implementation, although its help advertises a root-relative path. The default invocation produces stdout JSON without writing a receipt.

Adding `--write-binding` writes the fixed `project_outputs/portfolio_binding.json` (or the selected legacy output directory). The current writer checks that both final and `.tmp` destinations resolve below the root, refuses an existing or symlinked `.tmp`, creates the temporary file exclusively and then replaces the final receipt. A symlink that resolves outside the root is refused by this output check. Preserve prior final receipts: final replacement is still allowed, and there is no sealed-package-state check or general protection against hostile concurrent filesystem changes. On failure inspect retained receipt/temporary evidence before retrying.

Keep config and registry bytes unchanged throughout validation. The binding hashes are computed after separate parse/load reads; there is no immutable snapshot or final consistency check. A concurrent edit can pair earlier availability metadata with a later registry hash. Preserve the input bytes used for review, record their hashes, compare the receipt to those exact files and rerun against unchanged inputs if uncertain. A binding receipt reports declared inventory and workflow states; it does not verify every referenced evidence file or scientific claim. See [project-registry validation limits](#project-registry-validation-and-receipt-limits).
