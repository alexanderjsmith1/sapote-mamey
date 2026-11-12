# Domain & scan prevalence (cohort-wide widgets)

Review domain and scan prevalence using existing evidence.  
This page is for researchers preparing a prevalence review.

Turn a frozen cohort's antiSMASH domain and mamey-scan databases into a populated prevalence database, a
ranked review queue, and an **interactive host-filterable widget** (Bees & Wasps vs all, single-strain
drill-down, nr/ClusteredNR/Swiss-Prot evidence states, per-locus links, SVG figure export). It uses
existing evidence only; it runs no new scans. A rare domain is a review candidate, not a novelty claim, and a
missing annotation is not missing biology.

## When to run
After a cohort has its `antismash_gene_census` + `antismash_gbk_domains` SQLite (and optionally the
`blastp_nr/clustered_nr/swissprot` and mamey keyword-scan SQLite). Open every input read-only.

## Domains (Pfam / aSDomain / TIGRFAM / module)
```
python3 tools/domain_prevalence.py \
  --census   ANTISMASH_GENE_CENSUS.sqlite \
  --gbk-domains ANTISMASH_GBK_DOMAINS.sqlite \
  --nr NR.sqlite --cnr CNR.sqlite --sp SP.sqlite \
  --host-tsv STRAIN_METADATA_CONSOLIDATED.tsv --host-source-col source \
  --exclude "<excluded-ID>" --host-override "<admitted-nonexcluded-ID>=<reviewed-host-class>" \
  --widget --out project/domain_review_new
```
The optional nr/ClusteredNR/Swiss-Prot paths must be bound to the intended cohort and channel
schemas. Exclusions and host overrides are explicit choices; record them with the build.
The two ID placeholders are distinct: the override target must already belong to the admitted, nonexcluded denominator, and its host class requires reviewed metadata. The domain tool ignores an out-of-scope override and prints a `WARN --host-override <ID>: not in scope` line to stderr; the scan tool ignores it silently. Do not use an override to reinclude excluded evidence. See [the source-scoped prevalence guide](../docs/PREVALENCE_WORKFLOW.md#host-metadata-and-filtering).

The command is one shell invocation: comments after a continuation backslash would break it.

Outputs: `domain_prevalence__v0.1.0.sqlite`, `domain_prevalence_ranking.json`, `domain_prevalence_widget.html`,
`figure_top20_*.svg`, `AUDIT_RECEIPT.json`.

## Mamey keyword scans (resistance / regulator / transporter / chitinase / …)
```
python3 tools/scan_prevalence.py --scan-db MAMEY_RESISTANCE_KEYWORDS.sqlite \
  --dataset-name mamey_resistance --host-tsv STRAIN_METADATA_CONSOLIDATED.tsv \
  --exclude "<excluded-ID>" --host-override "<admitted-nonexcluded-ID>=<reviewed-host-class>" \
  --widget --out project/scan_review_new
```
Emits `domain_prevalence_ranking.json` in the compatible widget shape; `--widget` additionally
requests HTML/SVG. It does not emit the domain-prevalence SQLite. It writes its own
`AUDIT_RECEIPT.json`; inspect its source, scope and empty evidence-channel list,
and retain independent input bindings. Its
homology evidence counters are placeholders initialized to zero, not completed no-hit searches.

## Output preservation and partial results

Use a fresh output directory for each reviewed build. The domain builder removes an existing
`domain_prevalence__v0.1.0.sqlite` and overwrites ranking/receipt files; the scan builder overwrites
ranking JSON and its receipt. Neither command offers a dry-run or rollback contract. Inputs are opened SQLite
read-only, but that does not make outputs immutable or provenance complete.

If the widget step fails, the command exits 3 after writing the ranking tables. Retry the widget separately with
`python3 tools/domain_prevalence_widget.py results/` after diagnosing the failed step.

## Reading the widget
- **Host filter**: whole cohort, Bees & Wasps (bee+wasp+bee_or_wasp), or one host class. **Strain drill-down**: one strain's domains, ranked by cohort rarity.
- **Views**: Most-common, or Rarest (the review queue). **Evidence** columns: `nr h/n/m` (hit / no-hit / missing-search) and `sp h/n`; the builder distinguishes VERIFIED_HITS, VERIFIED_NO_HIT, VERIFIED_MIXED_OUTCOMES and other/missing
states. None of these optional channel databases is guaranteed complete by this command. An absent
database yields zeroed counters rather than a measured all-no-hit result; record channel presence
and admitted search coverage separately.
- **loci (rare)** lists source loci for families within `--rare-loci-max` (default 5).
  It displays full exact identity when supplied, otherwise an explicit
  `IDENTITY_HOLD` with a source locator. **Download chart (SVG)** exports the view.

## Governance
Retain the exact denominator, exclusions and held-feature ledger beside the build. The domain SQLite
metadata records requested exclusions and held-feature counts, but the widget is not a complete exclusion
receipt. Optional homology inputs and host metadata also need independently retained locators and hashes.
TIGR/Pfam labels are raw source labels, not evidence of functional confirmation.

The widget footer sums saved hit, no-hit, mixed and missing states per gene-domain
entry across the ranking rows, separately for nr, ClusteredNR and Swiss-Prot. A
protein contributing to several feature rows can contribute several entries;
these are not unique-protein or completed-search counts. Missing means no saved
state, not a no-hit. Do not use a
prevalence figure as a functional or novelty claim about a strain.

## Plain-English Pfam names (optional enrichment)
`tools/domain_prevalence_widget.py` auto-enriches clusterhmmer (Pfam) families with descriptions if a
`pfam_desc_map.json` sits in the same OUT dir as `domain_prevalence_ranking.json`. Build it once from the
local Pfam-A.hmm (a registered asset — do NOT re-download):
```
python3 tools/build_pfam_desc_map.py --hmm BigSCAPE/Pfam-A.hmm --out project/domain_review_new
```
Build that map before running the complete domain command above with the same
output folder; do not run a literal `...` as a command argument.
Each mapped rare Pfam family can then show its name (e.g. `DDE_Tnp_1_4` → "Transposase DDE domain group 1 [PF13701]"),
to aid interpretation. A description does not itself verify function or prevent
a mistaken novelty claim. TIGRFAM (`TIGR#####`) names are
not covered by Pfam and require a separate source. If the map is absent, the widget renders normally without names.

## Related pages

For a single locus and its evidence channels, see [Mode B](Mode-B.md).
