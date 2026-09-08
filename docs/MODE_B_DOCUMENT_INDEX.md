# MODE_B_DOCUMENT_INDEX.md

**Sapote–Mamey v9.7.319 / Mamey 1.9.111 / build 20260628v97144b**

Purpose: give ChatGPT, Claude, patch-chat reviewers, and human operators one authoritative map of where Mode B instructions live in the bundle. This file is an index, not a replacement for the source documents. Read the listed files before proposing Mode B patches or producing scientific Mode B interpretations.

---

## 0. Mandatory first-read bootstrap

Read these before any run, audit, patch, or Mode B analysis.

| Priority | Path | Why it matters |
|---:|---|---|
| 1 | `000_READ_ME_FIRST_CHATGPT_CLAUDE.md` | Root bootstrap. Defines assistant routing, six-place discoverability contract, timeout-safe defaults, and the v9.7.143b Mode B workflow note. |
| 2 | `CHATGPT_START_HERE.md` | Authoritative ChatGPT operating contract. Defines read-proof sentence, staged workflow, smoke-first rule, Mode B continuation path, current build gotchas, and v9.7.143b Mode B requirements. |
| 3 | `CHATGTP_READ_ME_FIRST.md` | Optional accidental-typo rescue alias for ChatGPT→ChatGTP transposition. It points back to the real ChatGPT instructions and is not authoritative. |
| 4 | `README_START_HERE.md` / `README.md` | Human-facing package entry points; verify that they point to the same current workflow. |
| 5 | `CURRENT_DOCS_INDEX.md` | Current broad documentation map. Use as orientation, but verify whether it is up to date for v9.7.143b. |

**ChatGPT read-proof:** if asked whether ChatGPT-specific instructions were found, emit the live read-proof required by `CHATGPT_START_HERE.md` and include the current bundle / engine / build values from the file, not from memory.

---

## 1. Current Mode B workflow documents

These are the most relevant files for Mode B behavior in this cut.

| Priority | Path | Status / use |
|---:|---|---|
| 0 | `docs/reference/modeb_exemplars/phosphonate_reference_full48_no_blastp_exemplar.md` | Current §1–§48 typed-terminal format exemplar. Shows exact-locus writing, complete CDS accounting, all-stream disposition, and a typed no-BLASTP fixture without invented hits. It is not positive substantive calibration for §§20, 39, 40, 42, or 48. |
| 0A | `docs/MODEB_LLM_AUTHORING_CONTEXT_HYGIENE.md` | Defines the minimal scientific context passed to an LLM and excludes distribution stamps and unrelated packaging state from card authoring. |
| 1 | `docs/MODEB_CORRECTIVE_PROTOCOL.md` | Current prose-first Mode B corrective protocol. Owns the exact §1–§30 section titles and artifact-drift quality gate. |
| 2 | `docs/MODEB_EVIDENCE_ESCALATION_WORKFLOW_v97143a.md` | Focused Mode B escalation workflow. Read this before interpreting large modular proteins, repeated comparator hits, split/composite loci, or comparator axes. |
| 3 | `mamey/patches/MODEB_COMPARATOR_WORKFLOW_USER_GUIDANCE_v97143a.md` | Patch-master packet for comparator lessons. Defines Mode B as an interactive evidence-escalation workflow, not a static BLASTP table. |
| 4 | `docs/modules/MODE_B_WRITE.md` | Persistence protocol and full card contract history. Defines the §1–§10 card, §9/§10 gate, §11–§20 enrichment floor, write-back, claim-safety placement, and workbook/judgment persistence. |
| 5 | `docs/modules/MODE_B_BATCH_RUN.md` | Batch execution protocol for full Mode B. Defines rank-ordered batches, default batch size guidance, quality gates, resume behavior, compile gate, and fragment exceptions. |
| 6 | `docs/modules/DOMAIN_LEVEL_MODE_B.md` | Domain-level Mode B add-on. Defines architecture confidence, domain-burden evidence, claim ceiling, safe/unsafe claim pairs, and `--with-domain-level` usage. |
| 7 | `docs/PER_MODE_ARTIFACT_SET.md` | Explains which artifacts exist in smoke / standard / gold. Important because Mode B cards are on-demand, while gene context is core and `deep_data.json` / `gene_data.json` are gold-only. |
| 8 | `docs/PER_BGC_PAGE_LAYOUT_SPEC.md` | Layout contract for compiled reports: locus map + class line + Mode B card must stay together as one BGC page-unit. |
| 9 | `docs/DELIVERABLE_CONTRACT.md` | Broader deliverable contract. Read for report packaging, per-BGC accounting, and compiled output expectations. |

---

## 2. Mode B implementation files

Read these when checking what the code actually enforces.

| Path | What to inspect |
|---|---|
| `mamey/chatgpt_commands.py` | ChatGPT-facing commands, including `mode_b_command`, coverage behavior, and strict/top-n behavior. |
| `mamey/gene_by_gene.py` | Gene-by-gene extraction and tabulation logic. |
| `mamey/mode_b/schema.py` | Mode B gene-table schema. Important for preserving `protein_length_aa` and normalizing `query_length`. |
| `mamey/mode_b/guards.py` | Large-protein misannotation guard; prevents huge SDR/oxidoreductase-labelled modular proteins from being treated as small enzymes. |
| `mamey/mode_b/comparator_workflow.py` | Detects repeated comparator hits and renders comparator next-step guidance. |
| `mamey/mode_b/claim_safety.py` | Split/composite status labels and conservative claim notes. |
| `mamey/mode_b_quality_gate.py` | Priority-tier-aware depth gate; checks section presence, length floors, fragment exemptions, and enrichment sections. |
| `mamey/mode_b_receipt.py` | Sapote Mode B persistence / receipt ingestion front door. |
| `mamey/validators/modeb_full20.py` | Validator for the exact corrective-protocol §1–§20 Mode B sections. Read this before claiming a §1–§20 contract is implemented. |
| `tools/build_modeb_deepdive.py` | Tooling for Mode B deep-dive generation. |

---

## 3. Mode B tests and acceptance gates

These tests are part of the instruction set because they encode expected behavior.

| Path | Behavior encoded |
|---|---|
| `tests/test_modeb_workflow_v97143a.py` | AS-XXX regression lessons: `protein_length_aa` required; huge small-enzyme-labelled proteins trigger warnings; NODE_24/NODE_30 trigger NPDC041969 comparator guidance; NODE_58 must not collapse into that comparator model. |
| `tests/test_modeb_coverage_contract.py` | Mode B coverage receipt behavior: `--top-n` is not full-inventory coverage; partial native coverage is reported; `--strict-all` fails on missing cards. |
| `tests/test_mode_b_quality_gate.py` | Quality gate: §1–§10 presence, priority character floors, §11–§20 enrichment block, fragment exemption, and section-number parsing. |
| `tests/test_mode_b_receipt.py` | Receipt ingestion and persistence behavior. |
| `tests/test_mode_b_fixture.py` | Fixture-level Mode B expectations. |

---

## 4. Resolved Mode B contract hierarchy

The bundle previously contained overlapping Mode B depth language. This patch resolves the hierarchy rather than creating a new fourth contract.

| Source | Reconciled status |
|---|---|
| `CHATGPT_START_HERE.md` and older broad docs referring to `§1–§8` | Legacy compact/core-spine language. Must not be used as the complete Full Mode B contract. |
| `docs/modules/MODE_B_WRITE.md` | Transitional implementation gate. The `§1–§10` card and `§11–§20` enrichment floor remain active quality/depth checks. |
| `docs/modules/MODE_B_BATCH_RUN.md` | Transitional batch execution protocol. Update wording from `full §1–§10` to `Full Mode B §1–§20 with §1–§10 depth gate`. |
| `mamey/mode_b_quality_gate.py` and `tests/test_mode_b_quality_gate.py` | Existing depth/character/fragment gate. Keep as additive quality gate, not the definition of Full Mode B. |
| `mamey/validators/modeb_full20.py` | Canonical named-section inventory for public Full Mode B. |

**Resolved policy:** Full Mode B uses the exact §1–§48 contract in `mamey/data/mode_b/modeb_full30_corrective_contract.json` (`modeb_corrective_full48_v1`). The older class exemplars and §1–§30 documentation remain historical calibration until upgraded. `mamey/validators/modeb_full20.py` is a legacy facade, not the current completeness definition.

**Output rule:** if an assistant or report says `full Mode B`, it must satisfy the current §1–§48 contract or explicitly identify itself as partial, reference-authoring exemplar, fragment-level, or ledger-only.

---

## 5. Placeholder / caution files

| Path | Caution |
|---|---|
| `docs/SOPs/SOP-06_Mode_B_BGC_Card_Production.md` | Explicitly marked `PLACEHOLDER / OUTLINE ONLY`. Do not treat as completed operator instructions until that status line is removed. |
| Older prompt files under `prompts/` and standalone docs | May be superseded by `CHATGPT_START_HERE.md`. Use only after checking version stamps and current-start-file guidance. |
| Historical patch notes | Useful provenance, not automatically current behavior. Prefer current tests and active docs. |

---

## 6. Practical reading order for a new assistant session

1. `000_READ_ME_FIRST_CHATGPT_CLAUDE.md`
2. `CHATGPT_START_HERE.md`
3. `CURRENT_DOCS_INDEX.md`
4. `docs/MODEB_CORRECTIVE_PROTOCOL.md`
5. `docs/MODEB_EVIDENCE_ESCALATION_WORKFLOW_v97143a.md`
6. `docs/modules/MODE_B_WRITE.md`
7. `docs/modules/MODE_B_BATCH_RUN.md`
8. `docs/modules/DOMAIN_LEVEL_MODE_B.md`
9. `mamey/patches/MODEB_COMPARATOR_WORKFLOW_USER_GUIDANCE_v97143a.md`
10. `mamey/validators/modeb_full20.py`
11. The relevant tests in `tests/test_modeb_workflow_v97143a.py`, `tests/test_modeb_coverage_contract.py`, and `tests/test_mode_b_quality_gate.py`

Only after this sequence should an assistant propose Mode B patches, judge whether a Mode B output is complete, or generate a full BGC interpretation.

---

## 7. Search commands to rediscover this index manually

From the repository root:

```bash
find . -type f \( \
  -iname '*mode*b*' -o \
  -iname '*gene*by*gene*' -o \
  -iname '*chatgpt*' -o \
  -iname '*start*here*' -o \
  -iname '*workflow*' -o \
  -iname '*contract*' -o \
  -iname '*candidate*card*' \
\) | sort
```

To find Mode B contract text inside files:

```bash
grep -RInE 'Mode B|MODE_B|Full Mode|§1|§10|§20|protein_length_aa|comparator|claim-safety|coverage receipt' . \
  --include='*.md' --include='*.py' --include='*.json' --include='*.txt'
```

---

## 8. Minimal Mode B preflight checklist

Before starting a BGC workup, confirm:

- [ ] ChatGPT-specific instructions were loaded from the current cut.
- [ ] antiSMASH class / products are visible in the card.
- [ ] Node / contig / region locator is node-first.
- [ ] Boundary status is recorded: Interior / Edge / Full-contig / fragment.
- [ ] Gene table includes `protein_length_aa` in the same table as function / BLASTP evidence.
- [ ] Huge “small enzyme” labels are checked against protein length and domain architecture.
- [ ] Repeated comparator hits trigger a comparator workflow card.
- [ ] Different comparator axes are not collapsed into one story.
- [ ] Split/composite calls are labelled conservatively.
- [ ] Mode B coverage receipt is checked; `--top-n` is not treated as full inventory coverage.
- [ ] Completed Mode B cards are written back / persisted via the judgment or receipt path.
- [ ] Claim boundaries are stated at the interpretation level, not repeated after every gene.

---

## 9. One-line rule

For Mode B, read the actual instructions and tests first. If the docs, code, and tests disagree, stop and make the disagreement explicit before patching or interpreting.
