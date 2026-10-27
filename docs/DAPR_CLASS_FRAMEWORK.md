# DAPR Class → Activity Framework (Sapote scoring vocabulary)

Vocabulary for DAPR (antibacterial / antifungal) judgment: which compound classes are usually linked with which activity. Use it to name a class-level hypothesis. It does not score a locus or show that a strain makes a compound. **All calls are class-level hypotheses; optional typed strain-level bioactivity metadata is
the project default. Never an isolation or per-BGC activity claim.**

> **Historical 18-strain verification statement (requires its original supporting evidence):** the class→activity associations used on the 18-strain
> cohort are **literature-verified** — antibacterial (carbapenem MM4550, clavulanate, A54145, teicoplanin,
> formicamycin, surugamide, glycinocin), antifungal polyenes (filipin, candicidin, nystatin, linearmycin,
> mediomycin) and the HSAF/PTM tetramate class. See `examples/judgment_18strain/Lit_Verification_DAPR_New_Leads.md` for the citation set.

## What the tools do with this vocabulary

- `mamey/scoring.py` uses AB/AF weights as routing priors, not final DAPR scores.
- `tools/apply_dapr_boards.py` restores owner-written CSV boards into a workbook. It does not derive judgment. A missing board is skipped; if no board applies, the workbook is not written and the tool exits 1.
- `tools/build_dapr_rescue_sheets.py` fills `Activity_Ref` from the first framework name found in the KCB text. A row with no match keeps its old value, so check for stale references.

Both tools edit the workbook you name and write no receipt. Work on a copy.

The examples and literature notes below are retained reference content, not re-checked biology. Any compound or activity claim about a locus needs its own citation, and the locus is cited as strain / full node-or-contig / region / BGC alias.

## Antifungal buckets (highest-confidence first)
| Bucket | Named examples | BGC / marker clue |
|---|---|---|
| Polyenes | nystatin, amphotericin, natamycin, candicidin, filipin, rimocidin, eurocidin, linearmycin, mediomycin | **large modular T1PKS**, DH-rich (polyene), PAS-LuxR regulator. NOT `arylpolyene` (pigment). |
| Peptidyl nucleosides | nikkomycin, polyoxin, pacidamycin, mureidomycin, napsamycin | chitin-synthase inhibition; nucleoside pathway genes; UV ~260 nm |
| PTM tetramate macrolactams (HSAF) | HSAF, dihydromaltophilin, maltophilin, alteramide, frontalamide, ikarugamycin, combamide | hybrid PKS-NRPS, ornithine A-domain; sphingolipid biology |
| Bacillus lipopeptides | iturin, bacillomycin, mycosubtilin (iturin); fengycin, plipastatin (fengycin) | large NRPS, lipid tail; mostly Bacillus (atypical in Streptomyces) |
| Phenylpyrroles | pyrrolnitrin | prnABCD, halogenated tryptophan |
| Glycolipopeptides | occidiofungin, burkholdine | Burkholderia; β-amino acid/sugar |
| Phenazines | phenazine-1-carboxylic acid, pyocyanin | phz core; redox/colored |
| Polyether ionophores | nigericin, monensin, lasalocid, salinomycin, maduramicin | cis-AT T1PKS + epoxidase; **cytotoxic caution** |
| Macrolide (ATP-synthase) | oligomycin | large T1PKS; **cytotoxic caution** |

## Antibacterial buckets
| Bucket | Named examples | BGC / marker clue |
|---|---|---|
| Aminoglycosides | streptomycin, neomycin, kanamycin, gentamicin, apramycin, hygromycin | DOIS/aminotransferase/GT; APH/AAC resistance |
| Glycopeptides (anti-MRSA) | vancomycin, teicoplanin, A40926 | NRPS core, halogenase, VanHAX self-resistance |
| β-lactams / carbapenems | thienamycin, carbapenem MM4550, cephamycin, clavulanate | CarB/CarC; β-lactam synthetase; PBP self-protection |
| Lipopeptides (membrane) | daptomycin, A54145, friulimicin, glycinocin | NRPS, acidic residues, lipid starter, Ca-dependent motif |
| Lanthipeptides / thiopeptides | nisin, mersacidin; thiostrepton, nosiheptide, GE2270 | LanB/C or LanM; YcaO/azole RiPP |
| Aromatic T2PKS | formicamycin/fasamycin, tetracyclines | T2PKS core + cyclases; TetR/efflux |
| Macrolides | erythromycin, tylosin, pikromycin | modular T1PKS + GT; Erm resistance |
| Orthosomycins | evernimicin, avilamycin | glycosylated oligosaccharide |
| Aminocoumarins | novobiocin, clorobiocin | gyrase target; aminocoumarin genes |
| Phosphonates / FabF / moenomycin | fosfomycin; platensimycin; moenomycin | PepM; terpenoid-PKS; phosphoglycolipid |
| Liponucleosides | tunicamycin, muraymycin, caprazamycin | MraY logic; polar extraction |

## Routed OUT (do not score as clean antibacterial/antifungal leads)
- **Cytotoxic-adjacent (route to cytotoxicity):** indolocarbazoles (staurosporine, rebeccamycin, K-252), enediynes (kedarcidin), aureolic acids (mithramycin), anthracyclines (cosmomycin), Hsp90 ansamycins (geldanamycin, herbimycin), angucycline-diazo (kinamycin), aminoquinone (streptonigrin).
- **Ecological / siderophore (iron-withholding, not direct antibiotic):** coelichelin, mirubactin, desferrioxamine, pyoverdine, enterobactin. Acknowledge ecological role; do not overcall as antibacterial.
- **arylpolyene** (flexirubin-type pigment): oxidative-stress defense, **not** an antifungal polyene.

**Historical verification statement (not re-verified here):** the routed-out classes were described as literature-verified as cytotoxic-adjacent (anthracyclines, kinamycin, indolocarbazoles, Hsp90 ansamycins, enediynes) or ecological iron-acquisition (coelichelin, desferrioxamine, mirubactin) — see `examples/judgment_18strain/Lit_Verification_Routed_Out.md`.

*Source vocabulary contributed by the project PI/domain expert; encodes standard bacterial NP activity associations.*
