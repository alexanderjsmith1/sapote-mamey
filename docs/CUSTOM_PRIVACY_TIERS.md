# Defining your own privacy tiers

Sapote-Mamey ships a **release-tier framework**: one source tree, cut several
ways, each way withholding a different amount of private content. The framework
is not specific to this project's cohort — you can use it to separate *your own*
private material (unpublished strains, collaborator names, internal notes) from
a shareable public bundle, with a fail-closed gate that refuses to ship anything
you marked private.

This guide is for a user who downloaded Sapote-Mamey and wants to produce their
own public/private cuts. For what the *project's* built-in tiers contain, see
[tier set explainer](./TIER_SET_EXPLAINER.md).

## The one tool

Everything is driven by [`tools/make_public_tier.sh`](../tools/make_public_tier.sh):

```
tools/make_public_tier.sh <tier> <src_dir> <out_dir>
```

`<tier>` is one of `code`, `clean`, `sid`, `merged` (and `public`, a labelled
alias of `code`). The cut runs a version-sync gate, strips per-tier content,
scrubs your denylist, runs a fail-closed leak audit, runs the in-tier test
suite, and only then zips. If any gate fails, **no zip is produced.**

The optional `--privacy-profile <profile.json>` argument reuses the same
portable privacy profile that Mamey accepts at intake. It adds folder-level and
free-text controls to the public-export boundary; it does not change Mamey's
deterministic extraction behavior or turn a profile into scientific evidence.

## The three privacy controls you drive

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

1. Copy the template:
   ```
   cp tools/release_denylist.example.txt tools/release_denylist.txt
   ```
2. Add one term per line (literal, case-sensitive match).
3. Cut any non-`merged` tier. Each term is removed from file content, any file
   whose *name* contains the term is dropped, and a **leak check re-greps the
   staged tree** — if a term survives anywhere, the cut is **REFUSED**.

`tools/release_denylist.txt` is itself stripped from every public tier, so your
private terms never ship. The `.example` template ships inert as your starting
point.

### 3. Strain-ID redaction — the `AS_SCRUB` switch

Strain identifiers (`AS-###`, `AJS-###`, `PENDING-###`) have a dedicated
redaction path separate from the denylist, controlled by the `AS_SCRUB`
environment variable:

```
AS_SCRUB=1 tools/make_public_tier.sh code <src> <out>   # redact strain IDs
AS_SCRUB=0 tools/make_public_tier.sh code <src> <out>   # keep them (default here)
```

With `AS_SCRUB=1`, IDs are scrubbed from all non-`merged` tiers and a leak audit
refuses any tier that still contains an unpublished identifier. Use it when your
strain IDs are not yet public.

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
| Share the tool but not your worked analyses/figures | `clean` |
| Ship a public cohort data bank alongside the tool | `sid` |
| Keep your own full working copy (nothing stripped) | `merged` |

## Verifying a cut is safe

The cut is fail-closed — it will not zip a bundle that fails a gate — but you can
also audit any tree yourself:

```
python tools/public_release_audit.py <tree_dir>
```

`PASS` means no banned identity term or leak was found in the whole tree.

## Adding a brand-new named tier (advanced)

The four content policies above cover most needs without editing code. If you
need a *new named tier* with a different strip policy, add a `case` arm in
[`tools/make_public_tier.sh`](../tools/make_public_tier.sh) alongside the
existing ones — each arm is just the list of directories that tier removes,
followed by `strip_internal`. Keep the fail-closed leak check downstream intact;
it is what guarantees a mislabeled tier still cannot ship private content.
