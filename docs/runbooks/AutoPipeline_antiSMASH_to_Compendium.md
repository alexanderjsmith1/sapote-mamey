# AutoPipeline: antiSMASH ZIP → Mamey → Handoff → Compendium

**Patch v1.0 · bundle Sapote–Mamey v9.7.319 · engine Mamey 1.9.98**
**· PRIVATE**

A runbook (not engine code) describing how a Claude session auto-runs the full
single-strain pipeline when an antiSMASH ZIP is uploaded. The engine pieces it
calls (`mamey_run.py`, `mamey/locus_map.py`, the locked locus palette, gold mode)
ship in this bundle; the session glue scripts (`build_factsheet.py`,
`build_handoff.py`, expansion/compendium generators) are created per-session.

See the Patch Chat record for the full step list. Summary of the 9 steps:
1. Identify strain ID (strip suffixes).
2. Mamey gold-mode extraction → package.
3. Build fact sheet (metadata lookup order: conversation → master list → PENDING).
4. Build Sapote handoff markdown (self-contained for a parallel chat).
5. Locus maps for top 3 AB + top 2 AF leads (locked palette, data-only PNG + CSV).
6. Mode B cards at lead-tier depth, standing rules applied before writing.
7. Domain expansions (EXPANSION = PKS/halogenase/etc; EXPANSION2 = sulphur/saccharide).
8. Assemble per-strain compendium.
9. Present outputs + plain-text summary.

Standing rules enforced throughout: capacity-not-production; KCB = similarity;
bioactivity extract-level; contig/node on every BGC; the permanent downgrades
(NAPAA, NI-siderophore, NRP-metallophore, hglE-KS/PREV-001, ectoine, PQQ);
enediyne = neutral [E-signal], no BSL-2 flag. Batch strains sequentially (memory);
large ZIPs (>50 MB) run alone. Genus never inferred from KCB.

Cross-strain pattern flags to check per strain: DUF692, ranthipeptide, AP_endonuc_2,
PQQ, HxlR, SnoaL_2, Asn_synthase+RRE, T3PKS chalcone synthase, Hemerythrin, SelO,
GlfT2, GlgE, LytR, Bac_transf.
