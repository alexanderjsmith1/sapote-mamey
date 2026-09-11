# Mode B Interpretive Floor
**Minimum requirements per section — floors, not ceilings**

**v9.7.149a** | Source: `docs/MODEB_INTERPRETIVE_FLOOR_v97146.md` | Last updated: 2026-06-29

---

## What this document is

Mode B cards are often structurally complete but interpretively thin. The same pattern recurs: §4 gene tables are detailed, but the findings don't flow forward into §5, §9, §11, §12, or §19. Each of those sections has a minimum floor defined here. Meeting the floor is not the goal — it is the baseline below which a card is incomplete.

**Authority:** `docs/MODEB_INTERPRETIVE_FLOOR_v97146.md` is the canonical source. This document is a readable companion to that spec, not a replacement. If they conflict, the spec wins.

---

## The pre-§19 checklist

Run this before drafting §19 (Final Mode B Judgement). If any box is unchecked, expand that section first.

- [ ] §5 connects domain architecture to **structural consequences** (not just names domains)
- [ ] §9 **weighs** each alternative against evidence (does not just list them)
- [ ] §11 connects tailoring complement to **scaffold complexity implications**
- [ ] §12 cites relevant ecological literature with **specific mechanism explained**
- [ ] Each claim has an **observed / inferred / assumed** tag where it matters

---

## §5 — Core Biosynthetic Logic

**The floor:** Domain architecture must connect to structural consequences — not just naming.

Required for every T1PKS / NRPS / hybrid BGC:

1. What does the domain arrangement *produce* at the molecular level? (ring size class, polyene/polyol ratio, branching, chain interruptions)
2. What structural feature is *determined* by a specific domain or domain combination?
3. One sentence distinguishing this from the nearest named comparator based on domain evidence

**Example of what passes the floor:**
> "The ER in M20 produces a fully saturated carbon at that position, creating the third polyene chain interruption — consistent with a tripartite chromophore distinct from nystatin's single interruption."

**Example of what fails the floor:**
> "The KS domain catalyses Claisen condensation."

That is domain naming. It is not interpretation.

---

## §9 — Alternative Hypotheses

**The floor:** Each alternative must be weighed, not just listed.

Required structure for every alternative:

1. State the alternative in one sentence
2. One piece of evidence that *supports* it
3. One piece of evidence that *argues against* it or makes it less likely
4. A closing sentence stating which hypothesis is currently most parsimonious and why

**Example of what passes the floor:**
> "Alternative: this locus is a siderophore rather than an antibiotic scaffold.
> Supporting: the flanking gene encodes an NRPS A-domain with predicted serine/threonine specificity (consistent with iron-chelating backbones).
> Against: no NIS synthetase or HMMS marker detected; known siderophores in the genus carry these.
> Leading interpretation: antibiotic/antifungal lipopeptide remains most parsimonious given the absent siderophore markers."

**Example of what fails the floor:**
> "1. Could be a siderophore. 2. Could be a signalling molecule. 3. Could be a novel compound."

A numbered list with no evidence weights and no conclusion.

---

## §11 — Product-Family Interpretation

**The floor:** The tailoring complement must connect to scaffold complexity implications.

Required:

- If the BGC has *more* P450s than the reference compound → state what additional modification the extra P450(s) imply
- If an ER is at an unusual position → state the structural consequence at that position
- If a specific tailoring combination is unprecedented → state what that predicts about structural novelty
- If no MIBiG hit → state explicitly that this is a novel compound class, not just "no hit found"

**Example of what passes the floor:**
> "The reference nystatin cluster carries one P450 (NysL); this BGC carries three. The additional oxidases are consistent with additional hydroxylation events on the polyene backbone, a modification pattern seen in candicidin and candidin class variants. Structural novelty prediction: trihydroxylated polyene with altered membrane selectivity compared to nystatin."

**Example of what fails the floor:**
> "Biosynthetic capacity consistent with nystatin-family polyene."

That is the claim ceiling. It is not the interpretation.

---

## §12 — Ecological Interpretation

**The floor:** Must reason through the mechanism, not just name the context.

Required:

1. Host context and its *specific* chemical ecology challenge (not just "bee" but the relevant pathogen or competitor — e.g. *Ascosphaera apis*, *Botrytis cinerea*, *Vairimorpha ceranae*)
2. The mechanism by which this compound *class* addresses that challenge (membrane disruption, competitive exclusion, chitin synthesis inhibition, etc.)
3. If relevant literature exists: cite the *specific finding* and connect it to the strain's phylogenetic position
4. Tag the ecological claim: **observed** / **inferred** / **assumed**

**Example of what passes the floor:**
> "Host context: *Bombus* colony nest material is colonised by *Aspergillus* spp. and other moulds that threaten developing larvae (observed: Chevrette et al. 2019). Mechanism: polyene macrolides disrupt ergosterol-containing membranes, selectively targeting fungi over bacteria — the proposed antimycotic mechanism (inferred from compound class; fractionation not performed on this strain). The bee-associated *Streptomyces* in Chevrette 2019 show high rates of polyene-class BGCs (observed: 4/12 bee strains in that cohort), consistent with a guild-level antifungal function (inferred)."

**Example of what fails the floor:**
> "This BGC is ecologically relevant in a bee context."

That is the context label. It is not the interpretation.

---

## §19 — Final Mode B Judgement

**The floor:** Must be structured as an argument, not a restatement of §11.

Required structure:

1. **Evidence summary** — what the BLASTP/KCB/domain data established (1–3 sentences)
2. **Alternative rejection** — which alternative hypotheses were considered and why the leading interpretation is preferred (reference §9 explicitly)
3. **Claim ceiling** — what the evidence supports (positive) and what it does not (negative), stated as a pair
4. **Confidence tags** — observed / computed / inferred / assumed per claim

**Example of what passes the floor:**
> "Evidence summary: KCB top hit is nystatin-class polyene (observed, KCB cumulative 7,840; ~73% gene-level identity to *S. noursei* nystatin cluster). Domain architecture is complete for a large modular T1PKS with DH-rich modules (observed; 9 KS / 9 DH / 9 KR / 1 ER by domain count). Three tailoring P450s are consistent with hydroxylated variant (inferred from domain complement).
>
> Alternative rejection: siderophore hypothesis rejected (§9) — no NIS synthetase or hydroxamate markers detected; aromatic NRPS hypothesis rejected — no adenylation domains with aromatic specificity prediction. Polyene backbone remains most parsimonious.
>
> Claim ceiling: biosynthetic capacity consistent with a hydroxylated nystatin-class polyene antifungal (positive claim, inferred). This does not establish compound identity, production level, or biological activity against any specific target organism (negative claim). Extract-level bioactivity assumed (MRSA + *Candida* default).
>
> Confidence: compound class = HIGH (well-conserved PKS core + DH-rich polyene signature); structure prediction = MEDIUM (tailoring complement inferred; no BLASTP on individual tailoring enzymes); bioactivity = ASSUMED (extract-level default; no fractionation)."

**Example of what fails the floor:**
> "Biosynthetic capacity consistent with X. No compound name can be assigned."

That is the claim ceiling alone. §19 should earn that ceiling through the argument above it.

---

## Confidence vocabulary

Applied across all sections when tagging claims:

| Tag | Meaning |
|-----|---------|
| **Observed** | In the raw Mamey data: KCB score, domain count, boundary flag, etc. |
| **Computed** | Output of a deterministic rule: corrected BGC count, architecture grade |
| **Inferred** | LLM reasoning from observed + computed data: mechanism hypothesis, structural prediction |
| **Assumed** | Project default applied in absence of direct evidence: extract-level bioactivity, bldA expression assumption |

---

## Thinness patterns to watch for

These are the most common ways cards fail the interpretive floor without being obviously wrong:

**Domain naming without consequence:**
> "The NRPS contains three A-domains, two T-domains, and one C-domain."
Fix: state what substrate each A-domain is predicted to activate and how that affects the likely peptide sequence.

**Alternative list without weighting:**
> "This could be a lipopeptide or a siderophore or something novel."
Fix: use the §9 structure — one supporting piece, one against, one conclusion per alternative.

**Ecology label without mechanism:**
> "Bee-associated strains often produce antifungals."
Fix: name the specific pathogen or ecological pressure and the specific mechanism.

**§19 as a summary of §11:**
> Repeating the compound-class claim from §11 verbatim with "therefore Grade B confidence."
Fix: add evidence summary, alternative rejection, and positive/negative claim pair.

---

## See also

- **Authoritative source:** `docs/MODEB_INTERPRETIVE_FLOOR_v97146.md`
- **Real Mode B section titles:** `docs/FULL_MODEB_20_SECTION_CONTRACT_v97144.md`
- **Active judgment controller:** `docs/CHATGPT_EXECUTION_SLICE_v97147.md`
- **Mode B teaching guide:** `batch10_modeb_output_contract_plain_english.md`
- **Escalation workflow:** `docs/MODEB_EVIDENCE_ESCALATION_WORKFLOW_v97143a.md`
