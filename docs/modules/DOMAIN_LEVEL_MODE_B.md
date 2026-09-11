# Domain-level Mode B

*Module added in v9.7.89. Post-seal, non-blocking domain evidence review.*

## What it does

Domain-level Mode B turns each top-lead BGC's protein domains into a structured evidence
review. It separates three things that AB/AF score and product label alone conflate:

1. **Score priority** — the AB/AF numbers (unchanged; from the engine).
2. **Architecture confidence** — how much real biosynthetic-core domain support a BGC has,
   versus accessory clutter (domain burden).
3. **Claim ceiling** — the safest thing that may be said from domain evidence, always
   architecture/family-level capacity language, never product identity.

Every domain is mapped to a controlled role category, per-BGC burden is computed, and a
safe/unsafe claim pair with a ceiling is assigned.

## How to run

```bash
# full per-domain detail from the antiSMASH source zip
python -m mamey domain-level --package COMPLETE_PACKAGE --source-antismash STRAIN.zip --top-n 10 --emit-figures

# or limited mode from the sealed gene context alone (domain names only)
python -m mamey domain-level --package COMPLETE_PACKAGE --top-n 10

# Mode B cards that consume the domain evidence
python -m mamey mode-b --package COMPLETE_PACKAGE --top-n 10 --with-domain-level

# figures only
python -m mamey render-figures --package COMPLETE_PACKAGE --figure-set domain-level
```

## Two input paths

- **Full (`--source-antismash`)** — re-parses the antiSMASH zip via `extract_domain_features`,
  giving every domain's name, description, and e-value.
- **Limited (sealed package only)** — falls back to the v9.7.88 sealed gene context
  (`<strain>_gene_context.jsonl`), which carries domain **names** but not descriptions or
  e-values. Clearly marked with `MODE_B_LIMITED_DOMAIN_CONTEXT.md`.

If neither is available, a `DOMAIN_LEVEL_SKIPPED_NO_GBK.md` receipt is written and the core
package stays valid.

## Outputs (`package/domain_level/`)

| File | Contents |
|------|----------|
| `domain_rows_long.csv` | one row per domain, with its role category |
| `domain_complexity_metrics_by_bgc.csv` | per-BGC total / core / tailoring / transport / regulatory burden |
| `domain_safe_unsafe_claims.csv` | per-BGC safe claim, unsafe claim, claim ceiling |
| `domain_role_counts_by_bgc.csv` | role tallies per BGC |
| `figures/` | role-burden heatmap, core-burden bar, per-BGC domain strips |
| `domain_level_receipt.json` | inputs, mode, counts, taxonomy/claim-safety versions |
| `OPEN_ME_FIRST_Domain_Level_ModeB.md` | front-facing summary |

## Rule files (versioned, auditable)

- `mamey/data/domain_level/domain_role_taxonomy.v1.json` — domain-name -> role mapping.
- `mamey/data/domain_level/domain_claim_safety.v1.json` — safe/unsafe claim ceilings.
- `mamey/data/domain_level/domain_figure_specs.v1.json` — figure style settings (out of code).

The taxonomy and claim-safety versions are stamped in `domain_level_receipt.json` so schema
drift is auditable.

## Limitations

- Role assignment is by domain-name substring; opaque identifiers (bare TIGRxxxxx, DUF families)
  fall to `Unknown/repeat/accessory` — honestly, not silently.
- Limited mode has no e-values or descriptions; the burden counts still hold, but the per-domain
  detail columns are blank.
- This is **annotate-only and post-seal**: it never changes scores and never blocks the package
  seal. It adds an evidence layer; it does not re-rank.

## Claim-safety reminder

Domain burden is evidence of biosynthetic capacity, not proof of a product. A high core-domain
count means more architecture support, never a stronger compound-identity claim. KCB remains
similarity, not identity. All language stays capacity-based.
