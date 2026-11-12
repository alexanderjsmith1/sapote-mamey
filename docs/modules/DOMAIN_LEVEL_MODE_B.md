# Domain-level Mode B

Optional, and run after scoped validation of an authorized working copy. It does not change triage scores, but may refuse or fail and can write inside the package. For terms such as BGC, package and Mode B, see the [glossary](../GLOSSARY.md).

## What it does

Domain-level Mode B turns each top-lead BGC's protein domains into a structured evidence
review. A top lead is a cluster near the top of the triage board, which ranks clusters by their antibacterial (AB) and antifungal (AF) scores. The review separates three things that a score and a product label blur together:

1. **Score priority** — the AB and AF numbers (unchanged; from the engine).
2. **Architecture confidence** — how much real biosynthetic-core domain support a BGC has,
   versus accessory clutter (domain burden).
3. **Claim ceiling** — the safest thing that may be said from domain evidence, always
   architecture/family-level capacity language, never product identity.

Retained domain observations are mapped to controlled role categories, per-BGC burden is computed, and a safe/unsafe claim pair with a ceiling is assigned. This is not a census of every domain in the source genome. Top-N selection uses eligible triage rows ranked by AB+AF; missing/partial triage or source coverage is not repaired into a full inventory. Verify that every selected triage ID binds uniquely to the manifest and its full strain / full contig / region / BGC alias. The selector can retain a triage-only ID with missing manifest context; missing or conflicting binding is a hold, not validated identity.

## How to run

```bash
# full per-domain detail from the antiSMASH source zip
python mamey_run.py domain-level --package runs/EXAMPLE/package --source-antismash path/to/antismash_result.zip --top-n 10 --emit-figures --out reviews/EXAMPLE-domain-full

# or limited mode from the package gene context alone (domain names only)
python mamey_run.py domain-level --package runs/EXAMPLE/package --top-n 10 --out reviews/EXAMPLE-domain-limited

# Mode B cards with a domain block (reads <package>/domain_level/ only)
python mamey_run.py mode-b --package runs/EXAMPLE/package --top-n 10 --with-domain-level

# figures only (reads <package>/domain_level/ only)
python mamey_run.py render-figures --package runs/EXAMPLE/package --figure-set domain-level
```

Pass a fresh external output path, for example `--out reviews/EXAMPLE-domain-new`, when the package is sealed and must stay unchanged; see [post-seal readers](../POSTSEAL_READERS.md). Without `--out`, the command writes `domain_level/` inside the package.

The last two commands do not read a `--out` folder. They read `<package>/domain_level/`. If that folder has no `domain_complexity_metrics_by_bgc.csv`, they run domain-level themselves and write its tables into the package, and they print a line saying so. With `--with-domain-level`, `mode-b` uses tables already in `<package>/domain_level/` even when they came from an earlier run. So an external `--out` run is not picked up by these commands, and running them can change the package.

The output folder must be fresh. If it already holds any file domain-level writes (a table, a card such as `DOMAIN_LEVEL_SKIPPED_NO_GBK.md`, or `domain_level_receipt.json`), the command prints `domain-level: REFUSED`, names the files, writes nothing and exits 2. `--emit-figures` renders nothing after a refusal. Choose a new `--out` folder; the earlier files are kept.

### What you should see

Read `domain_level_receipt.json` and any named skip card first. On `OK`, open `OPEN_ME_FIRST_Domain_Level_ModeB.md` in the output folder. If you find `DOMAIN_LEVEL_SKIPPED_NO_GBK.md` instead, nothing was analyzed. The command exits 0 for `OK` and for two documented skips: no domain context (that file), and no eligible top BGC. Every other skip, including a source-archive digest mismatch, exits 2. So a 0 exit can still mean nothing was analyzed; check for the file and read the receipt. A failed figure render is only a warning and does not change the exit code.

## Two input paths

- **Full (`--source-antismash`)** — re-reads the antiSMASH zip,
  giving every retained domain's name, description, and e-value. The archive is used only when
  its SHA-256 matches `input_zip_sha256` in the package manifest, because its features are joined
  to the package's BGCs by contig name and coordinates. A mismatch writes
  `DOMAIN_LEVEL_SOURCE_ZIP_MISMATCH.md` and a SKIPPED receipt. When either digest is missing
  (an older package, or a source folder rather than a file), or the archive is not found, the
  archive is not used and the run falls back to limited mode. The receipt records
  `source_antismash_sha256` and `source_binding` (`MATCHES_MANIFEST_INPUT_ZIP_SHA256`,
  `SOURCE_ZIP_DIGEST_MISMATCH`, `SOURCE_ZIP_DIGEST_UNBOUND` or `SOURCE_ZIP_UNAVAILABLE`).
- **Limited (sealed package only)** — falls back to the package's gene context
  (`<strain>_gene_context.jsonl`), which carries domain **names** but not descriptions or
  e-values. Clearly marked with `MODE_B_LIMITED_DOMAIN_CONTEXT.md`.

When neither route yields domain context, the helper writes `DOMAIN_LEVEL_SKIPPED_NO_GBK.md` and a SKIPPED receipt. A failed or empty source read falls back to gene context. Read `mode` and the warnings in `domain_level_receipt.json` to see which route ran.

`core_package_valid` in the receipt is always true. The command does not validate the package, so run `validate` yourself.

## Outputs (`domain_level/` in the package, or your `--out` folder)

| File | Contents |
|------|----------|
| `domain_rows_long.csv` | one row per domain, with its role category |
| `domain_complexity_metrics_by_bgc.csv` | per-BGC total / core / tailoring / transport / regulatory burden |
| `domain_safe_unsafe_claims.csv` | per-BGC safe claim, unsafe claim, claim ceiling |
| `domain_role_counts_by_bgc.csv` | role tallies per BGC |
| `figures/` | requested role-burden figures only when the selected rendering route succeeds; inspect its actual output and warnings |
| `domain_level_receipt.json` | inputs, mode, counts, taxonomy/claim-safety versions |
| `OPEN_ME_FIRST_Domain_Level_ModeB.md` | front-facing summary |

Use a fresh `--out` folder for each run; an occupied one is refused (see above). The handled failures (missing rule files, no manifest, no eligible BGCs, no domain context, a source digest mismatch) write a named card and a SKIPPED receipt. Other errors, such as an unreadable manifest or triage board or a write error, stop the command without a receipt, and files written before the error stay in the folder. The command exits 0 after the two documented skips (no domain context, no eligible top BGC) and when figure rendering fails, so list the folder after every run. A refusal and the other skips exit 2. The receipt records counts, rule versions and the source digest, not output-file hashes. Look at each figure yourself.

## Rule files (versioned, auditable)

- `mamey/data/domain_level/domain_role_taxonomy.v1.json` — domain-name -> role mapping.
- `mamey/data/domain_level/domain_claim_safety.v1.json` — safe/unsafe claim ceilings.
- `mamey/data/domain_level/domain_figure_specs.v1.json` — figure style settings (out of code).

The taxonomy and claim-safety versions are stamped in `domain_level_receipt.json` so schema
drift is auditable.

## Limitations

- Role assignment uses the selected taxonomy and substring matching, with an explicit TIGR map when present. Unmapped bare TIGR identifiers and other unmatched names fall to `Unknown/repeat/accessory`; that fallback is not proof of an accessory biological function.
- Limited mode has no e-values or descriptions; the burden counts still hold, but the per-domain
  detail columns are blank.
- It does not change triage scores or re-rank; it can refuse, fail or leave partial files. Its receipt is not package validation.

## Claim-safety reminder

Domain burden summarizes retained annotation matches and can support a capacity hypothesis; missing or zero counts are not a completed negative search by themselves. A high core-domain
count means more architecture support, never a stronger compound-identity claim. KCB remains
similarity, not identity. All language stays capacity-based.
