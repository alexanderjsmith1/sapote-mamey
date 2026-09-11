# Scanner Validation Plan — v0.5 (UNTESTED class-priors + RS01)

**Status: plan, not results.** These scanners have not been run. Each shares
`test_note: "no domain-name proxy available; needs HMM to test"` — their gate domains
aren't in the 35-family `scanner_pfam.hmm`, so validation requires building discriminating
HMMs (via `Wheelhouse/engine/pyhmmer_scanner_engine.py`) and searching known-positive
proteomes. This document specifies *how* to validate, and reviews each gate's soundness.
No `test_status` was promoted to PASS here — that requires an actual run.

## Method (per scanner)
1. Build HMMs for the gate's discriminating domains from curated seed alignments.
2. Search the MIBiG proteomes of the `pos` producers → gate must fire.
3. Search negative controls (the `trap` cases) → gate must NOT fire.
4. Only on pass both → promote `test_status` UNTESTED → PASS with the fired-cluster note.

## Per-scanner review

**AF04 — Echinocandin-like lipopeptide.** Gate `cyclic hexapeptide NRPS` is
under-specified (the trap itself warns "generic lipopeptide NRPS"). *Validation must
require* the `fatty-acyl-AMP_ligase` + ≥2 hydroxylases from `support` to discriminate.
Positives: echinocandin B, pneumocandin (MIBiG). Negative: any generic cyclic-NRPS.

**AF05 — Antifungal heptaene polyene.** Gate (polyene KS + mycosamine aminotransferase)
is **sound** — mycosamine biosynthesis separates it from carotenoid/terpene polyenes.
Positives: candicidin, nystatin, amphotericin. Negative: isorenieratene.

**AB01 — Glycopeptide (vancomycin-family).** Gate (OxyB+OxyC crosslinking P450 pair) is
the **correct** discriminator; trap correctly rejects any P450-carrying NRPS. Positives:
vancomycin, teicoplanin, balhimycin. Negative: other P450-NRPS.

**AB04 — Beta-lactam.** **GATE/POS MISMATCH (must fix before validating).** Gate
(ACVS + IPNS) only catches IPNS-route β-lactams (penicillin/cephalosporin/cephamycin).
The `pos` list includes clavulanate and nocardicin, which do **not** use IPNS (clavam via
CEAS/BLS; monobactam via a distinct NRPS) — the gate as written will miss them. Fix:
either split into an IPNS-route sub-rule vs a clavam/monobactam sub-rule, or drop
clavulanate/nocardicin from `pos`. Validate the IPNS route vs cephamycin C.

**AB06 — Pleuromutilin / diterpene.** Gate (diterpene cyclase + GGPP synthase) is sound
but **narrow** (single known product) — high specificity, low recall by design. Positive:
pleuromutilin. Negative: carotenoid/hopanoid terpene.

## RS01 — Self-resistance / TDGM (new)
Not a domain-HMM scanner: needs a **duplication + co-localization** check (a resistance or
duplicated-essential gene inside a BGC, with a second housekeeping copy elsewhere). Model
on ARTS/FunARTS. Validate against known self-resistance exemplars (e.g. duplicated
fabB/fabF near a FAS-inhibitor BGC). Output is a target-class **hypothesis**, never an
MoA claim.
