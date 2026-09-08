# Citation-Compact Mode

**Introduced:** proposed v9.7.136  
**Purpose:** reduce repeated claim-safety prose while increasing citation/evidence density.

---


## CLI Usage

Use citation-compact mode during `mamey run`:

```bash
python -m mamey run --strain <ID> --input-zip <antiSMASH.zip> --mode gold --capped-session --token-budget citation-compact --outdir <runs>
```

The compact outputs are emitted into the package before final manifest/checksum/ZIP sealing.

## Summary

Citation-compact mode is a reader-facing output profile. It does not weaken claim-safety. It changes where claim-safety appears.

Instead of repeating the same genome-mining caveat in every BGC card, the report says the caveat once, then uses structured fields:

- `interpretation_scope`
- `evidence_basis`
- `citation_basis`
- `uncertainty_flags`
- `next_experiment`

---

## Global BGC Caveat

Use one global caveat per report/package:

> Sapote-Mamey reports biosynthetic capacity from genome-mining evidence. Product identity, expression, compound abundance, and bioactivity require experimental confirmation unless separately shown.

Individual BGC cards should not repeat this paragraph.

---


## Literature Search Work Orders

Citation-compact mode does not invent citations. If a lead requires support but no verified citation is available, the package emits:

- `citation_compact/Literature_Search_WorkOrder.md`
- `citation_compact/Literature_Search_WorkOrder.json`

These files are instructions for a separate web/literature ChatGPT session. They ask that session to find DOI/PMID/primary-reference support, or return `citation_needed` if no support is found.

## Required Outputs

Citation-compact report generation should write:

- `Citation_Ledger.csv`
- `Citation_Ledger.json`

Priority leads should have a citation basis or an explicit `citation_needed` marker.

---

## Compact Lead Table Columns

| Column | Meaning |
|---|---|
| `lead_id` | stable lead identifier |
| `strain_id` | strain/source identifier |
| `bgc_id` | BGC identifier, if applicable |
| `stable_locus` | node/region locator |
| `lead_priority` | EXCEPTIONAL/HIGH/MEDIUM/etc. |
| `interpretation_scope` | what can safely be claimed |
| `evidence_basis` | extracted evidence anchors |
| `citation_basis` | references supporting class/family/method |
| `uncertainty_flags` | unresolved or risky assumptions |
| `next_experiment` | best practical next experiment |

---

## Validator Expectations

- repeated global caveat count must be ≤1;
- priority leads must include citation basis;
- missing citations must be explicit, not silent;
- templates must include citation-ledger output;
- compact templates must not include repeated citation-compact boilerplate.

---

## Why This Matters

Compact mode saves tokens, improves merge reliability across assistants, and makes reports easier for BGC researchers to audit.


---

## Citation-Compact Provenance and Citation Status

Sapote-Mamey uses citation-compact outputs to separate runtime evidence structure from literature verification.

- **antiSMASH 8.0** is recorded as method/database provenance for BGC detection and product/region calls: DOI `10.1093/nar/gkaf334`.
- **MIBiG 4.0** is recorded as reference-database provenance for curated BGC entries and KnownClusterBlast dereplication context: DOI `10.1093/nar/gkae1115`.
- **`PASS_STRUCTURE`** means the package structure, citation ledger, work-order files, compact reports, manifest tracking, and checksum tracking passed validation. It does **not** mean every literature claim has been manually verified.
- **`operator_supplied`** means the citation/provenance row came from runtime evidence or comparator fields already present in the package.
- **`citation_needed`** means literature support is missing and should be filled by a separate literature-search pass.
- **`Literature_Search_WorkOrder.md/json`** is a safe handoff for another ChatGPT/web-literature session. It is a search instruction, not a verified fact.

Current compact lead tables use `interpretation_scope` for reader-facing scope. The older reader-facing scope field should not appear in current citation-compact outputs.
