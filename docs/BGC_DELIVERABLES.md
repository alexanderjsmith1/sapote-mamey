# BGC deliverables toolkit
bgc_reference_align.py (align a BGC to reference clusters from DB/NCBI/GBK -> synteny + CSV),
bgc_figures.py (locus/GCF/BLASTp figures, RGB-safe), bgc_deliverable_pdf.py (cover+figures+Mode B PDF).
Figures MUST be RGB-on-white (RGBA won't load in many viewers). See README_PATCH v9.7.319.

## v9.7.338 interpretive & cohort add-ons (report-only, non-scoring; capacity-level, judgment deferred)
All read already-sealed package outputs and change no score / tier / gate / manifest / version. Similarity
is not identity; measured bioactivity is strain-level context, never a per-BGC production claim.
- good_guesses.py (`good-guesses`) — single best claim-safe interpretive read per notable BGC (Exceptional/High
  leads), tagged SOLID / RARE / REMARKABLE / NOTABLE / INTERESTING with a HIGH / MEDIUM / FRONTIER / LOW
  confidence + the resolving wet-lab experiment. Emits GOOD_GUESSES.md/.csv/.docx/.pdf (per-page claim-safety
  footer; a reference-dark guess is a novelty prior, not proof of a new compound).
- modeb_export.py (`modeb-export`) — an authored Mode-B card .md (or a package mode_b/ dir, batch) → .docx
  (every §-table, §4 evidence grid included, a real Word table) + .pdf (page number + claim-safety footer on
  every page). The card's own claim-safety language is preserved verbatim; degrades gracefully with no python-docx.
- af_dossier.py (`af-dossier`) — AF lead board × optional measured Candida-activity crosswalk → AF_LEAD_DOSSIER.csv/.md;
  Standout shortlist = strains measured Candida-positive AND carrying a High AF-capacity lead. Capacity (class-level
  routing prior) and measured activity (strain-level context) stay in separate columns; runs with no wet-lab input.
- kcb_locusmap.py (`figures kcb-locusmap`) — offline KnownClusterBlast query-vs-MIBiG comparative locus map; see docs/BGC_FIGURES.md.
- cohort_leads_ledger.py (`cohort-leads`) — union every sealed triage board → COHORT_PRIORITY_LEADS.csv (Exceptional+High,
  ranked by tier/AF/AB); carries a MIXED-ENGINE comparability caution when strains span engine versions.
- cohort_assemble.py (`cohort-assemble`) — assemble sealed packages → COHORT_MASTER.csv (+ _strain_summary / _class_by_strain
  siblings, optional .xlsx) without the O(N^2) master rewrite; the figure-ready cohort substrate.
- mibig_comparator_coverage.py (`comparator-coverage`) — re-expresses every named MIBiG comparator against two denominators
  (all-locus vs defining-core genes) + collision / within-BGC-specificity / cohort-promiscuity flags →
  _3b_comparator_coverage.csv (+ _summary.json). The named-family false-positive killer for the AF lead list.
- domain_reference.py (`domain-reference`) — Mode-B domain functional-context dictionary emitted from sealed package(s).
- realistic_bgc_count.py (`realistic-count`) — corrected-denominator BGC count (marginal-drop + HIGH RG-GMCI merge); advisory.
- build_novelty_shortlist.py (`novelty-shortlist`) — composite multi-signal novelty shortlist (KCB-dark + low recognizability
  + RG-GMCI + cohort-unique domain); all columns are priors and move no tier.
