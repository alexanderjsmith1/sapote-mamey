# Defining your own privacy tiers

Sapote-Mamey ships a **release-tier framework**: one source tree, cut several
ways, each way withholding a different amount of private content. The framework
is not specific to this project's cohort — you can use it to separate *your own*
private material (unpublished strains, collaborator names, internal notes) from
a shareable public bundle, with source-defined export exclusions and audits. A gate checks its encoded policy and scanned surfaces; it does not independently discover every private fact in prose or grant permission to disclose it.

This guide is for a user who downloaded Sapote-Mamey and wants to produce their
own public/private cuts. For what the *project's* built-in tiers contain, see
[tier set explainer](./TIER_SET_EXPLAINER.md).

## The one tool

Everything is driven by [`tools/make_public_tier.sh`](../tools/make_public_tier.sh):

```
tools/make_public_tier.sh <tier> <src_dir> <out_dir>
```

**Only the CODE tier runs by default.** Releases cut the CODE tier only, so every tier other than
`code` refuses to run (exit 2) unless you set `SAPOTE_ENABLE_DISABLED_TIERS=1`. See
[CUT_PROTOCOL.md](../CUT_PROTOCOL.md).

`<tier>` is one of `code`, `clean`, `cohort`, `merged` or `public`. `sid` is a deprecated alias normalized to `cohort`; `public` is a separate labelled branch and is disabled by default along with all non-code tiers. The cut runs source/version and tier-content gates, denylist handling and public audits before its final archive transaction. The in-tier test suite can be explicitly bypassed with `SKIP_INTIER_PYTEST=1`, which requires separate out-of-band evidence; do not describe that cut as in-tier tested. Existing archive names are refused. A failed precommit gate does not publish a new archive; a postcommit durability failure can retain an archive with a recovery hold.

The optional `--privacy-profile <profile.json>` argument reuses the same
portable privacy profile that Mamey accepts at intake. It adds folder-level and
free-text controls to the public-export boundary; it does not change Mamey's
deterministic extraction behavior or turn a profile into scientific evidence.

## Privacy controls and their actual boundaries

You do not need to edit any code to establish your own privacy separation. Three
existing controls cover the common cases:

### 1. Private directories — put it where the cut strips it

The `code`/`clean`/`public` tiers delete these directories from the bundle:
`private/`, `cohort/`, `merged_cohort/`, `data/`, `release2_source_library/`,
`docs/legacy/`, `offline_deps/`. Anything you place under **`private/`** is
removed from every non-`merged` tier automatically. Keep your working copy as
`merged` (strips nothing); hand out `code` (strips `private/`).

### 2. The denylist — scrub names and free-text terms

For private *terms* that appear inside otherwise-shippable files (a collaborator
surname, an internal codename, an unpublished project name):

1. Copy [`release_denylist.example.txt`](../tools/release_denylist.example.txt) into an operator-held denylist only after removing every `#` comment line and reviewing the resulting terms. The shell reader skips empty lines but treats comment lines as terms.
2. Add one term per line. Content replacement is case-sensitive and limited to the selected text extensions. Name deletion uses case-insensitive `find -iname` glob matching, so wildcard characters have a different meaning in that path operation. Review terms for both uses; do not assume the filename check is literal.
3. Use this file only during an independently authorized cut of a disposable stage. The non-`merged` shell branch modifies matching text and deletes matching paths. Both operations exclude paths below `wheels/` and `sapote_addons/wheels/`. The later fixed-string content grep is a separate check, not a proof that all paths, binary content or case variants were inspected.

`tools/release_denylist.txt` is stripped from the staged public output. The `.example` file is documentation until an operator supplies it as the active denylist; copying its commented body verbatim does not make those comments inert to the consumer. This describes the retained shell branch, not permission to run a cut or a comprehensive privacy clearance. Current CODE-only and redaction boundaries are described above.

### 3. Strain-ID audit switches do not rewrite IDs

The current builder removed the automatic AS/AJS/PENDING identifier-rewriting pass. `AS_SCRUB=1` controls retained identifier audit checks; it does not redact identifiers into placeholders. In the legacy shell audit, `AS_GUARD_RETIRED` defaults to `1`, which demotes some AS findings to warnings; `AS_GUARD_RETIRED=0` changes those findings to blocking when `AS_SCRUB=1`. Separate Python policy and documentation-redaction gates also apply; neither switch replaces them.

For your own unpublished collection, declare explicit private identifiers and excluded roots in an operator-held privacy profile. Inspect the actual staged output and audit findings. Do not assume prefix switches make a private dataset publishable. The separately shipped redaction tool has its own contract and is not automatically re-enabled by setting this variable.

### 4. Public-export policy — fail closed on staging roots and project-specific identifiers

The optional `public_export_policy` object in the same
`sapote_privacy_profile_v1` file is the portable configuration surface for
folder-level export controls. Add the object to an operator-held profile; the
profile itself is not copied into the staged public tree.

- `exclude_root_names` removes every directory with that basename from the
  disposable non-merged stage. `future_improvements` is protected by default,
  including when it appears below `docs/`.
- `exclude_relative_paths` removes one exact, source-root-relative directory.
  Absolute paths and `..` are rejected.
- `private_identifiers` contains typed `{identifier_id, literal}` values. The
  public audit checks every shipped text surface and every shipped path for the
  literal. It does not silently rewrite the literal: a remaining match refuses
  the cut.
- `allowlisted_occurrences` is exceptional. It must name a declared
  `identifier_id`, one exact relative path, the full-file SHA-256, and a reason.
  It permits content only for that byte-exact file; it never permits a private
  identifier in a path.

Keep a profile that contains real private literals outside the public source
tree (or under a root that the public cut excludes). Passing it by path keeps
the operator policy out of the staged bundle:

```bash
tools/make_public_tier.sh code ./sapote-source ./out \
  --privacy-profile ../private-policy/strain_privacy_profile.json
python tools/public_release_audit.py ./out/staged-tree \
  --privacy-profile ../private-policy/strain_privacy_profile.json
```

Synthetic fixtures and ordinary public examples do not need an allowlist: do
not list their literal in `private_identifiers`. An allowlist is only for a
reviewed, source-bound exception that truly must contain a declared private
literal.

## Final archive transaction

For non-merged tiers, the builder does not publish the final ZIP with a
generic rename or an overwrite option. After the disposable stage has passed
the privacy audit, it invokes `tools/finalize_public_archive.py`. That
transaction independently inventories the stage, writes a deterministic
temporary archive, reopens it to verify member names, member types, bytes, and
hashes, and then commits that same audited file with the platform's native
no-clobber primitive.

Before staging, the transaction runs a same-filesystem two-call capability
probe: an existing destination must remain unchanged, then an absent
destination must receive exactly the source bytes. Platforms or filesystems
that cannot prove that behavior refuse before a final archive is created.
Existing output names are never replaced. A post-commit durability problem
retains the committed archive and reports a typed recovery hold; it does not
pretend to roll the archive back.

## Which tier to hand out

| You want to… | Cut this tier |
|---|---|
| Share the tool and let the recipient re-run the pipeline | `code` |
| Prepare an analysis-free tier | `clean` (disabled by default) |
| Prepare a cohort-containing tier for separately authorized review | `cohort` (disabled by default) |
| Prepare a private scaffold retaining tier content | `merged` (disabled by default; common hygiene/version operations still apply) |

## Verifying a cut is safe

The cut is fail-closed — it will not zip a bundle that fails a gate — but you can
also audit any tree yourself:

```
python tools/public_release_audit.py <tree_dir>
```

`PASS` means the selected encoded checks found no blocking findings within their configured scope. Default checks have allowlisted paths, skipped content categories and conditional identifier rules; they are not a proof that every byte or private scientific statement was adjudicated. Inspect `--report-json` surface counts and, when the review calls for it, `--strict-source-disclosure` for the additional source/test pass. `--governance-only` checks requested decisions rather than content; it requires `--require-active-decision`. Never substitute that result for a content audit.

The normal audit is a read-only check, but `--apply-public-export-exclusions` deliberately removes configured directories. Use that flag only on a disposable stage. Keep the exact policy, command, source identities and logs for the authorized release review; a passing audit is not release approval.

## Public-workbook audit limits

`tools/audit_public_cut.py` is a separate merged-master Excel disclosure guard. It is not `public_release_audit.py`, a code-tree audit, archive test, version/engine check or validation of an intake privacy profile. A workbook's label, engine stamp or `CLEAN` result does not supply disclosure authority. Preserve original public/private workbooks and select a new report in an existing output directory:

```bash
python tools/audit_public_cut.py inputs/public_candidate.xlsx \
  --private inputs/private_master.xlsx \
  --out outputs/public_workbook_audit_new.md
```

Without `--private`, there is no derived held-set or public/private reconciliation. The tool reads recognized BGC-master and strain-roster sheets, hunts configured identifier/held/denylist patterns in cached cell values, and checks available `release` columns. The main scan uses `read_only=True, data_only=True`: formula expressions and missing formula caches are not inspected or recalculated. Hidden-sheet cell values are included, but sheet names, comments, hyperlinks, document properties, images, embedded objects and other workbook/package surfaces are not independently scanned. Review those separately when relevant to disclosure.

Sheet admission verifies only that a recognized BGC-master and roster sheet exist. Readers take the first recognized sheet alias. Required identity/cohort headers, nonblank UID rows and authoritative schema content are not fully admitted. Missing `bgc_uid` or cohort headers can yield zero counted rows and apparently clean subset/count reconciliation; a missing `strain` header uses the second column as roster fallback. The per-row release check permits blanks and can check zero rows when no release column exists. Reconcile actual intended rows, headers, unique strain/BGC identities and disclosure states before interpreting those counts.

The roster check recognizes only its fixed SID/WAC/AS/AJS token shapes in designated columns; uppercase SID and WAC tokens are exempt from the out-of-roster branch. Unknown labels can be outside this check altogether. `--roster` augments the workbook's derived roster rather than restricting it, and can change the private-minus-public held set. Derived cohorts/strains are absence-based comparisons, not an independently admitted exclusion policy. An unchanged UID and equal cohort row counts also do not verify equality of all retained row values. Preserve a separately reviewed allowed/held identity roster and source evidence; do not infer permission from a regex family or a zero finding count.

The identifier helper uses its own historical shared rules and public/test-name exceptions, with a narrower fallback if that helper cannot be imported. The workbook command has no portable `--privacy-profile` argument. Missing release denylist is warned on stderr and processing continues with built-in checks; that result is reduced coverage. Record the exact policy/helper/denylist version and full diagnostics instead of treating `CLEAN` as a universal prohibition or allowance for any strain-prefix family.

Default audit mode writes a Markdown report even though it does not otherwise intend to edit the workbook. Explicit `--out` has no input-alias guard and atomically replaces an existing target; it can overwrite a public/private workbook, roster or other evidence if selected incorrectly. Keep every source and report destination disjoint, use a fresh report path and retain original hashes. The report can contain private cohort names/counts and leaked cell snippets, so its own audience needs review. Findings details are capped at 30 per kind, and no input/report/denominator hash receipt is emitted. Save the actual source identities, command, exit status and report hash separately.

Optional `--scrub` writes a selected `--scrub-out` workbook (default `<input>_SCRUBBED.xlsx`) before re-auditing it. It substitutes every matching string cell, including data cells and formula text; it is not limited to prose and does not remove held rows. Its substitution patterns do not exactly match all main-audit identifier exceptions/rules. Use only a separately identified candidate output, preserve authoritative sources and compare all changed cells and formula behavior before adoption. There is no source/private/report output-collision guard or group transaction: a scrubbed workbook can remain after re-audit/report failure, and a selected existing destination can be replaced. Correct the problem and retry into new reviewed paths; retain failed/partial outputs. Normal `CLEAN` returns zero and findings return one; read/load/write errors can instead raise without a completed report. Sources: `tools/audit_public_cut.py:89–512`, `tools/redact_public_tier.py:77–119`, and `tools/_wbio.py:25–125`.

## Adding a brand-new named tier (advanced)

The four content policies above cover most needs without editing code. If you
need a *new named tier* with a different strip policy, add a `case` arm in
[`tools/make_public_tier.sh`](../tools/make_public_tier.sh) alongside the
existing ones — each arm is just the list of directories that tier removes,
followed by `strip_internal`. Keep the fail-closed leak check downstream intact;
it checks the encoded disclosure policy. Add meaningful fixtures for new tier behavior and preserve separate owner review; a misleading tier label is not corrected by the filename alone.
