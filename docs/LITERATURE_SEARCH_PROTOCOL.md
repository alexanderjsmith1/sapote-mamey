# Literature Search Protocol — Sapote-Mamey Bundle

Every strain analysis produces a §8 literature section covering five topic
buckets (top antibacterial lead, co-lead, top antifungal lead, ecological
framing, and siderophore/mechanistic support). This document tells you exactly
what to search for each BGC class so the references can be verified and the
§8 deferral closed.

---

## Why §8 is deferred by default

The Sapote interpretation layer runs without guaranteed network access.
Protocol §4.8 and §10 require every citation to carry a *verified* PMID and
DOI resolved against PubMed/DOI.org. Rather than fabricate unverifiable
references, §8 is logged as `DEFERRED` with a completion path.

**Your job:** run the searches below, send the PMIDs to Claude, and §8 will be
written and closed in one pass.

---

## Standard five-bucket search map

For each strain, the §8 deferral note in the Layer B report names the specific
BGC IDs and classes. Map those to the searches below.

### Bucket 1 — Top antibacterial lead

| BGC class | PubMed search strings |
|---|---|
| NRPS + β-lactamase-fold self-resistance | `nonribosomal peptide synthetase self-resistance beta-lactamase Streptomyces` · `antibiotic biosynthetic gene cluster self-protection resistance gene` |
| T1PKS (hglE-KS) | `hglE KS heterocyst glycolipid polyketide synthase` · `type I PKS Streptomyces antibacterial biosynthesis` |
| Betalactone / NRP-metallophore | `betalactone biosynthesis Streptomyces antibiotic` · `obafluorin beta-lactone natural product` · `NRP-metallophore siderophore biosynthesis` |
| T2PKS aromatic + β-lactamase-fold | `type II polyketide synthase aromatic Streptomyces self-resistance` · `angucycline anthracycline T2PKS beta-lactamase` |
| Hybrid NRPS/PKS + resistance | `hybrid NRPS PKS lipopeptide Streptomyces antibacterial biosynthesis` |
| Lanthipeptide class III | `class III lanthipeptide biosynthesis LanKC` · `lanthipeptide antimicrobial Streptomyces` |

### Bucket 2 — Resistance/self-protection framing (always include)

These two apply to every antibacterial lead with coupled resistance genes:

- `Ogawara self-resistance Streptomyces beta-lactam` *(Ogawara 2016, Molecules — PMID 27171072)*
- `Wencewicz antibiotic resistance biosynthesis crossroads` *(Wencewicz 2019, J Mol Biol — PMID 31288031)*
- `self-resistance gene directed natural product discovery` *(Yan et al. 2020, Nat Prod Rep — PMID 31912842)*

These are verified references already used in AS-XXX. Reuse them across strains
where the mechanistic framing applies — no re-verification needed.

### Bucket 3 — Top antifungal lead

| BGC class | PubMed search strings |
|---|---|
| T1PKS polyene / fatty-acid | `polyene macrolide polyketide Streptomyces antifungal biosynthesis` · First: look up the top MIBiG hit ID at mibig.secondarymetabolites.org to identify the known compound, then search by name |
| Halogenated T1PKS | `halogenated polyketide Streptomyces biosynthesis` · `flavin-dependent halogenase polyketide actinomycete` |
| Lanthipeptide | `lanthipeptide antifungal biosynthesis mining microorganism` *(Li et al. 2021, Front Bioeng Biotechnol — PMID 34395400; verified in AS-XXX)* |
| NI-siderophore / NRP-metallophore | `bacterial siderophore community host interactions` *(Kramer et al. 2020, Nat Rev Microbiol — PMID 31748738; verified)* · `iron infection immunity nutritional` *(Cassat & Skaar 2013, Cell Host Microbe — PMID 23684303; verified)* |

### Bucket 4 — Ecology / habitat framing

Always include one insect-symbiont or soil-ecology anchor:

- **Bee/insect-associated strains:** `Streptomyces insect microbiome antimicrobial potential` *(Chevrette et al. 2019, Nat Commun — PMID 30705269; verified)*
- **Soil strains:** `soil Streptomyces chemical ecology competition antibiotic`
- **Any Streptomyces:** `Streptomyces symbionts emerging widespread theme` *(Seipke et al. 2012, FEMS Microbiol Rev — PMID 22091965; verified)*
- **Strain-specific:** always search `[species name] secondary metabolites` to check prior characterization

### Bucket 5 — Strain-specific prior literature

Always run this before §8:
`[Genus species] secondary metabolites` and `[Genus species] biosynthesis antibiotic`

If hits exist, they become the first reference in §8.1 (discovery/prior context).
If no hits, note "no prior secondary metabolite characterization reported" — that
itself is a positive statement of novelty.

---

## Verified reference bank (carry across all strains)

These were verified against DOI.org for AS-XXX and can be reused without
re-verification:

| Key | Citation | PMID | DOI |
|---|---|---|---|
| Chevrette2019 | Chevrette MG et al. Nat Commun. 2019. | 30705269 | 10.1038/s41467-019-08438-0 |
| Seipke2012 | Seipke RF et al. FEMS Microbiol Rev. 2012. | 22091965 | 10.1111/j.1574-6976.2011.00313.x |
| Risdian2019 | Risdian C et al. Microorganisms. 2019. | 31064143 | 10.3390/microorganisms7050124 |
| Campbell1997 | Campbell EL et al. Arch Microbiol. 1997. | 9075624 | 10.1007/s002030050440 |
| Ogawara2016 | Ogawara H. Molecules. 2016. | 27171072 | 10.3390/molecules21050605 |
| Wencewicz2019 | Wencewicz TA. J Mol Biol. 2019. | 31288031 | 10.1016/j.jmb.2019.06.033 |
| Yan2020 | Yan Y et al. Nat Prod Rep. 2020. | 31912842 | 10.1039/c9np00050j |
| Hegemann2020 | Hegemann JD, Suessmuth RD. RSC Chem Biol. 2020. | 34458752 | 10.1039/d0cb00073f |
| Li2021 | Li C et al. Front Bioeng Biotechnol. 2021. | 34395400 | 10.3389/fbioe.2021.692466 |
| Kramer2020 | Kramer J et al. Nat Rev Microbiol. 2020. | 31748738 | 10.1038/s41579-019-0284-4 |
| Cassat2013 | Cassat JE, Skaar EP. Cell Host Microbe. 2013. | 23684303 | 10.1016/j.chom.2013.04.010 |
| Johnson2008 | Johnson L. Mycol Res. 2008. | 18280720 | 10.1016/j.mycres.2007.11.012 |

---

## How to close a §8 deferral

1. Run the searches above for the specific BGC classes flagged in your Layer B §8.
2. Collect PMIDs (1–2 per topic bucket; reviews preferred).
3. Verify each DOI resolves at https://doi.org/[DOI].
4. Send PMIDs to Claude with the strain ID. Claude writes §8, updates the
   workbook Literature_Index, and regenerates the package.

---

## What Claude cannot do

Claude cannot resolve DOIs or PMIDs without network access. This is why §8 is
always deferred by default and why verification is a human step. Do not ask
Claude to generate citations from memory — they will not be verified.

---

*Sapote-Mamey Bundle v9.4 | docs/LITERATURE_SEARCH_PROTOCOL.md*
