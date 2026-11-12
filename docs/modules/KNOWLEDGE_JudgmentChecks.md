> Some rows below are code (named file); others are review habits. Tags are review signals, not measured activity.
> See [module dispositions](README.md).

# KNOWLEDGE — Judgment Checks: the Sapote judgments converted to deterministic rules

## 0. Header block
> **Filing.** `docs/modules/KNOWLEDGE_JudgmentChecks.md`.
> **References:** `KNOWLEDGE_Evidence_Axes_and_Lead_Class_Logic.md`, `resources/bioactivity_axes.json`,
> `DELIVERABLE_AssemblyQC.md`, `MODE_B_CARD_CLAIM_SAFETY_AUDIT.md`.
> **Precedence.** The current user task and [assistant governance](../ASSISTANT_GOVERNANCE.md) govern actions. Use the selected current contract and actual source for implemented behavior; the monolith remains a design/history reference.
> **Status:** `KNOWLEDGE` (a checklist; the rules themselves live in the named tools/resources).
> **One-line purpose.** Catalog every Sapote *judgment* that has been moved into the deterministic layer, so any
> reviewer reproduces it without having to *notice* the right thing.

## 1. Why this exists
Mamey (deterministic Python) ports to any model. Sapote (LLM judgment) may not: the same banks and prompts can
surface a lead in one run and miss it in the next. Each time a run misses something a careful analyst would catch,
that judgment is a candidate to convert into a rule/filter/guard. This module is the running list. **A rule here
is portable; a judgment is not.** When a new miss appears, add the rule, do not rely on the reviewer noticing it.

## 2. The converted checks
A file-named rule applies only when its relevant code path runs with the required inputs and settings; a resource alone does not execute a rule. Review habits are not automatic. Verify the executing path and conditions for the selected run.

| # | The judgment | Deterministic rule | Lives in |
|---|---|---|---|
| 1 | "nikkomycin / polyoxin are antifungal" | chemistry→axis lookup by KCB anchor / class name | `resources/bioactivity_axes.json` |
| 2 | "HSAF / SGR PTM are antifungal (polycyclic tetramate macrolactams)" | same table, keyed on the **anchor strings antiSMASH emits** (`sgr ptm`, `ptm compound`, …) | `resources/bioactivity_axes.json` |
| 3 | "a nucleoside BGC here is a chitin-synthase inhibitor → antifungal" | The generic nucleoside/T43-NUC fallback is chitin-context gated only after priority keyword matching. An earlier keyword in class, note or anchor can assign another label. Review those contributing fields; labels are not measured activity. `mamey/scoring.py` does not apply this gate to its AF diagnostic bonus | `axis(...,chitin_context=)` in `tools/build_lead_tiers.py` + `compound_rules` in the table |
| 4 | "what's the antifungal lead?" should not depend on noticing | `--bioactivity antifungal` filter = deterministic lookup | `build_lead_tiers.py` |
| 5 | "genuine enediyne needs a low-KS iterative PKSE, not a 16-KS modular line" | KS-count veto: ≥ double-digit KS ⇒ retire the enediyne descriptor (likely hglE cross-reaction) | review habit (no code) |
| 6 | "this oversized genome is a co-assembly, hold its leads" | In default size-anchored mode, raw/contig triggers without an oversized genome are WARN; `--literal-or` uses different FLAG logic. Record mode, thresholds and available inputs, and review purity/contamination separately. A FLAG does not prove co-assembly | `tools/assembly_qc_check.py` |
| 7 | "SARP means the activator is coupled to *this* BGC" | read per-BGC `tfbs_coupling.json`, not strain-level `SARP_BTAD_like` | the tools that read `tfbs_coupling.json`: `tools/lead_board.py`, `tools/build_lead_tiers.py`, `tools/build_subset_panel.py`, `tools/build_modeb_deepdive.py`, `tools/build_thesis_vignettes.py` |
| 8 | "KCB is similarity, leads are class-level, bioactivity is extract-level" | Review selected outputs against their source-bound claim ceiling; a checklist does not establish universal caption coverage | review habit (no code) |
| 9 | "a high KCB score on ≤4 proteins is a fragment trap" | A high KCB score supported by few proteins is a review signal. Inspect the selected producer's documented threshold, alignment coverage, region boundaries and full source identity before a pathway claim | Mode B trap card |
| 10 | "a low score shouldn't make an antifungal/antibacterial lead disappear; nucleosides are rare and worth always screening" | **nucleoside priority floor**: `build_lead_tiers.py` sorts rows flagged `priority_floor=high` to the top regardless of AF_auto. The writer does not emit a Primary / Low-priority-adjacent partition: `--bioactivity` removes rows whose label does not contain the requested text, so read the unfiltered view to see what a filtered view left out. The `priority_policy` block in `bioactivity_axes.json` states the intent; the writer does not read it | `build_lead_tiers.py` |
| 11 | "Diagnostic-bearing capacity evidence should remain visible to scoring" | **marker-aware scoring + TIER_1 floor**: `scoring.triage_bgcs` reads per-BGC CCTT/cassette diagnostics; an antifungal trigger adds an AF bonus, and eligible corroborated class diagnostics can floor the tier to Medium (tailoring-only/cargo exclusions and later standing-rule/RiPP downgrades still apply) so KCB-dark gene-only leads aren't buried by text-only scoring | `mamey/scoring.py` (inspect this selected diagnostic-marker path and its guards; no individual locus is bound here) |

## 3. The meta-lesson
**Audit every keyword against the strings antiSMASH/KCB actually emit, not the textbook chemistry name.** Rules 1–2
first passed synthetic tests keyed on "nikkomycin"/"dihydromaltophilin" — and still missed real leads
whose anchors read "nucleoside" (a genome match, no compound name) and "SGR PTMs". A name table is only as good as
its match against real output. When adding a chemistry→axis keyword: pull the actual `closest_kcb_product` /
MIBiG product string from a real run and confirm the keyword is a substring of it.

## 4. How to add a new check
1. The run missed something a careful analyst catches. Name the judgment in one line.
2. Find the deterministic signal(s) that distinguish it (anchor string, domain count, scan flag, marker).
3. Encode it: a keyword in the table, a gated rule, a filter flag, or a guard in the relevant tool.
4. **Test against the real anchor/field**, not an idealized name.
5. Add a row to §2. Document the executing path and conditions, and verify them for the selected run.
