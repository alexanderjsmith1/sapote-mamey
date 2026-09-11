# DELIVERABLE — Reviewer Attack Simulation (RAS)

> **Filing.** `docs/modules/DELIVERABLE_ReviewerAttack.md`.
> **Extends / references:** `DELIVERABLE_CONTRACT.md` (Offer Protocol, Contig-ID Mandate, Next-Paths, claim-safety), `SAPOTE_SLIM_JUDGMENT_KERNEL.md` MODULE 13 (Mode B), MODULE 14 (ecology synthesis), MODULE 5 (§34 Hallucination-Trap — the bioinformatics-only defence draws on it). **Do not restate claim-safety language — point to the contract.**
> **Precedence.** Parent monolith (`SAPOTE_MAMEY_BUNDLE_MONOLITH.md`) wins over this module. This module is the authority for the *reviewer-attack format and required categories*; the *claims* it stress-tests are owned by the Mode B / synopsis that produced them.
> **Status:** `PROMPT_BACKED` (Sapote-only; no deterministic artifact). There is nothing to compute — the value is structured adversarial judgment against claims the package already supports.
> **One-line purpose.** Before a claim leaves the building, surface the criticisms a peer reviewer would raise and the manuscript-safe revision for each — so every report ships pre-hardened against fragmentation, overclaiming, and causality objections.

---

## 1. When it is offered (Deliverable Offer Protocol)

Per `DELIVERABLE_CONTRACT.md`, auto-build it; the user must not need to ask.

- **Auto-place** it:
  - in the **Deep Dive Synopsis**, immediately after the Executive Summary;
  - in the **Ecological Synthesis**, immediately after the integrated model;
  - in **any manuscript-bound output** where a strain finding is asserted.
- **Offer as a next-path** whenever a strong, contestable claim has been made (novel class call, mechanism→activity link, ecological hypothesis) but no RAS block accompanies it.
- **Incomplete delivery** = a report that makes a class-level, mechanistic, or ecological claim with no RAS block, or a RAS block that omits any of the five required categories (§4) that apply to the report.

---

## 2. Inputs required

| Source | Feeds | Required for |
|---|---|---|
| The report's strongest claim(s) (from Mode B §4 / Synopsis exec summary) | the "Claim or interpretation" line | Every RAS block |
| `manifest.json → bgc_counts.assembly_tier`, `assembly.quality` | the fragmentation criticism + its defence | Category 1 |
| `_4_triage_board.csv → KCB_score, Novelty_auto`, MIBiG hits | the dereplication / known-compound criticism | Category 2 |
| Mode B §6 mechanism→bioactivity link (if made) | the causality criticism | Category 3 |
| Ecology synthesis hypothesis (if made) | the ecological-overreach criticism | Category 4 |
| Standing constraints (NAPAA exclusion, hglE-KS habitat-non-specific, [E-signal] enediyne notes) | pre-empt known reviewer objections the project has already settled | All |

**Skip-not-fake.** A category whose claim was never made is marked **"not applicable — no [ecological / causal] claim made,"** never answered with an invented criticism. RAS hardens real claims; it does not manufacture them.

---

## 3. Template (port of v7.5.2 §36.3 — use verbatim structure)

```text
Reviewer Attack Simulation — [Strain ID] [BGC_ID (contig · regionXXX) if BGC-specific]

Claim or interpretation:
[State the report's strongest claim, in its actual claim-safe wording]

Likely reviewer criticism:
1. [Assembly / fragmentation criticism]
2. [Bioinformatics-only criticism]
3. [Dereplication / known-compound criticism]
4. [Ecological overreach criticism]   (omit/Not-applicable if no ecological claim)
5. [Need-for-chemical-validation criticism]

Defense / safe revision:
1. [How the report already limits the claim — cite the Mamey field/number]
2. [Evidence supporting the class-level interpretation — domain bitscore, KCB, RiQ]
3. [The specific experiment that resolves it — long-read / HRMS / bioassay]
4. [Manuscript-safe wording that survives the objection]
5. [What chemical evidence would upgrade the claim from "consistent with"]

Recommended manuscript wording:
"[One sentence suitable for Results or Discussion, claim-safe per the contract]"
```

---

## 4. Required reviewer-attack categories

Every report includes at least one criticism + response for each category **that applies**:

1. **Assembly fragmentation** — "your N BGCs / boundaries are an assembly artefact." (Always applies when tier is POOR/VERY POOR.)
2. **Compound-identity overclaiming** — "a domain hit is not a compound."
3. **Bioactivity-to-BGC causality** — "extract activity does not implicate this cluster." (Applies whenever a mechanism link is drawn.)
4. **Ecological causality** — "genomic capacity is not in-host function." (Applies only if an ecological claim is made.)
5. **Need for chemical validation** — "no HRMS / NMR, therefore unproven."

The defence to (1) is the corrected count + edge-status discipline; to (2) the diagnostic-domain bitscore + Architecture grade; to (3) the extract-level bioactivity ceiling (never attribute without fractionation); to (4) the claim-safe ecological wording (kernel MODULE 14); to (5) the named experiment.

---

## 5. Acceptance checklist ("done" = all)

- [ ] Claim line states the report's *actual* strongest claim, in its real claim-safe wording.
- [ ] Every applicable category (§4) has a criticism **and** a defence; inapplicable ones are explicitly marked, not skipped silently.
- [ ] Each defence cites a Mamey field / number (bitscore, KCB, corrected count) — not assertion.
- [ ] Standing constraints pre-empted where relevant (NAPAA, hglE-KS habitat, [E-signal] enediyne note).
- [ ] Exactly one recommended manuscript sentence, claim-safe per `DELIVERABLE_CONTRACT.md`.
- [ ] Contig-ID locator on any BGC referenced.
- [ ] Placed correctly (after exec summary / after integrated model).
- [ ] No retired codenames; affiliation = .
- [ ] Closes with exactly 8 unique plain-text numbered next-paths.

---

## 6. Knowledge inventory

| Piece | Owner |
|---|---|
| Claim-safety wording rules | `DELIVERABLE_CONTRACT.md` (do not restate) |
| Fragmentation / corrected-count discipline | kernel MODULE 1–2 (§4) |
| Bioinformatics-only defence evidence | kernel MODULE 5 (§34 Hallucination-Trap) |
| Ecological claim-safety | kernel MODULE 14 (§ECO) |
| Standing constraints to pre-empt | parent monolith |

---

## 7. Worked example + next-paths closer (SID-XXX, BGC047 enediyne)

```text
Reviewer Attack Simulation — SID-XXX  BGC047 (WWFW01000137.1 · region001)

Claim or interpretation:
"BGC047 shows biosynthetic capacity consistent with an enediyne chromoprotein."

Likely reviewer criticism:
1. The cluster is Edge (Arch C) on a POOR assembly — boundaries unreliable.
2. This is an antiSMASH 'RiPP-like/T1PKS' region; the enediyne call is over-read.
3. No isolated compound; class is asserted from homology alone.
4. (Not applicable — no in-host ecological function is claimed.)
5. No HRMS/NMR evidence of an enediyne warhead.

Defense / safe revision:
1. Claim is class-level, not structural; boundaries flagged, long-read named Priority 1.
2. ene_KS bitscore = 830.8 (genome-max single-domain hit) + TIGR03604 + YcaO + an
   NCBI-annotated 'enediyne biosynthesis protein' (GTY63_26925) — three independent supports.
3. Gene-level homology is definitive for class even where cluster-level MIBiG score is low.
4. n/a.
5. SEC/UV-DAD + cytotoxicity readout on the fraction would confirm the warhead.

Recommended manuscript wording:
"WWFW01000137.1 encodes an ene_KS-containing locus consistent with an enediyne
biosynthetic gene cluster (cytotoxicity-guided handling per standard lab SOPs indicated prior to scale-up)."
```

> Next paths:
> 1. Generate RAS blocks for the other Immediate/Strong leads (BGC063, 025, 074, 019).
> 2. Feed the recommended sentences into the manuscript Results draft.
> 3. Pair each RAS with its §34 Hallucination-Trap row to show the audit trail.
> 4. Add RAS to the Ecological Synthesis once the integrated model is written.
> 5. Bank a control strain to test the fragmentation defence against a Good assembly.
