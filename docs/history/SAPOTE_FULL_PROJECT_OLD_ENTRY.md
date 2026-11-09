# Sapote Full Project — Pointer

## Current reading route

Start with [the current human guide](../GUIDE/00_README.md), [assistant governance](../ASSISTANT_GOVERNANCE.md)
and [large-reference entry guide](../GUIDE/07_LARGE_REFERENCE_ENTRY.md). The historical recommendation below
to use the slim kernel for a new per-strain session is superseded: the slim file itself is explicitly
deprecated. Select the task/profile through current governance and the [Mode B profile matrix](../MODEB_PROFILE_MATRIX.md),
not a historical full-run/archive trigger. Reference content does not activate all modules or authorize jobs.

The monolith is a maintained analytical-design/history reference with separate full-read and spot-vet
anchors, not a statement that every paragraph is current executable behavior. Its Release 1 workbook note
is a design reference; actual [workbook schema](../WORKBOOK_SCHEMA.md) and source owners determine compatibility.
Version synchronization is not full content/scientific review. Read existing large references in place;
do not duplicate them into a handoff, and preserve exact source paths/SHA-256 plus scoped holds.

<!-- Historical source text follows. -->
**Historical:** the text below is the original entry. Its advice to use the slim kernel for per-strain work is superseded (see the reading route above).


The full Sapote monolith workflow (v9.4) is provided as:

**`docs/SAPOTE_MAMEY_BUNDLE_MONOLITH.md`** — the analytical specification (§0–§57 in the historical text; the current file has 5,151 lines, not the ~6,600 this page once gave).

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

Sapote monolith uses the self-contained **Sapote-Mamey Release 1 Workbook Standard** in Section 18 of `docs/SAPOTE_MAMEY_BUNDLE_MONOLITH.md`. Historical: the original sentence here said this keeps Sapote standalone while Mamey, the Sapote monolith and Sapote slim "converge on the same workbook/package deliverable". That was a design intention, not a guarantee. The per-strain workbook (`mamey/workbook.py`) and the master workbook (`mamey/master_workbook.py`) are separate writers with their own sheet definitions, and the Release 1 standard describes neither exactly. Use the [workbook schema](../WORKBOOK_SCHEMA.md) and the writers themselves for the sheets a run produces.
