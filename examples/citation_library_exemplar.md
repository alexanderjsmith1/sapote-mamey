# Extended Citation Library — Format Exemplar (Path A)

**Sapote-Mamey Bundle v9.7.96 | Bert Mode literature deliverable**
**[EXAMPLE: entries below are illustrative of the FORMAT. Every real entry must be Bert-Mode verified against PubMed/DOI this session — see `docs/BERT_MODE_PROTOCOL.md`.]**
Source reference: Extended BGC Guide Path A, Actinomycetes Project, May 2026.

---

## Purpose

The citation library is the deliverable that turns a strain's MIBiG hits and
compound-class predictions into a verified, manuscript-ready bibliography. One
entry per compound family present in the dataset. It complements the Layer B
literature section (§4.8) and supplies the "Key references" blocks that bench
guides cite.

Produced under Bert Mode: every entry is bucketed Verified / Partially verified /
Unverified, and no identifier is ever emitted without primary-source confirmation.

---

## Header block

```
Extended Citation Library — [Project name]
Bert Mode applied throughout. All citations directly verified against PubMed,
DOI.org, or publisher pages. PMID, DOI, PMCID, and full author lists confirmed.
Evidence type stated for each entry.
[N] compound families · [N] verified · [N] partial · [N] unverified leads
```

---

## Per-entry format (15-field standard)

### A[N]. [Compound family name] | VERIFIED

```
MIBiG accession: [BGCxxxxxxx.v  OR  "class definition — no single accession"]
Category: [mechanism / chemical class — e.g. "Antimetastatic transAT-PKS glutarimide polyketide"]

Strains in dataset:
  [StrainID BGC-NN] ([sim]% MIBiG, [frag class] — [assembly tier])
  [additional strains carrying this family, one per line]

Mechanism / biosynthetic logic:
  [2–4 sentences. What the compound does; the BGC architecture (ORF count,
  key enzymes named); what makes it notable. Paraphrased synthesis — never a
  verbatim quote from the source.]

Verified references:
  [Primary — BGC characterisation]
  [Full author list] ([year]). [Title]. [Journal] [vol(issue):pages].
  DOI: https://doi.org/[doi] | PMID: [pmid] | PMCID: [pmcid] |
  PubMed: https://pubmed.ncbi.nlm.nih.gov/[pmid]/ |
  Evidence: Experimental — [what the paper established, one line].

  [Supporting — tailoring / mechanism / review]
  [Full author list] ([year]). [Title]. [Journal] [vol(issue):pages].
  DOI: https://doi.org/[doi] | PMID: [pmid] |
  Evidence: [Experimental/Review] — [what it adds].

PNAS-style formatted citation:
  [Authors] ([year]) [Title]. [Journal] [vol(issue):pages]. https://doi.org/[doi]

Dataset context note:
  [Why this entry matters for THIS dataset: the strain, the % similarity, the
  assembly reliability, whether it is the only instance, what makes it a priority
  or a caution. This is the interpretive bridge from citation to bench decision.]
```

---

## Worked example (illustrative format — verify before real use)

### A1. Ranthipeptides (radical non-α thioether peptides) | VERIFIED

```
MIBiG accession: class definition — no single MIBiG accession
Category: RiPP — radical SAM-installed non-α thioether peptides

Strains in dataset:
  AS-XXX BGC-06 (ranthipeptide domain, interior — Good assembly)
  AS-XXX BGC-09 (ranthipeptide, interior — Good assembly)
  [+ additional carriers across the collection]

Mechanism / biosynthetic logic:
  Ranthipeptides are a recently defined RiPP class. A Cys-rich precursor peptide
  is modified by a radical SAM enzyme that installs thioether bridges between Cys
  donors and the β- or γ-carbon of acceptor residues — non-α-carbon linkages,
  distinct from sactipeptides (S-Cα). Most family members are cryptic with
  unexplored bioactivity, making them a discovery opportunity.

Verified references:
  [Class definition + bioinformatic mapping]
  Clark KA, Bushin LB, Seyedsayamdost MR (2019). Bioinformatic mapping of radical
  S-adenosylmethionine-dependent ribosomally synthesized and post-translationally
  modified peptides identifies new Cα, Cβ, and Cγ-linked thioether-containing
  peptides. J Am Chem Soc 141(20):8228–8238.
  DOI: https://doi.org/10.1021/jacs.9b01519 | PMID: 31059252 |
  Evidence: Experimental — RODEO 2.0 mapping; freyrasin and thermocellin
  characterised; class named and defined.

PNAS-style formatted citation:
  Clark KA, Bushin LB, Seyedsayamdost MR (2019) Bioinformatic mapping of radical
  S-adenosylmethionine-dependent RiPPs ... J Am Chem Soc 141(20):8228–8238.
  https://doi.org/10.1021/jacs.9b01519

Dataset context note:
  Ranthipeptide BGCs appear in multiple strains; AS-XXX BGC-06 and AS-XXX BGC-09
  are both large interior loci on Good assemblies — among the most unexplored
  classes in the dataset. A low-% MIBiG hit here likely reflects domain-level
  similarity only, not structural identity; treat as a novelty lead.
```

---

## Tiered build strategy (how to sequence a large library)

When a dataset has many families, build in priority tiers rather than all at once:

- **Tier 1:** high-priority families that anchor the manuscript narrative (the
  top antibacterial and antifungal leads, any unique-in-dataset family).
- **Tier 2:** families with a clear MIBiG hit and consolidated literature (fast
  to verify).
- **Tier 3:** medium-priority families and housekeeping classes.
- **Tier 4:** low-priority / background, added as encountered in manuscript writing.

---

## Closing compliance note (mandatory)

End every citation library with the Bert Mode compliance note (see
`docs/BERT_MODE_PROTOCOL.md`) stating what was verified this session versus
transcribed, and listing any Unverified leads with the exact search needed to
close them.
