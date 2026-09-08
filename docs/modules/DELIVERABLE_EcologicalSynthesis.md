# DELIVERABLE — Ecological Synthesis (ECO)

> **Filing.** `docs/modules/DELIVERABLE_EcologicalSynthesis.md`.
> **Extends / references:** `SAPOTE_SLIM_JUDGMENT_KERNEL.md` MODULE 14 (§ECO — the compressed synthesis this module expands), `DELIVERABLE_ReviewerAttack.md` (an ecological-overreach RAS block follows the integrated model), `DELIVERABLE_CONTRACT.md` (claim-safety). **Do not restate claim-safety — point to it.**
> **Precedence.** Parent monolith wins. This module restores the §17 **eleven-step structure** that kernel M14 compressed to a single synthesis; M14's one-paragraph form is the abstract, this is the method.
> **Status:** `PROMPT_BACKED`. Every output is a labelled hypothesis; nothing here is computed.
> **One-line purpose.** Translate BGC-level evidence into testable ecological hypotheses about how predicted chemistry maps onto host biology — each hypothesis citing specific BGC evidence, each labelled by confidence, with null results reported as findings.

---

## 1. When it is offered (Deliverable Offer Protocol)

Auto-trigger at the end of a Full-Run Profile when host metadata is present; standalone trigger `Run ecological synthesis for [Strain]. [Host]. [Habitat].`; fast-mode `Run fast ecological synthesis…`. **Incomplete delivery** = an ecological narrative with no per-hypothesis BGC citation, or omitting a null result (a *null is informative and must be stated*, §17.4).

---

## 2. Inputs required (run after Mode B is complete)

| Input | Feeds |
|---|---|
| `manifest.json → source` (host/substrate) | **provenance only** — caveated context, NOT the synthesis frame; isolation source ≠ ecological function (often unreliable, haphazard collection). Never escalate into a functional claim. |
| TFBS hits ≥18 across BGCs | Step 1 regulatory coupling |
| GH/LPMO/CotH/t2fas domains within cluster boundaries | Step 2 polysaccharide gating |
| bldA tier (kernel M8) | Step 3 developmental mapping |
| strain bioactivity (extract level) + class calls | Step 4 disease-defence matching |
| HGT flags, RiQ, KCB top | Steps 5–6 novel signals + integrated model |

**Skip-not-fake / §17.2A evidence ceilings:**

| Evidence basis | Allowed claim strength |
|---|---|
| Direct assay | strain-level activity; no compound causation without fractionation |
| Bioinformatic BGC | "contains domains consistent with" / "predicted to encode" |
| Regulatory prediction | "predicts" / "consistent with regulated activation under…" |
| Ecological analogy | "could represent" / "is hypothesised to" |
| Literature verified | cited, cautious; no untested strain-specific causality |

If evidence is absent, **report a null result rather than inventing an ecological story.**

---

## 3. Pipeline — the eleven steps (restored from §17.3–17.11)

1. **TFBS regulatory coupling table** — regulators in ≥2 BGCs = coupled network; ≥6 = genome-wide network. Interpret each in *host* context (the common error is dismissing a habitat-specific signal as generic stress — e.g. IolR in a polyol-rich niche is a catabolism signal, not stress).
2. **Polysaccharide substrate coupling** — BGCs with GH/LPMO + cognate TFBS = polysaccharide-gated candidates. **A null network is reported explicitly.**
3. **bldA tier → host developmental mapping** — map T1–T4 to the host's seasonal/developmental phases.
4. **Host disease-defence matching** — match strain class capacity to the host's known pathogens (claim-safe: capacity, not protection).
5. **Novel regulatory signals** — regulators/contexts not in the project's standing set.
6. **Integrated model** — one coherent, falsifiable narrative tying Steps 1–5 to the host.
7. **BGC-by-BGC ecological matrix** — one row per BGC: evidence → ecological role hypothesis → confidence.
8. **Scoring rubric** — rank hypotheses by evidence-stream count.
9. **Hypothesis format** — each as `[claim] — based on [BGC/locus/domain/bitscore/TFBS] — confidence [H/M/L] — test: [experiment]`.
10. **Claim-safety pass** — apply §17.2A ceilings to every sentence.
11. **Reviewer-attack (ecological)** — append an ecological-overreach RAS block (`DELIVERABLE_ReviewerAttack.md` category 4).

Host-context lookups (TFBS→ecology, bldA→phase, host→pathogen→class) are **project-specific worked examples**; populate the columns with your own isolate-source categories rather than copying the reference project's Hymenoptera/Attine/Bryophyte cells.

---

## 4. Outputs & contract surface

`[Strain]_Ecological_Synthesis_YYYY-MM-DD.pdf` + the BGC-by-BGC ecological matrix + an ecology memory line in the Project Memory Snapshot. **Standing constraints enforced:** NAPAA excluded from comparative/ecological claims; hglE-KS habitat-non-specific; retired hypotheses (BRYO-HGT-001, Nosema/NAPAA) not revived.

---

## 5. Acceptance checklist

- [ ] Every hypothesis cites specific BGC evidence (node/locus/domain/bitscore/TFBS).
- [ ] Every hypothesis carries a confidence label and a named test.
- [ ] Null results stated explicitly (polysaccharide gating, absent networks).
- [ ] §17.2A claim ceilings applied to every sentence.
- [ ] Standing constraints enforced; no retired hypotheses revived.
- [ ] Ecological RAS block appended.
- [ ] Host-context tables are the user's own categories, not reference-project cells.
- [ ] Contig-ID locators; affiliation = ; exactly 8 unique next-paths.

---

## 6. Knowledge inventory

| Piece | Owner |
|---|---|
| Eleven-step method | this module (expansion of kernel M14) |
| Evidence ceilings (§17.2A) | this module + `DELIVERABLE_CONTRACT.md` |
| TFBS extraction | Mamey scans / kernel M8 context |
| Standing constraints | parent monolith |

---

## 7. Worked next-paths closer (SID-XXX — insect microbiome)

> Ecological synthesis (claim-safe): iron-economy hypothesis (catecholate siderophore BGC019 diOH-Bz + NI-siderophore BGC062) — competitive Fe piracy, confidence M, test: CAS assay under iron limitation. Chemical-warfare hypothesis (enediyne BGC047 + thioamitide BGC012) — antagonism in a crowded community, confidence M, bioinformatic only. NAPAA excluded; no hglE-KS habitat claim. Next paths:
> 1. Build the BGC-by-BGC ecological matrix for all interior leads.
> 2. Append the ecological-overreach RAS block.
> 3. Populate the host-context TFBS table with insect-microbiome categories.
> 4. Test the iron-economy hypothesis design against the metabolomics CAS-assay plan.
> 5. Bank a second insect-microbiome strain to test recurrence of the iron + warhead pairing.
