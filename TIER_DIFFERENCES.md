# Tier Differences — Sapote–Mamey Release Bundles

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
