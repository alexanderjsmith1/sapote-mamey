# Domain & scan prevalence (cohort-wide widgets)

Turn a frozen cohort's antiSMASH domain and mamey-scan databases into a populated prevalence database, a
ranked review queue, and an **interactive host-filterable widget** (Bees & Wasps vs all, single-strain
drill-down, nr/ClusteredNR/Swiss-Prot evidence states, per-locus links, SVG figure export). Existing-evidence
analysis only — no new scans, no Mode-B cards. Class-level; rarity, relevance and evidence are separate axes;
absent annotation is not absent biology; similarity is not function; judgment deferred.

## When to run
After a cohort has its `antismash_gene_census` + `antismash_gbk_domains` SQLite (and optionally the
`blastp_nr/clustered_nr/swissprot` and mamey keyword-scan SQLite). Open every input read-only.

## Domains (Pfam / aSDomain / TIGRFAM / module)
```
python3 tools/domain_prevalence.py \
  --census   ANTISMASH_GENE_CENSUS.sqlite \
  --gbk-domains ANTISMASH_GBK_DOMAINS.sqlite \
  --nr NR.sqlite --cnr CNR.sqlite --sp SP.sqlite         # optional evidence channels \
  --host-tsv STRAIN_METADATA_CONSOLIDATED.tsv --host-source-col source \
  --exclude AS-XXX --host-override AS-XXX=ant            # per-strain owner rulings, explicit \
  --widget --out results/
```
Outputs: `domain_prevalence__v0.1.0.sqlite`, `domain_prevalence_ranking.json`, `domain_prevalence_widget.html`,
`figure_top20_*.svg`, `AUDIT_RECEIPT.json`.

## Mamey keyword scans (resistance / regulator / transporter / chitinase / …)
```
python3 tools/scan_prevalence.py --scan-db MAMEY_RESISTANCE_KEYWORDS.sqlite \
  --dataset-name mamey_resistance --host-tsv STRAIN_METADATA_CONSOLIDATED.tsv \
  --exclude AS-XXX --host-override AS-XXX=ant --widget --out results/resistance/
```
Emits the same ranking-JSON shape, so the identical widget renders it.

## Reading the widget
- **Host filter**: whole cohort, Bees & Wasps (bee+wasp+bee_or_wasp), or one host class. **Strain drill-down**: one strain's domains, ranked by cohort rarity.
- **Views**: Most-common, or Rarest (the review queue). **Evidence** columns: `nr h/n/m` (hit / no-hit / missing-search) and `sp h/n`; nr/ClusteredNR are selectively searched so *missing ≠ no-hit*; Swiss-Prot is complete.
- **loci (rare)** column lists exact loci for families in ≤5 loci. **Download chart (SVG)** turns any view into a figure.

## Governance
Denominators explicit; the excluded/held strains are visible; TIGR/Pfam labels are raw source labels (see the
domain-annotation DB for human descriptions + citations when available). Do not read a gate/prevalence figure
as a claim about a strain.

## Plain-English Pfam names (optional enrichment)
`tools/domain_prevalence_widget.py` auto-enriches clusterhmmer (Pfam) families with descriptions if a
`pfam_desc_map.json` sits in the same OUT dir as `domain_prevalence_ranking.json`. Build it once from the
local Pfam-A.hmm (a registered asset — do NOT re-download):
```
python3 tools/build_pfam_desc_map.py --hmm BigSCAPE/Pfam-A.hmm --out <OUT_dir>
python3 tools/domain_prevalence.py ... --out <OUT_dir> --widget   # picks up the map automatically
```
Each rare Pfam family then shows its name (e.g. `DDE_Tnp_1_4` → "Transposase DDE domain group 1 [PF13701]"),
so a mobile-element family is not mistaken for a biosynthetic novelty candidate. TIGRFAM (`TIGR#####`) names are
not covered by Pfam and require a separate source. If the map is absent, the widget renders normally without names.
