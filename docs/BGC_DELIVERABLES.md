# BGC deliverables toolkit

Three tools build per-BGC deliverables. `tools/bgc_reference_align.py` aligns a BGC to reference clusters (from a database, NCBI or a GenBank file) and writes a synteny figure and CSV. `tools/bgc_figures.py` draws locus, GCF and BLASTp figures. `tools/bgc_deliverable_pdf.py` builds a PDF with a cover, figures and the Mode B card.

For the legacy RGB-on-white route, verify the actual image mode: `tools/bgc_figures.py` saves a white-background PNG and attempts RGB flattening when Pillow is available. Missing Pillow or a flattening failure can leave an alpha channel. See [current BGC figure routes and limits](BGC_FIGURES.md); a saved file alone does not establish the requested export mode.

## Interpretive and cohort add-ons
These are report-oriented add-ons, not a guarantee that every operation is a read-only or transactional reader. Inspect each command's source and destination contract; use preserved package copies and fresh output paths when originals must remain immutable. See [post-seal reader boundaries](POSTSEAL_READERS.md) and the [deliverable queue](DELIVERABLE_QUEUE.md). Similarity
is not identity; measured bioactivity is strain-level context, never a per-BGC production claim.
- good_guesses.py (`good-guesses`) — a claim-bounded interpretive summary for notable Exceptional/High leads, tagged SOLID / RARE / REMARKABLE / NOTABLE / INTERESTING and HIGH / MEDIUM / FRONTIER / LOW, with a proposed resolving experiment. Without `--out` it prints Markdown; with `--out` it writes GOOD_GUESSES.md/.csv. DOCX and PDF require their separate `--docx` / `--pdf` flags and usable render dependencies. The handler can return zero while a requested format reports a skipped or failed status; inspect the actual format results and files. These labels are software priors, not calibrated confidence, novelty proof or scientific adoption.
- modeb_export.py (`modeb-export`) — an authored Mode-B card .md (or a package mode_b/ dir, batch) → .docx
  (every §-table, §4 evidence grid included, a real Word table) + .pdf (page number + claim-safety footer on
  every page). The card's own claim-safety language is preserved verbatim. A requested DOCX skipped because python-docx is unavailable makes the command fail, including DOCX-only requests; `--format both` also fails if either requested format is not written. A PDF can already exist when the combined result fails; inspect actual artifacts before retrying.
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
  _3b_comparator_coverage.csv (+ _summary.json). A diagnostic comparator-context report; its flags do not independently adjudicate named-family identity.
- domain_reference.py (`domain-reference`) — Mode-B domain functional-context dictionary emitted from sealed package(s).
- realistic_bgc_count.py (`realistic-count`) — an advisory connected-component count after its annotation-based marginal filter and pairs whose confidence text contains `HIGH`. This reader does not itself require a genuine-tiling verdict or independently validate exact group identities, physical linkage or acceptance. Preserve the raw region denominator, selected pairs and source hashes; a reduced count is a computational hypothesis, not a corrected biological census.
- build_novelty_shortlist.py (`novelty-shortlist`) — an advisory composite of saved KCB, recognizability, RG-GMCI text, package-level domain recurrence and novelty fields; it moves no tier. A blank KCB field is scored as dark, missing recognizability also receives the low-recognizability contribution, and any nonempty RG-GMCI support string contributes. Domain uniqueness means occurrence in one supplied package path, not an independently sampled strain or locus. Preserve missing/unmeasured inputs as holds and reconcile the unique panel before interpreting scores; these fallbacks do not establish measured no-hit, global rarity or chemical novelty.
