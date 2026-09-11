# Tree figure display and provenance

Use labels derived from explicit, hash-bound panel metadata. Display style does not establish scientific acceptance.

## Labels

Query labels may show strain, deposited host or collection location, and accession. Reference labels may show the organism, deposited isolation source and country, and accession. Keep collection origin distinct from later handling location. Do not invent values or turn a missing database into biological absence.

Use parentheses for accessions and brackets for deposited source text. Extract accessions before interpreting organism text; culture collection codes are not accessions. Preserve complete accession strings outside the organism-text budget. Repeated copies of one accession are redundant; different accessions on one tip require reconciliation.

`tools/build_placement_ggtree_inputs.py` accepts explicit host, auxiliary and reference SQLite inputs. Its annotation and receipt distinguish unrequested metadata, unbound accessions, unmatched accessions, empty deposited fields and populated deposited metadata. The configurable `GG_REF_LABEL_CHARS` budget controls organism text; it does not validate label uniqueness or guarantee that every canvas is wide enough.

## Rendering and review

Use `tools/ggtree_placement.R` or `tools/ggtree_rect_heatmap.R` with a complete annotation join. Inspect the actual PDF or image for clipping, collisions and legibility after changing canvas size or label length. Identify the outgroup, analysis source, display transformations, and any missing metadata in the caption or accompanying provenance record.

The analysis tree and any pruned or collapsed display derivative have separate roles. Preserve the analysis tree and the transformation ledger. A visible missingness marker can be omitted from a label only while its underlying hold and provenance remain available.

## Outgroups and claims

Use an explicitly selected, provenance-bound outgroup designation. Non-modal genera in a comparator panel are not automatically outgroups. Missing or conflicting designation remains a hold. The bundled registry is a historical reference snapshot; use a governed external registry for project decisions. `tools/phylo_outgroup_gate.py` is the shipped outgroup gate; do not add a duplicate under a different name.

A passing mechanical check does not accept a rooting, species assignment, compound identity or biological activity. Report aligned length with identity measurements and distinguish sequence placement from scientific interpretation.

Deposited reference databases may include an optional `host` column. Host values remain explicitly labeled as host, even when isolation material is present. The full combined deposited text remains in annotations; the visible label uses its independent display budget. Databases containing only `acc_base`, `isolation_source` and `country` remain supported.
