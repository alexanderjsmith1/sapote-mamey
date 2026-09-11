# Corrective Protocol for Real Mode B Cards

## Why the previous approach failed

The previous AS-XXX work drifted into a data-extraction workflow. It produced inventories, character counts, and large tables, but it did not consistently produce scientific Mode B cards.

A real Mode B card is not a table with section headings. It is a written interpretation built from evidence.

The core failure was this:

> I treated “touch every gene” as equivalent to “interpret the BGC.”

That is wrong. A report can touch every gene and still fail if the reader cannot understand the pathway logic, the alternative interpretations, the claim boundary, and the next experiment.

## Correct definition of a real Mode B card

A real Mode B card must contain:

1. A clear lead interpretation.
2. The node/region identity at first mention.
3. A concise cluster overview.
4. A gene-by-gene interpretation written as prose, not only a table.
5. A small evidence table that supports the prose.
6. A pathway model that explains how the genes work together.
7. Comparator/KCB discussion that separates similarity from product identity.
8. Alternative hypotheses.
9. Fragmentation and boundary caveats.
10. Claim-safe final interpretation.
11. Wet-lab implications.
12. Missing-evidence ledger.

The evidence table is supporting material. The card itself is the narrative.

## Correct workflow

### Step 1 — Select one BGC

Do not work on twelve BGCs in parallel until one card is good.

Start with one high-value BGC, ideally:

- BGC018 for the megacluster problem, or
- BGC050 for the antifungal/PTM problem, or
- BGC041 for a cleaner phosphonate card.

### Step 2 — Build the evidence pack

For the selected BGC, extract:

- BGC_ID
- Node
- Region
- start/end coordinates
- boundary status
- antiSMASH products/classes
- CDS list in genomic order
- protein_length_aa for each CDS
- domain/function evidence
- KCB/comparator evidence
- any known boundary or class conflicts

### Step 3 — Collapse genes into functional blocks

Before writing prose, group genes into blocks:

- core biosynthetic genes
- tailoring genes
- transport/export/self-protection
- regulatory genes
- precursor/maturation genes, for RiPPs
- cofactor/metabolic supply genes
- likely co-captured housekeeping genes
- uncertain genes

This prevents the report from becoming a 200-row table.

### Step 4 — Write the gene-by-gene section as narrative

The gene-by-gene section should read like this:

> The first block is dominated by a large modular PKS/NRPS gene. Its length and domain composition indicate that it is not a small accessory enzyme. The adjacent oxidoreductase and transporter genes define the likely maturation/export context. The following region shifts into a separate RiPP-like block, so this cluster is better interpreted as a biosynthetic island than as one clean linear pathway.

That is Mode B prose.

A table can follow, but the prose comes first.

### Step 5 — Write §1–§20 around the evidence

The §1–§30 sections should not be filled mechanically. Each section should answer a real scientific question.

Recommended structure:

1. Identity and node/region
2. Why this BGC was selected
3. Boundary and assembly status
4. Gene-by-gene interpretation
5. Core biosynthetic logic
6. Tailoring and maturation logic
7. Transport, resistance, and regulation
8. Comparator/KCB interpretation
9. Alternative hypotheses
10. Fragmentation and co-capture risks
11. Product-family interpretation
12. Bee/microbe ecological interpretation
13. Antibacterial/antifungal relevance
14. What cannot be claimed
15. Missing evidence
16. BLASTP/HMMER next steps
17. LC-MS / fermentation implications
18. Figure/locus-map notes
19. Final Mode B judgement
20. Next actions

### Step 6 — Run a quality gate before moving to the next BGC

A card passes only if all answers are yes:

| Gate | Pass condition |
|---|---|
| Node/region | Every first BGC mention includes node and region |
| §1–§20 | All sections are present and meaningful |
| Gene prose | §4 contains prose interpretation, not only tables |
| Protein length | Important genes include protein length |
| Pathway model | The card explains how genes work together |
| Comparator caution | KCB is treated as similarity, not identity |
| Alternatives | At least two plausible alternative interpretations are named |
| Claim boundary | Exact product claims are avoided |
| Wet-lab next step | The next experiment or analysis is specific |
| Reader test | A scientist can understand the BGC without opening the CSV |

### Step 7 — Only then scale to the next BGC

Once one card passes the gate, use it as the style standard for the rest.

## Correct output after each round

For each round, report:

| BGC | Before chars | After chars | Delta | What changed | Remaining problem |
|---|---:|---:|---:|---|---|

Character counts are a progress signal, not a quality signal. The “what changed” and “remaining problem” columns are mandatory.

## Immediate execution plan for AS-XXX

The next productive move is not another all-twelve expansion.

The next productive move is:

1. Write one complete, prose-first Mode B card for BGC018.
2. Include its evidence table as an appendix, not as the main report.
3. Check it against the quality gate.
4. Revise until it reads like a real scientific report.
5. Then repeat for BGC050, BGC005, BGC028, BGC041, and the remaining BGCs.

## Recommended first target

Use BGC018 first only if the goal is the hardest flagship report.

Use BGC050 first if the goal is to produce a cleaner high-quality example faster.

My recommendation: start with BGC050 as the reference-quality card, then return to BGC018 after the standard is clear.
