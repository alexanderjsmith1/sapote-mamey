# 000 READ ME FIRST — ChatGPT + Claude Bootstrap

> **One door: run `python mamey_run.py start`, then read `AGENTS.md`.** Everything below only routes
> you there and adds the ChatGPT/Claude upload specifics. `start` prints this bundle's real version and
> the ordered happy path; `AGENTS.md` (= `CLAUDE.md`) is the canonical contract for every assistant.
> Invoke the pipeline as `python mamey_run.py <cmd>` (it pins the local package).


**Purpose:** make this ZIP self-starting when uploaded into either ChatGPT or Claude. Read this file before running Sapote–Mamey, patching the bundle, or diagnosing an antiSMASH ZIP.

**Current bundle:** Sapote–Mamey v9.7.414 · Mamey engine 1.9.152 · build 20260907v97414a

**BiG-SCAPE/GToTree/IQ-TREE:** after assistant-specific startup, read
`docs/LLM_COMPANION_TOOL_PROTOCOL.md` before inventorying, running, resuming, or interpreting them.

## 1 · Assistant routing

- **ChatGPT:** read `CHATGPT_START_HERE.md` immediately, then emit its required read-proof/initiation prompt before any strain run, audit, patch review, or release cut. The read-proof sentence is:

  ```text
  The sky is not red, it is blue, just like the ocean.
  ```

- **Claude:** read `CLAUDE_START_HERE.md` immediately, then use the Claude/Sapote execution style while preserving the deterministic Mamey command order.

- **Typo rescue:** if you accidentally typed `CHATGTP`, `CHAT GTP`, `ChatGTP read me first`, or similar, `CHATGTP_READ_ME_FIRST.md` exists only to redirect you back here and then to the canonical `CHATGPT_START_HERE.md`; it is optional and not scanner authority.

## 2 · Timeout-safe ChatGPT defaults

Use the capped-session workflow for timeout-safe defaults. Gold is the only analysis mode and runs directly as the first (and only) run — it completes in about a minute on a typical genome:

```bash
python mamey_run.py doctor
python mamey_run.py inspect <antiSMASH.zip>
> **Offline install (no internet needed):** `pip install -e . --break-system-packages` from the bundle root. The engine runs fully offline.
> Do NOT parse raw antiSMASH JSON as a substitute — that is not a Mamey package.

python mamey_run.py run --strain <ID> --display '<display name>' --input-zip <antiSMASH.zip> \
  --outdir runs_<date> --mode gold --release <PUBLIC|PRIVATE> \
  --capped-session --json-evidence off --master runs_<date>/Mamey_Master.xlsx
python mamey_run.py validate runs_<date>/<ID>/package
```

When a chat has a tight execution cap, do **targeted gates first**. Treat a full `python -m pytest tests/ -q` as a separate path unless the user explicitly asks for it.

<!-- BEGIN GENERATED: bootstrap_surface_map from bootstrap_contract.yml -->
## 3 · Bootstrap surface contract

This map is generated from `bootstrap_contract.yml`. Required canonical surfaces are hard release gates; generated mirrors are convenience surfaces; optional typo-rescue aliases are convenience shims and must not become scanner authority.

| Path | Classification | Required | Scanner authority | Generation | Purpose |
|---|---|---:|---:|---|---|
| `CHATGPT_START_HERE.md` | canonical / canonical_chatgpt_contract | yes | yes | partial | Authoritative ChatGPT operating contract. |
| `CLAUDE_START_HERE.md` | canonical_other_assistant / canonical_claude_contract | yes | yes | version_probe_only | Claude front door; ChatGPT should not follow Claude-specific instructions. |
| `000_READ_ME_FIRST_CHATGPT_CLAUDE.md` | canonical_router / cross_assistant_router | yes | yes | partial | Root-level upload front door routing ChatGPT and Claude to their contracts. |
| `CHATGPT_READ_ME_FIRST.md` | generated_mirror / correctly_spelled_chatgpt_alias | yes | no | full | Correctly spelled convenience mirror pointing to CHATGPT_START_HERE.md. |
| `CHATGTP_READ_ME_FIRST.md` | optional_typo_rescue_alias / accidental_chatgtp_transposition_rescue | no | no | full | Optional rescue for accidental ChatGPT→ChatGTP transposition, especially in scientific contexts where GTP is a familiar acronym. Must redirect to CHATGPT_START_HERE.md and must never be canonical. |
| `README.md` | generated_mirror / package_reader_banner | yes | no | partial | Normal package reader banner; should route assistants to canonical contracts. |
| `README_START_HERE.md` | generated_mirror / reviewer_operator_banner | yes | no | partial | Reviewer/operator start page; should route assistants to canonical contracts. |
| `BOOTSTRAP_FILE_AUDIT.md` | generated_report / generated_bootstrap_map | yes | no | full | Human-readable audit of canonical files, generated mirrors, compatibility aliases, and obsolete surfaces. |
<!-- END GENERATED: bootstrap_surface_map from bootstrap_contract.yml -->

## 4 · Current gotchas copied here for first-contact visibility

- v9.7.143 BLASTP follow-up parsing is hardened for headerless NCBI Hit Tables and comma-bearing query titles; preserve Hit Table CSVs and XML2 in the BLASTP evidence store before summarizing.
- Single-region public accession antiSMASH ZIPs are valid raw intake targets when `inspect` passes; do not treat `VERY_POOR / 0% interior` as a failed full-genome run for these inputs.
- `mode-b --top-n` is cumulative, not sliced.
- ChatGPT first-run default is `--mode gold --capped-session --json-evidence off`; use `bounded` only when evidence arrays are required.
- `standard` currently aliases into the heavier/gold-style path in the CLI; do not recommend it as the ChatGPT first-run command.
- `*_timing_breakdown` files are populated for standard/gold phases; verify against terminal timing on very large or interrupted runs.
- Bootstrap surfaces are mapped in `bootstrap_contract.yml`; canonical ChatGPT discovery is `CHATGPT_START_HERE.md`, while `CHATGTP_READ_ME_FIRST.md` is optional accidental-typo rescue only.

## v9.7.143 ChatGPT-safe intake and BLASTP evidence-store guard

In capped sessions, run `--mode gold --capped-session` directly — gold is the only analysis mode (smoke removed v9.7.161: its triage-only package couldn't support DAPR, lead boards, or comparison). `--capped-followup` is a legacy no-op. Quiet post-parse stages emit heartbeat lines for source scans, gene context, package add-ons, and citation-compact output so the last visible line is not mistaken for a hang.



## v9.7.143b Mode B workflow note

For Mode B BGC workups, ChatGPT must preserve `protein_length_aa` in the same table as BLASTP/function evidence, flag huge small-enzyme-labelled proteins, and generate comparator next-step guidance when repeated hits point to an external strain. Example: AS-XXX NODE_24 + NODE_30 must trigger NPDC041969 antiSMASH upload/run guidance; NODE_58 must remain a separate comparator axis.

## v9.7.338 post-seal deliverables (first-contact visibility)

New **post-seal, non-scoring / advisory** surfaces run on an already-sealed package (or a runs dir of
them). They read sealed outputs and never move AB/AF/novelty priors or the lead tier — every read is a
**class-level capacity hypothesis** (judgment deferred, similarity not identity, no structure/product/activity claim):

- `good-guesses` — Good Guesses interpretive-priors report → md/csv/docx/pdf.
- `modeb-export` — authored §1–§30 Mode B card (or a `mode_b/` dir) → Word `.docx` + `.pdf`.
- `figures kcb-locusmap` — offline clinker-style KCB comparative locus map (png/svg/csv).
- `af-dossier` — Antifungal Lead Dossier (AF lead board × measured Candida activity, separate columns).
- `cohort-leads` + `cohort-assemble` — cross-strain priority-leads ledger + figure-ready cohort assembler.
- `comparator-coverage` — two-denominator MIBiG comparator-coverage evidence (low-specificity collision flag).
- `domain-reference`, `realistic-count`, `novelty-shortlist` — domain dictionary, honest BGC count, novelty shortlist.
- `signoff` — analysis sign-off QC gate on phylogenetic trees (advisory, exit 0).
- `verify-modeb --interp` — Mode-B interpretation gate (advisory WARN) added to the structure verify.
