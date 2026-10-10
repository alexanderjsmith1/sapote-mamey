# Literature Search Protocol — Sapote-Mamey Bundle

This historical five-bucket search map supports a selected literature task. Its §8 numbering belongs to the older Layer B report, not every current Mode B profile. Use the selected profile’s actual literature/evidence slots; no parser automatically executes this search map or closes its deferrals.

---

## Why §8 is deferred by default

The Sapote interpretation layer runs without guaranteed network access.
Protocol §4.8 and §10 require verification of the identifiers that the primary record actually assigns,
using PubMed/DOI.org as applicable. Record an unassigned or unavailable PMID or DOI explicitly;
never invent one or reject a supported source solely because it has no PMID or DOI. Rather than fabricate unverifiable
references, §8 is logged as `DEFERRED` with a completion path.

For an authorized literature task, record actual queries, searched sources, date, source/passage locators and results. Preparing a source-backed handoff is distinct from browsing, sending it or rewriting a package. Each summarized claim still needs its supporting passage; identifiers alone do not close a deferral.

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

These references were verified once (metadata) for AS-XXX. Reuse one when the specific claim and its scope still
apply, keeping the earlier review receipt: passage locator, date, applicability and open gaps. A metadata match does
not show that the paper supports a new claim; check the passage for each new use (`docs/BERT_MODE_PROTOCOL.md`).

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
If there are no hits, report a bounded result, not a conclusion: "No relevant records found in [database] using
[queries] on [date]; coverage limits: [...]". A no-hit search shows only that this search found nothing. It does
not establish that no literature exists, and it never establishes a novel compound or novel chemistry. Keep four
things as separate fields: the search outcome, bibliographic verification, claim support, and any novelty
inference (which needs its own evidence).

---

## Historical reference bank (rebind for each current use)

These entries retain the original document’s historical metadata-verification claim for AS-XXX. This table does not carry its dated review receipts or passages, and does not independently verify the papers. Reuse requires the actual retained receipt or a separately authorized review; each new claim needs its supporting passage. A missing identifier is a metadata gap to record,
never one to fill in:

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

1. Bind the selected task, exact locus identity and current profile’s literature slot.
2. Within authorized retrieval scope, record the actual search and primary bibliographic identity; record unavailable identifiers rather than requiring every paper to have them.
3. Check the passage/table supporting each claim, with units/conditions, scope and reviewed date. DOI resolution alone is metadata verification.
4. Prepare a bounded handoff or author the selected section under the actual user scope. Do not infer sending, workbook merging or package-regeneration permission from this list; preserve original receipts and report unresolved evidence.

---

## Access and completion boundaries

Access depends on the actual environment and admitted local sources, not a model name. An assistant can check supplied primary text without networking, but must identify which fields/passages it inspected. Missing access is an explicit partial/deferred state. Memory-generated citations, query strings, a work-order file or a labelled bank row are not verified sources.

---

*Sapote-Mamey Bundle v9.4 | docs/LITERATURE_SEARCH_PROTOCOL.md*
