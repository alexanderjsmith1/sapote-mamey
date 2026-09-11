# Patch note — native domain-level Mode B + figure pack (v9.7.89)

**Engine:** mamey 1.9.89 -> 1.9.90 · **Bundle:** 9.7.88 -> 9.7.89
**Scope:** annotate-only, post-seal. No scoring change. No scoring-boundary impact.

## Summary

Makes the domain-level analysis native, file-backed, post-seal, and figure-ready, per the
AS-XXX/AS-XXX patch request. Turns Mode B from ranked-lead explanation into biosynthetic
evidence review by separating score priority (AB/AF) from architecture confidence (domain
burden) from claim ceiling (what may safely be said).

Builds directly on the v9.7.88 sealed gene context: the limited path reads domain names from
`<strain>_gene_context.jsonl`; the full path re-parses the antiSMASH zip for descriptions and
e-values.

## What landed

**New module `mamey/domain_level.py`** — domain extraction (full from source zip / limited from
sealed gene context), role mapping, complexity metrics, claim ceilings. Post-seal, never raises,
writes failure receipts (`DOMAIN_LEVEL_SKIPPED_NO_GBK.md`, `..._LIMITED_PACKAGE_ONLY.md`,
`..._CLAIM_SAFETY_RULES_MISSING.md`, `MODE_B_LIMITED_DOMAIN_CONTEXT.md`).

**New module `mamey/domain_figures.py`** — three figures (role-burden heatmap, core-burden bar,
per-BGC domain strips), each with a companion data CSV and `figure_manifest.csv` rows.
Node-first labels, role-colored strand-aware arrows, accessory-collapse with a receipt.

**Rule files (versioned)** under `mamey/data/domain_level/`:
- `domain_role_taxonomy.v1.json` (20 role categories + 2 fallbacks)
- `domain_claim_safety.v1.json` (7 claim-ceiling rules, incl. SapB-like and cacaoidin cautions)
- `domain_figure_specs.v1.json` (role palette + style settings, out of code)

**CLI**:
- `domain-level --package --source-antismash --top-n --emit-figures --out` (post-seal, always
  returns 0 unless the package is unreadable)
- `mode-b --with-domain-level` (injects a domain burden + claim block into each card; adds
  Domain_total / Core_domain_burden / Tailoring_domain_burden / Domain_claim_ceiling CSV columns)
- `render-figures --figure-set domain-level`

**Workbook** — `master_workbook.update_domain_level_sheets` adds six sheets (Domain_Rows_Long,
Domain_Role_Counts_By_BGC, Domain_Role_Counts_By_Strain, Domain_Architecture_Strings,
ASModules_Domain_Level, Domain_Claim_Safety), created on demand so existing sheet gates are
untouched, idempotent per strain. Also adds Domain_total / Core_domain_burden /
Tailoring_domain_burden columns to B1_BGC_Master for cross-strain ranking beyond AB/AF.

**Docs / prompts / fixtures** — `docs/modules/DOMAIN_LEVEL_MODE_B.md`, three figure prompt specs,
`resources/reference_seed_inputs/README.md` (external-source policy), and a vendored synthetic
fixture (`tests/fixtures/domain_level_minimal_antismash.zip` + expected counts).

## Taxonomy note (for audit)

The role taxonomy is the engine's own judgment, validated against the AS-XXX/AS-XXX reference
output: 69% literal agreement on 893 rows. Most disagreements are cases where this taxonomy
assigns a **specific** role (Siderophore, Resistance, Regulatory) that the upstream pass left as
"Other" — i.e. corrections, not regressions. Opaque identifiers (bare TIGR/DUF) route to
Unknown/accessory by design.

## Verification

- `tests/test_domain_level_v9789.py` — role mapping, evalue-suffix handling, complexity,
  claim safety (incl. the no-product-identity invariant), command smoke, failure receipt,
  Mode B `--with-domain-level` injection.
- `tests/test_domain_figures_v9789.py` — figures render, nonzero dimensions, manifest matches files.
- `tests/test_domain_workbook_v9789.py` — six sheets populate, cross-strain burden lands,
  idempotent re-run, no-op when tables absent.

## What is NOT in this cut

- `domain_architecture_templates.v1.json` (request item 5) — the templates file is deferred;
  the architecture STRING per BGC is captured in the workbook sheet instead.
- aSModule monomer-pairing tables (the request's `antismash_module_summary` reference table)
  are not reproduced; the domain strip + burden carry the architecture signal.
- No real AS-XXX/AS-XXX zips are vendored (external-sidecar policy, request item 23).

## Contract reminder

Domain-level output lives in `package/domain_level/` as a post-seal supplement, OUTSIDE the
core checksum set (consistent with the Finding L figures-as-sidecar contract from v9.7.88).
