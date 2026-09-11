# CUT_PROTOCOL — the confirm-before-cut handshake

**Purpose.** Cuts are cheap to start and expensive to get wrong. This protocol exists because the most
costly failure mode in this project isn't a bad patch — it's a cut that happens *without explicit
acknowledgment*, or one that silently drops a file because six chats each prepared an overlapping fix.
This is the ritual the Patch Chat follows. It is binding on the Patch Chat, not advisory.

## The rule

0. **Upload pytest at session start.** The cut gates need pytest (+ pluggy + iniconfig). Download
   the wheels from PyPI and upload them into the chat. Takes 2 minutes. Without it, the post-cut
   invariant and the in-tier pytest gate cannot run and the Patch Chat is blocked.

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

4. **Verify out-of-band, then cut with the gates live.** Run the configured full suite once on the
   assembled cut source. The ordinary `release_cut.sh` route runs that suite itself. Its
   `--skip-tests` route accepts only a hash-pinned structured external-validation receipt verified by
   `tools/verify_external_validation_receipt.py`; a free-text `PYTEST_LOG`, typed pass count, or
   `SKIP_INTIER_PYTEST=1` environment variable is not external-validation authority. The receipt must
   bind the exact source-tree digest; the canonical `python -m pytest -q -p no:cacheprovider --run-slow --run-network` command
   and `configured-full-suite` profile; zero process exit code; UTC start/completion times no more than
   24 hours old; Python, pytest, and platform identity; and SHA-256-bound log, exact node-ID list, and
   per-node outcome TSV. The identity and outcome node sets and all declared outcome counts must agree,
   with zero failures/errors. Keep the receipt and its three artifacts outside the source tree so the
   tree digest is not circular. Never skip the un-skippable gates: `sync_version --check`, the leak
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
6. `python3 tools/render_bootstrap_contract.py --apply` — **after** step 4, not instead of it; this
   regenerates the "generated block" sections (`AGENTS.md`'s initiation prompt and known-
   gotchas section, `docs/BOOTSTRAP_FILE_AUDIT.md`) that step 4's plain regex substitutions don't reach.
7. Run the full suite and retain its complete green log. Then run
   `python3 tools/gen_release_manifest.py --apply --pytest-log <path to that fresh full-suite log>`.
   The `--tests-passed N --tests-skipped M` flags exist too, but the release-cut path requires the
   actual log so a red or stale suite cannot be restated as passing evidence.
8. Re-run `sync_version --check`, `render_bootstrap_contract --check`, and `gen_release_manifest
   --check` — all three green before proceeding.

`sync_version.py` owns all three `TAG` identity lines: bundle, engine, and build stamp. Do not
freehand the `TAG` build line. A green `sync_version --check` is the governing check; the release
identity gate independently verifies the assembled artifact afterward.

## The cut

```bash
cd <cutsrc>

# Preferred: release_cut.sh runs and captures the configured full suite itself.
RELEASE_DATE=<YYYYMMDD> bash tools/release_cut.sh <bundle-version> . <OUT> <build-letter>

# External-validation route: first compute the exact tree digest using the shipped verifier,
# then produce the structured receipt + bound log/node-ID/outcome artifacts outside <cutsrc>.
python3 tools/verify_external_validation_receipt.py --root . --emit-tree-sha256
PYTEST_RECEIPT=/absolute/path/external-validation-receipt.json \
PYTEST_RECEIPT_SHA256=<sha256-of-receipt> \
RELEASE_DATE=<YYYYMMDD> \
  bash tools/release_cut.sh <bundle-version> . <OUT> <build-letter> --skip-tests
```

The structured receipt schema is `sapote-mamey.external-pytest-validation.v1`. Its result artifact is
a two-column UTF-8 TSV with the exact header `nodeid<TAB>outcome`; allowed outcomes are `passed`,
`skipped`, `xfailed`, `xpassed`, `failed`, and `errors`. The identity artifact contains one exact pytest
node ID per line. Relative artifact locators resolve beside the receipt, but the release entry points
require the receipt itself to be supplied by absolute path together with its independently calculated
SHA-256. `tools/release.sh` applies the same receipt gate before honoring
`SKIP_INTIER_PYTEST=1`; direct environment-only bypass is refused.

If a public tier **REFUSES** (leak audit) or **FATALs** (parity gate), that is the gate working. Do not
force past it — fix the source (allowlist a genuine synthetic token; redact a real ID) and re-cut.

## The per-tier disclosure block (paste, fill, never skip)

```
Bundle vX.Y.Z / engine A.B.C / build <stamp>
Full suite (out-of-band): <P> passed / <S> skipped / <F> failed
Per tier — leak audit | parity gate | version-sync gate | files:
  CODE                : <0 AS> | OK | OK | <n>
  CODE-analysis-free  : <0 AS> | OK | OK | <n>
  SID-public          : <0 AS> | n/a | OK | <n>
  MERGED-PRIVATE      : n/a    | n/a | OK | <n>
Fixes that landed in ALL tiers: <list>
Fixes that landed in SOME tiers only: <list — TOP OF HANDBACK, or "none">
Expected synthetic-ID noise (do not re-chase): <list>
NOT in this cut (flagged, your call): <list>
```

## Generator mandate (v9.7.148h)

> **Before zipping any tier**, always run both generators to derive manifests from source-of-truth:
> ```bash
> python3 tools/gen_release_manifest.py --root . --apply   # RELEASE_MANIFEST.md
> python3 tools/render_bootstrap_contract.py --apply       # docs/BOOTSTRAP_FILE_AUDIT.md
> python3 tools/sync_version.py --check                    # confirm no drift
> ```
> Never hand-edit `RELEASE_MANIFEST.md` build stamps — they drift within one cut. The generators exist; use them.
