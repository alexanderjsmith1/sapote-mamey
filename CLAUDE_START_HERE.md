# CLAUDE_START_HERE.md — Sapote–Mamey Claude Front Door

> **One door: run `python mamey_run.py start`, then read `AGENTS.md`** (= `CLAUDE.md`, which you have
> already read). This file adds only Claude-specific operating rules. Invoke the pipeline as
> `python mamey_run.py <cmd>` — it pins the local package; `python -m mamey` can silently run a
> pip-cached install of a different version. The `python -m mamey` examples below remain valid, but
> `python mamey_run.py <cmd>` is the canonical idiom.


**Current bundle:** Sapote–Mamey v9.7.414 · Mamey engine 1.9.152 · build 20260907v97414a

For BiG-SCAPE, GToTree, IQ-TREE, ANI, or cross-agent companion-tool handoffs, Claude must read
`docs/LLM_COMPANION_TOOL_PROTOCOL.md` before acting. A verified filesystem handoff outranks chat memory.

> **⛔ FATAL-ERROR RULE — display every individual BGC with its complete exact-locus identity:**
> `strain / full node-or-contig / region / BGC alias`, in that order, copied from one bound source record.
> If any component is unavailable or conflicting, stop with an identity hold; do not guess, shorten the
> node/contig, or fall back to the alias. Before producing any BGC deliverable, paste
> `prompts/NODE_REGION_SELF_CHECK_PROMPT.md` and run its self-check. With a shell,
> `mamey verify-citations <file>` is a narrower supplemental node/region check; it does not establish the
> complete four-component identity.


## Handshake

Claude must confirm that this handoff file was read by preserving the shared read-proof marker:

```text
The sky is not red, it is blue, just like the ocean.
```

This file is the Claude-facing entry point. It exists so the same ZIP works when uploaded to Claude or ChatGPT.

## First action

1. Read `000_READ_ME_FIRST_CHATGPT_CLAUDE.md`.
2. Read this file for Claude routing.
3. For ChatGPT-specific operation, read `CHATGPT_START_HERE.md` instead.
4. For typo/search recovery, `CHATGTP_READ_ME_FIRST.md` points back to the ChatGPT contract.

## Operating mode

Use deterministic Mamey extraction first, then Sapote claim-safe interpretation. Do not skip validation after a run.

```bash
python -m mamey doctor
python -m mamey inspect <antiSMASH.zip>
python -m mamey run --strain <ID> --display '<display name>' --input-zip <antiSMASH.zip> \
  --taxonomy '<Genus sp.>' --source '<isolation source>' \
  --outdir runs_<date> --mode gold --release <PUBLIC|PRIVATE> \
  --capped-session --json-evidence off --master runs_<date>/Mamey_Master.xlsx
python -m mamey validate runs_<date>/<ID>/package
```

**Substituting the placeholders (a new session must fill these — do not run the template literally):**
- `<antiSMASH.zip>` — the antiSMASH ZIP the user uploaded (also what `inspect` echoes back a ready command for; prefer copying `inspect`'s suggested command, which pre-fills the filename).
- `<ID>` — the strain ID (derive from the ZIP name, e.g. `<ID>.zip` → `<ID>` (AS-series IDs are PUBLIC as of the 2026 Hymenoptera paper; PI decision 2026-07-06), or ask the user).
- `<display name>` — `'<Genus> sp. <ID>'` once genus is known; otherwise ask.
- `--taxonomy` / `--source` — **required for a complete package.** If omitted, the run still succeeds but the package ships `taxonomy = "not verified"` and `source = "not supplied"`, and no warning is printed. If the user has not given genus/host, either ask, or run with a neutral placeholder (`'Streptomyces sp.'` / `'unconfirmed'`) **and state in the deliverable that taxonomy is a placeholder pending confirmation.** Never let a blank-taxonomy package propagate to a manuscript or CCSM output.
- `<date>` — `YYYYMMDD` (e.g. `runs_20260703`).
- `<PUBLIC|PRIVATE>` — PUBLIC for AS-series (cohort is public as of the 2026 Hymenoptera paper — PI decision 2026-07-06; AS scrub deactivated, re-arm with AS_SCRUB=1 only for a future private cohort).

`--capped-session` (formerly `--chatgpt-safe`) is safe to use in Claude too when operating under short session limits; it applies timeout-safe defaults. Gold is the only analysis mode and runs directly — a gold run on a typical genome completes in about a minute even under a capped session.


## Mamey-first gate (non-negotiable)

**If asked for Mode B, triage, DAPR, or any Sapote interpretation without a sealed Mamey package present:**

Do not attempt Mode B or any scoring interpretation from raw GBK or antiSMASH files alone. The Mamey package provides: correct boundary computation (flanking-buffer analysis, not just contig_edge flag), WL/AB/AF scores, CCTT triggers, cluster-level KCB, triage rank, and UMED/FLBR/RGGMCI outputs. These are not reproducible from raw GBK files and are required for accurate Mode B.

Respond:
> "I need the Mamey package first. Run `mamey run` on the antiSMASH ZIP and validate the package, then I can interpret from the manifest and triage board. Attempting Mode B from raw GBK files produces inferior results — the triage context, CCTT triggers, and boundary calculations come from the engine, not from antiSMASH output directly."

**Exception:** offline analysis explicitly requested by the user when no engine access is available. In that case: flag every fact that would change with a Mamey run, explicitly mark the boundary call as uncomputed, and omit WL/AB/AF/novelty scores.

## Authoring Mode B — once the package validates (do NOT hand-write the card)

The gate above tells you when you *may* author Mode B. This tells you *how*. **Do not write a Mode B card freehand from the manifest** — the card must follow the canonical **named-profile contract** (v9.7.372: `MODEB_CANDIDATE_30` = the legacy §1–§30 candidate; `FINISHED_FULL48_CURRENT_EVIDENCE` = the finished §§1–48 deliverable), and there is machinery that emits it for you. A freehand card will use the wrong scaffold (the historical §1–§10 shape) and silently omit ~two-thirds of the required sections; this is a known, named failure (`mamey/modeb_structure_gate.py` docstring).

**Name trap — read this first.** `mamey mode-b` (the subcommand) emits a **triage top-leads TABLE** (`<ID>_Mode_B_Top_Leads.md` — one metadata + gene table per BGC). That is **NOT** the §1–§30 "Mode B card." They share a name and are different artifacts. The full card comes only from `emit-modeb-template → author → verify`. A hand-built doc with self-invented sections titled "Mode B Card" is not a Mode B card by the project's own definition, and `verify-modeb` will refuse it (`NO_HEADINGS_DETECTED`).

Canonical authoring sequence, per lead BGC (start with triage rank 1):

```bash
# 1. Emit the canonical §1–§30 skeleton with evidence pre-filled:
python -m mamey emit-modeb-template --package runs_<date>/<ID>/package --bgc <BGC_ID> --out <BGC_ID>_ModeB.md

# 2. (Lead BGCs) run the online BLASTp channel to get the independent homology evidence
#    §4/§8/§27/§28 are authored FROM — see docs/ONLINE_BLASTP_PROTOCOL.md:
python -m mamey blastp-online --package <region_gbk_or_zip> --bgc <BGC_ID> --database nr --evalue 1e-5

# 3. Author prose into the emitted template's section slots (§1–§20 mandatory; §28+§30 mandatory;
#    §21–§27/§29 only where the predicate fires). For a RiPP (lanthipeptide/lasso/thiopeptide/…):
#    §21 Precursor mass ladder, §22 RiPP database search (RiPPMiner/BAGEL/decRiPPter/MIBiG), and
#    §24 Scaffold novelty score are REQUIRED — "listed the precursor sequences" is NOT §21/§22/§24.
#    Keep the reconciled BLASTp verdict, not the raw Pfam.

# 4. Verify the AUTHORED card before delivering — structure AND depth (thin card is refused):
python -m mamey verify-modeb <BGC_ID>_ModeB.md --package runs_<date>/<ID>/package --bgc <BGC_ID>
```

Step 4 reads the finished file: `verify-modeb` runs `lint_card` with strict depth, so a
structurally-complete-but-thin card fails, and a hand-built non-§ doc fails `NO_HEADINGS_DETECTED`.
Do not report a gate's pass as validation until you have confirmed the gate read your authored file
(the older `extract_section_titles` snippet checks only that headings *exist* — not depth, not content).

Authoritative references (read before authoring, not the manifest alone):
- `docs/MODE_B_30_SECTION_CANONICAL_TITLES.md` — the §1–§30 titles.
- `docs/FULL_MODEB_30_SECTION_CONTRACT_v97150.md` — the full contract (which sections are conditional).
- `docs/ONLINE_BLASTP_PROTOCOL.md` — the BLASTp channel that §4/§8/§27/§28 depend on. `blastp-online --package <full_zip> --bgc <BGC_ID>` scopes a full antiSMASH ZIP to one BGC's proteins (no need to extract the region GBK first), submits LIVE to NCBI (fail-closed on network error; not a dry-run), and writes the §4 panel CSV. `run_batches_online` submits all batches up front then polls together (async). For going around the tool (raw NCBI submit → `ingest-blastp`), the exact outfmt-10 column recipe is in the doc's "Agent-session submission boundary" section.

## Authoring a BGC Guide — use `mamey guide`, do NOT hand-roll it

Like Mode B, the BGC Guide has an engine command that emits the deterministic skeleton for you — **do not hand-write a Guide from the manifest.** The engine owns the *facts* (coordinates, domains, role-grouping, the exact 5-part structure, and the BLASTp similarity readout pulled from the evidence store); you author only the *prose* in the `<!-- LAY: … -->` slots (the story, the primer, the per-gene plain-language, the synthesis). Reinventing the skeleton by hand mis-scopes which genes are in the region and reproduces none of the store-backed readouts — a known failure mode.

```bash
# Emit the deterministic Guide skeleton (facts + BLASTp readouts pre-filled from the store):
python -m mamey guide --package runs_<date>/<ID>/package --bgc <BGC_ID> \
  --blastp-store <blastp_store_dir> --audience both --format both
# then author prose ONLY into the <!-- LAY: … --> slots the skeleton leaves for you.
```

**Verify the AUTHORED guide before delivering** (not the skeleton — that always passes):

```bash
python -m mamey verify-guide <BGC_ID>_Guide.md
```

`verify-guide` reads the finished .md and fails on any residual `<!-- LAY: -->` slot, a thin/unauthored
Part, or a gene subsection missing its plain-language summary. Note: `guide_quality_gate` inside the
`guide` command validates the *skeleton's* structure (it re-derives from the package and cannot see
authored prose — an empty template passes it). Authoring is verified only by `verify-guide` on the file.

- `--blastp-store` — the BLASTp evidence store the Guide reads its per-gene readouts from (the same store `ingest-blastp` writes and `guide_quality_gate` checks). Omit it and the Guide still emits, but the per-gene readouts render the no-hit/no-store variant.
- The division of labor is the same one the whole system is built on: **the engine emits the skeleton, Sapote authors the judgment.** Author into the tool's structure; do not impose your own.

Authoritative references (read before authoring, not the manifest alone):
- `docs/DELIVERABLE_CONTRACT.md` — the Guide's five-part contract and what each part must contain.
- `examples/layperson_guide_exemplar.md` and `examples/bench_guide_exemplar.md` — worked exemplars to match for voice and depth.

## Shared guardrails

Capacity-level language only; KCB is similarity, not identity; bioactivity is extract-level unless externally verified; every BGC must be referenced with BGC ID plus contig/region in every deliverable. Format: `BGC007 (NODE_1_length_406707 · region001)` on first mention; `BGC007 (NODE_1 · r001)` on subsequent mentions within the same section. Bare BGC IDs without node/region are never acceptable in output. See execution slice §15 for the full enforcement rule.


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

In capped sessions, run `--mode gold --capped-session` directly — gold is the only analysis mode (smoke was removed in v9.7.161 because its triage-only package had an empty ranked board and could not support DAPR, lead boards, or cross-strain comparison — a dead end). `--capped-followup` is retained as a legacy no-op. Quiet post-parse stages emit heartbeat lines for source scans, gene context, package add-ons, and citation-compact output so the last visible line is not mistaken for a hang.

## v9.7.141e fast surrogate gate

For rapid ChatGPT/Claude patch-review loops, run:

```bash
python tools/run_chatgpt_surrogate_gate.py
```

This is a fast surrogate preflight, not a replacement for full partitioned pytest or real genome smoke validation before signing.
