# CUT_PROTOCOL — the confirm-before-cut handshake

**Purpose.** Cuts are cheap to start and expensive to get wrong. This protocol exists because the most
costly failure mode in this project isn't a bad patch — it's a cut that happens *without explicit
acknowledgment*, or one that silently drops a file because six chats each prepared an overlapping fix.
This is the ritual the Patch Chat follows. It is binding on the Patch Chat, not advisory.

## The rule

0. **Verify the configured test environment.** Check the selected compatible Python/pytest and
   dependencies before an authorized cut. Reuse a verified environment or approved compatible
   wheelhouse; do not download/upload wheels every session as a ritual. Network installs and the
   configured `--run-network` test profile have their own task/resource scope. Missing prerequisites
   are a hold, not permission to bypass the tests.

1. **A cut is PROPOSED until the Developer or User explicitly says go.** "Looks good", a thumbs-up on an analysis, or
   "yes that's the right fix" approves the *patch*, not the *cut*. The Patch Chat does not run
   `make_public_tier.sh` until it has an unambiguous instruction to cut (e.g. "cut it", "ship v9.7.NN",
   "go"). Ambiguity resolves to *not cutting yet* — ask.

2. **One Patch Chat owns versioning and cuts.** Analysis chats investigate and prepare patches; they do
   not cut. If two chats both think they're the Patch Chat, stop and reconcile before anyone cuts.

3. **Reconcile every inbound stream before cutting.** When more than one patch stream targets the same
   release, do not apply them in arrival order. For each shared filename, determine superset vs fork vs
   duplicate *by reading them*, and use the newest superset. Record the resolution. (This release folded
   six streams; three of them independently re-derived the same `make_public_tier.sh` at different
   completeness — arrival order would have shipped the weakest.)

4. **Verify out-of-band, then cut with the gates live.** The ordinary `release_cut.sh` route mutates its source tree: identity rewrite, version sync,
   generated surfaces and source integrity precede the cut. Use an authorized candidate copy,
   not an immutable reviewed baseline. Its normal test route runs a measured convergence baseline
   followed by a final configured full-suite run; the baseline may fail and is evidence seed only.
   Only the final successful run is the source test gate. Its
   shell exports `PYTHONDONTWRITEBYTECODE=1` before Python starts: the parent pytest process
   can create unmarked caches during collection before `tests/conftest.py` sets the child
   environment, causing the bundle runner to refuse later tests. Start a manual source-suite
   run with that setting too, and use a clean source tree; the setting does not remove old caches.
   The `--skip-tests` route accepts only a hash-pinned structured external-validation receipt verified by
   `tools/verify_external_validation_receipt.py`; a free-text `PYTEST_LOG`, typed pass count, or
   `SKIP_INTIER_PYTEST=1` environment variable is not external-validation authority at the release
   orchestrator. The low-level `make_public_tier.sh` does accept that variable without verifying
   a structured receipt itself; that is a technical bypass, not an authorization to use it. The receipt must
   bind the exact source-tree digest. It must also bind the canonical `python -m pytest -q -p no:cacheprovider --run-slow --run-network` command
   and `configured-full-suite` profile, and a zero process exit code. It must bind ordered UTC start/completion times and a completion no more than 24 hours old
   (the verifier permits at most five minutes of future clock skew). It must bind Python, pytest, and platform identity. It must also bind a SHA-256-bound log, exact node-ID list, and
   per-node outcome TSV. The identity and outcome node sets and all declared outcome counts must agree,
   with zero failures/errors. Keep the receipt and its three artifacts outside the source tree so the
   tree digest is not circular. The gate compares supplied artifacts; it does not execute pytest
   or authenticate authorship. Preserve the independently observed run evidence, not just its labels.
   In `release_cut.sh`, receipt verification happens after source preparation. A receipt bound to
   pre-bump/pre-regeneration bytes is stale at that point and must not be reused as if it covered
   the prepared tree. Never skip the required gates: `sync_version --check`, staged content/privacy
   audit, CODE tier-derivation checks, and source-integrity/membership checks. The
   current cut preserves genuine strain names and strain-to-class associations;
   identifier redaction is an explicit utility, not an automatic cut transform.

5. **Verify the artifact, not just the source.** At this point the tier ZIP is an **engineering build
   candidate, not a sealed release**. Extract it to a clean scratch
   directory (`unzip <tier>.zip -d /tmp/artifact_check && cd /tmp/artifact_check`) and run the full suite
   from there — the same `pytest` invocation as step 4, but against the extracted artifact, not
   the assembled-source working tree. Compare pass/fail/skip/error counts against step 4's numbers from
   the same session. Any new failure or error that wasn't present in step 4 means something was lost,
   corrupted, or altered between "assembled source" and "shipped zip". That is most likely a
   packaging/export-tooling issue, not a code issue, but it still blocks the cut until explained. A clean diff (same
   numbers, or only the expected differences from environment-skip variance) is required before the
   artifact is considered cut. (Added 2026-06-30 after a `.gitignore`-driven export bug silently stripped
   every `.zip` test fixture from a shipped release; nothing short of testing the actual artifact would
   have caught it. Cheap — one `unzip` and one more `pytest` run — and a backstop for *any* future
   "looked right in the working tree, broke in the zip" class of bug, regardless of cause). Only the
   artifact-verified candidate can proceed to the separately authorized seal decision; building or
   testing the archive does not itself seal it.

5b. **Run the taxonomy-drift gate.** `pytest tests/test_bert_taxonomy_drift.py` must be green. It pins the
   Bert Mode status-tier vocabulary (Verified / Partial / Policy / GenBank) in-bundle so the retired v9.4
   three-bucket taxonomy ("Partially verified" / "Unverified leads") cannot creep back into the reconciled
   surface. Note: the gate cannot diff the external `literature-digest` skill (not shipped in the bundle by
   design — self-containment), so it pins the vocabulary in-bundle rather than diffing upstream. When the
   skill's tier set changes, propagate skill -> `docs/BERT_MODE_PROTOCOL.md` -> this gate's pattern list.

6. **Hand back with a per-tier disclosure.** Every cut ends with the disclosure block below — filled in,
   per tier, with real numbers. No "should be fine." If a fix landed in only some tiers, that is the
   single most important line in the handback and goes at the top.

## Current registry and interpreter inputs

Inspect the executable entry points before preparing a disposable cut source:
`bash tools/release_cut.sh --help` and
`SELECTED_PYTHON -B tools/release_workflow.py cut --help`.
The shell route takes VERSION SOURCE OUTPUT and an optional LETTER. The resumable
Python route takes explicit `--version`, `--date`, `--source`, and `--out`, plus
its recorded stage options. A cut command performs source preparation and tests;
its help output and a passing registry snapshot do not authorize that operation.

Select one installed Python 3.12+ executable. For the shell route, set `PYTHON`
to that executable; the fallback is `python3` on PATH. For direct workflow calls,
pass the same invocation path with `--python`. Preserve its virtual-environment
locator rather than substituting the resolved base executable. A command string
such as `python -O` is not an executable selection. Compatibility, package
availability and pytest identity are separate observations; availability alone
is not a validated environment or accepted release.

The registry diagnostic is optional for ordinary CODE cuts, including direct
tier builds, monolithic and partitioned workflows. With no registry options,
it records `NOT_REQUESTED` / `NOT_RUN`; it performs no metadata discovery and
grants no synthetic-role or disclosure clearance. Private-content, personal-path,
codename, roster/exclusion, contig, source-integrity, test and seal gates still apply.
The standalone `verify_export_registry.py` diagnostic keeps its HOLD behavior
without explicit metadata.

If any registry option is supplied, all four selections are required:

- `--synthetic-registry`: absolute path to the selected external TSV metadata.
- `--synthetic-registry-sha256`: SHA256 of those exact metadata bytes.
- `--synthetic-guard-sha256`: SHA256 of the selected source's
  `tools/synthetic_id_registry_guard.py`.
- `--synthetic-allowlist-sha256`: SHA256 of that source's
  `tools/test_synthetic_ids.txt`.

The guard and allowlist paths are fixed to the selected source; they are not
private-data discovery options. Digest strings must contain 64 hexadecimal
characters. Do not copy a historical digest into a new source selection or
expand the synthetic list to hide a genuine/public identifier collision.

For an explicitly authorized selected-source/metadata diagnostic, replace all
six assignments below with the actual available paths and digests. This
`_registry` invocation is admission only; it does not start a cut:

```bash
CUT_PYTHON=/absolute/path/to/installed/python
CUT_SOURCE=/absolute/path/to/selected/disposable/source
REGISTRY_TSV=/absolute/path/to/selected/metadata.tsv
REGISTRY_SHA256=ACTUAL_64_HEX_DIGEST
GUARD_SHA256=ACTUAL_64_HEX_DIGEST
ALLOWLIST_SHA256=ACTUAL_64_HEX_DIGEST
"$CUT_PYTHON" -B "$CUT_SOURCE/tools/release_workflow.py" _registry \
  --source "$CUT_SOURCE" --python "$CUT_PYTHON" \
  --synthetic-registry "$REGISTRY_TSV" \
  --synthetic-registry-sha256 "$REGISTRY_SHA256" \
  --synthetic-guard-sha256 "$GUARD_SHA256" \
  --synthetic-allowlist-sha256 "$ALLOWLIST_SHA256"
```

Admission returns 0 for a bound snapshot pass, 1 for failure and 2 for a hold/refusal.
Diagnostics remain redacted. The pass binds only the selected metadata/guard/list
snapshot; fixture roles, public-tier disclosure, source completeness and release
acceptance remain separate. Partial selection, changed bytes or an unavailable
interpreter is a hold to resolve against the owner, not a reason to choose a
nearby file automatically. Omitting all four options records a diagnostic that
was not requested, never a passing registry snapshot. Selected and not-requested
states are bound into workflow context, commands and external inputs; resume
and independent verification cannot switch that selection. Retain old failed
roots; changed workflow/source definitions require a fresh validation lineage. Source and staged-artifact checks must retain the same
selection; later source or metadata changes require new admission/validation.

Unset ambient `PYTEST_ADDOPTS` before an authorized cut; the shell route refuses
it rather than silently changing the test profile. Do not set `CUT_TIERS` to an
empty or whitespace-only value. Omit it for the documented CODE default or
supply an explicit supported tier selection. The partitioned workflow currently
admits CODE only. A successful default test partition is not the configured
slow/network release profile or artifact validation.

`--skip-tests` is only the structured external-receipt route described above;
a log or typed pass count cannot replace its absolute receipt and expected
SHA256. Partitioned mode cannot use that option. Resolve dependency, process
monitoring, disk/RSS or generated-metadata holds with the named owner while
preserving the failed attempt. An optional-R readiness qualifier is not a
completed native-R check. On interruption, retain the actual process handle and
terminal receipt, preserve partial outputs, and use only the matching recorded
resume/retry contract. No manual cleanup of original evidence follows from a
failed prerequisite. Save the current state, partial transcript, file inventory
and next action under the approved session policy.

## The version bump (do not freehand)

Run the steps below from the selected `"$CUT_SOURCE"`; Python helpers use
the same `"$CUT_PYTHON"` chosen above.

Bundle and engine version independently. Bump only what changed:

- **Hygiene / doc / tooling / test cut** → bump **bundle** only (`pyproject [tool.sapote].bundle_version`,
  `CITATION.cff version`, `mamey/__init__.py BUNDLE_VERSION`, `BUILD_STAMP.txt version`), engine unchanged.
- **Engine/scoring change** → bump engine too, and say so loudly (it gates cross-strain comparability).

Direct execution at v9.7.153 confirmed the order below. Running these out of order produces a
confusing, fully-recoverable but wasted round of transient "OUT OF SYNC" / "stale generated block"
failures. They look alarming but are just sequencing, not real drift. Then, **in this exact order**:

1. Bump `pyproject.toml [tool.sapote].bundle_version` (and engine, if applicable).
2. Add the `CHANGELOG` entry (bolded headlines feed the `BUILD_STAMP.txt` `patch=` line).
3. Set `BUILD_STAMP.txt`'s `version=` / `build=` lines to match — **before** the next step; several
   restated files pull their build-stamp string from `BUILD_STAMP.txt`, not directly from
   `pyproject.toml`, so this has to land first or `sync_version` will write a stale stamp everywhere.
4. `"$CUT_PYTHON" tools/sync_version.py` (bare invocation — **there is no `--apply` flag; the tool writes
   by default and only `--check` makes it check-only and refuse to write**).
5. `"$CUT_PYTHON" -c "import sys; sys.path.insert(0,'tools'); import sync_version as sv; sv.sync_build_stamp_patch(check=False)"`
   — derives `BUILD_STAMP.txt`'s `patch=` line from the CHANGELOG head you just wrote.
6. `"$CUT_PYTHON" tools/render_bootstrap_contract.py --apply` — the explicit generator step can confirm the owner output. Current sync_version already delegates
   bootstrap regeneration before its anchored writes; do not describe it as regex-only.
   This owner renders AGENTS generated blocks, its CLAUDE mirror and BOOTSTRAP_FILE_AUDIT.
   Then regenerate every other version-bearing generated surface with
   `"$CUT_PYTHON" tools/gen_command_catalog.py`, `"$CUT_PYTHON" tools/generate_deliverables_menu.py --apply`,
   and `"$CUT_PYTHON" tools/gen_tools_inventory.py`; `release_cut.sh` performs all four regenerations.
7. Refresh the source-stage `TIER_MANIFEST.txt` and `SOURCE_CHECKSUMS_SHA256.txt`, then run the full
   suite once to measure the stale-manifest baseline. Run `gen_release_manifest.py --fixed-point`
   with that run's measured pass/skip counts, refresh source integrity again, and run the complete
   suite a second time. The second run must be green. Bind only that complete green log with
   `"$CUT_PYTHON" tools/gen_release_manifest.py --apply --pytest-log <path to final green log>`, then
   refresh source integrity once more. The first run is a convergence seed and never authorizes a
   package; `release_cut.sh` performs this sequence automatically.
8. Re-run `sync_version --check`, `render_bootstrap_contract --check`, and `gen_release_manifest
   --check` — all three green before proceeding.
9. Run `"$CUT_PYTHON" tools/verify_release_identity.py --root . --strict-membership`; the cut must
   refuse any tracked file omitted from `TIER_MANIFEST.txt`, even when every listed checksum passes.

`sync_version.py` owns all three `TAG` identity lines: bundle, engine, and build stamp. Do not
freehand the `TAG` build line. A green `sync_version --check` is the governing check; the release
identity gate independently verifies the assembled artifact afterward.

## The cut

Select the interpreter and source as described in
[Current registry and interpreter inputs](#current-registry-and-interpreter-inputs).
For an ordinary CODE cut, use `REGISTRY_ARGS=()` and omit the four registry
options on every route, including resume and verification. Only when the
diagnostic is requested, fill the following array with the four exact selections:

```bash
cd "$CUT_SOURCE"
REGISTRY_ARGS=()  # Ordinary CODE cut: no registry diagnostic requested.
# Only for a requested diagnostic, replace the empty array above with:
# REGISTRY_ARGS=(
#   --synthetic-registry "$REGISTRY_TSV"
#   --synthetic-registry-sha256 "$REGISTRY_SHA256"
#   --synthetic-guard-sha256 "$GUARD_SHA256"
#   --synthetic-allowlist-sha256 "$ALLOWLIST_SHA256"
# )

# Preferred: release_cut.sh runs and captures the configured full suite itself.
PYTHON="$CUT_PYTHON" RELEASE_DATE=<YYYYMMDD> bash tools/release_cut.sh <bundle-version> . <OUT> <build-letter> ${REGISTRY_ARGS[@]+"${REGISTRY_ARGS[@]}"}

# Optional partitioned route; select the same interpreter and registry inputs.
"$CUT_PYTHON" -B tools/release_workflow.py cut --python "$CUT_PYTHON" \
  --version <bundle-version> --date <YYYYMMDD> --letter <build-letter> \
  --source "$CUT_SOURCE" --out <OUT> ${REGISTRY_ARGS[@]+"${REGISTRY_ARGS[@]}"}

# External-validation route: bind the exact prepared tree at the later receipt-verification boundary,
# produce observed full-suite evidence and receipt outside <cutsrc>; any later source mutation invalidates the binding.
"$CUT_PYTHON" tools/verify_external_validation_receipt.py --root . --emit-tree-sha256
PYTEST_RECEIPT=/absolute/path/external-validation-receipt.json \
PYTEST_RECEIPT_SHA256=<sha256-of-receipt> \
PYTHON="$CUT_PYTHON" RELEASE_DATE=<YYYYMMDD> \
  bash tools/release_cut.sh <bundle-version> . <OUT> <build-letter> --skip-tests ${REGISTRY_ARGS[@]+"${REGISTRY_ARGS[@]}"}
```

The normal driver exports `SKIP_INTIER_PYTEST=1` before invoking the tier builder, even when it
ran its own source suite. Thus its cut log may say the child in-tier gate was skipped. Neither source
testing nor that line proves extracted-archive testing occurred; step 5 remains a separate artifact
check. Bind each tested object's bytes and report SOURCE, STAGED TIER and EXTRACTED ARCHIVE phases
separately instead of claiming a blanket “all gates tested” result.

The structured receipt schema is `sapote-mamey.external-pytest-validation.v1`. Its result artifact is
a two-column UTF-8 TSV with the exact header `nodeid<TAB>outcome`; allowed outcomes are `passed`,
`skipped`, `xfailed`, `xpassed`, `failed`, and `errors`. The identity artifact contains one exact pytest
node ID per line. Relative artifact locators resolve beside the receipt, but the release entry points
require the receipt itself to be supplied by absolute path together with its independently calculated
SHA-256. `tools/release.sh` applies the same receipt gate before honoring
`SKIP_INTIER_PYTEST=1`; direct environment-only bypass is refused.

If a tier refuses its content/privacy or derivation checks, preserve the failed evidence
and resolve the named finding in the authorized candidate or explicit export policy before
retrying. Do not add identifiers to allowlists or rewrite genuine labels merely to force a pass;
a matching identifier pattern alone does not establish private status.

### Releases cut the CODE tier only (v9.7.444)

2026-09-28: the four other tiers (CODE-analysis-free `clean`, `cohort` (formerly `sid`), `merged` and `public`)
are no longer part of the cut. `tools/release_cut.sh` cuts the CODE tier only, which still runs its own leak audit,
derivation check and checksums. The tooling for the other tiers stays in the bundle, disabled by default:
- the `clean`, `cohort`/`sid`, `merged` and `public` branches of `tools/make_public_tier.sh`, and the four-tier driver
  `tools/release.sh`, refuse to run unless `SAPOTE_ENABLE_DISABLED_TIERS=1` is set.
- `tools/check_tier_parity.py`, `tools/tier_vocabulary.py` and the redaction and leak-scan tools stay live, because
  the CODE tier and the release manifest still use them.

The following is a capability reference for a separately authorized policy change, not a standing instruction to re-enable retired tiers: `SAPOTE_ENABLE_DISABLED_TIERS=1 CUT_TIERS="code clean cohort merged public" bash
tools/release_cut.sh …`. For a CODE-only cut the disclosure block below has one row, CODE.

## Release tarball (only when one is published)

The sealed ZIP is the validated artifact. A `.tar.gz` for a release page is a repackaging, and the
gates above never see it. Build it only from a fresh extraction of the sealed ZIP, with the bundle
tool. Then prove it carries exactly the sealed files:

```bash
"$CUT_PYTHON" -c "import zipfile,sys; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])" <sealed.zip> <tmp>/<bundle-dir-name>
bash tools/make_verified_code_tarball.sh <tmp>/<bundle-dir-name> <OUT> <sealed.zip> <selected-SEAL_RECEIPT.json>
```

The CODE tarball route runs the producer, receipt-bound tarball verifier and SHA-256 sidecar check in private scratch space. It places the tarball and sidecar in `<OUT>` only after those checks pass. The selected local CODE seal receipt must name the supplied ZIP and bind its exact SHA-256 and byte count. Verify the receipt itself by the cut record before using it; this tool checks consistency, not owner selection. Publish only after that owner review, and quote the `.tar.gz.sha256` the tool wrote. Never
hand-build or copy the tarball through another volume. A tree that crossed exFAT, FAT or SMB
carries macOS `._*` files that Linux extracts as real files; at v9.7.441 that broke pytest
collection and failed `--strict-membership`.

## The per-tier disclosure block (paste, fill, never skip)

```text
Bundle / engine / build: <actual identities>
Source identity and configured-suite receipt: <hash; command; outcomes; holds>
Built tier: CODE (other tiers NOT BUILT unless separately authorized)
Tier derivation / content-audit / version / membership checks: <actual receipts>
Child in-tier pytest: <RAN with outcomes / SKIPPED with reason>
Extracted archive identity / complete-suite check: <hash; command; outcomes / NOT RUN>
Archive publication state: <published engineering candidate / refusal / recovery hold>
Seal / promotion / publication authority: <separate owner decision / NOT GRANTED>
Changed scope and unresolved limitations: <specific records>
```

## Generator mandate

Regenerate bootstrap and other owned surfaces in version-bump step 6, before
source-integrity refresh and configured-suite validation. After the final green
suite in step 7, set `FINAL_GREEN_PYTEST_LOG` to that complete log for the selected
source, retained outside the source tree, and bind it with:

```bash
"$CUT_PYTHON" tools/gen_release_manifest.py --root . --apply --pytest-log "$FINAL_GREEN_PYTEST_LOG"
```

A bare `--apply` without test evidence is refused. Refresh source-stage membership
and checksums after the manifest update, then run the checks in steps 8–9 before
packaging. Never freehand derived build stamps. The generator preserves narrative
prose; review archive-content and seal descriptions against the actual evidence.


## Custom private-vocabulary coverage

Ordinary CODE cuts do not require an operator's private vocabulary or strain registry.
A successful public audit reports generic configured checks separately from custom literal
coverage. With no configured private literals, custom coverage is `NOT_EVALUATED`; that is
not private-vocabulary or universal privacy clearance. An empty supplied profile has the
same vocabulary status. A selected valid profile still enforces its private identifiers
across shipped text, tests, detector code and the existing archive-policy surfaces.
Invalid profiles and actual private payload/path/readability/integrity findings still refuse.

Select an external profile directly with `tools/public_release_audit.py TREE
--privacy-profile PROFILE --report-json`, or the direct tier builder's documented
`--privacy-profile PROFILE` option. Keep the real profile outside distributed CODE.
The high-level release-cut/workflow does not currently forward that profile option;
do not infer coverage from a file merely existing nearby or from a default PASS.
A maintainer assertion that specified private words are absent needs an explicit external
Source/artifact check tied to the exact resulting hashes and declared scan scope.

This partial cleanup holds package-home/default-discovery and historical routing-policy-ID
migration separately. Existing configured-home support and numerical scoring are unchanged.
Held files can still contain historical deployment words; this proposal does not establish
complete name removal. Preserve genuine strain names, public examples, public package
formats and strain-to-class associations. Do not embed, encode or reconstruct private words
inside CODE to simulate an absence check. Regenerate governed metadata and validate the
actual integrated source/artifact before acceptance.

## Controlled import evidence v2

The complete static `mamey`/`tools` roster retains every Python file and its
production or test/fixture role. Production modules run in both declared orders;
CSV setters additionally run in both reload orders. The v2 worker and controller
receipts retain every module outcome, raw operation, source origin, CSV check and
losslessly encoded before/after module-search path. Receipt verification requires
current source, environment, machinery, resource policy and complete ordered
coverage. Old v1 evidence does not satisfy this changed contract.

`PASS` means every required import passed. `READY_WITH_OPTIONAL_UNAVAILABLE` is a
separate visible ready state: only exact pinned vendored ijson YAJL/CFFI backend
modules may have `OPTIONAL_UNAVAILABLE` outcomes, with exact exception identity,
origin and dependency-absence evidence. These outcomes remain in every worker and
root summary and are never relabeled PASS. The pinned pure-Python JSON backend
must pass fixed valid, incomplete, malformed and trailing-garbage JSON capability checks at its natural roster
position. Unexpected exceptions, unknown vendor/dependency bytes, unavailable
explicitly selected backends or DLLs, protected operations, altered global state,
failed fallback or incomplete coverage remain HOLD. Installed `ijson.common`
bytes and vendored common bytes are separately pinned because their actual code
is different in the supported environment. Source and extracted CODE evidence
are independently verified; the owner consumer preserves the exact ready state.

A source/tools priority change is admissible only inside the leading approved
root block with unchanged foreign tail and identical concrete FileFinder module
and package origins. Reordered namespace portions additionally require disjoint
concrete leaves and unambiguous resources. Collisions, nested symlinks, unreadable
namespace trees, foreign priority changes and unsupported path entries remain
HOLD. Unsupported entries in an initial or unchanged before/after path state
also require HOLD; complete diagnostics retain their typed markers and raw
path tables. Strict verification refuses PASS or ready claims for those states.
Existing local-helper pinning is preserved. Raw path changes and their
replayable proof remain recorded even when equivalence is established.

When the roster declares Matplotlib imports, a separate dependency-only process
prepares a fresh private font cache under the report output. It uses the selected
Python runtime, pinned helper, installed dependency/font inputs and fixed data-only
CLI. It cannot read project source contents, write source, access the network or
write admission evidence. One explicit pre-guard exception loads the bound internal font-cache machinery
helper under a distinct machinery-only alias. Its ordinary project module names
remain unpreloaded and present in the complete production roster; their first
ordinary execution, including any dependency import, runs under the installed
guards and is accounted. Ordinary cached modules continue to reload under the
guard. No other ordinary project module or Matplotlib module
is preloaded. Workers validate the prepared cache using standard-library code and retain the existing thread/process/network/source-write guards. The
controller and selected interpreter must have matching executable, version and
prefix identities; a mismatch refuses before bootstrap rather than substituting
a runtime.

The production OS profile grants only the prepared cache directory's literal
creation/write probe, with no permission to write children or change attributes.
Admission separately proves an unchanged existing-directory probe plus denied
child creation, native cache-content writes and directory-mode changes. A worker
may accept only the pinned Matplotlib cache chooser's `Path.mkdir(exist_ok=True)`
call on that exact owned nonsymlink mode-0700 directory, raw mode 0777/no dir-fd,
with EEXIST and identical device/inode/mode/owner/link-count/size/timestamps. Its
raw mkdir event and complete proof remain visible. Every other operation stays
blocking. Invalid bootstrap/cache admission refuses before imports; terminal
cache drift produces HOLD. Receipt relocation preserves original request and
manifest bytes/hashes and uses the helper's explicit current-evidence envelope;
no cache validation reads fall back to the original output.

These are import-readiness checks. Full configured-suite, metadata, archive,
extracted-artifact, owner sealing and hosted portability requirements remain
separate release gates.
