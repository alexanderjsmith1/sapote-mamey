# Sapote-Mamey release tiers

**Bundle v9.7.414 · build 20260907v97414a · engine Mamey 1.9.152**

> **HISTORICAL SNAPSHOT — measured 2026-07-12 for v9.7.319; reviewed 2026-09-03.**
> The five-cut layout, 1,353-file count, sizes, and checksums below describe that historical cut.
> They are retained as provenance, not current operating instructions. For the current four-tier
> set and its separately governed public-release promotion, use `TIER_DIFFERENCES.md` and
> `CURRENT_DOCS_INDEX.md`.

Every release cut produces the same bundle in five labelled tiers. This note explains what each tier is *designed* to be, and — importantly for this release — what the five tiers actually contain right now. For internal distribution.

## The short version

The five tiers are a distribution framework: one source tree, cut five ways, each way withholding a different amount of private content. In **v9.7.319 the five tiers are content-identical** — same 1,353 files, same bytes — because this bundle carries no private content to withhold and the strain cohort is public. They differ only in a one-word tier label stamped into two files. The framework is real and stays wired; it just has nothing to strip in this release.

## The five tiers

| Tier | Zip name | Designed to be |
|---|---|---|
| code | `...-CODE-...` | The full runnable pipeline: all engine code, tools, docs, examples, and the Wheelhouse (scanners, HMMs). Private cohort data and internal working notes removed. |
| clean | `...-CODE-analysis-free-...` | The code tier with worked strain-by-strain outputs also removed — a tool-only distribution that ships the machinery but none of the analyses run through it. |
| cohort | `...-COHORT-public-...` | The code tier plus the public reference cohort data banks. Private material still removed. This is the tier that keeps `cohort/` where `code` strips it. |
| merged | `...-MERGED-PRIVATE-scaffold-...` | Everything, held back from nobody: the full internal working scaffold including any `private/` tree and real strain IDs. The Developer or User's copy. |
| public | `...-PUBLIC-RELEASE-...` | The public GitHub artifact. Same content as the code tier, including the Pfam scanner HMM (CC0, freely redistributable). |

**Renamed in v9.7.407+ (owner ruling 2026-09-04):** the tier now called **cohort** was previously
called `sid`, after one lab's strain series. The behaviour is unchanged — same strip rule, same
content — only the name is now generic. `sid` is still accepted on the command line as a deprecated
alias, and bundles sealed before the rename carry `-SID-public-` in their zip name and `tier=sid`
in `BUILD_STAMP.txt`; current tools read both. `tools/tier_vocabulary.py` is the canonical owner of
tier names, labels and aliases.

## What each tier strips, by design

When private content *is* present in the source tree, the cut removes different slices per tier. This is the actual logic in `tools/make_public_tier.sh`:

- **code / public**: remove `private/`, `cohort/`, `merged_cohort/`, `data/`, `release2_source_library/`, `docs/legacy/`, `offline_deps/`, plus internal working docs (session handoffs, freeze-triage notes, `PRIVATE_DO_NOT_PUBLISH.txt`, and similar).
- **clean**: everything code removes, and *also* the worked outputs — `deliverables/deep_dives`, `deliverables/analyses`, `deliverables/reports`, `figures/`, and the example ledgers.
- **cohort**: removes `private/`, `merged_cohort/`, and `docs/legacy/`, but keeps the `cohort/` banks — that is the whole point of this tier, to ship the public cohort data alongside the tool.
- **merged**: strips nothing. Full scaffold.

A separate step can scrub embedded strain IDs (`AS-`/`AJS-`/`PENDING-`) from every tier except merged. That scrub is **deactivated** in this release (`AS_SCRUB=0`) per the 2026-07-06 PI decision that the AS-series cohort is public — so real strain IDs are retained everywhere and no redaction runs.

## Why all five are identical in v9.7.319

Verified against the actual zips: **0 differing files between any pair of tiers.** The reason is that everything the tiers are built to strip is simply absent from this bundle:

- No `private/`, `cohort/`, `merged_cohort/`, `data/`, `release2_source_library/`, `docs/legacy/`, or `offline_deps/` directories exist in the source tree.
- No worked strain outputs or `figures/` tree to remove for the clean tier.
- `AS_SCRUB=0`, so the ID scrub is a no-op.

With nothing to strip and nothing to redact, all five cuts land on the same 1,353 files. The public tier is, by explicit design in this release, a labelled alias of the code tier (the last thing it used to withhold, the Pfam HMM, is CC0 and now ships in all tiers — see `NOTICE`).

## The only real difference: the tier label

Each tier stamps its own name into two files, so a bundle always knows which tier it is even after it is unzipped:

```
BUILD_STAMP.txt   -> tier=code | clean | cohort | merged | public
TIER_MANIFEST.txt -> # TIER_MANIFEST tier=<name> version=9.7.319 stamp=20260712v97319a
```

That one-word difference is why the five zip sizes differ by a handful of bytes (6,345,805 to 6,345,823) while the file lists are identical. The cut's fail-closed derivation gate (`verify_tier_derivation.py`) confirms `public == redact(private source)` for every shared file and allows only these two label files to vary per tier.

## Which tier to hand out

- **Sharing the tool with a collaborator who should not see worked analyses** → clean.
- **Sharing the tool and being able to re-run the pipeline** → code.
- **Handing over the public cohort data with the tool** → cohort.
- **The public GitHub release** → public.
- **Your own full working copy / archival** → merged.

In this release any of them gives the same files; pick by the label that matches the audience, and the recipient's bundle will self-identify correctly.

## Integrity

`SHA256SUMS.txt` ships alongside the five zips. Verify with `sha256sum -c SHA256SUMS.txt` before distributing.

```
clean   624b25a0...baf128a7
code    61750e02...11244d69
merged  ee206c1e...1dba4824
public  943a0e7d...acd550ff
cohort  d149e0e6...ab55a8d
```

*(Full 64-character digests are in `SHA256SUMS.txt`.)*

---

*One caveat worth stating plainly: because the tiers are identical here, the tier label is the only thing distinguishing a "public" zip from the "merged private" zip. If a future cut reintroduces private content, that stops being true and the strip logic above does real work — so treat the label as meaningful, not decorative.*
