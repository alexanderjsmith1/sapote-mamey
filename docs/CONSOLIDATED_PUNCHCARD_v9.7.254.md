# CONSOLIDATED PATCH PUNCH CARD — v9.7.254

**Card ID:** PUNCHCARD_CONSOLIDATED_20260710_v97254
**Applies to:** Mamey (engine/CODE tier) — release audit, multi-chat reconciliation
**Bundle version:** v9.7.254 · build `20260710v97254a` · engine 1.9.111 · tier CODE
**Status:** OPEN — 4 actionable patches reconciled; 1 open bug; full regression FAILS (3, fix in hand)
**Authority:** consolidation of feedback from multiple audit chats. Every apply-status and bug
status below is **re-verified against the extracted .254 tree**, not taken from any card's word.

---

## What this consolidates

Feedback arrived as **7 punch cards + 5 patches + 2 bug reports** from several audit chats.
This card is the single reconciled view: duplicates collapsed, each actionable patch
test-applied against the real tree, each bug re-checked, ID collisions flagged.

| Source | Contributed |
|---|---|
| my prior audit (this chat) | full regression, PC-set verification, N1/#1 |
| pandas chat (`PATCH_PUNCH_CARD_v9_7_254.md`) | S1–S7 findings, S4+S6+N1 patches, `.254+fixes → 3002/0` receipt |
| Archive PC-card (`PUNCHCARD_v9.7.254.md`) | PC-11…PC-15 new findings |
| Archive AS-cards (`PATCH_PUNCHCARD*.md`, Guanabana) | strain-level findings (AS-XXX phantom, AS-XXX, AS-XXX/956) |
| Archive bug reports | phantom-locus gap, blastp-ebi `--hits` |
| Archive `.patch` (cohort_figures v222) | stale — see below |

---

## 🔴 Consolidated action list (do these, in order)

1. **N1 — RELEASE-BLOCKING.** `RELEASE_MANIFEST.md` body still stamps `.252` under a `.254`
   header → 3 tests fail. **Triple-corroborated** (my #1, pandas N1, Archive N1 diff). Fix:
   `python3 tools/gen_release_manifest.py --apply` (preferred — derives from source-of-truth)
   *or* the static `N1_release_manifest_regen.diff`. Verified: → `3 passed`; full suite → 0 fail.
2. **S4 — RELEASE-RELEVANT.** `remediate_phantom_locus.py --apply` deletes from **protected
   non-card files** (e.g. `ONLINE_BLASTP_PROTOCOL.md`). Patch `S4_remediate_card_filter.diff`
   (+ companion test) restricts it to card files. Applies clean (-p0). PENDING.
3. **readiness_lint FP — APPLY THE CORRECTED PATCH, NOT THE ORIGINAL.** The supplied
   `readiness_lint_FP_fixes.patch` applies clean but is **functionally dead** (see finding F1).
   Use `readiness_lint_FP_fixes_CORRECTED.patch` (in this bundle) instead.
4. **S6 — doc.** `pandas` half-documented in `docs/PREREQUISITES.md`. `S6_prereq_pandas.diff` applies
   clean (-p0). PENDING.
5. **Phantom-locus gap — OPEN, high.** The `PHANTOM_LOCUS` gate is silent on cross-assembly
   contamination (see bug B1). Needs a BGC-membership check, not just existence. Not yet patched.
6. **Do NOT apply `cohort_figures_priv_removal_v222.patch`** — stale/superseded (see below).

---

## Incoming patches — apply receipts (test-applied against clean .254)

| Patch | Target | Apply | Status | Receipt |
|---|---|:---:|---|---|
| **N1** `N1_release_manifest_regen.diff` | `RELEASE_MANIFEST.md` | clean `-p1` | **PENDING — release-blocking** | = my finding #1; prefer tooling `--apply` (static diff can go stale) |
| **S4** `S4_remediate_card_filter.diff` | `tools/remediate_phantom_locus.py` | clean `-p0` | **PENDING** | + `test_remediate_only_touches_cards.py`; stops deletion from protected docs |
| **S6** `S6_prereq_pandas.diff` | `docs/PREREQUISITES.md` | clean `-p0` | **PENDING (doc)** | pandas still `*(optional)*` at L61; no wheels/find-links entry |
| **readiness_lint FP** (original) | `mamey/modeb_structure_gate.py` | clean `-p1` | 🔴 **BROKEN — do not use** | see F1; corrected version supplied |
| **readiness_lint FP** (CORRECTED) | same | clean `-p1` | **PENDING — apply this one** | regex fixed; verified matches `BGC0000227` |
| **cohort_figures priv** `v222` | `mamey/cohort_figures.py` | **FAILS 14/14** | ⚠ **STALE / SUPERSEDED** | .254 already past it — `cohort_figures.py:47` comments ".222 divider removal"; `is_private()` :49 only flags `AJS-`/`PENDING-`; AS is already public |

### F1 — the readiness_lint patch is functionally dead as supplied (my catch)
`cat -A` on the patch shows literal **double** backslashes: `r"BGC0\\d{5,}"` and
`r"(?<=[.!?])\\s+"`. As raw strings those are `\\d`/`\\s` (backslash-then-letter), so:
- `_MIBIG_REF` never matches a real accession — **proven**: after applying,
  `_MIBIG_REF.search("…BGC0000227")` → **False**. The MIBiG comparator guard never fires.
- the sentence split degrades — the whole card collapses to one "sentence".

Net: the patch applies with zero rejects and **does nothing it claims to do**. The corrected
patch (`\d`, `\s`) is verified: match → **True**, split → correct. This is the classic
"applies clean ≠ works" trap — exactly what receipt-level audit is for.

---

## Open bugs (re-verified against .254)

| Bug | Status @ .254 | Receipt |
|---|---|---|
| **B1 — `PHANTOM_LOCUS` silent on cross-assembly contamination** | 🔴 **OPEN** | `_phantom_locus_findings` at `modeb_structure_gate.py:996` checks existence in the whole-strain CDS table; `ctgN_M` is a contig-index name that recurs across assemblies, so a leaked locus that *happens to exist* passes. No `LOCUS_BGC_MISMATCH` / `PANEL_ABSENT_CLAIM` in the tree. AS-XXX's 14 cards passed the gate carrying the fabricated §4 sentence. Needs BGC-membership check. |
| **B2 — `blastp-ebi --hits` unregistered (v218)** | ✅ **RESOLVED in .254** | now registered at `cli.py:3597` (`--hits`, default 6). The v218 report is stale; no action. |

B1 is the live residue of the phantom-locus failure class. It is the single most important
**un-patched** finding across all the feedback.

---

## The cut's own PC-set — verified, with cross-chat corroboration

All confirmed against the tree in my prior audit (receipts in `PATCH_PUNCHCARD_v9.7.254.md`);
"seen-by" counts how many incoming cards also carry the row.

| Patch | Verdict | Seen by |
|---|---|:---:|
| PC-5 `CORE_SYNTHASE_TERMS` (`guards.py:21`) | VERIFIED, non-behavioral | 3 cards |
| PC-6 `_relpath` warn (`release_qa.py:14`) | VERIFIED, non-behavioral | 3 cards |
| PC-7 deprecation banner (`build_master.py:23`) | VERIFIED, non-behavioral | 3 cards |
| PC-9 `view_fidelity` (`domain_level.py:484`) | VERIFIED, additive | 3 cards |
| PC-2 / PC-10 doc notes | VERIFIED code-free (closed) | 2 cards |
| Drift tests PC-1/3/4/8 + RV-1/2 | **20 tests, all pass** | 2 cards |
| Full regression | **2991 pass / 3 fail / 157 skip** → 0 fail after N1 | pandas: 3002/0 after N1+S4+S6 |

"No engine/scoring/logic change" claim: **UPHELD** by all corroborating cards.

---

## New findings catalog (deduped from S-series + PC-11..15)

From the pandas card (landing status is theirs, spot-checked):

| ID | Finding | Landing @ .254 | Note |
|---|---|---|---|
| S1 | scrubbed tier stale checksum manifest | LANDED (gate wired into `make_public_tier.sh`) | superseded a proposed pytest check — correct call |
| S2 | scrub collapsed strain-table PK (181→1) | PARTLY — reported, left as release-policy decision | your call |
| S3 | `TAG`/`CITATION.cff date-released` unowned by sync | LANDED (`sync_version.py:133`) | |
| **S4** | `remediate --apply` deletes from non-cards | **NOT LANDED** | → action #2 (patch in bundle) |
| S5 | exemplar gate blind to same-contig phantom | OPEN (low) | overlaps B1 |
| **S6** | pandas half-documented | **NOT LANDED** | → action #4 (patch in bundle) |
| S7 | `check_license_docs.py` skips glob entries | OPEN (minor) | |

From the Archive PC-card (PC-11..15 — that chat overloaded the PC namespace; see collisions):

| ID | Finding | Note |
|---|---|---|
| PC-11 | `gen_tools_inventory.py --help` rewrites two checked-in files (side-effect) | fix in hand; real bug, verify |
| PC-12 | split monolithic D-series `build()` | proposal (follow-on to PC-2) |
| PC-13 | wire governance gates into `release.sh` | proposal; same theme as S1-gate / my "wire the gate" path |
| PC-14 | confirm `view_fidelity` populated on a real run | verification task (I can run it) |
| PC-15 | re-run figure suite per tier on dense strain | verification (AS-XXX → 21 figs) |

---

## ⚠ ID collisions flagged

1. **`AS-1/2/3` as finding IDs** (`PATCH_PUNCHCARD.md`) collide with the **AS-strain-ID**
   namespace (AS-XXX, AS-XXX, AS-XXX are strains). A reader can't tell "audit finding AS-2"
   from "strain AS-2". Recommend the AS-cards renumber their findings to a non-AS prefix.
2. **Two schemes for NEW findings.** The pandas chat uses **S1–S7**; the Archive PC-card uses
   **PC-11–PC-15**. PC-1…PC-10 are the *cut's own* patch IDs — extending PC with audit findings
   overloads it. Recommend one scheme (S-series is cleaner; keep PC for cut patches only).
3. **N1 vs the tooling remedy.** N1 ships a static `RELEASE_MANIFEST.md` diff; my #1 uses
   `gen_release_manifest.py --apply`. Same end state, but the static diff goes stale on the next
   bump. Prefer the tooling form and treat N1's diff as the fallback.

---

## Cross-chat agreement

- **Unanimous / strong:** the release-manifest stamp bug (N1 / my #1 / pandas N1) — three
  independent chats, same finding, same fix. High confidence; ship it.
- **Complementary, no conflict:** pandas S-series (release/scrub/doc hygiene) and the PC-card
  PC-11+ (tooling side-effects, figure verification) cover different surfaces; no contradictions.
- **One correction I made to incoming work:** the readiness_lint regex (F1) — the only patch
  that was wrong, now fixed.
- **One stale item to discard:** cohort_figures priv v222 (already superseded).

---

## Open / not done (stated plainly)

1. **Nothing applied to the delivered tree.** All patches are verified-ready, not shipped —
   consolidation doesn't mutate the cut. The patch chat applies the bundle set.
2. **B1 (phantom-locus gap) has no patch yet** — it's the top un-patched finding; needs a
   BGC-membership gate designed and written.
3. **S-series landing statuses are the pandas chat's**, spot-checked not fully re-audited (S3
   `sync_version.py:133` and S1 gate wiring confirmed present; S2/S5/S7 taken as reported).
4. **PC-11/14/15 not independently run here** — verification tasks, doable on request.

---

*Consolidated Patch Punch Card · Sapote–Mamey v9.7.254 · engine 1.9.111 · 2026-07-10*
