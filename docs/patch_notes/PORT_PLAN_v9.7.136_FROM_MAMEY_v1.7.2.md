# Port Plan — v9.7.136 Citation-Compact from Mamey v1.7.2

**Source artifact inspected:** `Mamey_v1.7.2_Patched_Release`  
**Target base:** Sapote-Mamey v9.7.135  
**Port style:** selective conceptual port, not direct file replacement.

---

## 1. Useful Ideas to Port

The v1.7.2 patch contains several useful concepts:

| v1.7.2 idea | Port decision for v9.7.136 |
|---|---|
| `--token-budget citation-compact` | Keep as stable mode/profile name; exact CLI wiring can be finalized. |
| `Citation_Ledger.csv/json` | Port as structured output contract. |
| `citation_basis` on lead records | Port as required priority-lead field. |
| `evidence_basis`, `uncertainty_flags`, `next_experiment` | Port as compact lead-table columns. |
| one global BGC caveat | Port as report/package-level constraint. |
| compact report templates | Port as new `templates/citation_compact/` family. |
| repeated claim-ceiling suppression | Port to templates/output profile, not scoring. |

---

## 2. What Not to Port Directly

Do not wholesale copy v1.7.2 code into v9.7.136.

Reasons:

- v1.7.2 predates v9.7.135 release gates;
- it contains cache artifacts in the uploaded archive;
- it uses standalone module layout not aligned with current package structure;
- it predates current four-tier packaging, registry, and docs systems;
- reportlab-era PDF style files are not the current docs/PDF path.

---

## 3. Clean Port Strategy

Implement v9.7.136 as:

1. a small helper module: `mamey/citation_compact.py`;
2. JSON schemas under `schemas/`;
3. compact templates under `templates/citation_compact/`;
4. validator tests under `tests/`;
5. docs under `docs/CITATION_COMPACT_MODE.md`.

Then wire into CLI/report rendering in a second implementation patch if needed.

---

## 4. Implementation Phases

### Phase A — Contract and validation

- Add schemas.
- Add helper module.
- Add tests for coverage and caveat count.
- Add templates.

### Phase B — Runtime wiring

- Add `--token-budget citation-compact` or `--output-profile citation-compact`.
- Make package writers emit `Citation_Ledger.csv/json`.
- Add compact output to report render path.
- Add compact mode to docs and `mamey chatgpt-init` if public.

### Phase C — Benchmark

Run one before/after strain:

- AS-XXX, because timing evidence already exists; or
- AS-XXX, because poor assembly creates many repeated caveats and is a good stress case.

Metrics:

- total words/tokens in technical report;
- count of repeated caveat strings;
- number of populated citation rows;
- number of priority leads with citation basis;
- human readability.

---

## 5. Release Scope Recommendation

v9.7.136 should ship Phase A and, if time allows, Phase B. If Phase B is too invasive, ship Phase A as a public contract and run one patch cycle for wiring.

Do not destabilize v9.7.135.
