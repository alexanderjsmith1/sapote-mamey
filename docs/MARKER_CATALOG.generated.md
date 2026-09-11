# Marker / Cassette Catalog (generated)

**Generated from** `mamey/source_scans.py` — do not edit by hand.
**Content hash:** `666e3bd82586132a…`

Regenerate with `python3 tools/gen_marker_catalog.py`. The build checks this file against the live regex tables (`--check`), so the catalog cannot drift from the scanner.


## CASSETTE_PATTERNS  ·  15 families / 72 patterns

- **release_macrocyclization** (6): `thioesterase`, `\bte\b`, `cyclase`, `macrocycl`, `esterase`, `reductase release`
- **glycosylation** (5): `glycosyltransferase`, `glycosyl`, `sugar`, `deoxysugar`, `gt\b`
- **halogenation** (4): `(?<!de)halogenase`, `fluorinase`, `chlorinase`, `brominase`
- **phosphonate** (5): `(?<!carboxy)phosphonate(?!.*transporter)(?!.*utilization)(?!.*c-?p lyase)(?!.*phn[g-m]\b)`, `pep mutase(?!\s*family)`, `phosphoenolpyruvate mutase(?!\s*family)`, `foma`, `fomb`
- **nucleoside** (7): `peptidyl[- ]nucleoside`, `nikkomycin`, `polyoxin`, `\bnikj\b`, `\bnikd\b`, `\bnikc\b`, `chitin synthase inhibit`
- **aminoglycoside_aminocyclitol** (4): `aminocyclitol`, `dois`, `btrc`, `2-deoxy-scyllo-inosose`
- **tetronate_spirotetronate** (4): `tetronate`, `spirotetronate`, `fkbh`, `(?<!acyl)glyceryl`
- **thioamide_ycao** (2): `thioamide`, `ycaO`
- **lanthipeptide** (6): `lanthipeptide`, `lantibiotic`, `(?<![A-Za-z])lanc(?![A-Za-z])`, `(?<![A-Za-z])lanm(?![A-Za-z])`, `(?<![A-Za-z])lant(?![A-Za-z_])`, `(?<![A-Za-z])lanp(?![A-Za-z])`
- **lassopeptide** (2): `lassopeptide`, `lasso peptide`
- **tomm_azole_ripp** (5): `azole`, `tomm`, `cyclodehydratase`, `dehydrogenase`, `ripp`
- **polyene_ptm_hsaf** (5): `(?<!aryl)polyene`, `hsaf`, `maltophilin`, `tetramate`, `pks-nrps`
- **siderophore_metallophore** (5): `siderophore`, `metallophore`, `nrp-metallophore`, `iron`, `ferric`
- **transporter_resistance** (5): `transporter`, `efflux`, `exporter`, `resistance`, `immunity`
- **chitin_glycan_ecology** (7): `chitinase`, `gh18`, `gh19`, `aa10`, `lpmo`, `glcnac`, `dasr`

## CCTT_PATTERNS  ·  18 families / 121 patterns

- **T43-HAL_halogenase** (3): `(?<!de)halogenase`, `flavin-dependent halogenase`, `tryptophan halogenase`
- **T43-XHAL_fluorinase_chlorinase** (5): `fluorinase`, `chlorinase`, `\bsall\b`, `\bfla\b`, `sam-dependent halogenase`
- **T43-PHO_phosphonate** (4): `(?<!carboxy)phosphonate(?!.*transporter)(?!.*utilization)(?!.*c-?p lyase)(?!.*phn[g-m]\b)`, `\bpep_mutase\b`, `pep mutase(?!\s*family)`, `phosphoenolpyruvate mutase(?!\s*family)`
- **T43-NUC_nucleoside** (7): `nikkomycin`, `polyoxin`, `\bnikj\b`, `\bnikd\b`, `\bnikc\b`, `peptidyl[- ]nucleoside`, `chitin synthase inhibit`
- **T43-BLA_betalactam** (11): `\bnocardicin\b`, `isopenicillin n synthase(?!\s*family)`, `\bpcbab\b`, `\bpcbc\b`, `acv synthetase`, `beta-lactam synthetase`, `\bbls\b`, `clavaminate synthase`  … (+3 more)
- **T43-AMC_aminocyclitol** (4): `aminocyclitol`, `dois`, `btrc`, `2-deoxy-scyllo-inosose`
- **T43-ENE_enediyne** (1): `enediyne`
- **T43-LAN_lanthipeptide** (4): `lanthipeptide`, `lantibiotic`, `\blanc\b`, `\blanm\b`
- **T43-LASSO_lassopeptide** (2): `lassopeptide`, `lasso peptide`
- **T43-THA_thioamide** (2): `thioamide`, `ycaO`
- **T43-DKP_cdps** (3): `cyclodipeptide synthase`, `\bcdps\b`, `diketopiperazine`
- **T43-IDC_indolocarbazole** (4): `indolocarbazole`, `rebeccamycin`, `staurosporine`, `indsynth`
- **T43-PTM_hsaf_tetramate** (13): `\bhsaf\b`, `maltophilin`, `dihydromaltophilin`, `heat.?stable.?antifungal`, `tetramate`, `tetramic acid`, `xanthobaccin`, `frontalamide`  … (+5 more)
- **T43-TET_tetronate_spirotetronate** (4): `tetronate`, `spirotetronate`, `fkbh`, `(?<!acyl)glyceryl`
- **T43-NN_n_n_bond** (6): `n-n bond`, `diazo`, `\bcreE\b`, `\bcreD\b`, `azoxy`, `hydrazine`
- **T43-PYE_polyene_macrolide** (25): `(?<!aryl)polyene macrolide`, `(?<!aryl)polyene antifungal`, `\bnatamycin\b`, `\bpimaricin\b`, `\bcandicidin\b`, `\bamphotericin\b`, `\bnystatin\b`, `\bfilipin\b`  … (+17 more)
- **T43-GPA_glycopeptide** (15): `\boxyB\b`, `\boxyA\b`, `\boxyC\b`, `\bdpgs\b`, `3,5-dihydroxyphenylglycine`, `4-hydroxyphenylglycine`, `\bhpg\b aminotransferase`, `\bglycopeptide\b`  … (+7 more)
- **T43-BLT_betalactone** (8): `\bbetalactone\b`, `\bbeta-lactone\b`, `\bsalinosporamide\b`, `\bplatensimycin\b`, `\bplatencin\b`, `\blactacystin\b`, `\bebelactone\b`, `\bovalicin\b`

## CCTT_VETOES  ·  3 families / 9 patterns

- **T43-NUC_nucleoside** (3): `glycogen_trehalose`, `nucleoside`, `sugar-kinase/glycogen-trehalose context (APH misreads as nucleoside)`
- **T43-ENE_enediyne** (3): `hglE_hglD`, `enediyne`, `hglE/hglD glycolipid ketosynthase cross-reacts with ene_KS (PREV-001)`
- **T43-DKP_cdps** (3): `copalyl_terpene`, `cyclodipeptide`, `copalyl diphosphate synthase (ent-CDPS, a terpene cyclase) collides with the cyclodipeptide synthase (CDPS) gene token — veto unless region is typed cyclodipeptide`

## CHITINASE_PATTERNS  ·  5 families / 15 patterns

- **GH18** (3): `gh18`, `glycoside hydrolase family 18`, `chitinase`
- **GH19** (2): `gh19`, `glycoside hydrolase family 19`
- **AA10_LPMO** (3): `aa10`, `lpmo`, `lytic polysaccharide monooxygenase`
- **CBM_CHITIN** (3): `chitin.?binding`, `cbm`, `carbohydrate.binding`
- **GlcNAc** (4): `glcnac`, `n-acetylglucosamine`, `nag[a-z]`, `dasr`

## DOMAIN_CLASS_PATTERNS  ·  20 families / 52 patterns

- **NRPS_A** (4): `\bA\b`, `AMP-binding`, `adenylation`, `NRPS_A`
- **NRPS_C** (3): `\bC\b`, `condensation`, `NRPS_C`
- **NRPS_T_PCP** (3): `\bT\b`, `PCP`, `thiolation`
- **NRPS_E** (2): `\bE\b`, `epimerization`
- **TE_release** (2): `\bTE\b`, `thioesterase`
- **PKS_KS** (4): `PKS_KS`, `\bKS\b`, `ketosynthase`, `ketoacyl synthase`
- **PKS_AT** (3): `PKS_AT`, `\bAT\b`, `acyltransferase`
- **PKS_DH** (3): `PKS_DH`, `\bDH\b`, `dehydratase`
- **PKS_ER** (3): `PKS_ER`, `\bER\b`, `enoylreductase`
- **PKS_KR** (3): `PKS_KR`, `\bKR\b`, `ketoreductase`
- **PKS_ACP** (3): `PKS_ACP`, `\bACP\b`, `acyl carrier`
- **RiPP_precursor** (3): `precursor`, `leader peptide`, `core peptide`
- **YcaO_TOMM** (2): `YcaO`, `cyclodehydratase`
- **Halogenase** (1): `(?<!de)halogenase`
- **Glycosyltransferase** (2): `glycosyltransferase`, `\bGT\b`
- **Methyltransferase** (1): `methyltransferase`
- **Oxidoreductase** (3): `oxidoreductase`, `dehydrogenase`, `oxygenase`
- **Aminotransferase** (2): `aminotransferase`, `transaminase`
- **Transporter** (3): `transporter`, `efflux`, `exporter`
- **Regulator** (2): `regulator`, `transcriptional`

## FLBR_PATTERNS  ·  4 families / 10 patterns

- **mod_KS** (4): `modular.?ks`, `ketosynthase`, `pks ks`, `beta-ketoacyl synthase`
- **hyb_KS** (3): `hybrid.?ks`, `nrps.*pks`, `pks.*nrps`
- **tra_KS** (2): `trans.?at`, `trans-acyltransferase`
- **mega_NRPS** (1): `nonribosomal peptide synthetase`

## MOBILE_ELEMENT_PATTERNS  ·  6 families / 30 patterns

- **integrase** (4): `\bintegrase\b`, `phage integrase`, `tyrosine integrase`, `\bxis\b`
- **recombinase** (5): `\brecombinase\b`, `site-specific recombinase`, `\bxerc\b`, `\bxerd\b`, `serine recombinase`
- **transposase** (5): `\btransposase\b`, `\btransposon\b`, `insertion sequence`, `\btnp\b`, `\bis[0-9]{2,}\b`
- **conjugation** (7): `\bftsk\b`, `\bspoiiie\b`, `conjugal`, `conjugative`, `type iv secretion`, `\brelaxase\b`, `\bmobl\b`
- **tox_repeat** (5): `\brhs\b`, `rhs repeat`, `\bwxg\b`, `\blxg\b`, `\byd repeat\b`
- **rep_initiator** (4): `replication initiat`, `\brepa\b`, `\brepb\b`, `plasmid replication`

## PRIMARY_METABOLISM_PATTERNS  ·  5 families / 69 patterns

- **housekeeping** (23): `topoisomerase`, `\bgyrase\b`, `\btoprim\b`, `topoisom`, `dna_topoiso`, `\btopa\b`, `\bgyra\b`, `\bgyrb\b`  … (+15 more)
- **pigment** (16): `lycopene`, `carotenoid`, `phytoene`, `\bcrti\b`, `\bcrtb\b`, `\bcrte\b`, `squalene-hopene`, `squalene.hopene cyclase`  … (+8 more)
- **cofactor_pqq** (6): `\bpqqd\b`, `\bpqqe\b`, `\bpqqf\b`, `\btigr03859\b`, `pyrroloquinoline quinone`, `pqq biosynthesis`
- **cofactor_ectoine** (7): `\bectoine\b`, `\bectoine synthase\b`, `\bectABC\b`, `\bectA\b`, `\bectB\b`, `\bectC\b`, `ectoine compatible solute`
- **replication_core** (17): `replicative dna helicase`, `replicative helicase`, `\bdnab\b`, `dna primase`, `\bdnag\b`, `primosom`, `chromosomal replication init`, `replication initiator protein`  … (+9 more)

## REGULATOR_PATTERNS  ·  14 families / 31 patterns

- **DasR_GntR** (2): `dasr`, `gntr`
- **LuxR** (1): `luxr`
- **TetR** (1): `tetr`
- **LysR** (1): `lysr`
- **SARP** (2): `sarp`, `streptomyces antibiotic regulatory protein`
- **MarR** (1): `marr`
- **LacI** (1): `laci`
- **AraC** (1): `arac`
- **TwoComponent** (3): `response regulator`, `histidine kinase`, `two-component`
- **Fur_Zur** (4): `\bfur\b`, `\bzur\b`, `ferric uptake regulator`, `zinc uptake regulator`
- **IolR** (1): `iolr`
- **PhoP** (2): `phop`, `phor`
- **OsdR** (1): `osdr`
- **GBL** (10): `gamma-butyrolactone`, `\bbutyrolactone\b`, `a-factor receptor`, `autoregulator receptor`, `\barpr\b`, `\barpa\b`, `\bscbr\b`, `\bbara\b`  … (+2 more)

## RESISTANCE_PATTERNS  ·  6 families / 21 patterns

- **Beta_lactamase_fold** (2): `beta.?lactamase`, `metallo-beta-lactamase`
- **Erm_methylase** (4): `\berm\b`, `rrna methyltransferase`, `23s rrna methyltransferase`, `erythromycin resistance methyltransferase`
- **VanHAX_like** (5): `\bvanh\b`, `\bvana\b`, `\bvanx\b`, `d-ala-d-lac`, `vancomycin resistance`
- **APH_AAC** (4): `aminoglycoside phosphotransferase`, `aminoglycoside acetyltransferase`, `\baph\b`, `\baac\b`
- **Fosfomycin** (3): `\bfoma\b`, `\bfomb\b`, `fosfomycin resistance`
- **Self_resistance_general** (3): `resistance protein`, `immunity protein`, `self-resistance`

## TFBS_MOTIFS  ·  12 families / 14 patterns

- **DasR_like_palindrome** (2): `TGTCTAGACNA`, `TGTNANNNNNNTNACA`
- **DmdR_iron_box_like** (1): `TTAGGTTAGGCTAACCTAA`
- **LexA_SOS_like** (2): `CTGTATATATATACAG`, `CGAACNNNNGTTCG`
- **BldD_like** (1): `GTCTAGAC`
- **FuR_like** (1): `GATAATGATAATCATTATC`
- **Zur_like** (1): `AAATGTTATAACATTT`
- **IolR_like** (1): `TGTGANNNNNNTCACA`
- **PhoP_box_like** (1): `GTTCANNNNNGTTC`
- **ANR_FNR_like** (1): `TTGATNNNNATCAA`
- **GBL_AdpA_like** (1): `TGGCSNGWWY`
- **SARP_BTAD_like** (1): `TCGAGNNNNCTCGA`
- **PAS_LuxR_like** (1): `ACCTGTNNNNACAGGT`

## TRANSPORTER_PATTERNS  ·  6 families / 10 patterns

- **ABC** (2): `abc transporter`, `atp-binding cassette`
- **MFS** (2): `major facilitator`, `\bmfs\b`
- **RND** (2): `rnd transporter`, `resistance-nodulation`
- **MATE** (1): `mate transporter`
- **Efflux** (1): `efflux`
- **Export** (2): `exporter`, `secretion`

## UMED_PATTERNS  ·  7 families / 23 patterns

- **LanP_S8_protease** (4): `(?<![A-Za-z])lanp(?![A-Za-z])`, `subtilisin`, `peptidase[ _-]?s8`, `serine protease`
- **LanT_C39_transporter_peptidase** (4): `(?<![A-Za-z])lant(?![A-Za-z_])`, `(?<![A-Za-z])c39(?![A-Za-z])`, `peptidase.*abc`, `abc.*peptidase`
- **FlaP_AplP_S9_protease** (3): `(?<![A-Za-z])flap(?![A-Za-z])(?!\s*endonuclease)`, `(?<![A-Za-z])aplp(?![A-Za-z])`, `peptidase[ _-]?s9`
- **M16B_metalloprotease** (3): `m16`, `metalloprotease`, `pitrilysin`
- **YcaO_TfuA_thioamide** (3): `ycao`, `tfua`, `thioamide`
- **RiPP_RRE** (2): `ripp recognition element`, `(?<![A-Za-z])rre(?![A-Za-z])`
- **nucleoside_maturation** (4): `nik`, `nucleoside`, `radical sam`, `aminotransferase`

## VETO_CONTEXT_PATTERNS  ·  4 families / 35 patterns

- **glycogen_trehalose** (14): `glycogen`, `trehalose`, `malto-?oligosyl`, `\btrey\b`, `\btres\b`, `\bglgx\b`, `\bglgb\b`, `\bglge\b`  … (+6 more)
- **hglE_hglD** (4): `\bhgle\b`, `\bhgld\b`, `hgle-ks`, `heterocyst glycolipid`
- **sugar_kinase** (7): `sugar kinase`, `carbohydrate kinase`, `hexokinase`, `fructokinase`, `galactokinase`, `sugar-phosphate kinase`, `ribokinase`
- **copalyl_terpene** (10): `copalyl`, `\bcdps\b.{0,4}diphosphate`, `diphosphate synthase`, `geranylgeranyl`, `\bggps\b`, `ent-copalyl`, `terpene cyclase`, `ent-cdps`  … (+2 more)
