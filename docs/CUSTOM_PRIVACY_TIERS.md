# Defining your own privacy tiers

This is a maintainer page. Use it if you keep a fork of Sapote-Mamey and want to share a public copy without your unpublished strains, collaborator names or internal notes. If you only run analyses, you do not need it. For what the built-in tiers contain, see the [tier set explainer](./TIER_SET_EXPLAINER.md).

One source tree is cut into tiers. Each tier withholds a different amount of private content. The cut checks the policy it encodes and the files it scans. A pass is not clearance: it does not find every private fact in prose, and it does not give you permission to share.

## The one tool

```bash
tools/make_public_tier.sh <tier> <src_dir> <out_dir>
```

`<tier>` is `code`, `clean`, `cohort`, `merged` or `public`. Only `code` runs by default. Any other tier prints `REFUSED` and exits 2 unless you set `SAPOTE_ENABLE_DISABLED_TIERS=1`. `sid` is an old name for `cohort`. See [CUT_PROTOCOL.md](../CUT_PROTOCOL.md) for the cut process.

Example:

```bash
tools/make_public_tier.sh code ./sapote-source ./out
```

The script copies the source to a temporary stage, strips private content, runs its audits, and writes one ZIP into `./out`. A finished cut prints a line starting `OK  code  ->` with the ZIP path, and exits 0. A failed gate prints a `FATAL`, `REFUSED` or `HOLD` line and exits non-zero. A failed gate before the final step writes no archive.

An existing archive name is never replaced. Pick a new `<out_dir>` or remove the old file yourself. To skip the in-tier test suite, set `SKIP_INTIER_PYTEST=1`. A cut made that way has not been tested in-tier, so keep separate test evidence.

The broader [`tools/release_cut.sh`](../tools/release_cut.sh) rewrites its source tree (release identity, generated docs, manifests, checksums). Run it only on a working candidate.

## Three ways to keep content out

### 1. Private directories

The `code`, `clean` and `public` tiers delete `private/`, `cohort/`, `merged_cohort/`, `data/`, `release2_source_library/`, `docs/legacy/` and `offline_deps/`. Put anything private under `private/`. The `merged` tier keeps those private folders, but it is not an unchanged copy: every tier drops the GToTree author note, `.git`, `__pycache__`, `.pytest_cache` and `.DS_Store`, and the staged `RELEASE_MANIFEST.md` version lines are rewritten. Keep your real working copy separately, not as a cut archive. Hand out the `code` tier.

### 2. The denylist

A denylist removes private terms from files you otherwise ship, such as a collaborator surname or a codename.

1. Copy [`release_denylist.example.txt`](../tools/release_denylist.example.txt) to `tools/release_denylist.txt`. The cut strips that file from the output.
2. Add one term per line. Blank lines and lines that start with `#` are skipped.
3. Content replacement is case-sensitive and covers only selected text file types. File-name deletion is case-insensitive and treats `*` and `?` as wildcards, so check each term for both uses.

The shell branch rewrites matching text and deletes matching paths in the stage. It skips `wheels/` and `sapote_addons/wheels/`. A later search for the terms is a check, not proof that every binary file or spelling was caught.

### 3. A public-export policy

An optional privacy profile (`sapote_privacy_profile_v1` JSON) can carry a `public_export_policy` object. Keep the profile outside the source tree. Passing it does not exclude an in-tree copy.

- `exclude_root_names`: remove every directory with that name from the stage. `future_improvements` is always protected.
- `exclude_relative_paths`: remove one directory by its exact path from the source root. Absolute paths and `..` are rejected.
- `private_identifiers`: a list of `{identifier_id, literal}` values. The audit searches every shipped text file and path for each literal. A match refuses the cut. Nothing is rewritten.
- `allowlisted_occurrences`: a rare exception. Each entry needs `identifier_id`, one `relative_path`, the file's full `sha256`, a `reason`, `purpose: "CONTENT_ONLY_EXCEPTION"` and `state: "ACTIVE"`. It allows content in that exact file. It never allows a private identifier in a path.

Pass the profile to the cut:

```bash
tools/make_public_tier.sh code ./sapote-source ./out \
  --privacy-profile ../private-policy/strain_privacy_profile.json
```

Synthetic examples and ordinary public text need no allowlist. Do not list their literals as private.

The strain-ID switches `AS_SCRUB` and `AS_GUARD_RETIRED` are retired. No cut script reads them, so setting them does nothing. The cut does not rewrite strain IDs. To protect your own collection, declare its identifiers in `private_identifiers` and read the staged output.

## What the final step does

After the stage passes the audit, `tools/finalize_public_archive.py` builds the ZIP, reopens it to check names, types and hashes, and then commits it without overwriting anything. If an existing name is found, or a gate fails, you get no archive. If something goes wrong after the commit, the script keeps the archive and prints a `HOLD` line. Treat a `HOLD` as unfinished and read its message before you share the file.

## Which tier to hand out

| You want to | Cut this tier |
|---|---|
| Share the tool so the recipient can re-run the pipeline | `code` |
| Prepare an analysis-free tier | `clean` (disabled by default) |
| Prepare a tier with cohort content for separate review | `cohort` (disabled by default) |
| Prepare a private scaffold for separate review | `merged` (disabled by default); keep a separately verified working copy |

## Audit a tree yourself

```bash
python tools/public_release_audit.py <tree_dir>
```

`PASS` means the encoded checks found no blocking findings in their scope. Useful options:

- `--report-json`: print surface counts.
- `--strict-source-disclosure`: add a source and test pass for personal paths and internal literals.
- `--privacy-profile <file>`: apply a profile's export policy.
- `--governance-only`: check requested governance decisions, not content. It needs `--require-active-decision`.

The audit only reads the tree. The exception is `--apply-public-export-exclusions`, which deletes directories. Use that flag on a disposable stage only. Keep the policy, command and logs for the review.

## Public-workbook audit limits

`tools/audit_public_cut.py` is a separate check for an Excel master workbook. It is not a code-tree audit.

```bash
python tools/audit_public_cut.py inputs/public_candidate.xlsx \
  --private inputs/private_master.xlsx \
  --out outputs/public_workbook_audit_new.md
```

It writes a Markdown report. It returns 0 for `CLEAN` and 1 when it finds something. Use a fresh `--out` path: the tool replaces an existing file there without asking, including a workbook. The report can name private strains and quote leaked cells, so decide who may read it.

What it covers and misses:

- It reads cached cell values on recognized BGC-master and roster sheets, including hidden sheets. It does not read formulas, sheet names, comments, hyperlinks, document properties or images.
- Without `--private`, it has no held set to compare against.
- It matches fixed strain-ID token shapes in set columns. Other labels can pass.
- A missing `bgc_uid` or cohort header can give zero counted rows and a clean-looking result. Check the headers and row counts yourself.
- `--scrub` writes a new workbook (`--scrub-out`) with matching strings replaced, including data cells and formula text. It does not remove held rows. Review every changed cell before you use the output.

A `CLEAN` report covers only the cells listed above. It is not a full disclosure review and does not approve a release. Review the parts it does not read by hand, keep the private workbook unchanged, and record both reviews for the person who approves the release.

## Adding a new named tier

This is a maintainer change, not routine customization. A new tier needs the tier name, its aliases, archive naming, strip rules, and every parity and checker that reads them. Adding a `case` arm in the strip policy alone is not enough. Use the existing tiers and export policy where you can.
