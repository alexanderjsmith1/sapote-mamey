# Reading bundle identity, manifests and checksums

Start with the exact bundle tree/archive and a trusted expected release hash or receipt supplied independently of that tree. Record the path, SHA-256 and selected build. Metadata carried inside a bundle describes its contents; it does not independently establish who supplied them, that required jobs ran, or that scientific conclusions were accepted. Keep the original bundle in place and prepare any documentation/code changes as a separate candidate.

| Record | What it describes | Limit |
|---|---|---|
| `pyproject.toml`, `BUILD_STAMP.txt`, `TAG` | Engine/bundle versions and build identity | Agreement identifies metadata scope, not runtime or source correctness |
| `SOURCE_CHECKSUMS_SHA256.txt` | Expected digests for listed source files | Needs recomputation and an independently trusted release pin; the list does not validate itself |
| `TIER_MANIFEST.txt` | Selected tier/build header and tracked file roster | Requires membership/stamp checks under the current tracked-file policy; a tier label is not disclosure acceptance |
| `MODULE_MANIFEST.txt` | Generated mamey-module names and one-line docstring descriptions | Not a command catalog, call graph, execution record or the current accretion gate's membership baseline |
| `RELEASE_MANIFEST.md` and validation receipts | Recorded check commands/outcomes for a named source | Read exact source digest, command, partitions, failures and skips; historical PASS is not a test of a new composition |
| `REVIEW_CANDIDATE_TEST_RESULT.txt` | Pointer to source-bound external cut validation receipts | Does not provide those receipts or certify their current availability/acceptance |

## Read-only integrity checks

From the selected bundle, the documented integrity checker is:

```bash
python tools/check_release_manifest.py --root "/absolute/path/to/selected/bundle"
```

It recomputes admitted checksum targets, reports missing/mismatched/unsafe targets and malformed rows, checks the stamp when both identity files exist, and compares a present tier manifest with actual tracked membership. Cache/build/run-output exclusions follow `tools/tracked_file_policy.py`; inspect the reported scope. Working trees may have legitimate new files, but a candidate cut requires the selected owner to resolve membership and source drift before final regeneration.

**Required-artifact hold:** the current checker conditionally evaluates tier/stamp checks and does not reject their absence by itself. A checksum-only tree can pass without either `TIER_MANIFEST.txt` or `BUILD_STAMP.txt`. Confirm the required identity/membership files and selected cut receipts exist separately; do not interpret this checker's PASS as a complete release gate. Keep release certification with the selected cut receipts and authorized maintainer decision.

## Module inventory and accretion

`tools/check_module_accretion.py` reads module membership from the sealed checksum list, validating its row syntax/duplicate paths. It does not use the human `MODULE_MANIFEST.txt` inventory for that comparison or rehash source files as part of membership admission. Current module names are scanned separately; additions require a recognized justification basename in the newest changelog block. Removed modules are reported without independently failing this gate. These are code-composition checks, not evidence that each module executes correctly.

`--write` regenerates the human module-purpose inventory and mutates that file; it does not repair the sealed checksum baseline. The generated inventory header still describes the older baseline behavior. Preserve generated ownership and resolve its wording through the owner rather than editing the generated record. For readable command/capability discovery, use [the catalog guide](CATALOG_MAINTENANCE.md) and [current task routes](USER_TASK_ROUTER.md).

## Recovery and acceptance

Retain exact failure output and file hashes. Separate unexpected corruption, intentional candidate changes, missing dependencies and unrun checks. Regenerate final metadata only through the authorized [cut protocol](../CUT_PROTOCOL.md), after the candidate and required gates are ready. Reader checks do not update version stamps, seal or publish a bundle. For retired tier history and the parity/derivation limits, read [tier differences](TIER_DIFFERENCES.md). Scientific evidence admission, selected-profile completeness and rendered-page review remain separate from file integrity.
