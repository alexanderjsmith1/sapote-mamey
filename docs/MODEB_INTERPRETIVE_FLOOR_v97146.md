# Mode B Interpretive Floor — v9.7.146
*Minimum interpretive requirements per section. These are floors, not ceilings.*  
*Before drafting §19, verify each floor is met. Expand thin sections first.*

---

## The core problem this document addresses

Mode B cards are structurally complete but interpretively thin in a consistent pattern:
§4 gene tables are detailed, but the findings do not flow forward into §5/§9/§11/§12/§19.
Each of those sections has a minimum floor defined below.

---

## §5 — Core Biosynthetic Logic

**Floor:** Domain architecture must connect to structural consequences — not just naming.

Required for every T1PKS/NRPS/hybrid BGC:
1. What does the domain arrangement *produce* at the molecular level? (ring size class, polyene/polyol ratio, branching, chain interruptions)
2. What structural feature is *determined* by a specific domain or domain combination? (e.g. "the ER in M20 produces a fully saturated carbon at that position, creating the third polyene chain interruption")
3. One sentence distinguishing this from the nearest named comparator based on domain evidence (e.g. "the three-ER architecture predicts a tripartite chromophore distinct from nystatin's single interruption")

**Not sufficient:** "The KS domain catalyses Claisen condensation." That is domain naming, not interpretation.

---

## §9 — Alternative Hypotheses

**Floor:** Each alternative must be weighed, not just listed.

Required structure for every alternative:
1. State the alternative in one sentence
2. One piece of evidence that *supports* it
3. One piece of evidence that *argues against* it or makes it less likely
4. A closing sentence stating which hypothesis is currently most parsimonious and why

**Not sufficient:** A numbered list of alternatives with no evidence weights and no conclusion.

---

## §11 — Product-Family Interpretation

**Floor:** Tailoring complement must connect to scaffold complexity implications.

Required:
- If the BGC has *more* P450s than the reference compound: state what additional modification the extra P450(s) imply
- If an ER is at an unusual position: state the structural consequence at that position
- If a specific tailoring combination is unprecedented (e.g. dual luciferase-like oxygenases): state what that predicts about the compound's structural novelty
- If no MIBiG hit: report "no admissible MIBiG match in the searched reference set" — a search-negative, **not** a novel-compound-class claim. MIBiG is not exhaustive, so absence of a reference hit is *reference-dark* status, never evidence of novelty; defer any novelty judgement to gene-level architecture plus phylogenomic evidence, framed as a class-level hypothesis with judgement deferred

**Not sufficient:** "Biosynthetic capacity consistent with nystatin-family polyene." That is the claim ceiling, not the interpretation.

---

## §12 — Bee/Microbe Ecological Interpretation

**Floor:** Must reason through the mechanism, not just name the context.

Required:
1. Host context and its *specific* chemical ecology challenge (not just "bee" but "the brood fungal pathogen Ascosphaera apis / floral pathogen Botrytis cinerea / etc.")
2. The mechanism by which this compound *class* addresses that challenge (membrane disruption, competitive exclusion, etc.)
3. If relevant literature exists (e.g. Kim et al. 2019 for the plant–pollinator–microbe model): cite the *specific finding* and connect it to the strain's phylogenetic position
4. Tag the ecological claim: **observed** / **inferred** / **assumed** per the confidence vocabulary

**Not sufficient:** "This BGC is ecologically relevant in a bee context." That is the context label, not the interpretation.

---

## §19 — Final Mode B Judgement

**Floor:** Must be structured as an argument, not a restatement of §11.

Required structure:
1. **Evidence summary** — what the BLASTP/KCB/domain data established (1–3 sentences)
2. **Alternative rejection** — which alternative hypotheses were considered and why the leading interpretation is preferred (reference §9)
3. **Claim ceiling** — what the evidence supports (positive) and what it does not (negative), stated as a pair
4. **Confidence tags** — observed / computed / inferred / assumed per claim

**Not sufficient:** "Biosynthetic capacity consistent with X. No compound name can be assigned." That is the claim ceiling alone. §19 should earn that ceiling through the argument above it.

---

## Pre-§19 internal check (add to Sapote judgment layer)

Before drafting §19, verify:
- [ ] §5 connects domain architecture to structural consequences (not just names domains)
- [ ] §9 weighs each alternative against evidence (does not just list them)
- [ ] §11 connects tailoring complement to scaffold complexity implications
- [ ] §12 cites relevant ecological literature with specific mechanism explained
- [ ] Each has an observed/inferred/assumed tag where it matters

If any box is unchecked, expand that section before writing §19.

---

## Confidence vocabulary (applies across all sections)

| Tag | Meaning |
|---|---|
| **observed** | Directly present in a named field, file, or database hit |
| **computed** | Derived by a stated deterministic rule (corrected BGC count, identity %) |
| **inferred** | Drawn from multiple observed facts by reasoned argument |
| **assumed** | Default position in the absence of contrary evidence; should be flagged |

---

*Sapote–Mamey v9.7.146  ·  Applies to all Mode B §1–§20 cards*
