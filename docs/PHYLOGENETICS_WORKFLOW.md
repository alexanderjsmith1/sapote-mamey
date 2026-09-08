# Phylogenetics workflow (Sapote-Mamey, generic)

The standard procedure for placing bacterial strains on a trustworthy tree. Generic — applies to any
actinomycete or bacterial genome set; carries no project/organism/collection specifics. Two tiers: a fast
MLSA **screen** to find each query's neighborhood, then a **core-genome** resolve on a pruned panel, gated by
sign-off before anything is shown.

## Inputs / outputs
- **In:** query assemblies (FASTA) + reference genomes from `assets/reference_genomes/`; the decided outgroup
  from `assets/outgroup_registry.tsv`.
- **Out:** one signed-off tree per taxon (per `runs/phylo/<taxon>_<method>_<date>/`): alignment, `.treefile`
  with SH-aLRT + UFBoot support, a whole-genome ANI table, and a sign-off report.

## The rule that prevents the #1 defect (bad rooting)
- A **genus** tree roots on a **sister genus, same family** (one rank out).
- A **family/backbone** tree roots **outside the family**, on a sister-family/order genus.
- **Never** root on an ingroup member; **never** on a distant taxon; the outgroup genus must not also appear
  in the ingroup. The outgroup is not chosen ad hoc — it is looked up in `outgroup_registry.tsv` by
  `(taxon, scope)`. If a taxon has no registered outgroup, the tooling **fails loud** ("add a row"), never guesses.

## Steps (linear; one taxon at a time, smallest first)
1. **Scope** — the taxon (genus or family), the query genomes, the tree scope (genus vs family).
2. **MLSA screen** — concatenated single-copy markers over a broad candidate pool → place each query, find its
   nearest *named* species. Fast, low CPU. → `runs/phylo/<taxon>_mlsa_<date>/screen.treefile`.
3. **Prune the panel** — keep query + clade + ~6 named references + the registry outgroup for `(taxon, scope)`.
   Record one documented comparator-selection criterion. → `panel.tsv`.
4. **ANI** — whole-genome ANI (e.g. fastANI) from each query to the nearest *named* species. Report values
   within ~1% of 95% as boundary/indeterminate; never quote amino-acid identity (AAI) as nucleotide ANI. → `ani.tsv`.
5. **Core-genome resolve** — a single-copy-gene set (e.g. GToTree) on the pruned panel → a maximum-likelihood
   tree (e.g. IQ-TREE) with **SH-aLRT + UFBoot** support. (CPU-heavy — gate on operator approval.) → `tree.treefile`.
6. **Hard sanity gate** — `tree_sanity_check.py tree.treefile` MUST PASS (no dominating/long terminal branch)
   before the tree is rendered or shown. A tree that fails here is not displayed.
7. **Sign-off gate** — `signoff_check.py tree.treefile`: outgroup sanity, ANI honesty, assembly-quality caption,
   comparator provenance, label integrity, support + sampling, no rogue/MAG tips. Fix + re-run until PASS.
8. **Relabel + render** — consistent `Genus species strain` tips, current taxonomy; render figure + caption.

## Policies (declared per project, NOT baked into the engine)
- Which strains are in scope, their importance tier (→ order/depth), and privacy tier (→ what may be published)
  come from the project's `PROJECT.yaml`.
- Keeping distinct sampling sources in separate trees is a **project policy** (declared per project), not an
  engine rule — the engine provides the mechanism (separate runs), the project decides the grouping.

*Claim-safety: trees give taxonomy/novelty context (class-level). No bioactivity/structure claims. Judgment deferred.*
