<!-- Restored in v9.7.447 from the v9.7.338 CODE bundle (Wheelhouse/hmm/SCANNER_PFAM_MANIFEST.md, sha256 2ef4fcc2be21f765…). The Wheelhouse/hmm/ folder is no longer shipped; this list is the provenance record for the rebuild recipe in docs/PUBLIC_RELEASE_DATA.md. -->

# scanner_pfam.hmm — curated Pfam subset for Sapote-Mamey scanners

Extracted from Pfam-A.hmm (v3.3, 30,134 families, 2.2GB) — the ~35 families the
v0.3 scanner registry gates on. Use this instead of the full 400MB file: same
Pfam models, same curated gathering thresholds, 4MB instead of 2.2GB.

Contains 35 HMMs (official Pfam models + gathering cutoffs):

  PF00155.28   Aminotran_1_2          aminotransferase
  PF00202.28   Aminotran_3            aminotransferase-3
  PF00501.35   AMP-binding            NRPS adenylation
  PF16715.12   CDPS                   cyclodipeptide synthase (DKP)
  PF02797.22   Chal_sti_synt_C        type-III PKS-C
  PF00195.26   Chal_sti_synt_N        type-III PKS
  PF00668.26   Condensation           NRPS condensation
  PF01041.24   DegT_DnrJ_EryC1        sugar aminotransferase
  PF01761.27   DHQ_synthase           valiolone/DHQ synthase
  PF01370.28   Epimerase              NDP-sugar / epimerase
  PF06276.18   FhuF                   siderophore reductase
  PF00534.27   Glycos_transf_1        glycosyltransferase-1
  PF03033.27   Glyco_transf_28        glycosyltransferase
  PF04183.19   IucA_IucC              NIS siderophore synthase
  PF00109.33   ketoacyl-synt          PKS ketosynthase-N
  PF02801.29   Ketoacyl-synt_C        PKS ketosynthase-C
  PF08659.17   KR                     ketoreductase
  PF05147.20   LANC_like              lanthipeptide cyclase
  PF00891.25   Methyltransf_2         methyltransferase
  PF00067.28   p450                   cytochrome P450
  PF13714.13   PEP_mutase             phosphonate PepM
  PF00348.23   polyprenyl_synt        prenyltransferase
  PF01943.23   Polysacc_synt          polysaccharide synthase
  PF00550.32   PP-binding             PCP/ACP carrier
  PF14765.13   PS-DH                  dehydratase
  PF04321.24   RmlD_sub_bind          dTDP-sugar RmlD
  PF01397.28   Terpene_synth          terpene synthase
  PF03936.22   Terpene_synth_C        terpene synthase-C
  PF00975.27   Thioesterase           TE release
  PF00108.30   Thiolase_N             thiolase/KS-like
  PF04820.21   Trp_halogenase         tryptophan halogenase
  PF02624.22   YcaO                   thiopeptide/LAP cyclodehydratase
  PF00698.27   Acyl_transf_1          
  PF14028.12   Lant_dehydr_C          
  PF04738.19   Lant_dehydr_N          

## Usage (pyhmmer, offline)
```python
import pyhmmer
with pyhmmer.plan7.HMMFile('scanner_pfam.hmm') as hf:
    for hmm in hf:
        for hits in pyhmmer.hmmer.hmmsearch([hmm], proteome, bit_cutoffs='gathering'):
            ...  # bit_cutoffs='gathering' uses Pfam's curated per-family thresholds
```

## Validated (AS-XXX known compounds)
- CDPS -> c1.1.r001 (photopiperazine DKP) ✅
- Trp_halogenase -> c4.1.r003 (tetrachlorizine) ✅
- ketoacyl-synt -> ionostatin region among PKS hits (needs >=5/region gate)

## Integrity
SHA256 (scanner_pfam_full.hmm): 4d3d2ebb31d962a358fa71a84acc31979287e01a6a8a4990c632bd78d58c9fa5
Size: 4313 KB
