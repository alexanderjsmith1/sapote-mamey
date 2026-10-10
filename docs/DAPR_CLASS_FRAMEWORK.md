# DAPR Class → Activity Framework (Sapote scoring vocabulary)

Owner-contributed vocabulary for DAPR (antibacterial / antifungal) judgment. The tables describe historical review associations; they are not an automatic product-to-activity acceptance function. **All calls are class-level hypotheses; optional typed strain-level bioactivity metadata is
the project default. Never an isolation or per-BGC activity claim.**

> **Historical 18-strain verification statement (requires its original supporting evidence):** the class→activity associations used on the 18-strain
> cohort are **literature-verified** — antibacterial (carbapenem MM4550, clavulanate, A54145, teicoplanin,
> formicamycin, surugamide, glycinocin), antifungal polyenes (filipin, candicidin, nystatin, linearmycin,
> mediomycin) and the HSAF/PTM tetramate class. See `examples/judgment_18strain/Lit_Verification_DAPR_New_Leads.md` for the citation set.

## Software boundary and retained association holds

Extraction-side `mamey/scoring.py:53–74` explicitly calls AB/AF weights routing priors, not final WL/DAPR scores. `tools/apply_dapr_boards.py:2–6,20–36` restores owner-authored CSV boards; it does not derive scientific judgment from banked JSON. Missing sheet/CSV skips that board and can still save successfully. `tools/build_dapr_rescue_sheets.py:83–88,159–176` populates `Activity_Ref` by the first framework substring match in KCB text; an unmapped row leaves an existing value untouched. Thus an old reference annotation can remain after upstream text changes. These tools mutate the specified workbook and do not provide a source-hash/adoption receipt.

Do not infer automated DAPR scoring, verified citations, or a fresh activity classification from board restoration or an `Activity_Ref` string. Retain the adopted board CSV and its owner provenance, full input/code/output hashes and any holds; inspect stale/unmapped reference fields before reuse. Use a separately authorized candidate workbook rather than an authoritative source. Current50 report/card approval is a separate gate.

The named examples, marker clues, mechanistic vocabulary and historical literature-verification statements below are retained as **historical owner-reference content**, not newly checked biology. A table entry cannot authorize target selection or establish assay activity for a locus. Any current compound/activity claim requires its exact citation and comparator/evidence context to be independently admitted. Preserve strain / full node-or-contig / region / BGC alias wherever a locus is mentioned; a KCB product name or BGC alias is insufficient. Bind any current score, restored board or literature claim to its own source and acceptance record.

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
