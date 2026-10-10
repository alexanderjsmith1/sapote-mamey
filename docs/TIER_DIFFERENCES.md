# Release-tier history and current verification limits

Current release work cuts CODE only under [CUT_PROTOCOL](../CUT_PROTOCOL.md). `tools/make_public_tier.sh` refuses the other retained tier branches unless the explicit disabled-tier override is set. Their presence in source does not authorize rebuilding or publishing them. Read the exact selected privacy assignment in [portable privacy/evidence guidance](PORTABLE_STRAIN_PRIVACY_AND_EVIDENCE.md); a tier label, identifier prefix or historical public-availability statement does not settle disclosure of new genome findings.

The original tier note below is retained as history. Its blanket “byte-identical” and “safe for external sharing” statements are not current validation results. The builder still unconditionally invokes the maintained documentation/configuration redactor for non-merged tiers. Retiring the old AS_SCRUB switch and SID rewrite did not remove that later transform. Do not re-arm disabled branches or bypass current release gates merely to satisfy an old four-tier description.

## What the checkers establish

| Owner | Checked scope | Limit |
|---|---|---|
| `tools/check_tier_parity.py` | Archive labels/set completeness, version, selected cassette/marker counts, registry and four manifest-file presence checks | Requires the historical ordinary four-tier set; does not compare every payload byte, all scientific data or current CODE-only release completeness |
| `tools/verify_tier_derivation.py` | Expected text transforms for selected extensions on files walked from the supplied private source, with stated metadata/strip exclusions | Reads text with decoding errors ignored; does not hash all binaries or detect arbitrary extra destination files; not a complete archive checksum or disclosure audit |
| `tools/make_public_tier.sh` | Staging, profile/content transforms, metadata and checksum regeneration under the selected cut route | Mutates a candidate tree and can run gates; this guide authorizes no cut or release |
| `tools/sync_version.py` | Regenerates version/build restatements, including `TIER_NOTE_CODE.md` | Restated versions identify metadata; they do not certify execution or source correctness |

The derivation checker treats test/synthetic-allowlist text as identity comparisons and skips a larger explicit metadata set than the old “three differentials” summary. A PASS applies only to the provided inputs, options and checker scope. Compare final source/archive checksums and required cut receipts separately; record the actual command and source hash. Keep the tier-builder and release-checker execution receipts separately.

## Tier-parity selection, writes and evidence

`tools/check_tier_parity.py --zips <archive> ...` selects an explicit archive roster. `--tiers-dir <directory>` selects every top-level lowercase `*.zip` match there; a nonempty `--zips` list takes precedence. The owner requires exactly one each of the historical `merged`, `cohort`, `code` and `clean` tiers. A present public promotion is inspected, and `--with-public` makes it required. Do not create disabled tiers just to obtain this check's PASS, or substitute it for the current CODE-only cut gates.

Tier identity comes from the full governed archive filename. Inspection selects the first extracted directory with a `mamey` subdirectory, falling back to the extraction root; it does not refuse multiple candidate roots. Version comparison reads a numeric prefix from `CITATION.cff`, rather than binding every archive-name version/stamp or build identity. Cassette and marker comparisons use counts of regex matches from four source files, not equality of the matched ID sets or registry content. Different IDs can therefore have equal counts. Missing citation/cassette/marker files become `?` or zero; if every tier has the same missing values, those parity comparisons alone do not fail. Registry and manifest checks test path existence, not that each path is a readable regular file with valid content. Use separate source-presence, exact identity/content and archive-integrity checks before treating selected-count parity as validation.

The helper writes a complete temporary extraction for each selected archive, sequentially, then attempts cleanup in `finally` with removal errors ignored. It is not a write-free archive-list inspection; reserve temporary space for an extracted tier and verify cleanup after interruption. It uses the maintained safe-extraction preflight, whose member/path checks are separate from tier-content validation. No selected archive is rewritten by inspection. Exit zero reports no collected parity findings; one reports findings; two is explicitly used for no selected archives. Archive/read/extraction failures can raise exceptions before the report is produced, so absence of a receipt is not PASS.

`--json` prints the receipt. `--receipt-out <path>` creates parent directories and directly opens that destination for writing, including when parity fails; it has no fresh-destination or alias refusal and no atomic publication. Use a separate fresh receipt path outside source/archive evidence and retain stderr plus the actual return code. The receipt records archive basenames and selected observations, not archive paths/hashes, complete ID sets or a current-run source binding. Record those separately. `tools/release.sh` invokes this retained checker without `--receipt-out`; a successful console gate does not itself leave this JSON receipt. Sources: `tools/check_tier_parity.py:82–202`, `tools/tier_vocabulary.py:61–107`, `mamey/ziputil.py:114–189` and `tools/release.sh:80–84`.

## Historical note — preserved original body

The following wording records prior policy and tools descriptions. It does not override current user instructions, privacy profiles, CODE-only cut governance or the implementation limits above.

---

# Tier Differences — Sapote–Mamey Release Bundles

> **Historical (retired tiers).** Releases now cut the CODE tier only (`CUT_PROTOCOL.md`, since v9.7.444); the
> other tiers' tooling is disabled. This page describes how the retired tiers differed. Nothing here makes any
> tier "safe to share": disclosure follows each strain's exact assignment profile
> (`docs/PORTABLE_STRAIN_PRIVACY_AND_EVIDENCE.md`), not a tier name or an ID prefix.

The four-tier release system produces bundles that are **intentionally file-tree-identical
except for metadata redaction.** This is by design, not a packaging error.

## What differs between tiers

| File | CODE | CODE-analysis-free | COHORT-public | MERGED-PRIVATE |
|------|------|--------------------|------------|----------------|
| `TIER_MANIFEST.txt` | `tier=code` | `tier=clean` | `tier=cohort` | `tier=merged` |
| `SOURCE_CHECKSUMS_SHA256.txt` | per-tier checksums | per-tier checksums | per-tier checksums | per-tier checksums |
| Tracked payload other than tier identity/checksum records | same current payload | same current payload | same current payload | same current payload |

All other files (code, documentation, tests, data, prompts) are byte-identical across all four tiers.

**Historical correction.** The shipped v9.7.246 clean tier once differed from merged on 16 files, and
older text incorrectly described AS redaction. That measurement is retained as history only. The later
SID rewrite was removed in v9.7.364, and the current four-tier payload state is summarized above.

## Why the tiers exist

The four-tier structure is retained for **release discipline** (separating code, analysis-free
code, SID data banks, and the private merged scaffold), not for AS-strain-ID protection.

> **v9.7.156 (PI decision, 2026-06-30):** the AS-series privacy guard is **retired**. All AS
> strains have 16S rRNA on GenBank publicly associating strain number, genus, and host, and
> Sapote–Mamey ships concurrent with the associated publications — so BGC-level content is not
> meaningful additional disclosure. Real AS IDs in public tiers are no longer a leak; the AS-ID
> leak audit is now WARN (see `make_public_tier.sh AS_GUARD_RETIRED`). The redaction machinery is
> retained but inactive, reusable for any future genuinely-private cohort.

Historically (pre-v9.7.156): the tiers protected unpublished strain identifiers; real strain IDs
in public-facing cuts would have constituted a data leak. The redaction system
(`tools/redact_public_tier.py`) replaces
real AS-### identifiers with `AS-XXX` in the CHANGELOG and any analysis-specific outputs.

- **CODE** — the full bundle. For development and Patch Chat sessions.
- **CODE-analysis-free** — the analysis-free label in the current four-tier set; the retired SID
  uniformity rewrite is not applied.
- **COHORT-public** — leak-audited. Safe for external sharing. Since the AS guard was retired the audit is
  WARN for AS identifiers and hard-fail for `AJS-` / `PENDING-`.
- **MERGED-PRIVATE** — the cut source. Never distributed.

## Current label-only state and the retired SID scrub

The four canonical tiers are currently label-only variants: after the tier builders remove paths that
are absent from the sealed source and apply the shared public-content audit, their tracked payloads are
the same except for the tier identity recorded in `BUILD_STAMP.txt`, `TIER_MANIFEST.txt`, and the
resulting checksum records. This is a statement about the current sealed input, not a guarantee that
future tier payloads will remain identical.

The former CODE-analysis-free SID uniformity rewrite was removed in v9.7.364 (CUT-02, 2026-08-12).
SID identifiers are public, and the rewrite was both destructive to retained reference evidence and
ineffective as redaction because identifiers could remain in filenames and manifests. Therefore the
clean tier no longer rewrites SID content. The fail-closed public-content audit remains a separate
control and must not be described as a scrub.

`PUBLIC-RELEASE` is not a fifth synonym for these candidate tiers. It is a separately authorized
promotion state guarded by `GOV-001`; its tooling may describe or prepare an archive, but no candidate
becomes a public release without the active governance decision and release gates.

## Verification

`tools/check_tier_parity.py` verifies that the four tiers are structurally identical
except for the three expected differentials above. `tools/verify_tier_derivation.py`
confirms that public tiers are derived from the private tier by the live redaction logic.

---

*Sapote–Mamey*
