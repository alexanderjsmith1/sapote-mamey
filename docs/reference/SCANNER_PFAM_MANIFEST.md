# Current scanner manifest boundary

The retained manifest below describes a historical 35-model artifact. Its size, model descriptions, source-version wording, checksum and “Validated” examples are provenance claims, not verification of a currently installed HMM or current scanner result. The CODE bundle does not ship the old `Wheelhouse/hmm/` artifact. The `v3.3` label alone does not bind a Pfam release/archive; historical download/model provenance must be retained separately. Bind the installed HMM's exact source, hash and native scan receipt before using this manifest as current execution evidence.

## Current selectors and producer

`bundle_support/scanner_pfam_35_accessions.txt` has 35 unique versioned selectors; `scanner_pfam_148_accessions.txt` has 148. Their bytes match the accession-file hashes in `bundle_support/scanner_accession_source_pins.json`. These are selectors, not HMM models, and do not prove historical model bytes or gathering thresholds. Preset 148 is distinct from the historical 35-model list below; a filename containing `150` can still denote a 148-model set.

The current producer is `tools/build_scanner_hmm.py`, accepting `--source`, `--out` and exactly one of `--preset {35,148}` or `--accessions`. It requires operator-provided HMM bytes and installed `hmmfetch`/`hmmpress`; it makes no network request. It reads the selected accession list and hashes source/list, but does **not** consult `scanner_accession_source_pins.json` to authenticate the source HMM against historical pins. A completed new-source receipt is not exact reconstruction of the historical artifact.

The builder refuses existing HMM, four index paths or build-receipt path (including symlinks), stages in the output parent, fetches one exact accession/model per selector, checks all four indices and unchanged source/list hashes, then publishes HMM, `.h3f/.h3i/.h3m/.h3p` and `<out>.build_receipt.json` through non-replacing hardlinks. Caught failures return 2; completed build returns 0 and receipt status `COMPLETE_NEW_SOURCE_BUILD`. Failed publication rolls back files it published, but this is sequential publication rather than a multi-file atomic transaction; interruptions still require inspection. Use a reviewed destination and preserve accepted evidence. Source: `tools/build_scanner_hmm.py:31–92`.

## Discovery versus execution

`SM_HMM_DB` takes precedence when its path exists; then configured directories and bundled/addon locations are searched. Resolver `n_models_hint` is filename-derived metadata, not an HMM inventory or successful model load (`mamey/wheelhouse.py:57–124`). In particular the explicit override checks path existence, not that it is a valid model file. `doctor` points to source-bound provisioning (`mamey/cli.py:4985–4991`); a discoverable path is not an executed scan. Missing models, skipped scanners and genuine negative evidence need separate states. See [external data](../EXTERNAL_DATA.md), [database inspection](../TOOL_DATABASE_INSPECTION.md) and [public data provisioning](../PUBLIC_RELEASE_DATA.md).

The historical “Validated” examples below lack complete strain/contig/region/BGC identity and source receipts in this manifest. Preserve them as unverified historical claims; do not infer compound production, scanner specificity or general validation from them.

## Retained historical manifest — unchanged below

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
