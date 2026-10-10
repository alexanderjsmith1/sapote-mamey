# Citation-Compact Mode

Operational examples below use the bundle-local launcher. Run them with the selected compatible interpreter from the directory containing `pyproject.toml` and `mamey_run.py`; follow the current task/profile and input bindings in `AGENTS.md`. An installed console/module entry point is supported, but does not by itself select this bundle.


**Introduced:** historical proposal v9.7.136; current opt-in CLI output implementation exists  
**Purpose:** reduce repeated claim-safety prose while increasing citation/evidence density.

---


## CLI Usage

Use citation-compact mode during `python mamey_run.py run`:

```bash
python mamey_run.py run --strain <ID> --input-zip <antiSMASH.zip> --mode gold --capped-session --token-budget citation-compact --outdir <runs>
```

The run emits these supplements before its final manifest/checksum/ZIP sealing. The citation phase can catch an error, record ERROR/WARN and continue; inspect actual output, phase receipt and package validation rather than treating a run’s exit zero as proof of this optional set. It does not perform online citation verification.

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

These are proposed retrieval instructions for a separately authorized literature task. They do not send a message or perform a search. A returned identifier/status still needs bibliographic and passage-level support; unavailable/unassigned identifiers remain explicit gaps.

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
- **`PASS_STRUCTURE` in CITATION_COMPACT_QA.json** means the emitter’s priority citation-basis and global-caveat checks found no error. It does not establish sealing/checksum tracking or literature truth. The separate package compact gate reports PASS/FAIL/NOT_REQUESTED and checks its own required files, schema, tracking and checksums when present; it accepts a QA WARN as an allowed status, so preserve warnings rather than upgrading them into verified content.
- **`operator_supplied`** means the citation/provenance row came from runtime evidence or comparator fields already present in the package.
- **`citation_needed`** means literature support is missing and should be filled by a separate literature-search pass.
- **`Literature_Search_WorkOrder.md/json`** is a safe handoff for another ChatGPT/web-literature session. It is a search instruction, not a verified fact.

Current compact lead tables use `interpretation_scope` for reader-facing scope. The older reader-facing scope field should not appear in current citation-compact outputs.

The compact emitter replaces its fixed ledger, work-order and supplement paths. Do not invoke its
low-level writer against an immutable sealed source to “complete” citations. Selected compact report
text can use generic template placeholders; neither rendered prose nor a citation-needed record is
an accepted scientific interpretation. Global caveat counting is across the emitted compact Markdown
set, not a requirement to repeat the caveat once in every file. Source statuses are `verified`,
`citation_needed`, `not_applicable` and `operator_supplied`; syntactic acceptance of a status does
not independently verify its source. Keep package and resolver status vocabularies separate.
