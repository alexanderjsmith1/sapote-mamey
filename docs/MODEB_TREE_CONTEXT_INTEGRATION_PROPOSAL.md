# Mode B HTML phylogenetic context — candidate integration specification

Status: proposal for the next cut, not implemented runtime behavior or release clearance. This extends the owner-requested 50-section layout. It consumes existing tree outputs; no new placement, alignment, genome tree or biological scan is requested.

## Presentation

Place an optional **Strain phylogenetic and isolation-source context** panel after the card identity and concise orientation, before the numbered scientific sections. Keep the familiar numbering intact: §48 biosynthetic citations/relevance, §49 genus/broader citations/relevance, §50 full gene evidence table.

Provide separately labeled views when available:

- **16S placement (EPA-ng)**: fixed-backbone placement, with query highlighted, accession and placement uncertainty.
- **Genome-marker phylogeny (GToTree workflow)**: marker-based genome tree, showing the actual downstream inference method and support metric from its receipt.

Default to one legible compact view with expansion to the full tree. Avoid loading a giant full-cohort figure into every card by default. Reuse one strain/genus tree across its BGC cards; do not recompute or falsely describe it as a BGC tree.

## Interpretation placement

§12, ecological interpretation, should discuss isolation-source metadata in phylogenetic context: what the focal strain's neighborhood looks like, which neighboring tips have comparable metadata, and whether any suggested host association is merely descriptive or has actually been tested. Keep host identity, isolation material, geography and disease context as distinct fields. Preserve raw metadata and its provenance beside any normalized category. Unknown is not soil, environmental or non-host by default.

§41 should describe tree type, marker/sequence scope, reference selection, uncertainty and any disagreement between methods. A 16S placement tree is not a BGC/domain phylogeny. A genome tree is not proof of BGC inheritance or horizontal transfer. Explain why a focal strain was highlighted and what a pruned neighborhood omits.

§47 may use an actual host-matched comparator only when metadata and matching criteria are supported. A nearby colored tip does not automatically meet that standard. §49 can cite literature relevant to the ecological interpretation, without turning literature phenotype into focal-strain evidence.

## Asset and provenance contract

Use a portable artifact reference resolved through the program's configured evidence interface. Bind the figure to a receipt containing: tree kind; focal strain and assembly/sequence accession or hash; source tree hash; figure hash; metadata-table hash and version; reference/query membership; outgroup/rooting; pruning rule and displayed/full denominators; actual inference tool/model; support metric and scope; date; draft/final owner status. No hardcoded workstation paths or discovery based solely on newest filename.

The panel must verify that the focal strain/assembly is represented and appropriate to the card selection. A 16S tree may contain more strains than the selected genome cohort. Show that scope difference; do not silently admit excluded assemblies or change card selection to match a figure. Mapping is strain-context binding, not BGC identity or a physical-locus join.

For EPA-ng, label placement likelihood-weight ratio as placement support over candidate edges, separate from the reference backbone's bootstrap values. For GToTree-derived outputs, read the actual tree-inference receipt rather than assuming IQ-TREE, a bootstrap method or a model. Do not put unlike measures in one unlabeled support column.

## Standalone HTML and storage

For a shareable single-file card, embed the approved display figure in the HTML. A safely encoded image data URI can preserve self-contained viewing; sanitize SVG or use it only as an inert image resource. Do not inject active SVG scripts, external-resource references or event handlers into the page. Do not bundle full alignments, genome FASTAs, jplace files or database exports into every card.

Prefer the compact approved SVG when legible and small; retain an explicit size budget and report any large increase. Raw scientific inputs remain in a shared evidence store with portable links/receipts. Explain that external evidence links may not accompany a shared single-file card. Private strain labels and metadata remain private; public/redacted export is a separate action.

## Incomplete assets and compatibility

Trees are optional evidence. While work is in progress, show **tree pending** or the owner-approved draft state; do not substitute an unrelated genus, stale figure or unlabeled draft. A missing figure must not block card production. Use source data to generate tip/host labels rather than manually editing a figure to imply metadata certainty.

Legacy cards and cards without trees must remain readable. The program's canonical report/figure interface should own this feature; avoid a parallel workstation-specific tree registry. The current owner-requested pause on card validation remains in effect. Any eventual software tests/release checks require the cut workflow; this proposal does not claim they ran.

## Handoff boundary

The current delivery is a specification. No HTML renderer, figure-ingestion API, tree-label join or runtime schema has been patched by this document. The next-cut owner should implement the bridge using the existing tree producers and report interface, then demonstrate it using a bound, owner-approved tree and generic portable fixture before calling the feature implemented.
