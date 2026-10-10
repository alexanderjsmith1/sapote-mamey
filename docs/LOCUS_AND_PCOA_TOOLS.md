# Read locus maps, gene tables and protein PCoA comparisons

The optional `gap-rescue` command runs after validation and requires separately provisioned search inputs. It is a screen, not an adjudication. The main extraction command does not launch it. Use `python mamey_run.py gap-rescue --help` to check its inputs and output destination before authorizing a run.

`tools/gap_rescue_gene_table.py` pairs a reference-gene table with the locus map. Each reference gene has one row; a displayed split lists both pieces together in that row. The table includes local protein lengths; the reference-length extension is not included in this cut. Captions distinguish reference-gene counts from distinct local proteins. Homology does not establish physical linkage, product identity or production.

`tools/locus_reading_pages.py` builds Markdown reading pages from supplied packages, annotation ledgers and optional comparison evidence. Run its `--help` from the bundle root to bind the required arguments. Search inputs, when supplied, can trigger additional searches; omit them for an existing-evidence reading pass and retain the reported unsearched states. Each locus retains strain / full node-or-contig / region / BGC alias. Hand assessments remain separately authored material.

`tools/protein_pcoa_compare.py` consumes an existing protein PCoA kit and a cohort table. Its denominator uses cohort members represented in the kit's canonical per-set tables before set selection. It records denominator membership and hashes contributing tables, including unselected sets. Genome-level tests are primary; protein-level tests are secondary and pairwise p-values are raw, exploratory values. Similarity and position do not establish activity or resistance.

`tools/pcoa_bgc_explorer.py` adds an offline rotatable three-axis view of the same coordinates. Rotation changes the display, not the scores or point membership. Points without identity values retain a separate symbol. Supplied metadata and disagreements are recorded rather than silently inferred.

Use [figure house rules](FIGURE_HOUSE_RULES.md) and [figure style](FIGURE_STYLE.md) for exports. Inspect the actual rendered page and keep its caption, methods, source bindings and denominator together. Tools and command availability are listed by the generated [command catalog](COMMAND_CATALOG.generated.md) and [tools inventory](TOOLS_INVENTORY.generated.md).
