# Sapote–Mamey: The Kernel, the Gates, and What Has Changed
**Sapote–Mamey v9.7.414 · Engine 1.9.152 · build 20260907v97414a**
Hamilton, Ontario

*This document is a catch-up reference for the PI who built the system but has not had time to track every cut. It explains what the kernel is, how the two layers work together, what gates now exist, and what changed in recent versions — in plain language, with pointers to the authoritative source files.*

---

## Part I: What the System Actually Is

### The two-layer design

Sapote–Mamey is built on a strict division of labour between two distinct layers:

**Mamey** is the deterministic extraction engine. It reads raw antiSMASH output (a ZIP of GenBank files), runs a fixed set of computations in a fixed order, and writes a sealed package of facts to disk. There is no LLM judgment anywhere in Mamey. Given the same input ZIP and the same engine version, Mamey will always produce the same numbers: the same BGC count, the same AB and AF scores, the same boundary calls, the same KCB similarity scores, the same scan results. This reproducibility is by design. Mamey is the part of the system that can be wrong in a fixed, auditable, correctable way — when a bug is found (and several have been), the fix is patched, the engine version is bumped, and any affected strains can be re-run to get corrected numbers.

**Sapote** is the LLM judgment layer. It reads the sealed Mamey package (primarily `manifest.json` and the CSV outputs) and interprets the evidence using scientific reasoning, ecological context, and claim-safe language. Sapote is where the Mode B analysis cards, the layperson guides, the ecological synthesis, and the fermentation recommendations come from. Sapote is not deterministic — it is judgment, and judgment can be shallow, can make claim errors, and can silently omit evidence if not properly constrained. The entire gate and contract infrastructure described in this document exists to constrain Sapote's outputs to be deep enough, honest about uncertainty, and grounded in the actual Mamey evidence rather than confabulated from general LLM knowledge.

The core rule that flows from this design: **you cannot run Sapote on raw antiSMASH files.** The boundary computations, AB/AF scores, CCTT triggers, KCB cluster scores, UMED maturation-enzyme detection, RGGMCI split-pathway pairs, and FLBR megasynthase census are all computed by Mamey. Sapote does not reproduce these — it reads them. Mode B cards authored without a sealed Mamey package are missing most of the quantitative scaffolding they claim to be built from.

### What "sealing" means

A Mamey package is sealed by `mamey validate`. Validation checks structural completeness (all required files present), checksum integrity (every file matches the SHA256 in `checksums_sha256.txt`), and schema compliance (the manifest fields match the declared schema version). A sealed package carries a status: `MAMEY_COMPLETE`, `MAMEY_COMPLETE_WITH_ISSUES`, or `VALIDATION_FAIL`. Sapote should only operate on `MAMEY_COMPLETE` or `MAMEY_COMPLETE_WITH_ISSUES` packages. The distinction between the two is that `_WITH_ISSUES` means at least one non-fatal issue was logged (e.g. a figure module failed to render) — the core numerical outputs are still valid, but something in the peripheral output set requires attention.

---

## Part II: The Judgment Kernel — History and Current State

### What "the kernel" meant originally

The original controller for the Sapote judgment layer was `docs/SAPOTE_SLIM_JUDGMENT_KERNEL.md`, a condensed prompt document designed to be loaded into a frontier LLM session alongside a Mamey package. It described 17 modules (MODULE 0 through MODULE 17) covering intake, assembly declaration, BGC inventory, architecture-first assessment, wet-lab scoring, RGGMCI split-pathway validation, Mode B cards, DAPR boards, fermentation, and ecology. The "slim" in the name was deliberate: it was a compressed version of the full controller, designed to fit in a context window.

The slim kernel was retired as the default controller at v9.7.147. Its replacement is `docs/CHATGPT_EXECUTION_SLICE_v97147.md`. Both files are still in the bundle; the slim kernel is retained for legacy integrations only. If both are loaded, the execution slice overrides.

### The current controller: the Execution Slice

The Execution Slice (`docs/CHATGPT_EXECUTION_SLICE_v97147.md`) is the authoritative operating contract for the Sapote judgment layer. It is intentionally not a summary — it is full-depth, because abbreviation was identified as the primary failure mode of the slim kernel. The key non-negotiable rules it enforces:

- Every BGC must be visible in the triage board. None may be silently omitted.
- Edge and full-contig BGCs are not buried. They receive the same scientific depth as interior BGCs at the same priority rank, because for POOR and VERY_POOR assemblies the boundary is usually an assembly artefact, not a real missing locus edge.
- The session does not end at `MAMEY_COMPLETE`. A package without Sapote judgment is a skeleton. The Execution Slice requires a JUDGMENT PENDING banner and a complete handback of all code-backed outputs (strain brief PDF, figures, locus maps, workbook) before judgment begins.
- Mode B is prose-first. Tables are companions, not substitutes.
- Every substantive handback ends with exactly 8 distinct numbered next paths.

### The module sequence (as it stands in the slim kernel, still the conceptual backbone)

| Module | Name | What it does |
|---|---|---|
| 0 | Intake | Read `manifest.json`, confirm MAMEY_COMPLETE, preserve typed bioactivity metadata state |
| 0.5 | RGGMCI front-end | Read split-pathway reconstruction pairs before any Mode B |
| 1 | Assembly declaration | State tier, interior %, FLBR warning if megasynthase is fragmented |
| 2 | BGC inventory | Full table, sorted by Corrected_rank, no interior-first bias |
| 2.5 | Architecture-first assessment | Classify each BGC from gene domain content before reading KCB |
| 3 | Architecture confidence | Validate Arch grades; apply two-level split-pathway rule |
| 4 | Wet-lab decision score | Four-axis WL score + LMPKS bonuses |
| 5 | DAPR boards | Antibacterial (AB) and antifungal (AF) ranked leads |
| 6–16 | Mode B cards | Full §1–§30 per lead BGC (see Part III) |
| 17 | DAPR final | Consolidated AB/AF deliverable |

The Execution Slice extends this with additional structure: the mandatory handback block (§3 of the slice), the interpretive floor check before §19 (§8), the conditional §21–§30 extensions (§9), and the final output gate checklist (§11).

---

## Part III: The Gate Stack

This is the section that has grown fastest and is easiest to lose track of. The system now has a layered set of gates that enforce correctness at different points. Here they are in the order they apply:

### Gate 1: Mamey doctor (`mamey doctor`)

A pre-run environment self-check. Confirms Python version, required libraries (openpyxl, biopython, ijson, numpy, matplotlib), file permissions, and the presence of required bundle files. Also reports the add-on stack status (the science/HMM/figure wheels). Exit 0 = environment is ready to run; warnings are acceptable (optional deps only). This gate is a prerequisite, not a quality gate on analysis.

### Gate 2: Mamey validate (`mamey validate <pkg>`)

The package seal gate. Checks structural completeness, SHA256 checksums, and schema compliance. Produces `gate_validation.json` with pass/fail per check. A `MAMEY_COMPLETE` status is required before any Sapote judgment can run. This is enforced behaviorally by the Execution Slice (it aborts if the package is not sealed) and programmatically by the Sapote Workflow Contract (W0).

### Gate 3: Architecture-first assessment (internal, `mamey/architecture_first.py`)

Before any KCB similarity score is read, the system classifies each BGC's pathway type from its gene domain content alone. This gate exists because KCB similarity is not product class assignment — the KnownClusterBlast tool finds the most similar known cluster, but similarity does not mean the same compound. Known failure modes: a T2PKS architecture getting a terpene KCB anchor because a terpene gene sits adjacent to the boundary; a trans-AT PKS getting a polyunsaturated fatty acid KCB because the KS subdomain matches. When architecture and KCB disagree, architecture wins.

### Gate 4: Interpretive floor check (`INTERPRETIVE_FLOOR_CHECK`, `docs/MODEB_INTERPRETIVE_FLOOR_v97146.md`)

Before §19 (the final Mode B verdict) can be written, five sections must meet a minimum depth threshold:

- **§5** (Core biosynthetic logic) must connect domain architecture to structural consequences — not just name the domains. "The KS domain catalyses Claisen condensation" fails this gate.
- **§9** (Alternative hypotheses) must weigh each alternative against evidence, not just list them.
- **§11** (Product-family interpretation) must connect the tailoring complement to scaffold complexity implications.
- **§12** (Ecological interpretation) must reason through mechanism, not just name the context.
- **§19** itself must be structured as an argument: evidence summary → alternative rejection → claim ceiling → confidence tags.

If any section is thin, the gate requires expanding it before writing the verdict. This gate is currently enforced behaviorally (the Execution Slice instructs the LLM to run the check) rather than programmatically.

### Gate 5: Mode B structure gate (`mamey verify-modeb`, `mamey/modeb_structure_gate.py`)

The structural and depth validator for completed Mode B cards. It reads the authored `.md` file and checks:

1. All §1–§20 section headings are present, in order, with exact titles.
2. §28 (Evidence provenance ledger) is present.
3. §30 (Experimental decision tree) is present.
4. All conditional §21–§27/§29 sections that apply to this BGC are present (predicate-evaluated).
5. Section 4 contains prose, not only tables.
6. Important genes include protein length where available.
7. The card is not thin — a structurally complete but interpretively empty card fails.

A hand-built document with self-invented section titles fails `NO_HEADINGS_DETECTED`. The template emitter (`mamey emit-modeb-template`) should always be used to start a card; hand-rolling the scaffold is a known failure mode documented in `docs/ISSUES_EXPERIENCED_DURING_DEVELOPMENT.md`.

**Important distinction:** `mamey mode-b` (the subcommand) produces a triage top-leads table — one metadata row and a gene table per BGC. This is *not* a Mode B card. The §1–§30 card is produced by `emit-modeb-template → author prose → verify-modeb`. They share a name and are different artifacts.

**§4 evidence gate now bites (MB-01, v9.7.338).** The §4_BLASTP_COVERAGE / `EVIDENCE_GAP` check was for a long time dead on every card produced by the supported workflow (its bare-verdict branch matched the emitter's own unauthored skeleton text; its coverage clause was satisfied by digits inside the locus tag). Those holes are closed and the gate now fires: when the strain carries a BLASTp panel, a §4 that asserts `CONFIRM/REFINE/OVERTURN` without the reconciled per-gene closest-match table — or with no authoritative package core count reaching the gate — raises an `EVIDENCE_GAP`/`COVERAGE_UNVERIFIED` **WARN** and the summary reads `OK (§4 coverage NOT verified — no package core count)`. WARN-level, matching depth severity; never a structural refuse. Re-run with `--package … --bgc …` so the real-core-count coverage gates.

**`--interp` (v9.7.338) — the interpretation/judgment gate.** `mamey verify-modeb --package <pkg> --bgc <BGC_ID> --interp` layers a judgment check over structure + depth: it flags a card that asserts a class read without at least one alternative interpretation, a resolving experiment, or capacity-level (not production) framing. **WARN-only** — advisory to the author, never a blocker.

### Gate 6: BGC Guide quality gate (`mamey verify-guide`)

The analogous gate for the BGC Guide deliverable. The Guide has a deterministic skeleton emitted by `mamey guide` — the engine populates coordinates, domain annotations, gene counts, and BLASTp readouts from the evidence store. The PI (or Sapote) authors prose into the `<!-- LAY: ... -->` slots. `verify-guide` reads the finished file and fails on any residual empty slot, any Part that is thin, or any gene subsection missing its plain-language summary. The skeleton's own quality gate (`guide_quality_gate`) only validates the skeleton's structure — it cannot see authored prose and always passes on an empty template.

### Gate 7: Sapote Workflow Contract (`tools/sapote_workflow.py`, `docs/SAPOTE_WORKFLOW_CONTRACT.md`)

Added at v9.7.237. This is the ordering gate — it enforces that the judgment layer's steps happen in sequence rather than being reported complete out of order. It reads the real package artifacts, marks each of 11 steps PASS / PENDING / BLOCKED / N/A, and (with `--strict`) exits non-zero if any mandatory step is incomplete.

The steps in order: W0 (sealed package) → W1 (triage board) → W2 (lead boards) → W3 (Mode B templates emitted) → W4 (Mode B cards authored and verified) → W5 (BGC Guides, conditional) → W6 (narrative set) → W7 (compiled report) → W8 (13-item deliverable suite) → W9 (judgment receipt) → W10 (session close + 8 next paths).

A step is BLOCKED when its mandatory predecessor is not PASS. The driver never invents artifacts — a missing file is PENDING, never silently PASS.

### Gate 8: Compiled report gate (`mamey compile-report --strict`)

Before the compiled report is deliverable, `compile-report --strict` verifies that no SAPOTE narrative slots are still open. Unfilled slots (executive summary not written, layperson guide missing, ecological synthesis missing) cause exit non-zero. Narrative sections are written into the package using `mamey write-narrative`; each write runs the claim-safety linter and is refused (exit 3) if the linter flags a safety violation.

### Gate 9: Deliverable suite gate (`tools/check_deliverable_suite.py`)

Mechanically enforces the 13-item full-run deliverable contract. Reads a filled `DELIVERABLE_MANIFEST_<strain>.md` and fails closed on unfilled items, under-justified items, and JUDGMENT_PENDING gold gate violations.

### Gate 10: Judgment receipt (`tools/sapote_judgment_receipt.py`)

The write-back artifact that flips `gold_completeness` from asserted to verified. Until this runs, the package's completeness status is unconfirmed. Fails closed.

### Gate 11: Claim-safety linter (`tools/claim_safety_linter.py`)

A post-hoc linter for Sapote interpretive text. Scans for language that violates the claim-safe vocabulary: production claims ("produces X"), structure assertions ("the compound is a macrolide"), bioactivity attributions per-BGC ("this BGC inhibits MRSA"). Flags but does not automatically block unless invoked from `write-narrative`, where it causes a hard exit 3.

### Gate 13: Analysis sign-off gate (`mamey signoff`, `tools/signoff_check.py`) — v9.7.338

The QC gate for phylogenomic/taxonomy analysis, distinct from the BGC gates above: `mamey signoff <tree.treefile>` mechanises the objective items of "would a master's student sign off?" — outgroup sanity (a genuine sister group, not a distant taxon), ANI-boundary honesty (calls within ~1% of 95% are boundary/indeterminate; never quote AAI as ANI), assembly-quality flags, comparator provenance, label integrity, and support/sampling. **Advisory** — it reports check outcomes and never blocks a deliverable; it is also wired as a `Stop` hook and stays silent when clean.

### Gate 12: Novelty contradiction guard (`conservation_saturated`, engine 1.9.111)

Added at v9.7.239/240. When the genome-wide median BLASTp identity against nr exceeds the novelty floor (≥90%), the guard fires. Rather than being suppressed, it is made interpretable: the system reports the genome-wide conservation background and the delta for each BGC relative to that background. AS-XXX demonstrated why this matters: all 36 BGCs fired the guard (medians 92–99%) because *Streptosporangium saharense* is in nr, so the absolute identity measures "does this genus have a sequenced member," not "is this cluster distinctive." The correct signal is the delta (BGC identity minus background). A BGC at 94% identity in a genome with a 95.4% background (Δ−1.6%) is not novel by absolute identity, but it is also not identifiably distinctive — which is the honest conclusion.

---

## Part IV: What Has Changed — Recent Cuts

This section tracks additions and changes to the Sapote-facing parts of the system, most recent first. Engine changes that affect scoring are noted separately from pure documentation/gate additions.

---

### v9.7.338 — Interpretive-priors + cross-strain deliverable surface, two gate behaviours

**New Sapote-facing subcommands/deliverables (all claim-safe, capacity-level; judgment deferred):** `good-guesses` (the interpretive-priors report — per notable BGC, the single best class read tagged `solid`/`rare`/`remarkable`/`notable`/`interesting`, with a confidence band and the resolving experiment; `md`/`csv`/`docx`/`pdf`), `comparator-coverage` (two-denominator MIBiG comparator-coverage evidence — matched/all-locus-genes **and** matched-core/all-defining-core, the false-positive killer for comparators carried by housekeeping genes; report-only, non-scoring), `af-dossier` (Antifungal Lead Dossier × optional measured-*Candida* join), `novelty-shortlist` (strongest reference-dark candidates — a prior, not proof), `realistic-count` (honest corrected BGC denominator), `modeb-export` (Mode-B §1–§30 cards → docx + pdf), `domain-reference` (domain glossary + per-BGC ordered-domain readout), `cohort-leads` (cross-strain priority-leads CSV), `cohort-assemble` (cross-cohort master workbook), and `figures kcb-locusmap` (offline KnownClusterBlast comparative locus map). See Part VI and the Operational Reference §9 for invocations.

**MB-01 — the §4 Mode-B evidence gate now bites.** The §4_BLASTP_COVERAGE / `EVIDENCE_GAP` check, previously dead on every card from the supported workflow, now fires: a §4 asserting `CONFIRM/REFINE/OVERTURN` without the reconciled per-gene table (or with no authoritative package core count) raises a WARN. WARN-level, never a structural refuse (Gate 5).

**RG-01 — the NAPAA standing rule now follows the registry.** NAPAA (ε-poly-L-lysine synthetase / TIGR02353) is now **registry-NEUTRAL** — the rule is read from `mamey/data/rules_registry.json` rather than a hardcoded exclusion, so a BGC whose *own product* is NAPAA is no longer auto-excluded from comparative/ecological claims. NAPAA is common and frequently adjacent to genuine BGCs; it is neither downgraded nor lead-blocked (the retired Nosema hypothesis does not justify excluding NAPAA itself). Combo-detection routing on TIGR02353 is unchanged.

**Analysis sign-off gate (`signoff`).** Advisory QC gate over phylogenomic trees — see Gate 13.

---

### v9.7.241 (2026-07-09) — BLASTp overlay write bug fixes (P7a/b/c)

**What broke.** Three bugs in the multi-round BLASTp ingest path — the path introduced in v9.7.239 to support the novelty guard overlay.

**P7a (write_nr_overlay truncation).** `write_nr_overlay()` opened the output CSV in `"w"` mode. Because a genome's BLASTp campaign runs in rounds (one batch → one Hit Table → one `ingest-blastp` call per round), every round erased the previous round's data for any BGC it touched. On a real 30-round AS-XXX campaign: 877 genes in, 504 retained — 373 lost (43%), worst case BGC042 44→7 genes. Fixed: now merges by `locus_tag`, higher bitscore wins a collision. Post-patch: 877/877.

**P7b (antismash_domains hardcoded to empty).** The `antismash_domains` field was hardcoded to `""` on the `ingest-blastp` path (a sibling to P5 in v9.7.240, which fixed the same field on the `blastp-online` path). The field is the input to `reconcile(domains, hit_def)` which categorises hits as CONFIRM / REFINE / OVERTURN based on whether the BLASTp hit agrees with the antiSMASH domain call. With `antismash_domains = ""`, `reconcile()` could only return REVIEW — the entire discrimination column carried no signal. Fixed: field now backfilled from `*_gene_context.jsonl` on the `gene=` token; fails open when gene_context is absent.

**P7c (B5_BLASTp_Hits append not idempotent).** Re-ingesting a Hit Table multiplied rows (150→300→450). Fixed: keyed on `(strain, query_locus, subject_acc, hit_rank, q_start, q_end)`; `duplicates_skipped` returned in the result.

**Scientific correction.** The v9.7.240 changelog reported AS-XXX conservation background "over 504 genes" — that 504 was P7a's truncation. Corrected: background 95.4% over 877 genes. Per-BGC `n` values also corrected (BGC028: 29→66, BGC042: 7→44). Conclusions unchanged — no AS-XXX BGC is distinctive against its genome background — but the evidence base for those conclusions was biased by 43%.

**Tests added:** 29 new tests in `test_as421_patchset_v9_7_240.py` and `test_blastp_ingest_overlay_v9_7_241.py`. All 2,842 suite tests pass.

---

### v9.7.240 (2026-07-08) — Conservation background + cohort BLASTp driver

**Novelty contradiction guard made interpretable.** The guard was firing on 36/36 AS-XXX BGCs (all above 90% identity) because *S. saharense* is in nr. Root cause: absolute identity against nr measures whether a close relative has been sequenced, not whether the cluster is distinctive. Fix: `genome_explore.conservation_background(pkg)` computes the genome-wide median across all overlays; `conservation_saturated(pkg)` is True when this background itself clears the floor. `authored_verify` now reports the delta rather than the absolute. The guard is not suppressed; its interpretation is corrected.

**MAX_BATCH raised 10→30.** The 10-batch cap was overly conservative. AS-XXX's real 878-protein campaign completed cleanly at 30/batch (30 RIDs total, verified).

**`tools/cohort_blastp_driver.py`.** New tool to drive BLASTp + overlay ingest across a scoped set of BGCs (leads / modular / all). The receipt is the overlay file on disk — the driver refuses to mark a BGC done unless the overlay file exists with populated identity + coverage fields. `--plan-only` prints scale before running.

**`ingest-blastp --xml` closes field gap.** The XML2 ingest path now fills `blastp_top_def` and `blastp_organism`, where the outfmt10-only path left both blank.

**Five-defect AS-XXX audit patch set (P1–P5).** The audit session found and fixed: P1 over-merge banner was region-unscoped (13 wrong banners → 7 correct); P2 authored_verify aliased `single_protocluster_count` onto `protocluster_count` (wrong for BGC041); P3 UMED registry patterns were unanchored (14 false LanT_C39 hits → 1 real); P4 `isolate-giants` shredded BGC groups into singletons; P5 `blastp_online` never populated `antismash_domains` (`cluster_coherence` reported n_core=0 on every cluster ever analysed).

---

### v9.7.239 (2026-07-08) — Novelty guard overlay write path

Introduced the nr-overlay write path: after each `ingest-blastp` round, an overlay CSV per BGC is written to `blastp_online/<BGC>_online_blastp.csv`. This was the infrastructure P7a subsequently found to be truncating.

---

### v9.7.237 (2026-07-08) — Sapote Workflow Contract + false-PASS gate fix

**Sapote Workflow Contract.** Formalised the mandatory ordered step sequence for the judgment layer (W0–W10) as both a documentation contract (`docs/SAPOTE_WORKFLOW_CONTRACT.md`) and an executable gate (`tools/sapote_workflow.py`). Before this version, the delivery order existed as prose across several documents, but no single driver enforced it. Now: a downstream step is BLOCKED until its mandatory predecessor is PASS; `--strict` exits non-zero if any mandatory step is incomplete.

**`sapote_workflow.py` false-PASS gate.** Several workflow gate checks were returning PASS incorrectly. The gate was reading marker files that existed but were empty, treating existence as completion. Fixed: each step now reads the actual artifact contents and checks the relevant fields.

**AS-series public scrub deactivated.** `AS_SCRUB` flag is now off by default — the AS-series cohort is public as of the 2026 Hymenoptera paper (PI decision 2026-07-06). The scrub can be re-armed with `AS_SCRUB=1` for a future private cohort. The `is_private('AS-XXX')` return corrected to False; `derive_release('AS-XXX')` now returns PUBLIC.

---

### v9.7.236 (2026-07-08) — AS-series release tier reconciliation

Resolved the conflict between `dedup_and_guard.derive_release` (which was returning PRIVATE for any AS-series strain) and the figure tier (which already treated them as public). Both now agree: AS-series strains are PUBLIC; AJS-/PENDING- remain private.

Also: audit record-keeping protocol bundled (`docs/audit_recordkeeping/`). Standing templates for finding ledger, decision log, run ledger, and instruction-compliance matrix. These are the reviewable audit trail that the recurring proxy-verification failures (gates that didn't actually read the output file they claimed to verify) argued for.

---

### v9.7.186 (engine 1.9.107) — NP Atlas resolver + `mamey guide`

**NP Atlas compound-reference resolver.** A new `B6_Compound_Reference` workbook sheet enriches each BGC's KCB-named compound with molecule-level chemistry from NP Atlas: npclassifier compound class, molecular formula, exact mass, [M+H]⁺ and [M+Na]⁺ ions, InChIKey, primary DOI/PMID. This sheet is INVENTORY_ONLY — it makes no genus-restriction or product-identity claim. Useful for feeding metabolomics acquisition lists with correct precursor masses.

**`mamey guide`.** New deliverable: the per-BGC BGC Guide, a layered explanation with a deterministic skeleton (facts, BLASTp readouts, gene groupings) emitted by the engine and prose slots authored by Sapote. The Guide is distinct from the Mode B card: it is intended for a broader audience (bench scientists who did not run the pipeline) and its per-gene claims are capped at the BLASTp `evidence_tier` field. The guide quality gate at seal time (`guide_quality_gate`) validates the skeleton's structure; `mamey verify-guide` validates the authored prose.

---

### v9.7.157 (engine 1.9.103) — Mandatory deliverable gate

Post-seal auto-emit of the compiled report. The engine now automatically attempts to produce the compiled report after `MAMEY_COMPLETE`; if SAPOTE narrative slots are still open, the gate notes them and the compiled report is produced with explicit placeholders rather than silently incomplete. Non-blocking but tracked.

---

### v9.7.152 (engine 1.9.101) — macOS cruft filter + `--capped-session` rename

macOS resource-fork files (`._*`, `__MACOSX/`, `.DS_Store`) were being double-counted in `namelist()` sweeps, causing spurious "N/2N GBK files yielded no records" warnings on antiSMASH ZIPs created on macOS. Now filtered at every namelist sweep.

`--chatgpt-safe` renamed to `--capped-session` (deprecated alias retained). The flag applies timeout-safe defaults for sessions with execution limits.

---

### v9.7.150 / v9.7.150e — §1–§30 Mode B contract + `emit-modeb-template`

**The §1–§30 expansion.** Before v9.7.150, the Mode B card contract was §1–§20. Ten conditional sections (§21–§30) were added:

- §21–§22: RiPP-specific sections (precursor mass ladder, RiPP database search). Required for any RiPP BGC.
- §23: Heterologous expression. Required when a MATURATION_GAP is present or the compound class is novel.
- §24: Scaffold novelty score. Required when there is no MIBiG hit.
- §25: Genome neighbourhood. Required for isolation-worthy BGCs.
- §26: OSMAC protocol. Required for fermentation-selected BGCs.
- §27: Self-resistance assessment. Required for any antimicrobial candidate (which is the default for AB/AF leads).
- §28: Evidence provenance ledger. **Always required** — every claim tagged as observed/computed/inferred/assumed.
- §29: Cross-cluster interactions. Required when the strain has >3 high-priority BGCs.
- §30: Experimental decision tree. **Always required** — open questions mapped to experiments and programme consequences.

The single source of truth for the contract is `mamey/data/mode_b/modeb_full30_corrective_contract.json`. The validator and the template emitter both read this file. Any schema discrepancy between the docs and the JSON is resolved by the JSON.

**`mamey emit-modeb-template`.** The canonical starting point for any Mode B card. Given a package and a BGC ID, it emits a §1–§30 skeleton pre-filled with the BGC's facts from the triage board. Batch mode (`--batch --scope all|top|leads|pending`) writes one template per BGC and an `_INDEX.md` work order. Hand-writing a card from scratch is documented as a known failure mode that produces a §1–§10 shape and fails the structure gate.

**`mamey render-all-figures`.** New post-seal command that runs the full figure suite (smoke, brief, locus-maps, figure-suite, domain-level) after `--capped-session` runs that suppressed them for wall-clock budget. Recommended after every capped run.

**Schema consolidation (N10).** Before v9.7.150e there were six different §1–§20 schema sources in the bundle. N10 collapsed them to one: `modeb_full30_corrective_contract.json`. The validator's facade derives sections via `load_contract()`. `tools/regen_modeb_contract_docs.py --check` enforces no drift in CI.

---

### v9.7.147 — Execution Slice replaces Slim Kernel; Trigger Routing Table

**The Execution Slice.** `docs/CHATGPT_EXECUTION_SLICE_v97147.md` becomes the default ChatGPT/Sapote controller, replacing the Slim Kernel. The Slim Kernel is retained for legacy integrations.

**Interpretive floor gate.** `docs/MODEB_INTERPRETIVE_FLOOR_v97146.md` formalises the minimum depth requirements for §5, §9, §11, §12, and §19. The `INTERPRETIVE_FLOOR_CHECK` trigger constant fires before §19 is written.

**`MAMEY_COMPLETE_HANDOFF_REQUIRED`.** The execution slice now requires a formal handback block before any judgment begins: surface `OPEN_ME_FIRST.html`, `manifest.json`, the strain brief PDF, all figures, locus maps, the workbook, and the checksums file. Then emit a JUDGMENT PENDING banner. A handback without this block is incomplete.

**Trigger routing table.** `docs/TRIGGER_ROUTING.md` becomes the single authoritative routing table for all workflow, quality-gate, and biology-specific escalation triggers. Named trigger constants are formally defined and tested. Conflict guard between `OFFLINE_EVIDENCE_ALLOWED` and `WISE_PKS_QUEUE_DETECTED` is documented and enforced.

---

### v9.7.145 — Node/region citation enforcement

Every BGC must be cited as `BGC007 (NODE_1_length_406707 · region001)` on first mention in any deliverable. Bare BGC IDs without node/region are invalid. `mamey/validators/node_notation.py` implements this check and is unit-tested (`tests/test_node_notation_v97145.py`), but as of the v9.7.374 audit it has no production call site anywhere in the pipeline — nothing invokes it on a generated Mode B card or compiled report, so this rule is not currently mechanically enforced; it is a standing-rule instruction for the author (human or LLM), not a machine gate. The rule exists because BGC IDs are assigned run-locally and may collide across strains — the only unambiguous identifier is the contig name + region number combination.

---

### v9.7.142 (engine 1.9.100) — BLASTp evidence store + online BLASTP channel

Major addition: the durable BLASTp evidence store. Before v9.7.142, BLASTp results lived only in chat and were lost between sessions. Now:

- `mamey blastp-online` submits a BGC's protein set to NCBI BLASTp (real network calls; fail-closed on network error), scopes extraction to one BGC, and writes a `§4 panel CSV` to the evidence store.
- `mamey ingest-blastp` ingests Hit Table CSVs or BLAST XML2 files from a prior run (offline path).
- `mamey/blastp_evidence_store.py` is the durable per-BGC store. Results written here persist across sessions.
- `mamey ingest-receipts` is the Sapote→store front door: a session ends by writing a `mode_b_receipt.json`; this command persists each card, flips the register to COMPLETE, and reconciles the workbook's `E1_Mode_B_Index`. Mode B cards should never live only in chat.
- `mamey/citation_compact.py` separates runtime evidence from literature verification. `PASS_STRUCTURE` means the package structure passed; it does not mean every literature claim is verified.

---

### Engine 1.9.104 (v9.7.158) — KCB scoring fix

Two bugs fixed in `mamey/antismash_evidence.py`:

1. KCB score aggregation was pooling `knownclusterblast/clusterblast/subclusterblast` records and taking max across all three. Now restricted to `knownclusterblast` records only.
2. `_parse_txt_evidence` was taking `max(blocks, key=score)` as best hit rather than rank-1. KnownClusterBlast ranks hits by similarity; a lower-ranked hit can have a higher raw score if it matches a sub-region more tightly. The rank-1 hit is the correct best match.

**Every strain's `kcb_top` field and KCB-derived scores (novelty, lead tier, DAPR rank) may differ under this engine from earlier versions.** Any strain processed under engine ≤1.9.103 and used in KCB-dependent downstream decisions should be re-run.

---

## Part V: Terminology Reference for the Above

**RGGMCI (RG-GMCI):** RG-based Gene-Module Correspondence Index. The split-pathway reconstruction module. When a BGC is too large for a single contig (common in POOR/VERY_POOR assemblies), Mamey identifies pairs of BGC fragments that likely belong to the same biosynthetic pathway using corroborating evidence (CORE trigger = shared KCB reference; ARM trigger = shared domain class or adjacent gene order). Validated pairs are in `_4A_RGGMCI_ranked_pairs.csv`.

**FLBR:** Megasynthase fragmentation census. FLBR = STRONG means at least one large modular PKS or NRPS pathway (≥6 modules, roughly ≥100 kb in a non-fragmented genome) is distributed across multiple contigs. This triggers the LMPKS rescue workflow.

**CCTT triggers:** A set of coded trigger labels that fire when specific biosynthetic domain combinations are detected. `T43-HAL` = halogenase (Trp_halogenase domain); `T43-ENE` = enediyne (the E-signal). Each trigger carries a bonus to the BGC's priority score (+≤2, non-stacking). The [E-signal] trigger for enediyne BGCs replaced the earlier BSL-2 per-BGC flagging approach; it is now a neutral annotation.

**UMED:** Unusual/uncharacterised Maturation Enzyme Detection. Scans for maturation enzyme families that antiSMASH does not specifically annotate: RiPP RRE domains, C39 peptidase transporters, FlaP/AplP S9 proteases, SPASM radical-SAM domains. UMED hits are logged in `B4_Cross_Strain_Scans` and influence the presence/absence of §21–§22 in Mode B cards.

**CGAD:** Chitinase and GH18 domain scan. Relevant to the ecological interpretation of bee- and ant-associated isolates: chitinases may target fungal cell walls (Ascosphaera, Botrytis) or the insect cuticle. CGAD output appears in `F1_Ecology_Readiness`.

**DAPR:** Dual-Axis Priority Ranking. The AB (antibacterial) and AF (antifungal) lead boards. Each BGC receives an AB score and an AF score. Scoring weights: compound class bucket (from the DAPR class framework) × self-resistance tier (T1 APH/Van/Erm = highest, T3 transporter-only = lowest) × boundary status (interior > edge > full-contig, but only for GOOD/MODERATE assemblies — POOR/VERY_POOR assemblies receive no boundary penalty).

**KCB / KnownClusterBlast:** antiSMASH's reference-database comparison tool. It aligns the BGC's proteins against the MIBiG database of characterised clusters and reports a similarity percentage. KCB similarity is *not* product identity — it is a similarity signal that informs class assignment. When no MIBiG hit exists, the BGC is an orphan and §24 (scaffold novelty score) is required in the Mode B card.

**WL score:** Wet-Lab Decision Score. A composite priority score combining AB and AF axes with LMPKS fragmentation bonuses. Used to rank BGCs for isolation experiments.

**Assembly tiers:**
- GOOD: ≥70% of all BGCs are interior (fully on a contig)
- MODERATE: ≥45% interior
- POOR: ≥20% interior
- VERY_POOR: <20% interior

*Note: the 66/50/33 thresholds used in earlier versions are retired.*

**Confidence vocabulary (applies to all Sapote-authored prose):**
- **observed:** directly present in a named field or database hit
- **computed:** derived by a stated deterministic rule
- **inferred:** drawn from multiple observed facts by reasoned argument
- **assumed:** default position in absence of contrary evidence — must be flagged

**Claim-safe language:** capacity consistent with X, not "produces X" or "is X." KCB similarity, not KCB identity. Bioactivity metadata is optional strain-level context. No per-BGC bioactivity claim without governed linkage.

---

*Sources: `docs/ENGINE_LINEAGE.md`, `docs/CHATGPT_EXECUTION_SLICE_v97147.md`, `docs/SAPOTE_SLIM_JUDGMENT_KERNEL.md`, `docs/FULL_MODEB_30_SECTION_CONTRACT_v97150.md`, `docs/MODEB_INTERPRETIVE_FLOOR_v97146.md`, `docs/SAPOTE_WORKFLOW_CONTRACT.md`, `docs/TRIGGER_ROUTING.md`, `docs/DAPR_CLASS_FRAMEWORK.md`, `CHANGELOG.md` (v9.7.237–241), `BUILD_STAMP.txt`. Compiled from primary bundle sources; no inference from general knowledge.*

---

## Part VI: The Figure and Deliverable Pipeline

### How figures flow from extraction to deliverable

Figures are produced in layers: the extraction layer emits them from sealed package data; the Sapote layer adds judgment-dependent content; the compiled report assembles them into the final deliverable.

The extraction-layer figures (`_8a` through `_8m`) require only `manifest.json` and the triage board CSV. They are deterministic — the same package always produces the same figures. The gold figures (F01–F15) require deep_data and a multi-strain cohort. All figures ship companion `_data.csv` files so a scientist can reproduce or restyle any figure in their preferred environment without touching the engine.

**The `--capped-session` suppression pattern** — Under `--capped-session`, `--brief none` is applied, suppressing all figure rendering inside the session to stay within wall-clock limits. This is correct behavior, not an error. The recovery command is `mamey render-all-figures --package <pkg>`, which re-runs all figure modules post-seal and populates the full suite. `NO_FIGURES_RENDERED.md` in the package is the marker file; if `mamey compile-report` detects it, it runs `render-all-figures` before presenting the handback.

**Figure policy** — The `mamey/figure_policy.py:is_pure_saccharide()` function is the single gate controlling which BGCs appear in figures. Pure-saccharide BGCs are excluded from all figures and covered only in text. No individual figure module duplicates this logic — they all import from `figure_policy`. This ensures that a policy change propagates to all figures automatically.

### The compiled report assembly sequence

The `mamey compile-report` pipeline assembles the §13 master deliverable. Build order is mandatory:

1. Generate derivable figures from triage CSVs (`fig_bgc_ranking`, `fig_class_composition`, `fig_assembly_tier`).
2. Generate domain-strip locus maps for top-priority BGCs.
3. Resolve any reclassified or invalidated Mode B cards.
4. Assemble sections in this exact order: Cover → Executive summary → Layperson guide → Assembly summary → Triage board (all BGCs) → Figures → Cross-strain synthesis → Priority lead deep-dives → Complete Mode B cards → BLASTp evidence summary → Fermentation guidance → Wet-lab matrix → Outstanding work → Methods and claim-safety note.
5. Gate delivery on `mamey compile-report --strict` (open SAPOTE slots → exit non-zero).

**TOC auto-generation** — Table of contents must be auto-generated by pandoc, never hand-written. Hand-written TOCs in a long document diverge from actual page numbers by 50+ pages. Use YAML front-matter `toc: true` in the pandoc command.

### The deliverable offer protocol

After `MAMEY_COMPLETE` is detected, the next Sapote response must surface the code-backed output block (OPEN_ME_FIRST.html, manifest.json, strain brief PDF, figures, locus maps, workbook, checksums, issue log), then emit the JUDGMENT PENDING banner, then either auto-produce or explicitly offer the full prompt-backed set. A handback that stops at "the run completed" without surfacing files is non-conformant.

---

## Part VII: Common Failure Modes with Diagnostic Paths

These are the failure modes that produce incorrect output without crashing — the dangerous kind, because they look like valid results.

### Silent truncation failures

**P7a pattern** — A multi-round write path that opens in `"w"` mode truncates to the last round's data. The P7a bug in `write_nr_overlay()` was exactly this: 30-round BLASTp campaign produced 877 genes but the overlay retained only 504 (43% loss) because each round erased the previous round's BGCs it touched. Diagnostic: compare the number of genes with overlay entries against the number of genes submitted to BLASTp. If overlay coverage is below 100%, suspect a write-mode bug in the ingest path. Fix path: always open overlay CSV in merge mode keyed on `locus_tag`, higher bitscore wins.

**Silent field hardcoding** — A field computed correctly at one stage but hardcoded to a constant downstream. P7b: `antismash_domains` hardcoded to `""` meant `reconcile("", hit_def)` could only ever return `REVIEW` — the column looked populated but carried no signal. Diagnostic: check a computed column's value distribution; if every row has the same value (or blank), suspect hardcoding. The CONFIRM/REFINE/OVERTURN ratio in the §4 panel should not be 0:0:N for all BGCs.

**Non-idempotent append** — P7c: `B5_BLASTp_Hits` append was not keyed, so re-ingesting the same Hit Table multiplied rows (150 → 300 → 450). Diagnostic: count rows before and after a second ingest of the same file; idempotent operations should produce the same count. Fix: key on `(strain, query_locus, subject_acc, hit_rank, q_start, q_end)`.

### Evidence confabulation failure modes

**KCB genome-self-hit** — The `kcb_top` genome-self-hit bug (fixed v9.7.22): when a strain's own genome is in the reference database, its own BGCs match themselves and receive artificially high KCB scores. This inflates the novelty penalty (`kcb_cumulative > 10000 → novelty −15`) and misidentifies the BGC as a "known cluster" when it is simply the strain itself. Diagnostic: check if `kcb_top` organism field matches the query strain's own species. Fix: the engine filters self-hits during KCB scoring.

**Conservation background saturation** — When a close relative is in nr, ALL BGCs fire the novelty guard (`kcb_cumulative > 90%`). This was observed on AS-XXX (*Streptosporangium*) where *S. saharense* in nr caused 36/36 BGCs to fire. The correction (v9.7.240): compute `conservation_background` (genome-wide median) and report delta (per-BGC identity minus background) rather than absolute identity. When `conservation_saturated = True`, absolute identity is meaningless as a novelty signal.

**Over-merge banner misassignment** — P1 (v9.7.240): the `_over_merge_facts` function matched `predicted_polymers.csv` on the bare contig name, never comparing the region number. Every BGC sharing a contig with an over-merged region inherited the wrong banner. Diagnostic: check that over-merge banners cite specific node·region identifiers, not just node names. A banner on BGC008 that shows the same merge signature as BGC009 and BGC010 (which share a contig) is the P1 pattern.

### Gate bypass failure modes

**sapote_workflow false-PASS** — Gates that check for file existence rather than file contents can report PASS on empty or placeholder files. The sapote_workflow false-PASS pattern (fixed v9.7.237): several W-step checks tested file existence only. Fix: every gate reads the actual artifact, checks required fields, and reports PASS only when those fields are populated.

**verify-modeb checking skeleton instead of authored file** — The `guide_quality_gate` inside `mamey guide` validates the skeleton's structure (it re-derives from the package), not the authored prose. A skeleton always passes. `verify-guide` (the separate command) validates the authored file. Never report guide validation as complete unless `verify-guide` ran on the finished `.md` file. Source: `CLAUDE_START_HERE.md`, section on authoring Mode B.

**TOC page number divergence** — A hand-written TOC in a compiled PDF diverges from actual page numbers as the document grows. The known worst case: a TOC that claimed Outstanding Work on page 60; it was actually on page 113. Always use `pandoc --toc`.

---

*Last updated: 2026-07-09 · v2 additions (Parts VI, VII) · Bundle v9.7.319*

---

## Part VIII: The Gate Stack, Revised (v9.7.246)

Part III listed 12 gates. Two have been added and one materially changed since. The full stack, in application order:

| # | Gate | Enforced by | Blocking? |
|---|---|---|---|
| 1 | `mamey doctor` | environment pre-check | prerequisite |
| 2 | `mamey validate` | structure + checksums + schema | yes (seal) |
| 3 | Architecture-first assessment | `architecture_first.py` (internal) | — |
| 4 | Interpretive floor check | behavioral (§5/§9/§11/§12 before §19) | authoring |
| 5 | **`PHANTOM_LOCUS` referent lint** | `modeb_structure_gate._phantom_locus_findings` | **yes (ERROR, release-blocking)** |
| 6 | `mamey verify-modeb` | structure + depth + readiness | yes |
| 7 | `mamey verify-guide` | authored prose completeness | yes |
| 8 | Sapote Workflow Contract W0–W10 | `sapote_workflow.py` | `--strict` |
| 9 | `mamey compile-report --strict` | open narrative slots | yes |
| 10 | `check_deliverable_suite.py` | 13-item contract | yes |
| 11 | `sapote_judgment_receipt.py` | gold_completeness write-back | yes |
| 12 | `claim_safety_linter.py` | claim-safe vocabulary | via `write-narrative` (exit 3) |
| 13 | Novelty contradiction guard | `conservation_background` / `conservation_saturated` | readiness |
| 14 | **`check_monolith_freshness.py`** | parent-doc anchor + retired doctrine | release (exit 1) |
| 15 | `check_dangling_refs --strict-paths` | path-qualified reference ratchet | release |

### Why gate 5 exists, and why the other twelve missed what it catches

The §4 authoring template hardcoded a genuine per-gene BLASTp result from *Amycolatopsis* sp. NPDC004378 and emitted it, verbatim, into every Mode B card of every strain — including the locus tag `ctg12_71`, which exists in neither strain the cards were written about. 74 cards carried it.

Claim-safety passed: the phrasing was capacity-level. Evidence-presence passed: §4 was non-empty. Citation passed: node·region locators were present. Padding passed: the prose cleared its floor. **Each gate asked a real question. None asked whether the cited gene existed.**

`PHANTOM_LOCUS` asks exactly one question — *does this `ctgN_M` appear in this strain's own CDS table?* — and it opened the class of gates that validate a **referent** rather than a **claim**. The distinction matters for anyone adding gates: "capacity consistent with a glycopeptide" is safe phrasing about a real cluster. "BLASTp settled ctg12_71" is unsafe not because of its phrasing but because the referent does not exist here. No amount of phrasing discipline catches that.

**Two sibling referent lints joined gate 5 in v9.7.256**, for fabrications where the gene *does* exist: `LOCUS_BGC_MISMATCH` (a real locus cited under the wrong BGC — the AS-XXX BGC006/BGC010 leak class) and `PANEL_ABSENT_CLAIM` (a per-gene BLASTp result asserted for a BGC with no panel; it keys on panel *selection*, not returned alignments, so an in-panel-but-never-run BGC still passes — reproduced on `S_erythraea` BGC017). Both are ERROR-severity → `DRAFT`; neither is a member of the four-code `_READINESS_BLOCKING` set below, which is unchanged.

**Fail-silent by design.** With no CDS table the lint returns nothing. The source states the reasoning: *"it cannot judge what it cannot see, and a false accusation of fabrication is worse than none."* This is the correct direction for a lint whose ERROR verdict is "you fabricated an observation."

### The readiness state machine (the presentation gate)

`verify-modeb` reports one of three states. Only the last may be presented.

```python
_READINESS_BLOCKING = {"NOVELTY_CONTRADICTION", "INTERNAL_CONTRADICTION",
                       "FACT_MISMATCH", "PHANTOM_LOCUS"}

DRAFT          ← any ERROR finding, or quality_tier in (None, STUB, UNKNOWN)
VERIFIED       ← depth adequate, but a blocking correctness code is present
RELEASE_READY  ← depth adequate AND no blocking code
```

A card can be structurally complete, adequately deep, and claim-safe, and still be held at `VERIFIED` — because a fact in it contradicts the package, or a locus in it belongs to another organism. That is the intended behaviour.

---

## Part IX: Version-by-Version — v9.7.243 through v9.7.246

*Most recent first. Engine 1.9.111 throughout; no scoring change in any of these cuts.*

### v9.7.246 — The fabricated observation, and the gate that catches it

Documented above and in the Development Issues Compendium (Group 13). One sentence of summary: **a true example from the wrong organism is more dangerous than an obviously wrong one, because it survives review.**

Two fixes. *Source:* §4 keeps the methodology and now cites the validation set by path with the instruction "a different strain — do not cite its loci here"; §8 keeps the colibrimycin-class lesson without the foreign BGC id or score. All 30 sections swept — zero foreign loci, BGC ids, or scores remain in any emitted body. *Net:* the `PHANTOM_LOCUS` lint, wired into `_READINESS_BLOCKING`, with `known_loci` loaded from the sealed `<strain>_cds_table.csv`.

**The 74 already-authored cards are not repaired by this cut.** Re-running `verify-modeb` with a sealed package flags every one. Every §4 and §16 paragraph containing `ctg12_71` should be **deleted, not reworded** — there is no BLASTp result to reword.

### v9.7.245 — Three defects the outside verifier found, each reproduced before it was touched

**`region_label(-1)` returned `region001`.** `re.search(r"(\d+)", "-1")` matches `"1"` — the sign is not part of `\d+` — so the negative was dropped before the `n > 0` check could see it. The function contradicted its own stated rule. Found by a verifier who **tested the boundary the fix note named, instead of assuming the note covered it.**

**Owned regression from v9.7.240: `chunk_proteins` defaulted to the ceiling, not the courteous default.** v9.7.240 raised `MAX_BATCH` 10 → 30 on the strength of a real 878-protein AS-XXX run, and added `DEFAULT_BATCH = 10` — *which nothing ever read.* The signature still said `batch_size: int = MAX_BATCH`. Every caller that omitted `batch_size` silently tripled its NCBI submission size. Verified: `chunk_proteins(60)` returned `[30, 30]`; now `[10] × 6`. Explicit `30` still honoured; `99` still clamps to 30.

**The nr overlay was invisible to the BGC Guide.** `ingest-blastp --package` writes `blastp_online/<BGC>_online_blastp.csv`, whose gene column is `locus_tag`. `bgc_guide._load_blastp_store()` did `if "query_gene" not in r: continue` — skipping **every row**. The Guide could not see the nr evidence that v9.7.239 created and v9.7.241 stopped truncating. Confirmed on the real overlay: 0 rows loaded before, 1 after. Now accepts either column.

**All three are the same shape** as `wanted_region` and `--strict-paths`: *a thing defined and never invoked.*

### v9.7.244 — A wrong-region silent answer, and the crosswalk it hops to

**`tab-reconcile --bgc` reported a different region's evidence.** `_choose_record()` computed `wanted_region` and never read it; `_gene_overview_summary()` hardcoded `areas[0]`. Reproduced on the real 74 MB AS-XXX antiSMASH JSON: `NODE_2_length_553361` carries three regions, and BGC018 is region003 — but the ledger reported region001's span, region001's products, and the whole contig's CDS count. **Any BGC that is not the first region on its contig received another cluster's evidence**, and the tab ledger is the artifact a Mode B card cites.

Fixed via `_region_index()` (antiSMASH `areas` carry no region number; **index order IS the region number**, verified against the real JSON) and a new `_feature_in_span()` that scopes the CDS count to the region. Verified on all three regions of the real record. The `region003 → 22 CDS` result is an independent cross-check: the BGC018 BLASTp panel run in v9.7.239 had exactly 22 queries.

**Why no test caught it:** the reference fixture sits on a contig with exactly one region, where `areas[0]` is always right. **A single-region fixture cannot exercise region selection.**

**`mamey/crosswalk.py` hardened** (fan-in 11): `region_label("region003")` raised ValueError even though callers read `antismash_region`, whose value *is* that string; `region_label(0)` rendered `region000` (region numbers are 1-based); `assembly_locator` used `get("region_number") or get("Region")`, and `or` treats `0` as absent, silently answering from a different field.

### v9.7.243 — Bunny Hop audit session with receipts

**`tools/file_atlas.py` (new).** Describes every file under `mamey/` and `tools/` from the real source via `ast`: LOC, docstring summary, fan-in, fan-out, CLI verbs, test references, orphan status. **280 files, 74,981 LOC, 35 orphan candidates, 57 files no test names at all.** The orphan column is the roll pool for the audit game.

**H-003 — owned retraction.** `kcb-frontpage --node` / `--bgc` matched keys that `read_frontpage` never sets. Verified against a real 14 MB `regions.js`: the anchors are `r1c1`-style and carry no contig, no `seq_id`, no Mamey BGC id. Those filters could only ever return "no hits after filter." **They passed CI because the v9.7.230 test stubbed `bgc_id` into the hit dicts — a proxy, not the artifact.** The flags now fail closed (exit 2) with a pointer to `--region` and `<strain>_2b_bgc_crosswalk.csv`, rather than lying quietly.

**`tools/_wbio.py` hardened** — 125 lines, **38 importers**, 1 test. The bunny hop landed on the highest-fan-in file in the bundle. Permission widening (`os.replace()` adopts the temp file's mode, so a `0600` deliverable became `0644` — in a bundle that ships a MERGED-PRIVATE tier); stray `.tmp` on failure in three of four helpers; and a `.bak` window in which the target did not exist at all, the exact opposite of the module's stated invariant. Tests 1 → 6.

**`tools/check_monolith_freshness.py` (new, WIRED).** The monolith's anchor read "vetted against v9.7.6 / current bundle 9.7.57" at v9.7.242 — **185 cuts of drift, no signal.** The gate does not demand a re-read; it demands that the monolith state truthfully how far behind it is. The doctrine scan came back clean: the content was current even where the label was not.

---

## Part X: The Lineage Split

Two active codebases have each shipped a `v9.7.244`, and a third `.243` exists carrying documentation and an exit-code fix. None contains the others.

| Lineage | Head | Distinguishing content |
|---|---|---|
| Bunny Hop | v9.7.246 | `file_atlas`, `_wbio` hardening, `kcb-frontpage` fail-closed, `tab-reconcile` region resolution, crosswalk hardening, monolith gate, `PHANTOM_LOCUS` |
| Guide | v9.7.244 | P8 / P9 / P10 (`chunk_proteins` default, `background_tier`, blastp-store column) |
| Docs | v9.7.243 | `P-emit-01` (exit 3 on empty `--scope leads`), `--fail-on-empty`, `docs/user_guides/` v2–v3, `math_reference_vol2.md` |

The Bunny Hop lineage reproduced and independently fixed P8 and P10 — **so the code differs from the Guide lineage even where the behaviour now agrees.** P9 (`background_tier` in `genome_explore`) is not merged: it does not exist in the Bunny Hop lineage, and guessing its name or semantics would produce a third incompatible implementation.

**Recommended resolution (a project decision, offered rather than taken):** freeze all three at their heads; consolidate at **v9.7.250**, a number no lineage has used, with room beneath it; apply Bunny Hop `.243`–`.246`, then Docs `.243`, then Guide P8/P9/P10 resolving P8/P10 against the versions already present; run the full suite on the merged tree.

**On test counts.** `2884p / 152s` (Bunny Hop) vs `2877p / 147s` (Guide) vs `2857p / 152s` (Docs) is **expected** — different trees with different tests. **Zero failures on all three is the invariant that matters.** Chasing the counts to equality would mean one of them was lying.

**On scoring parity.** Six independent `mamey run` invocations across lineages produced 46 raw / 32.25 corrected / MODERATE, six times. Engine 1.9.111 everywhere, identical numbers everywhere. That is the scoring-parity claim doing its job, and it is the strongest evidence that the split is confined to tooling and gates rather than the extraction engine.

---

*Last updated: 2026-07-09 · v3 additions (Parts VIII, IX, X) · Bundle v9.7.246*
