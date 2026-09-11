# Volume IV — Detection & Trigger Frameworks

> **Currency scope:** This volume retains its historical edition and review stamps. Only the checks listed in the [currency record](Encyclopedia-Currency.md) have been refreshed for the current candidate. Other constants, numerical claims, literature interpretations, and worked-run results have not been comprehensively revalidated. A newer bundle does not make those older observations current.

*Edition: bundle v9.7.33 / engine Mamey 1.9.41 · re-grounded to bundle v9.7.91 / engine Mamey 1.9.91 on 2026-06-20 (the fifteen CCTT_PATTERNS families, the 6 AB / 2 AF diagnostic subsets, the 3 promiscuous families, the RG-GMCI constants — gap 30 / span 400 / hub-degree 4 — and the TFBS 300 bp window all re-verified against the running engine; §IV.9 bldA gating corrected) · 2026-06-15*
*Chapters IV.1–IV.10. The densest reference volume. Read Volumes I–III first (→ Master Index).*
*Rev. 2026-06-16: incorporates the encyclopedia-poll corrections (AB-diagnostic set = 6; CCTT triggers = 15 with T43-NN promoted, TOMM/LMPKS/SILENT de-listed; ENE \[E-signal\] not BSL-2; \#28 real-data caveat; RG-GMCI no-FDR).*

------------------------------------------------------------------------

## §IV.1 · KnownClusterBlast and ClusterBlast — the two similarity passes

antiSMASH produces **two** distinct homology comparisons, and the engine reads both — a distinction worth
stating plainly because the front-facing outputs foreground one of them. <span class="tag t-engine">\[engine\]</span>

- **KnownClusterBlast (KCB)** compares a region to **characterized reference clusters** (the MIBiG repository).
  A KnownClusterBlast hit answers "does this region resemble a cluster whose product is *known*?" This is the
  headline similarity signal — the **KCB anchor**, the `kcb_top` line, the MIBiG reference hits — and it is the
  one disciplined by *similarity, not identity* (→ §I.3): a strong MIBiG hit says the region is *consistent with
  the class of* a known cluster, never that it makes that cluster's product.
- **ClusterBlast** compares a region to **other antiSMASH-detected regions** across a broad genome database —
  region-to-region homology, not comparison to characterized references. It answers a different question: "does
  this region resemble *other clusters*, characterized or not?"

The engine parses both from the TXT clusterblast files (the `source_kind` field tags each line `knownclusterblast`
vs `clusterblast`), and uses them for different jobs. KnownClusterBlast drives the anchor and the primary KCB
score. **ClusterBlast is used mainly behind the scenes**: it scaffolds the cross-contig reconstruction in RG-GMCI
(→ §IV.4 — the "clusterblast-scaffolded reconstruction hypothesis"), and it supplies a **fallback denominator**
(`denominator_type = "clusterblast best subject cluster"`) when no KnownClusterBlast hit exists, so a similarity
band is never reported against an unstated denominator (→ §III.7). So the engine *does* look at ClusterBlast — it
is simply less visible than KnownClusterBlast because its role is reconstruction and denominator-of-last-resort
rather than the front-facing anchor. A reader who sees "KCB" in an output is seeing KnownClusterBlast; ClusterBlast
is doing quieter structural work underneath. <span class="tag t-engine">\[engine\]</span>

One naming note for anyone reading the code: the knownclusterblast-vs-clusterblast distinction appears under
*two* field names in *two* layers — `source_kind` at the evidence-parse layer (above), and,
as of v9.7.100, `db_kind` in the RG-GMCI rescue layer (§IV.4). They tag the same distinction; the rescue
layer additionally recognises `subclusterblast` (sub-operon hits) and excludes it from cluster geometry.
<span class="tag t-engine">\[engine\]</span>

## §IV.2 · The CCTT T43 trigger framework

Where KCB asks "does this resemble a known cluster?", the **CCTT framework** (the **T43** trigger set) asks a
sharper, gene-level question: "is a *class-defining diagnostic* present in this region?" A **trigger** is a
motif/keyword signature whose presence corroborates a specific biosynthetic-class capacity — a halogenase for a
halogenated product, a PEP-mutase for a phosphonate, a YcaO for an azole RiPP. Triggers are how a KCB-dark,
gene-only lead still reaches lead tier (the Tier-1 diagnostic floor, → §III.4). <span class="tag t-engine">\[engine\]</span>

Three disciplines govern triggers, all already met elsewhere in this work:

1.  **Corroboration, not just firing.** A trigger that fires on a class-*incompatible* locus is **uncorroborated**:
    recorded for the judgment layer, but granted no class-capacity credit, no AB/AF diagnostic bonus, and no floor
    (→ §III.6). Only corroborated triggers build the capacity claim.
2.  **Promiscuous families need extra corroboration.** A small set — the halogenase (T43-HAL), the exotic-halogenase
    (T43-XHAL), and the N–N-bond (T43-NN) families — fire broadly across unrelated chemistry (`CCTT_PROMISCUOUS`),
    so their bare presence is weak evidence and is treated with extra caution.
3.  **AB/AF diagnostic subset.** A few families are strong enough bioactivity diagnostics to move a score directly
    (→ §III.3). The antifungal set has **three** members: **T43-NUC**, **T43-PTM**, and **T43-PYE**. The antibacterial set has **eight** members:
    **T43-LAN**, **T43-LASSO**, **T43-THA**, plus **T43-PHO** (phosphonate antibiotics), **T43-AMC** (aminoglycoside),
    and **T43-BLA** (β-lactam), with **T43-GPA** (glycopeptide) and **T43-BLT** (betalactone) added later. PHO/AMC/BLA were wired in v9.7.20/.21 because each fires only on its *own* biosynthetic
    diagnostic (not a similarity-only KCB anchor), so a fired AMC/BLA/PHO is a real class hit. The remaining families
    corroborate *class capacity* without an automatic bioactivity bonus. <span class="tag t-engine">\[engine\]</span> (`AB_DIAGNOSTIC_TRIGGERS` /
    `AF_DIAGNOSTIC_TRIGGERS`, scoring.py:34–46).

**Worked example (real v9.7.33 run — the Attine *Pseudonocardia*).** The three disciplines, all visible in one
strain's CCTT firings: <span class="tag t-engine">\[engine: real run; strain in the PRIVATE worked-examples key\]</span>

| Trigger | Fired on | Class label | Corroborated? | Outcome |
|----|----|----|----|----|
| **T43-THA** (AB diagnostic) | one RiPP locus (Edge) | RiPP; RiPP-like | Yes (RiPP context is THA-compatible) | diagnostic lifts AB to **59.9**, making it the strain's **\#1 corrected-rank lead** — though as an Edge RiPP it is itself capped at Inventory (the RiPP-fragment cap, → §V.2) |
| **T43-HAL** (Promiscuous) | five loci (Interior/Edge/Full-contig) | PKS/fatty-acid/hglE-KS · ectoine/halogenated · NRP-metallophore/NRPS · halogenated · halogenated | Yes — each carries a "halogenated" label, so none is marked uncorroborated | **none reaches lead tier** (AB 18.7–41.0, all Inventory) |

The contrast is the chapter in miniature. **T43-THA** was one of the six AB diagnostics in that historical run (the current set has eight): corroborated on a RiPP, it
earns the bonus and becomes the strain's \#1 corrected-rank lead (even though that Edge RiPP fragment is itself
capped at Inventory — a corrected-*rank* leader can still be a capped fragment, which is exactly why rank and
raw tier are reported together, → §III). **T43-HAL** fires *five times across four unrelated chemistries*
— the definition of a Promiscuous family — and although each firing is technically corroborated by a "halogenated"
product label, halogenation is a *modification, not a class call*, so `T43-HAL_` sits in the Tier-1-floor exclusion
set (→ §V.2) and a lone halogenase never floors a lead. The result is exactly right: a class diagnostic (THA)
rescues a real lead, while five promiscuous tailoring-enzyme hits stay catalogued at Inventory rather than
inflating the board. (Note BGC027's `hglE-KS` label — a standing-rule PREV-001 domain, → §I.6 — independently
keeps that region out of the lead rank.)

## §IV.3 · The eighteen CCTT trigger families

The engine's `CCTT_PATTERNS` carries exactly **eighteen** gene-signature trigger families (`source_scans.py`). Each
detects a class-defining gene/motif signature; the *detection signature* is <span class="tag t-engine">\[engine\]</span>, while the *capacity-class*
it corroborates is a <span class="tag t-science">\[science\]</span> literature inference. Presence corroborates *capacity*, never product.

| Family | Detects (signature) <span class="tag t-engine">\[engine\]</span> | Corroborates capacity for <span class="tag t-science">\[science\]</span> |
|----|----|----|
| **T43-HAL** halogenase | flavin-dependent / tryptophan halogenase | halogenated metabolites *(promiscuous)* |
| **T43-XHAL** exotic halogenation | fluorinase, chlorinase, SAM-dependent halogenase (e.g. SalL) | C–F / C–Cl bonds *(promiscuous)* |
| **T43-NN** N–N bond | n–n bond, diazo, azoxy, hydrazine, creE/creD | N–N-bond natural products *(promiscuous)* |
| **T43-PHO** phosphonate | "phosphonate" product token + PEP-mutase; excludes catabolic phn / C–P lyase / transporters (the token still over-fires; the §IV.2 corroboration gate is the real protection, → §IV.2) | C–P-bond natural products *(phosphonate antibiotics: AB-diagnostic)* |
| **T43-NUC** nucleoside | nikkomycin, polyoxin, peptidyl-nucleoside, chitin-synthase-inhibitor | **antifungal** nucleosides |
| **T43-PTM** HSAF / tetramate | HSAF, maltophilin, dihydromaltophilin, heat-stable antifungal, tetramate | **antifungal** macrolactams |
| **T43-BLA** β-lactam | nocardicin, isopenicillin-N synthase, pcbAB/pcbC | β-lactams *(AB-diagnostic)* |
| **T43-AMC** aminocyclitol | aminocyclitol, DOIS, 2-deoxy-scyllo-inosose, btrC | aminoglycoside/aminocyclitol *(AB-diagnostic)* |
| **T43-ENE** enediyne | enediyne | enediynes *(→ `[E-signal]` claim-safety note, §I.6 — not a BSL-2 flag)* |
| **T43-LAN** lanthipeptide | lanthipeptide, lantibiotic, lanC/lanM | **antibacterial** lanthipeptides |
| **T43-LASSO** lasso peptide | lassopeptide / lasso peptide | **antibacterial** lasso peptides |
| **T43-THA** thioamide | thioamide, YcaO *(thioamide/thiopeptide reading of YcaO; cf. azole catalog below)* | **antibacterial** thioamitides/thiopeptides |
| **T43-DKP** diketopiperazine | cyclodipeptide synthase (CDPS), diketopiperazine | DKP natural products |
| **T43-IDC** indolocarbazole | indolocarbazole, rebeccamycin, staurosporine | indolocarbazoles |
| **T43-TET** tetronate | tetronate, spirotetronate, fkbH | (spiro)tetronates |
| **T43-PYE** polyene macrolide | polyene-macrolide / polyene-antifungal tokens, named polyenes including natamycin and nystatin; arylpolyene exclusion in the generic polyene tokens | polyene-macrolide class routing; AF diagnostic requires its corroboration gates |
| **T43-GPA** glycopeptide | OxyB/OxyA/OxyC, DPGS, hydroxyphenylglycine machinery, glycopeptide and named-class tokens | glycopeptide class routing; AB diagnostic requires its corroboration gates |
| **T43-BLT** betalactone | betalactone / beta-lactone and the named tokens listed in the engine dictionary | betalactone class routing; a token match does not identify the product or validate every named-token association |

These added rows describe executable detection and routing rules, not independently validated biological assignments. In particular, named-compound tokens are search signatures rather than proof of a scaffold. Consult the exact dictionary and the separate scoring/architecture corroboration gates before interpreting a match. The polyene corroboration minimum is four KS domains where that gate applies; a pattern firing alone does not earn the diagnostic bonus.

**Not CCTT trigger families (don't confuse with the eighteen above).** Three names share the `T43-`/detection
namespace but are *not* `CCTT_PATTERNS` keys, so they are **<span class="tag t-concept">\[concept\]</span>/<span class="tag t-engine">\[engine: other scan\]</span>**, not trigger rows:
the azole-RiPP **TOMM** markers (YcaO/cyclodehydratase) ride along as HMM-only *catalog* and do not fire as a
pattern trigger (azole detection overlaps the THA YcaO reading); **LMPKS** is the large-modular-PKS megasynthase
grade emitted by the **FLBR census** (→ §II.6), not a trigger; and **SILENT** is the no-anchor/no-known-product
*flag* (an absence, → §IV.10's cryptic-cluster signal), not a signature. Earlier drafts of this volume wrongly
listed these three as families, miscounted the set as "seventeen," and demoted the real T43-NN to a footnote —
all corrected here.

**Per-family notes (the class chemistry each trigger corroborates).** Concise, claim-safe class facts; the engine
detects the *signature*, the chemistry below is the established class biology. <span class="tag t-science">\[science\]</span>

- **T43-LAN** lanthipeptides — RiPPs bearing thioether (lanthionine) crosslinks installed by LanB/LanC or LanM;
  many are antibacterial (the nisin family is the textbook case). Precursor + cyclase are the completeness markers.
- **T43-LASSO** lasso peptides — RiPPs with a threaded "lariat-knot" topology (an isopeptide-bonded macrolactam
  ring through which the C-terminal tail is threaded); often protease- and heat-stable.
- **T43-THA** thioamitides / thiopeptides — RiPPs carrying a thioamide (C=S for C=O) installed via a YcaO; the
  thiopeptide sub-class is potently antibacterial against Gram-positives.
- **T43-TOMM** (catalog) thiazole/oxazole-modified microcins — azoline/azole heterocycles formed by a YcaO
  cyclodehydratase; the THA and TOMM readings of a YcaO are distinguished by their downstream chemistry.
- **T43-PHO** phosphonates — C–P-bond natural products built from phosphoenolpyruvate by **PEP-mutase** (the
  committed, irreversible first step), then aepY/Ppd; biosynthesis is mechanistically distinct from the catabolic
  *phn*/C–P-lyase machinery the trigger excludes. Fosfomycin and dehydrophos are antibacterial members.
- **T43-NUC** peptidyl-nucleoside antibiotics — nikkomycin and polyoxin are nucleoside-peptide hybrids that
  inhibit fungal **chitin synthase**; an antifungal class with no mammalian target (chitin is absent in mammals).
- **T43-PTM** polycyclic tetramate macrolactams — HSAF (heat-stable antifungal factor), maltophilin; a tetramate
  iPKS/NRPS hybrid family with antifungal activity.
- **T43-BLA** β-lactams — nocardicins (monocyclic) and the penicillin/cephalosporin route via isopenicillin-N
  synthase (pcbAB/pcbC); cell-wall (transpeptidase) targeting.
- **T43-AMC** aminoglycosides / aminocyclitols — built from 2-deoxy-*scyllo*-inosose (DOIS-initiated); ribosome
  (30S) targeting antibacterials (kanamycin, gentamicin).
- **T43-ENE** enediynes — a (9- or 10-membered) enediyne core that undergoes Bergman cyclization to a diradical
  that cleaves DNA; among the most cytotoxic natural products (calicheamicin) — hence the `[E-signal]` claim-safety
  routing (§I.6), not a per-cluster lab-safety flag.
- **T43-IDC** indolocarbazoles — staurosporine / rebeccamycin scaffolds; protein-kinase and topoisomerase
  inhibitors. Class capacity is supported by a constellation of tryptophan-derived core-forming genes — the
  rebeccamycin/staurosporine `reb`/`sta` family (e.g. `rebO/rebD/rebC/rebP/rebH`, MIBiG BGC0000821); report the
  observed gene names explicitly rather than relying on a generic marker label.
- **T43-DKP** diketopiperazines — cyclodipeptides made by tRNA-dependent cyclodipeptide synthases (CDPS).
- **T43-TET** (spiro)tetronates — polyketides bearing a tetronate (and often a spiro center), e.g. chlorothricin /
  the abyssomicin family.
- **T43-HAL / T43-XHAL** halogenation — flavin-dependent (Cl/Br) and the rarer SAM-dependent fluorinase/chlorinase
  (C–F/C–Cl); a *tailoring modification* found across many unrelated classes, which is why both are Promiscuous and
  floor-excluded (§V.2).
- **T43-NN** N–N-bond chemistry — diazo, azoxy, hydrazine, and related N–N linkages (cremeomycin, valanimycin);
  a rare, reactive functionalization, also Promiscuous. In cremeomycin the CreE/CreD-like genes generate the
  nitrous-acid input, while the ATP-dependent CreM installs the diazo group — so a complete diazo-capacity call
  should look for the downstream diazo-forming context, not read CreE/CreD alone as installing the N–N bond.

*Marker citations (Literature Pass 3, verified DOIs/PMIDs).* T43-HAL flavin-dependent halogenases: van Pée & Patallo 2006, *Appl. Microbiol. Biotechnol.* **70**, 631–641 (DOI 10.1007/s00253-005-0232-2; PMID 16544142) — a halogenase alone is tailoring/capacity evidence, never proof of a halogenated product. T43-XHAL SAM-dependent halogenases: Eustáquio et al. 2008, *Nat. Chem. Biol.* **4**, 69–74 (DOI 10.1038/nchembio.2007.56; PMID 18059261, SalL-like chlorinase) and Dong et al. 2004, *Nature* **427**, 561–565 (DOI 10.1038/nature02280; PMID 14765200, FlA-like fluorinase) — mechanistically distinct from flavin-dependent T43-HAL. T43-AMC aminocyclitol/DOIS: Kudo & Eguchi 2009, *J. Antibiot.* **62**, 471–481 (DOI 10.1038/ja.2009.76) and Kudo et al. 1999, *J. Antibiot.* **52**, 81–88 — a DOIS/2-deoxy-scyllo-inosose-synthase marker supports aminocyclitol capacity only in a compatible aminoglycoside gene context. T43-TET tetronate/FkbH: Sun et al. 2008, *ChemBioChem* **9**, 150–156 (DOI 10.1002/cbic.200700492; PMID 18046685) and Vieweg et al. 2014, *Nat. Prod. Rep.* **31**, 1554–1584 (DOI 10.1039/C4NP00015C) — FkbH-family glyceryl-transfer + dedicated ACP context, paired with a compatible polyketide architecture. T43-NN diazo: Sugai et al. 2016, *Nat. Chem. Biol.* **12**, 73–75 (DOI 10.1038/nchembio.1991; PMID 26689788) and Waldman et al. 2015/2018 (DOI 10.1002/cbic.201500407; 10.1021/acs.joc.8b00367, PMID 29771512). T43-IDC indolocarbazoles: Sánchez et al. 2002, *Chem. Biol.* **9**, 519–531 (DOI 10.1016/S1074-5521(02)00126-6; PMID 11983340), Onaka et al. 2002, *J. Antibiot.* **55**, 1063–1071 (DOI 10.7164/antibiotics.55.1063; PMID 12617516), Nakano & Ōmura 2009, *J. Antibiot.* **62**, 17–26 (DOI 10.1038/ja.2008.4; PMID 19132059). All carry the standing claim ceiling: marker constellation = class capacity, never final-product identity.

## §IV.4 · RG-GMCI — reference-guided gapped multi-contig integration

A fragmented assembly splits a real pathway across contigs (→ §II.2, §II.6). **RG-GMCI** is the engine's
reconstruction adjudicator: using a shared **ClusterBlast** reference (§IV.1) as a scaffold, it asks whether two
fragments on different contigs are **complementary tiles** of one cluster — covering different, non-overlapping
parts of the same reference — and if so proposes them as one candidate pathway unit. The verdict is graded
`HIGH_RG_GMCI_RESCUE` or `MODERATE_RG_GMCI_CANDIDATE`, and a rescued region gains a scoring bonus with a reduced
boundary/confidence handling (→ §III.3). <span class="tag t-engine">\[engine\]</span>

Critically, RG-GMCI carries a **claim ceiling**: a reconstruction is a *homology-guided hypothesis*, never an
asserted assembled cluster. The two-level architecture rule (→ §III.5) applies — an anchor fragment keeps its own
grade, while the integrated pathway-unit label is graded more cautiously. The engine reconstructs to avoid
*undercounting* a split megasynthase, while never *overclaiming* the reassembled whole as fact. <span class="tag t-engine">\[engine/concept\]</span>

### §IV.4.1 · No subject coordinates — the locus-number proxy **\[v9.7.39\]**

The reconstruction needs to know *where on the reference* each fragment sits, to ask whether two fragments tile
**different** parts of it. But the clusterblast TXT format the engine parses does not carry subject gene
coordinates — the subject location table is empty in this format — so adjacency cannot be measured in base pairs.
The engine falls back to subject **locus-tag numbers** as a coarse position estimate, tagged
`adjacency_basis = LOCUS_PROXY` so it is never mistaken for a coordinate claim (`adjacency_basis ∈ {COORDINATE, LOCUS_PROXY, NONE}`, rggmci.py). The proxy is **prefix-aware**: it compares locus numbers only within a shared
locus-tag namespace, so two references from different reference genomes are never spuriously called adjacent on
raw number alone. A 5-strain internal calibration found `COORDINATE` basis = 0 on **every** strain — including a
MODERATE-tier assembly — establishing that the missing-coordinates condition is a property of the TXT format, not
of the query assembly's quality. <span class="tag t-engine">\[engine\]</span>

A narrow parser hazard here, fixed in **v9.7.40**: a Blast-hits `%coverage` decimal such as `101.5625` was briefly
misread as a coordinate span `(101, 5625)`, fabricating a phantom `COORDINATE` interval that promoted a handful of
pairs to HIGH (only when coverage ≥ 100%, a coincidence). The fix excludes Blast-hits rows from interval scanning
and accepts only genuine hyphen / GenBank-`..` ranges, so real coordinates — on the rare reference that has them —
still parse. <span class="tag t-engine">\[engine\]</span>

A second, deeper hazard in the same locus-tag path was found in the v9.7.43 full-pipeline shake-down and is
worth teaching as a **worked failure mode**, because its signature is silent. RG-GMCI's `_blast_hits` parser
originally accepted a query gene only if its identifier began with `ctg` — the internal antiSMASH naming the engine
sees on its *own* loose-mode assemblies. But a public WGS genome downloaded from GenBank names its genes by
**locus tag** (e.g. `GTY48_01375`), not `ctg…`. On such a genome every Blast-hits row was dropped at the gate, so
the reconstruction saw **zero subjects, zero identity**, every pair's `adjacency_basis` collapsed to `NONE`, and the
ceiling was silently forced to MODERATE — not through any honest demotion but because the evidence never entered the
function. The output looked plausible (a MODERATE ceiling is unremarkable), which is exactly what made it dangerous.
The tell is in the run's RG-GMCI summary line: **`adjacency basis 0/0/N`** (zero COORDINATE, zero LOCUS_PROXY, N
NONE) on a genome that clearly has biosynthetic neighborhoods is the fingerprint of this class of bug — the engine
found regions but extracted no adjacency evidence from any of them. The fix (v9.7.43) gates on the **6-column row
structure** of a Blast-hits line rather than on the `ctg` prefix, so locus-tag-named queries parse identically to
`ctg`-named ones. After the fix the same public strain went from `0/0/711` to `LOCUS_PROXY 688 / identity 688 / HIGH`;
internal loose-mode (AS) strains, which always named genes `ctg…`, were unchanged — confirming the fix only opened a
path that had been wrongly closed. The general lesson: when a public-genome run shows an all-`NONE` adjacency basis,
suspect a naming-convention gate before trusting the MODERATE ceiling. <span class="tag t-engine">\[engine: v9.7.43 shake-down\]</span>

### §IV.4.2 · Adjacency geometry and the good-geometry count <span class="tag t-engine">\[engine\]</span>

For each shared reference, the pair's two fragments are classified by how their reference segments relate:
`OVERLAPPING_REFERENCE_SEGMENTS`, `ADJACENT_OR_NEARBY_REFERENCE_SEGMENTS`, or `DISTANT_ON_REFERENCE_CAUTION`. A
reference counts toward the pair's `good_geometry_references` only if it is **overlapping or adjacent** — distant
co-occurrence does not. `ADJACENT` requires the locus gap ≤ `ADJ_MAX_LOCUS_GAP` (**30**) and the spanned range ≤
`ADJ_MAX_SPAN` (**400**). Both constants were set from the 5-strain calibration: genuine adjacency clusters at gap
≈ 0 (median 0 on all five strains; gap ≤ 30 retains ~95% of adjacent pairs), and the maximum real adjacent span
observed was 315–400, so the span cap sits exactly at the top of the genuine distribution. <span class="tag t-engine">\[engine\]</span>

### §IV.4.3 · Two acceptance gates for HIGH **\[v9.7.74\]**

A pair reaching `HIGH_RG_GMCI_RESCUE` must clear more than a count of shared references — convergence alone was the
top over-promotion the calibration exposed. Two demote-only gates apply, in order:

1.  **Geometry gate — `good_geometry_references ≥ 2`.** The calibration found that 50–76% of HIGH pairs on *every*
    strain rode on a **single** good-geometry reference. A lone coarse-proxy adjacency is too weak for HIGH, so a
    pair with fewer than two good-geometry references is demoted `HIGH → MODERATE` (and, with no geometry and no
    cross-scaffold split signal, on to `LOW`). <span class="tag t-engine">\[engine\]</span>
2.  **Product-class gate.** HIGH additionally requires a **specific shared product class** or a **known compatible
    hybrid** (PKS+NRPS and the like), evaluated *after* excluding `other`, saccharide, and NAPAA tokens and the
    generic RiPP umbrella; two **distinct** RiPP subclasses are treated as different terminal machineries and
    blocked. This catches the residue the geometry gate misses — pairs that reach `gg ≥ 2` yet whose only shared
    "product" is a permanent-exclusion token (the clearest case: a both-Interior pair whose single shared token is
    NAPAA, which the standing rules already downgrade). Like the geometry gate it only ever **demotes**, never
    promotes. <span class="tag t-engine">\[engine\]</span>

The net effect on a real POOR assembly was a tightening of HIGH from 29 to 4 candidates, with the genuine
both-Edge split leads (a shared-class T1PKS+T1PKS pair carried by 21 references; a shared-NRPS pair by 24) retained
and the NAPAA-only both-Interior co-occurrence correctly demoted. <span class="tag t-engine">\[engine: real run\]</span>

On a poor assembly the dominant *failure* mode is hub promiscuity: one large multidomain contig tiles
"complementarily" with many partners, so the raw candidate set can be large while the family-concordant set is
empty (on a real VERY_POOR public assembly, 326 rescue candidates → 0 family-concordant). The two HIGH gates above
attack this directly — a promiscuous hub rarely clears both ≥2 real adjacency geometry and product-class
compatibility — but the concordance gate remains what makes 0-concordant the honest output; note there is **no
false-discovery-rate estimate** for the raw candidate set, and a promiscuous hub should be flagged by its component
degree rather than read as 326 real links. <span class="tag t-engine">\[engine: observed on a public VERY_POOR genome\]</span>

### §IV.4.4 · Hub-degree guard and the co-cluster exemption **\[v9.7.42\]**

The hub-promiscuity problem above is now metered, not merely described. v9.7.42 added a **hub-degree guard**: each
candidate endpoint carries a `max_endpoint_hub_degree` field, and a pair is blocked from HIGH when an endpoint's
component degree exceeds `RGGMCI_MAX_HUB_DEGREE` (**4**). A contig that tiles "complementarily" with five or more
partners is, by construction, a promiscuous hub rather than the unique other half of a split pathway, so the guard
demotes it before it can inflate the HIGH set. A companion field, `mibig_good_geometry_references`, records the
good-geometry reference list explicitly so the geometry gate's input is auditable rather than implicit. <span class="tag t-engine">\[engine\]</span>

The same release added a **co-cluster exemption**: when two fragments are not cross-contig partners at all but two
protoclusters genuinely co-located *within one contig* (a real biological co-cluster, not an assembly artifact), the
adjacency machinery should not treat them as a fragmented-pathway rescue. The exemption recognizes the in-contig
co-cluster case and routes it away from the cross-contig HIGH gates, so a legitimate co-cluster is neither rescued as
a phantom split nor penalized by the hub-degree guard meant for cross-contig hubs. <span class="tag t-concept">\[concept\]</span>

Two narrow keying bugs were fixed alongside the guard. **Bug A:** the MIBiG reference index was keyed through an
`ACCESSION_RE` that mis-parsed certain accession forms, so a subset of MIBiG references silently failed to match and
dropped out of the good-geometry count — making some pairs look weaker than their evidence warranted. **Bug B:** a
locus identifier carrying a **version suffix** (e.g. `…_1`) was treated as a distinct namespace from its unversioned
twin, splitting what should have been one locus-tag namespace in two; a paired `diagnostic_rescue` twin had the same
suffix-sensitivity. Both were normalization gaps — the fix strips the version suffix and unifies the accession key —
and both are the kind of silent under-count that the `mibig_good_geometry_references` audit field now makes visible.
<span class="tag t-engine">\[engine\]</span>

*Grounded against bundle v9.7.74 / engine Mamey 1.9.81, constants re-verified unchanged at v9.7.91 (gap 30 / span 400 / hub-degree 4): the v9.7.38 adjacency guard, v9.7.39
locus-number proxy + identity axis, v9.7.40 phantom-coordinate fix, v9.7.74 gg≥2 + product-class gates, v9.7.42
hub-degree guard + co-cluster exemption + Bug A/B keying fixes, and the v9.7.43 `_blast_hits` locus-tag fix (§IV.4)
are all shipped.*

### §IV.4.5 · The rescue overhaul — full ClusterBlast utilisation and the terminus-truncation path **\[v9.7.100\]**

Through v9.7.99 the rescue layer leaned on KnownClusterBlast alone and discarded most of the ClusterBlast
evidence — which meant a fragment with real cross-genome neighbours but no characterised MIBiG match could be
invisible to a rescue. v9.7.100 reworks the layer along four lines, all of which surface as new fields on the
`*_4A_RGGMCI_ranked_pairs.csv` output.

- **Database-of-origin separation (`db_kind`).** The ClusterBlast TXT filter previously
  blind-merged knownclusterblast, clusterblast, *and* subclusterblast, because the substring "clusterblast"
  matches all three. Each reference is now tagged: `knownclusterblast` (characterised MIBiG cluster),
  `clusterblast` (cross-genome GenBank neighbour), `subclusterblast` (sub-operon — *excluded*
  from cluster geometry). Same distinction the parse layer calls `source_kind` (§IV.1). <span class="tag t-engine">\[engine\]</span>
- **Evidence base (`rescue_evidence_base`).** Each pair records whether it is corroborated
  by BOTH_KCB_AND_CB, CLUSTERBLAST_ONLY, or KNOWNCLUSTERBLAST_ONLY. On a representative POOR wasp assembly, 341 of
  402 pairs were CLUSTERBLAST_ONLY — every one of which a KnownClusterBlast-only path would have missed. Observational;
  it does not by itself move the score.
- **Functional complementarity (`functional_rescue_class`).** Each fragment's gene roles
  (core / tailoring / transport / regulatory, from `gene_kind` + sec_met) are profiled, and the pair is
  classed by *core-fraction asymmetry*: COMPLEMENTARY (one fragment core-bearing, the other accessory-dominated —
  a real split), BOTH_CORE (both core-rich — paralogous clusters, not a split), or ACCESSORY_ONLY. A cross-check on the
  subject-tiling verdict, not a standalone call. (The first implementation mislabelled every pair BOTH_CORE because every
  called BGC trivially has a core gene; the fix was to compare core *fractions*, not core presence.)
- **Terminus-truncation rescue (`TERMINUS_TRUNCATION_SPLIT`).** The simplest, most certain
  rescue is physical, not homological: an Edge region whose boundary sits at the contig terminus is a cluster sliced by
  the assembly break. When such a region is paired with a small (≤25 kb) complete-contig severed arm, or shares a
  *specific* biosynthetic class, the pair is flagged a terminus-truncation split and *overrides* an
  OVERLAPPING_PARALOG subject-tiling verdict — because that verdict can be an artefact of a gene class that is
  legitimately multi-copy *within one* cluster (the canonical case is the bottromycin RRE/methyltransferase, which
  appears once on each severed fragment and looks like paralogy to the tiling logic). The override is conservative: it
  flips a paralog verdict and promotes a weak verdict only on genuine severed-arm geometry, and it leaves true paralogs
  (two core-complete fragments on different contigs, neither terminus-truncated) untouched. <span class="tag t-engine">\[engine\]</span>

All four remain **candidate inference, not nucleotide-level contig joining**. A small severed-arm contig
can be the arm of only one cluster, so where it pairs with several Edge regions the evidence base and functional class
disambiguate which partner is real; physical confirmation still requires long-read sequencing or gap-PCR across the
junction. This is the same claim-safety stance the rest of RG-GMCI takes — a rescue raises a linkage *hypothesis*
and routing priority, never an assembly claim. → Glossary "RG-GMCI rescue layer"; → User Manual §9.2. <span class="tag t-engine">\[engine\]</span>

## §IV.5 · CGAD — chitinase / glycan-active-domain scan

**CGAD** is a proteome-wide scan for chitin-active machinery — glycoside hydrolase families GH18 and GH19, AA10
LPMOs, and chitin-binding modules. Its relevance is ecological and biomedical: chitin is the fungal cell wall and
the arthropod exoskeleton, so chitin-degrading capacity bears on antifungal mechanism and on insect-association
ecology (→ §I.4). CGAD is a context channel — it informs the antifungal reading of a strain (and couples to the
T43-NUC chitin-synthase-inhibitor diagnostic) without, on its own, asserting antifungal activity. <span class="tag t-engine">\[engine/science\]</span>

The marker families CGAD reads, and what each one means: <span class="tag t-science">\[science\]</span>

1.  **GH18 chitinases**: the largest and most common bacterial chitinase family, a TIM-barrel fold that hydrolyses the β-1,4 bond of chitin. GH18 enzymes in actinomycetes are often secreted and multi-modular, and their presence is the baseline chitinolytic signal.
2.  **GH19 chitinases**: a structurally unrelated, lysozyme-like fold more typical of plants and *Streptomyces*: a GH19 hit in a bacterial proteome is a stronger ecological signal because it is comparatively concentrated in chitin-degrading actinomycetes.
3.  **AA10 LPMOs (lytic polysaccharide monooxygenases)**: oxidative, copper-dependent enzymes that cleave crystalline chitin where hydrolases stall. An AA10 hit alongside GH18/GH19 signals a *complete* degradation toolkit: oxidative attack on the crystalline regions plus hydrolytic processing of the released chains.
4.  **Chitin-binding modules (CBMs, e.g. CBM5/CBM12)**: non-catalytic accessory domains that anchor an enzyme to its substrate. They do not cleave chitin but raise the on-substrate residence time of the catalytic domains, so their co-occurrence is corroborating context rather than an independent signal.

*Citations (Literature Pass 3, verified):* AA10 / chitin-active LPMOs — Courtade & Aachmann 2019, *Adv. Exp. Med. Biol.* **1142**, 115–129 (DOI 10.1007/978-981-13-7318-3_6; PMID 31102244); an LPMO annotation supports chitin-active oxidative-enzyme *capacity*, not antifungal activity by itself. CBMs — Boraston et al. 2004, *Biochem. J.* **382**, 769–781 (DOI 10.1042/BJ20040892; PMID 15214846) and Shoseyov et al. 2006, *Microbiol. Mol. Biol. Rev.* **70**, 283–295 (DOI 10.1128/MMBR.00028-05); CBMs support substrate-localization context for glycan-active enzymes and are not catalytic, so they are never alone proof of chitinase, glucanase, or antifungal activity.

A worked reading: a strain whose proteome carries GH18 + GH19 + AA10 together has the biosynthetic capacity for a full chitinolytic program, which is a coherent *antifungal* and *insect-degradation* context for interpreting its secondary metabolome. The claim stays at capacity: CGAD reports machinery, never demonstrated antifungal activity, and the standing bioactivity default still governs (extract-level MRSA + *Candida*, → §I.3). What CGAD changes is the *prior* with which the judgment layer reads an antifungal-class BGC in the same strain: a spirotetronate or polyene cluster in a chitinolytic background is a more ecologically coherent antifungal lead than the same cluster in a strain with no chitin machinery.

## §IV.6 · UMED — maturation / tailoring-enzyme detection

**UMED** detects the **maturation and tailoring enzymes** that convert a core biosynthetic scaffold into a
finished product — the dehydratases, cyclases, oxidoreductases, and class-specific modifiers that a *complete*
pathway needs. Its job is completeness evidence: a core gene with its maturation set present is a more credible
complete cluster than a bare core, and a RiPP core captured without its maturation/precursor context is flagged
as a fragment (the RiPP-fragment cap, → §III.4). UMED is keyed to the families that require maturation (RiPP,
lanthipeptide, lasso, thioamide, azole, nucleoside). <span class="tag t-engine">\[engine\]</span>

The maturation logic is class-specific, because each class is *defined* by the modifications that build it.
What "complete" means, family by family: <span class="tag t-cand">\[science: candidate — Pass-2 pending\]</span>

1.  **Lanthipeptide**: the precursor peptide plus the dehydratase that installs dehydro-residues and the **LanC/LanM cyclase** that forms the thioether (lanthionine) ring. The cyclase is the class-defining enzyme: a lanthipeptide *label* with no LanC/LanM in-region is precisely the impostor signature that the corroboration guard must catch (→ §IV.8, §V.4).
2.  **Lasso peptide**: the precursor plus the cyclase/isopeptidase pair that ties the threaded lariat knot. Without the maturation pair, a captured precursor is a fragment, not a producible lasso.
3.  **Thioamide-containing RiPP**: the **YcaO** enzyme that, with a partner, installs the thioamide bond (the T43-THA diagnostic, → §IV.3). The YcaO signature is what lets a thioamidated RiPP be called with confidence.
4.  **Azol(in)e RiPP**: the heterocyclase/dehydrogenase set that cyclises Cys/Ser/Thr into thiazol(in)es and oxazol(in)es. These tailoring enzymes are the difference between a linear precursor and a heterocyclic natural product.
5.  **Nucleoside**: the tailoring enzymes that decorate a nucleoside core, relevant to the T43-NUC antifungal diagnostic and to the chitin-synthase-inhibitor reading (→ §IV.5).

The worked principle: UMED never *upgrades* a cluster on its own, it *qualifies completeness*. A bare core with no maturation set is read as a capacity floor; a core with its full maturation complement is a credible complete pathway; and a sub-threshold RiPP core with no precursor or maturation context is capped at Inventory regardless of how its keyword score lands (the RIPP-FRAGMENT-FLOOR, → §III.4). This is the completeness counterpart to the corroboration gate: corroboration asks *is the class signal real*, UMED asks *is the pathway whole*.

## §IV.7 · EFLS — cross-contig shared-evidence linkage

**EFLS** is the second cross-contig integrator, complementary to RG-GMCI's reference-guided rescue. Where RG-GMCI
leans on a ClusterBlast reference, EFLS links fragments by the **evidence they share directly** — common
cassettes, common CCTT triggers, common FLBR megasynthase signal across contigs. Two fragments that carry the
same diagnostic cassette are candidate pieces of one locus even without a clean reference scaffold. EFLS and
RG-GMCI together let the judgment layer treat a set of fragments as one candidate pathway from two independent
angles, each under the same reconstruction claim ceiling (§IV.4). <span class="tag t-engine">\[engine\]</span>

The evidence EFLS links on, in decreasing strength: <span class="tag t-engine">\[engine\]</span>

1.  **Shared diagnostic cassette**: two contig fragments that both carry the same diagnostic accessory cassette (a tailoring set, a regulator/transporter pair characteristic of one class) are the strongest direct-evidence pairing, because the cassette is class-specific rather than generic.
2.  **Shared CCTT trigger**: two fragments that both fire the same T43 trigger may be two halves of one trigger-bearing pathway. This is weaker than a shared cassette, because a trigger can recur independently.
3.  **Shared FLBR megasynthase signal**: when the megasynthase ketosynthase census (→ §II.6) finds compatible PKS/NRPS fragments on different contigs, EFLS proposes them as a split megasynthase, the cross-contig case the FLBR scan exists to surface.

A worked example of the shape (illustrative): a fragmented assembly leaves a partial NRPS adenylation module on contig 14 and a partial condensation/thioesterase module on contig 51, and both fragments carry the same diagnostic tailoring cassette. RG-GMCI may miss the pairing if no single reference cluster spans both fragments, but EFLS links them on the shared cassette, and the judgment layer can then read them as one candidate NRPS pathway. The critical discipline is the **claim ceiling**: a EFLS-linked pathway is reported as a *candidate reconstruction*, never as a confirmed contiguous cluster. The linkage raises a hypothesis for wet-lab confirmation (long-read resequencing, targeted PCR across the proposed junction), it does not assert that the contigs are physically adjacent. A cross-contig rescue is a lead about where to look, calibrated as such (→ §IV.4).

## §IV.8 · The resistance screen and the HGT guard

The **resistance screen** tiers source-derived self-protection signals proximal to each cluster, because a
producing cluster often encodes resistance to its own product (→ §IV cross-ref to resistance-gene-guided mining).
The tiers (→ §II.3): **T1** diagnostic self-protection (a class-specific resistance determinant — Erm methylase,
VanHAX-like, APH/AAC, fosfomycin) class-concordant with the product; **T2** resistance-like (generic folds); **T3**
transporter-only (use for extraction/polarity routing, not mechanism). A class-concordant T1 hit is a
high-confidence self-resistance signal and contributes to the Tier-1 diagnostic floor (→ §III.4). The screen
carries vetoes — an APH/AAC in a sugar-kinase/glycogen context is a kinase, not a resistance determinant. <span class="tag t-engine">\[engine\]</span>

The same screen carries the **HGT guard** — the gene-level mobile-element detector of the \#28 fix (→ §II.3, §III.6).
It scans CDS annotations for mobility families (integrase, recombinase, transposase as the core; conjugation,
toxin-repeat, replication-initiator as accessory) and marks a region **mobile-dominant** when a core mobility gene
is present with ≥1 further family, or ≥3 families total. The scoring layer then demotes a mobile-dominant region
that is not independently class-typed (the CCTT-veto, → §III.6) — an integrative element mis-typed as a
biosynthetic class is not a discovery lead. <span class="tag t-engine">\[engine: detection + demotion logic\]</span>

**Real-data status (this edition).** The demotion is logic-complete and fixture-verified, and its *specificity*
holds on real public genomes: no genuine lead is lost, and a corroborated mobile-dominant RiPP is correctly
exempted. Its positive path was the subject of a two-axis fix. On the public genome `NZ_CP029601.1`, BGC032 is
correctly detected as mobile-dominant (five mobility families) but originally was not demoted: it topped the AB
track at 82.0 over the genuine flagship at 65.0, because it carried a `T43-LAN` trigger the corroboration guard
never marked uncorroborated (the locus is an ICE with no lanthipeptide cyclase/precursor), so the CCTT-veto was
satisfied by a false class signal. The two guards did not compose: an uncorroborated trigger the corroboration
guard missed became the veto that shielded the impostor. **The class-trigger half shipped in v9.7.35** (#28): the
corroboration guard now marks a class trigger uncorroborated when the region is mobile-dominant and the class's
defining enzyme is absent (`architecture_class_confidence == LOW`), dropping BGC032 from rank-1. **The
resistance-trigger half is PC-12** (shipped v9.7.37): a second `tier1_diag` source, a non-class-concordant T1 self-protection tier
(`APH_AAC` against a lanthipeptide product), independently shielded the region until gated on
`class_concordant_groups` (→ §V.4 for the full label-vs-domain treatment). The lesson the arc encodes: a guard that
consults a single shared flag composes only as well as every signal that can set that flag. <span class="tag t-engine">\[engine: verified
against NZ_CP029601.1; class-axis fix shipped v9.7.35, resistance-axis fix in the patch chat\]</span>

## §IV.9 · bldA / TTA-codon dependence

**bldA/TTA** flags the **TTA codon** in a cluster's genes. In actinomycetes the leucyl-tRNA that reads TTA is
encoded by **bldA** and is developmentally regulated, so TTA-containing genes — disproportionately
secondary-metabolism and morphological-development genes — are translated mainly in the appropriate growth phase.
A TTA codon in a biosynthetic gene is therefore a signal about *when and whether* a cluster is expressed: a
regulatory dependence worth knowing before interpreting silence as absence (→ §I.3, absence is not negative). The
scan tiers clusters by their TTA dependence. <span class="tag t-engine">\[engine/science\]</span>

Why TTA is informative, and why it is taxon-specific: <span class="tag t-cand">\[science: candidate — Pass-2 pending\]</span>

TTA is the rarest codon in the GC-rich actinomycete genome, and *Streptomyces* couples its translation to the bldA tRNA, whose own expression rises as the colony enters stationary phase and aerial differentiation. The result is a built-in timer: a biosynthetic gene that carries a TTA codon is gated to the developmental window when bldA is abundant, which is the same window in which many secondary metabolites are produced. A cluster with TTA codons in its core or regulatory genes is one whose silence under standard growth may be a *timing* phenomenon rather than an absence of capacity, which is exactly the kind of cluster that rewards an elicitation strategy (altered media, co-culture, late-harvest) at the bench.

This is why the scan is **taxonomy-gated** — though the gate is coarser than the biology, and the difference matters. The bldA/TTA developmental coupling is a property of *Streptomyces* and close relatives, not of bacteria in general. The engine's gate, however, keys on **actinomycete vs non-actinomycete** (`actino_status` against the `NON_ACTINO_GENERA` set, → §IX.5c), *not* on *Streptomyces* vs non-*Streptomyces*. A recognised non-actinomycete reports **NOT_APPLICABLE** with the taxonomy reason rather than a misleading **NULL** — so a reader never mistakes "not applicable" for "bldA-independent," and the distinction is the clearest worked example of the engine's honest-incompleteness vocabulary (→ §II.3). But a non-*Streptomyces* *actinomycete* — *Nocardia*, *Pseudonocardia*, *Actinomadura* — **runs the scan and is tiered**: a real *Nocardia fluminea* run at v9.7.91 reports `bldA_TTA: PASS — 48 BGCs assessed; 16 T4`, even though the bldA developmental system is not established outside the *Streptomyces* clade. So the current gate **over-applies** bldA to all actinomycetes; tightening it to *Streptomyces*-and-close-relatives (and deriving the kingdom/clade from the GBK source-organism lineage rather than a genus list, → §IX.5c) is a recorded refinement. Where the scan does apply, the tiering ranks clusters by TTA load (a T4 tier marks the heaviest TTA dependence), feeding the judgment layer's **isolation strategy** section: a high-TTA lead carries an explicit "expect developmental gating; plan elicitation" note rather than being read as a failed expression. **\[observed: *Nocardia* run; engine gate = `actino_status` non-actinomycete only\]**

## §IV.10 · TFBS — transcription-factor binding-site scan

**TFBS** scans the region **upstream** of clusters for transcription-factor binding-site signal — a regulatory
read on how a cluster may be controlled. Like bldA/TTA, it is a *regulation* channel, not a biosynthesis
diagnostic: it does not corroborate class capacity, but it informs the expression/activation picture (which
regulators may gate a cluster, relevant to why a cluster might be cryptic or silent — and to the silent/cryptic-cluster flag — a no-anchor scan output, not a T43 trigger).
It is one of the ten First-Pass Scans (→ §II.3) and feeds the judgment layer's context, not the AB/AF score. <span class="tag t-engine">\[engine\]</span>

The grounded mechanics: TFBS reads a fixed **300 bp** window upstream of each cluster's genes (`scan_tfbs(upstream_bp=300)`, → §VII.7 for the tunable) and counts simple regulator-motif matches, reporting a status of `MOTIF_SCAN_PRELIMINARY` with the hit counts. The engine attaches its own claim-safety caveat to the channel: this is a simple motif scan, to be replaced with calibrated TFBS models and background scoring before any manuscript use. That self-caveat is deliberate and load-bearing: a raw motif count is suggestive context, not a validated regulatory call, and the channel says so rather than letting a reader over-read it. <span class="tag t-engine">\[engine\]</span>

What TFBS is *for*, concretely: it contributes to the reading of a **cryptic or silent cluster**. A high-capacity BGC that shows no recorded activity is the central puzzle of genome-mining, and the honest interpretation is rarely "the cluster does nothing" (→ §I.3, absence is not negative). TFBS, alongside bldA/TTA, populates the alternative: the cluster may be *transcriptionally gated*, awaiting a regulator or condition that standard growth does not supply. A cluster with a dense upstream regulator-motif signal carries a context note in the judgment layer's isolation section — a candidate handle for *elicitation* (manipulate the implicated regulator, screen inducing conditions) rather than a verdict of inactivity. The discipline is the same one that governs the whole regulation tier: TFBS tells you *where a cluster's expression might be controlled*, never *that the cluster is or is not active*.

------------------------------------------------------------------------

*End of Volume IV. Remaining: Volume V — Scoring, Ranking & DAPR (seeded by the other chat's guards draft, → the
consolidation note); Volume VII — Operations, Release & Provenance; Volume VIII — Reference & Apparatus. Grounded
in the running engine of its edition before it ships.*

</div>

<div id="vol5" class="section vol">
