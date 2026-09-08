# KNOWLEDGE — Judgment Checks: the Sapote judgments converted to deterministic rules

## 0. Header block
> **Filing.** `docs/modules/KNOWLEDGE_JudgmentChecks.md`.
> **References:** `KNOWLEDGE_Evidence_Axes_and_Lead_Class_Logic.md`, `resources/bioactivity_axes.json`,
> `DELIVERABLE_AssemblyQC.md`, `MODE_B_CARD_CLAIM_SAFETY_AUDIT.md`.
> **Precedence.** `DELIVERABLE_CONTRACT.md` wins; the active monolith wins over everything.
> **Status:** `KNOWLEDGE` (a checklist; the rules themselves live in the named tools/resources).
> **One-line purpose.** Catalogue every Sapote *judgment* that has been moved into the deterministic layer, so a
> fresh runner — Claude, ChatGPT, any backend — reproduces it without having to *notice* the right thing.

## 1. Why this exists
Mamey (deterministic Python) ports to any model. Sapote (LLM judgment) may not: the same banks and prompts can
surface a lead in one run and miss it in the next. Each time a run misses something a careful analyst would catch,
that judgment is a candidate to convert into a rule/filter/guard. This module is the running list. **A rule here
is portable; a judgment is not.** When a new miss appears, add the rule, don't re-explain it to the model.

## 2. The converted checks (apply every run)
| # | The judgment | Deterministic rule | Lives in |
|---|---|---|---|
| 1 | "nikkomycin / polyoxin are antifungal" | chemistry→axis lookup by KCB anchor / class name | `resources/bioactivity_axes.json` |
| 2 | "HSAF / SGR PTM are antifungal (polycyclic tetramate macrolactams)" | same table, keyed on the **anchor strings antiSMASH emits** (`sgr ptm`, `ptm compound`, …) | `resources/bioactivity_axes.json` |
| 3 | "a nucleoside BGC here is a chitin-synthase inhibitor → antifungal" | **gated** rule: product=nucleoside/T43-NUC **AND** chitin marker (CBM_CHITIN/GlcNAc/chitinase) → antifungal; without the chitin context → "axis uncertain", never silently antibacterial | `axis(...,chitin_context=)` + `compound_rules` in the table |
| 4 | "what's the antifungal lead?" should not depend on noticing | `--bioactivity antifungal` filter = deterministic lookup | `build_lead_tiers.py` |
| 5 | "genuine enediyne needs a low-KS iterative PKSE, not a 16-KS modular line" | KS-count veto: ≥ double-digit KS ⇒ retire the enediyne descriptor (likely hglE cross-reaction) | claim-safety audit (AS chat) |
| 6 | "this oversized genome is a co-assembly, hold its leads" | assembly-QC gate: genome_bp ceiling = the discriminator; raw/contig trips alone are WARN (fragmentation looks identical) | `tools/assembly_qc_check.py` |
| 7 | "SARP means the activator is coupled to *this* BGC" | read per-BGC `tfbs_coupling.json`, not strain-level `SARP_BTAD_like` | all SARP-reading tools |
| 8 | "KCB is similarity, leads are class-level, bioactivity is extract-level" | claim-safety language locks baked into every caption | claim-safety audit |
| 9 | "a high KCB score on ≤4 proteins is a fragment trap" | flag KCB hits with protein_hits ≤ 4 as fragment-trap; no complete-pathway claim | Mode B trap card |
| 10 | "a low score shouldn't make an antifungal/antibacterial lead disappear; nucleosides are rare and worth always screening" | **never-drop**: chemistry-relevant axes are partitioned into Primary / Low-priority-adjacent, never truncated; **nucleoside priority floor** = HIGH regardless of AF_auto | `priority_policy` in `bioactivity_axes.json`; `build_lead_tiers.py` |
| 11 | "Mamey already proved this is antifungal (NikJ/T43-NUC) — the scorer just never read it" | **marker-aware scoring + TIER_1 floor**: `scoring.triage_bgcs` reads per-BGC CCTT/cassette diagnostics; an antifungal trigger adds an AF bonus, and any TIER_1 diagnostic floors the tier to ≥ Medium so KCB-dark gene-only leads aren't buried by text-only scoring | `mamey/scoring.py` (the root-cause fix for BGC008) |

## 3. The meta-lesson (learned the hard way on AS-XXX)
**Audit every keyword against the strings antiSMASH/KCB actually emit, not the textbook chemistry name.** Rules 1–2
first passed synthetic tests keyed on "nikkomycin"/"dihydromaltophilin" — and still missed the real AS-XXX leads,
whose anchors read "nucleoside" (a genome match, no compound name) and "SGR PTMs". A name table is only as good as
its match against real output. When adding a chemistry→axis keyword: pull the actual `closest_kcb_product` /
MIBiG product string from a real run and confirm the keyword is a substring of it.

## 4. How to add a new check
1. The run missed something a careful analyst catches. Name the judgment in one line.
2. Find the deterministic signal(s) that distinguish it (anchor string, domain count, scan flag, marker).
3. Encode it: a keyword in the table, a gated rule, a filter flag, or a guard in the relevant tool.
4. **Test against the real anchor/field**, not an idealized name.
5. Add a row to §2. The next runner gets it for free.

## 5. Next-paths closer
```
1. Implement the chitin-context join in the AF_auto scorer (test chat) so rule #3 fires on nucleoside BGCs automatically.
2. After each new strain run, diff "what a careful read caught" vs "what the run ranked" and mint any miss into §2.
3. Extend resources/bioactivity_axes.json with the next batch of real anchors (loonamycin/pyrroloindoline, indolocarbazole DNA-targeting).
4. Add a fragment-trap auto-flag (protein_hits<=4 + KCB>10k) as a standing column rather than per-card prose.
5. Re-run --bioactivity antifungal on merged_cohort and confirm BGC008 + BGC031 now surface (BGC008 also floored HIGH as a nucleoside, and never dropped by cutoff).
```
