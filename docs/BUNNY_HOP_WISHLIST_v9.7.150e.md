# Bunny Hop Sweep — Wishlist for Next Round
*Source: 60-file random-sample hostile audit (`1.docx`, sessions "v150e-fast30" rounds 1+2), 2026-06-30*
*Status: triaged at end of v9.7.150e session. One finding actioned (see below); the rest filed here unverified.*

---

## What this document is

A 60-file random-sample sweep across the bundle, each file given an Inspector/Defender/Consensus pass. Tally: 13 KEEP, 17 CHANGE, 19 PENDING, plus 11 files folded into a patch card. This is a **discovery document**, not a tested patch — most CHANGE/PENDING items are "worth verifying" notes, not confirmed bugs. Before acting on any item below, verify against the live source the same way the one actioned item was verified tonight (see "How tonight's fix was actually verified").

---

## Actioned this session (v9.7.150f)

**#9 + #51 — `tools/sapote_judgment_receipt.py` and `tools/compilation_gate.py` vs `modeb_structure_gate.py`**

Verified real: `compilation_gate.py`'s G2 gate checked card *presence* (regex header count) and depth (`mode_b_quality_gate`), with zero awareness of the new §1–§30 structure gate. A card on the legacy §1–§20 scaffold could pass G2/G4 here while being refused by `modeb_structure_gate.py` at ingest — the two gates could genuinely disagree about whether a card is "complete."

**Fix applied:** `g2_modeb_coverage()` now calls `modeb_structure_gate.lint_card()` per card; a card with ERROR-severity structural findings no longer counts as carded, even if its header is present. Docstring updated from "§1–§8" to "§1–§30."

**Bug found and fixed within the same patch:** the first version of this fix used `from .modeb_structure_gate import lint_card` — a relative import. `tools/compilation_gate.py` is a standalone script, not loaded as part of the `mamey` package, so the relative import has no parent package context and fails silently (caught by a bare `except Exception`). The structure cross-check never fired. Functional testing caught this immediately — fixed by switching to `from mamey.modeb_structure_gate import lint_card` (absolute path). Two regression tests added: one pinning the legacy-card-rejection behavior, one pinning the absolute-import requirement so this specific failure mode can't silently recur.

**`tools/sapote_judgment_receipt.py`** (the other half of #9) — not yet touched. Its `count_modeb_cards()` regex has the identical blind spot. Same fix pattern applies: cross-check via `modeb_structure_gate.lint_card` before flipping `gold_completeness` to COMPLETE. Filed below as the first item for next round since it's the same fix shape already proven tonight.

---

## How tonight's fix was actually verified (do this for every item below before acting)

1. `ls <file>` / `grep -n <claimed pattern>` — confirm the file and the specific code the finding describes actually exist as described.
2. Read the relevant function in full, not just the snippet quoted in the finding.
3. Write a 5-line functional test that exercises the claimed behavior directly (no fixtures needed for most of these — plain function calls).
4. If the fix doesn't work as expected on the first functional test, that's information — don't assume the original `FINDINGS.md`-style write-up was right just because it sounds plausible. Tonight's import bug is a good example: the *concept* of the fix was right, the *first implementation* was wrong, and only the functional test caught it.

---

## High-priority items for next round (concrete, checkable, plausibly real)

### 1. `tools/sapote_judgment_receipt.py` — same structure-gate blind spot as the fix above
Apply the identical pattern: import `modeb_structure_gate.lint_card` (absolute path — same trap), cross-check each counted card, don't flip `gold_completeness` to COMPLETE if any card is structurally invalid. Effort: S (the pattern is now proven).

### 2. `mamey/mode_b/evidence_ledgers.py` — undocumented hard pandas dependency
Claimed: `_frame()` raises `RuntimeError` if pandas isn't installed, but pandas isn't in the documented core dependency list (openpyxl, reportlab, ijson). §28 (the evidence ledger this module builds) is mandatory per the new structure gate. **Verify first:** check `PREREQUISITES.md` and any install docs for whether pandas is already listed; check whether pandas is a transitive dependency of openpyxl (it may already be implicitly required and just undocumented as a direct dep). If genuinely missing: either add pandas to the documented install list, or write a non-pandas fallback for the two ledger builders. Effort: XS to verify the gap, S–M to fix.

### 3. `mamey/figures/locus_map.py`, `mamey/figures_smoke.py`, and whatever `build_figures.py` uses — three independent hardcoded colour palettes
Claimed: `locus_map.py` uses `#2E75B6`-style biosynthetic-blue, `figures_smoke.py` uses `#1f3a93`-style boundary colours, different hex values, different files, no shared source. If real, this is a genuine house-style drift risk — a future palette update would need to touch 3+ files. **Verify first:** grep all three files for their actual hex constants, confirm they really are independent (not, say, intentionally different for different figure *types* rather than accidental drift). If confirmed accidental: consolidate into one shared constants module. Effort: M (touches multiple files, needs care not to break visual output).

### 4. `tools/compilation_gate.py` G3 — `pdfinfo` external binary dependency, no fallback
Lower priority than #1–3 but cheap to check: does `g3_page_count_floor` (not shown in the excerpts I read) crash hard or degrade gracefully if `pdfinfo` isn't installed in the environment? Effort: XS to check, XS to fix if it's a hard crash.

---

## Medium-priority — doc/docstring staleness (cheap, mostly cosmetic, worth a batch cleanup pass)

- `tools/check_dangling_refs.py` — docstring claims "examples/ is empty"; 9 files now exist there. Cosmetic, but actively misleading to a reader.
- `mamey/cohort_figures_g.py` — docstring references `make_figures_complement.py`, actual filename is `cohort_figures_g.py`. Stale rename artifact.
- `mamey/timing.py` — no docstring note that Windows runs silently lack CPU/memory telemetry (resource module unavailable). Cheap addition, prevents user confusion.
- `tools/check_chatgpt_next_paths.py` — GENERIC filler-word set is missing a few obvious entries ("execute," "perform," "build"). XS fix.
- `tools/build_panel_figure.py` — returns silently (exit 0) on missing panels instead of `sys.exit(1)`; a CI/automation caller wouldn't detect the failure. XS fix.

A single cleanup pass through these five would be a clean, low-risk next-round item — none of them touch scoring logic or claim-safety, all are either docstring accuracy or an exit-code fix.

---

## Items requiring verification before any action (the bulk of the 19 PENDING)

These are speculative "worth checking" notes from the audit, not confirmed findings. Each needs the verification procedure above before it's worth scheduling:

- **#1** `tools/evidence_conservation_audit.py` — does a test file actually exist? (`grep -r evidence_conservation tests/`)
- **#5 / #13** `tools/_wbio.py` — does `atomic_open` exist in the full file? (Only 85 lines were sampled; function may be further down. Two other files import it — if it's genuinely missing, that's a real crash risk for both importers.)
- **#11** `mamey/cohort_figures_bridge.py` — when a cohort-bridge failure is "logged," does that mean a log file nobody checks, or something user-visible?
- **#16** `mamey/rggmci.py` (1192 lines) — is FASTA/zip parsing mixed with scoring math in one file, or are the 1192 lines genuinely cohesive?
- **#23** `tools/build_family_map.py` — does the referenced 11-pair adjudicated discordant-pairs validation CSV actually exist in the bundle?
- **#27** `mamey/comparators/antismash_ingest.py` — has its "v9.7.138 research" status label in `legacy_feature_gate.py` been updated now that it's wired into 3 production call sites?
- **#38/#39** `mamey/sapote_markers.py` / `sapote_cassettes.py` — does `docs/SAPOTE_v8.10.2_MONOLITH.md` (cited as `source_locator` in every marker definition) actually exist in the bundle? If not, every marker's provenance citation is dangling.
- **#43** `tools/build_genelevel_triage.py` vs `mamey/rggmci.py` — do these two split-detection systems ever produce conflicting verdicts (SPLIT_CANDIDATE vs HIGH-confidence pairing) on the same BGC pair? Needs a real test case, not just a code read.
- **#45** `tools/lead_board.py` — is its `HIGH` product-class set kept in sync with `source_scans.py`'s CCTT trigger names, or could they silently diverge?
- **#52** `mamey/cross_strain_card_context.py` — is the AS-XXX redaction this module depends on actually enforced by a test anywhere, or just described in a docstring?
- **#53** `tools/intake_harness.py` — `resource.ru_maxrss` units differ between Linux (KB) and macOS (bytes). Is there cross-platform normalization, or could this corrupt the calibration-data telemetry the docstring says this tool feeds?
- **#59** `FIGURE_CONVENTIONS.md` vs `docs/FIGURE_STYLE.md` — same document under two names, or genuinely different files? Affects whether a prior session's doc citation needs a fix.
- **#60** `mamey/nominal_length.py` — still labeled "DRAFT v9.7.104" 46 point-releases later. Either fine (low-priority feature) or stuck — worth a one-line status check.

---

## Items the audit itself walked back (do not action — for context only)

The audit's author noted these as findings that turned out to be non-issues on closer reading, consistent with the same self-correction pattern Opus showed earlier this session with the figures diagnostic (Gaps 2/4/5 in `FIGURES_DIAGNOSTIC_v9.7.150.md`). No equivalent walk-back is recorded for this 60-file sweep yet — that's expected, since this document hasn't been cross-checked against source the way the figures diagnostic was. Treat every PENDING item above as genuinely unverified, not as "probably fine."

---

## Net assessment

One real, fixable cross-gate inconsistency was found and closed tonight (#9/#51, `compilation_gate.py` half). Its sibling (`sapote_judgment_receipt.py`) is the highest-value, lowest-effort next step since the fix pattern is now proven. The colour-palette consolidation (#3) and the pandas dependency gap (#2) are the next tier — both plausible, both cheap to verify, neither yet confirmed. Everything else in this document is unverified speculation from a single read-through and should not be treated as a backlog of confirmed bugs — it's a list of places worth a closer look.
