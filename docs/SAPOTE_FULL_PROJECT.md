# Sapote Full Project — Pointer

The full Sapote monolith workflow (v9.4) is provided as:

**`docs/SAPOTE_MAMEY_BUNDLE_MONOLITH.md`** — the complete analytical specification (~6,600 lines, §0–§57).

The monolith is the analytical design reference (since v9.4).

> **Scope and precedence (v9.7.447).** Operational startup is governed by `AGENTS.md` and `docs/ASSISTANT_GOVERNANCE.md`; they take precedence over this document. The task the user asked for sets the scope: reading this file never expands a review into a run, a full-suite authoring job, or a release. A version stamp at the top records version synchronization, not a full content review.

It may be loaded into a project knowledge file as reference material. It is not system instructions, and it does not override the current operating contract.
It contains the full cross-strain CCSM, literature deep-dive protocols, manuscript
support, figure layout, ecological synthesis, and all sections (§0–§57) including
§54 Output Registry, §56 Benchmarking, and §57 Per-Class Sub-Grades restored in v9.3.

For per-strain analysis without cross-strain features, use the lightweight
**`SAPOTE_SLIM_JUDGMENT_KERNEL.md`** (~320 lines, ~5K tokens) instead.

See `HOW_TO_USE.md` for the two-stage workflow (Mamey extraction → judgment).


## Release 1 workbook compatibility note

Sapote monolith uses the self-contained **Sapote-Mamey Release 1 Workbook Standard** in Section 18 of `docs/SAPOTE_MAMEY_BUNDLE_MONOLITH.md`. This keeps Sapote standalone while ensuring Mamey executable, Sapote monolith, and Sapote slim converge on the same workbook/package deliverable.
