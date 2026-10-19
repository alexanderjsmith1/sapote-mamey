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

The command recomputes admitted checksum targets and enforces tracked-file coverage: it refuses empty/no-verified-content manifests, omitted or unexpected governed paths and duplicate normalized records, as well as missing, mismatched, unsafe or malformed targets. It also requires readable, safely admitted `TIER_MANIFEST.txt` and `BUILD_STAMP.txt`, checks their build stamps and compares tier membership with the tracked-file policy. Missing required identity files no longer pass this command. Cache/build/run-output exclusions still follow `tools/tracked_file_policy.py`.

This scope describes `check_release_manifest.py`'s CLI, which enables strict coverage. The lower-level `checksum_problems` helper defaults to non-strict coverage, and `verify_release_identity.py` requests strict content coverage only with `--strict-membership`; do not transfer this CLI contract to every helper call. A successful check establishes the implemented content/metadata comparisons, not release authority, complete test execution, Linux validation or scientific acceptance. Candidate changes still require owner review and final metadata regeneration.

## Module inventory and accretion

`tools/check_module_accretion.py` reads module membership from the sealed checksum list, validating its row syntax/duplicate paths. It does not use the human `MODULE_MANIFEST.txt` inventory for that comparison or rehash source files as part of membership admission. Current module names are scanned separately; additions require a recognized justification basename in the newest changelog block. Removed modules are reported without independently failing this gate. These are code-composition checks, not evidence that each module executes correctly.

`--write` regenerates the human module-purpose inventory and mutates that file; it does not repair the sealed checksum baseline. The generated inventory header still describes the older baseline behavior. Preserve generated ownership and resolve its wording through the owner rather than editing the generated record. For readable command/capability discovery, use [the catalog guide](CATALOG_MAINTENANCE.md) and [current task routes](USER_TASK_ROUTER.md).

## Recovery and acceptance

Retain exact failure output and file hashes. Separate unexpected corruption, intentional candidate changes, missing dependencies and unrun checks. Regenerate final metadata only through the authorized [cut protocol](../CUT_PROTOCOL.md), after the candidate and required gates are ready. Reader checks do not update version stamps, seal or publish a bundle. For retired tier history and the parity/derivation limits, read [tier differences](TIER_DIFFERENCES.md). Scientific evidence admission, selected-profile completeness and rendered-page review remain separate from file integrity.

## Exact-identity seal-plan generation

When `tools/make_seal_script.py` is present in the selected candidate, it is a standalone generation tool; it is not a `mamey_run.py` subcommand and does not execute pytest, collection, a subprocess, a seal or a release. Its generation mode reads an existing cut directory, pinned source/archive logs, explicit native execution manifests, the archive and expected SHA-256, exact named outcome dispositions, and a selected owner-consumer script. Every generation argument below is required. The output parent must already exist, and the output directory must be fresh and outside the cut and bound source/extracted trees.

```bash
python tools/make_seal_script.py \
  --cut-folder /path/to/existing-cut \
  --source-log /path/to/source.log --archive-log /path/to/archive.log \
  --source-evidence /path/to/source-suite-input.json \
  --archive-evidence /path/to/archive-suite-input.json \
  --differences /path/to/exact-named-differences.json \
  --archive /path/to/existing-cut/candidate.zip --archive-sha256 EXPECTED_ARCHIVE_SHA256 \
  --owner-script /path/to/reviewed-owner-consumer.sh \
  --output /path/to/fresh-review/seal-plan
```

The suite manifests use `sapote-mamey.seal-suite-input.v1` and pin the actual log and native `sapote-mamey.pytest-execution.v1` capture by path/hash, plus the selected tree digest. The generator requires complete admitted phase evidence, compatible selection/configuration/pytest version and the same exact collected identities. Order alone may differ; counts, progress dots and reconstructed JUnit names cannot establish identity. Collection-level skips and ambiguous subtest contexts refuse. Every observed main-outcome/reason/xfail difference needs exactly one matching named disposition with a nonblank explanation. That explanation is an operator judgment, not proof of its cause. The extracted archive must already exist and match ZIP file bytes/modes with no extra files; the tool does not extract it. This comparison does not certify source/package parity beyond the supplied archive/extracted tree.

Generation writes `PLAN.json` and a mode-0600 `SEAL_CANDIDATE.sh` sequentially, reporting `PREPARED_OWNER_REVIEW`; a later failure can leave partial artifacts. Preserve any failed attempt and use a fresh destination. `--verify-plan PLAN --plan-sha256 EXPECTED_PLAN_SHA256` is a separate evidence-recheck mode and refuses generation arguments. It recomputes bound evidence, machinery, trees and named differences; it does not execute the consumer.

The generated wrapper is a separate owner-execution artifact. It checks a plan-hash acknowledgment, rechecks the plan, then would hand off to the pinned consumer through `/bin/bash`. Its nonexecutable file mode does not prevent an explicit shell invocation. Setting an acknowledgment variable is not human authorization. Review the actual consumer, plan and remaining release gates before any separately authorized execution; this guide does not authorize it. Input/namespace races, immutable source-generation proof, consumer safety, Linux behavior, final-stack runtime and release/scientific adoption remain held. Historical logs lacking the native manifests cannot be retrospectively certified by this route. Generated inventories and final checksums stay with their canonical owners.
