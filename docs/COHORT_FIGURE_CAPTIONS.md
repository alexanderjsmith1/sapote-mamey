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

## fig10 — Resistance-related source signals per strain
BGCs per strain classified by the highest-priority resistance-related tier recorded among their genes
(T1 before T2 before T3). The panel counts annotation signals; it cannot establish the product's
target, antimicrobial activity, potency, or a causal self-protection mechanism.

- **T1 — diagnostic self-protection candidate:** a source-derived diagnostic resistance group near
  the cluster. Verify class concordance and gene context before assigning a mechanism.
- **T2 — resistance-like (source-derived):** a resistance-associated function present but not a clear-cut
  target-duplication self-protection call.
- **T3 — transporter-only routing:** an efflux/transport function only (e.g. ABC/MFS pump); consistent with
  export but not, on its own, a self-protection signal.
- **no resistance signal:** no qualifying tier recorded in the supplied per-gene table.

The generated chart and CSV contain **counts**, not a percentage. If reporting a percentage, calculate
`100 × (T1 + T2 BGCs) / (all BGCs with rows in this figure's per-gene input)` for each strain and
state that denominator. This is the fraction with annotated resistance-related signals, not a
measure of potency or confirmed resistance. Missing gene rows can change the denominator.

---

## fig11 — TTA burden tier per strain
BGCs per strain classified by their highest recorded TTA tier. The source scan assigns tiers from
the **BGC-wide count of TTA codons in CDS**: T1 is zero; T2 is one or two; T3 is three to five;
T4 is six or more. A TTA count can motivate follow-up of translational regulation in an
applicable actinomycete, but this figure cannot establish transcription, protein abundance,
silencing, or induction conditions.

- **T1:** no TTA codons detected in BGC CDS.
- **T2:** one or two TTA codons detected.
- **T3:** three to five TTA codons detected.
- **T4:** six or more TTA codons detected.
- **unknown / missing:** no recognized tier in the per-gene input.
- **not applicable:** source scan explicitly declined a bldA tier for a non-actinomycete.

The renderer takes the **maximum recognized tier** among per-gene rows for a BGC. These rows
repeat a BGC-wide source-scan tier, so disagreement among its rows warrants source-data review.
The chart and CSV contain counts, not percentages; if reporting a T4 fraction, divide T4 by all
BGCs represented in the input for that strain, including unknown/not-applicable bins, and give
both numerator and denominator. Interpret not-applicable separately.

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
