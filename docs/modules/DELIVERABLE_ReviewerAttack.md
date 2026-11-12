# DELIVERABLE: Reviewer Attack Simulation

**What this is.** A template for a short block that lists the criticisms a peer reviewer would raise against a strain's strongest claim, and a safer wording for each. No tool builds it. You or an assistant write it by hand.

**Purpose.** Harden a claim before it leaves the repo. The block tests claims the package already supports. It does not create claims.

The [deliverable contract](../DELIVERABLE_CONTRACT.md) and the code win over this page. Claim-safety wording lives in the contract. The current task and [assistant governance](../ASSISTANT_GOVERNANCE.md) decide what you may do. Terms such as BGC (biosynthetic gene cluster) and KCB (KnownClusterBlast) are in the [glossary](../GLOSSARY.md).

## When to write it

Write one whenever a report states a class-level, mechanistic or ecological claim. Place it right after the executive summary in a strain report, right after the integrated model in an [ecological synthesis](DELIVERABLE_EcologicalSynthesis.md), and in any manuscript-bound output that asserts a strain finding. A report with such a claim and no block is incomplete. So is a block that skips an applicable category.

## Inputs

| Source | Used for | Category |
|---|---|---|
| The report's strongest claim, in its own wording | The "Claim or interpretation" line | All |
| `manifest.json → bgc_counts.assembly_tier`, `assembly.quality` | The fragmentation criticism and its defense | 1 |
| `*_4_triage_board.csv` columns `KCB_score` and `Novelty_auto`, plus MIBiG hits | The compound-identity criticism | 2 |
| The Mode B mechanism-to-activity link, if you drew one | The bioactivity-to-BGC criticism | 3 |
| The ecological hypothesis, if you made one | The ecological criticism | 4 |

If a category's claim was never made, write "not applicable, no <ecological or causal> claim made". Do not invent a criticism.

## Template

```text
Reviewer Attack Simulation: <strain> <BGC alias> (<full contig> · region<NNN>) if locus-specific

Claim or interpretation:
<the report's strongest claim, in its claim-safe wording>

Likely reviewer criticism:
1. <assembly fragmentation>
2. <compound identity>
3. <bioactivity-to-BGC causality, or "not applicable">
4. <ecological causality, or "not applicable">
5. <need for chemical validation>

Defense or safe revision:
1. <how the report limits the claim; cite the field and number>
2. <evidence for the class-level reading: domain bitscore, KCB, comparator>
3. <the recorded material and assay scope, or "not applicable">
4. <manuscript-safe wording, or "not applicable">
5. <the experiment that would upgrade the claim: HRMS, NMR, isolation>

Recommended manuscript wording:
"<one claim-safe sentence>"
```

## The five categories

1. **Assembly fragmentation.** "Your BGC count or boundaries are an assembly artifact." It always applies when `bgc_counts.assembly_tier` is `VERY_POOR`. That tier is the share of regions whose boundaries are interior, not a contiguity measure; report it beside `assembly.quality.fragmentation_tier` (from contig and N50 metrics), and name which one you cite. Answer with the edge status of each cluster. The corrected count is a boundary-weighted heuristic (interior 1, edge 0.5, full-contig 0.25), not a recovered count of missing regions; cite it as such, beside the raw count.
2. **Compound identity.** "A domain hit is not a compound." Defend with the diagnostic-domain bitscore and the architecture grade.
3. **Bioactivity to BGC causality.** "Extract activity does not implicate this cluster." It applies whenever you draw a mechanism link. Defend with the recorded material and assay scope. Fractionation alone does not establish compound identity or BGC causation.
4. **Ecological causality.** "Genomic capacity is not in-host function." It applies only if you made an ecological claim.
5. **Need for chemical validation.** "No HRMS or NMR, so unproven." Defend by naming the experiment.

## Checklist

- [ ] The claim line states the report's actual strongest claim.
- [ ] Every applicable category has a criticism and a defense. Inapplicable ones are marked.
- [ ] Each defense cites a field or number from the package.
- [ ] There is exactly one recommended manuscript sentence.
- [ ] Every locus is written as `strain / full contig / region / BGC alias`.
- [ ] The block sits in the right place.
- [ ] Open holds are listed.

## Example shape

```text
Reviewer Attack Simulation: EXAMPLE BGC001 (contig_1 · region001)

Claim or interpretation:
"BGC001 shows biosynthetic capacity consistent with an enediyne-type locus."

Likely reviewer criticism:
1. The cluster sits on a contig edge, and the boundary-based tier is VERY_POOR. The boundaries need review.
2. The enediyne call rests on one domain hit, and a domain hit is not a compound.
3. Not applicable, no bioactivity-to-BGC link drawn.
4. Not applicable, no ecological claim made.
5. No HRMS or NMR evidence for the warhead.

Defense or safe revision:
1. The claim is class-level. Boundaries are flagged. Long-read sequencing is named as the next step.
2. The call rests on <domain, bitscore, supporting annotations from the package>. Homology supports the class. It does not identify a compound.
3. Not applicable.
4. Not applicable.
5. HRMS and NMR on an isolated compound would test it. A chromatography and UV-DAD readout on the fraction is a first step.

Recommended manuscript wording:
"The assembly contains a locus with domains consistent with an enediyne-type cluster."
```

The example is a shape. Every value in a real block comes from your package.
