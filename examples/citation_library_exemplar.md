# Extended Citation Library — Format Exemplar (Path A)

**Historical v9.7.96 format example; current task and evidence admission rules apply.** The three-bucket vocabulary retained below is historical. Current digest labels are Verified / Partial / Policy / GenBank, with the definitions in [the citation-review protocol](../docs/BERT_MODE_PROTOCOL.md). Preserve the citation store’s separate binding/adoption states; do not map an illustrative VERIFIED heading to SOURCE_VERIFIED or OWNER_ACCEPTED.

The example's VERIFIED labels are illustrative, not a current verification receipt. Before reuse, confirm each cited statement against its actual source. Replace every historical strain/alias shorthand with `strain / full node-or-contig / region / BGC alias` copied from a bound record. If the node/region binding is unavailable, retain an identity hold rather than reconstructing it.
**[EXAMPLE: entries below are illustrative of the FORMAT. Verify bibliographic fields in an authoritative record and each claim against its source passage; record unavailable full text before use — see `docs/BERT_MODE_PROTOCOL.md`.]**

---

## Purpose

A citation library organizes reviewed reference literature beside the dataset's comparator or class hypotheses. One entry may cover a named reference family, but a similarity anchor does not establish that family's chemistry in the query strain. Bibliographic identity, claim support and applicability need separate recorded review before manuscript use. It complements the literature
sections of a Mode B card (§48 and §49 in `current50_v2`) and supplies the "Key references" blocks that bench
guides cite.

This historical example uses Bert Mode's earlier three-bucket vocabulary. Current digest labels are
Verified / Partial / Policy / GenBank, defined in [the citation-review protocol](../docs/BERT_MODE_PROTOCOL.md).
Check every identifier against its primary source before you use it.

---

## Header block

```
Extended Citation Library — [Project name]
[N] compound families · [N] verified · [N] partial · [N] unverified leads
Method: [how each entry was checked, e.g. PubMed record, DOI.org, publisher page; date checked]
Evidence type stated for each entry.
```

---

## Per-entry format

### A[N]. [Compound family name] | VERIFIED

```
MIBiG accession: [BGCxxxxxxx.v  OR  "class definition — no single accession"]
Category: [mechanism / chemical class — e.g. "Antimetastatic transAT-PKS glutarimide polyketide"]

Strains in dataset:
  [StrainID BGC-NN] ([sim]% MIBiG, [frag class] — [assembly tier])
  [additional query loci with reference-similarity evidence: full identity, source, coverage and unresolved interpretation]

Mechanism / biosynthetic logic:
  [2–4 sentences. What the compound does; the BGC architecture (ORF count,
  key enzymes named); what makes it notable. Paraphrased synthesis — never a
  verbatim quote from the source.]

Verified references:
  [Primary — BGC characterization]
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

## Worked example (fabricated dataset placeholders; literature claims require verification)

The query-locus/assembly context below is fabricated for format illustration, not a measured dataset. For each actual query, bind full locus and comparator identities, alignment metric and coverage, source status and assembly scope. Do not infer a functional family or chemical novelty from this example. The abbreviated citation title below is illustrative; a final bibliography must reproduce the verified complete title.

### A1. Ranthipeptides (radical non-α thioether peptides) | VERIFIED

```
MIBiG accession: class definition — no single MIBiG accession
Category: RiPP — radical SAM-installed non-α thioether peptides

Strains in dataset:
  <strain> / <full node-or-contig> / <region> / <BGC alias> (ranthipeptide domain, interior — Good assembly)
  <strain> / <full node-or-contig> / <region> / <BGC alias> (ranthipeptide, interior — Good assembly)
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
  characterized; class named and defined.

PNAS-style formatted citation:
  Clark KA, Bushin LB, Seyedsayamdost MR (2019) Bioinformatic mapping of radical
  S-adenosylmethionine-dependent RiPPs ... J Am Chem Soc 141(20):8228–8238.
  https://doi.org/10.1021/jacs.9b01519

Dataset context note:
  Bind the actual query and comparator identities, alignment metric/coverage,
  source status and assembly scope. These fabricated placeholders establish
  neither shared functional family nor chemical novelty. Similarity is not
  structural identity; literature applicability is a separate review.
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
`docs/BERT_MODE_PROTOCOL.md`) stating what was verified versus
transcribed, and listing any Unverified leads with the exact search needed to
close them.
