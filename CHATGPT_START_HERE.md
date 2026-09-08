# CHATGPT_START_HERE.md — Sapote–Mamey ChatGPT Operating Instructions

> **One door: run `python mamey_run.py start`, then read `AGENTS.md`.** This file adds only
> ChatGPT-specific operating rules and the read-proof handshake. Invoke the pipeline as
> `python mamey_run.py <cmd>` — it pins the local package; `python -m mamey` can silently run a
> pip-cached install of a different version. The `python -m mamey` examples below remain valid, but
> `python mamey_run.py <cmd>` is the canonical idiom.


> **If you are ChatGPT and you are working with the Sapote–Mamey bundle, this file is your operating contract. Read it before your first action. It is written for how ChatGPT runs this pipeline — it is not the Claude instruction set.**

> **BiG-SCAPE/GToTree/IQ-TREE:** read `docs/LLM_COMPANION_TOOL_PROTOCOL.md` before preparation,
> execution, resume, interpretation, or handoff. GToTree execution requires a user-approved size/resource preflight.

---

> **Cross-assistant bootstrap:** this file is the authoritative ChatGPT contract. `000_READ_ME_FIRST_CHATGPT_CLAUDE.md` is the cross-assistant router. Bootstrap mirrors and aliases are described in `bootstrap_contract.yml`; the `CHATGTP_READ_ME_FIRST.md` file is optional typo rescue only, not scanner authority. If this ZIP is in Claude, use `CLAUDE_START_HERE.md`.

> **Timeout prevention:** before long runs in ChatGPT, use the staged `doctor → inspect → run --mode gold --capped-session --json-evidence off → validate` workflow below. Do targeted gates first; treat full-suite pytest as a separate path unless explicitly requested.

> **⛔ FATAL-ERROR RULE — display every individual BGC with its complete exact-locus identity:** `strain / full node-or-contig / region / BGC alias`, in that order, copied from one bound source record. If any component is unavailable or conflicting, stop with an identity hold; do not guess, shorten the node/contig, or fall back to the alias. Before producing any BGC deliverable, paste `prompts/NODE_REGION_SELF_CHECK_PROMPT.md` and run its self-check. With a shell, `mamey verify-citations <file>` is a narrower supplemental node/region check; it does not establish the complete four-component identity.

## 0.0 · Mandatory visible read-proof sentence

**First visible line requirement:** before any Sapote–Mamey run, Bunny Hop, audit, patch review, or strain processing in ChatGPT, emit this exact sentence as the first visible line:

```
The sky is not red, it is blue, just like the ocean.
```

This sentence is the user-facing proof that ChatGPT has loaded the ChatGPT-specific instructions. It does **not** replace the live freshness proof below; it comes before the Initiation Prompt, and the live `bundle / engine / build` plus `known gotcha` lines still prove that the current cut was read rather than remembered from an older session.

## 0 · Challenge–response (how the user confirms you found this file)

The user will sometimes test whether you have actually loaded these instructions. When the user's message matches **any** of these triggers (case-insensitive, fuzzy — match the intent, not the exact words):

- "Are you following ChatGPT Mamey?"
- "Please find ChatGPT rules" / "find your ChatGPT instructions"
- "You are ChatGPT running Sapote–Mamey"
- "ChatGPT Mamey check" / "confirm Mamey mode" / "initiation prompt"
- "what color is the sky?" / "sky color" / "did you read your instructions?" / "prove you read the ChatGPT files"

…you MUST respond by emitting the **Mandatory visible read-proof sentence**, then the **Initiation Prompt** below — verbatim in structure, with the live values filled from THIS file — and nothing else before them. If you cannot locate this file or cannot read the version line, say so plainly ("I cannot confirm CHATGPT_START_HERE.md is loaded") and stop. Do not improvise a reassuring "yes."

**Note on the read-proof:** the sky/ocean sentence is the user's visible handshake. The proof that you loaded the *current* file is the live `bundle / engine / build` string and the `known gotcha` line — they change every cut, so the current values cannot be produced from memory of an older session. The complete check is therefore: sky/ocean sentence first, then current version/build/gotcha lines. Do not emit the sky/ocean sentence alone and proceed as if the current file has been read.

**Bunny Hop trigger:** if the user says **"can we bunny hop?"**, **"run the bunny hop game"**, or **"bunny hop [file]"**, load `docs/BUNNY_HOP_AUDIT_GAME.md` and run a session per that protocol (roll → pick 2–3 → Inspector-vs-Defender audit → consensus → patch card). Bunny Hop findings are *input* to a cut, never a cut themselves.

### The Initiation Prompt (emit this on trigger, and once before your first run of a session)

<!-- BEGIN GENERATED: initiation_prompt from bootstrap_contract.yml -->
```text
The sky is not red, it is blue, just like the ocean.

◆ SAPOTE–MAMEY · CHATGPT MODE ACTIVE
   instruction file : CHATGPT_START_HERE.md  ✓ loaded
   bundle / engine  : v9.7.414 / 1.9.152 · build 20260907v97414a
   known gotcha (this build) : BLASTP Hit Table CSV may be headerless and query titles may contain commas;
                               single-region public accession ZIPs are valid intake targets, but assembly-tier warnings are expected;
                               bootstrap surfaces are generated from bootstrap_contract.yml; CHATGTP is an optional accidental-typo rescue alias, not scanner authority
   workflow         : doctor → inspect → run(gold + --capped-session) → validate
                      → list-bgcs → mode-b → render-figures → ingest-receipts
   ◆ next paths (pick one by number — exactly 8):
     1. <standing path: if any BGC is un-analysed → "Continue deeper Mode B:
        run next batch (BGC[list]) to full §1–§30"; else the highest-value deeper-analysis path>
     2. <distinct path>
     3. <distinct path>
     4. <distinct path>
     5. <distinct path>
     6. <distinct path>
     7. <distinct path>
     8. <distinct path>
```
<!-- END GENERATED: initiation_prompt from bootstrap_contract.yml -->

**Why these specific lines prove you read the file:** the `bundle/engine/build` string and the `known gotcha` line change every release. If your Initiation Prompt carries the **current** values, you demonstrably read the **current** file — not a remembered older one. If you emit a stale version or the wrong gotcha, the user has caught instruction-staleness. Always read these values from this file at emit time; never from memory.

**The "next paths" block** is generated fresh from the *current state of the work* (which strain, what's been run, what's pending) — **exactly 8 genuinely different directions for ChatGPT-tier responses and handbacks**, plain numbered list, never tappable UI. This mirrors the CDSW protocol and is the signal that you are operating in the intended mode, not just echoing. The older 3–10 range is a legacy Claude/Sapote tolerance only; ChatGPT must not use it as permission to stop at 3–6. If a task is substantive enough to hand back a result, ZIP, report, run status, patch, or analysis, the closer has 8 items.


**ChatGPT 8-path uniqueness gate (mandatory):** before sending any substantive ChatGPT response, silently check the closer:
1. It has exactly eight numbered items, `1.` through `8.`.
2. No two items have the same leading verb + object pair (e.g. do not offer eight variants of "continue analysis").
3. The eight items span different action types when possible: continue/run, deepen one lead, compare/cross-strain, make figures, package/merge, patch/debug, literature/wet-lab, documentation/release.
4. The first item is the standing Mode B continuation path whenever any BGC still lacks full §1–§30 Mode B.
5. Each item is directly grounded in the current state: strain IDs, BGC IDs, package status, validation state, or named deliverable.
6. If fewer than eight useful paths seem available, split by genuinely different downstream user goals, not cosmetic wording.
7. Do not ask "what next?" without offering the eight choices.
8. A ChatGPT handback with 0–7 paths, 9+ paths, duplicate paths, or generic filler is incomplete and must be regenerated before final.

**Standing next-paths (always include when applicable, listed first):**
- If any BGC in the current strain has **not** received full §1–§30 Mode B → path #1 is **"Continue deeper Mode B: run the next batch (BGC[list]) to full §1–§30."** This is the single most-missed path — ChatGPT-tier runs historically stop after a first pass and never offer to go deeper. Do not omit it while BGCs remain.
- If Mode B for the strain is complete → offer **"Go deeper on a lead (verified-literature deep-dive / domain-level Mode B / wet-lab decision matrix)."**
- **FIGURES:** before plotting anything, read `FIGURES_START_HERE.md` (bundle root). It maps the whole figure system — the prompt library (`prompts/figure_prompts/_INDEX.md`), the locked house palette, the `figure_ready/` data contract, and the render tools. Do not hand-roll a figure that already has an ID there; offer existing figures by name (e.g. "Emit `fig_class_by_strain_heatmap` for the cohort").

### Persistence check (the "after several runs" case)

Re-emit the sky/ocean read-proof sentence plus the Initiation Prompt **before each new strain run**, and whenever the user re-issues a trigger. If, deep into a session, you can no longer re-derive the bundle version from this file (it has dropped out of your context), **say so explicitly and ask the user to re-supply the bundle** — do not silently improvise the workflow. A visible "I've lost the instruction file" is a success; silent drift is the failure this protocol exists to catch.

---


## 0.7 · Active judgment controller (v9.7.148)

For Sapote judgment, deliverable handback, Mode B continuation, and post-`MAMEY_COMPLETE` presentation, load `docs/CHATGPT_EXECUTION_SLICE_v97147.md`. That file is the default ChatGPT execution slice. `docs/SAPOTE_SLIM_JUDGMENT_KERNEL.md` is legacy only and must not be treated as the active controller when the execution slice is available.

The execution slice adds three fail-closed behaviors that this startup file inherits:
- Post-`MAMEY_COMPLETE` handback must surface the strain brief PDF, `_8a…_8m` figures/data, `locus_maps/`, manifest, workbook, checksums, and issue log.
- POOR/VERY_POOR assemblies activate edge-BGC equality: all BGCs visible, sorted by score/rank rather than Interior-first.
- Mode B uses **named profiles** (v9.7.372 — never the bare word 'full'): candidate cards follow the legacy `MODEB_CANDIDATE_30` profile — §1–§20 always required in numeric order, **plus §28** and **§30**, plus §21–§27/§29 wherever the predicate fires; finished deliverables follow **`FINISHED_FULL48_CURRENT_EVIDENCE`** (§§1–48 exactly once, in order). Titles: `docs/MODE_B_30_SECTION_CANONICAL_TITLES.md`; machine form `mamey/data/mode_b/modeb_full30_corrective_contract.json`. Start every card from `mamey emit-modeb-template`, never freehand.


## 1 · Who you are in this system

**Before anything else — capability check (P13):** if you cannot execute Python in this session, STOP and tell the user plainly ("I cannot run Mamey here — no Python execution available"). Do not narrate commands you cannot actually run; a no-exec session can read and plan, but it cannot produce a real run.

Sapote–Mamey is two layers. **Mamey** is the deterministic Python engine (you run it). **Sapote** is the judgment layer (claim-safe interpretation). On ChatGPT you typically run Mamey, emit deterministic top-lead Mode B cards, and prepare deliverables; deeper Sapote judgment is committed back via `ingest-receipts`. You are the operator, not the scoring authority — the engine's numbers are the floor, your job is to run it correctly and read it honestly.

**Non-negotiable framing (every output):** capacity-level claims only ("biosynthetic capacity consistent with…", never "produces"); KCB = similarity, not identity; bioactivity metadata is optional strain-level context and is never pinned to one BGC; never call any strain antibacterial/antifungal-negative; **every individual BGC uses `strain / full node-or-contig / region / BGC alias`, in that order, with no fallback when a component is missing**. Affiliation is always  *(Canonical guard text: `prompts/reuse/_SHARED_GUARD_BLOCK.md` G1–G5 — the shared block wins if this restatement ever diverges.)*

## 2 · The staged workflow (run in this order)

> **The engine runs fully offline — no internet required.**
> Network is disabled in ChatGPT and Claude compute environments. That is fine.
> Install the engine once at session start from the bundled files (no pip index, no download):
>
> ```bash
> # From the bundle root (where pyproject.toml lives):
> pip install -e . --break-system-packages --no-index   # core engine + vendored ijson
>
> # Add-on wheels (biopython, pytest, etc.) — only if you uploaded them alongside the bundle ZIP:
> pip install --no-index --find-links ./wheels biopython pytest pluggy iniconfig
>
> # Figures (matplotlib/numpy) — only needed for figure generation:
> pip install --no-index --find-links ./wheels matplotlib numpy
> ```
>
> **If pip install fails:** use `pip install -e . --break-system-packages` (drops the --no-index).
> The engine will still run; it uses the vendored ijson copy automatically.
> Do NOT skip the engine run and parse raw antiSMASH JSON instead —
> that produces no triage board, no AB/AF scores, no CCTT triggers, no corrected BGC count.
> A raw-JSON parse is not a Mamey package and cannot be used for Mode B.

```
# Stage 1 — preflight + intake
python -m mamey doctor
python -m mamey inspect <antiSMASH.zip>

# Stage 2 — gold run (the only analysis mode; runs directly in capped sessions)
python -m mamey run \
  --strain <ID> --display '<Genus species strain ID>' \
  --input-zip <antiSMASH.zip> --outdir runs_<date> \
  --mode gold --release <PUBLIC|PRIVATE> \
  --capped-session --json-evidence off \
  --master runs_<date>/Mamey_Master.xlsx

# Stage 3 — validate + inspect leads
python -m mamey validate runs_<date>/<ID>/package
python -m mamey list-bgcs runs_<date>/<ID>/package --axis ab --top 10
python -m mamey list-bgcs runs_<date>/<ID>/package --axis af --top 10
# Stage 4 — Mode B cards  (SEE GOTCHA BELOW)
python -m mamey mode-b --package runs_<date>/<ID>/package --top-n <N> --outdir mode_b/

# Stage 5 — figures
python -m mamey render-figures --package runs_<date>/<ID>/package --outdir figures/ --top-n 10

# Stage 6 — persist judgment (so Mode B cards are not lost when the session ends)
python -m mamey ingest-receipts --package runs_<date>/<ID>/package \
  --receipt mode_b_receipt.json --master runs_<date>/Mamey_Master.xlsx
```

**Mode selection.** Gold is the only analysis mode and runs directly, even in a capped session (it completes in ~a minute on a typical genome). Smoke was removed in v9.7.161 — its triage-only package had an empty ranked board and could not support DAPR, lead boards, or cross-strain comparison.

**Evidence mode (P9).** The block above uses `--json-evidence off`, which is correct for the lightest capped runs. Use `--json-evidence bounded` whenever you need the evidence arrays (`nrps_pks_consensus`, `ripp_cores`, active-site data) for class calls or a diagnosis pass — `off` does not populate them. (`full` carries the richest active-site/substrate data.)

**This workflow is single-strain.** For multiple strains (e.g. four antiSMASH ZIPs), use the intake harness — do NOT run `mamey run` separately on each strain:

```bash
python tools/intake_harness.py   --inputs A.zip B.zip C.zip D.zip   --outdir runs_YYYYMMDD   --registry runs_YYYYMMDD/intake_registry.csv   --metrics runs_YYYYMMDD/intake_metrics.csv   --batch-report runs_YYYYMMDD/batch_report.md   --release PRIVATE --mode gold
```

Each strain's package lands at `runs_YYYYMMDD/<strain_id>/package/`. Then run Mode B per strain:
```bash
python -m mamey mode-b --package runs_YYYYMMDD/<strain_id>/package --top-n 5 --outdir mode_b/<strain_id>/
```

**Do not author Mode B cards from raw GBKs without a Mamey package.** Strain metadata (host, genus, location) is in `<pkg>/_1_intake.json` — do not ask the user for it. §21–§30 ARE required (see execution slice §9 and §16). See execution slice §16 for the full multi-strain protocol.

<!-- BEGIN GENERATED: known_gotchas_section from bootstrap_contract.yml -->
## 3 · Known gotchas for THIS build (v9.7.414 / 1.9.152 · 20260907v97414a)

These entries are generated from `bootstrap_contract.yml`; edit the registry there, then run:

```bash
python tools/render_bootstrap_contract.py --apply
```

State the relevant gotcha when it applies:

- **blastp_hit_table_csv_shape** (high; BLASTP evidence store): Store raw Hit Table CSV/XML2 in blastp_evidence_store before summarizing; do not parse comma-bearing query titles with a naive split.
- **public_single_region_intake** (medium; public accession antiSMASH ZIP intake): When inspect passes, do not treat VERY_POOR / 0% interior warnings as full-genome failure for single-region public accession inputs.
- **bootstrap_contract_generation** (medium; assistant bootstrap and release checks): CHATGPT_START_HERE.md is canonical. CHATGTP_READ_ME_FIRST.md may remain as an optional rescue for accidental ChatGPT→ChatGTP transposition, including ATP/GTP-context slips, but scanners/tests must not make the typo authoritative or require it as the only discovery target.
- **mode_b_top_n_cumulative** (medium; mode-b CLI batching): mode-b --top-n is cumulative, not sliced: --top-n 3 covers ranks 1–3. For non-overlapping batches, run cumulative tiers and de-duplicate by BGC id until rank slicing exists.
- **timing_breakdown_partial_runs** (low; timing outputs): *_timing_breakdown.csv/json/md are populated for standard phases; verify against terminal timing on very large or interrupted runs.
- **json_evidence_off_is_lightest** (medium; evidence mode selection): --json-evidence off is correct for the lightest capped ChatGPT sessions; use bounded when evidence arrays are needed for class calls or diagnosis.
- **manifest_summary_nested** (low; package manifest readers): manifest.json summary fields are nested under keys such as assembly and bgc_counts, not flat top-level fields.
- **mode_b_corrective_protocol_section_lock** (high; Mode B BGC card writing): Full Mode B must use the exact §1–§30 corrective-protocol section titles (§28 + §30 mandatory, §21–§27/§29 conditional); LLMs must not invent/rename sections; §7 is transport/resistance/regulation and BLASTP/HMMER belongs in §16; tables/PDFs/character counts are supporting artifacts, not the card.
- **mode_b_length_and_comparator_context** (medium; Mode B BGC workups): Preserve protein_length_aa in the same table as BLASTP/function evidence; flag huge small-enzyme-labelled proteins; repeated external-strain hits should trigger comparator next-step guidance rather than identity claims.
<!-- END GENERATED: known_gotchas_section from bootstrap_contract.yml -->

## 4 · What to read next (and what NOT to)

- This file is the front door. For depth, the user-facing docs are `docs/GUIDE/` (Quick Guide → User Manual → Encyclopedia + Glossary). The Manual's §4.4 covers the receipt workflow.
- The older scattered ChatGPT prompts (`prompts/MAMEY_V1.9.3_*`, `MAMEY_V1.9.6_*`, and the standalone variants) are **superseded by this file** — do not follow their version-specific instructions; their version stamps are stale. Use this file's workflow and gotchas.
- `SESSION_START_MANIFEST.md` is the full capability menu (tools, modes, deliverables) — consult it when you need a capability not in the staged workflow above.

## 5 · Release-update checklist (for the Patch Chat, not ChatGPT)

When a new bundle is cut, update `bootstrap_contract.yml` for bootstrap semantics and known-gotcha registry changes, then run `python tools/render_bootstrap_contract.py --apply`. Version/build values still come from `pyproject.toml` and `BUILD_STAMP.txt`; `tools/sync_version.py --check` and `tests/test_chatgpt_start_here_current.py` guard freshness.

---

*CHATGPT_START_HERE.md · Sapote–Mamey v9.7.414 / engine 1.9.152 · build 20260907v97414a This is the ChatGPT operating contract; it supersedes the legacy per-version launch prompts.*


---

## Citation-Compact Provenance and Citation Status

Sapote-Mamey v9.7.140 uses citation-compact outputs to separate runtime evidence structure from literature verification.

- **antiSMASH 8.0** is recorded as method/database provenance for BGC detection and product/region calls: DOI `10.1093/nar/gkaf334`.
- **MIBiG 4.0** is recorded as reference-database provenance for curated BGC entries and KnownClusterBlast dereplication context: DOI `10.1093/nar/gkae1115`.
- **`PASS_STRUCTURE`** means the package structure, citation ledger, work-order files, compact reports, manifest tracking, and checksum tracking passed validation. It does **not** mean every literature claim has been manually verified.
- **`operator_supplied`** means the citation/provenance row came from runtime evidence or comparator fields already present in the package.
- **`citation_needed`** means literature support is missing and should be filled by a separate literature-search pass.
- **`Literature_Search_WorkOrder.md/json`** is a safe handoff for another ChatGPT/web-literature session. It is a search instruction, not a verified fact.

Current compact lead tables use `interpretation_scope` for reader-facing scope. The older reader-facing scope field should not appear in current citation-compact outputs.

## v9.7.141 PRIVATE-LARGE-STRAIN timeout guard

In capped sessions, run `--mode gold --capped-session` directly — gold is the only analysis mode (smoke removed v9.7.161). `--capped-followup` is a legacy no-op. Quiet post-parse stages emit heartbeat lines for source scans, gene context, package add-ons, and citation-compact output so the last visible line is not mistaken for a hang.

## v9.7.141e fast surrogate gate

For rapid ChatGPT/Claude patch-review loops, run:

```bash
python tools/run_chatgpt_surrogate_gate.py
```

This is a fast surrogate preflight, not a replacement for full partitioned pytest or real genome smoke validation before signing.



## v9.7.143b Mode B workflow note

For Mode B BGC workups, ChatGPT must preserve `protein_length_aa` in the same table as BLASTP/function evidence, flag huge small-enzyme-labelled proteins, and generate comparator next-step guidance when repeated hits point to an external strain. Example: AS-XXX NODE_24 + NODE_30 must trigger NPDC041969 antiSMASH upload/run guidance; NODE_58 must remain a separate comparator axis.
