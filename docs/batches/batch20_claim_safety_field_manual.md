# Claim-Safety Field Manual
**Language rules, hallucination traps, and standing exclusions**

**v9.7.149a** | Source: `docs/GLOSSARY.md`, `CHATGPT_START_HERE.md`, `docs/DELIVERABLE_CONTRACT.md` | Last updated: 2026-06-29

---

## The single most important rule

Every claim the pipeline makes is **capacity-level**:

> "Biosynthetic capacity consistent with [class X]" — never "produces [compound Y]"

A KCB hit is **similarity, not identity**. Bioactivity is **extract-level** (MRSA + *Candida* default), never pinned to one BGC without fractionation. Absence of recorded activity is **never** read as "inactive."

These are not stylistic preferences. They are the contract between what the data says and what the pipeline claims.

---

## Required framing in every deliverable

**BGC citation format (non-negotiable):**
- First mention in any section: `BGC007 (NODE_1_length_406707 · region001)`
- Subsequent mentions within same section: `BGC007 (NODE_1 · r001)`
- Bare `BGC007` without node/region = non-conformant; never acceptable in any output

**KCB framing:**
- Correct: "Top KCB hit: ~natamycin (65% gene-level similarity to *S. noursei* cluster)"
- Correct: "Biosynthetic capacity consistent with natamycin-class polyenes"
- Wrong: "Produces natamycin"
- Wrong: "KCB identity: 65%" — KCB is cumulative score, not percent identity; never call it % identity

**Bioactivity framing:**
- Correct: "Bioactivity assumed at extract level (MRSA + *Candida* default). Fractionation required for compound-level assignment."
- Wrong: "This BGC is responsible for the antifungal activity of the strain"
- Wrong: "This strain is antibacterial-negative" — absence of data ≠ absence of activity

**Affiliation:**
- Always: 
- Never: University of Wisconsin-Madison or other institutions

---

## Capacity claim tiers

Use these phrases to match the evidence strength:

| Evidence level | Correct phrasing |
|---------------|-----------------|
| KCB match + complete core architecture | "Biosynthetic capacity consistent with [class]" |
| KCB match only (no architecture confirmation) | "Candidate [class] cluster; architecture incomplete" |
| CCTT trigger only (no KCB match) | "[Class] signal detected; KCB-dark cluster" |
| No KCB, no CCTT | "Class unknown; novel compound candidate" |
| Fractionated bioassay confirms activity | "Active against [organism] in fractionated assay ([MIC/zone data])" |

---

## Hallucination traps (active in claim_safety_linter.py)

These are the most common over-confident claims the Sapote layer produces. Each is a trap to avoid.

### Trap 1: Compound identity from KCB

**Fires when:** Mode B says "produces natamycin" or "the natamycin compound" based on KCB alone.
**Correct:** "Biosynthetic capacity consistent with natamycin-class polyenes; 45% similarity to *S. natalensis* cluster. Actual product may be a novel variant."

### Trap 2: Bioactivity pinned to one BGC

**Fires when:** "BGC_0012 is responsible for the antifungal activity" without fractionation data.
**Correct:** "Extract-level antifungal activity observed (strain-level); fractionation needed to assign to BGC_0012."

### Trap 3: Exclusive ecology (universal claim from local observation)

**Fires when:** "HSAF is bee-specific" or "hglE is a bee-associated marker."
**Correct:** "HSAF signal observed in 3/12 bee-associated strains and 2/3 wasp-associated strains in this cohort — not habitat-exclusive."

### Trap 4: Causality reversal (bldA → antibiotic production)

**Fires when:** "The high bldA T4 signal indicates this strain produces antibiotics."
**Correct:** "High bldA TTA codon prevalence (T4 signal) suggests stationary-phase regulation; consistent with defensive secondary metabolism. Not a production claim."

### Trap 5: Negative bioactivity claim

**Fires when:** "This strain has no antifungal activity" or "no antibacterial BGCs detected."
**Correct:** Never call any strain antifungal-negative or antibacterial-negative. "No antifungal BGCs detected at this assembly quality" if you need to note it.

### Trap 6: Reference bias (ecology without habitat-neutral comparison)

**Fires when:** "This compound class is bee-specific" based on only bee-associated strains in the cohort.
**Correct:** Always include the denominator: "3/12 bee-associated strains vs 2/3 wasp-associated strains carry this class — insufficient for a habitat-specificity claim."

---

## Standing exclusions from comparative claims

These three classes are permanently excluded from cross-strain or habitat-comparative claims:

### 1. NAPAA (Nosema hypothesis — retired)

**Why excluded:** NAPAA-class BGCs are ubiquitous across phyla and habitats. Including them in comparative claims inflates apparent differences between strain sets. The Nosema microsporidian hypothesis that motivated their analysis was retired.

**In Mode B:** Include NAPAA in the BGC inventory but exclude from all comparative/ecological statements. Flag: "NAPAA — excluded from comparative claims per standing rule."

### 2. hglE-KS-PREV-001 / hexacosalactone

**Why excluded:** hglE-KS-containing BGCs are prevalent across ≥8 strains spanning 7 genera and 3 habitats in the current cohort. They are habitat-non-specific. The BRYO-HGT-001 bryophyte-horizontal-transfer hypothesis was retired when the pattern proved non-habitat-specific.

**In Mode B:** Include hglE-KS clusters in the BGC inventory; exclude from comparative/ecological statements. Flag: "hglE-KS-PREV-001 — habitat-non-specific; excluded from comparative claims per standing rule."

### 3. Saccharide BGCs

**Why excluded:** Saccharide BGCs represent primary or housekeeping carbohydrate metabolism in many cases and are non-informative for natural product discovery comparisons.

**In Mode B:** Move to the background section. Flag: "Saccharide — excluded from comparative claims; primary metabolism."

---

## Evidence tagging (required in §28 / evidence ledger)

Every claim in a completed Mode B card must be tagged in the evidence ledger:

| Tag | Definition | Example |
|-----|-----------|---------|
| **OBSERVED** | In the raw Mamey data or antiSMASH output | "18 genes detected in BGC boundary (OBSERVED, antiSMASH region annotation)" |
| **COMPUTED** | Output of a deterministic rule | "Corrected BGC count = 38.25 (COMPUTED, Interior + ½·Edge + ¼·FC formula)" |
| **INFERRED** | LLM reasoning from observed + computed data | "Polyene backbone predicted from DH-rich domain architecture (INFERRED, domain pattern)" |
| **ASSUMED** | Project default applied without direct evidence | "Extract-level bioactivity (ASSUMED, MRSA + *Candida* default)" |

---

## Deliverable conformance rules (from DELIVERABLE_CONTRACT.md)

Two hard requirements for every deliverable:

1. **No internal codenames.** The project name is "Actinomycetes Project" / affiliation . Retired codenames must never appear. Run a codename scan before release.

2. **Contig-ID locator on every BGC.** A bare `BGC###` is meaningless without its locus. The first mention in any section must include at minimum `BGC_ID (contig · regionXXX)`. This applies to layperson guides, technical reports, bench guides, fermentation cards, gene-by-gene tables, and chat — not just workbook tables.

A deliverable with a bare BGC ID or a codename is non-conformant and must be regenerated.

---

## Quick reference card

```
KCB hit           → "biosynthetic capacity consistent with [class]"
% identity        → never use; say "X% similarity"
Bioactivity       → "extract-level (MRSA + Candida default)"
NAPAA             → exclude from comparative claims
hglE-KS-PREV-001  → habitat-non-specific; exclude from comparative claims
Saccharide        → exclude from comparative claims
Negative activity → never claim; absent data ≠ absent activity
BGC reference     → always include contig + region on first mention
Affiliation       → 
```

---

## See also

- **Authoritative framing rules:** `CHATGPT_START_HERE.md` § "Non-negotiable framing"
- **Shared guard block:** `prompts/reuse/_SHARED_GUARD_BLOCK.md`
- **Standing exclusions:** `docs/GLOSSARY.md` (NAPAA, hglE-KS-PREV-001 entries)
- **Deliverable contract:** `docs/DELIVERABLE_CONTRACT.md`
- **Claim-safety linter:** `tools/claim_safety_linter.py`
- **Hallucination trap audit (§34 in monolith):** `docs/CHATGPT_EXECUTION_SLICE_v97147.md`
