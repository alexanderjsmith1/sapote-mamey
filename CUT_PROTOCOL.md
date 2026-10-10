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
   bind the exact source-tree digest; the canonical `python -m pytest -q -p no:cacheprovider --run-slow --run-network` command
   and `configured-full-suite` profile; zero process exit code; ordered UTC start/completion times and a completion no more than 24 hours old
   (the verifier permits at most five minutes of future clock skew); Python, pytest, and platform identity; and SHA-256-bound log, exact node-ID list, and
   per-node outcome TSV. The identity and outcome node sets and all declared outcome counts must agree,
   with zero failures/errors. Keep the receipt and its three artifacts outside the source tree so the
   tree digest is not circular. The gate compares supplied artifacts; it does not execute pytest
   or authenticate authorship. Preserve the independently observed run evidence, not just its labels.
   In `release_cut.sh`, receipt verification happens after source preparation. A receipt bound to
   pre-bump/pre-regeneration bytes is stale at that point and must not be reused as if it covered
   the prepared tree. Never skip the un-skippable gates: `sync_version --check`, the leak
   audit, tier-derivation parity, and redaction.

5. **Verify the artifact, not just the source.** At this point the tier ZIP is an **engineering build
   candidate, not a sealed release**. Extract it to a clean scratch
   directory (`unzip <tier>.zip -d /tmp/artifact_check && cd /tmp/artifact_check`) and run the full suite
   from there — the same `pytest` invocation as step 4, but against the extracted artifact, not
   the assembled-source working tree. Compare pass/fail/skip/error counts against step 4's numbers from
   the same session. Any new failure or error that wasn't present in step 4 means something was lost,
   corrupted, or altered between "assembled source" and "shipped zip" — most likely a packaging/export-
   tooling issue, not a code issue, but it still blocks the cut until explained. A clean diff (same
   numbers, or only the expected differences from environment-skip variance) is required before the
   artifact is considered cut. (Added 2026-06-30 after a `.gitignore`-driven export bug silently stripped
   every `.zip` test fixture from a shipped release; nothing short of testing the actual artifact would
   have caught it. Cheap — one `unzip` and one more `pytest` run — and a backstop for *any* future
   "looked right in the working tree, broke in the zip" class of bug, regardless of cause.) Only the
   artifact-verified candidate can proceed to the separately authorized seal decision; building or
   testing the archive does not itself seal it.

5b. **Run the taxonomy-drift gate.** `pytest tests/test_bert_taxonomy_drift.py` must be green. It pins the
   Bert Mode status-tier vocabulary (Verified / Partial / Policy / GenBank) in-bundle so the retired v9.4
   three-bucket taxonomy ("Partially verified" / "Unverified leads") cannot creep back into the reconciled
   surface. Note: the gate cannot diff the external `literature-digest` skill (not shipped in the bundle by
   design — self-containment), so it pins the vocabulary in-bundle rather than diffing upstream; when the
   skill's tier set changes, propagate skill -> `docs/BERT_MODE_PROTOCOL.md` -> this gate's pattern list.

6. **Hand back with a per-tier disclosure.** Every cut ends with the disclosure block below — filled in,
   per tier, with real numbers. No "should be fine." If a fix landed in only some tiers, that is the
   single most important line in the handback and goes at the top.

## The version bump (do not freehand)

Bundle and engine version independently. Bump only what changed:

- **Hygiene / doc / tooling / test cut** → bump **bundle** only (`pyproject [tool.sapote].bundle_version`,
  `CITATION.cff version`, `mamey/__init__.py BUNDLE_VERSION`, `BUILD_STAMP.txt version`), engine unchanged.
- **Engine/scoring change** → bump engine too, and say so loudly (it gates cross-strain comparability).

Then, **in this exact order** (confirmed by direct execution at v9.7.153 — running these out of
order produces a confusing, fully-recoverable but wasted round of transient "OUT OF SYNC" / "stale
generated block" failures that look alarming but are just sequencing, not real drift):

1. Bump `pyproject.toml [tool.sapote].bundle_version` (and engine, if applicable).
2. Add the `CHANGELOG` entry (bolded headlines feed the `BUILD_STAMP.txt` `patch=` line).
3. Set `BUILD_STAMP.txt`'s `version=` / `build=` lines to match — **before** the next step; several
   restated files pull their build-stamp string from `BUILD_STAMP.txt`, not directly from
   `pyproject.toml`, so this has to land first or `sync_version` will write a stale stamp everywhere.
4. `python3 tools/sync_version.py` (bare invocation — **there is no `--apply` flag; the tool writes
   by default and only `--check` makes it check-only and refuse to write**).
5. `python3 -c "import sys; sys.path.insert(0,'tools'); import sync_version as sv; sv.sync_build_stamp_patch(check=False)"`
   — derives `BUILD_STAMP.txt`'s `patch=` line from the CHANGELOG head you just wrote.
6. `python3 tools/render_bootstrap_contract.py --apply` — the explicit generator step can confirm the owner output. Current sync_version already delegates
   bootstrap regeneration before its anchored writes; do not describe it as regex-only.
   This owner renders AGENTS generated blocks, its CLAUDE mirror and BOOTSTRAP_FILE_AUDIT.
   Then regenerate every other version-bearing generated surface with
   `python3 tools/gen_command_catalog.py`, `python3 tools/generate_deliverables_menu.py --apply`,
   and `python3 tools/gen_tools_inventory.py`; `release_cut.sh` performs all four regenerations.
7. Refresh the source-stage `TIER_MANIFEST.txt` and `SOURCE_CHECKSUMS_SHA256.txt`, then run the full
   suite once to measure the stale-manifest baseline. Run `gen_release_manifest.py --fixed-point`
   with that run's measured pass/skip counts, refresh source integrity again, and run the complete
   suite a second time. The second run must be green. Bind only that complete green log with
   `python3 tools/gen_release_manifest.py --apply --pytest-log <path to final green log>`, then
   refresh source integrity once more. The first run is a convergence seed and never authorizes a
   package; `release_cut.sh` performs this sequence automatically.
8. Re-run `sync_version --check`, `render_bootstrap_contract --check`, and `gen_release_manifest
   --check` — all three green before proceeding.
9. Run `python3 tools/verify_release_identity.py --root . --strict-membership`; the cut must
   refuse any tracked file omitted from `TIER_MANIFEST.txt`, even when every listed checksum passes.

`sync_version.py` owns all three `TAG` identity lines: bundle, engine, and build stamp. Do not
freehand the `TAG` build line. A green `sync_version --check` is the governing check; the release
identity gate independently verifies the assembled artifact afterward.

## The cut

```bash
cd <cutsrc>

# Preferred: release_cut.sh runs and captures the configured full suite itself.
RELEASE_DATE=<YYYYMMDD> bash tools/release_cut.sh <bundle-version> . <OUT> <build-letter>

# External-validation route: bind the exact prepared tree at the later receipt-verification boundary,
# produce observed full-suite evidence and receipt outside <cutsrc>; any later source mutation invalidates the binding.
python3 tools/verify_external_validation_receipt.py --root . --emit-tree-sha256
PYTEST_RECEIPT=/absolute/path/external-validation-receipt.json \
PYTEST_RECEIPT_SHA256=<sha256-of-receipt> \
RELEASE_DATE=<YYYYMMDD> \
  bash tools/release_cut.sh <bundle-version> . <OUT> <build-letter> --skip-tests
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

If a public tier **REFUSES** (leak audit) or **FATALs** (parity gate), that is the gate working. Do not
force past it — fix the source (allowlist a genuine synthetic token; redact a real ID) and re-cut.

### Releases cut the CODE tier only (v9.7.444)

2026-09-28: the four other tiers (CODE-analysis-free `clean`, `cohort` (formerly `sid`), `merged` and `public`)
are no longer part of the cut. `tools/release_cut.sh` cuts the CODE tier only, which still runs its own leak audit,
derivation check and checksums. The tooling for the other tiers stays in the bundle, disabled by default:
- the `clean`, `cohort`/`sid`, `merged` and `public` branches of `tools/make_public_tier.sh`, and the four-tier driver
  `tools/release.sh`, refuse to run unless `SAPOTE_ENABLE_DISABLED_TIERS=1` is set;
- `tools/check_tier_parity.py`, `tools/tier_vocabulary.py` and the redaction and leak-scan tools stay live, because
  the CODE tier and the release manifest still use them.

The following is a capability reference for a separately authorized policy change, not a standing instruction to re-enable retired tiers: `SAPOTE_ENABLE_DISABLED_TIERS=1 CUT_TIERS="code clean cohort merged public" bash
tools/release_cut.sh …`. For a CODE-only cut the disclosure block below has one row, CODE.

## Release tarball (only when one is published)

The sealed ZIP is the validated artifact. A `.tar.gz` for a release page is a repackaging, and the
gates above never see it. Build it only from a fresh extraction of the sealed ZIP, with the bundle
tool, then prove it carries exactly the sealed files:

```bash
python3 -c "import zipfile,sys; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])" <sealed.zip> <tmp>/<bundle-dir-name>
bash tools/make_verified_code_tarball.sh <tmp>/<bundle-dir-name> <OUT> <sealed.zip> <selected-SEAL_RECEIPT.json>
```

The CODE tarball route runs the producer, receipt-bound tarball verifier and SHA-256 sidecar check in private scratch space; it places the tarball and sidecar in `<OUT>` only after those checks pass. The selected local CODE seal receipt must name the supplied ZIP and bind its exact SHA-256 and byte count. Verify the receipt itself by the cut record before using it; this tool checks consistency, not owner selection. Publish only after that owner review, and quote the `.tar.gz.sha256` the tool wrote. Never
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

## Generator mandate (v9.7.148h)

> **Before zipping any tier**, always run both generators to derive manifests from source-of-truth:
> ```bash
> python3 tools/gen_release_manifest.py --root . --apply   # RELEASE_MANIFEST.md
> python3 tools/render_bootstrap_contract.py --apply       # docs/BOOTSTRAP_FILE_AUDIT.md
> python3 tools/sync_version.py --check                    # confirm no drift
> ```
> Never hand-edit `RELEASE_MANIFEST.md` build stamps — they drift within one cut. The generators exist; use them.
