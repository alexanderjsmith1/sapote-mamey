# MODE_B_FULL20_CONTRACT_RECONCILIATION.md

## Purpose

This patch resolves Mode B artifact drift: previous outputs could look compliant because they had files, tables, trackers, PDFs, or character counts, while still failing to deliver a prose-first scientific Mode B interpretation.

## Decision

**Full Mode B = the exact 20-section prose-first contract in `docs/MODEB_CORRECTIVE_PROTOCOL.md` and `mamey/data/mode_b/modeb_full20_corrective_contract.json`.**

No assistant, renderer, prompt, or validator may invent section titles. The current section list is fixed until a developer edits the contract file and updates tests.

## Required wording

Use the following language across current docs and prompts:

> Full Mode B is the per-BGC prose-first 20-section interpretive report defined by `mamey/data/mode_b/modeb_full20_corrective_contract.json`. Older `§1–§8`, `§1–§10`, and earlier 20-title inventories are legacy/scaffold contracts and must not be used as the current Full Mode B schema. Evidence tables are appendices/supporting indexes, not substitutes for the card.

## Critical section placement

- §7 is **Transport, resistance, and regulation**.
- §16 is **BLASTP/HMMER next steps**.
- `Manual BLASTP evidence, if present` at §7 is obsolete and must fail validation.

## Operator rule

When a user asks for **full Mode B**, the assistant must produce sections 1–20 with the exact current titles for each requested BGC, or explicitly state that the output is a scaffold, partial card, candidate card, fragment card, abbreviated ledger, or evidence pack.

## Quality-gate rule

A card may not pass as `FULL` if it:

- lacks any of the 20 exact sections;
- uses old/invented section names;
- contains only legacy `§1–§8` or `§1–§10` content;
- turns §4 into a table dump without gene-by-gene prose;
- treats a PDF, FASTA, character count, or before/after tracker as acceptance evidence;
- silently omits unavailable evidence instead of naming the gap and next action;
- uses repeated gene-level claim-safety filler instead of a higher-level claim boundary.

## Non-goals

This patch does not delete historical docs. Historical docs must be labelled as such when cited. This patch does not require padding every section; short evidence-gap sections are acceptable when they are explicit and claim-safe.
