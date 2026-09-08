---
schema_version: sapote-markdown-1.0
document_type: mode_b_card
title: Synthetic Mode B 48-Section Export Fixture
subtitle: Exact-identity, wide-matrix, long-document rendering test
audience: Mode B authors and scientific reviewers
authority: TRUE_DRAFT_NOT_PARENT_AUDITED_NOT_SHELF_PROMOTABLE; synthetic fixture
render_profile: mode_b_card
claim_safety_footer: TRUE DRAFT; synthetic fixture; capacity is not production and missing evidence is not biological absence.
source_manifest: fixture_manifest.json
exact_locus:
  strain: DEMO-STRAIN
  node_or_contig: demo_contig_0001_length_80000
  region: region001
  bgc_alias: BGC001
---

# DEMO-STRAIN / demo_contig_0001_length_80000 / region001 / BGC001 — Synthetic Mode B fixture

> [CAUTION] Fixture, not evidence
> Every gene name, annotation, comparison, and value below is synthetic. The card exists only to test a complete 48-section document shape.

## §1 Identity and node/region

DEMO-STRAIN / demo_contig_0001_length_80000 / region001 / BGC001 is the complete synthetic identity. No alias-only transfer is permitted.

## §2 Why this BGC was selected

The fixture was selected because it combines a named core enzyme, tailoring genes, transport, regulation, and an intentionally unassigned resistance state.

## §3 Boundary and assembly status

The synthetic interval spans 10,000–42,000 nt on one demonstration contig. Boundary certainty is not evaluated because no GBK backs this fixture.

## §4 Gene-by-gene interpretation

<!-- sapote:table id=governed_gene_matrix layout=landscape repeat_header=true widths=1.1,1.1,1.6,1.2,1.2,1.2,1.2,1.2,1.2,1.2,1.2 -->
| Gene | SHA prefix | Proposed role | nr subject | nr identity | nr positives | ClusteredNR subject | CNR identity | CNR positives | Swiss-Prot subject | SP identity |
|---|---|---|---|---|---|---|---|---|---|---|
| demo_001 | a1b2c3d4 | putative precursor-supply enzyme | UNBOUND | n/a | n/a | UNRETURNED | n/a | n/a | NOT_SCANNED | n/a |
| demo_002 | b2c3d4e5 | putative core enzyme | synthetic_subject_2 | 71.2% (356/500 aa) | 82.0% (410/500 aa) | synthetic_cluster_2 | 68.4% (342/500 aa) | 79.4% (397/500 aa) | synthetic_reviewed_2 | 63.0% (315/500 aa) |
| demo_003 | c3d4e5f6 | candidate tailoring enzyme | synthetic_subject_3 | 54.8% (137/250 aa) | 66.0% (165/250 aa) | UNRETURNED | n/a | n/a | NOT_SCANNED | n/a |
| demo_004 | d4e5f6a7 | predicted transporter-family protein | UNBOUND | n/a | n/a | UNRETURNED | n/a | n/a | NOT_SCANNED | n/a |
| demo_005 | e5f6a7b8 | predicted local regulator | UNBOUND | n/a | n/a | UNRETURNED | n/a | n/a | NOT_SCANNED | n/a |

## §5 Core biosynthetic logic

demo_001 could supply a precursor accepted by demo_002, while demo_002 carries the only synthetic core-enzyme annotation. This ordering is a testable route, not a product assignment; a housekeeping role for demo_001 remains a competing interpretation.

## §6 Tailoring and maturation logic

demo_003 is placed after demo_002 only as a plausible tailoring step. Its synthetic family annotation does not establish substrate order, so assays of demo_002 alone and demo_002 plus demo_003 would distinguish core formation from maturation.

## §7 Transport, resistance, and regulation

demo_004 has transporter-family capacity and demo_005 has regulator-family capacity. Neither annotation proves export, self-resistance, pathway regulation, or physical interaction with a product.

## §8 Comparator/KCB interpretation

The synthetic demo_002 comparison supports only enzyme-family resemblance. Similarity is not identity, and no named product is assigned.

## §9 Alternative hypotheses

The region could represent a partial pathway, a primary-metabolism neighborhood, or unrelated adjacent genes. The fixture retains all three alternatives.

## §10 Fragmentation and co-capture risks

No real assembly is present. A production card would check edge distance, neighboring protoclusters, and co-capture before treating the interval as complete.

## §11 Product-family interpretation

The fixture supports no product family. It demonstrates how a card can preserve a class-level hold.

## §12 Bee/microbe ecological interpretation

No host or substrate evidence is bound, so ecological interpretation is deferred as an evidence gap rather than reported as absence.

## §13 Antibacterial/antifungal relevance

No assay, product, or resistance phenotype is present. Activity claims are prohibited.

## §14 What cannot be claimed

Product identity, production, activity, ecological function, novelty, self-resistance, and publication readiness cannot be claimed from this fixture.

## §15 Missing evidence

Missing items include exact GBK features, full protein sequences, domain coordinates, local scans, comparator manifests, expression data, and metabolite measurements.

## §16 BLASTP/HMMER next steps

The demonstration workflow would bind every query to a full protein SHA, run approved local searches, and preserve unreturned cells separately by channel.

## §17 LC-MS / fermentation implications

No mass or culture condition is predicted. A future experiment would compare a controlled culture panel only after a chemically plausible target is established.

## §18 Figure/locus-map notes

A real locus map should label demo_001–demo_005, interval coordinates, direction, domains, and uncertain boundaries without implying product identity.

## §19 Final Mode B judgement

This is a rendering fixture with no biological judgment. The only valid state is TRUE_DRAFT_NOT_PARENT_AUDITED_NOT_SHELF_PROMOTABLE.

## §20 Next actions

No gene is called an A-domain programming target because the fixture localizes no AMP-binding or adenylation domain. Bind structured domains before making such a designation.

## §21 Precursor mass ladder

No formula or precursor mass is supported. The correct state is NOT_CALCULATED_SOURCE_UNBOUND.

## §22 RiPP database search

No RiPP precursor or maturation evidence is present. The search state is NOT_STAGED, not a biological no-hit.

## §23 Heterologous expression

Expression is not proposed until boundaries, coding sequences, and a safe host strategy are defined.

## §24 Scaffold novelty score

No scaffold is known and no novelty score is calculated. Sequence difference alone would not establish chemical novelty.

## §25 Genome neighbourhood

The fixture places demo_001–demo_005 adjacently but supplies no neighboring coordinates beyond the synthetic interval.

## §26 OSMAC protocol

A real OSMAC design would specify medium, temperature, time, aeration, replicates, controls, and falsifying readouts. None are inferred here.

## §27 Self-resistance assessment

No self-resistance gene is assigned. demo_004 is only a transporter-family protein; resistance-specific local evidence, substrate relation, and phenotype remain unbound.

## §28 Evidence provenance ledger

All values in this card are authored fixture data. `fixture_manifest.json` would identify their synthetic origin in a packaged test.

## §29 Cross-cluster interactions

RG-GMCI, BiG-SCAPE, ClusterBlast, assembly-link, and exact local comparison streams are all NOT_STAGED for this fixture. No cross-cluster conclusion follows.

## §30 Experimental decision tree

First bind the source; then validate gene and domain identities; then compare core-only and core-plus-tailoring constructs; finally test chemistry with controlled assays.

## §31 Region CDS census

The governed synthetic roster contains five unique gene labels and five unique SHA prefixes. It is illustrative, not sequence-backed.

## §32 Assembly-line inventory

demo_002 is the only synthetic core enzyme. No module count is asserted because domain and module evidence is absent.

## §33 Module programming readout

No modules are localized. Therefore substrate programming, stereochemistry, and module order remain unassigned.

## §34 Initiation & release logic

No loading, initiation, termination, or release domain is bound. Linear gene order cannot substitute for domain evidence.

## §35 Protocluster decomposition

The fixture contains one demonstration interval and no antiSMASH protocluster definitions, so decomposition is not performed.

## §36 Boundary status + overmerge/locus-splitting adjudication (merged)

Neither overmerge nor split-pathway rescue can be adjudicated without the exact region and flanking features.

## §37 Partner & accessory proteins

demo_001 and demo_003 are possible complementary proteins; their roles remain hypotheses until biochemical or genetic evidence binds them to demo_002.

## §38 Co-located resistance & efflux

demo_004 is co-listed but not assigned to resistance or efflux. Co-location and transporter-family similarity are insufficient.

## §39 Cross-strain sequence identity

No cross-strain query panel, subject coordinates, or denominator ledger is present. The workflow state is NOT_STAGED.

## §40 BiG-SCAPE family / cohort placement

BiG-SCAPE placement is NOT_STAGED. No family or cohort language is admissible.

## §41 Protein / domain phylogeny

No alignment, model, rooting rule, or support analysis exists. Phylogenetic placement is held.

## §42 Horizontal transfer evidence

No composition, synteny, mobility, or phylogenetic discordance evidence is bound. Horizontal transfer is not assessed.

## §43 Split-pathway / cross-contig (RG-GMCI)

RG-GMCI is NOT_STAGED and the synthetic interval is not an assembly. Physical linkage is not inferred.

## §44 Within-cohort prevalence & tier

No governed cohort denominator is available. Prevalence and tier are unassigned.

## §45 Supervisor / university cohort comparison

The exact demo_001–demo_005 query roster has no staged cohort scans. No comparator conclusion is written.

## §46 Type / reference strain comparison

The exact demo_001–demo_005 query roster has no staged type/reference scans. Pending or missing scans cannot become type-strain conclusions.

## §47 Host-matched unrelated reference

No host-matched unrelated reference is bound. The comparison remains NOT_STAGED.

## §48 Cross-cohort synthesis & claim ceiling

The five-gene synthetic roster demonstrates document structure only. It does not establish a complete biosynthetic locus, product, production, activity, resistance, ecology, novelty, or physical linkage.

