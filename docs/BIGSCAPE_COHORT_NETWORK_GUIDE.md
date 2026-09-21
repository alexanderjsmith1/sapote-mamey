# BiG-SCAPE cohort reports and adaptive network sections

`tools/bigscape_cohort_report.py` converts one explicitly selected BiG-SCAPE 2 SQLite run into portable cohort tables. It requires a run ID, cutoff, strain metadata table, and node and region to BGC alias crosswalk. The database is opened read-only, and a missing BGC alias is never inferred.

```bash
python tools/bigscape_cohort_report.py \
  --db cohort.db --run-id 1 --cutoff 0.3 \
  --host-table strain_genus_host.tsv \
  --crosswalk node_region_bgc_crosswalk.tsv \
  --out cohort_report
```

An optional exact-identity recovery overlay can be supplied with
`--alias-overlay ALIAS_RECOVERY_CROSSWALK.tsv`. It is keyed by
`strain`, `full_node_or_contig`, and `region`. Only rows whose status is
`RESOLVED_EXACT_CURRENT_PACKAGE` and whose recorded complete identity exactly
matches the recovered alias are admitted. A held overlay row overrides an older
crosswalk alias and remains held; loci absent from the overlay may fall back to
the original crosswalk. The receipt hashes both sources and reports complete and
held denominators for the whole cohort and the cross-strain subset.

The report writes locus membership, per-family summaries, direct BiG-SCAPE edge distances, pairwise strain Jaccard similarity, and a JSON receipt with source hashes and denominators. Add `--require-complete-alias` when every exported locus must satisfy the complete identity contract. That strict command exits with status 2 and writes no outputs if any alias is unresolved.

Strain identifiers are admitted from the host table, base crosswalk, and optional overlay rather than from a hardcoded naming convention. For each GBK filename the parser selects the longest exact `<strain>_` prefix, then parses the remaining full node-or-contig and `regionNNN`. An unmatched database record is excluded from the admitted cohort and counted in the receipt; it is never guessed. Equal-length canonical matches are ambiguous and stop the run.

Every family summary also carries `class_code`, `class_nickname`, and `reviewed_subtype_code`. The single source for code definitions, matching terms, plain-language meanings, source bases, and claim ceilings is `mamey/data/bigscape_class_vocabulary.json`. Broad class codes are derived deterministically from the antiSMASH family labels and are limited to claim-safe routing categories such as `NRPS`, `T1PKS`, `T2PKS`, `T3PKS`, `PKS-NRPS`, `TERP`, `SAC`, `RiPP`, `LAP`, `LASSO`, `LAN`, `RANTHI`, `PHOS`, `NIS-SID`, `METAL`, `OTH`, `MIX`, and `UNK`. Heterogeneous families become `MIX`; unrecognized families become `UNK`. No exact product is inferred from a loose name.

`reviewed_subtype_code` remains blank unless a separate reviewed TSV is supplied through `--reviewed-subtypes`. Each reviewed subtype row must provide `family_id`, `reviewed_subtype_code`, `full_name`, `plain_language_meaning`, `source_basis`, and `claim_ceiling`. This supports displays such as `GCF 4329 · TERP · HOP` only after that subtype has been independently reviewed, and it keeps the reviewed interpretation separate from the broad source label.

Every network shows a non-abbreviated legend immediately below the SVG. The compact legend includes only the broad class and optional reviewed subtype present in that network. An expandable control opens the complete bundled glossary. Generate or verify the reusable Markdown version with:

```bash
python tools/bigscape_class_glossary.py --out docs/BIGSCAPE_CLASS_GLOSSARY.md
```

See `docs/BIGSCAPE_CLASS_GLOSSARY.md` for the undergraduate workflow: identify the GCF and cutoff, expand the code, inspect the complete locus identity, check the boundary state, interpret direct distance only as similarity context, and stop at the stated claim ceiling.

Generate standalone interactive views with:

```bash
python deliverable_tools/bigscape_network_widget.py \
  --membership cohort_report/BIGSCAPE_LOCUS_MEMBERSHIP.tsv \
  --summary cohort_report/BIGSCAPE_GCF_SUMMARY.tsv \
  --pairwise cohort_report/BIGSCAPE_STRAIN_PAIRWISE_JACCARD.tsv \
  --direct-edges cohort_report/BIGSCAPE_DIRECT_EDGES.tsv \
  --out cohort_widgets --require-complete-alias
```

## Adaptive labels

Family-network labels are selected deterministically from the displayed node count.

- One to three loci use compact `strain BGC-alias` labels on every node.
- Four to eight loci use strain-only labels in collision-managed side columns with leader lines.
- Nine or more loci label only the focal strain. Every node retains the complete `strain / full node-or-contig / region / BGC alias` identity and its metadata in hover and click detail.

Every family view identifies the family ID, cutoff, direct edge distance, genus, host metadata, boundary state, and claim ceiling. A contig-edge locus receives a distinct outline; this is a boundary caution, not a completeness call.

## Add a family section to an existing HTML report

Report integration is additive and strict. The source report is read but never modified; the integrated copy is written to `--report-out`. Every selected family must contain the focal strain and every selected locus must have a complete authoritative alias.

```bash
python deliverable_tools/bigscape_network_widget.py \
  --membership cohort_report/BIGSCAPE_LOCUS_MEMBERSHIP.tsv \
  --summary cohort_report/BIGSCAPE_GCF_SUMMARY.tsv \
  --pairwise cohort_report/BIGSCAPE_STRAIN_PAIRWISE_JACCARD.tsv \
  --direct-edges cohort_report/BIGSCAPE_DIRECT_EDGES.tsv \
  --out cohort_widgets --require-complete-alias \
  --report-html source_report.html --report-out integrated_report.html \
  --strain DEMO-A --family-id 12 --family-id 47
```

The insertion point is the report's `Claim ceiling` heading. The tool refuses a second integration block and refuses reports without that anchor.

### Optional MIBiG comparator context

When the source report already contains one marked MIBiG Comparator Identity Summary, add adjacent comparator-only context with `--mibig-json-dir`. The directory must contain accession-named MIBiG JSON records such as `BGC0000001.json`; only `biosynthesis.classes` is read for the class display. Missing class records remain visibly unavailable and are never inferred from compound names.

```bash
python deliverable_tools/bigscape_network_widget.py \
  --membership cohort_report/BIGSCAPE_LOCUS_MEMBERSHIP.tsv \
  --summary cohort_report/BIGSCAPE_GCF_SUMMARY.tsv \
  --pairwise cohort_report/BIGSCAPE_STRAIN_PAIRWISE_JACCARD.tsv \
  --direct-edges cohort_report/BIGSCAPE_DIRECT_EDGES.tsv \
  --out cohort_widgets --require-complete-alias \
  --report-html source_report.html --report-out integrated_report.html \
  --report-receipt-out integration_receipt.json \
  --strain DEMO-A --family-id 12 \
  --mibig-json-dir mibig_json
```

Every enhanced table states: `Characterized comparator context. These MIBiG fields describe the characterized comparator only and do not predict activity or mechanism for the focal locus.` Activity category, mechanism or target, evidence status, and primary-literature fields display `not verified in current evidence` unless a separate provenance-bearing table is admitted through `--curated-comparator-context`.

The curated TSV uses one row per exact MIBiG accession. It records the MIBiG class, activity and mechanism fields with separate verification statuses, overall evidence status, PMID/PMCID/DOI, primary-article title and URL, an abstract-level quotation/paraphrase locator, row-level holds, source-file hashes, curator, and review date. `activity_verification_status` and `mechanism_verification_status` must each be either `VERIFIED_PRIMARY_LITERATURE` or `NOT_VERIFIED_CURRENT_EVIDENCE`. An unverified field must contain the literal `not verified in current evidence`; a verified field must contain a direct primary-literature result. Rows with unresolved fields require a hold reason. Source and citation URLs must match, provenance source/hash lists must have equal widths, and every hash must be a valid SHA-256. The table class must exactly match the class parsed from the bound accession-named MIBiG JSON. The comparator name itself is never used to infer activity or mechanism.

### How to read comparator badges and citations

A comparator is a characterized reference cluster. Its literature describes that reference, not the focal locus in the report.

- **Activity + mechanism verified** means both fields were found in bound primary literature for the comparator.
- **Activity verified; mechanism unresolved** means the comparator's reported activity was found, but the selected evidence did not establish a mechanism or molecular target.
- **Comparator context unresolved** means a comparator accession exists, but the current curated table does not verify the requested field.
- **No admitted comparator** means the row has no comparator accession. It is not evidence that no related cluster exists.
- A dash is a compact cell-level unresolved marker. Its accessible label and hover title preserve the exact machine status.

Each citation link is paired with a PMID and a local evidence locator. The locator is relative to the curated table, and its SHA-256 must match the actual file. A plausible-looking hash for a missing file is rejected.

Neutral example: if `BGC0000001` has a primary paper that reports antibacterial activity but does not state a target, the activity cell may be verified and linked to the paper while the mechanism cell remains a dash. That does not make `DEMO-A / NODE_7_length_47000_cov_20.0 / region001 / BGC004` antibacterial.

### Whole-region and coherent-component metrics

antiSMASH regions can merge more than one biological neighborhood. Keep the original whole-region fraction and add a local component view only when gene order supports a coherent comparator-matched block.

For example, `25 / 47` matched CDS remains the whole-region result. If 24 matches occupy genes 1–26 and one match is an isolated outlier, the component view is `24 / 26 (92.3%)`, genes 1–26, plus one outlier. The higher local percentage does not replace `25 / 47`. It supports pathway-family context while an `OVERMERGED_REGION_COMPONENT_BOUNDARIES_REQUIRE_REVIEW` hold remains active. Core markers elsewhere in the region must be reported separately; their presence does not prove exact product or pathway completeness.

Build a provenance-bound component row from a per-gene evidence table:

```bash
python deliverable_tools/mibig_component_context.py \
  --evidence-tsv functional_evidence.tsv \
  --identity "DEMO-A / NODE_7_length_47000_cov_20.0 / region001 / BGC004" \
  --mibig-accession BGC0000001 \
  --evidence-extract evidence/sources/DEMO-A_NODE_7_length_47000_cov_20.0_region001_BGC004.tsv \
  --evidence-locator sources/DEMO-A_NODE_7_length_47000_cov_20.0_region001_BGC004.tsv \
  --out evidence/comparator_component_context.tsv
```

Pass that table with `--comparator-component-context`. The renderer verifies the exact identity, arithmetic, controlled interpretation, relative locator, file existence, and hash before displaying it.

## Batch enrichment without changing source reports

`batch_mibig_comparator_context.py` recursively finds `REPORT.html` files, validates every report before writing anything, and creates an additive copy tree. The output must be outside the source tree.

```bash
python deliverable_tools/batch_mibig_comparator_context.py \
  --report-root authoritative_reports \
  --out-root enriched_report_copies \
  --mibig-json-dir mibig_json \
  --curated-comparator-context evidence/comparator_context.tsv \
  --comparator-component-context evidence/comparator_component_context.tsv \
  --receipt-out enriched_report_copies/BATCH_RECEIPT.json
```

The receipt records portable relative locators and before/after hashes. It never needs an absolute user directory. Re-hash the source `REPORT.html` files after the run and compare them with `source_sha256` to prove that the authoritative inputs did not change.

## Static gene-order and GCF figure

Use `bigscape_gene_domain_context.py` after selecting one GCF and binding every member to its exact region GBK. The tool normalizes gene direction around a shared anchor, summarizes antiSMASH domains, shows direct BiG-SCAPE distances, and computes deterministic reciprocal-best protein 5-mer similarities. These are comparison aids, not BLAST identities.

```bash
python deliverable_tools/bigscape_gene_domain_context.py \
  --membership cohort_report/BIGSCAPE_LOCUS_MEMBERSHIP.tsv \
  --direct-edges cohort_report/BIGSCAPE_DIRECT_EDGES.tsv \
  --family-id 12 --focal-strain DEMO-A \
  --gbk-dir exact_region_gbks --out-dir gcf_context \
  --figure-png gcf_context/GCF_0012_CONTEXT.png \
  --figure-pdf gcf_context/GCF_0012_CONTEXT.pdf
```

The static figure contains three linked views: gene order and domains, the run-specific GCF network, and domain counts. Every locus is displayed with the complete `strain / full node-or-contig / region / BGC alias` identity. Inspect the rendered PNG and every PDF page before delivery.

### Smoother stacked locus maps

`stacked_locus_map.py` is the portable presentation layer for a manuscript-style query/comparator locus panel. It reads an explicit JSON specification rather than inferring biology. Track-relative base-pair coordinates preserve a shared true scale; reverse a comparator in the prepared specification when a homologous segment is displayed in the opposite orientation. Gene symbols appear above consistent arrow glyphs, role colors use one restrained palette, and optional submitted protein-identity links are drawn as translucent ribbons.

```bash
python deliverable_tools/stacked_locus_map.py \
  --spec exact_locus_map.json \
  --out-prefix figures/exact_locus_map \
  --receipt figures/exact_locus_map_receipt.json
```

The tool emits vector SVG plus manuscript PNG and PDF. The complete query identity appears outside the gene track, while track boundaries are marked explicitly. Labels are assigned to deterministic lanes; if the configured lanes cannot prevent collisions, the renderer exits without claiming success. Role labels and ribbons must already be evidence bound by the caller. They remain comparative context and do not raise product, expression, activity, mechanism, novelty, or completeness claims.

## Using a browser assistant

Open the generated HTML copy in a current browser or a browser assistant that can inspect local files. Use it for navigation, accessibility checks, and visual review, not as an evidence source.

1. Confirm that the page contains exactly one comparator-context block and one GCF integration block.
2. At a typical laptop width, verify that the wide comparator table scrolls horizontally instead of compressing text into unreadable columns.
3. Tab through citation links and confirm that every dash and badge has an accessible status label.
4. Hover or click each network node and confirm the complete locus identity appears.
5. Compare displayed counts with the JSON receipt. If the browser view and receipt differ, hold delivery and regenerate.

Do not paste private paths, credentials, unpublished identifiers, or unbound scientific claims into a browser assistant prompt. The generated HTML is self-contained; the assistant is a viewing aid, not part of the provenance chain.

## Common mistakes

- Treating comparator activity as focal-locus activity.
- Converting `NO_VERIFIED_SEARCH` into `VERIFIED_NO_HIT`.
- Replacing a whole-region denominator with a favorable component denominator.
- Calling a region complete because minimal core markers are present.
- Reading a small BiG-SCAPE distance as percentage identity.
- Guessing a BGC alias or accepting a displayed identity that disagrees with its component fields.
- Trusting a recorded hash without confirming that the bound evidence file exists.
- Writing enriched HTML back into the authoritative report tree.
- Shipping a screenshot or PDF that was rendered but not visually inspected.

## Glossary

- **BGC:** biosynthetic gene cluster; here, always identified by strain, full node or contig, region, and BGC alias.
- **Comparator:** a characterized MIBiG reference used for bounded comparison.
- **GCF:** gene cluster family created by one named BiG-SCAPE run and cutoff.
- **Direct edge distance:** BiG-SCAPE similarity distance for a directly recorded pair, not sequence identity.
- **Coherent component:** a dense local block of comparator-matched genes inside a broader region.
- **Whole-region fraction:** comparator-matched CDS divided by every CDS in the reported antiSMASH region.
- **Provenance binding:** a relative evidence locator plus the SHA-256 of the file that was actually read.
- **Claim ceiling:** the strongest interpretation permitted by the admitted evidence.

## Interpretation

GCF membership and direct edge distance are run- and cutoff-specific region-similarity context only. They can route gene-level comparison, but they do not establish pathway completeness, a shared or exact product, expression, production, activity, novelty, enrichment, host adaptation, or physical cross-contig linkage. Host comparisons require genus-aware sampling. `NO_VERIFIED_SEARCH` is not `VERIFIED_NO_HIT`.
