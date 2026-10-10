# HTML evidence views: source, identity and receipt boundaries

These three files are shipped **templates**, not completed datasets or self-validating rendered evidence. Opening unfilled templates does not establish a usable view. A browser filter or selected record does not redefine the frozen source denominator.

| Surface | Producer and serving contract | Data/export scope |
|---|---|---|
| `mamey/data/siderophore_atlas.html` | `tools/render_siderophore_atlas.py` replaces placeholders from a pinned atlas JSON into a fresh output HTML. | Embedded snapshot; exact-identity search and route/state filters. No table/download exporter. |
| `mamey/enzyme_neighborhoods.html` | `mamey/cohort_enzyme_neighborhoods.py` substitutes `__VIEW_DATA__`; generated explorer is a standalone local view. | Embedded source projection; at most three selected loci, independent coordinate scales, raw evidence drawers. No canonical evidence-table exporter. |
| `mamey/evidence_disagreements.html` | Served by `mamey/evidence_disagreements.py` on loopback; calls its `/api/*` routes. | Live frozen-session reader, paginated gene/hit/reference context. Not a standalone snapshot and no browser export/acceptance writer. |

## Siderophore snapshot admission

The renderer checks the supplied atlas-file SHA-256, permitted output root and existing output, then consumes records and a `receipt.population` shape containing `frozen45` and `current_handback`. It does not validate full-locus uniqueness, individual evidence/source hashes, roster completeness or that the input receipt was scientifically admitted. A pinned file proves byte selection, not the truth of embedded authority/chemistry/reference statements. Preserve the atlas path/hash, producer/template hashes and output hash in a separate receipt.

The renderer returns source/output hashes to stdout; it does not save that return value as a receipt. HTML includes relative links to `GUIDE.pdf`, `GUIDE.docx` and `FIRST_FIVE_AND_NEGATIVE_AUDIT.json`, but the renderer neither creates nor checks those assets. Report absent companions as unavailable rather than treating a link as delivery. Template reference citations are external links; following them can leave the local page. The generated HTML is written directly, without atomic publication or a race-safe exclusive creation. Inspect partial/current bytes after failure and keep authoritative sources disjoint from output destinations (`tools/render_siderophore_atlas.py:7–19`).

Frozen population, current handback entries, eligible bases and displayed/exported records are separate counts. The page's “negative controls” describe its selected source states, never biological absence. Reference chemistry remains reference context; no filter or row selection transfers it to a locus.

## Enzyme neighborhood template

See [enzyme builder contract](ENZYME_NEIGHBORHOODS.md), including its pilot-control and final-manifest qualifications. The template calls its no-call selector “Five tested no-call controls,” but the builder selects up to five and does not require that count. Its fixed10kb flank prose likewise must be checked against the bound source manifest's actual `flank_bp`; geometry and sparse coverage come from that source, not the wording. Missing linked domains are explicitly not domain absence. Recurrence counts source annotation patterns, not orthology or physical linkage.

The template has a no-connect content-security policy and no external asset requests. That does not validate source data, rendering, annotations or biological claims. Generated `SOURCE_MANIFEST.json` hashes output files; retain its own hash externally. Browser-selected comparisons are a display state, not a new accepted dataset.

## Evidence disagreement service

See [candidate service contract](EVIDENCE_DISAGREEMENTS_CANDIDATE.md). The HTML relies on an active loopback service and frozen reader sessions; copying it alone does not make the evidence portable. Query filters, missing states, paginated retained hits and drawers preserve review context. No pairwise cue adjudicates function or supplies a current50 section-completion certificate. Export a bounded source audit only through the explicit CLI audit path, retaining its identity/source/code/template hashes separately. A UI failure must remain a hold, not be reinterpreted as an empty source result.
