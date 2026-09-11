# Examples reference ledger — CLOSED

> **Status: resolved at v9.7.97.** All 8 `examples/` targets listed below were restored from the
> v9.7.72 CODE tier, and `tests/test_no_dangling_examples_refs_v9795.py` now enforces
> `DANGLING_BASELINE = frozenset()` — zero dangling references, permanently.
>
> This file is kept as a **closed-out record**, not a worklist. It was framed as an open decision
> ("restore vs rewrite") for 150 cuts after that decision had been made and executed. A reader at
> session start would conclude something is broken. Nothing is. (v9.7.247, F7.)

---

# Dangling `examples/` reference ledger — v9.7.96 (audit P-A6, re-confirmed at v9.7.96)

`examples/` is empty across all four tiers (already true in v9.7.94), but **10 live (non-historical)
documents still reference 8 distinct files under `examples/`**. Each reference is a dead pointer: a
user or LLM session that follows it finds nothing. None of this is a privacy or correctness risk — it
is accuracy/usability rot. Historical docs (CHANGELOG, `BUNDLE_PATCH_NOTES_*`, `RELEASE_NOTES_*`,
`PATCH_NOTES_*`) are intentionally excluded; their references describe past states.

I did **not** rewrite these references in this patch. Two reasons: (1) I can't restore the exemplar
*content* (the source files aren't in any tier I was given, and inventing exemplar text would violate
the no-fabrication rule); (2) for the exemplar references the right fix is genuinely your call —
**restore the files** (better for the prompts, which use them as quality benchmarks) **vs. rewrite the
pointers** to describe the format inline / mark the exemplar as externally maintained. This ledger is
the worklist; the guard test (`tests/test_no_dangling_examples_refs_v9795.py`) freezes the set below so
no *new* dangling `examples/` reference can be added unnoticed, and shrinks automatically as you fix these.

## A · Data/fixture references — broken runnable instructions (recommend: restore the fixture)

| Target | Referenced in | What breaks |
|---|---|---|
| `examples/test_data/smoke_antismash_small.zip` | `RELEASE_MANIFEST.md` (Gate-5 smoke-parse row) | The documented smoke-parse verification input is absent; the Gate-5 row can't be reproduced. `mamey doctor` also warns "no antiSMASH ZIPs". |
| `examples/test_data/test_master.xlsx` | `docs/PREREQUISITES.md` (schema-check example command), `README.md` (synthetic-fixture note) | The copy-paste `workbook_schema_check` command fails for a new user; the start-here note points at a missing file. |

These are small synthetic fixtures with no strain data. Restoring them is low-risk and fixes the
quickstart + Gate-5 reproducibility. If they are intentionally unbundled, the three references should
instead say "supply your own antiSMASH ZIP / workbook."

## B · Exemplar-format references — LLM/operator quality benchmarks (recommend: your call, restore vs rewrite)

| Target | Referenced in |
|---|---|
| `examples/layperson_guide_exemplar.md` | `prompts/CLAUDE_SYSTEM_PROMPT.md`, `prompts/FULL_RUN_PROFILE.md`, `docs/SAPOTE_MAMEY_BUNDLE_MONOLITH.md`, `docs/RELEASE_CHECKLIST_v9.md` |
| `examples/bench_guide_exemplar.md` | `prompts/CLAUDE_SYSTEM_PROMPT.md`, `prompts/FULL_RUN_PROFILE.md`, `docs/HOW_TO_USE.md`, `docs/SAPOTE_MAMEY_BUNDLE_MONOLITH.md` |
| `examples/fermentation_card_exemplar.md` | `prompts/CLAUDE_SYSTEM_PROMPT.md`, `docs/HOW_TO_USE.md`, `docs/SAPOTE_MAMEY_BUNDLE_MONOLITH.md` |
| `examples/citation_library_exemplar.md` | `prompts/CLAUDE_SYSTEM_PROMPT.md`, `docs/HOW_TO_USE.md`, `docs/BERT_MODE_PROTOCOL.md` |
| `examples/judgment_18strain/Lit_Verification_DAPR_New_Leads.md` | `docs/DAPR_CLASS_FRAMEWORK.md` |
| `examples/judgment_18strain/Lit_Verification_Routed_Out.md` | `docs/DAPR_CLASS_FRAMEWORK.md` |

These set output quality for the Sapote/ChatGPT sessions. Deleting the pointers degrades the prompts;
the better fix is usually to restore the exemplar files. Because they are pasted into LLM sessions that
can't open a missing path, leaving them dangling silently lowers deliverable quality.

## Recommended sequence
1. Decide bucket A: restore the two fixtures (preferred) or rewrite the three references.
2. Decide bucket B: restore the six exemplars (preferred — they drive prompt quality) or rewrite the pointers inline.
3. As each target is fixed, remove it from `DANGLING_BASELINE` in `tests/test_no_dangling_examples_refs_v9795.py`.
4. When the baseline is empty, tighten the guard to "zero dangling `examples/` refs allowed."

*Detector:* `python3 tools/check_dangling_refs.py` lists every dangling `examples/` reference on demand.
