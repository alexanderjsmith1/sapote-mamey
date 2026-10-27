# Domain-level Mode B

Optional, after validation. It never changes scores or blocks the package.

## What it does

Domain-level Mode B turns each top-lead BGC's protein domains into a structured evidence
review. It separates three things that AB/AF score and product label alone conflate:

1. **Score priority** — the AB/AF numbers (unchanged; from the engine).
2. **Architecture confidence** — how much real biosynthetic-core domain support a BGC has,
   versus accessory clutter (domain burden).
3. **Claim ceiling** — the safest thing that may be said from domain evidence, always
   architecture/family-level capacity language, never product identity.

Retained domain observations are mapped to controlled role categories, per-BGC burden is computed, and a safe/unsafe claim pair with a ceiling is assigned. This is not a census of every domain in the source genome. Top-N selection uses eligible triage rows ranked by AB+AF; missing/partial triage or source coverage is not repaired into a full inventory.

## How to run

```bash
# full per-domain detail from the antiSMASH source zip
python mamey_run.py domain-level --package COMPLETE_PACKAGE --source-antismash STRAIN.zip --top-n 10 --emit-figures

# or limited mode from the sealed gene context alone (domain names only)
python mamey_run.py domain-level --package COMPLETE_PACKAGE --top-n 10

# Mode B cards that consume the domain evidence
python mamey_run.py mode-b --package COMPLETE_PACKAGE --top-n 10 --with-domain-level

# figures only
python mamey_run.py render-figures --package COMPLETE_PACKAGE --figure-set domain-level
```

Run it on a working copy if the sealed package must stay unchanged; see [post-seal readers](../POSTSEAL_READERS.md).

## Two input paths

- **Full (`--source-antismash`)** — re-parses the antiSMASH zip via `extract_domain_features`,
  giving every domain's name, description, and e-value.
- **Limited (sealed package only)** — falls back to the package's gene context
  (`<strain>_gene_context.jsonl`), which carries domain **names** but not descriptions or
  e-values. Clearly marked with `MODE_B_LIMITED_DOMAIN_CONTEXT.md`.

When neither route yields retained domain context, the helper writes `DOMAIN_LEVEL_SKIPPED_NO_GBK.md` and a SKIPPED receipt. A failed source parse can fall back to gene context; an empty source result also falls back. Read the actual `mode`, warnings and per-locus coverage. `full_source`/`FULL` identifies the source route, not a complete-source extraction certificate.

The receipt initializes `core_package_valid=true`; it does not run package validation. This field and normal command completion cannot establish that an input was valid or sealed. Preserve and read the independent package validator and integrity evidence.

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

Use `domain-level --out <fresh-external-directory>` when the package must remain unchanged. The default writes under the supplied package; existing fixed output names are reused. Tables, optional extensions and receipt are published separately, so failure can leave partial output or a previous receipt. Retain prior evidence and inspect the current artifact roster before a retry.

The CLI can return zero for SKIPPED enrichment or failed optional figure rendering. Its receipt records counts and rule versions, not a complete source/output hash binding; preserve exact package/archive, code, configuration and output hashes separately. A rendered file is not visual QA. No enrichment receipt establishes scientific acceptance.

## Rule files (versioned, auditable)

- `mamey/data/domain_level/domain_role_taxonomy.v1.json` — domain-name -> role mapping.
- `mamey/data/domain_level/domain_claim_safety.v1.json` — safe/unsafe claim ceilings.
- `mamey/data/domain_level/domain_figure_specs.v1.json` — figure style settings (out of code).

The taxonomy and claim-safety versions are stamped in `domain_level_receipt.json` so schema
drift is auditable.

## Limitations

- Role assignment is by domain-name substring; opaque identifiers (bare TIGRxxxxx, DUF families)
  fall to `Unknown/repeat/accessory`.
- Limited mode has no e-values or descriptions; the burden counts still hold, but the per-domain
  detail columns are blank.
- This is **annotate-only and post-seal**: it never changes scores and never blocks the package
  seal. It adds an evidence layer; it does not re-rank.

## Claim-safety reminder

Domain burden is evidence of biosynthetic capacity, not proof of a product. A high core-domain
count means more architecture support, never a stronger compound-identity claim. KCB remains
similarity, not identity. All language stays capacity-based.
