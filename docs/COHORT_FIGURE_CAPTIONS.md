# Cohort figure captions (Sapote-Mamey)

Captions ride along with each figure. Every "domain" here is an HMM profile call: the **deterministic
function is the HMM match** — a protein region scored above the model's gathering/cutoff threshold by
antiSMASH (Pfam, antiSMASH-specific, or TIGRFAM profiles). A profile is a position-specific probability
model, not a single consensus string; the **diagnostic catalytic signature** given below is the
textbook active-site motif/residue the profile is built around, not a claim that a literal sequence was
matched. Domain presence is a **capacity** signal, not evidence a product is made.

---

## fig9 — Domain co-occurrence across BGCs (pooled cohort)
Cell = number of BGCs whose domain set contains **both** row and column domains; diagonal = number of
BGCs carrying that domain. Pooled across all cohort BGCs. Reads as: which biosynthetic modules travel
together (the PKS block co-occurs; the NRPS block co-occurs; carrier/transport domains ride along).

**Domain glossary** (accession · function · diagnostic catalytic signature):
- **PP-binding** · Pfam PF00550 · carrier domain (ACP in PKS / PCP in NRPS). The growing acyl/peptidyl
  chain is tethered as a thioester to a 4'-phosphopantetheine (Ppant) arm. Signature: the **invariant
  serine** of PF00550 (in a [LV]G[FY]**DS**[LI]-type context) onto which a PPTase transfers the Ppant
  moiety from CoA. This is the attachment point every modular assembly line is built around.
- **PCP** · peptidyl carrier (thiolation) domain — the NRPS instance of the same PF00550 Ppant-serine
  chemistry, in peptide context.
- **ketoacyl-synt** · Pfam PF00109 · β-ketoacyl synthase (KS), N-terminal. Catalyses the decarboxylative
  Claisen condensation that extends the polyketide by two carbons. Signature: active-site **cysteine**
  nucleophile plus a **His–His** pair.
- **PKS_KS** / **PKSI-KS_m3**, **PKSI-KS_m5** · antiSMASH type-I modular-PKS ketosynthase profiles
  (module-position variants of the KS above). Same KS Cys/His–His catalytic chemistry; the m3/m5 tags mark
  specific module contexts antiSMASH resolves.
- **Ketoacyl-synt_C** · Pfam PF02801 · KS C-terminal domain; completes the condensing-enzyme fold
  (dimerisation / substrate channel). Structural partner to PF00109.
- **KAsynt_C_assoc** · Pfam PF16197 · ketoacyl-synthase C-terminal *associated* domain; structural,
  packs against the KS.
- **PKS_AT** / **Acyl_transf_1** · Pfam PF00698 · acyltransferase (AT). Selects the extender unit
  (malonyl-CoA → acetate; methylmalonyl-CoA → propionate) and loads it onto the ACP Ppant thiol.
  Signature: catalytic **serine** in the **GHSxG** motif (forms a covalent acyl-enzyme intermediate).
- **PKS_KR** / **PKSI-KR_m1** · Pfam PF08659 · ketoreductase (KR). NADPH-dependent reduction of the
  β-keto group to β-hydroxy. Signature: Rossmann-fold NADPH pocket (**GxGxxG**) + catalytic
  **Ser/Tyr/Lys** triad. PKSI-KR_m1 is antiSMASH's type-I PKS KR module profile.
- **AMP-binding** · Pfam PF00501 · adenylation (A) domain (NRPS and acyl-CoA ligases). Activates a
  carboxylic acid (an amino acid, in NRPS) as an **acyl-adenylate** using ATP, then thioesterifies it onto
  PCP. Substrate is read from the ~8–10-residue **Stachelhaus specificity code** lining the pocket.
- **AMP-binding_C** · Pfam PF13193 · the small C-terminal subdomain of the adenylation domain.
- **NRPS-A_a3**, **NRPS-A_a6**, **NRPS-A_a8** · antiSMASH adenylation sub-profiles marking the conserved
  A-domain core motifs **A3 / A6 / A8** (Marahiel numbering) used to detect and sub-classify NRPS A-domains.
- **Condensation** · Pfam PF00668 · NRPS condensation (C) domain; forms the peptide bond between the
  upstream PCP-bound peptidyl and the downstream PCP-bound aminoacyl. Signature: catalytic second
  histidine in the **HHxxxDG** motif.
- **TIGR01733** · TIGRFAM (not Pfam) · "amino acid adenylation domain" — an equivalent NRPS A-domain
  diagnostic model; its co-occurrence with AMP-binding is expected (two models over the same feature).
- **ABC_tran** · Pfam PF00005 · ABC-transporter nucleotide-binding (ATPase) domain. Powers efflux/export.
  Signature: **Walker A** P-loop (GxxGxGK[S/T]), **Walker B**, and the ABC **LSGGQ** signature. In BGCs it
  is often the product-export / self-resistance pump — hence its co-occurrence with the assembly line.

---

## fig10 — Self-resistance marker map per strain
BGCs per strain classified by **source-derived resistance tier** (the strongest-signal tier present in
the cluster). The **potency tell** is a T1 or T2 marker: a cluster that encodes defence against its own
product is more likely to make a genuinely bioactive compound, so these rank higher for follow-up.

- **T1 — self-protection (source-derived):** a diagnostic self-resistance determinant (e.g. a duplicated
  or modified copy of the compound's own cellular target) co-located in the cluster. Strongest potency tell.
- **T2 — resistance-like (source-derived):** a resistance-associated function present but not a clear-cut
  target-duplication self-protection call.
- **T3 — transporter-only routing:** an efflux/transport function only (e.g. ABC/MFS pump); consistent with
  export but not, on its own, a self-protection signal.
- **no resistance signal:** no source-derived resistance determinant detected.

"% potency-signal" = fraction of the strain's BGCs with a T1 **or** T2 marker (this session: AS-XXX 24%,
AS-XXX 11%, AS-XXX 11%, AS-XXX 4%). All calls are capacity signals (mechanism present/absent), not
confirmed phenotype.

---

## fig11 — TTA / bldA regulatory-dependency profile per strain
BGCs per strain classified by their **strongest bldA/TTA dependency tier** (the lowest = most-dependent
tier across the cluster's genes). A TTA (Leu) codon is decoded efficiently only when the *bldA*-encoded
tRNA is charged, which in streptomycetes happens mainly during development — so TTA-dependent clusters are
often **silent under standard growth** and are candidates for activation.

- **T1 — strongest dependency:** TTA codon(s) in core/essential cluster genes; expression is expected to be
  tightly bldA-gated (most likely silent under standard conditions → highest-priority activation candidate).
- **T2 — moderate dependency:** TTA codon(s) present in cluster genes, less central than T1.
- **T3 — weak dependency:** limited/peripheral TTA involvement.
- **T4 — negligible / none:** no meaningful TTA/bldA dependency detected.

The tier is the **minimum** (strongest) tier across the cluster's genes. "% strongly gated" = fraction at
T1 (this session: AS-XXX 37%, AS-XXX 32%, AS-XXX 55%, AS-XXX 63%). Capacity/regulatory signal, not a
measured expression level.

---

## Other figures (brief)
- **fig1 census_notier** — per-strain gene/domain census; cells = raw counts, colour = z-score within
  each metric; assembly tier in the caption line.
- **fig2 pks_bars** — each PKS BGC a bar, height = length (kb), stacked by gene-type coding bp; grey = non-CDS.
- **fig3 size_vs_rich** — BGC length vs functional-gene richness, all BGCs, by strain.
- **fig4 enriched_locus** — gene arrows coloured by function + per-gene domain track + gene-specific
  T2/T3-resistance (◇) and CCTT-trigger (★) badges; BGC-wide resistance/TTA summarised in the title.
- **fig5 archetype** — BGC biosynthetic-class composition per strain (from Products).
- **fig6 kcb_novelty** — BGCs by KCB tier (dark <1 = candidate-novel; similarity, not identity).
- **fig7 cctt_triggers** — CCTT cryptic-chemistry trigger family × strain (BGCs carrying each).
- **fig8 boundary_profile** — interior / edge / full-contig BGCs per strain (the assembly-quality lens).

*Read every count against fig8: fragmentation (edge/full-contig) inflates apparent BGC numbers relative
to interior-confident clusters.*
