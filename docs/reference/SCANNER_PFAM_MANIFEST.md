# Scanner Pfam models

The optional Pfam scanner reads a small HMM file built from a fixed list of Pfam families. You build that file yourself from a Pfam-A.hmm file you supply. `tools/build_scanner_hmm.py` does the build.

Every selector below carries a Pfam family version (for example `PF00155.28`). The builder fetches each one by that exact versioned accession. Your `Pfam-A.hmm` must contain those exact versions. The repository does not record which Pfam release that is, so a different release may lack some of them. If any selector is missing, the builder prints `SCANNER_BUILD_REFUSED: ` followed by the reason, exits 2 and publishes nothing. `hmmfetch` and `hmmpress` come from HMMER, installed separately.

## Build the HMM file

```bash
python tools/build_scanner_hmm.py --source path/to/Pfam-A.hmm --out results/EXAMPLE/scanner_pfam.hmm --preset 35
```

Substitute the actual source and a fresh authorized destination; quote paths containing spaces. Use `--preset 148` for the larger set, or `--accessions <file>` for your own list (exactly one of the three). You need `hmmfetch` and `hmmpress` installed. The builder makes no network request. It refuses to overwrite an existing output file, index file or receipt.

Success: exit 0, the HMM file with its four index files, and `<out>.build_receipt.json` with status `COMPLETE_NEW_SOURCE_BUILD`. A caught failure exits 2. If the build is interrupted, inspect the output folder before you rerun.

To use the file, export the variable in the shell session, for example `export SM_HMM_DB="/actual/path/scanner_pfam.hmm"`, substituting the real bound model path. The scanner checks that variable first, then its configured folders. A path that exists is not proof of a valid model file or of a completed scan. See [external data](../EXTERNAL_DATA.md), [database inspection](../TOOL_DATABASE_INSPECTION.md) and [public data provisioning](../PUBLIC_RELEASE_DATA.md).

The receipt records the hash of the Pfam file you supplied. The builder does not compare the result with any earlier HMM file, so the same source bytes can give an identical model. Record your Pfam release with the receipt.

## The 35 selectors

`bundle_support/scanner_pfam_35_accessions.txt` holds these 35 versioned accessions. `scanner_pfam_148_accessions.txt` holds the 148 for `--preset 148`. They are selectors, not models.

| Accession | Family | Role |
|---|---|---|
| PF00155.28 | Aminotran_1_2 | aminotransferase |
| PF00202.28 | Aminotran_3 | aminotransferase-3 |
| PF00501.35 | AMP-binding | NRPS adenylation |
| PF16715.12 | CDPS | cyclodipeptide synthase |
| PF02797.22 | Chal_sti_synt_C | type-III PKS, C-terminal |
| PF00195.26 | Chal_sti_synt_N | type-III PKS, N-terminal |
| PF00668.26 | Condensation | NRPS condensation |
| PF01041.24 | DegT_DnrJ_EryC1 | sugar aminotransferase |
| PF01761.27 | DHQ_synthase | DHQ synthase |
| PF01370.28 | Epimerase | NDP-sugar epimerase |
| PF06276.18 | FhuF | siderophore reductase |
| PF00534.27 | Glycos_transf_1 | glycosyltransferase |
| PF03033.27 | Glyco_transf_28 | glycosyltransferase |
| PF04183.19 | IucA_IucC | NIS siderophore synthase |
| PF00109.33 | ketoacyl-synt | PKS ketosynthase, N-terminal |
| PF02801.29 | Ketoacyl-synt_C | PKS ketosynthase, C-terminal |
| PF08659.17 | KR | ketoreductase |
| PF05147.20 | LANC_like | lanthipeptide cyclase |
| PF00891.25 | Methyltransf_2 | methyltransferase |
| PF00067.28 | p450 | cytochrome P450 |
| PF13714.13 | PEP_mutase | phosphonate PepM |
| PF00348.23 | polyprenyl_synt | prenyltransferase |
| PF01943.23 | Polysacc_synt | polysaccharide synthase |
| PF00550.32 | PP-binding | carrier protein |
| PF14765.13 | PS-DH | dehydratase |
| PF04321.24 | RmlD_sub_bind | dTDP-sugar RmlD |
| PF01397.28 | Terpene_synth | terpene synthase |
| PF03936.22 | Terpene_synth_C | terpene synthase, C-terminal |
| PF00975.27 | Thioesterase | TE release |
| PF00108.30 | Thiolase_N | thiolase |
| PF04820.21 | Trp_halogenase | tryptophan halogenase |
| PF02624.22 | YcaO | cyclodehydratase |
| PF00698.27 | Acyl_transf_1 | acyltransferase |
| PF14028.12 | Lant_dehydr_C | lanthipeptide dehydratase, C-terminal |
| PF04738.19 | Lant_dehydr_N | lanthipeptide dehydratase, N-terminal |

A significant profile match is evidence consistent with a family assignment. Inspect the alignment, thresholds, context and alternatives; a match does not demonstrate gene function, a product or activity.
