# GATE & REFERENCE-DATA INTEGRITY AUDIT — v9.7.96

**From:** Patch Chat (audit thread) · **Date:** 2026-06-20 · **Against:** sapote-mamey v9.7.96 / engine 1.9.96

You asked me to look for *larger issues* — the same method that caught the orphaned `sync_version` gate, applied broadly to every check/gate/tool and to reference-data integrity. It found more of the same class, and they share one root cause.

---

## The throughline: single-source-of-truth violations

Every defect in this audit arc is the same shape — **a fact or a piece of logic was copied instead of derived/imported, then drifted:**

| Finding (this arc) | What was copied | How it drifted |
|---|---|---|
| `sync_version` orphaning | the gate was a tool nothing *ran* | shipped version-stale, invisibly |
| `BUNDLE_VERSION` literal | hand-copied bundle version | stale at 9.7.91 → mislabeled every output zip |
| AS-48 / ISID-XXX | redactor over-matched public names | corrupted shipped MIBiG reference data |
| **`verify_tier_derivation` (new)** | **inlined copy of the redaction logic** | **lacked the AS-48 carve-out → reported false drift** |

The fix in every case is the same principle: **derive or import from one source; never duplicate.** That's the lens for the readiness scorecard.

---

## Findings & status

### F1 — `verify_tier_derivation.py`: orphaned **and** carrying stale duplicated logic  *(FIXED + WIRED)*
The tool designed to be "the cheap parity check that replaces re-running the full pytest suite per tier" was wired into **neither pytest nor the cut**. Worse, it **re-implemented the redaction logic inline** (its own docstring admitted it should import instead) — and that copy had drifted: it lacked the v9.7.97 AS-48 carve-out, so it reported **false drift** on every file mentioning `enterocin AS-48`.
- **Fixed:** it now imports `redact_text`/`redact_py` from the live `redact_public_tier.py` (one source of truth). Re-ran against a real cut: **568 files, 0 mismatches, exit 0**.
- **Wired:** added as a fail-closed **tier-derivation parity gate** in `make_public_tier.sh` (section 3d) for the code/clean tiers (pure redaction-views; the sid tier applies extra SID anonymization so it's excluded by design). Confirmed firing: `tier-derivation parity gate: OK (public == redact(private))`.

### F2 — `.pytest_cache` scrubbed *after* the leak audit, not before  *(FIXED)*
The cut stripped `.pytest_cache` at section 3a — but the leak audit runs at section 3, **before** it. A cache carrying strain IDs in its cached test node-ids would fail the audit (or, worse, the ordering masked that the strip was load-bearing). Caught live: a stale cache leaked `AS-XXX`/`AS-XXX` node-ids and the cut refused.
- **Fixed:** added a `.pytest_cache` strip in the early cache-scrub (section 1), *before* the leak audit. Re-cut clean.

### F3 — `ISID-XXX`: a redactor corruption of a public MIBiG organism name  *(FLAGGED — needs online restoration)*
`mibig_reference_index.bacterial.json` carries `"Streptomyces sp. ISID-XXX"` (ncbiTaxId 2601673). An older redactor pattern matched `SID\d+` *inside* the organism string and scrubbed it; **the original strain number is gone** (irrecoverable offline). The current regex has the `\b` boundary and won't re-corrupt it, and the AS-48 carve-out (batch 2) handles that sibling case — but this one needs the authoritative MIBiG/NCBI organism name restored from taxId 2601673. **I will not guess the number.**
- **Recommend:** a guard test asserting no MIBiG `taxonomy.name` / `compounds[]` field contains `-XXX` (add once ISID is restored, so it stays a tripwire).
- **Left untouched (correctly):** the three `AJS-XXX` genus entries in `reference_bgc_library.json` are *deliberate* redactions of a private class-anchor strain — un-redacting would be a privacy leak.

### F4 — `check_tier_parity.py`: orphaned (manual-only)  *(DOCUMENTED)*
Referenced only in `docs/BUNDLE_CAPABILITIES.md`, run by nothing automatically. It checks tier *sameness* (versions/cassettes/markers identical across tiers) — which, recall, is why the v9.7.91 version desync passed parity. It's a useful post-cut tool but isn't a wired gate. Recommend either wiring it into the build (it needs all four tier zips, so it runs *after* the four cuts) or formalizing it as a documented manual release step.

### F5 — my own AS-48 test used **real cohort IDs**  *(FIXED — and the guard caught it)*
The batch-2 `test_as48_public_np_carveout.py` used `AS-XXX`/`AS-XXX`/`AS-XXX` (real cohort strains) as redaction fixtures — exactly the leak anti-pattern the v9.7.88 `tests/` audit exists to stop. The cut **refused to ship**, correctly. Rewritten to synthetic IDs (`AS-XXX/902/903`); `AS-48`/`AS-XXX` added to `test_synthetic_ids.txt` with provenance. This is a clean demonstration that the leak guard is robustly wired.

### F6 — un-wired QA/audit tools  *(TRIAGE — needs your read)*
Five tools are neither tested nor cut-wired: `schema_deployed_audit.py`, `mamey_package_qa_v2.py`, `assembly_qc_check.py`, `check_deliverable_suite.py`, `wac_validation_genelevel.py`. Most read like *operator* tools (run by hand during analysis), not release gates — but `schema_deployed_audit` and `mamey_package_qa_v2` sound gate-like. Worth a pass to decide which (if any) should be wired, and to delete or clearly label the rest as operator-only so the next audit doesn't re-flag them.

---

## What's verified now
A full `code`-tier cut runs end-to-end (exit 0) with every gate firing: `version-sync gate: OK` → cassette redaction (48 IDs, CAS intact) → `tier-derivation parity gate: OK` → leak audit `0 AS` → zip. JSON across `mamey/data` all valid. `verify_tier_derivation` 0 mismatches.

## Files changed (staged in `audit_batch3/`)
- `tools/verify_tier_derivation.py` — import SSOT (no inlined copy)
- `tools/make_public_tier.sh` — early `.pytest_cache` strip + wired parity gate (on top of batch-2's sync gate)
- `tools/redact_public_tier.py`, `tests/test_as48_public_np_carveout.py`, `tools/test_synthetic_ids.txt` — AS-48 carve-out + synthetic-ID test (supersedes batch 2)
- `tools/log_release.py` (NEW) — idempotent RELEASES_LOG appender (see DAPR/leftover note)
- `mamey/data/mibig/*` — AS-48 restoration (from batch 2)

## Still needs you
- **F3 ISID-XXX:** restore organism name from MIBiG/NCBI taxId 2601673 (online).
- **F6:** decide which QA tools are gates vs operator-only.
