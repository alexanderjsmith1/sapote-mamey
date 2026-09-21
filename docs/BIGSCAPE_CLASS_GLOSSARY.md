# BiG SCAPE Class Glossary

This key explains the broad biosynthetic class codes shown in Sapote-Mamey BiG-SCAPE reports and widgets. The same bundled vocabulary drives the TSV fields, report headings, network labels, and visible legends.

## How to read a network

1. Start with the GCF number and cutoff. They identify one run-specific family, not a universal biological name.
2. Expand the class code with the table below. Treat it as a broad routing label from source antiSMASH annotations.
3. Hover or click a node and record the complete strain, node or contig, region, and BGC alias identity.
4. Read the boundary state. CONTIG_EDGE is a caution that the called region touches a contig boundary.
5. Read direct edge distance as pairwise similarity context. Smaller distance means closer by this run's model; it does not prove the same product.
6. Stop at the claim ceiling. Use gene order, domains, verified searches, chemistry, and experiments for stronger conclusions.

## Broad class vocabulary

| Code | Full name | Plain-language meaning | Source basis | Claim ceiling |
|---|---|---|---|---|
| PKS-NRPS | Hybrid polyketide and nonribosomal peptide | The source labels contain both polyketide and nonribosomal peptide biosynthetic classes. | Co-occurring PKS and NRPS terms in source antiSMASH family labels. | Hybrid broad-class label only; module order and product remain unverified. |
| T1PKS | Type I polyketide synthase | A modular or iterative type I polyketide biosynthetic class is present in the source labels. | T1PKS or trans-AT PKS source label. | Broad PKS class only; product, module chemistry, and completeness remain unverified. |
| T2PKS | Type II polyketide synthase | A type II aromatic polyketide biosynthetic class is present in the source labels. | T2PKS or HR-T2PKS source label. | Broad PKS class only; scaffold and product remain unverified. |
| T3PKS | Type III polyketide synthase | A type III polyketide biosynthetic class is present in the source labels. | T3PKS source label. | Broad PKS class only; substrate and product remain unverified. |
| NRPS | Nonribosomal peptide synthetase | The source labels identify a nonribosomal peptide biosynthetic class. | NRPS, nonribosomal, or NRP-metallophore source label. | Broad peptide class only; monomer sequence, product, and completeness remain unverified. |
| PKS | Polyketide synthase | The source labels identify a polyketide class without a resolved type I, II, or III subtype. | Generic PKS or polyketide source label. | Broad PKS class only; subtype and product remain unverified. |
| RANTHI | Ranthipeptide | The source labels identify a radical non-alpha thioether peptide class. | Ranthipeptide source label. | Broad RiPP subclass label only; precursor, modifications, and product remain unverified. |
| LASSO | Lassopeptide | The source labels identify a lasso-shaped ribosomal peptide class. | Lassopeptide source label. | Broad RiPP subclass label only; mature peptide and activity remain unverified. |
| LAN | Lanthipeptide | The source labels identify a lanthionine-containing ribosomal peptide class. | Lanthipeptide source label. | Broad RiPP subclass label only; precursor, ring pattern, and product remain unverified. |
| LAP | Linear azol or azoline containing peptide | The source labels identify a ribosomal peptide class with azole or azoline modifications. | Linear azol, linear azoline, LAP, or azole-containing-RiPP source label. | Broad RiPP subclass label only; mature peptide and modification pattern remain unverified. |
| RiPP | Ribosomally synthesized and post translationally modified peptide | The source labels identify a ribosomal peptide class without a more specific code in this vocabulary. | Generic RiPP source label. | Broad peptide class only; precursor, modifications, product, and activity remain unverified. |
| TERP | Terpene | The source labels identify a terpene or terpene-precursor biosynthetic class. | Terpene source label. | Broad terpene class only; scaffold and product remain unverified. |
| SAC | Saccharide | The source labels identify a saccharide or oligosaccharide biosynthetic class. | Saccharide or oligosaccharide source label. | Broad carbohydrate class only; pathway role and product remain unverified. |
| PHOS | Phosphonate | The source labels identify a phosphonate biosynthetic class. | Phosphonate source label. | Broad phosphonate class only; product and activity remain unverified. |
| NIS-SID | Nonribosomal independent siderophore | The source labels identify a siderophore assembled without an NRPS backbone. | NI-siderophore or NIS-siderophore source label. | Broad siderophore class only; metal preference, product, and activity remain unverified. |
| METAL | Metallophore | The source labels identify a broad metal-chelating biosynthetic class without a more specific code. | Metallophore source label not already assigned to NRPS. | Broad metal-chelation class only; metal preference, product, and activity remain unverified. |
| OTH | Other antiSMASH class | The source label is recognized but does not map to a more specific code in this compact vocabulary. | Other, fatty acid, ectoine, butyrolactone, or betalactone source label. | Routing category only; no pathway or product inference follows. |
| MIX | Mixed broad classes | Members of the displayed GCF carry more than one broad class code. | Deterministic disagreement among member-level broad class codes. | Mixed routing label only; it does not establish a hybrid pathway or shared product. |
| UNK | Unresolved class | The available source labels do not resolve to a code in this vocabulary. | No configured class term matched the available source labels. | Unknown means unresolved, not biologically absent or novel. |

## Reviewed subtype codes

A reviewed subtype is an optional, separately supplied interpretation and is not derived from the broad source label.

A reviewed subtype row must provide `family_id`, `reviewed_subtype_code`, `full_name`, `plain_language_meaning`, `source_basis`, and `claim_ceiling`. The subtype is displayed separately from the broad class code so readers can see which statement comes from the source label and which came from a later review.

**Subtype claim ceiling.** A reviewed subtype remains a comparison or class-level interpretation unless exact-locus evidence and the stated release conditions support a stronger claim.

## Overall claim ceiling

Broad class codes describe source antiSMASH class labels for navigation only. They do not establish an exact product, pathway completeness, expression, production, activity, novelty, enrichment, host adaptation, or physical cross-contig linkage.
